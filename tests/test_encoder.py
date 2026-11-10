"""games/encoder.py on the Mac (P758): detents from a fake pulse counter, and the pin map's names. No board.
Run from the repository root: python3 -m unittest discover tests. --- MVP (P758) ---"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))

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

    def test_a_bounce_beside_a_detent_rounds_to_it(self):
        counter = FakeCounter()
        knob = Encoder(counter, 4)
        for edges, detents in ((1, 0), (-1, 0), (7, 2), (9, 2)):
            counter.edges = edges
            self.assertEqual(knob.detents(), detents, edges)

    def test_edges_are_the_raw_count(self):
        self.assertEqual(Encoder(FakeCounter(-3), 4).edges(), -3)


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
