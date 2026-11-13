"""Bucket's art (P773): a Czech village at the golden hour, in watercolour. A large low sun with its halo over cool
hills, the village with its red roofs and a church tower on the left hill, an orchard on the right, the river in the
valley with the sun's glint on it, and a meadow where the crates pile up under a wooden rail. The sky over the middle,
where the crates fall, stays calm. The crates and the bucket are the most saturated things on the screen.

The rows and places here are games/bucket.py's (RAIL_Y, the chimneys, the river's glints): tests/test_bucket_art.py
checks that the two agree.
"""

from math import sin

from PIL import Image, ImageChops, ImageDraw

from artset import ArtSet, Painting
from brush import H, W, Sprite, Strip, autocontrast, blur, cloud, glaze, jitter, lay, ridge, rnd, scale

RAIL_Y = 210  # games/bucket.py's: the line the bucket rides on, and the top of a full pile
HORIZON = 150
RIVER = (151, 163)  # the river's rows in the valley
SUN = (258, 96, 22)  # x, y, radius: low over the right hill
SKY = ((136, 158, 206), (206, 190, 214), (252, 206, 168), (255, 214, 150))  # cool high, lilac, peach, gold low
SKY_AT = (16, 66, 112, HORIZON)
INK = (70, 44, 34)  # the warm pencil


def sky_at(y):
    if y <= SKY_AT[0]:
        return SKY[0]
    for (y0, a), (y1, b) in zip(zip(SKY_AT, SKY), zip(SKY_AT[1:], SKY[1:])):
        if y <= y1:
            t = (y - y0) / (y1 - y0)
            return tuple(int(p + (q - p) * t) for p, q in zip(a, b))
    return SKY[-1]


def calm(s, lo=0.15):
    """A mask that is lo over the middle 60 % where the crates fall and full at the sides."""
    m = Image.new("L", s.size, 255)
    ImageDraw.Draw(m).rectangle((70 * s.S, 0, 250 * s.S, s.size[1]), fill=int(255 * lo))
    return blur(m, 24 * s.S / 4)


def crest(x0, x1, y0, peak, y1, bump):
    """A soft hill's crest from (x0, y0) over a top at peak to (x1, y1), as 41 points."""
    px, py = peak
    pts = []
    for i in range(41):
        x = x0 + (x1 - x0) * i / 40
        if x <= px:
            t = (x - x0) / (px - x0)
            y = y0 + (py - y0) * (1 - (1 - t) ** 2)
        else:
            t = (x - px) / (x1 - px)
            y = py + (y1 - py) * t * t
        pts.append((x, y + bump * sin(x / 7.0)))
    return pts


def on(pts, x):
    """The crest's y at x."""
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        if ax <= x <= bx:
            return ay + (by - ay) * (x - ax) / (bx - ax)
    return pts[-1][1]


VILLAGE_HILL = crest(-6, 156, 112, (34, 100), RIVER[0] + 1, 0.5)
ORCHARD_HILL = crest(168, 326, RIVER[0] + 1, (292, 112), 120, 0.5)
# The village's houses back to front: (x, width, wall height); the church stands at CHURCH_X. Fixed, so the chimneys
# below are where games/bucket.py lets its smoke rise.
HOUSES = ((0, 14, 9), (22, 12, 8), (58, 15, 9), (74, 12, 8), (90, 13, 7), (6, 13, 8), (44, 11, 7), (104, 12, 7),
          (118, 11, 6), (130, 10, 6), (64, 12, 7), (26, 14, 8), (84, 11, 6))
CHURCH_X = 34
CHIMNEY_OF = (1, 2, 4)  # the houses with a chimney that smokes


def house_base(x, w, k):
    """A house's foot: on the hill, lower for the houses further down the list (nearer the viewer)."""
    return on(VILLAGE_HILL, x + w / 2) + 2 + (3 if k >= 5 else 0) + (3 if k >= 10 else 0)


CHIMNEYS = tuple((round(HOUSES[k][0] + HOUSES[k][1] * 0.72), round(house_base(HOUSES[k][0], HOUSES[k][1], k)
                  - HOUSES[k][2] - HOUSES[k][1] * 0.28 - 3)) for k in CHIMNEY_OF)  # each chimney's top: x, y
GLINTS = ((250, 154), (262, 156), (254, 159), (268, 153), (244, 160))  # the river's shimmer, under the sun


# --- the still scene, painted in layers ---------------------------------------------------------------------------

