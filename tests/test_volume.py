"""games/volume.py on the Mac (P757): the master volume's gains and its scale of a block. No board.
Run from the repository root: python3 -m unittest discover tests. --- MVP (P757) ---"""

import math
import os
import sys
import unittest
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))

import volume_viper  # noqa: E402
from volume import DB_PER_STEP, DEFAULT_STEP, FULL, GAINS, STEPS, MasterVolume, VolumeKnob  # noqa: E402
from volume_viper import CASES, CORNERS, ViperMasterVolume  # noqa: E402


class Ptr16:
    """Viper's ptr16 on the Mac: a read is unsigned, and a store keeps the low 16 bits."""

    def __init__(self, buf):
        self.view = memoryview(buf).cast("B").cast("H")

    def __getitem__(self, i):
        return self.view[i]

    def __setitem__(self, i, value):
        self.view[i] = value & 0xFFFF


volume_viper.ptr16 = Ptr16


def samples(*values):
    return array("h", values)


class GainsTest(unittest.TestCase):
    def test_step_0_is_silent_and_the_last_step_is_the_mix_as_it_is(self):
        self.assertEqual(len(GAINS), STEPS + 1)
        self.assertEqual((GAINS[0], GAINS[STEPS]), (0, FULL))

    def test_each_step_is_3_db(self):
        for step in range(2, STEPS + 1):
            self.assertAlmostEqual(20 * math.log10(GAINS[step] / GAINS[step - 1]), DB_PER_STEP, delta=0.03)


