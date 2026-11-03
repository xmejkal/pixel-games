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

FIRE_C = os.path.join(os.path.dirname(HERE), "engine", "core", "fx_fire.c")
FRAME_MS = 40  # app.py's FRAME_MS
REPORT = re.compile(r"^fire (B|A|picture) fps \d+ step \d+\.\d\d draw \d+\.\d\d$", re.M)


class Field(ctypes.Structure):
    _fields_ = [("w", ctypes.c_int32), ("h", ctypes.c_int32), ("heat", ctypes.POINTER(ctypes.c_uint8)),
                ("rng", ctypes.c_uint32)]


class Tft:
    """The s3lcd display: its frame, and the blits it was asked for."""

    def __init__(self):
        self.frame, self.blits = bytearray(fire.PANEL_W * fire.PANEL_H * 2), []

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
    """The engine module's HeatField and largest_free_internal (engine/binding.c), on fx_fire.c through ctypes."""

    def __init__(self, lib):
        engine = self

        class HeatField:
            where = "internal"

            def __init__(self, w, h, seed):
                self.heat, self.f = bytearray(w * h), Field()
                lib.fx_fire_init(ctypes.byref(self.f), (ctypes.c_uint8 * (w * h)).from_buffer(self.heat), w, h, seed)

            def step(self, steps, decay):
                lib.fx_fire_step(ctypes.byref(self.f), steps, decay)

            def draw(self, target, palette):
                engine.targets.append("tft" if isinstance(target, Tft) else "buffer")
                out = target.frame if isinstance(target, Tft) else target  # path B writes the display's frame
                lib.fx_fire_draw(ctypes.byref(self.f), (ctypes.c_uint16 * (len(out) // 2)).from_buffer(out),
                                 (ctypes.c_uint16 * 256).from_buffer(palette))

        self.HeatField, self.targets = HeatField, []

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
        subprocess.run(["clang", "-std=c99", "-O2", "-shared", "-fPIC", "-o", lib_path, FIRE_C], check=True)
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
        self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame))  # the fire reached the frame

    def test_a_tap_moves_to_the_next_mode(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            game = fire.Fire()
            tft = Tft()
            _, now = play(game, 5, 0, tft)
            seen = []
            for _ in range(3):
                tft.blits, fire.engine.targets = [], []
                cv, now = play(game, 1, now, tft, pressed=True)
                cv, now = play(game, 1, now, tft)
                seen.append((fire.MODES[game.mode], fire.engine.targets, tft.blits, cv.fills))
        whole = (0, 0, fire.PANEL_W, fire.PANEL_H)
        self.assertEqual([
            ("A", ["buffer", "buffer"], [whole, whole], []),
            ("picture", ["buffer", "buffer"], [whole + (128, 0)] * 2, [(0, 0, fire.WIDTH, fire.HEIGHT)]),  # no sky here
            ("B", ["tft", "tft"], [], []),
        ], seen)
        self.assertIn("fire mode A\nfire mode picture\nfire mode B\n", out.getvalue())


if __name__ == "__main__":
    unittest.main()
