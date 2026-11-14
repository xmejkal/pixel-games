"""Three side-on games for one button: flappy (tap), runner (tap, hold for a high jump), snake (tap turns right)."""

import random
import time
from math import exp, sqrt

import pictures
import track
from array import array

from effects import FireTrail
from cues import Cue
from fire import FireLayer, ramp
from gfx import (ACCENT, BEST, BLACK, GREEN, GREY, HEIGHT, ORANGE, OVER, RED, WHITE, WIDTH, YELLOW, Dice, Game,
                 Particles, c565)

W, H = WIDTH, HEIGHT
BIRD = ("..kkkk...", ".kyyyywk.", "kyyyyywkk", "kkkyyyyoo", "kwwkyyyok", ".kwwkkkk.", "..kkk....")
BIRD_COLOURS = {"k": c565(40, 30, 20), "y": YELLOW, "w": WHITE, "o": ORANGE}
RUN_TOP = ("..rrrr..", ".rrrrrr.", ".ssskss.", ".ssssss.", "..bbbb..", ".bbbbbb.", "sbbbbbbs", ".bbbbbb.", "..pppp..", "..pppp..")
RUN_LEGS = (("..p..p..", ".kk..kk."), ("...pp...", "...kk..."))
RUN_COLOURS = {"r": RED, "s": c565(250, 200, 160), "k": BLACK, "b": c565(50, 90, 240), "p": c565(40, 40, 120)}
# --- MVP (P651) --- the runner's fire, tuned on Mac frames of the C kernel over the Runner's sky (seven sheets, bench.md P651)
# fx_fire_set_look's decay, cool, sway, spots, spread, fast, embers, fade. DECAY sets how high the flame climbs, COOL (the cooling map's patches) and FADE tear it
# into ragged wisps that die toward the tip. Burning's own look is 32, 40 and 16: a longer, smoother tongue.
FIRE_DECAY, FIRE_COOL, FIRE_FADE = 36, 255, 56
FIRE_FAST, FIRE_EMBERS = 200, 30
OBSTACLE_GAP = 1  # factor on the gap between the Runner's obstacles: the tuning knob (P651), 3 while tuning the flame, 1 is the game's own
FIRE_DRAG_PCT = 5  # % of the world's speed that the heat field scrolls: at 100 the heat is smeared into a flat bar behind the runner


def fire_look(decay):
    return (decay, FIRE_COOL, 1, 0, 1, FIRE_FAST, FIRE_EMBERS, FIRE_FADE)  # sway is on or off in fx_fire.c, so 1


FIRE_START_SPEED, FIRE_FULL_SPEED = 300, 560  # px/s of base speed: no flame below the first, the full short flame from the second
# See-through flame: alpha by heat, a ramp (the soft cutout of burning's FRONT_ALPHA, P639, with other ends): clear below
# FIRE_CLEAR, solid FIRE_ALPHA_MAX from FIRE_SOLID, so the sky shows through the cool edges and only the core is solid.
# The colour by heat is FIRE_STOPS through fire.ramp, as fire.PALETTE is made: orange-red edges (version E, no dark rim) that show against the pale sky
# (burning's BLEND_PALETTE takes every cool heat at one orange-red), orange, yellow, and a small pale core only at the top.
FIRE_STOPS = ((0, 200, 60, 10), (16, 215, 60, 10), (70, 235, 80, 5), (120, 250, 110, 5), (170, 255, 150, 10),
              (225, 255, 190, 50), (255, 255, 235, 150))
