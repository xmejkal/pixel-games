"""A detailed fireman at 96 px (P904's spike): the run of art/mocap.py painted with a face, gloves, a turnout coat
and an air tank, to see whether the detail shows at that size. It is in no game and in no art set: art/paint.py
does not call it, and the packs stay as they are.

One number, the height in px from the soles to the helmet's top, sets the size. Every width and offset is a share
of the body height, so the same painter gives 48 px or 96 px.

Run from the repository root: python3 art/detailed.py --out DIR writes figure-sheet.png (the twelve run poses,
today's 26 px fireman beside them, and two poses at 3x), run.gif (both firemen run over Rescue's street at the
captured speed) and run-close.gif (the run in place at 2x and half speed), and prints the run's box and bytes.
It needs the CMU files in mocap.CMU_DIR and paints nothing without them.
"""

import argparse
import os
import sys

from PIL import Image, ImageChops

import mocap
from brush import Sprite, rnd
from export import Sheet, committed_index, from_bin, pack_bytes, q565
from sets.rescue import FEET, HELMET, HELMET_L, HELMET_TOP, Figure, along, dist

TALL = 96  # px from the soles to the helmet's top, standing
SEED = 904  # the grain's seed: two runs write the same files
COAT, TROUSERS = (198, 158, 84), (168, 132, 72)  # a tan turnout coat: shade shows on it after RGB565, on black not
BOOT, SOLE = (30, 28, 36), (92, 88, 100)
SKIN, EYE, MOUTH = (236, 184, 146), (36, 28, 30), (150, 84, 74)
GLOVE = (104, 60, 40)
SEAM = (74, 62, 52)  # round the near arm where it lies on the coat
TANK, STRAP, BUCKLE = (108, 124, 152), (44, 42, 52), (214, 190, 120)
SHIELD = (206, 48, 40)  # the helmet's front shield
FRAME_MS = 40  # one frame of the game
RUN_PX_S = 2.316  # body heights a second: the capture's stride, 1.698 body heights, in its 0.733 s loop
STRIDE = 1.698  # body heights he runs in one run cycle (art/mocap.py prints it)


def box(height):
    """The picture a pose is painted in, w and h: wide enough for a stride, high enough for the run's flight."""
    return (round(height * 1.4), round(height * 1.2))


def darker(colour, k=0.7):
    return tuple(int(c * k) for c in colour)


def lighter(colour):
    return tuple(min(255, int(c * 1.22 + 16)) for c in colour)


def unit(a, b):
    d = dist(a, b)
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d)


def union(*masks):
    out = masks[0]
    for m in masks[1:]:
        out = ImageChops.lighter(out, m)
    return out


