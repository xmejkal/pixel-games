"""games/drivers/stick.py on the Mac (P851): the joystick's axes from a fake ADC. The center is fixed at CENTER, a read
inside DEAD_ZONE (the bench's rest, 32391 to 33688, among them) is 0, the ends are -FULL and FULL, a value past an end
is clamped, and X_SIGN and Y_SIGN turn each axis. Run from the repository root:
python3 -B -m unittest tests.test_stick. --- MVP (P851) ---"""

import os
import sys
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))

from drivers import stick  # noqa: E402
from drivers.stick import CENTER, DEAD_ZONE, FULL, TOP, Stick  # noqa: E402


class FakeADC:
    def __init__(self, raw):
        self.raw = raw

    def read_u16(self):
        return self.raw


def read(x, y=CENTER):
    return Stick(FakeADC(x), FakeADC(y))


class StickTest(unittest.TestCase):
    """The arithmetic with both signs 1; the box's own signs and swap are in BoxFactsTest."""

    def setUp(self):
        for name in ("X_SIGN", "Y_SIGN"):
            patcher = mock.patch.object(stick, name, 1)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_the_bench_s_rest_reads_0(self):
        for raw in (32391, CENTER, 33000, 33688, CENTER - DEAD_ZONE, CENTER + DEAD_ZONE):
            with self.subTest(raw=raw):
                self.assertEqual((0, 0), (read(raw).read_x(), read(CENTER, raw).read_y()))

    def test_just_outside_the_dead_zone_moves(self):
        self.assertEqual(0, read(CENTER + DEAD_ZONE + 1).read_x())  # under 1 of FULL
        self.assertLess(0, read(CENTER + DEAD_ZONE + 400).read_x())
        self.assertGreater(0, read(CENTER - DEAD_ZONE - 400).read_x())

    def test_the_ends_read_full(self):
        self.assertEqual((-FULL, FULL), (read(0).read_x(), read(TOP).read_x()))
        self.assertEqual((-FULL, FULL), (read(CENTER, 0).read_y(), read(CENTER, TOP).read_y()))

    def test_half_way_reads_about_half(self):
        self.assertIn(read(CENTER + DEAD_ZONE + (TOP - CENTER - DEAD_ZONE) // 2).read_x(), (49, 50))  # rounded down
        self.assertEqual(-(FULL // 2), read(CENTER - DEAD_ZONE - (CENTER - DEAD_ZONE) // 2).read_x())

    def test_a_value_past_an_end_is_clamped(self):
        self.assertEqual((-FULL, FULL), (read(-5000).read_x(), read(TOP + 5000).read_x()))

    def test_the_signs_turn_each_axis_alone(self):
        with mock.patch.object(stick, "X_SIGN", -1):
            self.assertEqual((-FULL, FULL), (read(TOP).read_x(), read(CENTER, TOP).read_y()))
        with mock.patch.object(stick, "Y_SIGN", -1):
            self.assertEqual((FULL, -FULL), (read(TOP).read_x(), read(CENTER, TOP).read_y()))

    def test_on_board_opens_both_pads_at_11_db(self):
        self.assertEqual([("pad4", 3), ("pad5", 3)], self.opened(False))

    def test_swapped_axes_read_left_and_right_on_the_y_pad(self):
        self.assertEqual([("pad5", 3), ("pad4", 3)], self.opened(True))

    def opened(self, swap):
        """The pads Stick.on_board(4, 5) opens, x first, with SWAP_AXES as swap."""
        made = []

        class ADC:
            ATTN_11DB = 3

            def __init__(self, pin, atten=None):
                made.append((pin, atten))

        machine = types.SimpleNamespace(ADC=ADC, Pin=lambda n: "pad%d" % n)
        with mock.patch.dict(sys.modules, {"machine": machine}), mock.patch.object(stick, "SWAP_AXES", swap):
            Stick.on_board(4, 5)
        return made


class BoxFactsTest(unittest.TestCase):
    """The PO's box (logs/p851-stick-directions.log): up reads JOY_X low, left reads JOY_Y high. With SWAP_AXES and
    the signs, left and up read negative, right and down positive."""

    def test_left_and_up_read_negative(self):
        self.assertTrue(stick.SWAP_AXES)
        left = Stick(FakeADC(TOP), FakeADC(CENTER))  # x is the JOY_Y pad once swapped: left reads it high
        up = Stick(FakeADC(CENTER), FakeADC(0))  # y is the JOY_X pad: up reads it low
        self.assertEqual((-FULL, 0), (left.read_x(), left.read_y()))
        self.assertEqual((0, -FULL), (up.read_x(), up.read_y()))


if __name__ == "__main__":
    unittest.main()
