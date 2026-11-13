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
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engine", "tests"))  # pixel-engine: clang_lib
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

import fire  # noqa: E402
import lcd  # noqa: E402

from clang_lib import S3LCD_SRC  # noqa: E402  blend565.h

FIRE_C = os.path.join(os.path.dirname(HERE), "engine", "core", "fx_fire.c")
FRAME_MS = 40  # app.py's FRAME_MS
REPORT = re.compile(r"^fire (linear|picture|nearest) fps \d+ step \d+\.\d\d draw \d+\.\d\d$", re.M)
SEED_WIND = 595  # the gust test's seed for Python's random
LAYER_LOOK = (32, 40, 1, 0, 1, 128, 0, 16)  # P602: a FireLayer's look in the tests, burning's numbers


sys.path.insert(0, HERE)
from test_fire_core import MAP_H, MAP_W, Field  # noqa: E402  fx_fire_t and its map


class Tft:
    """The s3lcd display: its frame, and the blits it was asked for."""

    def __init__(self):
        self.frame, self.blits = bytearray(lcd.PANEL_W * lcd.PANEL_H * 2), []

    def blit_buffer(self, buf, *args):
        self.blits.append(args)

    def fill_rect(self, x, y, w, h, c):
        """A panel rectangle into the frame, each pixel a native uint16 as the C draw writes it (P639), so a render
        through lcd.TftCanvas shows the fills under the field."""
        px = memoryview(self.frame).cast("H")
        for row in range(y, y + h):
            px[row * lcd.PANEL_W + x:row * lcd.PANEL_W + x + w] = array("H", [c] * w)


class Recorder:
    """A canvas with a tft, that keeps each fill as (x, y, w, h) and ignores the text."""

    def __init__(self, tft):
        self.tft, self.fills = tft, []

    def fill(self, x, y, w, h, c):
        self.fills.append((int(x), int(y), int(w), int(h)))

    def text(self, *args):
        pass


