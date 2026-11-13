"""Meteors' art (P773): a violet to rose dusk over a cool dark plain, the walker's run posed by motion capture through
art/mocap.py (the fireman's painter of art/sets/rescue.py, as a civilian with a cyan scarf), and the meteors' fire: the
rock and its glow, the coal that dims, the impact's light on the ground, the landing shadow and the ground's flash. The
only warm bright things are the meteors, the coals and the impacts.

The walker is painted only when the CMU files are in mocap.CMU_DIR. Without them his pictures are read back from
games/art as committed, so art/paint.py still paints every other set and writes the same files.
"""

from math import cos, hypot, pi, sin

from PIL import Image, ImageChops, ImageOps

import mocap
from artset import ArtSet, Painting
from brush import H, W, Sprite, Strip, autocontrast, blur, glaze, lay, rnd, scale
from sets.rescue import Figure, along, read_committed

DUSK = ((30, 20, 58), (92, 50, 108), (214, 112, 132))  # the sky from the top, to the middle, to the rose horizon
HORIZON = 176
GROUND = 206  # the plain's near edge: the ground band the walker runs on starts here
PLAIN = (58, 56, 88)  # the cool ground


def dusk_at(y):
    t = max(0.0, min(1.0, y / HORIZON))
    a, b, t = (DUSK[0], DUSK[1], t / 0.55) if t < 0.55 else (DUSK[1], DUSK[2], (t - 0.55) / 0.45)
    return tuple(int(p + (q - p) * t) for p, q in zip(a, b))


# --- the still picture, painted in layers -------------------------------------------------------------------------

def paint_heavens(s):
    """Stars in the high violet, a thin moon, soft blooms, and the smoke of earlier meteors drawn across the sky."""
    stars = s.mask()
    for _ in range(46):
        s.ellipse(stars, rnd.uniform(0, W), rnd.uniform(18, 90), 0.35, 0.35)
    lay(s.rgb, blur(stars, 1), (236, 226, 250), 0.85)
    moon, bite = s.mask(), s.mask()
    s.ellipse(moon, 64, 44, 7, 7)
    s.ellipse(bite, 67, 41, 7, 7)
    lay(s.rgb, blur(ImageChops.subtract(moon, bite), 1.5), (250, 230, 236), 0.9)
    blooms = autocontrast(blur(s.noise(160), 24))
    glaze(s.rgb, scale(blooms, 1.4, -150), (150, 110, 170), 0.35)
    for x0, y0, x1, y1, w in ((340, 20, 150, 150, 3.0), (250, 26, 40, 140, 2.2), (120, 18, -20, 104, 1.6)):
        trail = s.mask()  # a smoke trail, wider and paler toward the ground
        s.polygon(trail, [(x0, y0), (x0 + 1, y0 + 1), (x1 + w * 4, y1), (x1 - w * 4, y1)])
        glaze(s.rgb, blur(trail, 10), (120, 90, 120), 0.5)
    haze = s.mask()
    s.polygon(haze, [(0, HORIZON - 40), (W, HORIZON - 50), (W, HORIZON + 4), (0, HORIZON + 4)])
    lay(s.rgb, blur(haze, 40), (240, 150, 140), 0.35)  # the glow low over the horizon


def paint_ridges(s):
    """Two far ridges in cool violet, paler with distance, and a near rise of the plain with a few bare trees."""
    for base, amp, k, colour in ((HORIZON, 22, 3, (122, 78, 128)), (HORIZON + 14, 16, 5, (78, 56, 102))):
        pts = [(x, base - amp * (0.5 + 0.5 * sin(2 * pi * k * x / W + k) * cos(2 * pi * 2 * x / W)))
               for x in range(0, W + 1, 2)]
        m = s.mask()
        s.polygon(m, pts + [(W, H + 2), (0, H + 2)])
        s.wash(m, colour, alpha=0.97, rim=0.5, rim_px=4, grain=0.25, cell=14, rough=(1, 0.3, 6), dark=0.85, soft=0.8)
    lines = []
    for x, h in ((26, 20), (276, 26), (300, 14)):  # bare trees on the rise, in pencil
        y = HORIZON + 12
        lines.append(([(x, y), (x + 1, y - h)], 3))
        for k in range(3):
            ty = y - h * (0.5 + 0.18 * k)
            side = 1 if k % 2 else -1
            lines.append(([(x + 0.6, ty), (x + side * h * 0.3, ty - h * 0.2)], 2))
    s.pencil(lines, strength=0.8, colour=(40, 30, 56))


