"""games/marshmallow.py on the Mac (P773): the Roast's rules, the two flames, and the game with no engine and on the
ctypes stand-in for engine.HeatField of test_fire.py. Run from the repository root: python3 -m unittest discover tests.
--- MVP (P773) ---"""

import contextlib
import io
import shutil
import sys
import unittest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import test_fire  # noqa: E402  (puts games/ and stubs/ on the path)
from test_fire import Engine, Recorder, Tft  # noqa: E402

import cues  # noqa: E402
import fire  # noqa: E402
import gfx  # noqa: E402
import marshmallow as mm  # noqa: E402
import signals  # noqa: E402
from marshmallow import BLACK, BURN, GOLDEN, SERVE, WHITE, Roast  # noqa: E402

FLAME_TOP = gfx.HEIGHT - mm.BOTTOM_Y  # a flame whose top is the marshmallow's bottom edge at depth 0: under is 0 there


def roast_at(depth, browned=0):
    roast = Roast()
    roast.depth, roast.browned = depth, browned
    return roast


class RoastTest(unittest.TestCase):
    def test_held_lowers_it_and_released_lifts_it_in_whole_px(self):
        roast = Roast()
        for _ in range(10):
            roast.update(100, True, 0)
        self.assertEqual(mm.LOWER_PX_S, roast.depth)  # one second held
        for _ in range(5):
            roast.update(100, False, 0)
        self.assertEqual(mm.LOWER_PX_S - mm.LIFT_PX_S // 2, roast.depth)  # half a second released
        roast.update(7, True, 0)  # 7 ms is under a pixel: the rest is carried, not lost
        roast.update(7, True, 0)
        self.assertEqual(mm.LOWER_PX_S - mm.LIFT_PX_S // 2 + mm.LOWER_PX_S * 14 // 1000, roast.depth)

    def test_depth_stays_between_the_top_and_the_deepest_place(self):
        roast = Roast()
        roast.update(60, False, 0)
        self.assertEqual(0, roast.depth)
        for _ in range(100):
            roast.update(60, True, 0)
        self.assertEqual(mm.DEPTH_MAX, roast.depth)
        roast.update(60, False, 0)  # lifting from the stop starts at once: no debt is carried
        self.assertEqual(mm.DEPTH_MAX - mm.LIFT_PX_S * 60 // 1000, roast.depth)

    def test_under_is_the_px_of_the_bottom_edge_below_the_flame_top_and_never_negative(self):
        roast = roast_at(50)
        roast.update(10, True, FLAME_TOP + 20)  # 1 px lower, 51: the flame top is 20 px above the edge's y at depth 0
        self.assertEqual(10 * (51 + 20), roast.browned)
        roast = roast_at(50)
        roast.update(10, True, FLAME_TOP - 100)  # a flame far below the bottom edge
        self.assertEqual(0, roast.browned)

    def test_browned_grows_by_under_times_ms(self):
        roast = roast_at(100)
        roast.update(40, False, gfx.HEIGHT)  # a flame to the top of the screen: under is the whole bottom edge's y
        depth = roast.depth  # 100 - 8 px lifted
        self.assertEqual(40 * (mm.BOTTOM_Y + depth), roast.browned)

    def test_the_colour_is_white_under_golden_golden_under_black_else_black(self):
        for browned, colour in ((0, WHITE), (mm.GOLDEN_AT - 1, WHITE), (mm.GOLDEN_AT, GOLDEN),
                                (mm.BLACK_AT - 1, GOLDEN), (mm.BLACK_AT, BLACK)):
            self.assertEqual(colour, roast_at(0, browned).colour(), browned)

    def test_black_is_a_burn_once_it_browns_no_more_and_counts_a_lost_one(self):
        roast = roast_at(100, mm.BLACK_AT - 1)
        self.assertEqual(BURN, roast.update(40, True, gfx.HEIGHT))
        self.assertEqual((1, BLACK), (roast.lost, roast.colour()))
        browned = roast.browned
        self.assertIsNone(roast.update(40, True, gfx.HEIGHT))  # still in the flames: no second burn, no more brown
        self.assertEqual((1, browned), (roast.lost, roast.browned))

    def test_a_black_one_at_the_top_is_replaced_by_a_white_one_with_no_outcome(self):
        roast = roast_at(1, mm.BLACK_AT)
        roast.lost = 1
        self.assertIsNone(roast.update(40, False, FLAME_TOP))  # lifted to 0
        self.assertEqual((0, 0, WHITE, 1), (roast.depth, roast.browned, roast.colour(), roast.lost))

    def test_a_golden_one_at_the_top_is_served_and_a_white_one_comes(self):
        roast = roast_at(1, mm.GOLDEN_AT)
        self.assertEqual(SERVE, roast.update(40, False, FLAME_TOP))
        self.assertEqual((0, 0, WHITE, 0), (roast.depth, roast.browned, roast.colour(), roast.lost))

    def test_a_white_one_at_the_top_is_neither(self):
        roast = roast_at(1, mm.GOLDEN_AT - 1)
        self.assertIsNone(roast.update(40, False, FLAME_TOP))
        self.assertEqual(mm.GOLDEN_AT - 1, roast.browned)  # it keeps what it had

    def test_the_third_lost_one_is_the_last_life(self):
        roast = Roast()
        for n in range(mm.LIVES):
            roast.depth, roast.browned = 100, mm.BLACK_AT - 1
            self.assertEqual(BURN, roast.update(40, True, gfx.HEIGHT))
            self.assertEqual(n + 1, roast.lost)
            roast.depth, roast.browned = 0, mm.BLACK_AT  # to the top, replaced by a white one
            roast.update(40, False, FLAME_TOP)
        self.assertEqual(mm.LIVES, roast.lost)

    def test_the_highest_flame_never_reaches_a_marshmallow_at_the_top(self):
        self.assertLessEqual(gfx.HEIGHT - mm.FLAME_MAX_PX, mm.BOTTOM_Y)
        roast = Roast()
        roast.update(60, False, mm.FLAME_MAX_PX)
        self.assertEqual(0, roast.browned)

    def test_lift_speed_saves_a_golden_one_from_the_deepest_place_under_the_highest_flame(self):
        """By the constants: lifting from DEPTH_MAX at a still flame of FLAME_MAX_PX adds under_max squared over twice
        the lift speed (px times ms), and golden plus that stays under black."""
        under_max = mm.BOTTOM_Y + mm.DEPTH_MAX - (gfx.HEIGHT - mm.FLAME_MAX_PX)
        self.assertGreater(under_max, 0)
        extra = under_max * under_max * 1000 // (2 * mm.LIFT_PX_S)
        self.assertLess(mm.GOLDEN_AT + extra, mm.BLACK_AT)
        for ms in (40, 60):  # and by steps of the longest frame, with the rounding of whole px
            roast = roast_at(mm.DEPTH_MAX, mm.GOLDEN_AT)
            outcomes = []
            while roast.depth:
                outcomes.append(roast.update(ms, False, mm.FLAME_MAX_PX))
            self.assertEqual([None] * (len(outcomes) - 1) + [SERVE], outcomes, ms)