def paint_sky(s):
    """Soft washes kept to the sides, the low sun with a wide warm halo, baked clouds at the sides lit warm from the
    sun, thin streaks low over it, a few birds."""
    sides = calm(s)
    blooms = autocontrast(blur(s.noise(180), 26))
    glaze(s.rgb, ImageChops.multiply(scale(blooms, 1.4, -150), sides), (190, 184, 226), 0.45)  # lilac washes
    glaze(s.rgb, ImageChops.multiply(scale(ImageChops.invert(blooms), 1.3, -160), sides), (255, 214, 190), 0.45)
    sx, sy, sr = SUN
    for k, a, colour in ((6.0, 150, (255, 206, 150)), (3.0, 190, (255, 214, 150)), (1.6, 220, (255, 232, 180))):
        halo = s.mask()
        s.ellipse(halo, sx, sy, sr * k, sr * k * 0.85, a)
        lay(s.rgb, blur(halo, sr * k * 1.2), colour)
    disc = s.mask()
    s.ellipse(disc, sx, sy, sr, sr)
    s.wash(disc, (255, 238, 186), alpha=1.0, rim=0.3, rim_px=6, grain=0.05, rough=(3, 0.4, 14), dark=0.97, soft=1.5)
    core = s.mask()
    s.ellipse(core, sx + 3, sy - 3, sr * 0.6, sr * 0.6)
    lay(s.rgb, ImageChops.multiply(blur(core, 20), disc), (255, 252, 230), 0.8)
    lines = []
    for cx, cy, cw in ((30, 54, 70), (300, 44, 60), (122, 30, 34), (8, 96, 40)):
        cloud(s, cx, cy, cw, lines, (255, 246, 236), (186, 170, 210), (255, 200, 150))
    s.pencil(lines, strength=0.22, colour=(120, 100, 130))
    streaks = s.mask()  # thin wisps across the sun, ragged and tapering
    for x0, y0, w in ((214, 92, 90), (236, 106, 70), (190, 112, 60)):
        for k in range(6):
            t = k / 5 - 0.5
            s.ellipse(streaks, x0 + w / 2 + t * w * 0.8 + rnd.uniform(-3, 3), y0 + rnd.uniform(-0.6, 0.6),
                      w * 0.14, 1.3 * (1 - 2 * t * t))
    s.wash(streaks, (214, 160, 168), alpha=0.6, rim=0.4, rim_px=2, grain=0.3, cell=8, rough=(1.5, 0.5, 6), dark=0.85,
           soft=1.5, cover=False)
    lit = ImageChops.subtract(streaks, ImageChops.offset(streaks, 0, -int(0.7 * s.S)))
    lay(s.rgb, blur(lit, 1), (255, 220, 170), 0.8)
    s.pencil([([(x - 2.2 * k, y - 1.1 * k), (x - 0.9 * k, y - 0.1 * k), (x, y + 0.4 * k), (x + 0.9 * k, y - 0.1 * k),
                (x + 2.2 * k, y - 1.3 * k)], 2) for x, y, k in ((60, 82, 0.9), (70, 88, 0.7), (52, 90, 0.6))],
             strength=0.5, colour=(90, 80, 100))


def paint_far(s):
    """The far hills: two ranges in cool lavender and blue-grey, paler with distance, mist at their foot, the sun's
    light along the crests near it."""
    for base, heights, rough, colour, mist in (
            (HORIZON - 4, [20, 28, 16, 24, 32, 18, 26, 22], 8, (184, 172, 210), (240, 214, 206)),
            (HORIZON + 1, [10, 16, 7, 18, 12, 9, 20, 14], 6, (142, 148, 186), (230, 206, 200))):
        pts = ridge(W, base, heights, rough)
        m = s.mask()
        s.polygon(m, pts + [(W, RIVER[0] + 2), (0, RIVER[0] + 2)])
        m = s.wash(m, colour, alpha=0.96, rim=0.5, rim_px=5, grain=0.25, cell=16, rough=(1.5, 0.35, 8), dark=0.88,
                   soft=1)
        foot = s.mask()
        s.polygon(foot, [(0, base - 4), (W, base - 4), (W, base + 10), (0, base + 10)])
        lay(s.rgb, ImageChops.multiply(blur(foot, 16), m), mist, 0.5)
        lit = s.mask()
        s.ellipse(lit, SUN[0], base - 20, 70, 20)
        lay(s.rgb, ImageChops.multiply(blur(lit, 30), m), (255, 214, 176), 0.35)


