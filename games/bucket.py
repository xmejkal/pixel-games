"""
Bucket (P773): catch the falling boxes. A bucket rides on a rail near the bottom of the screen.

How to play: hold BOOT and the bucket goes right, let go and it goes left. A box that falls into the bucket is a
point. A box you miss bounces and lands on the pile in its column. When a column of the pile reaches the rail, the
round ends. Each of the first 10 points makes the boxes come faster.

The boxes fall on the rain's physics (plugins.PhysicsPlugin: engine.Bodies, or its twin in Python). The bodies do not
touch each other, so the pile is a count of boxes per column in Python: a missed box falls and bounces on the real
physics, onto the top of the pile in its column.
--- MVP (P773) ---
"""

import math
import random
from array import array

import pictures
import plugins
from cues import Cue
from gfx import GREY, HEIGHT, OVER, PALETTE, PLAY, WIDTH, YELLOW, Dice, Game, Particles, c565
from plugins import PhysicsPlugin

# --- MVP (P773) --- the rules, in px, ms and ints. Mac trials through Game.step on the Python bodies (frames of 42 ms,
# 60 ms and random 20 to 90 ms, 8 seeds; the trial script is not in the repository): an idle player lost after 14 to
# 54 s, one who held always after 14 to 51 s, and 50 blind rhythms (hold periods 200 to 2000 ms, duty 20 to 80 %) after
# 61 s at the slowest. A bot that steers to the lowest box it can see lasted the whole 600 s at every frame pace.
# BUCKET_W 56 failed it at 60 ms and with jitter (39 s at the least), so it is 64: the bang-bang bot overshoots by a
# frame's travel (BUCKET_PX_S * 60 ms = 22 px), which the inside of the bucket (W - 2 * WALL_PX - SIZE, over 2) must
# hold. BUCKET_PX_S is 360 so that a trip from one wall to the other plus two 60 ms frames fits in the gap of two
# drops at DROP_MIN_MS (a test drops columns 0 and 31 in turn). Take care with DROP_MIN_MS: at SIZE 12 the bot broke
# down in a narrow band of it (1100 and 1150 ms: 27 to 82 s), as a box takes about 1.2 s to fall to the rail.
SIZE = 10  # px, a box's side
COLS = WIDTH // SIZE  # the columns a box drops at, and the pile's
PILE_ROWS = 3  # boxes a column holds before it reaches the rail
RAIL_Y = HEIGHT - SIZE * PILE_ROWS  # px: the line the bucket rides on, and the top of a full column
BUCKET_W = 64  # px
WALL_PX = 4  # px: the bucket's walls; it may go this far past each screen edge, so its inside reaches the end columns
LEFT_X, RIGHT_X = -WALL_PX, WIDTH - BUCKET_W + WALL_PX  # px: the bucket's left edge, least and most
BUCKET_PX_S = 360  # px a second, to the right while BOOT is held and to the left while it is not
N = 8  # boxes out at most
GRAVITY_PX = 300  # px/s squared, a box needs about 1.2 s to the rail (the rain's is 2000)
DROP_MS, DROP_STEP_MS, DROP_MIN_MS = 1500, 50, 1000  # a new box each DROP_MS, shorter by DROP_STEP_MS for each of the first (DROP_MS - DROP_MIN_MS) / DROP_STEP_MS = 10 points


