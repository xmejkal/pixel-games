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

RUN_CELL_X = (arcade.RUN_X + arcade.RUN_BOX // 2) // 2  # the fire cell under the runner's centre


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
        run_frames(self.game, 60)
        burns = fire.engine.burns
        self.assertTrue(burns)
        self.assertEqual((RUN_CELL_X, RUN_CELL_X), (burns[0][0], burns[0][2]))  # the first burn is under the runner
        self.assertTrue(fire.engine.scrolls)
        self.assertTrue(all(dx < 0 for dx in fire.engine.scrolls))

    def test_a_new_round_starts_with_no_fire(self):
        run_frames(self.game, 60)
        heat = self.game.layer.field.heat
        self.assertTrue(any(heat[:fire.W * fire.H]))
        self.game.restart()
        self.assertEqual(bytes(fire.W * fire.H), bytes(heat[:fire.W * fire.H]))
        self.assertFalse(self.game.trail.has_path)

    def test_the_fire_is_drawn_blended_over_the_frame(self):
        run_frames(self.game, 60)
        self.game.layer.draw(Recorder(tft := Tft()))
        self.assertEqual("tft alpha", fire.engine.targets[-1])
        self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame))

    def test_the_heat_steps_every_fire_step_ms_not_every_frame(self):
        now = run_frames(self.game, 40)  # past the title
        steps = []
        self.game.layer.field.step = lambda n, wind: steps.append(n)
        run_frames(self.game, 20, now)  # 800 ms of play: a step in every second frame
        self.assertEqual(arcade.FIRE_STEP_MS, 80)
        self.assertTrue(8 <= sum(steps) <= 11, steps)

    def test_the_flame_starts_at_nothing_and_grows_to_full_in_fire_grow_ms(self):
        game, looks = self.game, fire.engine.looks
        self.assertEqual((0, 0), (game.trail.heat, looks[-1][0]))  # off at the start of the round
        now = run_frames(game, 36)  # the title, under 1,500 ms: the round has not begun
        self.assertEqual(0, game.trail.heat)
        now = run_frames(game, 29, now)  # about 1,000 ms of play: about half
        self.assertTrue(0 < game.trail.heat < arcade.FIRE_HEAT, game.trail.heat)
        self.assertTrue(0 < looks[-1][0] < arcade.FIRE_DECAY, looks[-1])
        run_frames(game, 30, now)  # past FIRE_GROW_MS
        self.assertEqual((arcade.FIRE_HEAT, arcade.FIRE_DECAY), (game.trail.heat, looks[-1][0]))
        n = len(looks)
        run_frames(game, 10, now + 1200)
        self.assertEqual(n, len(looks))  # full: the look is not set again
        game.restart()
        self.assertEqual((0, 0), (game.trail.heat, looks[-1][0]))
