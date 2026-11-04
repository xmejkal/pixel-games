"""games/fire.py on the Mac (P595): the scene with a ctypes stand-in for engine.HeatField (engine/core/fx_fire.c) and a
recording canvas, and the scene without the engine. framebuf comes from tests/stubs and time gets the MicroPython ticks
functions, so gfx imports here. Run from the repository root: python3 -m unittest discover tests. --- MVP (P595) ---"""

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

import fire  # noqa: E402
import lcd  # noqa: E402

FIRE_C = os.path.join(os.path.dirname(HERE), "engine", "core", "fx_fire.c")
S3LCD_SRC = os.path.join(os.path.dirname(HERE), "s3lcd", "src")  # blend565.h
FRAME_MS = 40  # app.py's FRAME_MS
REPORT = re.compile(r"^fire (B|picture) fps \d+ step \d+\.\d\d draw \d+\.\d\d$", re.M)
SEED_WIND = 595  # the gust test's seed for Python's random


sys.path.insert(0, HERE)
from test_fire_core import MAP_H, MAP_W, Field  # noqa: E402  fx_fire_t and its map


class Tft:
    """The s3lcd display: its frame, and the blits it was asked for."""

    def __init__(self):
        self.frame, self.blits = bytearray(lcd.PANEL_W * lcd.PANEL_H * 2), []

    def blit_buffer(self, buf, *args):
        self.blits.append(args)


class Recorder:
    """A canvas with a tft, that keeps each fill as (x, y, w, h) and ignores the text."""

    def __init__(self, tft):
        self.tft, self.fills = tft, []

    def fill(self, x, y, w, h, c):
        self.fills.append((int(x), int(y), int(w), int(h)))

    def text(self, *args):
        pass


