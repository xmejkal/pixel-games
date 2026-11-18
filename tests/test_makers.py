"""The three makers (P904 step 2b, art/makers.py): the same run made whole, flat and from turned parts (cutout). On
the standing pose and on bent(), the standing pose with each arm and each leg turned at the shoulder, the elbow, the
hip and the knee by known angles and the body leant forward, so no part hangs on a whole step of the atlas; and on
stand-in pictures for the sheet, the clip and the printed lines: these hold without the CMU files. And, only when the
CMU files are downloaded, the fireman's run made by each maker. Run from the repository root: python3 -m unittest
discover tests."""

import dataclasses
import functools
import math
import os
import sys
import unittest
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names
sys.path.insert(0, os.path.join(REPO, "tests"))

import detailed  # noqa: E402
import makers  # noqa: E402
import mocap  # noqa: E402
from brush import rnd  # noqa: E402
from PIL import Image  # noqa: E402
from sets.rescue import STRIPE, along, leant  # noqa: E402
from test_detailed_figure import opaque_rows, standing  # noqa: E402

SMALL = 48  # px: the two atlas tests that paint the most pictures paint at this height, so they run fast
LEAN = 8  # degrees bent() leans the body forward
# degrees bent() turns each side at the shoulder, the elbow, the hip and the knee (positive: the lower end forward);
# r is the standing pose's near side
TURNS = {"r": (37, 41, 29, -54), "l": (-23, 28, -19, -33)}
ARM, LEG = ("humerus", "radius", "wrist", "hand", "fingers", "thumb"), ("femur", "tibia", "foot", "toes")


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
    """The standing pose leant LEAN degrees forward, each arm and leg turned by TURNS: each part's angle on the screen
    is 1.7 to 4.8 degrees off the nearest whole step of 11.25."""
    pose = leant(standing(), LEAN)
    for side, (shoulder, elbow, hip, knee) in TURNS.items():
        pose = swung(pose, side + "clavicle", [side + n for n in ARM], shoulder)
        pose = swung(pose, side + "humerus", [side + n for n in ARM[1:]], elbow)
        pose = swung(pose, side + "hipjoint", [side + n for n in LEG], hip)
        pose = swung(pose, side + "femur", [side + n for n in LEG[1:]], knee)
    return pose


POSES = {"standing": standing, "bent": bent}


def opaque(img):
    a = img.getchannel("A")
    return {(x, y) for y in range(img.height) for x in range(img.width) if a.getpixel((x, y))}


def iou(a, b, shift=(0, 0)):
    """The IoU of two pictures' opaque masks, b moved by shift: the pixels both cover over the pixels either covers."""
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


def bone(pose, kind, far):
    """A part's joint and end in 3D in the pose: a limb's on the far side (l) or the near side (r)."""
    joint, end = makers.BONES[kind]
    side = ("l" if far else "r") if kind in makers.LIMBS else ""
    places = dict(pose, hips=tuple((a + b) / 2 for a, b in zip(pose["lhipjoint"], pose["rhipjoint"])))
    return places[side + joint], places[side + end]


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


def q565(colour):
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
    ATLAS = Reversed


class Coarse(makers.Atlas):
    """An atlas with a picture every 45 degrees."""

    ANGLES = 8


class CoarseCutout(makers.CutoutFigure):
    ATLAS = Coarse


class FlatTest(unittest.TestCase):
    """The flat maker on the standing pose at 96 px with no rim, beside the whole painter's picture."""

    def test_every_opaque_pixel_is_a_colour_that_part_or_detail_got_or_the_bands(self):
        rnd.seed(1)
        figure = Recording(detailed.box(detailed.TALL), detailed.TALL, detailed.NoRim())
        img = detailed.q565(figure.paint(standing()))
        given = {q565(c) for c in figure.given} | {q565(STRIPE)}
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


