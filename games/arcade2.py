"""Three more for one button: stack (tap drops the block), cave (hold to rise), BUBBLE (tap turns the net)."""

import random
import time

import pictures
from cues import Cue
from gfx import (ACCENT, BEST, BLACK, GREEN, GREY, HEIGHT, ORANGE, OVER, PLAY, RED, TITLE, WHITE, WIDTH, YELLOW, Dice,
                 Game, Particles, c565, shade)

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


# BUBBLE's picture names, made once (P573): no formatting while drawing. Each size's bubble in its five poses, its film
# (the round one's four turns, then the other poses) and its glow's three rings; each net width's four sags; each
# worker's run, backing, and spent run and backing, and its spent stand, the left worker's first.
BUBBLE_SIZES, BUBBLE_RINGS = (12, 16, 20, 24, 28), (26, 16, 8)
BUBBLE_POSES = ("round", "squash", "stretch", "wobblea", "wobbleb")
BUBBLES = tuple(tuple("gravpong_bubble_%d_%s" % (d, pose) for pose in BUBBLE_POSES) for d in BUBBLE_SIZES)
FILMS = tuple(tuple("gravpong_film_%d_%s" % (d, f) for f in ("round0", "round1", "round2", "round3") + BUBBLE_POSES[1:])
              for d in BUBBLE_SIZES)
HALOS = tuple(tuple("gravpong_halo_%d_%d" % (d, ring) for ring in BUBBLE_RINGS) for d in BUBBLE_SIZES)
NET_WIDTHS = (70, 62, 54, 46)  # px: the net, and as the workers tire (art/sets/gravpong.py paints each)
NETS = {w: tuple("gravpong_net_%d_%d" % (w, k) for k in range(4)) for w in NET_WIDTHS}
WORKERS = tuple({kind: tuple("gravpong_worker_%s_%s%d" % (side, kind, k) for k in range(4))
                 for kind in ("run", "back", "trun", "tback")} for side in "lr")
STANDS = tuple("gravpong_worker_%s_tired" % side for side in "lr")  # holding the empty net


class Sparks(Particles):
    """The particles of a game that can hide them for a few frames: BUBBLE's hit-pause holds the pop still."""

    hide = False

    def draw(self, cv):
        if not self.hide:
            Particles.draw(self, cv)


class BubbleLook:
    """The bubble as drawn, from the play: the size of its pictures for its radius, and its pose from the time since
    the last catch and its speed. Squashed first, then stretched while fast, then wobbling as it settles, then
    round."""

    ROUND, SQUASH, STRETCH, WOBBLE_A, WOBBLE_B = range(5)
    SQUASH_MS, WOBBLE_MS, WOBBLE_STEP_MS = 140, 640, 80  # the squash holds 3 to 4 frames
    STRETCH_VY = 470  # px/s: faster than this, up or down, the bubble stretches
    MIN_RADIUS = 6

    @classmethod
    def size_index(cls, radius):
        """The index of the bubble's size in BUBBLE_SIZES: its pictures are drawn one to one for its radius."""
        return (radius - cls.MIN_RADIUS) // 2

    @classmethod
    def pose(cls, since, vy):
        """The pose since ms after the last catch, at vy px/s."""
        if since < cls.SQUASH_MS:
            return cls.SQUASH
        if vy < -cls.STRETCH_VY or vy > cls.STRETCH_VY:
            return cls.STRETCH
        if since < cls.WOBBLE_MS:
            return cls.WOBBLE_A + since // cls.WOBBLE_STEP_MS % 2
        return cls.ROUND


class Net:
    """The net's sag at its middle: a damped spring (stack's), kicked down by each catch's speed, and the picture of
    its sag: bulging up as it recoils, flat, sagging, deep."""

    SPRING, DAMP, KICK = 250.0, 11.0, 0.7  # a catch at 500 px/s sags it about 9 px, in 40 ms frames
    POSES = (-0.8, 2.0, 7.0)  # sag in px: under the first the net bulges up, under the next it is flat, then it sags,
    # and deeper it is deep

    def __init__(self):
        self.sag, self.v = 0.0, 0.0

    def kick(self, vy):
        self.v += vy * self.KICK

    def update(self, dt):
        self.v -= (self.SPRING * self.sag + self.DAMP * self.v) * dt
        self.sag += self.v * dt

    def pose(self):
        k = 0
        while k < 3 and self.sag >= self.POSES[k]:
            k += 1
        return k


