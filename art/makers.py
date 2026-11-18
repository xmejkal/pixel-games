"""The three makers at 96 px (P904 step 2b, P909's first test): the fireman's run made three ways side by side, for
the eye to judge which way the board should make a figure. A maker is a way to get a pose's picture; on the Mac each
is a Figure class with paint(pose), and a run of any maker is a RunPictures of art/detailed.py with that maker:

- whole: DetailedFigure, the shaded painter of art/detailed.py, whose pictures the board keeps whole.
- flat: FlatFigure, the same shapes in flat fills, one colour a pixel, as a C painter on the board can draw them.
- cutout: CutoutFigure, painted parts turned and put together at the pose's joints. Its Atlas holds the parts.

It is in no game and in no art set: art/paint.py does not call it.

Run from the repository root: python3 art/makers.py --out DIR writes makers-sheet.png (the run's twelve poses by each
maker, pose 3 by each at 3x, and the cutout's parts) and makers.webp (the run in place over Rescue's street at 2x,
the three makers side by side), and prints what each maker's run costs the board in bytes and the cutout's worst
miss. It needs the CMU files of the run in mocap.CMU_DIR and paints nothing without them.
"""

import argparse
import copy
import math
import os
import sys
from collections import namedtuple

from PIL import Image, ImageChops

import mocap
from brush import Sprite
from detailed import (CLOSE_MS, FIREMAN, TALL, CharacterClip, Committed, DetailedFigure, NoRim, RunPictures,
                      on_dark, write_clip)
from export import Sheet, q565
from sets.rescue import FEET, STRIPE, Figure, along

HIPS = "hips"  # the middle of the two hip joints: the joint of the torso and of the back gear
ARM, LEG = ("upper arm", "forearm", "hand"), ("thigh", "shin", "foot")
LIMBS = ARM + LEG  # the six limb kinds, each on both sides
# each kind's joint, which is its pivot, and its end; a limb's without its side's letter
BONES = {"upper arm": ("clavicle", "humerus"), "forearm": ("humerus", "radius"), "hand": ("radius", "fingers"),
         "thigh": ("hipjoint", "femur"), "shin": ("femur", "tibia"), "foot": ("tibia", "toes"),
         "back gear": (HIPS, "lowerneck"), "torso": (HIPS, "lowerneck"), "head": ("lowerneck", "head")}
# a pose's parts in paste order, (kind, far) each, as DetailedFigure.paint paints them: the far arm and leg, the gear
# on the back, the near leg, the torso with the gear over it, the head with its headwear, the near arm
PARTS = (tuple((kind, True) for kind in LIMBS) + (("back gear", False),) + tuple((kind, False) for kind in LEG) +
         (("torso", False), ("head", False)) + tuple((kind, False) for kind in ARM))
# each kind's upright angle on the screen, in degrees clockwise from forward (y is down): the limbs hang down, the
# foot points forward, the torso, the back gear and the head point up
UPRIGHT = {"upper arm": 90, "forearm": 90, "hand": 90, "thigh": 90, "shin": 90, "foot": 0, "back gear": 270,
           "torso": 270, "head": 270}
# the joints each kind puts on its upright way, each at its 3D distance from the kind's joint; a kind comes after the
# one that puts its joint (Atlas.measure puts the hip joints and the clavicles)
WAYS = (("torso", ("lowerback", "upperback", "thorax", "lowerneck")), ("head", ("upperneck", "head")),
        ("upper arm", ("humerus",)), ("forearm", ("radius",)), ("hand", ("wrist", "hand", "fingers", "thumb")),
        ("thigh", ("femur",)), ("shin", ("tibia",)), ("foot", ("foot", "toes")))
PartPicture = namedtuple("PartPicture", "image pivot end")  # a part's picture, its joint's and its end's places in it
Placed = namedtuple("Placed", "key place joint end")  # a placed part: its atlas key, its paste place, its joint and end


def sides(pose):
    """The side letter of the near limbs (False) and of the far ones (True), as DetailedFigure.paint picks them: the
    near hip is the one nearer the viewer."""
    near = "r" if pose["rhipjoint"][2] >= pose["lhipjoint"][2] else "l"
    return {False: near, True: "l" if near == "r" else "r"}


