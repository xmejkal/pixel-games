"""engine/core/fx_fire.c (P595) against a Python reference of its xorshift32, its cooling map, its look, its step and its
draw: clang builds it into a temporary folder and ctypes calls it. The panel corners are checked against lcd.TftCanvas.fill's own map. Run from
the repository root: python3 -m unittest discover tests. --- MVP (P595) ---"""

import ctypes
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engine", "tests"))  # pixel-engine: clang_lib
sys.path.insert(0, HERE)

import lcd  # noqa: E402
from clang_lib import S3LCD_SRC  # noqa: E402  blend565.h, the blend fx_fire_blend shares
from test_blend import reference as reference_blend  # noqa: E402

FIRE_C = os.path.join(os.path.dirname(HERE), "engine", "core", "fx_fire.c")
W, H = 160, 120  # games/fire.py's field: the panel is 240 x 320
SEED, STEPS = 595, 50
SMALL_W, SMALL_H = 24, 18  # the reference steps in Python: a small field keeps the run short
MAP_W, MAP_H, MAX_SPOTS, MAX_EMBERS = 256, 32, 16, 24  # FX_FIRE_MAP_W, FX_FIRE_MAP_H, FX_FIRE_MAX_SPOTS and EMBERS
PART1 = (31, 0, 0, 0, 1, 0, 0, 0)  # the look at init: decay, cool, sway, spots, spread, fast, embers, fade
ALL_ON = (33, 90, 1, 5, 4, 120, 200, 21)  # decay 33 lifts sums past the hottest cell read, so the bound is reached too
PART2_AT_31 = (31, 24, 1, 12, 16, 0, 0, 0)  # part 2's look at decay 31, where the bound does nothing


class Field(ctypes.Structure):
    _fields_ = [("w", ctypes.c_int32), ("h", ctypes.c_int32), ("heat", ctypes.POINTER(ctypes.c_uint8)),
                ("cooling", ctypes.POINTER(ctypes.c_uint8)), ("rng", ctypes.c_uint32), ("map_row", ctypes.c_int32),
                ("fast_map_row", ctypes.c_int32), ("decay", ctypes.c_int32), ("cool", ctypes.c_int32),
                ("sway", ctypes.c_int32), ("spots", ctypes.c_int32), ("spread", ctypes.c_int32),
                ("fast", ctypes.c_int32), ("embers", ctypes.c_int32), ("fade", ctypes.c_int32),
                ("spot_x", ctypes.c_int32 * MAX_SPOTS)]
    _fields_ += [(name, ctypes.c_int32 * MAX_EMBERS) for name in ("ember_x", "ember_y", "ember_vx", "ember_vy",
                                                                   "ember_heat")]
    _fields_ += [("base", ctypes.c_int32)]  # --- MVP (P596) ---
    _fields_ += [("filter", ctypes.c_int32)]  # --- MVP (P608) ---
    _fields_ += [("born", ctypes.c_int32)]  # --- MVP (P747) ---


NEAREST, LINEAR = 0, 1  # FX_FIRE_NEAREST and FX_FIRE_LINEAR (P608)


def xorshift32(x):
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= x >> 17
    x ^= (x << 5) & 0xFFFFFFFF
    return x


