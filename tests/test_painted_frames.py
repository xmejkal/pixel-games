"""Meteors', Bucket's, BUBBLE's and FEED's painted sprites in the frames the README's GIFs are made from (P773, story 4; P573):
over each render_scene row, every pictures.draw call is logged with the game's numbers as they are in that frame. The
walker's sprite is drawn where Rules.walker_x is, in the run's pose for that place and facing his way, the bucket's
where Rules.bucket_x is, and BUBBLE's bubble centred where the game's bubble is, at the size of its radius. Each row
runs in its own process, as tools/render_scene.py sets module state (the clock, the engines). Needs clang. Run from the repository root: python3 -m unittest discover tests. --- MVP (P773) ---"""

import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# One line per pictures.draw of a picture with one of the prefixes: the frame, the picture, x, y, then the game's state
# and the numbers the test needs, each an expression over game (game.rules.walker_x, game.radius()), as they are when
# the picture is drawn.
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
                              + tuple(eval(f, {"game": game}) for f in fields)))
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
    return [(int(k), name, int(x), int(y), int(state)) + tuple(float(v) for v in rest)
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
        cls.draws = drawn("meteors", ("meteors_run_",), ("game.rules.walker_x", "game.rules.dir"))

    def test_the_walker_is_drawn_once_a_frame_where_rules_walker_x_is(self):
        mt = self.game
        frames = [k for k, *_ in self.draws]
        self.assertEqual(sorted(set(frames)), frames)  # never twice in a frame
        self.assertGreater(len(frames), 100)
        for k, name, x, y, state, walker_x, direction in self.draws:
            with self.subTest(frame=k):
                self.assertEqual(walker_x - mt.FIG_DX, x)
                self.assertIn(mt.HEIGHT - mt.FIG_H - y, mt.SHAKE)  # his soles on the last row, or up in a shake

    def test_his_pose_is_the_runs_for_his_place_and_he_faces_his_way(self):
        mt = self.game
        for k, name, x, y, state, walker_x, direction in self.draws:
            side = "r" if direction > 0 else "l"
            with self.subTest(frame=k):
                self.assertEqual("meteors_run_%s%d" % (side, mt.pose_for(walker_x, direction > 0)), name)


@unittest.skipUnless(shutil.which("clang"), "clang is missing: the C engines are not built, so the rows were not drawn")
class BucketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(ROOT, "tests", "stubs"))
        sys.path.insert(0, os.path.join(ROOT, "games"))
        import bucket
        import gfx
        cls.game, cls.OVER = bucket, gfx.OVER
        cls.draws = drawn("bucket", ("bucket_bucket", "bucket_tipped"), ("game.rules.bucket_x",))

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


@unittest.skipUnless(shutil.which("clang"), "clang is missing: the C engines are not built, so the rows were not drawn")
class BubbleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(ROOT, "tests", "stubs"))
        sys.path.insert(0, os.path.join(ROOT, "games"))
        import arcade2
        import gfx
        cls.game, cls.PLAY = arcade2.GravityPong, gfx.PLAY
        fields = ("game.bx", "game.by", "game.radius()", "game.px")
        cls.bubbles = drawn("gravitypong", ("gravpong_bubble_",), fields)
        cls.nets = drawn("gravitypong", ("gravpong_net_",), fields)

    def test_the_bubble_is_drawn_once_a_frame_of_play_centred_where_it_is_at_the_size_of_its_radius(self):
        g = self.game
        play = [d for d in self.bubbles if d[4] == self.PLAY]
        frames = [d[0] for d in play]
        self.assertEqual(list(range(frames[-1] + 1)), frames)  # every frame of play, once, from the first (0)
        over = [d[0] for d in self.bubbles if d[4] != self.PLAY]
        self.assertEqual(frames[-1] + 1, over[0])  # then the hit-pause's squash, the frame after the loss
        self.assertGreater(len(frames), 50)
        self.assertGreater(max(d[7] for d in play), 6)  # the bubble swelled in the row
        for k, name, x, y, state, bx, by, radius, px in play:
            size = (int(radius) - 6) // 2
            half = g.BOX[size] // 2
            with self.subTest(frame=k):
                self.assertIn(name, g.BUBBLES[size])
                self.assertEqual(int(bx) - half, x)
                self.assertEqual(min(int(by), g.FLOOR - int(radius)) - half, y)  # on the floor once it is down there
                if int(by) > g.FLOOR - int(radius):
                    self.assertTrue(name.endswith("_squash"))

    def test_the_net_is_drawn_once_a_frame_at_the_paddles_place(self):
        g = self.game
        frames = [d[0] for d in self.nets]
        self.assertEqual(list(range(frames[-1] + 1)), frames)  # every frame, once, in play and over
        self.assertGreater(len(frames), 400)
        for k, name, x, y, state, bx, by, radius, px in self.nets:
            with self.subTest(frame=k):
                self.assertIn(name, [n for names in g.NETS.values() for n in names])
                self.assertEqual((int(px), g.PY - 2), (x, y))  # its end ropes on the hit row PY
        self.assertEqual(g.PY - 2, g.NET_Y)



