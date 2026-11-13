"""
Drawing for the games: colours, a recording Canvas, and the Game base class.

A game's paint() does not draw pixels. It calls Canvas.fill, box, line, text and so on, and each call is RECORDED as a
tuple (x0, y0, x1, y1, kind, ...): the box it covers first, so equal tuples are equal pictures. render.py compares this
frame's tuples with the last frame's, finds the rectangles that changed, and the Canvas replays only the tuples inside
each rectangle into ONE buffer of 51,200 bytes (at most 25,600 pixels: 320x80, or a narrower, taller rectangle), which
the display blits. A still scene sends nothing; a moving sprite sends its old and new boxes.

Colours are PRE-SWAPPED: framebuf stores RGB565 little-endian but the ST7789 wants the high byte first, so c565()
returns the two bytes swapped and the buffer goes to the display as it is.
"""

import math
import random
import time

import framebuf

from fast import native
from st7789 import HEIGHT, WIDTH, rgb565

BUF_PX = 25600  # the buffer without PSRAM: 51,200 bytes
FULL_PX = 320 * 240  # with PSRAM: the whole screen, 153,600 bytes
FULL = (0, 0, WIDTH, HEIGHT)
# --- MVP (P599) ---
HUD_RECT = (0, 0, WIDTH, 16)  # a game's score bar, kept by Canvas.keep
LABEL_RECT = (0, 0, WIDTH, 14)  # a scene's one-line label (rain, fire), kept the same way


def c565(r, g, b):
    v = rgb565(r, g, b)
    return ((v & 0xFF) << 8) | (v >> 8)


BLACK, WHITE = c565(0, 0, 0), c565(255, 255, 255)
RED, GREEN, BLUE = c565(230, 40, 40), c565(40, 210, 70), c565(50, 90, 240)
YELLOW, CYAN, MAGENTA = c565(250, 220, 40), c565(40, 220, 230), c565(230, 60, 220)
ORANGE, GREY, DARK = c565(250, 140, 30), c565(120, 120, 130), c565(30, 30, 40)
ACCENT = c565(214, 40, 48)  # the one accent the restyled games share (P565 D5): art/brush.py's ACCENT
KEY = c565(8, 4, 8)  # the colour a sprite buffer keeps for 'clear'; no game uses it
PALETTE = (RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, MAGENTA, WHITE)


def shade(r, g, b, t):
    """A colour scaled by t (0..1), for fading with distance."""
    t = max(0.0, min(1.0, t))
    return c565(int(r * t), int(g * t), int(b * t))


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


GLYPHS = {}  # each character's dot runs, shared by every canvas


