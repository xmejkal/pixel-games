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
"""

import math
import time
from array import array

from machine import I2S, Pin

GAME = "Fire"  # Fire, BallPit or Road: a name in app
TONE = 1  # 0: the control run, no I2S
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

    def __init__(self, sd):
        self.sd, self.i2s = sd, None
        wave = [int(AMPLITUDE * math.sin(2 * math.pi * 11 * i / CYCLE)) for i in range(CYCLE)]
        self.table = memoryview(array("h", (wave[i % CYCLE] for i in range(7 * CYCLE))))  # CYCLE + LEAD fit
        self.written = self.played = self.frac = self.phase = self.dry = 0
        self.last = 0
        self.reset()

    def reset(self):
        self.between_max, self.write_max, self.lead_min = 0, 0, LEAD

    def open(self):
        """At the first refill, so the game is built before the I2S takes its memory."""
        self.i2s = I2S(0, sck=Pin(12), ws=Pin(13), sd=Pin(14), mode=I2S.TX, bits=16, format=I2S.MONO, rate=RATE,
                       ibuf=4096)
        self.last = time.ticks_us()
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


class Probe:
    """The hook around App.frame: the refill, the 5 s report, the switch every 60 s, the press on game over, the end."""

    def __init__(self, tone):
        self.tone, self.switches, self.start = tone, 0, None

    def after(self, app_, now):
        if self.start is None:
            self.start = self.report = now
            self.next_switch = time.ticks_add(now, SWITCH_MS)
            self.press_on_over(app_)
        if self.tone:
            self.tone.refill()
        if time.ticks_diff(now, self.report) >= REPORT_MS:
            self.report = now
            t = self.tone
            if t:
                print("sound %s between_max %d write_max %d dry %d lead_min %d" % (
                    app_.game.name, t.between_max // 1000, t.write_max // 1000, t.dry, t.lead_min))
                t.reset()
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
    tone = Tone(sd) if TONE else None
    probe = Probe(tone)
    frame = app.App.frame

    def hooked(self):
        frame(self)
        probe.after(self, time.ticks_ms())

    app.App.frame = hooked
    start = time.ticks_ms()
    try:
        app.run(games=(getattr(app, GAME),))
    except Done:
        pass
    finally:
        if tone:
            tone.close()
    if tone:
        print("written %d expected %d" % (tone.written, time.ticks_diff(time.ticks_ms(), start) * RATE // 1000))
    print("done")
# --- MVP ---


if __name__ == "__main__":
    main()