def hill(s, pts, colour, fields):
    """A hill from its crest down to the river: a sage wash, a patchwork of field strips down its slope with hedges
    along them, cool shade at its foot and the sun's warm light on its right. Returns its mask."""
    m = s.mask()
    s.polygon(m, pts + [(pts[-1][0], RIVER[0] + 2), (pts[0][0], RIVER[0] + 2)])
    m = s.wash(m, colour, alpha=0.99, rim=0.6, rim_px=5, grain=0.3, cell=12, rough=(1.2, 0.35, 6), dark=0.82, soft=1)
    hedges = []
    x0, x1 = pts[0][0], pts[-1][0]
    for i, tint in enumerate(fields):  # strips that run down the slope, each a field
        a, b = x0 + (x1 - x0) * i / len(fields), x0 + (x1 - x0) * (i + 1) / len(fields)
        lean = (b - a) * 0.6
        strip = s.mask()
        s.polygon(strip, [(a, on(pts, a) - 2), (b, on(pts, b) - 2), (b + lean, RIVER[0] + 2), (a + lean, RIVER[0] + 2)])
        if tint:
            s.wash(ImageChops.multiply(strip, m), tint, alpha=0.55, rim=0.4, rim_px=3, grain=0.4, cell=6, rough=None,
                   dark=0.85, soft=0.6, cover=False)
        for t in range(0, 24):  # a hedge of small trees along the field's edge, with gaps
            if rnd.random() < 0.35:
                continue
            y = on(pts, b) + 1 + (RIVER[0] - on(pts, b)) * t / 24
            hedges.append((b + lean * (y - on(pts, b)) / (RIVER[0] - on(pts, b)) + rnd.uniform(-0.6, 0.6), y,
                           rnd.uniform(0.7, 1.4)))
    bushes, lit = s.mask(), s.mask()
    for x, y, r in hedges:
        s.ellipse(bushes, x, y, r, r * 0.8)
        s.ellipse(lit, x + r * 0.4, y - r * 0.4, r * 0.5, r * 0.4)
    bm = s.wash(ImageChops.multiply(bushes, m), (74, 108, 76), alpha=0.95, rim=0.5, rim_px=2, grain=0.3, cell=4,
                rough=None, dark=0.75, soft=0.4, cover=False)
    lay(s.rgb, ImageChops.multiply(lit, bm), (176, 186, 110), 0.7)
    foot = s.mask()
    foot.paste(Image.linear_gradient("L").resize((s.size[0], 28 * s.S)), (0, (RIVER[0] - 26) * s.S))
    glaze(s.rgb, ImageChops.multiply(foot, m), (110, 128, 150), 0.35)
    sun = s.mask()
    s.ellipse(sun, SUN[0] + 20, SUN[1] + 30, 110, 50)
    lay(s.rgb, ImageChops.multiply(blur(sun, 40), m), (246, 218, 150), 0.4)
    return m


def tree(s, crowns, lights, shadows, x, y, r):
    """A round tree whose foot is at (x, y): its crown, the sunlit side up right, its shadow thrown left."""
    s.ellipse(crowns, x, y - r, r, r * 0.92)
    s.ellipse(lights, x + r * 0.35, y - r * 1.35, r * 0.6, r * 0.45)
    s.polygon(shadows, [(x, y - 0.5), (x - r * 3.2, y + 0.6), (x - r * 3.0, y + 1.6), (x, y + 1)])


def trees(s, crowns, lights, shadows, trunks, colour=(92, 132, 88)):
    """The trees gathered by tree(): shadows, then the crowns with their lit sides, then the trunks."""
    glaze(s.rgb, blur(shadows, 2), (100, 110, 140), 0.5)
    s.pencil(trunks, strength=0.6, colour=(80, 60, 50))
    cm = s.wash(crowns, colour, alpha=0.97, rim=0.6, rim_px=3, grain=0.3, cell=6, rough=(0.8, 0.3, 4), dark=0.72,
                soft=0.6)
    lay(s.rgb, ImageChops.multiply(blur(lights, 3), cm), (220, 214, 128), 0.8)
    return cm