class Reference:
    """fx_fire_t and its functions in Python, its random draws in the order fx_fire.c's comment gives."""

    def __init__(self, w, h, seed):
        self.w, self.h, self.rng, self.map_row, self.fast_map_row = w, h, seed or 1, 0, 0
        self.decay, self.cool, self.sway, self.spots, self.spread, self.fast, self.embers, self.fade = PART1
        self.ember = [[0] * 5 for _ in range(MAX_EMBERS)]  # x, y, vx, vy, heat: as fx_fire_t's ember arrays
        self.bound = True  # part 3's bound: False for the step without it
        self.base = True  # P596: False makes no bottom row and clears it
        self.heat = [0] * (w * h)
        self.cooling = [255 if self.draw() >> 28 == 0 else 0 for _ in range(MAP_W * MAP_H)]
        for _ in range(2):
            for k in range(MAP_H):
                self.blur_ring(k * MAP_W, MAP_W, 1)
            for k in range(MAP_W):
                self.blur_ring(k, MAP_H, MAP_W)
        lo, hi = min(self.cooling), max(self.cooling)
        self.cooling = [(v - lo) * 255 // (hi - lo) if hi > lo else 0 for v in self.cooling]
        self.place_spots()

    def draw(self):
        self.rng = xorshift32(self.rng)
        return self.rng

    def blur_ring(self, start, n, stride):
        cells = [start + i * stride for i in range(n)]
        old = [self.cooling[i] for i in cells]
        for i, at in enumerate(cells):
            self.cooling[at] = (old[i - 1] + old[i] + old[(i + 1) % n]) // 3

    def place_spots(self):
        self.spot_x = [self.draw() % self.w for _ in range(MAX_SPOTS)]

    def set_look(self, decay, cool, sway, spots, spread, fast, embers, fade):
        self.decay, self.cool, self.sway, self.spread = decay, cool, sway, spread
        self.fast, self.embers, self.fade = fast, embers, fade
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

    def step(self, steps, wind=0):
        w, h, heat = self.w, self.h, self.heat

        def at(x, y):
            return heat[y * w + x] if 0 <= x < w and 0 <= y < h else 0

        for _ in range(steps):
            if not self.base:
                heat[(h - 1) * w:] = [0] * w
            elif self.spots:
                heat[(h - 1) * w:] = self.spots_row()
            else:
                heat[(h - 1) * w:] = [self.draw() >> 24 for _ in range(w)]
            for y in range(h - 1):
                shift = 0
                if wind and self.draw() & 255 < abs(wind):
                    shift = -1 if wind > 0 else 1
                bits = 0
                for x in range(w):
                    c = x + shift
                    if self.sway:
                        if x % 16 == 0:
                            bits = self.draw()
                        c += (bits >> 1 & 1) + (bits & 1) - 1
                        bits >>= 2
                    d = 1  # a fast cell reads one row further down, unless its three cells would be past the bottom
                    fast = self.cooling[(y + self.fast_map_row) % MAP_H * MAP_W + (x + 128) % MAP_W] >= 256 - self.fast
                    if fast and y + 2 < h:
                        d = 2
                    read = (at(c - 1, y + d), at(c, y + d), at(c + 1, y + d), at(c, y + d + 1))
                    up = h - 1 - y  # the fade: fade sixteenths of a unit a row
                    loss = self.cooling[(y + self.map_row) % MAP_H * MAP_W + x % MAP_W] * self.cool >> 8
                    loss += ((up + 1) * self.fade >> 4) - (up * self.fade >> 4)
                    top = max(read) if self.bound else 255
                    heat[y * w + x] = max(0, min(top, sum(read) * self.decay >> 7) - loss)
            self.embers_step(wind)
            self.map_row = (self.map_row + 1) % MAP_H
            self.fast_map_row = (self.fast_map_row + 2) % MAP_H


    def embers_step(self, wind):
        w, h = self.w, self.h
        r = self.draw() if self.embers else 0
        free = [e for e in self.ember if e[4] == 0]
        if r & 255 < self.embers and free:
            x = self.spot_x[(r >> 8 & 255) % self.spots] if self.spots else (r >> 8) % w
            free[0][:] = [x * 256, (h - 2) * 256, (r >> 18 & 127) - 64 + int(wind / 8), -(2 + (r >> 16 & 3)) * 256, 255]
        for e in self.ember:
            if e[4]:
                e[0] += e[2]
                e[1] += e[3]
                e[4] -= 12
                if e[4] < 40 or e[0] < 0 or e[1] < 0 or e[0] >= w * 256:
                    e[4] = 0
                else:
                    at = e[1] // 256 * w + e[0] // 256
                    self.heat[at] = max(self.heat[at], e[4])


def part1_step(heat, w, h, rng, steps, decay, bound=True):
    """Part 1's fx_fire_step, as written then (at most 255) but with part 3's bound unless asked: the field changed in
    place, and the random state after it."""
    def at(x, y):
        return heat[y * w + x] if 0 <= x < w and 0 <= y < h else 0

    for _ in range(steps):
        for x in range(w):
            rng = xorshift32(rng)
            heat[(h - 1) * w + x] = rng >> 24
        for y in range(h - 1):
            for x in range(w):
                read = (at(x - 1, y + 1), at(x, y + 1), at(x + 1, y + 1), at(x, y + 2))
                heat[y * w + x] = min(max(read) if bound else 255, sum(read) * decay >> 7)
    return rng


def cdiv(a, b):
    """C's integer division, which truncates toward 0."""
    q = abs(a) // b
    return q if a >= 0 else -q


def reference_burn(heat, w, h, x0, y0, x1, y1, r, value):
    """fx_fire_burn in Python: each of the segment's points stamps a disc of radius r, the larger heat kept."""
    n = max(abs(x1 - x0), abs(y1 - y0))
    for i in range(n + 1):
        cx = x0 + (cdiv((x1 - x0) * i, n) if n else 0)
        cy = y0 + (cdiv((y1 - y0) * i, n) if n else 0)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = cx + dx, cy + dy
                if dx * dx + dy * dy <= r * r and 0 <= x < w and 0 <= y < h:
                    heat[y * w + x] = max(heat[y * w + x], value)


def reference_draw(heat, w, h, palette):
    """fx_fire_draw in Python: panel (px, py) shows cell ((2w - 1 - py) // 2, px // 2)."""
    pw, ph = 2 * h, 2 * w
    return [palette[heat[(px // 2) * w + (2 * w - 1 - py) // 2]] for py in range(ph) for px in range(pw)]


# --- MVP (P608) ---
def linear_heat(heat, w, h, gx, gy):
    """Game pixel (gx, gy)'s heat with bilinear filtering: GL_LINEAR's weights at 2x. The pixel sits a quarter cell
    from its cell's centre, toward the neighbour on its side, so it takes 9/16 of its cell, 3/16 of each side
    neighbour and 1/16 of the diagonal one. A neighbour past the edge is the edge cell (GL_CLAMP_TO_EDGE)."""
    x, y = gx // 2, gy // 2
    nx = min(w - 1, max(0, x + (1 if gx & 1 else -1)))
    ny = min(h - 1, max(0, y + (1 if gy & 1 else -1)))
    a, b, c, d = heat[y * w + x], heat[y * w + nx], heat[ny * w + x], heat[ny * w + nx]
    return (9 * a + 3 * b + 3 * c + d + 8) >> 4


def reference_draw_linear(heat, w, h, palette):
    """fx_fire_draw with LINEAR in Python: the game pixels first, then the panel map, panel (px, py) shows game pixel
    (2w - 1 - py, px)."""
    game = {(gx, gy): linear_heat(heat, w, h, gx, gy) for gx in range(2 * w) for gy in range(2 * h)}
    return [palette[game[(2 * w - 1 - py, px)]] for py in range(2 * w) for px in range(2 * h)]


def game_pixel(panel, w, h, gx, gy):
    """What the panel shows at game pixel (gx, gy)."""
    return panel[(2 * w - 1 - gx) * 2 * h + gy]


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
        subprocess.run(["clang", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-I", S3LCD_SRC,
                        "-o", lib_path, FIRE_C], check=True)
        cls.lib = ctypes.CDLL(lib_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def field(self, w, h, seed=SEED, look=None):
        heat = (ctypes.c_uint8 * (w * h))(*([7] * (w * h)))  # init must zero it
        cooling = (ctypes.c_uint8 * (MAP_W * MAP_H))()
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

    # --- MVP (P603) ---
    def blend(self, f, palette, alpha, background):
        panel = (ctypes.c_uint16 * len(background))(*background)
        self.lib.fx_fire_blend(ctypes.byref(f), panel, (ctypes.c_uint16 * 256)(*palette),
                               (ctypes.c_uint8 * 256)(*alpha))
        return list(panel)

    def random_scene(self, rng):
        """A field of random heats, a random palette and a random background of panel pixels."""
        f, heat = self.field(SMALL_W, SMALL_H)
        for i in range(SMALL_W * SMALL_H):
            heat[i] = rng.randrange(256)
        palette = [rng.randrange(1 << 16) for _ in range(256)]
        background = [rng.randrange(1 << 16) for _ in range(4 * SMALL_W * SMALL_H)]
        return f, heat, palette, background

    # --- MVP (P608) ---
    def random_field(self, rng, w, h, flt):
        f, heat = self.field(w, h)
        for i in range(w * h):
            heat[i] = rng.randrange(256)
        self.lib.fx_fire_set_filter(ctypes.byref(f), flt)
        return f, heat

    def test_init_sets_nearest(self):
        f, heat, cooling = Field(), (ctypes.c_uint8 * 4)(), (ctypes.c_uint8 * (MAP_W * MAP_H))()
        f.filter = LINEAR  # init must set it, not find it 0
        self.lib.fx_fire_init(ctypes.byref(f), heat, cooling, 2, 2, SEED)
        self.assertEqual(NEAREST, f.filter)

    def test_linear_draw_and_blend_match_the_reference(self):
        """Odd and even sizes, one row, one column and 1 x 1: byte for byte, every pixel written."""
        rng = random.Random(608)
        for w, h in ((SMALL_W, SMALL_H), (7, 5), (6, 9), (1, 1), (1, 4), (5, 1), (2, 2)):
            with self.subTest(w=w, h=h):
                f, heat = self.random_field(rng, w, h, LINEAR)
                palette = [rng.randrange(1 << 16) for _ in range(256)]
                palette[rng.randrange(256)] = 0xABCD + 1  # one colour next to the sentinel, so a mix-up shows
                panel = self.draw(f, palette)
                self.assertNotIn(0xABCD, panel)
                self.assertEqual(reference_draw_linear(list(heat), w, h, palette), panel)
                alpha = [rng.randrange(256) for _ in range(256)]
                alpha[0] = 0
                background = [rng.randrange(1 << 16) for _ in range(4 * w * h)]
                heats = reference_draw_linear(list(heat), w, h, list(range(256)))
                want = [bg if alpha[t] == 0 else reference_blend(palette[t], bg, alpha[t])
                        for t, bg in zip(heats, background)]
                self.assertEqual(want, self.blend(f, palette, alpha, background))

    # --- MVP (P646) --- the early-out: a cell too cold for any alpha but 0 skips its heats, with the same output
    def linear_blend_matches(self, heat_values, w, h, alpha, rng):
        """fx_fire_blend with LINEAR over heat_values gives the reference's pixels, each blended at its heat's alpha."""
        f, heat = self.field(w, h)
        heat[:] = heat_values
        self.lib.fx_fire_set_filter(ctypes.byref(f), LINEAR)
        palette = [rng.randrange(1 << 16) for _ in range(256)]
        background = [rng.randrange(1 << 16) for _ in range(4 * w * h)]
        heats = reference_draw_linear(list(heat_values), w, h, list(range(256)))
        want = [bg if alpha[t] == 0 else reference_blend(palette[t], bg, alpha[t]) for t, bg in zip(heats, background)]
        self.assertEqual(want, self.blend(f, palette, alpha, background))

    def test_linear_blend_skips_cold_cells_byte_for_byte(self):
        """A table clear below heat 101 with a hole at 150, over cold fields of varied heats with hot blocks and single
        hot cells: a skipped cell still moves its mixes on, so the next blended cell reads the right ones."""
        rng = random.Random(646)
        alpha = [0 if t < 101 else (t - 100) * 255 // 130 if t < 230 else 255 for t in range(256)]
        alpha[150] = 0
        for w, h in ((SMALL_W, SMALL_H), (7, 5), (6, 9), (1, 4), (5, 1)):
            with self.subTest(w=w, h=h):
                heat = [rng.randrange(1, 101) for _ in range(w * h)]  # cold, never all 0
                for _ in range(max(1, w * h // 12)):  # single hot cells, some at the edges
                    heat[rng.randrange(w * h)] = rng.randrange(101, 256)
                x0, y0 = rng.randrange(w), rng.randrange(h)  # one hot block
                for y in range(y0, min(h, y0 + 3)):
                    for x in range(x0, min(w, x0 + 3)):
                        heat[y * w + x] = rng.randrange(140, 256)
                self.linear_blend_matches(heat, w, h, alpha, rng)

    def test_linear_blend_reads_the_cells_above_and_below(self):
        """A hot cell on the top row and one on the bottom row of a cold field: the cells next to them blend only if the
        check reads both down and up."""
        w, h = 5, 6
        heat = [90] * (w * h)  # mixes of 360 skip, and a hot cell beside lifts a pixel to heat 121
        heat[2], heat[(h - 1) * w + 3] = 255, 255
        self.linear_blend_matches(heat, w, h, [0] * 101 + [255] * 155, random.Random(651))

    def test_linear_blend_mixes_a_heat_of_exactly_the_first_visible(self):
        """Columns of heat T - 1 and T + 1 make the mixes 3(T - 1) + T + 1 = 4T - 2 down a T - 1 column, so its pixels
        have heat T, the first one with alpha, and must blend: the largest mix a cell may skip at is 4T - 3. T 101 is
        FRONT_ALPHA's, T 1 the picture field's."""
        w, h = 8, 6
        for first in (101, 1):
            with self.subTest(first=first):
                alpha = [0] * first + [255] * (256 - first)
                heat = [first - 1 if x % 2 == 0 else first + 1 for _ in range(h) for x in range(w)]
                self.linear_blend_matches(heat, w, h, alpha, random.Random(647))

    def test_linear_blend_at_alpha_of_heat_0_mixes_a_cold_field(self):
        self.linear_blend_matches([0] * (6 * 5), 6, 5, [9] + [0] * 255, random.Random(648))

    def test_linear_blend_at_every_alpha_0_leaves_the_background(self):
        self.linear_blend_matches([random.Random(649).randrange(256) for _ in range(35)], 7, 5, [0] * 256,
                                  random.Random(650))

    def test_nearest_after_linear_is_the_old_draw(self):
        f, heat = self.random_field(random.Random(609), SMALL_W, SMALL_H, LINEAR)
        self.lib.fx_fire_set_filter(ctypes.byref(f), NEAREST)
        palette = list(range(1000, 1256))
        self.assertEqual(reference_draw(list(heat), SMALL_W, SMALL_H, palette), self.draw(f, palette))

    def test_linear_draws_a_field_of_one_heat_flat(self):
        f, heat = self.field(7, 5)
        for i in range(7 * 5):
            heat[i] = 77
        self.lib.fx_fire_set_filter(ctypes.byref(f), LINEAR)
        self.assertEqual([77] * (4 * 7 * 5), self.draw(f, list(range(256))))

    def test_linear_clamps_at_the_four_edges(self):
        """An edge pixel takes the 1-D value (3a + c + 2) >> 2 along its edge, a corner pixel its own cell."""
        w, h = 7, 5
        f, heat = self.random_field(random.Random(610), w, h, LINEAR)
        panel = self.draw(f, list(range(256)))
        for gx in range(2 * w):
            for gy in range(2 * h):
                at_x, at_y = gx in (0, 2 * w - 1), gy in (0, 2 * h - 1)
                if not (at_x or at_y):
                    continue
                x, y = gx // 2, gy // 2
                a = heat[y * w + x]
                if at_x and at_y:
                    want = a
                elif at_x:
                    want = (3 * a + heat[(y + (1 if gy & 1 else -1)) * w + x] + 2) >> 2
                else:
                    want = (3 * a + heat[y * w + x + (1 if gx & 1 else -1)] + 2) >> 2
                self.assertEqual(want, game_pixel(panel, w, h, gx, gy), (gx, gy))
        one, heat = self.field(1, 1)
        heat[0] = 201
        self.lib.fx_fire_set_filter(ctypes.byref(one), LINEAR)
        self.assertEqual([201] * 4, self.draw(one, list(range(256))))

    def test_an_impulse_spreads_to_its_facing_pixels_only(self):
        """255 in cell (4, 3): 143 on its own four pixels, 48 on each side neighbour's two facing pixels, 16 on each
        diagonal's facing pixel, 0 elsewhere. A plain mean of the four cells or a half-pixel shift draws otherwise."""
        w, h = 8, 6
        f, heat = self.field(w, h)
        heat[3 * w + 4] = 255
        self.lib.fx_fire_set_filter(ctypes.byref(f), LINEAR)
        panel = self.draw(f, list(range(256)))
        want = {(gx, gy): 0 for gx in range(2 * w) for gy in range(2 * h)}
        for gx, gy in ((8, 6), (9, 6), (8, 7), (9, 7)):
            want[(gx, gy)] = 143
        for gx, gy in ((7, 6), (7, 7), (10, 6), (10, 7), (8, 5), (9, 5), (8, 8), (9, 8)):
            want[(gx, gy)] = 48
        for gx, gy in ((7, 5), (10, 5), (7, 8), (10, 8)):
            want[(gx, gy)] = 16
        self.assertEqual(want, {(gx, gy): game_pixel(panel, w, h, gx, gy) for gx, gy in want})

    def test_blend_at_alpha_0_leaves_the_background(self):
        f, _, palette, background = self.random_scene(random.Random(603))
        self.assertEqual(background, self.blend(f, palette, [0] * 256, background))

    def test_blend_at_alpha_255_gives_the_draw(self):
        f, _, palette, background = self.random_scene(random.Random(604))
        self.assertEqual(self.draw(f, palette), self.blend(f, palette, [255] * 256, background))

    def test_blend_mixes_each_pixel_at_its_heats_alpha(self):
        """Each of a cell's four panel pixels is blended over its own background: rows 2k and 2k + 1 differ."""
        rng = random.Random(605)
        f, heat, palette, background = self.random_scene(rng)
        alpha = [rng.randrange(256) for _ in range(256)]
        heats = reference_draw(list(heat), SMALL_W, SMALL_H, list(range(256)))  # the heat each panel pixel shows
        want = [reference_blend(palette[t], bg, alpha[t]) for t, bg in zip(heats, background)]
        self.assertEqual(want, self.blend(f, palette, alpha, background))

    # --- MVP (P596) ---
    def test_with_the_base_off_the_step_matches_the_reference(self):
        """No bottom row and no draw for it: the RNG order still matches, and the bottom row is cleared."""
        f, heat = self.field(SMALL_W, SMALL_H, look=ALL_ON)
        ref = Reference(SMALL_W, SMALL_H, SEED)
        ref.set_look(*ALL_ON)
        self.lib.fx_fire_set_base(ctypes.byref(f), 0)
        ref.base = False
        self.lib.fx_fire_burn(ctypes.byref(f), 3, SMALL_H - 1, 20, SMALL_H - 1, 2, 250)  # a burn on the bottom row
        reference_burn(ref.heat, SMALL_W, SMALL_H, 3, SMALL_H - 1, 20, SMALL_H - 1, 2, 250)
        for _ in range(STEPS):
            self.lib.fx_fire_step(ctypes.byref(f), 1, 0)
            ref.step(1)
            self.assertEqual((ref.rng, ref.heat), (f.rng, list(heat)))
        self.assertEqual([0] * SMALL_W, list(heat)[-SMALL_W:])

    def test_a_zero_field_with_the_base_off_stays_zero(self):
        f, heat = self.field(SMALL_W, SMALL_H, look=PART2_AT_31)
        self.lib.fx_fire_set_base(ctypes.byref(f), 0)
        self.lib.fx_fire_step(ctypes.byref(f), 20, 0)
        self.assertEqual([0] * (SMALL_W * SMALL_H), list(heat))

    def test_init_turns_the_base_on(self):
        f, _ = self.field(SMALL_W, SMALL_H)
        self.assertEqual(1, f.base)

    def test_burn_matches_the_reference(self):
        """Random segments, some past every edge, over random heats: each cell keeps the larger heat."""
        rng = random.Random(596)
        for _ in range(300):
            f, heat = self.field(SMALL_W, SMALL_H)
            for i in range(SMALL_W * SMALL_H):
                heat[i] = rng.randrange(256)
            ref = list(heat)
            args = [rng.randrange(-8, SMALL_W + 8), rng.randrange(-8, SMALL_H + 8), rng.randrange(-8, SMALL_W + 8),
                    rng.randrange(-8, SMALL_H + 8), rng.randrange(0, 5), rng.randrange(256)]
            self.lib.fx_fire_burn(ctypes.byref(f), *args)
            reference_burn(ref, SMALL_W, SMALL_H, *args)
            self.assertEqual(ref, list(heat), args)

    def test_a_burn_covers_its_whole_segment(self):
        f, heat = self.field(SMALL_W, SMALL_H)
        self.lib.fx_fire_burn(ctypes.byref(f), 2, 5, 20, 5, 0, 200)
        row = list(heat)[5 * SMALL_W:6 * SMALL_W]
        self.assertEqual([0, 0] + [200] * 19 + [0] * (SMALL_W - 21), row)

    # --- MVP (P602) ---
    def test_scroll_moves_every_row_and_clears_what_it_uncovers(self):
        """Exact bytes on a 6 x 3 field of distinct heats: -3 moves left, +2 right, 0 keeps the field."""
        for dx, row0 in ((-3, [4, 5, 6, 0, 0, 0]), (2, [0, 0, 1, 2, 3, 4]), (0, [1, 2, 3, 4, 5, 6])):
            with self.subTest(dx=dx):
                f, heat = self.field(6, 3)
                heat[:] = list(range(1, 19))
                self.lib.fx_fire_scroll(ctypes.byref(f), dx)
                self.assertEqual([v + 6 * y if v else 0 for y in range(3) for v in row0], list(heat))

    def test_a_scroll_of_the_width_or_more_clears_the_field(self):
        for dx in (-6, -11, 6, 11):
            with self.subTest(dx=dx):
                f, heat = self.field(6, 3)
                heat[:] = list(range(1, 19))
                self.lib.fx_fire_scroll(ctypes.byref(f), dx)
                self.assertEqual([0] * 18, list(heat))

    def test_a_scroll_moves_the_live_embers_only(self):
        f, _ = self.field(SMALL_W, SMALL_H)
        f.ember_x[0], f.ember_heat[0] = 10 * 256 + 7, 200
        f.ember_x[1], f.ember_heat[1] = 10 * 256, 0
        self.lib.fx_fire_scroll(ctypes.byref(f), -4)
        self.assertEqual((6 * 256 + 7, 10 * 256), (f.ember_x[0], f.ember_x[1]))

    def test_take_births_counts_each_new_ember_once(self):  # --- MVP (P747) ---
        f, _ = self.field(SMALL_W, SMALL_H, look=ALL_ON)
        seen = 0
        for _ in range(STEPS):
            self.lib.fx_fire_step(ctypes.byref(f), 1, 0)
            seen += sum(1 for heat in f.ember_heat if heat == 255 - 12)  # a new ember has cooled one step
        births = self.lib.fx_fire_take_births(ctypes.byref(f))
        self.assertEqual((seen, 0), (births, self.lib.fx_fire_take_births(ctypes.byref(f))))
        self.assertGreater(births, 0)

    def test_a_draw_with_every_ember_slot_taken_is_no_birth(self):  # --- MVP (P747) ---
        f, _ = self.field(SMALL_W, SMALL_H, look=(31, 0, 0, 0, 1, 0, 255, 0))
        for i in range(MAX_EMBERS):
            f.ember_x[i], f.ember_y[i], f.ember_heat[i] = 5 * 256, 5 * 256, 200
        self.lib.fx_fire_step(ctypes.byref(f), 1, 0)
        self.assertEqual(0, self.lib.fx_fire_take_births(ctypes.byref(f)))

    def test_init_zeroes_the_field_and_a_seed_of_0_is_1(self):
        f, heat = self.field(SMALL_W, SMALL_H, seed=0)
        self.assertEqual([0] * (SMALL_W * SMALL_H), list(heat))
        self.assertEqual(Reference(SMALL_W, SMALL_H, 0).rng, f.rng)  # the map's and the spots' draws from 1

    def test_init_makes_the_map_and_the_spots_of_the_reference(self):
        f, _ = self.field(SMALL_W, SMALL_H)
        ref = Reference(SMALL_W, SMALL_H, SEED)
        self.assertEqual(ref.cooling, list(f.cooling[:MAP_W * MAP_H]))
        self.assertEqual((0, 255), (min(ref.cooling), max(ref.cooling)))  # stretched
        self.assertEqual(ref.spot_x, list(f.spot_x))
        self.assertEqual((ref.rng, PART1), (f.rng, (f.decay, f.cool, f.sway, f.spots, f.spread, f.fast, f.embers,
                                                f.fade)))

    def test_the_step_matches_the_reference(self):
        for w, h, look, wind in ((SMALL_W, SMALL_H, ALL_ON, 0), (SMALL_W, SMALL_H, PART1, 0),
                                 (3, 4, (31, 0, 1, 0, 1, 0, 0, 0), 0), (SMALL_W, SMALL_H, (31, 0, 1, 0, 1, 0, 0, 0), 0),
                                 (3, 4, (40, 60, 1, 2, 2, 255, 255, 255), 0), (1, 4, ALL_ON, 0),
                                 (1, 4, (31, 0, 0, 0, 1, 255, 0, 0), 0),
                                 (SMALL_W, SMALL_H, ALL_ON, 200), (SMALL_W, SMALL_H, ALL_ON, -200), (3, 4, PART1, 255),
                                 (SMALL_W, SMALL_H, (31, 0, 1, 0, 1, 0, 255, 0), 100), (2, 3, ALL_ON, 0),
                                 (1, 4, ALL_ON, -255), (4, 40, (31, 0, 0, 0, 1, 0, 255, 0), 255)):
            # sway and wind on 3 x 4 and 1 x 4 read at 0 and w - 1, and 4 x 40 with embers at full wind sends embers
            # past the right edge. Outside cells read 0 in both, so a read past the edge shows only if memory there is
            # not 0: the edge reads are checked by the mutation run, not proven here.
            with self.subTest(w=w, h=h, look=look, wind=wind):
                f, heat = self.field(w, h, look=look)
                self.lib.fx_fire_step(ctypes.byref(f), STEPS, wind)
                ref = Reference(w, h, SEED)
                ref.set_look(*look)
                ref.step(STEPS, wind)
                self.assertEqual(ref.heat, list(heat), "the field byte for byte, edge cells reading 0 outside")
                self.assertEqual((ref.rng, ref.map_row, ref.fast_map_row, ref.spot_x),
                                 (f.rng, f.map_row, f.fast_map_row, list(f.spot_x)))
                self.assertEqual(ref.ember, [[f.ember_x[i], f.ember_y[i], f.ember_vx[i], f.ember_vy[i],
                                              f.ember_heat[i]] for i in range(MAX_EMBERS)])
                if look == ALL_ON and w == SMALL_W and wind == 0:
                    self.assertIn(0, ref.heat[:-w])  # the map cut the flames
                    self.assertNotEqual(ref.heat[-w:], [0] * w)  # the spots heat the base
                    slow = Reference(w, h, SEED)
                    slow.set_look(*look[:5], 0, *look[6:])
                    slow.step(STEPS)
                    self.assertNotEqual(slow.heat, ref.heat)  # fast cells took part
                    self.assertTrue(any(e[4] for e in ref.ember))  # embers fly
                    still = Reference(w, h, SEED)
                    still.set_look(*look[:6], 0, look[7])
                    still.step(STEPS)
                    self.assertNotEqual(still.heat, ref.heat)  # and left heat in the field

    def test_the_wind_blows_the_flames_its_way(self):
        """A byte for byte reference would share a wrong sign, so: after 100 steps on the real field, the heat-weighted
        mean column of the top half lies right of the same seed's at wind 0 with wind 255, and left with -255."""
        def mean_column(wind):
            f, heat = self.field(W, H, look=(33, 24, 1, 12, 16, 128, 0, 0))
            self.lib.fx_fire_step(ctypes.byref(f), 100, wind)
            top = heat[:H // 2 * W]
            return sum(v * (i % W) for i, v in enumerate(top)) / max(1, sum(top))

        still = mean_column(0)
        self.assertGreater(mean_column(255), still)
        self.assertLess(mean_column(-255), still)

    def test_at_decay_31_the_bound_does_nothing(self):
        """Part 2's look at decay 31 gives the field of the step without the bound. Part 3's 256 x 32 map (the PO's
        three columns: the 64-wide map repeated at x, x + 64 and x + 128) ended byte equality with part 2's kernel."""
        f, heat = self.field(SMALL_W, SMALL_H, look=PART2_AT_31)
        self.lib.fx_fire_step(ctypes.byref(f), STEPS, 0)
        ref = Reference(SMALL_W, SMALL_H, SEED)
        ref.set_look(*PART2_AT_31)
        ref.bound = False
        ref.step(STEPS)
        self.assertEqual(ref.heat, list(heat))
        self.assertNotEqual([0] * (SMALL_W * SMALL_H), ref.heat)

    def test_part_1s_look_is_part_1s_step(self):
        for decay in (31, 40):  # 40 lifts the sum past the hottest cell read, so the bound is reached too
            with self.subTest(decay=decay):
                f, heat = self.field(SMALL_W, SMALL_H, look=(decay, 0, 0, 0, 1, 0, 0, 0))
                rng = f.rng
                self.lib.fx_fire_step(ctypes.byref(f), STEPS, 0)
                ref = [0] * (SMALL_W * SMALL_H)
                self.assertEqual(part1_step(ref, SMALL_W, SMALL_H, rng, STEPS, decay), f.rng)
                self.assertEqual(ref, list(heat))
                if decay == 40:
                    unbound = [0] * (SMALL_W * SMALL_H)
                    part1_step(unbound, SMALL_W, SMALL_H, rng, STEPS, decay, bound=False)
                    self.assertIn(255, unbound)
                    self.assertNotEqual(unbound, ref)

    def test_a_new_spot_count_places_the_spots_again(self):
        f, _ = self.field(SMALL_W, SMALL_H, look=ALL_ON)
        rng, spots = f.rng, list(f.spot_x)
        self.lib.fx_fire_set_look(ctypes.byref(f), *ALL_ON)  # the same count: no draw
        self.assertEqual((rng, spots), (f.rng, list(f.spot_x)))
        self.lib.fx_fire_set_look(ctypes.byref(f), 31, 0, 0, 3, 4, 0, 0, 0)
        self.assertNotEqual(rng, f.rng)

    def test_the_bottom_row_is_xorshift32(self):
        f, heat = self.field(4, 3, look=(0, 0, 0, 0, 1, 0, 0, 0))
        rng, row = f.rng, []
        self.lib.fx_fire_step(ctypes.byref(f), 1, 0)  # decay 0: every row above the bottom stays 0
        for _ in range(4):
            rng = xorshift32(rng)
            row.append(rng >> 24)
        self.assertEqual([0] * 8 + row, list(heat))

    def test_the_draw_matches_the_reference_and_writes_every_pixel(self):
        f, heat = self.field(W, H)
        self.lib.fx_fire_step(ctypes.byref(f), 20, 0)
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