def paint_plain(s):
    """The plain the walker runs on: cool slate, lighter where the sky lights it, stones with lit tops, grass tufts."""
    near = s.mask()
    s.polygon(near, [(0, GROUND), (W, GROUND - 3), (W, H + 2), (0, H + 2)])
    s.wash(near, PLAIN, alpha=1.0, rim=0.3, rim_px=3, grain=0.35, cell=8, rough=(0.8, 0.3, 4), dark=0.8, soft=0.5)
    sheen = s.mask()
    s.polygon(sheen, [(0, GROUND), (W, GROUND - 3), (W, GROUND + 8), (0, GROUND + 10)])
    glaze(s.rgb, blur(sheen, 10), (200, 150, 170), 0.2)
    shade = s.mask()
    shade.paste(Image.linear_gradient("L").resize((s.size[0], 22 * s.S)), (0, (H - 22) * s.S))
    glaze(s.rgb, shade, (80, 76, 120), 0.4)  # darker toward the viewer
    stones, tops = s.mask(), s.mask()
    for _ in range(26):
        x, y, r = rnd.uniform(0, W), rnd.uniform(GROUND + 4, H - 2), rnd.uniform(1.0, 3.2)
        s.ellipse(stones, x, y, r * 1.4, r * 0.7)
        s.ellipse(tops, x + r * 0.3, y - r * 0.4, r * 0.8, r * 0.25)
    lay(s.rgb, stones, (36, 34, 58), 0.9)
    lay(s.rgb, ImageChops.multiply(tops, stones), (150, 132, 170), 0.8)
    tufts = []
    for _ in range(60):
        x, y = rnd.uniform(0, W), rnd.uniform(GROUND + 1, H)
        for dx in (-1.2, 0, 1.1):
            tufts.append(([(x, y), (x + dx * 1.4, y - rnd.uniform(1.5, 3.4))], 2))
    s.pencil(tufts, strength=0.55, colour=(30, 30, 50))


def meteors_sky():
    """The still picture, 320 x 240: the heavens, the ridges and the plain, at 4x, then shrunk."""
    s = Strip(W, 0, H, False, dusk_at)
    for painter in (paint_heavens, paint_ridges, paint_plain):
        painter(s)
    s.paper(0.05)
    return s.rgb.resize((W, H), Image.LANCZOS).convert("RGBA")


# --- the walker ---------------------------------------------------------------------------------------------------

WALKER_PX = 27  # px per body height: the head's top stays inside the 32 px hit box (games/meteors.py's WALKER_H)
FIG = (30, 32)  # each pose's picture, w x h; drawn at the walker's left edge less FIG_DX, its soles on the last row
FIG_DX = 9  # so the 12 px hit box is columns 9 to 20, its middle at 14.5, where the torso is
SCARF, SCARF_HIT = (64, 224, 236), (236, 52, 52)  # the one accent, and its flash when a meteor hits


class Walker(Figure):
    """The fireman's painter as a civilian runner: a long dark coat and no helmet, a bare head, a 1 px rim lit by the
    dusk (rose ahead, violet behind), and a scarf that streams behind his neck; flutter picks its shape, 0 to 2."""

    PX = WALKER_PX
    NEAR, FAR = (20, 18, 30), (50, 44, 70)
    RIMS = ((236, 168, 190), (150, 120, 210))
    BANDS = False
    HIPS = -0.5  # the torso near the box's middle, and a foot in the box's columns on every row

    def __init__(self, scarf, flutter):
        super().__init__(FIG)
        self.scarf, self.flutter = scarf, flutter

    def head(self, s, p):
        hx, hy = p["head"]
        r = 0.07 * self.PX
        s.part(s.shape("ellipse", hx - r, hy - r * 1.05, hx + r, hy + r * 1.1), self.NEAR, rim=0, grain=0)
        neck = along(p["lowerneck"], p["head"], 0.35)
        wave = (0.0, 1.0, -0.8)[self.flutter]
        tail = [neck, (neck[0] - 3.5, neck[1] + 0.6 + wave * 0.4), (neck[0] - 6.5, neck[1] + 0.2 - wave),
                (neck[0] - 9.5, neck[1] + 1.4 + wave * 0.6)]
        s.part(s.shape("line", *tail, width=1.5), self.scarf, rim=0, grain=0)
        s.part(s.shape("ellipse", neck[0] - 1.6, neck[1] - 1.0, neck[0] + 1.6, neck[1] + 1.2), self.scarf, rim=0,
               grain=0)