class CutoutTest(unittest.TestCase):
    """The cutout maker on the standing pose and on bent() at 96 px with no rim, beside the whole painter's picture;
    its atlas on bent(), and filled at 48 px."""

    BENT = 0.86  # the IoU with the whole painter's on bent(): measured 0.874, and 0.569 with the turn reversed

    def test_standing_its_shape_agrees_with_the_whole_painters(self):
        self.assertGreaterEqual(iou(made(detailed.DetailedFigure, "standing")[1],
                                    made(makers.CutoutFigure, "standing")[1]), 0.94)

    def test_bent_its_shape_agrees_and_with_the_turn_reversed_it_does_not(self):
        whole = made(detailed.DetailedFigure, "bent")[1]
        self.assertGreaterEqual(iou(whole, made(makers.CutoutFigure, "bent")[1]), self.BENT)
        self.assertLess(iou(whole, painted(ReversedCutout, "bent")[1]), self.BENT)

    def test_each_parts_pivot_lands_on_its_joint_and_its_end_near_the_poses(self):
        """The end: within the angle step's error, plus the 3D length less the screen length, plus 0.71 px."""
        figure, pose = made(makers.CutoutFigure, "bent")[0], bent()
        parts = figure.placed(pose)
        self.assertEqual([(kind, far) for kind, far in makers.PARTS], [part.key[:2] for part in parts])
        for part in parts:
            with self.subTest(part=part.key):
                picture, (x, y) = figure.atlas.picture(part.key), part.place
                self.assertLessEqual(math.dist((x + picture.pivot[0], y + picture.pivot[1]), part.joint), 0.71)
                length = math.dist(*bone(pose, *part.key[:2])) * figure.PX
                step = length * 2 * math.sin(math.radians(180 / figure.atlas.ANGLES) / 2)
                bound = step + length - math.dist(part.joint, part.end) + 0.71
                self.assertLessEqual(math.dist((x + picture.end[0], y + picture.end[1]), part.end), bound)

    def test_an_angle_rounds_to_the_nearest_step_and_wraps(self):
        atlas = made(makers.CutoutFigure, "bent")[0].atlas
        self.assertEqual(32, atlas.ANGLES)
        self.assertEqual([0, 0, 2, 30, 8], [atlas.step(a) for a in (5, 355, 17, -17, 92)])
        self.assertEqual(("thigh", True, 2), atlas.key("thigh", True, 17))

    def test_the_turn_takes_the_upright_picture_to_the_steps_angle_counter_clockwise(self):
        """Sprite.turn turns counter-clockwise; a screen angle grows clockwise, with y down."""
        atlas = made(makers.CutoutFigure, "bent")[0].atlas
        self.assertEqual([90 - 22.5, 0 - 22.5, 270 - 22.5], [atlas.turn(k, 2) for k in ("thigh", "foot", "torso")])

    def test_the_near_arm_is_pasted_over_the_torso(self):
        figure, img = made(makers.CutoutFigure, "bent")
        parts = figure.placed(bent())
        torso, upper = (makers.PARTS.index(k) for k in (("torso", False), ("upper arm", False)))
        over = visible(figure, parts, upper) & covered(figure, parts[torso])
        self.assertGreaterEqual(len(over), 20)
        x, y = parts[upper].place
        picture = figure.atlas.picture(parts[upper].key).image
        self.assertEqual([picture.getpixel((i - x, j - y)) for i, j in sorted(over)],
                         [img.getpixel(q) for q in sorted(over)])

    def test_a_far_limb_has_the_far_shade(self):
        """The far thigh's pixels that show are darker than the near thigh's: shade() is 0.7 of the trousers' colour.
        (In bent() the far arm hangs behind the body and the tank, and a far boot is lighter, not darker.)"""
        figure, img = made(makers.CutoutFigure, "bent")
        parts = figure.placed(bent())
        far, near = (visible(figure, parts, makers.PARTS.index(("thigh", f))) for f in (True, False))
        self.assertGreaterEqual(min(len(far), len(near)), 10)
        self.assertLess(sum(mean(img, far)), 0.85 * sum(mean(img, near)))

    def test_with_8_angles_the_worst_end_miss_is_larger_than_with_32(self):
        rnd.seed(1)
        coarse = CoarseCutout(detailed.box(detailed.TALL), detailed.TALL, detailed.NoRim())
        self.assertGreater(max(coarse.misses(bent())), max(made(makers.CutoutFigure, "bent")[0].misses(bent())))

    def test_the_same_pose_painted_twice_adds_no_picture_and_the_bytes_are_the_sum(self):
        figure, _ = painted(makers.CutoutFigure, "bent", SMALL)
        keys = set(figure.atlas.pictures)
        self.assertEqual(len(makers.PARTS), len(keys))
        figure.paint(bent())
        self.assertEqual(keys, set(figure.atlas.pictures))
        self.assertEqual(sum(p.image.width * p.image.height * 2 for p in figure.atlas.pictures.values()),
                         figure.atlas.bytes())

    def test_after_fill_each_limb_kind_has_every_angle_in_each_shade_and_the_others_keep_theirs(self):
        figure, _ = painted(makers.CutoutFigure, "bent", SMALL)
        others = {key for key in figure.atlas.pictures if key[0] not in makers.LIMBS}
        figure.atlas.fill()
        counts = Counter(key[:2] for key in figure.atlas.pictures if key[0] in makers.LIMBS)
        self.assertEqual({(kind, far): figure.atlas.ANGLES for kind in makers.LIMBS for far in (True, False)},
                         dict(counts))
        self.assertEqual(others, {key for key in figure.atlas.pictures if key[0] not in makers.LIMBS})

    def test_a_band_on_a_turned_part_is_the_bands_colour_at_the_turned_place(self):
        """The near forearm turns from hanging down to forward: its band is across it at 0.62 of the way from the
        elbow, as the whole painter puts it, in the band's colour in RGB565 (the atlas's pictures are)."""
        figure, img = made(makers.CutoutFigure, "bent")
        elbow, wrist = (figure.at(bent()["r" + n]) for n in ("humerus", "radius"))
        length, (ux, uy) = math.dist(elbow, wrist), ((wrist[0] - elbow[0]), (wrist[1] - elbow[1]))
        on = []
        for x, y in opaque(img):
            if img.getpixel((x, y))[:3] != q565(STRIPE):
                continue
            dx, dy = x + 0.5 - elbow[0], y + 0.5 - elbow[1]
            ahead, across = (dx * ux + dy * uy) / length, abs(dx * uy - dy * ux) / length
            if 0.3 * length <= ahead <= 0.9 * length and across <= figure.FORE[0] * figure.PX / 2 + 1:
                on.append((x + 0.5, y + 0.5))
        self.assertGreaterEqual(len(on), 4)
        middle = (sum(x for x, _ in on) / len(on), sum(y for _, y in on) / len(on))
        self.assertLessEqual(math.dist(middle, along(elbow, wrist, 0.62)), 2)

    def test_a_limb_part_is_cut_to_a_capsule_round_its_bone(self):
        """At its upright angle, a limb part's picture is along its bone no longer than the bone and two of the
        capsule's half widths, and across it no wider than two; and it covers its bone."""
        figure = made(makers.CutoutFigure, "bent")[0]
        atlas = figure.atlas
        for kind in makers.LIMBS:
            for far in (True, False):
                with self.subTest(kind=kind, far=far):
                    picture = atlas.picture(atlas.key(kind, far, makers.UPRIGHT[kind]))
                    w, h = picture.image.size
                    along_, across = (w, h) if makers.UPRIGHT[kind] == 0 else (h, w)
                    bone_px, half = math.dist(picture.pivot, picture.end), atlas.CAPSULE[kind] * figure.PX
                    self.assertGreaterEqual(along_, bone_px)
                    self.assertLessEqual(along_, bone_px + 2 * half + 2)
                    self.assertLessEqual(across, 2 * half + 2)


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


