"""The three makers (P904 step 2b, art/makers.py): the same run made whole, flat and from turned parts (cutout). On
the standing pose and on bent(), the standing pose with each arm and each leg turned at the shoulder, the elbow, the
hip and the knee by known angles, the body leant forward and the neck bent, so no part hangs on a whole step of the
atlas; on two other poses of the same skeleton, twisted() and reaching(); and on stand-in pictures for the sheet, the
clip and the printed lines: these hold without the CMU files. And, only when the CMU files are downloaded, the
fireman's run made by each maker. Run from the repository root: python3 -m unittest discover tests."""

import dataclasses
import functools
import math
import os
import re
import sys
import unittest
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names
sys.path.insert(0, os.path.join(REPO, "tests"))

import detailed  # noqa: E402
import makers  # noqa: E402
import mocap  # noqa: E402
from brush import Sprite, rnd  # noqa: E402
from PIL import Image  # noqa: E402
from sets.rescue import FEET, STRIPE, along, leant  # noqa: E402
from test_detailed_figure import opaque_rows, standing  # noqa: E402

SMALL = 48  # px: the atlas tests that paint the most pictures paint at this height, so they run fast
LEAN, NECK = 8, -17  # degrees bent() leans the body forward, and bends the neck forward more
# degrees bent() turns each side at the shoulder, the elbow, the hip and the knee (positive: the lower end forward);
# r is the standing pose's near side
TURNS = {"r": (37, 41, 29, -54), "l": (-23, 28, -19, -33)}
ARM_JOINTS = ("humerus", "radius", "wrist", "hand", "fingers", "thumb")  # each a side's, below its clavicle
LEG_JOINTS = ("femur", "tibia", "foot", "toes")  # each a side's, below its hip joint
# each kind's joints from its joint to its end as DetailedFigure paints them, a limb's without its side's letter
CHAINS = {"upper arm": ("clavicle", "humerus"), "forearm": ("humerus", "radius"),
          "hand": ("radius", "wrist", "hand", "fingers"), "thigh": ("hipjoint", "femur"), "shin": ("femur", "tibia"),
          "foot": ("tibia", "foot", "toes"), "back gear": ("hips", "lowerback", "upperback", "thorax", "lowerneck"),
          "torso": ("hips", "lowerback", "upperback", "thorax", "lowerneck"),
          "head": ("lowerneck", "upperneck", "head")}
LIMB_KINDS = ("upper arm", "forearm", "hand", "thigh", "shin", "foot")
UPRIGHT = {"upper arm": 90, "forearm": 90, "hand": 90, "thigh": 90, "shin": 90, "foot": 0, "back gear": 270,
           "torso": 270, "head": 270}  # each kind's upright angle: hanging down, the foot forward, the rest up
SIDE = {True: "l", False: "r"}  # the standing pose's far side and near side
# DetailedFigure.paint's order: the far arm, the far leg, the gear under, the near leg, the torso and the gear over,
# the head, the near arm
PAINT_ORDER = (("upper arm", True), ("forearm", True), ("hand", True), ("thigh", True), ("shin", True), ("foot", True),
               ("back gear", False), ("thigh", False), ("shin", False), ("foot", False), ("torso", False),
               ("head", False), ("upper arm", False), ("forearm", False), ("hand", False))


def swung(pose, about, joints, degrees):
    """The pose with the joints turned about the joint about in the forward and up plane, the lower end forward."""
    c, k = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    af, au, _ = pose[about]
    out = dict(pose)
    for n in joints:
        f, u, d = pose[n]
        out[n] = (af + (f - af) * c - (u - au) * k, au + (f - af) * k + (u - au) * c, d)
    return out


def bent():
    """The standing pose leant LEAN degrees forward, each arm and leg turned by TURNS and the neck bent by NECK: each
    part's angle on the screen is 1.7 to 4.8 degrees off the nearest whole step of 11.25."""
    pose = leant(standing(), LEAN)
    for side, (shoulder, elbow, hip, knee) in TURNS.items():
        pose = swung(pose, side + "clavicle", [side + n for n in ARM_JOINTS], shoulder)
        pose = swung(pose, side + "humerus", [side + n for n in ARM_JOINTS[1:]], elbow)
        pose = swung(pose, side + "hipjoint", [side + n for n in LEG_JOINTS], hip)
        pose = swung(pose, side + "femur", [side + n for n in LEG_JOINTS[1:]], knee)
    return swung(pose, "lowerneck", ["upperneck", "head", "nose"], NECK)


