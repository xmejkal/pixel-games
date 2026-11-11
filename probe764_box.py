"""
P764 (#1051): the game box with its knob and its volume pane, in every game. --- MVP (P764) ---

Copy the games to the board, then, from the repository root:

    mpremote run probe764_box.py

The probe runs the game box (app.run) and hooks App.frame, as probe733_games.py does. It stays SECONDS in each game,
then moves to the next one, as a D14 press does, and ends after the last game. The box prints its own `game`, `fps`
and `time` lines. The probe adds one line per game: `box <name> windows_max <n> spins <n> level <n>`: the most windows
that one show() sent, the spins that ended in this game, and the step at the end. `knob 1` or `knob 0` at the first
frame says if the box has a knob. A box with no knob (the code before P764's knob) runs too, with no spin.

SPIN_EVERY_MS is the run with no hand: at this period the step moves by 1 per frame to an end (0, then 16, in turn),
so the volume pane shows. 0 is no spin.
"""

import time

SECONDS = 12  # in each game: two `time` lines of the box
SPIN_EVERY_MS = 0


class Done(Exception):
    """Raised in the hook to end app.run(), after the last game."""


class Probe:
    until = None  # the end of this game's time, set at the first frame

    def enter(self, now):
        self.until = time.ticks_add(now, SECONDS * 1000)
        self.next_spin, self.spin = time.ticks_add(now, SPIN_EVERY_MS), 0  # spin: the step per frame, or 0
        self.windows_max, self.spins = 0, 0

    def after(self, box, now):
        knob = getattr(box, "knob", None)
        if self.until is None:
            print("knob %d" % (1 if knob else 0))
            self.enter(now)
        self.windows_max = max(self.windows_max, getattr(box.out, "windows", 0) or 0)
        if SPIN_EVERY_MS and knob:
            step = knob.volume.step
            if not self.spin and time.ticks_diff(now, self.next_spin) >= 0:
                self.spin = -1 if step else 1
            knob.volume.set(step + self.spin)
            if knob.volume.step == step and self.spin:  # at an end
                self.spin, self.next_spin = 0, time.ticks_add(now, SPIN_EVERY_MS)
                self.spins += 1
        if time.ticks_diff(now, self.until) >= 0:
            print("box %s windows_max %d spins %d level %d" % (
                box.game.name, self.windows_max, self.spins, knob.volume.step if knob else -1))
            if box.index == len(box.games) - 1:
                raise Done
            box.switch()
            self.enter(time.ticks_ms())


def main():
    import app

    probe = Probe()
    frame = app.App.frame

    def hooked(self):
        frame(self)
        probe.after(self, time.ticks_ms())

    app.App.frame = hooked
    try:
        app.run()
    except Done:
        pass
    print("done")


if __name__ == "__main__":
    main()
