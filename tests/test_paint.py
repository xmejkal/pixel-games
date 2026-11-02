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
from PIL import Image  # noqa: E402

from brush import ACCENT, rnd  # noqa: E402
from export import from_bin, q565, to_bin  # noqa: E402
from letters import GLYPHS, write  # noqa: E402
from looks import NightInk, Watercolour  # noqa: E402
from paint import main  # noqa: E402
from sets import runner as runner_set, stack as stack_set  # noqa: E402
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
        self.assertEqual(list(art)[-1], "runner_jump")
        self.assertEqual(art["runner_jump"], art["runner_apex"])
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


if __name__ == "__main__":
    unittest.main()