class Canvas:
    """Records what a game draws (fill, box, line, text, big, gradient, sprite, hill, disc), then replays a rectangle."""

    def __init__(self, full=False):
        """full: the board has PSRAM, so the buffer holds the whole screen and a second one keeps the background."""
        self.full, self.px = full, (FULL_PX if full else BUF_PX)
        self.buf = bytearray(self.px * 2)
        self.mv = memoryview(self.buf)
        self.bg = memoryview(bytearray(FULL_PX * 2)) if full else None
        self.reset_background()
        self.mono = framebuf.FrameBuffer(bytearray(16 * 8), 16 * 8, 8, framebuf.MONO_HLSB)  # scratch for big text
        self.cache = {}  # sprites, shapes and gradients, worked out once
        self.ops, self.clip, self.fb, self.view = [], FULL, None, None
        self.kept = {}  # rect: (key, the tuples draw recorded), for keep()

    def reset_background(self):
        self.bg_ok = False

    def build_background(self, colour):
        """Draw the recorded tuples once into self.bg, then forget them: they are the game's still picture."""
        fb = framebuf.FrameBuffer(self.bg, WIDTH, HEIGHT, framebuf.RGB565)
        fb.fill(colour)
        self.replay(fb, 0, 0, WIDTH, HEIGHT)
        self.ops, self.clip, self.bg_ok = [], FULL, True

    def start(self):
        self.ops, self.clip = [], FULL

    # --- MVP (P599) ---
    def keep(self, key, rect, draw, alpha=255):
        """draw(canvas) fills rect; it runs only when key changes, else its last tuples are recorded again (P599). The
        key names the caller, such as the game's name, so another game never reuses this one's tuples. The clip must be
        FULL, as Game.draw leaves it: lcd.TftCanvas.keep ignores the clip. The alpha is lcd.TftCanvas.keep's: this
        canvas has no blend, so its picture stays solid (P762)."""
        kept = self.kept.get(rect)
        if kept is not None and kept[0] == key:
            self.ops.extend(kept[1])
            return
        first = len(self.ops)
        draw(self)
        self.kept[rect] = (key, self.ops[first:])

    # --- recording ---
    def fill(self, x, y, w, h, c):
        x0, y0 = int(x), int(y)
        x1, y1 = x0 + int(w), y0 + int(h)
        cx0, cy0, cx1, cy1 = self.clip
        x0, y0, x1, y1 = max(x0, cx0), max(y0, cy0), min(x1, cx1), min(y1, cy1)
        if x1 > x0 and y1 > y0:
            self.ops.append((x0, y0, x1, y1, 0, c))

    def box(self, x, y, w, h, c):
        x0, y0 = int(x), int(y)
        x1, y1 = x0 + int(w), y0 + int(h)
        cx0, cy0, cx1, cy1 = self.clip
        if x1 > cx0 and x0 < cx1 and y1 > cy0 and y0 < cy1 and x1 > x0 and y1 > y0:
            self.ops.append((x0, y0, x1, y1, 1, c))

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = [clamp(int(v), -2000, 2000) for v in (x0, y0, x1, y1)]
        bx0, bx1, by0, by1 = min(x0, x1), max(x0, x1) + 1, min(y0, y1), max(y0, y1) + 1
        cx0, cy0, cx1, cy1 = self.clip
        if bx1 > cx0 and bx0 < cx1 and by1 > cy0 and by0 < cy1:
            self.ops.append((max(bx0, 0), max(by0, 0), min(bx1, WIDTH), min(by1, HEIGHT), 2, x0, y0, x1, y1, c))

    def text(self, words, x, y, c):
        x, y = int(x), int(y)
        if x < WIDTH and y < HEIGHT and y > -8:
            self.ops.append((max(x, 0), max(y, 0), min(x + 8 * len(words), WIDTH), min(y + 8, HEIGHT), 3, words, c, x, y))

    def big(self, words, x, y, c, scale=2):
        """Text with each dot of the 8x8 font drawn as a scale x scale block."""
        if not (-8 * scale < y < HEIGHT):
            return
        step = 8 * scale
        for ch in words:
            if ch != " ":
                for start, row, n in self.glyph(ch):
                    self.fill(x + start * scale, y + row * scale, n * scale, scale, c)
            x += step

    def glyph(self, ch):
        """The dots of one character as (start, row, length) runs, worked out once: a new score allocates nothing."""
        runs = GLYPHS.get(ch)
        if runs is None:
            self.mono.fill(0)
            self.mono.text(ch, 0, 0, 1)
            runs = []
            for row in range(8):
                col = 0
                while col < 8:
                    if self.mono.pixel(col, row):
                        start = col
                        while col < 8 and self.mono.pixel(col, row):
                            col += 1
                        runs.append((start, row, col - start))
                    else:
                        col += 1
            runs = GLYPHS[ch] = tuple(runs)
        return runs

    def gradient(self, y0, y1, top, bottom, step=8):
        """Bands of colour from top to bottom, each an (r, g, b); the sky, the cave, the dusk."""
        key = (y0, y1, top, bottom, step)
        colours = self.cache.get(key)
        if colours is None:
            n = max(1, (y1 - y0) // step)
            colours = self.cache[key] = [c565(*[int(a + (b - a) * i / n) for a, b in zip(top, bottom)]) for i in range(n)]
        for i, c in enumerate(colours):
            self.fill(0, y0 + i * step, WIDTH, step, c)

    def sprite(self, rows, palette, x, y, scale=1):
        """Rows of letters, each a colour in palette (a dict); '.' is clear. Drawn once into a small buffer, then one op."""
        key = (rows, scale)  # the rows, not id(rows): see TftCanvas.sprite
        art = self.cache.get(key)
        if art is None:
            w, h = len(rows[0]) * scale, len(rows) * scale
            art = self.cache[key] = (framebuf.FrameBuffer(bytearray(w * h * 2), w, h, framebuf.RGB565), w, h)
            art[0].fill(KEY)
            for j, row in enumerate(rows):
                for i, ch in enumerate(row):
                    if ch != ".":
                        art[0].fill_rect(i * scale, j * scale, scale, scale, palette[ch])
        x, y = int(x), int(y)
        cx0, cy0, cx1, cy1 = self.clip
        if x + art[1] > cx0 and x < cx1 and y + art[2] > cy0 and y < cy1:
            self.ops.append((x, y, x + art[1], y + art[2], 4, art[0], x, y))

    def hill(self, cx, base, half, height, c):
        """A triangle, drawn as rows two pixels high."""
        rects = self.cache.get(("h", half, height))
        if rects is None:
            rects = self.cache[("h", half, height)] = [
                (-(half * (dy + 2) // height), dy - height, 2 * (half * (dy + 2) // height), 2) for dy in range(0, height, 2)]
        for dx, dy, w, h in rects:
            self.fill(cx + dx, base + dy, w, h, c)

    def disc(self, cx, cy, r, c):
        rects = self.cache.get(("d", r))
        if rects is None:
            rects = self.cache[("d", r)] = [
                (-int(math.sqrt(max(0, r * r - dy * dy))), dy, 2 * int(math.sqrt(max(0, r * r - dy * dy))), 2)
                for dy in range(-r, r + 1, 2)]
        for dx, dy, w, h in rects:
            self.fill(cx + dx, cy + dy, w, h, c)

    # --- replaying ---
    def begin(self, x, y, w, h, colour):
        """Aim at the rectangle x, y, w, h of the screen and clear it (or copy the background in); view is its bytes."""
        self.view = self.mv[:w * h * 2]
        self.fb = framebuf.FrameBuffer(self.view, w, h, framebuf.RGB565)
        if not self.bg_ok:
            return self.fb.fill(colour)
        row = WIDTH * 2
        if w == WIDTH:
            self.view[:] = self.bg[y * row:(y + h) * row]
        else:
            for j in range((h)):
                at = (y + j) * row + x * 2
                self.view[j * w * 2:(j + 1) * w * 2] = self.bg[at:at + w * 2]

    def render(self, x, y, w, h):
        """Draw every recorded tuple, after the background's, that touches the rectangle begin() chose."""
        self.replay(self.fb, x, y, w, h)

    def replay(self, fb, x, y, w, h):
        x1, y1 = x + w, y + h
        for op in self.ops:
            if op[0] >= x1 or op[2] <= x or op[1] >= y1 or op[3] <= y:
                continue
            kind = op[4]
            if kind == 0:
                fb.fill_rect(op[0] - x, op[1] - y, op[2] - op[0], op[3] - op[1], op[5])
            elif kind == 1:
                fb.rect(op[0] - x, op[1] - y, op[2] - op[0], op[3] - op[1], op[5])
            elif kind == 2:
                fb.line(op[5] - x, op[6] - y, op[7] - x, op[8] - y, op[9])
            elif kind == 3:
                fb.text(op[5], op[7] - x, op[8] - y, op[6])
            else:
                fb.blit(op[5], op[6] - x, op[7] - y, KEY)


@native
def advance(particles, dt):
    for q in particles:
        q[0] += q[2] * dt
        q[1] += q[3] * dt
        q[3] += q[6] * dt
        q[4] -= dt


class Particles:
    """Sparks, smoke and feathers: [x, y, vx, vy, seconds left, colour, gravity]. At most MAX at once."""

    MAX = 40

    def __init__(self):
        self.p = []

    def burst(self, x, y, colour, n=8, speed=90.0, life=0.5, gravity=200.0):
        for _ in range(n):
            a, v = random.random() * 6.283, speed * (0.4 + random.random())
            self.p.append([x, y, math.cos(a) * v, math.sin(a) * v, life * (0.6 + random.random() * 0.6), colour, gravity])
        del self.p[:-self.MAX]

    def add(self, x, y, vx, vy, colour, life=0.4, gravity=0.0):
        self.p.append([x, y, vx, vy, life, colour, gravity])
        del self.p[:-self.MAX]

    def update(self, dt):
        advance(self.p, dt)
        self.p = [q for q in self.p if q[4] > 0]

    def draw(self, cv):
        for q in self.p:
            cv.fill(q[0], q[1], 3 if q[4] > 0.25 else 2, 3 if q[4] > 0.25 else 2, q[5])


class Dice:
    """A random stream of the effects' own (the ZX81's generator), so an effect never moves the game's random draws
    (P773: Meteors' and Bucket's painted effects)."""

    def __init__(self, seed=773):
        self.v = seed

    def below(self, n):
        self.v = (self.v * 75 + 74) % 65537
        return self.v % n

    def spread(self, n):
        """-n to n."""
        return self.below(2 * n + 1) - n


def hint_lines(hint):
    """The hint as the title shows it: one line, or two when it is wider than the screen, broken after the last comma
    that leaves a first line that fits (P800)."""
    if 8 * len(hint) <= WIDTH - 8:
        return (hint,)
    cut = hint.rfind(", ", 0, (WIDTH - 8) // 8)
    return (hint[:cut + 1], hint[cut + 2:]) if cut > 0 else (hint,)


BEST = {}  # best score of each game since the board started
TITLE, PLAY, OVER = 0, 1, 2


PHASES = [0] * 6  # bench: the slowest of each draw phase in microseconds: static, paint, fx, hud, over, title
PHASE_SUM = [0] * 6  # bench: the same phases summed since the last report, for the average per frame (P550)


def slowest(i, t):
    now = time.ticks_us()
    took = time.ticks_diff(now, t)
    PHASES[i] = max(PHASES[i], took)
    PHASE_SUM[i] += took
    return now


class Game:
    """One game: a title, play, game over. A subclass sets name, hint, bg and accent and writes setup(), play(pressed,
    held) and paint(cv). It calls self.die() to end the round and adds to self.score."""

    name = "game"
    hint = "tap to play"
    bg = BLACK
    accent = GREEN
    HUD_SCORE, HUD_BEST = WHITE, YELLOW  # the score bar's colours; a restyled game sets its own
    covers = False  # True: paint_static covers the whole screen, so no background fill goes under it (TftOut)
    plugins = ()  # the engine's layers the game turns on (plugins.Plugin), in their stage order; setup lists them
    signals = None  # --- MVP (P768) --- the game box's signals.Signals; a class attribute, as setup runs in __init__
    cues = {}  # --- MVP (P768) --- signal name -> cues.Cue: the sounds this game asks for
    TITLE_MS = 1500
    OVER_MS = 900

    def __init__(self):
        self.reset()

    def reset(self):
        self.state, self.since, self.last, self.age, self.dt, self.ms = TITLE, None, None, 0, 0.0, 0
        self.restart()

    def restart(self):
        self.score, self.t = 0, 0.0
        self.fx = Particles()
        self.setup()

    def setup(self):
        pass

    def play(self, pressed, held):
        pass

    def paint(self, cv):
        pass

    def emit(self, name, value=None):
        """Say what happened (P768). With no signals, in a test or a probe, it does nothing."""
        if self.signals is not None:
            self.signals.emit(name, value)

    def die(self, x=None, y=None, colours=(RED, YELLOW)):
        """End the round; at (x, y), a burst in the two colours."""
        self.emit("die")
        BEST[self.name] = max(BEST.get(self.name, 0), self.score)
        if x is not None:
            self.fx.burst(x, y, colours[0], 14, 170.0, 0.8)
            self.fx.burst(x, y, colours[1], 10, 110.0, 0.6)
        self.state, self.since = OVER, self.last

    def pop(self, x, y, colour=YELLOW):
        """A little burst for a point scored."""
        self.fx.burst(x, y, colour, 7, 80.0, 0.4, 120.0)

    def step(self, now_ms, pressed, held):
        if self.since is None:
            self.since = self.last = now_ms
        self.ms = min(time.ticks_diff(now_ms, self.last), 60)  # --- MVP (P633) --- an int, so the plugins get no float
        self.dt = self.ms / 1000
        self.last = now_ms
        self.fx.update(self.dt)
        self.age = time.ticks_diff(now_ms, self.since)
        if self.state == TITLE:
            if pressed or self.age >= self.TITLE_MS:
                self.state, self.since = PLAY, now_ms
        elif self.state == PLAY:  # --- MVP (P633) --- the plugins' stages (plugins.py), only while the game plays
            self.t += self.dt
            for plugin in self.plugins:  # FixedUpdate
                plugin.fixed_update(self.ms)
            self.play(pressed, held)  # Update
            for plugin in self.plugins:  # LateUpdate: read again, as a restart in play makes new plugins
                plugin.late_update(self.ms)
        elif pressed and self.age >= self.OVER_MS:
            self.restart()
            self.state, self.since = PLAY, now_ms

    def paint_static(self, cv):
        """What never moves. With PSRAM it is drawn once into the kept background; else it is recorded every frame."""

    def hud(self, cv):
        """The score bar, drawn again only when the score or the best changes (P599)."""
        cv.keep((self.name, self.score, BEST.get(self.name, 0)), HUD_RECT, self.draw_hud)

    def draw_hud(self, cv):
        cv.fill(0, 0, WIDTH, HUD_RECT[3], DARK)
        cv.big(str(self.score), 6, 0, self.HUD_SCORE, 2)
        best = "best %d" % max(self.score, BEST.get(self.name, 0))
        cv.text(best, WIDTH - 8 * len(best) - 6, 4, self.HUD_BEST)
        cv.text(self.name, WIDTH // 2 - 4 * len(self.name), 4, GREY)

    def draw(self, cv):
        t = time.ticks_us()
        if not cv.bg_ok:
            self.paint_static(cv)
            cv.clip = FULL
        t = slowest(0, t)
        if self.state == TITLE:
            self.draw_title(cv)
            slowest(5, t)
            return
        self.paint(cv)
        cv.clip = FULL
        t = slowest(1, t)
        self.fx.draw(cv)
        t = slowest(2, t)
        self.hud(cv)
        t = slowest(3, t)
        if self.state == OVER:
            self.draw_over(cv)
            slowest(4, t)

    def draw_over(self, cv):
        """The game-over box over the live scene. A game with its own end (stack's collapse) draws its own."""
        x, y = WIDTH // 2 - 100, HEIGHT // 2 - 50
        cv.fill(x, y, 200, 100, BLACK)
        cv.box(x, y, 200, 100, self.accent)
        cv.box(x + 3, y + 3, 194, 94, GREY)
        cv.big("game over", x + 28, y + 12, RED, 2)
        cv.text("score %d   best %d" % (self.score, BEST.get(self.name, 0)), x + 20, y + 48, WHITE)
        if self.age >= self.OVER_MS and (self.age // 400) % 2 == 0:
            cv.text("tap to retry", x + 52, y + 74, YELLOW)

    def draw_title(self, cv):
        a, cx, cy = self.age, WIDTH // 2, HEIGHT // 2
        for i in range(5):  # rectangles growing out of the middle, one after the other
            r = (a // 6 + i * 22) % 110
            cv.box(cx - r * 3 // 2, cy - r, 3 * r, 2 * r, shade(255, 255, 255, 1 - r / 110) if i % 2 else self.accent)
        cv.fill(0, cy - 44, WIDTH, 84, BLACK)
        cv.fill(0, cy - 44, WIDTH, 2, self.accent)
        cv.fill(0, cy + 38, WIDTH, 2, self.accent)
        cv.big(self.name, cx - 12 * len(self.name), cy - 36, PALETTE[(a // 90) % len(PALETTE)], 3)
        if (a // 300) % 2 == 0:  # a hint wider than the screen goes on two lines, broken after a comma (P800)
            lines = hint_lines(self.hint)
            for k, line in enumerate(lines):
                cv.text(line, cx - 4 * len(line), cy + 2 + 10 * k - 5 * (len(lines) - 1), WHITE)
        cv.text("best %d" % BEST.get(self.name, 0), cx - 28, cy + 22, YELLOW)
