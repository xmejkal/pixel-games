"""
The fire (P595): the first native effect. A heat field in C (engine/core/fx_fire.c, through engine.HeatField) rises
and cools, drawn as 2 x 2 px cells over the whole screen. Its look (part 2): hot spots that wander at the base, a
cooling map that rises with the flames and cuts them into tongues, and a sideways sway. Part 3 adds patches that rise
two rows a step, gusts of wind and embers. The fire assumes ORIENTATION 0
(lcd.py), as the pictures do. A BOOT tap moves to the next mode:
    linear   C writes the s3lcd frame itself, each cell smoothed over its 2 x 2 px by bilinear filtering (P608)
    picture  C blends the linear fire over the painted sky in the s3lcd frame, each pixel at its heat's alpha (P603)
    nearest  C writes the frame with each cell as one 2 x 2 px block, the draw before P608 (path B)
Path A, a buffer blitted opaque, was timed and dropped: 15.0 ms of step + draw against B's 7.8 (bench.md,
P595, D7).
The HUD says the mode, the step + draw ms and the fps.

Every REPORT_MS it prints, for the bench log, the average ms per frame:
    fire <mode> fps <fps> step <ms> draw <ms>
A tap prints `fire mode <mode>` and starts a new interval, so each line holds one mode. Before the field opens it prints
`fire internal largest <bytes>` (A9), then `fire field <internal|psram>`. Without the engine module the HUD says
"fire: no C" and nothing else is drawn.

FirePlugin (P633) holds the field, its gusts and its step clock as an engine layer a scene lists in Game.plugins: the
fire scene lists it alone, the burning scene after its PhysicsPlugin. The scene only picks the mode and draws.

FireLayer (P602) puts the same field into another game as one more layer of its picture: heat burned at a body, moved
with the world and blended over the game's frame. It was tried as a fire trail behind flappy's bird, and the PO kept
it for other games (2026-11-04). The Runner uses it (P651).
--- MVP (P595) ---
"""

import random
import time
from array import array

import pictures
from gfx import BLACK, DARK, HEIGHT, LABEL_RECT, WHITE, WIDTH, Game, c565
from motion import StepClock
from plugins import Plugin

try:
    import engine
except ImportError:  # the image with s3lcd only
    engine = None
# --- MVP (P602) --- the import above succeeds on the Mac too: it finds the repository's engine/ folder, an empty
# package. Only the C engine has HeatField
if not hasattr(engine, "HeatField"):
    engine = None