def paint_village(s):
    """The left hill with the village: cream walls with their shade side cool, red roofs with a warm rim along the
    edges the sun catches, windows, the church with its tower and onion dome, trees between the houses, chimneys."""
    hill(s, VILLAGE_HILL, (132, 160, 138), ((168, 176, 122), None, (206, 196, 138), (150, 172, 132), None,
                                            (196, 186, 132)))
    crowns, lights, shadows, trunks = s.mask(), s.mask(), s.mask(), []
    for x, y, r in ((16, 0, 4.2), (52, 0, 3.6), (100, 0, 3.4), (140, 0, 3.0), (70, 4, 3.2), (36, 6, 3.6)):
        tree(s, crowns, lights, shadows, x, on(VILLAGE_HILL, x) + 3 + y, r)
        trunks.append(([(x, on(VILLAGE_HILL, x) + 3 + y - r * 0.3), (x, on(VILLAGE_HILL, x) + 4 + y)], 2))
    trees(s, crowns, lights, shadows, trunks)
    tx = CHURCH_X  # the church behind the houses: a nave, and a tower with an onion dome and a spire
    ty = on(VILLAGE_HILL, tx) + 2
    church = Building(s)
    for poly in ([(tx - 8, ty), (tx - 8, ty - 11), (tx + 6, ty - 11), (tx + 6, ty)],
                 [(tx + 6, ty), (tx + 6, ty - 30), (tx + 14, ty - 30), (tx + 14, ty)]):
        s.polygon(church.walls, poly)
    s.polygon(church.roof, [(tx - 9.5, ty - 10.5), (tx - 1, ty - 18), (tx + 7, ty - 10.5)])
    church.edge([(tx - 1, ty - 18), (tx + 7, ty - 10.5)])
    s.polygon(church.shade, [(tx - 8, ty), (tx - 8, ty - 11), (tx - 4, ty - 11), (tx - 4, ty)])
    s.polygon(church.shade, [(tx + 6, ty), (tx + 6, ty - 30), (tx + 8.5, ty - 30), (tx + 8.5, ty)])
    for wy in (ty - 24, ty - 16):
        s.polygon(church.windows, [(tx + 9, wy), (tx + 11, wy), (tx + 11, wy + 3), (tx + 9, wy + 3)])
    church.paint()
    dome = s.mask()
    s.ellipse(dome, tx + 10, ty - 33.5, 5.4, 4.6)
    s.polygon(dome, [(tx + 7.8, ty - 37), (tx + 10, ty - 43), (tx + 12.2, ty - 37)])
    s.ellipse(dome, tx + 10, ty - 44, 1.6, 1.6)
    s.wash(dome, (82, 124, 116), alpha=1.0, rim=0.6, rim_px=3, grain=0.2, cell=6, rough=None, dark=0.7, soft=0.4)
    s.pencil([([(tx + 10, ty - 45), (tx + 10, ty - 51)], 2), ([(tx + 8.4, ty - 49), (tx + 11.6, ty - 49)], 2)],
             strength=0.8, colour=(60, 70, 70))
    for k, (x, w, h) in enumerate(HOUSES):  # back to front, each painted whole, so the next one hides it
        y = house_base(x, w, k)
        top = y - h - w * 0.42
        house = Building(s)
        s.polygon(house.walls, [(x, y), (x, y - h), (x + w, y - h), (x + w, y)])
        s.polygon(house.roof, [(x - 1.4, y - h + 0.6), (x + w * 0.5, top), (x + w + 1.4, y - h + 0.6)])
        house.edge([(x + w * 0.5, top), (x + w + 1.4, y - h + 0.6)])
        s.polygon(house.shade, [(x, y), (x, y - h), (x + w * 0.32, y - h), (x + w * 0.32, y)])
        for wx in range(int(x + w * 0.4), int(x + w - 2), 4):
            s.polygon(house.windows, [(wx, y - h * 0.6), (wx + 1.6, y - h * 0.6), (wx + 1.6, y - h * 0.6 + 2.2),
                                      (wx, y - h * 0.6 + 2.2)])
        door = x + w * 0.15
        s.polygon(house.windows, [(door, y), (door, y - 3.2), (door + 2, y - 3.2), (door + 2, y)])
        if k in CHIMNEY_OF:
            cx, cy = CHIMNEYS[CHIMNEY_OF.index(k)]
            s.polygon(house.roof, [(cx - 1.2, cy), (cx + 1.2, cy), (cx + 1.2, cy + 5), (cx - 1.2, cy + 5)])
        house.paint()


class Building:
    """One building's masks on strip s, painted together: cream walls, a red roof, the shade side cool, windows and
    doors, and a warm rim along the roof's edge that faces the sun."""

    def __init__(self, s):
        self.s = s
        self.walls, self.roof, self.shade, self.windows, self.rim = (s.mask() for _ in range(5))

    def edge(self, pts):
        ImageDraw.Draw(self.rim).line([self.s.pt(x, y)[0] for x, y in pts], fill=255, width=int(0.8 * self.s.S))

    def paint(self):
        s = self.s
        s.wash(self.walls, (240, 228, 206), alpha=1.0, rim=0.5, rim_px=3, grain=0.25, cell=8, rough=None, dark=0.86,
               soft=0.4)
        glaze(s.rgb, ImageChops.multiply(blur(self.shade, 0.8), self.walls), (168, 156, 200), 0.65)
        lay(s.rgb, ImageChops.multiply(self.windows, self.walls), (104, 80, 92), 0.85)
        s.wash(self.roof, (194, 96, 78), alpha=1.0, rim=0.6, rim_px=3, grain=0.3, cell=6, rough=None, dark=0.72,
               soft=0.4)
        lay(s.rgb, ImageChops.multiply(blur(self.rim, 0.6), self.roof), (255, 204, 140), 0.95)


