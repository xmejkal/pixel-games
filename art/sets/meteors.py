"""Meteors' art (P773): a violet to rose dusk over a cool dark plain, the walker's run posed by motion capture through
art/mocap.py (the fireman's painter of art/sets/rescue.py, as a civilian with a cyan scarf), and the meteors' fire: the
rock and its glow, the coal that dims, the impact's light on the ground, the landing shadow and the ground's flash. The
only warm bright things are the meteors, the coals and the impacts.

The walker is painted only when the CMU files are in mocap.CMU_DIR. Without them his pictures are read back from
games/packs as committed, so art/paint.py still paints every other set and writes the same files.
"""

from math import cos, hypot, pi, sin

from PIL import Image, ImageChops, ImageOps

import mocap
from artset import ArtSet, Painting
from brush import H, W, Sprite, Strip, autocontrast, blur, glaze, lay, ridge, rnd, scale
from sets.rescue import Figure, along, read_committed

DUSK = ((18, 14, 44), (52, 30, 90), (128, 58, 124), (222, 112, 128), (250, 172, 140))  # top to horizon, in bands
BANDS = (0.0, 0.3, 0.62, 0.86, 1.0)  # where each of DUSK's colours sits, from the top (0) to the horizon (1)
HORIZON = 178
GROUND = 206  # the plain's near edge: the ground band the walker runs on starts here
GROUND_TOP = 196  # games/meteors.py's: the band of the sky the shake draws again, its own picture
PLAIN = (82, 74, 112)  # the cool ground, lit a little by the dusk, so the dark walker and the shadows read on it


def dusk_at(y):
    t = max(0.0, min(1.0, y / HORIZON))
    for (t0, a), (t1, b) in zip(zip(BANDS, DUSK), zip(BANDS[1:], DUSK[1:])):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return tuple(int(p + (q - p) * k) for p, q in zip(a, b))
    return DUSK[-1]


# --- the still picture, painted in layers -------------------------------------------------------------------------

def paint_heavens(s):
    """Stars in the high indigo (a few with a glint), a thin moon with its halo, soft blooms, and the smoke of earlier
    meteors drawn across the sky."""
    stars, bright = s.mask(), s.mask()
    for _ in range(60):
        x, y = rnd.uniform(0, W), rnd.uniform(18, 100)
        s.ellipse(stars, x, y, 0.32, 0.32)
    for x, y in ((40, 30), (150, 24), (212, 52), (296, 34), (104, 70)):
        s.ellipse(bright, x, y, 0.5, 0.5)
        s.polygon(bright, [(x - 2, y), (x, y - 0.2), (x + 2, y), (x, y + 0.2)])
        s.polygon(bright, [(x, y - 2), (x + 0.2, y), (x, y + 2), (x - 0.2, y)])
    lay(s.rgb, blur(stars, 1), (236, 226, 250), 0.8)
    lay(s.rgb, blur(bright, 0.8), (255, 246, 236))
    halo, moon, bite = s.mask(), s.mask(), s.mask()
    s.ellipse(halo, 64, 44, 20, 20)
    lay(s.rgb, blur(halo, 40), (200, 170, 230), 0.25)
    s.ellipse(moon, 64, 44, 7, 7)
    s.ellipse(bite, 67, 41, 7, 7)
    lay(s.rgb, blur(ImageChops.subtract(moon, bite), 1.5), (252, 236, 236), 0.95)
    blooms = autocontrast(blur(s.noise(160), 24))
    glaze(s.rgb, scale(blooms, 1.4, -150), (130, 100, 170), 0.3)
    for x0, y0, x1, y1, w in ((340, 20, 150, 150, 3.0), (250, 26, 40, 140, 2.2), (120, 18, -20, 104, 1.6)):
        trail = s.mask()  # a smoke trail, wider and paler toward the ground
        s.polygon(trail, [(x0, y0), (x0 + 1, y0 + 1), (x1 + w * 4, y1), (x1 - w * 4, y1)])
        glaze(s.rgb, blur(trail, 10), (120, 90, 130), 0.45)
    haze = s.mask()
    s.polygon(haze, [(0, HORIZON - 30), (W, HORIZON - 40), (W, HORIZON + 4), (0, HORIZON + 4)])
    lay(s.rgb, blur(haze, 40), (255, 190, 150), 0.35)  # the glow low over the horizon