W, H = WIDTH // 2, HEIGHT // 2  # cells of 2 x 2 px: 160 x 120
RATE = 25  # kernel steps a second, one per 40 ms. Game.step caps dt at 60 ms, so a frame takes at most 2
STEP_MS = 1000 // RATE
STEP_CAP = 2  # steps a frame at most: Game.step caps a frame at 60 ms, which holds one or two
# The look's feel numbers, set by the lead from frames on the Mac (fx_fire_set_look)
DECAY = 33  # 32 keeps the heat, 33 adds a little each row, never past the hottest cell read, and the map brakes it
COOL = 24  # 0 to 255: how much the rising cooling map takes, so the flames break into tongues; 64 keeps them low
SWAY = 1  # 1: each cell reads the cells below it shifted by -1, 0 or +1 at random, the sideways flicker
SPOTS = 12  # 0 to 16 hot spots at the base, each walking and now and then jumping. 0 is part 1's random bottom row
SPREAD = 16  # 1 to 64: a spot's half-width in cells
FAST = 128  # 0 to 255: how much of the field rises two rows a step, in patches from the cooling map. 0 is none
EMBERS = 40  # 0 to 255: an ember starts in EMBERS of 256 kernel steps and rises faster than any flame
FADE = 4  # 0 to 255: a loss every cell pays, FADE sixteenths of a unit a row, so no parcel keeps its heat to the top.
# 4 keeps the stability test's seven seeds under its line of 48 (fade 2 reached 47.1 on seed 4)
WIND = 60  # 0 to 255: the strongest gust, a row shifts one column with the wind in WIND of 256 steps
GUST_MS = 1500  # a new gust, -WIND to WIND, every GUST_MS to 2 * GUST_MS; the wind eases an eighth of the way a frame
SEED = 595
# The palette's stops as (heat, r, g, b): black, dark red, red, orange, yellow, white. Heat 0 is exactly black, and its
# alpha is 0, so the picture mode leaves the sky there.
STOPS = ((0, 0, 0, 0), (48, 140, 10, 0), (96, 240, 60, 0), (144, 255, 160, 20), (192, 255, 230, 80), (255, 255, 255, 255))
# --- MVP (P608) ---
# The filters of HeatField.set_filter, OpenGL's GL_NEAREST and GL_LINEAR. 0 and 1 without the C engine
NEAREST, LINEAR = getattr(engine, "NEAREST", 0), getattr(engine, "LINEAR", 1)
# Each mode as (name, filter, blend): blend True paints the sky and blends the fire over it. A name is one word, as the
# report line has one token for it
MODES = (("linear", LINEAR, False), ("picture", LINEAR, True), ("nearest", NEAREST, False))
REPORT_MS = 5000  # app.py's FPS_EVERY_MS, so a fire line comes with each of its time lines
HUD_MS = 500
# --- Later, not MVP: kept for other games, the PO 2026-11-04 (P602) ---
CELL_PX_MS = 2000  # px/s times ms of one cell of 2 px, so FireLayer counts the world's motion in ints


def ramp(stops):
    """256 colours, linear between the stops, through gfx.c565."""
    out = array("H", [0] * 256)
    for (h0, r0, g0, b0), (h1, r1, g1, b1) in zip(stops, stops[1:]):
        for i in range(h0, h1 + 1):
            t = (i - h0) / (h1 - h0)
            out[i] = c565(int(r0 + (r1 - r0) * t), int(g0 + (g1 - g0) * t), int(b0 + (b1 - b0) * t))
    return out


