"""games/engine/subpixel.py on the Mac (P872): a speed in px a second, stepped by a frame's ms, answers whole px and
keeps the rest for the next step. Run from the repository root: python3 -B -m unittest tests.test_subpixel.
--- MVP (P872) ---"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))

from engine.subpixel import SubPixel  # noqa: E402


class SubPixelTest(unittest.TestCase):
    def test_240_px_s_for_250_ms_is_60_px(self):
        self.assertEqual(60, SubPixel().step(240, 250))

    def test_1_px_s_moves_1_px_only_when_its_1000_ms_are_up(self):
        motion, moved = SubPixel(), []
        for _ in range(25):
            moved.append(motion.step(1, 40))
        self.assertEqual([0] * 24 + [1], moved)
        self.assertEqual(0, motion.rest)

    def test_a_negative_speed_moves_back_and_its_rest_stays_0_to_999(self):
        motion = SubPixel()
        self.assertEqual(-1, motion.step(-1, 40))  # floor: 40 px.ms short is 1 px back, 960 to the next whole px
        self.assertEqual(960, motion.rest)
        total = -1
        for _ in range(24):
            total += motion.step(-1, 40)
            self.assertTrue(0 <= motion.rest <= 999, motion.rest)
        self.assertEqual(-1, total)  # 1000 ms of -1 px/s: 1 px back in all
        self.assertEqual(-60, SubPixel().step(-240, 250))

    def test_reset_drops_the_rest(self):
        motion = SubPixel()
        motion.step(1, 900)
        self.assertEqual(900, motion.rest)
        motion.reset()
        self.assertEqual(0, motion.rest)
        self.assertEqual(0, motion.step(1, 900))


if __name__ == "__main__":
    unittest.main()
