"""The detailed fireman (P904's spike, art/detailed.py): one number sets his size, he stands on the picture's last
row, he has a face, a helmet, gloves and a tank on his back, facing right or left, and his edge is one of three
rims. The other characters of CAST: each field of the record shows, skin is where the record says and has no band,
and characters.webp's clip. On a standing pose written here, so these hold without the CMU files. And,
only when the CMU files are downloaded, the run poses painted from them. Run from the repository root:
python3 -m unittest discover tests."""

import dataclasses
import functools
import hashlib
import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names

import detailed  # noqa: E402
import mocap  # noqa: E402
from brush import rnd  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402
from sets.rescue import COOL, STRIPE, WARM  # noqa: E402

SIDES = {"r": 0.05, "l": -0.05}  # each side's depth toward the viewer, in body heights


def standing():
    """A person standing upright, facing right, the arms hanging: joint name to (forward, up, near) in body heights,
    as art/mocap.py gives a pose."""
    pose = {"head": (0.0, 1.0, 0.0), "nose": (0.1, 1.0, 0.0), "upperneck": (0.0, 0.935, 0.0),
            "lowerneck": (0.0, 0.87, 0.0), "thorax": (0.0, 0.8, 0.0), "upperback": (0.0, 0.72, 0.0),
            "lowerback": (0.0, 0.63, 0.0), "root": (0.0, 0.58, 0.0)}
    for side, near in SIDES.items():
        for joint, (forward, up) in (("hipjoint", (0.0, 0.55)), ("femur", (0.0, 0.3)), ("tibia", (0.0, 0.05)),
                                     ("foot", (0.07, 0.01)), ("toes", (0.11, 0.0)), ("clavicle", (0.0, 0.85)),
                                     ("humerus", (0.0, 0.68)), ("radius", (0.03, 0.52)), ("wrist", (0.04, 0.47)),
                                     ("hand", (0.045, 0.45)), ("fingers", (0.05, 0.43)), ("thumb", (0.055, 0.455))):
            pose[side + joint] = (forward, up, near * 2 if joint in ("clavicle", "humerus", "radius") else near)
    return pose


def facing_left():
    """The standing pose mirrored: every joint's forward negated."""
    return {n: (-f, u, d) for n, (f, u, d) in standing().items()}


def painted(height, pose=None, rim=None, seed=1):
    rnd.seed(seed)
    figure = detailed.DetailedFigure(detailed.box(height), height, rim or detailed.NoRim())
    return figure, figure.paint(pose or standing())


def mean_x(pixels):
    return sum(x for x, _ in pixels) / len(pixels)


def opaque_rows(img):
    a = img.getchannel("A")
    return [y for y in range(img.height) if any(a.getpixel((x, y)) for x in range(img.width))]


def coloured(img, colour, within=40):
    """The opaque pixels close to colour: (x, y) each."""
    return [(x, y) for y in range(img.height) for x in range(img.width)
            if img.getpixel((x, y))[3] and sum(abs(a - b) for a, b in zip(img.getpixel((x, y)), colour)) < within]


def drawn(character, pose=None, seed=1):
    """A character of detailed.CAST, or one made with dataclasses.replace, at 96 px with no rim."""
    rnd.seed(seed)
    figure = detailed.DetailedFigure(detailed.box(detailed.TALL), detailed.TALL, detailed.NoRim(), character)
    return figure, figure.paint(pose or standing())


def other(value):
    """Another value of a record's field: a colour turned round, a colour for none, a share or a size moved, a
    yes for a no, the other headwear, the gear without its last part or with a tank."""
    if isinstance(value, bool):
        return not value
    if value is None:
        return (128, 64, 200)
    if isinstance(value, (int, float)):
        return value * 0.75 if value else 0.5
    if isinstance(value, tuple) and value and isinstance(value[0], int):
        return tuple(255 - c for c in value)
    if isinstance(value, tuple):
        return value[:-1] if value else (detailed.Tank(),)
    if isinstance(value, detailed.Proportions):
        return detailed.Proportions(0.8, 0.9)
    return detailed.Hair((60, 40, 30), 1.0) if isinstance(value, detailed.Helmet) else detailed.Helmet()


def bytes_of(img):
    return hashlib.sha256(img.tobytes()).hexdigest()[:16]


def changed_by(img, other_img):
    """The pixels that differ between two pictures of one size: (x, y) each."""
    return [(x, y) for y in range(img.height) for x in range(img.width)
            if img.getpixel((x, y)) != other_img.getpixel((x, y))]


@functools.lru_cache(maxsize=None)
def base(character):
    """drawn(character) on the standing pose, painted once for all the tests that read it."""
    return drawn(character)


@functools.lru_cache(maxsize=None)
def cast_runs():
    """The capture and every runner of detailed.CAST painted from the CMU files, once for all the tests that read
    them; None without the files."""
    capture = mocap.Capture()
    if capture.missing():
        return None
    return capture, [detailed.RunPictures(capture, detailed.TALL, character=c, cycle_name=name)
                     for c, name in detailed.CAST]


def far_leg_back(pose):
    """The pose with the far (left) leg from the knee down a step back, so both shins show."""
    out = dict(pose)
    for joint in ("femur", "tibia", "foot", "toes"):
        f, u, d = out["l" + joint]
        out["l" + joint] = (f - (0.06 if joint == "femur" else 0.14), u, d)
    return out


