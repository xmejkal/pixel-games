"""Three more for one button: stack (tap drops the block), cave (hold to rise), gravity pong (tap turns the paddle)."""

import random

import pictures

from gfx import ACCENT, BEST, BLACK, GREEN, GREY, HEIGHT, ORANGE, OVER, RED, WHITE, WIDTH, YELLOW, Game, c565, shade

W, H = WIDTH, HEIGHT


class Stack(Game):
    """RENT (P568): you build a tower of flats nobody will live in. The next floor hangs from a hook on a cable and
    slides straight across (a swing was tried; the PO found it unpredictable, 2026-11-02). Each drop kicks the tower
    into a sway; a perfect drop holds the world still for a beat; a miss shakes the tower, and it leans and falls.
    Watercolour noir at noon: ink, bone and one accent."""

    INK, BONE = c565(24, 20, 30), c565(236, 230, 214)  # art/sets/stack.py's pair
    name = "stack"
    hint = "tap to drop"
    bg = c565(196, 192, 208)
    accent = HUD_BEST = ACCENT
    HUD_SCORE = BONE
    LEVEL_H, BASE = 14, 220
    SHOWN = 14  # floors drawn at most: the 12 the view keeps, and two sinking under the street
    SPRING, DAMP, KICK = 250.0, 11.0, 7.0  # the tower's sway: about 2.5 Hz, settled in about 0.6 s
    SHAKE = (3, -2, 2, -1)  # the death shake, one offset per 40 ms frame
    SHAKE_MS, FALL_MS, CARD_MS = 160, 250, 500  # the lean starts after the shake, the floors fall, then the card
    RENT, RENT_PER_FLOOR = 900, 140  # what the billboard asks: every floor raises it
    PLATE_RIGHT, PLATE_TOP, DIGIT_W = 301, 38, 8  # the billboard's empty plate in stack_noon; the digits are 8 x 12
    SOLD_X, SOLD_Y = 248, 36  # stack_sold over that plate when the tower falls
    CARD_X, CARD_Y = 60, 70  # stack_over; its plates' right ends and top, for the floors and the best (art/sets/stack.py)
    FLOORS_RIGHT, BEST_RIGHT, CARD_PLATE_TOP = 161, 237, 123
    TITLE_BEST_RIGHT, TITLE_BEST_TOP = 193, 161  # the title's plate for the best
    LOWER_MS = 1200  # the title's hook lowers the first floor this long

    LIT = tuple("stack_lit%d" % i for i in range(8))  # the show flat on top, its windows warm
    DARK = tuple("stack_dark%d" % i for i in range(8))  # every floor below it: nobody lives there
    DIGITS = tuple("stack_digit%d" % d for d in range(10))  # the names made once: no formatting while drawing
    COTS = tuple("stack_cot%d" % k for k in range(4))  # a quarter turn each
    CONCRETE = tuple(c565(v, v, v + 8) for v in (172, 160, 180, 150, 168, 186, 156, 166))  # the Mac's flat floors

    def setup(self):
        self.covers = pictures.load("stack")  # the painted noon covers the screen, so no fill goes under it
        self.floors = [(90, 140)]  # (x, width) of each placed floor, x without the sway
        self.x, self.w, self.dir, self.speed = 0.0, 140, 1, 120.0
        self.sway, self.sway_v = 0.0, 0.0  # the tower top's offset and speed
        self.hold, self.lean, self.dusted = 0, 1, False  # hitstop frames left; the side the tower falls to
        self.slabs = []  # the cut-offs that fell: [x, y, width, speed, colour]

    def level_y(self, i):
        return self.BASE - (i - max(0, len(self.floors) - 12) + 1) * self.LEVEL_H

    def floor_x(self, i):
        """Floor i's drawn x: its own, plus the sway, more of it the higher it sits in the visible window, so the
        floor at the street stays put. The hit test reads this too; paint works it out the same way."""
        first = max(0, len(self.floors) - self.SHOWN)
        return int(self.floors[i][0] + self.sway / (len(self.floors) - first) * (i - first))

    def hanging_x(self):
        """The hanging floor's drawn x: the straight slide, as before RENT."""
        return int(self.x)

    def play(self, pressed, held):
        if self.hold:  # the hitstop after a perfect drop: the tower and the hanging floor stand still for two frames
            self.hold -= 1
            return
        dt = self.dt
        for c in self.slabs:
            c[3] += 700 * dt
            c[1] += c[3] * dt
            if c[1] >= self.BASE:  # the cot on it breaks on the street
                self.fx.burst(c[0] + c[2] // 2, self.BASE + 8, GREY, 8, 70.0, 0.5, 200.0)
        self.slabs = [c for c in self.slabs if c[1] < self.BASE]
        self.sway_v -= (self.SPRING * self.sway + self.DAMP * self.sway_v) * dt
        self.sway += self.sway_v * dt
        self.x += self.dir * self.speed * dt
        if self.x < 0:
            self.x, self.dir = 0.0, 1
        elif self.x > W - self.w:
            self.x, self.dir = float(W - self.w), -1
        if not pressed:
            return
        n = len(self.floors)
        tx, tw = self.floor_x(n - 1), self.floors[-1][1]
        x, y = self.hanging_x(), self.level_y(n)
        left, right = max(x, tx), min(x + self.w, tx + tw)
        if right - left < 4:
            self.lean = 1 if x > tx else -1
            return self.die(x + self.w // 2, y, (ACCENT, self.INK))
        i = n % 8
        if abs(x - tx) < 4:  # a perfect drop keeps the whole width, glows, and holds the world still
            left, right = tx, tx + tw
            self.hold = 2
            self.fx.burst(left + (right - left) // 2, y, self.BONE, 10, 120.0, 0.5, 100.0)
            self.fx.burst(left + (right - left) // 2, y, ACCENT, 14, 160.0, 0.6, -60.0)
        elif x < left:
            self.slabs.append([x, y, left - x, 0.0, i])
        elif x + self.w > right:
            self.slabs.append([right, y, x + self.w - right, 0.0, i])
        first = max(0, n + 1 - self.SHOWN)  # the window once this floor is in it
        self.floors.append((left - self.sway / (n + 1 - first) * (n - first), right - left))  # stored without the sway
        self.sway_v += max(-24, min(24, x - tx)) * self.KICK  # the tower leans the way the floor landed
        self.w = right - left
        self.score += 1
        self.pop(left + self.w // 2, y, self.INK)
        self.speed = min(330.0, 120 + self.score * 8)

    def block(self, cv, x, y, w, i, lit):
        """Floor i, w px wide: painted lit or dark, else a flat grey on the Mac."""
        if pictures.draw_cut(cv, (self.LIT if lit else self.DARK)[i % 8], x, y, w):  # its top and bottom in pencil
            cv.fill(x, y, 1, self.LEVEL_H, self.INK)  # the ends, where any width was cut
            cv.fill(x + w - 1, y, 1, self.LEVEL_H, self.INK)
            return
        cv.fill(x, y, w, self.LEVEL_H - 1, self.CONCRETE[i % 8] if lit else shade(110, 106, 120, 1))
        cv.fill(x, y, w, 2, self.BONE)  # the slab in the sun
        cv.fill(x, y + self.LEVEL_H - 4, w, 3, shade(60, 56, 70, 1))

    def hook(self, cv, x, y, top):
        """The cable from (top, 16) to the hook over the hanging floor's middle (x, y: its top middle). In play the
        cable's top rides the slide with the floor, so it hangs straight."""
        cv.line(top, 16, x, y - 12, self.INK)
        if not pictures.draw(cv, "stack_hook", x - 8, y - 16):
            cv.fill(x - 4, y - 14, 8, 4, GREY)
            cv.fill(x - 1, y - 10, 2, 10, GREY)

    def number(self, cv, value, right, top):
        """value in digit pictures on a plate, right-aligned at right, the last digit first; text on the Mac."""
        x, rest = right, value
        while True:
            x -= self.DIGIT_W
            if not pictures.draw(cv, self.DIGITS[rest % 10], x, top):
                return cv.text(str(value), right - 8 * len(str(value)), top + 2, self.INK)
            rest //= 10
            if not rest:
                return

    def draw_title(self, cv):
        """RENT: the title card, the hook lowering the first floor onto the street over 1.2 s, then the SOLD plate,
        and the best on its plate."""
        if not pictures.draw(cv, "stack_title", 0, 0):
            return Game.draw_title(self, cv)
        x, w = self.floors[0]
        y = -self.LEVEL_H + (self.level_y(0) + self.LEVEL_H) * min(self.age, self.LOWER_MS) // self.LOWER_MS
        self.hook(cv, x + w // 2, y, x + w // 2)
        self.block(cv, x, y, w, 0, True)
        if self.age >= self.LOWER_MS:
            pictures.draw(cv, "stack_sold", self.SOLD_X, self.SOLD_Y)
        self.number(cv, BEST.get(self.name, 0), self.TITLE_BEST_RIGHT, self.TITLE_BEST_TOP)

    def paint_static(self, cv):
        if pictures.draw(cv, "stack_noon", 0, 0):  # the painted noon (P568)
            return
        cv.gradient(16, self.BASE + 14, (128, 120, 150), (238, 234, 226), 12)
        cv.fill(0, self.BASE + 14, W, H - self.BASE - 14, c565(58, 54, 66))

    def paint(self, cv):
        """The tower, the hanging floor and the slabs. Over, the tower shakes, then leans and falls, from self.age."""
        n, shake, lean, drop, over = len(self.floors), 0, 0.0, 0.0, self.state == OVER
        if over:
            t = self.age
            if t < self.SHAKE_MS:
                shake = self.SHAKE[t // 40]
            lean = self.lean * 600.0 * (max(0, t - self.SHAKE_MS) / 1000) ** 2  # px at the top; (i / n)^2 below
            drop = 450.0 * (max(0, t - self.FALL_MS) / 1000) ** 2
            if drop and not self.dusted:  # the street takes the first floor: one cloud of dust
                self.dusted = True
                self.fx.burst(self.floor_x(0) + self.floors[0][1] // 2, self.BASE + 10, GREY, 20, 90.0, 0.8, -40.0)
        first = max(0, n - self.SHOWN)
        span, top = n - first, n - 1
        step = self.sway / span  # the sway per floor up the visible window, as floor_x works it out
        for i in range(first, n):
            x, w = self.floors[i]
            x, y = int(x + step * (i - first)), self.level_y(i)
            if over:  # the lean and the fall, more of them the higher the floor; only here, so play makes few floats
                k = (i - first) / span
                x += shake + int(lean * k * k)
                y += int(drop * (0.3 + 0.7 * k))
                if y >= H:
                    continue
            self.block(cv, x, y, w, i, i == top)  # only the top floor is the show flat, lit
            if self.hold == 2 and i == top:  # the perfect drop's one white frame
                cv.fill(x, y, w, self.LEVEL_H, WHITE)
        x, y = self.hanging_x() + shake + int(lean), self.level_y(n) + int(drop)
        if y < H:
            self.hook(cv, x + self.w // 2, y, int(self.x) + self.w // 2)
            self.block(cv, x, y, self.w, n, True)
        for x, y, w, _, i in self.slabs:  # over, they fall with the tower; each carries a cot, tumbling as it falls
            if y + drop >= H:  # gone below the street: drop grows for as long as the over screen stays, past 2^31 px
                continue
            self.block(cv, x, int(y + drop), w, i, True)
            pictures.draw(cv, self.COTS[int(y) // 10 % 4], x + w // 2 - 8, int(y + drop) - 12)
        if not over or not pictures.draw(cv, "stack_sold", self.SOLD_X, self.SOLD_Y):
            self.number(cv, self.RENT + self.RENT_PER_FLOOR * self.score, self.PLATE_RIGHT, self.PLATE_TOP)

    def draw_over(self, cv):
        """The collapse plays over the live scene first; then SOLD OUT, 0 RESIDENTS, the floors and the best."""
        if self.age < self.CARD_MS:
            return
        if not pictures.draw(cv, "stack_over", self.CARD_X, self.CARD_Y):
            return Game.draw_over(self, cv)
        self.number(cv, self.score, self.FLOORS_RIGHT, self.CARD_PLATE_TOP)
        self.number(cv, BEST.get(self.name, 0), self.BEST_RIGHT, self.CARD_PLATE_TOP)
        if self.age >= self.OVER_MS and (self.age // 400) % 2 == 0:
            cv.text("tap to retry", self.CARD_X + 52, self.CARD_Y + 84, self.BONE)


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
