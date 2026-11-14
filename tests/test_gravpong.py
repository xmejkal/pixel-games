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
        away = (game.bx - game.px - game.PW / 2) * game.pdir < -20
        tap = k == 0 or (game.state == gfx.PLAY and k % EVERY == 0 and away)
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


# The trace on BUBBLE's rules (P573): master 4088c42's, with D9's swelling radius. The first four catches are as on
# master (the radius is 6 under 4 points); from the fifth the walls, the ceiling, the catch and the death reach as far
# as the bubble does, so the round runs on otherwise: on master it ended at frame 765 with 26 points.
EVENTS = (
    (19, "catch", 1, 213.2, 118.0),
    (58, "catch", 2, 233.76, -62.0),
    (99, "catch", 3, 132.08, -128.0),
    (140, "catch", 4, 87.92, 185.0),
    (181, "catch", 5, 238.0, -200.0),
    (218, "catch", 6, 72.0, 200.0),
    (252, "catch", 7, 288.0, -200.0),
    (291, "catch", 8, 32.0, 200.0),
    (324, "catch", 9, 296.0, 112.0),
    (355, "catch", 10, 189.04, -49.0),
    (384, "catch", 11, 132.2, -96.0),
    (411, "catch", 12, 28.52, -149.0),
    (438, "death", 12, 155.04, 149.0),
)
CHECKPOINTS = (
    (0, 1, 0, 125.0, 160.0, 60.0, 70.0, 0.0),
    (50, 1, 1, 222.16, 271.52, 111.19, -118.0, 225.8),
    (100, 1, 3, 122.0, 126.96, 211.18, -128.0, -416.2),
    (150, 1, 4, 110.8, 161.92, 94.86, 185.0, -238.0),
    (200, 1, 5, 38.64, 86.0, 26.0, -200.0, 59.8),
    (250, 1, 6, 242.24, 304.0, 192.08, -200.0, 422.4),
    (300, 1, 8, 80.64, 104.0, 91.32, 200.0, -294.8),
    (350, 1, 9, 167.6, 211.44, 137.04, -112.0, 366.2),
    (400, 1, 11, 49.52, 70.76, 47.92, -96.0, 259.4),
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
        game.score = 30  # the speed stops growing at 25 points; the bubble is 14 px round by then (D9)
        game.by, game.vy = game.PY - 16.0, 100.0
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


class SwellTest(unittest.TestCase):
    """D9 (P573): the bubble's radius grows with the score, and every rule that read 6 px reads it."""

    def test_the_radius_is_6_and_2_more_for_each_4_points_up_to_14(self):
        game = playing()
        for score, radius in ((0, 6), (3, 6), (4, 8), (8, 10), (12, 12), (15, 12), (16, 14), (40, 14)):
            game.score = score
            with self.subTest(score=score):
                self.assertEqual(radius, game.radius())

    def test_the_walls_and_the_ceiling_hold_the_bubble_by_its_radius(self):
        game = playing()
        game.score = 16
        game.bx, game.by, game.vx, game.vy = 15.0, 100.0, -100.0, 0.0
        game.play(False, False)
        self.assertEqual((14.0, 100.0), (game.bx, game.vx))
        game.bx, game.vx = gfx.WIDTH - 15.0, 100.0
        game.play(False, False)
        self.assertEqual((gfx.WIDTH - 14.0, -100.0), (game.bx, game.vx))
        game.by, game.vy = 34.0, -200.0
        game.play(False, False)
        self.assertEqual(18.0 + 14, game.by)
        self.assertGreater(game.vy, 0)

    def test_a_bubble_already_leaving_a_wall_is_not_turned_back(self):
        game = playing()
        game.score = 16  # radius 14: a bubble that moves to x 12 is inside the wall's reach but already going right
        game.bx, game.by, game.vx, game.vy = 8.0, 100.0, 100.0, 0.0
        game.play(False, False)
        self.assertEqual((14.0, 100.0), (game.bx, game.vx))

    def test_the_catch_window_and_the_death_line_reach_the_radius(self):
        for bx, caught in ((100 - 14.0, True), (100 - 15.0, False), (170 + 14.0, True), (170 + 15.0, False)):
            game = playing()
            game.score = 16
            game.px, game.pdir = 100.0 - (170 + 16 * 4) * 0.04, 1  # at 100 once it has moved
            game.bx, game.by, game.vx, game.vy = bx, game.PY - 16.0, 0.0, 100.0
            game.play(False, False)
            with self.subTest(bx=bx):
                self.assertEqual(caught, game.score == 17)
        game = playing()
        game.score, game.px = 16, 0.0
        game.bx, game.by, game.vx, game.vy = 300.0, gfx.HEIGHT + 13.0, 0.0, 0.0
        game.play(False, False)
        self.assertEqual(gfx.PLAY, game.state)  # H + 13.83: inside the reach of 14
        game.by = gfx.HEIGHT + 14.5
        game.play(False, False)
        self.assertEqual(gfx.OVER, game.state)


class Heard:
    """signals.Signals as the game box gives it: the names emitted, in order."""

    def __init__(self):
        self.names = []

    def emit(self, name, value=None):
        self.names.append(name)


class SoundTest(unittest.TestCase):
    def test_a_catch_plays_the_jump_and_the_loss_the_die(self):
        self.assertEqual({"catch": "jump", "die": "die"}, {k: c.sound for k, c in GravityPong.cues.items()})
        game = playing()
        game.signals = Heard()
        game.px, game.pdir = 100.0, 1
        game.bx, game.by, game.vx, game.vy = 140.0, game.PY - 8.0, 0.0, 100.0
        game.play(False, False)
        game.bx, game.by, game.vy = 300.0, gfx.HEIGHT + 20.0, 10.0
        game.play(False, False)
        self.assertEqual(["catch", "die"], game.signals.names)


if __name__ == "__main__":
    unittest.main()
