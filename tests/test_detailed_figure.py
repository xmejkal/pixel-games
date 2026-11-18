"""The detailed fireman (P904's spike, art/detailed.py): one number sets his size, he stands on the picture's last
row, he has a face, a helmet, gloves and a tank on his back, facing right or left, and his edge is one of three
rims. On a standing pose written here, so these hold without the CMU files. And, only when the CMU files are
downloaded, the twelve run poses painted from them. Run from the repository root:
python3 -m unittest discover tests."""

import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names

import detailed  # noqa: E402
import mocap  # noqa: E402
from brush import rnd  # noqa: E402
from PIL import Image  # noqa: E402
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
    figure = detailed.DetailedFireman(detailed.box(height), height, rim or detailed.NoRim())
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
        self.assertIsInstance(detailed.DetailedFireman(detailed.box(48), 48).edge, detailed.Outline)

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
        px = detailed.DetailedFireman(detailed.box(detailed.TALL), detailed.TALL).PX
        self.assertIsInstance(self.captured.stride, int)
        self.assertLessEqual(abs(self.captured.stride / px - 41 / 24.07), 0.02)
        self.assertLessEqual(abs(self.captured.speed / px - 56 / 24.07), 0.03)

    def test_a_run_of_px_shows_the_pose_of_the_index(self):
        for ran in (0, self.captured.stride // 2, self.captured.stride - 1):
            with self.subTest(ran=ran):
                self.assertIs(self.captured.pictures[detailed.pose_index(ran, self.captured.stride, 12)],
                              self.captured.picture(ran))


if __name__ == "__main__":
    unittest.main()
