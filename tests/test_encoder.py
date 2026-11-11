"""games/encoder.py on the Mac (P758, P757): detents from a fake pulse counter, and the pin map's names. No board.
Run from the repository root: python3 -m unittest discover tests. --- MVP (P758, P757) ---"""

import os
import sys
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
if not hasattr(time, "ticks_diff"):  # the same three as tests/test_sound.py, which looks for ticks_diff too
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

import pins  # noqa: E402
from encoder import REST_MS, Encoder, take_pads  # noqa: E402


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

    def test_the_rest_point_follows_a_knob_that_rests_1_edge_off(self):
        knob = self.knob_at(0)
        self.assertEqual(self.take(knob, 1, 40), 0)
        self.assertEqual(self.take(knob, 1, 40 + REST_MS), 0)  # at rest: the rest point is now 1
        self.assertEqual([self.take(knob, edges, 600 + 40 * k) for k, edges in enumerate((3, -1, 1))], [0, 0, 0])
        self.assertEqual(self.take(knob, -2, 800), -1)  # a click back that ends 1 edge short still counts
        self.assertEqual(self.take(knob, -6, 840), -1)

    def test_a_turn_of_a_detent_and_a_half_keeps_its_half(self):
        knob = self.knob_at(0)
        self.assertEqual(self.take(knob, 6, 40), 1)
        self.assertEqual(self.take(knob, 8, 80), 1)  # a rest point that jumped to 6 would see 2 edges and no detent

    def test_a_slow_turn_loses_no_detent(self):
        for ms_per_edge in (400, 600, 2500):  # under REST_MS, over it (the refuter's case), and far over it
            knob, turned, now_ms = self.knob_at(5), 0, 0
            for k in range(1, 9):
                for _ in range(ms_per_edge // 40):  # a poll each 40 ms
                    now_ms += 40
                    turned += self.take(knob, 5 + k, now_ms)
            self.assertEqual(turned, 2, ms_per_edge)
            self.assertEqual(self.take(knob, 5 + 8, now_ms + 1000), 0)
            self.assertEqual(self.take(knob, 5 + 4, now_ms + 1040), -1, ms_per_edge)  # no click is lost on the way back

    def test_a_hand_that_stops_in_the_middle_of_a_click_loses_no_edge(self):
        knob = self.knob_at(0)
        self.assertEqual(self.take(knob, 2, 40), 0)
        self.assertEqual(self.take(knob, 2, 40 + 2 * REST_MS), 0)  # 2 edges are too far for the rest point to follow
        self.assertEqual(self.take(knob, 4, 1100), 1)

    def test_the_rest_follows_across_the_wrap_of_ticks_ms(self):
        period = 1 << 30
        with mock.patch.object(time, "ticks_diff", lambda a, b: (a - b + period // 2) % period - period // 2):
            self.counter = FakeCounter(0)
            knob = Encoder(self.counter, 4)
            self.assertEqual(knob.take_detents(period - 100), 0)
            self.assertEqual(self.take(knob, 1, period - 60), 0)
            self.assertEqual(self.take(knob, 1, REST_MS - 60), 0)  # REST_MS later: the rest point is now 1
            self.assertEqual(self.take(knob, 3, REST_MS), 0)

    def test_the_rest_point_does_not_follow_a_knob_that_still_turns(self):
        knob = self.knob_at(0)
        self.assertEqual(self.take(knob, 1, 450), 0)
        self.assertEqual(self.take(knob, 2, 900), 0)  # 2 edges in 900 ms, each change under REST_MS ago
        self.assertEqual(self.take(knob, 3, 1350), 1)


class FakePin:
    IN, PULL_UP = "in", "up"

    def __init__(self, number, mode=None, pull=None):
        self.number, self.mode, self.pull = number, mode, pull


class TakePadsTest(unittest.TestCase):
    def machine(self):
        counter = mock.Mock(return_value=FakeCounter(8))
        return mock.patch.dict(sys.modules, {"machine": mock.Mock(Pin=FakePin, Encoder=counter)}), counter

    def test_both_pads_become_inputs_with_the_pull_up(self):
        patch, _ = self.machine()
        with patch:
            a, b = take_pads(44, 43)
        self.assertEqual([(p.number, p.mode, p.pull) for p in (a, b)], [(44, "in", "up"), (43, "in", "up")])

    def test_on_board_counts_on_the_pads_it_took(self):
        patch, counter = self.machine()
        with patch:
            knob = Encoder.on_board(44, 43, 4)
        unit, a, b = counter.call_args.args
        self.assertEqual((unit, a.number, a.pull, b.number, b.pull), (0, 44, "up", 43, "up"))
        self.assertEqual(knob.detents(), 2)


class PinMapTest(unittest.TestCase):
    def test_the_pin_map_keeps_the_names_the_games_import(self):
        for name in ("SCLK", "MOSI", "MISO", "ONBOARD_BUTTON", "ONBOARD_BUTTON_ON", "ENC_A", "ENC_B"):
            self.assertTrue(hasattr(pins, name), name)

    def test_the_encoder_is_off_the_wired_pins(self):
        wired = {pins.SCLK, pins.MOSI, pins.MISO, pins.GDI_RST, pins.GDI_CS, pins.GDI_SD_CS, pins.GDI_BL,
                 pins.ONBOARD_BUTTON, pins.AUDIO_SHUTDOWN, pins.JOY_X, pins.JOY_Y, pins.JOY_SW,
                 pins.MIC_SCK, pins.MIC_WS, pins.MIC_SD, pins.I2S_BCLK, pins.I2S_LRC, pins.I2S_DIN}
        self.assertFalse({pins.ENC_A, pins.ENC_B} & wired)

    def test_the_encoder_is_on_the_pads_rx_and_tx_with_the_pull_up(self):
        self.assertEqual((pins.ENC_A, pins.ENC_B), (44, 43))  # GA on RX, GB on TX: requirements.json (P757)
        self.assertEqual((pins.ENC_A_PULL, pins.ENC_B_PULL), ("up", "up"))


if __name__ == "__main__":
    unittest.main()