@unittest.skipUnless(shutil.which("clang"), "clang is missing: the C engines are not built, so the rows were not drawn")
class FeedTest(unittest.TestCase):
    """FEED (P573) over the snake row: the head in every frame of play on its slide from its last cell into its new
    one, at the new one once the slide is done and never past it; the dot in every frame of play where the food is;
    over, the bite, then the flip head to tail by its clock, then the card."""

    FIELDS = ("game.body[0][0]", "game.body[0][1]", "game.body[1][0]", "game.body[1][1]", "game.acc", "game.food[0]",
              "game.food[1]", "game.over_ms()", "len(game.body)")

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(ROOT, "tests", "stubs"))
        sys.path.insert(0, os.path.join(ROOT, "games"))
        import arcade
        import gfx
        cls.game, cls.module, cls.PLAY, cls.OVER = arcade.Snake, arcade, gfx.PLAY, gfx.OVER
        cls.draws = drawn("snake", ("snake_head_", "snake_dot_", "snake_seen_", "snake_tile_", "snake_over"),
                          cls.FIELDS)

    def play(self, prefix):
        return [d for d in self.draws if d[4] == self.PLAY and d[1].startswith(prefix)]

    def test_the_head_is_drawn_once_every_frame_of_play_on_its_slide_never_past_its_cell(self):
        g = self.game
        heads = self.play("snake_head_")
        frames = [d[0] for d in heads]
        self.assertEqual(list(range(frames[-1] + 1)), frames)  # every frame of play, once, from the first (0)
        self.assertGreater(len(frames), 600)
        slid = 0
        for k, name, x, y, state, hx, hy, lx, ly, acc, fx, fy, ms, n in heads:
            new = (g.LEFT + int(hx) * g.CELL - 2, g.TOP + int(hy) * g.CELL - 2)
            last = (g.LEFT + int(lx) * g.CELL - 2, g.TOP + int(ly) * g.CELL - 2)
            with self.subTest(frame=k):
                if acc >= self.module.Slide.SLIDE_MS or abs(new[0] - last[0]) > g.CELL or abs(new[1] - last[1]) > g.CELL:
                    self.assertEqual(new, (x, y))  # the slide is done, or a wrap: at the cell
                else:
                    self.assertTrue(min(last[0], new[0]) <= x <= max(last[0], new[0]))
                    self.assertTrue(min(last[1], new[1]) <= y <= max(last[1], new[1]))
                    self.assertTrue(x == new[0] or y == new[1])  # on the line between the two cells
                    slid += (x, y) != new
        self.assertGreater(slid, 100)  # it slides in many frames, not only at the steps

    def test_the_dot_is_drawn_once_every_frame_of_play_where_the_food_is(self):
        g = self.game
        dots = self.play("snake_dot_")
        self.assertEqual(list(range(dots[-1][0] + 1)), [d[0] for d in dots])
        for k, name, x, y, state, hx, hy, lx, ly, acc, fx, fy, ms, n in dots:
            with self.subTest(frame=k):
                self.assertEqual((g.LEFT + int(fx) * g.CELL, g.TOP + int(fy) * g.CELL), (x, y))

    def test_over_the_head_bites_then_every_tile_turns_to_seen_head_to_tail_then_the_card(self):
        g, flip = self.game, self.module.Flip
        over = {}
        for d in self.draws:
            if d[4] == self.OVER:
                over.setdefault(d[0], []).append(d)
        self.assertGreater(len(over), 20)
        for f, ds in sorted(over.items()):
            names, ms, n = [d[1] for d in ds], int(ds[0][12]), int(ds[0][13])
            seen = [k for k in names if k.startswith("snake_seen_")]
            with self.subTest(frame=f, ms=ms):
                self.assertEqual(sum(flip.pose(i, n, ms) >= 0 for i in range(n)), len(seen))
                self.assertEqual(ms < flip.HOLD_MS, any(k.endswith("_chew") for k in names))  # the bite, then no head
                self.assertEqual(ms >= g.CARD_MS, "snake_over" in names)
                if ms >= flip.END_MS:
                    self.assertEqual(["snake_seen_2"] * n, seen)
        self.assertTrue(any("snake_over" in [d[1] for d in ds] for ds in over.values()))


if __name__ == "__main__":
    unittest.main()