class Notes:
    """The banknotes of a pop: COUNT of them burst up from it on the game's own Dice and flutter down, slowed by the
    air, swaying and flipping; each lies on the floor, or in the net where it falls into it and rides there. A note is
    [x, y, vx, vy, k, place]: k its own phase, place its x in the net or -1."""

    COUNT, MAX_VY, GRAVITY, DRAG = 14, 46.0, 420.0, 2.5
    FLIPS = (0, 1, 2, 1)  # the note's poses as it turns over, one each 60 ms
    SWAY = (0, 1, 2, 2, 1, 0, -1, -2, -2, -1)  # px, one step each 60 ms
    NAMES = tuple("gravpong_note_%d" % k for k in range(3))

    def __init__(self, dice):
        self.dice, self.q = dice, []

    def burst(self, x, y):
        dice = self.dice
        for _ in range(self.COUNT):
            self.q.append([float(x + dice.spread(10)), float(y - dice.below(12)), float(dice.spread(160)),
                           float(-120 - dice.below(220)), dice.below(40), -1])

    def update(self, dt, floor, left, width, top):
        """dt s of flight. floor: the row a note lies on; the net from left, width wide, its rope on row top."""
        for q in self.q:
            if q[1] >= floor or q[5] >= 0:
                continue
            q[2] -= q[2] * self.DRAG * dt
            q[3] = min(q[3] + self.GRAVITY * dt, self.MAX_VY)
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            if q[3] > 0 and left <= q[0] <= left + width and top + 1 <= q[1] < top + 5:  # into the net
                q[5] = int(q[0] - left)
            elif q[1] >= floor:
                q[1] = float(floor)

    def draw(self, cv, ms, floor, left, top):
        t = ms // 60
        for x, y, _, _, k, place in self.q:
            if place >= 0:  # in the net: it rides with it
                pictures.draw(cv, self.NAMES[0], int(left) + place - 4, top + 1)
            elif y >= floor:
                pictures.draw(cv, self.NAMES[0 if k % 3 else 2], int(x), floor - 1)
            else:
                pictures.draw(cv, self.NAMES[self.FLIPS[(t + k) % 4]], int(x) + self.SWAY[(t + k) % 10], int(y))


