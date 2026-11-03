"""engine/core/fx_fire.c (P595) against a Python reference of its xorshift32, its step and its draw: clang builds it into
a temporary folder and ctypes calls it. The panel corners are checked against lcd.TftCanvas.fill's own map. Run from
the repository root: python3 -m unittest discover tests. --- MVP (P595) ---"""

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))

import lcd  # noqa: E402

FIRE_C = os.path.join(os.path.dirname(HERE), "engine", "core", "fx_fire.c")
W, H = 160, 120  # games/fire.py's field: the panel is 240 x 320
SEED, STEPS = 595, 50
SMALL_W, SMALL_H = 24, 18  # the reference steps in Python: a small field keeps the run short


class Field(ctypes.Structure):
    _fields_ = [("w", ctypes.c_int32), ("h", ctypes.c_int32), ("heat", ctypes.POINTER(ctypes.c_uint8)),
                ("rng", ctypes.c_uint32)]


def xorshift32(x):
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= x >> 17
    x ^= (x << 5) & 0xFFFFFFFF
    return x


def reference_step(heat, w, h, rng, steps, decay):
    """fx_fire_step in Python: the field changed in place, and the random state after it."""
    def at(x, y):
        return heat[y * w + x] if 0 <= x < w and 0 <= y < h else 0

    for _ in range(steps):
        for x in range(w):
            rng = xorshift32(rng)
            heat[(h - 1) * w + x] = rng >> 24
        for y in range(h - 1):
            for x in range(w):
                total = at(x - 1, y + 1) + at(x, y + 1) + at(x + 1, y + 1) + at(x, y + 2)
                heat[y * w + x] = min(255, total * decay >> 7)
    return rng


def reference_draw(heat, w, h, palette):
    """fx_fire_draw in Python: panel (px, py) shows cell ((2w - 1 - py) // 2, px // 2)."""
    pw, ph = 2 * h, 2 * w
    return [palette[heat[(px // 2) * w + (2 * w - 1 - py) // 2]] for py in range(ph) for px in range(pw)]


class PanelRecorder:
    """The s3lcd fill_rect calls TftCanvas makes, as panel rectangles."""

    def __init__(self):
        self.rects = []

    def fill_rect(self, x, y, w, h, c):
        self.rects.append((x, y, w, h))


@unittest.skipUnless(shutil.which("clang"), "clang is missing: engine/core/fx_fire.c is not built")
class FireCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        lib_path = os.path.join(cls.tmp.name, "libfire.so")
        subprocess.run(["clang", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-o", lib_path,
                        FIRE_C], check=True)
        cls.lib = ctypes.CDLL(lib_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def field(self, w, h, seed=SEED):
        heat = (ctypes.c_uint8 * (w * h))(*([7] * (w * h)))  # init must zero it
        f = Field()
        self.lib.fx_fire_init(ctypes.byref(f), heat, w, h, seed)
        return f, heat

    def draw(self, f, palette):
        panel = (ctypes.c_uint16 * (4 * f.w * f.h))(*([0xABCD] * (4 * f.w * f.h)))  # a sentinel no palette holds
        self.lib.fx_fire_draw(ctypes.byref(f), panel, (ctypes.c_uint16 * 256)(*palette))
        return list(panel)

    def test_init_zeroes_the_field_and_a_seed_of_0_is_1(self):
        f, heat = self.field(SMALL_W, SMALL_H, seed=0)
        self.assertEqual([0] * (SMALL_W * SMALL_H), list(heat))
        self.assertEqual(1, f.rng)

    def test_the_step_matches_the_reference(self):
        for decay in (31, 40):  # 40 lifts the sum past 255, so the clamp is reached too
            with self.subTest(decay=decay):
                f, heat = self.field(SMALL_W, SMALL_H)
                self.lib.fx_fire_step(ctypes.byref(f), STEPS, decay)
                ref = [0] * (SMALL_W * SMALL_H)
                rng = reference_step(ref, SMALL_W, SMALL_H, SEED, STEPS, decay)
                self.assertEqual(ref, list(heat), "the field byte for byte, edge cells reading 0 outside")
                self.assertEqual(rng, f.rng)
                if decay == 40:
                    self.assertIn(255, ref)

    def test_the_bottom_row_is_xorshift32(self):
        f, heat = self.field(4, 3)
        self.lib.fx_fire_step(ctypes.byref(f), 1, 0)  # decay 0: every row above the bottom stays 0
        rng, row = SEED, []
        for _ in range(4):
            rng = xorshift32(rng)
            row.append(rng >> 24)
        self.assertEqual([0] * 8 + row, list(heat))

    def test_the_draw_matches_the_reference_and_writes_every_pixel(self):
        f, heat = self.field(W, H)
        self.lib.fx_fire_step(ctypes.byref(f), 20, 31)
        palette = list(range(1000, 1256))
        panel = self.draw(f, palette)
        self.assertNotIn(0xABCD, panel)
        self.assertEqual(reference_draw(heat, W, H, palette), panel)

    def test_a_hot_cell_lands_where_tftcanvas_fills_it(self):
        palette = [0] * 256
        palette[200] = 0xF00F
        for cx, cy in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1), (37, 81)):  # the corners and one inside
            with self.subTest(cell=(cx, cy)):
                f, heat = self.field(W, H)
                heat[cy * W + cx] = 200
                panel = self.draw(f, palette)
                hot = {(i % (2 * H), i // (2 * H)) for i, c in enumerate(panel) if c == 0xF00F}
                tft = PanelRecorder()
                lcd.TftCanvas(tft).fill(2 * cx, 2 * cy, 2, 2, 0)  # the cell's 2 x 2 game pixels
                x, y, w, h = tft.rects[0]
                self.assertEqual({(x + i, y + j) for i in range(w) for j in range(h)}, hot)


if __name__ == "__main__":
    unittest.main()