class DetailedFireman(Figure):
    """One pose of the fireman with detail, facing the way the pose does: a tan coat with a collar and a hem,
    trousers, boots with soles, reflective bands, gloves from the wrist to the fingers, a face on the side the nose
    is, a helmet with a brim, a shield and a neck flap, an air tank on his back with a strap, and a belt. The
    numbers below are shares of the body height. Figure gives the joints' places, the bands as whole pixels and the
    1 px rim."""

    SOLE = 0.038  # from the toe joint down to the boot's underside
    THIGH, SHIN, UPPER, FORE = (0.115, 0.095), (0.095, 0.075), (0.095, 0.08), (0.08, 0.07)  # each limb's two widths
    TORSO, NECK, HEAD = 0.17, 0.05, 0.068  # the torso's and the neck's width, the head's radius
    SHAFT_W, FOOT_W, SOLE_W = 0.086, 0.06, 0.018
    GLOVE_W, CUFF = 0.066, 0.022
    BAND, SEAM_W = 0.024, 0.014
    TANK_W, TANK_OUT, STRAP_W, BELT_W = 0.085, 0.105, 0.022, 0.034

    def __init__(self, size, height=TALL):
        super().__init__(size)
        self.PX = height / (1 + HELMET_TOP + self.SOLE)

    def at(self, joint):
        x, y, _ = joint
        return (self.w / 2 + self.HIPS + x * self.PX, self.h - (self.SOLE + y) * self.PX)

    def paint(self, pose):
        s = Sprite(self.w, self.h)
        self.bands = Image.new("L", s.size, 0)
        p = {n: self.at(v) for n, v in pose.items()}
        near = "r" if pose["rhipjoint"][2] >= pose["lhipjoint"][2] else "l"
        far = "l" if near == "r" else "r"
        ahead = max(-1.0, min(1.0, (p["nose"][0] - p["head"][0]) / (0.1 * self.PX)))  # 1 right, -1 left, 0 at us
        toward = pose["nose"][2] >= pose["head"][2]  # the face is on our side of the head, or level with it
        self.arm(s, p, far, True)
        self.leg(s, p, far, True)
        self.tank(s, p, ahead)
        self.leg(s, p, near, False)
        self.coat(s, p)
        self.belt(s, p, ahead)
        self.head(s, p, ahead, toward)
        self.arm(s, p, near, False)
        return self.rim(self.banded(s.cut(outline=False)), ahead >= 0)

    # --- the brush -----------------------------------------------------------------------------------------------

    def part(self, s, mask, colour, band=None):
        """A shaded part over what is painted: a light on its upper half, a darker wet rim, a faint grain. It hides
        the bands under it. band: the mask of its own band."""
        found = mask.getbbox()
        if found is None:
            return
        x0, y0, x1, y1 = (v / s.S for v in found)
        light = ((x0 + x1) / 2, y0 + (y1 - y0) * 0.35, max(x1 - x0, y1 - y0) * 0.4, lighter(colour))
        s.part(mask, colour, light=light, rim=0.45, grain=0.05)
        self.bands = ImageChops.subtract(self.bands, mask)
        if band is not None:
            self.bands = ImageChops.lighter(self.bands, ImageChops.multiply(mask, band))

    def detail(self, s, mask, colour):
        """A small flat part: an eye, a mouth, a buckle."""
        s.part(mask, colour, rim=0, grain=0)
        self.bands = ImageChops.subtract(self.bands, mask)

    def taper(self, s, a, b, widths):
        """A limb from a to b with round ends, widths[0] of a body height wide at a and widths[1] at b."""
        wa, wb = (w * self.PX / 2 for w in widths)
        ux, uy = unit(a, b)
        quad = s.shape("poly", (a[0] - uy * wa, a[1] + ux * wa), (a[0] + uy * wa, a[1] - ux * wa),
                       (b[0] + uy * wb, b[1] - ux * wb), (b[0] - uy * wb, b[1] + ux * wb))
        return union(quad, s.shape("ellipse", a[0] - wa, a[1] - wa, a[0] + wa, a[1] + wa),
                     s.shape("ellipse", b[0] - wb, b[1] - wb, b[0] + wb, b[1] + wb))

    def band(self, s, a, b, t):
        """A reflective band across the limb from a to b, at t of the way: the mask of a line square to it, longer
        than any limb is wide."""
        cx, cy = along(a, b, t)
        ux, uy = unit(a, b)
        half = self.TORSO * self.PX
        return s.shape("line", (cx - uy * half, cy + ux * half), (cx + uy * half, cy - ux * half),
                       width=self.BAND * self.PX)

    # --- the body ------------------------------------------------------------------------------------------------

    def leg(self, s, p, side, far):
        hip, knee, ankle = p[side + "hipjoint"], p[side + "femur"], p[side + "tibia"]
        ball, toe = p[side + "foot"], p[side + "toes"]
        cloth, boot = (darker(TROUSERS), darker(BOOT, 1.5)) if far else (TROUSERS, BOOT)
        self.part(s, self.taper(s, hip, knee, self.THIGH), cloth)
        self.part(s, self.taper(s, knee, ankle, self.SHIN), cloth, None if far else self.band(s, knee, ankle, 0.42))
        self.part(s, self.taper(s, along(knee, ankle, 0.62), ankle, (self.SHAFT_W, self.SHAFT_W)), boot)
        self.part(s, s.shape("line", ankle, ball, toe, width=self.FOOT_W * self.PX), boot)
        ux, uy = unit(ankle, toe)  # the sole: under the foot, on the side away from the knee
        down = 1 if (ankle[0] - knee[0]) * -uy + (ankle[1] - knee[1]) * ux >= 0 else -1
        off = (self.FOOT_W / 2 + self.SOLE_W / 4) * self.PX * down
        heel = (ankle[0] - ux * self.FOOT_W * self.PX / 2, ankle[1] - uy * self.FOOT_W * self.PX / 2)
        self.detail(s, s.shape("line", (heel[0] - uy * off, heel[1] + ux * off), (toe[0] - uy * off, toe[1] + ux * off),
                               width=self.SOLE_W * self.PX), SOLE)

    def arm(self, s, p, side, far):
        shoulder, elbow, wrist = p[side + "clavicle"], p[side + "humerus"], p[side + "radius"]
        cloth, glove = (darker(COAT), darker(GLOVE)) if far else (COAT, GLOVE)
        upper, fore = self.taper(s, shoulder, elbow, self.UPPER), self.taper(s, elbow, wrist, self.FORE)
        if not far:  # the near arm over the body: a seam round it, where it lies on what is painted
            seam = self.SEAM_W * 2
            wide = union(self.taper(s, shoulder, elbow, tuple(w + seam for w in self.UPPER)),
                         self.taper(s, elbow, wrist, tuple(w + seam for w in self.FORE)))
            self.detail(s, ImageChops.multiply(wide, s.alpha), SEAM)
        self.part(s, upper, cloth)
        self.part(s, fore, cloth, None if far else self.band(s, elbow, wrist, 0.78))
        self.glove(s, p, side, glove)

    def glove(self, s, p, side, colour):
        """From the wrist joint (radius) through the palm (wrist, hand) to the fingers, with a cuff."""
        wrist, palm, hand, fingers = p[side + "radius"], p[side + "wrist"], p[side + "hand"], p[side + "fingers"]
        ux, uy = unit(palm, fingers)
        tip = (fingers[0] + ux * self.GLOVE_W * self.PX * 0.3, fingers[1] + uy * self.GLOVE_W * self.PX * 0.3)
        self.part(s, s.shape("line", wrist, palm, hand, tip, width=self.GLOVE_W * self.PX), colour)
        cx, cy = unit(wrist, palm)
        half = self.GLOVE_W * self.PX * 0.62
        self.detail(s, s.shape("line", (wrist[0] - cy * half, wrist[1] + cx * half),
                               (wrist[0] + cy * half, wrist[1] - cx * half), width=self.CUFF * self.PX),
                    darker(colour, 0.6))

    def coat(self, s, p):
        """The coat: the torso from the hips to the neck, and a hem that hangs over the tops of both thighs."""
        hips = along(p["lhipjoint"], p["rhipjoint"], 0.5)
        spine = (hips, p["lowerback"], p["upperback"], p["thorax"], p["lowerneck"])
        torso = s.shape("line", *spine, width=self.TORSO * self.PX)
        half, margin = self.TORSO * self.PX / 2, self.THIGH[0] * self.PX * 0.62
        hems = sorted(along(p[k + "hipjoint"], p[k + "femur"], 0.4) for k in "lr")
        back, front = (hems[0][0] - margin, hems[0][1]), (hems[1][0] + margin, hems[1][1])
        waist = p["lowerback"]
        hem = s.shape("poly", (waist[0] - half, waist[1]), (waist[0] + half, waist[1]), front, back)
        lift = self.BAND * self.PX
        bands = union(self.band(s, p["upperback"], p["thorax"], 0.5),
                      s.shape("line", (back[0], back[1] - lift), (front[0], front[1] - lift), width=lift))
        self.part(s, union(torso, hem), COAT, bands)
        self.detail(s, s.shape("line", p["lowerneck"], along(p["lowerneck"], p["upperneck"], 0.3),
                               width=self.NECK * self.PX * 1.7), darker(COAT, 0.62))  # the collar

    def tank(self, s, p, ahead):
        """The air tank on his back, under the coat's edge: a cylinder beside the spine, a valve under it."""
        out = -ahead * self.TANK_OUT * self.PX
        top, low = p["thorax"], along(p["lowerback"], p["upperback"], 0.1)
        a, b = (top[0] + out, top[1]), (low[0] + out, low[1])
        self.detail(s, s.shape("line", b, along(a, b, 1.22), width=self.TANK_W * self.PX * 0.45), STRAP)
        self.part(s, s.shape("line", a, b, width=self.TANK_W * self.PX), TANK)

    def belt(self, s, p, ahead):
        """The tank's strap over the shoulder and down the chest, the belt, its buckle and a pouch."""
        hips = along(p["lhipjoint"], p["rhipjoint"], 0.5)
        coat = s.shape("line", hips, p["lowerback"], p["upperback"], p["thorax"], p["lowerneck"],
                       width=self.TORSO * self.PX)
        front = ahead * self.TORSO * self.PX
        shoulder, chest = p["lowerneck"], p["upperback"]
        strap = s.shape("line", (shoulder[0] - front * 0.5, shoulder[1] + self.STRAP_W * self.PX),
                        (chest[0] + front * 0.12, chest[1]), (p["lowerback"][0] + front * 0.2, p["lowerback"][1]),
                        width=self.STRAP_W * self.PX)
        waist = along(hips, p["lowerback"], 0.75)
        ux, uy = unit(hips, p["lowerback"])
        half = self.TORSO * self.PX
        belt = s.shape("line", (waist[0] - uy * half, waist[1] + ux * half), (waist[0] + uy * half, waist[1] - ux * half),
                       width=self.BELT_W * self.PX)
        self.detail(s, ImageChops.multiply(union(strap, belt), coat), STRAP)
        r = self.BELT_W * self.PX * 0.42
        bx, by = waist[0] + front * 0.34, waist[1]
        self.detail(s, s.shape("rect", bx - r, by - r, bx + r, by + r, r * 0.3), BUCKLE)
        px, py, pw = waist[0] - front * 0.1, waist[1] + self.BELT_W * self.PX * 0.5, self.BELT_W * self.PX * 0.75
        self.detail(s, s.shape("rect", px - pw, py, px + pw, py + pw * 2.2, pw * 0.3), darker(STRAP, 1.5))

    # --- the head ------------------------------------------------------------------------------------------------

    def head(self, s, p, ahead, toward):
        """The neck, the neck flap, the head with its face, and the helmet. The head's own up is the line from the
        upper neck to the head joint, so the face tilts as the head does; ahead moves the face across the head as he
        turns toward the viewer."""
        centre, r = p["head"], self.HEAD * self.PX
        ux, uy = unit(p["upperneck"], centre)  # the head's up, on the screen
        side = 1 - abs(ahead)

        def at(a, b):
            """A place on the head: a head radii toward the screen's right of its up, b up."""
            return (centre[0] - uy * a * r + ux * b * r, centre[1] + ux * a * r + uy * b * r)

        self.part(s, s.shape("line", p["lowerneck"], centre, width=self.NECK * self.PX), darker(SKIN, 0.85))
        cx, cy = centre
        self.part(s, s.shape("ellipse", cx - r, cy - r * 1.12, cx + r, cy + r * 1.12), SKIN)
        back = -1 if ahead >= 0 else 1
        if side < 0.7:  # the neck flap, over the back of the head and down to the collar
            self.detail(s, s.shape("poly", at(back * 0.25, 0.1), at(back * 1.7 * abs(ahead), -0.1),
                                   at(back * 1.3 * abs(ahead), -1.5), at(back * 0.1, -1.4)), darker(COAT, 0.62))
        if toward or side < 0.5:
            self.face(s, at, r, ahead, side)
        self.helmet(s, at, r, ahead, side)

    def face(self, s, at, r, ahead, side):
        """An eye (two as he turns to us), a nose past the head's edge and a mouth."""
        e = r * 0.17
        for k in ((-1, 1) if side > 0.15 else (0,)):
            ex, ey = at(ahead * 0.5 + k * side * 0.42, -0.02)
            self.detail(s, s.shape("ellipse", ex - e, ey - e * 1.25, ex + e, ey + e * 1.25), EYE)
        self.detail(s, s.shape("poly", at(ahead * 0.86, 0.02), at(ahead * 1.24 + (0.18 if ahead >= 0 else -0.18) * side,
                                                                    -0.34), at(ahead * 0.8, -0.44)), darker(SKIN, 0.9))
        wide = 0.2 + 0.2 * side
        self.detail(s, s.shape("line", at(ahead * 0.62 - wide, -0.62), at(ahead * 0.62 + wide, -0.62), width=r * 0.14),
                    MOUTH)

    def helmet(self, s, at, r, ahead, side):
        """The dome down to the brow, a short brim ahead and a long one behind, and the shield at the front."""
        top = HELMET_TOP / self.HEAD  # the dome's top, in head radii above the head joint
        dome = s.shape("poly", *[at(1.22 * c, 0.12 + (top - 0.12) * v) for c, v in
                                 ((-1.0, 0.0), (-0.92, 0.45), (-0.7, 0.78), (-0.38, 0.95), (0.0, 1.0), (0.38, 0.95),
                                  (0.7, 0.78), (0.92, 0.45), (1.0, 0.0))])
        way = 1 if ahead >= 0 else -1
        peak, tail = abs(ahead) * 1.75 + side * 1.4, abs(ahead) * 2.15 + side * 1.4
        brim = s.shape("line", at(way * peak, 0.08), at(0.0, 0.2), at(-way * tail, -0.12 * abs(ahead) + 0.08 * side),
                       width=r * 0.34)
        lx, ly = at(ahead * 0.5, top * 0.7)
        s.part(union(dome, brim), HELMET, light=(lx, ly, r * 0.9, HELMET_L), rim=0.4, grain=0)
        self.bands = ImageChops.subtract(self.bands, union(dome, brim))
        sx, sy = at(ahead * 0.78, 0.62)
        self.detail(s, s.shape("ellipse", sx - r * 0.3, sy - r * 0.36, sx + r * 0.3, sy + r * 0.36), SHIELD)