class GravityPong(Game):
    """BUBBLE (P573): two night workers carry a net across an exchange floor at midnight and keep a soap bubble in the
    air. A tap turns them round. Each catch sends the bubble up again, faster; the net sags and springs back, and the
    workers tire. A missed bubble hits the floor and pops into banknotes, the ticker board's chart crashes, and the
    card says IT WAS NEVER REAL. Watercolour noir at midnight: ink, bone, the film's cool tone and one accent."""

    name = "gravpong"
    hint = "tap turns the net"
    bg = c565(10, 30, 40)
    accent = c565(40, 220, 230)
    BONE = c565(232, 224, 204)  # art/sets/gravpong.py's
    FILM = (c565(112, 178, 226), c565(196, 170, 220), c565(250, 246, 236), c565(255, 178, 96))  # the film's drops
    HUD_SCORE, HUD_BEST = BONE, ACCENT
    cues = {"catch": Cue("jump"), "die": Cue("die")}
    PW, PY = NET_WIDTHS[0], 218  # the net's width at the start, and its hit row
    MIN_RADIUS = BubbleLook.MIN_RADIUS  # the bubble's radius at the start, px

    # --- the painted look: art/sets/gravpong.py's sizes and places, which the board has no art/ to read
    # (tests/test_paint.py pins them), and the feel's numbers, set by eye on Mac frames of tools/render_scene.py
    FLOOR, NET_Y = 236, 216  # the floor's first row; the net picture's top (its end ropes on the rows PY, PY + 1)
    SIZES = BUBBLE_SIZES  # the bubble's diameters, one per radius 6, 8, 10, 12, 14
    BOX = (18, 24, 28, 34, 38)  # each size's square picture, its middle on the bubble's middle
    RINGS = BUBBLE_RINGS  # px the glow's rings reach past the bubble, outer first
    GLOW_ALPHAS, FILM_ALPHA = (34, 42, 54), 120
    DROPS = 8  # the film's drops at each catch
    WORKER_W, WORKER_H, HAND_DX = 26, 34, 9  # a worker's picture; px from its middle to the hands on the net's end
    STEP_PX, TIRED_STEP_PX, STRIDE = 8, 13, 4  # px the net moves for each pose of the run (fresh, spent); its poses
    POOL_W, POOL_H, POOL_ALPHA = 150, 16, 90  # the light pool under the crew
    POP, POP_FRAMES, POP_MS = 40, 5, 60
    BOARD, PLATE_RIGHT, PLATE_TOP, DIGIT_W = (92, 22), 219, 76, 8  # the board's top left; the index's plate
    CARD_X, CARD_Y = 60, 70  # gravpong_over, and its plates' right ends and top, for the score and the best
    SCORE_RIGHT, BEST_RIGHT, CARD_PLATE_TOP = 137, 217, 137
    TITLE_BEST_RIGHT, TITLE_BEST_TOP, COIN = 201, 137, 10
    TIRED_MS = 300  # the workers' sigh after each catch
    NEVER = 1 << 20  # ms since a catch, before the first
    SPOT_W, SPOT_H = 48, 10  # the bubble's light on the floor
    TIRED_SCORE = 15  # from this score the workers are spent
    FILM_MS = 120  # the round film turns a quarter swirl this often
    HIT_MS, CARD_MS = 80, 700  # the hit-pause's 2 frames before the pop; the card after the death
    INDEX = tuple(min(9999999, int(100 * 1.3 ** n)) for n in range(44))  # the board's index at each score, 1.3 times
    # the last: a bubble. From 44 points on it stays at 9,999,999, the plate's seven digits

    BUBBLES, FILMS, HALOS, NETS, WORKERS, STANDS = BUBBLES, FILMS, HALOS, NETS, WORKERS, STANDS
    POPS = tuple("gravpong_pop_%d" % k for k in range(POP_FRAMES))
    DIGITS = tuple("gravpong_digit_%d" % d for d in range(10))

    def setup(self):
        self.px, self.pdir = 125.0, 1
        self.bx, self.by, self.vx, self.vy = 160.0, 60.0, 70.0, 0.0
        self.covers = pictures.load(self.name)  # the painted midnight covers the screen, so no fill goes under it
        self.trail = []  # the flat look's fading tail, where there is no art
        self.fx = Sparks()
        self.dice = Dice(5732)  # the effects' own random stream: the rules' draws stay as they are
        self.caught_at = None  # ms of the last catch, for the squash, the wobble and the workers' sigh
        self.net, self.notes = Net(), Notes(self.dice)
        self.popped = False
        self.pop_x, self.pop_y = 0, 0

    def radius(self):
        """The bubble's radius in px: 6, and 2 more for each 4 points up to 14 (D9, P573): the bubble swells as the
        score climbs, and its walls, ceiling, catch and death all reach as far as it does."""
        return self.MIN_RADIUS + 2 * min(self.score // 4, 4)

    def net_width(self):
        """The net's width in px: 70, and 8 less for each 4 points past TIRED_SCORE down to 46 (a second named rule
        change, P573's review): the spent workers hold a smaller net under a bigger bubble."""
        return NET_WIDTHS[min(3, max(0, (self.score - self.TIRED_SCORE + 3) // 4))]

    def play(self, pressed, held):
        dt, pw = self.dt, self.net_width()
        if pressed:
            self.pdir = -self.pdir
        self.px += self.pdir * (170 + min(self.score, 20) * 4) * dt
        if self.px < 0 or self.px > W - pw:
            self.px = max(0.0, min(float(W - pw), self.px))
            self.pdir = -self.pdir
        self.vy += 520 * dt
        self.bx += self.vx * dt
        before, self.by = self.by, self.by + self.vy * dt
        r = self.radius()
        if self.bx < r:  # the walls send it back inward: a radius that grew at a catch never flips one leaving a wall
            self.bx, self.vx = float(r), abs(self.vx)
        elif self.bx > W - r:
            self.bx, self.vx = float(W - r), -abs(self.vx)
        if self.by < 18 + r:  # the ceiling: under the score bar, however big the bubble
            self.by, self.vy = 18.0 + r, abs(self.vy)
        if self.vy > 0 and before < self.PY - r <= self.by and self.px - r <= self.bx <= self.px + pw + r:
            self.score += 1
            self.px += (pw - self.net_width()) / 2  # a net that shrinks at the catch keeps its middle
            self.landed(self.vy)
            self.vy = -(410 + min(self.score, 25) * 9)
            self.vx += self.pdir * 70 + random.randrange(-25, 26)
            self.vx = max(-200.0, min(200.0, self.vx))
            self.fx.burst(self.bx, self.PY, self.BONE, 9, 120.0, 0.4, 250.0)
        elif self.by > H + r:
            self.pop_x, self.pop_y = int(self.bx), self.FLOOR - self.radius() * 3 // 4
            self.die(self.bx, self.pop_y, (self.FILM[0], self.BONE))

    def landed(self, vy):
        """A catch at vy px/s: the sound, the squash and the sigh from now, the net kicked down, the film's drops."""
        self.emit("catch")
        self.caught_at = self.last
        self.net.kick(vy)
        dice, r = self.dice, self.radius()
        for _ in range(self.DROPS):  # the film sheds drops where the net strikes it, on the game's own Dice
            self.fx.add(self.bx + dice.spread(r), self.by + r - 2, dice.spread(90), -60 - dice.below(120),
                        self.FILM[dice.below(4)], 0.3 + dice.below(30) / 100, 400.0)

    def step(self, now_ms, pressed, held):
        """Game.step; then the flat look's tail where there is no art; the net's spring in play and over; and over,
        the notes: they burst from the pop after the hit-pause and flutter down."""
        super().step(now_ms, pressed, held)
        if self.state == TITLE:
            return
        if not self.covers and self.state == PLAY:
            self.trail = (self.trail + [(self.bx, self.by)])[-5:]
        self.net.update(self.dt)
        if self.state != OVER:
            return
        if not self.popped and self.over_ms() >= self.HIT_MS:
            self.popped = True
            self.notes.burst(self.pop_x, self.pop_y)
        self.notes.update(self.dt, self.FLOOR - 3, self.px, self.net_width(), self.PY)

    def over_ms(self):
        """ms since the bubble was lost: age is read before the frame's play, so in the frame of the loss it is
        still play's."""
        return time.ticks_diff(self.last, self.since)

    def since_catch(self):
        """ms since the last catch, NEVER before the first."""
        return self.NEVER if self.caught_at is None else time.ticks_diff(self.last, self.caught_at)

    def tired(self):
        """Whether the workers are spent: for TIRED_MS after each catch, and always from TIRED_SCORE."""
        return self.score >= self.TIRED_SCORE or self.since_catch() < self.TIRED_MS

    def number(self, cv, value, right, top):
        """value in digit pictures, right-aligned at right, the last digit first."""
        x, rest = right, value
        while True:
            x -= self.DIGIT_W
            pictures.draw(cv, self.DIGITS[rest % 10], x, top)
            rest //= 10
            if not rest:
                return

    def bubble_y(self):
        """The bubble's drawn middle row: where it is, or on the floor once it is down there."""
        return min(int(self.by), self.FLOOR - self.radius())

    def draw_bubble(self, cv, x, y, k, pose, glow=1):
        """The bubble of size k in pose with its middle at (x, y): the glow's rings, the film and the rim."""
        d = self.SIZES[k]
        for i in range(3):  # no iterator or tuple a frame
            n = (d + self.RINGS[i]) // 2
            pictures.draw(cv, self.HALOS[k][i], x - n, y - n, self.GLOW_ALPHAS[i] * glow)
        b = self.BOX[k] // 2
        film = self.last // self.FILM_MS % 4 if pose == BubbleLook.ROUND else pose + 3
        pictures.draw(cv, self.FILMS[k][film], x - b, y - b, self.FILM_ALPHA)
        pictures.draw(cv, self.BUBBLES[k][pose], x - b, y - b)

    def draw_crew(self, cv, px, tired, over):
        """The light pool on the floor, then the workers on the net's ends at px, running their way (the left one faces
        right) or standing spent, and the net between them in the picture for its sag. Spent, they step slower and slump on
        every other step."""
        pw = self.net_width()
        pictures.draw(cv, "gravpong_pool", px + pw // 2 - self.POOL_W // 2, self.FLOOR - self.POOL_H // 2,
                      self.POOL_ALPHA)
        step = int(px) // (self.TIRED_STEP_PX if tired else self.STEP_PX)
        slump = 1 if tired and not over and step % 2 else 0
        for side in (0, 1):
            if over:
                name = self.STANDS[side]
            else:
                ahead = (self.pdir > 0) == (side == 0)  # the worker runs the way it faces
                kind = ("trun" if tired else "run") if ahead else ("tback" if tired else "back")
                name = self.WORKERS[side][kind][(step if side == 0 else -step) % self.STRIDE]
            x = px - self.HAND_DX if side == 0 else px + pw + self.HAND_DX
            pictures.draw(cv, name, x - self.WORKER_W // 2, self.FLOOR - self.WORKER_H + slump)
        pictures.draw(cv, self.NETS[pw][self.net.pose()], px, self.NET_Y)

    def paint_static(self, cv):
        if pictures.draw(cv, "gravpong_midnight", 0, 0):  # the painted midnight (P573)
            return
        cv.gradient(16, H, (6, 20, 34), (14, 50, 62), 16)
        for x in range(0, W, 40):  # court lines
            cv.fill(x, 16, 1, H, c565(20, 70, 80))
        cv.fill(0, 20, W, 2, GREY)

    def paint(self, cv):
        if not (self.covers and getattr(cv, "pictures", False)):
            return self.paint_flat(cv)
        over, px = self.state == OVER, int(self.px)
        age = self.over_ms() if over else 0
        if over and age >= self.HIT_MS:
            pictures.draw(cv, "gravpong_crash", self.BOARD[0], self.BOARD[1])
        else:
            self.number(cv, self.INDEX[min(self.score, len(self.INDEX) - 1)], self.PLATE_RIGHT, self.PLATE_TOP)
        self.draw_crew(cv, px, self.tired(), over)
        self.fx.hide = over and age < self.HIT_MS
        k = BubbleLook.size_index(self.radius())
        if not over:
            y = self.bubble_y()
            if y > 60:  # its light on the floor, brighter as it comes down
                pictures.draw(cv, "gravpong_spot", int(self.bx) - self.SPOT_W // 2, self.FLOOR - self.SPOT_H + 2,
                              (y - 60) * (y - 60) // 300)
            down = int(self.by) > y  # down on the floor: squashed there, in the frame or two before the loss
            pose = BubbleLook.SQUASH if down else BubbleLook.pose(self.since_catch(), self.vy)
            self.draw_bubble(cv, int(self.bx), y, k, pose)
            return
        if age < self.HIT_MS:  # the hit-pause: the bubble held squashed on the floor, its glow flaring
            self.draw_bubble(cv, self.pop_x, self.pop_y, k, BubbleLook.SQUASH, 3)
            return
        frame = (age - self.HIT_MS) // self.POP_MS
        if frame < self.POP_FRAMES:
            pictures.draw(cv, self.POPS[frame], self.pop_x - self.POP // 2, self.pop_y - self.POP // 2)
        self.notes.draw(cv, self.last, self.FLOOR - 3, px, self.PY)

    def paint_flat(self, cv):
        """The look before BUBBLE, where there is no art: a fading trail and a square ball over a paddle."""
        for i, (tx, ty) in enumerate(self.trail):  # the ball's tail fades
            cv.fill(tx - 4 + i // 2, ty - 4 + i // 2, 8 - i // 2 * 2, 8 - i // 2 * 2, shade(60, 160, 180, 0.2 + i * 0.15))
        px, pw = int(self.px), self.net_width()
        cv.fill(px, self.PY, pw, 8, self.accent)
        cv.fill(px, self.PY, pw, 2, WHITE)
        cv.fill(px + (pw - 10 if self.pdir > 0 else 0), self.PY, 10, 8, YELLOW)  # the leading end
        cv.fill(self.bx - 6, self.by - 6, 12, 12, WHITE)
        cv.fill(self.bx - 3, self.by - 3, 4, 4, c565(190, 220, 255))

    def draw_title(self, cv):
        """BUBBLE: the title card; a coin on the empty net, then the bubble grows from it through its five sizes over
        1.2 s and wobbles; the best on its plate."""
        if not pictures.draw(cv, "gravpong_title", 0, 0):
            return Game.draw_title(self, cv)
        a, cx = self.age, 160
        if a < 240:
            pictures.draw(cv, "gravpong_coin", cx - self.COIN // 2, self.PY - self.COIN)
        else:
            k = min(4, (a - 240) * 5 // 960)
            r = self.SIZES[k] // 2
            look = BubbleLook
            pose = look.SQUASH if (a - 240) % 192 < 40 else (look.WOBBLE_A + a // 80 % 2 if a < 1500 else look.ROUND)
            self.draw_bubble(cv, cx, self.PY - r, k, pose)
        self.number(cv, BEST.get(self.name, 0), self.TITLE_BEST_RIGHT, self.TITLE_BEST_TOP)

    def draw_over(self, cv):
        """The pop and the notes play over the live scene first; then IT WAS NEVER REAL, the score and the best."""
        if self.over_ms() < self.CARD_MS:
            return
        if not pictures.draw(cv, "gravpong_over", self.CARD_X, self.CARD_Y):
            return Game.draw_over(self, cv)
        self.number(cv, self.score, self.SCORE_RIGHT, self.CARD_PLATE_TOP)
        self.number(cv, BEST.get(self.name, 0), self.BEST_RIGHT, self.CARD_PLATE_TOP)
        if self.age >= self.OVER_MS and (self.age // 400) % 2 == 0:
            cv.text("tap to retry", self.CARD_X + 52, self.CARD_Y + 86, self.BONE)
