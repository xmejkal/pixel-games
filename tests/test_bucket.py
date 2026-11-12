"""games/bucket.py on the Mac (P773, story 2): the Rules with no display, and the game on Python's bodies and on the
ctypes stand-in for engine.Bodies of engine/tests/world_lib.py. Run from the repository root:
python3 -m unittest discover tests. --- MVP (P773) ---"""

import contextlib
import io
import os
import random
import sys
import time
import unittest

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
import bucket as bk  # noqa: E402
import gfx  # noqa: E402
import lcd  # noqa: E402
import plugins  # noqa: E402
import signals  # noqa: E402
import world_lib  # noqa: E402
from bucket import FALL, FREE, LAND, Bucket, Rules  # noqa: E402

FRAME_MS = 42  # app.py's FRAME_MS is 40, and the board's frames run 42 to 60 ms


class RulesTest(unittest.TestCase):
    def test_held_moves_the_bucket_right_and_released_moves_it_left_in_whole_px(self):
        rules = Rules()
        start = rules.bucket_x
        for _ in range(3):
            rules.move(100, True)
        self.assertEqual(start + bk.BUCKET_PX_S * 3 // 10, rules.bucket_x)  # 0.3 s held
        for _ in range(2):
            rules.move(100, False)
        self.assertEqual(start + bk.BUCKET_PX_S // 10, rules.bucket_x)
        before = rules.bucket_x
        rules.move(3, True)  # 3 ms is under a pixel: the rest is carried, not lost
        rules.move(3, True)
        self.assertEqual(before + bk.BUCKET_PX_S * 6 // 1000, rules.bucket_x)

    def test_the_bucket_stays_on_the_screen_at_both_edges_and_leaves_an_edge_at_once(self):
        rules = Rules()
        for _ in range(100):
            rules.move(60, False)
        self.assertEqual(bk.LEFT_X, rules.bucket_x)
        rules.move(60, True)  # no debt is carried from the edge
        self.assertEqual(bk.LEFT_X + bk.BUCKET_PX_S * 60 // 1000, rules.bucket_x)
        for _ in range(100):
            rules.move(60, True)
        self.assertEqual(bk.RIGHT_X, rules.bucket_x)
        rules.move(60, False)
        self.assertEqual(bk.RIGHT_X - (bk.BUCKET_PX_S * 60 + 999) // 1000, rules.bucket_x)  # going left, a part px counts
        self.assertEqual(0, bk.LEFT_X + bk.WALL_PX)  # the inside reaches both screen edges
        self.assertEqual(bk.WIDTH, bk.RIGHT_X + bk.BUCKET_W - bk.WALL_PX)

    def test_caught_needs_the_whole_box_between_the_walls_at_both_edges(self):
        rules = Rules()
        left, right = rules.bucket_x + bk.WALL_PX, rules.bucket_x + bk.BUCKET_W - bk.WALL_PX  # the inside
        self.assertTrue(rules.caught(left))
        self.assertTrue(rules.caught(right - bk.SIZE))
        self.assertFalse(rules.caught(left - 1))  # over the left wall
        self.assertFalse(rules.caught(right - bk.SIZE + 1))  # over the right wall
        self.assertFalse(rules.caught(0 if left > bk.SIZE else bk.WIDTH - bk.SIZE))

    def test_the_end_columns_can_be_caught(self):
        rules = Rules()
        rules.bucket_x = bk.LEFT_X
        self.assertTrue(rules.caught(0))
        rules.bucket_x = bk.RIGHT_X
        self.assertTrue(rules.caught(bk.WIDTH - bk.SIZE))

    def test_the_drop_clock_drops_one_box_each_drop_ms_and_carries_the_rest(self):
        rules = Rules()
        drops, total = 0, 0
        for _ in range(1000):  # 42 ms frames
            total += 42
            drops += rules.due(42, True)
        self.assertEqual(total // bk.DROP_MS, drops)

    def test_a_full_pool_never_sends_a_burst(self):
        rules = Rules()
        for _ in range(500):
            self.assertFalse(rules.due(60, False))
        self.assertTrue(rules.due(1, True))  # a body frees: one box drops at once
        self.assertFalse(rules.due(1, True))  # and the clock starts again, with no second box
        self.assertFalse(rules.due(60, True))

    def test_each_point_shortens_the_drop_time_down_to_the_least(self):
        rules = Rules()
        self.assertEqual(bk.DROP_MS, rules.drop_ms())
        rules.score = 3
        self.assertEqual(bk.DROP_MS - 3 * bk.DROP_STEP_MS, rules.drop_ms())
        rules.score = 1000
        self.assertEqual(bk.DROP_MIN_MS, rules.drop_ms())
        # the speed-up stops at the first (DROP_MS - DROP_MIN_MS) / DROP_STEP_MS points
        stop = (bk.DROP_MS - bk.DROP_MIN_MS) // bk.DROP_STEP_MS
        rules.score = stop - 1
        self.assertGreater(rules.drop_ms(), bk.DROP_MIN_MS)
        rules.score = stop
        self.assertEqual(bk.DROP_MIN_MS, rules.drop_ms())
        self.assertGreater(bk.DROP_MIN_MS, 60)  # a frame holds one drop at most

    def test_a_catch_is_a_point(self):
        rules = Rules()
        self.assertEqual(1, rules.catch())
        self.assertEqual(2, rules.catch())
        self.assertEqual(2, rules.score)

    def test_a_miss_adds_to_its_column_and_the_pile_is_full_at_the_rail(self):
        rules = Rules()
        for k in range(1, bk.PILE_ROWS):
            self.assertEqual(k, rules.miss(5))
            self.assertFalse(rules.full(5))
        self.assertEqual(bk.PILE_ROWS, rules.miss(5))
        self.assertTrue(rules.full(5))
        self.assertFalse(rules.full(6))
        self.assertEqual(bk.HEIGHT - bk.SIZE * bk.PILE_ROWS, bk.RAIL_Y)

    def test_there_is_a_column_for_every_x_a_box_drops_at(self):
        self.assertEqual(bk.WIDTH, bk.COLS * bk.SIZE)
        self.assertEqual(bk.COLS, len(Rules().pile))


def new_game():
    with contextlib.redirect_stdout(io.StringIO()):
        return Bucket()


def put(game, i, x, y, vy=0):
    """Box i falling at x, y with speed vy, as drop() makes it but not at a random column."""
    game.phase[i], game.last_y[i] = FALL, y
    game.physics_plugin.spawn(i, x, y, 0, vy, bk.HEIGHT)


def no_drops(game):
    """The drop clock never ticks: a test with its own boxes keeps them alone."""
    game.rules.due = lambda ms, free: False


def start(game):
    """The tap that leaves the title; the time of that frame."""
    game.step(0, True, False)
    return 0


def run(game, now, frames, hold, ms=FRAME_MS, limit=None):
    """frames frames of ms (a number, or a function that gives each frame's ms) from now, or until the round is over or limit ms of play have passed. hold(game, t) says
    whether BOOT is down at play time t. Answers the time of the last frame and the ms of play."""
    t = 0
    for _ in range(frames):
        frame = ms() if callable(ms) else ms
        now += frame
        t += frame
        game.step(now, False, hold(game, t))
        if game.state != gfx.PLAY or (limit is not None and t >= limit):
            break
    return now, t


def idle(game, t):
    return False


def held(game, t):
    return True


def rhythm(period, duty):
    return lambda game, t: t % period < period * duty // 100


def bot(game, t):
    """Steers to the lowest falling box it can see: BOOT is down when its middle is right of the bucket's."""
    best = None
    for i in range(bk.N):
        if game.phase[i] == FALL and game.last_y[i] != -bk.SIZE:  # a box just dropped has no read yet
            x, y = game.physics_plugin.place(i)
            if best is None or y > best[1]:
                best = (x, y)
    target = bk.WIDTH // 2 if best is None else best[0] + bk.SIZE // 2
    return game.rules.bucket_x + bk.BUCKET_W // 2 < target


class Log:
    """A signals.Signals with every signal of the cues noted as (name, value)."""

    def __init__(self, game):
        self.log, self.signals = [], signals.Signals()
        for name in ("catch", "miss", "die"):
            self.signals.listen(name, lambda n, v: self.log.append((n, v)))
        game.signals = self.signals

    def names(self):
        return [n for n, _ in self.log]


class SeededTest(unittest.TestCase):
    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(773)  # setup() never seeds: the tests do


class BucketTest(SeededTest):
    def setUp(self):
        super().setUp()
        self.game = new_game()
        self.log = Log(self.game)

    def test_it_is_a_game_with_a_title_a_hint_and_three_cues_the_bank_has(self):
        game = self.game
        self.assertIsInstance(game, gfx.Game)
        self.assertEqual(("bucket", "hold: right"), (game.name, game.hint))
        self.assertEqual({"catch", "miss", "die"}, set(game.cues))
        self.assertEqual("python", game.physics_plugin.name)
        self.assertEqual((game.physics_plugin,), game.plugins)

    def test_it_takes_the_rains_place_in_the_game_box(self):
        self.assertIn(Bucket, app.GAMES)
        self.assertNotIn("rain", [g.name for g in app.GAMES])

    def test_a_box_moves_after_one_frame_in_play(self):
        game = self.game
        now = start(game)
        game.drop(0)
        game.step(now + FRAME_MS, False, False)
        self.assertEqual(gfx.PLAY, game.state)
        self.assertGreater(game.physics_plugin.place(0)[1], -bk.SIZE)
        self.assertEqual(FALL, game.phase[0])

    def test_the_frame_after_the_title_with_boot_still_held_plays(self):
        game = self.game
        game.step(0, True, True)  # the tap leaves the title: no play yet
        self.assertEqual(gfx.PLAY, game.state)
        left = game.rules.bucket_x
        game.step(FRAME_MS, False, True)
        self.assertEqual(left + bk.BUCKET_PX_S * FRAME_MS // 1000, game.rules.bucket_x)

    def test_the_bucket_moves_in_play_with_boot(self):
        game = self.game
        now = start(game)
        x = game.rules.bucket_x
        game.step(now + 40, False, True)
        self.assertGreater(game.rules.bucket_x, x)
        game.step(now + 80, False, False)
        game.step(now + 120, False, False)
        self.assertLess(game.rules.bucket_x, x)

    def test_a_box_that_crosses_the_rail_in_one_60_ms_frame_is_decided(self):
        game = self.game
        now = start(game)
        game.rules.bucket_x = 110  # 60 ms left take it 18 px: 92 to 142 holds the box at 120
        put(game, 0, 120, bk.RAIL_Y - bk.SIZE - 5, 400)  # its bottom is 5 px above the rail, 24 px in a frame
        game.step(now + 60, False, False)
        self.assertGreater(game.physics_plugin.place(0)[1] + bk.SIZE, bk.RAIL_Y)  # it did cross
        self.assertEqual((FREE, 1, 1), (game.phase[0], game.score, game.rules.score))
        self.assertEqual(["catch"], self.log.names())
        self.assertEqual(bytearray(bk.COLS), game.rules.pile)

    def test_a_box_beside_the_bucket_is_a_miss_that_lands_on_the_pile_in_its_column(self):
        game = self.game
        now = start(game)
        no_drops(game)
        game.rules.bucket_x = 200
        put(game, 0, 0, bk.RAIL_Y - bk.SIZE - 5, 400)
        game.step(now + 60, False, True)
        self.assertEqual((LAND, 0, 1), (game.phase[0], game.score, game.rules.pile[0]))
        self.assertEqual(["miss"], self.log.names())
        now, _ = run(game, now + 60, 400, idle)
        self.assertEqual((FREE, 1, 0), (game.phase[0], game.shown[0], game.shown[1]))
        self.assertEqual(bk.HEIGHT - bk.SIZE, game.physics_plugin.place(0)[1])  # on the floor
        self.assertEqual(["miss"], self.log.names())

    def test_a_missed_box_bounces_back_above_the_rail_and_is_not_caught(self):
        game = self.game
        now = start(game)
        no_drops(game)
        game.rules.pile[0] = 1  # the pile is 2 high with this box: its top is 10 px under the rail's
        game.rules.bucket_x = 200
        put(game, 0, 0, bk.RAIL_Y - bk.SIZE - 5, 400)
        now += 60
        game.step(now, False, True)
        self.assertEqual(LAND, game.phase[0])
        peak = bk.HEIGHT
        for _ in range(300):
            now += 40
            game.rules.bucket_x = 0  # the bucket waits under it for the box's way back through the rail
            game.step(now, False, False)
            peak = min(peak, game.physics_plugin.place(0)[1] + bk.SIZE)
            if game.state != gfx.PLAY:
                break
        self.assertLess(peak, bk.RAIL_Y)  # the bottom went back above the rail
        self.assertEqual((0, 2, 1), (game.score, game.rules.pile[0], game.shown[0]))
        self.assertEqual(["miss"], self.log.names())

    def test_two_boxes_in_one_column_land_one_above_the_other_and_the_third_ends_the_round(self):
        game = self.game
        now = start(game)
        no_drops(game)
        game.rules.bucket_x = 200
        put(game, 0, 0, bk.RAIL_Y - bk.SIZE - 5, 400)
        put(game, 1, 0, bk.RAIL_Y - bk.SIZE - 45, 400)
        now, _ = run(game, now, 400, idle)
        self.assertEqual(gfx.PLAY, game.state)
        self.assertEqual((2, 2, FREE, FREE), (game.rules.pile[0], game.shown[0], game.phase[0], game.phase[1]))
        self.assertEqual(sorted((bk.HEIGHT - bk.SIZE, bk.HEIGHT - 2 * bk.SIZE)),
                         sorted(game.physics_plugin.place(i)[1] for i in (0, 1)))
        game.rules.bucket_x = 200  # the idle bucket went left to the box's column
        put(game, 2, 0, bk.RAIL_Y - bk.SIZE - 5, 400)
        run(game, now, 20, held)
        self.assertEqual(gfx.OVER, game.state)
        self.assertEqual(["miss", "miss", "miss", "die"], self.log.names())

    def test_a_box_asleep_in_the_air_is_a_miss_and_loses_no_body(self):
        game = self.game
        start(game)
        game.rules.bucket_x = 200
        put(game, 0, 70, 50)  # column 7
        game.physics_plugin.read(lambda i: None)
        game.rest(0)  # by the rules it cannot happen
        self.assertEqual((LAND, 1, 0), (game.phase[0], game.rules.pile[7], game.rules.pile[0]))

    def test_a_missed_box_is_never_spawned_below_its_plane(self):
        game = self.game
        start(game)
        game.rules.bucket_x = 200
        game.rules.pile[0] = 2  # this miss makes 3: the plane is the rail
        put(game, 0, 0, bk.RAIL_Y - 2 * bk.SIZE)
        spawns = []
        game.physics_plugin.spawn = lambda i, x, y, vx, vy, plane: spawns.append((y, plane))
        game.at_rail(0, 0, bk.RAIL_Y + 6)
        self.assertEqual([(bk.RAIL_Y, bk.RAIL_Y)], spawns)

    def test_play_stops_when_a_body_asleep_in_the_air_ends_the_round(self):
        game = self.game
        now = start(game)
        game.rules.bucket_x = 200
        game.rules.pile[0] = bk.PILE_ROWS - 1
        put(game, 0, 0, 50)
        game.physics_plugin.read = lambda callback: callback(0)
        game.rules.due = lambda ms, free: self.fail("play went on after the round ended")
        game.step(now + FRAME_MS, False, False)
        self.assertEqual(gfx.OVER, game.state)

    def test_a_body_that_rests_is_free_for_the_next_box(self):
        game = self.game
        now = start(game)
        no_drops(game)
        put(game, 0, 0, bk.RAIL_Y - bk.SIZE - 5, 400)
        game.rules.bucket_x = 200
        run(game, now, 400, idle, limit=8000)
        self.assertEqual(FREE, game.phase[0])
        self.assertEqual(0, game.free_body())

    def test_a_pool_that_is_full_drops_nothing_until_a_body_frees(self):
        game = self.game
        now = start(game)
        for i in range(bk.N):
            put(game, i, 0, -bk.SIZE)
        game.rules.clock = bk.DROP_MS
        spawns = []
        spawn = game.physics_plugin.spawn
        game.physics_plugin.spawn = lambda i, *state: (spawns.append(i), spawn(i, *state))[1]
        run(game, now, 5, idle)
        self.assertEqual([], spawns)

    def test_two_rounds_drop_at_different_columns(self):
        game = self.game
        rounds = []
        for _ in range(2):
            columns = []
            spawn = game.physics_plugin.spawn
            game.physics_plugin.spawn = lambda i, x, *state, spawn=spawn: (columns.append(x), spawn(i, x, *state))[1]
            for _ in range(20):
                game.drop(0)
            rounds.append(columns)
            game.restart()
        self.assertNotEqual(rounds[0], rounds[1])
        self.assertTrue(all(x % bk.SIZE == 0 and 0 <= x < bk.WIDTH for x in rounds[0] + rounds[1]))

    def test_a_new_round_starts_clean(self):
        game = self.game
        start(game)
        game.rules.pile[3], game.shown[3], game.rules.score = 2, 2, 5
        game.restart()
        self.assertEqual((bytearray(bk.COLS), bytearray(bk.COLS), 0, 0),
                         (game.rules.pile, game.shown, game.rules.score, game.score))
        self.assertEqual(bytearray(bk.N), game.phase)

    def test_the_bucket_the_rail_the_pile_and_the_boxes_are_drawn(self):
        game = self.game
        start(game)
        game.shown[4] = 2
        game.rules.bucket_x = 100
        put(game, 0, 60, 30)
        game.physics_plugin.read(lambda i: None)
        cv = Recorder(Tft())
        game.paint(cv)
        self.assertIn((4 * bk.SIZE, bk.HEIGHT - 2 * bk.SIZE, bk.SIZE, 2 * bk.SIZE), cv.fills)
        self.assertIn((0, bk.RAIL_Y, bk.WIDTH, 1), cv.fills)
        self.assertIn((60, 30, bk.SIZE, bk.SIZE), cv.fills)
        put(game, 1, 90, 40)
        game.last_y[1] = -bk.SIZE  # dropped this frame: the plugin's read is stale
        game.physics_plugin.read(lambda i: None)
        cv = Recorder(Tft())
        game.paint(cv)
        self.assertNotIn((90, 40, bk.SIZE, bk.SIZE), cv.fills)
        self.assertIn((60, 30, bk.SIZE, bk.SIZE), cv.fills)
        self.assertIn((100, bk.RAIL_Y - bk.FLOOR, bk.BUCKET_W, bk.FLOOR), cv.fills)

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
    """The gate beside the Mac trial: who does nothing, or plays blind, loses; who steers lasts. 60 ms is the
    longest frame the game takes."""

    def lasts(self, player, ms, limit):
        game = new_game()
        run(game, start(game), limit, player, ms, limit)
        return game

    def test_an_idle_player_loses_in_under_60_s(self):
        for ms in (42, 60):
            for seed in (1, 2, 3):
                random.seed(seed)
                self.assertEqual(gfx.OVER, self.lasts(idle, ms, 60000).state, (ms, seed))

    def test_a_player_who_always_holds_loses_in_under_60_s(self):
        for ms in (42, 60):
            for seed in (1, 2, 3):
                random.seed(seed)
                self.assertEqual(gfx.OVER, self.lasts(held, ms, 60000).state, (ms, seed))

    def test_every_blind_rhythm_loses_in_under_90_s(self):
        for ms in (42, 60):
            for period in range(200, 2001, 300):
                for duty in (20, 35, 50, 65, 80):
                    random.seed(period + duty)
                    game = self.lasts(rhythm(period, duty), ms, 90000)
                    self.assertEqual(gfx.OVER, game.state, (ms, period, duty, game.score))

    def test_a_bot_that_steers_to_the_lowest_box_lasts_3_minutes(self):
        jitter = lambda: random.randint(20, 90)  # frames that are not fixed
        for ms in (42, 60, jitter):
            for seed in (1, 2, 3):
                random.seed(seed)
                game = self.lasts(bot, ms, 180000)
                self.assertEqual(gfx.PLAY, game.state, (ms, seed, game.score))
                self.assertGreater(game.score, 100)

    def test_a_perfect_player_catches_every_box_when_the_columns_alternate_0_and_31_at_full_speed(self):
        columns = [0, bk.COLS - 1] * 100
        for ms in (42, 60):
            game = new_game()
            drops = iter(columns)
            randrange = bk.random.randrange
            bk.random.randrange = lambda n: next(drops)
            try:
                run(game, start(game), 120000, bot, ms, 120000)
            finally:
                bk.random.randrange = randrange
            self.assertEqual(gfx.PLAY, game.state, ms)
            self.assertEqual(bytearray(bk.COLS), game.rules.pile, ms)
            self.assertGreater(game.score, 90, ms)


@unittest.skipUnless(world_lib.HAVE_CLANG, "clang is missing: engine/core/world.c is not built")
class CBucketTest(SeededTest):
    def setUp(self):
        super().setUp()
        plugins.engine = world_lib.engine()
        self.addCleanup(setattr, plugins, "engine", None)

    def test_c_and_python_make_the_same_pile_for_one_seed(self):
        for player in (idle, bot):
            piles = []
            for c in (True, False):
                random.seed(773)
                game = new_game()
                game.c = c
                game.restart()
                self.assertEqual("c" if c else "python", game.physics_plugin.name)
                run(game, start(game), 1500, player, 42, 40000)
                piles.append((bytes(game.rules.pile), bytes(game.shown), game.score, game.state))
            self.assertEqual(piles[0], piles[1], player.__name__)
            self.assertGreater(sum(piles[0][0]) + piles[0][2], 5)


if __name__ == "__main__":
    unittest.main()
