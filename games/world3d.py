"""Two 3D games for one button: tunnel (wireframe rings, tap turns the ship) and road (horizon road, tap changes lane)."""

import math
import random

from gfx import BLACK, CYAN, HEIGHT, ORANGE, RED, WHITE, WIDTH, YELLOW, Game, c565, shade

W, H = WIDTH, HEIGHT


class Tunnel(Game):
    name = "tunnel"
    hint = "tap turns the ship"
    bg = c565(4, 4, 18)
    accent = CYAN
    F, CX, CY, HX, HY, NEAR, FAR, SPACE = 150, W // 2, 130, 0.7, 0.5, 1.0, 10.0, 2.6
    AREA = (40, 40, 280, 220)  # the picture lives here; the frame around it is drawn once

    def setup(self):
        self.side, self.speed, self.run = 0, 2.6, 0.0
        self.rings = [[5.0, random.randrange(4)], [7.6, random.randrange(4)]]  # [depth, side with the gap]

    def play(self, pressed, held):
        if pressed:
            self.side = (self.side + 1) % 4
        self.run += self.speed * self.dt
        for r in self.rings:
            r[0] -= self.speed * self.dt
        if self.rings[0][0] < self.NEAR:
            sx, sy = self.ship()
            if self.rings[0][1] != self.side:
                return self.die(sx, sy)
            self.rings.pop(0)
            self.score += 1
            self.pop(sx, sy, CYAN)
            self.speed = min(5.4, self.speed + 0.07)
        if self.rings[-1][0] <= self.FAR - self.SPACE:
            self.rings.append([self.FAR, random.randrange(4)])
        sx, sy = self.ship()  # a thin trail of sparks behind the ship
        self.fx.add(sx, sy, random.randrange(-20, 21), random.randrange(-20, 21), YELLOW, 0.3)

    def ship(self):
        k = self.F / 1.3
        sx, sy = ((0, -self.HY), (self.HX, 0), (0, self.HY), (-self.HX, 0))[self.side]
        return self.CX + sx * k, self.CY + sy * k

    def corners(self, z):
        k, hx, hy = self.F / z, self.HX, self.HY
        return [(self.CX + x * k, self.CY + y * k) for x, y in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]

    def ring(self, cv, z, colour, gap=-1, thick=False):
        c = self.corners(z)
        for i in range(4):
            a, b = c[i], c[(i + 1) % 4]
            if i == gap:  # the opening shows as a faint green line
                cv.line(a[0], a[1], b[0], b[1], c565(0, 90, 40))
                continue
            cv.line(a[0], a[1], b[0], b[1], colour)
            if thick:
                cv.line(a[0], a[1] + 1, b[0], b[1] + 1, colour)
                cv.line(a[0] + 1, a[1], b[0] + 1, b[1], colour)

    def paint_static(self, cv):
        cv.clip = self.AREA
        far, near = self.corners(self.FAR), self.corners(self.NEAR)
        for a, b in zip(far, near):  # the four edges running away to the middle
            cv.line(a[0], a[1], b[0], b[1], c565(40, 50, 120))
        cv.clip = (0, 0, W, H)
        cv.box(39, 39, 242, 182, c565(60, 60, 110))

    def paint(self, cv):
        cv.clip = self.AREA
        step = 1.0  # dim rings rush past and give the speed
        z = self.NEAR + step - (self.run % step)
        while z < self.FAR:
            self.ring(cv, z, shade(50, 80, 200, 1.3 - z / self.FAR))
            z += step
        for z, gap in reversed(self.rings):
            self.ring(cv, z, shade(255, 100, 60, 1.4 - z / self.FAR), gap, z < 4)
        sx, sy = self.ship()  # the ship points into the tunnel
        cv.line(sx - 12, sy + 8, sx, sy - 12, YELLOW)
        cv.line(sx + 12, sy + 8, sx, sy - 12, YELLOW)
        cv.line(sx - 12, sy + 8, sx + 12, sy + 8, YELLOW)
        cv.fill(sx - 3, sy - 3, 6, 6, WHITE)


