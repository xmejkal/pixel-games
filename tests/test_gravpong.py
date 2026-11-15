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
import arcade2  # noqa: E402
from arcade2 import BubbleLook, GravityPong, Net, Notes  # noqa: E402

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
        right = 100 + 62  # at 16 points the spent workers' net is 62 wide
        for bx, caught in ((100 - 14.0, True), (100 - 15.0, False), (right + 14.0, True), (right + 15.0, False)):
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


def lost():
    """A game on the frame clock whose bubble is lost on its second frame: (game, the ms of the loss)."""
    game, now = GravityPong(), FRAME_MS
    game.step(now, True, True)  # the tap starts play
    game.px, game.bx, game.by, game.vy = 0.0, 300.0, gfx.HEIGHT + 30.0, 10.0
    now += FRAME_MS
    game.step(now, False, False)
    return game, now


class FeelTest(unittest.TestCase):
    """The look's feel (P573's review): the bubble's poses in order, the workers' tiredness, the net's sag, the notes
    and the crashed board."""

    def test_the_bubble_squashes_at_least_3_frames_then_stretches_while_fast_then_wobbles_then_is_round(self):
        look = BubbleLook
        self.assertGreaterEqual(look.SQUASH_MS, 3 * FRAME_MS)
        self.assertEqual(look.SQUASH, look.pose(0, -600))
        self.assertEqual(look.SQUASH, look.pose(look.SQUASH_MS - 1, -600))
        self.assertEqual(look.STRETCH, look.pose(look.SQUASH_MS, -600))
        self.assertIn(look.pose(look.SQUASH_MS, -100), (look.WOBBLE_A, look.WOBBLE_B))
        self.assertEqual(look.ROUND, look.pose(look.WOBBLE_MS, -100))
        self.assertEqual([0, 0, 1, 1, 2, 2, 3, 3, 4, 4], [look.size_index(r) for r in range(6, 16)])

    def test_the_workers_tire_for_a_moment_after_each_catch_and_for_good_from_the_tired_score(self):
        game = playing()
        game.last, game.caught_at = 10000, 0
        game.score = GravityPong.TIRED_SCORE - 1
        self.assertFalse(game.tired())
        game.caught_at = game.last - GravityPong.TIRED_MS + 1
        self.assertTrue(game.tired())
        game.caught_at, game.score = 0, GravityPong.TIRED_SCORE
        self.assertTrue(game.tired())

    def test_a_catch_sags_the_net_deep_and_it_springs_back_flat(self):
        net = Net()
        net.kick(500)
        sags, poses = [], set()
        for _ in range(60):
            net.update(FRAME_MS / 1000)
            sags.append(net.sag)
            poses.add(net.pose())
        self.assertGreater(max(sags), 6.0)  # deep: more than 4 px, so it moves visibly
        self.assertEqual({0, 1, 2, 3}, poses)  # deep, sag, flat and the recoil's bulge
        self.assertEqual(1, net.pose())  # at rest: flat
        self.assertLess(abs(net.sag), 0.5)

    def test_the_notes_burst_after_the_hit_pause_and_every_one_comes_to_rest(self):
        game, now = lost()
        self.assertEqual(gfx.OVER, game.state)
        while game.over_ms() + FRAME_MS < GravityPong.HIT_MS:
            now += FRAME_MS
            game.step(now, False, False)
            self.assertEqual([], game.notes.q)
        now += FRAME_MS
        game.step(now, False, False)
        self.assertEqual(Notes.COUNT, len(game.notes.q))
        for _ in range(150):  # 6 s
            now += FRAME_MS
            game.step(now, False, False)
        self.assertEqual(Notes.COUNT, len(game.notes.q))
        for x, y, vx, vy, k, place in game.notes.q:
            self.assertTrue(place >= 0 or y == game.FLOOR - 3)

    def test_a_note_that_falls_into_the_net_rides_with_it(self):
        notes = Notes(gfx.Dice(5732))
        notes.q.append([120.0, 200.0, 0.0, 40.0, 0, -1])
        for _ in range(20):
            notes.update(FRAME_MS / 1000, 233, 100.0, 70, 218)
        self.assertEqual(20, notes.q[0][5])  # 20 px from the net's left end
        drawn = []
        saved = arcade2.pictures.draw
        arcade2.pictures.draw = lambda cv, name, x, y, alpha=255: drawn.append((name, x, y))
        try:
            notes.draw(None, 0, 233, 150, 218)
        finally:
            arcade2.pictures.draw = saved
        self.assertEqual([("gravpong_note_0", 150 + 20 - 4, 219)], drawn)

    def test_the_hit_pause_holds_the_squashed_bubble_two_frames_with_the_sparks_hidden_then_the_pop_starts(self):
        class Canvas:
            pictures = True

            def fill(self, *args):
                pass

        game, now = lost()
        game.covers = True
        drawn, saved = [], arcade2.pictures.draw
        arcade2.pictures.draw = lambda cv, name, x, y, alpha=255: drawn.append(name) or True
        try:
            for frame in range(4):
                drawn.clear()
                game.last = game.since + frame * FRAME_MS
                game.paint(Canvas())
                squashed = [n for n in drawn if n.startswith("gravpong_bubble_")]
                with self.subTest(frame=frame):
                    if frame < 2:
                        self.assertEqual(1, len(squashed))
                        self.assertTrue(squashed[0].endswith("_squash"))
                        self.assertTrue(game.fx.hide)
                        self.assertNotIn("gravpong_pop_0", drawn)
                    else:
                        self.assertEqual([], squashed)
                        self.assertFalse(game.fx.hide)
                        self.assertIn("gravpong_pop_%d" % ((frame - 2) * FRAME_MS // GravityPong.POP_MS), drawn)
        finally:
            arcade2.pictures.draw = saved
        self.assertEqual(2 * FRAME_MS, GravityPong.HIT_MS)

    def test_the_board_crashes_when_the_hit_pause_ends(self):
        class Canvas:
            pictures = True

            def fill(self, *args):
                pass

        game, now = lost()
        game.covers = True
        drawn, saved = [], arcade2.pictures.draw
        arcade2.pictures.draw = lambda cv, name, x, y, alpha=255: drawn.append(name) or True
        try:
            for ms in range(0, 200, FRAME_MS):
                drawn.clear()
                game.last = game.since + ms
                game.paint(Canvas())
                with self.subTest(ms=ms):
                    self.assertEqual(ms >= GravityPong.HIT_MS, "gravpong_crash" in drawn)
        finally:
            arcade2.pictures.draw = saved


class NetTest(unittest.TestCase):
    """The spent workers' net shrinks (P573's review, a second named rule change): 70 px, and 8 less for each 4 points
    past TIRED_SCORE, down to 46, its middle kept at the catch that shrinks it."""

    def test_the_net_is_70_px_until_the_tired_score_then_8_less_each_4_points_down_to_46(self):
        game = playing()
        widths = {}
        for score in range(0, 40):
            game.score = score
            widths[score] = game.net_width()
        self.assertEqual({70}, {widths[k] for k in range(16)})
        self.assertEqual((62, 62, 54, 54, 46, 46), tuple(widths[k] for k in (16, 19, 20, 23, 24, 39)))

    def test_the_catch_that_shrinks_the_net_keeps_its_middle(self):
        game = playing()
        game.score, game.px, game.pdir = 15, 100.0, 1
        game.bx, game.by, game.vx, game.vy = 140.0, game.PY - 16.0, 0.0, 100.0
        game.play(False, False)
        self.assertEqual(16, game.score)
        moved = 100.0 + (170 + 15 * 4) * 0.04
        self.assertAlmostEqual(moved + (70 - 62) / 2, game.px)

    def test_the_catch_window_and_the_walls_read_the_narrow_net(self):
        for bx, caught in ((100 + 46 + 14.0, True), (100 + 46 + 15.0, False)):
            game = playing()
            game.score = 24  # the net 46 wide, the bubble 14 round
            game.px, game.pdir = 100.0 - (170 + 20 * 4) * 0.04, 1
            game.bx, game.by, game.vx, game.vy = bx, game.PY - 16.0, 0.0, 100.0
            game.play(False, False)
            with self.subTest(bx=bx):
                self.assertEqual(caught, game.score == 25)
        game = playing()
        game.score, game.px, game.pdir = 24, gfx.WIDTH - 47.0, 1
        game.play(False, False)
        self.assertEqual(gfx.WIDTH - 46.0, game.px)  # the net reaches the right wall at its own width
        self.assertEqual(-1, game.pdir)


class Drawn:
    """pictures.draw as logged: each (name, x, y, alpha) one paint of a game with its art draws."""

    pictures = True

    def __init__(self, game):
        self.calls, saved = [], arcade2.pictures.draw
        arcade2.pictures.draw = lambda cv, name, x, y, alpha=255: self.calls.append((name, x, y, alpha)) or True
        try:
            game.covers = True
            game.paint(self)
        finally:
            arcade2.pictures.draw = saved

    def fill(self, *args):
        pass

    def named(self, prefix):
        return [c for c in self.calls if c[0].startswith(prefix)]


class CrewDrawingTest(unittest.TestCase):
    """The net, the workers and the light pool as drawn at each of the net's widths (P573's review)."""

    def crew(self, score, px, sag=0.0):
        game = playing()
        game.score, game.px, game.pdir, game.last = score, float(px), 1, 10000
        game.net.sag = sag
        return game, Drawn(game)

    def test_the_net_is_drawn_at_its_width_in_the_picture_for_its_sag(self):
        for score in (0, 16, 20, 24):
            for sag, pose in ((-2.0, 0), (0.0, 1), (4.0, 2), (9.0, 3)):
                game, drawn = self.crew(score, 100, sag)
                with self.subTest(score=score, sag=sag):
                    self.assertEqual(pose, game.net.pose())
                    self.assertEqual([(GravityPong.NETS[game.net_width()][pose], 100, game.NET_Y, 255)],
                                     drawn.named("gravpong_net_"))

    def test_the_workers_hold_the_nets_ends_and_the_pool_lies_under_its_middle(self):
        g = GravityPong
        for score in (0, 16, 20, 24):
            game, drawn = self.crew(score, 100)
            pw = game.net_width()
            left, right = drawn.named("gravpong_worker_l_")[0], drawn.named("gravpong_worker_r_")[0]
            pool = drawn.named("gravpong_pool")[0]
            with self.subTest(score=score):
                self.assertEqual(100 - g.HAND_DX - g.WORKER_W // 2, left[1])
                self.assertEqual(100 + pw + g.HAND_DX - g.WORKER_W // 2, right[1])
                self.assertEqual(100 + pw // 2 - g.POOL_W // 2, pool[1])

    def test_spent_workers_step_slower_and_slump_every_other_step(self):
        g = GravityPong
        top = g.FLOOR - g.WORKER_H
        game, drawn = self.crew(0, 26)  # fresh: a pose each 8 px, no slump
        left = drawn.named("gravpong_worker_l_")[0]
        self.assertEqual((g.WORKERS[0]["run"][26 // g.STEP_PX % 4], top), left[:3][::2])
        game, drawn = self.crew(g.TIRED_SCORE + 1, 26)  # spent: a pose each 13 px; step 2, no slump
        left = drawn.named("gravpong_worker_l_")[0]
        self.assertEqual((g.WORKERS[0]["trun"][26 // g.TIRED_STEP_PX % 4], top), left[:3][::2])
        self.assertNotEqual(26 // g.STEP_PX % 4, 26 // g.TIRED_STEP_PX % 4)
        game, drawn = self.crew(g.TIRED_SCORE + 1, 13)  # step 1: slumped 1 px
        self.assertEqual({top + 1}, {c[2] for c in drawn.named("gravpong_worker_")})

    def test_the_notes_fall_into_the_net_only_within_its_width(self):
        game, now = lost()
        game.score, game.px, game.popped = 24, 100.0, True  # the net 46 px wide
        game.notes.q[:] = [[120.0, 200.0, 0.0, 40.0, 0, -1], [160.0, 200.0, 0.0, 40.0, 0, -1]]
        for _ in range(30):
            now += FRAME_MS
            game.step(now, False, False)
        inside, outside = game.notes.q
        self.assertEqual(20, inside[5])  # in the net, 20 px from its left end
        self.assertEqual((-1, game.FLOOR - 3), (outside[5], outside[1]))  # past its 46 px: on the floor


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
