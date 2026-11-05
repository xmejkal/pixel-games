"""s3lcd's blend (P603) against a Python reference: the games keep colours in the panel's byte order (gfx.c565), so the
blend swaps the bytes in, mixes red, green and blue, and swaps the result back. clang builds a shim around
engine/driver/src/blend565.h into a temporary folder and ctypes calls it. Run from the repository root:
python3 -m unittest discover tests. --- MVP (P603) ---"""

import ctypes
import os
import random
import shutil
import subprocess
import sys
import tempfile
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

import gfx  # noqa: E402

from clang_lib import S3LCD_SRC  # noqa: E402
SHIM = """#include <stdint.h>
#include "blend565.h"
uint16_t blend(uint16_t fg, uint16_t bg, uint8_t alpha) { return alpha_blend_565(fg, bg, alpha); }
"""


def swap(v):
    return ((v & 0xFF) << 8) | (v >> 8)


def fields(panel):
    """Red, green and blue of a colour in the panel's byte order."""
    v = swap(panel)
    return v >> 11, (v >> 5) & 0x3F, v & 0x1F


def reference(fg, bg, alpha):
    """The upstream formula on the unswapped fields, the result swapped back."""
    if alpha == 0:
        return bg
    if alpha == 255:
        return fg
    mixed = [(f * alpha + b * (255 - alpha)) >> 8 for f, b in zip(fields(fg), fields(bg))]
    return swap((mixed[0] << 11) | (mixed[1] << 5) | mixed[2])


@unittest.skipUnless(shutil.which("clang"), "clang is missing: engine/driver/src/blend565.h is not built")
class BlendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        shim, lib_path = os.path.join(cls.tmp.name, "shim.c"), os.path.join(cls.tmp.name, "libblend.so")
        with open(shim, "w") as f:
            f.write(SHIM)
        subprocess.run(["clang", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-I", S3LCD_SRC,
                        "-o", lib_path, shim], check=True)
        cls.lib = ctypes.CDLL(lib_path)
        cls.lib.blend.restype = ctypes.c_uint16
        cls.lib.blend.argtypes = (ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint8)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_red_at_half_over_blue_gives_the_half_mix(self):
        mixed = fields(self.lib.blend(gfx.RED, gfx.BLUE, 128))
        halves = [(a + b) / 2 for a, b in zip(fields(gfx.RED), fields(gfx.BLUE))]
        for got, half in zip(mixed, halves):
            self.assertLessEqual(abs(got - half), 1, (mixed, halves))

    def test_alpha_0_and_255_give_the_background_and_the_colour(self):
        self.assertEqual(gfx.BLUE, self.lib.blend(gfx.RED, gfx.BLUE, 0))
        self.assertEqual(gfx.RED, self.lib.blend(gfx.RED, gfx.BLUE, 255))

    def test_green_split_across_the_bytes_stays_green(self):
        """In panel order green's six bits sit in both bytes: a blend that cut fields in normal order would leak them
        into red and blue."""
        red, green, blue = fields(self.lib.blend(gfx.c565(0, 255, 0), gfx.BLACK, 128))
        self.assertEqual((0, 0), (red, blue))
        self.assertLessEqual(abs(green - 63 / 2), 1)

    def test_the_blend_matches_the_reference(self):
        rng = random.Random(603)
        for _ in range(5000):
            fg, bg, alpha = rng.randrange(1 << 16), rng.randrange(1 << 16), rng.randrange(256)
            self.assertEqual(reference(fg, bg, alpha), self.lib.blend(fg, bg, alpha), (hex(fg), hex(bg), alpha))


if __name__ == "__main__":
    unittest.main()
