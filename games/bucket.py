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

from gfx import HEIGHT, WIDTH

# --- MVP (P773) --- the rules, in px, ms and ints. Mac trials of the rules through Game.step (frames of 42 and 60 ms).
SIZE = 8  # px, a box's side
COLS = WIDTH // SIZE  # the columns a box drops at, and the pile's
PILE_ROWS = 4  # boxes a column holds before it reaches the rail
RAIL_Y = HEIGHT - SIZE * PILE_ROWS  # px: the line the bucket rides on, and the top of a full column
BUCKET_W = 48  # px
BUCKET_PX_S = 200  # px a second, to the right while BOOT is held and to the left while it is not
DROP_MS, DROP_STEP_MS, DROP_MIN_MS = 1500, 60, 500  # a new box each DROP_MS, shorter by DROP_STEP_MS for each point


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
