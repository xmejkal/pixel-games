"""
The ball pit (P598): a few hundred round balls that fall, knock and pile in the box of the screen, the first bodies
in the engine that touch each other. The solver is C (engine/core/fx_balls.c, through engine.Balls, on the uniform grid
of grid.c); one C call steps every ball and one paints them all. A BOOT tap pours a handful of POUR balls from the
top, each pour in its own colour, so the heap shows layers; when the pit holds MAX, the next tap empties it and pours
again. Each hit is a fact in the event buffer that Python drains and counts (D12): the HUD shows the balls, the step and
draw ms, the fps and the hits a second. The pit assumes ORIENTATION 0 (lcd.py), as the fire does.

Every REPORT_MS it prints, for the bench log, the average ms per frame:
    balls n <n> fps <fps> step <ms> draw <ms> hits <n>
Without the engine module the HUD says "balls: no C" and nothing else is drawn.
--- MVP (P598) ---
"""

import math
import random
import time
from array import array

from gfx import BLACK, DARK, LABEL_RECT, WHITE, WIDTH, Game, c565
from motion import MAX_EVENTS, StepClock

try:
    import engine
except ImportError:  # the image with s3lcd only
    engine = None
# the import above succeeds on the Mac too: it finds the repository's engine/ folder, an empty package (P602). Only the
# C engine has Balls
if not hasattr(engine, "Balls"):
    engine = None

POUR = 25  # balls a tap
MAX = 320  # balls in the pit, engine.Balls' most, so the PO sees where it gets too slow ("dont empty it", 2026-11-04).
# On the board 100 keep about 24 fps, 185 run at 20, 320 at 8 (run99d, run100); P614 #820 makes the solver faster
R_MIN, R_MAX = 2, 5  # a ball's radius, random per ball (fx_balls.h's FX_BALLS_R_MIN and FX_BALLS_R_MAX)
DROP = 40  # a poured ball starts up to this far above the top
RATE = 100  # steps a second, so a step is STEP_MS (D18)
STEP_MS, DT = 1000 // RATE, 1 / RATE
STEP_CAP = 8  # steps a frame at most (D18); gfx clamps a frame to 60 ms, so it never acts today
SUBSTEPS = 4  # solver substeps a step: the overlap bar of tests/test_balls_core.py holds at 4, and the board measures 3
GRAVITY = 2000.0  # px/s2 (A7)
# The feel numbers, set from Mac runs (tests/test_balls_core.py's fixtures hold the same)
DAMPING = 0.98  # the part of its speed a ball keeps over one step: the settled pile's jitter fell from 5 to under 1 px/s
HIT_MIN = 60.0  # px/s: a hit counts from here, a fall of 1 px; a resting pile's loudest contact is 5 px/s, 0 hits at rest
SEED = 598
# --- MVP (P598): the shake, the PO 2026-11-04: "as long as I hold the button pressed the stronger the bump would be" ---
HOLD_MS = 300  # a press held this long or longer shakes on its release; a shorter one is a tap and pours
SHAKE_FULL_MS = 1500  # held this long, the bump is at full strength
SHAKE_MIN, SHAKE_MAX = 200.0, 600.0  # px/s; fx_balls' move cap (1.5 px a substep, 4 substeps of 2.5 ms) is 600
SHAKE_SPREAD = 1.0  # rad: the bump points up, up to this far to either side
# Twelve colours, one per pour in turn, so the heap shows layers; engine.Balls' palette holds 16, the rest black
POUR_COLOURS = (c565(230, 40, 40), c565(250, 140, 30), c565(250, 220, 40), c565(120, 220, 40), c565(40, 210, 70),
                c565(40, 220, 230), c565(50, 150, 240), c565(50, 90, 240), c565(130, 70, 230), c565(230, 60, 220),
                c565(240, 120, 160), c565(235, 235, 235))
PALETTE = array("H", POUR_COLOURS + (BLACK,) * (16 - len(POUR_COLOURS)))
BG = BLACK
REPORT_MS = 5000  # app.py's FPS_EVERY_MS, so a balls line comes with each of its time lines
HUD_MS = 500


