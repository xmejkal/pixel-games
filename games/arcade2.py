"""Three more for one button: stack (tap drops the block), cave (hold to rise), gravity pong (tap turns the paddle)."""

import random

import pictures

from fast import native
from gfx import ACCENT, BEST, BLACK, GREEN, GREY, HEIGHT, ORANGE, OVER, RED, WHITE, WIDTH, YELLOW, Game, c565, shade
from motion import Bodies, Spring

W, H = WIDTH, HEIGHT


@native
def pile_under(pile, i):
    """The pile rule (P582): the floor that floor i of the pile rests on, or -1 for the street. It is the highest of
    the floors that stood under it in the tower, were released (a standing floor holds nothing up: it is still to
    fall) and overlap it by pile.overlap px or more. A floor's top is its rest_y less a floor's height: where it
    rests, or where a falling one will stop, so floors falling together land on each other. The tower's order is
    kept, so two floors never rest on each other and the street floor always reaches the street. It reads the pile
    and changes nothing."""
    b, w, h, overlap = pile.bodies, pile.w, pile.h, pile.overlap
    x, rest_y, live, released = b.x, b.rest_y, b.live, pile.released
    left, right = x[i], x[i] + w[i]
    plane, under = pile.street, -1
    for j in range(i):
        if live[j] and released[j] and rest_y[j] - h < plane and min(right, x[j] + w[j]) - max(left, x[j]) >= overlap:
            plane, under = rest_y[j] - h, j
    return under


class Pile:
    """The falling tower (P582): its floors as bodies, standing (asleep) where they were drawn until release() lets
    one go with a push. step() moves them and keeps the pile rule each frame: a falling floor aims at the top of
    what is under it now (pile_under), and a resting floor wakes when the floor it rests on moves or slides from
    under it. A floor that is never released (the basement) only stands."""

    def __init__(self, n, h, street, overlap=8):
        self.bodies, self.h, self.street, self.overlap = Bodies(n), h, street, overlap
        self.w, self.art, self.slide = [0] * n, [0] * n, [0.0] * n
        self.under, self.released = [-1] * n, [0] * n
        self.count = 0

    def add(self, x, y, w, art):
        """One more floor, standing at (x, y): asleep on its own plane until it is released."""
        j, b = self.count, self.bodies
        b.spawn(j, x, y, 0, 0, y)
        b.asleep[j] = 1
        self.w[j], self.art[j], self.slide[j], self.under[j], self.released[j] = w, art, 0.0, -1, 0
        self.count += 1

    def release(self, j, vx):
        self.released[j] = 1
        self.wake(j, vx)

    def wake(self, j, vx):
        b = self.bodies
        b.asleep[j], b.vx[j], b.vy[j] = 0, float(vx), 0.0
        self.settle(j)

    def settle(self, j):
        """Floor j's plane from the pile rule; one already past it is set on it. Answers whether the plane moved."""
        b = self.bodies
        u = self.under[j] = pile_under(self, j)
        plane = b.rest_y[u] - self.h if u >= 0 else self.street
        if plane == b.rest_y[j]:
            return False
        b.rest_y[j] = plane
        if b.y[j] > plane:  # a floor of the tower landed under it: up onto that one
            b.y[j] = plane
        return True

    def step(self, dt, gravity, restitution, friction, drag):
        """Fall, bounce and slide for dt s; a slide loses drag times itself per second and stops under 8 px/s. The
        pile rule runs once a frame for every released floor, bottom up, so a floor sees the plane of the one under it
        as it is this frame; a resting floor whose plane moves wakes, and one that slides on keeps its slide."""
        b = self.bodies
        b.step(dt, gravity, restitution, friction)
        x, w, live, asleep, slide, released = b.x, self.w, b.live, b.asleep, self.slide, self.released
        for j in range(self.count):
            if not live[j] or not released[j]:
                continue
            if not asleep[j]:
                slide[j] = b.vx[j]
            elif slide[j]:  # it slides on what it rests on
                x[j] += slide[j] * dt
                slide[j] -= slide[j] * drag * dt
                if -8.0 < slide[j] < 8.0:
                    slide[j] = 0.0
            if x[j] + w[j] < 0 or x[j] > W:
                b.free(j)
            elif self.settle(j) and asleep[j]:
                self.wake(j, slide[j])  # what it rests on moved, or it slid off

    def still(self):
        """Every floor at rest and no slide left: the collapse is over."""
        b = self.bodies
        for j in range(self.count):
            if b.live[j] and (not b.asleep[j] or self.slide[j]):
                return False
        return True


