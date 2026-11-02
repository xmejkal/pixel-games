"""The shared brushes: watercolour washes, pencil and paper grain for a background strip, and a sprite painted
big and cut to a hard mask. Every game's art set paints with these, on the one shared random stream."""

import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H, GROUND = 320, 240, 192
STRIP = 640  # a parallax strip's width in game px
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

    def turn(self, degrees, centre):
        """Tilt everything painted so far about centre (game px), counter-clockwise for positive degrees."""
        c = (centre[0] * self.S, centre[1] * self.S)
        self.rgb = self.rgb.rotate(degrees, Image.BICUBIC, center=c, fillcolor=GRAPHITE)
        self.alpha = self.alpha.rotate(degrees, Image.BICUBIC, center=c, fillcolor=0)

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
