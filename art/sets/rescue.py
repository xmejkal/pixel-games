"""Rescue's art (P800): a street at night under a red sky, the fire station at the left with its lit door, a crater,
and the fireman's cycles (run, spray, turn) posed by motion capture through art/mocap.py, facing right and left.

The fireman is painted only when the CMU files are in mocap.CMU_DIR. Without them his pictures are read back from
games/art as committed, so art/paint.py still paints every other set and writes the same files.
"""

import os
from math import cos, pi, sin

from PIL import Image, ImageChops, ImageDraw, ImageOps

import mocap
from artset import ArtSet, Painting
from brush import H, W, Sprite, Strip, autocontrast, blur, glaze, jitter, lay, rnd, scale
from export import from_bin
from letters import text_width, write

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LANE = 180  # the street lane: the bottom 60 px, from this row down
FEET = 214  # the row the fireman's soles stand on (games/rescue.py's FEET)
DOOR = (16, 132, 58, LANE)  # the station's door: x0, y0, x1, y1
NIGHT = ((8, 8, 22), (30, 16, 40), (120, 34, 30))  # the sky from the top, to the middle, to the glow at the horizon
HORIZON = 150


def night_at(y):
    t = max(0.0, min(1.0, y / HORIZON))
    a, b, t = (NIGHT[0], NIGHT[1], t / 0.6) if t < 0.6 else (NIGHT[1], NIGHT[2], (t - 0.6) / 0.4)
    return tuple(int(p + (q - p) * t) for p, q in zip(a, b))


# --- the street, painted in layers once and laid into one still picture ------------------------------------------

def paint_sky(s):
    """The night sky: a few stars, the red glow of the fires low over the town, and smoke drifting across it."""
    stars = s.mask()
    for _ in range(40):
        x, y = rnd.uniform(0, W), rnd.uniform(4, 70)
        s.ellipse(stars, x, y, 0.35, 0.35)
    lay(s.rgb, blur(stars, 1), (220, 214, 240), 0.8)
    glow = s.mask()
    for cx in (110, 230, 300):
        s.ellipse(glow, cx, HORIZON, 90, 46)
    lay(s.rgb, blur(glow, 60), (200, 66, 34), 0.55)
    smoke = autocontrast(blur(s.noise(90), 14))
    band = s.mask()
    s.polygon(band, [(0, 40), (W, 20), (W, 130), (0, 140)])
    glaze(s.rgb, ImageChops.multiply(scale(smoke, 1.6, -120), blur(band, 50)), (60, 44, 52), 0.7)


def paint_skyline(s):
    """The far town: flat dark blocks against the glow, a few dim windows."""
    far, lit, x = s.mask(), s.mask(), 0.0
    while x < W:
        w, h = rnd.uniform(10, 26), rnd.uniform(18, 52)
        s.polygon(far, [(x, 160), (x, 150 - h), (x + w, 150 - h), (x + w, 160)])
        for wy in range(int(154 - h), 148, 5):
            for wx in (x + 2, x + w - 4):
                if rnd.random() < 0.18:
                    s.polygon(lit, [(wx, wy), (wx + 1.2, wy), (wx + 1.2, wy + 1.6), (wx, wy + 1.6)])
        x += w + rnd.uniform(1, 5)
    s.wash(far, (40, 26, 44), alpha=0.95, rim=0.4, rim_px=3, grain=0.2, cell=12, rough=(1, 0.3, 6), dark=0.8, soft=0.6)
    lay(s.rgb, lit, (200, 120, 70), 0.8)


