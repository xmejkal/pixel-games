"""The Runner's fire (P651): a fire.FireLayer and a FireTrail on the Runner, on the same ctypes stand-in for the engine as
test_fire.py, and without the engine. --- MVP (P651) ---"""

import contextlib
import io
import shutil
import sys
import unittest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import test_fire  # noqa: E402  (puts games/ and stubs/ on the path)
from test_fire import Engine, Recorder, Tft  # noqa: E402

import arcade  # noqa: E402
import fire  # noqa: E402

RUN_CELL_X = arcade.RUN_X // 2  # the fire cell at the runner's back, where the trail burns


FAST_FAR = 40000  # px: base speed is past the full-flame speed


def run_frames(game, frames, now=0):
    for _ in range(frames):
        now += 40
        game.step(now, False, True)
    return now


class RunnerFireNoEngineTest(unittest.TestCase):
    def test_no_engine_no_field_and_the_runner_plays(self):
        fire.engine = None
        game = arcade.Runner()
        self.assertIsNone(game.trail)
        self.assertIsNone(game.layer.field)
        run_frames(game, 60)
        self.assertGreater(game.odo, 0)  # it ran
        game.layer.draw(Recorder(Tft()))  # nothing to draw, and no error


@unittest.skipUnless(shutil.which("clang"), "clang is missing: engine/core/fx_fire.c is not built")
class RunnerFireTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_fire.FireTest.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        fire.engine = Engine(self.lib)
        with contextlib.redirect_stdout(io.StringIO()):
            self.game = arcade.Runner()

    def tearDown(self):
        fire.engine = None

    def test_the_runner_burns_at_its_own_cell_and_the_world_scrolls_the_fire_left(self):
        self.game.far = FAST_FAR  # a run far enough on that the flame is full
        run_frames(self.game, 60)
        burns = fire.engine.burns
        self.assertTrue(burns)
        self.assertEqual((RUN_CELL_X, RUN_CELL_X), (burns[0][0], burns[0][2]))  # the first burn is under the runner
        self.assertTrue(fire.engine.scrolls)
        self.assertTrue(all(dx < 0 for dx in fire.engine.scrolls))

    def test_a_new_round_starts_with_no_fire(self):
        self.game.far = FAST_FAR  # a run far enough on that the flame is full
        run_frames(self.game, 60)
        heat = self.game.layer.field.heat
        self.assertTrue(any(heat[:fire.W * fire.H]))
        self.game.restart()
        self.assertEqual(bytes(fire.W * fire.H), bytes(heat[:fire.W * fire.H]))
        self.assertFalse(self.game.trail.has_path)

    def test_the_fire_is_drawn_blended_over_the_frame(self):
        self.game.far = FAST_FAR  # a run far enough on that the flame is full
        run_frames(self.game, 60)
        self.game.layer.draw(Recorder(tft := Tft()))
        self.assertEqual("tft alpha", fire.engine.targets[-1])
        self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame))

    def test_the_heat_steps_every_fire_step_ms_not_every_frame(self):
        self.game.far = FAST_FAR  # a run far enough on that the flame is full
        now = run_frames(self.game, 40)  # past the title
        steps = []
        self.game.layer.field.step = lambda n, wind: steps.append(n)
        run_frames(self.game, 20, now)  # 800 ms of play: a step in every second frame
        self.assertEqual(arcade.FIRE_STEP_MS, 80)
        self.assertTrue(8 <= sum(steps) <= 11, steps)

    def test_the_flame_follows_the_speed_none_at_the_start_full_at_the_full_speed(self):
        game, looks = self.game, fire.engine.looks
        self.assertEqual(150, int(game.base_speed()))  # the run starts below the start speed
        self.assertEqual((0, 0), (game.trail.heat, looks[-1][0]))  # no flame
        game.grow_fire(arcade.FIRE_START_SPEED)
        self.assertEqual((0, 0), (game.trail.heat, looks[-1][0]))  # still none at the start speed
        game.grow_fire((arcade.FIRE_START_SPEED + arcade.FIRE_FULL_SPEED) // 2)
        self.assertTrue(0 < game.trail.heat < arcade.FIRE_HEAT and 0 < looks[-1][0] < arcade.FIRE_DECAY, looks[-1])
        game.grow_fire(arcade.FIRE_FULL_SPEED)
        self.assertEqual((arcade.FIRE_HEAT, arcade.FIRE_DECAY), (game.trail.heat, looks[-1][0]))  # the flicker comes in play
        n = len(looks)
        game.grow_fire(arcade.FIRE_FULL_SPEED + 100)
        self.assertEqual((n, arcade.FIRE_HEAT), (len(looks), game.trail.heat))  # faster is no bigger, no new look
        game.restart()
        self.assertEqual((0, 0), (game.trail.heat, looks[-1][0]))

    def test_the_speed_grows_to_a_higher_top_and_the_flame_is_see_through(self):
        game = self.game
        speeds = []
        for far in (0, 800, 5000, 40000, 10 ** 7):
            game.far = far
            speeds.append(int(game.base_speed()))
        self.assertEqual(sorted(speeds), speeds)
        self.assertTrue(arcade.FIRE_FULL_SPEED < speeds[3] < speeds[4] <= arcade.SPEED_KNEE + 80, speeds)
        self.assertGreater(speeds[4], 650)  # the old top was 600
        alpha = arcade.FIRE_ALPHA
        self.assertEqual((0, arcade.FIRE_ALPHA_MAX), (alpha[0], alpha[255]))
        self.assertEqual(0, alpha[arcade.FIRE_CLEAR - 1])  # the coolest cells are clear
        self.assertLess(alpha[96], fire.ALPHA[96])  # fire.ALPHA is opaque from heat 96: this ramp is not
        self.assertEqual(sorted(alpha), list(alpha))