class FlatFigure(DetailedFigure):
    """The whole painter's shapes in the same order, each in its plain colour: no light, no rim and no grain (as
    sets.rescue.Figure.part paints a part). The cut gives each pixel the colour and the cover of the 8x sprite's pixel
    nearest its middle, so inside the shape a pixel is one of the given colours or a band's. Its edge, the Outline by
    default, is a pass over the picture that C can do: its pixels are blends of their neighbours."""

    part = Figure.part  # one colour: no light, no rim, no grain

    def detail(self, s, mask, colour, light=None, rim=0):
        """A detail in its plain colour: the light and the rim are left out."""
        super().detail(s, mask, colour)

    def cut(self, s):
        """Each pixel's colour and cover from the 8x sprite's pixel nearest its middle (Image.NEAREST), and the bands
        cut the same way."""
        size, nearest = (s.w, s.h), Image.Resampling.NEAREST
        out = s.rgb.resize(size, nearest).convert("RGBA")
        out.putalpha(s.alpha.resize(size, nearest))
        out.paste(STRIPE + (255,), (0, 0) + size, ImageChops.multiply(self.bands.resize(size, nearest),
                                                                       out.getchannel("A")))
        return out


class Atlas:
    """The part pictures of one character: a PartPicture for each key (kind, far, step), painted at the first request
    for it. A kind is one of BONES; far, the far shade; step, the part's angle on the screen rounded to the nearest of
    ANGLES steps.

    It holds a whole painter with no rim. The first pose it measures gives the bone lengths (3D, after
    Proportions.fit) and one upright pose with every joint: the spine and the head straight up, the arms and the legs
    straight down, the ball and the toes level and forward of the ankle (WAYS), and the hip joints and the clavicles
    where they are against the spine in that pose. A gear that reads the knees finds them there. The painter's own arm,
    leg, torso with the gear over it, gear under (the back gear) or head (facing right, in profile) paints each part's
    group alone on a sprite with the part's joint at its middle; a limb part and its bands are masked to a capsule round
    its bone, so two parts both keep a round end at their joint. For a key, Sprite.turn turns the sprite about the
    joint, the same rotation turns the bands, and the painter's cut cuts it."""

    ANGLES = 32  # a kind has a picture every 11.25 degrees
    REACH = 0.45  # body heights from a part's joint to the sprite's edge: the fireman's torso reaches 0.40
    # each limb kind's capsule's half width in body heights: past the half width of what the whole painter paints on
    # its bone (DetailedFigure's UPPER, FORE, GLOVE_W, THIGH, SHIN and SHAFT_W, FOOT_W and the sole), so a part keeps
    # its whole width
    CAPSULE = {"upper arm": 0.055, "forearm": 0.05, "hand": 0.05, "thigh": 0.068, "shin": 0.058, "foot": 0.05}

    def __init__(self, painter):
        self.painter, self.pictures, self.uprights = painter, {}, None
        self.reach = math.ceil(self.REACH * painter.PX)  # px from the sprite's middle to its edge

    def measure(self, pose):
        """From the first pose (fitted): the upright pose, each part's upright sprite and its bands, and each part's
        bone in it (px from its joint to its end). A later pose changes nothing."""
        if self.uprights is not None:
            return
        self.sides = sides(pose)
        pose = dict(pose, hips=tuple((a + b) / 2 for a, b in zip(pose["lhipjoint"], pose["rhipjoint"])))
        up = {HIPS: (0.0, 0.0, 0.0)}
        for kind, joints in WAYS[:2]:  # the spine and the head straight up
            self.place(up, pose, kind, "", joints)
        for side in "lr":
            for joint, spine in (("hipjoint", HIPS), ("clavicle", "lowerneck")):  # where they are against the spine
                up[side + joint] = tuple(u + a - b for u, a, b in zip(up[spine], pose[side + joint], pose[spine]))
            for kind, joints in WAYS[2:]:
                self.place(up, pose, kind, side, joints)
        self.uprights, self.bones = {}, {}
        places = {n: self.painter.at(v) for n, v in up.items()}
        for kind, far in PARTS:
            side = self.sides[far] if kind in LIMBS else ""
            (jx, jy), (ex, ey) = (places[side + n] for n in BONES[kind])
            self.bones[kind, far] = (ex - jx, ey - jy)
            self.uprights[kind, far] = self.upright(kind, far, side, {n: (x - jx + self.reach, y - jy + self.reach)
                                                                       for n, (x, y) in places.items()})

    @staticmethod
    def place(up, pose, kind, side, joints):
        """Puts the kind's joints on its upright way from its joint, each at its 3D distance from it in the pose."""
        start = side + BONES[kind][0]
        a = math.radians(UPRIGHT[kind])
        forward, rise = math.cos(a), -math.sin(a)
        for n in joints:
            d = math.dist(pose[start], pose[side + n])
            up[side + n] = (up[start][0] + forward * d, up[start][1] + rise * d, 0.0)

    def upright(self, kind, far, side, p):
        """The kind's group painted alone on the upright places p (px, its joint at the sprite's middle), a limb's
        masked to its capsule: the sprite and its bands."""
        painter = self.painter
        s = Sprite(2 * self.reach, 2 * self.reach)
        painter.bands = Image.new("L", s.size, 0)
        if kind in ARM:
            painter.arm(s, p, side, far)
        elif kind in LEG:
            painter.leg(s, p, side, far)
        elif kind == "head":
            painter.head(s, p, 1, True)
        else:
            if kind == "torso":
                painter.torso(s, p)
            for gear in painter.character.gear:
                (gear.under if kind == "back gear" else gear.over)(painter, s, p, 1)
        if kind in LIMBS:
            joint, end = (p[side + n] for n in BONES[kind])
            capsule = s.shape("line", joint, end, width=2 * self.CAPSULE[kind] * painter.PX)
            s.alpha = ImageChops.multiply(s.alpha, capsule)
            painter.bands = ImageChops.multiply(painter.bands, capsule)
        return s, painter.bands

    def step(self, degrees):
        """The nearest of the ANGLES steps to an angle in degrees, 0 to ANGLES - 1."""
        return round(degrees * self.ANGLES / 360) % self.ANGLES

    def key(self, kind, far, degrees):
        """The key of a part at an angle on the screen, in degrees clockwise from forward."""
        return (kind, far, self.step(degrees))

    def turn(self, kind, step):
        """The degrees counter-clockwise (as Sprite.turn turns) that take the kind's upright picture to the step's
        angle: a screen angle grows clockwise, because y is down."""
        return UPRIGHT[kind] - step * 360 / self.ANGLES

    def picture(self, key):
        """The key's PartPicture: the kind's upright sprite and its bands turned about the joint, cut by the painter,
        cropped to what it covers and in the board's RGB565 colours. The pivot is the joint's place in it, the end its
        bone's end turned with it."""
        if key not in self.pictures:
            kind, far, step = key
            sprite, bands = self.uprights[kind, far]
            degrees, r = self.turn(kind, step), self.reach
            s = copy.copy(sprite)
            s.turn(degrees, (r, r))
            self.painter.bands = bands.rotate(degrees, Image.Resampling.BICUBIC, center=(r * s.S, r * s.S),
                                              fillcolor=0)
            img = self.painter.cut(s)
            x0, y0, x1, y1 = img.getchannel("A").getbbox() or (r, r, r, r)
            (bx, by), c, k = self.bones[kind, far], math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
            pivot = (r - x0, r - y0)
            self.pictures[key] = PartPicture(q565(img.crop((x0, y0, x1, y1))), pivot,
                                             (pivot[0] + bx * c + by * k, pivot[1] - bx * k + by * c))
        return self.pictures[key]

    def bytes(self):
        """The pictures in RGB565, two bytes a pixel."""
        return sum(p.image.width * p.image.height * 2 for p in self.pictures.values())

    def fill(self):
        """Paints every step of the six limb kinds in both shades. The torso, the head and the back gear keep the steps
        that the poses used."""
        for kind in LIMBS:
            for far in (True, False):
                for step in range(self.ANGLES):
                    self.picture((kind, far, step))


