"""
P768 (#1058): the game box with its Speaker, or with none, in one game. --- MVP (P768) ---

Copy the games to the board (also box_bank.raw), then, from the repository root:

    mpremote run probe768_box.py      # after sed set SOUND, GAME, SECONDS and PRESS_EVERY_MS

The probe runs the game box (app.run) and hooks App.frame, as probe764_box.py does. SOUND = 1 passes the box a
Speaker with the knob's volume, as main.py does, so one I2S opens and the knob turns the sound. SOUND = 0 is the control run: the same game and presses, and no I2S.
With no hand, the probe presses the game button every PRESS_EVERY_MS while the game plays, and once on the game-over
screen, so the game plays most of the time. 0 is no press: a hand plays.

The box prints its own `game`, `fps` and `time` lines. The probe adds, every 5 s:
`sound <game> sent <n> of <expected> between_max <ms> late <n> render_max <us> plays <n> presses <n>`. `sent` counts
the blocks of 256 samples of the window, and `expected` is one per 16 ms. `late` counts the refills since the open
that came later than the ring minus one block (sound.Refill). `render_max` is the longest Mixer.render of the window.
`plays` counts the sounds that the cues started in the window. With SOUND = 0 the line is `sound <game> off presses
<n>`. At the end: `late <n> written <samples>` (with SOUND), then `done`.
"""

import time

SOUND = 1  # 0: the control run, no I2S
GAME = "Runner"  # a class name in app
SECONDS = 120
PRESS_EVERY_MS = 900
REPORT_MS = 5000


class Done(Exception):
    """Raised in the hook to end app.run(), at SECONDS."""


class TimedMixer:
    """Wraps Mixer.render and Mixer.play of one Mixer: the longest render and the plays of the window."""

    def __init__(self, mixer):
        self.render_max = self.plays = 0
        render, play = mixer.render, mixer.play

        def timed(buf):
            t = time.ticks_us()
            render(buf)
            self.render_max = max(self.render_max, time.ticks_diff(time.ticks_us(), t))

        def counted(sound, loop=False):
            self.plays += 1
            return play(sound, loop)

        mixer.render, mixer.play = timed, counted


class Probe:
    def __init__(self, speaker):
        self.speaker, self.timed = speaker, TimedMixer(speaker.mixer) if speaker else None
        self.start = self.mark = self.next_press = None
        self.presses = self.sent = 0

    def press(self, box):
        """The probe's presses, added to the button's own."""
        import gfx

        update = box.fire.update

        def pressing(now):
            pressed, game = update(now), box.game
            if game.state == gfx.OVER:
                auto = game.age >= game.OVER_MS
            else:
                auto = game.state == gfx.PLAY and time.ticks_diff(now, self.next_press) >= 0
            if auto:
                self.next_press = time.ticks_add(now, PRESS_EVERY_MS)
                self.presses += 1
            return pressed or auto

        box.fire.update = pressing

    def after(self, box, now):
        if self.start is None:
            self.start = self.mark = self.next_press = now
            if PRESS_EVERY_MS:
                self.press(box)
        refill = self.speaker and self.speaker.refill
        if time.ticks_diff(now, self.mark) >= REPORT_MS:
            if refill:
                sent, timed = refill.sent_count, self.timed
                print("sound %s sent %d of %d between_max %d late %d render_max %d plays %d presses %d" % (
                    box.game.name, sent - self.sent, time.ticks_diff(now, self.mark) // 16,
                    refill.between_max // 1000, refill.late, timed.render_max, timed.plays, self.presses))
                refill.reset()
                self.sent, timed.render_max, timed.plays = sent, 0, 0
            else:
                print("sound %s off presses %d" % (box.game.name, self.presses))
            self.mark, self.presses = now, 0
        if time.ticks_diff(now, self.start) >= SECONDS * 1000:
            if refill:
                print("late %d written %d" % (refill.late, refill.written))
            raise Done


def main():
    import app

    knob = app.open_knob()  # as main.py: the knob's volume is the Speaker's master volume
    speaker = app.open_speaker(knob) if SOUND else None
    probe = Probe(speaker)
    frame = app.App.frame

    def hooked(self):
        frame(self)
        probe.after(self, time.ticks_ms())

    app.App.frame = hooked
    try:
        app.run(games=(getattr(app, GAME),), knob=knob, speaker=speaker)
    except Done:
        pass
    print("done")


if __name__ == "__main__":
    main()
