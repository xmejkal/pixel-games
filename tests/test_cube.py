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
from space3d import CubeTiming, Housing  # noqa: E402

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



def faces_you(normal, yaw):
    """Whether a face of the cube with this normal faces the eye, worked out here on its own: the face's middle is
    its normal (a cube 2 wide), turned by the yaw and the tilt; the eye is D before the cube's middle."""
    c, s, tc, ts = math.cos(yaw), math.sin(yaw), math.cos(CubeTiming.TILT), math.sin(CubeTiming.TILT)
    x, y, z = normal
    x, z = x * c + z * s, -x * s + z * c
    y, z = y * tc - z * ts, y * ts + z * tc
    return x * x + y * y + z * (z + CubeTiming.D) < 0  # (middle - eye) . normal, the middle being the normal


class HousingTest(unittest.TestCase):
    """The housing as SMILE draws it (P573): its corners where the rules' project puts them, to the last bit, so the
    lens is the timing cue; its faces facing you as a separate sum says; the lens hidden when its corner is on the
    back."""

    YAWS = [k * 2 * math.pi / 720 for k in range(720)] + [CubeTiming.TARGET, -1.0, 40.123]

    def test_every_corner_the_top_and_the_light_are_where_project_puts_them(self):
        game = playing()
        h = Housing(game)
        for yaw in self.YAWS:
            h.update(yaw)
            for i, v in enumerate(h.points3d):
                with self.subTest(yaw=yaw, i=i):
                    self.assertEqual(game.project(v, yaw), (h.x[i], h.y[i], h.z[i]))
        self.assertEqual(game.VERTS[game.MARK], h.points3d[game.MARK])
        self.assertEqual(((0, -1, 0), (0.55, -1, 0.55)), h.points3d[h.CENTRE:])

    def test_the_faces_that_face_you(self):
        h = Housing(playing())
        normals = ((1, 0, 0), (0, 0, 1), (-1, 0, 0), (0, 0, -1), (0, -1, 0))
        counts = set()
        for yaw in self.YAWS:
            h.update(yaw)
            with self.subTest(yaw=yaw):
                self.assertEqual([faces_you(n, yaw) for n in normals], h.seen)
                self.assertFalse(faces_you((0, 1, 0), yaw))  # the bottom never does
            counts.add(sum(h.seen))
        self.assertEqual({2, 3}, counts)  # the top and one or two sides

    def test_the_lens_shows_only_while_its_corner_faces_you(self):
        h = Housing(playing())
        shown = []
        for yaw in self.YAWS[:720]:
            h.update(yaw)
            shown.append(h.lens_seen())
            with self.subTest(yaw=yaw):
                self.assertEqual(faces_you((1, 0, 0), yaw) or faces_you((0, 0, 1), yaw), h.lens_seen())
        self.assertTrue(200 < shown.count(False) < 300)  # hidden about a third of a turn, on the back
        h.update(CubeTiming.TARGET)
        self.assertTrue(h.lens_seen())  # it faces you when a tap is on time

    def test_an_edge_is_drawn_when_one_of_its_faces_faces_you(self):
        h = Housing(playing())
        self.assertEqual(12, len(h.edges))
        for a, b, f, g in h.edges:
            self.assertIn(a, h.FACES[f])
            self.assertIn(b, h.FACES[f])
            if g >= 0:
                self.assertIn(a, h.FACES[g])
        self.assertEqual(4, sum(1 for e in h.edges if e[3] < 0))  # the bottom's four edges join one seen face


class LookTest(unittest.TestCase):
    def test_the_line_colours_are_night_inks(self):
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "art"))
        from looks import NightInk
        self.assertEqual((gfx.c565(*NightInk.INK), gfx.c565(*NightInk.BONE)), (CubeTiming.INK, CubeTiming.BONE))
        self.assertEqual(gfx.c565(214, 40, 48), gfx.ACCENT)


if __name__ == "__main__":
    unittest.main()
