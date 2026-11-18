"""The three makers at 96 px (P904 step 2b, P909's first test): the fireman's run made three ways side by side, for
the eye to judge which way the board should make a figure. A maker is a way to get a pose's picture; on the Mac each
is a Figure class with paint(pose), and a run of any maker is a RunPictures of art/detailed.py with that maker:

- whole: DetailedFigure, the shaded painter of art/detailed.py, whose pictures the board keeps whole.
- flat: FlatFigure, the same shapes in flat fills, one colour a pixel, as a C painter on the board can draw them.
- cutout: CutoutFigure, painted parts turned and put together at the pose's joints. Its Atlas holds the parts.

An angle is in degrees on the screen, clockwise from forward (y is down). A step is the index of a part's picture:
the atlas has a picture every 360 / Atlas.STEPS degrees. It is in no game and in no art set: art/paint.py does not
call it.

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
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageDraw, ImageFont

import mocap
from brush import Sprite
from detailed import (CLOSE_MS, DARK, FIREMAN, GAP, TALL, CharacterClip, Committed, DetailedFigure, NoRim,
                      RunPictures, on_dark, write_clip)
from export import Sheet, q565
from sets.rescue import FEET, STRIPE, Figure, along

HIPS = "hips"  # the middle of the two hip joints: the joint of the torso and of the back gear
NAME_INK, NAME_H = (226, 220, 236), 16  # the names on the sheet's parts row and in the clip: light ink, px a line


def arm(painter, s, p, side, far):
    painter.arm(s, p, side, far)


def leg(painter, s, p, side, far):
    painter.leg(s, p, side, far)


def back_gear(painter, s, p, side, far):
    """The gear on the back (Gear.under), facing right."""
    for gear in painter.character.gear:
        gear.under(painter, s, p, 1)


def torso(painter, s, p, side, far):
    """The torso and the gear over it (Gear.over), facing right."""
    painter.torso(s, p)
    for gear in painter.character.gear:
        gear.over(painter, s, p, 1)


def head(painter, s, p, side, far):
    """The neck and the head facing right, in profile, with its headwear."""
    painter.head(s, p, 1, True)


@dataclass(frozen=True)
class Kind:
    """A kind of part: its name; its chain, its joint (which is its pivot) and the joints after it to its end, a
    limb's without its side's letter; its upright angle; group, the function that paints its group with the
    painter's own method (painter, sprite, places, side, far); and half, a limb's half width, the most that the whole
    painter paints on either side of its bone, in body heights (None: not a limb, not masked to a capsule)."""

    name: str
    chain: tuple
    upright: float
    group: object
    half: float | None = None

    @property
    def limb(self):
        return self.half is not None

    def joints(self, side):
        """Its chain's joint names on a side: a limb's with the side's letter, the others' as they are."""
        return tuple((side if self.limb else "") + n for n in self.chain)


SPINE = (HIPS, "lowerback", "upperback", "thorax", "lowerneck")
D = DetailedFigure  # each limb's half width, from the whole painter's widths: the foot's holds the sole under it
KINDS = {kind.name: kind for kind in (
    Kind("upper arm", ("clavicle", "humerus"), 90, arm, max(D.UPPER) / 2),
    Kind("forearm", ("humerus", "radius"), 90, arm, max(D.FORE) / 2),
    Kind("hand", ("radius", "wrist", "hand", "fingers"), 90, arm, D.GLOVE_W / 2),
    Kind("thigh", ("hipjoint", "femur"), 90, leg, max(D.THIGH) / 2),
    Kind("shin", ("femur", "tibia"), 90, leg, max(D.SHIN + (D.SHAFT_W,)) / 2),
    Kind("foot", ("tibia", "foot", "toes"), 0, leg, D.FOOT_W / 2 + D.SOLE_W * 3 / 4),
    Kind("back gear", SPINE, 270, back_gear), Kind("torso", SPINE, 270, torso),
    Kind("head", ("lowerneck", "upperneck", "head"), 270, head))}
ARM, LEG = ("upper arm", "forearm", "hand"), ("thigh", "shin", "foot")
LIMBS = ARM + LEG  # the six limb kinds, each on both sides
# a pose's parts in paste order, (kind, far) each, as DetailedFigure.paint paints them: the far arm and leg, the gear
# on the back, the near leg, the torso with the gear over it, the head with its headwear, the near arm
PARTS = (tuple((kind, True) for kind in LIMBS) + (("back gear", False),) + tuple((kind, False) for kind in LEG) +
         (("torso", False), ("head", False)) + tuple((kind, False) for kind in ARM))
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


class UprightPose:
    """One upright pose with every joint the painter reads, from a pose's bone lengths alone, so every pose of one
    skeleton gives the same one: the spine and the head straight up from the middle of the hips, both hip joints there
    and both clavicles at the lower neck, the arms and the legs straight down, the ball and the toes level and forward
    of the ankle. Each joint is a bone's length (3D) from the one before it in its kind's chain. A gear that reads the
    knees finds them there. joints: each joint's (forward, up, 0) in body heights, the middle of the hips (HIPS) at 0.
    """

    def __init__(self, pose):
        pose = dict(pose, hips=tuple((a + b) / 2 for a, b in zip(pose["lhipjoint"], pose["rhipjoint"])))
        self.joints = {HIPS: (0.0, 0.0, 0.0)}
        self.lay(pose, KINDS["torso"], "")
        self.lay(pose, KINDS["head"], "")
        for side in "lr":
            self.joints[side + "hipjoint"], self.joints[side + "clavicle"] = self.joints[HIPS], self.joints["lowerneck"]
            for name in LIMBS:
                self.lay(pose, KINDS[name], side)

    def lay(self, pose, kind, side):
        """Puts the joints after the kind's joint on its upright way, each a bone's length from the one before it."""
        joints = kind.joints(side)
        a = math.radians(kind.upright)
        forward, rise = math.cos(a), -math.sin(a)
        for before, n in zip(joints, joints[1:]):
            d = math.dist(pose[before], pose[n])
            self.joints[n] = (self.joints[before][0] + forward * d, self.joints[before][1] + rise * d, 0.0)


class Atlas:
    """The part pictures of one character, by key (kind, far, step): a kind's name, far for the far shade, and the step
    nearest to the part's angle. It is a texture atlas: "an image containing multiple smaller images" (Wikipedia,
    Texture atlas, https://en.wikipedia.org/wiki/Texture_atlas), kept here as one picture a key. It holds a whole
    painter with no rim and the upright pose (UprightPose) of the bone lengths of the first pose it measures (3D, after
    Proportions.fit).

    Each part is painted once, upright, when the first pose is measured: the painter's own group paints it alone on a
    sprite with the part's joint at its middle. A limb part and its bands are masked to a capsule round its bone, so
    two parts both keep a round end at their joint: a capsule, "a cylinder with hemispherical ends" (Wikipedia, Capsule
    (geometry), https://en.wikipedia.org/wiki/Capsule_(geometry)), here its 2D form, a stadium. A key's picture only
    turns and cuts that painting, at the first request for the key: Sprite.turn turns the sprite about the joint, the
    same rotation turns the bands, and the painter's cut cuts it."""

    STEPS = 32  # a kind has a picture every 11.25 degrees
    REACH = 0.45  # body heights from a part's joint to the sprite's edge: the fireman's torso reaches 0.40
    MARGIN = 0.01  # body heights a capsule's half width is past its kind's half width

    def __init__(self, painter):
        self.painter, self.pictures = painter, {}
        self.reach = math.ceil(self.REACH * painter.PX)  # px from the sprite's middle to its edge
        self.upright, self.sides, self.bones, self.uprights = None, None, {}, {}

    def measure(self, pose):
        """From the first pose (fitted): the upright pose, each part's upright sprite and its bands, and each part's
        bone in it (px from its joint to its end). A later pose changes nothing."""
        if self.upright is not None:
            return
        self.sides, self.upright = sides(pose), UprightPose(pose)
        places = {n: self.painter.at(v) for n, v in self.upright.joints.items()}
        for name, far in PARTS:
            kind, side = KINDS[name], self.sides[far]
            joints = kind.joints(side)
            (jx, jy), (ex, ey) = places[joints[0]], places[joints[-1]]
            self.bones[name, far] = (ex - jx, ey - jy)
            self.uprights[name, far] = self.paint(kind, far, side, {n: (x - jx + self.reach, y - jy + self.reach)
                                                                    for n, (x, y) in places.items()})

    def paint(self, kind, far, side, p):
        """The kind's group painted alone on the upright places p (px, its joint at the sprite's middle), a limb's
        masked to its capsule: the sprite and its bands."""
        painter = self.painter
        s = Sprite(2 * self.reach, 2 * self.reach)
        painter.bands = Image.new("L", s.size, 0)
        kind.group(painter, s, p, side, far)
        if kind.limb:
            joints = kind.joints(side)
            half = (kind.half + self.MARGIN) * painter.PX  # the capsule's half width, px
            capsule = s.shape("line", p[joints[0]], p[joints[-1]], width=2 * half)
            s.alpha = ImageChops.multiply(s.alpha, capsule)
            painter.bands = ImageChops.multiply(painter.bands, capsule)
        return s, painter.bands

    def step(self, degrees):
        """The nearest step to an angle, 0 to STEPS - 1. round() takes an angle half way between two steps to the even
        one."""
        return round(degrees * self.STEPS / 360) % self.STEPS

    def key(self, kind, far, degrees):
        """The key of a part at an angle."""
        return (kind, far, self.step(degrees))

    def turn(self, kind, step):
        """The degrees counter-clockwise (as Sprite.turn turns) that take the kind's upright picture to the step's
        angle: a screen angle grows clockwise, because y is down."""
        return KINDS[kind].upright - step * 360 / self.STEPS

    def picture(self, key):
        """The key's PartPicture: the kind's upright sprite and its bands turned about the joint and cut by the
        painter at the first request for it, then cropped to what it covers and in the board's RGB565 colours. The
        pivot is the joint's place in it, the end its bone's end turned with it."""
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

    def size_bytes(self):
        """The pictures for one facing, in RGB565: two bytes a pixel."""
        return sum(p.image.width * p.image.height * 2 for p in self.pictures.values())

    def fill(self):
        """Turns and cuts every step of the six limb kinds in both shades. The torso, the head and the back gear keep
        the steps that the poses used."""
        for kind in LIMBS:
            for far in (True, False):
                for step in range(self.STEPS):
                    self.picture((kind, far, step))


class CutoutFigure(DetailedFigure):
    """One pose put together from painted parts turned at its joints, known as cutout animation: "figures that have
    joints made with a rivet or pin or, when simulated on a computer, an anchor" (Wikipedia, Cutout animation,
    https://en.wikipedia.org/wiki/Cutout_animation). The parts are its ATLAS's, painted by a whole painter of the same
    size and character; each joint is at its captured place (not chained), and a far limb's parts have the far shade.
    The atlas measures the first pose it paints. Its parts are in RGB565, as the board keeps them, so its edge blends
    those colours, as the board's would.

    What it does not keep from the whole painter: no seam round the near arm; the hem and its band (and an apron)
    hang straight and do not follow the thighs; the tank turns with the spine; a bulge at a bent knee or elbow,
    where two round ends meet; the face only in profile; a part's light, rim and grain turn with the part; a part
    that points toward the viewer keeps its whole 3D length; the bends of the spine, the foot and the hand are
    straight. It paints a pose that faces right, and a left picture is its mirror, as in Pictures."""

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
        for name, far in PARTS:
            joints = KINDS[name].joints(side[far])
            joint, end = p[joints[0]], p[joints[-1]]
            key = self.atlas.key(name, far, math.degrees(math.atan2(end[1] - joint[1], end[0] - joint[0])))
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


def named(strip, xs, names):
    """The strip with each name under its picture, x px from the strip's left, on one of three lines in turn so that
    two long names side by side do not meet: light ink on the street's dark, as on_dark's strip."""
    font = ImageFont.load_default(size=14)
    out = Image.new("RGB", (strip.width, strip.height + 3 * NAME_H + 4), DARK)
    out.paste(strip, (0, 0))
    draw = ImageDraw.Draw(out)
    for k, (x, name) in enumerate(zip(xs, names)):
        draw.text((x, strip.height + k % 3 * NAME_H), name, fill=NAME_INK, font=font)
    return out


class MakerSheet:
    """makers-sheet.png: the run's twelve poses by each maker, a row each; pose POSE by each maker at ZOOM; then the
    cutout's parts at PARTS_ZOOM, a pose's at their upright angles in paste order with each kind's name under it, and
    the near thigh at the steps of THIGH; on the street's dark."""

    ZOOM, PARTS_ZOOM, POSE = 3, 2, 3
    THIGH = range(0, Atlas.STEPS, Atlas.STEPS // 8)  # the thigh row's steps: eight, 45 degrees apart

    def __init__(self, runs):
        self.runs = runs

    def rows(self):
        """Each row's label and picture."""
        runs, atlas, zoom = self.runs, self.runs["cutout"].painter.atlas, self.PARTS_ZOOM
        rows = [("%s: the run's twelve poses at %d px, each %d by %d px" % ((name, run.height) + run.size),
                 on_dark(run.pictures)) for name, run in runs.items()]
        rows.append(("pose %d by each maker at %dx: %s" % (self.POSE, self.ZOOM, ", ".join(runs)),
                     on_dark([run.pictures[self.POSE] for run in runs.values()], self.ZOOM)))
        parts = [atlas.picture(atlas.key(kind, far, KINDS[kind].upright)).image for kind, far in PARTS]
        xs = [(GAP * (k + 1) + sum(img.width for img in parts[:k])) * zoom for k in range(len(parts))]
        rows.append(("the cutout's %d parts of a pose at their upright angles, in paste order (far, then near), at %dx"
                     % (len(parts), zoom), named(on_dark(parts, zoom), xs, [kind for kind, _ in PARTS])))
        rows.append(("the near thigh at %d of the %d steps, %g degrees apart, at %dx" % (
            len(self.THIGH), atlas.STEPS, 360 / atlas.STEPS * self.THIGH.step, zoom),
            on_dark([atlas.picture(("thigh", False, step)).image for step in self.THIGH], zoom)))
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
    side with the maker's name at its top left. The panels are of one size, and each picture's pivot is at one place
    in its panel, MARGIN px over its bottom, on the street's FEET row."""

    ZOOM, MARGIN = 2, 10

    def __init__(self, runs, street):
        self.names, self.runs, self.street = list(runs), list(runs.values()), street
        self.left = max(run.pivot[0] for run in self.runs)  # the most px left of a pivot
        right = max(run.size[0] - run.pivot[0] for run in self.runs)
        self.panel = (self.left + right + 2 * self.MARGIN, max(run.size[1] for run in self.runs) + 2 * self.MARGIN)

    def frames(self):
        (pw, ph), m, zoom = self.panel, self.MARGIN, self.ZOOM
        x = (CharacterClip.W - pw) // 2
        back = self.street.crop((x, FEET + m + 1 - ph, x + pw, FEET + m + 1))
        font = ImageFont.load_default(size=14)
        out = []
        for i in range(len(self.runs[0].pictures)):
            frame = Image.new("RGB", (len(self.runs) * pw, ph))
            for k, run in enumerate(self.runs):
                panel, img = back.copy(), run.pictures[i]
                panel.paste(img, (m + self.left - run.pivot[0], ph - m - run.size[1]), img)
                frame.paste(panel, (k * pw, 0))
            frame = frame.resize((frame.width * zoom, frame.height * zoom), Image.Resampling.NEAREST)
            draw = ImageDraw.Draw(frame)
            for k, name in enumerate(self.names):
                draw.text((k * pw * zoom + 6, 4), name, fill=NAME_INK, font=font)
            out.append(frame)
        return out


def maker_costs(runs):
    """The lines main prints for the run made by each maker (runs: a maker's name to its RunPictures): what each
    costs the board in bytes, then the cutout's worst miss over the run's poses. The flat maker's cost is its poses
    only: its code and its time on the board are not measured. The cutout's bytes are its pictures' pixels, with no
    header. It fills the cutout's atlas."""
    whole, flat, cutout = runs["whole"], runs["flat"], runs["cutout"]
    atlas, poses = cutout.painter.atlas, flat.poses()
    placed = [cutout.painter.placed(pose) for pose in cutout.poses()]
    used = [atlas.picture(key) for key in {part.key for parts in placed for part in parts}]
    atlas.fill()
    count, joints, parts = len(whole.pictures), len(poses[0]), len(placed[0])
    again = "; a second move costs the same again"
    return ["whole: %d pictures of %d by %d px (%d poses, both facings), %d bytes%s" % (
                2 * count, whole.size[0], whole.size[1], count, whole.size_bytes(), again),
            "flat, the poses only (no code, no time): %d poses of %d joints at two 16-bit numbers a joint, %d "
            "bytes%s" % (len(poses), joints, len(poses) * joints * 4, again),
            "cutout, the pixels only: the run uses %d part pictures, %d bytes, for one facing (the board mirrors a "
            "part for the other); with every step of the six limb kinds, %d pictures, %d bytes; %d poses of %d parts "
            "at three 16-bit numbers a part (its place and its picture), %d bytes; a second move costs its poses and "
            "the pictures of the steps that it adds" % (
                len(used), sum(p.image.width * p.image.height * 2 for p in used), len(atlas.pictures),
                atlas.size_bytes(), len(placed), parts, len(placed) * parts * 6),
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