class StandAtlas:
    """A stand-in for Atlas: a plain picture for any key, of the kind's width; fill() adds two."""

    ANGLES = 32

    def __init__(self):
        self.pictures = {("thigh", False, k): self.picture(("thigh", False, k)) for k in range(3)}

    def key(self, kind, far, degrees):
        return (kind, far, 0)

    def picture(self, key):
        return makers.PartPicture(Image.new("RGBA", (3 + len(key[0]), 9), (90, 90, 90, 255)), (0, 0), (0, 0))

    def bytes(self):
        return sum(p.image.width * p.image.height * 2 for p in self.pictures.values())

    def fill(self):
        for k in (3, 4):
            self.pictures["shin", True, k] = self.picture(("shin", True, k))


class StandCutout:
    """A stand-in for CutoutFigure: its atlas, fifteen parts a pose, and an end that misses by a quarter of the pose's
    index."""

    def __init__(self):
        self.atlas = StandAtlas()

    def placed(self, pose):
        return [None] * 15

    def misses(self, pose):
        return [0.5, pose["j0"][0] / 4]


def stand_runs():
    return {"whole": StandRun((200, 0), (30, 50), 12), "flat": StandRun((0, 200), (28, 48), 10),
            "cutout": StandRun((0, 0), (34, 52), 15, StandCutout())}


