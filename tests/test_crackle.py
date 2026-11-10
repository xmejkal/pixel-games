"""games/crackle.py on the Mac (P747): the Python Crackle against the C of engine/core/fx_crackle.c, sample for sample,
and its pop queue. Run from the repository root: python3 -m unittest discover tests. --- MVP (P747) ---"""

import os
import random
import sys
import unittest
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engine", "tests"))  # pixel-engine: crackle_lib

from crackle import (CRACKLE_LOOK, GRAIN_LOOK, PEAK, SAMPLED_POPS, Crackle, GrainCrackle, SampledCrackle,  # noqa: E402
                     check_grain_look, check_look)
from crackle_lib import HAVE_CLANG, CCrackle  # noqa: E402
from fire_bank import FIRE_BANK_INDEX  # noqa: E402
from grains_lib import GrainsModule  # noqa: E402

RATE, BLOCK = 16000, 256  # sound.py's RATE and REFILL_SAMPLES
FRAME_BLOCKS = 2  # about one Fire frame of 40 ms between two add_pops


def play(crackle, seconds, seed=747, burst=0.01):
    """seconds of blocks, with a few births before every second block, as Fire's frames add them (about 3.9 a
    second), and in burst of them a test's 9 at once, which fills every slot (Fire adds at most 2 a frame)."""
    rng, out, buf = random.Random(seed), array("h"), array("h", bytes(2 * BLOCK))
    for k in range(seconds * RATE // BLOCK):
        if k % FRAME_BLOCKS == 0:
            crackle.add_pops(9 if rng.random() < burst else 1 if rng.random() < 0.16 else 0)
        crackle.render(buf)
        out.extend(buf)
    return out


class CrackleTest(unittest.TestCase):
    def test_the_queue_counts_each_pop_once(self):
        c = Crackle(1)
        c.add_pops(2)
        c.add_pops(9)
        c.render(array("h", bytes(2 * BLOCK)))
        self.assertEqual(c.counts(), (11, 8, 3))  # 8 slots, so 3 of 11 at once drop
        c.render(array("h", bytes(2 * BLOCK)))
        self.assertEqual(c.counts(), (11, 8, 3))  # none starts twice

    def test_the_peak_stays_under_90_percent(self):
        self.assertLessEqual(max(map(abs, play(Crackle(5), 10, burst=0))), PEAK * 9 // 10)

    def test_a_look_out_of_range_is_refused(self):
        check_look(CRACKLE_LOOK)
        for i, bad in ((0, 9), (3, 16384), (5, 32768), (8, 1024)):  # a C shift past 31 or a Python long int
            look = list(CRACKLE_LOOK)
            look[i] = bad
            with self.assertRaises(ValueError):
                Crackle(1, tuple(look))

    def test_sampled_pops_end_inside_their_samples(self):
        for pop in SampledCrackle(747).pops:
            self.assertGreater(max(map(abs, pop)), 0)
            self.assertEqual(max(map(abs, pop[-200:])), 0)

    def test_sampled_crackle_plays_one_pop_a_frame(self):
        c, buf = SampledCrackle(747), array("h", bytes(2 * BLOCK))
        c.add_pops(2)
        c.render(buf)
        self.assertEqual((c.counts(), list(buf)), ((2, 1, 1), list(c.pops[0][:BLOCK])))
        for _ in range(SAMPLED_POPS):
            c.add_pops(1)
        c.render(buf)
        self.assertEqual((c.counts(), list(buf)), ((6, 2, 4), list(c.pops[0][:BLOCK])))  # the 4th wraps to pop 0

    @unittest.skipUnless(HAVE_CLANG, "clang is needed")
    def test_python_equals_c_sample_for_sample(self):
        python, c = Crackle(747), CCrackle(747, CRACKLE_LOOK)
        self.assertEqual(play(python, 10), play(c, 10))
        self.assertEqual(python.counts(), c.counts())
        self.assertGreater(python.counts()[2], 0)  # the bursts of 9 dropped some, the same in both


@unittest.skipUnless(HAVE_CLANG, "clang is needed")
class GrainCrackleTest(unittest.TestCase):
    """P751's pass lines on the Mac: on 15 s with Fire's births, RMS 1500 to 2500, under 0.1 % of samples at the clamp,
    and every 16 ms block's RMS above 200 (the bed never silent)."""

    @classmethod
    def setUpClass(cls):
        bank = os.path.join(os.path.dirname(HERE), "games", "fire_bank.raw")
        cls.crackle = GrainCrackle(747, bank_path=bank, native=GrainsModule())
        cls.out = play(cls.crackle, 15, burst=0)

    def test_the_bank_matches_its_index(self):
        last = FIRE_BANK_INDEX[-3] + FIRE_BANK_INDEX[-2]
        self.assertEqual(len(self.crackle.bank), 2 * last)
        self.assertLess(len(self.crackle.bank), 256 * 1024)

    def test_rms_is_1500_to_2500(self):
        rms = (sum(v * v for v in self.out) / len(self.out)) ** 0.5
        self.assertTrue(1500 <= rms <= 2500, rms)

    def test_under_a_tenth_of_a_percent_is_clamped(self):
        self.assertLess(sum(abs(v) >= PEAK for v in self.out) / len(self.out), 0.001)

    def test_the_bed_is_never_silent(self):
        blocks = [self.out[k:k + 256] for k in range(0, len(self.out), 256)]
        self.assertGreater(min((sum(v * v for v in b) / 256) ** 0.5 for b in blocks), 200)

    def test_each_birth_starts_one_pop_and_a_burst_drops_the_rest(self):
        c = GrainCrackle(1, bank_path=os.path.join(os.path.dirname(HERE), "games", "fire_bank.raw"),
                         native=GrainsModule())
        c.add_pops(9)
        c.render(array("h", bytes(2 * BLOCK)))
        self.assertEqual(c.counts(), (9, 8, 1))

    def test_a_look_out_of_range_is_refused(self):
        check_grain_look(GRAIN_LOOK)
        for bad in ((-1, 0), (0, 32769), (1,)):
            with self.assertRaises(ValueError):
                check_grain_look(bad)


if __name__ == "__main__":
    unittest.main()
