"""The detailed fireman (P904's spike, art/detailed.py): one number sets his size, he stands on the picture's last
row, and he has a face and gloves. On a standing pose written here, so these hold without the CMU files. And, only
when the CMU files are downloaded, the twelve run poses painted from them. Run from the repository root:
python3 -m unittest discover tests."""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names

import detailed  # noqa: E402
import mocap  # noqa: E402
from brush import rnd  # noqa: E402

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


def painted(height, seed=1):
    rnd.seed(seed)
    figure = detailed.DetailedFireman(detailed.box(height), height)
    return figure, figure.paint(standing())


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
        self.assertTrue([q for q in coloured(img, detailed.EYE, 60) if abs(q[0] - hx) <= r and abs(q[1] - hy) <= r])

    def test_the_face_is_on_the_side_the_nose_is(self):
        figure, img = painted(detailed.TALL)
        hx, _ = figure.at(standing()["head"])
        xs = [x for x, _ in coloured(img, detailed.SKIN)]
        self.assertGreater(sum(xs) / len(xs), hx)

    def test_a_glove_starts_at_the_wrist_and_no_higher(self):
        figure, img = painted(detailed.TALL)
        _, wrist_row = figure.at(standing()["rradius"])
        gloves = coloured(img, detailed.GLOVE)
        self.assertGreaterEqual(len(gloves), 12)
        self.assertGreaterEqual(min(y for _, y in gloves), wrist_row - figure.GLOVE_W * figure.PX)

    def test_the_same_seed_paints_the_same_bytes(self):
        self.assertEqual(painted(detailed.TALL)[1].tobytes(), painted(detailed.TALL)[1].tobytes())


class RunFromCaptureTest(unittest.TestCase):
    """The twelve run poses, painted from the CMU files: skipped without them, and a skip is not a pass."""

    @classmethod
    def setUpClass(cls):
        capture = mocap.Capture()
        if capture.missing():
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.run = detailed.RunPictures(capture, detailed.TALL)

    def test_twelve_poses_and_none_is_empty(self):
        self.assertEqual(12, len(self.run.pictures))
        for i, img in enumerate(self.run.pictures):
            with self.subTest(pose=i):
                self.assertTrue(opaque_rows(img))

    def test_every_pose_has_the_one_box_and_no_column_or_top_row_of_it_is_unused(self):
        w, h = self.run.size
        self.assertEqual({(w, h)}, {img.size for img in self.run.pictures})
        used = [img.getchannel("A").getbbox() for img in self.run.pictures]
        self.assertEqual((0, 0, w), (min(b[0] for b in used), min(b[1] for b in used), max(b[2] for b in used)))

    def test_the_lowest_pose_stands_on_the_last_row_and_a_flight_lifts_no_pose_by_a_tenth(self):
        h = self.run.size[1]
        lowest = [opaque_rows(img)[-1] for img in self.run.pictures]
        self.assertEqual(h - 1, max(lowest))
        self.assertGreater(min(lowest), h - 1 - detailed.TALL // 10)

    def test_the_bytes_are_two_a_pixel_for_each_pose_and_both_facings(self):
        w, h = self.run.size
        self.assertEqual(w * h * 2 * 12 * 2, self.run.bytes())

    def test_the_stride_is_a_whole_number_of_px(self):
        self.assertIsInstance(self.run.stride, int)
        self.assertLessEqual(abs(self.run.stride - 1.698 * self.run.figure.PX), 1.5)


if __name__ == "__main__":
    unittest.main()
