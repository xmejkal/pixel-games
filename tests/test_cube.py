"""CubeTiming's rules on the Mac (P573): a seeded trace of a round and named checks of the tolerance, the lap miss,
the tap outside the window, the speed-up and the lives. The restyle as SMILE draws over these rules and must leave
them as they are. Run from the repository root: python3 -B -m unittest discover tests."""

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
from space3d import CubeTiming  # noqa: E402

FRAME_MS = 40  # app.py's FRAME_MS
SEED, FRAMES, EVERY = 3, 1500, 2  # the trace's seed, its length, and the bot's look: one frame in EVERY


def trace(seed=SEED, frames=FRAMES):
    """A round on the frame clock: the first frame taps, so play starts; then a bot that looks one frame in EVERY and
    taps once a lap when the mark is near the target: on each fifth lap (rev 4, 9, ...) it taps late, outside the
    window, and on each seventh (rev 3, 10, ...) it does not tap. Answers each point, each lost life and the death as
    (frame, what, score, lives, yaw, w) and each 50th frame as (frame, state, score, lives, yaw, w, rev, done), the
    numbers rounded to 0.001."""
    random.seed(seed)
    game, now, events, checkpoints = CubeTiming(), 0, [], []
    for k in range(frames):
        now += FRAME_MS
        score, lives = game.score, game.lives
        err, late, idle = game.err(), game.rev % 5 == 4, game.rev % 7 == 3
        near = (0.55 < err < 1.0) if late else (-0.35 < err < 0.6)
        tap = k == 0 or (game.state == gfx.PLAY and k % EVERY == 0 and not game.done and not idle and near)
        game.step(now, tap, tap)
        numbers = (game.score, game.lives, round(game.yaw, 3), round(game.w, 3))
        if game.score != score:
            events.append((k, "good") + numbers)
        elif game.lives != lives:
            events.append((k, "miss") + numbers)
        if k % 50 == 0:
            checkpoints.append((k, game.state) + numbers + (game.rev, game.done))
        if game.state == gfx.OVER:
            events.append((k, "death") + numbers)
            break
    return events, checkpoints


# The trace on master 09ff107's rules: three points, a lap with no tap (frame 239), a late tap (274), four points
# more, and a late tap that takes the last life at frame 516.
EVENTS = (
    (24, "good", 1, 3, 2.112, 2.376),
    (90, "good", 2, 3, 8.385, 2.566),
    (152, "good", 3, 3, 14.749, 2.771),
    (239, "miss", 3, 2, 24.393, 2.771),
    (274, "miss", 3, 1, 28.273, 2.771),
    (322, "good", 4, 1, 33.594, 2.993),
    (376, "good", 5, 1, 40.059, 3.233),
    (424, "good", 6, 1, 46.265, 3.491),
    (470, "good", 7, 1, 52.689, 3.77),
    (516, "miss", 7, 0, 59.627, 3.77),
    (516, "death", 7, 0, 59.627, 3.77),
)
CHECKPOINTS = (
    (0, 1, 0, 3, 0.0, 2.2, 0, False),
    (50, 1, 1, 3, 4.583, 2.376, 0, True),
    (100, 1, 2, 3, 9.411, 2.566, 1, True),
    (150, 1, 2, 3, 14.543, 2.566, 2, False),
    (200, 1, 3, 3, 20.07, 2.771, 3, False),
    (250, 1, 3, 2, 25.612, 2.771, 4, False),
    (300, 1, 3, 1, 31.155, 2.771, 5, False),
    (350, 1, 4, 1, 36.946, 2.993, 6, False),
    (400, 1, 5, 1, 43.162, 3.233, 6, True),
    (450, 1, 6, 1, 49.896, 3.491, 8, False),
    (500, 1, 7, 1, 57.213, 3.77, 9, False),
)


def playing(yaw=0.0, w=2.2):
    """A game in play at yaw, turning w rad/s, its frame 40 ms long."""
    game = CubeTiming()
    game.state, game.dt = gfx.PLAY, FRAME_MS / 1000
    game.yaw, game.w = yaw, w
    return game


def at_err(err, w=2.2):
    """A game whose play() this frame brings the mark err from the target, in the lap of the start."""
    return playing(CubeTiming.TARGET + err - w * FRAME_MS / 1000, w)


class TraceTest(unittest.TestCase):
    def test_the_seeded_round_is_as_pinned(self):
        events, checkpoints = trace()
        self.assertEqual(EVENTS, tuple(events))
        self.assertEqual(CHECKPOINTS, tuple(checkpoints))


class RulesTest(unittest.TestCase):
    def test_the_tolerance_is_12_percent_of_the_speed_capped_at_half_a_radian(self):
        game = playing()
        for w, tol in ((2.2, 0.264), (4.0, 0.48), (4.2, 0.5), (5.5, 0.5)):
            game.w = w
            with self.subTest(w=w):
                self.assertAlmostEqual(tol, game.tol())

    def test_a_tap_inside_the_tolerance_scores_and_one_just_outside_costs_a_life(self):
        tol = 2.2 * 0.12
        for err, good in ((0.0, True), (tol - 0.01, True), (-tol + 0.01, True), (tol + 0.01, False),
                          (-tol - 0.01, False)):
            game = at_err(err)
            game.play(True, True)
            with self.subTest(err=err):
                self.assertAlmostEqual(err, game.err())
                self.assertEqual((1, 3) if good else (0, 2), (game.score, game.lives))
                self.assertTrue(game.done)

    def test_a_lap_without_a_tap_costs_a_life_when_the_mark_comes_round(self):
        game = playing(CubeTiming.TARGET + math.pi - 0.05)  # just before the point opposite the target
        game.play(False, False)
        self.assertEqual((1, 2), (game.rev, game.lives))
        self.assertFalse(game.done)  # the new lap is open again
        game = playing(CubeTiming.TARGET + math.pi - 0.05)
        game.done = True  # this lap was tapped: no miss
        game.play(False, False)
        self.assertEqual((1, 3), (game.rev, game.lives))
        self.assertFalse(game.done)

    def test_a_second_tap_in_the_same_lap_costs_a_life(self):
        game = at_err(0.0)
        game.play(True, True)
        game.play(True, True)
        self.assertEqual((1, 2), (game.score, game.lives))

    def test_a_good_tap_speeds_the_turn_up_8_percent_up_to_5_5_rad_s(self):
        game = at_err(0.0)
        game.play(True, True)
        self.assertAlmostEqual(2.2 * 1.08, game.w)
        game = at_err(0.0, 5.3)
        game.play(True, True)
        self.assertEqual(5.5, game.w)
        game = at_err(1.0)
        game.play(True, True)
        self.assertEqual(2.2, game.w)  # a miss does not speed it up

    def test_the_yaw_turns_by_w_each_second(self):
        game = playing(1.0, 3.0)
        game.play(False, False)
        self.assertAlmostEqual(1.0 + 3.0 * 0.04, game.yaw)

    def test_three_lives_and_the_third_miss_ends_the_round(self):
        game = playing()
        self.assertEqual(3, game.lives)
        for lives in (2, 1):
            game.done = False
            game.yaw = CubeTiming.TARGET + 1.0
            game.play(True, True)
            self.assertEqual((lives, gfx.PLAY), (game.lives, game.state))
        game.done = False
        game.play(True, True)
        self.assertEqual((0, gfx.OVER), (game.lives, game.state))


if __name__ == "__main__":
    unittest.main()
