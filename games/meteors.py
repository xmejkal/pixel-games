"""
Meteors (P773): stay alive under a rain of burning meteors. A small walker walks the ground, left or right, and never
stops.

How to play: tap BOOT to turn the walker round. It also turns at each screen edge. A mark on the ground shows where a
meteor will land: a dark shadow at the meteor's full width (a red bar without the painted art). A meteor lands,
bounces and then lies as a burning coal for a while, so the safe ground shrinks. The walker dies when it touches a
meteor, in the air or as a coal. The score is the seconds it lived. Meteors come faster as time goes on, up to a limit.

The meteors are the bodies of burning.py, on the rain's physics (plugins.PhysicsPlugin: engine.Bodies, or its twin in
Python) and the fire field of fire.py. A meteor is dropped to land on its mark: Rules.aim picks the mark and the drift
that fits it. A body with no meteor is parked off the screen.
--- MVP (P773) ---
"""

import random
from array import array

import pictures
import plugins
from burning import BODY, N, BurningBodies
from burning import COAL_SHADE
from cues import Cue
from fire import MODES
from gfx import BLACK, GREEN, HEIGHT, OVER, PLAY, RED, WHITE, WIDTH, YELLOW, Dice, Game, c565
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

# --- MVP (P773, story 4) --- the painted look: art/sets/meteors.py's sizes, which the board has no art/ to read
# (tests/test_meteors_art.py pins them), and the effects' numbers, set by eye on Mac frames of tools/render_scene.py
FIG_W, FIG_H, FIG_DX = 30, 32, 9  # the walker's picture, drawn at its left edge less FIG_DX, its soles on the last row
RUN_POSES = 12  # art/mocap.py's run
STRIDE_PX = 46  # px of one run cycle: the capture's stride, 1.698 body heights, at 27 px a body height
ROCK, ROCK_FRAMES, SPIN_MS = 10, 4, 90  # the rock's picture round its 8 px body, its frames, the ms of each
HALO, HALO_ALPHA = 24, 120  # the glow round a falling rock, blended over the frame
COAL_W, COAL_H, COAL_FRAMES = 10, 7, 4  # the coal's picture, its base on the last row; it dims over COAL_MS
SHADOW_W, SHADOW_H = 8, 3  # the landing shadow: the mark's full width, from the drop on
RING_W, RING_H, RING_MS = 12, 5, 300  # the white ring round the shadow, in the last RING_MS before the landing
GLOW_W, GLOW_H, GLOW_MS, GLOW_ALPHA = 84, 24, 500, 230  # an impact's light on the ground, fading over GLOW_MS
FLASH_H, FLASH_ALPHAS = 14, (170, 80)  # the ground band's white flash at an impact: one alpha a frame
SHAKE = (2, 0, 1)  # px the ground band jumps up in each frame after an impact
GROUND_TOP = 196  # the ground band's top row: its own picture, so the shake redraws only it, wholly on the panel
HIT_MS = 160  # the scarf flashes red this long after a hit, then the smoke hides him
SMOKE_W, SMOKE_H, SMOKE_FRAMES, SMOKE_MS = 30, 34, 5, 120  # the dark puff at a hit, a frame each SMOKE_MS
SMOKE_ALPHAS = (255, 220, 180, 130, 80)  # each frame thinner
SPARK_S, DEBRIS = 0.2, 8  # a spark's life (one a frame a meteor: 5 at 40 ms), and the bits of rock an impact throws
SPARKS = (c565(255, 248, 220), c565(255, 200, 90), c565(255, 130, 40))
BITS = (c565(70, 46, 48), c565(255, 150, 60), c565(255, 222, 150))
POSES = {(kind, side): tuple("meteors_%s_%s%d" % (kind, side, i) for i in range(RUN_POSES))
         for kind in ("run", "hit") for side in "rl"}
ROCKS = tuple("meteors_rock%d" % i for i in range(ROCK_FRAMES))
EMBERS = tuple("meteors_coal%d" % i for i in range(COAL_FRAMES))
PUFFS = tuple("meteors_smoke%d" % i for i in range(SMOKE_FRAMES))
ASH = (c565(40, 34, 50), c565(84, 74, 96))  # the burst at a hit: dark ash, never fire colours
# fx_fire_set_look's decay, cool, sway, spots, spread, fast, embers, fade for the painted look, set by eye on Mac
# frames: more cooling and fade, no fast patches and a decay under 32, so a falling meteor's heat dies within about
# 40 px of it, a tail behind a rock and not a column to the top of the screen. The flat look keeps BurningBodies'.
TAIL_LOOK = (30, 200, 1, 0, 1, 0, 0, 120)


