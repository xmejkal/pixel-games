"""
P733 steps 2 and 3: the 440 Hz tone beside the game loop, refilled once per frame by Python, through stock machine.I2S.

    mpremote run probe733_games.py      # GAME, TONE, MIC and SECONDS set by sed before each run

TONE = 0 is the control run: the same game, restarts and presses, with no tone. It changes no file in games/: it
replaces App.frame with a hook that refills the tone after each frame, switches to a new copy of the game every 30 s
(the heavy frame of D19), and presses BOOT on the game-over screen, so the game plays most of the time.

ibuf=4096 gives 8 DMA buffers of 256 samples (16 ms), a ring of 128 ms (machine_i2s.c:152). A poll switches the
writes to not waiting (machine_i2s.c:239): each refill writes what fits in the free buffers and returns at once.
The first version kept a lead of 96 ms with waiting writes, and each refill waited about 40 ms (run140, entry 2).
A refill more than 112 ms after the last one can find the ring empty: that is a `late` count. `short` is the samples
the clock expected minus the samples written. It moves by up to about 300 samples with no break, so only a rise
between reports by more than that means the speaker played silence.

Lines: `sound <game> between_max <ms> write_max <ms> late <n> short <samples>` every 5 s, `switch <n> <ms>`, and
at the end `written <samples> short <samples>`, then `done`. The App prints its own fps and time lines.

Step 3, MIC = 1 (D18, D22: a separate run): the microphone on the second controller hears the speaker and counts the
gaps in the tone. It opens on the first frame, and the tone opens 2.5 s later, so the run measures the room first.
Lines: `mic dma_free <B> largest <B>` before it opens, `gap <ms since the microphone opened> <length ms>`, and
`mic <game> gaps <n> lost <samples> blind <n> tone_mean <n> floor <n>` every 5 s.

P746, HITS = "auto" or "press" (with MIC = 1): silence instead of the tone, and a beep at each hit, a game event. The
refill keeps the ring full of silence, so a beep waits behind the whole ring. The microphone measures the delay from
the start of the frame that sees the hit to the beep: `hit <n> delay <ms> between <ms>`, or `hit <n> missed`
(`lost` stays in the 5 s line: inside a read it counts a block twice), and at the end `hits <n> median <ms> max <ms> missed <n>`. No game restarts in these runs. IBUF sets the ring.
"""

import math
import time
from array import array

import micropython
from micropython import const
from machine import I2S, Pin