def paint_clouds(s):
    """Thin bands of cloud across the dusk: dark violet bodies with their bellies lit rose and gold from below, where
    the sun has set."""
    for cx, cy, cw, ch in ((60, 96, 70, 5.0), (250, 84, 90, 5.6), (180, 124, 120, 4.4), (20, 142, 60, 3.8),
                           (300, 150, 70, 3.4), (120, 158, 90, 2.8)):
        body = s.mask()
        n = 9
        for k in range(n):  # puffs that thin out toward both ends, a little ragged
            t = (k + 0.5) / n - 0.5
            r = ch * (1 - 3 * t * t) * rnd.uniform(0.6, 1.2)
            s.ellipse(body, cx + t * cw + rnd.uniform(-3, 3), cy + rnd.uniform(-1, 1) - r * 0.3,
                      cw / n * rnd.uniform(0.9, 1.7), max(1.0, r * 1.5))
        for _ in range(3):  # wisps trailing off the ends
            x = cx + rnd.choice((-1, 1)) * cw * rnd.uniform(0.45, 0.65)
            s.ellipse(body, x, cy + rnd.uniform(-1, 1.5), cw * rnd.uniform(0.08, 0.16), 0.6)
        warm = 1 - (cy - 80) / 100  # higher clouds darker, lower ones warmer
        m = s.wash(body, (int(70 + 60 * (1 - warm)), 44, int(96 + 10 * warm)), alpha=0.85, rim=0.3, rim_px=3,
                   grain=0.3, cell=10, rough=(1.5, 0.5, 6), dark=0.85, soft=1.2)
        belly = ImageChops.subtract(m, ImageChops.offset(m, 0, -int(1.4 * s.S)))  # the underside, lit from below
        lay(s.rgb, blur(belly, 2), (255, 160, 130), 0.8)
        lit = ImageChops.subtract(m, ImageChops.offset(m, 0, -int(0.6 * s.S)))
        lay(s.rgb, ImageChops.multiply(lit, autocontrast(blur(s.noise(30), 6))), (255, 226, 170), 0.9)


def paint_ridges(s):
    """Three ridges, paler and bluer with distance and a band of mist at each foot, and a near rise of the plain with
    a few bare trees."""
    for base, heights, rough, colour, mist in (
            (HORIZON + 2, [26, 34, 18, 40, 30, 22, 36, 28], 10, (150, 96, 140), (236, 150, 140)),
            (HORIZON + 12, [16, 22, 12, 26, 14, 20], 8, (102, 70, 118), (200, 120, 140)),
            (HORIZON + 24, [10, 6, 14, 8, 12], 5, (66, 52, 92), (150, 96, 130))):
        pts = ridge(W, base, heights, rough)
        m = s.mask()
        s.polygon(m, pts + [(W, H + 2), (0, H + 2)])
        m = s.wash(m, colour, alpha=0.97, rim=0.5, rim_px=4, grain=0.25, cell=14, rough=(1, 0.3, 6), dark=0.85,
                   soft=0.8)
        foot = s.mask()
        s.polygon(foot, [(0, base - 6), (W, base - 6), (W, base + 6), (0, base + 6)])
        lay(s.rgb, ImageChops.multiply(blur(foot, 14), m), mist, 0.3)
    lines = []
    for x, h in ((26, 20), (276, 26), (300, 14)):  # bare trees on the rise, in pencil
        y = HORIZON + 26
        lines.append(([(x, y), (x + 1, y - h)], 3))
        for k in range(3):
            ty = y - h * (0.5 + 0.18 * k)
            side = 1 if k % 2 else -1
            lines.append(([(x + 0.6, ty), (x + side * h * 0.3, ty - h * 0.2)], 2))
    s.pencil(lines, strength=0.8, colour=(34, 26, 50))