def twisted():
    """The standing pose with the pelvis and the legs turned 30 degrees about the up axis, the body above the thorax
    bent 20 degrees forward at it, and the near hand bent 40 degrees at the wrist: each bone keeps its length, while
    the hip joints move against the spine, the spine bends and the hand bends."""
    pose, c, k = standing(), math.cos(math.radians(30)), math.sin(math.radians(30))
    hf, _, hd = (sum(pose[s + "hipjoint"][i] for s in "lr") / 2 for i in range(3))
    for n in [s + j for s in "lr" for j in ("hipjoint",) + LEG_JOINTS]:
        f, u, d = pose[n]
        pose[n] = (hf + (f - hf) * c - (d - hd) * k, u, hd + (f - hf) * k + (d - hd) * c)
    above = ["lowerneck", "upperneck", "head", "nose"] + [s + j for s in "lr" for j in ("clavicle",) + ARM_JOINTS]
    pose = swung(pose, "thorax", above, -20)
    return swung(pose, "rwrist", ["rhand", "rfingers", "rthumb"], 40)


def reaching():
    """bent() with the near forearm and hand turned 50 degrees toward the viewer at the elbow: out of the picture's
    plane, so on the screen the forearm is shorter than its bone."""
    pose, c, k = bent(), math.cos(math.radians(50)), math.sin(math.radians(50))
    ef, _, ed = pose["rhumerus"]
    for n in ["r" + j for j in ARM_JOINTS[1:]]:
        f, u, d = pose[n]
        pose[n] = (ef + (f - ef) * c - (d - ed) * k, u, ed + (f - ef) * k + (d - ed) * c)
    return pose


POSES = {"standing": standing, "bent": bent, "twisted": twisted, "reaching": reaching}


def opaque(img):
    a = img.getchannel("A")
    return {(x, y) for y in range(img.height) for x in range(img.width) if a.getpixel((x, y))}


def iou(a, b, shift=(0, 0)):
    """The IoU of two pictures' opaque masks, b moved by shift: the pixels both cover over the pixels either covers.
    It is the Jaccard index, "also called intersection over union (IoU)" (Wikipedia, Jaccard index,
    https://en.wikipedia.org/wiki/Jaccard_index)."""
    first, second = opaque(a), {(x + shift[0], y + shift[1]) for x, y in opaque(b)}
    return len(first & second) / len(first | second)


def painted(maker, pose_name, height=detailed.TALL, character=detailed.FIREMAN):
    """A figure of the maker and its picture of the pose, with no rim, on seed 1."""
    rnd.seed(1)
    figure = maker(detailed.box(height), height, detailed.NoRim(), character)
    return figure, figure.paint(POSES[pose_name]())


@functools.lru_cache(maxsize=None)
def made(maker, pose_name):
    """painted(maker, pose_name), once for all the tests that read it."""
    return painted(maker, pose_name)


def chain(pose, kind, far):
    """A part's joints in 3D in the pose, from its joint to its end, a limb's on its side; the hips' middle as hips."""
    side = SIDE[far] if kind in LIMB_KINDS else ""
    places = dict(pose, hips=tuple((a + b) / 2 for a, b in zip(pose["lhipjoint"], pose["rhipjoint"])))
    return [places[side + n] for n in CHAINS[kind]]


def length(pose, kind, far):
    """A part's 3D length: the sum of its bones' lengths."""
    joints = chain(pose, kind, far)
    return sum(math.dist(a, b) for a, b in zip(joints, joints[1:]))


def on_screen(figure, pose, kind, far):
    """The painter's own places (DetailedFigure.at) of a part's joint and its end: the hips' middle is between the
    places of the two hip joints."""
    side = SIDE[far] if kind in LIMB_KINDS else ""

    def at(n):
        if n == "hips":
            return along(figure.at(pose["lhipjoint"]), figure.at(pose["rhipjoint"]), 0.5)
        return figure.at(pose[side + n])

    return at(CHAINS[kind][0]), at(CHAINS[kind][-1])


def covered(figure, part):
    """The pixels a placed part's picture covers in the figure's picture: (x, y) each."""
    x, y = part.place
    return {(x + i, y + j) for i, j in opaque(figure.atlas.picture(part.key).image)}


def visible(figure, parts, k):
    """The pixels of part k that no later part covers."""
    later = set().union(*(covered(figure, part) for part in parts[k + 1:]))
    return covered(figure, parts[k]) - later


def mean(img, pixels):
    return [sum(img.getpixel(q)[i] for q in pixels) / len(pixels) for i in range(3)]


def in565(colour):
    """A colour as the board shows it (export.q565)."""
    return detailed.q565(Image.new("RGBA", (1, 1), tuple(colour) + (255,))).getpixel((0, 0))[:3]


class Recording(makers.FlatFigure):
    """A flat figure that keeps each colour that part and detail get."""

    def paint(self, pose):
        self.given = set()
        return super().paint(pose)

    def part(self, s, mask, colour, band=None):
        self.given.add(colour)
        super().part(s, mask, colour, band)

    def detail(self, s, mask, colour, light=None, rim=0):
        self.given.add(colour)
        super().detail(s, mask, colour, light, rim)


