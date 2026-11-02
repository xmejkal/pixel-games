"""Paint the runner's art in a pencil and watercolour style, and write it for the board.

Run from the repository root: python3 art/paint.py. Standard library and PIL only, deterministic (fixed seed).
Writes games/art/<name>.bin (RGB565 big-endian, panel layout), games/art_index.py and art/preview.png.

The background is painted at 4x and shrunk, so washes and pencil grain stay soft. A sprite is painted at 8x as
watercolour parts, shrunk, cut to a hard mask (every pixel fully on or off: the board skips one key colour), and
given a pencil outline outside its shape, tinted by the colour it borders.
"""

import os
import random
from math import cos, pi, sin

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, GROUND = 320, 240, 192
KEY = 0xF81F  # the transparent pixel, RGB565 as written (big-endian bytes F8 1F)
NUDGE = 0xF81E  # an opaque pixel that would be the key
GRAPHITE = (58, 50, 62)
rnd = random.Random(562)


# --- paint helpers -----------------------------------------------------------------------------------------------

def noise(size, cell, period=None):
    """Smooth value noise, 0..255 around 128: random cells enlarged with bicubic. With a period (in pixels) it
    repeats across x, so a strip painted with it tiles."""
    w, h = size
    ch = max(2, h // cell + 3)
    if period is None:
        cw = max(2, w // cell + 3)
        small = Image.frombytes("L", (cw, ch), rnd.randbytes(cw * ch))
        return small.resize((cw * cell, ch * cell), Image.BICUBIC).crop((cell, cell, cell + w, cell + h))
    n, tiles = max(1, round(period / cell)), w // period + 3
    block = Image.frombytes("L", (n, ch), rnd.randbytes(n * ch))
    small = Image.new("L", (n * tiles, ch))
    for i in range(tiles):
        small.paste(block, (i * n, 0))
    big = small.resize((period * tiles, ch * cell), Image.BICUBIC)
    return big.crop((period, cell, period + w, cell + h))


def autocontrast(img):
    lo, hi = img.getextrema()
    return img.point(lambda v: int((v - lo) * 255 / max(1, hi - lo)))


def scale(img, k, offset=0):
    return img.point(lambda v: max(0, min(255, int(v * k + offset))))


def solid(size, colour):
    return Image.new("RGB", size, colour)


def blur(img, r):
    return img.filter(ImageFilter.GaussianBlur(r))


def glaze(base, mask, colour, alpha):
    """A transparent glaze that multiplies, for shadows and warm light."""
    tint = Image.composite(solid(base.size, colour), solid(base.size, (255, 255, 255)),
                           mask.point(lambda v: int(v * alpha)))
    base.paste(ImageChops.multiply(base, tint))


def lay(base, mask, colour, alpha=1.0):
    """Opaque-ish paint, laid over what is there."""
    base.paste(Image.composite(solid(base.size, colour), base, mask.point(lambda v: int(v * alpha))))


class Strip:
    """A band of game rows painted at S times its size. A wrapped strip is painted three times as wide with every
    shape and every noise repeated each period, then its middle copy is kept, so its left and right edges join."""

    S = 4

    def __init__(self, w, top, h, wrap, backdrop):
        self.w, self.top, self.h, self.wrap = w, top, h, wrap
        self.period = w * self.S if wrap else None
        self.size = ((3 * w if wrap else w) * self.S, h * self.S)
        self.rgb = solid(self.size, (255, 255, 255))
        if callable(backdrop):  # a colour per game row
            d = ImageDraw.Draw(self.rgb)
            for y in range(self.size[1]):
                d.line([(0, y), (self.size[0], y)], fill=backdrop(top + y / self.S))
        else:
            self.rgb.paste(backdrop, (0, 0, *self.size))
        self.cover = Image.new("L", self.size, 0 if wrap or backdrop is None else 255)

    def xs(self, x):
        """Hi-res x of each copy of game x."""
        return [x * self.S + k * self.period for k in range(3)] if self.wrap else [x * self.S]

    def pt(self, x, y):
        return [(px, (y - self.top) * self.S) for px in self.xs(x)]

    def mask(self):
        return Image.new("L", self.size, 0)

    def ellipse(self, m, x, y, rx, ry, fill=255):
        d = ImageDraw.Draw(m)
        for px, py in self.pt(x, y):
            d.ellipse((px - rx * self.S, py - ry * self.S, px + rx * self.S, py + ry * self.S), fill=fill)

    def polygon(self, m, pts, fill=255):
        d = ImageDraw.Draw(m)
        for k in range(3 if self.wrap else 1):
            d.polygon([self.pt(x, y)[k] for x, y in pts], fill=fill)

    def noise(self, cell):
        return noise(self.size, cell, self.period)

    def roughen(self, m, r, amount, cell):
        """A wash's ragged edge: blur the shape, push it with noise, cut again."""
        n = scale(self.noise(cell), amount, 128 - 128 * amount)
        return ImageChops.add(blur(m, r), n, 1.0, -128).point(lambda v: 255 if v > 127 else 0)

    def wash(self, m, colour, alpha=0.9, rim=0.5, rim_px=6, grain=0.25, cell=40, rough=(3, 0.5, 12), dark=0.75,
             soft=1.2, cover=True):
        """One watercolour wash: ragged edge, uneven pigment, a darker dried rim."""
        if rough:
            m = self.roughen(m, *rough)
        m = blur(m, soft) if soft else m
        n = self.noise(cell)
        a = ImageChops.multiply(m, n.point(lambda v: int(255 * alpha * (1 - grain + grain * v / 255))))
        self.rgb.paste(Image.composite(solid(self.size, colour), self.rgb, a))
        if rim:
            edge = scale(ImageChops.subtract(m, blur(m, rim_px)), 2.2 * rim)
            lay(self.rgb, edge, tuple(int(c * dark) for c in colour))
        if cover:
            self.cover = ImageChops.lighter(self.cover, m)
        return m

    def pencil(self, strokes, width=2, strength=0.55, colour=GRAPHITE):
        """Graphite strokes in game coordinates, broken up by grain, multiplied on."""
        layer = self.mask()
        d = ImageDraw.Draw(layer)
        for pts, w in strokes:
            for k in range(3 if self.wrap else 1):
                d.line([self.pt(x, y)[k] for x, y in pts], fill=255, width=w or width, joint="curve")
        grain = self.noise(2).point(lambda v: 255 if v > 90 else 120)
        glaze(self.rgb, blur(ImageChops.multiply(layer, grain), 0.6), colour, strength)

    def paper(self, strength):
        """The paper's tooth: a faint, slightly coarse grain."""
        tooth = blur(self.noise(5), 1.2).point(lambda v: 255 - int(max(0, 150 - v) * strength))
        self.rgb = ImageChops.multiply(self.rgb, Image.merge("RGB", (tooth, tooth, tooth)))

    def hires(self):
        """The kept copy at S times: (rgb, cover)."""
        if not self.wrap:
            return self.rgb, self.cover
        box = (self.period, 0, 2 * self.period, self.size[1])
        return self.rgb.crop(box), self.cover.crop(box)

    def game(self, keyed):
        """The strip at game size: RGBA, with a hard mask when keyed."""
        w = (3 if self.wrap else 1) * self.w
        rgb = self.rgb.resize((w, self.h), Image.LANCZOS)
        a = self.cover.resize((w, self.h), Image.BOX).point(lambda v: 255 if v >= 128 or not keyed else 0)
        if self.wrap:
            rgb, a = rgb.crop((self.w, 0, 2 * self.w, self.h)), a.crop((self.w, 0, 2 * self.w, self.h))
        out = rgb.convert("RGBA")
        out.putalpha(a)
        return out


def jitter(pts, j):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        steps = max(1, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / 1.5))
        for i in range(steps):
            t = i / steps
            out.append((x0 + (x1 - x0) * t + rnd.uniform(-j, j), y0 + (y1 - y0) * t + rnd.uniform(-j, j)))
    out.append(pts[-1])
    return out


def ridge(w, base, heights, rough, depth=6):
    """A ridge that repeats every w game px, by midpoint displacement: (x, y) points from 0 to w."""
    pts = [(w * i / len(heights), base - hh) for i, hh in enumerate(heights)] + [(w, base - heights[0])]
    amp = rough
    for _ in range(depth):
        nxt = [pts[0]]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            nxt += [((ax + bx) / 2, (ay + by) / 2 + rnd.uniform(-amp, amp)), (bx, by)]
        pts, amp = nxt, amp * 0.5
    return pts


def peaks(pts, gap):
    """Local tops of a ridge, at least gap game px apart."""
    tops = []
    for i in range(1, len(pts) - 1):
        if pts[i][1] <= pts[i - 1][1] and pts[i][1] <= pts[i + 1][1]:
            if not tops or pts[i][0] - tops[-1][0] > gap:
                tops.append(pts[i])
            elif pts[i][1] < tops[-1][1]:
                tops[-1] = pts[i]
    return tops


# --- the background, as parallax layers --------------------------------------------------------------------------

SKY_TOP, SKY_LOW = (248, 140, 104), (255, 224, 160)
STRIP = 640  # a parallax strip's width in game px


def sky_at(y):
    t = max(0.0, min(1.0, (y - 4) / (GROUND - 4)))
    return tuple(int(a + (b - a) * t) for a, b in zip(SKY_TOP, SKY_LOW))


def paint_sky():
    """Static: the sky wash with soft blooms, the sun and its halo."""
    s = Strip(W, 0, H, False, sky_at)
    blooms = autocontrast(blur(s.noise(240), 30))
    glaze(s.rgb, scale(blooms, 1.4, -150), (255, 196, 170), 0.45)  # warm blooms
    glaze(s.rgb, scale(ImageChops.invert(blooms), 1.2, -160), (236, 192, 218), 0.4)  # a lilac breath
    sx, sy, sr = 250, 70, 22
    halo = s.mask()
    s.ellipse(halo, sx, sy, sr * 2.6, sr * 2.6, 140)
    lay(s.rgb, blur(halo, sr * 4), (255, 240, 196))
    disc = s.mask()
    s.ellipse(disc, sx, sy, sr, sr)
    s.wash(disc, (255, 247, 205), alpha=0.97, rim=0.3, rim_px=10, grain=0.06, rough=(3, 0.4, 14), dark=0.96, soft=2)
    s.paper(0.03)
    return s


def paint_clouds():
    """Soft cumulus with violet bellies, a peach top and a light pencil touch; transparent between them."""
    top, h = 16, 94
    s = Strip(STRIP, top, h, True, sky_at)
    lines = []
    for cx, cy, cw in ((70, 62, 84), (200, 94, 48), (322, 54, 64), (455, 88, 96), (575, 50, 46)):
        bumps = []  # (x, y, r): a low row of small puffs and a high row of big ones, on a flat base at cy
        n = max(3, round(cw / 16))
        for i in range(n):
            t = (i + 0.5) / n - 0.5
            r = cw / n * 0.66 * (1 - 0.4 * (2 * t) ** 2) * rnd.uniform(0.9, 1.1)
            bumps.append((cx + t * cw * 0.8, cy - r * 0.6, r))
        m_hi = max(1, n // 2)
        for i in range(m_hi):
            t = (i + 0.5) / m_hi - 0.5
            r = cw * 0.24 * rnd.uniform(0.85, 1.1) * (1.0 if m_hi == 1 else 0.85)
            bumps.append((cx + t * cw * 0.45 + rnd.uniform(-2, 2), cy - r * 0.95 - cw * 0.06, r))
        puff = s.mask()
        for x, y, r in bumps:
            s.ellipse(puff, x, y, r, r * 0.92)
        flat = s.mask()
        s.polygon(flat, [(cx - cw, cy), (cx + cw, cy), (cx + cw, cy + 40), (cx - cw, cy + 40)])
        puff = ImageChops.subtract(puff, flat)
        m = s.wash(puff, (255, 247, 236), alpha=0.98, rim=0.25, rim_px=3, grain=0.08, cell=20, rough=(3, 0.45, 10),
                   dark=0.93, soft=2)
        belly = s.mask()
        s.polygon(belly, [(cx - cw, cy - cw * 0.16), (cx + cw, cy - cw * 0.13), (cx + cw, cy + 4), (cx - cw, cy + 4)])
        belly = ImageChops.multiply(s.roughen(blur(belly, 4), 6, 0.7, 12), m)
        s.wash(belly, (206, 178, 214), alpha=0.7, rim=0.7, rim_px=3, grain=0.3, cell=10, rough=None, dark=0.85,
               soft=2.5, cover=False)
        warm = s.mask()
        for x, y, r in bumps:
            s.ellipse(warm, x + r * 0.3, y - r * 0.3, r * 0.6, r * 0.5)
        glaze(s.rgb, ImageChops.multiply(blur(warm, 6), m), (255, 214, 178), 0.55)
        for x, y, r in bumps:  # the pencil: a broken arc over each bump's top
            if rnd.random() < 0.7:
                a0, a1 = rnd.uniform(3.5, 4.0), rnd.uniform(5.1, 5.7)
                arc = [(x + r * 0.97 * cos(a0 + (a1 - a0) * i / 8), y + r * 0.9 * sin(a0 + (a1 - a0) * i / 8))
                       for i in range(9)]
                lines.append((arc, 2))
        lines.append((jitter([(cx - cw * 0.4, cy - 0.6), (cx + cw * 0.35, cy - 0.6)], 0.2), 2))
    s.pencil(lines, strength=0.28, colour=(120, 96, 128))
    s.paper(0.04)
    return s


def paint_far():
    """The far mountains: a pale cool range, a warmer plum range before it, peaks lit from the right."""
    top, h = 70, 100
    s = Strip(STRIP, top, h, True, sky_at)
    for base, heights, rough, col, dark, shade in (
            (156, [30, 50, 28, 44, 56, 32, 48, 38, 52, 26], 14, (178, 164, 204), 0.88, (160, 140, 186)),
            (170, [14, 34, 22, 42, 18, 30, 46, 20, 36, 26], 12, (176, 116, 136), 0.8, (126, 86, 126))):
        r = ridge(STRIP, base, heights, rough)
        r = [(x, min(y, top + h - 2)) for x, y in r]
        m = s.mask()
        s.polygon(m, r + [(STRIP, top + h + 4), (0, top + h + 4)])
        m = s.wash(m, col, alpha=0.96, rim=0.6, rim_px=6, grain=0.3, cell=20, rough=(1.5, 0.35, 8), dark=dark,
                   soft=1)
        wedge = s.mask()
        for px, py in peaks(r, 18):  # the shadow side, left of each peak, and a lit edge right of it
            s.polygon(wedge, [(px, py), (px - 34, top + h + 4), (px + 4, top + h + 4)])
        glaze(s.rgb, ImageChops.multiply(blur(wedge, 22), m), shade, 0.4)
        mist = s.mask()
        mist.paste(Image.linear_gradient("L").resize((s.size[0], 24 * s.S)), (0, (h - 24) * s.S))
        glaze(s.rgb, ImageChops.multiply(mist, m), (236, 200, 206), 0.35)
    s.paper(0.1)
    return s


def paint_hills():
    """The near hills in sunset light: a sage band, a fresh green band, shrubs and small round trees."""
    top, h = 120, 75
    s = Strip(STRIP, top, h, True, (160, 110, 128))
    trees = []
    for base, amp, col, k, dots in ((158, 12, (166, 180, 104), 3, 22), (176, 9, (120, 170, 80), 5, 16)):
        pts = [(x, base - amp * (0.5 + 0.5 * sin(2 * pi * k * x / STRIP) * cos(2 * pi * 2 * x / STRIP + k)))
               for x in range(0, STRIP + 1, 2)]
        m = s.mask()
        s.polygon(m, pts + [(STRIP, top + h + 4), (0, top + h + 4)])
        m = s.wash(m, col, alpha=0.97, rim=0.6, rim_px=6, grain=0.35, cell=16, rough=(1.5, 0.35, 8), dark=0.78,
                   soft=1)
        bushes = s.mask()  # shrubs sitting on the crest, and a few lower down
        for i in range(dots):
            x = (i + rnd.uniform(0.1, 0.9)) * STRIP / dots
            low = rnd.random() < 0.12
            y = pts[int(x / 2)][1] + (rnd.uniform(5, 10) if low else 0.8)
            rx = rnd.uniform(2.5, 5)
            s.ellipse(bushes, x, y - rx * 0.3, rx, rx * 0.65)
        s.wash(bushes, tuple(int(c * 0.74) for c in col), alpha=0.9, rim=0.6, rim_px=3, grain=0.3, cell=8,
               rough=(1, 0.4, 4), dark=0.75, soft=1)
        shade = s.mask()
        shade.paste(Image.linear_gradient("L").resize((s.size[0], 14 * s.S)), (0, (base + 2 - top) * s.S))
        glaze(s.rgb, ImageChops.multiply(shade, m), (170, 150, 120), 0.3)
    for i, x in enumerate((40, 150, 236, 330, 420, 530, 600)):  # little round trees on the back band
        y = 158 - 12 * (0.5 + 0.5 * sin(2 * pi * 3 * x / STRIP) * cos(2 * pi * 2 * x / STRIP + 3)) + 2
        crown = s.mask()
        s.ellipse(crown, x, y - 6, 3.4 + i % 2, 4.4 + i % 2)
        s.wash(crown, (92, 138, 76), alpha=0.95, rim=0.7, rim_px=3, grain=0.2, cell=8, rough=(0.8, 0.3, 4),
               dark=0.68, soft=0.8)
        trees.append(([(x, y + 1), (x, y - 4)], 4))
    s.pencil(trees, strength=0.55)
    s.paper(0.1)
    return s


def paint_ground():
    """Grass at y 192 to 197 with pencil blades, earth below with pebbles and hatching. Opaque."""
    top, h = 190, H - 190
    s = Strip(STRIP, top, h, True, (112, 162, 74))  # the near hill's foot, behind the blade tips
    g = GROUND
    grass = s.mask()
    s.polygon(grass, [(0, g), (STRIP, g), (STRIP, g + 5), (0, g + 5)])
    s.wash(grass, (110, 190, 60), alpha=1.0, rim=0.0, grain=0.25, cell=10, rough=None, soft=0)
    blades, lines = s.mask(), []
    for i in range(STRIP):
        x = i + rnd.uniform(0, 1)
        hh, lean = rnd.uniform(0.8, 2.6), rnd.uniform(-1, 1)
        for px, py in zip(s.xs(x), s.xs(x + lean)):
            ImageDraw.Draw(blades).line([(px, (g + 2 - top) * s.S), (py, (g - hh - top) * s.S)], fill=255, width=3)
        if i % 3 == 0:
            lines.append(([(x, g + 1.5), (x + lean * 1.4, g - hh - 0.6)], 2))
    lay(s.rgb, blur(blades, 0.6), (86, 164, 50))
    lines.append((jitter([(0, g + 0.4), (STRIP, g + 0.4)], 0.25), 2))
    s.pencil(lines, strength=0.5, colour=(38, 70, 30))
    earth = s.mask()
    s.polygon(earth, [(0, g + 5), (STRIP, g + 5), (STRIP, H + 2), (0, H + 2)])
    s.wash(earth, (134, 84, 44), alpha=1.0, rim=0.0, grain=0.25, cell=24, rough=None, soft=0)
    stain = autocontrast(blur(s.noise(60), 6))
    glaze(s.rgb, ImageChops.multiply(earth, scale(stain, 1.4, -150)), (160, 120, 80), 0.5)
    band = s.mask()
    s.polygon(band, [(0, g + 5), (STRIP, g + 5), (STRIP, g + 9), (0, g + 9)])
    glaze(s.rgb, blur(band, 6), (120, 76, 48), 0.45)  # the shade under the grass
    hatch = []
    for _ in range(40):
        x, y = rnd.uniform(0, STRIP), rnd.uniform(g + 12, H - 4)
        for i in range(rnd.randrange(3, 6)):
            hatch.append(([(x + i * 1.6, y), (x + i * 1.6 + 2.6, y - 3)], 2))
    s.pencil(hatch, strength=0.35, colour=(70, 40, 22))
    pebbles, rims = s.mask(), []
    for _ in range(36):
        x, y = rnd.uniform(0, STRIP), rnd.uniform(g + 11, H - 5)
        rx, ry = rnd.uniform(1.4, 3.0), rnd.uniform(1.0, 1.8)
        s.ellipse(pebbles, x, y, rx, ry)
        rims.append(([(x + rx * cos(a), y + ry * sin(a)) for a in [i * pi / 8 for i in range(0, 9)]], 2))
    s.wash(pebbles, (196, 170, 142), alpha=0.95, rim=0.5, rim_px=2, grain=0.2, cell=6, rough=None, dark=0.75,
           soft=0.6)
    s.pencil(rims, strength=0.55, colour=(60, 36, 22))
    s.paper(0.12)
    return s


LAYERS = (  # name, painter, speed as a fraction of the runner's, keyed
    ("sky", paint_sky, 0.0, False),
    ("clouds", paint_clouds, 0.08, True),
    ("far", paint_far, 0.2, True),
    ("hills", paint_hills, 0.45, True),
    ("ground", paint_ground, 1.0, False),
)


def compose_bg(strips):
    """The full background, the fallback: every layer's first 320 px laid soft at 4x, then shrunk."""
    S = Strip.S
    rgb, _ = strips["sky"].hires()
    bg = rgb.copy()
    for name, _, _, keyed in LAYERS[1:]:
        s = strips[name]
        rgb, cover = s.hires()
        box = (0, 0, W * S, s.h * S)
        bg.paste(rgb.crop(box), (0, s.top * S), blur(cover.crop(box), 1.0) if keyed else None)
    return bg.resize((W, H), Image.LANCZOS).convert("RGBA")


# --- sprites -----------------------------------------------------------------------------------------------------

class Sprite:
    """Paint at 8x in game-pixel units, then cut a hard mask and add an outside pencil outline."""

    S = 8

    def __init__(self, w, h, inset=1):
        self.w, self.h = w, h
        self.size = (w * self.S, h * self.S)
        self.rgb = solid(self.size, GRAPHITE)
        self.alpha = Image.new("L", self.size, 0)
        self.details = []  # (x, y, colour) drawn at 1x after the cut, on top
        self.inset = inset

    def p(self, x, y):
        return (x * self.S, y * self.S)

    def shape(self, kind, *args, width=0):
        m = Image.new("L", self.size, 0)
        d = ImageDraw.Draw(m)
        S = self.S
        if kind == "ellipse":
            x0, y0, x1, y1 = args
            d.ellipse((x0 * S, y0 * S, x1 * S, y1 * S), fill=255)
        elif kind == "poly":
            d.polygon([self.p(x, y) for x, y in args], fill=255)
        elif kind == "line":  # a thick limb with round ends
            pts = [self.p(x, y) for x, y in args]
            d.line(pts, fill=255, width=int(width * S), joint="curve")
            r = width * S / 2
            for x, y in (pts[0], pts[-1]):
                d.ellipse((x - r, y - r, x + r, y + r), fill=255)
        elif kind == "rect":
            x0, y0, x1, y1, rad = args
            d.rounded_rectangle((x0 * S, y0 * S, x1 * S, y1 * S), radius=rad * S, fill=255)
        return m

    def part(self, m, colour, light=None, rim=0.35, grain=0.08):
        """A watercolour part: base colour, a soft lighter side, a darker wet rim, a faint grain."""
        layer = solid(self.size, colour)
        if light:  # light from the upper right: a soft lighter bloom there
            lx, ly, lr, lc = light
            g = Image.new("L", self.size, 0)
            ImageDraw.Draw(g).ellipse(((lx - lr) * self.S, (ly - lr) * self.S, (lx + lr) * self.S,
                                       (ly + lr) * self.S), fill=170)
            g = g.filter(ImageFilter.GaussianBlur(lr * self.S / 2.5))
            layer = Image.composite(solid(self.size, lc), layer, g)
        if grain:
            n = noise(self.size, 3 * self.S).point(lambda v: int(255 * grain * abs(v - 128) / 128))
            layer = Image.composite(solid(self.size, tuple(int(c * 0.85) for c in colour)), layer, n)
        if rim:
            edge = ImageChops.subtract(m, m.filter(ImageFilter.GaussianBlur(self.S * 0.9)))
            layer = Image.composite(solid(self.size, tuple(int(c * 0.72) for c in colour)), layer,
                                    scale(edge, 2 * rim))
        self.rgb.paste(layer, (0, 0), m)
        self.alpha.paste(255, (0, 0), m)

    def dot(self, x, y, colour):
        self.details.append((x, y, colour))

    def cut(self, outline=True, threshold=120, ink=None):
        w, h = self.w, self.h
        a = self.alpha.resize((w, h), Image.BOX)
        rgb = self.rgb.resize((w, h), Image.BOX)
        on = [[a.getpixel((x, y)) >= threshold for x in range(w)] for y in range(h)]
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for y in range(h):
            for x in range(w):
                if on[y][x]:
                    out.putpixel((x, y), rgb.getpixel((x, y)) + (255,))
        if outline:
            for y in range(h):
                for x in range(w):
                    if on[y][x]:
                        continue
                    near = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                            if 0 <= x + dx < w and 0 <= y + dy < h and on[y + dy][x + dx]]
                    if near:
                        cs = [rgb.getpixel(q) for q in near]
                        avg = [sum(c[i] for c in cs) / len(cs) for i in range(3)]
                        col = ink or tuple(int(GRAPHITE[i] * 0.72 + avg[i] * 0.28 * 0.6) for i in range(3))
                        out.putpixel((x, y), col + (255,))
        for x, y, c in self.details:
            if 0 <= x < w and 0 <= y < h:
                out.putpixel((x, y), tuple(c) + (255,))
        return out


SKIN, SKIN_L = (246, 196, 158), (255, 222, 192)
RED, RED_L = (222, 60, 50), (250, 120, 90)
BLUE, BLUE_L = (60, 104, 222), (120, 160, 245)
NAVY, NAVY_L = (62, 68, 158), (104, 110, 196)
SHOE = (34, 30, 36)
INK = (30, 26, 40)  # the runner's inner pencil lines


# A pose: body drop (game px, + is lower), then per limb the knee and ankle (legs) or elbow and hand (arms), in game
# px with the feet on row 21.3 when on the ground (the shoe's sole is row 22, its outline row 23). Near is the
# viewer's side, drawn in front; far is drawn darker behind.
RUN = {  # contact, down, pass: then the same three with the legs and arms swapped
    "contact": (0.0, ((10.0, 18.2), (11.4, 21.3)), ((6.8, 18.4), (4.0, 19.6)),
                ((6.6, 12.6), (4.8, 14.0)), ((10.4, 12.4), (12.2, 11.0))),
    "down": (0.8, ((9.8, 18.8), (9.0, 21.3)), ((6.8, 18.6), (4.8, 18.4)),
             ((7.4, 13.2), (6.0, 14.6)), ((9.8, 13.0), (11.4, 12.2))),
    "pass": (-0.4, ((7.6, 18.2), (5.8, 21.0)), ((10.4, 17.2), (8.4, 19.2)),
             ((9.8, 12.8), (11.6, 11.8)), ((6.8, 12.8), (5.2, 13.8))),
}
JUMP = {
    "takeoff": (1.6, ((10.8, 19.2), (9.6, 21.3)), ((7.0, 19.6), (5.6, 21.3)),
                ((6.4, 13.4), (4.4, 14.8)), ((6.8, 13.6), (5.0, 15.2))),
    "rise": (-0.4, ((10.8, 16.8), (9.4, 19.4)), ((7.0, 18.6), (5.4, 21.4)),
             ((10.4, 9.2), (12.0, 7.2)), ((6.4, 9.4), (5.2, 7.4))),
    "apex": (0.0, ((11.0, 16.6), (9.0, 19.0)), ((10.0, 17.4), (7.4, 19.6)),
             ((10.8, 11.2), (13.0, 9.6)), ((5.8, 11.4), (3.6, 9.8))),
    "fall": (-0.2, ((10.0, 18.4), (10.4, 21.4)), ((7.4, 18.8), (6.4, 21.4)),
             ((10.8, 9.6), (12.6, 7.8)), ((5.8, 9.8), (4.0, 8.2))),
    "land": (2.0, ((11.0, 19.6), (10.2, 21.3)), ((8.6, 19.8), (6.4, 21.3)),
             ((10.8, 13.8), (13.2, 13.0)), ((5.6, 14.0), (3.2, 13.2))),
}


ALIASES = {"runner_jump": "runner_apex"}  # old name: the picture it now shows


def run_cycle():
    """Six frames: contact, down, pass with the near leg in front, then the same with the far leg in front."""
    frames = []
    for swap in (False, True):
        for name in ("contact", "down", "pass"):
            dy, near_leg, far_leg, near_arm, far_arm = RUN[name]
            if swap:
                near_leg, far_leg, near_arm, far_arm = far_leg, near_leg, far_arm, near_arm
            frames.append((dy, near_leg, far_leg, near_arm, far_arm))
    return frames


def runner(pose):
    dy, near_leg, far_leg, near_arm, far_arm = pose
    s = Sprite(16, 24)
    hip, shoulder = (8.2, 15.4 + dy), (8.2, 10.8 + dy)

    def leg(knee_ankle, colour, light, edge):
        knee, ankle = knee_ankle
        ax, ay = ankle
        if edge:  # a pencil line around the near leg, so it reads over the far one
            s.part(s.shape("line", hip, knee, ankle, width=3.3), INK, rim=0, grain=0)
            s.part(s.shape("ellipse", ax - 1.8, ay - 1.4, ax + 2.9, ay + 1.9), INK, rim=0, grain=0)
        s.part(s.shape("line", hip, knee, ankle, width=2.3), colour, light=light, rim=0.25)
        s.part(s.shape("ellipse", ax - 1.3, ay - 0.9, ax + 2.4, ay + 1.4), SHOE, rim=0)

    def arm(elbow_hand, colour, skin, edge):
        elbow, hand = elbow_hand
        if edge:  # a pencil line around the near arm, so it reads over the shirt
            s.part(s.shape("line", shoulder, elbow, hand, width=2.7), INK, rim=0, grain=0)
        s.part(s.shape("line", shoulder, elbow, width=1.8), colour, rim=0.2)  # the sleeve
        s.part(s.shape("line", elbow, hand, width=1.5), skin, rim=0.1)  # the forearm and hand

    arm(far_arm, (40, 76, 190), (226, 172, 136), False)
    leg(far_leg, (30, 32, 84), None, False)
    leg(near_leg, NAVY, (10, 17, 3, NAVY_L), True)
    s.part(s.shape("rect", 5.4, 9.6 + dy, 11.0, 16.2 + dy, 2.0), BLUE, light=(10.5, 10.5 + dy, 3.5, BLUE_L), rim=0.4)
    s.part(s.shape("ellipse", 4.9, 1.8 + dy, 12.3, 9.6 + dy), SKIN, light=(11, 4 + dy, 3, SKIN_L), rim=0.3)
    cap = s.shape("ellipse", 4.4, 0.7 + dy, 12.4, 7.4 + dy)
    cap = ImageChops.multiply(cap, s.shape("rect", 0, 0, 16, 4.6 + dy, 0))
    cap = ImageChops.lighter(cap, s.shape("rect", 8.5, 3.4 + dy, 14.6, 4.9 + dy, 0.7))  # the brim, forward
    s.part(cap, RED, light=(10, 1.5 + dy, 3, RED_L), rim=0.35)
    arm(near_arm, BLUE, SKIN, True)
    ey = int(6 + dy + 0.5)
    s.dot(10, ey, (30, 26, 40))  # the eye
    s.dot(11, ey + 2, (200, 90, 90))  # a smile
    s.dot(8, ey + 1, (250, 150, 140))  # a rosy cheek
    return s.cut()


CACTUS_INK = (20, 34, 30)  # its outline: near black, so it stands out on the green hills


def cactus(h):
    """A saguaro in a deep, slightly blue green, a yellow-green stripe where the light falls, a near-black outline."""
    s = Sprite(20, h)
    green, light = (34, 118, 92), (64, 156, 108)
    cx, tw = 10.0, (7.0 if h >= 32 else 6.0)
    top = 1.2
    k = min(1.0, h / 40)  # arms: left low, right higher, each out and up; smaller on short ones
    aw = 3.6 if h >= 24 else 3.0
    ly, ry = h * 0.62, h * 0.45
    lh, rh = max(3.0, h * 0.30 * (0.6 + 0.4 * k)), max(3.0, h * 0.28 * (0.6 + 0.4 * k))
    lx, rx = 3.2, 16.8
    if h <= 16:
        ly, ry, lh, rh = 10.0, 8.0, 3.0, 3.0
    s.part(s.shape("line", (cx - 1, ly), (lx, ly), (lx, ly - lh), width=aw), green, light=(lx, ly - lh, 2, light),
           rim=0.45, grain=0.1)
    s.part(s.shape("line", (cx + 1, ry), (rx, ry), (rx, ry - rh), width=aw), green, light=(rx, ry - rh, 2, light),
           rim=0.45, grain=0.1)
    s.part(s.shape("rect", cx - tw / 2, top, cx + tw / 2, h + 2, tw / 2), green,
           light=(cx + 1.5, top + 4, max(3.0, h / 6), light), rim=0.5, grain=0.1)
    img = s.cut(ink=CACTUS_INK)
    stripe, rib = (168, 214, 92), (24, 92, 74)

    def paint(x, y0, y1, colour, every=0):
        for y in range(int(y0), int(y1)):
            p = img.getpixel((x, y))
            if p[3] and p[:3] != CACTUS_INK and not (every and y % every == 0):
                img.putpixel((x, y), colour + (255,))

    paint(int(cx) + 1, top + 2, h, stripe)  # the lit stripe down the trunk
    paint(int(cx) - 2, top + 3, h, rib, 4)  # a broken rib in the shade
    paint(int(lx), ly - lh + 1, ly, stripe)  # and up each arm
    paint(int(rx), ry - rh + 1, ry, stripe)
    for i, y in enumerate(range(5, h - 3, 4)):  # spines: pale ticks just outside the outline
        x = int(cx - tw / 2) - 2 if i % 2 else int(cx + tw / 2) + 1
        if 0 <= x < 20 and img.getpixel((x, y))[3] == 0 and img.getpixel((x + (1 if i % 2 else -1), y))[3]:
            img.putpixel((x, y), (226, 222, 170, 255))
    if h >= 40:  # a pink flower on the tall ones
        for x, y, c in ((9, 1, (240, 110, 150)), (10, 1, (255, 170, 190)), (11, 1, (240, 110, 150))):
            img.putpixel((x, y), c + (255,))
    return img


def bird(frame):
    s = Sprite(20, 12)
    body, belly, wing = (124, 112, 156), (196, 184, 210), (98, 86, 136)
    if frame == 1:  # wings down: the far wing shows under the body
        s.part(s.shape("poly", (10, 7), (14, 7), (12, 11.2)), (84, 74, 118), rim=0.2)
    s.part(s.shape("poly", (12, 5.4), (19.4, 3.6), (18.6, 6.4), (13, 8)), (100, 90, 132), rim=0.3)  # tail
    s.part(s.shape("ellipse", 4.4, 3.8, 15.6, 10.0), body, light=(9, 4.5, 3, (160, 150, 190)), rim=0.4)
    s.part(s.shape("ellipse", 5.4, 6.8, 12.6, 10.2), belly, rim=0.2)
    s.part(s.shape("ellipse", 2.4, 2.2, 8.4, 8.2), body, light=(5, 3.5, 2, (164, 154, 196)), rim=0.3)  # head
    s.part(s.shape("poly", (3.0, 4.4), (0.4, 5.8), (3.0, 6.9)), (250, 150, 40), rim=0.2)  # the beak, to the left
    if frame == 0:  # wings up
        s.part(s.shape("poly", (8.0, 5.6), (11.0, 0.6), (16.6, 0.4), (13.6, 6.4)), wing, light=(14, 1, 2.5, body),
               rim=0.45)
    else:
        s.part(s.shape("poly", (8.6, 6.0), (13.4, 6.0), (13.0, 11.6), (11.2, 11.2)), wing, light=(12, 10, 2, body),
               rim=0.35)
    s.dot(4, 4, (255, 255, 255))
    s.dot(4, 5, (24, 20, 32))
    return s.cut()


GOLD, GOLD_L, GOLD_D = (238, 184, 46), (255, 236, 150), (196, 126, 30)


def coin(frame):
    s = Sprite(16, 16)
    half = (6.6, 4.6, 1.5, 4.6)[frame]
    cx, cy, ry = 8.0, 8.0, 6.6
    if frame in (1, 3):  # the edge shows as a darker rim on one side
        side = 1.0 if frame == 1 else -1.0
        s.part(s.shape("ellipse", cx - half + side, cy - ry, cx + half + side, cy + ry), GOLD_D, rim=0.3)
    s.part(s.shape("ellipse", cx - half, cy - ry, cx + half, cy + ry), GOLD,
           light=(cx - half * 0.3, cy - 3, max(1.5, half * 0.7), GOLD_L), rim=0.6, grain=0.05)
    img = s.cut()
    if frame != 2:  # an inner pencil ring and a struck star-dot in the middle
        r_x, r_y = half - 2.0, ry - 2.0
        ring = set()
        for i in range(48):
            a = i * 2 * pi / 48
            ring.add((round(cx - 0.5 + r_x * cos(a)), round(cy - 0.5 + r_y * sin(a))))
        for x, y in ring:
            if img.getpixel((x, y))[3]:
                img.putpixel((x, y), (204, 140, 40, 255))
    shine = {0: [(5, 4), (5, 5), (4, 6), (4, 7)], 1: [(6, 4), (5, 5), (5, 6)], 2: [(8, 4), (8, 5), (8, 6)],
             3: [(7, 4), (7, 5), (6, 6)]}[frame]
    for x, y in shine:
        if img.getpixel((x, y))[3]:
            img.putpixel((x, y), (255, 252, 226, 255))
    return img


def clock():
    s = Sprite(16, 16)
    blue, blue_l = (52, 98, 214), (120, 162, 246)
    for x in (4.0, 12.0):  # the bells
        s.part(s.shape("ellipse", x - 2.4, 0.9, x + 2.4, 5.0), (70, 110, 220), light=(x, 1.5, 1.5, blue_l), rim=0.3)
    for x0, x1 in ((3.2, 5.0), (11.0, 12.8)):  # the feet
        s.part(s.shape("line", (x0 + 1, 13), (x0 if x0 < 8 else x1, 14.8), width=1.4), (40, 60, 140), rim=0)
    s.part(s.shape("ellipse", 2.0, 2.6, 14.0, 14.6), blue, light=(10, 5.5, 3.5, blue_l), rim=0.6, grain=0.06)
    img = s.cut()
    white = (255, 255, 250, 255)
    for x, y in ((8, 5), (8, 6), (8, 7), (8, 8), (9, 8), (10, 8), (11, 8)):  # hands: twelve and three
        img.putpixel((x, y), white)
    for x, y in ((8, 3), (13, 8), (8, 13), (3, 8)):  # ticks
        img.putpixel((x, y), (190, 210, 250, 255))
    return img


def star():
    s = Sprite(16, 16)
    cx, cy, ro, ri = 8.0, 8.7, 7.4, 3.0
    pts = []
    for i in range(10):
        a = -pi / 2 + i * pi / 5
        r = ro if i % 2 == 0 else ri
        pts.append((cx + r * cos(a), cy + r * sin(a)))
    s.part(s.shape("poly", *pts), (224, 58, 168), light=(cx - 1, cy - 2, 3, (252, 140, 210)), rim=0.6, grain=0.06)
    img = s.cut()
    for x, y in ((7, 5), (6, 7)):
        if img.getpixel((x, y))[3]:
            img.putpixel((x, y), (255, 236, 248, 255))
    for x, y in ((14, 1), (13, 2), (14, 2), (15, 2), (14, 3)):  # a sparkle
        img.putpixel((x, y), (255, 255, 255, 255))
    return img


# --- the stack game (P563) ---------------------------------------------------------------------------------------

STACK_FLOOR, BLOCK_H = 234, 14
PALETTE = ((230, 40, 40), (250, 140, 30), (250, 220, 40), (40, 210, 70), (40, 220, 230), (50, 90, 240),
           (230, 60, 220), (226, 230, 244))  # gfx.PALETTE in its order; white painted as a cool paper white
NIGHT = ((26, 22, 66), (74, 46, 110), (150, 82, 128))  # the sky from the top, to the middle, to the horizon
STACK_INK = (40, 30, 50)  # the pencil, as the game draws the block ends


def night_at(y):
    t = max(0.0, min(1.0, (y - 16) / (STACK_FLOOR - 16)))
    a, b, t = (NIGHT[0], NIGHT[1], t / 0.6) if t < 0.6 else (NIGHT[1], NIGHT[2], (t - 0.6) / 0.4)
    return tuple(int(p + (q - p) * t) for p, q in zip(a, b))


def calm(s, lo=0.35):
    """A mask that is lo across the tower's columns (x 60 to 260) and full at the sides, and 0 over the score bar."""
    m = Image.new("L", s.size, 255)
    d = ImageDraw.Draw(m)
    d.rectangle((60 * s.S, 0, 260 * s.S, s.size[1]), fill=int(255 * lo))
    m = blur(m, 30 * s.S / 4)
    ImageDraw.Draw(m).rectangle((0, 0, s.size[0], 17 * s.S), fill=0)
    return m


def paint_stack_bg():
    """Dusk to night: violet and indigo washes, soft stars, a pale moon, a far town with lit windows, a stone floor."""
    s = Strip(W, 0, H, False, night_at)
    blooms = autocontrast(blur(s.noise(160), 24))
    sides = calm(s)
    glaze(s.rgb, ImageChops.multiply(scale(blooms, 1.5, -150), sides), (150, 120, 220), 0.45)  # indigo blooms
    glaze(s.rgb, ImageChops.multiply(scale(ImageChops.invert(blooms), 1.4, -170), sides), (220, 150, 210), 0.35)
    mx, my, mr = 266, 50, 12
    halo = s.mask()
    s.ellipse(halo, mx, my, mr * 3, mr * 3, 110)
    lay(s.rgb, blur(halo, mr * 5), (176, 160, 214))
    moon = s.mask()
    s.ellipse(moon, mx, my, mr, mr)
    s.wash(moon, (244, 238, 214), alpha=0.98, rim=0.35, rim_px=6, grain=0.15, cell=12, rough=(2, 0.3, 10), dark=0.9,
           soft=1.5)
    craters = s.mask()
    for cx, cy, r in ((-4, -3, 3.2), (3, 2, 2.4), (-2, 6, 1.8), (6, -5, 1.4)):
        s.ellipse(craters, mx + cx, my + cy, r, r * 0.9)
    glaze(s.rgb, ImageChops.multiply(blur(craters, 3), moon), (214, 204, 196), 0.6)
    stars, twinkles = s.mask(), []
    for _ in range(46):
        x, y = rnd.uniform(4, W - 4), rnd.uniform(22, 170)
        middle = 64 < x < 256
        if middle and rnd.random() < 0.55:
            continue
        r = rnd.uniform(0.5, 0.9) * (0.7 if middle else 1.0)
        s.ellipse(stars, x, y, r, r, 255 if not middle else 170)
        if not middle and r > 0.8 and len(twinkles) < 6 and abs(x - mx) > 22:
            twinkles.append((x, y))
    lay(s.rgb, blur(stars, 2.2), (255, 246, 214))
    rays = s.mask()
    d = ImageDraw.Draw(rays)
    for x, y in twinkles:  # a four-pointed twinkle
        px, py = x * s.S, y * s.S
        d.line([(px - 14, py), (px + 14, py)], fill=230, width=2)
        d.line([(px, py - 14), (px, py + 14)], fill=230, width=2)
    lay(s.rgb, blur(rays, 1.2), (255, 250, 230))
    # The far hills, low in the middle, and a little town at each side with warm windows.
    hill = [(x, 214 - 10 * (0.5 + 0.5 * sin(x / 34 + 1.3)) * (1.0 if not 60 < x < 260 else 0.5)) for x in range(0, W + 1, 2)]
    m = s.mask()
    s.polygon(m, hill + [(W, STACK_FLOOR + 2), (0, STACK_FLOOR + 2)])
    s.wash(m, (70, 44, 92), alpha=0.95, rim=0.6, rim_px=6, grain=0.3, cell=16, rough=(1.5, 0.35, 8), dark=0.8, soft=1)
    town, windows = s.mask(), []
    for x0, x1 in ((0, 64), (250, W)):
        x = x0
        while x < x1:
            w, h = rnd.uniform(8, 16), rnd.choice((rnd.uniform(8, 16), rnd.uniform(18, 34)))
            gy = 222
            body = [(x, gy + 14), (x, gy - h), (x + w / 2, gy - h - w * 0.45), (x + w, gy - h), (x + w, gy + 14)]
            s.polygon(town, body)
            for wy in range(int(gy - h + 4), int(gy - 2), 6):
                for wx in (x + 2.5, x + w - 4.5):
                    if rnd.random() < 0.4:
                        windows.append((wx, wy))
            x += w + rnd.uniform(-1, 2)
    s.wash(town, (46, 32, 70), alpha=0.97, rim=0.5, rim_px=4, grain=0.25, cell=10, rough=(1, 0.3, 6), dark=0.78,
           soft=0.8)
    lit = s.mask()
    for wx, wy in windows:
        s.polygon(lit, [(wx, wy), (wx + 2, wy), (wx + 2, wy + 2.4), (wx, wy + 2.4)])
    lay(s.rgb, blur(lit, 3), (255, 170, 80), 0.5)  # the glow
    lay(s.rgb, lit, (255, 214, 120))
    # The stone floor from row 234: a grey-violet wash, a pencil line on top, joints between the stones.
    floor = s.mask()
    s.polygon(floor, [(0, STACK_FLOOR), (W, STACK_FLOOR), (W, H + 2), (0, H + 2)])
    s.wash(floor, (122, 110, 132), alpha=1.0, rim=0.0, grain=0.35, cell=12, rough=None, soft=0)
    stones = s.mask()
    for x in range(0, W, 18):  # each stone a little lighter on top
        s.ellipse(stones, x + 9, STACK_FLOOR + 2.5, 7, 1.6)
    lay(s.rgb, ImageChops.multiply(blur(stones, 3), floor), (160, 150, 172), 0.6)
    joints = [([(x, STACK_FLOOR + 0.5), (x + rnd.uniform(-0.5, 0.5), H)], 2) for x in range(18, W, 18)]
    joints.append((jitter([(0, STACK_FLOOR + 0.3), (W, STACK_FLOOR + 0.3)], 0.2), 3))
    s.pencil(joints, strength=0.7, colour=STACK_INK)
    s.paper(0.06)
    return s.rgb.resize((W, H), Image.LANCZOS).convert("RGBA")


def paint_block(colour, edge=None):
    """A 320 x 14 block strip: a light top, a darker foot, grain and a gentle change along it, pencil top and bottom.
    Any width is cut from its left end, so the change along it is slow and even."""
    s = Strip(W, 0, BLOCK_H, False, colour)
    body = s.mask()
    s.polygon(body, [(0, 0), (W, 0), (W, BLOCK_H), (0, BLOCK_H)])
    s.wash(body, colour, alpha=1.0, rim=0.0, grain=0.45, cell=6, rough=None, soft=0)
    drift = autocontrast(blur(s.noise(90), 10))  # slow light and dark along the length
    glaze(s.rgb, scale(drift, 1.2, -110), tuple(int(c * 0.82) for c in colour), 0.7)
    light = tuple(min(255, int(c + (255 - c) * 0.55)) for c in colour)
    top = s.mask()
    s.polygon(top, [(0, 1), (W, 1), (W, 3.2), (0, 3.2)])
    broken = blur(s.noise(14), 2).point(lambda v: 255 if v > 105 else 90)  # a dry-brush highlight, not a stripe
    lay(s.rgb, ImageChops.multiply(blur(top, 2), broken), light, 0.7)
    blooms = blur(scale(s.noise(28), 2.4, -330), 3)  # pale wet blooms here and there
    lay(s.rgb, blooms, light, 0.25)
    foot = s.mask()
    s.polygon(foot, [(0, 10.5), (W, 10.5), (W, 13), (0, 13)])
    glaze(s.rgb, blur(foot, 3), tuple(int(c * 0.62) for c in colour), 0.9)
    if edge:  # the mover: a warm glow along its top and foot
        glow = s.mask()
        s.polygon(glow, [(0, 0), (W, 0), (W, 2.5), (0, 2.5)])
        s.polygon(glow, [(0, 11), (W, 11), (W, 14), (0, 14)])
        glaze(s.rgb, blur(glow, 3), edge, 0.6)
    strokes = []
    for _ in range(14):  # a few faint dry-brush streaks
        x, y = rnd.uniform(-10, W), rnd.uniform(4.5, 9.5)
        strokes.append(([(x, y), (x + rnd.uniform(14, 30), y + rnd.uniform(-0.4, 0.4))], 2))
    s.pencil(strokes, strength=0.12, colour=tuple(int(c * 0.5) for c in colour))
    img = s.rgb.resize((W, BLOCK_H), Image.LANCZOS)
    ink = tuple(int(i * 0.8 + c * 0.2) for i, c in zip(STACK_INK, colour))
    for x in range(W):  # the pencil rows, a little uneven
        k = 1.0 + 0.12 * sin(x * 0.7) * sin(x * 0.13)
        for y in (0, BLOCK_H - 1):
            img.putpixel((x, y), tuple(max(0, min(255, int(c * k))) for c in ink))
    return img.convert("RGBA")


def paint_stack():
    """Every stack picture, on its own seed so the runner's art does not move it."""
    rnd.seed(563)
    pics = {"stack_bg": paint_stack_bg()}
    for i, colour in enumerate(PALETTE):
        pics["stack_block%d" % i] = paint_block(colour)
    pics["stack_mover"] = paint_block((255, 248, 230), edge=(255, 196, 120))
    return pics


def stack_scene(pics):
    """A tower of ten blocks, narrower as it grows, and the mover, as the game draws them (its pencil ends too)."""
    out = pics["stack_bg"].copy()
    x, w = 90, 140
    rows = []
    for i in range(10):
        rows.append((x, 220 - (i + 1) * BLOCK_H, w, "stack_block%d" % (i % 8)))
        cut = (3, 7, 2, 11, 5, 9, 4, 6, 8, 3)[i]
        x, w = (x + cut, w - cut) if i % 2 else (x, w - cut)
    rows.append((150, 220 - 11 * BLOCK_H, w, "stack_mover"))
    d = ImageDraw.Draw(out)
    for x, y, w, name in rows:
        out.paste(pics[name].crop((0, 0, w, BLOCK_H)), (x, y))
        d.line([(x, y), (x, y + BLOCK_H - 1)], fill=STACK_INK)
        d.line([(x + w - 1, y), (x + w - 1, y + BLOCK_H - 1)], fill=STACK_INK)
    return out.convert("RGB")


# --- the board's format ------------------------------------------------------------------------------------------

def c565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def to_bin(img, keyed):
    """Game image (w, h) -> panel bytes (h by w after a 90 degree turn), RGB565 big-endian."""
    panel = img.transpose(Image.ROTATE_90)
    out = bytearray()
    for px in panel.get_flattened_data():
        if keyed and px[3] == 0:
            v = KEY
        else:
            v = c565(*px[:3])
            if v == KEY:
                v = NUDGE
        out += bytes((v >> 8, v & 0xFF))
    return bytes(out)


def from_bin(data, w, h):
    """The reverse, to check: panel bytes -> game RGBA image, the key as transparent."""
    panel = Image.new("RGBA", (h, w))
    px = []
    for i in range(0, len(data), 2):
        v = (data[i] << 8) | data[i + 1]
        if v == KEY:
            px.append((0, 0, 0, 0))
        else:
            px.append((((v >> 11) & 31) << 3, ((v >> 5) & 63) << 2, (v & 31) << 3, 255))
    panel.putdata(px)
    return panel.transpose(Image.ROTATE_270)


def q565(img):
    """What the board shows: each opaque pixel cut to RGB565 (the key nudged), the rest transparent."""
    def one(p):
        if p[3] == 0:
            return (0, 0, 0, 0)
        r, g, b = p[0] & 0xF8, p[1] & 0xFC, p[2] & 0xF8
        return (r, g, b - 8, 255) if (r, g, b) == (248, 0, 248) else (r, g, b, 255)
    out = Image.new("RGBA", img.size)
    out.putdata([one(p) for p in img.get_flattened_data()])
    return out


# --- the preview sheet -------------------------------------------------------------------------------------------

SCENE = (("runner_run0", 52, GROUND - 24), ("cactus40", 150, GROUND - 40), ("cactus24", 172, GROUND - 24),
         ("bird0", 240, GROUND - 58), ("coin0", 100, 128), ("coin1", 118, 128), ("coin2", 136, 128),
         ("star", 280, 116), ("clock", 210, 136))


def frame(layers, sprites, shift, scene=SCENE):
    """One composed game frame: each layer moved by its speed, the sprites on top, as the board would."""
    out = Image.new("RGBA", (W, H))
    for name, img, top, speed in layers:
        x = int(shift * speed) % img.width
        strip = Image.new("RGBA", (img.width * 2, img.height))
        strip.paste(img, (0, 0))
        strip.paste(img, (img.width, 0))
        out.alpha_composite(strip.crop((x, 0, x + W, img.height)), (0, top))
    for name, x, y in scene:
        out.alpha_composite(sprites[name], (x, y))
    return out.convert("RGB")


def checker(w, h, c=8):
    img = Image.new("RGB", (w, h), (240, 240, 240))
    d = ImageDraw.Draw(img)
    for y in range(0, h, c):
        for x in range(0, w, c):
            if (x + y) // c % 2:
                d.rectangle((x, y, x + c - 1, y + c - 1), fill=(200, 200, 200))
    return img


def preview(bg, layers, sprites, stack, path):
    font = ImageFont.load_default(size=14)
    ink = (40, 40, 40)
    width = 1320
    sheet = Image.new("RGB", (width, 3000), (245, 240, 230))
    d = ImageDraw.Draw(sheet)

    def put(label, img, x, y):
        d.text((x, y), label, fill=ink, font=font)
        sheet.paste(img, (x, y + 18))
        return y + 18 + img.height

    y = 8
    put("bg 320x240 (the fallback) at 2x", bg.convert("RGB").resize((W * 2, H * 2), Image.NEAREST), 10, y)
    f = frame(layers, sprites, 900)
    y = put("parallax layers composed, a frame at 2x, with sprites", f.resize((W * 2, H * 2), Image.NEAREST),
            W * 2 + 30, y) + 14
    for name, img, top, speed in layers:  # each strip alone at 2x, on a checkerboard, twice so the seam shows
        if img.width == W:
            continue
        two = Image.new("RGBA", (img.width * 2, img.height))
        two.paste(img, (0, 0))
        two.paste(img, (img.width, 0))
        two = two.crop((img.width - 330, 0, img.width + 330, img.height)).resize((660 * 2, img.height * 2),
                                                                                Image.NEAREST)
        ch = checker(*two.size)
        ch.paste(two, (0, 0), two)
        y = put("%s %dx%d, rows %d to %d, speed %.2f: the seam in the middle, at 2x" %
                (name, img.width, img.height, top, top + img.height, speed), ch, 0, y) + 10
        d.line([(660, y - 10 - ch.height), (660, y - 14)], fill=(255, 0, 0), width=1)
    def frames(names, k=4, gap=6):
        """Sprites side by side at k times, each on the background where it would stand."""
        w, h = sprites[names[0]].size
        out = Image.new("RGB", (len(names) * (w * k + gap), h * k), (245, 240, 230))
        for i, name in enumerate(names):
            under = bg.convert("RGBA").crop((60, GROUND - h, 60 + w, GROUND))
            under.alpha_composite(sprites[name])
            out.paste(under.convert("RGB").resize((w * k, h * k), Image.NEAREST), (i * (w * k + gap), 0))
        return out

    run = ["runner_run%d" % i for i in range(6)]
    jump = ["runner_" + n for n in JUMP]
    put("the run cycle, runner_run0 to runner_run5, at 4x", frames(run), 10, y)
    y = put("the jump: " + ", ".join(jump) + ", at 4x", frames(jump), 10 + 6 * 70 + 30, y) + 14
    cacti = [n for n in sprites if n.startswith("cactus")]
    scene = [(n, 14 + i * 44, GROUND - sprites[n].height) for i, n in enumerate(cacti)] + [(run[0], 300, GROUND - 24)]
    over = frame(layers, sprites, 0, scene).crop((0, 110, W, H)).resize((W * 3, (H - 110) * 3), Image.NEAREST)
    y = put("every cactus over the hills band, a composed frame at 3x", over, 10, y) + 14
    put("stack: stack_bg with ten blocks and the mover, at 2x", stack_scene(stack).resize((W * 2, H * 2), Image.NEAREST),
        10, y)
    for i, name in enumerate(["stack_block%d" % k for k in range(8)] + ["stack_mover"]):
        put("%s 320x14, at 2x" % name, stack[name].convert("RGB").resize((W * 2, BLOCK_H * 2), Image.NEAREST),
            W * 2 + 30, y + i * 52)
    y += H * 2 + 32
    x = 10
    tallest = 0
    for name, img in sprites.items():
        if name.startswith("runner"):
            continue  # shown in the strips above
        w, h = img.size
        big = img.resize((w * 4, h * 4), Image.NEAREST)
        cell = 2 * w * 4 + 6
        if x + cell > width - 10:
            x, y, tallest = 10, y + tallest + 30, 0
        ch = checker(w * 4, h * 4)
        ch.paste(big, (0, 0), big)
        gy = GROUND - h if name.startswith(("runner", "cactus")) else 100
        under = bg.convert("RGB").crop((60, gy, 60 + w, gy + h)).resize((w * 4, h * 4), Image.NEAREST)
        under.paste(big, (0, 0), big)
        d.text((x, y), "%s %dx%d" % (name, w, h), fill=ink, font=font)
        sheet.paste(ch, (x, y + 18))
        sheet.paste(under, (x + w * 4 + 6, y + 18))
        x += max(cell, 120) + 14
        tallest = max(tallest, h * 4)
    sheet.crop((0, 0, width, y + tallest + 40)).save(path)


# --- main --------------------------------------------------------------------------------------------------------

def seam(img):
    """The mean colour step across the wrap, and the worst mean step between two neighbour columns inside."""
    cols = [[img.getpixel((x, y)) for y in range(img.height)] for x in range(img.width)]

    def step(a, b):
        d = [abs(p - q) for pa, pb in zip(a, b) if pa[3] and pb[3] for p, q in zip(pa[:3], pb[:3])]
        return sum(d) / max(1, len(d))
    return step(cols[-1], cols[0]), max(step(cols[x], cols[x + 1]) for x in range(img.width - 1))


def main():
    strips = {name: painter() for name, painter, _, _ in LAYERS}
    bg = compose_bg(strips)
    layers = [(name, strips[name].game(keyed), strips[name].top, speed) for name, _, speed, keyed in LAYERS]
    sprites = {"runner_run%d" % i: runner(pose) for i, pose in enumerate(run_cycle())}
    sprites.update({"runner_" + name: runner(pose) for name, pose in JUMP.items()})
    for h in (16, 24, 32, 40, 48, 56, 64):
        sprites["cactus%d" % h] = cactus(h)
    sprites["bird0"], sprites["bird1"] = bird(0), bird(1)
    for i in range(4):
        sprites["coin%d" % i] = coin(i)
    sprites["clock"], sprites["star"] = clock(), star()

    out_dir = os.path.join(ROOT, "games", "art")
    os.makedirs(out_dir, exist_ok=True)
    pictures = {"bg": (bg, False)}
    pictures.update({name: (img, keyed) for (name, img, _, _), (_, _, _, keyed) in zip(layers, LAYERS)})
    pictures.update({n: (img, True) for n, img in sprites.items()})
    stack = paint_stack()
    pictures.update({n: (img, False) for n, img in stack.items()})
    index, total = {}, 0
    for name, (img, keyed) in pictures.items():
        for p in img.get_flattened_data():  # a hard mask: no pixel is half there
            assert p[3] in ((0, 255) if keyed else (255,)), name
        data = to_bin(img, keyed)
        w, h = img.size
        assert len(data) == w * h * 2, name
        assert from_bin(data, w, h).tobytes() == q565(img).tobytes(), name  # the file decodes back to the picture
        if not keyed:
            assert all((data[i] << 8 | data[i + 1]) != KEY for i in range(0, len(data), 2)), name
        with open(os.path.join(out_dir, name + ".bin"), "wb") as f:
            f.write(data)
        index[name] = (w, h, "art/%s.bin" % name)
        total += len(data)
    for name, img, _, _ in layers[1:]:
        print("%s: seam step %.1f, worst step inside %.1f" % ((name,) + seam(img)))
    lines = ['"""Generated by art/paint.py: do not edit. The painted pictures, as RGB565 files the board copies."""',
             "",
             "KEY = 0x%04X  # the transparent pixel as written in the .bin files (big-endian bytes F8 1F)" % KEY,
             "KEY_C565 = 0x%04X  # the same key as the board's colour int (c565 values are the byte-swapped v)"
             % (((KEY & 0xFF) << 8) | (KEY >> 8)),
             "",
             "# name: (game width, game height, path on the board). A file is the picture turned to the panel: h x w,",
             "# so a strip's game x runs along the file's rows, and a 320 px window of a strip is one contiguous slice.",
             "ART = {"]
    for old, new in ALIASES.items():  # an old name the game may still ask for, the same file
        index[old] = index[new]
    lines += ['    "%s": (%d, %d, "%s"),' % (n, w, h, p) for n, (w, h, p) in index.items()]
    lines += ["}", "",
              "# The parallax layers, back to front: (name, top game row, width, height, speed as a fraction of the",
              "# runner's, keyed, path). A strip wider than 320 tiles: its left and right edges join. bg is the fallback.",
              "LAYERS = ["]
    lines += ['    ("%s", %d, %d, %d, %s, %s, "art/%s.bin"),' % (name, top, img.width, img.height, speed, keyed, name)
              for (name, img, top, speed), (_, _, _, keyed) in zip(layers, LAYERS)]
    lines += ["]", ""]
    with open(os.path.join(ROOT, "games", "art_index.py"), "w") as f:
        f.write("\n".join(lines))
    preview(bg, layers, sprites, stack, os.path.join(ROOT, "art", "preview.png"))
    print("%d pictures, %d bytes" % (len(index), total))


if __name__ == "__main__":
    main()
