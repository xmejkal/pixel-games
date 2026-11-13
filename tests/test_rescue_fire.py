"""Rescue's fire on the heat field (P803), on test_fire.py's ctypes stand-in for engine.HeatField: with cool, as the
firmware built from an engine with P803, and without it, as the board's firmware before. The frame a fire ends, its
columns are emptied; a fire far from it keeps every cell of its flame, and a fire near it is burned back in. Without
cool the whole field is emptied and every fire is burned back in. The field's step is held for that frame, so only
the end and the burns change it. Needs clang. Run from the repository root: python3 -m unittest discover tests.
--- MVP (P803) ---"""

import contextlib
import io
import random
import shutil
import sys
import unittest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import test_fire  # noqa: E402  (puts games/ and stubs/ on the path)
from test_fire import Engine  # noqa: E402

import fire  # noqa: E402
import rescue  # noqa: E402
from rescue import HEAT_REACH, Crater  # noqa: E402

NEVER = 10 ** 9  # ms: no meteor falls and nobody comes out
FAR_PX, NEAR_PX = 80, 30  # 40 cells apart, out of each other's reach; 15 cells, in it
END_X = 120  # px: the crater whose fire ends
FULL_FRAMES = 50  # 2 s of frames: both flames are full


def regrows(burns, x):
    """The REGROW burns (radius 3) into the fire at x px."""
    return [b for b in burns if b[4] == 3 and b[0] == b[2] == x // 2]


@unittest.skipUnless(shutil.which("clang"), "clang is missing: engine/core/fx_fire.c is not built")
class FireEndsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_fire.FireTest.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def tearDown(self):
        fire.engine = None

    def end_beside(self, apart_px, cool=True):
        """A round with a fire at END_X + apart_px that burns on and one at END_X that ends after FULL_FRAMES. The heat
        before and after the frame it ends, the fire that burns on, the game and the burns of that frame."""
        fire.engine = Engine(self.lib, cool)
        random.seed(803)
        with contextlib.redirect_stdout(io.StringIO()):
            game = rescue.Rescue()
        now = 0
        game.step(now, True, True)  # the title's press
        rules = game.rules
        rules.meteor_ms = rules.come_ms = NEVER
        on, ends = Crater(END_X + apart_px), Crater(END_X)
        ends.left_ms = FULL_FRAMES * 40 + 1
        rules.craters += [on, ends]
        for _ in range(FULL_FRAMES):
            now += 40
            game.step(now, False, False)
        self.assertTrue(on.burning() and ends.burning())
        game.layer.field.step = lambda n, wind: None  # held: only the end and the burns change the field
        before, fire.engine.burns, fire.engine.scrolls = bytes(game.layer.field.heat[:fire.W * fire.H]), [], []
        game.step(now + 40, False, False)
        self.assertFalse(ends.burning())
        return before, bytes(game.layer.field.heat[:fire.W * fire.H]), on, game, fire.engine.burns

    def cells(self, heat, x_px):
        """The cells of the columns HEAT_REACH each side of x px, row by row."""
        x = x_px // 2
        return [heat[y * fire.W + c] for y in range(fire.H) for c in range(x - HEAT_REACH, x + HEAT_REACH + 1)]

    def test_a_far_fire_keeps_every_cell_of_its_flame_and_is_not_burned_back(self):
        before, after, on, game, burns = self.end_beside(FAR_PX)
        self.assertTrue(any(self.cells(before, on.x)))
        lowered = [(a, b) for a, b in zip(self.cells(before, on.x), self.cells(after, on.x)) if b < a]
        self.assertEqual(0, len(lowered))  # its own foot's burns only raise cells
        self.assertEqual([], regrows(burns, on.x))
        self.assertTrue(game.layer.can_cool)
        self.assertEqual([(END_X // 2 - HEAT_REACH, 0, END_X // 2 + HEAT_REACH, fire.H - 1, 255)], fire.engine.cools)
        self.assertEqual([], fire.engine.scrolls)  # no clear

    def test_the_ended_fire_s_columns_are_empty(self):
        before, after, *_ = self.end_beside(FAR_PX)
        self.assertTrue(any(self.cells(before, END_X)))
        self.assertFalse(any(self.cells(after, END_X)))

    def test_a_near_fire_is_burned_back_in(self):
        _, _, on, _, burns = self.end_beside(NEAR_PX)
        self.assertEqual(len(rescue.REGROW), len(regrows(burns, on.x)))
        self.assertEqual([], fire.engine.scrolls)

    def test_without_cool_the_field_is_emptied_and_even_a_far_fire_is_burned_back_in(self):
        _, after, on, game, burns = self.end_beside(FAR_PX, cool=False)
        self.assertFalse(game.layer.can_cool)
        self.assertEqual([-fire.W], fire.engine.scrolls)  # FireLayer.clear: a scroll by the whole width
        self.assertEqual(len(rescue.REGROW), len(regrows(burns, on.x)))
        self.assertFalse(any(self.cells(after, END_X)))


if __name__ == "__main__":
    unittest.main()
