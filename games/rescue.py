"""
Rescue (P800), the first slice: a fireman on a street at night, and a crater that burns.

How to play: the fireman runs along the street and never stops on his own. Tap BOOT and he turns round. Hold it and
he stops and sprays the hose ahead of him: a fire within REACH_PX goes down and is out after about a second of water.
A fire left alone burns out after FIRE_MS, and a new one starts elsewhere. The people, the meteors and the score come
with the next slice.

His cycles are motion capture (art/mocap.py, art/sets/rescue.py): the run, the spray and the turn, each painted facing
right and facing left. The run's pose follows the distance he ran, so his feet do not slide. The fire is the heat
field (fire.FireLayer), burned at the crater above the street lane and stepped every FIRE_STEP_MS, as the Runner's.
--- MVP (P800) ---
"""

import random

import pictures
from fire import ALPHA, PALETTE, FireLayer
from gfx import DARK, ORANGE, WHITE, WIDTH, YELLOW, Game, Particles, c565

# --- MVP (P800) --- the rules, in px, ms and ints
TAP_MS = 180  # a press released before this is a tap, and turns him; held this long, he sprays
FLASH_MS = 120  # the nozzle flashes from here until the spray starts
SPEED_PX_S = 56  # his run: the motion capture's 3.6 m/s at 24.07 px a body height (art/mocap.py prints the stride)
STRIDE_PX = 41  # px he runs in one run cycle: the capture's stride, 1.698 body heights, at 24.07 px a body height
RUN_POSES, SPRAY_POSES, TURN_POSES = 12, 6, 4  # art/mocap.py's CYCLES
SPRAY_POSE_MS = 83  # the spray cycle's loop is 0.5 s of capture, over its six poses
TURN_MS = 160  # the turn's four poses, after a turn: he turns on the spot, and cannot spray
LEFT_X, RIGHT_X = 74, 304  # px: his hips, from the station's door to the street's end, where he turns by himself
REACH_PX = 40  # px ahead of his hips that the hose reaches
HEAT_MAX = 255
DOUSE_MS = 1000  # ms of water that put out a full fire
FIRE_MS = 6000  # a fire left alone burns this long
NEXT_MS = 1500  # ms from one fire's end to the next
FIRE_LEFT_X, FIRE_RIGHT_X = 110, 300  # px: where a crater may open
FIRE_GAP_PX = 60  # px at least between his hips and a new crater
TURNED, OUT, BURNT = 1, 2, 4  # what Rules.step answers, as bits: a tap turned him, the hose put a fire out, it burnt out


class Fireman:
    """Where he is, the way he faces (1 right, -1 left), the press he is in, and the px he ran (the run's pose)."""

    def __init__(self, x):
        self.x, self.facing, self.rest = x, 1, 0  # rest: px times ms short of the next whole px
        self.down_ms = -1  # ms the button has been held, the first frame's ms included; -1 when it is up
        self.ran, self.turned_ms, self.spray_ms = 0, TURN_MS, 0

    def spraying(self):
        """Held TAP_MS or longer, and not in a turn."""
        return self.down_ms >= TAP_MS and not self.turning()

    def turning(self):
        return self.turned_ms < TURN_MS

    def flashing(self):
        return FLASH_MS <= self.down_ms < TAP_MS

    def press(self, ms, held):
        """ms of a frame with the button held or not. A press released before TAP_MS turns him, at the release.
        Answers whether he turned."""
        self.turned_ms += ms
        if held:
            self.down_ms = ms if self.down_ms < 0 else self.down_ms + ms  # it went down during this frame
            return False
        tap = 0 <= self.down_ms < TAP_MS
        self.down_ms = -1
        if tap:
            self.turn()
        return tap

    def turn(self):
        """He turns on the spot. The turn's poses are the run's at phases 0, 3, 6 and 9 of 12, so the run goes on
        after it from phase 0: ran moves on to the next whole stride."""
        self.facing, self.turned_ms = -self.facing, 0
        self.ran += -self.ran % STRIDE_PX

    def run(self, ms):
        """ms of running the way he faces; at an end of the street he turns by himself. Spraying or turning, he
        stands."""
        if self.spraying():
            self.spray_ms += ms
            return
        if self.turning():
            return
        self.rest += self.facing * SPEED_PX_S * ms
        px = self.rest // 1000
        self.rest -= px * 1000
        self.x += px
        self.ran += abs(px)
        if self.x <= LEFT_X or self.x >= RIGHT_X:
            self.x = LEFT_X if self.x <= LEFT_X else RIGHT_X
            self.rest = 0
            if (self.x == LEFT_X) == (self.facing < 0):
                self.turn()

    def run_pose(self):
        return self.ran * RUN_POSES // STRIDE_PX % RUN_POSES

    def ahead(self, x):
        """px from his hips to x, the way he faces: negative when x is behind him."""
        return (x - self.x) * self.facing