class Engine:
    """The engine module's HeatField, largest_free_internal, NEAREST and LINEAR (engine/binding.c), on fx_fire.c
    through ctypes. looks keeps each set_look's numbers, filters each set_filter's, cools each cool's. cool=False makes
    HeatField the firmware's before P803, which has no cool (P803)."""

    NEAREST, LINEAR = 0, 1  # --- MVP (P608) ---

    def __init__(self, lib, cool=True):
        engine = self

        class OldHeatField:  # the firmware built from an engine before P803
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

            def set_filter(self, mag_filter):  # P608
                engine.filters.append(mag_filter)
                lib.fx_fire_set_filter(ctypes.byref(self.f), mag_filter)

            def take_births(self, rises=None):  # P747, P751: the binding's, with rises an array("b") or None
                if rises is None:
                    return lib.fx_fire_take_births(ctypes.byref(self.f), None, 0)
                return lib.fx_fire_take_births(ctypes.byref(self.f), ctypes.c_void_p(rises.buffer_info()[0]),
                                               len(rises))

            def stats(self, threshold=48):  # --- MVP (P753) --- the binding's: (total, height)
                total, height = ctypes.c_int32(), ctypes.c_int32()
                lib.fx_fire_stats(ctypes.byref(self.f), threshold, ctypes.byref(total), ctypes.byref(height))
                engine.stats_calls += 1
                return total.value, height.value

            def set_base(self, on):  # P596
                lib.fx_fire_set_base(ctypes.byref(self.f), 1 if on else 0)

            def burn(self, *args):  # P596
                engine.burns.append(args)
                lib.fx_fire_burn(ctypes.byref(self.f), *args)

            def scroll(self, dx):  # --- MVP (P602) --- with the binding's check
                if not -1024 <= dx <= 1024:
                    raise ValueError("dx is -1024 to 1024")
                engine.scrolls.append(dx)
                lib.fx_fire_scroll(ctypes.byref(self.f), dx)

            def draw(self, tft, palette, alpha=None):
                engine.targets.append("tft" if alpha is None else "tft alpha")
                engine.alphas.append(alpha)  # P639: the tables that reach the C draw
                engine.palettes.append(palette)
                out = (ctypes.c_uint16 * (len(tft.frame) // 2)).from_buffer(tft.frame)  # the display's frame
                if alpha is None:
                    lib.fx_fire_draw(ctypes.byref(self.f), out, (ctypes.c_uint16 * 256).from_buffer(palette))
                else:
                    lib.fx_fire_blend(ctypes.byref(self.f), out, (ctypes.c_uint16 * 256).from_buffer(palette),
                                      (ctypes.c_uint8 * 256).from_buffer(alpha))

        class HeatField(OldHeatField):  # --- MVP (P803) ---
            def cool(self, x0, y0, x1, y1, amount):  # the binding's, with its check
                w, h = self.f.w, self.f.h
                if not (-w <= x0 <= 2 * w and -w <= x1 <= 2 * w and -h <= y0 <= 2 * h and -h <= y1 <= 2 * h
                        and 0 <= amount <= 255):
                    raise ValueError("x within -w to 2w, y within -h to 2h, amount 0 to 255")
                engine.cools.append((x0, y0, x1, y1, amount))
                lib.fx_fire_cool(ctypes.byref(self.f), x0, y0, x1, y1, amount)

        self.HeatField = HeatField if cool else OldHeatField
        self.targets, self.looks, self.burns, self.filters, self.cools = [], [], [], [], []
        self.scrolls, self.alphas, self.palettes = [], [], []  # P602, P639
        self.stats_calls = 0  # P753

    def largest_free_internal(self):
        return 123456


def play(game, frames, now, tft, pressed=False, canvas=Recorder):
    """frames frames 40 ms apart from now, the first one pressed if asked: the last frame's canvas, and now. canvas
    makes each frame's canvas from the tft (P639: tools/render_scene.py passes lcd.TftCanvas)."""
    for k in range(frames):
        now += FRAME_MS
        game.step(now, pressed and k == 0, False)
        cv = canvas(tft)
        game.paint_static(cv)
        game.paint(cv)
    return cv, now


class TftTest(unittest.TestCase):
    def test_fill_rect_writes_native_uint16_pixels_as_the_c_draw(self):
        """P639: the stand-in's fill lands where and as the C draw's pixels do, a uint16 per pixel, row after row."""
        tft = Tft()
        tft.fill_rect(1, 2, 2, 1, 0x1234)
        k = 2 * (2 * lcd.PANEL_W)
        self.assertEqual(array("H", [0, 0x1234, 0x1234, 0]).tobytes(), bytes(tft.frame[k:k + 8]))
        self.assertEqual(4, sum(1 for b in tft.frame if b))  # two pixels of two bytes, nothing else


class PaletteTest(unittest.TestCase):
    def test_heat_0_is_black_and_heat_255_white(self):
        self.assertEqual(256, len(fire.PALETTE))
        self.assertEqual(fire.BLACK, fire.PALETTE[0])
        self.assertEqual(fire.WHITE, fire.PALETTE[255])

    def test_a_blend_keeps_the_red_of_alpha_full_below_it(self):
        """P639: no dark edge over a bright sky. Below ALPHA_FULL the blend's colour stays PALETTE[ALPHA_FULL]."""
        red = fire.PALETTE[fire.ALPHA_FULL]
        self.assertEqual([red] * (fire.ALPHA_FULL + 1), list(fire.BLEND_PALETTE[:fire.ALPHA_FULL + 1]))
        self.assertEqual(list(fire.PALETTE[fire.ALPHA_FULL:]), list(fire.BLEND_PALETTE[fire.ALPHA_FULL:]))

    def test_the_alpha_climbs_from_clear_to_full_at_heat_96(self):
        """P603: the cool cells fade into the sky, the fire from heat 96 up is solid (the PO's pick, curve B)."""
        alpha = list(fire.ALPHA)
        self.assertEqual((256, 0, 127, 252, 255, 255), (len(alpha), alpha[0], alpha[48], alpha[95], alpha[96], alpha[255]))
        self.assertEqual(sorted(alpha), alpha)


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

    # --- MVP (P602) ---
    def test_alone_the_mac_has_no_engine(self):
        """On the Mac `import engine` finds the repository's engine/ folder, so fire.engine is None only by its check.
        Run alone, no other test's tearDown sets it."""
        root = os.path.dirname(HERE)
        run = subprocess.run([sys.executable, "-m", "unittest", "tests.test_fire.NoEngineTest.test_no_c_shows_and_"
                              "nothing_else_is_drawn"], cwd=root, capture_output=True, text=True)
        self.assertEqual(0, run.returncode, run.stderr)

    def test_a_layer_without_the_engine_has_no_field_and_still_counts_cells(self):
        layer = fire.FireLayer(LAYER_LOOK, 1)
        self.assertIsNone(layer.field)
        self.assertEqual((-1, -2), (layer.update(40, 95), layer.update(40, 95)))  # 3,800 px·ms a frame, 2,000 a cell
        layer.clear()
        layer.draw(Recorder(Tft()))  # nothing to draw, and no error
        self.assertFalse(layer.can_cool)  # --- MVP (P803) ---
        self.assertEqual((0, fire.W - 1), layer.cool(10, 20))

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
        self.assertRegex(game.label, r"^fire linear \d+\.\d ms \d+ fps$")
        self.assertEqual({"tft"}, set(fire.engine.targets))
        look = (fire.DECAY, fire.COOL, fire.SWAY, fire.SPOTS, fire.SPREAD, fire.FAST, fire.EMBERS,
                    fire.FADE)
        self.assertEqual([look], fire.engine.looks)  # once
        self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame))  # the fire reached the frame

    def births(self, crackle, old_engine=False):  # --- MVP (P751) --- 8 s of Fire into crackle: its add_pops calls
        if old_engine:  # a HeatField whose take_births takes no argument, as before P751
            real = fire.engine.HeatField

            class OldField(real):
                def take_births(self):
                    return real.take_births(self)

            fire.engine.HeatField = OldField
        fire.FirePlugin.crackle = crackle
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                play(fire.Fire(), 200, 0, Tft())
        finally:
            fire.FirePlugin.crackle = None

    def test_a_crackle_that_takes_rises_gets_each_births_rise_2_to_5(self):  # --- MVP (P751) ---
        class Taking:
            takes_rises = True

            def __init__(self):
                self.calls = []

            def add_pops(self, n, rises=None):
                self.calls.append((n, None if rises is None else list(rises)))

        c = Taking()
        self.births(c)
        self.assertGreater(sum(n for n, _ in c.calls), 8)
        for n, rises in c.calls:
            self.assertEqual([0] * (8 - min(n, 8)), rises[min(n, 8):])
            self.assertTrue(all(2 <= r <= 5 for r in rises[:min(n, 8)]), rises)

    def test_other_crackles_and_an_old_engine_get_the_count_alone(self):  # --- MVP (P751) ---
        class Counting:
            def __init__(self):
                self.calls = []

            def add_pops(self, n):
                self.calls.append(n)

        class Taking(Counting):
            takes_rises = True

            def add_pops(self, n, rises=None):
                self.calls.append((n, rises))

        plain = Counting()
        self.births(plain)
        self.assertGreater(sum(plain.calls), 8)
        old = Taking()
        self.births(old, old_engine=True)
        self.assertTrue(old.calls and all(rises is None for _, rises in old.calls), old.calls)

    def test_a_crackle_with_follow_field_gets_the_stats_and_the_wind_once_per_step(self):  # --- MVP (P753) ---
        class Following:
            def __init__(self):
                self.calls, self.pops = [], 0

            def add_pops(self, n):
                self.pops += n

            def follow_field(self, total, height, wind):
                self.calls.append((total, height, wind))

        c = Following()
        self.births(c)
        self.assertGreater(len(c.calls), 100)  # 200 frames of 40 ms: a step each, a frame now and then takes none
        self.assertEqual(len(c.calls), fire.engine.stats_calls)  # one stats() per follow_field
        for total, height, wind in c.calls:
            self.assertTrue(all(type(v) is int for v in (total, height, wind)))
            self.assertTrue(0 <= total <= 255 * fire.W * fire.H and 0 <= height <= fire.H)
            self.assertTrue(-fire.WIND <= wind <= fire.WIND)
        self.assertGreater(c.calls[-1][0], 100000)  # a burning field, not a cold one
        self.assertTrue(any(w != 0 for _, _, w in c.calls))

    def test_no_stats_call_without_follow_field_or_on_a_firmware_without_stats(self):  # --- MVP (P753) ---
        class Counting:
            def add_pops(self, n):
                pass

        self.births(Counting())
        self.assertEqual(0, fire.engine.stats_calls)

        class Following(Counting):
            def follow_field(self, total, height, wind):
                raise AssertionError("an old firmware has no stats")

        real = fire.engine.HeatField

        class OldField(real):
            stats = property(lambda self: (_ for _ in ()).throw(AttributeError("stats")))

        fire.engine.HeatField = OldField
        self.births(Following())
        self.assertEqual(0, fire.engine.stats_calls)

        class BedOff(Following):
            has_bed = False  # a FireSound with BED off: the pops alone, no stats() a step

        fire.engine.HeatField = real
        self.births(BedOff())
        self.assertEqual(0, fire.engine.stats_calls)

    def test_a_tap_moves_to_the_next_mode(self):
        """P608: the scene starts linear, and a tap walks the three modes, each setting its filter. Only the picture
        mode paints the sky (here black: the Mac has no art) and blends."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            game = fire.Fire()
            tft = Tft()
            _, now = play(game, 5, 0, tft)
            self.assertEqual([fire.LINEAR], fire.engine.filters)  # setup's
            seen = []
            for _ in range(3):
                tft.blits, fire.engine.targets, fire.engine.filters = [], [], []
                cv, now = play(game, 1, now, tft, pressed=True)
                cv, now = play(game, 1, now, tft)
                seen.append((fire.MODES[game.mode][0], fire.engine.filters, game.fire_plugin.field.f.filter,
                             fire.engine.targets, tft.blits, cv.fills))
        sky = [(0, 0, fire.WIDTH, fire.HEIGHT)]
        self.assertEqual([
            ("picture", [fire.LINEAR], fire.LINEAR, ["tft alpha", "tft alpha"], [], sky),
            ("nearest", [fire.NEAREST], fire.NEAREST, ["tft", "tft"], [], []),
            ("linear", [fire.LINEAR], fire.LINEAR, ["tft", "tft"], [], []),
        ], seen)
        self.assertIn("fire mode picture\nfire mode nearest\nfire mode linear\n", out.getvalue())

    def test_the_wind_stays_within_wind(self):
        fire.random.seed(SEED_WIND)  # the gusts draw from Python's random: seeded, so both signs always show
        with contextlib.redirect_stdout(io.StringIO()):
            game = fire.Fire()
            winds, now = [], 0
            for _ in range(1000):
                _, now = play(game, 1, now, Tft())
                winds.append(game.fire_plugin.wind)
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
                plugin = game.fire_plugin
                plugin.wind, plugin.target, plugin.gust = 0, target, 10 ** 9  # no new gust during the test
                _, now = play(game, 100, now, Tft())
                self.assertEqual(target, plugin.wind)

    # --- MVP (P602) ---
    def test_scroll_moves_the_field_within_the_bindings_range(self):
        field = fire.engine.HeatField(4, 2, 1)
        field.heat[:8] = bytes(range(1, 9))
        field.scroll(-1)
        self.assertEqual(bytes([2, 3, 4, 0, 6, 7, 8, 0]), bytes(field.heat[:8]))
        field.scroll(-1024)
        self.assertEqual(bytes(8), bytes(field.heat[:8]))
        with self.assertRaises(ValueError):
            field.scroll(1025)

    def test_a_layer_scrolls_whole_cells_with_the_world_and_keeps_the_rest(self):
        """N frames at 95 px/s and 40 ms scroll (95 * 40 * N) // 2000 cells in all, each one to the left."""
        layer = fire.FireLayer(LAYER_LOOK, 1)
        self.assertEqual(([LAYER_LOOK], [fire.LINEAR]), (fire.engine.looks, fire.engine.filters))
        self.assertEqual(0, layer.field.f.base)  # only burns put heat in
        for n in (1, 2, 7, 50):
            with self.subTest(n=n):
                layer.clear()
                fire.engine.scrolls = []
                cells = -sum(layer.update(40, 95) for _ in range(n))  # left
                self.assertEqual((95 * 40 * n) // 2000, cells)
                self.assertEqual(-cells, sum(fire.engine.scrolls))
                self.assertTrue(all(dx < 0 for dx in fire.engine.scrolls))

    def test_a_layer_moves_its_heat_left_and_clear_empties_it(self):
        layer = fire.FireLayer(LAYER_LOOK, 1)
        layer.field.burn(100, 60, 100, 60, 0, 255)
        layer.field.step = lambda n, wind: None  # the scroll alone
        self.assertEqual(-2, layer.update(40, 100))  # 4,000 px·ms: 2 cells left
        row = layer.field.heat[60 * fire.W:61 * fire.W]
        self.assertEqual((0, 255), (row[100], row[98]))
        layer.field.burn(fire.W - 1, 0, fire.W - 1, 0, 0, 255)  # the last column, which a scroll one short keeps
        layer.clear()
        self.assertEqual(bytes(fire.W * fire.H), bytes(layer.field.heat[:fire.W * fire.H]))

    def test_a_scroll_one_column_short_of_the_width_keeps_the_edge_column(self):
        layer = fire.FireLayer(LAYER_LOOK, 1)
        for dx, start, end in ((-(fire.W - 1), fire.W - 1, 0), (fire.W - 1, 0, fire.W - 1)):
            with self.subTest(dx=dx):
                layer.clear()
                layer.field.burn(start, 60, start, 60, 0, 255)
                layer.field.scroll(dx)
                heat = bytes(layer.field.heat[:fire.W * fire.H])
                self.assertEqual(255, heat[60 * fire.W + end])
                self.assertEqual(255, sum(heat))  # no other cell holds heat

    # --- MVP (P803) ---
    def test_a_layer_cools_whole_columns_and_says_which(self):
        layer = fire.FireLayer(LAYER_LOOK, 1)
        self.assertTrue(layer.can_cool)
        for x in range(fire.W):
            layer.field.burn(x, 0, x, fire.H - 1, 0, 200)
        self.assertEqual((0, 12), layer.cool(-5, 12))  # clipped to the field
        self.assertEqual((150, fire.W - 1), layer.cool(150, fire.W + 9))
        heat = layer.field.heat
        empty = [x for x in range(fire.W) if not any(heat[y * fire.W + x] for y in range(fire.H))]
        full = [x for x in range(fire.W) if all(heat[y * fire.W + x] == 200 for y in range(fire.H))]
        self.assertEqual(list(range(13)) + list(range(150, fire.W)), empty)
        self.assertEqual(list(range(13, 150)), full)
        self.assertEqual([], fire.engine.scrolls)

    def test_without_cool_a_layer_s_cool_clears_the_whole_field(self):
        fire.engine = Engine(self.lib, cool=False)
        layer = fire.FireLayer(LAYER_LOOK, 1)
        self.assertFalse(hasattr(layer.field, "cool") or layer.can_cool)
        layer.field.burn(100, 60, 100, 60, 3, 255)
        steps = []
        layer.field.step = lambda n, wind: steps.append(n)
        layer.update(30, 0)
        self.assertEqual((0, fire.W - 1), layer.cool(0, 3))
        self.assertEqual(bytes(fire.W * fire.H), bytes(layer.field.heat[:fire.W * fire.H]))
        layer.update(30, 0)
        self.assertEqual([], steps)  # as clear: no part of a step carried over

    def test_clear_carries_no_part_of_a_step_into_the_next_round(self):
        layer = fire.FireLayer(LAYER_LOOK, 1)
        steps = []
        layer.field.step = lambda n, wind: steps.append(n)
        layer.update(30, 95)
        layer.clear()
        layer.update(30, 95)
        self.assertEqual([], steps)  # 30 + 30 ms would make a 40 ms step without the clear

    def test_a_layer_steps_by_its_clock_and_blends_over_the_frame(self):
        layer = fire.FireLayer(LAYER_LOOK, 1)
        layer.field.burn(80, 100, 80, 100, 3, 255)
        steps = []
        layer.field.step = lambda n, wind: steps.append((n, wind))
        for ms in (40, 20, 60, 60, 60, 200):
            layer.update(ms, 95)
        self.assertEqual([(1, 0), (2, 0), (1, 0), (2, 0), (2, 0)], steps)  # StepClock(STEP_MS, 2): at most 2 a frame
        tft = Tft()
        layer.draw(Recorder(tft))
        layer.draw(object())  # a canvas without tft draws nothing
        self.assertEqual(["tft alpha"], fire.engine.targets)
        self.assertEqual([fire.BLEND_PALETTE], fire.engine.palettes)  # P639: the red edge, no dark border
        self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame))

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
