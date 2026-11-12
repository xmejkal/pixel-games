"""games/meteors.py on the Mac (P773, story 3): the Rules with no display (the walker, the drop clock, the fair aim), and
the game on Python's bodies and on the ctypes stand-in for engine.Bodies of engine/tests/world_lib.py. Run from the
repository root: python3 -m unittest discover tests. --- MVP (P773) ---"""

import contextlib
import io
import itertools
import os
import random
import sys
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engine", "tests"))  # pixel-engine: clang_lib
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

sys.path.insert(0, HERE)
from test_fire import Recorder, Tft  # noqa: E402

import app  # noqa: E402
import burning  # noqa: E402
import effects  # noqa: E402
import fire  # noqa: E402
import gfx  # noqa: E402
import lcd  # noqa: E402
import meteors as mt  # noqa: E402
import motion  # noqa: E402
import plugins  # noqa: E402
import signals  # noqa: E402
import world_lib  # noqa: E402
from meteors import COAL, FALL, PARKED, Meteors, Rules  # noqa: E402

COALS = [0] * 8  # the ms of eight meteors that are coals: they block always

FRAME_MS = 42


def walker_at(x, direction=1):
    rules = Rules()
    rules.walker_x, rules.dir = x, direction
    return rules


class RulesTest(unittest.TestCase):
    def test_the_walker_walks_in_whole_px_and_carries_the_rest(self):
        rules = Rules()
        start = rules.walker_x
        rules.move(100, False)
        self.assertEqual(start + mt.WALK_PX_S // 10, rules.walker_x)
        rules.move(7, False)  # 7 ms is under a pixel: the rest is carried, not lost
        before = rules.walker_x
        rules.move(7, False)
        self.assertEqual(before + mt.WALK_PX_S * 14 // 1000 - mt.WALK_PX_S * 7 // 1000, rules.walker_x)
        self.assertEqual(114, rules.played_ms)

    def test_it_turns_at_both_edges_and_leaves_an_edge_at_once(self):
        rules = Rules()
        while rules.dir > 0:
            rules.move(60, False)
        self.assertEqual(mt.WALKER_MAX_X, rules.walker_x)
        self.assertEqual(-1, rules.dir)
        rules.move(60, False)
        self.assertEqual(mt.WALKER_MAX_X - (mt.WALK_PX_S * 60 + 999) // 1000, rules.walker_x)  # going left, a part px counts
        while rules.dir < 0:
            rules.move(60, False)
        self.assertEqual((0, 1), (rules.walker_x, rules.dir))
        rules.move(60, False)
        self.assertEqual(mt.WALK_PX_S * 60 // 1000, rules.walker_x)
        self.assertEqual(mt.WIDTH, mt.WALKER_MAX_X + mt.WALKER_W)

    def test_a_tap_turns_it_but_not_within_turn_ms_of_the_last_turn(self):
        rules = Rules()
        rules.move(50, True)
        self.assertEqual(-1, rules.dir)
        for _ in range(mt.TURN_MS // 50 - 1):
            rules.move(50, True)  # 50, 100 ms after the turn: ignored
        self.assertEqual(-1, rules.dir)
        rules.move(50, True)  # TURN_MS after it
        self.assertEqual(1, rules.dir)
        rules = walker_at(0, -1)  # an edge turn counts as a turn too
        rules.move(10, False)
        self.assertEqual((1, 0), (rules.dir, rules.walker_x))
        rules.move(10, True)
        self.assertEqual(1, rules.dir)

    def test_fast_taps_never_stand_still(self):
        rules = Rules()
        xs = set()
        for _ in range(200):
            rules.move(42, True)
            xs.add(rules.walker_x)
        self.assertGreater(max(xs) - min(xs), 6)

    def test_the_hit_test_at_the_rectangles_edges(self):
        rules = walker_at(100)
        top = mt.HEIGHT - mt.WALKER_H
        self.assertTrue(rules.hits(100 - mt.BODY + 1, top - mt.BODY + 1))
        self.assertFalse(rules.hits(100 - mt.BODY, top - mt.BODY + 1))  # touching sides only
        self.assertFalse(rules.hits(100 - mt.BODY + 1, top - mt.BODY))  # touching top only
        self.assertTrue(rules.hits(100 + mt.WALKER_W - 1, mt.GROUND_Y))
        self.assertFalse(rules.hits(100 + mt.WALKER_W, mt.GROUND_Y))
        self.assertFalse(rules.hits(100, mt.HEIGHT))  # a parked body is off the screen

    def test_the_drop_clock_drops_one_meteor_each_drop_ms_and_carries_the_rest(self):
        rules = Rules()
        drops = total = 0
        for _ in range(60):  # 42 ms frames: under a second, so the level is 0
            total += 42
            drops += rules.due(42, True)
        self.assertEqual(total // mt.DROP_MS, drops)

    def test_a_full_pool_never_sends_a_burst(self):
        rules = Rules()
        for _ in range(500):
            self.assertFalse(rules.due(60, False))
        self.assertTrue(rules.due(1, True))
        self.assertFalse(rules.due(1, True))
        self.assertFalse(rules.due(60, True))

    def test_each_second_shortens_the_drop_time_down_to_the_floor(self):
        rules = Rules()
        self.assertEqual(mt.DROP_MS, rules.drop_ms())
        rules.played_ms = 3999
        self.assertEqual(mt.DROP_MS - 3 * mt.DROP_STEP_MS, rules.drop_ms())
        rules.played_ms = 10 ** 6
        self.assertEqual(mt.DROP_MIN_MS, rules.drop_ms())
        stop = (mt.DROP_MS - mt.DROP_MIN_MS) // mt.DROP_STEP_MS
        rules.played_ms = (stop - 1) * 1000
        self.assertGreater(rules.drop_ms(), mt.DROP_MIN_MS)
        rules.played_ms = stop * 1000
        self.assertEqual(mt.DROP_MIN_MS, rules.drop_ms())
        self.assertGreater(mt.DROP_MIN_MS, 60)  # a frame holds one drop at most

    def test_the_first_bounce_peaks_under_the_walkers_height(self):
        v = y = 0.0
        while y < mt.HEIGHT:  # as the bodies fall, from y = -BODY
            v += mt.GRAVITY_PX * plugins.DT
            y += v * plugins.DT
        up = v * plugins.RESTITUTION
        self.assertGreaterEqual(mt.WALKER_H, up * up / (2 * mt.GRAVITY_PX))


class AimTest(unittest.TestCase):
    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(5)

    def test_an_aim_starts_and_lands_on_the_screen_at_both_edges(self):
        for walker, direction in ((0, -1), (0, 1), (mt.WALKER_MAX_X, 1), (mt.WALKER_MAX_X, -1), (150, 1)):
            rules = walker_at(walker, direction)
            seen = set()
            for _ in range(400):
                land_x, vx, x0 = rules.aim([-1] * 8, COALS)
                self.assertTrue(0 <= land_x <= mt.WIDTH - mt.BODY and 0 <= x0 <= mt.WIDTH - mt.BODY, (walker, land_x, x0))
                self.assertLessEqual(abs(vx), mt.DRIFT)
                self.assertLessEqual(abs(x0 + vx * mt.FALL_MS / 1000 - land_x), 1)  # the drift carries it to its mark
                seen.add(land_x)
            self.assertGreater(len(seen), 20)

    def test_a_drop_aims_at_the_walker_and_ahead_of_it(self):
        rules = walker_at(100, 1)
        spots = {rules.aim([-1] * 8, COALS)[0] for _ in range(300)}
        here = 100 + (mt.WALKER_W - mt.BODY) // 2
        ahead = here + mt.WALK_PX_S * mt.FALL_MS // 1000
        self.assertTrue({here, ahead} <= spots)

    def marks(self, *xs):
        return list(xs) + [-1] * (8 - len(xs))

    def test_a_mark_that_leaves_less_than_safe_px_is_not_fair(self):
        rules = walker_at(50)
        coal = self.marks(100)  # blocks 80 to 116: the walker's gap is 0 to 80
        self.assertTrue(rules.fair(coal, COALS, 200))
        self.assertFalse(rules.fair(coal, COALS, 20))  # leaves 36 to 80: 44 px
        self.assertFalse(rules.fair(coal, COALS, 30))
        self.assertFalse(rules.fair(coal, COALS, 60))  # on the walker: its ends open into 40 and 4 px
        self.assertEqual(44, mt.room(mt.blocked(list(coal) + [20], COALS + [0]), 50, 1))

    def test_a_mark_on_the_walker_is_fair_when_it_can_leave_in_time_into_a_wide_gap(self):
        self.assertTrue(walker_at(150).fair(self.marks(), COALS, 150 + 2))
        self.assertTrue(walker_at(150, -1).fair(self.marks(), COALS, 150 + 2))
        old = mt.LAND_MS
        self.addCleanup(setattr, mt, "LAND_MS", old)
        mt.LAND_MS = 100  # no time to cross 20 px, and to turn
        self.assertFalse(walker_at(150, -1).fair(self.marks(), COALS, 152))

    def test_an_escape_that_passes_under_a_falling_meteor_must_clear_it_before_it_lands(self):
        """The refuter's case (seed 32 at 60 ms): the walker under a falling meteor at 202, going left; a new mark at 161
        closes the left. The right needs a turn and 18 px under the meteor at 202: fair only if that one lands later."""
        rules = walker_at(200, -1)
        soon, late = self.marks(202), self.marks(202)
        self.assertFalse(rules.fair(soon, [200] + [0] * 7, 161))
        self.assertTrue(rules.fair(late, [mt.LAND_MS] + [0] * 7, 161))

    def test_a_coal_beside_the_walker_bars_only_its_own_side(self):
        coal = self.marks(100 - mt.BODY - 4)  # within the margin on the left, not touching
        zones = mt.blocked(coal, COALS)
        self.assertGreater(mt.room(zones, 100, -1), mt.SAFE_PX)  # it turns and leaves to the right

    def test_fair_at_both_walls(self):
        self.assertTrue(walker_at(0, -1).fair(self.marks(), COALS, 0))  # leaves right, into 292 px
        self.assertTrue(walker_at(mt.WALKER_MAX_X, 1).fair(self.marks(), COALS, mt.WIDTH - mt.BODY))
        coal = self.marks(60)  # the left wall's gap is 0 to 40: already under SAFE_PX
        rules = walker_at(0, -1)
        self.assertTrue(rules.fair(coal, COALS, 250))  # no worse than before
        self.assertFalse(rules.fair(coal, COALS, 20))  # would leave nothing
        rules = walker_at(mt.WALKER_MAX_X, 1)
        self.assertTrue(rules.fair(self.marks(250), COALS, 20))
        self.assertFalse(rules.fair(self.marks(250), COALS, 280))

    def test_fair_with_coals_and_marks_on_both_sides(self):
        rules = walker_at(120)
        both = self.marks(60, 200)  # blocks 40 to 76 and 180 to 216: the gap is 76 to 180
        self.assertTrue(rules.fair(both, COALS, 150))  # leaves 76 to 130: 54 px
        self.assertFalse(rules.fair(both, COALS, 140))  # leaves 76 to 120: 44 px
        self.assertFalse(rules.fair(both, COALS, 130))  # on the walker: its ends open into 34 px
        self.assertTrue(rules.fair(both, COALS, 100))  # leaves 116 to 180
        self.assertTrue(rules.fair(both, COALS, 20))  # outside the gap

    def test_no_aim_leaves_the_walker_cut_off_and_a_crowded_ground_skips_the_drop(self):
        random.seed(11)
        rules = walker_at(50)
        coal = self.marks(100)
        for _ in range(300):
            aim = rules.aim(coal, COALS)
            if aim is not None:
                self.assertTrue(rules.fair(coal, COALS, aim[0]), aim)

    def test_when_every_try_is_unfair_the_drop_is_skipped(self):
        rules = walker_at(20)  # a coal at 60 leaves it 0 to 40: a drop at 0 would leave 16 to 40
        tries = itertools.cycle([-mt.DRIFT, 0, 0])  # the drift, the kind, the place
        with mock.patch.object(mt.random, "randrange", lambda *args: next(tries)):
            self.assertIsNone(rules.aim(self.marks(60), COALS))


def new_game():
    with contextlib.redirect_stdout(io.StringIO()):
        return Meteors()


def start(game):
    """The tap that leaves the title; the time of that frame."""
    game.step(0, True, False)
    return 0


def aim_at(land_x, vx=0):
    shift = vx * mt.FALL_MS // 1000
    return lambda places, left: (land_x, vx, land_x - shift)


def calm(game):
    """The walker stands, the clock never ticks: a test with its own meteors keeps them alone."""
    def move(ms, tapped):
        game.rules.played_ms += ms
    game.rules.move = move
    game.rules.due = lambda ms, free: False


def run(game, now, frames, tap, ms=FRAME_MS, limit=None):
    """frames frames of ms (a number, or a function) from now, or until the round is over or limit ms of play have
    passed. tap(game, t) says whether BOOT was tapped at play time t. Answers the time of the last frame and the ms."""
    t = 0
    for _ in range(frames):
        frame = ms() if callable(ms) else ms
        now += frame
        t += frame
        game.step(now, tap(game, t, frame), False)
        if game.state != gfx.PLAY or (limit is not None and t >= limit):
            break
    return now, t


def idle(game, t, ms):
    return False


def always(game, t, ms):
    return True


def rhythm(period):
    return lambda game, t, ms: t // period != (t - ms) // period


def bot(game, t, ms):
    """Keeps out of every place a mark or a coal blocks, leaves one that falls on it by the end into the wider gap, and
    turns only at the ends of its gap."""
    rules, top = game.rules, mt.WALKER_MAX_X
    zones = mt.blocked(game.land_x, COALS)  # the bot keeps out of every mark, as of a coal
    x = rules.walker_x
    inside = [z for z in zones if z[0] < x < z[1]]
    if inside:
        lo, hi, marks = inside[0]
        ends = [e for e in (lo, hi) if 0 <= e <= top
                and not (e == lo and any(m + mt.BODY <= x for m, _ in marks))
                and not (e == hi and any(m - mt.WALKER_W >= x for m, _ in marks))]
        if not ends:
            return False
        width = lambda e: e - max([z[1] for z in zones if z[1] <= e] + [0]) if e == lo else min(
            [z[0] for z in zones if z[0] >= e] + [top]) - e
        return (1 if max(ends, key=width) > x else -1) != rules.dir
    a = max([z[1] for z in zones if z[1] <= x] + [0])
    b = min([z[0] for z in zones if z[0] >= x] + [top])
    if rules.dir > 0:
        return b < top and b - x <= 14
    return a > 0 and x - a <= 14


class Log:
    def __init__(self, game):
        self.log, self.signals = [], signals.Signals()
        for name in ("land", "die"):
            self.signals.listen(name, lambda n, v: self.log.append((n, v)))
        game.signals = self.signals

    def names(self):
        return [n for n, _ in self.log]


class SeededTest(unittest.TestCase):
    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(773)  # setup() never seeds: the tests do


class MeteorsTest(SeededTest):
    def setUp(self):
        super().setUp()
        self.game = new_game()
        self.log = Log(self.game)

    def test_it_is_a_game_with_a_title_a_hint_two_cues_and_one_fire_mode(self):
        game = self.game
        self.assertIsInstance(game, burning.BurningBodies)
        self.assertEqual(("meteors", "tap: turn"), (game.name, game.hint))
        self.assertEqual({"land", "die"}, set(game.cues))
        self.assertEqual(gfx.Game.TITLE_MS, game.TITLE_MS)
        self.assertEqual(1, len(game.MODES))
        self.assertIsNone(game.SEED)
        self.assertEqual((game.physics_plugin, game.fire_plugin), game.plugins)
        self.assertEqual(float(mt.GRAVITY_PX), game.physics_plugin.world[1])
        self.assertEqual(0.0, game.physics_plugin.world[3])

    def test_it_takes_burnings_place_in_the_game_box(self):
        self.assertIn(Meteors, app.GAMES)
        self.assertNotIn("burning", [g.name for g in app.GAMES])

    def test_every_body_starts_parked_off_the_screen(self):
        game = self.game
        self.assertEqual(bytearray(mt.N), game.phase)
        self.assertEqual([-1] * mt.N, list(game.land_x))
        plugin = game.physics_plugin
        for i in range(mt.N):
            self.assertEqual((0, mt.HEIGHT), plugin.place(i))

    def test_the_title_lasts_title_ms_and_a_tap_leaves_it(self):
        game = new_game()
        game.step(0, False, False)
        game.step(gfx.Game.TITLE_MS - 1, False, False)
        self.assertEqual(gfx.TITLE, game.state)
        game.step(gfx.Game.TITLE_MS, False, False)
        self.assertEqual(gfx.PLAY, game.state)
        game = new_game()
        game.step(0, True, False)
        self.assertEqual(gfx.PLAY, game.state)

    def test_the_hud_is_the_score_bar_and_the_score_is_the_seconds_lived(self):
        game = self.game
        self.assertIs(gfx.Game.hud, type(game).hud)
        self.assertIs(gfx.Game.draw_hud, type(game).draw_hud)
        now = start(game)
        calm(game)
        run(game, now, 100, idle, 42, 3500)
        self.assertEqual(game.rules.played_ms // 1000, game.score)
        self.assertEqual(3, game.score)

    def test_a_meteor_moves_after_one_frame(self):
        game = self.game
        now = start(game)
        game.rules.aim = aim_at(150)
        game.rules.due = lambda ms, free: False
        game.drop(0)
        self.assertEqual(FALL, game.phase[0])
        game.step(now + FRAME_MS, False, False)
        self.assertGreater(game.physics_plugin.place(0)[1], -mt.BODY)

    def test_a_tap_turns_the_walker_and_does_not_change_the_fire_mode(self):
        game = self.game
        now = start(game)
        game.step(now + 40, True, False)
        self.assertEqual((-1, 0), (game.rules.dir, game.mode))
        self.assertEqual(game.MODES[0][0], game.mode_name)

    def test_parked_bodies_are_not_drawn_not_burned_and_not_hit(self):
        game = self.game
        now = start(game)
        calm(game)
        game.rules.walker_x = 0
        burns = []

        class Field:
            def burn(self, *args):
                burns.append(args)

        game.effects.bodies[0].effect = effects.FireTrail(Field(), mt.BODY, burning.RADIUS, burning.HEAT, burning.LAG)
        run(game, now, 5, idle)
        self.assertEqual(gfx.PLAY, game.state)  # a parked body at x 0 is not under the walker at x 0
        self.assertEqual([], burns)
        cv = Recorder(Tft())
        game.paint(cv)
        self.assertEqual([(0, mt.HEIGHT - mt.WALKER_H, mt.WALKER_W, mt.WALKER_H)], cv.fills)

    def test_a_falling_meteor_has_a_mark_and_the_coal_none(self):
        game = self.game
        now = start(game)
        calm(game)
        game.rules.aim = aim_at(100)
        game.drop(2)
        game.step(now + FRAME_MS, False, False)
        cv = Recorder(Tft())
        game.paint(cv)
        self.assertIn((100, mt.HEIGHT - mt.MARK_H, mt.BODY, mt.MARK_H), cv.fills)
        now, _ = run(game, now + FRAME_MS, 100, idle)
        self.assertEqual(COAL, game.phase[2])
        cv = Recorder(Tft())
        game.paint(cv)
        self.assertNotIn((100, mt.HEIGHT - mt.MARK_H, mt.BODY, mt.MARK_H), cv.fills)
        self.assertIn((100, mt.GROUND_Y, mt.BODY, mt.BODY), cv.fills)

    def test_a_coal_rests_within_1_px_of_its_mark_and_on_the_screen_at_both_ends(self):
        for land_x, vx in ((0, -mt.DRIFT), (mt.WIDTH - mt.BODY, mt.DRIFT), (150, 0), (150, mt.DRIFT)):
            game = new_game()
            now = start(game)
            calm(game)
            game.rules.walker_x = 150 + 100 if land_x < 200 else 20
            game.rules.aim = aim_at(land_x, vx)
            game.drop(0)
            run(game, now, 100, idle)
            x, y = game.physics_plugin.place(0)
            self.assertEqual(COAL, game.phase[0], land_x)
            self.assertLessEqual(abs(x - land_x), 1, (land_x, vx, x))
            self.assertTrue(0 <= x <= mt.WIDTH - mt.BODY)
            self.assertEqual(mt.GROUND_Y, y)

    def test_a_coal_kills(self):
        game = self.game
        now = start(game)
        calm(game)
        game.rules.walker_x = 100
        game.phase[0], game.slept[0] = COAL, game.rules.played_ms
        game.land_x[0] = 104
        game.physics_plugin.spawn(0, 104, mt.GROUND_Y, 0, 0, mt.GROUND_Y)
        game.step(now + FRAME_MS, False, False)
        self.assertEqual(gfx.OVER, game.state)
        self.assertEqual(["die"], self.log.names())

    def test_a_falling_meteor_kills(self):
        game = self.game
        now = start(game)
        calm(game)
        game.rules.walker_x = 100
        game.phase[0] = FALL
        game.land_x[0] = 104
        game.physics_plugin.spawn(0, 104, mt.HEIGHT - mt.WALKER_H - mt.BODY - 2, 0, 200, mt.GROUND_Y)
        run(game, now, 10, idle)
        self.assertEqual(gfx.OVER, game.state)

    def test_a_meteor_beside_the_walker_does_not_kill_it(self):
        game = self.game
        now = start(game)
        calm(game)
        game.rules.walker_x = 100
        game.rules.aim = aim_at(100 + mt.WALKER_W)
        game.drop(0)
        run(game, now, 100, idle)
        self.assertEqual(gfx.PLAY, game.state)
        self.assertEqual(COAL, game.phase[0])

    def test_a_landing_on_the_walker_kills_at_42_ms_60_ms_and_jittered_frames(self):
        for ms in (42, 60, lambda: random.randint(20, 90)):
            game = new_game()
            now = start(game)
            calm(game)
            game.rules.walker_x = 150
            game.rules.aim = aim_at(152)
            game.drop(0)
            run(game, now, 400, idle, ms)
            self.assertEqual(gfx.OVER, game.state)
            self.assertLess(game.rules.played_ms, 2500)

    def test_a_first_hit_on_the_walker_kills_though_the_read_place_is_far_above_it(self):
        game = self.game
        start(game)
        calm(game)
        game.rules.walker_x = 150
        game.phase[0], game.landed[0] = FALL, 0
        game.physics_plugin.spawn(0, 152, 0, 0, 0, mt.GROUND_Y)
        game.physics_plugin.read(lambda i: None)
        game.hit(game.effects.bodies[0], 440)
        self.assertEqual(gfx.OVER, game.state)
        self.assertEqual(["land", "die"], self.log.names())
        game.hit(game.effects.bodies[0], 440)  # a second hit of the same meteor: nothing more
        self.assertEqual(["land", "die"], self.log.names())

    def test_a_first_hit_beside_the_walker_only_lands(self):
        game = self.game
        start(game)
        game.rules.walker_x = 50
        game.phase[1], game.landed[1] = FALL, 0
        game.physics_plugin.spawn(1, 200, 100, 0, 0, mt.GROUND_Y)
        game.physics_plugin.read(lambda i: None)
        game.hit(game.effects.bodies[1], 440)
        self.assertEqual((gfx.PLAY, ["land"]), (game.state, self.log.names()))

    def test_land_sounds_once_per_meteor_and_a_bounce_does_not(self):
        game = self.game
        now = start(game)
        calm(game)
        game.rules.walker_x = 20
        game.rules.aim = aim_at(200)
        game.drop(0)
        run(game, now, 150, idle)  # 6 s: the fall and every bounce
        self.assertEqual(["land"], self.log.names())

    def test_a_coal_is_parked_after_coal_ms(self):
        game = self.game
        start(game)
        game.phase[3], game.slept[3], game.land_x[3] = COAL, 1000, 80
        game.rules.played_ms = 1000 + mt.COAL_MS - 1
        game.sleep(3)
        self.assertEqual(COAL, game.phase[3])
        game.rules.played_ms += 1
        game.sleep(3)
        self.assertEqual((PARKED, -1), (game.phase[3], game.land_x[3]))
        self.assertEqual((0, mt.HEIGHT), game.physics_plugin.place(3))
        game.sleep(3)  # a parked body that sleeps again does nothing
        self.assertEqual(PARKED, game.phase[3])

    def test_a_falling_meteor_that_sleeps_becomes_a_coal_with_its_time(self):
        game = self.game
        start(game)
        game.phase[0] = FALL
        game.rules.played_ms = 777
        game.sleep(0)
        self.assertEqual((COAL, 777), (game.phase[0], game.slept[0]))

    def test_a_pool_that_is_full_drops_nothing_until_a_body_frees(self):
        game = self.game
        now = start(game)
        for i in range(mt.N):
            game.phase[i] = COAL
            game.slept[i] = 10 ** 9
        game.rules.clock = mt.DROP_MS
        game.rules.walker_x = 0
        spawns = []
        game.drop = lambda i: spawns.append(i)
        now, _ = run(game, now, 5, idle)
        self.assertEqual([], spawns)
        game.park(3)  # one body frees: one meteor, never a burst
        run(game, now, 5, idle)
        self.assertEqual([3], spawns)

    def test_a_restart_keeps_the_field_and_the_bodies_and_resets_the_time_and_the_score(self):
        game = self.game
        now = start(game)
        field, physics, effects_ = game.fire_plugin, game.physics_plugin, game.effects
        run(game, now, 300, idle)
        self.assertEqual(gfx.OVER, game.state)
        self.assertGreater(game.score, 0)
        game.restart()
        self.assertEqual((0, 0), (game.score, game.rules.played_ms))
        self.assertEqual(bytearray(mt.N), game.phase)
        self.assertEqual([-1] * mt.N, list(game.land_x))
        self.assertIs(field, game.fire_plugin)
        self.assertIs(physics, game.physics_plugin)
        self.assertIs(effects_, game.effects)
        self.assertEqual((physics, field), game.plugins)

    def test_a_round_never_seeds_random_so_two_rounds_drop_at_different_places(self):
        with mock.patch.object(burning.random, "seed") as seed:
            game = new_game()
            game.restart()
        seed.assert_not_called()

    def test_a_skipped_aim_leaves_the_body_parked(self):
        game = self.game
        start(game)
        game.rules.aim = lambda places, left: None
        game.drop(0)
        self.assertEqual(PARKED, game.phase[0])

    def test_the_title_the_play_and_the_game_over_draw_without_an_error(self):
        game = self.game
        for state in (gfx.TITLE, gfx.PLAY, gfx.OVER):
            if state == gfx.PLAY:
                start(game)
                game.step(FRAME_MS, False, False)
            elif state == gfx.OVER:
                game.die()
            tft = Tft()
            game.draw(lcd.TftCanvas(tft))
            self.assertEqual(state, game.state)
            self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame), state)


class PlayersTest(SeededTest):
    """The gate beside the Mac trial: who does nothing, or plays blind, loses; who sees the marks lasts. 60 ms is the
    longest frame the game takes."""

    def lasts(self, player, ms, limit):
        game = new_game()
        run(game, start(game), limit, player, ms, limit)
        return game

    def jitter(self):
        return random.randint(20, 90)

    def test_an_idle_player_loses_in_under_60_s(self):
        for ms in (42, 60, self.jitter):
            for seed in (1, 2, 3, 4):
                random.seed(seed)
                self.assertEqual(gfx.OVER, self.lasts(idle, ms, 60000).state, (ms, seed))

    def test_a_player_who_taps_every_frame_or_at_8_hz_loses_in_under_60_s(self):
        for player in (always, rhythm(125)):
            for ms in (42, 60, self.jitter):
                for seed in (1, 2, 3, 4):
                    random.seed(seed)
                    self.assertEqual(gfx.OVER, self.lasts(player, ms, 60000).state, (ms, seed))

    def test_every_blind_rhythm_loses_in_under_90_s(self):
        for ms in (42, 60, self.jitter):
            for period in range(200, 3001, 400):
                random.seed(period)
                game = self.lasts(rhythm(period), ms, 90000)
                self.assertEqual(gfx.OVER, game.state, (ms, period))

    def test_a_bot_that_keeps_to_the_free_ground_lasts_3_minutes(self):
        for ms in (42, 60, self.jitter):
            for seed in (1, 2, 3, 4):
                random.seed(seed)
                game = self.lasts(bot, ms, 180000)
                self.assertEqual(gfx.PLAY, game.state, (ms, seed, game.score))
                self.assertGreater(game.score, 100)


@unittest.skipUnless(world_lib.HAVE_CLANG, "clang is missing: engine/core/world.c is not built")
class CMeteorsTest(SeededTest):
    def tearDown(self):
        plugins.engine = None

    def test_c_and_python_give_the_same_game_within_a_frame(self):
        """C steps in float and Python in double: a falling meteor's read y may differ by 1 px, so a death may come one
        frame apart (the refuter: 2 of 320 runs). The outcome is the same."""
        for seed in (773, 4, 15, 30):
            for player in (idle, bot):
                ends = []
                for c in (True, False):
                    plugins.engine = world_lib.engine() if c else None
                    random.seed(seed)
                    game = new_game()
                    self.assertEqual("c" if c else "python", game.physics_plugin.name)
                    run(game, start(game), 1500, player, 42, 40000)
                    ends.append((game.state, game.rules.played_ms))
                (state_c, ms_c), (state_py, ms_py) = ends
                self.assertEqual(state_c, state_py, (seed, player.__name__))
                self.assertLessEqual(abs(ms_c - ms_py), 42, (seed, player.__name__))


if __name__ == "__main__":
    unittest.main()