class Crater:
    """A crater and its fire: x, the ms of water it took, the ms it burns on."""

    def __init__(self, x):
        self.x, self.wet_ms, self.left_ms = x, 0, FIRE_MS

    def burning(self):
        return self.wet_ms < DOUSE_MS and self.left_ms > 0

    def heat(self):
        """0 to HEAT_MAX: down with the water, 0 once it is out."""
        return HEAT_MAX * (DOUSE_MS - self.wet_ms) // DOUSE_MS if self.burning() else 0


class Rules:
    """The rules, with no display: the fireman, one crater, and the wait for the next. place(x) answers the x of a new
    crater with his hips at x (the game's random choice, a test's own). Ints only."""

    def __init__(self, place, x=(LEFT_X + RIGHT_X) // 2):
        self.place = place
        self.man = Fireman(x)
        self.crater = Crater(place(x))
        self.wait_ms = 0  # ms to the next fire, once this one is over

    def step(self, ms, held):
        """One frame of ms with the button held or not. Answers TURNED, OUT and BURNT as bits."""
        man, crater, events = self.man, self.crater, 0
        if man.press(ms, held):
            events |= TURNED
        man.run(ms)
        if crater.burning():
            crater.left_ms -= ms
            if man.spraying() and 0 <= man.ahead(crater.x) <= REACH_PX:
                crater.wet_ms += ms
            if not crater.burning():
                events |= OUT if crater.wet_ms >= DOUSE_MS else BURNT
                self.wait_ms = NEXT_MS
        else:
            self.wait_ms -= ms
            if self.wait_ms <= 0:
                self.crater = Crater(self.place(man.x))
        return events


# --- MVP (P800) --- the game
FEET = 214  # px: the row his soles stand on (art/sets/rescue.py's FEET)
LANE = 180  # px: the street lane's top; the fire burns above it (art/sets/rescue.py's LANE)
SIZES = {"run": 26, "turn": 26, "spray": 40}  # each cycle's picture width; the hips at its middle (art/sets/rescue.py)
PICTURE_H = 30  # the pictures' height (art/sets/rescue.py's SIZES)
# px from his hips and soles to the nozzle's tip, facing right: the spray poses hold it 11 to 13 px ahead and 24 up
# (tests/test_rescue_art.py pins it)
NOZZLE_DX, NOZZLE_DY = 12, -24
FIRE_STEP_MS = 80  # ms a heat step, as the Runner's: 40 sank the Runner to 16 fps (bench.md P651)
# fx_fire_set_look's decay, cool, sway, spots, spread, fast, embers, fade: one flame out of the crater that tapers into
# tongues, set by eye on Mac frames of tools/render_scene.py against eight looks (fast patches and more cooling split
# it into blobs with a gap, less fade makes a white column)
FIRE_LOOK = (34, 30, 1, 0, 1, 0, 0, 16)  # no fast patches (they split the flame), no field embers (they rose low)
FIRE_SEED = 800
DECAY_DROP = 3  # the decay falls this much as a fire goes out: from 34, which keeps the flame climbing, to 31
BURN_HALF_PX = 12  # px each side of the crater's middle that burn
BURNS = 8  # hot spots burned a frame by a full fire
BURN_HEAT, FOOT_HEAT = 223, 160  # a spot's heat in a full fire, and in a fire nearly out: still bright, never see-through
WATER = (c565(170, 214, 255), c565(230, 244, 255))
STEAM = c565(200, 200, 210)
GLOW_LEVELS = 8  # the fire's light on the kerb and the street, from none to the full fire


def glow(base, warm):
    """GLOW_LEVELS colours from base (unlit) toward warm (lit by a full fire)."""
    n = GLOW_LEVELS - 1
    return tuple(c565(*[b + (w - b) * k // n for b, w in zip(base, warm)]) for k in range(GLOW_LEVELS))


KERB_GLOW = glow((84, 76, 86), (240, 116, 48))  # art/sets/rescue.py's kerb, lit
STREET_GLOW = glow((38, 34, 42), (210, 96, 40))  # the tarmac, a wet shine
SPARK = c565(255, 190, 80)


POSES = {(cycle, side): tuple("rescue_%s_%s%d" % (cycle, side, i) for i in range(n))
         for cycle, n in (("run", RUN_POSES), ("spray", SPRAY_POSES), ("turn", TURN_POSES)) for side in "rl"}


class Spray(Particles):
    """The hose's water: the game's own pool, so the shared fx pool keeps its room for the steam."""

    MAX = 60

    def draw(self, cv):
        for q in self.p:  # a drop: 2 x 1 px, then 1 px as it thins out
            cv.fill(q[0], q[1], 2 if q[4] > 0.12 else 1, 1, q[5])


class Rescue(Game):
    name = "rescue"
    hint = "tap turns, hold sprays"
    bg = c565(14, 12, 26)
    accent = ORANGE

    def __init__(self):
        self.layer = FireLayer(FIRE_LOOK, FIRE_SEED, FIRE_STEP_MS, ALPHA, PALETTE)  # made once, as the Runner's
        super().__init__()

    def setup(self):
        self.layer.clear()
        self.decay = FIRE_LOOK[0]  # the look's decay now, set again only when it steps (DECAY_DROP times a fire)
        self.rules = Rules(self.place)
        self.water = Spray()
        self.covers = pictures.load()  # the painted street covers the screen, so no fill goes under it

    @staticmethod
    def place(man_x):
        """A crater's x on the street, FIRE_GAP_PX at least from the fireman's hips at man_x."""
        x = random.randrange(FIRE_LEFT_X, FIRE_RIGHT_X - FIRE_GAP_PX * 2)
        return x if x < man_x - FIRE_GAP_PX else x + FIRE_GAP_PX * 2

    def play(self, pressed, held):
        rules = self.rules
        events = rules.step(self.ms, held)
        man, crater = rules.man, rules.crater
        self.layer.update(self.ms, 0)
        field = self.layer.field
        heat = crater.heat()
        if field is not None:  # the flame climbs less high as the fire dies down: its decay falls toward 31
            decay = FIRE_LOOK[0] - DECAY_DROP + DECAY_DROP * heat // HEAT_MAX
            if decay != self.decay:
                self.decay = decay
                field.set_look(decay, *FIRE_LOOK[1:])
        if field is not None and heat:
            # hot spots at random along the crater, on its two rows: a wide, ragged base. As the fire dies down it
            # narrows and has fewer spots, but its foot stays hot, so the flame never lifts off the crater
            half = 3 + (BURN_HALF_PX - 3) * heat // HEAT_MAX
            for _ in range(1 + (BURNS - 1) * heat // HEAT_MAX):
                x = (crater.x + random.randrange(-half, half + 1)) // 2
                y = LANE // 2 - 2 - random.randrange(2)
                field.burn(x, y, x, y, 1, FOOT_HEAT + (BURN_HEAT - FOOT_HEAT) * heat // HEAT_MAX - random.randrange(30))
        if heat and random.randrange(HEAT_MAX) < heat // 4:  # sparks fly up from the fire, fewer as it dies down
            self.fx.add(crater.x + random.randrange(-8, 9), LANE - 6, random.randrange(-20, 21),
                        -random.randrange(40, 90), SPARK, 0.8, 20.0)
        if man.spraying():
            x, y = man.x + NOZZLE_DX * man.facing, FEET + NOZZLE_DY
            for _ in range(5):
                self.water.add(x, y, man.facing * random.randrange(100, 140), -random.randrange(50, 90),
                               WATER[random.randrange(2)], 0.34, 320.0)
            if crater.burning() and 0 <= man.ahead(crater.x) <= REACH_PX and random.randrange(3) == 0:
                self.fx.add(crater.x + random.randrange(-8, 9), LANE - 4, random.randrange(-12, 13),
                            -random.randrange(20, 50), STEAM, 0.7, -30.0)
        if events & OUT:
            self.fx.burst(crater.x, LANE - 6, STEAM, 14, 50.0, 0.9, -60.0)
        if events & (OUT | BURNT):  # the field's heat would rise on alone as a flame with no crater under it
            self.layer.clear()
        self.water.update(self.dt)

    def man_picture(self):
        """The painted picture for now and its cycle: the turn just after a turn, the spray while he sprays, else
        the run's pose for the px he ran. The names are made once, in POSES."""
        man = self.rules.man
        side = "r" if man.facing > 0 else "l"
        if man.turned_ms < TURN_MS:  # the turn's poses go from the old facing to the new one
            return POSES["turn", "l" if man.facing > 0 else "r"][man.turned_ms * TURN_POSES // TURN_MS], "turn"
        if man.spraying():
            return POSES["spray", side][man.spray_ms // SPRAY_POSE_MS % SPRAY_POSES], "spray"
        return POSES["run", side][man.run_pose()], "run"

    def paint_static(self, cv):
        if pictures.draw(cv, "rescue_night", 0, 0):
            return
        cv.gradient(16, LANE, (10, 10, 26), (110, 34, 30), 12)
        cv.fill(0, 96, 80, LANE - 96, c565(84, 40, 36))  # the station
        cv.fill(16, 132, 42, LANE - 132, c565(255, 226, 160))  # its lit door
        cv.fill(0, LANE, WIDTH, 60, c565(38, 34, 42))

    def light(self, cv, x, heat):
        """The fire's light round the crater: the kerb lit warm, and two lines of shine on the tarmac below, each
        as bright as the fire is hot. Opaque fills: the canvas has no blend."""
        k = heat * (GLOW_LEVELS - 1) // HEAT_MAX
        if k:
            for half, level in ((40, k // 3), (30, k * 2 // 3), (20, k)):  # brighter toward the crater
                cv.fill(x - half, LANE, 2 * half, 3, KERB_GLOW[level])
            for y, half in ((LANE + 4, 22), (LANE + 6, 16), (LANE + 9, 10)):  # the shine fades down the street
                cv.fill(x - half, y, 2 * half, 1, STREET_GLOW[k * half // 22])

    def paint(self, cv):
        rules = self.rules
        man, crater = rules.man, rules.crater
        self.light(cv, crater.x, crater.heat())
        if crater.burning() and self.layer.field is None:  # the flat fire, without the heat field
            h = crater.heat() // 8
            cv.fill(crater.x - 6, LANE - h, 12, h, ORANGE)
            cv.fill(crater.x - 3, LANE - h // 2, 6, h // 2, YELLOW)
        self.layer.draw(cv)
        if not pictures.draw(cv, "rescue_crater", crater.x - 14, LANE - 1):  # over the flame's foot: it comes out
            cv.fill(crater.x - 13, LANE, 26, 6, DARK)
            cv.fill(crater.x - 11, LANE, 22, 1, c565(232, 70, 40))
        name, cycle = self.man_picture()
        w = SIZES[cycle]
        if not pictures.draw(cv, name, man.x - w // 2, FEET - PICTURE_H + 1):
            cv.fill(man.x - 2, FEET - 20, 5, 12, DARK)
            cv.fill(man.x - 3, FEET - 24, 7, 4, YELLOW)
            step = man.run_pose() // 3 % 2 * 3 - 1
            cv.fill(man.x - 2 + step, FEET - 8, 2, 8, DARK)
            cv.fill(man.x + 1 - step, FEET - 8, 2, 8, DARK)
        if man.flashing():
            x, y = man.x + 7 * man.facing, FEET - 16
            cv.fill(x - 1, y - 1, 3, 3, WATER[0])
            cv.fill(x, y, 1, 1, WHITE)
        self.water.draw(cv)
