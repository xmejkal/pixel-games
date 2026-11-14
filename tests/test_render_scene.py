"""tools/render_scene.py and tests/drawing_tft.py on the Mac (P795): the font's parse into the framebuf stub, the
stand-in display's blit, blend and line against the driver's, pictures.ROOT, the button patterns, the font refusal,
and a smoke run of every subject as a subprocess of the tool. framebuf comes from tests/stubs and time gets the
MicroPython ticks functions, as in test_fire. Run from the repository root: python3 -B -m unittest tests.test_render_scene.
--- MVP (P795) ---"""

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from drawing_tft import DrawingTft, blend  # noqa: E402  first: it puts games/ and the stubs on the path

import framebuf  # noqa: E402
import gfx  # noqa: E402
import lcd  # noqa: E402
import pictures  # noqa: E402
import render_scene  # noqa: E402
from clang_lib import S3LCD_SRC  # noqa: E402
from PIL import Image  # noqa: E402
from test_blend import SHIM  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "art"))  # export: the committed pictures
from export import pack_bytes  # noqa: E402

TOOL = os.path.join(ROOT, "tools", "render_scene.py")
A_COLUMNS = bytes((0x7C, 0x12, 0x11, 0x12, 0x7C, 0, 0, 0))  # a made-up A: bit 0 is the top row
CHECKER = bytes((0xAA, 0x55) * 4)  # the header's last character, 127, as font_petme128_8x8.h has it
NO_CLANG = "clang is missing: the C engines are not built"


def header(path):
    """A font_petme128_8x8.h with A's columns at 65 and the checkerboard at 127, the other characters blank."""
    rows = [bytes(8)] * 96
    rows[65 - 32], rows[127 - 32] = A_COLUMNS, CHECKER
    with open(path, "w") as f:
        f.write("// 0x99 in a comment\nstatic const uint8_t font_petme128_8x8[] = {\n")
        for n, row in enumerate(rows):
            f.write("    " + ", ".join("0x%02x" % b for b in row) + ", // %d\n" % (n + 32))
        f.write("};\n")


def dots(fb, x, y):
    """The set bits of the 8 x 8 cell at (x, y) as (column, row)."""
    return {(i, j) for j in range(8) for i in range(8) if fb.pixel(x + i, y + j)}


def count(img, colour=None):
    """How many pixels of img hold colour, or any colour but black."""
    return sum(n for n, c in img.getcolors(1 << 16) if (c != (0, 0, 0) if colour is None else c == colour))


