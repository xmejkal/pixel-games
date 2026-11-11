"""
Marshmallow (P773): roast a marshmallow over a campfire. It hangs on a stick above the fire.

How to play: hold BOOT to lower it into the flames and let go to lift it. The heat browns it from white to golden
and then to black. Lift a golden one to the top of the screen and you score a point. A black one is lost. Three
lost ones end the round. Each point makes the campfire higher and less steady.

The campfire is the heat field of fire.py. The game burns it itself at the bottom middle, and the field's own base is
off, as in burning.py. Without the C engine a plain flame of bars takes its place, and the rules are the same.
--- MVP (P773) ---
"""

from cues import LEVELS, Cue
from fire import FAST, MODES, SWAY, Fire, H, W
from gfx import BEST, GREY, HEIGHT, HUD_RECT, ORANGE, RED, WIDTH, YELLOW, Game, c565

# --- MVP (P773) --- the rules, in px, ms and ints. Mac trials of the burn, over fire.py's field with the look below.
SERVE, BURN = 1, 2  # what Roast.update answers, besides None
WHITE, GOLDEN, BLACK = 0, 1, 2  # what Roast.colour answers
LIVES = 3  # lost marshmallows that end a round
FLAME_MAX_PX = 200  # px: no flame is read higher, so the marshmallow at the top is safe (Mac trial: 222 px at most)
BOTTOM_Y = HEIGHT - FLAME_MAX_PX  # px: the marshmallow's bottom edge at the top, y 40: level with the highest flame
SIZE = 16  # px, a marshmallow's side
DEPTH_MAX = 180  # px it goes down: its bottom edge is then at y 220
LOWER_PX_S = 120  # px a second while BOOT is held: the whole way takes 1.5 s
LIFT_PX_S = 200  # px a second while it is not. test_marshmallow proves from the constants that it is fast enough
GOLDEN_AT, BLACK_AT = 100000, 300000  # browned, in px times ms: the cooking so far. 40 px under the flame, golden takes
# 2.5 s and black 7.5 s. The campfire in play (Mac, 1,400 frames) reaches 76 to 180 px high at 0 points and 102 to 200
# at 5. At the lowest, 76 px, the deepest place is 56 px under it: golden in 1.8 s


class Roast:
    """The rules, with no display. depth: px down from the top. browned: the cooking, in px times ms. lost: the
    marshmallows that went black. Ints only, so a frame makes nothing."""

    def __init__(self):
        self.depth, self.rest, self.browned, self.lost = 0, 0, 0, 0  # rest: px times ms short of the next whole px

    def colour(self):
        return WHITE if self.browned < GOLDEN_AT else GOLDEN if self.browned < BLACK_AT else BLACK

    def update(self, ms, held, flame_px):
        """ms of play. held: BOOT is down. flame_px: the flame's height above the screen's bottom. Answers None, SERVE
        (a golden one reached the top) or BURN (a marshmallow just went black)."""
        self.rest += (LOWER_PX_S if held else -LIFT_PX_S) * ms
        px = self.rest // 1000
        self.rest -= px * 1000
        self.depth += px
        if self.depth < 0 or self.depth > DEPTH_MAX:
            self.depth = 0 if self.depth < 0 else DEPTH_MAX
            self.rest = 0
        under = BOTTOM_Y + self.depth - (HEIGHT - flame_px)  # px of the bottom edge below the flame's top
        if under > 0 and self.browned < BLACK_AT:
            self.browned += under * ms
            if self.browned >= BLACK_AT:
                self.lost += 1
                return BURN
        if self.depth == 0 and self.browned >= GOLDEN_AT:
            served = self.browned < BLACK_AT
            self.browned = 0  # a white one for the golden one served, and for a black one
            return SERVE if served else None
        return None


# --- MVP (P773) --- the flames. Mac trials of the burn at the bottom middle (24 cells wide, radius 4 cells) over the
# look below, 800 steps each: the field's height over THRESHOLD 96, in cells, was the same in the whole field and in the
# middle 24 columns (at most 6 cells apart in the other looks, 0 here). Heat 150 gave 82 px on average (50 to 118), heat
# 200 gave 126 px (90 to 162) and heat 250 gave 182 px (136 to 222), so the lowest campfire is a third of the screen and
# the highest three quarters.
# decay, cool, sway, spots, spread, fast, embers, fade: no spots and no embers, the base is off
LOOK = (33, 40, SWAY, 0, 1, FAST, 0, 8)
BURN_HALF, BURN_RADIUS = 12, 4  # cells: the burned line is 2 * BURN_HALF + 1 wide, centred, with discs of this radius
THRESHOLD = 96  # a cell counts as flame from this heat (the red of the palette)
HEAT_LOW, HEAT_HIGH = 150, 200  # the burn's heat swings between these, a triangle wave
WILD_MAX, HEAT_WILD = 5, 10  # a point raises the high heat by HEAT_WILD, up to WILD_MAX points: 250
WAVE_MS, WAVE_WILD_MS = 4000, 400  # the wave's period: each point makes it 400 ms shorter, 2 s at WILD_MAX
PLAIN_PX = 68  # the plain flame's height is the heat less this: the Mac trial's px at heat 150 and 250 are 82 and 182
BAR_HALF = (32, 20, 8)  # px, the plain flame's red, orange and yellow bars
BAR_COLOURS = (RED, ORANGE, YELLOW)
CENTRE = WIDTH // 2


