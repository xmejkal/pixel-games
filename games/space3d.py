"""Two more 3D games for one button: starfire (tap fires at the sweeping crosshair) and cube (tap when the mark faces you)."""

import math
import random

from gfx import CYAN, GREEN, GREY, HEIGHT, ORANGE, RED, WHITE, WIDTH, YELLOW, Game, c565, shade

W, H = WIDTH, HEIGHT
CX, CY = W // 2, 128


class Starfire(Game):
    name = "starfire"
    hint = "tap fires"
    bg = c565(2, 2, 10)
    accent = CYAN
    F, STARS = 150, 40
    AREA = (50, 40, 270, 200)
    HEX = [(math.cos(i * 1.047), math.sin(i * 1.047)) for i in range(6)]

    def setup(self):
        self.stars = [[random.uniform(-4, 4), random.uniform(-3, 3), random.uniform(0.3, 4)] for _ in range(self.STARS)]
        self.rocks, self.booms, self.lives, self.spawn, self.shot = [], [], 3, 0.8, 0.0
        self.aim = (CX, CY)

    def project(self, x, y, z):
        k = self.F / z
        return CX + x * k, CY + y * k

    def play(self, pressed, held):
        dt, t = self.dt, self.t
        self.aim = (CX + 95 * math.sin(t * 1.9), CY + 55 * math.sin(t * 1.3 + 1))
        for s in self.stars:
            s[2] -= 1.6 * dt
            if s[2] < 0.2:
                s[:] = [random.uniform(-4, 4), random.uniform(-3, 3), 4.0]
        speed = 0.9 + min(self.score, 30) * 0.03
        for r in self.rocks:
            r[2] -= speed * dt
            r[3] += dt * 2
        for r in [r for r in self.rocks if r[2] < 0.6]:
            self.rocks.remove(r)
            self.lives -= 1
            self.fx.burst(CX, H - 20, RED, 10, 120.0, 0.5)
        if self.lives <= 0:
            return self.die(CX, H - 40)
        self.spawn -= dt
        if self.spawn <= 0 and len(self.rocks) < 4:
            self.rocks.append([random.uniform(-1.6, 1.6), random.uniform(-1.0, 1.0), 6.0, 0.0])
            self.spawn = max(0.5, 1.6 - self.score * 0.04)
        self.shot = max(0.0, self.shot - dt)
        for b in self.booms:
            b[2] += dt
        self.booms = [b for b in self.booms if b[2] < 0.35]
        if pressed:
            self.fire()

    def fire(self):
        self.shot = 0.1
        ax, ay = self.aim
        for r in sorted(self.rocks, key=lambda r: r[2]):
            sx, sy = self.project(r[0], r[1], r[2])
            reach = self.F * 0.25 / r[2] + 9
            if abs(sx - ax) < reach and abs(sy - ay) < reach:
                self.rocks.remove(r)
                self.booms.append([sx, sy, 0.0])
                self.fx.burst(sx, sy, ORANGE, 12, 140.0, 0.6, 0.0)
                self.score += 1
                return

    def paint_static(self, cv):
        cv.clip = self.AREA
        cv.gradient(40, 200, (4, 2, 24), (24, 6, 40), 16)  # a faint nebula
        cv.disc(236, 76, 20, c565(60, 50, 110))  # a far planet with a shadow
        cv.disc(242, 72, 14, c565(100, 90, 170))
        cv.clip = (0, 0, W, H)
        cv.box(49, 39, 222, 162, c565(60, 60, 110))
        cv.line(CX - 24, 215, CX, 201, GREY)  # the nose of your ship, under the picture
        cv.line(CX + 24, 215, CX, 201, GREY)

    def paint(self, cv):
        cv.clip = self.AREA
        for x, y, z in self.stars:
            sx, sy = self.project(x, y, z)
            px, py = self.project(x, y, z + 0.25)
            if not (50 < sx < 270 and 40 < sy < 200 and 50 < px < 270 and 40 < py < 200):
                continue
            cv.line(px, py, sx, sy, shade(200, 220, 255, 1.2 - z / 4))
        for x, y, z, spin in sorted(self.rocks, key=lambda r: -r[2]):
            sx, sy = self.project(x, y, z)
            r = self.F * 0.25 / z
            c, s = math.cos(spin), math.sin(spin)
            pts = [(sx + r * (hc * c - hs * s), sy + r * (hs * c + hc * s)) for hc, hs in self.HEX]
            colour = shade(255, 140, 60, 1.4 - z / 6)
            for i in range(6):
                a, b = pts[i], pts[(i + 1) % 6]
                cv.line(a[0], a[1], b[0], b[1], colour)
                cv.line(a[0], a[1], sx, sy, shade(160, 80, 40, 1.4 - z / 6))
            cv.fill(sx - 1, sy - 1, 3, 3, WHITE)
        for bx, by, age in self.booms:
            r = 6 + age * 160
            cv.box(bx - r, by - r, 2 * r, 2 * r, YELLOW if age < 0.18 else ORANGE)
        ax, ay = self.aim
        if self.shot > 0:
            cv.line(CX, 196, ax, ay, WHITE)
        cv.box(ax - 10, ay - 10, 20, 20, GREEN)
        cv.fill(ax - 15, ay, 8, 1, GREEN)
        cv.fill(ax + 7, ay, 8, 1, GREEN)
        for i in range(self.lives):
            cv.fill(W - 16 - i * 14, 22, 10, 10, RED)


