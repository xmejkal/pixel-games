"""Three side-on games for one button: flappy (tap), runner (tap, hold for a high jump), snake (tap turns right)."""

import random

from gfx import (BLACK, GREEN, GREY, HEIGHT, ORANGE, RED, WHITE, WIDTH, YELLOW, Game, c565)

W, H = WIDTH, HEIGHT
BIRD = ("..kkkk...", ".kyyyywk.", "kyyyyywkk", "kkkyyyyoo", "kwwkyyyok", ".kwwkkkk.", "..kkk....")
BIRD_COLOURS = {"k": c565(40, 30, 20), "y": YELLOW, "w": WHITE, "o": ORANGE}
RUN_TOP = ("..rrrr..", ".rrrrrr.", ".ssskss.", ".ssssss.", "..bbbb..", ".bbbbbb.", "sbbbbbbs", ".bbbbbb.", "..pppp..", "..pppp..")
RUN_LEGS = (("..p..p..", ".kk..kk."), ("...pp...", "...kk..."))
RUN_COLOURS = {"r": RED, "s": c565(250, 200, 160), "k": BLACK, "b": c565(50, 90, 240), "p": c565(40, 40, 120)}


class Flappy(Game):
    name = "flappy"
    hint = "tap to flap"
    bg = c565(70, 170, 230)
    accent = YELLOW
    X, GAP, PW, SPACE, FLOOR = 80, 84, 32, 130, 222

    def setup(self):
        self.y, self.vy, self.dist = 110.0, 0.0, 0.0
        self.pipes = [[W + 20 + i * self.SPACE, self.gap_y(), False] for i in range(3)]
        self.clouds = [[random.randrange(W), random.randrange(30, 110), random.randrange(24, 48)] for _ in range(4)]

    def gap_y(self):
        return random.randrange(64, self.FLOOR - 64)

    def play(self, pressed, held):
        dt = self.dt
        if pressed:
            self.vy = -270.0
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
        cv.gradient(0, self.FLOOR, (60, 150, 230), (170, 220, 250), 12)
        cv.fill(0, self.FLOOR, W, 4, c565(120, 220, 60))
        cv.fill(0, self.FLOOR + 4, W, H - self.FLOOR, c565(200, 150, 80))

    def paint(self, cv):
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


class Runner(Game):
    name = "runner"
    hint = "tap jump, hold higher"
    bg = c565(250, 190, 120)
    accent = ORANGE
    GROUND = 192
    BUFFER = 0.15  # seconds a tap in the air is kept for the landing

    def setup(self):
        self.h, self.vy, self.odo, self.buffer = 0.0, 0.0, 0.0, 0.0
        self.obs = [[W + 20.0, 16, 30]]
        self.next = 220

    def play(self, pressed, held):
        dt = self.dt
        if pressed:  # a tap shortly before landing still jumps
            self.buffer = self.BUFFER
        self.buffer -= dt
        if self.h <= 0 and (held or self.buffer > 0):  # held: jump again at each landing
            self.vy, self.buffer = 420.0, 0.0
            self.fx.burst(60, self.GROUND, c565(150, 110, 70), 5, 60.0, 0.4, 200.0)
        self.vy -= (700 if held and self.vy > 0 else 1300) * dt
        was = self.h
        self.h = max(0.0, self.h + self.vy * dt)
        if self.h == 0:
            if was > 0:
                self.fx.burst(60, self.GROUND, c565(150, 110, 70), 5, 60.0, 0.4, 200.0)
            self.vy = 0.0
        speed = 150 + min(self.score, 40) * 4
        self.odo += speed * dt
        score = int(self.odo / 20)
        if score != self.score and score % 10 == 0:
            self.pop(W - 40, 40)
        self.score = score
        for o in self.obs:
            o[0] -= speed * dt
        if self.obs[0][0] + self.obs[0][1] < -10:
            self.obs.pop(0)
        if not self.obs or self.obs[-1][0] < W - self.next:
            self.obs.append([W + 10.0, random.randrange(14, 26), random.randrange(16, 64)])
            self.next = random.randrange(180, 300)
        for x, w, h in self.obs:
            if x < 66 and x + w > 52 and self.h < h - 2:
                self.die(60, self.GROUND - self.h - 12)

    def paint_static(self, cv):
        g = self.GROUND
        cv.gradient(16, g, (255, 150, 90), (255, 225, 150), 12)
        cv.disc(250, 70, 22, c565(255, 245, 190))
        for i in range(4):  # mountains
            cv.hill(i * 90 + 20, g, 60, 56 + (i % 2) * 20, c565(150, 90, 100))
        cv.fill(0, g, W, 5, c565(110, 190, 60))
        cv.fill(0, g + 5, W, H - g, c565(130, 80, 40))

    def paint(self, cv):
        g = self.GROUND
        for i in range(9):
            cv.fill((i * 44 - int(self.odo)) % (W + 44) - 20, g + 16, 12 + i % 4 * 3, 3, c565(90, 55, 25))
        green, dark = GREEN, c565(20, 120, 40)
        for x, w, h in self.obs:  # a cactus with two arms
            cv.fill(x + w // 3, g - h, w // 3 + 2, h, green)
            cv.fill(x, g - h * 2 // 3, w // 3 + 1, 5, green)
            cv.fill(x, g - h * 2 // 3 - 8, 5, 10, green)
            cv.fill(x + w * 2 // 3, g - h // 2, w // 3 + 1, 5, green)
            cv.fill(x + w - 5, g - h // 2 - 8, 5, 10, green)
            cv.fill(x + w // 3 + 3, g - h, 2, h, dark)
        top = g - self.h - 24
        leg = RUN_LEGS[int(self.odo / 14) % 2] if self.h <= 0 else RUN_LEGS[1]
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