class Flame:
    """What the game reads: top_px, the flame's height above the screen's bottom. update(ms, wild) runs once a frame in
    play, wild is 0 to WILD_MAX. A subclass draws it."""

    top_px = 0

    def __init__(self):
        self.pos = 0  # ms into the wave

    def reset(self):
        self.pos = 0

    def wave(self, ms, wild):
        """The heat now: a triangle wave from HEAT_LOW up to the high heat and back, ints only."""
        period = WAVE_MS - wild * WAVE_WILD_MS
        self.pos = (self.pos + ms) % period
        half = period // 2
        rise = self.pos if self.pos < half else period - self.pos
        return HEAT_LOW + (HEAT_HIGH + wild * HEAT_WILD - HEAT_LOW) * rise // half

    def update(self, ms, wild):
        pass

    def draw(self, cv):
        pass


class Campfire(Flame):
    """The flame burned into the field of a FirePlugin: each frame a line at the bottom middle, at the wave's heat. The
    field takes it in LateUpdate and steps. top_px is read from stats() after a frame in which the field stepped."""

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin

    def update(self, ms, wild):
        field = self.plugin.field
        y = H - 1 - BURN_RADIUS
        field.burn(W // 2 - BURN_HALF, y, W // 2 + BURN_HALF, y, BURN_RADIUS, self.wave(ms, wild))
        if self.plugin.take_step_us():  # the field stepped. stats() takes 0.4 to 0.5 ms (run147e) and makes one tuple
            self.top_px = min(FLAME_MAX_PX, 2 * field.stats(THRESHOLD)[1])  # cells are 2 px

    def draw(self, cv):
        self.plugin.draw(cv)


class PlainFlame(Flame):
    """The flame with no C engine: the same wave gives the height, and three bars are drawn."""

    def update(self, ms, wild):
        self.top_px = self.wave(ms, wild) - PLAIN_PX

    def draw(self, cv):
        top = HEIGHT - self.top_px
        for k in range(3):
            y = top + k * self.top_px // 3
            cv.fill(CENTRE - BAR_HALF[k], y, 2 * BAR_HALF[k], HEIGHT - y, BAR_COLOURS[k])


# --- MVP (P773) --- the sound, the picture and the game
FLAME_GAIN = 32768  # Q15: the fire loop at the highest flame, the runner's gain (arcade.FIRE_SOUND_GAIN)
FLAME_STEP = 16  # a new "flame" signal when the level moved by this much of LEVELS
STICK = c565(120, 80, 40)
SHADES = (c565(245, 240, 225), c565(222, 165, 55), c565(35, 28, 28))  # by WHITE, GOLDEN, BLACK


class Marshmallow(Fire):
    name = "marshmallow"
    hint = "hold to roast"
    TITLE_MS = Game.TITLE_MS
    LOOK = LOOK
    MODES = MODES[:1]  # the linear mode alone
    cues = {"serve": Cue("pickup"), "burn": Cue("land"), "die": Cue("die"), "flame": Cue("fire", FLAME_GAIN, True)}
    fire_plugin = flame = None  # made once in setup

    def __init__(self):
        super().__init__()
        self.covers = False  # the title needs its black fill

    def setup(self):
        """restart() calls this each round: the field keeps burning, so a round does not start cold."""
        if self.fire_plugin is None:
            super().setup()
            field = self.fire_plugin.field
            if field is None:
                self.flame = PlainFlame()
            else:
                field.set_base(False)
                self.flame = Campfire(self.fire_plugin)
        self.flame.reset()
        self.roast, self.level = Roast(), 0
        self.emit("flame", 0)

    def play(self, pressed, held):
        """Not Fire.play: a tap moves no mode."""
        flame, roast = self.flame, self.roast
        flame.update(self.ms, min(self.score, WILD_MAX))
        out = roast.update(self.ms, held, flame.top_px)
        level = flame.top_px * LEVELS // FLAME_MAX_PX
        if abs(level - self.level) >= FLAME_STEP:
            self.level = level
            self.emit("flame", level)
        if out == SERVE:
            self.score += 1
            self.emit("serve")
            self.pop(CENTRE, BOTTOM_Y)
        elif out == BURN:
            self.emit("burn")
            self.fx.burst(CENTRE, BOTTOM_Y + roast.depth, GREY, 10, 110.0, 0.6)
            if roast.lost >= LIVES:
                self.emit("flame", 0)  # play() does not run after a death, so the loop ends here
                self.die()

    def paint(self, cv):
        self.flame.draw(cv)
        y = BOTTOM_Y - SIZE + self.roast.depth
        cv.fill(CENTRE - 1, 0, 3, y + SIZE // 2, STICK)
        cv.fill(CENTRE - SIZE // 2, y, SIZE, SIZE, SHADES[self.roast.colour()])
        cv.box(CENTRE - SIZE // 2, y, SIZE, SIZE, GREY)

    def hud(self, cv):
        cv.keep((self.name, self.score, BEST.get(self.name, 0), self.roast.lost), HUD_RECT, self.draw_hud)

    def draw_hud(self, cv):
        """The score bar and a square for each life, red while it is left."""
        Game.draw_hud(self, cv)
        for i in range(LIVES):
            cv.fill(CENTRE + 56 + 12 * i, 4, 8, 8, RED if i < LIVES - self.roast.lost else GREY)
