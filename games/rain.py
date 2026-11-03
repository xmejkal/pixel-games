"""
The rain (P593): the C engine beside Python. N boxes of 4 px fall from above the screen, bounce on a plane each and,
once asleep, fall again from the top. The stepper steps them: C (the engine module, engine/core/world.c) or Python
(motion.Bodies, the same maths). A BOOT tap swaps the stepper and starts the rain again from the same seed. The HUD
says the stepper, the step ms and the fps, over a bar as long as the step time.

Every REPORT_MS it prints, for the bench log, the average ms per frame of each phase:
    rain <stepper> n <N> fps <fps> step <ms> read <ms> draw <ms>
step is the stepper's steps, read is the read-back and the respawn of sleepers, draw is one fill per box. A swap
prints `stepper <c|python>` and starts a new interval, so each line holds one stepper.
--- probe, throwaway: slice 0 of the engine demos (P593); the binding it calls is P589's probe ---
"""

import random
import time
from array import array

from gfx import DARK, HEIGHT, LABEL_RECT, PALETTE, WHITE, WIDTH, YELLOW, Game
from motion import Bodies

try:
    import engine
except ImportError:  # an image without the engine module: Python only, and the HUD says "no C"
    engine = None

W, H = WIDTH, HEIGHT
N = 160  # boxes: set on the board to the most that keep C at 24 fps (the engine's cap is 256)
SIZE = 4
RATE = 100  # steps a second, so a step is STEP_MS (D18)
STEP_MS, DT = 1000 // RATE, 1 / RATE
GRAVITY, RESTITUTION, FRICTION = 2000.0, 0.35, 0.6  # stack's heavy floors (p582-heavy)
SEED = 593
REPORT_MS = 5000  # app.py's FPS_EVERY_MS, so a rain line comes with each of its time lines
HUD_MS = 500  # the HUD's text is rebuilt this often, and its strip is blitted every frame (P599)
BAR_US_PER_PX = 200  # the step bar: 1 px for each 0.2 ms of step in a frame, so 45 ms is 225 px


class CStepper:
    """The engine's float world: one C call steps every body, and read() copies x, y and asleep out as ints."""

    name = "c"

    def __init__(self):
        self.out = array("h", [0] * (3 * N))
        self.spawn = engine.spawn
        zero = array("f", [0.0] * N)
        engine.load(zero, zero, zero, zero, zero)  # exactly N bodies: the C world outlives a soft reset, so a run before
        # with a larger N would leave more bodies than self.out holds

    def step(self, steps):
        engine.step(engine.FLOAT, steps, RATE, GRAVITY, RESTITUTION, FRICTION)

    def read(self, drop):
        """The bodies out of C, then drop(i) for each one asleep."""
        out = self.out
        engine.read(out)
        for i in range(N):
            if out[3 * i + 2]:
                drop(i)  # out still holds its resting place, so paint shows it there one more frame (C mode only)

    def paint(self, cv, colours):
        out, fill = self.out, cv.fill
        for i in range(N):
            j = 3 * i
            fill(out[j], out[j + 1], SIZE, SIZE, colours[i])


class PythonStepper:
    """motion.Bodies: the same step in Python, one call per step. Its lists are the bodies, so read() only looks."""

    name = "python"

    def __init__(self):
        self.bodies = Bodies(N)
        self.spawn = self.bodies.spawn

    def step(self, steps):
        for _ in range(steps):
            self.bodies.step(DT, GRAVITY, RESTITUTION, FRICTION)

    def read(self, drop):
        asleep = self.bodies.asleep
        for i in range(N):
            if asleep[i]:
                drop(i)

    def paint(self, cv, colours):
        x, y, fill = self.bodies.x, self.bodies.y, cv.fill
        for i in range(N):
            fill(x[i], y[i], SIZE, SIZE, colours[i])


class Rain(Game):
    name = "rain"
    TITLE_MS = 0  # straight into the rain, so the first BOOT tap swaps the stepper
    COLOURS = tuple(PALETTE[i % len(PALETTE)] for i in range(N))

    def __init__(self):
        self.c = engine is not None
        super().__init__()

    def setup(self):
        random.seed(SEED)
        self.stepper = CStepper() if self.c else PythonStepper()
        for i in range(N):
            self.drop(i)
        self.acc, self.us, self.frames, self.mark = 0, [0, 0, 0], 0, self.last  # us: step, read, draw
        self.hud_step, self.hud_frames, self.hud_mark = 0, 0, self.last  # self.last: None before the first step
        self.shown = "python, no C" if engine is None else self.stepper.name
        self.label, self.bar = self.shown, 0
        print("stepper", self.stepper.name)

    def drop(self, i):
        """Box i, anew above the screen: a random column, height, drift and plane (D12: Python decides the respawn)."""
        self.stepper.spawn(i, random.randrange(W - SIZE), -SIZE - random.randrange(H), random.randrange(-40, 41), 0,
                           H - SIZE - random.randrange(40))

    def play(self, pressed, held):
        if pressed:
            self.c = engine is not None and not self.c
            self.restart()
            return
        self.acc += int(self.dt * 1000 + 0.5)  # whole 10 ms steps; the rest waits for the next frame
        steps = self.acc // STEP_MS
        self.acc -= steps * STEP_MS
        t0 = time.ticks_us()
        self.stepper.step(steps)
        t1 = time.ticks_us()
        self.stepper.read(self.drop)
        step = time.ticks_diff(t1, t0)
        self.us[0] += step
        self.us[1] += time.ticks_diff(time.ticks_us(), t1)
        self.hud_step += step

    def paint(self, cv):
        t = time.ticks_us()
        self.stepper.paint(cv, self.COLOURS)
        self.us[2] += time.ticks_diff(time.ticks_us(), t)
        self.count(self.last)

    def count(self, now):
        """One more frame at now, the frame's start in ms: the HUD's text twice a second, the report every REPORT_MS."""
        if self.mark is None:
            self.mark = self.hud_mark = now
        self.frames += 1
        self.hud_frames += 1
        elapsed = time.ticks_diff(now, self.hud_mark)
        if elapsed >= HUD_MS:
            step = self.hud_step // self.hud_frames
            self.label = "%s step %.1f ms %d fps" % (self.shown, step / 1000, self.hud_frames * 1000 // elapsed)
            self.bar = min(W, step // BAR_US_PER_PX)
            self.hud_step, self.hud_frames, self.hud_mark = 0, 0, now
        elapsed = time.ticks_diff(now, self.mark)
        if elapsed >= REPORT_MS:
            us, n = self.us, 1000 * self.frames
            print("rain %s n %d fps %d step %.2f read %.2f draw %.2f" % (
                self.stepper.name, N, self.frames * 1000 // elapsed, us[0] / n, us[1] / n, us[2] / n))
            self.us, self.frames, self.mark = [0, 0, 0], 0, now

    def hud(self, cv):
        """One short line and the step bar, drawn again only when either changes (P599)."""
        cv.keep((self.name, self.label, self.bar), LABEL_RECT, self.draw_hud)

    def draw_hud(self, cv):
        cv.fill(0, 0, W, LABEL_RECT[3], DARK)
        cv.text(self.label, 4, 2, WHITE)
        cv.fill(0, 11, self.bar, 3, YELLOW)
