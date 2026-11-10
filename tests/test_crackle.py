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

from crackle import CRACKLE_LOOK, PEAK, SAMPLED_POPS, Crackle, SampledCrackle  # noqa: E402
from crackle_lib import HAVE_CLANG, CCrackle  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
