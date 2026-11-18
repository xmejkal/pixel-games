"""The detailed fireman (P904's spike, art/detailed.py): one number sets his size, he stands on the picture's last
row, he has a face, a helmet, gloves and a tank on his back, facing right or left, and his edge is one of three
rims. On a standing pose written here, so these hold without the CMU files. And, only when the CMU files are
downloaded, the twelve run poses painted from them. Run from the repository root:
python3 -m unittest discover tests."""

import dataclasses
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
    return detailed.Hair((60, 40, 30), 1.0, 0) if isinstance(value, detailed.Helmet) else detailed.Helmet()


def bytes_of(img):
    return hashlib.sha256(img.tobytes()).hexdigest()[:16]


def changed_by(img, other_img):
    """The pixels that differ between two pictures of one size: (x, y) each."""
    return [(x, y) for y in range(img.height) for x in range(img.width)
            if img.getpixel((x, y)) != other_img.getpixel((x, y))]


def outlined(character):
    """The character standing, with the dark outline, as the clip shows it."""
    rnd.seed(1)
    figure = detailed.DetailedFigure(detailed.box(detailed.TALL), detailed.TALL, detailed.Outline(), character)
    return figure.paint(standing())


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


class GifPaletteTest(unittest.TestCase):
    """A clip's one palette keeps the figure's colours, though the street alone has more colours than a GIF holds
    and the figure is not in the first frame."""

    FIGURE, STREET = 16, 24  # the most a channel of a pixel may be off, of 255

    def test_a_written_gif_keeps_the_figures_colours_and_the_streets(self):
        street = detailed.Committed().street
        figure = detailed.q565(painted(detailed.TALL, rim=detailed.Outline())[1])
        place = (120, detailed.FEET - figure.height + 1)
        with_figure = street.copy()
        with_figure.paste(figure, place, figure)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "clip.gif")
            detailed.write_gif([street, with_figure], path, 40, [figure])
            with Image.open(path) as gif:
                count, ms = gif.n_frames, gif.info["duration"]
                gif.seek(1)
                got = gif.convert("RGB")
        self.assertEqual((2, 40), (count, ms))
        off = {True: 0, False: 0}  # the worst channel error on the figure's pixels, and on the street's
        for y in range(got.height):
            for x in range(got.width):
                fx, fy = x - place[0], y - place[1]
                on = 0 <= fx < figure.width and 0 <= fy < figure.height and figure.getpixel((fx, fy))[3] > 0
                error = max(abs(a - b) for a, b in zip(got.getpixel((x, y)), with_figure.getpixel((x, y))))
                off[on] = max(off[on], error)
        self.assertLessEqual(off[True], self.FIGURE)
        self.assertLessEqual(off[False], self.STREET)


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
        capture = mocap.Capture()
        if capture.missing():
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.captured = detailed.RunPictures(capture, detailed.TALL)

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


class FiremanBytesGuardTest(unittest.TestCase):
    """During P904 step 2a's build only: the fireman's standing pose both ways, his 12 run poses and his 12 turned
    poses keep master's bytes (aa35f88). Removed in the PR's last commit."""

    MASTER = ('b1b254e1c62a192b', '94ebdebddad59f13', '62944133e66e0a47', 'd487390dae5def38', '44ca583b8ad453ec',
              '47037dbdad05a250', '7e868d5e0d7cfa06', 'b617d2af352f2ceb', '9c3d02b4196461de', 'd85d34f1a8774b3c',
              '51609a2a24ae3997', '3041a2eb5cf5f117', '1345c52c84ed6b5b', '6f595e006fe5d1e7', '19a422396ae2902e',
              'dbea70bb12385432', '8de7bb1900eb5605', '6e020e5eeb0a1242', '779763b99ce59afa', '202e59bc20a4cef8',
              'cd95334e879265b5', '269ae0f67de596f5', '5a641c73cf4964de', '265e5ca15bc9c418', '4d0592d56ad26e52',
              '1e73a45fd5f96431')

    def test_the_firemans_pictures_keep_masters_bytes(self):
        capture = mocap.Capture()
        if capture.missing():
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        got = [bytes_of(painted(detailed.TALL)[1]), bytes_of(painted(detailed.TALL, facing_left())[1])]
        run = detailed.RunPictures(capture, detailed.TALL)
        got += [bytes_of(img) for img in run.pictures]
        got += [bytes_of(run.alone(i, turned=True)) for i in range(12)]
        self.assertEqual(list(self.MASTER), got)


