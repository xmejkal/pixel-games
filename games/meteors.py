"""
Meteors (P773): stay alive under a rain of burning meteors. A small walker walks the ground, left or right, and never
stops.

How to play: tap BOOT to turn the walker round. It also turns at each screen edge. A red mark on the ground shows where
a meteor will land. A meteor lands, bounces and then lies as a burning coal for a while, so the safe ground shrinks.
The walker dies when it touches a meteor, in the air or as a coal. The score is the seconds it lived. Meteors come
faster as time goes on, up to a limit.

The meteors are the bodies of burning.py, on the rain's physics (plugins.PhysicsPlugin: engine.Bodies, or its twin in
Python) and the fire field of fire.py. A meteor is dropped to land on its mark: Rules.aim picks the mark and the drift
that fits it. A body with no meteor is parked off the screen.
--- MVP (P773) ---
"""

import random
from array import array

import plugins
from burning import BODY, N, BurningBodies
from burning import COAL_SHADE
from cues import Cue
from fire import MODES
from gfx import GREEN, HEIGHT, PLAY, RED, WHITE, WIDTH, Game
from motion import HIT

# --- MVP (P773) --- the rules, in px, ms and ints. Mac trials through Game.step on the Python bodies (frames of 42 ms, 60 ms
# and random 20 to 90 ms, 16 seeds each; the trial script is not in the repository). The lazy players lose early: an idle
# walker after 3 to 7 s, one who taps every frame after 16 s at the most, a tap at 8 Hz after 12 s, and every blind
# rhythm (a tap each 200 to 3000 ms in steps of 200) after 18 s at the most (seeds 17 to 32: 25 s, 25 s, 18 s). A bot that
# keeps out of every blocked place, leaves a mark that falls on it by the end into the wider gap, and turns only at the
# ends of its gap lasted the whole 180 s in all 96 runs; it was trapped in a gap under SAFE_PX once in each 48. Without the
# fair aim (Rules.fair) a bot that avoided the marks died after 9 to 44 s at every density tried: a mark cut it off in a
# pocket between a coal and a wall, and TURN_MS (18 px of travel) kept it from turning back. GRAVITY_PX 400 gives a fall of
# 1.1 s, so a mark gives time to act.
GROUND_Y = HEIGHT - BODY  # px: a meteor's plane, the y its top rests at
GRAVITY_PX = 400  # px/s squared (the rain's is 2000): a meteor falls for about 1.1 s, so its mark gives time to act
FLARE_MIN_PX = 300  # px/s: a first landing, at about 440, flares and no bounce after it does
DRIFT = 60  # px/s: a meteor's sideways speed is -DRIFT to DRIFT
COAL_MS = 4000  # a meteor lies as a coal this long, then it is parked
WALK_PX_S = 120  # px a second
TURN_MS = 150  # a tap within this many ms of the last turn does nothing, so fast taps never stand still
WALKER_W, WALKER_H = 12, 32  # px: on the ground. WALKER_H is at least the first bounce's peak, so no walker passes under one
AIM_KINDS = 3  # a drop lands anywhere, on the walker, or ahead of it: so one who stands still or goes on loses
DROP_MS, DROP_STEP_MS, DROP_MIN_MS = 2500, 50, 1000  # a new meteor each DROP_MS, shorter by DROP_STEP_MS for each second lived, down to DROP_MIN_MS at 30 s


def fall_ms():
    """The ms a meteor needs from y = -BODY to its plane, in whole physics steps, as PhysicsPlugin steps it."""
    v = y = 0.0
    steps = 0
    while y < HEIGHT:
        v += GRAVITY_PX * plugins.DT
        y += v * plugins.DT
        steps += 1
    return steps * plugins.STEP_MS


FALL_MS = fall_ms()
LAND_MS = FALL_MS - 200  # the ms a walker has from a drop to the meteor at its head
WALKER_MAX_X = WIDTH - WALKER_W  # the walker's left edge, at most
MARGIN_PX = 8  # px of ground kept free on each side of a meteor, for the frame's travel
SAFE_PX = 48  # px: the fair aim leaves the walker a free stretch this wide, which it can reach before the meteor lands
AIM_TRIES = 8  # kinds of aim tried for one drop; if none is fair, the drop is skipped


