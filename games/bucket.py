"""
Bucket (P773): catch the falling boxes. A bucket rides on a rail near the bottom of the screen.

How to play: hold BOOT and the bucket goes right, let go and it goes left. A box that falls into the bucket is a
point. A box you miss bounces and lands on the pile in its column. When a column of the pile reaches the rail, the
round ends. Each point makes the boxes come faster.

The boxes fall on the rain's physics (plugins.PhysicsPlugin: engine.Bodies, or its twin in Python). The bodies do not
touch each other, so the pile is a count of boxes per column in Python: a missed box falls and bounces on the real
physics, onto the top of the pile in its column.
--- MVP (P773) ---
"""

import math
import random
from array import array

import plugins
from cues import Cue
from gfx import GREY, HEIGHT, PALETTE, PLAY, WIDTH, YELLOW, Game
from plugins import PhysicsPlugin

# --- MVP (P773) --- the rules, in px, ms and ints. Mac trials through Game.step on the Python bodies (frames of 42 and
# 60 ms, 20 seeds): an idle player lost after 14 to 45 s, one who held always after 14 to 31 s, and 50 blind rhythms
# (hold periods 200 to 2000 ms, duty 20 to 80 %) after 61 s at the slowest. A bot that steers to the lowest box lasted
# 481 s at the least, mostly the whole 600 s. Take care with DROP_MIN_MS: at SIZE 12 the bot broke down in a narrow band
# of it (1100 and 1150 ms: 27 to 82 s), as a box takes about 1.2 s to fall to the rail.
SIZE = 10  # px, a box's side
COLS = WIDTH // SIZE  # the columns a box drops at, and the pile's
PILE_ROWS = 3  # boxes a column holds before it reaches the rail
RAIL_Y = HEIGHT - SIZE * PILE_ROWS  # px: the line the bucket rides on, and the top of a full column
BUCKET_W = 50  # px
BUCKET_PX_S = 300  # px a second, to the right while BOOT is held and to the left while it is not
N = 8  # boxes out at most
GRAVITY_PX = 300  # px/s squared, a box needs about a second to the rail (the rain's is 2000)
DROP_MS, DROP_STEP_MS, DROP_MIN_MS = 1500, 50, 1000  # a new box each DROP_MS, shorter by DROP_STEP_MS for each point


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
        if x < 0 or x > WIDTH - BUCKET_W:
            x = 0 if x < 0 else WIDTH - BUCKET_W
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
        """Whether a box at x, at the rail, is wholly inside the bucket."""
        return self.bucket_x <= x and x + SIZE <= self.bucket_x + BUCKET_W

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
WALL_PX, WALL_H = 4, 12  # px: the bucket's walls and their height above the rail
FLOOR = 3  # px, the bucket's floor


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

    def play(self, pressed, held):
        rules, plugin, phase = self.rules, self.physics_plugin, self.phase
        rules.move(self.ms, held)
        plugin.read(self.on_rest)
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
            self.pop(x + SIZE // 2, RAIL_Y)
            return
        col = x // SIZE
        rest_y = HEIGHT - SIZE * rules.miss(col)
        speed = int(math.sqrt(2 * GRAVITY_PX * (y + SIZE)))  # the bodies do not read their speed out: from the fall
        self.phase[i] = LAND
        self.physics_plugin.spawn(i, x, y, 0, speed, rest_y)  # the same box, now with a plane: the pile's top
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
            self.shown[self.physics_plugin.place(i)[0] // SIZE] += 1
            phase[i] = FREE

    def paint(self, cv):
        fill, shown = cv.fill, self.shown
        for col in range(COLS):
            if shown[col]:
                fill(SIZE * col, HEIGHT - SIZE * shown[col], SIZE, SIZE * shown[col], PALETTE[col % len(PALETTE)])
        plugin = self.physics_plugin
        for i in range(N):
            if self.phase[i]:
                x, y = plugin.place(i)
                fill(x, y, SIZE, SIZE, PALETTE[i % len(PALETTE)])
        fill(0, RAIL_Y, WIDTH, 1, GREY)
        x = self.rules.bucket_x
        fill(x, RAIL_Y - WALL_H, WALL_PX, WALL_H, YELLOW)
        fill(x + BUCKET_W - WALL_PX, RAIL_Y - WALL_H, WALL_PX, WALL_H, YELLOW)
        fill(x, RAIL_Y - FLOOR, BUCKET_W, FLOOR, YELLOW)