def paint_orchard(s):
    """The right hill with the orchard: rows of round fruit trees lit gold on their sun side, their shadows long to
    the left, fruit in them, and a lone cottage."""
    hill(s, ORCHARD_HILL, (126, 156, 130), (None, (196, 190, 132), (150, 170, 126), None, (210, 196, 136)))
    crowns, lights, shadows, trunks = s.mask(), s.mask(), s.mask(), []
    for row in range(4):
        for k in range(12):
            x = 186 + k * 12 + row * 5 + rnd.uniform(-1.5, 1.5)
            if x > W + 4:
                continue
            y = on(ORCHARD_HILL, x) + 6 + row * 7
            if y > RIVER[0] - 3:
                continue
            r = 3.0 + row * 0.5
            tree(s, crowns, lights, shadows, x, y, r)
            trunks.append(([(x, y - r * 0.3), (x, y + 1.2)], 2))
    cm = trees(s, crowns, lights, shadows, trunks, (96, 136, 88))
    fruit = s.mask()
    for _ in range(60):
        s.ellipse(fruit, rnd.uniform(178, W), rnd.uniform(110, RIVER[0] - 4), 0.55, 0.55)
    lay(s.rgb, ImageChops.multiply(fruit, cm), (236, 140, 84), 0.85)


def paint_river(s):
    """The river across the valley: the sky's colours in it, the hills' dark reflections, the sun's glint path, a lit
    line along its far bank, reeds on the near bank."""
    y0, y1 = RIVER
    water = s.mask()
    top = [(x, y0 + 1.2 * sin(x / 23.0)) for x in range(-4, W + 6, 4)]
    low = [(x, y1 + 1.2 * sin(x / 17.0 + 1)) for x in range(W + 4, -6, -4)]
    s.polygon(water, top + low)
    s.wash(water, (138, 164, 206), alpha=1.0, rim=0.4, rim_px=3, grain=0.2, cell=10, rough=None, dark=0.86, soft=0.4)
    warm = s.mask()
    s.ellipse(warm, SUN[0], y0 + 5, 110, 10)
    lay(s.rgb, ImageChops.multiply(blur(warm, 26), water), (255, 210, 160), 0.7)
    refl = s.mask()  # the hills mirrored, dark at each side
    s.polygon(refl, [(0, y0), (156, y0), (120, y0 + 5), (40, y0 + 9), (0, y0 + 9)])
    s.polygon(refl, [(168, y0), (W, y0), (W, y0 + 8), (226, y0 + 5)])
    glaze(s.rgb, ImageChops.multiply(blur(refl, 4), water), (90, 124, 120), 0.7)
    ripples = []
    for _ in range(40):
        x, y = rnd.uniform(0, W), rnd.uniform(y0 + 2, y1 - 1)
        ripples.append(([(x, y), (x + rnd.uniform(3, 8), y)], 2))
    s.pencil(ripples, strength=0.25, colour=(90, 110, 140))
    path = s.mask()  # the glint path under the sun: short bright strokes, wider near the viewer
    for i in range(22):
        y = y0 + 1 + i * (y1 - y0 - 2) / 22
        w = 2 + (y - y0) * 0.5
        x = SUN[0] + rnd.uniform(-w * 1.5, w * 1.5)
        s.polygon(path, [(x - w * 0.5, y), (x + w * 0.5, y), (x + w * 0.5, y + 0.45), (x - w * 0.5, y + 0.45)])
    glow = s.mask()
    s.polygon(glow, [(SUN[0] - 4, y0), (SUN[0] + 4, y0), (SUN[0] + 12, y1), (SUN[0] - 12, y1)])
    lay(s.rgb, ImageChops.multiply(blur(glow, 10), water), (255, 222, 160), 0.6)
    lay(s.rgb, ImageChops.multiply(blur(path, 0.3), water), (255, 250, 228), 0.95)
    edge = s.mask()
    ImageDraw.Draw(edge).line([s.pt(x, y + 0.4)[0] for x, y in top], fill=255, width=int(0.6 * s.S))
    lay(s.rgb, ImageChops.multiply(blur(edge, 1), water), (255, 236, 196), 0.6)


