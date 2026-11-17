"""Tunnel and Road with the stick on the Mac (P872): tunnel's wall is the way the stick leans, the larger axis winning,
and a stick at rest keeps it; road's lane is the stick's place, left, middle or right, and FIRE held still boosts. With
no stick a tap plays as before. Run from the repository root: python3 -B -m unittest tests.test_world3d.
--- MVP (P872) ---"""

import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

import gfx  # noqa: E402
from engine.actions import Actions  # noqa: E402
from world3d import Road, Tunnel  # noqa: E402

FRAME_MS = 40  # app.py's FRAME_MS


def playing(cls, x=None, y=0):
    """A game of cls in play, its frame 40 ms long; with x, a stick at (x, y), else no stick."""
    game = cls()
    game.state, game.dt = gfx.PLAY, FRAME_MS / 1000
    if x is not None:
        game.stick = Actions()
        game.stick.x, game.stick.y = x, y
    return game


class TunnelStickTest(unittest.TestCase):
    def test_each_way_of_the_stick_picks_its_wall_up_reading_negative(self):
        for x, y, side in ((0, -100, 0), (100, 0, 1), (0, 100, 2), (-100, 0, 3)):
            game = playing(Tunnel, x, y)
            game.side = (side + 2) % 4
            game.play(False, False)
            with self.subTest(x=x, y=y):
                self.assertEqual(side, game.side)

    def test_the_larger_axis_picks_the_wall_on_a_diagonal(self):
        for x, y, side in ((90, -60, 1), (60, -90, 0), (-60, 90, 2), (-90, 60, 3)):
            game = playing(Tunnel, x, y)
            game.play(False, False)
            with self.subTest(x=x, y=y):
                self.assertEqual(side, game.side)

    def test_a_stick_at_rest_or_a_small_tilt_keeps_the_wall(self):
        for x, y in ((0, 0), (39, -39), (-30, 20)):
            game = playing(Tunnel, x, y)
            game.side = 2
            game.play(False, False)
            with self.subTest(x=x, y=y):
                self.assertEqual(2, game.side)

    def test_a_ring_passes_at_the_wall_picked_in_the_same_frame(self):
        for x, alive in ((-100, True), (0, False)):
            game = playing(Tunnel, x)
            game.side, game.rings[0] = 0, [1.05, 3]  # the gap on the left wall, reached in this frame
            game.play(False, False)
            with self.subTest(x=x):
                self.assertEqual(alive, game.state == gfx.PLAY)
                self.assertEqual(1 if alive else 0, game.score)

    def test_with_no_stick_a_tap_turns_the_ship(self):
        game = playing(Tunnel)
        self.assertIsNone(game.stick)
        game.play(True, True)
        self.assertEqual(1, game.side)
        game.play(False, False)
        self.assertEqual(1, game.side)
        game.play(True, True)
        self.assertEqual(2, game.side)


class RoadStickTest(unittest.TestCase):
    def test_left_middle_and_right_of_the_stick_drive_lanes_0_1_and_2(self):
        for x, lane in ((-100, 0), (0, 1), (100, 2), (39, 1), (-39, 1)):
            game = playing(Road, x)
            game.play(False, False)
            with self.subTest(x=x):
                self.assertEqual(lane, game.lane)

    def test_fire_held_boosts_with_the_stick(self):
        odo = []
        for held in (False, True):
            game = playing(Road, 100)
            game.play(held, held)
            odo.append(game.odo)
        self.assertAlmostEqual(6.5 * FRAME_MS / 1000, odo[0])
        self.assertAlmostEqual(6.5 * 1.7 * FRAME_MS / 1000, odo[1])

    def test_with_no_stick_a_tap_moves_a_lane_and_turns_back_at_the_outer_lanes(self):
        game = playing(Road)
        self.assertIsNone(game.stick)
        lanes = []
        for _ in range(4):
            game.play(True, True)
            lanes.append(game.lane)
        self.assertEqual([2, 1, 0, 1], lanes)


if __name__ == "__main__":
    unittest.main()
