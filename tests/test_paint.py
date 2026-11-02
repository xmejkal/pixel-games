"""art/paint.py through its table of art sets: the board files come out byte for byte as committed, and the looks
keep the hard mask. Run from the repository root: python3 -m unittest discover tests."""

import contextlib
import io
import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names

import PIL  # noqa: E402
from PIL import Image  # noqa: E402

from export import q565  # noqa: E402
from looks import NightInk, Watercolour  # noqa: E402
from paint import main  # noqa: E402
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

    def test_preview_as_committed(self):
        if PIL.__version__ != PREVIEW_PILLOW:
            self.skipTest("Pillow %s, not %s: the PNG bytes differ" % (PIL.__version__, PREVIEW_PILLOW))
        self.assertTrue(same_bytes(os.path.join(self.tmp.name, "art", "preview.png"),
                                   os.path.join(REPO, "art", "preview.png")))


def board_colour(rgb):
    """The colour as the board shows it, after the RGB565 cut."""
    return q565(Image.new("RGBA", (1, 1), tuple(rgb) + (255,))).getpixel((0, 0))[:3]


class LooksTest(unittest.TestCase):
    """The looks on a keyed runner sprite: the board skips alpha 0, so a look must never change the mask."""

    @classmethod
    def setUpClass(cls):
        cls.sprite = runner(run_cycle()[0])

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


if __name__ == "__main__":
    unittest.main()
