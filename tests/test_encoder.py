"""games/encoder.py on the Mac (P758, P757): detents from a fake pulse counter, and the pin map's names. No board.
Run from the repository root: python3 -m unittest discover tests. --- MVP (P758, P757) ---"""

import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
if not hasattr(time, "ticks_diff"):  # the same three as tests/test_sound.py, which looks for ticks_diff too
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

import pins  # noqa: E402
from encoder import Encoder  # noqa: E402


class FakeCounter:
    def __init__(self, edges=0):
        self.edges = edges

    def value(self):
        return self.edges


class EncoderTest(unittest.TestCase):
    def test_detents_follow_the_edges_both_ways(self):
        counter = FakeCounter()
        knob = Encoder(counter, 4)
        for edges, detents in ((0, 0), (4, 1), (80, 20), (-80, -20), (-4, -1)):
            counter.edges = edges
            self.assertEqual(knob.detents(), detents, edges)

    def test_one_edge_off_a_detent_rounds_to_it(self):
        counter = FakeCounter()
        knob = Encoder(counter, 4)
        for edges, detents in ((1, 0), (-1, 0), (7, 2), (9, 2)):
            counter.edges = edges
            self.assertEqual(knob.detents(), detents, edges)

    def test_each_detent_spans_four_edges_and_a_half_goes_up(self):
        counter = FakeCounter()
        knob = Encoder(counter, 4)
        spans = {}
        for edges in range(-10, 11):
            counter.edges = edges
            spans.setdefault(knob.detents(), []).append(edges)
        self.assertEqual(spans[1], [2, 3, 4, 5])
        self.assertEqual(spans[2], [6, 7, 8, 9])
        self.assertEqual(spans[0], [-2, -1, 0, 1])
        self.assertEqual(spans[-1], [-6, -5, -4, -3])

    def test_edges_are_the_raw_count(self):
        self.assertEqual(Encoder(FakeCounter(-3), 4).edges(), -3)


class TakeDetentsTest(unittest.TestCase):  # --- MVP (P757) ---
    def knob_at(self, edges):
        """A knob that rests at `edges`, after its first take."""
        self.counter = FakeCounter(edges)
        knob = Encoder(self.counter, 4)
        self.assertEqual(knob.take_detents(0), 0)
        return knob

    def take(self, knob, edges, now_ms):
        self.counter.edges = edges
        return knob.take_detents(now_ms)

    def test_a_wobble_at_rest_is_no_turn(self):
        for rest in (9, 85, 5):  # run150's rest points, each 1 above a multiple of 4
            knob = self.knob_at(rest)
            for t, off in enumerate((1, 2, 0, -1, -2, 0, 1, -1)):
                self.assertEqual(self.take(knob, rest + off, 10 * t), 0, (rest, off))

    def test_each_click_of_4_edges_is_1_detent_both_ways(self):
        for rest in (9, 85, 5):
            knob = self.knob_at(rest)
            self.assertEqual([self.take(knob, rest + 4 * k, 40 * k) for k in (1, 2, 3)], [1, 1, 1], rest)
            self.assertEqual([self.take(knob, rest + 4 * k, 200 + 40 * k) for k in (2, 1, 0, -1)], [-1] * 4, rest)

    def test_a_fast_spin_between_two_takes_counts_every_detent(self):
        knob = self.knob_at(9)
        self.assertEqual(self.take(knob, 49, 40), 10)
        self.assertEqual(self.take(knob, 9, 80), -10)

    def test_3_to_6_edges_are_1_detent(self):
        for edges, detents in ((2, 0), (3, 1), (4, 1), (6, 1), (7, 2), (-2, 0), (-3, -1), (-6, -1), (-7, -2)):
            self.assertEqual(self.take(self.knob_at(0), edges, 40), detents, edges)

    def test_a_click_that_ends_1_edge_short_does_not_lose_the_next_clicks(self):
        knob, turned = self.knob_at(9), []
        for k, edges in enumerate((6, 3, 0, -3)):  # four clicks back of 3 edges each, a rest after each
            turned.append(self.take(knob, edges, 1000 * k + 40))
            self.assertEqual(self.take(knob, edges, 1000 * k + 600), 0)  # at rest: the rest point follows the count
        self.assertEqual(turned, [-1, -1, -1, -1])  # with a rest point that moves only by 4, the third click is lost

    def test_a_wobble_after_2_lost_edges_and_a_rest_is_no_turn(self):
        knob = self.knob_at(0)
        self.assertEqual(self.take(knob, 2, 40), 0)  # a click that lost 2 of its 4 edges: no detent
        self.assertEqual(self.take(knob, 2, 600), 0)  # at rest: the rest point is now 2
        self.assertEqual([self.take(knob, edges, 700 + 40 * k) for k, edges in enumerate((3, 4, 2, 1, 0, 2))], [0] * 6)

    def test_a_slow_turn_still_counts(self):
        knob, turned = self.knob_at(5), []
        for k in range(1, 9):  # 1 edge each 400 ms: the count changes before the knob counts as at rest
            turned.append(self.take(knob, 5 + k, 400 * k))
        self.assertEqual(sum(turned), 2)

    def test_the_rest_point_does_not_follow_a_knob_that_still_turns(self):
        knob = self.knob_at(0)
        self.assertEqual(self.take(knob, 1, 450), 0)
        self.assertEqual(self.take(knob, 2, 900), 0)  # 2 edges in 900 ms, each change under REST_MS ago
        self.assertEqual(self.take(knob, 3, 1350), 1)


class PinMapTest(unittest.TestCase):
    def test_the_pin_map_keeps_the_names_the_games_import(self):
        for name in ("SCLK", "MOSI", "MISO", "ONBOARD_BUTTON", "ONBOARD_BUTTON_ON", "ENC_A", "ENC_B"):
            self.assertTrue(hasattr(pins, name), name)

    def test_the_encoder_is_off_the_wired_pins(self):
        wired = {pins.SCLK, pins.MOSI, pins.MISO, pins.GDI_RST, pins.GDI_CS, pins.GDI_SD_CS, pins.GDI_BL,
                 pins.ONBOARD_BUTTON, pins.AUDIO_SHUTDOWN, pins.JOY_X, pins.JOY_Y, pins.JOY_SW,
                 pins.MIC_SCK, pins.MIC_WS, pins.MIC_SD, pins.I2S_BCLK, pins.I2S_LRC, pins.I2S_DIN}
        self.assertFalse({pins.ENC_A, pins.ENC_B} & wired)


if __name__ == "__main__":
    unittest.main()
