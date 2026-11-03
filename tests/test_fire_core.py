"""engine/core/fx_fire.c (P595) against a Python reference of its xorshift32, its cooling map, its look, its step and its
draw: clang builds it into a temporary folder and ctypes calls it. The panel corners are checked against lcd.TftCanvas.fill's own map. Run from
the repository root: python3 -m unittest discover tests. --- MVP (P595) ---"""

import ctypes
import hashlib
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
MAP, MAX_SPOTS = 64, 16  # FX_FIRE_MAP and FX_FIRE_MAX_SPOTS
PART1 = (31, 0, 0, 0, 1)  # the look at init: decay, cool, sway, spots, spread
ALL_ON = (33, 90, 1, 5, 4)  # decay 33 lifts sums past 255, so the clamp is reached too
# Part 2's look at decay 31 (the bound does nothing there): the small field's sha256 after STEPS steps with commit
# c4e232f's kernel, recorded from that commit's fx_fire.c before part 3 changed it
GOLDEN_LOOK = (31, 24, 1, 12, 16)
GOLDEN = "e68a78bfe9ed3a12129f40964e4779a13813d6e79c6788022da14b0b79d32677"


class Field(ctypes.Structure):
    _fields_ = [("w", ctypes.c_int32), ("h", ctypes.c_int32), ("heat", ctypes.POINTER(ctypes.c_uint8)),
                ("cooling", ctypes.POINTER(ctypes.c_uint8)), ("rng", ctypes.c_uint32), ("scroll", ctypes.c_int32),
                ("decay", ctypes.c_int32), ("cool", ctypes.c_int32), ("sway", ctypes.c_int32),
                ("spots", ctypes.c_int32), ("spread", ctypes.c_int32), ("spot_x", ctypes.c_int32 * MAX_SPOTS)]


def xorshift32(x):
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= x >> 17
    x ^= (x << 5) & 0xFFFFFFFF
    return x