PALETTE = ramp(STOPS)
# --- MVP (P603) ---
# The picture mode's alpha per heat: clear at heat 0, climbing evenly to full at ALPHA_FULL and full above it, so the
# fire is solid and only its cooler cells fade into the sky. The PO picked "full from heat 96 (red)" on the panel
# (2026-11-04). From 48, the dark red edges turn opaque and darken the sky again.
ALPHA_FULL = 96
ALPHA = array("B", [min(255, heat * 255 // ALPHA_FULL) for heat in range(256)])
# --- MVP (P639) --- The palette of every blended draw: below ALPHA_FULL each heat takes ALPHA_FULL's red, and only
# ALPHA fades it. With PALETTE the cool edges are dark red to black, so half of a dark colour went into a bright sky and
# the flames had dark borders (the PO saw them on the panel, 2026-11-06). Texture tools fix the same dark halo by edge
# dilation (also called alpha bleeding): a see-through pixel takes its colour from its opaque neighbour.
BLEND_PALETTE = array("H", [PALETTE[max(heat, ALPHA_FULL)] for heat in range(256)])


class FirePlugin(Plugin):
    """The heat field as an engine layer (P633): its look, its filter, the gusts of wind and its own StepClock.
    late_update takes the frame's burns, as the game made them in Update, then blows and steps; draw puts the field into
    the s3lcd frame, opaque or blended over what the frame holds. Without the engine, field is None and it draws
    nothing. --- MVP (P633) ---"""

    # --- MVP (P747) --- a Crackle of crackle.py, or None for no sound. A class attribute, so the field of each new
    # game adds its embers to it: one pop per birth, the pops with the sparks on screen
    crackle = None

    def __init__(self, look, seed):
        self.field, self.blend = None, False
        if engine is not None:
            self.field = engine.HeatField(W, H, seed)
            self.field.set_look(*look)
        self.wind, self.target, self.gust = 0, 0, 0  # the gust model: the wind now, where it goes, ms to the next
        self.clock = StepClock(STEP_MS, STEP_CAP)  # whole 40 ms steps; the rest waits

    def set_filter(self, mag_filter):
        if self.field is not None:
            self.field.set_filter(mag_filter)

    def late_update(self, ms):
        self.gust -= ms
        if self.gust <= 0:
            self.target = random.randrange(-WIND, WIND + 1)
            self.gust = GUST_MS + random.randrange(GUST_MS)
        d = self.target - self.wind
        self.wind += d // 8 if d < 0 else (d + 7) // 8  # rounded away from 0, so a gust reaches its target both ways
        steps = self.clock.take(ms)
        if self.field is not None and steps:
            t = time.ticks_us()
            self.field.step(steps, self.wind)
            self.step_us += time.ticks_diff(time.ticks_us(), t)
            if self.crackle is not None:  # P747
                self.crackle.add_pops(self.field.take_births())

    def draw(self, cv):
        """The field into the frame: blended at its heat's alpha over what the frame holds, or opaque."""
        if self.field is None:
            return
        if self.blend:
            self.draw_over(cv, ALPHA)
        else:
            self.field.draw(cv.tft, PALETTE)

    def draw_over(self, cv, alpha):
        """The field blended over what the frame holds, at alpha's byte for each heat. Only with a field: its callers
        check. --- MVP (P639) ---"""
        self.field.draw(cv.tft, BLEND_PALETTE, alpha)


class Fire(Game):
    name = "fire"
    TITLE_MS = 0  # straight into the fire, so the first BOOT tap moves to the next mode
    LOOK = (DECAY, COOL, SWAY, SPOTS, SPREAD, FAST, EMBERS, FADE)  # a scene on the same field sets its own (P596)
    MODES = MODES

    def __init__(self):
        self.mode = 0
        self.covers = engine is not None  # every mode paints every pixel: the fire opaque, or the sky under it
        super().__init__()

    def setup(self):
        pictures.load()
        if engine is not None:
            print(self.name, "internal largest", engine.largest_free_internal())
        self.fire_plugin = FirePlugin(self.LOOK, SEED)
        if self.fire_plugin.field is not None:
            print(self.name, "field", self.fire_plugin.field.where)
        self.plugins = (self.fire_plugin,)  # --- MVP (P633) ---
        self.set_mode(self.mode)
        self.begin()

    def set_mode(self, mode):
        """Mode number mode: its name, whether it blends, and its filter on the field. --- MVP (P608) ---"""
        self.mode = mode
        self.mode_name, mag_filter, self.fire_plugin.blend = self.MODES[mode]
        self.fire_plugin.set_filter(mag_filter)

    def begin(self):
        """A new interval for the report and the HUD."""
        self.us, self.frames, self.mark = [0, 0], 0, self.last  # us: step, draw
        self.hud_us, self.hud_frames, self.hud_mark = 0, 0, self.last  # self.last: None before the first step
        self.label = self.name + (": no C" if self.fire_plugin.field is None else " " + self.mode_name)

    def play(self, pressed, held):
        """A tap moves to the next mode. The field steps in the plugin's LateUpdate. --- MVP (P633) ---"""
        if pressed:
            self.set_mode((self.mode + 1) % len(self.MODES))
            print(self.name, "mode", self.mode_name)
            self.begin()

    def add(self, i, t):
        """The time since t into the report's sum i and the HUD's: add_us, timed here."""
        self.add_us(i, time.ticks_diff(time.ticks_us(), t))

    def add_us(self, i, us):
        """us µs into the report's sum i and the HUD's."""
        self.us[i] += us
        self.hud_us += us

    def paint_static(self, cv):
        """The sky under the picture mode, or black where there is no art, so covers stays true."""
        if self.fire_plugin.field is not None and self.fire_plugin.blend and not pictures.draw(cv, "sky", 0, 0):
            cv.fill(0, 0, WIDTH, HEIGHT, BLACK)

    def paint(self, cv):
        plugin = self.fire_plugin
        if plugin.field is None:
            return
        self.add_us(0, plugin.take_step_us())  # this frame's step: LateUpdate ran before the render. --- MVP (P633) ---
        t = time.ticks_us()
        self.draw_layers(cv)
        self.add(1, t)
        self.count(self.last)

    def draw_layers(self, cv):
        """What the report's draw times: here the field alone. A scene on the field draws its own layers around it.
        --- MVP (P639) ---"""
        self.fire_plugin.draw(cv)

    def count(self, now):
        """One more frame at now, the frame's start in ms: the HUD's text twice a second, the report every REPORT_MS."""
        if self.mark is None:
            self.mark = self.hud_mark = now
        self.frames += 1
        self.hud_frames += 1
        mode = self.mode_name
        elapsed = time.ticks_diff(now, self.hud_mark)
        if elapsed >= HUD_MS:
            self.label = "%s %s %.1f ms %d fps" % (
                self.name, mode, self.hud_us / self.hud_frames / 1000, self.hud_frames * 1000 // elapsed)
            self.hud_us, self.hud_frames, self.hud_mark = 0, 0, now
        elapsed = time.ticks_diff(now, self.mark)
        if elapsed >= REPORT_MS:
            us, n = self.us, 1000 * self.frames
            print("%s %s fps %d step %.2f draw %.2f" % (self.name, mode, self.frames * 1000 // elapsed, us[0] / n, us[1] / n))
            self.us, self.frames, self.mark = [0, 0], 0, now

    def hud(self, cv):
        """One short line, drawn again only when it changes (P599)."""
        cv.keep((self.name, self.label), LABEL_RECT, self.draw_hud)

    def draw_hud(self, cv):
        cv.fill(0, 0, WIDTH, LABEL_RECT[3], DARK)
        cv.text(self.label, 4, 2, WHITE)


# --- Later, not MVP: kept for other games, the PO 2026-11-04 (P602) ---
class FireLayer:
    """The fire field as one more layer of a game's picture, at the world's speed, as a parallax layer is (Godot's
    CanvasLayer): only burns put heat in, the base is off. update moves the heat with the world and steps it, draw
    blends it over the frame. Without the engine, field is None and draw does nothing. Made once: update and draw use
    int math only, so they make nothing a frame."""

    def __init__(self, look, seed, step_ms=STEP_MS, alpha=ALPHA, palette=BLEND_PALETTE):
        self.field, self.clock, self.acc = None, StepClock(step_ms, STEP_CAP), 0  # acc: px/s times ms; step_ms: the heat's step
        if engine is not None:
            self.field = engine.HeatField(W, H, seed)
            self.field.set_look(*look)
            self.field.set_base(False)
            self.field.set_filter(LINEAR)
        self.alpha, self.palette = alpha, palette  # the blend's alpha and colour by heat

    def update(self, ms, speed):
        """ms of a world moving left at speed px/s, an int: the field scrolls the whole cells it moved, the rest waits,
        then it steps by its clock. Its dx, the cells the field scrolled: negative, to the left, as Effect.scroll takes
        it."""
        self.acc += speed * ms
        cells = self.acc // CELL_PX_MS
        self.acc -= cells * CELL_PX_MS
        steps = self.clock.take(ms)
        if self.field is not None:
            if cells:
                self.field.scroll(-cells)
            if steps:
                self.field.step(steps, 0)
        return -cells

    def clear(self):
        """An empty field, and no part of a cell or a step carried over, for a new round. A scroll by the whole width
        empties the field (fx_fire_scroll)."""
        self.acc = self.clock.ms = 0
        if self.field is not None:
            self.field.scroll(-W)

    def draw(self, cv):
        """The heat blended over what the frame holds, at its alpha. Only a canvas with an s3lcd tft has a frame."""
        if self.field is not None and hasattr(cv, "tft"):
            self.field.draw(cv.tft, self.palette, self.alpha)
