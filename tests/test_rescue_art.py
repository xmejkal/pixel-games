"""The fireman's pictures (P800): the committed games/art files hold every cycle's poses, the left ones the exact
mirror of the right, and the motion that a run cycle needs. art/mocap.py on a tiny skeleton the test writes. And,
only when the CMU files are downloaded, the rescue set painted again gives the committed bytes. Run from the
repository root: python3 -m unittest discover tests."""

import contextlib
import io
import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names

from PIL import ImageOps  # noqa: E402

import mocap  # noqa: E402
from export import from_bin, to_bin  # noqa: E402

CYCLES = {c.name: c.poses for c in mocap.CYCLES}  # run 12, spray 6, turn 4
LOOPS = ("run", "spray")  # the cycles that repeat; the turn plays once


def art():
    index = {}
    with open(os.path.join(REPO, "games", "art_index.py")) as f:
        exec(f.read(), index)
    return index["ART"]


def picture(name):
    w, h, path = art()[name]
    with open(os.path.join(REPO, "games", path), "rb") as f:
        return from_bin(f.read(), w, h)


def opaque_rows(img):
    a = img.getchannel("A")
    return [y for y in range(img.height) if any(a.getpixel((x, y)) for x in range(img.width))]


def mask_difference(a, b):
    """The pixels where one picture is there and the other is not."""
    return sum((p != 0) != (q != 0) for p, q in zip(a.getchannel("A").get_flattened_data(), b.getchannel("A").get_flattened_data()))


class CommittedPosesTest(unittest.TestCase):
    """On the committed games/art files, not painted again: these hold without the CMU files."""

    @classmethod
    def setUpClass(cls):
        cls.art = art()
        cls.poses = {(c, side): [picture("rescue_%s_%s%d" % (c, side, i)) for i in range(n)]
                     for c, n in CYCLES.items() for side in "rl"}

    def test_each_cycle_has_its_poses_and_no_more(self):
        for c, n in CYCLES.items():
            for side in "rl":
                with self.subTest(cycle=c, side=side):
                    names = [k for k in self.art if k.startswith("rescue_%s_%s" % (c, side))]
                    self.assertEqual(["rescue_%s_%s%d" % (c, side, i) for i in range(n)], names)

    def test_no_pose_is_empty(self):
        for key, poses in self.poses.items():
            for i, img in enumerate(poses):
                with self.subTest(cycle=key, pose=i):
                    self.assertTrue(opaque_rows(img))

    def test_each_left_pose_is_the_exact_mirror_of_its_right_pose(self):
        for c in CYCLES:
            for i, (right, left) in enumerate(zip(self.poses[c, "r"], self.poses[c, "l"])):
                with self.subTest(cycle=c, pose=i):
                    self.assertEqual(to_bin(ImageOps.mirror(right), True), to_bin(left, True))

    def test_every_run_pose_stands_on_the_same_ground_row(self):
        lowest = [opaque_rows(img)[-1] for img in self.poses["run", "r"]]
        ground = max(lowest)
        self.assertEqual(self.poses["run", "r"][0].height - 1, ground)  # the soles on the picture's last row
        for i, row in enumerate(lowest):
            with self.subTest(pose=i):
                self.assertLessEqual(ground - row, 1)

    def test_the_top_moves_at_most_2_px_from_one_pose_to_the_next(self):
        for c in CYCLES:
            tops = [opaque_rows(img)[0] for img in self.poses[c, "r"]]
            pairs = list(zip(tops, tops[1:] + tops[:1])) if c in LOOPS else list(zip(tops, tops[1:]))
            for i, (a, b) in enumerate(pairs):
                with self.subTest(cycle=c, pose=i):
                    self.assertLessEqual(abs(a - b), 2)

    def test_a_loop_closes_no_harder_than_it_steps(self):
        for c in LOOPS:
            with self.subTest(cycle=c):
                poses = self.poses[c, "r"]
                steps = [mask_difference(a, b) for a, b in zip(poses, poses[1:])]
                self.assertLessEqual(mask_difference(poses[-1], poses[0]), max(steps))


class TinySkeletonTest(unittest.TestCase):
    """art/mocap.py on a skeleton of one leg, written here: its kinematics and its loop."""

    ASF = """:version 1.10
:units
  length 1
  angle deg
:root
   order TX TY TZ RX RY RZ
   axis XYZ
   position 0 0 0
   orientation 0 0 0
:bonedata
  begin
     id 1
     name thigh
     direction 0 -1 0
     length 2
     axis 0 0 0 XYZ
    dof rx
  end
  begin
     id 2
     name shin
     direction 0 -1 0
     length 2
     axis 0 0 0 XYZ
    dof rx
  end
:hierarchy
  begin
    root thigh
    thigh shin
  end
"""

    def test_the_kinematics_bend_the_leg_at_each_joint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "leg.asf")
            with open(path, "w") as f:
                f.write(self.ASF)
            skeleton = mocap.Skeleton(path)
            amc = os.path.join(tmp, "leg.amc")
            with open(amc, "w") as f:
                f.write(":FULLY-SPECIFIED\n:DEGREES\n1\nroot 1 4 0 0 0 0\nthigh 90\nshin 0\n"
                        "2\nroot 1 4 0 0 0 0\nthigh 0\nshin -90\n")
            frames = mocap.read_motion(amc)
        self.assertEqual(2, len(frames))
        straight = skeleton.joints({"root": [1, 4, 0, 0, 0, 0]})
        self.assertEqual((1, 0, 0), tuple(round(v, 6) for v in straight["shin"]))
        thigh_up = skeleton.joints(frames[0])  # the thigh turned 90 degrees about x: it points along z
        self.assertEqual((1, 4, -2), tuple(round(v, 6) + 0 for v in thigh_up["thigh"]))
        knee_bent = skeleton.joints(frames[1])  # the thigh down, the shin turned the other way about x
        self.assertEqual((1, 2, 0), tuple(round(v, 6) + 0 for v in knee_bent["thigh"]))
        self.assertEqual((1, 2, 2), tuple(round(v, 6) + 0 for v in knee_bent["shin"]))


class RepaintTest(unittest.TestCase):
    """The rescue set painted again from the CMU files gives the committed bytes, byte for byte."""

    def test_the_rescue_set_repaints_as_committed(self):
        capture = mocap.Capture()
        if capture.missing():
            self.skipTest("the CMU files are not in %s: the rescue bytes were not repainted (download them to run this)"
                          % mocap.CMU_DIR)
        from sets import rescue  # noqa: E402  only here, as it paints
        with contextlib.redirect_stdout(io.StringIO()):
            painting = rescue.ART_SET.paint()
        for name, (img, keyed) in painting.pictures.items():
            with self.subTest(name=name), open(os.path.join(REPO, "games", "art", name + ".bin"), "rb") as f:
                self.assertEqual(to_bin(img, keyed), f.read())


if __name__ == "__main__":
    unittest.main()
