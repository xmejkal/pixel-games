"""
Things on runner's track: the obstacles, the bonuses, how they come, and the timed effects a bonus starts (P560, P561).

A kind of obstacle is one small class with a size and a look. A bonus is one row of BONUSES. Track owns the things on
the track as [x, kind, w, h, lift] and places new ones by pattern; Runner keeps the jump, the score and the effects,
and asks Track which things the runner touched in this frame. Every number is a first guess, to tune by playing.
"""

import random

from gfx import BLACK, GREEN, WIDTH, WHITE, c565

W = WIDTH
RUN_X0, RUN_X1, RUN_TALL = 52, 66, 24  # the runner's hit box: from x, to x, and its height above its feet
SLOW, X2 = 1, 2  # effect names


class Effects:
    """Timed effects. Each entry is [name, seconds left, mult, seconds at start, colour]. factor() multiplies the
    entries of one name, so two x2 effects at once give x4."""

    def __init__(self):
        self.on = []

    def add(self, name, seconds, mult, colour):
        self.on.append([name, seconds, mult, seconds, colour])

    def step(self, dt):
        ended = False
        for e in self.on:
            e[1] -= dt
            ended = ended or e[1] <= 0
        if ended:  # a new list only when one ends, not every frame
            self.on = [e for e in self.on if e[1] > 0]

    def factor(self, name, cap=None):
        f = 1
        for e in self.on:
            if e[0] == name:
                f *= e[2]
        return min(f, cap) if cap else f