class StandingFigureTest(unittest.TestCase):
    """On the pose above: no CMU file is read."""

    def test_the_height_is_the_one_number_from_the_soles_to_the_helmets_top(self):
        for height in (detailed.TALL, 48):
            with self.subTest(height=height):
                rows = opaque_rows(painted(height)[1])
                self.assertLessEqual(abs(len(rows) - height), 1)

    def test_the_soles_stand_on_the_pictures_last_row(self):
        for height in (detailed.TALL, 48):
            with self.subTest(height=height):
                img = painted(height)[1]
                self.assertEqual(img.height - 1, opaque_rows(img)[-1])

    def test_the_head_has_a_face(self):
        figure, img = painted(detailed.TALL)
        hx, hy = figure.at(standing()["head"])
        r = figure.HEAD * figure.PX
        skin = coloured(img, detailed.SKIN)
        self.assertGreaterEqual(len(skin), 12)
        for x, y in skin:
            with self.subTest(x=x, y=y):
                self.assertLessEqual(abs(x - hx), 2 * r)
                self.assertLessEqual(abs(y - hy), 2.5 * r)

    def test_the_eye_is_on_the_side_the_nose_is_facing_right_and_left(self):
        for pose, ahead in ((standing(), 1), (facing_left(), -1)):
            with self.subTest(ahead=ahead):
                figure, img = painted(detailed.TALL, pose)
                hx, hy = figure.at(pose["head"])
                r = figure.HEAD * figure.PX
                eyes = [q for q in coloured(img, detailed.EYE, 60) if abs(q[0] - hx) <= r and abs(q[1] - hy) <= r]
                self.assertTrue(eyes)
                self.assertGreater((mean_x(eyes) - hx) * ahead, 0)

    def test_the_helmet_is_over_the_head(self):
        figure, img = painted(detailed.TALL)
        _, hy = figure.at(standing()["head"])
        helmet = coloured(img, detailed.HELMET, 60)
        self.assertGreaterEqual(len(helmet), 30)
        self.assertLess(sum(y for _, y in helmet) / len(helmet), hy)

    def test_the_tank_is_on_his_back_facing_right_and_left(self):
        for pose, ahead in ((standing(), 1), (facing_left(), -1)):
            with self.subTest(ahead=ahead):
                figure, img = painted(detailed.TALL, pose)
                spine_x, _ = figure.at(pose["upperback"])
                tank = coloured(img, detailed.TANK)
                self.assertGreaterEqual(len(tank), 12)
                self.assertLess((mean_x(tank) - spine_x) * ahead, 0)

    def test_each_reflective_band_is_on_its_part(self):
        """Between these heights of the standing pose, in body heights, only that part's band is."""
        figure, img = painted(detailed.TALL)
        stripes = coloured(img, STRIPE, 1)
        for part, (low, high) in (("the coat's chest", (0.72, 0.8)), ("the sleeve", (0.555, 0.61)),
                                  ("the coat's hem", (0.43, 0.5)), ("the shin", (0.15, 0.24))):
            with self.subTest(part=part):
                top, bottom = figure.at((0, high, 0))[1], figure.at((0, low, 0))[1]
                self.assertGreaterEqual(len([q for q in stripes if top <= q[1] <= bottom]), 4)

    def test_a_glove_is_at_the_end_of_the_arm_and_not_above_the_wrist(self):
        figure, img = painted(detailed.TALL)
        _, wrist_row = figure.at(standing()["rradius"])
        gloves = coloured(img, detailed.GLOVE, 24)
        self.assertGreaterEqual(len(gloves), 12)
        self.assertGreaterEqual(min(y for _, y in gloves), wrist_row - figure.GLOVE_W * figure.PX)

    def test_the_same_seed_paints_the_same_bytes(self):
        self.assertEqual(painted(detailed.TALL)[1].tobytes(), painted(detailed.TALL)[1].tobytes())


