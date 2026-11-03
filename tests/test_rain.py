"""games/rain.py on the Mac (P593): the Python stepper alone, and the C stepper on engine/core/world.c through ctypes (a
stand-in for the engine module), which must draw the same boxes. framebuf comes from tests/stubs and time gets the
MicroPython ticks functions, so gfx imports here. Run from the repository root: python3 -m unittest discover tests.
--- probe, throwaway (P593) ---"""

import contextlib
import ctypes
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

import rain  # noqa: E402

WORLD_C = os.path.join(os.path.dirname(HERE), "engine", "core", "world.c")
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


class Engine:
    """The engine module's FLOAT, spawn, step and read (engine/binding.c), on world.c through ctypes."""

    FLOAT = 0

    def __init__(self, lib):
        self.lib, self.world = lib, ctypes.create_string_buffer(lib.world_float_size())
        self.n = 0  # the world's body count, kept by the binding's rules: load sets it, a spawn past it raises it

    def load(self, *columns):
        self.n = len(columns[0])
        self.lib.world_load_float(self.world, self.n, *((ctypes.c_float * self.n).from_buffer(c) for c in columns))

    def spawn(self, i, x, y, vx, vy, rest_y):
        if not self.lib.world_spawn_float(self.world, i, *(ctypes.c_float(v) for v in (x, y, vx, vy, rest_y))):
            raise IndexError(i)
        self.n = max(self.n, i + 1)

    def step(self, mode, steps, rate, gravity, restitution, friction):
        self.lib.world_step_float(self.world, steps, rate,
                                  *(ctypes.c_float(v) for v in (gravity, restitution, friction)))

    def read(self, out):
        if len(out) < 3 * self.n:
            raise ValueError("an array('h') of 3n ints is needed")  # as engine.read does
        self.lib.world_read_float(self.world, (ctypes.c_int16 * len(out)).from_buffer(out))


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


@unittest.skipUnless(shutil.which("clang"), "clang is missing: engine/core/world.c is not built")
class CRainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        lib_path = os.path.join(cls.tmp.name, "libworld.so")
        subprocess.run(["clang", "-std=c99", "-O2", "-shared", "-fPIC", "-o", lib_path, WORLD_C], check=True)
        cls.lib = ctypes.CDLL(lib_path)
        cls.lib.world_float_size.restype = ctypes.c_size_t
        cls.lib.world_spawn_float.restype = ctypes.c_int32

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        rain.engine = Engine(self.lib)

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

    def test_a_world_left_larger_is_reset(self):
        rain.engine.spawn(rain.N + 10, 0, 0, 0, 0, 100)  # a run with a larger N before: the C world outlives a soft reset
        with contextlib.redirect_stdout(io.StringIO()):
            boxes, _ = play(rain.Rain(), 2, 0)
        self.assertEqual(rain.N, len(boxes))

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
