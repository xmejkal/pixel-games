"""The fireman's pictures (P800): the committed games/packs hold every cycle's poses, the left ones the exact
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
from export import committed_index, from_bin, pack_bytes, to_bin  # noqa: E402

CYCLES = {c.name: c.poses for c in mocap.CYCLES}  # run 12, spray 6, turn 4
LOOPS = ("run", "spray")  # the cycles that repeat; the turn plays once


def art():
    return committed_index()["ART"]


def picture(name):
    w, h = art()[name][:2]
    return from_bin(pack_bytes(name), w, h)


def opaque_rows(img):
    a = img.getchannel("A")
    return [y for y in range(img.height) if any(a.getpixel((x, y)) for x in range(img.width))]


def mask_difference(a, b):
    """The pixels where one picture is there and the other is not."""
    alpha_a, alpha_b = a.getchannel("A").get_flattened_data(), b.getchannel("A").get_flattened_data()
    return sum((p != 0) != (q != 0) for p, q in zip(alpha_a, alpha_b))


class CommittedPosesTest(unittest.TestCase):
    """On the committed games/packs, not painted again: these hold without the CMU files."""

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


class GameAndArtAgreeTest(unittest.TestCase):
    """games/rescue.py keeps its own copies of the art's numbers, as the board has no art/: they must agree."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(REPO, "tests", "stubs"))
        sys.path.insert(0, os.path.join(REPO, "games"))
        import rescue as game  # noqa: E402  games/rescue.py
        from sets import rescue as art_set  # noqa: E402  art/sets/rescue.py
        cls.game, cls.art_set = game, art_set

    def test_the_street_rows_the_sizes_and_the_pose_counts(self):
        game, art_set = self.game, self.art_set
        self.assertEqual((art_set.FEET, art_set.LANE), (game.FEET, game.LANE))
        self.assertEqual({c: w for c, (w, _) in art_set.SIZES.items()}, game.SIZES)
        self.assertEqual({h for _, h in art_set.SIZES.values()}, {game.PICTURE_H})
        self.assertEqual((CYCLES["run"], CYCLES["spray"], CYCLES["turn"]),
                         (game.RUN_POSES, game.SPRAY_POSES, game.TURN_POSES))

    def test_the_nozzle_is_where_the_spray_pictures_hold_it(self):
        brass = self.art_set.BRASS
        for i in range(CYCLES["spray"]):
            img = picture("rescue_spray_r%d" % i)
            w, h = img.size
            tips = [(x, y) for y in range(h) for x in range(w)
                    if img.getpixel((x, y))[3] and sum(abs(a - b) for a, b in zip(img.getpixel((x, y)), brass)) < 40]
            x, y = max(tips)
            with self.subTest(pose=i):
                self.assertLessEqual(abs(x - w // 2 - self.game.NOZZLE_DX), 1)
                self.assertLessEqual(abs(y - (h - 1) - self.game.NOZZLE_DY), 1)


class PeopleAndCarryPosesTest(unittest.TestCase):
    """PR 2's cycles on the committed games/packs: the carry (with an adult and with a child), each person's run
    and wave, and the dog. Each loops, so the last pose steps to the first as any other."""

    @classmethod
    def setUpClass(cls):
        from sets import rescue as art_set  # noqa: E402  art/sets/rescue.py
        cls.art = art()
        cls.counts = {c: n for c, n in art_set.CapturedPictures.cycles() if c not in CYCLES}
        cls.counts["carry"] = CYCLES["carry"]
        cls.counts["dog"] = art_set.DOG_POSES
        cls.poses = {(c, side): [picture("rescue_%s_%s%d" % (c, side, i)) for i in range(n)]
                     for c, n in cls.counts.items() for side in "rl"}

    def test_every_cycle_is_there_with_its_poses(self):
        self.assertEqual({"carry", "carrykid", "man_run", "man_wave", "woman_run", "woman_wave", "child_run",
                          "child_wave", "granny_run", "granny_wave", "dogman_run", "dogman_wave", "dog"},
                         set(self.counts))
        for c, n in self.counts.items():
            for side in "rl":
                with self.subTest(cycle=c, side=side):
                    names = [k for k in self.art if k.startswith("rescue_%s_%s" % (c, side))
                             and k[len("rescue_%s_%s" % (c, side)):].isdigit()]
                    self.assertEqual(["rescue_%s_%s%d" % (c, side, i) for i in range(n)], names)
                    self.assertEqual(12 if c != "dog" else 8, n)

    def test_each_left_pose_is_the_exact_mirror_and_none_is_empty(self):
        for c in self.counts:
            for i, (right, left) in enumerate(zip(self.poses[c, "r"], self.poses[c, "l"])):
                with self.subTest(cycle=c, pose=i):
                    self.assertTrue(opaque_rows(right))
                    self.assertEqual(to_bin(ImageOps.mirror(right), True), to_bin(left, True))

    def test_the_feet_stand_on_the_picture_s_last_row_in_every_pose(self):
        for c in self.counts:
            for i, img in enumerate(self.poses[c, "r"]):
                with self.subTest(cycle=c, pose=i):
                    self.assertLessEqual(img.height - 1 - opaque_rows(img)[-1], 1)

    def test_the_top_moves_at_most_2_px_from_one_pose_to_the_next(self):
        for c in self.counts:
            tops = [opaque_rows(img)[0] for img in self.poses[c, "r"]]
            for i, (a, b) in enumerate(zip(tops, tops[1:] + tops[:1])):
                with self.subTest(cycle=c, pose=i):
                    self.assertLessEqual(abs(a - b), 2)

    def test_the_game_knows_the_sizes(self):
        sys.path.insert(0, os.path.join(REPO, "tests", "stubs"))
        sys.path.insert(0, os.path.join(REPO, "games"))
        import rescue as game  # noqa: E402  games/rescue.py
        for kind, who in enumerate(game.KINDS):
            for cycle in ("run", "wave"):
                with self.subTest(who=who, cycle=cycle):
                    self.assertEqual(game.PEOPLE_SIZES[kind], self.poses[who + "_" + cycle, "r"][0].size)
        self.assertEqual((game.DOG_W, game.DOG_H), self.poses["dog", "r"][0].size)
        self.assertEqual((game.SIZES["carry"], game.PICTURE_H), self.poses["carrykid", "r"][0].size)
        self.assertEqual((game.PERSON_POSES, game.WAVE_POSES, game.DOG_POSES, game.CARRY_POSES),
                         (self.counts["man_run"], self.counts["man_wave"], self.counts["dog"], self.counts["carry"]))


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


class WithoutTheCaptureTest(unittest.TestCase):
    """art/paint.py paints without the CMU files: the captured pictures are read back from games/packs as committed."""

    def test_the_pictures_come_back_from_games_packs(self):
        from sets import rescue as art_set  # noqa: E402
        with tempfile.TemporaryDirectory() as empty, contextlib.redirect_stdout(io.StringIO()) as said:
            pictures = art_set.CapturedPictures(empty).pictures()
        self.assertIn("read back from games/packs", said.getvalue())
        self.assertEqual(set(art_set.CapturedPictures.names()), set(pictures))
        for name in ("rescue_carrykid_r3", "rescue_granny_wave_l7", "rescue_run_r0"):
            with self.subTest(name=name):
                self.assertEqual(pack_bytes(name), to_bin(pictures[name], True))


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
            with self.subTest(name=name):
                self.assertEqual(to_bin(img, keyed), pack_bytes(name))

    def test_the_game_s_strides_are_the_capture_s(self):
        """games/rescue.py keeps each cycle's stride in px: the capture's stride at the figure's size."""
        capture = mocap.Capture()
        if capture.missing():
            self.skipTest("the CMU files are not in %s: the strides were not measured" % mocap.CMU_DIR)
        sys.path.insert(0, os.path.join(REPO, "tests", "stubs"))
        sys.path.insert(0, os.path.join(REPO, "games"))
        import rescue as game  # noqa: E402
        from sets import rescue as art_set  # noqa: E402
        crowd = {c.name: c for c in mocap.CROWD}
        carry = [c for c in mocap.CYCLES if c.name == "carry"][0]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(game.CARRY_STRIDE_PX, round(capture.stride(carry) * art_set.PX))
            for kind, who in enumerate(game.KINDS):
                with self.subTest(who=who):
                    px = art_set.LOOKS[who].height / (1 + art_set.HEAD_TOP)
                    self.assertEqual(game.PERSON_STRIDE_PX[kind], round(capture.stride(crowd[who]) * px))


if __name__ == "__main__":
    unittest.main()
