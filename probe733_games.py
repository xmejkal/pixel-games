"""
P733 step 2: the 440 Hz tone beside the game loop, refilled once per frame by Python, through stock machine.I2S.

    mpremote run probe733_games.py      # GAME, TONE and SECONDS set by sed before each run

TONE = 0 is the control run: the same game, restarts and presses, with no I2S. It changes no file in games/: it
replaces App.frame with a hook that refills the tone after each frame, switches to a new copy of the game every 60 s
(the heavy frame of D19), and presses BOOT on the game-over screen, so the game plays most of the time.

ibuf=4096 gives 8 DMA buffers of 256 samples (16 ms), and the ESP-IDF queue takes 7 (machine_i2s.c:152,
i2s_common.c:329). The probe keeps a lead of 6 buffers (96 ms), so a write always finds a free buffer and does not
block. A frame longer than 96 ms runs the buffers dry: that is a `dry` count, not proof of a gap the ear hears.

Lines: `sound <game> between_max <ms> write_max <ms> dry <n> lead_min <samples>` every 5 s, `switch <n> <ms>`, and
at the end `written <samples> expected <samples>`, then `done`. The App prints its own fps and time lines.

Step 3, MIC = 1 (D18, D22: a separate run): the microphone on the second controller hears the speaker and counts the
gaps in the tone. It opens on the first frame, and the tone opens 1.5 s later, so the run measures the room first.
Lines: `mic dma_free <B> largest <B>` before it opens, `gap <ms since the microphone opened> <length ms>`, and
`mic <game> gaps <n> lost <samples> blind <n> tone_mean <n> floor <n>` every 5 s.
"""

import math
import time
from array import array

import micropython
from machine import I2S, Pin

GAME = "Fire"  # Fire, BallPit or Road: a name in app
TONE = 1  # 0: the control run, no I2S
MIC = 0  # 1: the microphone counts the gaps (step 3)
SECONDS = 300
SWITCH_MS = 60_000
REPORT_MS = 5000
RATE = 16000
CYCLE = 400  # exactly 11 cycles of 440 Hz at 16 kHz, so the wave has no seam
LEAD = 1536  # samples held ahead: 6 of the 7 queued DMA buffers of 256
AMPLITUDE = 3000  # of 32767, quiet


class Done(Exception):
    pass


# --- MVP ---
class Tone:
    """The 440 Hz tone, topped up to LEAD samples ahead at each refill. It counts the refills that came too late."""

    def __init__(self, sd, delay_ms=0):
        self.sd, self.i2s, self.delay_ms, self.open_at = sd, None, delay_ms, None
        wave = [int(AMPLITUDE * math.sin(2 * math.pi * 11 * i / CYCLE)) for i in range(CYCLE)]
        self.table = memoryview(array("h", (wave[i % CYCLE] for i in range(7 * CYCLE))))  # CYCLE + LEAD fit
        self.written = self.played = self.frac = self.phase = self.dry = 0
        self.last = 0
        self.reset()

    def reset(self):
        self.between_max, self.write_max, self.lead_min = 0, 0, LEAD

    def open(self):
        """delay_ms after the first refill, so the game is built before the I2S takes its memory."""
        self.i2s = I2S(0, sck=Pin(12), ws=Pin(13), sd=Pin(14), mode=I2S.TX, bits=16, format=I2S.MONO, rate=RATE,
                       ibuf=4096)
        self.last, self.opened = time.ticks_us(), time.ticks_ms()
        self.write(LEAD)
        self.sd.value(1)

    def write(self, n):
        t = time.ticks_us()
        self.i2s.write(self.table[self.phase:self.phase + n])
        self.write_max = max(self.write_max, time.ticks_diff(time.ticks_us(), t))
        self.written += n
        self.phase = (self.phase + n) % CYCLE

    def refill(self):
        if self.i2s is None:
            now = time.ticks_ms()
            if self.open_at is None:
                self.open_at = time.ticks_add(now, self.delay_ms)
            if time.ticks_diff(now, self.open_at) >= 0:
                self.open()
            return
        now = time.ticks_us()
        gap, self.last = time.ticks_diff(now, self.last), now
        self.between_max = max(self.between_max, gap)
        self.frac += gap * RATE // 1000  # samples x 1000, kept small: no long int in the loop
        self.played += self.frac // 1000
        self.frac %= 1000
        lead = self.written - self.played
        if lead < 0:  # the buffers ran dry before this refill: start again from now
            self.dry += 1
            self.written, lead = self.played, 0
        self.lead_min = min(self.lead_min, lead)
        if lead < LEAD:
            self.write(LEAD - lead)

    def close(self):
        """PHYS-13 order: the amplifier off before the clocks stop. The 10 ms is a margin with no datasheet figure."""
        self.sd.value(0)
        time.sleep_ms(10)
        if self.i2s:
            self.i2s.deinit()


BLOCK = 64  # samples per block mean: 4 ms, so any gap of 8 ms or more holds one whole quiet block
FLOOR_MS = (500, 1500)  # the room, after the microphone's start-up zeros, before the tone opens at 1500
TONE_MS = (1700, 2700)  # the tone, after the amplifier's click
QUIET = 0.3  # a block is quiet below floor + QUIET x (tone_mean - floor)
BLIND_US = 13 * 16_000  # a wait of 13 or more DMA buffers: ESP-IDF can skip or drop buffers without a report


@micropython.viper
def block_mean(buf, offset: int) -> int:
    """The mean absolute value of BLOCK int16 samples from offset (in samples). ptr16 reads unsigned."""
    p = ptr16(buf)  # noqa: F821, a viper built-in
    s = 0
    i = offset
    end = offset + 64
    while i < end:
        x = p[i]
        if x >= 32768:
            x = 65536 - x
        s += x
        i += 1
    return s >> 6