class Cactus:
    """An obstacle on the ground. A touch ends the run."""

    deadly = True

    def size(self, low):
        return random.randrange(14, 26), random.randrange(16, 41 if low else 65), 0

    def paint(self, cv, x, w, h, lift, ground, t):  # a cactus with two arms
        green, dark = GREEN, c565(20, 120, 40)
        cv.fill(x + w // 3, ground - h, w // 3 + 2, h, green)
        cv.fill(x, ground - h * 2 // 3, w // 3 + 1, 5, green)
        cv.fill(x, ground - h * 2 // 3 - 8, 5, 10, green)
        cv.fill(x + w * 2 // 3, ground - h // 2, w // 3 + 1, 5, green)
        cv.fill(x + w - 5, ground - h // 2 - 8, 5, 10, green)
        cv.fill(x + w // 3 + 3, ground - h, 2, h, dark)


BIRD_UP = ("...ww.....", "..www.....", "ybkbbbb...", ".bbbbbbbt.", "..........", "..........")
BIRD_DOWN = ("..........", "..........", "ybkbbbb...", ".bbbbbbbt.", "..www.....", "...ww.....")
BIRD_COLOURS = {"y": c565(250, 160, 40), "b": c565(90, 60, 130), "w": c565(150, 120, 190), "k": BLACK,
                "t": c565(50, 30, 80)}


class Bird:
    """A low flyer. A runner on the ground passes under it, a high jump hits it."""

    deadly = True

    def size(self, low):
        return 20, 12, random.randrange(34, 51)

    def paint(self, cv, x, w, h, lift, ground, t):
        cv.sprite(BIRD_UP if int(t * 8) % 2 else BIRD_DOWN, BIRD_COLOURS, x, ground - lift - h, 2)


DISC, CLOCK, CROSS = 0, 1, 2  # bonus shapes
COIN_RING = ((-9, 4, 5), (-5, 10, 9), (5, 4, 5))  # the coin's dark edge: (top from the centre, height, half width)
COIN_FACE = ((-8, 2, 3), (-6, 3, 6), (-3, 6, 8), (3, 3, 6), (6, 2, 3))  # its face, inside the edge


class Bonus:
    """A thing to collect: points, a timed effect, or both. One row of BONUSES per kind."""

    deadly = False
    SIZE = 16

    def __init__(self, colour, shape, points, effect, seconds, mult, first, weight):
        self.colour, self.shape, self.points = colour, shape, points
        self.effect, self.seconds, self.mult = effect, seconds, mult
        self.first, self.weight = first, weight  # the level it first comes at, and how often against the others

    def paint(self, cv, x, w, h, lift, ground, t):
        cx, cy, c = x + w // 2, ground - lift - h // 2, self.colour
        if self.shape == DISC:  # a round coin that spins: a stepped circle, narrower as it turns
            s = (8, 6, 3, 6)[int(t * 10 + x / 40) % 4]
            for dy, hh, half in COIN_RING:
                cv.fill(cx - half * s // 8, cy + dy, 2 * (half * s // 8), hh, BLACK)
            for dy, hh, half in COIN_FACE:
                cv.fill(cx - half * s // 8, cy + dy, 2 * (half * s // 8), hh, c)
            cv.fill(cx - 3 * s // 8, cy - 4, 2, 5, c565(255, 240, 160))  # the shine
        elif self.shape == CROSS:  # a star, twinkling
            cv.fill(cx - 8, cy - 3, 16, 6, BLACK)
            cv.fill(cx - 3, cy - 8, 6, 16, BLACK)
            cv.fill(cx - 7, cy - 2, 14, 4, c)
            cv.fill(cx - 2, cy - 7, 4, 14, c)
            if int(t * 6 + x / 30) % 3 == 0:
                cv.fill(cx - 1, cy - 1, 2, 2, WHITE)
        else:  # a clock: a blue face with two hands
            cv.disc(cx, cy, 8, BLACK)
            cv.disc(cx, cy, 6, c)
            cv.fill(cx - 1, cy - 5, 2, 6, WHITE)
            cv.fill(cx, cy - 1, 4, 2, WHITE)


COIN = Bonus(c565(230, 180, 20), DISC, 25, None, 0, 1, 0, 6)
BONUSES = (
    COIN,
    Bonus(c565(40, 90, 230), CLOCK, 0, SLOW, 4.0, 0.6, 50, 2),  # the world at 0.6 of its speed for 4 s
    Bonus(c565(220, 40, 200), CROSS, 0, X2, 6.0, 2, 120, 2),  # x2 score for 6 s, and two at once give x4
)
CACTUS, BIRD = Cactus(), Bird()
SINGLE, WIDE, PAIR, RUN3, FLYER = 0, 1, 2, 3, 4  # spawn patterns


class Track:
    """The things on the track, moved, placed and painted. Obstacles come by pattern, measured from the right edge of
    the last one, so every gap is exact; a bonus comes in the middle of a gap, so it is never close to an obstacle."""

    def __init__(self):
        self.things = []  # [x, kind, w, h, lift]
        self.last_end = W - 160.0  # the right edge of the last obstacle: the first one comes at about W + 20
        self.chain = 0  # obstacles still to come in a pair or a run, close behind each other
        self.bonus_due = 300.0  # px until a bonus may come
        self.seen = set()  # bonus kinds already shown once, alone

    def move(self, step):
        gone = False
        for t in self.things:
            t[0] -= step
            gone = gone or t[0] + t[2] < -10
        if gone:
            self.things = [t for t in self.things if t[0] + t[2] >= -10]
        self.last_end -= step
        self.bonus_due -= step

    def spawn(self, level, k):
        while self.last_end < W + 40:
            if self.chain:  # the rest of a pair or a run: low and close, and it cannot start another one
                self.chain -= 1
                self.add(CACTUS, self.last_end + random.randrange(40, 70) * k, True)
                continue
            pattern = self.pick(level)
            gap = random.randrange(300, 420) * k if pattern == WIDE else random.randrange(180, 300) * k
            if self.bonus_due <= 0 and pattern in (SINGLE, WIDE):
                gap = self.bonus(level, k, gap)
            if pattern in (PAIR, RUN3):
                self.chain = 1 if pattern == PAIR else 2
            self.add(BIRD if pattern == FLYER else CACTUS, self.last_end + gap, pattern in (PAIR, RUN3))

    def pick(self, level):
        weights = ((SINGLE, 6), (WIDE, 2), (PAIR, min(3, level / 60) if level >= 60 else 0),
                   (RUN3, 2 if level >= 300 else 0), (FLYER, 2 if level >= 150 else 0))
        r = random.random() * sum(w for _, w in weights)
        for pattern, w in weights:
            r -= w
            if r < 0:
                return pattern
        return SINGLE

    def add(self, kind, x, low):
        w, h, lift = kind.size(low)
        self.things.append([x, kind, w, h, lift])
        self.last_end = x + w

    def bonus(self, level, k, gap):
        """Bonuses in the middle of the coming gap. Answers the gap, longer when a kind is shown for the first time."""
        kinds = [b for b in BONUSES if level >= b.first]
        r, b = random.random() * sum(c.weight for c in kinds), kinds[-1]  # the coin comes from level 0, so never empty
        for c in kinds:
            r -= c.weight
            if r < 0:
                b = c
                break
        first = b not in self.seen
        if first:  # the first of a kind comes alone, with room to see it
            self.seen.add(b)
            gap = max(gap, 450 * k)
        n = min(5, max(1, int((gap - 140) // 24))) if b is COIN and not first and random.random() < 0.6 else 1  # a row
        x = self.last_end + (gap - 24 * (n - 1) - Bonus.SIZE) / 2
        lift = random.randrange(6, 90) if b is COIN else random.randrange(20, 100)
        for i in range(n):
            self.things.append([x + 24 * i, b, Bonus.SIZE, Bonus.SIZE, lift])
        self.bonus_due = random.randrange(250, 500) * k
        return gap

    def hit(self, t, step, was, h):
        """Did the runner touch thing t in this frame? Its x counts over the whole stretch it moved. An obstacle that
        has already passed is judged at the runner's higher height, so a landing runner is not hit by it; a bonus
        counts over the runner's whole rise or fall in the frame, so a fast one is not missed."""
        x, kind, w, th, lift = t
        if not (x < RUN_X1 and x + step + w > RUN_X0):
            return False
        if kind.deadly:
            lo = h if x + w > RUN_X0 else max(was, h)
            return lo < lift + th - 2 and lo + RUN_TALL > lift + 2
        return min(was, h) < lift + th and max(was, h) + RUN_TALL > lift

    def paint(self, cv, ground, t):
        for x, kind, w, h, lift in self.things:
            if x < W + 10:
                kind.paint(cv, int(x), w, h, lift, ground, t)