class Engine:
    """The engine module's HeatField and largest_free_internal (engine/binding.c), on fx_fire.c through ctypes. looks
    keeps each set_look's numbers."""

    def __init__(self, lib):
        engine = self

        class HeatField:
            where = "internal"

            def __init__(self, w, h, seed):
                self.heat, self.f = bytearray(w * h + MAP_W * MAP_H), Field()  # the map after the field, as binding.c
                lib.fx_fire_init(ctypes.byref(self.f), (ctypes.c_uint8 * (w * h)).from_buffer(self.heat),
                                 (ctypes.c_uint8 * (MAP_W * MAP_H)).from_buffer(self.heat, w * h), w, h, seed)

            def set_look(self, *look):
                engine.looks.append(look)
                lib.fx_fire_set_look(ctypes.byref(self.f), *look)

            def step(self, steps, wind):
                lib.fx_fire_step(ctypes.byref(self.f), steps, wind)

            def draw(self, tft, palette, alpha=None):
                engine.targets.append("tft" if alpha is None else "tft alpha")
                out = (ctypes.c_uint16 * (len(tft.frame) // 2)).from_buffer(tft.frame)  # the display's frame
                if alpha is None:
                    lib.fx_fire_draw(ctypes.byref(self.f), out, (ctypes.c_uint16 * 256).from_buffer(palette))
                else:
                    lib.fx_fire_blend(ctypes.byref(self.f), out, (ctypes.c_uint16 * 256).from_buffer(palette),
                                      (ctypes.c_uint8 * 256).from_buffer(alpha))

        self.HeatField, self.targets, self.looks = HeatField, [], []

    def largest_free_internal(self):
        return 123456


def play(game, frames, now, tft, pressed=False):
    """frames frames 40 ms apart from now, the first one pressed if asked: the last frame's canvas, and now."""
    for k in range(frames):
        now += FRAME_MS
        game.step(now, pressed and k == 0, False)
        cv = Recorder(tft)
        game.paint_static(cv)
        game.paint(cv)
    return cv, now


class PaletteTest(unittest.TestCase):
    def test_heat_0_is_black_and_heat_255_white(self):
        self.assertEqual(256, len(fire.PALETTE))
        self.assertEqual(fire.BLACK, fire.PALETTE[0])
        self.assertEqual(fire.WHITE, fire.PALETTE[255])


class NoEngineTest(unittest.TestCase):
    def test_no_c_shows_and_nothing_else_is_drawn(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = fire.Fire()
            tft = Tft()
            cv, _ = play(game, 3, 0, tft)
        self.assertEqual("fire: no C", game.label)
        self.assertFalse(game.covers)  # nothing covers the screen, so the app fills it
        self.assertEqual([], cv.fills)
        self.assertEqual([], tft.blits)


@unittest.skipUnless(shutil.which("clang"), "clang is missing: engine/core/fx_fire.c is not built")
class FireTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        lib_path = os.path.join(cls.tmp.name, "libfire.so")
        subprocess.run(["clang", "-std=c99", "-O2", "-shared", "-fPIC", "-I", S3LCD_SRC, "-o", lib_path,
                        FIRE_C], check=True)
        cls.lib = ctypes.CDLL(lib_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        fire.engine = Engine(self.lib)

    def tearDown(self):
        fire.engine = None

    def test_the_fire_burns_and_reports(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            game = fire.Fire()
            tft = Tft()
            play(game, 150, 0, tft)  # 6 s: past REPORT_MS
        self.assertTrue(game.covers)
        self.assertIn("fire internal largest 123456\nfire field internal\n", out.getvalue())
        self.assertRegex(out.getvalue(), REPORT)
        self.assertRegex(game.label, r"^fire B \d+\.\d ms \d+ fps$")
        self.assertEqual({"tft"}, set(fire.engine.targets))
        look = (fire.DECAY, fire.COOL, fire.SWAY, fire.SPOTS, fire.SPREAD, fire.FAST, fire.EMBERS,
                    fire.FADE)
        self.assertEqual([look], fire.engine.looks)  # once
        self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame))  # the fire reached the frame

    def test_a_tap_moves_to_the_next_mode(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            game = fire.Fire()
            tft = Tft()
            _, now = play(game, 5, 0, tft)
            seen = []
            for _ in range(2):
                tft.blits, fire.engine.targets = [], []
                cv, now = play(game, 1, now, tft, pressed=True)
                cv, now = play(game, 1, now, tft)
                seen.append((fire.MODES[game.mode], fire.engine.targets, tft.blits, cv.fills))
        self.assertEqual([
            ("picture", ["tft alpha", "tft alpha"], [], [(0, 0, fire.WIDTH, fire.HEIGHT)]),  # no sky here
            ("B", ["tft", "tft"], [], []),
        ], seen)
        self.assertIn("fire mode picture\nfire mode B\n", out.getvalue())

    def test_the_wind_stays_within_wind(self):
        fire.random.seed(SEED_WIND)  # the gusts draw from Python's random: seeded, so both signs always show
        with contextlib.redirect_stdout(io.StringIO()):
            game = fire.Fire()
            winds, now = [], 0
            for _ in range(1000):
                _, now = play(game, 1, now, Tft())
                winds.append(game.wind)
        self.assertLessEqual(-fire.WIND, min(winds))
        self.assertLessEqual(max(winds), fire.WIND)
        self.assertLess(min(winds), 0)  # the gusts blow both ways
        self.assertGreater(max(winds), 0)

    def test_a_gust_reaches_its_target_both_ways(self):
        """The wind eases an eighth of the way each frame, rounded away from 0, so it ends on the target from either side."""
        with contextlib.redirect_stdout(io.StringIO()):
            game = fire.Fire()
            now = 0
            for target in (3, -3, fire.WIND, -fire.WIND):
                game.wind, game.target, game.gust = 0, target, 10 ** 9  # no new gust during the test
                _, now = play(game, 100, now, Tft())
                self.assertEqual(target, game.wind)

    def test_the_look_stays_low_at_the_top_for_the_seven_seeds(self):
        """The scene's look on its real field, 5,000 steps a seed: at every 100th step the top 10 rows' mean heat
        stays under 48, with the wind +WIND for 100 steps, then -WIND. Part 2's look without the bound reached white at
        the top with seed 7, and seed 4 reached 55.1 at fade 0 and 47.1 at fade 2."""
        for seed in (1, 2, 3, 4, 5, 7, 595):
            with self.subTest(seed=seed):
                field = fire.engine.HeatField(fire.W, fire.H, seed)
                field.set_look(fire.DECAY, fire.COOL, fire.SWAY, fire.SPOTS, fire.SPREAD, fire.FAST, fire.EMBERS,
                               fire.FADE)
                top = []
                for k in range(50):
                    field.step(100, fire.WIND if k % 2 == 0 else -fire.WIND)  # the wind one way, then the other
                    top.append(sum(field.heat[:10 * fire.W]) / (10 * fire.W))
                self.assertLess(max(top), 48, "the top rows' mean heat, %s" % [round(v) for v in top])


if __name__ == "__main__":
    unittest.main()