def paint_meadow(s):
    """The meadow from the river down: gold-green in the sun near the water, cooler toward the viewer, grass in
    pencil, clumps of wildflowers and reeds at the sides, bushes at the edges, the trampled earth under the pile, and
    the wooden rail on its two posts."""
    y1 = RIVER[1]
    grass = s.mask()
    s.polygon(grass, [(0, y1 + 1), (W, y1 + 1), (W, H + 2), (0, H + 2)])
    s.wash(grass, (164, 176, 116), alpha=1.0, rim=0.3, rim_px=3, grain=0.4, cell=10, rough=(1, 0.3, 4), dark=0.85,
           soft=0.5)
    stain = autocontrast(blur(s.noise(40), 8))
    glaze(s.rgb, ImageChops.multiply(grass, scale(stain, 1.4, -150)), (150, 170, 120), 0.4)
    shade = s.mask()
    shade.paste(Image.linear_gradient("L").resize((s.size[0], (H - y1) * s.S)), (0, y1 * s.S))
    glaze(s.rgb, shade, (112, 132, 140), 0.5)
    warm = s.mask()
    s.ellipse(warm, SUN[0], y1 + 4, 130, 18)
    lay(s.rgb, ImageChops.multiply(blur(warm, 30), grass), (240, 214, 140), 0.45)
    reeds = []
    for _ in range(90):
        x = rnd.uniform(0, W)
        if 70 < x < 250 and rnd.random() < 0.8:
            continue  # the middle kept calm
        reeds.append(([(x, y1 + 3), (x + rnd.uniform(-1.5, 1.5), y1 + 1 - rnd.uniform(1, 4))], 2))
    s.pencil(reeds, strength=0.45, colour=(64, 100, 56))
    blades = []
    for _ in range(300):
        x, y = rnd.uniform(0, W), rnd.uniform(y1 + 3, H)
        blades.append(([(x, y), (x + rnd.uniform(-1.2, 1.2), y - rnd.uniform(1, 2.6 + (y - y1) * 0.05))], 2))
    s.pencil(blades, strength=0.32, colour=(70, 96, 60))
    crowns, lights, shadows, trunks = s.mask(), s.mask(), s.mask(), []
    for x, y, r in ((6, 196, 9), (20, 202, 6), (306, 194, 10), (290, 202, 6)):  # bushes at the edges
        tree(s, crowns, lights, shadows, x, y, r)
    trees(s, crowns, lights, shadows, trunks, (72, 112, 66))
    lane = s.mask()  # a dirt path from the near left down to the river bank
    left = [(40 + 84 * t ** 0.9 + 10 * sin(t * 4), y1 + 2 + (RAIL_Y - y1 - 2) * (1 - t)) for t in
            (k / 12 for k in range(13))]
    width = [(x + 3 + 26 * (y - y1) / (RAIL_Y - y1), y) for x, y in left]
    s.polygon(lane, left + width[::-1])
    s.wash(lane, (206, 178, 136), alpha=0.95, rim=0.5, rim_px=2, grain=0.4, cell=6, rough=(1, 0.4, 4), dark=0.8,
           soft=0.6, cover=False)
    for colour, n in (((250, 244, 238), 30), ((200, 170, 230), 20), ((250, 212, 90), 24)):
        flowers = s.mask()
        for _ in range(n // 2):  # in clumps at the sides
            cx = rnd.choice((rnd.uniform(0, 80), rnd.uniform(240, W)))
            cy = rnd.uniform(y1 + 6, RAIL_Y - 2)
            for _ in range(5):
                s.ellipse(flowers, cx + rnd.uniform(-2.5, 2.5), cy + rnd.uniform(-1.2, 1.2), 0.75, 0.65)
        lay(s.rgb, blur(flowers, 0.4), colour, 0.95)
    earth = s.mask()  # trampled earth where the crates land
    s.polygon(earth, [(0, H - 6), (W, H - 7), (W, H + 2), (0, H + 2)])
    s.wash(earth, (150, 128, 104), alpha=0.75, rim=0.3, rim_px=2, grain=0.4, cell=6, rough=(1, 0.5, 4), dark=0.8,
           soft=0.8, cover=False)
    for x0 in (0, W - 4):  # the rail's posts
        post = s.mask()
        s.polygon(post, [(x0, RAIL_Y), (x0 + 4, RAIL_Y), (x0 + 4, H + 2), (x0, H + 2)])
        s.wash(post, (116, 78, 50), alpha=1.0, rim=0.6, rim_px=2, grain=0.3, cell=4, rough=None, dark=0.65, soft=0.3)
    beam = s.mask()
    s.polygon(beam, [(0, RAIL_Y), (W, RAIL_Y), (W, RAIL_Y + 3), (0, RAIL_Y + 3)])
    s.wash(beam, (138, 94, 60), alpha=1.0, rim=0.5, rim_px=2, grain=0.35, cell=4, rough=None, dark=0.6, soft=0.2)
    lit = s.mask()
    s.polygon(lit, [(0, RAIL_Y), (W, RAIL_Y), (W, RAIL_Y + 0.8), (0, RAIL_Y + 0.8)])
    lay(s.rgb, lit, (226, 184, 130), 0.9)
    under = s.mask()  # the rail's soft shadow on the grass under it
    s.polygon(under, [(0, RAIL_Y + 3), (W, RAIL_Y + 3), (W, RAIL_Y + 7), (0, RAIL_Y + 7)])
    glaze(s.rgb, blur(under, 6), (110, 120, 120), 0.4)
    tufts = []  # darker tufts along the foot of the screen
    for _ in range(90):
        x, y = rnd.uniform(0, W), rnd.uniform(H - 12, H)
        for dx in (-1.4, 0, 1.3):
            tufts.append(([(x, y), (x + dx, y - rnd.uniform(2, 4.5))], 2))
    s.pencil(tufts, strength=0.4, colour=(60, 84, 50))
    s.pencil([(jitter([(0, RAIL_Y + 3.2), (W, RAIL_Y + 3.2)], 0.15), 2)], strength=0.6, colour=INK)


def bucket_scene():
    """The still scene, 320 x 240, at 4x and then shrunk."""
    s = Strip(W, 0, H, False, sky_at)
    for painter in (paint_sky, paint_far, paint_orchard, paint_village, paint_river, paint_meadow):
        painter(s)
    s.paper(0.07)
    return s.rgb.resize((W, H), Image.LANCZOS).convert("RGBA")


# --- the sprites --------------------------------------------------------------------------------------------------

CRATE = 10  # px: games/bucket.py's SIZE
WOOD = ((232, 142, 48), (244, 196, 70), (200, 120, 64), (230, 170, 96))  # orange, gold, honey, light pine
OUTLINE = (78, 42, 22)  # dark brown


def crate(hue):
    """One crate, CRATE px: a dark-brown outline, a lighter top edge, plank seams and a few grain lines, the wood a
    little lighter at its sunlit top right."""
    base = WOOD[hue]
    img = Image.new("RGBA", (CRATE, CRATE), OUTLINE + (255,))
    n = CRATE - 1
    for y in range(1, n):
        for x in range(1, n):
            k = 1.0 + 0.08 * (x - y) / n  # lighter toward the top right
            if y in (4, 7):  # the seams between the planks
                k *= 0.72
            elif (x * 3 + y * 5 + hue) % 11 == 0:  # grain
                k *= 0.86
            img.putpixel((x, y), tuple(min(255, int(c * k)) for c in base) + (255,))
    light = tuple(min(255, int(c * 1.22 + 30)) for c in base)
    for x in range(1, n):
        img.putpixel((x, 1), light + (255,))  # the top edge, lit
    for y in (2, 5, 8):  # two or three grain lines along the planks
        for x in range(2 + y % 3, n - 1, 3):
            p = img.getpixel((x, y))
            img.putpixel((x, y), tuple(int(c * 0.82) for c in p[:3]) + (255,))
    return img


def pile(height, mix):
    """A column of the pile, height crates, each one's hue (mix + the crate's place from the bottom) % 4, as the game
    picks them."""
    img = Image.new("RGBA", (CRATE, CRATE * height))
    for k in range(height):
        img.paste(crate((mix + k) % len(WOOD)), (0, CRATE * (height - 1 - k)))
    return img


TUB = (64, 13)  # px: games/bucket.py's BUCKET_W, and its walls' 12 px and a 1 px rim above them
HANDLE = 10  # px the rope handle arcs above the rim
BUCKET = (64, 13 + HANDLE)  # px: the tub and its handle
TIPPED = (80, 54)  # px: the bucket tipped over at the round's end, round its foot's right corner
ROPE, ROPE_D = (214, 186, 128), (150, 116, 70)
STAVE, BAND, BAND_L, RIVET = (184, 110, 54), (60, 58, 70), (156, 156, 170), (214, 212, 220)
INSIDE = (66, 38, 24)
STAVES = 9


def bucket_pixels():
    """The bucket, BUCKET px, pixel by pixel: a rope handle arcing over a tub that narrows to its foot, nine staves in
    turn lighter and darker and lit from the sun on the right, two iron bands with a lit edge and rivets, the dark
    inside of its mouth, a lit rim, and a dark-brown outline."""
    img = Image.new("RGBA", BUCKET)
    img.paste(tub_pixels(), (0, HANDLE))
    w = BUCKET[0]
    last = None
    for x in range(3, w - 3):  # the rope: a half ellipse from one end of the rim to the other, twisted
        t = (x - w / 2) / (w / 2 - 3)
        y = round(HANDLE - (HANDLE - 1) * max(0.0, 1 - t * t) ** 0.5)
        for yy in range(min(y, last if last is not None else y), max(y, last if last is not None else y) + 1):
            img.putpixel((x, yy), (ROPE if (x + yy) % 3 else ROPE_D) + (255,))
        last = y
    return img


def tub_pixels():
    """The tub alone, TUB px."""
    w, h = TUB
    img = Image.new("RGBA", TUB)
    for y in range(h):
        x0 = round(3 * max(0, y - 1) / (h - 1))  # the taper
        x1 = w - 1 - x0
        for x in range(x0, x1 + 1):
            if y == 0 or y == h - 1 or x in (x0, x1):
                c = OUTLINE
            elif y in (1, 2) and x0 + 3 <= x <= x1 - 3:  # the mouth: the dark inside, its far wall a little lit
                c = INSIDE if y == 2 or x < x0 + 6 or x > x1 - 6 else (98, 60, 36)
            elif y in (1, 2):
                c = (236, 176, 108)  # the rim's ends, lit
            elif y in (4, 9):
                c = BAND_L if (x * STAVES // w) % 2 == 0 and (x * STAVES) % w < 8 else BAND
                if (x - x0) % 10 == 4:
                    c = RIVET
            elif y in (5, 10):
                c = BAND
            else:
                stave = (x - x0) * STAVES // (x1 - x0 + 1)
                edge = (x - x0) * STAVES % (x1 - x0 + 1) < STAVES  # a joint between two staves
                k = (1.0 if stave % 2 else 0.9) * (0.86 + 0.28 * x / w) * (1.08 if y == 3 else 1.0)
                k *= 0.7 if edge else 1.0
                if (x * 7 + y * 3) % 13 == 0:  # grain
                    k *= 0.88
                c = tuple(min(255, int(v * k)) for v in STAVE)
            img.putpixel((x, y), c + (255,))
    return img


def bucket(tipped=False):
    """The bucket, its foot on the rail; tipped, turned over to the right round its foot's right corner (painted at
    4x, turned and shrunk, then cut to a hard mask)."""
    img = bucket_pixels()
    if not tipped:
        return img
    w, h = TIPPED
    big = Image.new("RGBA", (w * 4, h * 4))
    big.paste(img.resize((BUCKET[0] * 4, BUCKET[1] * 4), Image.NEAREST), (0, (h - BUCKET[1]) * 4))
    big = big.convert("RGBA")
    big = big.rotate(-30, Image.BICUBIC, center=((BUCKET[0] - 3) * 4, h * 4))
    small = big.resize(TIPPED, Image.BOX)
    a = small.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    small.putalpha(a)
    return small


def coin():
    s = Sprite(8, 8)
    s.part(s.shape("ellipse", 0.3, 0.3, 7.7, 7.7), (240, 184, 40), light=(5, 2.5, 2.5, (255, 240, 150)), rim=0.5)
    s.part(s.shape("ellipse", 2.4, 2.2, 5.6, 5.8), (214, 150, 30), rim=0, grain=0)
    img = s.cut(ink=(110, 70, 20))
    img.putpixel((5, 2), (255, 255, 230, 255))
    return img


def sparkle():
    """A four-pointed star of light, 11 px, with a small diagonal glint."""
    img = Image.new("RGBA", (11, 11))
    for d in range(-5, 6):
        c = (255, 252, 226, 255) if abs(d) < 2 else (255, 222, 120, 255) if abs(d) < 4 else (250, 170, 60, 255)
        img.putpixel((5 + d, 5), c)
        img.putpixel((5, 5 + d), c)
    for d in (-1, 1):
        img.putpixel((5 + d, 5 + d), (255, 236, 170, 255))
        img.putpixel((5 + d, 5 - d), (255, 236, 170, 255))
    img.putpixel((5, 5), (255, 255, 255, 255))
    return img


PUFFS = ((5, 4), (7, 5), (10, 7))  # px: a chimney's puff as it grows


def puff(size):
    """A soft puff of chimney smoke: pale, lit warm on its sun side; the game draws it see-through."""
    w, h = size
    s = Sprite(w, h)
    s.part(s.shape("ellipse", 0.2, h * 0.3, w * 0.7, h - 0.2), (214, 208, 220), rim=0.2, grain=0.1)
    s.part(s.shape("ellipse", w * 0.3, 0.2, w - 0.2, h * 0.85), (232, 224, 228),
           light=(w * 0.8, h * 0.3, w * 0.4, (255, 232, 206)), rim=0.2, grain=0.1)
    return s.cut(outline=False)


def shimmer(frame):
    """A glint on the river, 9 x 2: a bright dash that slides a little each frame."""
    img = Image.new("RGBA", (9, 2))
    x0 = frame * 2
    for x in range(x0, x0 + 5):
        img.putpixel((x, 0), (255, 252, 236, 255))
    img.putpixel((x0 + 2, 1), (255, 236, 190, 255))
    return img


def paint_bucket_set():
    """Every bucket picture: the scene first (on the seed's stream), then the sprites."""
    pictures = {"bucket_scene": (bucket_scene(), False)}
    for hue in range(len(WOOD)):
        pictures["bucket_crate%d" % hue] = (crate(hue), True)
    for height in (1, 2, 3):
        for mix in range(len(WOOD)):
            pictures["bucket_pile%d_%d" % (height, mix)] = (pile(height, mix), True)
    pictures["bucket_bucket"] = (bucket(), True)
    pictures["bucket_tipped"] = (bucket(True), True)
    pictures["bucket_coin"] = (coin(), True)
    pictures["bucket_sparkle"] = (sparkle(), True)
    for i in range(3):
        pictures["bucket_shimmer%d" % i] = (shimmer(i), True)
    for i, size in enumerate(PUFFS):
        pictures["bucket_puff%d" % i] = (puff(size), True)
    return Painting(pictures)


ART_SET = ArtSet("bucket", 774, paint_bucket_set)