class MakerSheetTest(unittest.TestCase):
    """MakerSheet on stand-in runs of three sizes and a stand-in atlas."""

    def test_a_row_of_twelve_poses_per_maker_then_pose_3_by_each_then_the_parts_and_the_thigh(self):
        runs = stand_runs()
        rows = makers.MakerSheet(runs).rows()
        self.assertEqual(6, len(rows))
        gap, zoom, parts = detailed.GAP, makers.MakerSheet.ZOOM, makers.MakerSheet.PARTS_ZOOM
        for (name, run), (label, img) in zip(runs.items(), rows):
            with self.subTest(maker=name):
                self.assertTrue(label.startswith(name))
                self.assertEqual(12 * run.size[0] + 13 * gap, img.width)
        self.assertEqual((sum(run.size[0] for run in runs.values()) + 4 * gap) * zoom, rows[3][1].width)
        atlas = runs["cutout"].painter.atlas
        widths = [atlas.picture(atlas.key(kind, far, makers.UPRIGHT[kind])).image.width for kind, far in makers.PARTS]
        self.assertEqual((sum(widths) + (len(widths) + 1) * gap) * parts, rows[4][1].width)
        self.assertEqual(((3 + len("thigh")) * 8 + 9 * gap) * parts, rows[5][1].width)


class MakerClipTest(unittest.TestCase):
    """MakerClip on stand-in runs of three sizes and pivots over a plain street."""

    def test_twelve_frames_of_three_panels_of_one_size_each_pivot_at_one_place(self):
        runs = stand_runs()
        clip = makers.MakerClip(runs, Image.new("RGB", (detailed.CharacterClip.W, 240), (40, 40, 40)))
        frames, (pw, ph), zoom = clip.frames(), clip.panel, makers.MakerClip.ZOOM
        self.assertEqual(12, len(frames))
        self.assertEqual({(3 * pw * zoom, ph * zoom)}, {frame.size for frame in frames})
        x, y = makers.MakerClip.MARGIN + max(run.pivot[0] for run in runs.values()), ph - makers.MakerClip.MARGIN - 1
        for i in (0, 7):
            for k, run in enumerate(runs.values()):
                with self.subTest(frame=i, panel=k):
                    self.assertEqual((255, 255, 255), frames[i].getpixel(((k * pw + x) * zoom, y * zoom)))


class MakerCostsTest(unittest.TestCase):
    """maker_costs on stand-in runs: each number in a line is its source's."""

    def test_each_number_in_a_line_is_its_sources(self):
        runs = stand_runs()
        atlas = runs["cutout"].painter.atlas
        used = (len(atlas.pictures), atlas.bytes())
        lines = makers.maker_costs(runs)
        filled = (len(atlas.pictures), atlas.bytes())
        self.assertEqual(4, len(lines))
        whole, flat, cutout, miss = lines
        for part in ("24 pictures", "30 by 50 px", " %d bytes" % runs["whole"].size_bytes()):
            self.assertIn(part, whole)
        for part in ("12 poses", "7 joints", " %d bytes" % (12 * 7 * 4)):
            self.assertIn(part, flat)
        for part in (" %d part pictures, %d bytes" % used, " %d pictures, %d bytes" % filled, "15 parts",
                     " %d bytes" % (12 * 15 * 6), "mirrors"):
            self.assertIn(part, cutout)
        self.assertEqual((3, 5), (used[0], filled[0]))
        self.assertIn("2.75 px", miss)


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