class RimTest(unittest.TestCase):
    """The figure's edge, one of detailed.RIMS, on the standing pose."""

    @classmethod
    def setUpClass(cls):
        cls.bare = painted(detailed.TALL)[1]
        cls.shape = cls.bare.getchannel("A")

    def added(self, img):
        """The pixels a rim painted: opaque now, and not in the bare shape."""
        return [(x, y) for y in range(img.height) for x in range(img.width)
                if img.getpixel((x, y))[3] and not self.shape.getpixel((x, y))]

    def touches(self, x, y, sides):
        w, h = self.shape.size
        return any(0 <= x + dx < w and 0 <= y + dy < h and self.shape.getpixel((x + dx, y + dy)) for dx, dy in sides)

    def test_the_names_and_the_default(self):
        self.assertEqual(["outline", "none", "lit"], list(detailed.RIMS))
        self.assertIsInstance(detailed.DetailedFigure(detailed.box(48), 48).edge, detailed.Outline)

    def test_no_rim_leaves_the_shape(self):
        self.assertEqual([], self.added(painted(detailed.TALL, rim=detailed.NoRim())[1]))

    def test_the_outline_is_one_dark_px_all_round_and_changes_nothing_inside(self):
        img = painted(detailed.TALL, rim=detailed.Outline())[1]
        added = self.added(img)
        w, h = img.size
        edge = [(x, y) for y in range(h) for x in range(w)
                if not self.shape.getpixel((x, y)) and self.touches(x, y, ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        self.assertEqual(edge, added)
        for x, y in added:
            with self.subTest(x=x, y=y):
                self.assertLess(max(img.getpixel((x, y))[:3]), 100)
        inside = [(x, y) for y in range(h) for x in range(w) if self.shape.getpixel((x, y))]
        self.assertEqual([self.bare.getpixel(q) for q in inside], [img.getpixel(q) for q in inside])

    def test_the_outline_adds_one_row_over_the_helmet_and_none_under_the_soles(self):
        img = painted(detailed.TALL, rim=detailed.Outline())[1]
        bare, outlined = opaque_rows(self.bare), opaque_rows(img)
        self.assertEqual((bare[0] - 1, bare[-1]), (outlined[0], outlined[-1]))

    def test_the_lit_rim_is_left_and_right_of_the_shape_only(self):
        added = self.added(painted(detailed.TALL, rim=detailed.LitRim())[1])
        self.assertTrue(added)
        for x, y in added:
            with self.subTest(x=x, y=y):
                self.assertTrue(self.touches(x, y, ((1, 0), (-1, 0))))

    def test_the_lit_rim_is_warm_on_the_side_he_faces_and_cool_behind(self):
        for pose, ahead in ((standing(), WARM), (facing_left(), COOL)):
            with self.subTest(right_of_the_shape=ahead):
                shape = painted(detailed.TALL, pose)[1].getchannel("A")
                img = painted(detailed.TALL, pose, detailed.LitRim())[1]
                right = [img.getpixel((x, y))[:3] for y in range(img.height) for x in range(1, img.width)
                         if not shape.getpixel((x, y)) and shape.getpixel((x - 1, y))]
                self.assertEqual({ahead}, set(right))


class ClipTest(unittest.TestCase):
    """A written clip holds every frame as it was painted: no palette stands between the picture and the file."""

    def test_a_written_clip_reads_back_as_the_same_frames_at_the_same_pace(self):
        street = detailed.Committed().street
        figure = detailed.q565(painted(detailed.TALL, rim=detailed.Outline())[1])
        with_figure = street.copy()
        with_figure.paste(figure, (120, detailed.FEET - figure.height + 1), figure)
        frames = [street, with_figure, street]
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "clip.webp")
            detailed.write_clip(frames, path, 40)
            with Image.open(path) as clip:
                count, read = clip.n_frames, []
                for i in range(count):
                    clip.seek(i)
                    frame = clip.convert("RGB").tobytes()  # the frame's duration is known once it is loaded
                    read.append((clip.info["duration"], frame))
        self.assertEqual(3, count)
        self.assertEqual([(40, frame.tobytes()) for frame in frames], read)


class PoseIndexTest(unittest.TestCase):
    """The pose a run of so many px shows, as games/rescue.py picks it."""

    def test_a_stride_of_px_walks_through_every_pose_once_and_starts_again(self):
        stride, poses = 151, 12
        indexes = [detailed.pose_index(ran, stride, poses) for ran in range(stride)]
        self.assertEqual(sorted(indexes), indexes)
        self.assertEqual(list(range(poses)), sorted(set(indexes)))
        self.assertEqual((0, 0, 11), (detailed.pose_index(stride, stride, poses), detailed.pose_index(0, stride, poses),
                                      detailed.pose_index(stride - 1, stride, poses)))

    def test_it_is_the_games_formula(self):
        sys.path.insert(0, os.path.join(REPO, "tests", "stubs"))
        sys.path.insert(0, os.path.join(REPO, "games"))
        import rescue as game  # noqa: E402  games/rescue.py
        for ran in (0, 7, 40, 41, 100):
            with self.subTest(ran=ran):
                self.assertEqual(ran * game.RUN_POSES // game.STRIDE_PX % game.RUN_POSES,
                                 detailed.pose_index(ran, game.STRIDE_PX, game.RUN_POSES))
        self.assertEqual((game.RUN_POSES, game.STRIDE_PX, game.SPEED_PX_S),
                         (detailed.Committed.RUN_POSES, detailed.Committed.STRIDE_PX, detailed.Committed.SPEED_PX_S))


class RunFromCaptureTest(unittest.TestCase):
    """The twelve run poses, painted from the CMU files: skipped without them, and a skip is not a pass."""

    @classmethod
    def setUpClass(cls):
        if cast_runs() is None:
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.captured = next(run for run in cast_runs()[1] if run.character == detailed.FIREMAN)

    def test_twelve_poses_and_none_is_empty(self):
        self.assertEqual(12, len(self.captured.pictures))
        for i, img in enumerate(self.captured.pictures):
            with self.subTest(pose=i):
                self.assertTrue(opaque_rows(img))

    def test_every_pose_has_the_one_box_and_no_column_or_top_row_of_it_is_unused(self):
        w, h = self.captured.size
        self.assertEqual({(w, h)}, {img.size for img in self.captured.pictures})
        used = [img.getchannel("A").getbbox() for img in self.captured.pictures]
        self.assertEqual((0, 0, w), (min(b[0] for b in used), min(b[1] for b in used), max(b[2] for b in used)))

    def test_the_lowest_pose_stands_on_the_last_row_and_a_flight_lifts_no_pose_by_a_tenth(self):
        h = self.captured.size[1]
        lowest = [opaque_rows(img)[-1] for img in self.captured.pictures]
        self.assertEqual(h - 1, max(lowest))
        self.assertGreater(min(lowest), h - 1 - detailed.TALL // 10)

    def test_the_bytes_are_two_a_pixel_for_each_pose_and_both_facings(self):
        w, h = self.captured.size
        self.assertEqual(w * h * 2 * 12 * 2, self.captured.size_bytes())

    def test_the_stride_and_the_speed_are_the_26_px_firemans_at_this_height(self):
        """games/rescue.py: 41 px a cycle and 56 px a second at 24.07 px a body height."""
        px = detailed.DetailedFigure(detailed.box(detailed.TALL), detailed.TALL).PX
        self.assertIsInstance(self.captured.stride, int)
        self.assertLessEqual(abs(self.captured.stride / px - 41 / 24.07), 0.02)
        self.assertLessEqual(abs(self.captured.speed / px - 56 / 24.07), 0.03)

    def test_a_run_of_px_shows_the_pose_of_the_index(self):
        for ran in (0, self.captured.stride // 2, self.captured.stride - 1):
            with self.subTest(ran=ran):
                self.assertIs(self.captured.pictures[detailed.pose_index(ran, self.captured.stride, 12)],
                              self.captured.picture(ran))


class ProportionsTest(unittest.TestCase):
    """A pose fitted to shorter legs or arms, on the standing pose: its legs are 0.5 body heights long."""

    FEET = ("lfoot", "ltoes", "rfoot", "rtoes")

    def length(self, pose, a, b):
        return sum((q - p) ** 2 for p, q in zip(pose[a], pose[b])) ** 0.5

    def test_the_default_is_the_pose_itself(self):
        pose = standing()
        self.assertIs(pose, detailed.Proportions().fit(pose))

    def test_short_legs_keep_the_lowest_foot_joint_and_lower_the_head_by_their_loss(self):
        pose, fitted = standing(), detailed.Proportions(leg=0.8).fit(standing())
        for side in "lr":
            with self.subTest(side=side):
                self.assertAlmostEqual(0.8 * 0.5, self.length(fitted, side + "hipjoint", side + "tibia"))
                self.assertAlmostEqual(self.length(pose, side + "tibia", side + "toes"),
                                       self.length(fitted, side + "tibia", side + "toes"))
                self.assertAlmostEqual(self.length(pose, side + "clavicle", side + "radius"),
                                       self.length(fitted, side + "clavicle", side + "radius"))
        self.assertAlmostEqual(min(pose[n][1] for n in self.FEET), min(fitted[n][1] for n in self.FEET))
        self.assertAlmostEqual(1.0 - (1 - 0.8) * 0.5, fitted["head"][1])

    def test_short_arms_keep_the_hands_and_move_nothing_else(self):
        pose, fitted = standing(), detailed.Proportions(arm=0.88).fit(standing())
        for side in "lr":
            with self.subTest(side=side):
                self.assertAlmostEqual(0.88 * self.length(pose, side + "clavicle", side + "radius"),
                                       self.length(fitted, side + "clavicle", side + "radius"))
                for n in ("wrist", "hand", "fingers", "thumb"):
                    self.assertAlmostEqual(self.length(pose, side + "radius", side + n),
                                           self.length(fitted, side + "radius", side + n))
        for n in ("head", "lhipjoint", "rtoes"):
            self.assertEqual(pose[n], fitted[n])


class CharacterTest(unittest.TestCase):
    """Every character of detailed.CAST on the standing pose (no CMU file is read), and the fields of its record."""

    def each(self):
        for character, _ in detailed.CAST:
            with self.subTest(character=character.name):
                yield character

    def test_each_character_runs_its_cycle(self):
        self.assertEqual([("fireman", "run"), ("paramedic", "woman"), ("footballer", "dogman"), ("child", "child"),
                          ("officer", "man"), ("builder", "dogman"), ("chef", "man"), ("acrobat", "woman")],
                         [(c.name, name) for c, name in detailed.CAST])

    def test_the_fireman_is_the_records_defaults_and_the_first_of_the_cast(self):
        self.assertEqual(detailed.Character(), detailed.FIREMAN)
        self.assertEqual((detailed.FIREMAN, "run"), detailed.CAST[0])
        self.assertEqual(painted(detailed.TALL)[1].tobytes(), drawn(detailed.FIREMAN)[1].tobytes())

    def test_from_the_soles_on_the_last_row_to_the_head_joint(self):
        """(head + SOLE) x PX - 1 px, PX from the height and the scale alone, head the head joint's height: 1 less
        what the legs lose, (1 - leg) x 0.5 on the standing pose. The picture's top row, the headwear's top, is 1 to
        1.4 head radii over that joint; a toque's, its height in head radii within 1 px."""
        for c in self.each():
            figure, img = base(c)
            px = detailed.TALL * c.scale / (1 + detailed.HELMET_TOP + figure.SOLE)
            head = 1 - (1 - c.proportions.leg) * 0.5
            rows = opaque_rows(img)
            self.assertEqual(img.height - 1, rows[-1])
            joint = rows[-1] - ((head + figure.SOLE) * px - 1)  # the head joint's row, from the soles' row
            r = c.head * px
            if isinstance(c.headwear, detailed.Toque):
                self.assertLessEqual(abs(joint - rows[0] - c.headwear.height * r), 1)
                continue
            self.assertLessEqual(r - 1, joint - rows[0])
            self.assertLessEqual(joint - rows[0], 1.4 * r + 1)

    def test_each_field_of_the_record_and_of_its_parts_changes_the_picture(self):
        """The record's fields on the fireman; each part's fields, and the gear without it, on the first character of
        the cast that wears it."""
        c = detailed.FIREMAN
        changed = [(c, f.name, dataclasses.replace(c, **{f.name: other(getattr(c, f.name))}))
                   for f in dataclasses.fields(c) if f.name != "name"]
        seen = set()
        for c, _ in detailed.CAST:
            for k, part in enumerate((c.headwear, c.proportions) + c.gear):
                if type(part) in seen:
                    continue
                seen.add(type(part))
                for f in dataclasses.fields(part):
                    moved = dataclasses.replace(part, **{f.name: other(getattr(part, f.name))})
                    worn = (dataclasses.replace(c, headwear=moved) if k == 0 else
                            dataclasses.replace(c, proportions=moved) if k == 1 else
                            dataclasses.replace(c, gear=c.gear[:k - 2] + (moved,) + c.gear[k - 1:]))
                    changed.append((c, "%s.%s" % (type(part).__name__, f.name), worn))
                if k > 1:
                    changed.append((c, "without %s" % type(part).__name__,
                                    dataclasses.replace(c, gear=c.gear[:k - 2] + c.gear[k - 1:])))
        self.assertTrue({detailed.Helmet, detailed.Hair, detailed.Proportions, detailed.Tank, detailed.Collar,
                         detailed.Strap, detailed.Belt, detailed.Bag, detailed.PeakedCap, detailed.Toque,
                         detailed.Apron} <= seen)
        for c, name, character in changed:
            with self.subTest(character=c.name, field=name):
                self.assertNotEqual(bytes_of(base(c)[1]), bytes_of(drawn(character)[1]))

    def test_facing_left_is_the_mirror_of_facing_right_in_shape_and_colour(self):
        """The shape: each pixel that one picture covers, the other covers within 1 px across (an odd line width at
        8x puts an edge that falls on a half pixel on one side only). The colour: of the pixels both cover, at least
        0.97 within 30 (the sum over the channels; the grain is not mirrored)."""
        for c in self.each():
            a, b = ImageOps.mirror(base(c)[1]), drawn(c, facing_left())[1]
            w, h = a.size

            def on(img, x, y):
                return 0 <= x < w and img.getpixel((x, y))[3] > 0

            cover = [(x, y) for y in range(h) for x in range(w) if on(a, x, y) or on(b, x, y)]
            shape = [q for q in cover if all(any(on(o, q[0] + d, q[1]) for d in (-1, 0, 1))
                                             for i, o in ((a, b), (b, a)) if on(i, *q))]
            both = [q for q in cover if on(a, *q) and on(b, *q)]
            colour = [q for q in both if sum(abs(u - v) for u, v in zip(a.getpixel(q)[:3], b.getpixel(q)[:3])) <= 30]
            self.assertGreaterEqual(len(shape) / len(cover), 0.99)
            self.assertGreaterEqual(len(colour) / len(both), 0.97)

    def test_the_top_is_between_the_hips_and_the_neck_and_the_headwear_over_the_head_joint(self):
        """A part's pixels are those that its colour changes."""
        for c in self.each():
            figure, img = base(c)
            pose = c.proportions.fit(standing())
            top = changed_by(img, drawn(dataclasses.replace(c, top=other(c.top)))[1])
            self.assertGreaterEqual(len(top), 30)
            middle = sum(y for _, y in top) / len(top)
            self.assertLess(figure.at(pose["lowerneck"])[1], middle)
            self.assertLess(middle, figure.at(pose["rhipjoint"])[1])
            hat = dataclasses.replace(c.headwear, colour=other(c.headwear.colour))
            worn = changed_by(img, drawn(dataclasses.replace(c, headwear=hat))[1])
            self.assertGreaterEqual(len(worn), 12)
            self.assertLess(sum(y for _, y in worn) / len(worn), figure.at(pose["head"])[1])

    def test_a_sleeve_share_under_one_leaves_the_forearm_in_skin_down_to_3_px_above_the_wrist(self):
        for sleeve in (0.45, 1.0):
            with self.subTest(sleeve=sleeve):
                c = dataclasses.replace(detailed.FIREMAN, sleeve=sleeve)
                figure, img = drawn(c)
                elbow, wrist = (round(figure.at(standing()["r" + j])[1]) for j in ("humerus", "radius"))
                skin = {y for _, y in coloured(img, c.skin) if elbow + 3 <= y <= wrist - 3}
                if sleeve < 1:
                    self.assertLessEqual(set(range(elbow + 3, wrist - 2)), skin)
                else:
                    self.assertEqual(set(), skin)

    def test_a_trouser_share_under_one_leaves_the_knee_in_skin(self):
        for trouser in (0.5, 1.0):
            with self.subTest(trouser=trouser):
                c = dataclasses.replace(detailed.FIREMAN, trouser=trouser)
                figure, img = drawn(c)
                knee = round(figure.at(standing()["rfemur"])[1])
                skin = [q for q in coloured(img, c.skin) if abs(q[1] - knee) <= 2]
                self.assertEqual(trouser < 1, bool(skin))

    def test_bare_hands_are_skin_below_the_wrist_and_gloves_are_not(self):
        for hands in (None, detailed.GLOVE):
            with self.subTest(hands=hands):
                c = dataclasses.replace(detailed.FIREMAN, hands=hands)
                figure, img = drawn(c)
                wrist = figure.at(standing()["rradius"])[1]
                skin = [q for q in coloured(img, c.skin) if q[1] > wrist + 1]
                self.assertEqual(hands is None, len(skin) >= 8)

    def test_a_shoe_has_no_shaft(self):
        """With shaft None and bare shins (the child), the boots' colour changes no pixel above the shoe, and the near
        shin is skin in every row from where a shaft would start down to the shoe."""
        c = detailed.CHILD
        self.assertIsNone(c.shaft)
        self.assertLess(c.trouser, 1)
        figure, img = base(c)
        pose = c.proportions.fit(standing())
        knee, ankle = figure.at(pose["rfemur"]), figure.at(pose["rtibia"])
        shoe = ankle[1] - figure.FOOT_W * figure.PX / 2
        changed = changed_by(img, drawn(dataclasses.replace(c, boots=other(c.boots)))[1])
        self.assertGreaterEqual(len(changed), 12)
        self.assertGreater(min(y for _, y in changed), shoe - 1)
        skin = {y for x, y in coloured(img, c.skin) if abs(x - ankle[0]) <= figure.SHIN[0] * figure.PX}
        top = round(knee[1] + (ankle[1] - knee[1]) * 0.62)
        self.assertLessEqual(set(range(top, int(shoe) - 1)), skin)

    def test_a_bare_hand_has_no_cuff(self):
        """The cuff is the glove's colour at 0.6: a bare hand has no pixel of the skin's at 0.6 at its wrist."""
        for hands in (None, detailed.GLOVE):
            with self.subTest(hands=hands):
                c = dataclasses.replace(detailed.FIREMAN, hands=hands)
                figure, img = drawn(c)
                wrist = figure.at(standing()["rradius"])[1]
                cuff = [q for q in coloured(img, detailed.darker(hands or c.skin, 0.6), 24) if abs(q[1] - wrist) <= 3]
                self.assertEqual(hands is not None, len(cuff) >= 3)

    def test_only_the_near_shin_has_a_band(self):
        """With the far leg a step back, both shins show: every band pixel on the shins' rows is on the near one."""
        figure, banded = drawn(detailed.FIREMAN, far_leg_back(standing()))
        plain = drawn(dataclasses.replace(detailed.FIREMAN, bands=False), far_leg_back(standing()))[1]
        top, bottom = figure.at((0, 0.24, 0))[1], figure.at((0, 0.1, 0))[1]
        near = figure.at(standing()["rtibia"])[0]
        shins = [(x, y) for x, y in changed_by(banded, plain) if top <= y <= bottom]
        self.assertGreaterEqual(len(shins), 4)
        self.assertLessEqual(max(abs(x - near) for x, _ in shins), figure.SHIN[0] * figure.PX)

    def test_no_reflective_band_is_on_skin(self):
        """A band pixel is one that the bands change; under it, with no bands, there is no skin. Also with short
        sleeves, short trousers and bare hands, where the bands would lie on bare skin."""
        bare = dataclasses.replace(detailed.FIREMAN, sleeve=0.45, trouser=0.5, hands=None)
        for c in list(self.each()) + [bare]:
            with self.subTest(bare=c is bare):
                banded = drawn(dataclasses.replace(c, bands=True))[1]
                plain = drawn(dataclasses.replace(c, bands=False))[1]
                bands = changed_by(banded, plain)
                self.assertGreaterEqual(len(bands), 8)
                skin = set(changed_by(plain, drawn(dataclasses.replace(c, bands=False, skin=other(c.skin)))[1]))
                near = (c.skin, detailed.shade(c.skin))  # and mostly skin: not a pixel at a skin part's edge
                on_skin = [q for q in bands if q in skin and any(
                    sum(abs(a - b) for a, b in zip(plain.getpixel(q), s)) < 40 for s in near)]
                self.assertEqual([], on_skin)

    def test_the_childs_head_is_wider_for_its_height_than_the_firemans(self):
        share = {}
        for c in (detailed.FIREMAN, detailed.CHILD):
            figure, img = base(c)
            hy = figure.at(c.proportions.fit(standing())["head"])[1]
            xs = [x for x, y in coloured(img, c.skin) if abs(y - hy) <= 2]
            rows = opaque_rows(img)
            share[c.name] = (max(xs) - min(xs) + 1) / (rows[-1] - rows[0] + 1)
        self.assertGreater(share["child"], share["fireman"] * 1.1)


class NewPartsTest(unittest.TestCase):
    """The parts of the second four characters on the standing pose, facing right and left: a part's pixels are those
    that one of its fields changes."""

    FACINGS = ((standing, 1), (facing_left, -1))

    def changed(self, c, moved, pose):
        """The figure, and the pixels that differ between c and moved on the pose."""
        figure, img = drawn(c, pose())
        return figure, changed_by(img, drawn(moved, pose())[1])

    def worn_on_the_head(self, c, pose, **fields):
        """The figure, and the pixels that these fields of the headwear change."""
        return self.changed(c, dataclasses.replace(c, headwear=dataclasses.replace(c.headwear, **fields)), pose)

    def worn_first(self, c, pose, **fields):
        """The figure, and the pixels that these fields of the first gear part change."""
        return self.changed(c, dataclasses.replace(c, gear=(dataclasses.replace(c.gear[0], **fields),) + c.gear[1:]),
                            pose)

    def test_the_peaked_caps_peak_is_on_the_side_the_nose_is(self):
        for pose, ahead in self.FACINGS:
            with self.subTest(ahead=ahead):
                cap = detailed.OFFICER.headwear
                figure, peak = self.worn_on_the_head(detailed.OFFICER, pose, peak=0.0)
                self.assertGreaterEqual(len(peak), 3)
                r = figure.HEAD * figure.PX  # the peak: from 0.9 head radii ahead to 0.9 + its length, over the crown
                ahead_of_head = (mean_x(peak) - figure.at(pose()["head"])[0]) * ahead
                self.assertGreater(ahead_of_head, (0.5 + cap.peak / 4) * r)

    def test_the_bun_is_behind_the_head(self):
        for pose, ahead in self.FACINGS:
            with self.subTest(ahead=ahead):
                figure, bun = self.worn_on_the_head(detailed.ACROBAT, pose, bun=0.35)  # a part still: the grain stays
                self.assertGreaterEqual(len(bun), 6)
                self.assertLess((mean_x(bun) - figure.at(pose()["head"])[0]) * ahead, 0)

    def test_the_apron_is_in_front_of_the_body_from_the_chest_to_the_knees(self):
        """Over the body it shows 218 px standing, either way; painted under the body only the 70 below the jacket's
        hem would show: at least 150 tell the two apart."""
        for pose, ahead in self.FACINGS:
            with self.subTest(ahead=ahead):
                c = detailed.CHEF
                figure, apron = self.worn_first(c, pose, colour=other(c.gear[0].colour))
                fitted = c.proportions.fit(pose())
                self.assertGreaterEqual(len(apron), 150)
                self.assertGreater((mean_x(apron) - figure.at(fitted["root"])[0]) * ahead, 0)
                chest, knee = figure.at(fitted["upperback"])[1], figure.at(fitted["rfemur"])[1]
                self.assertGreaterEqual(min(y for _, y in apron), chest - 1)
                self.assertLessEqual(max(y for _, y in apron), knee + 1)

    def test_the_builders_hard_hat_has_no_shield_and_no_flap(self):
        """No pixel near the shield's colour on his head; and nothing more than 1.25 head radii behind the head from
        0.4 to 1.3 head radii under the head joint, where only a neck flap reaches (under the brim's tail, over his
        vest's back)."""
        c = detailed.BUILDER
        figure, img = base(c)
        (hx, hy), r = figure.at(standing()["head"]), c.head * figure.PX
        self.assertEqual([], [q for q in coloured(img, detailed.SHIELD, 40) if abs(q[1] - hy) <= 2 * r])
        behind = [(x, y) for y in range(round(hy + 0.4 * r), round(hy + 1.3 * r)) for x in range(img.width)
                  if img.getpixel((x, y))[3] and x < hx - 1.25 * r]
        self.assertEqual([], behind)

    def test_the_toque_rises_higher_over_the_head_joint_than_the_helmet(self):
        tops = {c.name: opaque_rows(base(c)[1])[0] - base(c)[0].at(c.proportions.fit(standing())["head"])[1]
                for c in (detailed.FIREMAN, detailed.CHEF)}
        self.assertLess(tops["chef"], tops["fireman"] - detailed.FIREMAN.head * base(detailed.FIREMAN)[0].PX)

    def test_the_officer_has_a_belt_and_nothing_of_his_gear_crosses_his_chest(self):
        c = detailed.OFFICER
        figure, img = base(c)
        self.assertIsInstance(c.gear[0], detailed.Belt)
        gear = changed_by(img, drawn(dataclasses.replace(c, gear=()))[1])
        self.assertGreaterEqual(len(gear), 6)
        self.assertGreater(min(y for _, y in gear), figure.at(standing()["upperback"])[1])


class Stand:
    """A stand-in for RunPictures: one plain picture a facing, so CharacterClip is tested with no CMU file."""

    def __init__(self, colour, speed, size=(10, 20), stride=40):
        self.size, self.speed, self.stride = size, speed, stride
        self.pictures = [Image.new("RGBA", size, colour[:2] + (i * 20,) + (255,)) for i in range(12)]
        self.left = [Image.new("RGBA", size, tuple(255 - c for c in colour[:2]) + (i * 20,) + (255,))
                     for i in range(12)]

    def picture(self, ran, left=False):
        return (self.left if left else self.pictures)[detailed.pose_index(ran, self.stride, 12)]


class CharacterClipTest(unittest.TestCase):
    """characters.webp's frames on stand-in pictures: rows, facings, speeds and the paste order."""

    def setUp(self):
        self.runners = [Stand((200, 0, 0), 50), Stand((0, 200, 0), 80), Stand((0, 0, 200), 120)]
        self.street = Image.new("RGB", (detailed.CharacterClip.W, 240), (0, 0, 0))
        self.clip = detailed.CharacterClip(self.runners, self.street)

    def test_each_runner_has_a_row_from_200_to_238_and_every_second_runs_left(self):
        self.assertEqual([200, 219, 238], self.clip.rows)
        self.assertEqual([False, True, False], self.clip.runs_left)

    def test_the_runners_are_pasted_in_the_order_of_their_rows(self):
        places = self.clip.places(0)
        self.assertEqual(sorted(p[1] for p in places), [p[1] for p in places])

    def test_a_runner_shows_the_pose_of_its_place_in_the_lap_facing_its_way(self):
        """The place in the lap: x + width going right, W - x going left. The pose follows it, so the feet keep
        still."""
        for i in (0, 5, 40):
            for k, (x, y, img) in zip((0, 1, 2), self.clip.places(i)):
                with self.subTest(frame=i, runner=k):
                    left, w = self.clip.runs_left[k], self.runners[k].size[0]
                    self.assertIs(img, self.runners[k].picture(detailed.CharacterClip.W - x if left else x + w, left))

    def test_every_runner_shows_its_first_pose_when_the_clip_starts_again(self):
        for k, (start, end) in enumerate(zip(self.clip.places(0), self.clip.places(self.clip.count))):
            with self.subTest(runner=k):
                self.assertIs(start[2], end[2])

    def test_a_runner_advances_so_many_px_in_so_many_frames(self):
        """10 frames of 40 ms: 20 px at 50 px a second to the right, 32 px at 80 px a second to the left."""
        clip = detailed.CharacterClip([Stand((200, 0, 0), 50, stride=100), Stand((0, 200, 0), 80, stride=100)],
                                      self.street)
        (a0, b0), (a1, b1) = ([p[0] for p in clip.places(i)] for i in (0, 10))
        self.assertEqual((20, -32), (a1 - a0, b1 - b0))

    def test_the_smaller_a_runner_the_farther_up_the_street_it_runs(self):
        runners = [Stand((200, 0, 0), 50, (10, 20)), Stand((0, 200, 0), 80, (10, 30)),
                   Stand((0, 0, 200), 120, (10, 10))]
        self.assertEqual([219, 238, 200], detailed.CharacterClip(runners, self.street).rows)

    def test_the_clip_lasts_as_long_as_the_slowest_runner_takes_to_cross_once(self):
        """330 px at 50 px a second, the second runner, in frames of 40 ms: 165 frames and the one that ends the
        crossing."""
        clip = detailed.CharacterClip([Stand((0, 200, 0), 80), Stand((200, 0, 0), 50), Stand((0, 0, 200), 120)],
                                      self.street)
        self.assertEqual(166, len(clip.frames()))

    def test_a_run_of_no_whole_number_of_laps_goes_round_fewer_longer_laps(self):
        """At 105 px a second over 166 frames a runner runs 697 px: two laps of 330 px or more do not fill it, so it
        goes round one lap of 697 px and is back at its start when the clip starts again."""
        runners = [Stand((0, 200, 0), 80), Stand((200, 0, 0), 50), Stand((0, 0, 200), 105)]
        clip = detailed.CharacterClip(runners, self.street)
        self.assertEqual(697, clip.laps[2])
        self.assertEqual([p[:2] for p in clip.places(0)], [p[:2] for p in clip.places(clip.count)])

    def test_every_runner_is_at_its_start_place_when_the_clip_starts_again(self):
        start, end = self.clip.places(0), self.clip.places(self.clip.count)
        self.assertEqual([p[:2] for p in start], [p[:2] for p in end])
        for k, run in enumerate(self.runners):
            with self.subTest(runner=k):
                self.assertGreaterEqual(self.clip.laps[k], detailed.CharacterClip.W + run.size[0])

    def test_a_frame_is_the_street_with_each_runner_pasted_at_its_place(self):
        frames = self.clip.frames()
        self.assertGreater(len(frames), 1)
        for x, row, img in self.clip.places(3):
            h = img.height
            if 0 <= x and x + img.width <= detailed.CharacterClip.W:
                with self.subTest(row=row):
                    self.assertEqual(img.getpixel((0, h - 1))[:3], frames[3].getpixel((x, row)))


class CastFromCaptureTest(unittest.TestCase):
    """Every runner of detailed.CAST painted from the CMU files: skipped without them, and a skip is not a pass."""

    @classmethod
    def setUpClass(cls):
        if cast_runs() is None:
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.capture, cls.runners = cast_runs()

    def test_every_runners_lowest_pose_stands_on_the_last_row_and_no_pose_touches_its_boxs_left_right_or_top(self):
        """The chef's toque and the child's short legs among them: the poses' first column, top row and end column in
        the box the run paints in (RunPictures.used) are inside it."""
        for (c, _), run in zip(detailed.CAST, self.runners):
            with self.subTest(character=c.name):
                self.assertEqual(run.size[1] - 1, max(opaque_rows(img)[-1] for img in run.pictures))
                x0, y0, x1 = run.used
                self.assertTrue(x0 > 0 and y0 > 0 and x1 < detailed.box(detailed.TALL)[0])

    def test_the_stride_shrinks_with_the_legs(self):
        """So the feet keep still on the street: the capture's stride in px of the record's size, times its legs."""
        for (c, _), run in zip(detailed.CAST, self.runners):
            with self.subTest(character=c.name):
                px = detailed.TALL * c.scale / (1 + detailed.HELMET_TOP + detailed.DetailedFigure.SOLE)
                self.assertLessEqual(abs(run.stride - self.capture.stride(run.cycle) * px * c.proportions.leg), 0.5)

    def test_twelve_poses_in_one_box_and_each_left_picture_is_the_mirror(self):
        for (c, _), run in zip(detailed.CAST, self.runners):
            with self.subTest(character=c.name):
                self.assertEqual(12, len(run.pictures))
                self.assertEqual({run.size}, {img.size for img in run.pictures + run.left})
                for right, left in zip(run.pictures, run.left):
                    self.assertEqual(ImageOps.mirror(right).tobytes(), left.tobytes())

    def test_the_printed_total_is_the_sum_of_the_runs(self):
        lines = detailed.cast_bytes(self.runners)
        self.assertEqual(len(self.runners) + 1, len(lines))
        self.assertIn(" %d bytes" % sum(run.size_bytes() for run in self.runners), lines[-1])
        for (c, _), run, line in zip(detailed.CAST, self.runners, lines):
            with self.subTest(character=c.name):
                self.assertIn(c.name, line)
                self.assertIn(" %d bytes" % run.size_bytes(), line)


if __name__ == "__main__":
    unittest.main()