RUN = mocap.CYCLES[0]  # the run of subject 9, trial 1: 12 poses, a stride of 1.698 body heights


class WalkerPoses:
    """The walker's pictures by name, run and hit, facing right and left: painted from the CMU files when they are
    there, else read back from the committed games/art files (and said so)."""

    def __init__(self, folder=mocap.CMU_DIR):
        self.folder, self.capture = folder, mocap.Capture(folder)

    @staticmethod
    def names():
        return ["meteors_%s_%s%d" % (kind, side, i) for kind in ("run", "hit") for side in "rl"
                for i in range(RUN.poses)]

    def pictures(self):
        missing = self.capture.missing()
        if missing:
            print("meteors: no %s in %s: the walker is read back from games/art, not painted again" % (
                ", ".join(missing), self.folder))
            return read_committed(self.names())
        out = {}
        poses = self.capture.poses(RUN)
        for kind, scarf in (("run", SCARF), ("hit", SCARF_HIT)):
            right = [Walker(scarf, i % 3).paint(pose) for i, pose in enumerate(poses)]
            out.update({"meteors_%s_r%d" % (kind, i): img for i, img in enumerate(right)})
            out.update({"meteors_%s_l%d" % (kind, i): ImageOps.mirror(img) for i, img in enumerate(right)})
        return out


# --- the meteors' fire --------------------------------------------------------------------------------------------

ROCK = 10  # px: the rock's picture, round its 8 px body
ROCK_FRAMES = 4
HALO = 24  # px: the glow round a falling rock, drawn see-through
COAL = (10, 7)  # px: the coal's picture, w x h, its base on the screen's last row
COAL_FRAMES = 4
GLOW = (56, 16)  # px: the impact's light on the ground
SHADOW = (8, 3)  # px: the landing shadow, the mark's full width
RING = (12, 5)  # px: the white ring round the shadow in its last moments
FLASH = (W, 14)  # px: the ground band that flashes white at an impact
BAYER = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)  # a 4 x 4 ordered dither, for soft edges in a hard mask


def dithered(img, cover):
    """img with a hard mask from cover (0 to 1 per pixel, a function of x and y): an ordered dither, so a glow drawn
    with one alpha still fades at its edge."""
    out = img.copy()
    for y in range(img.height):
        for x in range(img.width):
            if cover(x, y) * 16 <= BAYER[(y % 4) * 4 + x % 4]:
                out.putpixel((x, y), (0, 0, 0, 0))
    return out


def radial(size, stops, cover):
    """A picture whose colour runs through stops ((d, r, g, b), d from 0 at the middle to 1 at the edge of the
    ellipse that fills size), cut by cover(d)."""
    w, h = size
    img = Image.new("RGBA", size)
    ds = {}
    for y in range(h):
        for x in range(w):
            d = hypot((x + 0.5 - w / 2) / (w / 2), (y + 0.5 - h / 2) / (h / 2))
            ds[x, y] = d
            for (d0, *c0), (d1, *c1) in zip(stops, stops[1:]):
                if d <= d1:
                    t = max(0.0, (d - d0) / (d1 - d0))
                    img.putpixel((x, y), tuple(int(a + (b - a) * t) for a, b in zip(c0, c1)) + (255,))
                    break
    return dithered(img, lambda x, y: cover(ds[x, y]))


def halo_cover(d):
    """A glow's cover by its distance from the middle: whole inside, every other pixel in its outer ring."""
    return 1 if d < 0.62 else 0.5 if d < 1 else 0


