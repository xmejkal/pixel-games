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
    """CBalls that keeps each spawn's arguments and the material it was given."""

    def __init__(self, n):
        super().__init__(n)
        self.spawns, self.material = [], None

    def set_material(self, *args):
        self.material = args
        return super().set_material(*args)

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
        self.assertEqual((balls.FRICTION, balls.RESTITUTION, balls.RESTITUTION_THRESHOLD), pit.material)

    def test_the_pit_fills_to_max_and_a_full_pit_pours_nothing(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = balls.BallPit()
            _, now = play(game, 1, 0, Tft())  # the first frame moves the title on; its tap would be eaten
            for _ in range(-(-balls.MAX // balls.POUR)):
                _, now = play(game, 2, now, Tft(), pressed=True)
            self.assertEqual(balls.MAX, game.balls.count)
            spawned = len(game.balls.spawns)
            _, now = play(game, 2, now, Tft(), pressed=True)
        self.assertEqual(balls.MAX, game.balls.count)
        self.assertEqual(spawned, len(game.balls.spawns))

    def test_a_hold_shakes_the_pit_harder_the_longer_it_is_held_and_pours_nothing(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = balls.BallPit()
            _, now = play(game, 60, 0, Tft())  # the first pour lands and rests
            pit = game.balls
            kicks = []
            pit.kick = lambda vx, vy: kicks.append((vx, vy))
            for hold in (8, 30):  # frames of 40 ms: 0.32 s, then 1.2 s
                for k in range(hold):
                    now += 40
                    game.step(now, k == 0, True)
                now += 40
                game.step(now, False, False)  # the release
        self.assertEqual(balls.POUR, pit.count)  # a hold pours nothing
        self.assertEqual(2, len(kicks))
        speeds = [(vx * vx + vy * vy) ** 0.5 for vx, vy in kicks]
        self.assertLess(speeds[0], speeds[1])
        self.assertTrue(all(vy < 0 for _, vy in kicks))  # up
        self.assertLessEqual(speeds[1], balls.SHAKE_MAX + 1e-3)

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
        self.assertRegex(game.label, r"^\d+ fps \d+ balls \d+\+\d+ ms \d+ hit/s$")
        self.assertLessEqual(len("8 fps 320 balls 165+6 ms 1188 hit/s"), (320 - 4) // 8)  # the worst seen fits
        self.assertEqual([], cv.fills)  # C paints the whole panel: no Python fill
        self.assertNotEqual(bytearray(len(tft.frame)), tft.frame)
        self.assertIs(drained, game.drained)  # made at setup, drained into each frame
