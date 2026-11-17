"""Starfire with the stick on the Mac (P872): the crosshair moves at AIM_PX_S * x // 100 px a second (and so for y, up
reading negative), rests when the stick rests, stops at its bounds with no rest kept, and a shot reads the frame's aim.
With no stick the sweep runs as before. Run from the repository root: python3 -B -m unittest tests.test_space3d.
--- MVP (P872) ---"""

import math
import os
import random
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
from space3d import CX, CY, Starfire  # noqa: E402

FRAME_MS = 40  # app.py's FRAME_MS


def playing(x=None, y=0, ms=FRAME_MS):
    """Starfire in play, its frame ms long; with x, a stick at (x, y), else no stick."""
    random.seed(3)
    game = Starfire()
    game.state, game.ms, game.dt = gfx.PLAY, ms, ms / 1000
    if x is not None:
        game.stick = Actions()
        game.stick.x, game.stick.y = x, y
    return game


def frames(game, n, pressed=False):
    for _ in range(n):
        game.play(pressed, pressed)


class StarfireStickTest(unittest.TestCase):
    def test_a_stick_at_rest_leaves_the_crosshair_and_makes_no_new_aim(self):
        game = playing(0, 0)
        aim = game.aim
        frames(game, 10)
        self.assertIs(aim, game.aim)
        self.assertEqual((CX, CY), game.aim)

    def test_full_right_moves_60_px_in_250_ms(self):
        game = playing(100, 0, ms=50)
        frames(game, 5)
        self.assertEqual((CX + 60, CY), game.aim)

    def test_y_up_reads_negative_and_moves_the_crosshair_up(self):
        game = playing(0, -100, ms=50)
        frames(game, 5)
        self.assertEqual((CX, CY - 60), game.aim)

    def test_a_small_tilt_moves_once_its_rest_adds_up(self):
        game = playing(10, 0)  # 24 px a second: 960 px.ms in a 40 ms frame, short of one px
        aim = game.aim
        frames(game, 1)
        self.assertIs(aim, game.aim)
        frames(game, 1)
        self.assertEqual((CX + 1, CY), game.aim)

    def test_it_stops_at_each_bound_with_no_rest_kept(self):
        g = Starfire
        for x, y, at in ((100, 0, (g.AIM_RIGHT, CY)), (-100, 0, (g.AIM_LEFT, CY)), (0, -100, (CX, g.AIM_TOP)),
                         (0, 100, (CX, g.AIM_BOTTOM))):
            game = playing(x, y)
            frames(game, 51)  # 2.04 s: 489 px, past every bound, and 600 px.ms short of a px had no bound reset it
            with self.subTest(x=x, y=y):
                self.assertEqual(at, game.aim)
                self.assertEqual((0, 0), (game.aim_x.rest, game.aim_y.rest))

    def test_a_shot_in_the_frame_of_a_steer_hits_a_rock_at_the_new_aim(self):
        for x, hit in ((100, True), (0, False)):
            game = playing(x, 0, ms=250)
            game.rocks = [[1.2, 0.0, 3.0, 0.0]]  # at z 2.775 after the frame: about 225 across, 22 px of reach
            game.play(True, True)
            with self.subTest(x=x):
                self.assertEqual(1 if hit else 0, game.score)

    def test_a_restart_centers_the_crosshair_with_no_rest(self):
        game = playing(30, 30)
        frames(game, 3)
        self.assertNotEqual((CX, CY), game.aim)
        game.restart()
        self.assertEqual((CX, CY), game.aim)
        self.assertEqual((0, 0), (game.aim_x.rest, game.aim_y.rest))

    def test_with_no_stick_the_crosshair_sweeps(self):
        game = playing()
        self.assertIsNone(game.stick)
        game.t = 0.5
        game.play(False, False)
        self.assertEqual((CX + 95 * math.sin(0.5 * 1.9), CY + 55 * math.sin(0.5 * 1.3 + 1)), game.aim)


if __name__ == "__main__":
    unittest.main()