def rock(frame):
    """A tumbling rock, ROCK px: dark crust broken by glowing cracks round a white-hot core, turned a quarter of a
    crack's pattern each frame."""
    s = Sprite(ROCK, ROCK)
    c = ROCK / 2
    crust = [(c + 4.3 * cos(a) * (0.86 + 0.14 * sin(3 * a + 1)), c + 4.3 * sin(a) * (0.9 + 0.1 * cos(2 * a)))
             for a in (2 * pi * k / 9 for k in range(9))]
    s.part(s.shape("poly", *crust), (70, 44, 46), light=(c + 2, c - 2, 2.5, (120, 70, 60)), rim=0.4, grain=0.2)
    turn = frame * pi / 2 / ROCK_FRAMES * 2
    for k in range(3):  # three cracks from the core out to the crust
        a = turn + 2 * pi * k / 3
        mid = (c + 2.0 * cos(a + 0.4), c + 2.0 * sin(a + 0.4))
        s.part(s.shape("line", (c, c), mid, (c + 3.6 * cos(a), c + 3.6 * sin(a)), width=0.9), (255, 140, 40),
               rim=0, grain=0)
    s.part(s.shape("ellipse", c - 1.7, c - 1.7, c + 1.7, c + 1.7), (255, 214, 120), rim=0, grain=0)
    s.part(s.shape("ellipse", c - 0.9, c - 1.0, c + 0.8, c + 0.7), (255, 252, 236), rim=0, grain=0)
    return s.cut(outline=False)


def coal(frame):
    """The coal lying on the ground, dimming over its frames: its cracks from orange-white to a dull red."""
    k = 1 - frame / COAL_FRAMES
    s = Sprite(*COAL)
    w, h = COAL
    s.part(s.shape("poly", (0.4, h), (1.2, 2.4), (3.6, 0.6), (7.0, 0.8), (9.4, 3.0), (9.8, h)), (54, 36, 40),
           rim=0.4, grain=0.2)
    hot = tuple(int(a + (b - a) * k) for a, b in zip((150, 36, 24), (255, 170, 60)))
    s.part(s.shape("line", (2.2, h - 1.2), (4.4, 3.0), (6.4, 4.2), (8.4, 2.2), width=1.0), hot, rim=0, grain=0)
    s.part(s.shape("line", (4.4, 3.0), (5.0, 1.4), width=0.9), hot, rim=0, grain=0)
    if frame < 2:
        core = tuple(int(a + (b - a) * k) for a, b in zip((230, 120, 50), (255, 246, 200)))
        s.part(s.shape("ellipse", 5.4, 3.2, 7.4, 5.2), core, rim=0, grain=0)
    return s.cut(outline=False)


def shadow():
    """The landing shadow, the mark's full width: a dark ellipse with a lighter rim, the warning on the ground."""
    s = Sprite(*SHADOW)
    w, h = SHADOW
    s.part(s.shape("ellipse", 0, 0, w, h), (10, 8, 18), rim=0, grain=0)
    return s.cut(outline=False)


def ring():
    """A thin white ring round the shadow, for its last moments."""
    w, h = RING
    s = Sprite(w, h)
    outer, inner = s.shape("ellipse", 0, 0, w, h), s.shape("ellipse", 1.3, 1.1, w - 1.3, h - 1.1)
    s.part(ImageChops.subtract(outer, inner), (250, 246, 255), rim=0, grain=0)
    return s.cut(outline=False, threshold=100)


def flash():
    """The ground band in white, thinning out upward: drawn see-through for the two frames of an impact."""
    w, h = FLASH
    img = Image.new("RGBA", FLASH, (255, 250, 240, 255))
    return dithered(img, lambda x, y: (y + 1) / h)


def paint_meteors():
    """Every meteors picture: the still sky, the fire's pictures, then the walker."""
    pictures = {"meteors_sky": (meteors_sky(), False)}
    for i in range(ROCK_FRAMES):
        pictures["meteors_rock%d" % i] = (rock(i), True)
    pictures["meteors_halo"] = (radial((HALO, HALO), ((0, 255, 236, 170), (0.4, 255, 160, 70), (1, 250, 110, 40)),
                                       halo_cover), True)
    for i in range(COAL_FRAMES):
        pictures["meteors_coal%d" % i] = (coal(i), True)
    pictures["meteors_glow"] = (radial(GLOW, ((0, 255, 240, 200), (0.35, 255, 170, 80), (1, 250, 110, 40)),
                                       halo_cover), True)
    pictures["meteors_shadow"] = (shadow(), True)
    pictures["meteors_ring"] = (ring(), True)
    pictures["meteors_flash"] = (flash(), True)
    pictures.update({name: (img, True) for name, img in WalkerPoses().pictures().items()})
    return Painting(pictures)


ART_SET = ArtSet("meteors", 773, paint_meteors)
