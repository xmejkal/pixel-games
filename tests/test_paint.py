"""art/paint.py through its table of art sets: the board files come out byte for byte as committed, and the looks
keep the hard mask. Run from the repository root: python3 -m unittest discover tests."""

import contextlib
import io
import os
import re
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names

import PIL  # noqa: E402
import PIL.ImageOps  # noqa: E402
from PIL import Image  # noqa: E402

from brush import ACCENT, rnd  # noqa: E402
from export import from_bin, q565, to_bin  # noqa: E402
from letters import GLYPHS, write  # noqa: E402
from looks import NightInk, Watercolour  # noqa: E402
from paint import main  # noqa: E402
from sets import gravpong as gravpong_set, runner as runner_set, snake as snake_set, stack as stack_set  # noqa: E402
from sets.runner import RED, run_cycle, runner  # noqa: E402

PREVIEW_PILLOW = "12.3.0"  # preview.png was written with it; fonts and zlib change PNG bytes, not the board files


def same_bytes(a, b):
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


class PaintedFilesTest(unittest.TestCase):
    """One main() run into a temporary root, compared with the files in the repository."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with contextlib.redirect_stdout(io.StringIO()):
            main(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_bin_as_committed(self):
        made, kept = os.path.join(self.tmp.name, "games", "art"), os.path.join(REPO, "games", "art")
        self.assertEqual(sorted(os.listdir(made)), sorted(n for n in os.listdir(kept) if n.endswith(".bin")))
        for name in os.listdir(made):
            with self.subTest(name=name):
                self.assertTrue(same_bytes(os.path.join(made, name), os.path.join(kept, name)))

    def test_index_as_committed(self):
        self.assertTrue(same_bytes(os.path.join(self.tmp.name, "games", "art_index.py"),
                                   os.path.join(REPO, "games", "art_index.py")))

    def test_aliases_are_the_last_rows_of_art(self):
        index = {}
        with open(os.path.join(self.tmp.name, "games", "art_index.py")) as f:
            exec(f.read(), index)
        art = index["ART"]
        aliases = ["runner_jump"] + ["rescue_smoke%d" % i for i in range(5)]  # in the sets' order
        self.assertEqual(aliases, list(art)[-len(aliases):])
        self.assertEqual(art["runner_jump"], art["runner_apex"])
        self.assertEqual(art["rescue_smoke4"], art["meteors_smoke4"])  # another set's file, no copy
        self.assertIs(index["LAYER_SETS"]["runner"], index["LAYERS"])

    def test_preview_as_committed(self):
        if PIL.__version__ != PREVIEW_PILLOW:
            self.skipTest("Pillow %s, not %s: the PNG bytes differ" % (PIL.__version__, PREVIEW_PILLOW))
        self.assertTrue(same_bytes(os.path.join(self.tmp.name, "art", "preview.png"),
                                   os.path.join(REPO, "art", "preview.png")))


class OneSetAloneTest(unittest.TestCase):
    """A set painted alone, after the stream was moved, gives the committed files: it does not lean on the sets
    painted before it."""

    def test_stack_alone_as_committed(self):
        rnd.random()
        painting = stack_set.ART_SET.paint()
        for name, (img, keyed) in painting.pictures.items():
            with self.subTest(name=name), open(os.path.join(REPO, "games", "art", name + ".bin"), "rb") as f:
                self.assertEqual(to_bin(img, keyed), f.read())


    def test_snake_alone_as_committed(self):
        rnd.random()
        painting = snake_set.ART_SET.paint()
        for name, (img, keyed) in painting.pictures.items():
            with self.subTest(name=name), open(os.path.join(REPO, "games", "art", name + ".bin"), "rb") as f:
                self.assertEqual(to_bin(img, keyed), f.read())

    def test_gravpong_alone_as_committed(self):
        rnd.random()
        painting = gravpong_set.ART_SET.paint()
        for name, (img, keyed) in painting.pictures.items():
            with self.subTest(name=name), open(os.path.join(REPO, "games", "art", name + ".bin"), "rb") as f:
                self.assertEqual(to_bin(img, keyed), f.read())


def board_colour(rgb):
    """The colour as the board shows it, after the RGB565 cut."""
    return q565(Image.new("RGBA", (1, 1), tuple(rgb) + (255,))).getpixel((0, 0))[:3]


class LooksTest(unittest.TestCase):
    """The looks on a keyed runner sprite: the board skips alpha 0, so a look must never change the mask."""

    @classmethod
    def setUpClass(cls):
        rnd.seed(runner_set.ART_SET.seed)  # the same sprite whichever test ran before
        cls.sprite = runner(run_cycle()[0])
        with open(os.path.join(REPO, "games", "art", "bg.bin"), "rb") as f:
            cls.bg = from_bin(f.read(), 320, 240)  # the runner's fallback, as the board shows it

    def test_watercolour_is_the_picture(self):
        self.assertIs(Watercolour().apply(self.sprite), self.sprite)

    def test_night_ink_keeps_the_mask_and_three_colours(self):
        look = NightInk(RED)
        inked = look.apply(self.sprite)
        alpha = self.sprite.getchannel("A").tobytes()
        self.assertIn(0, alpha)  # the sprite is keyed, so the check below means something
        self.assertEqual(inked.getchannel("A").tobytes(), alpha)
        allowed = {board_colour(c) for c in (look.INK, look.BONE, look.accent)}
        shown = {p[:3] for p in q565(inked).get_flattened_data() if p[3]}
        self.assertLessEqual(shown, allowed)
        self.assertIn(board_colour(RED), shown)  # the shirt keeps the accent


    def test_night_ink_turns_the_pale_sky_to_bone(self):
        look = NightInk(RED)
        sky = self.bg.getpixel((4, 4))  # orange, near the accent's hue, but pale: not the accent
        self.assertEqual(look.ink(sky), look.BONE + (255,))
        self.assertEqual(NightInk(RED, light=255).ink(sky), look.INK + (255,))  # light sets bone against ink
        self.assertEqual(NightInk(sky[:3], bright=1.01, vivid=0.0).ink(sky), sky[:3] + (255,))  # the rule, opened


def read(*parts):
    with open(os.path.join(REPO, *parts)) as f:
        return f.read()


class RentTest(unittest.TestCase):
    """Stack as RENT (P568): its pictures as the game asks for them, the one accent, and the stroke letters. The new
    files themselves are the expected output, judged on the preview; these say the game and the art agree."""

    @classmethod
    def setUpClass(cls):
        cls.painting = stack_set.ART_SET.paint()
        index = {}
        exec(read("games", "art_index.py"), index)
        cls.art = index["ART"]

    def test_sizes_and_key(self):
        sizes = {"stack_noon": (320, 240, False), "stack_hook": (16, 16, True)}
        sizes.update({"stack_%s%d" % (kind, i): (320, 14, False) for kind in ("lit", "dark") for i in range(8)})
        sizes.update({"stack_digit%d" % d: (8, 12, True) for d in range(10)})
        sizes.update({"stack_cot%d" % k: (16, 16, True) for k in range(4)})
        sizes.update({"stack_sold": (58, 18, False), "stack_title": (320, 240, False), "stack_over": (200, 100, False)})
        shown = {name: img.size + (keyed,) for name, (img, keyed) in self.painting.pictures.items()}
        self.assertEqual(shown, sizes)  # and the night's stack_bg, stack_block and stack_mover are gone

    def test_every_name_the_game_asks_for_is_drawn(self):
        names = re.findall(r'"(stack_[a-z]+)(%d)?"', read("games", "arcade2.py"))
        self.assertIn(("stack_digit", "%d"), names)  # the game asks by the patterns, so the test reads them
        count = {"stack_digit": 10, "stack_cot": 4}  # every other pattern runs over the eight floors
        for stem, pattern in names:
            for name in [stem + str(i) for i in range(count.get(stem, 8))] if pattern else [stem]:
                with self.subTest(name=name):
                    self.assertIn(name, self.art)

    def test_one_accent(self):
        self.assertIn("ACCENT = c565(%d, %d, %d)" % ACCENT, read("games", "gfx.py"))  # the board's copy of it
        for name in ("stack_hook", "stack_sold", "stack_cot0", "stack_over"):  # its band, the plate, the blanket, SOLD OUT
            with self.subTest(name=name):
                shown = {p[:3] for p in q565(self.painting.pictures[name][0]).get_flattened_data() if p[3]}
                self.assertIn(board_colour(ACCENT), shown)

    def test_letters_fit_their_cells_and_differ(self):
        masks = set()
        for ch, lines in GLYPHS.items():
            for x, y in (p for line in lines for p in line):
                self.assertTrue(0 <= x <= 4 and 0 <= y <= 6, ch)
            m = Image.new("L", (24, 32), 0)
            write(m, ch, 2, 2, 4, 2)
            masks.add(m.tobytes())
        self.assertEqual(len(masks), len(GLYPHS))  # no two letters look the same, the space included


class BubbleTest(unittest.TestCase):
    """Gravity pong as BUBBLE (P573): its pictures as the game asks for them, the sizes and places the game copies,
    the workers' poses, and the one accent. The files themselves are the expected output, judged on the preview."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(REPO, "tests", "stubs"))
        sys.path.insert(0, os.path.join(REPO, "games"))
        import time
        if not hasattr(time, "ticks_diff"):
            time.ticks_diff = lambda a, b: a - b
            time.ticks_us = lambda: int(time.perf_counter() * 1e6)
            time.ticks_ms = lambda: int(time.perf_counter() * 1e3)
        import arcade2
        cls.game, cls.module = arcade2.GravityPong, arcade2
        cls.painting = gravpong_set.ART_SET.paint()
        index = {}
        exec(read("games", "art_index.py"), index)
        cls.art, cls.sets = index["ART"], index["PICTURE_SETS"]

    def asked(self):
        """Every picture name the game holds or writes out."""
        g, arcade2 = self.game, self.module
        names = [n for k in g.BUBBLES + g.FILMS + g.HALOS + tuple(g.NETS.values()) for n in k]
        names += list(g.POPS + arcade2.Notes.NAMES + g.DIGITS)
        names += [n for side in g.WORKERS for poses in side.values() for n in poses] + list(g.STANDS)
        return names + re.findall(r'"(gravpong_[a-z_]+)"', read("games", "arcade2.py"))

    def test_every_name_the_game_asks_for_is_in_its_set(self):
        for name in self.asked():
            with self.subTest(name=name):
                self.assertIn(name, self.sets["gravpong"])

    def test_the_set_is_no_larger_than_the_pool(self):
        size = sum(self.art[n][0] * self.art[n][1] * 2 for n in self.sets["gravpong"])
        self.assertLess(size, 739200)  # runner's set makes the pool; a smaller one needs no reset (P573)

    def test_the_game_copies_the_sets_sizes_and_places(self):
        g, a = self.game, gravpong_set
        self.assertEqual(a.SIZES, g.SIZES)
        self.assertEqual(tuple(a.BOX[d] for d in a.SIZES), g.BOX)
        self.assertEqual((a.RINGS, a.GLOW_ALPHAS, a.FILM_ALPHA), (g.RINGS, g.GLOW_ALPHAS, g.FILM_ALPHA))
        self.assertEqual((a.FLOOR, a.NET_Y, a.NET_Y + a.NET_TOP), (g.FLOOR, g.NET_Y, g.PY))
        self.assertEqual(a.WORKER + (a.hand_dx(),), (g.WORKER_W, g.WORKER_H, g.HAND_DX))
        self.assertEqual((a.POP, a.POP_FRAMES, a.SPOT, a.COIN), (g.POP, g.POP_FRAMES, (g.SPOT_W, g.SPOT_H), g.COIN))
        self.assertEqual((a.POOL, a.NET_WIDTHS, a.NET_WIDTHS[0]), ((g.POOL_W, g.POOL_H), self.module.NET_WIDTHS, g.PW))
        self.assertEqual((a.BOARD[:2], a.PLATE[2] - 3, a.PLATE[1] + 2), (g.BOARD, g.PLATE_RIGHT, g.PLATE_TOP))
        self.assertEqual(a.TITLE_PLATE[0] + a.PLATE_W - 3, g.TITLE_BEST_RIGHT)
        self.assertEqual(a.TITLE_PLATE[1] + 3, g.TITLE_BEST_TOP)
        for (x, y), right in zip(a.CARD_PLATES, (g.SCORE_RIGHT, g.BEST_RIGHT)):
            self.assertEqual((g.CARD_X + x + a.PLATE_W - 3, g.CARD_Y + y + 3), (right, g.CARD_PLATE_TOP))

    def test_sizes_and_key(self):
        shown = {name: img.size + (keyed,) for name, (img, keyed) in self.painting.pictures.items()}
        for name in ("gravpong_midnight", "gravpong_title"):
            self.assertEqual((320, 240, False), shown[name])
        self.assertEqual((200, 100, False), shown["gravpong_over"])
        for d, b in zip(self.game.SIZES, self.game.BOX):
            for name in self.game.BUBBLES[self.game.SIZES.index(d)]:
                self.assertEqual((b, b, True), shown[name])
        for w, names in self.game.NETS.items():
            for name in names:
                self.assertEqual((w, 14, True), shown[name])

    def test_the_bubble_is_as_wide_as_its_size_in_the_round_pose(self):
        for d in self.game.SIZES:
            img = self.painting.pictures["gravpong_bubble_%d_round" % d][0]
            cols = [x for x in range(img.width) if any(img.getpixel((x, y))[3] for y in range(img.height))]
            with self.subTest(d=d):
                self.assertEqual(d, cols[-1] - cols[0] + 1)

    def test_each_right_worker_is_the_mirror_of_the_left_and_stands_on_the_last_row_holding_the_net(self):
        g, pics = self.game, self.painting.pictures
        for name in gravpong_set.WORKER_POSES:
            left, right = pics["gravpong_worker_l_" + name][0], pics["gravpong_worker_r_" + name][0]
            with self.subTest(pose=name):
                self.assertEqual(to_bin(PIL.ImageOps.mirror(left), True), to_bin(right, True))
                alpha = left.getchannel("A")
                self.assertTrue(any(alpha.getpixel((x, left.height - 1)) for x in range(left.width)))
                hand = g.PY - (g.FLOOR - g.WORKER_H)  # the net's row, in the picture
                self.assertTrue(any(alpha.getpixel((g.WORKER_W // 2 + g.HAND_DX + dx, hand + dy))
                                    for dx in (-1, 0) for dy in (0, 1, 2)))

    def test_one_accent(self):
        for name in ("gravpong_midnight", "gravpong_crash", "gravpong_title", "gravpong_over"):
            with self.subTest(name=name):
                shown = {p[:3] for p in q565(self.painting.pictures[name][0]).get_flattened_data() if p[3]}
                self.assertIn(board_colour(ACCENT), shown)



def shown(img):
    """The colours of a picture's drawn pixels as the board shows them."""
    return {p[:3] for p in q565(img).get_flattened_data() if p[3]}


class FeedTest(unittest.TestCase):
    """Snake as FEED (P573): its pictures as the game asks for them, the sizes and places the game copies, the glass's
    reflection kept faint, six tiles in six hues and the red dot the only red. The files themselves are the expected
    output, judged on the preview."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(REPO, "tests", "stubs"))
        sys.path.insert(0, os.path.join(REPO, "games"))
        import time
        if not hasattr(time, "ticks_diff"):
            time.ticks_diff = lambda a, b: a - b
            time.ticks_us = lambda: int(time.perf_counter() * 1e6)
            time.ticks_ms = lambda: int(time.perf_counter() * 1e3)
        import arcade
        cls.game, cls.module = arcade.Snake, arcade
        cls.painting = snake_set.ART_SET.paint()
        index = {}
        exec(read("games", "art_index.py"), index)
        cls.art, cls.sets = index["ART"], index["PICTURE_SETS"]

    def asked(self):
        """Every picture name the game holds or writes out."""
        m = self.module
        names = [n for poses in m.HEADS for n in poses]
        names += list(m.TILES + m.SEEN + m.DOTS + m.BULGES + m.RIPPLES + m.PINGS + m.THUMBS + m.FEED_DIGITS)
        return names + re.findall(r'"(snake_[a-z_]+)"', read("games", "arcade.py"))

    def test_every_name_the_game_asks_for_is_in_its_set(self):
        for name in self.asked():
            with self.subTest(name=name):
                self.assertIn(name, self.sets["snake"])

    def test_the_set_is_no_larger_than_the_pool(self):
        size = sum(self.art[n][0] * self.art[n][1] * 2 for n in self.sets["snake"])
        self.assertLess(size, 739200)  # runner's set makes the pool; a smaller one needs no reset (P573)

    def test_the_game_copies_the_sets_sizes_and_places(self):
        g, m, a = self.game, self.module, snake_set
        self.assertEqual((a.CELL, a.COLS, a.ROWS, a.LEFT, a.TOP), (g.CELL, g.COLS, g.ROWS, g.LEFT, g.TOP))
        self.assertEqual((a.KINDS, a.DIRS, a.POSES), (m.FEED_KINDS, m.FEED_DIRS, m.FEED_POSES))
        self.assertEqual(sorted(m.FEED_ORDER), sorted(list(range(6)) * 2))  # each kind twice in the shuffle
        self.assertEqual((a.HEAD, a.HALO, a.BULGE, a.RIPPLE, a.PING, a.THUMB[0]),
                         (g.HEAD, g.HALO, g.BULGE, g.RIPPLE, g.PING, g.THUMB_W))
        self.assertEqual((a.HALO_ALPHA, a.RIPPLE_ALPHAS, a.DIGIT_W), (g.HALO_ALPHA, g.RIPPLE_ALPHAS, g.DIGIT_W))
        self.assertEqual((a.RIPPLES, a.PINGS, a.DOT_POSES), (len(m.RIPPLES), len(m.PINGS), len(m.DOTS)))
        self.assertEqual((g.CARD_X + a.CARD_PLATE[0] + a.PLATE_W - 3, g.CARD_Y + a.CARD_PLATE[1] + 3),
                         (g.CARD_RIGHT, g.CARD_TOP))
        self.assertEqual((a.TITLE_PLATE[0] + a.PLATE_W - 3, a.TITLE_PLATE[1] + 3),
                         (g.TITLE_BEST_RIGHT, g.TITLE_BEST_TOP))
        self.assertEqual(board_colour(a.BONE), board_colour(self.colour(g.BONE)))

    @staticmethod
    def colour(c):
        """A c565 value back to (r, g, b), its bytes swapped back."""
        v = ((c & 0xFF) << 8) | (c >> 8)
        return ((v >> 11) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31)

    def test_sizes_and_key(self):
        a = snake_set
        sizes = {name: img.size + (keyed,) for name, (img, keyed) in self.painting.pictures.items()}
        for name in ("snake_morning", "snake_title"):
            self.assertEqual((320, 240, False), sizes[name])
        self.assertEqual((200, 100, False), sizes["snake_over"])
        for name in self.module.TILES + self.module.SEEN + self.module.DOTS:
            self.assertEqual((a.CELL, a.CELL, True), sizes[name])
        for name in [n for poses in self.module.HEADS for n in poses]:
            self.assertEqual((a.HEAD, a.HEAD, True), sizes[name])

    def test_the_glass_holds_the_street_faint(self):
        x0, y0, x1, y1 = snake_set.FIELD
        glass = self.painting.pictures["snake_morning"][0].convert("RGB").crop((x0, y0, x1, y1))
        mean = sum(snake_set.luma(p) for p in glass.get_flattened_data()) / (glass.width * glass.height)
        self.assertTrue(0.15 <= mean <= 0.25, mean)

    def test_six_tiles_in_six_hues_and_the_accent_the_only_red(self):
        import colorsys
        hues = set()
        for kind in snake_set.KINDS:
            r, g, b = snake_set.HUES[kind]
            hues.add(round(colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[0] * 12))
        self.assertEqual(6, len(hues))
        accent = board_colour(ACCENT)
        hue = colorsys.rgb_to_hsv(*(c / 255 for c in ACCENT))[0]
        for name, (img, keyed) in self.painting.pictures.items():
            reds = {c for c in shown(img) if snake_set.is_red(c)}
            with self.subTest(name=name):
                if keyed:  # a sprite's red is the accent itself
                    self.assertLessEqual(reds, {accent})
                for c in reds:  # a painted picture's red is the accent's glow: its hue
                    h = colorsys.rgb_to_hsv(*(v / 255 for v in c))[0]
                    self.assertLess(min(abs(h - hue), 1 - abs(h - hue)), 12 / 360, c)  # blended into the ink
        for name in self.module.TILES + self.module.SEEN + self.module.THUMBS:
            with self.subTest(name=name):
                self.assertNotIn(accent, shown(self.painting.pictures[name][0]))
        for name in self.module.DOTS + ("snake_over", "snake_title", "snake_head_r_gulp", "snake_bulge_0"):
            with self.subTest(name=name):
                self.assertIn(accent, shown(self.painting.pictures[name][0]))

    def test_the_head_faces_each_way_left_mirrored_so_the_eye_stays_up(self):
        pics = self.painting.pictures
        for pose in snake_set.POSES:
            right, left = pics["snake_head_r_%s" % pose][0], pics["snake_head_l_%s" % pose][0]
            down, up = pics["snake_head_d_%s" % pose][0], pics["snake_head_u_%s" % pose][0]
            with self.subTest(pose=pose):
                self.assertEqual(to_bin(PIL.ImageOps.mirror(right), True), to_bin(left, True))
                self.assertEqual(to_bin(right.transpose(Image.Transpose.ROTATE_270), True), to_bin(down, True))
                self.assertEqual(to_bin(right.transpose(Image.Transpose.ROTATE_90), True), to_bin(up, True))
        self.assertEqual(4, len({to_bin(pics["snake_head_r_%s" % p][0], True) for p in snake_set.POSES}))


if __name__ == "__main__":
    unittest.main()