class BallPit(Game):
    name = "balls"
    TITLE_MS = 0  # straight into the pit, so the first BOOT tap pours

    def __init__(self):
        self.covers = engine is not None  # C paints every pixel
        super().__init__()

    def setup(self):
        random.seed(SEED)
        self.balls = engine.Balls(MAX) if engine is not None else None
        self.clock = StepClock(STEP_MS, STEP_CAP)
        self.drained = array("i", [0] * (3 * MAX_EVENTS))  # made once: a frame drains into it and makes no list
        self.pressed_at = None  # the frame's start in ms when the button went down, until its release
        self.pours, self.hits = 0, 0  # pours so far; hits since the last report
        self.us, self.frames, self.mark = [0, 0], 0, self.last  # us: step, draw
        self.hud_us, self.hud_frames, self.hud_hits, self.hud_mark = [0, 0], 0, 0, self.last  # self.last: None before step
        self.label = self.name + (": no C" if self.balls is None else "")
        self.pour()

    def pour(self):
        """One tap's handful from the top, in the next pour's colour, as many as still fit: a full pit pours nothing, so
        the PO sees where it gets too slow ("dont empty it", 2026-11-04)."""
        if self.balls is None or self.balls.count >= MAX:
            return
        colour = self.pours % len(POUR_COLOURS)
        self.pours += 1
        for _ in range(min(POUR, MAX - self.balls.count)):
            r = random.randrange(R_MIN, R_MAX + 1)
            self.balls.spawn(random.uniform(r, WIDTH - r), -r - random.uniform(0, DROP), 0.0, 0.0, r, colour)

    def play(self, pressed, held):
        if pressed:
            self.pressed_at = self.last
        if self.pressed_at is not None and not held:  # the release, also in the press's frame: a tap pours, a hold shakes
            ms = time.ticks_diff(self.last, self.pressed_at)
            self.pressed_at = None
            if ms < HOLD_MS:
                self.pour()
            elif self.balls is not None:
                self.shake(ms)
        steps = self.clock.take(int(self.dt * 1000 + 0.5))
        if self.balls is None:
            return
        t = time.ticks_us()
        self.balls.step(steps, SUBSTEPS, DT, GRAVITY, DAMPING, HIT_MIN)
        self.add(0, t)
        hits = self.balls.drain(self.drained) + self.balls.dropped  # Python counts the hits (D12): its decision
        self.hits += hits
        self.hud_hits += hits

    def shake(self, ms):
        """Bump the box: every ball up and to a random side, faster the longer the button was held."""
        speed = SHAKE_MIN + (SHAKE_MAX - SHAKE_MIN) * min(ms, SHAKE_FULL_MS) / SHAKE_FULL_MS
        a = random.uniform(-SHAKE_SPREAD, SHAKE_SPREAD)
        self.balls.kick(speed * math.sin(a), -speed * math.cos(a))

    def add(self, i, t):
        """The time since t into the report's sum i and the HUD's."""
        us = time.ticks_diff(time.ticks_us(), t)
        self.us[i] += us
        self.hud_us[i] += us

    def paint(self, cv):
        if self.balls is None:
            return
        t = time.ticks_us()
        self.balls.draw(cv.tft, PALETTE, BG)
        self.add(1, t)
        self.count(self.last)

    def count(self, now):
        """One more frame at now, the frame's start in ms: the HUD's text twice a second, the report every REPORT_MS."""
        if self.mark is None:
            self.mark = self.hud_mark = now
        self.frames += 1
        self.hud_frames += 1
        elapsed = time.ticks_diff(now, self.hud_mark)
        if elapsed >= HUD_MS:
            us, n = self.hud_us, 1000 * self.hud_frames
            # fps first and whole ms, so the line fits the 39 glyphs of the screen (the PO, 2026-11-04): step+draw
            self.label = "%d fps %d balls %d+%d ms %d hit/s" % (
                self.hud_frames * 1000 // elapsed, self.balls.count, round(us[0] / n), round(us[1] / n),
                self.hud_hits * 1000 // elapsed)
            self.hud_us, self.hud_frames, self.hud_hits, self.hud_mark = [0, 0], 0, 0, now
        elapsed = time.ticks_diff(now, self.mark)
        if elapsed >= REPORT_MS:
            us, n = self.us, 1000 * self.frames
            print("%s n %d fps %d step %.2f draw %.2f hits %d" % (
                self.name, self.balls.count, self.frames * 1000 // elapsed, us[0] / n, us[1] / n, self.hits))
            self.us, self.frames, self.hits, self.mark = [0, 0], 0, 0, now

    def hud(self, cv):
        """One short line, drawn again only when it changes (P599)."""
        cv.keep((self.name, self.label), LABEL_RECT, self.draw_hud)

    def draw_hud(self, cv):
        cv.fill(0, 0, WIDTH, LABEL_RECT[3], DARK)
        cv.text(self.label, 4, 2, WHITE)
