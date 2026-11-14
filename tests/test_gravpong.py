"""GravityPong's rules on the Mac (P573): a seeded trace of a round and named checks of gravity, the catch, the clamp
and the death. The restyle as BUBBLE draws over these rules and must leave them as they are; only a named rule change
(D9) moves the trace, in a commit of its own. Run from the repository root: python3 -B -m unittest discover tests."""

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
from arcade2 import GravityPong  # noqa: E402

FRAME_MS = 40  # app.py's FRAME_MS
SEED, FRAMES, EVERY = 2, 1000, 3  # the trace's seed, its length, and the bot's look: one frame in EVERY
CHECK_EVERY = 50  # a checkpoint each this many frames


def trace(seed=SEED, frames=FRAMES):
    """A round on the frame clock: the first frame taps, so play starts; then a bot that looks one frame in EVERY and
    taps when the paddle goes the wrong way, more than 20 px from the ball. Answers each catch and the death as
    (frame, what, score, bx, vx) and each CHECK_EVERY-th frame as (frame, state, score, px, bx, by, vx, vy), rounded
    to 0.01."""
    random.seed(seed)
    game, now, events, checkpoints = GravityPong(), 0, [], []
    for k in range(frames):
        now += FRAME_MS
        score = game.score
        tap = k == 0 or (game.state == gfx.PLAY and k % EVERY == 0 and (game.bx - game.px - game.PW / 2) * game.pdir < -20)
        game.step(now, tap, tap)
        if game.score != score:
            events.append((k, "catch", game.score, round(game.bx, 2), round(game.vx, 2)))
        if k % CHECK_EVERY == 0:
            checkpoints.append((k, game.state, game.score) + tuple(round(v, 2) for v in (
                game.px, game.bx, game.by, game.vx, game.vy)))
        if game.state == gfx.OVER:
            events.append((k, "death", game.score, round(game.bx, 2), round(game.vx, 2)))
            break
    return events, checkpoints


# The trace on master 4088c42's rules (P573 step 1).
EVENTS = (
    (19, "catch", 1, 213.2, 118.0),
    (58, "catch", 2, 233.76, -62.0),
    (99, "catch", 3, 132.08, -128.0),
    (140, "catch", 4, 87.92, 185.0),
    (181, "catch", 5, 240.0, -200.0),
    (221, "catch", 6, 86.0, 200.0),
    (264, "catch", 7, 202.0, -200.0),
    (299, "catch", 8, 86.0, 200.0),
    (330, "catch", 9, 298.0, -148.0),
    (360, "catch", 10, 120.4, -200.0),
    (393, "catch", 11, 150.0, 200.0),
    (424, "catch", 12, 234.0, -200.0),
    (453, "catch", 13, 6.0, 200.0),
    (480, "catch", 14, 222.0, 200.0),
    (505, "catch", 15, 210.0, -200.0),
    (529, "catch", 16, 18.0, -200.0),
    (554, "catch", 17, 190.0, 200.0),
    (577, "catch", 18, 258.0, -200.0),
    (599, "catch", 19, 82.0, -125.0),
    (622, "catch", 20, 41.0, 197.0),
    (643, "catch", 21, 206.48, 200.0),
    (663, "catch", 22, 266.0, -200.0),
    (684, "catch", 23, 98.0, -200.0),
    (704, "catch", 24, 70.0, 200.0),
    (725, "catch", 25, 238.0, 200.0),
    (744, "catch", 26, 242.0, -139.0),
    (765, "death", 26, 125.24, -139.0),
)
CHECKPOINTS = (
    (0, 1, 0, 125.0, 160.0, 60.0, 70.0, 0.0),
    (50, 1, 1, 222.16, 271.52, 111.19, -118.0, 225.8),
    (100, 1, 3, 122.0, 126.96, 211.18, -128.0, -416.2),
    (150, 1, 4, 110.8, 161.92, 94.86, 185.0, -238.0),
    (200, 1, 5, 60.96, 88.0, 24.7, -200.0, -59.8),
    (250, 1, 6, 234.48, 314.0, 53.6, -200.0, 139.2),
    (300, 1, 8, 55.6, 94.0, 199.9, 200.0, -461.2),
    (350, 1, 9, 192.32, 179.6, 72.28, -148.0, 283.0),
    (400, 1, 11, 169.12, 206.0, 111.62, 200.0, -363.4),
    (450, 1, 12, 15.68, 26.0, 169.55, -200.0, 434.8),
    (500, 1, 14, 213.84, 250.0, 121.66, -200.0, 411.2),
    (550, 1, 16, 131.04, 158.0, 144.7, 200.0, 450.0),
    (600, 1, 19, 66.24, 77.0, 207.51, -125.0, -560.2),
    (650, 1, 21, 249.52, 262.48, 69.82, 200.0, -453.4),
    (700, 1, 23, 0.0, 38.0, 139.63, 200.0, 533.8),
    (750, 1, 26, 180.0, 208.64, 80.23, -139.0, -510.2),
)


