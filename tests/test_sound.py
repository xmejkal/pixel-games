"""games/sound.py on the Mac (P748): the Mixer renders one voice into blocks, and both refill drivers feed a fake I2S
in their own way. No board, no C. Run from the repository root: python3 -m unittest discover tests. --- MVP (P748) ---"""

import os
import sys
import time
import unittest
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)
if not hasattr(time, "sleep_ms"):
    time.sleep_ms = lambda ms: None

import sound  # noqa: E402
from sound import REFILL_SAMPLES, CallbackRefill, FrameRefill, Mixer  # noqa: E402
from volume import GAINS, STEPS, MasterVolume  # noqa: E402


def samples(*values):
    return array("h", values)


class FakeI2S:
    """Takes at most `room` samples per write, as a ring with that much free space does. irq() keeps the handler."""

    def __init__(self, room=10**9):
        self.room, self.out, self.handler, self.deinited = room, [], None, False

    def write(self, buf):
        view = memoryview(buf).cast("B").cast("h")
        n = min(len(view), self.room)
        self.room -= n
        self.out.extend(view[:n])
        return 2 * n

    def irq(self, handler):
        self.handler = handler

    def deinit(self):
        self.deinited = True
        self.sd_at_deinit = self.sd.level if getattr(self, "sd", None) else None


class FakePin:
    def __init__(self):
        self.level = 0

    def value(self, level):
        self.level = level


class MixerTest(unittest.TestCase):
    def test_render_copies_a_sound_then_silence(self):
        mixer, buf = Mixer(), samples(*[9] * 8)
        mixer.play(samples(1, 2, 3))
        mixer.render(buf)
        self.assertEqual(list(buf), [1, 2, 3, 0, 0, 0, 0, 0])
        mixer.render(buf)
        self.assertEqual(list(buf), [0] * 8)

    def test_a_sound_longer_than_a_block_goes_on_in_the_next(self):
        mixer, buf = Mixer(), samples(*[0] * 8)
        mixer.play(samples(*range(1, 13)))
        mixer.render(buf)
        self.assertEqual(list(buf), list(range(1, 9)))
        mixer.render(buf)
        self.assertEqual(list(buf), [9, 10, 11, 12, 0, 0, 0, 0])

    def test_a_looping_sound_wraps(self):
        mixer, buf = Mixer(), samples(*[0] * 8)
        mixer.play(samples(1, 2, 3), loop=True)
        mixer.render(buf)
        self.assertEqual(list(buf), [1, 2, 3, 1, 2, 3, 1, 2])
        mixer.render(buf)
        self.assertEqual(list(buf)[:2], [3, 1])

    def test_a_play_between_two_renders_starts_at_the_next(self):
        mixer, buf = Mixer(), samples(*[0] * 8)
        mixer.play(samples(*[1] * 20), loop=True)
        mixer.render(buf)
        mixer.play(samples(7, 7))
        mixer.render(buf)
        self.assertEqual(list(buf), [7, 7, 0, 0, 0, 0, 0, 0])

    def test_an_empty_looping_sound_is_silence(self):
        mixer, buf = Mixer(), samples(*[5] * 8)
        mixer.play(samples(), loop=True)  # it looped forever before the review
        mixer.render(buf)
        self.assertEqual(list(buf), [0] * 8)

    def test_any_multiple_of_8_is_filled(self):
        mixer = Mixer()
        for n in (8, 16, 256, 512):
            buf = samples(*[5] * n)
            mixer.render(buf)
            self.assertEqual(list(buf), [0] * n)