class CharacterTest(unittest.TestCase):
    """Every character of detailed.CAST on the standing pose (no CMU file is read), and the fields of its record."""

    def each(self):
        for character, _ in detailed.CAST:
            with self.subTest(character=character.name):
                yield character

    def test_the_fireman_is_the_records_defaults_and_the_first_of_the_cast(self):
        self.assertEqual(detailed.Character(), detailed.FIREMAN)
        self.assertEqual((detailed.FIREMAN, "run"), detailed.CAST[0])
        self.assertEqual(painted(detailed.TALL)[1].tobytes(), drawn(detailed.FIREMAN)[1].tobytes())

    def test_from_the_soles_on_the_last_row_to_the_head_joint(self):
        """(1 + SOLE) x PX - 1 px, PX from the height and the scale alone; the head joint measured down from the
        picture's top row by the headwear's rise."""
        for c in self.each():
            figure, img = drawn(c)
            px = detailed.TALL * c.scale / (1 + detailed.HELMET_TOP + figure.SOLE)
            rows = opaque_rows(img)
            self.assertEqual(img.height - 1, rows[-1])
            joint = rows[0] + c.headwear.rise(c.head) * px
            self.assertLessEqual(abs(rows[-1] - joint - ((1 + figure.SOLE) * px - 1)), 1)

    def test_each_field_of_the_record_and_of_its_parts_changes_the_picture(self):
        for c in self.each():
            before = bytes_of(drawn(c)[1])
            changed = [(f.name, dataclasses.replace(c, **{f.name: other(getattr(c, f.name))}))
                       for f in dataclasses.fields(c) if f.name != "name"]
            for k, part in enumerate((c.headwear,) + c.gear):
                for f in dataclasses.fields(part):
                    moved = dataclasses.replace(part, **{f.name: other(getattr(part, f.name))})
                    changed.append(("%s.%s" % (type(part).__name__, f.name),
                                    dataclasses.replace(c, headwear=moved) if k == 0 else
                                    dataclasses.replace(c, gear=c.gear[:k - 1] + (moved,) + c.gear[k:])))
                if k:
                    changed.append(("without %s" % type(part).__name__,
                                    dataclasses.replace(c, gear=c.gear[:k - 1] + c.gear[k:])))
            for name, character in changed:
                with self.subTest(field=name):
                    self.assertNotEqual(before, bytes_of(drawn(character)[1]))

    def test_facing_left_is_the_mirror_of_facing_right(self):
        for c in self.each():
            right = ImageOps.mirror(drawn(c)[1].getchannel("A"))
            left = drawn(c, facing_left())[1].getchannel("A")
            w, h = left.size
            both = [(bool(right.getpixel((x, y))), bool(left.getpixel((x, y)))) for y in range(h) for x in range(w)]
            either = [b for b in both if any(b)]
            self.assertGreaterEqual(sum(1 for a, b in either if a == b) / len(either), 0.97)

    def test_the_top_is_between_the_hips_and_the_neck_and_the_headwear_over_the_head_joint(self):
        """A part's pixels are those that its colour changes."""
        for c in self.each():
            figure, img = drawn(c)
            pose = standing()
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
                self.assertEqual(set(range(elbow + 3, wrist - 2)) if sleeve < 1 else set(), skin)

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
            figure, img = drawn(c)
            hy = figure.at(standing()["head"])[1]
            xs = [x for x, y in coloured(img, c.skin) if abs(y - hy) <= 2]
            rows = opaque_rows(img)
            share[c.name] = (max(xs) - min(xs) + 1) / (rows[-1] - rows[0] + 1)
        self.assertGreater(share["child"], share["fireman"] * 1.1)