class CutoutFigure(DetailedFigure):
    """One pose put together from painted parts turned at its joints, known as cutout animation: "figures that have
    joints made with a rivet or pin or, when simulated on a computer, an anchor" (Wikipedia, Cutout animation,
    https://en.wikipedia.org/wiki/Cutout_animation). The parts are its ATLAS's, painted by a whole painter of the same
    size and character; each joint is at its captured place (not chained), and a far limb's parts have the far shade.
    The atlas measures the first pose it paints."""

    ATLAS = Atlas

    def __init__(self, size, height=TALL, rim=None, character=FIREMAN):
        super().__init__(size, height, rim, character)
        self.atlas = self.ATLAS(DetailedFigure(size, height, NoRim(), character))

    def placed(self, pose):
        """Each part of the pose in paste order (PARTS), Placed: its key, its paste place (the pose's joint less the
        part's pivot, rounded once), and its joint and end on the screen."""
        pose = self.character.proportions.fit(pose)
        self.atlas.measure(pose)
        side = sides(pose)
        p = {n: self.at(v) for n, v in pose.items()}
        p[HIPS] = along(p["lhipjoint"], p["rhipjoint"], 0.5)
        out = []
        for kind, far in PARTS:
            joint, end = (p[(side[far] if kind in LIMBS else "") + n] for n in BONES[kind])
            key = self.atlas.key(kind, far, math.degrees(math.atan2(end[1] - joint[1], end[0] - joint[0])))
            pivot = self.atlas.picture(key).pivot
            out.append(Placed(key, (round(joint[0] - pivot[0]), round(joint[1] - pivot[1])), joint, end))
        return out

    def paint(self, pose):
        """The parts pasted at their places in paste order, then the edge."""
        img = Image.new("RGBA", (self.w, self.h))
        for part in self.placed(pose):
            picture = self.atlas.picture(part.key).image
            img.paste(picture, part.place, picture)
        return self.edge.apply(self, img, pose["nose"][0] >= pose["head"][0])

    def misses(self, pose):
        """Each part's miss, in px: from where its end lands to the pose's joint there."""
        out = []
        for part in self.placed(pose):
            end = self.atlas.picture(part.key).end
            out.append(math.dist((part.place[0] + end[0], part.place[1] + end[1]), part.end))
        return out