class Mic:
    """The microphone on the second controller: it reads all that is ready each frame, without waiting, and counts
    the runs of quiet blocks while the tone plays. Its time is the count of samples received."""

    def __init__(self):
        import esp32
        import select

        heaps = esp32.idf_heap_info(8)  # MALLOC_CAP_DMA: the 32 KB come from here, not from the PSRAM heap
        print("mic dma_free %d largest %d" % (sum(h[1] for h in heaps), max(h[2] for h in heaps)))
        self.i2s = I2S(1, sck=Pin(8), ws=Pin(11), sd=Pin(10), mode=I2S.RX, bits=16, format=I2S.MONO, rate=RATE,
                       ibuf=32768)
        self.poll = select.poll()
        self.poll.register(self.i2s, select.POLLIN)
        self.poll.poll(0)  # a poll switches the I2S to reads that return at once (extmod/machine_i2s.c:621)
        self.buf = bytearray(16384)
        self.view = memoryview(self.buf)
        self.fill = self.samples = self.gaps = self.blind = 0
        self.opened = self.last = time.ticks_us()
        self.floors, self.tones, self.threshold, self.quiet_from = [], [], None, None
        self.floor = self.tone_mean = 0

    def read(self):
        now = time.ticks_us()
        if time.ticks_diff(now, self.last) >= BLIND_US:
            self.blind += 1
        self.last = now
        while True:
            n = self.i2s.readinto(self.view[self.fill:])
            if not n:
                return
            self.fill += n
            whole = self.fill // (2 * BLOCK)
            for k in range(whole):
                self.block(block_mean(self.buf, k * BLOCK))
            rest = self.fill - whole * 2 * BLOCK
            self.buf[:rest] = self.buf[whole * 2 * BLOCK:self.fill]
            self.fill = rest

    def block(self, mean):
        t = self.samples * 1000 // RATE
        self.samples += BLOCK
        if self.threshold is None:
            if FLOOR_MS[0] <= t < FLOOR_MS[1]:
                self.floors.append(mean)
            elif TONE_MS[0] <= t < TONE_MS[1]:
                self.tones.append(mean)
            elif t >= TONE_MS[1]:
                self.calibrate()
            return
        if mean < self.threshold:
            if self.quiet_from is None:
                self.quiet_from = t
        elif self.quiet_from is not None:
            self.gaps += 1
            print("gap %d %d" % (self.quiet_from, t - self.quiet_from))
            self.quiet_from = None

    def calibrate(self):
        self.floor, self.tone_mean = median(self.floors), median(self.tones)
        if self.tone_mean < 4 * self.floor or self.tone_mean < 200:
            print("mic slot empty tone_mean %d floor %d" % (self.tone_mean, self.floor))
            raise Done
        self.threshold = self.floor + QUIET * (self.tone_mean - self.floor)

    def lost(self):
        return time.ticks_diff(time.ticks_us(), self.opened) * RATE // 1_000_000 - self.samples - self.fill // 2

    def close(self):
        self.i2s.deinit()


def median(values):
    values = sorted(values)
    return values[len(values) // 2] if values else 0


class Probe:
    """The hook around App.frame: the refill, the 5 s report, the switch every 60 s, the press on game over, the end."""

    def __init__(self, tone):
        self.tone, self.mic, self.switches, self.start = tone, None, 0, None

    def after(self, app_, now):
        if self.start is None:
            self.start = self.report = now
            self.next_switch = time.ticks_add(now, SWITCH_MS)
            self.press_on_over(app_)
            if MIC:
                self.mic = Mic()
        if self.tone:
            self.tone.refill()
        m = self.mic
        if m:
            m.read()
        if time.ticks_diff(now, self.report) >= REPORT_MS:
            self.report = now
            t = self.tone
            if t:
                print("sound %s between_max %d write_max %d dry %d lead_min %d" % (
                    app_.game.name, t.between_max // 1000, t.write_max // 1000, t.dry, t.lead_min))
                t.reset()
            if m:
                print("mic %s gaps %d lost %d blind %d tone_mean %d floor %d" % (
                    app_.game.name, m.gaps, m.lost(), m.blind, m.tone_mean, m.floor))
        if time.ticks_diff(now, self.next_switch) >= 0:
            self.next_switch = time.ticks_add(self.next_switch, SWITCH_MS)
            t = time.ticks_us()
            app_.switch()
            self.switches += 1
            print("switch %d %d" % (self.switches, time.ticks_diff(time.ticks_us(), t) // 1000))
        if time.ticks_diff(now, self.start) >= SECONDS * 1000:
            raise Done

    def press_on_over(self, app_):
        """Nobody presses BOOT, and a game waits on its game-over screen for a press (gfx.Game.step)."""
        import gfx

        update = app_.fire.update

        def pressing(now_ms):
            game = app_.game
            return update(now_ms) or (game.state == gfx.OVER and game.age >= game.OVER_MS)

        app_.fire.update = pressing


def main():
    import app

    sd = Pin(6, Pin.OUT, value=0)  # the amplifier stays off through the display setup
    tone = Tone(sd, 1500 if MIC else 0) if TONE else None
    probe = Probe(tone)
    frame = app.App.frame

    def hooked(self):
        frame(self)
        probe.after(self, time.ticks_ms())

    app.App.frame = hooked
    try:
        app.run(games=(getattr(app, GAME),))
    except Done:
        pass
    finally:
        if tone:
            tone.close()
        if probe.mic:
            probe.mic.close()
    if tone and tone.i2s:
        print("written %d expected %d" % (tone.written, time.ticks_diff(time.ticks_ms(), tone.opened) * RATE // 1000))
    print("done")
# --- MVP ---


if __name__ == "__main__":
    main()