class Stand:
    """A stand-in for RunPictures: one plain picture a facing, so CharacterClip is tested with no CMU file."""

    def __init__(self, colour, speed, size=(10, 20)):
        self.size, self.speed, self.stride = size, speed, 40
        self.pictures = [Image.new("RGBA", size, colour + (255,))] * 12
        self.left = [Image.new("RGBA", size, tuple(255 - c for c in colour) + (255,))] * 12

    def picture(self, ran, left=False):
        return (self.left if left else self.pictures)[detailed.pose_index(ran, self.stride, 12)]


class CharacterClipTest(unittest.TestCase):
    """characters.gif's frames on stand-in pictures: rows, facings, speeds and the paste order."""

    def setUp(self):
        self.runners = [Stand((200, 0, 0), 50), Stand((0, 200, 0), 80), Stand((0, 0, 200), 120)]
        self.street = Image.new("RGB", (detailed.CharacterClip.W, 240), (0, 0, 0))
        self.clip = detailed.CharacterClip(self.runners, self.street)

    def test_each_runner_has_a_row_from_200_to_238_and_every_second_runs_left(self):
        self.assertEqual([200, 219, 238], self.clip.rows)
        self.assertEqual([False, True, False], self.clip.left)

    def test_the_runners_are_pasted_in_the_order_of_their_rows(self):
        places = self.clip.places(0)
        self.assertEqual(sorted(p[1] for p in places), [p[1] for p in places])

    def test_a_left_runner_shows_its_left_pictures(self):
        for i in (0, 5):
            for k, (x, y, img) in zip((0, 1, 2), self.clip.places(i)):
                with self.subTest(frame=i, runner=k):
                    self.assertIs(img, self.runners[k].picture(0, self.clip.left[k]))

    def test_each_runner_advances_by_its_own_speed(self):
        for k, run in enumerate(self.runners):
            with self.subTest(runner=k):
                x0, x1 = self.clip.places(0)[k][0], self.clip.places(25)[k][0]
                way, lap = -1 if self.clip.left[k] else 1, detailed.CharacterClip.W + run.size[0]  # round again
                self.assertEqual(int(run.speed * 25 * detailed.FRAME_MS / 1000) % lap, (x1 - x0) * way % lap)

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
        capture = mocap.Capture()
        if capture.missing():
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.runners = [detailed.RunPictures(capture, detailed.TALL, character=c, cycle=cycle)
                       for c, cycle in detailed.CAST]

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


class CastPaletteTest(unittest.TestCase):
    """characters.gif's one palette, CAST_COLOURS of it from the figures, keeps every character's colours and the
    street's, within the bounds of GifPaletteTest."""

    def test_a_written_gif_keeps_the_figures_colours_and_the_streets(self):
        street = detailed.Committed().street
        figures = [detailed.q565(outlined(c)) for c, _ in detailed.CAST]
        with_figures, places = street.copy(), []
        for k, figure in enumerate(figures):
            places.append((10 + k * 78, 200 + k * 12 - figure.height + 1))
            with_figures.paste(figure, places[-1], figure)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "cast.gif")
            detailed.write_gif([street, with_figures], path, 40, figures, detailed.CAST_COLOURS)
            with Image.open(path) as gif:
                gif.seek(1)
                got = gif.convert("RGB")
        off = {True: 0, False: 0}
        for y in range(got.height):
            for x in range(got.width):
                on = any(0 <= x - px < f.width and 0 <= y - py < f.height and f.getpixel((x - px, y - py))[3]
                         for f, (px, py) in zip(figures, places))
                error = max(abs(a - b) for a, b in zip(got.getpixel((x, y)), with_figures.getpixel((x, y))))
                off[on] = max(off[on], error)
        self.assertLessEqual(off[True], GifPaletteTest.FIGURE)
        self.assertLessEqual(off[False], GifPaletteTest.STREET)


if __name__ == "__main__":
    unittest.main()
