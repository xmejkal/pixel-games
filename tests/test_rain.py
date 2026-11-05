"""games/rain.py on the Mac (P593, P590): the Python stepper alone, and the C stepper on engine/core/world.c through
engine/tests/world_lib.py's stand-in for the engine module, which must draw the same boxes. framebuf comes from tests/stubs and
time gets the MicroPython ticks functions, so gfx imports here. Run from the repository root:
python3 -m unittest discover tests. --- MVP (P590) ---"""

import contextlib
import io
import os
import re
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engine", "tests"))  # pixel-engine: clang_lib
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

import rain  # noqa: E402
import world_lib  # noqa: E402

rain.engine = None  # the repository's engine/ folder imports as an empty package here: each test sets its engine
FRAME_MS = 40  # app.py's FRAME_MS
REPORT = re.compile(r"^rain (c|python) n %d fps \d+ step \d+\.\d\d read \d+\.\d\d draw \d+\.\d\d$" % rain.N, re.M)


class Recorder:
    """A canvas that keeps each fill as (x, y, w, h) and ignores the text."""

    def __init__(self):
        self.fills = []

    def fill(self, x, y, w, h, c):
        self.fills.append((int(x), int(y), int(w), int(h)))

    def text(self, *args):
        pass


def play(game, frames, now, pressed=False):
    """frames frames 40 ms apart from now, the first one pressed if asked: the boxes the last one paints, and now."""
    for k in range(frames):
        now += FRAME_MS
        game.step(now, pressed and k == 0, False)
        cv = Recorder()
        game.paint(cv)
    return cv.fills, now


class PythonRainTest(unittest.TestCase):
    def test_the_rain_falls_respawns_and_reports(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            game = rain.Rain()
            self.assertFalse(game.c)  # no engine module on the Mac
            first, now = play(game, 1, 0)
            spawn, drops = game.stepper.spawn, []
            game.stepper.spawn = lambda i, *state: drops.append(i) or spawn(i, *state)
            last, now = play(game, 150, now)  # 6 s: past REPORT_MS
        self.assertEqual(rain.N, len(last))
        self.assertEqual({(rain.SIZE, rain.SIZE)}, {f[2:] for f in last})
        self.assertGreater(len(drops), 0)  # sleepers fall again
        self.assertEqual([0] * rain.N, game.stepper.bodies.asleep)  # each read drops every sleeper
        self.assertIn("stepper python\n", out.getvalue())
        self.assertRegex(out.getvalue(), REPORT)
        self.assertTrue(game.label.startswith("python, no C step "), game.label)

    def test_a_tap_starts_again_from_the_seed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = rain.Rain()
            first, now = play(game, 1, 0)
            moved, now = play(game, 30, now)
            again, _ = play(game, 1, now, pressed=True)
        self.assertNotEqual(first, moved)
        self.assertEqual(first, again)


class StepperTest(unittest.TestCase):
    def drains_once(self, c):
        """A hit in one frame's step, then a frame of 0 steps: the second frame drains nothing (mutation run, P590)."""
        stepper = rain.Stepper(1, c)
        stepper.spawn(0, 0.0, 99.5, 0.0, 1000.0, 100.0)
        stepper.step(1)
        self.assertEqual(1, stepper.events())
        stepper.step(0)
        self.assertEqual(0, stepper.events())

    def test_python_drains_an_event_once(self):
        self.drains_once(False)

    @unittest.skipUnless(world_lib.HAVE_CLANG, "clang is missing: engine/core/world.c is not built")
    def test_c_drains_an_event_once(self):
        rain.engine = world_lib.engine()
        try:
            self.drains_once(True)
        finally:
            rain.engine = None


@unittest.skipUnless(world_lib.HAVE_CLANG, "clang is missing: engine/core/world.c is not built")
class CRainTest(unittest.TestCase):
    def setUp(self):
        rain.engine = world_lib.engine()

    def tearDown(self):
        rain.engine = None

    def test_c_draws_the_boxes_python_draws(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game_c = rain.Rain()
            game_py = rain.Rain()
            game_py.c = False
            game_py.restart()
            boxes_c, _ = play(game_c, 10, 0)  # 0.36 s: no box reaches its plane yet, so no respawn draws on random
            boxes_py, _ = play(game_py, 10, 0)
        self.assertEqual("c", game_c.stepper.name)
        self.assertEqual("python", game_py.stepper.name)
        self.assertEqual(rain.N, len(boxes_c))
        worst = max(abs(a - b) for fc, fp in zip(boxes_c, boxes_py) for a, b in zip(fc, fp))
        self.assertLessEqual(worst, 1, "float32 against Python's float may truncate 1 px apart")
        self.assertNotEqual(boxes_c, play(game_c, 1, 1000)[0])  # and they move

    def test_a_tap_swaps_the_stepper(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = rain.Rain()
            _, now = play(game, 1, 0)
            names = []
            for _ in range(2):
                _, now = play(game, 1, now, pressed=True)
                names.append(game.stepper.name)
        self.assertEqual(["python", "c"], names)


if __name__ == "__main__":
    unittest.main()