class Stack(Game):
    """RENT (P568): you build a tower of flats nobody will live in. The next floor hangs from a hook on a cable and
    slides straight across (a swing was tried; the PO found it unpredictable, 2026-11-02). A tap lets it go: it falls,
    and its landing presses the tower down and kicks it into a sway (P582); a perfect drop holds the world still for a
    beat; a miss falls past the top, the tower shakes, and its floors fall from the top down into a pile. Watercolour noir at noon: ink, bone and
    one accent."""

    INK, BONE = c565(24, 20, 30), c565(236, 230, 214)  # art/sets/stack.py's pair
    name = "stack"
    hint = "tap to drop"
    bg = c565(196, 192, 208)
    accent = HUD_BEST = ACCENT
    HUD_SCORE = BONE
    LEVEL_H, BASE = 14, 220
    KEPT = 9  # floors the view keeps: 12 before P582; 9 keeps the floor hanging HANG px up under the score bar
    SHOWN = KEPT + 2  # floors drawn at most: those the view keeps, and two sinking under the street
    HANG, G = 40, 2000.0  # the hanging floor's height over its landing row, and gravity: a 200 ms fall, at 400 px/s
    PRESS_K, PRESS_DAMP, PRESS_KICK = 150.0, 9.0, 0.5  # a landing's press: half its speed sinks the top about 7 px
    SPRING, DAMP, KICK = 250.0, 11.0, 7.0  # the tower's sway: about 2.5 Hz, settled in about 0.6 s
    MAX_SLABS, SLAB_VX = 4, 40.0  # cut-offs falling at once (a fifth frees the oldest); each drifts 40 px/s off the tower
    SLAB_BOUNCE, SLAB_FRICTION = 0.35, 0.6  # a slab keeps 35 % of its fall speed and 60 % of its drift at each bounce
    TURN = 3.0  # the cot on a slab turns 3 degrees per px the slab travels: a quarter turn every 30 px
    SHAKE = (3, -2, 2, -1)  # the death shake, one offset per 40 ms frame
    SHAKE_MS, CARD_MS = 160, 500  # the shake, then the floors fall; the card from 500 ms
    RELEASE_MS, PUSH = 40, 300.0  # top down, a floor every 40 ms, thrown lean * 300 * k px/s (k: its share of height)
    WRECK_BOUNCE, WRECK_FRICTION, WRECK_DRAG = 0.25, 0.5, 4.0  # a floor's bounce, its drift kept at a bounce, its slide
    HIT_MS, HIT_MIN = 80, 150  # at most one collapse_hit every 80 ms, for an impact of 150 px/s or more
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
        self.covers = pictures.load()  # the painted noon covers the screen, so no fill goes under it
        self.floors = [(90, 140)]  # (x, width) of each placed floor, x without the sway
        self.x, self.w, self.dir, self.speed = 0.0, 140, 1, 120.0
        self.sway = Spring(self.SPRING, self.DAMP)  # the tower top's offset
        self.press = Spring(self.PRESS_K, self.PRESS_DAMP)  # how far the tower top is pressed down by a landing
        self.falling = Bodies(1)  # the released floor as it falls, body 0
        self.drop = None  # the tap's result while its floor falls, built once: see release()
        self.hold, self.lean = 0, 1  # hitstop frames left; the side the tower falls to
        self.wreck = Pile(self.SHOWN, self.LEVEL_H, self.BASE)  # the tower once it falls: see collapse_start()
        self.basement, self.released, self.hit_ms = 0, 0, -self.HIT_MS  # floors in the wreck that only stand
        self.slabs = Bodies(self.MAX_SLABS)  # the cut-offs, falling and bouncing on the street
        n = self.MAX_SLABS  # and what a body does not keep: width, colour, the cot's turn in degrees, birth order
        self.slab_w, self.slab_art, self.slab_turn, self.slab_born, self.born = [0] * n, [0] * n, [0.0] * n, [0] * n, 0

    def level_y(self, i):
        return self.BASE - (i - max(0, len(self.floors) - self.KEPT) + 1) * self.LEVEL_H

    def floor_x(self, i):
        """Floor i's drawn x: its own, plus the sway, more of it the higher it sits in the visible window, so the
        floor at the street stays put. The hit test reads this too; paint works it out the same way."""
        first = max(0, len(self.floors) - self.SHOWN)
        return int(self.floors[i][0] + self.sway.value / (len(self.floors) - first) * (i - first))

    def hanging_x(self):
        """The hanging floor's drawn x: the straight slide, as before RENT."""
        return int(self.x)

    def step(self, now_ms, pressed, held):
        """Game.step; over, the collapse runs on: the wreck, the missed floor and the slabs. Not on the frame the round
        ends, whose age is still the round's."""
        was = self.state
        Game.step(self, now_ms, pressed, held)
        if self.state == OVER:
            if was == OVER:
                self.collapse(self.dt)
            else:
                self.age = 0  # the round's age, else draw_over shows the card for this one frame

    def play(self, pressed, held):
        if self.hold:  # the hitstop after a perfect drop: the tower and the hanging floor stand still for two frames
            self.hold -= 1
            return
        dt = self.dt
        self.move_slabs(dt)
        self.sway.step(dt)
        self.press.step(dt)
        if self.drop:  # a floor is falling: no tap counts and the slide waits
            return self.fall(dt)
        self.x += self.dir * self.speed * dt
        if self.x < 0:
            self.x, self.dir = 0.0, 1
        elif self.x > W - self.w:
            self.x, self.dir = float(W - self.w), -1
        if pressed:
            self.release()

    def release(self):
        """The tap lets the floor go where it hangs. Its overlap, its cut and the perfect test are decided now, so the
        tap alone decides what the fall ends in; fall() carries it out at the first impact."""
        n = len(self.floors)
        tx, tw = self.floor_x(n - 1), self.floors[-1][1]
        x, y = self.hanging_x(), self.level_y(n)
        left, right = max(x, tx), min(x + self.w, tx + tw)
        miss = right - left < 4
        perfect = not miss and abs(x - tx) < 4  # a perfect drop keeps the whole width
        if miss:
            self.lean = 1 if x > tx else -1
        elif perfect:
            left, right = tx, tx + tw
        first = max(0, n + 1 - self.SHOWN)  # the window once this floor is in it
        stored = left - self.sway.value / (n + 1 - first) * (n - first)  # without the sway, as floors keeps x
        push = max(-24, min(24, x - tx))  # how far off the floor under it it lands: the sway's kick
        self.drop = (x, left, right, stored, push, miss, perfect)
        self.falling.spawn(0, x, y - self.HANG, 0, 0, H if miss else y)  # a miss has no plane on screen

    def fall(self, dt):
        """The released floor falls as body 0. At its first impact it joins the tower with what the tap decided; a
        miss falls on, and the round ends as it passes the tower top."""
        b = self.falling
        b.step(dt, self.G, 0.0, 1.0)
        x, left, right, stored, push, miss, perfect = self.drop
        n = len(self.floors)
        y = self.level_y(n)
        if miss:
            if b.y[0] >= y:
                self.collapse_start()
            return
        if not (b.hit[0] or b.asleep[0]):
            return
        speed = b.hit[0]
        b.free(0)
        self.drop = None
        i = n % 8
        if perfect:  # it glows and holds the world still
            self.hold = 2
            self.fx.burst(left + (right - left) // 2, y, self.BONE, 10, 120.0, 0.5, 100.0)
            self.fx.burst(left + (right - left) // 2, y, ACCENT, 14, 160.0, 0.6, -60.0)
        elif x < left:  # the cut-off drifts away from the tower, falling at the landing's speed
            self.cut_off(x, y, left - x, i, -self.SLAB_VX, speed)
        elif x + self.w > right:
            self.cut_off(right, y, x + self.w - right, i, self.SLAB_VX, speed)
        self.floors.append((stored, right - left))
        self.sway.kick(push * self.KICK)  # the tower leans the way the floor landed
        self.w = right - left
        self.landing(left + self.w // 2, y + self.LEVEL_H, speed)
        self.score += 1
        self.pop(left + self.w // 2, y, self.INK)
        self.speed = min(330.0, 120 + self.score * 8)

    def cut_off(self, x, y, w, i, vx, vy):
        """A slab w px wide falls from (x, y) with its cot, in a free body, or else in the oldest one's."""
        s, born = self.slabs, self.slab_born
        j = 0
        for k in range(self.MAX_SLABS):
            if not s.live[k]:
                j = k
                break
            if born[k] < born[j]:
                j = k
        s.spawn(j, x, y, vx, vy, self.BASE)
        self.born += 1
        self.slab_w[j], self.slab_art[j], self.slab_turn[j], born[j] = w, i, 0.0, self.born

    def move_slabs(self, dt):
        """The slabs fall and bounce on the street, each bounce a slab_hit; their cots turn with the distance they
        travel. One that drifts off the screen is freed; one at rest sleeps on the street."""
        s = self.slabs
        s.step(dt, self.G, self.SLAB_BOUNCE, self.SLAB_FRICTION)
        for j in range(self.MAX_SLABS):
            if not s.live[j]:
                continue
            w = self.slab_w[j]
            if s.x[j] + w < 0 or s.x[j] > W:
                s.free(j)
                continue
            if s.hit[j]:
                self.slab_hit(int(s.x[j]) + w // 2, self.BASE + 8, s.hit[j])
            if not s.asleep[j]:
                self.slab_turn[j] += (abs(s.vx[j]) + abs(s.vy[j])) * dt * self.TURN

    # The four moments P583 hangs its effects on; each fires a burst today, and the callers stay.

    def landing(self, x, y, speed):
        """A floor lands at speed px/s: the tower takes half of it as a press, so it sinks a few px and springs back
        once; a puff of dust where the floors meet at (x, y)."""
        self.press.kick(self.PRESS_KICK * speed)
        self.fx.burst(x, y, self.BONE, 8, 60.0, 0.35, 120.0)

    def slab_hit(self, x, y, speed):
        """A cut-off slab meets the street at speed px/s, at each bounce: the cot on it rattles."""
        self.fx.burst(x, y, GREY, 8, 70.0, 0.5, 200.0)

    def collapse_start(self):
        """The missed floor has passed the tower top: the round ends, the tower shakes, and its floors fall from the
        top down. The wreck starts as the tower is drawn now, pressed and swaying; a floor that reaches below the
        street is the basement: it stays where it stands."""
        n = len(self.floors)
        first = max(0, n - self.SHOWN)
        sink = 0.0 if self.press.settled() else self.press.value / (n - first)
        self.wreck.count, self.basement, self.released = 0, 0, 0
        for i in range(first, n):
            y = self.level_y(i) + min(self.LEVEL_H - 2, int(sink * (i - first)))
            if y < H:
                self.wreck.add(self.floor_x(i), y, self.floors[i][1], i)
                if y + self.LEVEL_H > self.BASE:
                    self.basement += 1
        self.die(int(self.falling.x[0]) + self.w // 2, self.level_y(len(self.floors)), (ACCENT, self.INK))

    def collapse(self, dt):
        """After the shake, one floor every RELEASE_MS from the top, thrown the way the tower leans as a tipping tower
        throws it, faster the higher it stood; the street floor goes last, the basement never. A hard impact is a
        collapse_hit, one at most every HIT_MS."""
        wreck, n, low = self.wreck, self.wreck.count, self.basement
        while self.released < n - low and self.age >= self.SHAKE_MS + self.released * self.RELEASE_MS:
            j = n - 1 - self.released
            wreck.release(j, self.lean * self.PUSH * (j - low) / max(1, n - 1 - low))
            self.released += 1
        wreck.step(dt, self.G, self.WRECK_BOUNCE, self.WRECK_FRICTION, self.WRECK_DRAG)
        b, top = wreck.bodies, -1
        for j in range(n):
            if b.hit[j] >= self.HIT_MIN and (top < 0 or b.hit[j] > b.hit[top]):
                top = j
        if top >= 0 and self.age - self.hit_ms >= self.HIT_MS:
            self.hit_ms = self.age
            self.collapse_hit(int(b.x[top]) + wreck.w[top] // 2, int(b.y[top]) + self.LEVEL_H, b.hit[top])
        if self.falling.live[0]:  # the missed floor falls on, out of the picture, and is let go there
            self.falling.step(dt, self.G, 0.0, 1.0)
            if self.falling.asleep[0]:
                self.falling.free(0)
        self.move_slabs(dt)

    def collapsed(self):
        """Every floor that falls has fallen and come to rest."""
        return self.released == self.wreck.count - self.basement and self.wreck.still()

    def collapse_hit(self, x, y, speed):
        """A falling floor meets the pile or the street at speed px/s: one cloud of dust."""
        self.fx.burst(x, y, GREY, 10, 90.0, 0.8, -40.0)

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
        """The tower, pressed down by its last landing, the hanging or falling floor and the slabs. Over, the wreck in
        its place: it shakes, then its floors fall."""
        n, shake, over = len(self.floors), 0, self.state == OVER
        if over:
            if 0 <= self.age < self.SHAKE_MS:
                shake = self.SHAKE[self.age // 40]
            self.paint_wreck(cv, shake)
        first = n if over else max(0, n - self.SHOWN)  # over, no floor stands
        span, top = max(1, n - first), n - 1
        step = self.sway.value / span  # the sway per floor up the visible window, as floor_x works it out
        sink = 0.0 if self.press.settled() else self.press.value / span  # the press, the same way: none at the street
        most = self.LEVEL_H - 2  # a deeper press would draw a floor's pencil line over the one under it
        for i in range(first, n):
            x, w = self.floors[i]
            x, y = int(x + step * (i - first)), self.level_y(i)
            if sink:
                y += min(most, int(sink * (i - first)))
            self.block(cv, x, y, w, i, i == top)  # only the top floor is the show flat, lit
            if self.hold == 2 and i == top:  # the perfect drop's one white frame
                cv.fill(x, y, w, self.LEVEL_H, WHITE)
        hang = self.level_y(n) - self.HANG
        if self.drop:  # the floor falls, the empty hook stays where the tap let it go
            x = self.drop[0]
            self.hook(cv, x + self.w // 2, hang, x + self.w // 2)
            x, y = x + shake, int(self.falling.y[0])
        else:
            x, y = self.hanging_x() + shake, hang
            if y < H:
                self.hook(cv, x + self.w // 2, y, int(self.x) + self.w // 2)
        if y < H:
            self.block(cv, x, y, self.w, n, True)
        s = self.slabs
        for j in range(self.MAX_SLABS):  # each carries a cot, turning as it travels
            if not s.live[j]:
                continue
            x, y, w = int(s.x[j]), int(s.y[j]), self.slab_w[j]
            if y >= H:  # the guard (c8bda9d): nothing is drawn below the screen
                continue
            self.block(cv, x, y, w, self.slab_art[j], True)
            k = int(self.slab_turn[j] // 90) % 4
            if s.asleep[j] and not k % 2:  # at rest it lies on a side frame
                k += 1
            pictures.draw(cv, self.COTS[k], x + w // 2 - 8, y - 12)
        if not over or not pictures.draw(cv, "stack_sold", self.SOLD_X, self.SOLD_Y):
            self.number(cv, self.RENT + self.RENT_PER_FLOOR * self.score, self.PLATE_RIGHT, self.PLATE_TOP)

    def paint_wreck(self, cv, shake):
        """The falling tower, bottom floor first so a floor that lands on another is drawn over it; the top one lit."""
        wreck = self.wreck
        b, n = wreck.bodies, wreck.count
        for j in range(n):
            if b.live[j] and b.y[j] < H:
                self.block(cv, int(b.x[j]) + shake, int(b.y[j]), wreck.w[j], wreck.art[j], j == n - 1)

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
