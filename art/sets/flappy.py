"""Flappy's art (P564): a bright, artsy morning in five parallax layers, the sandstone pillars and the bird."""

from math import cos, pi, sin

from PIL import Image, ImageChops, ImageDraw

from brush import H, STRIP, W, ArtSet, Painting, Sprite, Strip, autocontrast, blur, glaze, jitter, lay, rnd, scale
from sets.runner import cloud


MORNING = ((76, 172, 188), (186, 226, 216), (255, 212, 168))  # teal at the top, pale aqua, apricot low
FLAPPY_FLOOR = 222


def morning_at(y):
    t = max(0.0, min(1.0, (y - 16) / (FLAPPY_FLOOR - 16)))
    a, b, t = (MORNING[0], MORNING[1], t / 0.55) if t < 0.55 else (MORNING[1], MORNING[2], (t - 0.55) / 0.45)
    return tuple(int(p + (q - p) * t) for p, q in zip(a, b))


def flappy_sky():
    """Still: the morning wash with soft blooms, a low sun and its halo, a few far birds in pencil."""
    s = Strip(W, 0, H, False, morning_at)
    blooms = autocontrast(blur(s.noise(200), 26))
    glaze(s.rgb, scale(blooms, 1.4, -150), (190, 230, 236), 0.4)  # cool blooms
    glaze(s.rgb, scale(ImageChops.invert(blooms), 1.3, -160), (255, 226, 200), 0.35)  # warm breath
    sx, sy, sr = 236, 132, 18
    halo = s.mask()
    s.ellipse(halo, sx, sy, sr * 3, sr * 3, 150)
    lay(s.rgb, blur(halo, sr * 5), (255, 236, 196))
    disc = s.mask()
    s.ellipse(disc, sx, sy, sr, sr)
    s.wash(disc, (255, 246, 214), alpha=0.97, rim=0.3, rim_px=8, grain=0.06, rough=(3, 0.4, 14), dark=0.96, soft=2)
    ticks = []
    for x, y, k in ((54, 40, 1.0), (66, 46, 0.8), (78, 38, 0.9), (168, 30, 0.7), (286, 56, 0.8)):
        ticks.append(([(x - 2.4 * k, y - 1.2 * k), (x - 1.0 * k, y - 0.2 * k), (x, y + 0.4 * k),
                       (x + 1.0 * k, y - 0.2 * k), (x + 2.4 * k, y - 1.4 * k)], 2))
    s.pencil(ticks, strength=0.6, colour=(60, 70, 90))
    s.paper(0.03)
    return s


def flappy_clouds():
    """Big expressive cumulus: white, blue-grey bellies, apricot tops; transparent between them."""
    s = Strip(STRIP, 20, 100, True, morning_at)
    lines = []
    for cx, cy, cw in ((84, 78, 108), (232, 108, 70), (352, 66, 92), (486, 104, 122), (604, 58, 58)):
        cloud(s, cx, cy, cw, lines, (255, 252, 246), (176, 198, 224), (255, 220, 188))
    s.pencil(lines, strength=0.3, colour=(80, 100, 130))
    s.paper(0.04)
    return s


