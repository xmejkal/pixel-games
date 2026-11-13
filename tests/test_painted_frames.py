"""Meteors' and Bucket's painted sprites in the frames the README's GIFs are made from (P773, story 4): over each
render_scene row, every pictures.draw call is logged with the game's rules as they are in that frame. The walker's
sprite is drawn where Rules.walker_x is, in the run's pose for that place and facing his way, and the bucket's where
Rules.bucket_x is. Each row runs in its own process, as tools/render_scene.py sets module state (the clock, the
engines). Needs clang. Run from the repository root: python3 -m unittest discover tests. --- MVP (P773) ---"""

import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# One line per pictures.draw of a picture with one of the prefixes: the frame, the picture, x, y, then the game's state
# and the rules' numbers the test needs, as they are when the picture is drawn.
SCRIPT = r"""
import itertools, sys
sys.path.insert(0, "tools")
import render_scene as rs
import pictures
subject, prefixes, fields = sys.argv[1], tuple(sys.argv[2].split(",")), sys.argv[3].split(",")
row = rs.SUBJECTS[subject]
made, make = [], row.game
row.game = lambda: made.append(make()) or made[-1]
frame, lines = [0], []  # render_scene quiets the game's prints: the lines are printed after each frame
draw = pictures.draw
def logged(cv, name, x, y, alpha=255):
    if name.startswith(prefixes):
        game = made[0]
        lines.append(" ".join(str(v) for v in (frame[0], name, int(x), int(y), game.state)
                              + tuple(getattr(game.rules, f) for f in fields)))
    return draw(cv, name, x, y, alpha)
pictures.draw = logged
for k, _ in enumerate(itertools.islice(rs.frames(row), row.last)):
    frame[0] = k + 1
    print("\n".join(lines))
    lines.clear()
"""


def drawn(subject, prefixes, fields):
    run = subprocess.run([sys.executable, "-B", "-c", SCRIPT, subject, ",".join(prefixes), ",".join(fields)], cwd=ROOT,
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-800:]
    lines = [line.split() for line in run.stdout.split("\n") if line[:1].isdigit()]
    return [(int(k), name, int(x), int(y), int(state)) + tuple(int(v) for v in rest)
            for k, name, x, y, state, *rest in lines]


@unittest.skipUnless(shutil.which("clang"), "clang is missing: the C engines are not built, so the rows were not drawn")
class WalkerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(ROOT, "tests", "stubs"))
        sys.path.insert(0, os.path.join(ROOT, "games"))
        import gfx
        import meteors
        cls.game, cls.PLAY = meteors, gfx.PLAY
        cls.draws = drawn("meteors", ("meteors_run_",), ("walker_x", "dir"))

    def test_the_walker_is_drawn_once_a_frame_where_rules_walker_x_is(self):
        mt = self.game
        frames = [k for k, *_ in self.draws]
        self.assertEqual(sorted(set(frames)), frames)  # never twice in a frame
        self.assertGreater(len(frames), 100)
        for k, name, x, y, state, walker_x, direction in self.draws:
            with self.subTest(frame=k):
                self.assertEqual(walker_x - mt.FIG_DX, x)
                self.assertIn(y - (mt.HEIGHT - mt.FIG_H), mt.SHAKE)

    def test_his_pose_is_the_runs_for_his_place_and_he_faces_his_way(self):
        mt = self.game
        for k, name, x, y, state, walker_x, direction in self.draws:
            side = "r" if direction > 0 else "l"
            pose = (walker_x if direction > 0 else -walker_x) * mt.RUN_POSES // mt.STRIDE_PX % mt.RUN_POSES
            with self.subTest(frame=k):
                self.assertEqual("meteors_run_%s%d" % (side, pose), name)


@unittest.skipUnless(shutil.which("clang"), "clang is missing: the C engines are not built, so the rows were not drawn")
class BucketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(ROOT, "tests", "stubs"))
        sys.path.insert(0, os.path.join(ROOT, "games"))
        import bucket
        import gfx
        cls.game, cls.OVER = bucket, gfx.OVER
        cls.draws = drawn("bucket", ("bucket_bucket", "bucket_tipped"), ("bucket_x",))

    def test_the_bucket_is_drawn_once_a_frame_where_rules_bucket_x_is_its_foot_on_the_rail(self):
        bk = self.game
        frames = [k for k, *_ in self.draws]
        self.assertEqual(sorted(set(frames)), frames)
        self.assertGreater(len(frames), 100)
        for k, name, x, y, state, bucket_x in self.draws:
            with self.subTest(frame=k):
                self.assertEqual(bucket_x, x)
                self.assertEqual("bucket_tipped" if state == self.OVER else "bucket_bucket", name)
                self.assertEqual(bk.RAIL_Y - (bk.TIPPED_H if state == self.OVER else bk.BUCKET_H), y)


if __name__ == "__main__":
    unittest.main()