class Reference:
    """fx_fire_t and its functions in Python, its random draws in the order fx_fire.c's comment gives."""

    def __init__(self, w, h, seed):
        self.w, self.h, self.rng, self.scroll = w, h, seed or 1, 0
        self.decay, self.cool, self.sway, self.spots, self.spread = PART1
        self.heat = [0] * (w * h)
        self.cooling = [255 if self.draw() >> 28 == 0 else 0 for _ in range(MAP * MAP)]
        for _ in range(2):
            for k in range(MAP):
                self.blur_ring(k * MAP, 1)
            for k in range(MAP):
                self.blur_ring(k, MAP)
        lo, hi = min(self.cooling), max(self.cooling)
        self.cooling = [(v - lo) * 255 // (hi - lo) if hi > lo else 0 for v in self.cooling]
        self.place_spots()

    def draw(self):
        self.rng = xorshift32(self.rng)
        return self.rng

    def blur_ring(self, start, stride):
        cells = [start + i * stride for i in range(MAP)]
        old = [self.cooling[i] for i in cells]
        for i, at in enumerate(cells):
            self.cooling[at] = (old[i - 1] + old[i] + old[(i + 1) % MAP]) // 3

    def place_spots(self):
        self.spot_x = [self.draw() % self.w for _ in range(MAX_SPOTS)]

    def set_look(self, decay, cool, sway, spots, spread):
        self.decay, self.cool, self.sway, self.spread = decay, cool, sway, spread
        if spots != self.spots:
            self.spots = spots
            self.place_spots()

    def spots_row(self):
        w = self.w
        for i in range(self.spots):
            r = self.draw()
            if r >> 26 == 0:
                self.spot_x[i] = (r >> 8) % w
            else:
                self.spot_x[i] = min(w - 1, max(0, self.spot_x[i] + r % 3 - 1))
        row = [0] * w
        for x0 in self.spot_x[:self.spots]:
            for dx in range(-self.spread, self.spread + 1):
                if 0 <= x0 + dx < w:
                    row[x0 + dx] = max(row[x0 + dx], 255 - abs(dx) * 255 // (self.spread + 1))
        return [v * (128 + (self.draw() >> 25)) >> 8 for v in row]

    def step(self, steps):
        w, h, heat = self.w, self.h, self.heat

        def at(x, y):
            return heat[y * w + x] if 0 <= x < w and 0 <= y < h else 0

        for _ in range(steps):
            heat[(h - 1) * w:] = self.spots_row() if self.spots else [self.draw() >> 24 for _ in range(w)]
            for y in range(h - 1):
                bits = 0
                for x in range(w):
                    c = x
                    if self.sway:
                        if x % 16 == 0:
                            bits = self.draw()
                        c += (bits >> 1 & 1) + (bits & 1) - 1
                        bits >>= 2
                    total = at(c - 1, y + 1) + at(c, y + 1) + at(c + 1, y + 1) + at(c, y + 2)
                    loss = self.cooling[(y + self.scroll) % MAP * MAP + x % MAP] * self.cool >> 8
                    heat[y * w + x] = max(0, min(255, total * self.decay >> 7) - loss)
            self.scroll = (self.scroll + 1) % MAP


def part1_step(heat, w, h, rng, steps, decay):
    """Part 1's fx_fire_step, as written then: the field changed in place, and the random state after it."""
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

    def field(self, w, h, seed=SEED, look=None):
        heat = (ctypes.c_uint8 * (w * h))(*([7] * (w * h)))  # init must zero it
        cooling = (ctypes.c_uint8 * (MAP * MAP))()
        f = Field()
        self.lib.fx_fire_init(ctypes.byref(f), heat, cooling, w, h, seed)
        f.keep = cooling  # the map lives as long as the field
        if look:
            self.lib.fx_fire_set_look(ctypes.byref(f), *look)
        return f, heat

    def draw(self, f, palette):
        panel = (ctypes.c_uint16 * (4 * f.w * f.h))(*([0xABCD] * (4 * f.w * f.h)))  # a sentinel no palette holds
        self.lib.fx_fire_draw(ctypes.byref(f), panel, (ctypes.c_uint16 * 256)(*palette))
        return list(panel)

    def test_init_zeroes_the_field_and_a_seed_of_0_is_1(self):
        f, heat = self.field(SMALL_W, SMALL_H, seed=0)
        self.assertEqual([0] * (SMALL_W * SMALL_H), list(heat))
        self.assertEqual(Reference(SMALL_W, SMALL_H, 0).rng, f.rng)  # the map's and the spots' draws from 1

    def test_init_makes_the_map_and_the_spots_of_the_reference(self):
        f, _ = self.field(SMALL_W, SMALL_H)
        ref = Reference(SMALL_W, SMALL_H, SEED)
        self.assertEqual(ref.cooling, list(f.cooling[:MAP * MAP]))
        self.assertEqual((0, 255), (min(ref.cooling), max(ref.cooling)))  # stretched
        self.assertEqual(ref.spot_x, list(f.spot_x))
        self.assertEqual((ref.rng, PART1), (f.rng, (f.decay, f.cool, f.sway, f.spots, f.spread)))

    def test_the_step_matches_the_reference(self):
        for w, h, look in ((SMALL_W, SMALL_H, ALL_ON), (SMALL_W, SMALL_H, PART1), (3, 4, (31, 0, 1, 0, 1)),
                           (SMALL_W, SMALL_H, (31, 0, 1, 0, 1)), (3, 4, (40, 60, 1, 2, 2)), (1, 4, ALL_ON)):
            with self.subTest(w=w, h=h, look=look):  # sway on 3 x 4 and 1 x 4: an unguarded read at 0 or w - 1 shows
                f, heat = self.field(w, h, look=look)
                self.lib.fx_fire_step(ctypes.byref(f), STEPS)
                ref = Reference(w, h, SEED)
                ref.set_look(*look)
                ref.step(STEPS)
                self.assertEqual(ref.heat, list(heat), "the field byte for byte, edge cells reading 0 outside")
                self.assertEqual((ref.rng, ref.scroll, ref.spot_x), (f.rng, f.scroll, list(f.spot_x)))
                if look == ALL_ON and w == SMALL_W:
                    self.assertIn(0, ref.heat[:-w])  # the map cut the flames
                    self.assertNotEqual(ref.heat[-w:], [0] * w)  # the spots heat the base

    def test_part_2s_look_at_decay_31_is_part_2s_field(self):
        f, heat = self.field(SMALL_W, SMALL_H, look=GOLDEN_LOOK)
        self.lib.fx_fire_step(ctypes.byref(f), STEPS)
        self.assertEqual(GOLDEN, hashlib.sha256(bytes(heat)).hexdigest())

    def test_part_1s_look_is_part_1s_step(self):
        for decay in (31, 40):  # 40 lifts the sum past 255, so the clamp is reached too
            with self.subTest(decay=decay):
                f, heat = self.field(SMALL_W, SMALL_H, look=(decay, 0, 0, 0, 1))
                rng = f.rng
                self.lib.fx_fire_step(ctypes.byref(f), STEPS)
                ref = [0] * (SMALL_W * SMALL_H)
                self.assertEqual(part1_step(ref, SMALL_W, SMALL_H, rng, STEPS, decay), f.rng)
                self.assertEqual(ref, list(heat))
                if decay == 40:
                    self.assertIn(255, ref)

    def test_a_new_spot_count_places_the_spots_again(self):
        f, _ = self.field(SMALL_W, SMALL_H, look=ALL_ON)
        rng, spots = f.rng, list(f.spot_x)
        self.lib.fx_fire_set_look(ctypes.byref(f), *ALL_ON)  # the same count: no draw
        self.assertEqual((rng, spots), (f.rng, list(f.spot_x)))
        self.lib.fx_fire_set_look(ctypes.byref(f), 31, 0, 0, 3, 4)
        self.assertNotEqual(rng, f.rng)

    def test_the_bottom_row_is_xorshift32(self):
        f, heat = self.field(4, 3, look=(0, 0, 0, 0, 1))
        rng, row = f.rng, []
        self.lib.fx_fire_step(ctypes.byref(f), 1)  # decay 0: every row above the bottom stays 0
        for _ in range(4):
            rng = xorshift32(rng)
            row.append(rng >> 24)
        self.assertEqual([0] * 8 + row, list(heat))

    def test_the_draw_matches_the_reference_and_writes_every_pixel(self):
        f, heat = self.field(W, H)
        self.lib.fx_fire_step(ctypes.byref(f), 20)
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
