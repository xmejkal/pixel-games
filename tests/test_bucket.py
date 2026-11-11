"""games/bucket.py on the Mac (P773, story 2): the Rules with no display, and the game on Python's bodies and on the
ctypes stand-in for engine.Bodies of engine/tests/world_lib.py. Run from the repository root:
python3 -m unittest discover tests. --- MVP (P773) ---"""

import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engine", "tests"))  # pixel-engine: clang_lib
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

import bucket as bk  # noqa: E402
from bucket import Rules  # noqa: E402


class RulesTest(unittest.TestCase):
    def test_held_moves_the_bucket_right_and_released_moves_it_left_in_whole_px(self):
        rules = Rules()
        start = rules.bucket_x
        for _ in range(5):
            rules.move(100, True)
        self.assertEqual(start + bk.BUCKET_PX_S // 2, rules.bucket_x)  # half a second held
        for _ in range(2):
            rules.move(100, False)
        self.assertEqual(start + bk.BUCKET_PX_S // 2 - bk.BUCKET_PX_S // 5, rules.bucket_x)
        before = rules.bucket_x
        rules.move(3, True)  # 3 ms is under a pixel: the rest is carried, not lost
        rules.move(3, True)
        self.assertEqual(before + bk.BUCKET_PX_S * 6 // 1000, rules.bucket_x)

    def test_the_bucket_stays_on_the_screen_at_both_edges_and_leaves_an_edge_at_once(self):
        rules = Rules()
        for _ in range(100):
            rules.move(60, False)
        self.assertEqual(0, rules.bucket_x)
        rules.move(60, True)  # no debt is carried from the edge
        self.assertEqual(bk.BUCKET_PX_S * 60 // 1000, rules.bucket_x)
        for _ in range(100):
            rules.move(60, True)
        self.assertEqual(bk.WIDTH - bk.BUCKET_W, rules.bucket_x)
        rules.move(60, False)
        self.assertEqual(bk.WIDTH - bk.BUCKET_W - bk.BUCKET_PX_S * 60 // 1000, rules.bucket_x)

    def test_caught_needs_the_whole_box_inside_the_bucket_at_both_edges(self):
        rules = Rules()
        left, right = rules.bucket_x, rules.bucket_x + bk.BUCKET_W
        self.assertTrue(rules.caught(left))
        self.assertTrue(rules.caught(right - bk.SIZE))
        self.assertFalse(rules.caught(left - 1))
        self.assertFalse(rules.caught(right - bk.SIZE + 1))
        self.assertFalse(rules.caught(0 if left > bk.SIZE else bk.WIDTH - bk.SIZE))

    def test_the_drop_clock_drops_one_box_each_drop_ms_and_carries_the_rest(self):
        rules = Rules()
        drops, total = 0, 0
        for _ in range(1000):  # 42 ms frames
            total += 42
            drops += rules.due(42, True)
        self.assertEqual(total // bk.DROP_MS, drops)

    def test_a_full_pool_never_sends_a_burst(self):
        rules = Rules()
        for _ in range(500):
            self.assertFalse(rules.due(60, False))
        self.assertTrue(rules.due(1, True))  # a body frees: one box drops at once
        self.assertFalse(rules.due(1, True))  # and the clock starts again, with no second box
        self.assertFalse(rules.due(60, True))

    def test_each_point_shortens_the_drop_time_down_to_the_least(self):
        rules = Rules()
        self.assertEqual(bk.DROP_MS, rules.drop_ms())
        rules.score = 3
        self.assertEqual(bk.DROP_MS - 3 * bk.DROP_STEP_MS, rules.drop_ms())
        rules.score = 1000
        self.assertEqual(bk.DROP_MIN_MS, rules.drop_ms())
        self.assertGreater(bk.DROP_MIN_MS, 60)  # a frame holds one drop at most

    def test_a_catch_is_a_point(self):
        rules = Rules()
        self.assertEqual(1, rules.catch())
        self.assertEqual(2, rules.catch())
        self.assertEqual(2, rules.score)

    def test_a_miss_adds_to_its_column_and_the_pile_is_full_at_the_rail(self):
        rules = Rules()
        for k in range(1, bk.PILE_ROWS):
            self.assertEqual(k, rules.miss(5))
            self.assertFalse(rules.full(5))
        self.assertEqual(bk.PILE_ROWS, rules.miss(5))
        self.assertTrue(rules.full(5))
        self.assertFalse(rules.full(6))
        self.assertEqual(bk.HEIGHT - bk.SIZE * bk.PILE_ROWS, bk.RAIL_Y)

    def test_there_is_a_column_for_every_x_a_box_drops_at(self):
        self.assertEqual(bk.WIDTH, bk.COLS * bk.SIZE)
        self.assertEqual(bk.COLS, len(Rules().pile))


if __name__ == "__main__":
    unittest.main()