def paint_plain(s):
    """The plain the walker runs on: cool slate lit by the dusk at its far edge, stones with lit tops, grass tufts."""
    near = s.mask()
    s.polygon(near, [(0, GROUND), (W, GROUND - 3), (W, H + 2), (0, H + 2)])
    s.wash(near, PLAIN, alpha=1.0, rim=0.3, rim_px=3, grain=0.35, cell=8, rough=(0.8, 0.3, 4), dark=0.8, soft=0.5)
    sheen = s.mask()
    s.polygon(sheen, [(0, GROUND), (W, GROUND - 3), (W, GROUND + 6), (0, GROUND + 8)])
    lay(s.rgb, blur(sheen, 8), (176, 128, 150), 0.35)
    stones, tops = s.mask(), s.mask()
    for _ in range(26):
        x, y, r = rnd.uniform(0, W), rnd.uniform(GROUND + 4, H - 2), rnd.uniform(1.0, 3.2)
        s.ellipse(stones, x, y, r * 1.4, r * 0.7)
        s.ellipse(tops, x + r * 0.3, y - r * 0.4, r * 0.8, r * 0.25)
    lay(s.rgb, stones, (48, 42, 70), 0.9)
    lay(s.rgb, ImageChops.multiply(tops, stones), (176, 150, 186), 0.8)
    tufts = []
    for _ in range(60):
        x, y = rnd.uniform(0, W), rnd.uniform(GROUND + 1, H)
        for dx in (-1.2, 0, 1.1):
            tufts.append(([(x, y), (x + dx * 1.4, y - rnd.uniform(1.5, 3.4))], 2))
    s.pencil(tufts, strength=0.5, colour=(40, 36, 60))


def meteors_sky():
    """The still picture, 320 x 240: the heavens, the clouds, the ridges and the plain, at 4x, then shrunk."""
    s = Strip(W, 0, H, False, dusk_at)
    for painter in (paint_heavens, paint_clouds, paint_ridges, paint_plain):
        painter(s)
    s.paper(0.06)
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
    there, else read back from the committed games/packs (and said so)."""

    def __init__(self, folder=mocap.CMU_DIR):
        self.folder, self.capture = folder, mocap.Capture(folder)

    @staticmethod
    def names():
        return ["meteors_%s_%s%d" % (kind, side, i) for kind in ("run", "hit") for side in "rl"
                for i in range(RUN.poses)]

    def pictures(self):
        missing = self.capture.missing()
        if missing:
            print("meteors: no %s in %s: the walker is read back from games/packs, not painted again" % (
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
GLOW = (84, 24)  # px: the impact's light on the ground, its middle a few px above the last row
SHADOW = (8, 3)  # px: the landing shadow, the mark's full width
RING = (12, 5)  # px: the white ring round the shadow in its last moments
FLASH = (W, 14)  # px: the ground band that flashes white at an impact
SMOKE = (30, 34)  # px: the dark puff where the walker is hit, its base on the last row
SMOKE_FRAMES = 5
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
    """The ground band in a warm white, its top rows every other pixel: drawn see-through for the two frames of an
    impact."""
    img = Image.new("RGBA", FLASH, (255, 240, 214, 255))
    return dithered(img, lambda x, y: 0.5 if y < 4 else 1)


def smoke(frame):
    """A dark puff of smoke that hides the walker where a meteor hits him, rising and growing over its frames, its
    puffs lit violet on top. The game draws it see-through, thinner each frame."""
    w, h = SMOKE
    k = frame / (SMOKE_FRAMES - 1)
    s = Sprite(w, h)
    state = rnd.getstate()
    rnd.seed(7)  # the same puffs in every frame, so they grow and do not jump
    puffs = [(rnd.uniform(-1, 1), rnd.uniform(0, 1), rnd.uniform(0.6, 1.0)) for _ in range(12)]
    rnd.setstate(state)
    for dx, up, size in puffs:
        r = (5.5 + 3 * k) * size
        cx, cy = w / 2 + dx * (5 + 4 * k), h - 5 - up * 20 - 5 * k
        s.part(s.shape("ellipse", cx - r, cy - r, cx + r, cy + r * 0.9), (40, 34, 52),
               light=(cx + r * 0.3, cy - r * 0.5, r * 0.7, (96, 80, 118)), rim=0.3, grain=0.2)
    return s.cut(outline=False)


def paint_meteors():
    """Every meteors picture: the still sky, the fire's pictures, then the walker."""
    sky = meteors_sky()
    pictures = {"meteors_sky": (sky, False), "meteors_ground": (sky.crop((0, GROUND_TOP, W, H)), False)}
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
    for i in range(SMOKE_FRAMES):
        pictures["meteors_smoke%d" % i] = (smoke(i), True)
    pictures.update({name: (img, True) for name, img in WalkerPoses().pictures().items()})
    return Painting(pictures)


ART_SET = ArtSet("meteors", 773, paint_meteors)