class Rules:
    """The rules, with no display and no physics. pile: the boxes missed in each column. bucket_x: the bucket's left
    edge in px. score: the points. Ints only, so a frame makes nothing."""

    def __init__(self):
        self.pile = bytearray(COLS)
        self.bucket_x, self.rest = (WIDTH - BUCKET_W) // 2, 0  # rest: px times ms short of the next whole px
        self.score, self.clock = 0, 0  # clock: the ms since the last drop

    def drop_ms(self):
        """The ms between two drops."""
        return max(DROP_MIN_MS, DROP_MS - DROP_STEP_MS * self.score)

    def move(self, ms, held):
        """ms of play: the bucket goes right while held, else left, and stays on the screen."""
        self.rest += (BUCKET_PX_S if held else -BUCKET_PX_S) * ms
        px = self.rest // 1000
        self.rest -= px * 1000
        x = self.bucket_x + px
        if x < LEFT_X or x > RIGHT_X:
            x = LEFT_X if x < LEFT_X else RIGHT_X
            self.rest = 0
        self.bucket_x = x

    def due(self, ms, free):
        """ms of play. free: a body is free for a box. Answers True when a box drops. With no body free the clock holds
        at drop_ms(), so a body that frees gets one box, never a burst."""
        drop = self.drop_ms()
        self.clock += ms
        if self.clock >= drop and free:
            self.clock = min(self.clock - drop, drop)
            return True
        self.clock = min(self.clock, drop)
        return False

    def caught(self, x):
        """Whether a box at x, at the rail, is wholly between the bucket's walls."""
        return self.bucket_x + WALL_PX <= x and x + SIZE <= self.bucket_x + BUCKET_W - WALL_PX

    def catch(self):
        """A point; the score."""
        self.score += 1
        return self.score

    def miss(self, col):
        """A box lands on the pile in col; the pile's height there."""
        self.pile[col] += 1
        return self.pile[col]

    def full(self, col):
        """Whether the pile in col reaches the rail."""
        return self.pile[col] >= PILE_ROWS


# --- MVP (P773) --- the game
FREE, FALL, LAND = 0, 1, 2  # a box's phase: its body is free, the box falls to the rail, a missed one bounces and rests
WALL_H = 12  # px: the walls' height above the rail
FLOOR = 3  # px, the bucket's floor

# --- MVP (P773, story 4) --- the painted look: art/sets/bucket.py's sizes and places, which the board has no art/ to
# read (tests/test_bucket_art.py pins them), and the effects' numbers, set by eye on Mac frames of tools/render_scene.py
HUES = 4  # the crates' woods: a crate's hue is (its column + its place in the pile) % HUES
BUCKET_H, TIPPED_W, TIPPED_H = 13, 80, 44  # the bucket's picture (its rim 1 px over the walls), and tipped over
CHIMNEYS = ((31, 88), (69, 89), (99, 102))  # each chimney's top in the painted village, where its smoke rises
GLINTS = ((250, 154), (262, 156), (254, 159), (268, 153), (244, 160))  # the river's shimmer under the sun
GLINT_MS = 160  # each glint's frame lasts this long
SMOKE_MS = 420  # a puff from each chimney this often
COIN_MS, COIN_TO = 520, (10, 2)  # a caught crate's coin flies this long, to the score
SPARKLES, SPARKLE_MS, SPARKLE = 6, 420, 9  # the sparkles round a catch, each for a part of SPARKLE_MS; their size
GOLD = (c565(255, 226, 120), c565(255, 190, 70), c565(255, 250, 220))  # the bits of light thrown up at a catch
DUST = (c565(206, 184, 148), c565(176, 156, 126))
PUFF_SIZES = ((5, 4), (7, 5), (10, 7))  # a chimney's puff as it grows, drawn see-through
PUFF_ALPHAS = (170, 130, 80)
PILES = tuple(tuple("bucket_pile%d_%d" % (h, m) for m in range(HUES)) for h in range(PILE_ROWS + 1))
CRATES = tuple("bucket_crate%d" % m for m in range(HUES))
SHIMMER = tuple("bucket_shimmer%d" % i for i in range(3))
PUFFS = tuple("bucket_puff%d" % i for i in range(len(PUFF_SIZES)))