def flappy_far():
    """A distant hill town and forest in cool blue-green, paler toward its foot like morning mist."""
    top, h = 110, 90
    s = Strip(STRIP, top, h, True, morning_at)
    col = (118, 166, 168)
    pts = [(x, 168 - 12 * (0.5 + 0.5 * sin(2 * pi * 2 * x / STRIP + 0.7) * cos(2 * pi * 3 * x / STRIP)))
           for x in range(0, STRIP + 1, 2)]
    land = s.mask()
    s.polygon(land, pts + [(STRIP, top + h + 4), (0, top + h + 4)])

    def ground_y(x):
        return pts[int(x % STRIP) // 2][1]

    trees = s.mask()
    for i in range(70):  # pointed firs and round trees along the ridge
        x = rnd.uniform(0, STRIP)
        if 250 < x < 330:
            continue  # the town's hill
        y = ground_y(x) + 1
        if rnd.random() < 0.6:
            hh = rnd.uniform(7, 14)
            s.polygon(trees, [(x, y - hh), (x + hh * 0.3, y), (x - hh * 0.3, y)])
        else:
            r = rnd.uniform(3, 5.5)
            s.ellipse(trees, x, y - r * 0.8, r, r)
    town = s.mask()
    x = 254.0
    while x < 326:  # little houses, and a church with a spire
        w, hh = rnd.uniform(6, 10), rnd.uniform(5, 10)
        y = ground_y(x + w / 2) + 1
        s.polygon(town, [(x, y), (x, y - hh), (x + w / 2, y - hh - w * 0.5), (x + w, y - hh), (x + w, y)])
        x += w + rnd.uniform(0, 1.5)
    y = ground_y(290)
    s.polygon(town, [(287, y), (287, y - 16), (290, y - 28), (293, y - 16), (293, y)])
    shape = ImageChops.lighter(ImageChops.lighter(land, trees), town)
    m = s.wash(shape, col, alpha=0.97, rim=0.6, rim_px=5, grain=0.3, cell=16, rough=(1, 0.3, 6), dark=0.8, soft=0.8)
    walls = s.wash(town, (150, 186, 184), alpha=0.6, rim=0.0, grain=0.2, cell=8, rough=None, soft=0.6, cover=False)
    lit = s.mask()
    for wx in range(256, 324, 5):  # sunlit window glints
        if rnd.random() < 0.5:
            wy = ground_y(wx) - rnd.uniform(3, 6)
            s.polygon(lit, [(wx, wy), (wx + 1.6, wy), (wx + 1.6, wy + 1.8), (wx, wy + 1.8)])
    lay(s.rgb, ImageChops.multiply(lit, walls), (255, 230, 170))
    mist = s.mask()
    mist.paste(Image.linear_gradient("L").resize((s.size[0], 34 * s.S)), (0, (h - 34) * s.S))
    lay(s.rgb, ImageChops.multiply(mist, m), (206, 226, 214), 0.55)
    s.paper(0.06)
    return s


def flappy_near():
    """Rounded bushes and trees in warm greens, lit from the low sun on the right; a flat foot at row 222."""
    top, h = 160, FLAPPY_FLOOR - 160
    s = Strip(STRIP, top, h, True, (150, 190, 170))
    lines = []
    trunks = []
    for x, y, r in ((40, 184, 11), (196, 180, 13), (330, 188, 10), (452, 179, 13), (566, 186, 11)):
        trunks.append(([(x, y + r * 0.6), (x, 214)], 6))
        crown = s.mask()
        for dx, dy, k in ((0, 0, 1.0), (-r * 0.6, r * 0.35, 0.7), (r * 0.6, r * 0.3, 0.72)):
            s.ellipse(crown, x + dx, y + dy, r * k, r * k * 0.92)
        m = s.wash(crown, (96, 150, 64), alpha=0.97, rim=0.7, rim_px=5, grain=0.3, cell=10, rough=(1.5, 0.4, 6),
                   dark=0.72, soft=1)
        light = s.mask()
        s.ellipse(light, x + r * 0.35, y - r * 0.35, r * 0.55, r * 0.45)
        lay(s.rgb, ImageChops.multiply(blur(light, 8), m), (176, 210, 104), 0.7)
        lines.append(([(x + r * 0.9 * cos(a), y + r * 0.85 * sin(a)) for a in [3.5 + i * 0.25 for i in range(9)]], 2))
    s.pencil(trunks, strength=0.75, colour=(88, 60, 40))
    bush = s.mask()
    puffs = []
    x = 0.0
    while x < STRIP:
        r = rnd.uniform(9, 16)
        puffs.append((x, 206 - r * 0.45 + rnd.uniform(-2, 2), r))
        x += r * rnd.uniform(1.0, 1.4)
    for x, y, r in puffs:
        s.ellipse(bush, x, y, r, r * 0.8)
    s.polygon(bush, [(0, 204), (STRIP, 204), (STRIP, FLAPPY_FLOOR + 4), (0, FLAPPY_FLOOR + 4)])
    m = s.wash(bush, (122, 172, 70), alpha=0.98, rim=0.7, rim_px=5, grain=0.3, cell=10, rough=(1.5, 0.4, 6),
               dark=0.74, soft=1)
    light, dots = s.mask(), s.mask()
    for x, y, r in puffs:
        s.ellipse(light, x + r * 0.3, y - r * 0.4, r * 0.55, r * 0.35)
        if rnd.random() < 0.6:
            lines.append(([(x + r * 0.95 * cos(a), y + r * 0.76 * sin(a)) for a in [3.6 + i * 0.22 for i in range(9)]],
                          2))
        for _ in range(2):  # berries and blossoms
            s.ellipse(dots, x + rnd.uniform(-r * 0.6, r * 0.6), y + rnd.uniform(-r * 0.2, r * 0.5), 0.8, 0.8)
    lay(s.rgb, ImageChops.multiply(blur(light, 8), m), (190, 214, 110), 0.65)
    shade = s.mask()
    shade.paste(Image.linear_gradient("L").resize((s.size[0], 14 * s.S)), (0, (h - 14) * s.S))
    glaze(s.rgb, ImageChops.multiply(shade, m), (90, 120, 80), 0.45)
    lay(s.rgb, ImageChops.multiply(dots, m), (250, 236, 240))
    s.pencil(lines, strength=0.4, colour=(50, 80, 40))
    s.paper(0.08)
    return s


def flappy_ground():
    """Grass with a few flowers on painted earth, rows 222 to 240. Opaque."""
    top, h = FLAPPY_FLOOR, H - FLAPPY_FLOOR
    s = Strip(STRIP, top, h, True, (100, 140, 70))
    g = FLAPPY_FLOOR
    earth = s.mask()
    s.polygon(earth, [(0, g + 5), (STRIP, g + 5), (STRIP, H + 2), (0, H + 2)])
    s.wash(earth, (176, 126, 82), alpha=1.0, rim=0.0, grain=0.3, cell=16, rough=None, soft=0)
    stain = autocontrast(blur(s.noise(50), 5))
    glaze(s.rgb, ImageChops.multiply(earth, scale(stain, 1.4, -150)), (190, 140, 100), 0.5)
    grass = s.mask()
    s.polygon(grass, [(0, g), (STRIP, g), (STRIP, g + 5.5), (0, g + 5.5)])
    s.wash(grass, (124, 186, 74), alpha=1.0, rim=0.5, rim_px=3, grain=0.25, cell=8, rough=(1, 0.4, 4), dark=0.8,
           soft=0.5)
    lines, flowers, hearts = [], s.mask(), s.mask()
    for i in range(0, STRIP, 3):
        x = i + rnd.uniform(0, 2)
        lines.append(([(x, g + 4), (x + rnd.uniform(-1, 1), g + rnd.uniform(0.3, 1.6))], 2))
    s.pencil(lines, strength=0.4, colour=(50, 90, 40))
    petals = ((236, 84, 96), (255, 250, 240), (250, 204, 64), (150, 120, 220))
    spots = [(rnd.uniform(0, STRIP), g + rnd.uniform(1.2, 3.8), petals[i % 4]) for i in range(30)]
    for colour in petals:
        m = s.mask()
        for x, y, c in spots:
            if c == colour:
                s.ellipse(m, x, y, 1.1, 0.9)
        lay(s.rgb, blur(m, 0.6), colour)
    for x, y, _ in spots:
        s.ellipse(hearts, x, y, 0.35, 0.35)
    lay(s.rgb, hearts, (250, 190, 60))
    hatch = []
    for _ in range(22):
        x, y = rnd.uniform(0, STRIP), rnd.uniform(g + 9, H - 2)
        for i in range(3):
            hatch.append(([(x + i * 1.6, y), (x + i * 1.6 + 2.4, y - 2.6)], 2))
    s.pencil(hatch + [(jitter([(0, g + 5.4), (STRIP, g + 5.4)], 0.2), 2)], strength=0.35, colour=(90, 56, 30))
    s.paper(0.1)
    return s


FLAPPY_LAYERS = (  # name, painter, speed, keyed: back to front
    ("flappy_sky", flappy_sky, 0.0, False),
    ("flappy_clouds", flappy_clouds, 0.15, True),
    ("flappy_far", flappy_far, 0.3, True),
    ("flappy_near", flappy_near, 0.6, True),
    ("flappy_ground", flappy_ground, 1.0, False),
)
PILLAR_INK = (44, 38, 52)


def pillar(cap_at_bottom):
    """A mossy sandstone pillar, 32 x 240: a 26 px shaft, a wider cap at the gap end, a dark outline."""
    s = Sprite(32, 240)
    stone, light, shade = (222, 192, 150), (246, 226, 190), (150, 140, 170)

    def y(v):  # rows from the gap end
        return 240 - v if cap_at_bottom else v

    def box(x0, v0, x1, v1, r):
        a, b = sorted((y(v0), y(v1)))
        return s.shape("rect", x0, a, x1, b, r)

    s.part(box(3.6, 8, 28.4, 250, 0.6), stone, light=(9, 120, 30, light), rim=0.3, grain=0.14)
    s.part(box(1.2, 1.2, 30.8, 11.5, 1.5), (230, 202, 160), light=(12, y(6), 6, light), rim=0.45, grain=0.12)
    moss = Image.new("L", s.size, 0)
    d = ImageDraw.Draw(moss)
    S = s.S
    for _ in range(9):  # moss along the cap, a few drips, a few patches down the shaft
        x, v, r = rnd.uniform(3, 29), rnd.uniform(9.5, 13), rnd.uniform(1.4, 2.6)
        d.ellipse(((x - r) * S, (y(v) - r) * S, (x + r) * S, (y(v) + r) * S), fill=255)
    for _ in range(4):
        x, v = rnd.uniform(6, 26), rnd.uniform(12, 20)
        d.line([(x * S, y(11) * S), (x * S, y(v) * S)], fill=255, width=int(1.4 * S))
    for _ in range(5):
        x, v, r = rnd.choice((4.5, 27.5)), rnd.uniform(40, 220), rnd.uniform(1.4, 2.4)
        d.ellipse(((x - r) * S, (y(v) - r * 1.6) * S, (x + r) * S, (y(v) + r * 1.6) * S), fill=255)
    moss = ImageChops.multiply(moss, ImageChops.lighter(box(3.6, 8, 28.4, 250, 0.6), box(1.2, 1.2, 30.8, 11.5, 1.5)))
    s.part(moss, (104, 156, 70), light=(10, y(10), 4, (150, 196, 90)), rim=0.4, grain=0.2)
    img = s.cut(ink=PILLAR_INK)
    mortar = (176, 146, 116)
    for row, v in enumerate(range(24, 240, 14)):  # stone courses and their joints, in pencil
        yy = int(y(v))
        for x in range(4, 28):
            if 0 <= yy < 240 and img.getpixel((x, yy))[:3] not in (PILLAR_INK,) and img.getpixel((x, yy))[3]:
                img.putpixel((x, yy), mortar + (255,))
        jx = 11 if row % 2 else 20
        for k in range(1, 14):
            yj = int(y(v + k))
            if 0 <= yj < 240 and img.getpixel((jx, yj))[3] and img.getpixel((jx, yj))[:3] != PILLAR_INK:
                img.putpixel((jx, yj), mortar + (255,))
    for v in range(12, 240):  # a cool shadow down the right side of the shaft
        yy = int(y(v))
        for x, k in ((26, 0.8), (27, 0.72)):
            p = img.getpixel((x, yy))
            if p[3] and p[:3] != PILLAR_INK:
                img.putpixel((x, yy), tuple(int(c * k + sh * (1 - k)) for c, sh in zip(p[:3], shade)) + (255,))
    return img


def flappy_bird(wing_up, tilt):
    """A round, cheerful bird, 18 x 14, facing right; tilt in degrees, nose up when positive."""
    s = Sprite(18, 14)
    body, belly, wing = (252, 204, 66), (255, 240, 204), (240, 150, 48)
    s.part(s.shape("poly", (1.0, 5.2), (4.2, 6.6), (4.2, 8.8), (0.8, 9.2)), (226, 132, 44), rim=0.2)  # the tail
    s.part(s.shape("ellipse", 2.8, 2.2, 14.4, 12.4), body, light=(10, 4, 3.5, (255, 236, 140)), rim=0.4)
    s.part(s.shape("ellipse", 6.4, 7.0, 13.8, 12.2), belly, rim=0.15)
    s.part(s.shape("poly", (13.6, 6.4), (17.2, 7.8), (13.6, 9.4)), (244, 112, 40), rim=0.2)  # the beak
    s.part(s.shape("ellipse", 9.6, 3.2, 13.6, 7.2), (255, 255, 255), rim=0, grain=0)  # the eye
    s.part(s.shape("ellipse", 11.4, 4.2, 13.4, 6.6), (24, 20, 32), rim=0, grain=0)
    s.part(s.shape("ellipse", 10.4, 7.6, 12.4, 9.0), (250, 150, 130), rim=0, grain=0)  # a rosy cheek
    if wing_up:
        s.part(s.shape("poly", (4.0, 7.4), (5.6, 2.0), (9.0, 1.4), (9.2, 7.6)), wing, light=(7, 2.4, 2, body), rim=0.4)
    else:
        s.part(s.shape("poly", (4.0, 7.0), (9.4, 7.0), (8.2, 12.4), (5.0, 11.6)), wing, light=(7, 8, 2, body), rim=0.4)
    s.turn(tilt, (9.0, 7.3))
    img = s.cut()
    if tilt <= 0:  # the eye's glint
        img.putpixel((12, 5 if tilt == 0 else 6), (255, 255, 255, 255))
    return img


def flappy_scene(pics, layers, shift=500):
    """A frame as the game draws it: the layers, two pipe pairs with gaps at different heights, the bird."""
    out = Image.new("RGBA", (W, H))
    for name, img, top, speed, _ in layers[:-1]:
        x = int(shift * speed) % img.width
        out.alpha_composite(Image.merge("RGBA", img.split()).crop((x, 0, x + W, img.height))
                            if x + W <= img.width else _wrapped(img, x), (0, top))
    half = 42
    for px, gap in ((150, 90), (280, 150)):
        top_pipe = pics["flappy_pipe_top"]
        cut = 240 - (gap - half - 16)
        out.alpha_composite(top_pipe.crop((0, cut, 32, 240)), (px, 16))
        out.alpha_composite(pics["flappy_pipe_bottom"].crop((0, 0, 32, FLAPPY_FLOOR - gap - half)), (px, gap + half))
    name, img, top, speed, _ = layers[-1]
    out.alpha_composite(_wrapped(img, int(shift * speed) % img.width), (0, top))
    out.alpha_composite(pics["flappy_bird01"], (80 - 9, 110))
    return out.convert("RGB")


def _wrapped(img, x):
    two = Image.new("RGBA", (img.width * 2, img.height))
    two.paste(img, (0, 0))
    two.paste(img, (img.width, 0))
    return two.crop((x, 0, x + W, img.height))


def paint_flappy():
    """Every flappy picture: the five layers, then the pillars and the bird's six frames."""
    layers = []
    for name, painter, speed, keyed in FLAPPY_LAYERS:
        s = painter()
        layers.append((name, s.game(keyed), s.top, speed, keyed))
    pics = {"flappy_pipe_top": pillar(True), "flappy_pipe_bottom": pillar(False)}
    for i, tilt in enumerate((18, 0, -30)):
        for frame_ in (0, 1):
            pics["flappy_bird%d%d" % (i, frame_)] = flappy_bird(frame_ == 0, tilt)
    pictures = {name: (img, keyed) for name, img, _, _, keyed in layers}
    pictures.update({n: (img, True) for n, img in pics.items()})
    return Painting(pictures, layers)


ART_SET = ArtSet("flappy", 564, paint_flappy)