def pose_for(x, right):
    """The run's pose for a walker with his left edge at x, facing right or left: the pose follows the distance, so
    his feet stay put, and facing left the mirrored cycle runs the other way."""
    return (x if right else -x) * RUN_POSES // STRIDE_PX % RUN_POSES


class Meteors(BurningBodies):
    name = "meteors"
    hint = "tap: turn"
    SEED, GRAVITY, FRICTION, FLARE_MIN = None, GRAVITY_PX, 0.0, FLARE_MIN_PX  # friction 0: a meteor bounces straight up
    TITLE_MS = Game.TITLE_MS
    MODES = MODES[1:2]  # the picture mode alone: the flames over the painted dusk
    ART = ("meteors", None)  # its own art set, all of it
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
            self.impact = array("i", [-GLOW_MS] * N)  # played_ms at each meteor's landing, for its glow
            self.dice = Dice()
            if pictures.load(*self.ART):
                self.LOOK = TAIL_LOOK
            super().setup()
        else:
            self.start_bodies()
        self.art = pictures.load(*self.ART)  # the painted look and its effects; without it the flat shapes
        self.fx.MAX = 64  # the sparks of eight meteors and the bits of an impact
        self.flash, self.shake = len(FLASH_ALPHAS), len(SHAKE)  # the frames of each drawn since the last impact
        self.dy = 0  # px the ground moves down in this frame's shake: 0 or less

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
        self.phase[i], self.land_x[i], self.impact[i] = PARKED, -1, -GLOW_MS  # no glow: a new round starts at 0 ms
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
        if self.art:
            self.burst(body.place()[0] + BODY // 2)
            self.impact[i] = self.rules.played_ms
        if self.rules.hits(body.place()[0], GROUND_Y):
            self.kill()
        if self.fire_plugin.field is not None:
            self.flare(body, speed)

    def kill(self):
        """The walker dies, once, with a burst at it."""
        if self.state != PLAY:
            return
        # painted, the burst is dark ash, then a puff of smoke hides him (paint_walker): nobody is drawn burning. The
        # same burst as the flat look's, so the round draws the same random numbers
        self.die(self.rules.walker_x + WALKER_W // 2, HEIGHT - WALKER_H // 2, ASH if self.art else (RED, YELLOW))

    def burst(self, x):
        """An impact at x: bits of rock thrown up, and the flash and the shake start."""
        dice = self.dice
        for _ in range(DEBRIS):
            self.fx.add(x + dice.spread(3), HEIGHT - 4, dice.spread(120), -90 - dice.below(140), BITS[dice.below(3)],
                        0.4 + dice.below(25) / 100, 700.0)
        self.flash = self.shake = 0

    def play(self, pressed, held):
        """The walker walks, a tap turns it (never the fire's mode), the bodies step, and a meteor that touches the
        walker kills it."""
        rules, plugin, phase = self.rules, self.physics_plugin, self.phase
        self.covers = self.fire_plugin.field is not None or self.art  # no fill under the field or the painted dusk
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
        if self.art:
            self.trail()

    def trail(self):
        """A spark behind each falling meteor, one a frame."""
        out, dice = self.physics_plugin.out, self.dice
        for i in range(N):
            if self.phase[i] == FALL and not self.landed[i]:
                self.fx.add(out[3 * i] + 2 + dice.below(5), out[3 * i + 1] + dice.below(4), dice.spread(25),
                            -dice.below(40), SPARKS[dice.below(3)], SPARK_S, 0.0)

    def draw_layers(self, cv):
        """The scene's layers, then, painted, each falling rock in its glow in front of its own flames: the rock is
        the brightest thing of its tail."""
        super().draw_layers(cv)
        if not (self.art and getattr(cv, "pictures", False)):
            return
        out, now = self.physics_plugin.out, self.rules.played_ms
        for i in range(N):
            if self.phase[i] == FALL:
                x, y = out[3 * i], out[3 * i + 1]
                pictures.draw(cv, "meteors_halo", x + (BODY - HALO) // 2, y + (BODY - HALO) // 2, HALO_ALPHA)
                pictures.draw(cv, ROCKS[(now // SPIN_MS + i) % ROCK_FRAMES], x - 1, y - 1)

    def draw_bodies(self, cv):
        """Each meteor and coal; a parked body is not drawn. Painted: a coal that dims (draw_layers draws a falling
        rock in front of its flames)."""
        out, fill, phase = self.physics_plugin.out, cv.fill, self.phase
        art = self.art and getattr(cv, "pictures", False)
        now = self.rules.played_ms
        for i in range(N):
            if phase[i] == PARKED or art and phase[i] == FALL:
                continue
            x, y = out[3 * i], out[3 * i + 1]
            if not art:
                fill(x, y, BODY, BODY, COAL_SHADE)
            else:
                k = (now - self.slept[i]) * COAL_FRAMES // COAL_MS
                if (now // 80 + 3 * i) % 7 == 0:  # a flicker: a frame dimmer now and then
                    k += 1
                pictures.draw(cv, EMBERS[min(k, COAL_FRAMES - 1)], x - 1, HEIGHT - COAL_H + self.dy)

    def paint_static(self, cv):
        """The painted dusk under the flames, or black where there is no art, so covers stays true."""
        if not pictures.draw(cv, "meteors_sky", 0, 0) and self.fire_plugin.field is not None:
            cv.fill(0, 0, WIDTH, HEIGHT, BLACK)

    def paint(self, cv):
        """The scene's picture, then a red mark under each meteor that has not landed, and the walker. Painted: the
        impacts' light, flash and shake under the flames, then a shadow for each mark and the walker's run."""
        art = self.art and getattr(cv, "pictures", False)
        self.dy = 0
        if art:
            self.paint_impacts(cv)
        super().paint(cv)
        if art:
            self.paint_walker(cv)
            return
        phase, landed, fill = self.phase, self.landed, cv.fill
        land_x = self.land_x
        for i in range(N):
            if phase[i] == FALL and not landed[i]:
                fill(land_x[i], HEIGHT - MARK_H, BODY, MARK_H, RED)
        fill(self.rules.walker_x, HEIGHT - WALKER_H, WALKER_W, WALKER_H, GREEN if self.state == PLAY else WHITE)

    def paint_impacts(self, cv):
        """The frame's shake (the ground band drawn again, higher), each recent impact's light on the ground, and the
        ground band's white flash."""
        if self.shake < len(SHAKE):
            self.dy = -SHAKE[self.shake]
            self.shake += 1
            if self.dy:  # the ground band, up: wholly on the panel, so one copy by rows
                pictures.draw(cv, "meteors_ground", 0, GROUND_TOP + self.dy)
        now = self.rules.played_ms
        for i in range(N):
            age = now - self.impact[i]
            if 0 <= age < GLOW_MS and self.land_x[i] >= 0:
                x = self.land_x[i] + (BODY - GLOW_W) // 2
                alpha = GLOW_ALPHA * (GLOW_MS - age) // GLOW_MS
                pictures.draw(cv, "meteors_glow", x, HEIGHT - 4 - GLOW_H // 2 + self.dy, alpha)
        if self.flash < len(FLASH_ALPHAS):
            pictures.draw(cv, "meteors_flash", 0, HEIGHT - FLASH_H, FLASH_ALPHAS[self.flash])
            self.flash += 1

    def paint_walker(self, cv):
        """A shadow for each meteor that has not landed (a white ring round it in its last RING_MS), then the walker
        in the pose for where he is: his run by distance, so his feet stay put; the scarf red just after a hit, and then
        only the smoke."""
        now, dy = self.rules.played_ms, self.dy
        for i in range(N):
            if self.phase[i] == FALL and not self.landed[i]:
                x = self.land_x[i]
                pictures.draw(cv, "meteors_shadow", x, HEIGHT - SHADOW_H + dy)
                if now - self.dropped[i] >= FALL_MS - RING_MS:
                    pictures.draw(cv, "meteors_ring", x + (SHADOW_W - RING_W) // 2, HEIGHT - RING_H + dy)
        rules = self.rules
        x, right = rules.walker_x, rules.dir > 0
        pose = pose_for(x, right)
        if self.state != OVER:
            pictures.draw(cv, POSES["run", "r" if right else "l"][pose], x - FIG_DX, HEIGHT - FIG_H + dy)
            return
        since = self.last - self.since  # ms since the hit: age is read before the frame's play
        if since < HIT_MS:  # the scarf flashes red, then the smoke hides him: he is never drawn in the flames
            pictures.draw(cv, POSES["hit", "r" if right else "l"][pose], x - FIG_DX, HEIGHT - FIG_H + dy)
        k = since // SMOKE_MS
        if k < SMOKE_FRAMES:
            pictures.draw(cv, PUFFS[k], x + WALKER_W // 2 - SMOKE_W // 2, HEIGHT - SMOKE_H + dy, SMOKE_ALPHAS[k])