class Smoke(Particles):
    """The chimneys' smoke: puffs that rise slowly, drift with the breeze, grow and thin out as they go."""

    MAX = 18
    LIFE = 2.4  # seconds

    def draw(self, cv):
        for q in self.p:
            k = min(2, int((self.LIFE - q[4]) * 3 / self.LIFE))
            w, h = PUFF_SIZES[k]
            pictures.draw(cv, PUFFS[k], int(q[0]) - w // 2, int(q[1]) - h // 2, PUFF_ALPHAS[k])


class Bucket(Game):
    name = "bucket"
    hint = "hold: right"
    cues = {"catch": Cue("pickup"), "miss": Cue("land"), "die": Cue("die")}

    def __init__(self):
        self.c = plugins.engine is not None
        super().__init__()

    def setup(self):
        """No seed: two rounds drop different columns (the tests seed random)."""
        self.physics_plugin = PhysicsPlugin(N, self.c, gravity=GRAVITY_PX)
        self.plugins = (self.physics_plugin,)
        self.rules, self.on_rest = Rules(), self.rest
        self.shown = bytearray(COLS)  # the pile as drawn: a missed box joins it when it rests
        self.phase, self.last_y = bytearray(N), array("h", [-SIZE] * N)
        self.covers = self.art = pictures.load()  # the painted village covers the screen: no fill under it
        self.dice, self.smoke = Dice(774), Smoke()
        self.coins = []  # [x, y, the ms it was caught] of each coin on its way to the score
        self.puffed = 0  # the ms of the last chimney puff

    def play(self, pressed, held):
        rules, plugin, phase = self.rules, self.physics_plugin, self.phase
        rules.move(self.ms, held)
        plugin.read(self.on_rest)
        if self.state != PLAY:  # a body asleep in the air ended the round
            return
        for i in range(N):
            if phase[i] == FALL:
                x, y = plugin.place(i)
                if self.last_y[i] + SIZE < RAIL_Y <= y + SIZE:  # crossed the rail since the last frame
                    self.at_rail(i, x, y)
                    if self.state != PLAY:
                        return
                self.last_y[i] = y
        free = self.free_body()
        if rules.due(self.ms, free >= 0):
            self.drop(free)

    def free_body(self):
        """A body with no box, or -1."""
        for i in range(N):
            if self.phase[i] == FREE:
                return i
        return -1

    def drop(self, i):
        """A box at a random column, above the screen, with no plane on the way."""
        self.phase[i], self.last_y[i] = FALL, -SIZE
        self.physics_plugin.spawn(i, SIZE * random.randrange(COLS), -SIZE, 0, 0, HEIGHT)

    def at_rail(self, i, x, y):
        """Box i crosses the rail once: caught, or missed onto the pile in its column."""
        rules = self.rules
        if rules.caught(x):
            self.score = rules.catch()
            self.phase[i] = FREE
            self.physics_plugin.spawn(i, x, HEIGHT, 0, 0, HEIGHT)  # parked: it sleeps on the next step, off the screen
            self.emit("catch")
            if self.art:  # sparkles, bits of light and a coin that flies to the score (paint_effects)
                self.coins.append([x, RAIL_Y - SIZE, self.last])
                del self.coins[:-4]
                dice = self.dice
                for _ in range(8):
                    self.fx.add(x + dice.below(SIZE), RAIL_Y - 6, dice.spread(70), -60 - dice.below(90),
                                GOLD[dice.below(3)], 0.3 + dice.below(20) / 100, 260.0)
            else:
                self.pop(x + SIZE // 2, RAIL_Y)
            return
        col = x // SIZE
        rest_y = HEIGHT - SIZE * rules.miss(col)
        speed = int(math.sqrt(2 * GRAVITY_PX * (y + SIZE)))  # the bodies do not read their speed out: from the fall
        self.phase[i] = LAND
        self.physics_plugin.spawn(i, x, min(y, rest_y), 0, speed, rest_y)  # the same box, now with a plane: the pile's top, never below it
        self.emit("miss")
        if rules.full(col):
            self.die()

    def rest(self, i):
        """The plugin's callback for a body asleep. A missed box that rests joins the pile as drawn. A box asleep in
        FALL cannot happen by the rules; it counts as a miss so that no body is lost."""
        phase = self.phase
        if phase[i] == FALL:
            x, y = self.physics_plugin.place(i)
            self.at_rail(i, x, y)
        elif phase[i] == LAND:
            x, y = self.physics_plugin.place(i)
            self.shown[x // SIZE] += 1
            phase[i] = FREE
            if self.art:  # a puff of dust where it lands
                dice = self.dice
                for _ in range(6):
                    self.fx.add(x + dice.below(SIZE), y + SIZE - 2, dice.spread(40), -10 - dice.below(30),
                                DUST[dice.below(2)], 0.3 + dice.below(20) / 100, 60.0)

    def paint_static(self, cv):
        pictures.draw(cv, "bucket_scene", 0, 0)  # the painted village; without it the black fill (covers is False)

    def paint(self, cv):
        if self.art and getattr(cv, "pictures", False):
            self.paint_art(cv)
            return
        fill, shown = cv.fill, self.shown
        for col in range(COLS):
            if shown[col]:
                fill(SIZE * col, HEIGHT - SIZE * shown[col], SIZE, SIZE * shown[col], PALETTE[col % len(PALETTE)])
        plugin = self.physics_plugin
        for i in range(N):
            if self.phase[i] and not (self.phase[i] == FALL and self.last_y[i] == -SIZE):  # a new box: the read is stale
                x, y = plugin.place(i)
                fill(x, y, SIZE, SIZE, PALETTE[i % len(PALETTE)])
        fill(0, RAIL_Y, WIDTH, 1, GREY)
        x = self.rules.bucket_x
        fill(x, RAIL_Y - WALL_H, WALL_PX, WALL_H, YELLOW)
        fill(x + BUCKET_W - WALL_PX, RAIL_Y - WALL_H, WALL_PX, WALL_H, YELLOW)
        fill(x, RAIL_Y - FLOOR, BUCKET_W, FLOOR, YELLOW)

    def paint_art(self, cv):
        """The painted pile, one picture a column, the falling crates, the bucket (tipped over at the round's end),
        and the effects."""
        shown, draw = self.shown, pictures.draw
        for col in range(COLS):
            if shown[col]:
                draw(cv, PILES[shown[col]][col % HUES], SIZE * col, HEIGHT - SIZE * shown[col])
        plugin = self.physics_plugin
        for i in range(N):
            if self.phase[i] and not (self.phase[i] == FALL and self.last_y[i] == -SIZE):  # a new box: stale read
                x, y = plugin.place(i)
                col = x // SIZE
                draw(cv, CRATES[(col + shown[col]) % HUES], x, y)  # the wood it keeps on the pile
        x = self.rules.bucket_x
        if self.state == OVER:
            draw(cv, "bucket_tipped", x, RAIL_Y - TIPPED_H)
        else:
            draw(cv, "bucket_bucket", x, RAIL_Y - BUCKET_H)
        self.paint_effects(cv)

    def paint_effects(self, cv):
        """The river's shimmer, the chimneys' smoke, and each catch's sparkles and coin. They run on the frame's
        clock (self.last), so they go on at the round's end."""
        now, dice, draw = self.last, self.dice, pictures.draw
        for i, (x, y) in enumerate(GLINTS):
            k = now // GLINT_MS + 2 * i
            if k % 5:  # each glint goes out now and then: a twinkle
                draw(cv, SHIMMER[k % 3], x, y)
        if now - self.puffed >= SMOKE_MS:
            self.puffed = now
            for x, y in CHIMNEYS:
                self.smoke.add(x + dice.spread(1), y, 3 + dice.below(5), -7 - dice.below(5), 0, Smoke.LIFE, -1.0)
        self.smoke.update(self.dt)
        self.smoke.draw(cv)
        for coin in self.coins:
            x, y, at = coin
            t = now - at
            if t < SPARKLE_MS:
                for k in range(SPARKLES):  # the sparkles: each in turn, round the catch
                    if k * SPARKLE_MS // SPARKLES <= t < (k + 2) * SPARKLE_MS // SPARKLES:
                        draw(cv, "bucket_sparkle", x + (k * 23) % 34 - 16, y - 4 - (k * 17) % 18)
            if t < COIN_MS:  # the coin: up and over to the score, faster as it goes
                f = t * t * 1000 // (COIN_MS * COIN_MS)
                draw(cv, "bucket_coin", x + (COIN_TO[0] - x) * f // 1000, y + (COIN_TO[1] - y) * f // 1000
                     - 30 * (f * (1000 - f)) // 250000)
        if self.coins and now - self.coins[0][2] >= COIN_MS:
            self.coins.pop(0)
