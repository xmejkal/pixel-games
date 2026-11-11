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
from fire import FirePlugin, Fire, H, MODES, W
from gfx import BEST, DARK, GREY, HEIGHT, HUD_RECT, ORANGE, RED, WIDTH, YELLOW, Game, c565
from volume import FULL

# --- MVP (P773) --- the rules, in px, ms and ints. Mac trials of the burn, over fire.py's field with the look below.
SERVE, BURN = 1, 2  # what Roast.update answers, besides None
WHITE, GOLDEN, BLACK = 0, 1, 2  # what Roast.colour answers
LIVES = 3  # lost marshmallows that end a round
FLAME_MAX_PX = 200  # px: no flame is read higher, so the marshmallow at the top is safe (Mac trial: 222 px at most)
BOTTOM_Y = HEIGHT - FLAME_MAX_PX  # px: the marshmallow's bottom edge at the top, y 40, level with the highest flame's top
SIZE = 16  # px, a marshmallow's side
DEPTH_MAX = 180  # px it goes down: its bottom edge is then at y 220
LOWER_PX_S = 120  # px a second while BOOT is held: the whole way takes 1.5 s
LIFT_PX_S = 200  # px a second while it is not. test_marshmallow proves from the constants that it is fast enough
GOLDEN_AT, BLACK_AT = 100000, 300000  # browned, in px times ms: the cooking so far. 40 px deep, golden takes 2.5 s
# and black 7.5 s. Under the lowest campfire (82 px, y 158) at the deepest place the edge is 62 px under: golden in 1.6 s


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
