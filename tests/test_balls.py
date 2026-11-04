"""games/balls.py on the Mac (P598): the ball pit with tests/balls_lib.py's stand-in for engine.Balls (fx_balls.c
through ctypes) and a recording canvas, and the scene without the engine. framebuf comes from tests/stubs and time gets
the MicroPython ticks functions, so gfx imports here. Run from the repository root: python3 -m unittest discover tests.
--- MVP (P598) ---"""

import contextlib
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_fire import Recorder, Tft, play  # noqa: E402  also puts games/ and the stubs on the path

import balls  # noqa: E402
import balls_lib  # noqa: E402

balls.engine = None  # the repository's engine/ folder imports as an empty package here: each test sets its engine
REPORT = re.compile(r"^balls n (\d+) fps \d+ step \d+\.\d\d draw \d+\.\d\d hits (\d+)$", re.M)


class RecordingBalls(balls_lib.CBalls):
    """CBalls that keeps each spawn's arguments."""

    def __init__(self, n):
        super().__init__(n)
        self.spawns = []

    def spawn(self, *args):
        self.spawns.append(args)
        return super().spawn(*args)


class NoEngineTest(unittest.TestCase):
    def test_no_c_shows_and_nothing_else_is_drawn(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = balls.BallPit()
            tft = Tft()
            cv, _ = play(game, 3, 0, tft, pressed=True)
        self.assertEqual("balls: no C", game.label)
        self.assertFalse(game.covers)
        self.assertEqual([], cv.fills)
        self.assertEqual(bytearray(len(tft.frame)), tft.frame)


@unittest.skipUnless(balls_lib.HAVE_CLANG, "clang is missing: engine/core/fx_balls.c is not built")
class BallPitTest(unittest.TestCase):
    def setUp(self):
        balls.engine = balls_lib.engine()
        balls.engine.Balls = RecordingBalls

    def tearDown(self):
        balls.engine = None

    def test_setup_pours_once_a_tap_pours_the_next_colour_and_a_frame_spawns_nothing(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = balls.BallPit()
            pit = game.balls
            self.assertEqual(balls.POUR, pit.count)
            _, now = play(game, 10, 0, Tft())
            self.assertEqual(balls.POUR, pit.count)  # no pour without a tap
            _, now = play(game, 10, now, Tft(), pressed=True)
        self.assertEqual(2 * balls.POUR, pit.count)
        colours = [spawn[5] for spawn in pit.spawns]
        self.assertEqual([0] * balls.POUR + [1] * balls.POUR, colours)
        radii = {spawn[4] for spawn in pit.spawns}
        self.assertTrue(radii <= set(range(balls.R_MIN, balls.R_MAX + 1)) and len(radii) > 1, radii)
        self.assertTrue(all(spawn[1] < 0 for spawn in pit.spawns))  # from above the top
        self.assertTrue(game.covers)

    def test_a_full_pit_empties_on_the_next_tap_and_pours_again(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = balls.BallPit()
            _, now = play(game, 1, 0, Tft())  # the first frame moves the title on; its tap would be eaten
            for _ in range(balls.MAX // balls.POUR - 1):
                _, now = play(game, 2, now, Tft(), pressed=True)
            self.assertEqual(balls.MAX, game.balls.count)
            _, now = play(game, 1, now, Tft(), pressed=True)
        self.assertEqual(balls.POUR, game.balls.count)
        spawns = game.balls.spawns
        self.assertEqual((11, 0), (spawns[-balls.POUR - 1][5], spawns[-1][5]))  # the 12th pour's colour, then round again

    def test_the_pit_draws_reports_and_counts_hits(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            game = balls.BallPit()
            tft, drained = Tft(), game.drained
            cv, _ = play(game, 150, 0, tft)  # 6 s: past REPORT_MS, and the pour has landed
        report = REPORT.search(out.getvalue())
        self.assertTrue(report, out.getvalue())
        self.assertEqual(balls.POUR, int(report.group(1)))
        self.assertGreater(int(report.group(2)), 0)  # the handful landed: hits in the first 5 s
        self.assertRegex(game.label, r"^balls \d+ step \d+\.\d draw \d+\.\d ms \d+ fps \d+/s$")
        self.assertEqual([], cv.fills)  # C paints the whole panel: no Python fill
        self.assertNotEqual(bytearray(len(tft.frame)), tft.frame)
        self.assertIs(drained, game.drained)  # made at setup, drained into each frame
