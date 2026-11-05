"""
The rain (P593, P590): the C engine beside Python. N boxes of 4 px fall from above the screen, bounce on a plane each
and, once asleep, fall again from the top. Its one plugin, plugins.PhysicsPlugin, steps them on engine.Bodies
(engine/core/world.c) or on its twin motion.Bodies, the same maths in Python. A BOOT tap swaps the two and starts the
rain again from the same seed. The HUD says C or Python, the step ms and the fps, over a bar as long as the step time.

Every REPORT_MS it prints, for the bench log, the average ms per frame of each phase:
    rain <stepper> n <N> fps <fps> step <ms> read <ms> draw <ms>
step is the plugin's steps, read is the read-back and the respawn of sleepers, draw is one fill per box. A swap
prints `stepper <c|python>` and starts a new interval, so each line holds one stepper.
--- MVP (P590): the rain and the burning scene prove engine.Bodies; P633: on a PhysicsPlugin ---
"""

import random
import time

import plugins
from gfx import DARK, HEIGHT, LABEL_RECT, PALETTE, WHITE, WIDTH, YELLOW, Game
from plugins import PhysicsPlugin

W, H = WIDTH, HEIGHT
N = 160  # boxes: set on the board to the most that keep C at 24 fps (the engine's cap is 256)
SIZE = 4
SEED = 593
REPORT_MS = 5000  # app.py's FPS_EVERY_MS, so a rain line comes with each of its time lines
HUD_MS = 500  # the HUD's text is rebuilt this often, and its strip is blitted every frame (P599)
BAR_US_PER_PX = 200  # the step bar: 1 px for each 0.2 ms of step in a frame, so 45 ms is 225 px


class Rain(Game):
    name = "rain"
    TITLE_MS = 0  # straight into the rain, so the first BOOT tap swaps C and Python
    COLOURS = tuple(PALETTE[i % len(PALETTE)] for i in range(N))

    def __init__(self):
        self.c = plugins.engine is not None
        super().__init__()

    def setup(self):
        random.seed(SEED)
        self.physics_plugin = PhysicsPlugin(N, self.c)
        self.plugins = (self.physics_plugin,)  # --- MVP (P633) ---
        for i in range(N):
            self.drop(i)
        self.us, self.frames, self.mark = [0, 0, 0], 0, self.last  # us: step, read, draw
        self.hud_step, self.hud_frames, self.hud_mark = 0, 0, self.last  # self.last: None before the first step
        self.shown = "python, no C" if plugins.engine is None else self.physics_plugin.name
        self.label, self.bar = self.shown, 0
        print("stepper", self.physics_plugin.name)

    def drop(self, i):
        """Box i, anew above the screen: a random column, height, drift and plane (D12: Python decides the respawn)."""
        self.physics_plugin.spawn(i, random.randrange(W - SIZE), -SIZE - random.randrange(H), random.randrange(-40, 41),
                                  0, H - SIZE - random.randrange(40))

    def play(self, pressed, held):
        """A tap swaps C and Python and starts again. Else the bodies the plugin stepped in FixedUpdate are read.
        --- MVP (P633) ---"""
        if pressed:
            self.c = plugins.engine is not None and not self.c
            self.restart()
            return
        plugin = self.physics_plugin
        step = plugin.take_step_us()
        t = time.ticks_us()
        plugin.read(self.drop)
        self.us[0] += step
        self.us[1] += time.ticks_diff(time.ticks_us(), t)
        self.hud_step += step

    def paint(self, cv):
        t = time.ticks_us()
        self.physics_plugin.draw(cv, SIZE, self.COLOURS)
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
                self.physics_plugin.name, N, self.frames * 1000 // elapsed, us[0] / n, us[1] / n, us[2] / n))
            self.us, self.frames, self.mark = [0, 0, 0], 0, now

    def hud(self, cv):
        """One short line and the step bar, drawn again only when either changes (P599)."""
        cv.keep((self.name, self.label, self.bar), LABEL_RECT, self.draw_hud)

    def draw_hud(self, cv):
        cv.fill(0, 0, W, LABEL_RECT[3], DARK)
        cv.text(self.label, 4, 2, WHITE)
        cv.fill(0, 11, self.bar, 3, YELLOW)