def paint_houses(s):
    """The street's houses right of the station: gables and flat fronts, warm lit windows, dark ones, a chimney."""
    body, roofs, lit, dark = s.mask(), s.mask(), s.mask(), s.mask()
    x = 86.0
    while x < W + 10:
        w, h = rnd.uniform(34, 52), rnd.uniform(36, 58)
        top = LANE - h
        s.polygon(body, [(x, LANE), (x, top), (x + w, top), (x + w, LANE)])
        if rnd.random() < 0.6:
            s.polygon(roofs, [(x - 2, top + 1), (x + w / 2, top - w * 0.38), (x + w + 2, top + 1)])
            s.polygon(roofs, [(x + w * 0.7, top - w * 0.2), (x + w * 0.7, top - w * 0.34), (x + w * 0.78, top - w * 0.34),
                              (x + w * 0.78, top - w * 0.12)])
        for wy in range(int(top + 6), LANE - 12, 12):
            for wx in range(int(x + 5), int(x + w - 7), 10):
                m = lit if rnd.random() < 0.45 else dark
                s.polygon(m, [(wx, wy), (wx + 5, wy), (wx + 5, wy + 6), (wx, wy + 6)])
        x += w + rnd.uniform(2, 6)
    s.wash(body, (52, 38, 50), alpha=1.0, rim=0.5, rim_px=4, grain=0.3, cell=10, rough=(1, 0.3, 6), dark=0.75, soft=0.6)
    s.wash(roofs, (34, 26, 38), alpha=1.0, rim=0.4, rim_px=3, grain=0.2, cell=8, rough=None, dark=0.8, soft=0.5)
    lay(s.rgb, dark, (22, 18, 28), 0.9)
    lay(s.rgb, blur(lit, 6), (230, 150, 70), 0.35)  # the windows' light spills a little
    lay(s.rgb, lit, (246, 196, 110))