class CubeTiming(Game):
    name = "cube"
    hint = "tap: mark faces you"
    bg = c565(8, 8, 24)
    accent = c565(230, 60, 220)
    F, D, TILT, MARK = 200, 5.0, 0.6, 7
    TC, TS = math.cos(0.6), math.sin(0.6)
    _yaw, _c, _s = None, 1.0, 0.0
    TARGET = 3 * math.pi / 4  # the yaw at which vertex 7, (1, 1, 1), looks straight at you
    VERTS = [((i & 1) * 2 - 1, ((i >> 1) & 1) * 2 - 1, ((i >> 2) & 1) * 2 - 1) for i in range(8)]
    EDGES = [(a, a | b) for a in range(8) for b in (1, 2, 4) if not a & b]

    def setup(self):
        self.yaw, self.w, self.lives, self.done, self.flash, self.rev = 0.0, 2.2, 3, False, 0.0, 0
        self.good = False

    def tol(self):
        return min(0.5, self.w * 0.12)

    def err(self):
        return (self.yaw - self.TARGET + math.pi) % (2 * math.pi) - math.pi

    def project(self, v, yaw):
        if yaw != self._yaw:  # the sine and cosine of one yaw serve all eight corners
            self._yaw, self._c, self._s = yaw, math.cos(yaw), math.sin(yaw)
        x, y, z = v
        x, z = x * self._c + z * self._s, -x * self._s + z * self._c
        y, z = y * self.TC - z * self.TS, y * self.TS + z * self.TC
        k = self.F / (z + self.D)
        return CX + x * k, 116 + y * k, z

    def miss(self):
        self.lives -= 1
        self.flash, self.good = 0.25, False
        x, y, _ = self.project(self.VERTS[self.MARK], self.yaw)
        self.fx.burst(x, y, RED, 8, 100.0, 0.4)
        if self.lives <= 0:
            self.die(x, y)

    def play(self, pressed, held):
        self.yaw += self.w * self.dt
        self.flash = max(0.0, self.flash - self.dt)
        rev = int((self.yaw - self.TARGET + math.pi) // (2 * math.pi))
        if rev != self.rev:  # the mark went round again
            self.rev = rev
            if not self.done:
                self.miss()
            self.done = False
        if pressed:
            if self.done or abs(self.err()) > self.tol():
                self.miss()
                self.done = True
            else:
                self.done, self.good, self.flash = True, True, 0.25
                self.score += 1
                x, y, _ = self.project(self.VERTS[self.MARK], self.yaw)
                self.pop(x, y, GREEN)
                self.w = min(5.5, self.w * 1.08)

    def paint_static(self, cv):
        cv.fill(CX - 100, 229, 200, 3, c565(50, 50, 70))  # the timing bar's track

    def paint(self, cv):
        if self.flash > 0:
            cv.fill(0, 16, W, H, c565(0, 70, 20) if self.good else c565(90, 10, 10))
        for i in range(16):  # a ring of dots turns under the cube
            a = self.yaw * 0.7 + i * math.pi / 8
            cv.fill(CX + 120 * math.cos(a), 210 + 8 * math.sin(a), 3, 3, shade(130, 60, 170, 0.5 + 0.5 * math.sin(a)))
        pts = [self.project(v, self.yaw) for v in self.VERTS]
        for a, b in self.EDGES:
            marked = self.MARK in (a, b)
            near = 1.2 - (pts[a][2] + pts[b][2] + 2.8) / 5.6  # nearer edges are brighter
            colour = WHITE if marked else shade(230, 60, 220, near)
            cv.line(pts[a][0], pts[a][1], pts[b][0], pts[b][1], colour)
        tx, ty, _ = self.project(self.VERTS[self.MARK], self.TARGET)  # where the mark must be when you tap
        inside = abs(self.err()) <= self.tol()
        cv.box(tx - 14, ty - 14, 28, 28, GREEN if inside else c565(90, 90, 100))
        mx, my, _ = pts[self.MARK]
        cv.fill(mx - 4, my - 4, 9, 9, GREEN if inside else YELLOW)
        bar = int(self.tol() * 60)  # a timing bar: the mark runs through the green zone
        cv.fill(CX - bar, 227, 2 * bar, 6, c565(30, 140, 60))
        cv.fill(CX + max(-100, min(100, self.err() * 60)) - 1, 224, 3, 10, YELLOW)
        for i in range(self.lives):
            cv.fill(W - 16 - i * 14, 22, 10, 10, RED)