def playing():
    """A game in play, its frame 40 ms long."""
    game = GravityPong()
    game.state, game.dt = gfx.PLAY, FRAME_MS / 1000
    return game


class TraceTest(unittest.TestCase):
    def test_the_seeded_round_is_as_pinned(self):
        events, checkpoints = trace()
        self.assertEqual(EVENTS, tuple(events))
        self.assertEqual(CHECKPOINTS, tuple(checkpoints))


class RulesTest(unittest.TestCase):
    def test_gravity_adds_520_px_s_each_second_and_moves_the_ball_by_its_new_speed(self):
        game = playing()
        game.bx, game.by, game.vx, game.vy = 160.0, 100.0, 0.0, 0.0
        game.play(False, False)
        self.assertAlmostEqual(520 * 0.04, game.vy)
        self.assertAlmostEqual(100 + 520 * 0.04 * 0.04, game.by)

    def test_a_falling_ball_over_the_net_is_caught_and_sent_up_faster_with_each_point(self):
        game = playing()
        game.px, game.pdir = 100.0, 1
        game.bx, game.by, game.vx, game.vy = 140.0, game.PY - 8.0, 0.0, 100.0
        game.play(False, False)
        self.assertEqual(1, game.score)
        self.assertEqual(-(410 + 1 * 9), game.vy)
        game.score = 30  # the speed stops growing at 25 points
        game.by, game.vy = game.PY - 8.0, 100.0
        game.play(False, False)
        self.assertEqual(-(410 + 25 * 9), game.vy)

    def test_the_catch_window_reaches_6_px_past_each_end_of_the_net(self):
        for bx, caught in ((100 - 6.0, True), (100 - 7.0, False), (170 + 6.0, True), (170 + 7.0, False)):
            game = playing()
            game.px, game.pdir = 100.0, 1
            game.bx, game.by, game.vx, game.vy = bx, game.PY - 8.0, 0.0, 100.0
            game.px -= game.pdir * (170 + 0) * game.dt  # the net moves first: put it at 100 after its move
            game.play(False, False)
            with self.subTest(bx=bx):
                self.assertEqual(caught, game.score == 1)

    def test_the_sideways_speed_is_clamped_to_200_px_s_after_a_catch(self):
        for pdir, vx in ((1, 190.0), (-1, -190.0)):
            game = playing()
            game.px, game.pdir = 100.0, pdir
            game.bx, game.by, game.vx, game.vy = 140.0, game.PY - 8.0, vx, 100.0
            game.play(False, False)
            with self.subTest(pdir=pdir):
                self.assertEqual(200.0 * pdir, game.vx)

    def test_a_tap_flips_the_net_and_the_screen_edge_flips_it_back(self):
        game = playing()
        game.px, game.pdir = 100.0, 1
        game.play(True, True)
        self.assertEqual(-1, game.pdir)
        self.assertAlmostEqual(100 - 170 * 0.04, game.px)
        game.px = 2.0
        game.play(False, False)
        self.assertEqual(0.0, game.px)
        self.assertEqual(1, game.pdir)

    def test_the_ball_bounces_off_the_walls_and_the_ceiling(self):
        game = playing()
        game.bx, game.by, game.vx, game.vy = 7.0, 100.0, -100.0, 0.0
        game.play(False, False)
        self.assertEqual((6.0, 100.0), (game.bx, game.vx))
        game.bx, game.vx = gfx.WIDTH - 7.0, 100.0
        game.play(False, False)
        self.assertEqual((gfx.WIDTH - 6.0, -100.0), (game.bx, game.vx))
        game.by, game.vy = 26.0, -200.0
        game.play(False, False)
        self.assertEqual(24.0, game.by)
        self.assertGreater(game.vy, 0)

    def test_the_ball_past_the_bottom_ends_the_round(self):
        game = playing()
        game.px = 0.0
        game.bx, game.by, game.vx, game.vy = 300.0, gfx.HEIGHT + 5.0, 0.0, 0.0
        game.play(False, False)
        self.assertEqual(gfx.PLAY, game.state)  # H + 5.83: not yet
        game.by = gfx.HEIGHT + 6.5
        game.play(False, False)
        self.assertEqual(gfx.OVER, game.state)


if __name__ == "__main__":
    unittest.main()
