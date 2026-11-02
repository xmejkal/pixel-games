"""Three more for one button: stack (tap drops the block), cave (hold to rise), gravity pong (tap turns the paddle)."""

import random

import pictures

from gfx import BLACK, GREEN, GREY, HEIGHT, ORANGE, PALETTE, RED, WHITE, WIDTH, YELLOW, Game, c565, shade

W, H = WIDTH, HEIGHT


class Stack(Game):
    name = "stack"
    hint = "tap to drop"
    bg = c565(20, 20, 50)
    accent = c565(250, 220, 40)
    LEVEL_H, BASE = 14, 220
    stars = ()

    STRIPS = tuple("stack_block%d" % i for i in range(8))  # painted textures in PALETTE's order (P563)

    def setup(self):
        self.covers = pictures.load()  # the painted night covers the screen, so no fill goes under it
        self.layers = [(90, 140)]  # (x, width) of each placed block
        self.x, self.w, self.dir, self.speed = 0.0, 140, 1, 120.0
        self.cuts = []  # the slices that fell off: [x, y, width, speed, colour]
        if not self.stars:  # still, so made once: the kept background must not change on a retry
            self.stars = [(random.randrange(W), random.randrange(18, 200)) for _ in range(30)]

    def level_y(self, i):
        return self.BASE - (i - max(0, len(self.layers) - 12) + 1) * self.LEVEL_H

    def play(self, pressed, held):
        for c in self.cuts:
            c[3] += 700 * self.dt
            c[1] += c[3] * self.dt
        self.cuts = [c for c in self.cuts if c[1] < self.BASE]
        self.x += self.dir * self.speed * self.dt
        if self.x < 0:
            self.x, self.dir = 0.0, 1
        elif self.x > W - self.w:
            self.x, self.dir = float(W - self.w), -1
        if not pressed:
            return
        tx, tw = self.layers[-1]
        x, y = int(self.x), self.level_y(len(self.layers))
        left, right = max(x, tx), min(x + self.w, tx + tw)
        if right - left < 4:
            return self.die(x + self.w // 2, y)
        i = len(self.layers) % 8
        colour = PALETTE[i]
        if abs(x - tx) < 4:  # a perfect drop keeps the whole width, and glows
            left, right = tx, tx + tw
            self.fx.burst(left + (right - left) // 2, y, WHITE, 10, 120.0, 0.5, 100.0)
            self.fx.burst(left + (right - left) // 2, y, colour, 14, 160.0, 0.6, -60.0)
        elif x < left:
            self.cuts.append([x, y, left - x, 0.0, i])
        elif x + self.w > right:
            self.cuts.append([right, y, x + self.w - right, 0.0, i])
        self.layers.append((left, right - left))
        self.w = right - left
        self.score += 1
        self.pop(left + self.w // 2, y)
        self.speed = min(330.0, 120 + self.score * 8)

    def block(self, cv, x, y, w, colour, strip):
        if pictures.draw_cut(cv, strip, x, y, w):  # painted, with its own top and bottom lines: the ends in pencil
            ink = c565(40, 30, 50)
            cv.fill(x, y, 1, self.LEVEL_H, ink)
            cv.fill(x + w - 1, y, 1, self.LEVEL_H, ink)
            return
        cv.fill(x, y, w, self.LEVEL_H - 1, colour)
        cv.fill(x, y, w, 2, WHITE)  # top light
        cv.fill(x, y + self.LEVEL_H - 4, w, 3, shade(60, 60, 60, 1))

    def paint_static(self, cv):
        if pictures.draw(cv, "stack_bg", 0, 0):  # the painted night (P563)
            return
        cv.gradient(16, self.BASE + 14, (10, 10, 40), (90, 40, 90), 12)
        for sx, sy in self.stars:
            cv.fill(sx, sy, 2, 2, WHITE)
        cv.fill(0, self.BASE + 14, W, H - self.BASE - 14, GREY)

    def paint(self, cv):
        for i, (x, w) in enumerate(self.layers):
            self.block(cv, x, self.level_y(i), w, PALETTE[i % 8], self.STRIPS[i % 8])
        self.block(cv, int(self.x), self.level_y(len(self.layers)), self.w, c565(255, 255, 255), "stack_mover")
        for x, y, w, _, i in self.cuts:
            self.block(cv, x, int(y), w, PALETTE[i], self.STRIPS[i])


class Cave(Game):
    name = "cave"
    hint = "hold to climb"
    bg = c565(15, 10, 20)
    accent = ORANGE
    COLW, N, HX = 8, 42, 60
    TOP, BOT = 40, 200  # the cave is 160 rows high, in the middle

    def setup(self):
        self.cols = [(70, 170)] * self.N  # (top, bottom) of the open space in each column
        self.centre, self.off, self.dist, self.puff = 120, 0.0, 0.0, 0.0
        self.y, self.vy = 120.0, 0.0

    def new_column(self):
        gap = max(64, 104 - self.score)
        self.centre = max(self.TOP + 6 + gap // 2, min(self.BOT - 6 - gap // 2, self.centre + random.randrange(-12, 13)))
        return (self.centre - gap // 2, self.centre + gap // 2)

    def play(self, pressed, held):
        dt = self.dt
        self.vy = max(-230.0, min(230.0, self.vy + (-900 if held else 700) * dt))
        self.y += self.vy * dt
        speed = 120 + min(self.score, 60)
        self.off += speed * dt
        self.dist += speed * dt
        self.score = int(self.dist / 40)
        self.puff -= dt
        if self.puff <= 0:
            self.puff = 0.06
            self.fx.add(self.HX - 10, self.y, -speed * 0.8, random.randrange(-12, 13), GREY, 0.5, -20.0)
        while self.off >= self.COLW:
            self.off -= self.COLW
            self.cols.pop(0)
            self.cols.append(self.new_column())
        first = int((self.HX + self.off) // self.COLW)
        for i in (first, first + 2):
            top, bottom = self.cols[i]
            if self.y - 6 < top or self.y + 6 > bottom:
                self.die(self.HX + 10, self.y)

    def paint_static(self, cv):
        cv.clip = (0, self.TOP, W, self.BOT)
        cv.gradient(self.TOP, self.BOT, (30, 16, 40), (10, 6, 18), 16)

    def paint(self, cv):
        cv.clip = (0, self.TOP, W, self.BOT)
        w = self.COLW + 1
        for i, (top, bottom) in enumerate(self.cols):
            x = i * self.COLW - self.off
            rock = c565(90, 70, 60) if i % 3 else c565(78, 60, 52)
            cv.fill(x, self.TOP, w, top - self.TOP, rock)
            cv.fill(x, top - 4, w, 4, c565(170, 130, 95))
            if i % 5 == 0:  # a stalactite
                cv.fill(x + 2, top, 4, 8, rock)
            cv.fill(x, bottom, w, self.BOT - bottom, rock)
            cv.fill(x, bottom, w, 4, c565(170, 130, 95))
            if i % 7 == 3:  # a stalagmite
                cv.fill(x + 2, bottom - 8, 4, 8, rock)
        y, hx = self.y, self.HX
        cv.clip = (0, 0, W, H)
        cv.fill(hx - 12, y - 2, 14, 4, c565(190, 40, 40))  # tail boom
        cv.fill(hx - 14, y - 7, 3, 8, c565(190, 40, 40))
        cv.fill(hx - 2, y - 7, 22, 14, RED)
        cv.fill(hx + 8, y - 5, 10, 7, c565(150, 220, 250))  # cockpit glass
        cv.fill(hx - 2, y + 7, 22, 2, GREY)  # skid
        cv.fill(hx + 8, y - 11, 2, 4, GREY)
        cv.line(hx - 14, y - 11, hx + 30, y - 11 + int(self.t * 40) % 3, WHITE)  # rotor


class GravityPong(Game):
    name = "gravpong"
    hint = "tap flips paddle"
    bg = c565(10, 30, 40)
    accent = c565(40, 220, 230)
    PW, PY = 70, 218

    def setup(self):
        self.px, self.pdir = 125.0, 1
        self.bx, self.by, self.vx, self.vy = 160.0, 60.0, 70.0, 0.0
        self.trail = []

    def play(self, pressed, held):
        dt = self.dt
        if pressed:
            self.pdir = -self.pdir
        self.px += self.pdir * (170 + min(self.score, 20) * 4) * dt
        if self.px < 0 or self.px > W - self.PW:
            self.px = max(0.0, min(float(W - self.PW), self.px))
            self.pdir = -self.pdir
        self.vy += 520 * dt
        self.bx += self.vx * dt
        before, self.by = self.by, self.by + self.vy * dt
        self.trail = (self.trail + [(self.bx, self.by)])[-5:]
        if self.bx < 6 or self.bx > W - 6:
            self.bx = max(6.0, min(W - 6.0, self.bx))
            self.vx = -self.vx
        if self.by < 24:
            self.by, self.vy = 24.0, abs(self.vy)
        if self.vy > 0 and before < self.PY - 6 <= self.by and self.px - 6 <= self.bx <= self.px + self.PW + 6:
            self.score += 1
            self.vy = -(410 + min(self.score, 25) * 9)
            self.vx += self.pdir * 70 + random.randrange(-25, 26)
            self.vx = max(-200.0, min(200.0, self.vx))
            self.fx.burst(self.bx, self.PY, self.accent, 9, 120.0, 0.4, 250.0)
        elif self.by > H + 6:
            self.die(self.bx, H - 10)

    def paint_static(self, cv):
        cv.gradient(16, H, (6, 20, 34), (14, 50, 62), 16)
        for x in range(0, W, 40):  # court lines
            cv.fill(x, 16, 1, H, c565(20, 70, 80))
        cv.fill(0, 20, W, 2, GREY)

    def paint(self, cv):
        for i, (tx, ty) in enumerate(self.trail):  # the ball's tail fades
            cv.fill(tx - 4 + i // 2, ty - 4 + i // 2, 8 - i // 2 * 2, 8 - i // 2 * 2, shade(60, 160, 180, 0.2 + i * 0.15))
        px = int(self.px)
        cv.fill(px, self.PY, self.PW, 8, self.accent)
        cv.fill(px, self.PY, self.PW, 2, WHITE)
        cv.fill(px + (self.PW - 10 if self.pdir > 0 else 0), self.PY, 10, 8, YELLOW)  # the leading end
        cv.fill(self.bx - 6, self.by - 6, 12, 12, WHITE)
        cv.fill(self.bx - 3, self.by - 3, 4, 4, c565(190, 220, 255))
