"""Three side-on games for one button: flappy (tap), runner (tap, hold for a high jump), snake (tap turns right)."""

import random
from math import exp, sqrt

import pictures
import track
from effects import FireTrail
from fire import FireLayer
from gfx import (BLACK, GREEN, GREY, HEIGHT, ORANGE, RED, WHITE, WIDTH, YELLOW, Game, c565)

W, H = WIDTH, HEIGHT
BIRD = ("..kkkk...", ".kyyyywk.", "kyyyyywkk", "kkkyyyyoo", "kwwkyyyok", ".kwwkkkk.", "..kkk....")
BIRD_COLOURS = {"k": c565(40, 30, 20), "y": YELLOW, "w": WHITE, "o": ORANGE}
RUN_TOP = ("..rrrr..", ".rrrrrr.", ".ssskss.", ".ssssss.", "..bbbb..", ".bbbbbb.", "sbbbbbbs", ".bbbbbb.", "..pppp..", "..pppp..")
RUN_LEGS = (("..p..p..", ".kk..kk."), ("...pp...", "...kk..."))
RUN_COLOURS = {"r": RED, "s": c565(250, 200, 160), "k": BLACK, "b": c565(50, 90, 240), "p": c565(40, 40, 120)}
# --- MVP (P651) --- the runner's fire: the numbers start as the burning scene's and the flappy's (P607, P602), to tune on the panel
FIRE_LOOK = (32, 40, 1, 0, 1, 128, 0, 16)  # fx_fire_set_look's decay, cool, sway, spots, spread, fast, embers, fade
FIRE_RADIUS, FIRE_HEAT, FIRE_LAG, FIRE_SEED = 3, 200, 0.5, 651  # cells of the disc each burn writes, its heat, frames of lag
RUN_BOX = 24  # px: the box around the runner (its hit box height) that its trail burns from
RUN_X = 52  # px: the runner's left edge
FIRE_STEP_MS = 80  # ms a heat step: 40 (burning's) cost 10 ms a frame in update and sank the Runner to 16 fps (bench.md P651)


class Flappy(Game):
    name = "flappy"
    hint = "tap to flap"
    bg = c565(70, 170, 230)
    accent = YELLOW
    X, GAP, PW, SPACE, FLOOR = 80, 84, 32, 130, 222

    BACK = ("flappy_clouds", "flappy_far", "flappy_near")  # the layers behind the pipes; the ground goes over them
    BIRDS = tuple(tuple("flappy_bird%d%d" % (tilt, wing) for wing in range(2)) for tilt in range(3))

    def setup(self):
        self.covers = pictures.load()  # the painted morning covers the screen, so no fill goes under it
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

    def __init__(self):
        # --- MVP (P651) --- made once, before Game.__init__ runs setup; the trail only when the field exists
        self.layer = FireLayer(FIRE_LOOK, FIRE_SEED, FIRE_STEP_MS)
        self.trail = None
        if self.layer.field is not None:
            self.trail = FireTrail(self.layer.field, RUN_BOX, FIRE_RADIUS, FIRE_HEAT, FIRE_LAG)
        super().__init__()

    def setup(self):
        self.layer.clear()  # --- MVP (P651) --- each round starts with no fire
        if self.trail is not None:
            self.trail.reset()
        self.h, self.vy, self.buffer = 0.0, 0.0, 0.0
        self.odo, self.far, self.points = 0.0, 0.0, 0.0  # px the world moved, px at the base speed, and the exact score
        self.track, self.effects = track.Track(), track.Effects()
        self.jumped, self.landed = -1.0, -1.0  # when the last jump and the last landing began (self.t), for the pose
        self.covers = pictures.load()  # painted art on the board: its sky covers the screen, so no fill goes under it

    def base_speed(self):
        """px/s from the distance run, not the score, so a score bonus does not speed the game up. The same start as
        before, then it keeps growing and levels off softly near 600 (the PO, 2026-11-02: harder patterns from there)."""
        level = self.far / 20
        v = 150 + 4 * min(level, 40) + 6 * sqrt(max(0.0, level - 40))  # 6: the PO found 12 too fast (2026-11-02)
        return v if v <= 520 else 520 + 80 * (1 - exp((520 - v) / 80))

    def play(self, pressed, held):
        dt, base = self.dt, self.base_speed()
        k = max(1.0, sqrt(base / 310))  # quicker jumps at speed, the same heights; from the base, so slow keeps them
        if pressed:  # a tap shortly before landing still jumps
            self.buffer = self.BUFFER
        self.buffer -= dt
        if self.h <= 0 and (held or self.buffer > 0):  # held: jump again at each landing
            self.vy, self.buffer, self.jumped = 420.0 * k, 0.0, self.t
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
            self.vy = 0.0
        effects = self.effects
        effects.step(dt)
        step = base * max(0.5, effects.factor(track.SLOW)) * dt  # two clocks at once: still at least half speed
        self.odo += step
        self.far += base * dt
        self.points += base * dt / 20 * effects.factor(track.X2, 8)
        self.count()
        dx = self.layer.update(self.ms, int(base * max(0.5, effects.factor(track.SLOW))))  # --- MVP (P651) --- the fire moves with the world
        if self.trail is not None:
            self.trail.scroll(dx)
            self.trail.update(RUN_X, int(self.GROUND - self.h) - RUN_BOX)
        tr = self.track
        tr.move(step)
        tr.spawn(self.far / 20, k)
        for t in tr.things:
            if tr.hit(t, step, was, self.h):
                kind = t[1]
                if kind.deadly:
                    self.die(60, self.GROUND - self.h - 12)
                    return  # nothing after death counts
                self.points += kind.points
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


class Snake(Game):
    name = "snake"
    hint = "tap turns right"
    bg = c565(14, 34, 22)
    accent = GREEN
    CELL, COLS, ROWS, TOP = 12, 26, 18, 21
    DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))

    def setup(self):
        self.body = [(12, 9), (11, 9), (10, 9)]
        self.d, self.acc = 0, 0.0
        self.food = self.spot()

    def spot(self):
        for _ in range(60):
            c = (random.randrange(self.COLS), random.randrange(self.ROWS))
            if c not in self.body:
                return c
        return (0, 0)

    def play(self, pressed, held):
        if pressed:
            self.d = (self.d + 1) % 4
        self.acc += self.dt * 1000
        period = max(70, 160 - self.score * 4)
        if self.acc < period:
            return
        self.acc -= period
        dx, dy = self.DIRS[self.d]
        nxt = ((self.body[0][0] + dx) % self.COLS, (self.body[0][1] + dy) % self.ROWS)
        if nxt in self.body[:-1]:
            return self.die(*self.centre(nxt))
        self.body.insert(0, nxt)
        if nxt == self.food:
            self.score += 1
            self.pop(*self.centre(nxt), RED)
            self.food = self.spot()
        else:
            self.body.pop()

    def centre(self, cell):
        return 4 + cell[0] * self.CELL + 6, self.TOP + cell[1] * self.CELL + 6

    def paint_static(self, cv):
        n, left = self.CELL, 4
        for i in range(0, self.COLS, 2):  # a stripe lawn
            cv.fill(left + i * n, self.TOP, n, self.ROWS * n, c565(20, 48, 30))
        cv.box(left - 2, self.TOP - 2, self.COLS * n + 4, self.ROWS * n + 4, GREY)

    def paint(self, cv):
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