def paint_station(s):
    """The fire station at the left: dark brick, a red beacon, FIRE over the big door, and the door lit warm: the
    brightest still thing on the street."""
    x0, y0, x1, y1 = DOOR
    wall = s.mask()
    s.polygon(wall, [(0, LANE), (0, 96), (40, 84), (80, 96), (80, LANE)])
    s.wash(wall, (84, 40, 36), alpha=1.0, rim=0.5, rim_px=4, grain=0.35, cell=8, rough=None, dark=0.7, soft=0.5)
    bricks = []
    for y in range(100, LANE, 4):
        bricks.append(([(0, y), (80, y)], 1))
        for x in range(2 + (y // 4) % 2 * 4, 80, 8):
            bricks.append(([(x, y), (x, y + 4)], 1))
    s.pencil(bricks, strength=0.35, colour=(40, 16, 16))
    sign = s.mask()
    s.polygon(sign, [(x0 - 2, 108), (x1 + 2, 108), (x1 + 2, 122), (x0 - 2, 122)])
    lay(s.rgb, sign, (26, 20, 26))
    letters = s.mask()
    unit = 1.5
    write(letters, "FIRE", ((x0 + x1) / 2 - text_width("FIRE", unit) / 2) * s.S, 111 * s.S, unit * s.S, 1.2 * s.S)
    lay(s.rgb, letters, (250, 226, 180))
    glow = s.mask()
    s.polygon(glow, [(x0 - 10, y0 - 10), (x1 + 10, y0 - 10), (x1 + 34, H), (x0 - 20, H)])
    lay(s.rgb, blur(glow, 22), (255, 170, 80), 0.4)  # the door's light, out over the street
    door = s.mask()
    s.polygon(door, [(x0, y1), (x0, y0), (x1, y0), (x1, y1)])
    lay(s.rgb, door, (255, 226, 160))
    inside = s.mask()
    s.polygon(inside, [(x0 + 3, y1), (x0 + 3, y0 + 6), (x1 - 3, y0 + 6), (x1 - 3, y1)])
    glaze(s.rgb, blur(inside, 6), (255, 190, 110), 0.5)
    s.pencil([([(x0, y0 + k), (x1, y0 + k)], 1) for k in (3, 4)], strength=0.4, colour=(150, 90, 40))  # the shutter
    beacon = s.mask()
    s.ellipse(beacon, 40, 92, 2.4, 2.4)
    lay(s.rgb, blur(beacon, 10), (255, 40, 30), 0.6)
    lay(s.rgb, beacon, (255, 110, 90))


def paint_lane(s):
    """The street lane, dark and lit: the kerb, the tarmac, lane marks, and pools of lamp light."""
    tar = s.mask()
    s.polygon(tar, [(0, LANE), (W, LANE), (W, H + 2), (0, H + 2)])
    s.wash(tar, (38, 34, 42), alpha=1.0, rim=0.0, grain=0.4, cell=6, rough=None, soft=0)
    kerb = s.mask()
    s.polygon(kerb, [(0, LANE), (W, LANE), (W, LANE + 3), (0, LANE + 3)])
    lay(s.rgb, kerb, (84, 76, 86))
    marks = s.mask()
    for x in range(100, W, 30):
        s.polygon(marks, [(x, 228), (x + 14, 228), (x + 14, 229.4), (x, 229.4)])
    lay(s.rgb, marks, (150, 140, 130), 0.6)
    for lx in (150, 270):  # two lamps: a post at the kerb and a pool on the tarmac
        pool = s.mask()
        s.ellipse(pool, lx, 204, 34, 14)
        lay(s.rgb, blur(pool, 30), (170, 130, 90), 0.3)
        s.pencil([([(lx, LANE + 1), (lx, 128), (lx + 6, 124)], 2)], strength=0.9, colour=(20, 16, 22))
        lamp = s.mask()
        s.ellipse(lamp, lx + 7, 125, 2.2, 1.4)
        lay(s.rgb, blur(lamp, 10), (255, 200, 120), 0.5)
        lay(s.rgb, lamp, (255, 236, 190))


def paint_night():
    """The still street, 320 x 240: the sky, the far town, the houses, the station, the lane, at 4x, then shrunk."""
    s = Strip(W, 0, H, False, night_at)
    for painter in (paint_sky, paint_skyline, paint_houses, paint_station, paint_lane):
        painter(s)
    s.paper(0.05)
    return s.rgb.resize((W, H), Image.LANCZOS).convert("RGBA")


def paint_crater():
    """The hole a meteor leaves, seen from the side: a dark disc with a glowing red rim and a lip of thrown earth."""
    s = Sprite(28, 8)
    s.part(s.shape("ellipse", 0.5, 1.5, 27.5, 7.8), (110, 40, 26), rim=0.2, grain=0.1)
    s.part(s.shape("ellipse", 2.5, 2.6, 25.5, 6.6), (20, 14, 18), rim=0.1, grain=0.05)
    img = s.cut(outline=False)
    for x in range(4, 24):  # the red rim where the far edge glows
        if img.getpixel((x, 2))[3]:
            img.putpixel((x, 2), (232, 70, 40, 255))
    return img


# --- the fireman -------------------------------------------------------------------------------------------------

FIG_H = 26  # px from the soles to the helmet's top, standing
HELMET_TOP = 0.08  # body heights from the head joint to the helmet's top (the head joint is mid-head in CMU)
PX = FIG_H / (1 + HELMET_TOP)  # px per body height
COAT, COAT_FAR = (30, 28, 38), (58, 54, 70)  # the near side, and the far limbs about 25 % lighter
HELMET, HELMET_L = (246, 196, 36), (255, 236, 130)
STRIPE = (226, 236, 150)  # the reflective band
SEAM = (74, 68, 92)  # round the near arm where it crosses the body
WARM, COOL = (236, 130, 64), (128, 156, 214)  # the rims: the fire side (ahead of him) and the other
HOSE, BRASS = (184, 52, 40), (214, 190, 120)
SIZES = {"run": (26, 30), "turn": (26, 30), "spray": (40, 30)}  # each cycle's picture, w x h; the hips at w / 2


class Figure:
    """One pose of the fireman, facing right, painted at 8x on a brush.Sprite: far limbs, torso, near leg, head and
    helmet, near arm, then cut and given a 1 px rim outside the shape, warm ahead and cool behind. The reflective
    bands are kept as their own mask, so a part painted over one hides it, and come out as whole pixels. With hose,
    the nozzle is in his hands and the hose, under everything, runs from them down to the street behind him."""

    def __init__(self, size):
        self.w, self.h = size

    def at(self, joint):
        x, y, _ = joint
        return (self.w / 2 + x * PX, self.h - 1 - y * PX)

    def paint(self, pose, hose=False):
        s = Sprite(self.w, self.h)
        self.bands = Image.new("L", s.size, 0)
        p = {n: self.at(v) for n, v in pose.items()}
        near = "r" if pose["rhipjoint"][2] >= pose["lhipjoint"][2] else "l"
        far = "l" if near == "r" else "r"
        self.arm(s, p, far, COAT_FAR)
        self.leg(s, p, far, COAT_FAR)
        self.torso(s, p)
        self.leg(s, p, near, COAT)
        self.head(s, p)
        self.arm(s, p, near, COAT)
        if hose:
            self.nozzle(s, p, near)
        img = self.rim(self.banded(s.cut(outline=False)), pose["nose"][0] >= pose["head"][0])
        if hose:
            img = self.under(img, self.hose(p, near))
        return img

    def part(self, s, mask, colour, band=None):
        """A flat part over what is painted; it hides the bands under it. band: the mask of its own band."""
        s.part(mask, colour, rim=0, grain=0)
        self.bands = ImageChops.subtract(self.bands, mask)
        if band is not None:
            self.bands = ImageChops.lighter(self.bands, ImageChops.multiply(mask, band))

    def banded(self, img):
        """The bands as whole pixels: a pixel at least 40 % band is the band's colour."""
        cover = self.bands.resize(img.size, Image.BOX)
        out = img.copy()
        for y in range(img.height):
            for x in range(img.width):
                if cover.getpixel((x, y)) >= 102 and img.getpixel((x, y))[3]:
                    out.putpixel((x, y), STRIPE + (255,))
        return out

    def leg(self, s, p, side, colour):
        hip, knee, ankle = p[side + "hipjoint"], p[side + "femur"], p[side + "tibia"]
        ball, toe = p[side + "foot"], p[side + "toes"]
        self.part(s, s.shape("line", hip, knee, width=2.8), colour)
        band = across(s, knee, ankle, 0.66)
        self.part(s, s.shape("line", knee, ankle, width=2.3), colour, band if colour == COAT else None)
        self.part(s, s.shape("line", ankle, ball, toe, width=2.2), (16, 14, 20))  # the boot

    def arm(self, s, p, side, colour):
        shoulder, elbow, wrist, hand = p[side + "clavicle"], p[side + "humerus"], p[side + "radius"], p[side + "wrist"]
        upper, fore = s.shape("line", shoulder, elbow, width=2.3), s.shape("line", elbow, wrist, hand, width=2.0)
        if colour == COAT:  # the near arm over the body: a seam round it, where it lies on what is painted
            wide = ImageChops.lighter(s.shape("line", shoulder, elbow, width=4.3),
                                      s.shape("line", elbow, wrist, hand, width=4.0))
            self.part(s, ImageChops.multiply(wide, s.alpha), SEAM)
        self.part(s, upper, colour)
        self.part(s, fore, colour)

    def torso(self, s, p):
        hips = along(p["lhipjoint"], p["rhipjoint"], 0.5)
        neck = p["lowerneck"]
        band = across(s, hips, neck, 0.16)
        self.part(s, s.shape("line", hips, p["lowerback"], p["upperback"], p["thorax"], neck, width=4.2), COAT, band)

    def head(self, s, p):
        hx, hy = p["head"]
        ahead = (p["nose"][0] - hx) / (0.1 * PX)  # 1 facing ahead, -1 facing back, 0 facing the viewer
        side = 1 - abs(ahead)
        r = 0.068 * PX
        self.part(s, s.shape("ellipse", hx - r, hy - r * 1.1, hx + r, hy + r * 1.1), (40, 30, 30))
        top = hy - HELMET_TOP * PX
        dome = s.shape("ellipse", hx - r * 1.25, top, hx + r * 1.25, hy + r * 1.1)
        dome = ImageChops.multiply(dome, s.shape("rect", 0, 0, self.w, hy + 0.3, 0))
        back = hx - ahead * r * 2.6 - side * r * 1.6  # the long brim behind, both sides when he faces the viewer
        brim = s.shape("poly", (hx + ahead * r * 1.6, hy - 0.2), (back, hy + 0.9), (back, hy + 0.1),
                       (hx + side * r * 1.6, hy - 0.6))
        s.part(ImageChops.lighter(dome, brim), HELMET, light=(hx + ahead, top + 1, 1.6, HELMET_L), rim=0, grain=0)
        self.bands = ImageChops.subtract(self.bands, ImageChops.lighter(dome, brim))

    def nozzle(self, s, p, side):
        elbow, hand = p[side + "radius"], p[side + "wrist"]
        self.part(s, s.shape("line", along(elbow, hand, 0.8), along(elbow, hand, 1.0 + 5 / dist(elbow, hand)),
                             width=1.8), BRASS)

    def hose(self, p, side):
        """The hose alone, cut: from the near hand down past the back heel and along the street to the edge."""
        s = Sprite(self.w, self.h)
        hx, hy = p[side + "wrist"]
        heel = p[("l" if side == "r" else "r") + "foot"]
        pts = [(hx - 1, hy + 1), (hx - 4, hy + 6), (heel[0] - 3, self.h - 3), (heel[0] - 8, self.h - 1.4),
               (-1, self.h - 1.4)]
        s.part(s.shape("line", *pts, width=1.8), HOSE, rim=0, grain=0)
        return s.cut(outline=False)

    @staticmethod
    def under(img, below):
        out = below.copy()
        out.alpha_composite(img)
        return out

    def rim(self, img, right):
        """A 1 px rim outside the shape, warm on the side his face looks to (right, or else left) and cool on the
        other, so the turn hands the warm rim over from one side to the other. Nothing above or under, so the soles
        stay on the street."""
        ahead, behind = (WARM, COOL) if right else (COOL, WARM)
        out = img.copy()
        a = img.getchannel("A").load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                if a[x, y]:
                    continue
                if x > 0 and a[x - 1, y]:
                    out.putpixel((x, y), ahead + (255,))
                elif x < w - 1 and a[x + 1, y]:
                    out.putpixel((x, y), behind + (255,))
        return out


def along(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def across(s, a, b, t, thick=1.6):
    """A band thick px wide across the limb from a to b, at t of the way: the mask of a line square to it."""
    cx, cy = along(a, b, t)
    d = dist(a, b)
    nx, ny = (a[1] - b[1]) / d * 4, (b[0] - a[0]) / d * 4
    return s.shape("line", (cx - nx, cy - ny), (cx + nx, cy + ny), width=thick)


def dist(a, b):
    return ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 or 1.0


class FiremanPoses:
    """The fireman's pictures by name: painted from the CMU files when they are there, else read back from the
    committed games/art files (and said so)."""

    def __init__(self, folder=mocap.CMU_DIR):
        self.folder, self.capture = folder, mocap.Capture(folder)

    def pictures(self):
        missing = self.capture.missing()
        if missing:
            print("rescue: no %s in %s: the fireman is read back from games/art, not painted again" % (
                ", ".join(missing), self.folder))
            return self.committed()
        out = {}
        for cycle in mocap.CYCLES:
            figure = Figure(SIZES[cycle.name])
            right = [figure.paint(pose, cycle.name == "spray") for pose in self.capture.poses(cycle)]
            out.update({"rescue_%s_r%d" % (cycle.name, i): img for i, img in enumerate(right)})
            out.update({"rescue_%s_l%d" % (cycle.name, i): ImageOps.mirror(img) for i, img in enumerate(right)})
        return out

    @staticmethod
    def names():
        return ["rescue_%s_%s%d" % (c.name, side, i) for c in mocap.CYCLES for side in "rl" for i in range(c.poses)]

    def committed(self):
        index = {}
        with open(os.path.join(REPO, "games", "art_index.py")) as f:
            exec(f.read(), index)
        out = {}
        for name in self.names():
            w, h, path = index["ART"][name]
            with open(os.path.join(REPO, "games", path), "rb") as f:
                out[name] = from_bin(f.read(), w, h)
        return out


def paint_rescue():
    """Every rescue picture: the still street and the crater first (on the seed's stream), then the fireman."""
    pictures = {"rescue_night": (paint_night(), False), "rescue_crater": (paint_crater(), True)}
    pictures.update({name: (img, True) for name, img in FiremanPoses().pictures().items()})
    return Painting(pictures)


ART_SET = ArtSet("rescue", 800, paint_rescue)