class RefillTest(unittest.TestCase):
    def test_frame_refill_writes_until_full_and_keeps_the_rest(self):
        mixer, i2s = Mixer(), FakeI2S(room=REFILL_SAMPLES + 100)
        mixer.play(samples(*range(1, 2 * REFILL_SAMPLES + 1)))
        refill = FrameRefill(mixer, i2s, FakePin(), 4 * REFILL_SAMPLES)
        refill.write()  # open() without select.poll
        self.assertEqual(refill.written, REFILL_SAMPLES + 100)
        self.assertEqual(refill.rest, REFILL_SAMPLES - 100)
        i2s.room = REFILL_SAMPLES - 100
        refill.refill()
        self.assertEqual(i2s.out, list(range(1, 2 * REFILL_SAMPLES + 1)))

    def test_frame_refill_renders_at_most_one_ring_a_write(self):  # P747
        mixer, i2s = Mixer(), FakeI2S()  # a ring that never fills, as when the mixer is slower than real time
        refill = FrameRefill(mixer, i2s, FakePin(), 4 * REFILL_SAMPLES)
        refill.write()
        self.assertEqual(refill.written, 4 * REFILL_SAMPLES)

    def test_callback_refill_writes_once_per_sent_and_none_after_close(self):
        mixer, i2s, sd = Mixer(), FakeI2S(), FakePin()
        refill = CallbackRefill(mixer, i2s, sd, 4 * REFILL_SAMPLES)
        refill.open()
        self.assertEqual((i2s.handler, sd.level, len(i2s.out)), (refill.sent, 1, REFILL_SAMPLES))
        i2s.handler(i2s)
        i2s.handler(i2s)
        self.assertEqual((len(i2s.out), refill.sent_count), (3 * REFILL_SAMPLES, 2))
        refill.close()
        i2s.handler(i2s)  # the task's last schedule, after deinit
        self.assertEqual((len(i2s.out), sd.level, i2s.deinited), (3 * REFILL_SAMPLES, 0, True))

    def test_a_refill_with_a_volume_writes_the_scaled_mix(self):  # --- MVP (P757) ---
        for refill_class in (FrameRefill, CallbackRefill):
            mixer, i2s = Mixer(), FakeI2S(room=2 * REFILL_SAMPLES)
            mixer.play(samples(*[16384] * (2 * REFILL_SAMPLES)))  # a sample of 16384 reads the gain: out = gain >> 1
            refill = refill_class(mixer, i2s, FakePin(), 4 * REFILL_SAMPLES, MasterVolume(STEPS - 2))
            refill.write()
            refill.write()  # the callback's second block; the frame refill wrote both in its first write
            first, second = i2s.out[:REFILL_SAMPLES], i2s.out[REFILL_SAMPLES:2 * REFILL_SAMPLES]
            self.assertEqual(first, sorted(first), refill_class.__name__)  # the fade in
            self.assertLess(first[0], 100, refill_class.__name__)
            self.assertEqual(set(second), {GAINS[STEPS - 2] >> 1}, refill_class.__name__)

    def test_a_refill_with_no_volume_writes_the_mix_as_it_is(self):  # P757
        for refill_class in (FrameRefill, CallbackRefill):
            mixer, i2s = Mixer(), FakeI2S(room=REFILL_SAMPLES)
            mixer.play(samples(*range(1, REFILL_SAMPLES + 1)))
            refill_class(mixer, i2s, FakePin(), 4 * REFILL_SAMPLES).write()
            self.assertEqual(i2s.out[:REFILL_SAMPLES], list(range(1, REFILL_SAMPLES + 1)), refill_class.__name__)

    def test_the_refill_that_takes_a_play_keeps_its_gap(self):
        mixer, i2s = Mixer(), FakeI2S()
        refill = CallbackRefill(mixer, i2s, FakePin(), 4 * REFILL_SAMPLES)
        refill.open()
        i2s.handler(i2s)
        self.assertEqual(refill.play_between, 0)
        mixer.play(samples(1))
        i2s.handler(i2s)
        self.assertEqual(refill.play_between, refill.between)
        self.assertIsNone(mixer.pending)

    def test_a_late_refill_counts_and_a_dead_chain_is_stalled(self):
        mixer, i2s = Mixer(), FakeI2S()
        refill = CallbackRefill(mixer, i2s, FakePin(), 4 * REFILL_SAMPLES)
        refill.open()
        self.assertFalse(refill.stalled(64_000))
        refill.last -= 200_000  # no refill for 200 ms
        self.assertTrue(refill.stalled(64_000))
        i2s.handler(i2s)
        self.assertEqual((refill.late, refill.between_max >= 200_000), (1, True))

    def test_an_error_in_render_still_queues_a_block(self):
        mixer, i2s = Mixer(), FakeI2S()
        refill = CallbackRefill(mixer, i2s, FakePin(), 4 * REFILL_SAMPLES)
        refill.open()
        mixer.render = None  # render raises TypeError
        with self.assertRaises(TypeError):
            i2s.handler(i2s)
        self.assertEqual(len(i2s.out), 2 * REFILL_SAMPLES)

    def test_close_turns_the_amplifier_off_before_deinit(self):
        i2s, sd = FakeI2S(), FakePin()
        i2s.sd = sd
        refill = CallbackRefill(Mixer(), i2s, sd, 4 * REFILL_SAMPLES)
        refill.open()
        refill.close()
        self.assertEqual(i2s.sd_at_deinit, 0)

    def test_the_block_is_a_multiple_of_8(self):
        self.assertEqual(sound.REFILL_SAMPLES % 8, 0)


if __name__ == "__main__":
    unittest.main()