def blocked(places, left):
    """The walker's left edges that the meteors block, as merged [lo, hi, [(place, ms)]] with lo and hi open ends.
    places: each meteor's ground place (its left edge), -1 for none. left: the ms until it is at the walker's head, 0
    for a coal. Made at a drop, not in a frame."""
    out = []
    for h, ms in sorted((places[i], left[i]) for i in range(len(places)) if places[i] >= 0):
        lo, hi = h - WALKER_W - MARGIN_PX, h + BODY + MARGIN_PX
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
            out[-1][2].append((h, ms))
        else:
            out.append([lo, hi, [(h, ms)]])
    return out


def room(zones, x, direction):
    """The widest free stretch, in px, that a walker at left edge x going in direction can reach alive. In a free gap
    it is the gap. Inside a blocked place it leaves by an end, and it must clear each meteor on its way, by MARGIN_PX,
    before that meteor is at its head (a coal never lets it pass; a turn costs TURN_MS). The stretch is the gap that
    end opens into."""
    inside = [z for z in zones if z[0] < x < z[1]]
    if not inside:
        return min([z[0] for z in zones if z[0] >= x] + [WALKER_MAX_X]) - max([z[1] for z in zones if z[1] <= x] + [0])
    lo, hi, meteors = inside[0]
    best = 0
    for end in (lo, hi):
        if not 0 <= end <= WALKER_MAX_X:
            continue
        turn = TURN_MS if (end - x) * direction < 0 else 0
        if any(px * 1000 // WALK_PX_S + turn > ms for px, ms in on_the_way(meteors, x, end == lo)):
            continue
        gap = end - max([z[1] for z in zones if z[1] <= end] + [0]) if end == lo else \
            min([z[0] for z in zones if z[0] >= end] + [WALKER_MAX_X]) - end
        best = max(best, gap)
    return best


def on_the_way(meteors, x, leftward):
    """For each meteor that a walker at x passes under going left (leftward) or right: the px it walks to clear it by
    MARGIN_PX, and the meteor's ms."""
    for h, ms in meteors:
        if leftward and h < x + WALKER_W:
            yield x - (h - WALKER_W - MARGIN_PX), ms
        elif not leftward and h + BODY > x:
            yield h + BODY + MARGIN_PX - x, ms


class Rules:
    """The rules, with no display and no physics. walker_x: the walker's left edge in px. dir: +1 right, -1 left.
    played_ms: the ms played. Ints only, so a frame makes nothing."""

    def __init__(self):
        self.walker_x, self.dir, self.rest = (WIDTH - WALKER_W) // 2, 1, 0  # rest: px times ms short of the next whole px
        self.since = TURN_MS  # ms since the last turn, up to TURN_MS
        self.played_ms, self.clock = 0, 0  # clock: the ms since the last drop

    def drop_ms(self):
        """The ms between two drops: shorter for each second lived, down to the least."""
        return max(DROP_MIN_MS, DROP_MS - DROP_STEP_MS * (self.played_ms // 1000))

    def move(self, ms, tapped):
        """ms of play. A tap turns the walker round, unless it turned within TURN_MS. It walks, and turns at an edge."""
        self.played_ms += ms
        self.since = min(self.since + ms, TURN_MS)
        if tapped and self.since >= TURN_MS:
            self.dir, self.since = -self.dir, 0
        self.rest += self.dir * WALK_PX_S * ms
        px = self.rest // 1000
        self.rest -= px * 1000
        x = self.walker_x + px
        if x < 0 or x > WIDTH - WALKER_W:
            x = 0 if x < 0 else WIDTH - WALKER_W
            self.dir, self.rest, self.since = -self.dir, 0, 0
        self.walker_x = x

    def due(self, ms, free):
        """ms of play. free: a body is free for a meteor. Answers True when a meteor drops. With no body free the clock
        holds at drop_ms(), so a body that frees gets one meteor, never a burst."""
        drop = self.drop_ms()
        self.clock += ms
        if self.clock >= drop and free:
            self.clock = min(self.clock - drop, drop)
            return True
        self.clock = min(self.clock, drop)
        return False

    def fair(self, places, left, land_x):
        """Whether a new meteor at land_x leaves the walker a free stretch of SAFE_PX that it can reach alive, or at
        least no less than before. places, left: the meteors out now, as blocked() takes them."""
        before = room(blocked(places, left), self.walker_x, self.dir)
        after = room(blocked(list(places) + [land_x], list(left) + [LAND_MS]), self.walker_x, self.dir)
        return after >= SAFE_PX or after >= before

    def aim(self, places, left):
        """A drop that lands on its mark: (land_x, the drift vx, the start x0), with x0 and land_x both on the screen,
        or None. A drop lands anywhere, on the walker or ahead of it; one that leaves the walker no safe stretch (fair)
        is not taken, and another kind is tried. places, left: the meteors out now, as blocked() takes them."""
        for _ in range(AIM_TRIES):
            vx = random.randrange(-DRIFT, DRIFT + 1)
            shift = vx * FALL_MS // 1000  # px the drift carries it
            lo, hi = max(0, shift), min(WIDTH - BODY, WIDTH - BODY + shift)  # the marks whose start is on the screen too
            kind = random.randrange(AIM_KINDS)
            if kind == 0:
                land_x = random.randrange(lo, hi + 1)
            else:  # at the walker: where it is, then where it will be if it goes on
                land_x = self.walker_x + (WALKER_W - BODY) // 2 + (self.dir * WALK_PX_S * FALL_MS // 1000 if kind == 2 else 0)
                land_x = min(max(land_x, lo), hi)
            if self.fair(places, left, land_x):
                return land_x, vx, land_x - shift
        return None

    def hits(self, x, y):
        """Whether a meteor with its top left corner at x, y touches the walker."""
        return x < self.walker_x + WALKER_W and self.walker_x < x + BODY and HEIGHT - WALKER_H < y + BODY and y < HEIGHT


# --- MVP (P773) --- the game
PARKED, FALL, COAL = 0, 1, 2  # a meteor's phase: no meteor, it falls and bounces, it lies burning
MARK_H = 3  # px: the mark's height on the ground


class Meteors(BurningBodies):
    name = "meteors"
    hint = "tap: turn"
    SEED, GRAVITY, FRICTION, FLARE_MIN = None, GRAVITY_PX, 0.0, FLARE_MIN_PX  # friction 0: a meteor bounces straight up
    TITLE_MS = Game.TITLE_MS
    MODES = MODES[:1]  # the linear mode alone
    cues = {"land": Cue("land"), "die": Cue("die")}
    fire_plugin = None  # made once in setup
    hud, draw_hud = Game.hud, Game.draw_hud  # the score bar, not the fire's label

    def __init__(self):
        super().__init__()
        self.covers = False  # the title needs its black fill. play() sets it: the field then paints every pixel

    def setup(self):
        """restart() calls this each round. The first round makes the field, the bodies and the effects, once; a later
        round parks every body again, so the field keeps its heat and makes no new one."""
        if self.fire_plugin is None:
            self.phase, self.landed, self.land_x = bytearray(N), bytearray(N), array("h", [-1] * N)
            self.dropped, self.left = array("i", [0] * N), array("h", [0] * N)  # played_ms at each drop; ms, at a drop
            super().setup()
        else:
            self.start_bodies()

    def attach_effects(self):
        """As the scene's, and a hit is handled also with no field: it makes the sound and may kill."""
        super().attach_effects()
        self.handlers[HIT] = self.hit

    def start_bodies(self):
        """Every body parked, and a new walker."""
        self.rules = Rules()
        for i in range(N):
            self.park(i)

    def park(self, i):
        """Body i is no meteor: off the screen, asleep, its trail reset, not drawn and not hit."""
        self.phase[i], self.land_x[i] = PARKED, -1
        self.put(i, 0, HEIGHT, 1)
        self.physics_plugin.spawn(i, 0, HEIGHT, 0, 0, HEIGHT)
        self.slept[i], self.has_prev[i] = None, False
        self.effects.bodies[i].reset()

    def put(self, i, x, y, asleep):
        """Body i as read, so that a frame sees a body spawned in it and not its last place."""
        out = self.physics_plugin.out
        out[3 * i], out[3 * i + 1], out[3 * i + 2] = x, y, asleep

    def free_body(self):
        """A parked body, or -1."""
        for i in range(N):
            if self.phase[i] == PARKED:
                return i
        return -1

    def drop(self, i):
        """A meteor above the screen that lands on its mark. The fair aim gets each meteor's ms until it is at the
        walker's head: 0 for a coal or a landed one."""
        now, left, phase, landed, dropped = self.rules.played_ms, self.left, self.phase, self.landed, self.dropped
        for j in range(N):
            left[j] = max(0, LAND_MS - (now - dropped[j])) if phase[j] == FALL and not landed[j] else 0
        aim = self.rules.aim(self.land_x, left)
        if aim is None:  # no fair place: no meteor this time
            return
        land_x, vx, x0 = aim
        phase[i], landed[i], self.land_x[i], self.rest_y[i], dropped[i] = FALL, 0, land_x, GROUND_Y, now
        self.put(i, x0, -BODY, 0)
        self.physics_plugin.spawn(i, x0, -BODY, vx, 0, GROUND_Y)
        self.slept[i], self.has_prev[i] = None, False
        self.effects.bodies[i].reset()

    def sleep(self, i):
        """Body i is asleep. A meteor that falls asleep becomes a coal, and a coal that lay COAL_MS is parked."""
        phase, now = self.phase, self.rules.played_ms
        if phase[i] == FALL:
            phase[i], self.slept[i] = COAL, now
        elif phase[i] == COAL and now - self.slept[i] >= COAL_MS:
            self.park(i)

    def hit(self, body, speed):
        """A meteor's first hit: the sound, a landing on the walker, and the scene's flare."""
        i = body.i
        if self.phase[i] != FALL or self.landed[i]:
            return
        self.landed[i] = 1
        self.emit("land")
        if self.rules.hits(body.place()[0], GROUND_Y):
            self.kill()
        if self.fire_plugin.field is not None:
            self.flare(body, speed)

    def kill(self):
        """The walker dies, once, with a burst at it."""
        if self.state == PLAY:
            self.die(self.rules.walker_x + WALKER_W // 2, HEIGHT - WALKER_H // 2)

    def play(self, pressed, held):
        """The walker walks, a tap turns it (never the fire's mode), the bodies step, and a meteor that touches the
        walker kills it."""
        rules, plugin, phase = self.rules, self.physics_plugin, self.phase
        self.covers = self.fire_plugin.field is not None  # no fill under the field
        rules.move(self.ms, pressed)
        self.score = rules.played_ms // 1000
        self.step_bodies()
        if self.state != PLAY:
            return
        out = plugin.out  # read in place: no tuple a body
        for i in range(N):
            if phase[i] != PARKED and rules.hits(out[3 * i], out[3 * i + 1]):
                self.kill()
                return
        free = self.free_body()
        if rules.due(self.ms, free >= 0):
            self.drop(free)

    def draw_bodies(self, cv):
        """Each meteor and coal; a parked body is not drawn."""
        out, fill, phase = self.physics_plugin.out, cv.fill, self.phase
        for i in range(N):
            if phase[i] != PARKED:
                fill(out[3 * i], out[3 * i + 1], BODY, BODY, COAL_SHADE)

    def paint(self, cv):
        """The scene's picture, then a red mark under each meteor that has not landed, and the walker."""
        super().paint(cv)
        phase, landed, fill = self.phase, self.landed, cv.fill
        land_x = self.land_x
        for i in range(N):
            if phase[i] == FALL and not landed[i]:
                fill(land_x[i], HEIGHT - MARK_H, BODY, MARK_H, RED)
        fill(self.rules.walker_x, HEIGHT - WALKER_H, WALKER_W, WALKER_H, GREEN if self.state == PLAY else WHITE)