MAKERS = {"whole": DetailedFigure, "flat": FlatFigure, "cutout": CutoutFigure}  # by name, in the sheet's order


class MakerSheet:
    """makers-sheet.png: the run's twelve poses by each maker, a row each; pose POSE by each maker at ZOOM; then the
    cutout's parts at PARTS_ZOOM, a pose's at their upright angles in paste order, and the near thigh at the steps of
    THIGH; on the street's dark."""

    ZOOM, PARTS_ZOOM, POSE = 3, 2, 3
    THIGH = range(0, Atlas.ANGLES, Atlas.ANGLES // 8)  # the thigh row's steps: eight, 45 degrees apart

    def __init__(self, runs):
        self.runs = runs

    def rows(self):
        """Each row's label and picture."""
        runs, atlas = self.runs, self.runs["cutout"].painter.atlas
        rows = [("%s: the run's twelve poses at %d px, each %d by %d px" % ((name, run.height) + run.size),
                 on_dark(run.pictures)) for name, run in runs.items()]
        rows.append(("pose %d by each maker at %dx: %s" % (self.POSE, self.ZOOM, ", ".join(runs)),
                     on_dark([run.pictures[self.POSE] for run in runs.values()], self.ZOOM)))
        parts = [atlas.picture(atlas.key(kind, far, UPRIGHT[kind])).image for kind, far in PARTS]
        rows.append(("the cutout's %d parts of a pose at their upright angles, in paste order, at %dx" % (
            len(parts), self.PARTS_ZOOM), on_dark(parts, self.PARTS_ZOOM)))
        rows.append(("the near thigh at %d angles, %g degrees apart, at %dx" % (
            len(self.THIGH), 360 / atlas.ANGLES * self.THIGH.step, self.PARTS_ZOOM),
            on_dark([atlas.picture(("thigh", False, step)).image for step in self.THIGH], self.PARTS_ZOOM)))
        return rows

    def image(self):
        rows = self.rows()
        sheet = Sheet(max(img.width for _, img in rows) + 20, sum(img.height + 28 for _, img in rows) + 10)
        y = 6
        for label, img in rows:
            y = sheet.put(label, img, 10, y) + 10
        return sheet.image


class MakerClip:
    """makers.webp's frames: the run in place over Rescue's street at ZOOM, a pose a frame, a panel per maker side by
    side. The panels are of one size, and each picture's pivot is at one place in its panel, MARGIN px over its
    bottom, on the street's FEET row."""

    ZOOM, MARGIN = 2, 10

    def __init__(self, runs, street):
        self.runs, self.street = list(runs.values()), street
        self.left = max(run.pivot[0] for run in self.runs)  # the most px left of a pivot
        right = max(run.size[0] - run.pivot[0] for run in self.runs)
        self.panel = (self.left + right + 2 * self.MARGIN, max(run.size[1] for run in self.runs) + 2 * self.MARGIN)

    def frames(self):
        (pw, ph), m = self.panel, self.MARGIN
        x = (CharacterClip.W - pw) // 2
        back = self.street.crop((x, FEET + m + 1 - ph, x + pw, FEET + m + 1))
        out = []
        for i in range(len(self.runs[0].pictures)):
            frame = Image.new("RGB", (len(self.runs) * pw, ph))
            for k, run in enumerate(self.runs):
                panel, img = back.copy(), run.pictures[i]
                panel.paste(img, (m + self.left - run.pivot[0], ph - m - run.size[1]), img)
                frame.paste(panel, (k * pw, 0))
            out.append(frame.resize((frame.width * self.ZOOM, frame.height * self.ZOOM), Image.Resampling.NEAREST))
        return out


def maker_costs(runs):
    """The lines main prints for the run made by each maker (runs: a maker's name to its RunPictures): what each
    costs the board in bytes, then the cutout's worst miss over the run's poses. It fills the cutout's atlas."""
    whole, flat, cutout = runs["whole"], runs["flat"], runs["cutout"]
    atlas, poses = cutout.painter.atlas, flat.poses()
    used = (len(atlas.pictures), atlas.bytes())
    atlas.fill()
    placed = [cutout.painter.placed(pose) for pose in cutout.poses()]
    count, joints, parts = len(whole.pictures), len(poses[0]), len(placed[0])
    again = "; a second move costs the same again"
    return ["whole: %d pictures of %d by %d px (%d poses, both facings), %d bytes%s" % (
                2 * count, whole.size[0], whole.size[1], count, whole.size_bytes(), again),
            "flat: %d poses of %d joints at two 16-bit numbers a joint, %d bytes%s" % (
                len(poses), joints, len(poses) * joints * 4, again),
            "cutout: the run uses %d part pictures, %d bytes, for one facing (the board mirrors a part for the other); "
            "after fill(), %d pictures, %d bytes; %d poses of %d parts at three 16-bit numbers a part (its place and "
            "its picture), %d bytes; a second move costs its poses and the pictures of the angles that it adds" % (
                used + (len(atlas.pictures), atlas.bytes(), len(placed), parts, len(placed) * parts * 6)),
            "cutout: the worst miss from where a part's end lands to the pose's joint there, %.2f px" % max(
                max(cutout.painter.misses(pose)) for pose in cutout.poses())]


def main():
    parser = argparse.ArgumentParser(description="Make the fireman's run at %d px three ways, whole, flat and cutout: "
                                                 "a sheet and a clip." % TALL)
    parser.add_argument("--out", required=True, metavar="DIR", help="the folder the two pictures are written to")
    parser.add_argument("--cmu", default=mocap.CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    args = parser.parse_args()
    capture = mocap.open_capture(parser, args.cmu, (mocap.named("run"),))
    runs = {name: RunPictures(capture, TALL, maker=maker) for name, maker in MAKERS.items()}
    lines = maker_costs(runs)
    os.makedirs(args.out, exist_ok=True)
    MakerSheet(runs).image().save(os.path.join(args.out, "makers-sheet.png"))
    write_clip(MakerClip(runs, Committed().street).frames(), os.path.join(args.out, "makers.webp"), CLOSE_MS)
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
