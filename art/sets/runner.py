"""The runner's art: a sunset in five parallax layers, the full background as the fallback, and the sprites (the
runner's run and jump, cacti, a bird, coins, a clock, a star)."""

from math import cos, pi, sin

from PIL import Image, ImageChops, ImageDraw

from artset import ArtSet, Painting
from brush import (GROUND, H, STRIP, W, Sprite, Strip, autocontrast, blur, cloud, glaze, jitter, lay, peaks, ridge, rnd,
                   scale)
from export import checker


# --- the background, as parallax layers --------------------------------------------------------------------------

SKY_TOP, SKY_LOW = (248, 140, 104), (255, 224, 160)


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
        cloud(s, cx, cy, cw, lines)
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


SCENE = (("runner_run0", 52, GROUND - 24), ("cactus40", 150, GROUND - 40), ("cactus24", 172, GROUND - 24),
         ("bird0", 240, GROUND - 58), ("coin0", 100, 128), ("coin1", 118, 128), ("coin2", 136, 128),
         ("star", 280, 116), ("clock", 210, 136))


def paint_runner():
    """Every runner picture: the strips, the fallback, then the sprites, in the order that keeps their random stream."""
    strips = {name: painter() for name, painter, _, _ in LAYERS}
    bg = compose_bg(strips)
    layers = [(name, strips[name].game(keyed), strips[name].top, speed, keyed) for name, _, speed, keyed in LAYERS]
    sprites = {"runner_run%d" % i: runner(pose) for i, pose in enumerate(run_cycle())}
    sprites.update({"runner_" + name: runner(pose) for name, pose in JUMP.items()})
    for h in (16, 24, 32, 40, 48, 56, 64):
        sprites["cactus%d" % h] = cactus(h)
    sprites["bird0"], sprites["bird1"] = bird(0), bird(1)
    for i in range(4):
        sprites["coin%d" % i] = coin(i)
    sprites["clock"], sprites["star"] = clock(), star()
    pictures = {"bg": (bg, False)}
    pictures.update({name: (img, keyed) for name, img, _, _, keyed in layers})
    pictures.update({n: (img, True) for n, img in sprites.items()})
    return Painting(pictures, layers)



# --- on the preview sheets ---------------------------------------------------------------------------------------

def runner_sprites(painting):
    """The runner's sprites by name: its pictures less the fallback bg and the layers."""
    strips = {name for name, *_ in painting.layers}
    return {n: img for n, img in painting.images().items() if n != "bg" and n not in strips}


def frame(layers, sprites, shift, scene=SCENE):
    """One composed game frame: each layer moved by its speed, the sprites on top, as the board would."""
    out = Image.new("RGBA", (W, H))
    for name, img, top, speed, _ in layers:
        x = int(shift * speed) % img.width
        strip = Image.new("RGBA", (img.width * 2, img.height))
        strip.paste(img, (0, 0))
        strip.paste(img, (img.width, 0))
        out.alpha_composite(strip.crop((x, 0, x + W, img.height)), (0, top))
    for name, x, y in scene:
        out.alpha_composite(sprites[name], (x, y))
    return out.convert("RGB")


def runner_scene(painting):
    return frame(painting.layers, runner_sprites(painting), 900)


def side_by_side(sprites, bg, names, k=4, gap=6):
    """Sprites side by side at k times, each on the background where it would stand."""
    w, h = sprites[names[0]].size
    out = Image.new("RGB", (len(names) * (w * k + gap), h * k), (245, 240, 230))
    for i, name in enumerate(names):
        under = bg.convert("RGBA").crop((60, GROUND - h, 60 + w, GROUND))
        under.alpha_composite(sprites[name])
        out.paste(under.convert("RGB").resize((w * k, h * k), Image.NEAREST), (i * (w * k + gap), 0))
    return out


def runner_sheet(painting, sheet, y):
    """The fallback and a composed frame, each strip alone with its seam, the run and the jump, the cacti."""
    bg, layers, sprites = painting.images()["bg"], painting.layers, runner_sprites(painting)
    put = sheet.put
    put("bg 320x240 (the fallback) at 2x", bg.convert("RGB").resize((W * 2, H * 2), Image.NEAREST), 10, y)
    f = frame(layers, sprites, 900)
    y = put("parallax layers composed, a frame at 2x, with sprites", f.resize((W * 2, H * 2), Image.NEAREST),
            W * 2 + 30, y) + 14
    for name, img, top, speed, _ in layers:  # each strip alone at 2x, on a checkerboard, twice so the seam shows
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
        sheet.draw.line([(660, y - 10 - ch.height), (660, y - 14)], fill=(255, 0, 0), width=1)
    run = ["runner_run%d" % i for i in range(6)]
    jump = ["runner_" + n for n in JUMP]
    put("the run cycle, runner_run0 to runner_run5, at 4x", side_by_side(sprites, bg, run), 10, y)
    y = put("the jump: " + ", ".join(jump) + ", at 4x", side_by_side(sprites, bg, jump), 10 + 6 * 70 + 30, y) + 14
    cacti = [n for n in sprites if n.startswith("cactus")]
    scene = [(n, 14 + i * 44, GROUND - sprites[n].height) for i, n in enumerate(cacti)] + [(run[0], 300, GROUND - 24)]
    over = frame(layers, sprites, 0, scene).crop((0, 110, W, H)).resize((W * 3, (H - 110) * 3), Image.NEAREST)
    return put("every cactus over the hills band, a composed frame at 3x", over, 10, y) + 14


def sprite_grid(painting, sheet, y):
    """Every sprite but the runner's own, at 4x on a checkerboard and on the background, drawn after all sets."""
    bg, sprites = painting.images()["bg"], runner_sprites(painting)
    x = 10
    tallest = 0
    for name, img in sprites.items():
        if name.startswith("runner"):
            continue  # shown in the strips above
        w, h = img.size
        big = img.resize((w * 4, h * 4), Image.NEAREST)
        cell = 2 * w * 4 + 6
        if x + cell > sheet.image.width - 10:
            x, y, tallest = 10, y + tallest + 30, 0
        ch = checker(w * 4, h * 4)
        ch.paste(big, (0, 0), big)
        gy = GROUND - h if name.startswith(("runner", "cactus")) else 100
        under = bg.convert("RGB").crop((60, gy, 60 + w, gy + h)).resize((w * 4, h * 4), Image.NEAREST)
        under.paste(big, (0, 0), big)
        sheet.draw.text((x, y), "%s %dx%d" % (name, w, h), fill=sheet.INK, font=sheet.font)
        sheet.image.paste(ch, (x, y + 18))
        sheet.image.paste(under, (x + w * 4 + 6, y + 18))
        x += max(cell, 120) + 14
        tallest = max(tallest, h * 4)
    return y + tallest


ART_SET = ArtSet("runner", 562, paint_runner, aliases={"runner_jump": "runner_apex"}, index_layers=True,
                 sheet_fn=runner_sheet, tail_fn=sprite_grid, scene_fn=runner_scene, ink_accent=RED)