class Road(Game):
    name = "road"
    hint = "tap lane, hold boost"
    bg = c565(90, 170, 250)
    accent = ORANGE
    HOR, K, SEG, PY, TP = 88, 40.0, 4, 218, 130
    AREA = (40, 20, 280, 232)  # horizon row, depth scale, band height, player row, its depth row

    def setup(self):
        self.lane, self.dir, self.lx = 1, 1, 0.0  # lane index 0..2, direction of the next change, lane drawn at
        self.odo, self.obs, self.gapd, self.sway = 0.0, [], 6.0, 0.0

    def play(self, pressed, held):
        if pressed:
            self.lane += self.dir
            if self.lane in (0, 2):
                self.dir = -self.dir
        self.lx += (self.lane - 1 - self.lx) * min(1.0, self.dt * 12)
        v = 6.5 + min(self.score, 40) * 0.08
        v *= 1.7 if held else 1.0
        self.odo += v * self.dt
        score = int(self.odo / 4)
        if score != self.score and score % 10 == 0:
            self.pop(W - 40, 40)
        self.score = score
        d0 = self.K / self.TP
        for o in self.obs:
            before = o[0]
            o[0] -= v * self.dt
            if before > d0 >= o[0] and o[1] == self.lane - 1:
                self.die(*self.player_at())
        if self.obs and self.obs[0][0] < 0.1:
            self.obs.pop(0)
        if not self.obs or self.obs[-1][0] < 22 - self.gapd:
            self.obs.append([22.0, random.randrange(-1, 2)])
            self.gapd = random.randrange(5, 10)
        if held:
            self.fx.add(self.player_at()[0], self.PY, random.randrange(-30, 31), 90, ORANGE, 0.25)

    def player_at(self):
        return self.road_x(self.lx, self.TP), self.PY - 10

    def half(self, t):
        return t * 0.8 + 3

    def bend(self, t):
        return self.sway * ((144 - t) / 144) ** 2

    def road_x(self, lane, t):
        return W // 2 + self.bend(t) + lane * self.half(t) * 0.55

    def paint_static(self, cv):
        hor = self.HOR
        cv.clip = self.AREA
        cv.gradient(20, hor, (60, 130, 240), (255, 200, 150), 10)
        cv.disc(240, hor - 22, 14, c565(255, 235, 120))
        for x, hgt in ((30, 34), (110, 24), (190, 40), (290, 28)):  # blue mountains on the horizon
            cv.hill(x, hor, 50, hgt, c565(70, 90, 150))
        cv.clip = (0, 0, W, H)
        cv.box(39, 19, 242, 214, c565(60, 60, 110))

    def paint(self, cv):
        hor, seg = self.HOR, self.SEG
        self.sway = math.sin(self.odo * 0.25) * 45  # once per frame
        cv.clip = self.AREA
        for y in range(hor, 232, seg):
            t = y + seg / 2 - hor
            stripe = int(self.K / t + self.odo) % 2
            hw = self.half(t)
            cx = W // 2 + self.bend(t)
            cv.fill(0, y, W, seg, c565(30, 150, 50) if stripe else c565(20, 120, 40))
            cv.fill(cx - hw - 7, y, 2 * hw + 14, seg, RED if stripe else WHITE)  # rumble strips
            cv.fill(cx - hw, y, 2 * hw, seg, c565(70, 70, 80) if stripe else c565(85, 85, 95))
            if stripe:
                for lane in (-0.275, 0.275):  # lane dashes
                    cv.fill(cx + lane * hw * 2 - 1, y, 2 + t * 0.012, seg, WHITE)
        for k in range(10, 0, -1):  # trees on both sides slide past
            d = k * 2 - (self.odo % 2)
            t = self.K / d
            if t > H - self.HOR:
                continue
            s = max(2, t * 0.12)
            for side in (-1, 1):
                x = W // 2 + self.bend(t) + side * (self.half(t) + 14 + t * 0.4)
                y = self.HOR + t
                cv.fill(x - s / 4, y - s * 2, s / 2, s * 2, c565(100, 60, 30))
                cv.fill(x - s, y - s * 4, s * 2, s * 2.4, c565(20, 100, 30))
        for d, lane in reversed(self.obs):
            t = self.K / d
            self.car(cv, self.road_x(lane, t), self.HOR + t, self.half(t), c565(240, 200, 30))
        self.car(cv, self.road_x(self.lx, self.TP), self.PY, self.half(self.TP), RED)
        if self.state == 1 and self.fire_on():
            for i in range(3):  # speed lines when boosting
                cv.fill(70 + i * 80, 120 + (self.t * 600 + i * 50) % 100, 2, 14, WHITE)

    def fire_on(self):
        return self.fx.p and self.fx.p[-1][5] == ORANGE

    def car(self, cv, x, y, hw, colour):
        w = max(3, hw * 0.3)
        h = w * 0.7
        cv.fill(x - w / 2, y - h, w, h, colour)
        cv.fill(x - w / 2, y - h, w, max(1, h / 8), WHITE)  # roof light
        cv.fill(x - w / 3, y - h * 1.5, w * 2 / 3, h * 0.6, c565(190, 225, 255))  # glass
        cv.fill(x - w / 2 - 1, y - h * 0.3, max(2, w / 6), h * 0.3, BLACK)
        cv.fill(x + w / 2 - 1, y - h * 0.3, max(2, w / 6), h * 0.3, BLACK)
        cv.fill(x - w / 2 + 1, y - h * 0.7, max(2, w / 6), max(1, h / 8), RED if colour != RED else YELLOW)  # lamps
        cv.fill(x + w / 2 - 2, y - h * 0.7, max(2, w / 6), max(1, h / 8), RED if colour != RED else YELLOW)