class ScaleTest(unittest.TestCase):
    def test_a_steady_full_gain_leaves_the_block_as_it_is(self):
        buf = samples(32767, -32768, 1, -1, 0, 1234, -1234, 7)
        MasterVolume().scale(buf, FULL, FULL)
        self.assertEqual(list(buf), [32767, -32768, 1, -1, 0, 1234, -1234, 7])

    def test_a_steady_gain_of_0_gives_zeros(self):
        buf = samples(32767, -32768, 1, -1, 0, 1234, -1234, 7)
        MasterVolume().scale(buf, 0, 0)
        self.assertEqual(list(buf), [0] * 8)

    def test_a_steady_half_gain_halves_and_keeps_the_sign(self):
        buf = samples(32767, -32768, 1000, -1000, 0, 2, -2, 1)
        MasterVolume().scale(buf, FULL // 2, FULL // 2)
        self.assertEqual(list(buf), [16383, -16384, 500, -500, 0, 1, -1, 0])

    def test_a_ramp_up_rises_and_ends_within_1_of_the_end(self):
        buf = samples(*[16384] * 256)  # a sample of 16384 reads the gain: out = gain >> 1
        MasterVolume().scale(buf, 0, FULL)
        out = list(buf)
        self.assertEqual(out, sorted(out))
        self.assertGreater(out[0], 0)  # the first sample already moved: no sample repeats the old gain
        self.assertIn(out[-1], (16383, 16384))

    def test_a_ramp_down_falls_and_never_passes_the_end(self):
        buf = samples(*[16384] * 256)
        MasterVolume().scale(buf, FULL, 0)
        out = list(buf)
        self.assertEqual(out, sorted(out, reverse=True))
        self.assertEqual(out[-1], 0)
        self.assertGreaterEqual(min(out), 0)  # a gain under 0 turned the sign over

    def test_a_ramp_over_a_block_whose_length_does_not_divide_the_change(self):
        buf = samples(*[-32768] * 24)  # a sample of -32768 reads the gain: out = -gain
        MasterVolume().scale(buf, 1002, 1000)
        self.assertEqual(sorted({-v for v in buf}), [1000, 1001])  # down: it reaches the end and never passes it
        buf = samples(*[-32768] * 24)
        MasterVolume().scale(buf, 1000, 1002)
        self.assertEqual(sorted({-v for v in buf}), [1000, 1001])  # up: it stops 1 under, and apply keeps the end


class MasterVolumeTest(unittest.TestCase):
    def test_set_clamps_to_the_steps(self):
        volume = MasterVolume()
        self.assertEqual(volume.step, DEFAULT_STEP)
        volume.set(STEPS + 3)
        self.assertEqual(volume.step, STEPS)
        volume.set(-2)
        self.assertEqual(volume.step, 0)

    def test_the_first_block_fades_in_and_the_next_is_steady(self):
        volume, buf = MasterVolume(STEPS), samples(*[16384] * 256)
        volume.apply(buf)
        self.assertLess(buf[0], 100)
        self.assertEqual(volume.gain, FULL)
        buf = samples(*[16384] * 256)
        volume.apply(buf)
        self.assertEqual(set(buf), {16384})

    def test_a_new_step_is_reached_in_one_block(self):
        volume = MasterVolume(STEPS)
        volume.apply(samples(*[0] * 8))
        volume.set(4)
        volume.apply(samples(*[0] * 8))
        self.assertEqual(volume.gain, GAINS[4])
        buf = samples(*[16384] * 8)
        volume.apply(buf)
        self.assertEqual(set(buf), {GAINS[4] >> 1})

    def test_step_0_is_true_silence(self):
        volume = MasterVolume(0)
        buf = samples(32767, -32768, 1, -1, 5, -5, 9, -9)
        volume.apply(buf)
        self.assertEqual(list(buf), [0] * 8)

    def test_the_mix_as_it_is_skips_the_scale(self):
        calls = []

        class Counted(MasterVolume):
            def scale(self, buf, start, end):
                calls.append((start, end))

        volume = Counted(STEPS)
        volume.apply(samples(*[1] * 8))  # the fade in
        volume.apply(samples(*[1] * 8))
        self.assertEqual(calls, [(0, FULL)])


class FakeEncoder:
    """take_detents gives the next of `turns`, then 0."""

    def __init__(self, *turns):
        self.turns = list(turns)

    def take_detents(self, now_ms):
        return self.turns.pop(0) if self.turns else 0


class VolumeKnobTest(unittest.TestCase):
    def test_each_detent_is_one_step_and_poll_says_when_the_step_changed(self):
        volume = MasterVolume(8)
        knob = VolumeKnob(FakeEncoder(1, 0, -3, 2), volume)
        seen = [(knob.poll(40 * k), volume.step) for k in range(5)]
        self.assertEqual(seen, [(True, 9), (False, 9), (True, 6), (True, 8), (False, 8)])

    def test_a_turn_past_an_end_is_dropped_and_the_first_detent_back_counts(self):
        volume = MasterVolume(15)
        knob = VolumeKnob(FakeEncoder(5, -1, -20, 1), volume)
        seen = [(knob.poll(40 * k), volume.step) for k in range(4)]
        self.assertEqual(seen, [(True, STEPS), (True, STEPS - 1), (True, 0), (True, 1)])

    def test_a_turn_at_an_end_changes_nothing(self):
        volume = MasterVolume(STEPS)
        self.assertFalse(VolumeKnob(FakeEncoder(2), volume).poll(0))
        self.assertEqual(volume.step, STEPS)

    def test_louder_flips_the_direction(self):
        volume = MasterVolume(8)
        VolumeKnob(FakeEncoder(2), volume, louder=-1).poll(0)
        self.assertEqual(volume.step, 6)


class ViperMasterVolumeTest(unittest.TestCase):
    def test_the_viper_scale_gives_the_naive_samples_on_each_named_block(self):
        for start, end in CASES:
            naive, viper = samples(*CORNERS * 32), samples(*CORNERS * 32)
            MasterVolume().scale(naive, start, end)
            ViperMasterVolume().scale(viper, start, end)
            self.assertEqual(list(viper), list(naive), (start, end))
        self.assertTrue(volume_viper.scale_match())

    def test_scale_match_sees_a_scale_that_differs(self):
        class OffByOne(MasterVolume):
            def scale(self, buf, start, end):
                buf[5] = 1  # the naive scale leaves this corner at 0

        kept, volume_viper.ViperMasterVolume = volume_viper.ViperMasterVolume, OffByOne
        try:
            self.assertFalse(volume_viper.scale_match())
        finally:
            volume_viper.ViperMasterVolume = kept

    def test_apply_reaches_the_step_as_the_naive_class_does(self):
        naive, viper = MasterVolume(5), ViperMasterVolume(5)
        for _ in range(2):  # the fade in, then the steady block
            a, b = samples(*CORNERS * 32), samples(*CORNERS * 32)
            naive.apply(a)
            viper.apply(b)
            self.assertEqual(list(b), list(a))
        self.assertEqual(viper.gain, GAINS[5])


if __name__ == "__main__":
    unittest.main()
