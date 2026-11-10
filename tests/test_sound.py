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

    def test_the_refill_that_takes_a_play_keeps_its_gap(self):
        mixer, i2s = Mixer(), FakeI2S()
        refill = CallbackRefill(mixer, i2s, FakePin(), 4 * REFILL_SAMPLES)
        refill.open()
        i2s.handler(i2s)
        self.assertEqual(refill.play_between, 0)
        mixer.play(samples(1))
        i2s.handler(i2s)
        self.assertEqual(refill.play_between, refill.between)
        self.assertIsNone(mixer.next)

    def test_the_block_is_a_multiple_of_8(self):
        self.assertEqual(sound.REFILL_SAMPLES % 8, 0)


if __name__ == "__main__":
    unittest.main()