FIRE_PALETTE = ramp(FIRE_STOPS)
FIRE_CLEAR, FIRE_SOLID, FIRE_ALPHA_MAX = 30, 150, 235
FIRE_ALPHA = array("B", [0 if heat < FIRE_CLEAR else FIRE_ALPHA_MAX if heat >= FIRE_SOLID else
                         (heat - FIRE_CLEAR) * FIRE_ALPHA_MAX // (FIRE_SOLID - FIRE_CLEAR) for heat in range(256)])
FIRE_RADIUS, FIRE_HEAT, FIRE_LAG, FIRE_SEED = 2, 255, 0.5, 651  # cells of the disc each burn writes, its heat, frames of lag
FIRE_RADIUS_JIT, FIRE_HEAT_JIT = 1, 80  # each frame's burn is up to this much smaller and cooler, at random: the flicker
RUN_BOX = 24  # px: the box around the runner (its hit box height) that its trail burns from
RUN_X = 52  # px: the runner's left edge
# The speed's curve (the PO, 2026-11-06: "the speed should also grow more"). Was 4, 6 (the PO found 12 too fast on
# 2026-11-02) and a knee at 520, so a top near 600; the jump's reach and the gaps both scale with sqrt(base), so it still clears.
SPEED_SLOPE, SPEED_ROOT, SPEED_KNEE = 6, 8, 620
FIRE_STEP_MS = 80  # ms a heat step: 40 (burning's) cost 10 ms a frame in update and sank the Runner to 16 fps (bench.md P651)
FIRE_SOUND_GAIN = 32768  # Q15: the fire loop's gain at the full flame, a choice for the PO's ear (P768)


class Flappy(Game):
    name = "flappy"
    hint = "tap to flap"
    bg = c565(70, 170, 230)
    accent = YELLOW
    X, GAP, PW, SPACE, FLOOR = 80, 84, 32, 130, 222

    BACK = ("flappy_clouds", "flappy_far", "flappy_near")  # the layers behind the pipes; the ground goes over them
    BIRDS = tuple(tuple("flappy_bird%d%d" % (tilt, wing) for wing in range(2)) for tilt in range(3))

    def setup(self):
        self.covers = pictures.load("flappy")  # the painted morning covers the screen, so no fill goes under it
        self.flapped = -1.0  # when the last tap came (self.t), for the bird's wing
        self.y, self.vy, self.dist = 110.0, 0.0, 0.0
        self.pipes = [[W + 20 + i * self.SPACE, self.gap_y(), False] for i in range(3)]
        self.clouds = [[random.randrange(W), random.randrange(30, 110), random.randrange(24, 48)] for _ in range(4)]

    def gap_y(self):
        return random.randrange(64, self.FLOOR - 64)

    def play(self, pressed, held):
        dt = self.dt
        if pressed:
            self.vy, self.flapped = -270.0, self.t
            self.fx.burst(self.X - 8, self.y + 4, WHITE, 3, 40.0, 0.3, 100.0)
        self.vy += 820 * dt
        self.y += self.vy * dt
        speed = 95 + min(self.score, 20) * 3
        self.dist += speed * dt
        for c in self.clouds:
            c[0] -= speed * dt * 0.3
            if c[0] < -60:
                c[0], c[1] = W + 10, random.randrange(30, 110)
        for p in self.pipes:
            p[0] -= speed * dt
            if not p[2] and p[0] + self.PW < self.X - 8:
                p[2] = True
                self.score += 1
                self.pop(self.X, self.y)
        if self.pipes[0][0] < -self.PW - 4:
            self.pipes.pop(0)
            self.pipes.append([self.pipes[-1][0] + self.SPACE, self.gap_y(), False])
        if self.y < 20 or self.y > self.FLOOR - 8:
            self.die(self.X, self.y)
        for x, gap_y, _ in self.pipes:
            if x < self.X + 8 and x + self.PW > self.X - 8 and abs(self.y - gap_y) > self.GAP // 2 - 7:
                self.die(self.X, self.y)

    def pipe(self, cv, x, y, h):
        cv.fill(x, y, self.PW, h, c565(40, 170, 60))
        cv.fill(x + 4, y, 5, h, c565(120, 230, 120))  # light edge
        cv.fill(x + self.PW - 7, y, 7, h, c565(20, 110, 40))  # shadow edge

    def paint_static(self, cv):
        if pictures.draw_layers(cv, 0, False, "flappy"):  # the painted morning sky (P564)
            return
        cv.gradient(0, self.FLOOR, (60, 150, 230), (170, 220, 250), 12)
        cv.fill(0, self.FLOOR, W, 4, c565(120, 220, 60))
        cv.fill(0, self.FLOOR + 4, W, H - self.FLOOR, c565(200, 150, 80))

    def paint(self, cv):
        if self.paint_art(cv):
            return
        for x, y, w in self.clouds:
            cv.fill(x, y, w, 8, WHITE)
            cv.fill(x + 6, y - 5, w - 14, 6, WHITE)
        half = self.GAP // 2
        for x, gap_y, _ in self.pipes:
            self.pipe(cv, x, 16, gap_y - half - 16)
            self.pipe(cv, x, gap_y + half, self.FLOOR - gap_y - half)
            for y in (gap_y - half - 10, gap_y + half):  # the lips
                cv.fill(x - 3, y, self.PW + 6, 10, c565(50, 190, 70))
                cv.fill(x - 3, y, self.PW + 6, 2, c565(140, 240, 140))
        for i in range(12):  # the ground slides by
            cv.fill((i * 32 - int(self.dist)) % (W + 32) - 16, self.FLOOR + 10 + (i % 3) * 5, 14, 3, c565(160, 110, 50))
        flap = 0 if self.vy < 0 else 3
        cv.sprite(BIRD, BIRD_COLOURS, self.X - 9, self.y - 7, 2)
        cv.fill(self.X - 12, self.y - 2 + flap, 6, 3, WHITE)

    def paint_art(self, cv):
        """The painted flappy (P564): the layers behind, each pipe piece placed so its cap meets the gap (the driver
        clips the rest), the ground over the pipe feet, then the bird. False when there is no art."""
        if not pictures.draw_layers(cv, self.dist, True, "flappy", self.BACK):
            return False
        half = self.GAP // 2
        for x, gap_y, _ in self.pipes:
            pictures.draw(cv, "flappy_pipe_top", x, gap_y - half - 240)
            pictures.draw(cv, "flappy_pipe_bottom", x, gap_y + half)
        pictures.draw_layers(cv, self.dist, True, "flappy", ("flappy_ground",))
        tilt = 0 if self.vy < -60 else 2 if self.vy > 120 else 1
        wing = 0 if self.t - self.flapped < 0.12 else int(self.t * 6) % 2  # up just after a tap, then a slow beat
        pictures.draw(cv, self.BIRDS[tilt][wing], self.X - 9, self.y - 7)
        return True


class Runner(Game):
    name = "runner"
    hint = "tap jump, hold higher"
    bg = c565(250, 190, 120)
    accent = ORANGE
    GROUND = 192
    BUFFER = 0.15  # seconds a tap in the air is kept for the landing
    # --- MVP (P768) --- the PO: "steps, jump and fall, collect something, the fire ... as it gets bigger, dying"
    cues = {"jump": Cue("jump"), "land": Cue("land"), "pickup": Cue("pickup"), "footstep": Cue("footstep"),
            "die": Cue("die"), "fire": Cue("fire", FIRE_SOUND_GAIN, True)}

    def __init__(self):
        # --- MVP (P651) --- made once, before Game.__init__ runs setup; the trail only when the field exists
        self.layer = FireLayer(fire_look(FIRE_DECAY), FIRE_SEED, FIRE_STEP_MS, FIRE_ALPHA, FIRE_PALETTE)
        self.trail = None
        if self.layer.field is not None:
            self.trail = FireTrail(self.layer.field, RUN_BOX, FIRE_RADIUS, FIRE_HEAT, FIRE_LAG)
        super().__init__()

    def setup(self):
        self.layer.clear()  # --- MVP (P651) --- each round starts with no fire
        self.fire_decay = self.fire_k = self.fire_heat = 0
        if self.trail is not None:
            self.trail.reset()
            self.grow_fire(0, force=True)
        self.h, self.vy, self.buffer = 0.0, 0.0, 0.0
        self.odo, self.far, self.points = 0.0, 0.0, 0.0  # px the world moved, px at the base speed, and the exact score
        self.track, self.effects = track.Track(), track.Effects()
        self.beat = 0  # the run cycle's frame at the last footstep check (P768)
        self.emit("fire", 0)  # a new round: the last round's fire is silent (P768)
        self.jumped, self.landed = -1.0, -1.0  # when the last jump and the last landing began (self.t), for the pose
        self.covers = pictures.load("runner")  # painted art on the board: its sky covers the screen, so no fill under it

    def grow_fire(self, speed, force=False):
        """The flame at base speed px/s: none below FIRE_START_SPEED, then DECAY and the burns' heat climb evenly to
        their values at FIRE_FULL_SPEED. The look is set again only when the decay steps (at most FIRE_DECAY times in a
        round), so a frame allocates nothing; force sets it anyway (a new round). The burns' heat is play's. --- MVP (P651) ---"""
        k = max(0, min(256, (speed - FIRE_START_SPEED) * 256 // (FIRE_FULL_SPEED - FIRE_START_SPEED)))
        self.fire_k = k
        self.fire_heat = FIRE_HEAT * k // 256  # the burns' heat before the flicker
        decay = FIRE_DECAY * k // 256
        if decay != self.fire_decay or force:
            self.fire_decay = decay
            self.layer.field.set_look(*fire_look(decay))

    def base_speed(self):
        """px/s from the distance run, not the score, so a score bonus does not speed the game up. The same start as
        before, then it keeps growing and levels off softly near 600 (the PO, 2026-11-02: harder patterns from there)."""
        level = self.far / 20
        v = 150 + SPEED_SLOPE * min(level, 40) + SPEED_ROOT * sqrt(max(0.0, level - 40))
        return v if v <= SPEED_KNEE else SPEED_KNEE + 80 * (1 - exp((SPEED_KNEE - v) / 80))

    def play(self, pressed, held):
        dt, base = self.dt, self.base_speed()
        k = max(1.0, sqrt(base / 310))  # quicker jumps at speed, the same heights; from the base, so slow keeps them
        if pressed:  # a tap shortly before landing still jumps
            self.buffer = self.BUFFER
        self.buffer -= dt
        if self.h <= 0 and (held or self.buffer > 0):  # held: jump again at each landing
            self.vy, self.buffer, self.jumped = 420.0 * k, 0.0, self.t
            self.emit("jump")
            self.fx.burst(60, self.GROUND, c565(150, 110, 70), 5, 60.0, 0.4, 200.0)
        if not held and self.vy > 150 * k:  # let go while rising: the jump ends low, so the hold time sets the height
            self.vy = 150 * k
        self.vy -= (560 if held and self.vy > 0 else 1300) * k * k * dt
        was = self.h
        self.h = max(0.0, self.h + self.vy * dt)
        if self.h == 0:
            if was > 0:
                self.fx.burst(60, self.GROUND, c565(150, 110, 70), 5, 60.0, 0.4, 200.0)
                self.landed = self.t
                self.emit("land")
            self.vy = 0.0
            beat = int(self.t * 14) % 6  # the run cycle of pose(): a foot is down at its frames 0 and 3
            if beat != self.beat:
                self.beat = beat
                if beat % 3 == 0 and was <= 0:
                    self.emit("footstep")
        effects = self.effects
        effects.step(dt)
        step = base * max(0.5, effects.factor(track.SLOW)) * dt  # two clocks at once: still at least half speed
        self.odo += step
        self.far += base * dt
        self.points += base * dt / 20 * effects.factor(track.X2, 8)
        self.count()
        dx = self.layer.update(self.ms, int(base * max(0.5, effects.factor(track.SLOW))) * FIRE_DRAG_PCT // 100)  # the fire moves with the world
        if self.trail is not None:  # --- MVP (P651) ---
            self.grow_fire(int(base))
            self.emit("fire", self.fire_k)  # the fire's sound grows with the flame (P768)
            self.trail.scroll(dx)
            if self.fire_k:  # below FIRE_START_SPEED the burn is invisible, so it is skipped
                self.trail.heat = self.fire_heat - random.randrange(FIRE_HEAT_JIT * self.fire_k // 256 + 1)
                self.trail.radius = FIRE_RADIUS - random.randrange(FIRE_RADIUS_JIT + 1)
                self.trail.update(RUN_X - RUN_BOX // 2, int(self.GROUND - self.h) - RUN_BOX)  # burns at the runner's back, x = RUN_X
        tr = self.track
        tr.move(step)
        tr.spawn(self.far / 20, k, OBSTACLE_GAP)
        for t in tr.things:
            if tr.hit(t, step, was, self.h):
                kind = t[1]
                if kind.deadly:
                    self.emit("fire", 0)  # play() does not run after a death, so the loop ends here (P768)
                    self.die(60, self.GROUND - self.h - 12)
                    return  # nothing after death counts
                self.points += kind.points
                self.emit("pickup")
                if kind.effect:
                    effects.add(kind.effect, kind.seconds, kind.mult, kind.colour)
                y = self.GROUND - self.h - 12
                self.fx.burst(60, y, kind.colour, 10, 120.0, 0.5, 100.0)
                self.fx.burst(60, y, WHITE, 6, 60.0, 0.6, -120.0)  # sparkles that rise
                t[0] = -1000.0  # taken: move() drops it
        self.count()

    POSES = tuple("runner_run%d" % i for i in range(6))

    def pose(self):
        """The painted frame for now: a six-frame run cycle by time, a squash just after landing, and in the air
        take-off, rise, top or fall by the time since the jump and the vertical speed."""
        t = self.t
        if self.h <= 0:
            return "runner_land" if t - self.landed < 0.12 else self.POSES[int(t * 14) % 6]
        if t - self.jumped < 0.07:
            return "runner_takeoff"
        k = max(1.0, sqrt(self.base_speed() / 310))
        return "runner_rise" if self.vy > 90 * k else "runner_fall" if self.vy < -90 * k else "runner_apex"

    def count(self):
        """The whole score from the exact one, with a pop each time it passes a ten, even when x2 or a coin skips one."""
        score = int(self.points)
        if score // 10 != self.score // 10:
            self.pop(W - 40, 40)
        self.score = score

    def paint_static(self, cv):
        if pictures.draw_layers(cv, 0, False) or pictures.draw(cv, "bg", 0, 0):  # painted (P562): the still sky, or all of it
            return
        g = self.GROUND
        cv.gradient(16, g, (255, 150, 90), (255, 225, 150), 12)
        cv.disc(250, 70, 22, c565(255, 245, 190))
        for i in range(4):  # mountains
            cv.hill(i * 90 + 20, g, 60, 56 + (i % 2) * 20, c565(150, 90, 100))
        cv.fill(0, g, W, 5, c565(110, 190, 60))
        cv.fill(0, g + 5, W, H - g, c565(130, 80, 40))

    def paint(self, cv):
        g = self.GROUND
        if not pictures.draw_layers(cv, self.odo, True):  # painted layers, each at its own speed (parallax), or the old marks
            for i in range(9):
                cv.fill((i * 44 - int(self.odo)) % (W + 44) - 20, g + 16, 12 + i % 4 * 3, 3, c565(90, 55, 25))
        base = self.base_speed()
        if base > 450:  # speed lines in the sky, more of them the faster it runs
            for i in range(3 if base > 600 else 2):
                cv.fill(W - (int(self.odo * (1.5 + i * 0.4)) + i * 97) % (W + 60), 40 + i * 37, 24 + i * 8, 1, WHITE)
        self.track.paint(cv, g, self.t)
        effects = self.effects.on
        for i, e in enumerate(effects):  # one bar per effect, shrinking with its time left
            cv.fill(6, 19 + i * 5, 4 + int(56 * e[1] / e[3]), 3, e[4])
        top = g - self.h - 24
        if effects:  # a trail behind the runner in the colour of the newest effect
            c = effects[-1][4]
            cv.fill(36, top + 6, 14, 3, c)
            cv.fill(28, top + 13, 20, 3, c)
            cv.fill(40, top + 20, 10, 2, c)
        x2 = self.effects.factor(track.X2, 8)
        i = 0
        while x2 > 1:  # the multiplier as one small box per doubling, next to the bars: no text, which costs ~2.5 ms
            cv.fill(70 + i * 8, 19, 6, 6, track.BONUSES[2].colour)
            x2 //= 2
            i += 1
        self.layer.draw(cv)  # --- MVP (P651) --- the fire behind the runner
        if pictures.draw(cv, self.pose(), 52, top):
            return
        run = int(self.t * 10) % 2  # by time, so the legs do not flicker at speed
        if pictures.draw(cv, ("runner_run0", "runner_run1")[run] if self.h <= 0 else "runner_jump", 52, top):
            return  # the first painted runner, before the six-frame cycle
        leg = RUN_LEGS[run] if self.h <= 0 else RUN_LEGS[1]
        cv.sprite(RUN_TOP + leg, RUN_COLOURS, 52, top, 2)


# FEED's picture names, made once (P573): no formatting while drawing. The head faces each of DIRS in four poses; the
# feed's tiles are its six kinds in a shuffle twelve long, so the feed does not stripe.
FEED_DIRS, FEED_POSES = ("r", "d", "l", "u"), ("open", "gulp", "chew", "glow")
FEED_KINDS = ("photo", "text", "video", "ad", "chart", "selfie")
FEED_ORDER = (0, 3, 5, 1, 4, 2, 3, 0, 5, 2, 1, 4)
HEADS = tuple(tuple("snake_head_%s_%s" % (d, pose) for pose in FEED_POSES) for d in FEED_DIRS)
TILES = tuple("snake_tile_%s" % FEED_KINDS[k] for k in FEED_ORDER)
SEEN = tuple("snake_seen_%d" % k for k in range(3))
DOTS = tuple("snake_dot_%d" % k for k in range(3))
BULGES = tuple("snake_bulge_%d" % k for k in range(2))
RIPPLES = tuple("snake_ripple_%d" % k for k in range(4))
PINGS = tuple("snake_ping_%d" % k for k in range(3))
THUMBS = tuple("snake_thumb_%d" % k for k in range(3))
FEED_DIGITS = tuple("snake_digit_%d" % d for d in range(10))


class Slide:
    """The head's slide from its last cell into its new one: eased out over the first SLIDE_MS of each step, in
    256ths, so it never passes the new cell; across a wrap there is no slide, it is at the new cell. Whole numbers
    only: no float a frame."""

    SLIDE_MS = 60

    @classmethod
    def eased(cls, ms):
        """How far the slide is after ms of the step, 0 to 256: fast at first, slow into the cell."""
        rest = cls.SLIDE_MS - min(ms, cls.SLIDE_MS)
        return 256 - rest * rest * 256 // (cls.SLIDE_MS * cls.SLIDE_MS)

    @staticmethod
    def at(a, b, e, cell):
        """The px from a to b, e 256ths of the way; b itself when they are more than a cell apart (a wrap)."""
        if a - b > cell or b - a > cell:
            return b
        return a + (b - a) * e // 256


class Flip:
    """The death's flip: the head holds its bite for HOLD_MS, then each tile turns over to SEEN, head first,
    STAGGER_MS after the one before it (less when the feed is long, so the last starts by LAST_MS), through its three
    poses, POSE_MS each. The flip takes at most LAST_MS + 2 * POSE_MS, 600 ms, and ends by END_MS, inside the over
    window (Game.OVER_MS, 900)."""

    HOLD_MS, STAGGER_MS, LAST_MS, POSE_MS = 120, 30, 520, 40
    END_MS = HOLD_MS + LAST_MS + 2 * POSE_MS

    @classmethod
    def stagger(cls, n):
        return min(cls.STAGGER_MS, cls.LAST_MS // max(1, n - 1))

    @classmethod
    def pose(cls, i, n, ms):
        """Tile i's pose of the flip after ms, for a feed n long: -1 not yet turned, else 0, 1 or 2 (SEEN)."""
        t = ms - cls.HOLD_MS - i * cls.stagger(n)
        return -1 if t < 0 else min(2, t // cls.POSE_MS)


class Meals:
    """The dots the feed has eaten: each goes down the feed as a bulge, one tile a step, and the last one ripples the
    glass where it was eaten, ring by ring."""

    RIPPLE, RIPPLE_MS, ALPHAS = 48, 70, (230, 180, 120, 64)  # art/sets/snake.py's ripple and its rings' alphas

    def __init__(self):
        self.steps = []  # the step of each meal still going down the feed
        self.at, self.x, self.y = None, 0, 0  # ms of the last meal, and the middle of its cell

    def eaten(self, step, ms, x, y):
        self.steps.append(step)
        self.at, self.x, self.y = ms, x, y

    def stepped(self, step, n):
        """The feed took step and is n long: a bulge past its tail is gone."""
        if self.steps and step - self.steps[0] >= n:
            self.steps.pop(0)

    def draw(self, cv, game, e):
        """The bulges on the feed's tiles (next to the head only once the head has slid off it, e at 256), then the
        last meal's ripple."""
        body, n = game.body, len(game.body)
        for meal in self.steps:
            i = game.steps - meal
            if 0 < i < n and (i > 1 or e == 256):
                pictures.draw(cv, BULGES[i % 2], game.x_of(body[i]) - 2, game.y_of(body[i]) - 2)
        if self.at is not None:
            k = time.ticks_diff(game.last, self.at) // self.RIPPLE_MS
            if k < 4:
                half = self.RIPPLE // 2
                pictures.draw(cv, RIPPLES[k], self.x - half, self.y - half, self.ALPHAS[k])


class StatusBar:
    """FEED's score bar is the phone's status bar: 10:00, the notch with its camera and the live count beside a red
    dot, the best, the signal and a battery that drains as the feed grows. It fills HUD_RECT, so it is drawn by fills
    and text only (lcd.Strip)."""

    BAR, BONE = c565(26, 28, 40), c565(240, 232, 214)
    CHARGE = 18  # px of a full battery; 1 less for each CHARGE_POINTS points, never under 1
    CHARGE_POINTS, LOW = 2, 5

    @classmethod
    def draw(cls, cv, score, best):
        cv.fill(0, 0, WIDTH, 16, cls.BAR)
        cv.text("10:00", 10, 4, cls.BONE)
        cv.fill(112, 0, 96, 13, BLACK)  # the notch, its bottom corners rounded
        cv.fill(114, 13, 92, 1, BLACK)
        cv.fill(117, 14, 86, 1, BLACK)
        cv.fill(121, 4, 5, 5, c565(30, 36, 60))  # the camera's lens
        cv.fill(122, 5, 2, 2, c565(90, 110, 170))
        cv.fill(134, 4, 5, 5, ACCENT)
        cv.text(str(score), 143, 3, cls.BONE)
        best = "best %d" % best
        cv.text(best, 254 - 8 * len(best), 4, GREY)
        for k in range(4):  # the signal
            cv.fill(262 + k * 3, 10 - k * 2, 2, 2 + k * 2, cls.BONE)
        cv.box(280, 4, 22, 9, cls.BONE)  # the battery, its pip and its charge
        cv.fill(302, 6, 2, 5, cls.BONE)
        charge = cls.charge(score)
        cv.fill(282, 6, charge, 5, cls.BONE if charge > cls.LOW else ACCENT)

    @classmethod
    def charge(cls, score):
        return max(1, cls.CHARGE - score // cls.CHARGE_POINTS)


class Snake(Game):
    """FEED (P573): an endless feed of phone-screen tiles crawls over the glass and grows by eating red notification
    dots; you are eaten by your own feed. A tap turns it right. The head slides into each cell, gulps the dot and
    chews it, the dot goes down the feed as a bulge, and the glass ripples. When the feed meets itself every tile
    turns over to a grey SEEN, head to tail, and the card says YOU SAW n. YOU REMEMBER 0. Watercolour noir at
    10:00: the street mirrored in the glass, six hues for the feed, and one accent, the dot."""

    name = "snake"
    hint = "tap turns right"
    bg = c565(14, 34, 22)
    accent = GREEN
    BONE = StatusBar.BONE  # art/sets/snake.py's
    cues = {"eat": Cue("pickup"), "turn": Cue("footstep"), "die": Cue("die")}
    CELL, COLS, ROWS, TOP = 12, 26, 18, 21
    LEFT = 4
    DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))

    # --- the painted look: art/sets/snake.py's sizes, which the board has no art/ to read (tests/test_paint.py pins
    # them), and the feel's numbers, set by eye on Mac frames of tools/render_scene.py
    HEAD, HALO, BULGE, THUMB_W = 16, 36, 16, 32
    HALO_ALPHA, HALO_NEAR_ALPHA = 70, 120  # the head's glow; brighter when a dot is near
    RIPPLE, RIPPLE_ALPHAS = Meals.RIPPLE, Meals.ALPHAS
    DOT_MS, NEAR = 160, 2  # a pulse pose's time, the cells at which the head glows
    PING, PING_MS, PING_RING_MS, PING_ALPHAS = 28, 1200, 80, (200, 130, 70)  # the dot calls once each PING_MS
    DOT_PULSE = (0, 1, 2, 1)
    SPARKS = 6  # the bone sparks of a meal, on the game's own Dice
    CARD_MS = Flip.END_MS + 40  # the card, once the flip is over
    CARD_X, CARD_Y, CARD_RIGHT, CARD_TOP = 60, 70, 219, 85  # snake_over, and its plate's right end and top, for n
    TITLE_BEST_RIGHT, TITLE_BEST_TOP, DIGIT_W = 201, 131, 8
    OPEN, GULP, CHEW, GLOW = range(4)

    def setup(self):
        self.body = [(12, 9), (11, 9), (10, 9)]
        self.d, self.acc = 0, 0.0
        self.food = self.spot()
        self.covers = pictures.load(self.name)  # the painted glass covers the screen, so no fill goes under it
        self.made = 3  # tiles made so far: tile i of the body is number made - i, so its kind stays as it crawls
        self.steps = 0  # the steps taken
        self.ate_step = -9  # the step of the last meal, for the gulp and the chew
        self.gone = None  # the cell the tail left in the last step, for its slide out
        self.meals = Meals()
        self.dice = Dice(5731)  # the effects' own random stream: the rules' draws stay as they are
        self.glints = Particles()  # the meals' bone sparks, apart from the rules' pops in fx

    def spot(self):
        for _ in range(60):
            c = (random.randrange(self.COLS), random.randrange(self.ROWS))
            if c not in self.body:
                return c
        return (0, 0)

    def play(self, pressed, held):
        if pressed:
            self.d = (self.d + 1) % 4
            self.emit("turn")
        self.acc += self.dt * 1000
        period = max(70, 160 - self.score * 4)
        if self.acc < period:
            return
        self.acc -= period
        dx, dy = self.DIRS[self.d]
        nxt = ((self.body[0][0] + dx) % self.COLS, (self.body[0][1] + dy) % self.ROWS)
        if nxt in self.body[:-1]:
            return self.die(*self.centre(nxt), (ACCENT, self.BONE))
        self.body.insert(0, nxt)
        self.made += 1
        self.steps += 1
        self.meals.stepped(self.steps, len(self.body))
        if nxt == self.food:
            self.score += 1
            self.pop(*self.centre(nxt), ACCENT)
            self.food = self.spot()
            self.ate(nxt)
        else:
            self.gone = self.body.pop()

    def ate(self, cell):
        """A meal at cell: the sound, the gulp, the bulge down the feed, the ripple and the bone sparks."""
        self.emit("eat")
        self.ate_step, self.gone = self.steps, None
        x, y = self.centre(cell)
        self.meals.eaten(self.steps, self.last, x, y)
        dice = self.dice
        for _ in range(self.SPARKS):
            self.glints.add(x + dice.spread(4), y + dice.spread(4), dice.spread(70), -40 - dice.below(90), self.BONE,
                        0.3 + dice.below(30) / 100, 120.0)

    def centre(self, cell):
        return 4 + cell[0] * self.CELL + 6, self.TOP + cell[1] * self.CELL + 6

    def step(self, now_ms, pressed, held):
        """Game.step; then the meals' sparks fly."""
        super().step(now_ms, pressed, held)
        if self.glints.p:
            self.glints.update(self.dt)

    def over_ms(self):
        """ms since the feed met itself: age is read before the frame's play, so in the frame of the loss it is still
        play's."""
        return time.ticks_diff(self.last, self.since)

    def eased(self):
        """How far the head has slid into its cell, 0 to 256: by the ms of this step, all the way when over."""
        return 256 if self.state == OVER else Slide.eased(int(self.acc))

    def x_of(self, cell):
        return self.LEFT + cell[0] * self.CELL

    def y_of(self, cell):
        return self.TOP + cell[1] * self.CELL

    def head_pose(self):
        """Gulp in the step of a meal, chew in the next, glow when a dot is within NEAR cells, else open."""
        since = self.steps - self.ate_step
        if since == 0:
            return self.GULP
        if since == 1:
            return self.CHEW
        (hx, hy), (fx, fy) = self.body[0], self.food
        return self.GLOW if abs(hx - fx) + abs(hy - fy) <= self.NEAR else self.OPEN

    def paint_static(self, cv):
        if pictures.draw(cv, "snake_morning", 0, 0):  # the painted glass (P573)
            return
        n, left = self.CELL, 4
        for i in range(0, self.COLS, 2):  # a stripe lawn
            cv.fill(left + i * n, self.TOP, n, self.ROWS * n, c565(20, 48, 30))
        cv.box(left - 2, self.TOP - 2, self.COLS * n + 4, self.ROWS * n + 4, GREY)

    def paint(self, cv):
        """The dot, the tail's tile sliding out, the feed (turning over to SEEN when over), the bulges going down it,
        the ripple of the last meal, the head in its glow sliding into its cell, and the meals' sparks."""
        if not (self.covers and getattr(cv, "pictures", False)):
            return self.paint_flat(cv)
        body, n, over = self.body, len(self.body), self.state == OVER
        ms = self.over_ms() if over else 0
        e = self.eased()
        if not over:
            self.draw_dot(cv)
            self.draw_tail(cv, e)
        for i in range(1, n):
            k = Flip.pose(i, n, ms) if over else -1
            pictures.draw(cv, TILES[(self.made - i) % 12] if k < 0 else SEEN[k], self.x_of(body[i]), self.y_of(body[i]))
        if not over:
            self.meals.draw(cv, self, e)
        self.draw_head(cv, e, Flip.pose(0, n, ms) if over else -1)
        self.glints.draw(cv)

    def draw_dot(self, cv):
        """The red dot, pulsing, and now and then its ping, a red ring spreading from it."""
        x, y = self.x_of(self.food), self.y_of(self.food)
        k = self.last % self.PING_MS // self.PING_RING_MS
        if k < 3:
            pictures.draw(cv, PINGS[k], x + 6 - self.PING // 2, y + 6 - self.PING // 2, self.PING_ALPHAS[k])
        pictures.draw(cv, DOTS[self.DOT_PULSE[self.last // self.DOT_MS % 4]], x, y)

    def draw_tail(self, cv, e):
        """The tile the tail left, sliding into the tail's cell under it while the head slides, then gone."""
        gone = self.gone
        if gone is None or e == 256:
            return
        tail, n, cell = self.body[-1], len(self.body), self.CELL
        pictures.draw(cv, TILES[(self.made - n) % 12], Slide.at(self.x_of(gone), self.x_of(tail), e, cell),
                      Slide.at(self.y_of(gone), self.y_of(tail), e, cell))

    def draw_head(self, cv, e, flip):
        """The head slid e 256ths from its last cell into its new one, in its glow; or its pose of the flip."""
        body, cell = self.body, self.CELL
        x = Slide.at(self.x_of(body[1]), self.x_of(body[0]), e, cell)
        y = Slide.at(self.y_of(body[1]), self.y_of(body[0]), e, cell)
        if flip >= 0:
            return pictures.draw(cv, SEEN[flip], x, y)
        pose = self.CHEW if self.state == OVER else self.head_pose()  # over: biting its own tile
        pictures.draw(cv, "snake_halo", x + 6 - self.HALO // 2, y + 6 - self.HALO // 2,
                      self.HALO_NEAR_ALPHA if pose == self.GLOW else self.HALO_ALPHA)
        pictures.draw(cv, HEADS[self.d][pose], x - 2, y - 2)

    def paint_flat(self, cv):
        """The look before FEED, where there is no art: a lawn, an apple, a green snake with a yellow head."""
        n, left = self.CELL, 4
        fx, fy = self.food
        x, y = left + fx * n, self.TOP + fy * n
        cv.fill(x + 2, y + 3, n - 4, n - 5, RED)
        cv.fill(x + 3, y + 4, 3, 3, c565(255, 150, 150))  # shine
        cv.fill(x + 5, y, 3, 3, GREEN)  # leaf
        last = len(self.body) - 1
        for i, (bx, by) in enumerate(self.body):
            colour = YELLOW if i == 0 else c565(40, 200, 80) if i % 2 else c565(30, 160, 60)
            if i == last and last > 2:
                colour = c565(20, 110, 40)
            cv.fill(left + bx * n + 1, self.TOP + by * n + 1, n - 2, n - 2, colour)
        hx, hy = self.body[0]
        dx, dy = self.DIRS[self.d]  # two eyes on the side the head faces
        ex, ey = left + hx * n + 6 + dx * 3, self.TOP + hy * n + 6 + dy * 3
        cv.fill(ex - 3 * abs(dy) - 1, ey - 3 * abs(dx) - 1, 3, 3, BLACK)
        cv.fill(ex + 3 * abs(dy) - 1, ey + 3 * abs(dx) - 1, 3, 3, BLACK)

    def draw_hud(self, cv):
        """The phone's status bar (StatusBar), drawn again only when the score or the best change."""
        if not self.covers:
            return Game.draw_hud(self, cv)
        StatusBar.draw(cv, self.score, max(self.score, BEST.get(self.name, 0)))

    def number(self, cv, value, right, top):
        """value in digit pictures, right-aligned at right, the last digit first."""
        x, rest = right, value
        while True:
            x -= self.DIGIT_W
            pictures.draw(cv, FEED_DIGITS[rest % 10], x, top)
            rest //= 10
            if not rest:
                return

    def draw_title(self, cv):
        """FEED: the title card; the feed scrolls up the glass under the words, three columns of tiles, and the thumb
        flicks it; the best on its plate."""
        if not pictures.draw(cv, "snake_title", 0, 0):
            return Game.draw_title(self, cv)
        a, cell = self.age, self.CELL
        rise = a * 60 // 1000  # px the feed has scrolled up
        for col in range(3):
            x = 124 + col * 26
            for row in range(7):
                y = 236 - row * 14 - (rise + col * 5) % 14
                if 150 <= y <= 224:
                    pictures.draw(cv, TILES[(row + col * 5 + rise // 14) % 12], x, y)
        pictures.draw(cv, THUMBS[a // 120 % 3], 168, 196)  # on the right column, flicking it
        self.number(cv, BEST.get(self.name, 0), self.TITLE_BEST_RIGHT, self.TITLE_BEST_TOP)

    def draw_over(self, cv):
        """The flip plays over the live scene first; then YOU SAW n. YOU REMEMBER 0."""
        if self.over_ms() < self.CARD_MS:
            return
        if not pictures.draw(cv, "snake_over", self.CARD_X, self.CARD_Y):
            return Game.draw_over(self, cv)
        self.number(cv, self.score, self.CARD_RIGHT, self.CARD_TOP)
        if self.age >= self.OVER_MS and (self.age // 400) % 2 == 0:
            cv.text("tap to retry", self.CARD_X + 52, self.CARD_Y + 84, self.BONE)
