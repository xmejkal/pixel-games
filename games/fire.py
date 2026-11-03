"""
The fire (P595): the first native effect. A heat field in C (engine/core/fx_fire.c, through engine.HeatField) rises
and cools, drawn as 2 x 2 px cells over the whole screen. A BOOT tap moves to the next mode:
    B        C writes the s3lcd frame itself
    A        C fills a buffer, and Python blits it
    picture  the A buffer at alpha 128 over the painted sky, its black skipped
The HUD says the mode, the step + draw ms and the fps.

Every REPORT_MS it prints, for the bench log, the average ms per frame:
    fire <mode> fps <fps> step <ms> draw <ms>
A tap prints `fire mode <mode>` and starts a new interval, so each line holds one mode. Before the field opens it prints
`fire internal largest <bytes>` (A9), then `fire field <internal|psram>`. Without the engine module the HUD says
"fire: no C" and nothing else is drawn.
--- MVP (P595) ---
"""

import time
from array import array

import pictures
from gfx import BLACK, DARK, HEIGHT, WHITE, WIDTH, Game, c565
from lcd import PANEL_H, PANEL_W

try:
    import engine
except ImportError:  # the Mac, or the image with s3lcd only
    engine = None

W, H = WIDTH // 2, HEIGHT // 2  # cells of 2 x 2 px: 160 x 120
RATE = 25  # kernel steps a second, one per 40 ms. Game.step caps dt at 60 ms, so a frame takes at most 2
STEP_MS = 1000 // RATE
DECAY = 31  # 32 keeps the heat up to the top. 31 lets the flames die out about halfway up (Lode's 32 / 129)
SEED = 595
# The palette's stops as (heat, r, g, b): black, dark red, red, orange, yellow, white. Heat 0 is exactly black, the key
# of the picture mode.
STOPS = ((0, 0, 0, 0), (48, 140, 10, 0), (96, 240, 60, 0), (144, 255, 160, 20), (192, 255, 230, 80), (255, 255, 255, 255))
B, A, PICTURE = 0, 1, 2
MODES = ("B", "A", "picture")
REPORT_MS = 5000  # app.py's FPS_EVERY_MS, so a fire line comes with each of its time lines
HUD_MS = 500


def ramp(stops):
    """256 colours, linear between the stops, through gfx.c565."""
    out = array("H", [0] * 256)
    for (h0, r0, g0, b0), (h1, r1, g1, b1) in zip(stops, stops[1:]):
        for i in range(h0, h1 + 1):
            t = (i - h0) / (h1 - h0)
            out[i] = c565(int(r0 + (r1 - r0) * t), int(g0 + (g1 - g0) * t), int(b0 + (b1 - b0) * t))
    return out


PALETTE = ramp(STOPS)


class Fire(Game):
    name = "fire"
    TITLE_MS = 0  # straight into the fire, so the first BOOT tap moves to the next mode

    def __init__(self):
        self.mode = B
        self.covers = engine is not None  # every mode paints every pixel: the fire in B and A, the sky in picture
        self.buf = bytearray(PANEL_W * PANEL_H * 2)  # path A's buffer, made once (gc heap, PSRAM)
        super().__init__()

    def setup(self):
        pictures.load()
        self.field = None
        if engine is not None:
            print("fire internal largest", engine.largest_free_internal())
            self.field = engine.HeatField(W, H, SEED)
            print("fire field", self.field.where)
        self.begin()

    def begin(self):
        """A new interval for the report and the HUD."""
        self.acc, self.us, self.frames, self.mark = 0, [0, 0], 0, self.last  # us: step, draw
        self.hud_us, self.hud_frames, self.hud_mark = 0, 0, self.last  # self.last: None before the first step
        self.label = "fire: no C" if self.field is None else "fire " + MODES[self.mode]

    def play(self, pressed, held):
        if pressed:
            self.mode = (self.mode + 1) % len(MODES)
            print("fire mode", MODES[self.mode])
            self.begin()
            return
        self.acc += int(self.dt * 1000 + 0.5)  # whole 40 ms steps; the rest waits for the next frame
        steps = self.acc // STEP_MS
        self.acc -= steps * STEP_MS
        if self.field is not None and steps:
            t = time.ticks_us()
            self.field.step(steps, DECAY)
            self.add(0, t)

    def add(self, i, t):
        """The time since t into the report's sum i and the HUD's."""
        us = time.ticks_diff(time.ticks_us(), t)
        self.us[i] += us
        self.hud_us += us

    def paint_static(self, cv):
        """The sky under the picture mode, or black where there is no art, so covers stays true."""
        if self.field is not None and self.mode == PICTURE and not pictures.draw(cv, "sky", 0, 0):
            cv.fill(0, 0, WIDTH, HEIGHT, BLACK)

    def paint(self, cv):
        if self.field is None:
            return
        t = time.ticks_us()
        if self.mode == B:
            self.field.draw(cv.tft, PALETTE)
        else:
            self.field.draw(self.buf, PALETTE)
            if self.mode == A:
                cv.tft.blit_buffer(self.buf, 0, 0, PANEL_W, PANEL_H)
            else:
                cv.tft.blit_buffer(self.buf, 0, 0, PANEL_W, PANEL_H, 128, 0)
        self.add(1, t)
        self.count(self.last)

    def count(self, now):
        """One more frame at now, the frame's start in ms: the HUD's text twice a second, the report every REPORT_MS."""
        if self.mark is None:
            self.mark = self.hud_mark = now
        self.frames += 1
        self.hud_frames += 1
        mode = MODES[self.mode]
        elapsed = time.ticks_diff(now, self.hud_mark)
        if elapsed >= HUD_MS:
            self.label = "fire %s %.1f ms %d fps" % (
                mode, self.hud_us / self.hud_frames / 1000, self.hud_frames * 1000 // elapsed)
            self.hud_us, self.hud_frames, self.hud_mark = 0, 0, now
        elapsed = time.ticks_diff(now, self.mark)
        if elapsed >= REPORT_MS:
            us, n = self.us, 1000 * self.frames
            print("fire %s fps %d step %.2f draw %.2f" % (mode, self.frames * 1000 // elapsed, us[0] / n, us[1] / n))
            self.us, self.frames, self.mark = [0, 0], 0, now

    def hud(self, cv):
        """One short line, drawn every frame: TftCanvas keeps nothing to reuse."""
        cv.fill(0, 0, WIDTH, 14, DARK)
        cv.text(self.label, 4, 2, WHITE)