GAME = "Fire"  # Fire, BallPit or Road: a name in app
TONE = 1  # 0: the control run, no I2S
MIC = 0  # 1: the microphone counts the gaps (step 3), or measures the delays (HITS)
HITS = 0  # "auto": a hit every 2 s from 4 s on, "press": a hit at each BOOT press, 0: the tone (P746)
IBUF = 4096  # TX DMA bytes: 8 buffers of 256 samples, a ring of 128 ms; 8192 gives 16 buffers, 256 ms
SECONDS = 120
SWITCH_MS = 30_000
REPORT_MS = 5000
RATE = 16000
CYCLE = 400  # exactly 11 cycles of 440 Hz at 16 kHz, so the wave has no seam
RING = IBUF // 2  # samples in the TX DMA buffers
LATE_US = (IBUF // 512 - 1) * 16_000  # all buffers but one: a refill later than this can find the ring empty
AMPLITUDE = 10000  # of 32767: at 3000 the microphone heard the tone no louder than the room (run141)
BEEP = 20000  # a beep's amplitude: the tone at 10000 read 16 to 21 against a room of 0 to 5, too close for an onset
BEEP_SAMPLES = 960  # 60 ms
HIT_EVERY_MS = 2000
HIT_FROM_MS = 4000  # after the beeper opens (2.5 s) and the microphone's floor is set
ONSET_MS = 400  # a hit with no beep heard in this time is missed


# --- MVP ---
class Done(Exception):
    """Raised in the hook to end app.run(): at SECONDS, or when the microphone hears no tone."""


class Tone:
    """The 440 Hz tone. Each refill fills the free DMA buffers without waiting. It counts the refills that came too late."""

    def __init__(self, sd, delay_ms=0):
        self.sd, self.i2s, self.delay_ms, self.open_at = sd, None, delay_ms, None
        # the table holds CYCLE + RING samples or more, the longest slice a write takes
        cycles = RING // CYCLE + 2
        self.table = memoryview(array("h", (int(AMPLITUDE * math.sin(2 * math.pi * 11 * i / CYCLE)) for i in range(cycles * CYCLE))))
        self.written = self.phase = self.late = self.last = self.between = 0
        self.opened_ms = None
        self.reset()

    def reset(self):
        self.between_max, self.write_max = 0, 0

    def open(self):
        """The I2S, a fill, then the amplifier on, delay_ms after the first refill. The first fill writes nothing,
        because the ESP-IDF queue starts empty, so the tone starts one ring (128 ms) later (i2s_common.c:1325)."""
        import select

        self.i2s = I2S(0, sck=Pin(12), ws=Pin(13), sd=Pin(14), mode=I2S.TX, bits=16, format=I2S.MONO, rate=RATE,
                       ibuf=IBUF)
        self.poll = select.poll()
        self.poll.register(self.i2s, select.POLLOUT)
        self.poll.poll(0)  # a poll switches the I2S to writes that return at once (extmod/machine_i2s.c:622)
        self.last, self.opened_ms = time.ticks_us(), time.ticks_ms()
        self.fill()
        self.sd.value(1)

    def fill(self):
        """Write what fits in the free DMA buffers, from the current phase."""
        t = time.ticks_us()
        n = (self.i2s.write(self.table[self.phase:self.phase + RING]) or 0) // 2
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
        self.between = between = time.ticks_diff(now, self.last)
        self.last = now
        self.between_max = max(self.between_max, between)
        if between > LATE_US:
            self.late += 1
        self.fill()

    def short(self):
        """The samples the clock expected minus the samples written. It jitters by one buffer at each refill."""
        return time.ticks_diff(time.ticks_ms(), self.opened_ms) * (RATE // 1000) - self.written  # no long int

    def close(self):
        """PHYS-13 order: the amplifier off before the clocks stop. The 10 ms is a margin with no datasheet figure."""
        self.sd.value(0)
        time.sleep_ms(10)
        if self.i2s:
            self.i2s.deinit()


class Beeper(Tone):
    """Silence, and a beep at each hit: the sound of a game event (P746). The refill keeps the ring full of silence,
    so a beep waits behind the whole ring: the delay that A3 measures."""

    def __init__(self, sd, delay_ms=0):
        super().__init__(sd, delay_ms)
        self.table = memoryview(array("h", (int(BEEP * math.sin(2 * math.pi * 440 * i / RATE)) for i in range(BEEP_SAMPLES))))
        self.silence = memoryview(bytearray(2 * RING))
        self.left = 0

    def hit(self):
        self.left, self.phase = BEEP_SAMPLES, 0

    def fill(self):
        """The rest of a beep first, then silence in all the free DMA buffers, without waiting."""
        t = time.ticks_us()
        n = 0
        if self.left:
            n = (self.i2s.write(self.table[self.phase:self.phase + self.left]) or 0) // 2
            self.left -= n
            self.phase += n
        if not self.left:
            n += (self.i2s.write(self.silence) or 0) // 2
        self.write_max = max(self.write_max, time.ticks_diff(time.ticks_us(), t))
        self.written += n


BLOCK = const(64)  # samples per block mean, 1 << BLOCK_SHIFT: 4 ms, so any gap of 8 ms or more holds one whole quiet block
BLOCK_SHIFT = const(6)
TONE_OPEN_MS = 2500  # the tone opens this long after the microphone
FLOOR_MS = (1500, 2500)  # the room, after the microphone settles (about 1.3 s, run141), before the tone opens
TONE_MS = (3000, 4000)  # the tone: it starts one ring (128 ms) after it opens, after a frame and the click
TONE_MIN = 10  # the tone at 10000 read 16 to 21, the room 0 to 5 (run141): the 4 x floor margin is thin
QUIET = 0.3  # a block is quiet below floor + QUIET x (tone_mean - floor)
BLIND_US = 13 * 16_000  # a wait of 13 or more DMA buffers: ESP-IDF can skip or drop buffers without a report


@micropython.viper
def block_mean(buf, offset: int) -> int:
    """The mean |x - m| of BLOCK int16 samples from offset (in samples), with m their mean, so the microphone's
    constant offset does not count as sound (run141f). ptr16 reads unsigned."""
    p = ptr16(buf)  # noqa: F821, a viper built-in
    s = 0
    i = offset
    end = offset + BLOCK
    while i < end:
        x = p[i]
        if x >= 32768:
            x -= 65536
        s += x
        i += 1
    m = s >> BLOCK_SHIFT
    s = 0
    i = offset
    while i < end:
        x = p[i]
        if x >= 32768:
            x -= 65536
        x -= m
        if x < 0:
            x = 0 - x
        s += x
        i += 1
    return s >> BLOCK_SHIFT


def median(values):
    values = sorted(values)
    return values[len(values) // 2] if values else 0


class Mic:
    """The microphone on the second controller: it reads all that is ready each frame, without waiting, and counts
    the runs of quiet blocks while the tone plays. Its time is the count of samples received."""

    def __init__(self):
        import esp32
        import select

        heaps = esp32.idf_heap_info(8)  # MALLOC_CAP_DMA: the 32 KB come from here, not from the PSRAM heap
        print("mic dma_free %d largest %d" % (sum(h[1] for h in heaps), max(h[2] for h in heaps)))
        self.buf = bytearray(16384)  # before the I2S, so the clock below starts with the DMA
        self.i2s = I2S(1, sck=Pin(8), ws=Pin(11), sd=Pin(10), mode=I2S.RX, bits=16, format=I2S.MONO, rate=RATE,
                       ibuf=32768)
        self.opened_us = time.ticks_us()  # the sample clock starts here (run143d: 0 to 192 samples behind)
        try:
            self.poll = select.poll()
            self.poll.register(self.i2s, select.POLLIN)
            self.poll.poll(0)  # a poll switches the I2S to reads that return at once (extmod/machine_i2s.c:621)
        except Exception:
            self.i2s.deinit()
            raise
        self.view = memoryview(self.buf)
        self.fill = self.samples = self.gaps = self.blind = 0
        self.last = self.opened_us
        self.floors, self.tones, self.threshold, self.quiet_from = [], [], None, None
        self.floor = self.tone_mean = 0
        self.hits, self.delays, self.missed, self.pending, self.between = 0, [], 0, None, 0

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
                self.add_mean(block_mean(self.buf, k * BLOCK))
            rest = self.fill - whole * 2 * BLOCK
            self.buf[:rest] = self.buf[whole * 2 * BLOCK:self.fill]
            self.fill = rest

    def add_mean(self, mean):
        t = self.samples // (RATE // 1000)  # ms, with no long int
        self.samples += BLOCK
        if self.threshold is None:
            if FLOOR_MS[0] <= t < FLOOR_MS[1]:
                self.floors.append(mean)
            elif TONE_MS[0] <= t < TONE_MS[1]:
                self.tones.append(mean)
            elif t >= (FLOOR_MS[1] if HITS else TONE_MS[1]):
                self.calibrate()
            return
        if HITS:
            self.onset(t, mean)
            return
        if mean < self.threshold:
            if self.quiet_from is None:
                self.quiet_from = t
        elif self.quiet_from is not None:
            self.gaps += 1
            print("gap %d %d" % (self.quiet_from, t - self.quiet_from))
            self.quiet_from = None

    def hit(self, at_us, between):
        """A hit at at_us (ticks_us): its time in the microphone's sample clock, in ms."""
        self.hits += 1
        self.pending, self.between = time.ticks_diff(at_us, self.opened_us) // 1000, between

    def onset(self, t, mean):
        """The first block from the pending hit's time that reaches the threshold is its beep."""
        if self.pending is None or t < self.pending:
            return
        if mean >= self.threshold:
            self.delays.append(t - self.pending)
            print("hit %d delay %d between %d" % (self.hits, t - self.pending, self.between // 1000))
            self.pending = None
        elif t - self.pending > ONSET_MS:
            self.missed += 1
            print("hit %d missed" % self.hits)
            self.pending = None

    def calibrate(self):
        if HITS:
            self.floor = median(self.floors)
            self.threshold = max(4 * self.floor, TONE_MIN)
            return
        self.floor, self.tone_mean = median(self.floors), median(self.tones)
        if self.tone_mean < 4 * self.floor or self.tone_mean < TONE_MIN:
            print("mic slot empty tone_mean %d floor %d" % (self.tone_mean, self.floor))
            raise Done
        self.threshold = self.floor + QUIET * (self.tone_mean - self.floor)

    def lost(self):
        return time.ticks_diff(time.ticks_us(), self.opened_us) // 1000 * (RATE // 1000) - self.samples - self.fill // 2

    def close(self):
        self.i2s.deinit()


class Probe:
    """The hook around App.frame: the tone's refill, the microphone's read, the 5 s report, the switch every 30 s
    (none with HITS), the press on game over, the hits, and the end."""

    def __init__(self, tone):
        self.tone, self.mic, self.switches = tone, None, 0
        self.start = self.report = self.next_switch = self.next_hit = None

    def after(self, box, now):
        if self.start is None:
            self.start = self.report = now
            self.next_switch = None if HITS else time.ticks_add(now, SWITCH_MS)
            self.next_hit = time.ticks_add(now, HIT_FROM_MS)
            self.press_on_over(box)
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
            if t and t.i2s:
                print("sound %s between_max %d write_max %d late %d short %d" % (
                    box.game.name, t.between_max // 1000, t.write_max // 1000, t.late, t.short()))
                t.reset()
            if m:
                print("mic %s gaps %d lost %d blind %d tone_mean %d floor %d" % (
                    box.game.name, m.gaps, m.lost(), m.blind, m.tone_mean, m.floor))
        if self.next_switch is not None and time.ticks_diff(now, self.next_switch) >= 0:
            self.next_switch = time.ticks_add(self.next_switch, SWITCH_MS)
            t = time.ticks_us()
            box.switch()
            self.switches += 1
            print("switch %d %d" % (self.switches, time.ticks_diff(time.ticks_us(), t) // 1000))
        if time.ticks_diff(now, self.start) >= SECONDS * 1000:
            raise Done

    def press_on_over(self, box):
        """Nobody presses BOOT, and a game waits on its game-over screen for a press (gfx.Game.step)."""
        import gfx

        update = box.fire.update

        def pressing(now_ms):
            game = box.game
            pressed = update(now_ms)  # a real press: the probe's own press below is not a hit
            if HITS == "press" and pressed or HITS == "auto" and self.due(now_ms):
                self.hit()
            return pressed or (game.state == gfx.OVER and game.age >= game.OVER_MS)

        box.fire.update = pressing

    def due(self, now_ms):
        if self.next_hit is None or time.ticks_diff(now_ms, self.next_hit) < 0:
            return False
        self.next_hit = time.ticks_add(self.next_hit, HIT_EVERY_MS)
        return True

    def hit(self):
        """Stamped at the start of the frame that sees it. Skipped until the beeper opens and the floor is set, and
        while the last hit waits for its beep."""
        m, t = self.mic, self.tone
        if m and t and t.i2s and m.threshold is not None and m.pending is None:
            m.hit(time.ticks_us(), t.between)
            t.hit()


def main():
    import app

    sd = Pin(6, Pin.OUT, value=0)  # the amplifier stays off through the display setup
    tone = (Beeper if HITS else Tone)(sd, TONE_OPEN_MS if MIC else 0) if TONE else None
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
        print("written %d short %d" % (tone.written, tone.short()))
    m = probe.mic
    if m and HITS:
        print("hits %d median %d max %d missed %d" % (m.hits, median(m.delays), max(m.delays or [0]), m.missed))
    print("done")
# --- MVP ---


if __name__ == "__main__":
    main()
