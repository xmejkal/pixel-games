"""Bucket's pictures (P773, story 4): the committed games/packs hold every picture the game draws, none empty, at
the sizes the game draws them by; a pile's column is the crates in the woods the falling crates show, and the rows and
places the game keeps (the rail, the chimneys, the river's glints) are the painted scene's. Run from the repository
root: python3 -m unittest discover tests."""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names
sys.path.insert(0, os.path.join(REPO, "tests", "stubs"))
sys.path.insert(0, os.path.join(REPO, "games"))
sys.path.insert(0, os.path.join(REPO, "tests"))

import bucket as game  # noqa: E402  games/bucket.py
from export import to_bin  # noqa: E402
from sets import bucket as art_set  # noqa: E402  art/sets/bucket.py
from test_rescue_art import art, opaque_rows, picture  # noqa: E402


class CommittedPicturesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.art = art()

    def test_every_picture_the_game_draws_is_there_and_none_is_empty(self):
        names = [n for row in game.PILES[1:] for n in row] + list(game.CRATES) + list(game.SHIMMER) + list(
            game.PUFFS) + ["bucket_scene", "bucket_bucket", "bucket_tipped", "bucket_coin", "bucket_sparkle"]
        self.assertEqual(sorted(names), sorted(n for n in self.art if n.startswith("bucket_")))
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(opaque_rows(picture(name)))

    def test_the_sizes_the_game_draws_by_are_the_pictures_sizes(self):
        sizes = {"bucket_scene": (game.WIDTH, game.HEIGHT), "bucket_bucket": (game.BUCKET_W, game.BUCKET_H),
                 "bucket_sparkle": (game.SPARKLE, game.SPARKLE)}
        sizes.update({name: (game.SIZE, game.SIZE) for name in game.CRATES})
        sizes.update({name: size for name, size in zip(game.PUFFS, game.PUFF_SIZES)})
        for h in range(1, game.PILE_ROWS + 1):
            sizes.update({name: (game.SIZE, game.SIZE * h) for name in game.PILES[h]})
        for name, size in sizes.items():
            with self.subTest(name=name):
                self.assertEqual(size, tuple(self.art[name][:2]))
        self.assertEqual(game.TIPPED_H, self.art["bucket_tipped"][1])

    def test_the_bucket_stands_on_the_rail_its_mouth_over_the_walls_and_its_foot_narrower(self):
        img = picture("bucket_bucket")
        a = img.getchannel("A")
        self.assertEqual(game.BUCKET_H - 1, opaque_rows(img)[-1])  # drawn at RAIL_Y - BUCKET_H: its foot on the rail
        self.assertGreater(art_set.TUB[1], game.WALL_H)  # its mouth is at the walls' top or higher
        rim, foot = (sum(1 for x in range(img.width) if a.getpixel((x, y))) for y in (art_set.HANDLE + 1,
                                                                                     game.BUCKET_H - 1))
        self.assertEqual(game.BUCKET_W, rim)  # the rim spans the bucket's width
        self.assertLess(foot, rim)  # it narrows to its foot

    def test_a_pile_column_is_the_crates_in_the_woods_the_falling_crates_show(self):
        """A crate that falls in a column shows the wood (column + its place on the pile) % HUES, so it keeps its
        wood when it joins the pile's picture."""
        for h in range(1, game.PILE_ROWS + 1):
            for mix in range(game.HUES):
                column = picture(game.PILES[h][mix])
                for k in range(h):  # the k-th crate from the bottom
                    crate = column.crop((0, game.SIZE * (h - 1 - k), game.SIZE, game.SIZE * (h - k)))
                    with self.subTest(height=h, mix=mix, crate=k):
                        self.assertEqual(to_bin(picture(game.CRATES[(mix + k) % game.HUES]), True),
                                         to_bin(crate, True))

    def test_the_rows_and_places_the_game_keeps_are_the_paintings(self):
        self.assertEqual((art_set.RAIL_Y, art_set.CRATE, len(art_set.WOOD), art_set.BUCKET[0]),
                         (game.RAIL_Y, game.SIZE, game.HUES, game.BUCKET_W))
        self.assertEqual(art_set.CHIMNEYS, game.CHIMNEYS)
        self.assertEqual(art_set.GLINTS, game.GLINTS)
        self.assertEqual(art_set.PUFFS, game.PUFF_SIZES)
        self.assertEqual(art_set.TIPPED[1], game.TIPPED_H)


if __name__ == "__main__":
    unittest.main()
