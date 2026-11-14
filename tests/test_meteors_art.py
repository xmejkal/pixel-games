"""Meteors' pictures (P773, story 4): the committed games/packs hold every picture the game draws, none empty, the
walker's left poses the exact mirror of the right, his soles on the last row, his top within the 32 px hit box, his
torso at the box's middle and a pixel of him in the box's columns on every row; the game's copies of the art's sizes
agree. Only when the CMU files are downloaded: the stride the game walks by, and the set painted again gives the
committed bytes. Run from the repository root: python3 -m unittest discover tests."""

import contextlib
import io
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names
sys.path.insert(0, os.path.join(REPO, "tests", "stubs"))
sys.path.insert(0, os.path.join(REPO, "games"))
sys.path.insert(0, os.path.join(REPO, "tests"))

from PIL import ImageOps  # noqa: E402

import meteors as game  # noqa: E402  games/meteors.py
import mocap  # noqa: E402
from export import pack_bytes, to_bin  # noqa: E402
from sets import meteors as art_set  # noqa: E402  art/sets/meteors.py
from test_rescue_art import art, opaque_rows, picture  # noqa: E402

TORSO_PX = 2  # the torso's middle lies this close to the hit box's, at most
FLIGHT_PX = 2  # a run pose's soles lie this close to the last row, at most: the run's flight
TOP_PX = 2  # the tallest pose's top lies this close to the box's top, at most


def torso_middle(img):
    """The mean x of the figure's pixels on the rows from a quarter to a half of its height below its top: the chest
    and the belly, under the scarf and over the hips."""
    rows = opaque_rows(img)
    a = img.getchannel("A")
    top, h = rows[0], rows[-1] - rows[0]
    xs = [x for y in range(top + h // 4, top + h // 2) for x in range(img.width) if a.getpixel((x, y))]
    return sum(xs) / len(xs)


class CommittedPicturesTest(unittest.TestCase):
    """On the committed games/packs, not painted again: these hold without the CMU files."""

    @classmethod
    def setUpClass(cls):
        cls.art = art()
        cls.poses = {(kind, side): [picture(name) for name in game.POSES[kind, side]]
                     for kind in ("run", "hit") for side in "rl"}

    def test_every_picture_the_game_draws_is_there_and_none_is_empty(self):
        names = [n for poses in game.POSES.values() for n in poses] + list(game.ROCKS) + list(game.EMBERS) + list(
            game.PUFFS) + ["meteors_sky", "meteors_ground", "meteors_halo", "meteors_glow", "meteors_shadow",
                           "meteors_ring", "meteors_flash"]
        self.assertEqual(sorted(names), sorted(n for n in self.art if n.startswith("meteors_")))
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(opaque_rows(picture(name)))

    def test_the_sizes_the_game_draws_by_are_the_pictures_sizes(self):
        sizes = {"meteors_rock0": (game.ROCK, game.ROCK), "meteors_halo": (game.HALO, game.HALO),
                 "meteors_coal0": (game.COAL_W, game.COAL_H), "meteors_glow": (game.GLOW_W, game.GLOW_H),
                 "meteors_shadow": (game.SHADOW_W, game.SHADOW_H), "meteors_ring": (game.RING_W, game.RING_H),
                 "meteors_flash": (game.WIDTH, game.FLASH_H), "meteors_smoke0": (game.SMOKE_W, game.SMOKE_H),
                 "meteors_run_r0": (game.FIG_W, game.FIG_H), "meteors_sky": (game.WIDTH, game.HEIGHT),
                 "meteors_ground": (game.WIDTH, game.HEIGHT - game.GROUND_TOP)}
        for name, size in sizes.items():
            with self.subTest(name=name):
                self.assertEqual(size, tuple(self.art[name][:2]))
        self.assertEqual((art_set.FIG, art_set.FIG_DX, art_set.RUN.poses), ((game.FIG_W, game.FIG_H), game.FIG_DX,
                                                                            game.RUN_POSES))
        self.assertEqual(game.SHADOW_W, game.BODY)  # the shadow is the mark's full width
        self.assertEqual(art_set.GROUND_TOP, game.GROUND_TOP)
        sky, ground = picture("meteors_sky"), picture("meteors_ground")  # the band is the sky's, to the pixel
        self.assertEqual(to_bin(sky.crop((0, game.GROUND_TOP, game.WIDTH, game.HEIGHT)), False), to_bin(ground, False))

    def test_each_left_pose_is_the_exact_mirror_of_its_right_pose(self):
        for kind in ("run", "hit"):
            for i, (right, left) in enumerate(zip(self.poses[kind, "r"], self.poses[kind, "l"])):
                with self.subTest(kind=kind, pose=i):
                    self.assertEqual(to_bin(ImageOps.mirror(right), True), to_bin(left, True))

    def test_the_soles_stand_on_the_last_row(self):
        for kind in ("run", "hit"):
            lowest = [opaque_rows(img)[-1] for img in self.poses[kind, "r"]]
            self.assertEqual(game.FIG_H - 1, max(lowest))
            for i, row in enumerate(lowest):
                with self.subTest(kind=kind, pose=i):
                    self.assertLessEqual(game.FIG_H - 1 - row, FLIGHT_PX)

    def test_the_walker_fits_the_hit_box(self):
        """Drawn at his left edge less FIG_DX with his soles on the screen's last row: his top no higher than the box's
        and within TOP_PX of it (he fills the box), his torso's middle within TORSO_PX of the box's, and on every row
        of him a pixel in the box's columns."""
        box = range(game.FIG_DX, game.FIG_DX + game.WALKER_W)
        middle = game.FIG_DX + (game.WALKER_W - 1) / 2
        box_top = game.WALKER_H - game.FIG_H  # the box's top row in the picture's rows: the picture's own top or lower
        self.assertGreaterEqual(box_top, 0)
        tops = []
        for kind in ("run", "hit"):
            for side in "rl":
                for i, img in enumerate(self.poses[kind, side]):
                    a = img.getchannel("A")
                    rows = opaque_rows(img)
                    tops.append(rows[0])
                    with self.subTest(kind=kind, side=side, pose=i):
                        self.assertGreaterEqual(rows[0] + box_top, 0)  # the screen row of his top is in the box
                        self.assertLessEqual(abs(torso_middle(img) - middle), TORSO_PX)
                        self.assertEqual([], [y for y in rows if not any(a.getpixel((x, y)) for x in box)])
        self.assertLessEqual(min(tops) - box_top, TOP_PX)


class CaptureTest(unittest.TestCase):
    """Only with the CMU files: the stride the game's pose follows, and the set painted again."""

    def setUp(self):
        self.capture = mocap.Capture()
        if self.capture.missing():
            self.skipTest("the CMU files are not in %s: the walker's stride and the meteors bytes were not checked "
                          "(download them to run this)" % mocap.CMU_DIR)

    def test_the_games_stride_is_the_captures_at_the_walkers_scale(self):
        self.assertEqual(game.STRIDE_PX, round(self.capture.stride(art_set.RUN) * art_set.WALKER_PX))

    def test_the_meteors_set_repaints_as_committed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            painting = art_set.ART_SET.paint()
        for name, (img, keyed) in painting.pictures.items():
            with self.subTest(name=name):
                self.assertEqual(to_bin(img, keyed), pack_bytes(name))


if __name__ == "__main__":
    unittest.main()