class RunPictures:
    """The run's twelve poses from the capture, each painted on its own picture and all cut to the one box they
    use: pictures (RGBA, in the board's RGB565 colours), size, hips (the hips' x in the box), stride (px a cycle)."""

    def __init__(self, capture, height, seed=SEED):
        rnd.seed(seed)
        self.figure = DetailedFireman(box(height), height)
        self.cycle = next(c for c in mocap.CYCLES if c.name == "run")
        painted = [self.figure.paint(pose) for pose in capture.poses(self.cycle)]
        used = [img.getchannel("A").getbbox() for img in painted]
        x0, y0, x1 = min(b[0] for b in used), min(b[1] for b in used), max(b[2] for b in used)
        self.pictures = [q565(img.crop((x0, y0, x1, img.height))) for img in painted]
        self.size = self.pictures[0].size
        self.hips = self.figure.w // 2 - x0
        self.stride = round(STRIDE * self.figure.PX)

    def bytes(self):
        """The run in a pack: RGB565, both facings."""
        w, h = self.size
        return w * h * 2 * len(self.pictures) * 2

    def pose(self, ran):
        """The picture after ran px of running, as games/rescue.py picks it."""
        return self.pictures[ran * len(self.pictures) // self.stride % len(self.pictures)]


class Committed:
    """Today's Rescue from the committed pack: the street and the 26 px fireman's run."""

    RUN_POSES, STRIDE_PX, SPEED_PX_S = 12, 41, 56  # games/rescue.py's numbers

    def __init__(self):
        self.art = committed_index()["ART"]
        self.street = self.picture("rescue_night").convert("RGB")
        self.run = [self.picture("rescue_run_r%d" % i) for i in range(self.RUN_POSES)]

    def picture(self, name):
        return from_bin(pack_bytes(name), *self.art[name][:2])

    def pose(self, ran):
        return self.run[ran * self.RUN_POSES // self.STRIDE_PX % self.RUN_POSES]


class FigureSheet:
    """figure-sheet.png: the twelve poses in a row with today's fireman at their end, then one run pose and the
    pose turned toward the viewer at 3x, on the street's dark, so they read as on the board."""

    ZOOM, GAP, DARK = 3, 6, (30, 16, 40)  # DARK: the street's sky at its middle (art/sets/rescue.py's NIGHT)

    def __init__(self, run, turned, old):
        self.run, self.turned, self.old = run, turned, old

    def on_dark(self, pictures, zoom=1):
        w = sum(img.width for img in pictures) + self.GAP * (len(pictures) + 1)
        h = max(img.height for img in pictures) + 2 * self.GAP
        row, x = Image.new("RGB", (w, h), self.DARK), self.GAP
        for img in pictures:
            row.paste(img, (x, h - self.GAP - img.height), img)
            x += img.width + self.GAP
        return row.resize((w * zoom, h * zoom), Image.NEAREST)

    def image(self):
        w, h = self.run.size
        rows = [("the run's twelve poses at %d px, each %d by %d px, and today's 26 px fireman" % (TALL, w, h),
                 self.on_dark(self.run.pictures + [self.old.run[0]])),
                ("pose 3 of the run, and the same pose turned toward the viewer, at %dx" % self.ZOOM,
                 self.on_dark([self.run.pictures[3], self.turned], self.ZOOM))]
        sheet = Sheet(max(img.width for _, img in rows) + 20, sum(img.height + 28 for _, img in rows) + 10)
        y = 6
        for label, img in rows:
            y = sheet.put(label, img, 10, y) + 10
        return sheet.image


class RunClip:
    """The GIFs' frames. frames(): both firemen run left to right over Rescue's street, each at its captured speed,
    a frame of the game apart. close(): the big run in place over the street at 2x, a pose a frame."""

    W = 320

    def __init__(self, run, old):
        self.run, self.old = run, old

    def frames(self):
        speed = RUN_PX_S * self.run.figure.PX
        w, h = self.run.size
        count = int((self.W + w) / speed * 1000 / FRAME_MS) + 1
        out = []
        for i in range(count):
            frame = self.old.street.copy()
            small = self.old.SPEED_PX_S * i * FRAME_MS // 1000
            pose = self.old.pose(small)
            frame.paste(pose, (150 + small - pose.width // 2, FEET - pose.height + 1), pose)
            ran = int(speed * i * FRAME_MS / 1000)
            frame.paste(self.run.pose(ran), (ran - w, FEET - h + 1), self.run.pose(ran))
            out.append(frame)
        return out

    def close(self, zoom=2):
        w, h = self.run.size
        left, top = (self.W - w) // 2 - 10, FEET - h - 9
        out = []
        for img in self.run.pictures:
            frame = self.old.street.crop((left, top, left + w + 20, FEET + 11))
            frame.paste(img, (10, 10), img)
            out.append(frame.resize((frame.width * zoom, frame.height * zoom), Image.NEAREST))
        return out


def write_gif(frames, path, ms):
    """A looping GIF on one palette taken from the first frame, so the colours do not flicker."""
    palette = frames[0].quantize(255)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=ms, loop=0)


def turned_pose(capture, cycle, index):
    """The cycle's pose index, turned toward the viewer as the wave is (mocap.VIEW)."""
    view = mocap.Cycle(cycle.name, cycle.trial, cycle.fps, cycle.frames, cycle.period, cycle.poses, view=mocap.VIEW)
    return capture.poses(view)[index]


def main():
    parser = argparse.ArgumentParser(description="Paint the detailed fireman's run at %d px: a sheet and two GIFs." % TALL)
    parser.add_argument("--out", required=True, metavar="DIR", help="the folder the three pictures are written to")
    parser.add_argument("--cmu", default=mocap.CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    args = parser.parse_args()
    capture = mocap.Capture(args.cmu)
    if capture.missing():
        parser.error("not in %s: %s" % (args.cmu, ", ".join(capture.missing())))
    run, old = RunPictures(capture, TALL), Committed()
    turned = q565(DetailedFireman(box(TALL), TALL).paint(turned_pose(capture, run.cycle, 3)))
    os.makedirs(args.out, exist_ok=True)
    FigureSheet(run, turned.crop(turned.getchannel("A").getbbox()), old).image().save(
        os.path.join(args.out, "figure-sheet.png"))
    clip = RunClip(run, old)
    write_gif(clip.frames(), os.path.join(args.out, "run.gif"), FRAME_MS)
    write_gif(clip.close(), os.path.join(args.out, "run-close.gif"), 2 * round(mocap_loop_ms(capture, run.cycle) / 12))
    w, h = run.size
    print("the run at %d px: 12 poses of %d by %d px, %d bytes with both facings" % (TALL, w, h, run.bytes()))


def mocap_loop_ms(capture, cycle):
    """The cycle's loop in ms."""
    return capture.loop(cycle)[1] * 1000 / cycle.fps


if __name__ == "__main__":
    sys.exit(main())