class Reversed(makers.Atlas):
    """An atlas that turns each part the wrong way."""

    def turn(self, kind, step):
        return -super().turn(kind, step)


class ReversedCutout(makers.CutoutFigure):
    """A cutout figure whose atlas turns each part the wrong way."""

    ATLAS = Reversed


class Coarse(makers.Atlas):
    """An atlas with a picture every 45 degrees."""

    STEPS = 8


class CoarseCutout(makers.CutoutFigure):
    """A cutout figure with a part picture every 45 degrees."""

    ATLAS = Coarse


class Wide(makers.Atlas):
    """An atlas whose capsules are wider than any limb, so nothing across a bone is masked."""

    MARGIN = 0.3


class WideCutout(makers.CutoutFigure):
    """A cutout figure whose atlas does not mask a limb across its bone."""

    ATLAS = Wide


class FlatTest(unittest.TestCase):
    """The flat maker on the standing pose at 96 px with no rim (and once with the outline), beside the whole
    painter's picture."""

    def test_every_opaque_pixel_is_a_colour_that_part_or_detail_got_or_the_bands(self):
        rnd.seed(1)
        figure = Recording(detailed.box(detailed.TALL), detailed.TALL, detailed.NoRim())
        img = detailed.q565(figure.paint(standing()))
        given = {in565(c) for c in figure.given} | {in565(STRIPE)}
        self.assertGreaterEqual(len(figure.given), 12)
        self.assertEqual(set(), {img.getpixel(q)[:3] for q in opaque(img)} - given)

    def test_its_shape_agrees_with_the_whole_painters(self):
        self.assertGreaterEqual(iou(made(detailed.DetailedFigure, "standing")[1], made(makers.FlatFigure,
                                                                                          "standing")[1]), 0.97)

    def test_the_soles_are_on_the_last_row(self):
        img = made(makers.FlatFigure, "standing")[1]
        self.assertEqual(img.height - 1, opaque_rows(img)[-1])

    def test_a_band_pixel_is_the_bands_colour(self):
        """The band pixels are those that the bands change."""
        img = made(makers.FlatFigure, "standing")[1]
        plain = painted(makers.FlatFigure, "standing", character=dataclasses.replace(detailed.FIREMAN, bands=False))[1]
        bands = [q for q in opaque(img) if img.getpixel(q) != plain.getpixel(q)]
        self.assertGreaterEqual(len(bands), 30)
        self.assertEqual({STRIPE + (255,)}, {img.getpixel(q) for q in bands})

    def test_a_band_pixel_is_where_the_bands_cover_the_pixels_middle(self):
        """The bands are sampled as the colours are: at the 8x pixel nearest the pixel's middle."""
        rnd.seed(1)
        figure = makers.FlatFigure(detailed.box(detailed.TALL), detailed.TALL, detailed.NoRim())
        img, s = figure.paint(standing()), Sprite.S
        middle = {(x, y) for x, y in opaque(img) if figure.bands.getpixel((x * s + s // 2, y * s + s // 2))}
        self.assertGreaterEqual(len(middle), 30)
        self.assertEqual(middle, {q for q in opaque(img) if img.getpixel(q)[:3] == STRIPE})

    def test_with_the_outline_its_edge_is_one_px_all_round_the_flat_shape(self):
        rnd.seed(1)
        img = makers.FlatFigure(detailed.box(detailed.TALL), detailed.TALL).paint(standing())
        shape = opaque(made(makers.FlatFigure, "standing")[1])
        ring = {(x + dx, y + dy) for x, y in shape for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))} - shape
        self.assertEqual({q for q in ring if 0 <= q[0] < img.width and 0 <= q[1] < img.height}, opaque(img) - shape)


class CutoutTest(unittest.TestCase):
    """The cutout maker on the standing pose and on bent() at 96 px with no rim, beside the whole painter's picture;
    its atlas on bent(), twisted() and reaching(), some at 48 px."""

    BENT = 0.86  # the IoU with the whole painter's on bent(): measured 0.878, and 0.525 with the turn reversed

    def test_standing_its_shape_agrees_with_the_whole_painters(self):
        self.assertGreaterEqual(iou(made(detailed.DetailedFigure, "standing")[1],
                                    made(makers.CutoutFigure, "standing")[1]), 0.94)

    def test_bent_its_shape_agrees_and_with_the_turn_reversed_it_does_not(self):
        whole = made(detailed.DetailedFigure, "bent")[1]
        self.assertGreaterEqual(iou(whole, made(makers.CutoutFigure, "bent")[1]), self.BENT)
        self.assertLess(iou(whole, painted(ReversedCutout, "bent")[1]), self.BENT)

    def test_the_soles_are_within_a_row_of_the_last_row(self):
        """Not on it: the upright foot is straight from the ankle to the toes, and the standing pose's ball is 0.7 px
        under that line, so the sole lands a row higher."""
        img = made(makers.CutoutFigure, "standing")[1]
        self.assertIn(opaque_rows(img)[-1], (img.height - 2, img.height - 1))

    def test_the_parts_come_in_the_paint_order_and_each_pivot_lands_on_the_painters_joint(self):
        """The joint: DetailedFigure.at of the pose's joint, a far limb's on the far side. The end: within half a
        step's chord, plus the 3D length less the screen length, plus 0.71 px; and misses() is that distance."""
        figure, pose = made(makers.CutoutFigure, "bent")[0], bent()
        parts = figure.placed(pose)
        self.assertEqual(list(PAINT_ORDER), [part.key[:2] for part in parts])
        for part, miss in zip(parts, figure.misses(pose)):
            kind, far = part.key[:2]
            with self.subTest(part=part.key):
                joint, end = on_screen(figure, pose, kind, far)
                picture, (x, y) = figure.atlas.picture(part.key), part.place
                self.assertLessEqual(math.dist((x + picture.pivot[0], y + picture.pivot[1]), joint), 0.71)
                bone = length(pose, kind, far) * figure.PX
                chord = bone * 2 * math.sin(math.radians(180 / figure.atlas.STEPS) / 2)  # half a step's
                landed = math.dist((x + picture.end[0], y + picture.end[1]), end)
                self.assertLessEqual(landed, chord + bone - math.dist(joint, end) + 0.71)
                self.assertAlmostEqual(landed, miss)

    def test_an_angle_rounds_to_the_nearest_step_wraps_and_takes_a_half_step_to_the_even_step(self):
        atlas = made(makers.CutoutFigure, "bent")[0].atlas
        self.assertEqual(32, atlas.STEPS)
        self.assertEqual([0, 0, 2, 30, 8], [atlas.step(a) for a in (5, 355, 17, -17, 92)])
        self.assertEqual([0, 2], [atlas.step(a) for a in (5.625, 16.875)])
        self.assertEqual(("thigh", True, 2), atlas.key("thigh", True, 17))

    def test_the_turn_takes_the_upright_picture_to_the_steps_angle_counter_clockwise(self):
        """Sprite.turn turns counter-clockwise; a screen angle grows clockwise, with y down."""
        atlas = made(makers.CutoutFigure, "bent")[0].atlas
        self.assertEqual([90 - 22.5, 0 - 22.5, 270 - 22.5], [atlas.turn(k, 2) for k in ("thigh", "foot", "torso")])

    def test_the_near_arm_is_pasted_over_the_torso(self):
        figure, img = made(makers.CutoutFigure, "bent")
        parts = figure.placed(bent())
        torso, upper = (PAINT_ORDER.index(k) for k in (("torso", False), ("upper arm", False)))
        over = visible(figure, parts, upper) & covered(figure, parts[torso])
        self.assertGreaterEqual(len(over), 20)
        x, y = parts[upper].place
        picture = figure.atlas.picture(parts[upper].key).image
        self.assertEqual([picture.getpixel((i - x, j - y)) for i, j in sorted(over)],
                         [img.getpixel(q) for q in sorted(over)])

    def test_a_far_limb_has_the_far_shade(self):
        """The far thigh's pixels that show are darker than the near thigh's: shade() is 0.7 of the trousers' colour.
        (In bent() the far arm shows 4 pixels in the cutout's picture, all of its hand, and 1 in the whole
        painter's; and a far boot is lighter, not darker.)"""
        figure, img = made(makers.CutoutFigure, "bent")
        parts = figure.placed(bent())
        far, near = (visible(figure, parts, PAINT_ORDER.index(("thigh", f))) for f in (True, False))
        self.assertGreaterEqual(min(len(far), len(near)), 10)
        self.assertLess(sum(mean(img, far)), 0.85 * sum(mean(img, near)))

    def test_in_the_atlas_a_far_upper_arm_is_darker_than_a_near_one_at_the_same_step(self):
        atlas = made(makers.CutoutFigure, "bent")[0].atlas
        for step in (8, 11):
            with self.subTest(step=step):
                far, near = (atlas.picture(("upper arm", f, step)).image for f in (True, False))
                self.assertLess(sum(mean(far, opaque(far))), 0.85 * sum(mean(near, opaque(near))))

    def test_with_8_steps_the_worst_end_miss_is_larger_than_with_32(self):
        rnd.seed(1)
        coarse = CoarseCutout(detailed.box(detailed.TALL), detailed.TALL, detailed.NoRim())
        self.assertGreater(max(coarse.misses(bent())), max(made(makers.CutoutFigure, "bent")[0].misses(bent())))

    def test_the_same_pose_painted_twice_adds_no_picture_and_the_bytes_are_the_sum(self):
        figure, _ = painted(makers.CutoutFigure, "bent", SMALL)
        keys, upright = set(figure.atlas.pictures), figure.atlas.upright
        joints = dict(upright.joints)
        self.assertEqual(len(PAINT_ORDER), len(keys))
        figure.paint(bent())
        self.assertEqual(keys, set(figure.atlas.pictures))
        self.assertEqual(sum(p.image.width * p.image.height * 2 for p in figure.atlas.pictures.values()),
                         figure.atlas.size_bytes())
        figure.paint(twisted())
        self.assertIs(upright, figure.atlas.upright)
        self.assertEqual(joints, figure.atlas.upright.joints)

    def test_two_first_poses_with_the_same_bone_lengths_give_the_same_part_pictures(self):
        """The upright pose is built from the bone lengths alone: standing() and twisted() at 48 px, each part at its
        upright step and three steps on, byte for byte."""
        first, other = (painted(makers.CutoutFigure, name, SMALL)[0].atlas for name in ("standing", "twisted"))
        for kind, far in PAINT_ORDER:
            for degrees in (UPRIGHT[kind], UPRIGHT[kind] + 3 * 360 / first.STEPS):
                with self.subTest(kind=kind, far=far, degrees=degrees):
                    a, b = (atlas.picture(atlas.key(kind, far, degrees)) for atlas in (first, other))
                    self.assertEqual((a.image.size, a.image.tobytes(), a.pivot), (b.image.size, b.image.tobytes(),
                                                                                  b.pivot))
                    for u, v in zip(a.end, b.end):
                        self.assertAlmostEqual(u, v, places=6)

    def test_each_parts_bone_is_its_3d_length_also_when_it_points_toward_the_viewer(self):
        """reaching() is measured first: its near forearm is shorter on the screen than its bone, and its hip joints
        are off the hips' middle, toward and away from the viewer, so the torso's bone starts at the middle."""
        figure, pose = painted(makers.CutoutFigure, "reaching", SMALL)[0], reaching()
        screen = math.dist(*(figure.at(pose["r" + n]) for n in ("humerus", "radius")))
        self.assertLess(screen, 0.7 * length(pose, "forearm", False) * figure.PX)
        for kind, far in PAINT_ORDER:
            with self.subTest(kind=kind, far=far):
                picture = figure.atlas.picture(figure.atlas.key(kind, far, UPRIGHT[kind]))
                self.assertAlmostEqual(length(pose, kind, far) * figure.PX, math.dist(picture.pivot, picture.end))

    def test_after_fill_each_limb_kind_has_every_step_in_each_shade_and_the_others_keep_theirs(self):
        figure, _ = painted(makers.CutoutFigure, "bent", SMALL)
        others = {key for key in figure.atlas.pictures if key[0] not in LIMB_KINDS}
        figure.atlas.fill()
        counts = Counter(key[:2] for key in figure.atlas.pictures if key[0] in LIMB_KINDS)
        self.assertEqual({(kind, far): figure.atlas.STEPS for kind in LIMB_KINDS for far in (True, False)},
                         dict(counts))
        self.assertEqual(others, {key for key in figure.atlas.pictures if key[0] not in LIMB_KINDS})

    def test_a_band_on_a_turned_part_is_the_bands_colour_at_the_turned_place(self):
        """The near forearm turns from hanging down to forward: its band is across it at 0.62 of the way from the
        elbow, as the whole painter puts it, in the band's colour in RGB565 (the atlas's pictures are)."""
        figure, img = made(makers.CutoutFigure, "bent")
        elbow, wrist = (figure.at(bent()["r" + n]) for n in ("humerus", "radius"))
        bone, (ux, uy) = math.dist(elbow, wrist), ((wrist[0] - elbow[0]), (wrist[1] - elbow[1]))
        on = []
        for x, y in opaque(img):
            if img.getpixel((x, y))[:3] != in565(STRIPE):
                continue
            dx, dy = x + 0.5 - elbow[0], y + 0.5 - elbow[1]
            ahead, across = (dx * ux + dy * uy) / bone, abs(dx * uy - dy * ux) / bone
            if 0.3 * bone <= ahead <= 0.9 * bone and across <= figure.FORE[0] * figure.PX / 2 + 1:
                on.append((x + 0.5, y + 0.5))
        self.assertGreaterEqual(len(on), 4)
        middle = (sum(x for x, _ in on) / len(on), sum(y for _, y in on) / len(on))
        self.assertLessEqual(math.dist(middle, along(elbow, wrist, 0.62)), 2)

    def test_a_limb_part_is_masked_to_a_capsule_round_its_bone(self):
        """At its upright step, a limb part's picture is along its bone no longer than the bone and two of the
        capsule's half widths, and across it no wider than two; and it covers its bone."""
        figure = made(makers.CutoutFigure, "bent")[0]
        atlas = figure.atlas
        for kind in LIMB_KINDS:
            for far in (True, False):
                with self.subTest(kind=kind, far=far):
                    picture = atlas.picture(atlas.key(kind, far, UPRIGHT[kind]))
                    w, h = picture.image.size
                    along_, across = (w, h) if UPRIGHT[kind] == 0 else (h, w)
                    bone, half = math.dist(picture.pivot, picture.end), (makers.KINDS[kind].half + atlas.MARGIN)
                    self.assertGreaterEqual(along_, bone)
                    self.assertLessEqual(along_, bone + 2 * half * figure.PX + 2)
                    self.assertLessEqual(across, 2 * half * figure.PX + 2)

    def test_a_limb_part_is_as_wide_across_its_bone_as_the_whole_painters_limb(self):
        """Across the middle of its bone, at its upright step, it covers the pixels that the same part with no
        capsule across it (Wide) covers."""
        narrow, wide = made(makers.CutoutFigure, "bent")[0].atlas, painted(WideCutout, "bent")[0].atlas
        for kind in LIMB_KINDS:
            for far in (True, False):
                with self.subTest(kind=kind, far=far):
                    widths = []
                    for atlas in (narrow, wide):
                        picture = atlas.picture(atlas.key(kind, far, UPRIGHT[kind]))
                        (px, py), (ex, ey), img = picture.pivot, picture.end, picture.image
                        mx, my = int((px + ex) / 2), int((py + ey) / 2)
                        line = ([(mx, y) for y in range(img.height)] if UPRIGHT[kind] == 0 else
                                [(x, my) for x in range(img.width)])
                        widths.append(sum(1 for q in line if img.getpixel(q)[3]))
                    self.assertGreaterEqual(widths[0], 4)
                    self.assertEqual(widths[1], widths[0])

    def test_no_part_reaches_its_sprites_edge_at_any_step(self):
        """Each part's upright painting, before the cut, lies inside the circle that the sprite holds round its
        middle, so a turn about the joint there never takes a pixel off the sprite."""
        atlas = made(makers.CutoutFigure, "bent")[0].atlas
        r = atlas.reach
        for (kind, far), (sprite, _) in atlas.uprights.items():
            with self.subTest(kind=kind, far=far):
                cover = sprite.alpha.resize((sprite.w, sprite.h), Image.Resampling.BOX)
                corners = [math.dist((x + i, y + j), (r, r)) for y in range(cover.height) for x in range(cover.width)
                           if cover.getpixel((x, y)) for i in (0, 1) for j in (0, 1)]
                self.assertLessEqual(max(corners), r)

    def test_a_character_with_no_back_gear_has_an_empty_back_gear_part(self):
        figure, img = painted(makers.CutoutFigure, "standing", SMALL, detailed.FOOTBALLER)
        self.assertEqual((0, 0), figure.atlas.picture(figure.atlas.key("back gear", False, 270)).image.size)
        self.assertIn(opaque_rows(img)[-1], (img.height - 2, img.height - 1))


class StandRun(detailed.Pictures):
    """A stand-in for RunPictures: one plain picture a pose, each its own shade of colour with its pivot's pixel white,
    and poses of seven joints whose first number is the pose's index."""

    def __init__(self, colour, size, pivot_x, painter=None, height=detailed.TALL):
        self.size, self.pivot, self.painter, self.height = size, (pivot_x, size[1] - 1), painter, height
        self.pictures = [Image.new("RGBA", size, colour + (10 + 20 * i, 255)) for i in range(12)]
        for img in self.pictures:
            img.putpixel(self.pivot, (255, 255, 255, 255))

    def poses(self):
        return [{"j%d" % k: (i, 0.0, 0.0) for k in range(7)} for i in range(12)]


USED = (("thigh", False, 0), ("thigh", False, 1), ("thigh", False, 2))  # the stand-in run's part keys
LATE = ("thigh", False, 3)  # the key that only pose 7 of the stand-in run uses


class StandAtlas:
    """A stand-in for Atlas: for any key a plain picture 9 px high, of its own colour (its kind, its shade and its
    step) and as wide as 3 px and its kind's index in CHAINS. Its cache holds the run's three keys and one more;
    fill() adds two."""

    STEPS = 32

    def __init__(self):
        self.pictures = {key: self.picture(key) for key in USED + (("head", False, 24),)}

    def key(self, kind, far, degrees):
        return (kind, far, round(degrees * self.STEPS / 360) % self.STEPS)

    @staticmethod
    def colour(key):
        kind, far, step = key
        return (20 + 20 * list(CHAINS).index(kind), 200 if far else 100, 1 + 7 * step)

    def picture(self, key):
        img = Image.new("RGBA", (3 + list(CHAINS).index(key[0]), 9), self.colour(key) + (255,))
        return makers.PartPicture(img, (0, 0), (0, 0))

    def size_bytes(self):
        return sum(p.image.width * p.image.height * 2 for p in self.pictures.values())

    def fill(self):
        for k in (3, 4):
            self.pictures["shin", True, k] = self.picture(("shin", True, k))


class StandCutout:
    """A stand-in for CutoutFigure: its atlas, fifteen parts a pose, each with one of the three keys of USED, and in
    pose 7 one of four, with LATE; and three misses a pose, whose worst over the run, 3.0, is the middle one of pose
    5."""

    def __init__(self):
        self.atlas = StandAtlas()

    def placed(self, pose):
        keys = USED + (LATE,) if pose["j0"][0] == 7 else USED
        return [makers.Placed(keys[k % len(keys)], (0, 0), (0, 0), (0, 0)) for k in range(15)]

    def misses(self, pose):
        i = pose["j0"][0]
        return [0.5, 3.0 if i == 5 else i / 8, 0.25]


def stand_runs():
    return {"whole": StandRun((200, 0), (30, 50), 12), "flat": StandRun((0, 200), (28, 48), 10),
            "cutout": StandRun((0, 0), (34, 52), 15, StandCutout())}


def bottom_left(widths, k, height, zoom):
    """Where on_dark puts the bottom left pixel of the k-th of pictures of these widths, in a row of this height, at
    zoom: (x, y) in the zoomed row."""
    gap = detailed.GAP
    return (gap * (k + 1) + sum(widths[:k])) * zoom, (height - gap - 1) * zoom


class MakerSheetTest(unittest.TestCase):
    """MakerSheet on stand-in runs of three sizes, each picture its own colour, and a stand-in atlas whose picture's
    colour tells its key: every row's label, and each picture's colour at its place."""

    def setUp(self):
        self.runs = stand_runs()
        self.rows = makers.MakerSheet(self.runs).rows()
        self.atlas = self.runs["cutout"].painter.atlas

    def test_six_rows_and_their_labels(self):
        self.assertEqual(["whole: the run's twelve poses at 96 px, each 30 by 50 px",
                          "flat: the run's twelve poses at 96 px, each 28 by 48 px",
                          "cutout: the run's twelve poses at 96 px, each 34 by 52 px",
                          "pose 3 by each maker at 3x: whole, flat, cutout",
                          "the cutout's 15 parts of a pose at their upright angles, in paste order (far, then near), "
                          "at 2x", "the near thigh at 8 of the 32 steps, 45 degrees apart, at 2x"],
                         [label for label, _ in self.rows])

    def test_each_makers_row_holds_its_twelve_poses_in_order(self):
        for (name, run), (_, img) in zip(self.runs.items(), self.rows):
            for i in range(12):
                with self.subTest(maker=name, pose=i):
                    x, y = bottom_left([run.size[0]] * 12, i, img.height, 1)
                    self.assertEqual(run.pictures[i].getpixel((0, run.size[1] - 1))[:3], img.getpixel((x, y)))

    def test_the_pose_row_holds_pose_3_of_each_maker_in_order(self):
        img, zoom = self.rows[3][1], makers.MakerSheet.ZOOM
        runs = list(self.runs.values())
        for k, run in enumerate(runs):
            with self.subTest(maker=k):
                x, y = bottom_left([r.size[0] for r in runs], k, img.height // zoom, zoom)
                self.assertEqual(run.pictures[3].getpixel((0, run.size[1] - 1))[:3], img.getpixel((x, y)))

    def test_the_parts_row_names_each_part_under_it_in_paste_order(self):
        """On one of three lines in turn, under the strip."""
        zoom, height = makers.MakerSheet.PARTS_ZOOM, 9 + 2 * detailed.GAP
        keys = [self.atlas.key(kind, far, UPRIGHT[kind]) for kind, far in PAINT_ORDER]
        widths = [self.atlas.picture(key).image.width for key in keys]
        sheet = makers.MakerSheet(self.runs)
        self.assertEqual([((bottom_left(widths, k, height, zoom)[0], height * zoom + k % 3 * makers.NAME_H), kind)
                          for k, (kind, _) in enumerate(PAINT_ORDER)], sheet.labels(sheet.parts()))

    def test_the_parts_row_holds_each_part_at_its_upright_step_and_the_thigh_row_the_near_thigh(self):
        zoom, height = makers.MakerSheet.PARTS_ZOOM, 9 + 2 * detailed.GAP
        keys = [self.atlas.key(kind, far, UPRIGHT[kind]) for kind, far in PAINT_ORDER]
        thighs = [("thigh", False, step) for step in range(0, 32, 4)]
        for row, row_keys in ((self.rows[4][1], keys), (self.rows[5][1], thighs)):
            widths = [self.atlas.picture(key).image.width for key in row_keys]
            for k, key in enumerate(row_keys):
                with self.subTest(key=key):
                    self.assertEqual(StandAtlas.colour(key), row.getpixel(bottom_left(widths, k, height, zoom)))


class MakerClipTest(unittest.TestCase):
    """MakerClip on stand-in runs of three sizes and pivots, each picture its own colour, over a plain street whose
    FEET row is marked."""

    FEET_MARK = (250, 10, 10)

    def test_twelve_frames_of_three_panels_of_one_size_each_named_each_pose_in_its_panel_on_the_feet_row(self):
        runs = stand_runs()
        street = Image.new("RGB", (detailed.CharacterClip.W, 240), (40, 40, 40))
        for x in range(street.width):
            street.putpixel((x, FEET), self.FEET_MARK)
        clip = makers.MakerClip(runs, street)
        frames, (pw, ph), zoom = clip.frames(), clip.panel, makers.MakerClip.ZOOM
        self.assertEqual(12, len(frames))
        self.assertEqual({(3 * pw * zoom, ph * zoom)}, {frame.size for frame in frames})
        self.assertEqual([((k * pw * zoom + 6, 4), name) for k, name in enumerate(("whole", "flat", "cutout"))],
                         clip.labels())
        x, y = makers.MakerClip.MARGIN + max(run.pivot[0] for run in runs.values()), ph - makers.MakerClip.MARGIN - 1
        for i, frame in enumerate(frames):
            for k, run in enumerate(runs.values()):
                with self.subTest(frame=i, panel=k):
                    self.assertEqual((255, 255, 255), frame.getpixel(((k * pw + x) * zoom, y * zoom)))
                    self.assertEqual(run.pictures[i].getpixel((run.pivot[0] - 1, run.size[1] - 1))[:3],
                                     frame.getpixel(((k * pw + x - 1) * zoom, y * zoom)))
                    self.assertEqual(self.FEET_MARK, frame.getpixel(((k * pw + 1) * zoom, y * zoom)))
                    self.assertEqual((40, 40, 40), frame.getpixel(((k * pw + 1) * zoom, (y - 1) * zoom)))


class MakerCostsTest(unittest.TestCase):
    """maker_costs on stand-in runs: every number in each line, in order, is its source's."""

    def test_every_number_in_each_line_is_its_sources(self):
        runs = stand_runs()
        atlas = runs["cutout"].painter.atlas
        used = sum(atlas.picture(key).image.width * 9 * 2 for key in USED + (LATE,))
        lines = makers.maker_costs(runs)
        self.assertEqual(4, len(lines))
        numbers = [re.findall(r"\d+(?:\.\d+)?", line) for line in lines]
        self.assertEqual([["24", "30", "50", "12", str(runs["whole"].size_bytes())],
                          ["12", "7", "16", str(12 * 7 * 4)],
                          ["4", str(used), "6", "5", "1", str(atlas.size_bytes()), "12", "15", "16", str(12 * 15 * 6)],
                          ["3.00"]], numbers)
        self.assertIn("mirrors", lines[2])


@functools.lru_cache(maxsize=None)
def captured():
    """The fireman's run made by each maker from the CMU files, once for all the tests that read it; None without the
    files."""
    capture = mocap.Capture()
    if capture.missing((mocap.named("run"),)):
        return None
    return {name: detailed.RunPictures(capture, detailed.TALL, maker=maker) for name, maker in makers.MAKERS.items()}


class MakersFromCaptureTest(unittest.TestCase):
    """The fireman's run made by each maker from the CMU files at 96 px. Skipped without the files, and a skip is not a
    pass."""

    @classmethod
    def setUpClass(cls):
        if captured() is None:
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.runs = captured()

    def test_the_makers_are_the_whole_painter_the_flat_one_and_the_cutout(self):
        self.assertEqual({"whole": detailed.DetailedFigure, "flat": makers.FlatFigure, "cutout": makers.CutoutFigure},
                         makers.MAKERS)
        for name, run in self.runs.items():
            with self.subTest(maker=name):
                self.assertIs(makers.MAKERS[name], type(run.painter))

    def test_each_makers_run_has_twelve_poses_in_one_box(self):
        for name, run in self.runs.items():
            with self.subTest(maker=name):
                self.assertEqual(12, len(run.pictures))
                self.assertEqual({run.size}, {img.size for img in run.pictures + run.left})

    def test_the_cutouts_run_agrees_with_the_whole_painters_in_every_pose(self):
        whole, cutout = self.runs["whole"], self.runs["cutout"]
        shift = (whole.pivot[0] - cutout.pivot[0], whole.pivot[1] - cutout.pivot[1])
        for i, (a, b) in enumerate(zip(whole.pictures, cutout.pictures)):
            with self.subTest(pose=i):
                self.assertGreaterEqual(iou(a, b, shift), 0.8)


if __name__ == "__main__":
    unittest.main()