def panel(colour):
    """An image() RGB back to the uint16 it came from, in panel order."""
    r, g, b = colour
    v = ((r * 31 + 127) // 255 << 11) | ((g * 63 + 127) // 255 << 5) | (b * 31 + 127) // 255
    return ((v & 0xFF) << 8) | (v >> 8)


def rgb(panel):
    """A panel-order uint16 as the image()'s RGB."""
    v = ((panel & 0xFF) << 8) | (panel >> 8)
    return (v >> 11) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31


class FontTest(unittest.TestCase):
    def setUp(self):
        self.tmp, self.font, self.glyphs = tempfile.TemporaryDirectory(), framebuf.FONT, set(gfx.GLYPHS)
        self.fb = framebuf.FrameBuffer(bytearray(16 * 8), 128, 8, framebuf.MONO_HLSB)

    def tearDown(self):
        framebuf.FONT = self.font
        for ch in set(gfx.GLYPHS) - self.glyphs:
            del gfx.GLYPHS[ch]
        self.tmp.cleanup()

    def test_the_header_parses_and_text_draws_its_columns(self):
        path = os.path.join(self.tmp.name, "font.h")
        header(path)
        render_scene.Font(path).install()
        self.assertEqual(96 * 8, len(framebuf.FONT))
        self.fb.text("A", 8, 0, 1)
        want = {(i, j) for i, column in enumerate(A_COLUMNS) for j in range(8) if column >> j & 1}
        self.assertEqual(want, dots(self.fb, 8, 0))
        self.assertEqual(set(), dots(self.fb, 0, 0))
        self.fb.fill(0)
        self.assertEqual(set(), dots(self.fb, 8, 0))

    def test_a_character_outside_32_to_127_draws_as_127(self):
        path = os.path.join(self.tmp.name, "font.h")
        header(path)
        render_scene.Font(path).install()
        self.fb.text("\x01", 0, 0, 1)
        self.fb.text(chr(200), 8, 0, 1)
        checker = {(i, j) for i in range(8) for j in range(8) if (i + j) % 2 == 1}
        self.assertEqual(checker, dots(self.fb, 0, 0))
        self.assertEqual(checker, dots(self.fb, 8, 0))

    def test_a_short_header_or_no_header_is_refused_and_no_font_draws_nothing(self):
        path = os.path.join(self.tmp.name, "font.h")
        with open(path, "w") as f:
            f.write("static const uint8_t font_petme128_8x8[] = {\n 0x01, 0x02,\n};\n")
        with self.assertRaises(ValueError):
            render_scene.Font(path)
        with open(path, "w") as f:
            f.write("not a header\n")
        with self.assertRaises(ValueError):
            render_scene.Font(path)
        framebuf.FONT = None
        self.fb.text("A", 0, 0, 1)
        self.assertEqual(set(), dots(self.fb, 0, 0))


class BlitTest(unittest.TestCase):
    GAME = ((0x1111, 0x2222, 0x3333), (0x4444, 0x5555, 0x6666))  # a 3 x 2 picture in the game's view, GAME[j][i]

    def picture(self, x, y, key=-1):
        """The picture blitted at game (x, y) through TftCanvas, laid out as art/paint.py lays a picture out: a panel
        row per game column, from the right, a panel column per game row."""
        buf = array("H", [self.GAME[j][2 - i] for i in range(3) for j in range(2)])
        tft = DrawingTft()
        lcd.TftCanvas(tft).picture(buf.tobytes(), x, y, 3, 2, key)
        return tft.image()

    def test_a_picture_lands_at_its_game_place(self):
        img = self.picture(100, 50)
        for j in range(2):
            for i in range(3):
                self.assertEqual(rgb(self.GAME[j][i]), img.getpixel((100 + i, 50 + j)), (i, j))
        self.assertEqual(6, count(img))

    def test_a_picture_half_off_the_panel_is_clipped(self):
        for x, y, on in ((-2, 50, 2), (319, 50, 2), (100, -1, 3), (100, 239, 3)):
            with self.subTest(x=x, y=y):
                img = self.picture(x, y)
                self.assertEqual(on, count(img))
        self.assertEqual(rgb(self.GAME[0][2]), self.picture(-2, 50).getpixel((0, 50)))

    def test_the_key_colour_is_skipped_on_both_paths(self):
        for x in (100, -1):
            with self.subTest(x=x):
                img = self.picture(x, 50, key=0x4444)
                self.assertEqual(0, count(img, rgb(0x4444)))
                self.assertGreater(count(img), 0)

    def test_a_short_buffer_is_refused(self):
        with self.assertRaises(ValueError):
            DrawingTft().blit_buffer(bytes(10), 0, 0, 3, 2)

    def test_alpha_and_key_are_masked_as_the_cs_bytes(self):
        img = self.picture(100, 50, key=0x14444)  # the C sees 0x4444
        self.assertEqual(0, count(img, rgb(0x4444)))
        tft = DrawingTft()
        tft.blit_buffer(array("H", [0x1111]).tobytes(), 5, 6, 1, 1, 256 + 255)  # the C sees 255: no blend
        self.assertEqual(0x1111, memoryview(tft.frame).cast("H")[6 * lcd.PANEL_W + 5])

    def test_a_fill_half_off_the_panel_is_clipped(self):
        for x, y, on in ((-5, 3, 10), (235, 318, 10), (-20, -20, 0), (240, 0, 0)):
            with self.subTest(x=x, y=y):
                tft = DrawingTft()
                tft.fill_rect(x, y, 10, 2, 1)
                self.assertEqual(on, sum(1 for v in memoryview(tft.frame).cast("H") if v))
        tft = DrawingTft()
        tft.fill_rect(-5, 3, 10, 2, 1)
        self.assertEqual([(x, y) for y in (3, 4) for x in range(5)],
                         [(k % lcd.PANEL_W, k // lcd.PANEL_W) for k, v in enumerate(memoryview(tft.frame).cast("H")) if v])


@unittest.skipUnless(shutil.which("clang"), "clang is missing: engine/driver/src/blend565.h is not built")
class BlendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        shim, lib_path = os.path.join(cls.tmp.name, "shim.c"), os.path.join(cls.tmp.name, "libblend.so")
        with open(shim, "w") as f:
            f.write(SHIM)
        subprocess.run(["clang", "-std=c99", "-O2", "-shared", "-fPIC", "-I", S3LCD_SRC, "-o", lib_path, shim],
                       check=True)
        cls.lib = ctypes.CDLL(lib_path)
        cls.lib.blend.restype = ctypes.c_uint16
        cls.lib.blend.argtypes = (ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint8)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_blend_is_the_drivers(self):
        colours = (0x0000, 0xFFFF, 0x1234, 0xABCD, 0x8001, 0x7FFE, 0x00FF, 0xFF00, gfx.RED, gfx.GREEN, gfx.BLUE)
        for fg in colours:
            for bg in colours:
                for alpha in (0, 1, 128, 254):
                    self.assertEqual(self.lib.blend(fg, bg, alpha), blend(fg, bg, alpha), (hex(fg), hex(bg), alpha))

    def test_blit_buffer_blends_at_an_alpha_under_255(self):
        tft = DrawingTft()
        tft.fill(gfx.BLUE)
        tft.blit_buffer(array("H", [gfx.RED]).tobytes(), 5, 6, 1, 1, 128)
        self.assertEqual(self.lib.blend(gfx.RED, gfx.BLUE, 128), memoryview(tft.frame).cast("H")[6 * lcd.PANEL_W + 5])


class LineTest(unittest.TestCase):
    def lit(self, tft):
        return [(k % lcd.PANEL_W, k // lcd.PANEL_W) for k, v in enumerate(memoryview(tft.frame).cast("H")) if v]

    def test_a_diagonal_sets_both_ends_and_one_pixel_a_step(self):
        tft = DrawingTft()
        tft.line(10, 20, 19, 29, 1)
        lit = self.lit(tft)
        self.assertEqual(10, len(lit))
        self.assertIn((10, 20), lit)
        self.assertIn((19, 29), lit)
        tft = DrawingTft()
        tft.line(30, 5, 5, 30, 1)  # the other way round, and steep
        self.assertEqual(26, len(self.lit(tft)))

    def test_a_line_off_the_panel_is_clipped(self):
        tft = DrawingTft()
        tft.line(-10, 3, 4, 3, 1)
        self.assertEqual([(x, 3) for x in range(5)], self.lit(tft))
        tft = DrawingTft()
        tft.line(0, 400, 0, 500, 1)
        self.assertEqual([], self.lit(tft))


class PicturesRootTest(unittest.TestCase):
    def setUp(self):
        self.saved = pictures.ROOT, pictures.ready, pictures.loaded, dict(pictures.PICS), dict(pictures.SETS)
        pictures.ready, pictures.loaded = False, None
        pictures.PICS.clear()
        pictures.SETS.clear()

    def tearDown(self):
        pictures.ROOT, pictures.ready, pictures.loaded, pics, sets = self.saved
        pictures.PICS.clear()
        pictures.PICS.update(pics)
        pictures.SETS.clear()
        pictures.SETS.update(sets)

    def test_load_is_ready_with_the_games_folder_and_not_with_a_wrong_root(self):
        pictures.ROOT = os.path.join(ROOT, "nowhere", "")
        self.assertFalse(pictures.load())
        self.assertFalse(pictures.ready)
        pictures.ROOT = os.path.join(ROOT, "games", "")
        self.assertFalse(pictures.load())  # a refused load is kept until free()
        pictures.free()
        self.assertTrue(pictures.load())
        self.assertIn("flappy_sky", pictures.PICS)
        self.assertIn("flappy", pictures.SETS)


class ButtonsTest(unittest.TestCase):
    def pattern(self, **flags):
        return [render_scene.buttons(k, **flags) for k in range(7)]

    def test_tap_presses_on_one_frame_in_every_n(self):
        on, off = (True, True), (False, False)
        self.assertEqual([on, off, off, on, off, off, on], self.pattern(tap=3))

    def test_hold_is_a_square_wave_of_n_frames(self):
        self.assertEqual([(True, True), (False, True), (False, False), (False, False), (True, True), (False, True),
                          (False, False)], self.pattern(hold=2))
        self.assertEqual([(True, True)] + [(False, True)] * 6, self.pattern(hold=0))

    def test_the_first_frame_presses_unless_title(self):
        self.assertEqual([(True, True)] + [(False, False)] * 6, self.pattern())
        self.assertEqual([(False, False)] * 7, self.pattern(title=True))
        self.assertEqual((False, False), render_scene.buttons(0, tap=3, title=True))
        self.assertEqual((True, True), render_scene.buttons(3, tap=3, title=True))


class GifTest(unittest.TestCase):
    def test_write_gif_keeps_every_kth_image_at_its_time_and_loops(self):
        images = [Image.new("RGB", (8, 8), (40 * k, 0, 255 - 40 * k)) for k in range(6)]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.gif")
            render_scene.write_gif(images, path, 2)
            gif = Image.open(path)
            self.assertEqual((3, 80, 0), (gif.n_frames, gif.info["duration"], gif.info["loop"]))
            self.assertEqual((8, 8), gif.size)
            gif.seek(2)
            self.assertEqual(images[4].getpixel((0, 0)), gif.convert("RGB").getpixel((0, 0)))


class ToolTest(unittest.TestCase):
    """The tool as a subprocess: each run is one process, so the module state it sets stays out of this one."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args):
        return subprocess.run([sys.executable, "-B", TOOL, *args], cwd=ROOT, capture_output=True, text=True)

    def test_no_font_is_a_refusal_that_names_the_path(self):
        missing = os.path.join(self.tmp.name, "none.h")
        run = self.run_tool("--font", missing, "snake", os.path.join(self.tmp.name, "out.png"), "1")
        self.assertEqual(2, run.returncode)
        self.assertIn(missing, run.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "out.png")))

    def test_a_file_that_is_not_a_header_is_a_refusal_that_names_the_path(self):
        path = os.path.join(self.tmp.name, "font.h")
        with open(path, "w") as f:
            f.write("not a header\n")
        run = self.run_tool("--font", path, "snake", os.path.join(self.tmp.name, "out.png"), "1")
        self.assertEqual(2, run.returncode)
        self.assertIn(path, run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_all_refuses_the_single_run_flags(self):
        for flags in (("--tap", "3"), ("--hold", "2"), ("--title",), ("--seed", "0"), ("--gif", "x.gif"), ("--every", "3"),
                      ("snake",)):
            with self.subTest(flags):
                run = self.run_tool("--no-text", "--all", os.path.join(self.tmp.name, "all"), *flags)
                self.assertEqual(2, run.returncode)
                self.assertIn(flags[0], run.stderr)
                self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "all")))

    @unittest.skipUnless(shutil.which("clang"), NO_CLANG)
    def test_no_text_draws(self):
        out = os.path.join(self.tmp.name, "out.png")
        run = self.run_tool("--no-text", "snake", out, "3")
        self.assertEqual(0, run.returncode, run.stderr[-500:])
        img = Image.open(out)
        self.assertEqual((320, 240), img.size)
        self.assertGreater(len(img.getcolors(1 << 16)), 1)


@unittest.skipUnless(shutil.which("clang"), NO_CLANG)
class SmokeTest(unittest.TestCase):
    """Every subject drawn by the tool with its row's presses, one process each, all at once: the frame at the row's
    last count differs from the frame at 5 and has more than one colour; Flappy's row under the score bar at frame 5
    holds the painted sky (the axis)."""

    FIRST = 5
    SKY_ROW = 18  # under the 16 px score bar, above the clouds' top at 20

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        runs = {}
        for name, row in render_scene.SUBJECTS.items():
            out = os.path.join(cls.tmp.name, name + ".png")
            runs[name] = subprocess.Popen([sys.executable, "-B", TOOL, "--no-text", name, out, str(cls.FIRST),
                                           str(row.last)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                          text=True)
        cls.errors = {name: (run.communicate()[1], run.returncode) for name, run in runs.items()}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def sheet(self, name):
        err, code = self.errors[name]
        self.assertEqual(0, code, err[-800:])
        img = Image.open(os.path.join(self.tmp.name, name + ".png"))
        return img.crop((0, 0, 320, 240)), img.crop((330, 0, 650, 240))

    def test_every_subject_moves_and_draws_more_than_one_colour(self):
        for name in render_scene.SUBJECTS:
            with self.subTest(name):
                first, last = self.sheet(name)
                self.assertFalse(first.tobytes() == last.tobytes(), "frame %d is the last frame" % self.FIRST)
                self.assertGreater(len(last.getcolors(1 << 16)), 1)

    def test_flappys_row_under_the_score_bar_is_the_painted_sky(self):
        sky = pack_bytes("flappy_sky")
        y = self.SKY_ROW  # the picture's panel column y of each panel row, one row per game column
        colours = {rgb(int.from_bytes(sky[r * 480 + 2 * y:r * 480 + 2 * y + 2], "little")) for r in range(320)}
        first, _ = self.sheet("flappy")
        self.assertTrue(all(first.getpixel((x, y)) in colours for x in range(320)), first.getpixel((0, y)))
        self.assertGreater(len(colours), 1)


@unittest.skipUnless(shutil.which("clang"), NO_CLANG)
class OverlayBlendTest(unittest.TestCase):
    """The overlay subject blends: a pixel in the pane's dark part over the ball pit is neither the pane's own colour
    nor the pit's pixel without the pane (VolumePane.alpha is 128)."""

    FRAME = 30

    def test_the_pane_lets_the_pit_show_through(self):
        import overlay
        x, y = overlay.RECT[0] + 2, overlay.RECT[1] + 2  # inside the box's grey edge, left of the "vol" text
        with tempfile.TemporaryDirectory() as tmp:
            pixels = {}
            for name in ("overlay", "ballpit"):
                out = os.path.join(tmp, name + ".png")
                run = subprocess.run([sys.executable, "-B", TOOL, "--no-text", name, out, str(self.FRAME)], cwd=ROOT,
                                     capture_output=True, text=True)
                self.assertEqual(0, run.returncode, run.stderr[-800:])
                pixels[name] = Image.open(out).getpixel((x, y))
        dark = rgb(gfx.DARK)
        self.assertNotEqual(dark, pixels["overlay"])
        self.assertNotEqual(pixels["ballpit"], pixels["overlay"])
        self.assertEqual(rgb(blend(gfx.DARK, panel(pixels["ballpit"]), 128)), pixels["overlay"])


if __name__ == "__main__":
    unittest.main()
