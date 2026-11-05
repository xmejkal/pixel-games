"""games/plugins.py and Game.step's stages on the Mac (P633): the plugins' hooks run around the game's play, in the
list's order and only while the game plays; PhysicsPlugin steps every frame; FirePlugin steps by its clock and blows
its gusts; each scene lists only the layers it uses. No C is built. Run from the repository root:
python3 -m unittest discover tests. --- MVP (P633) ---"""

import contextlib
import importlib.util
import io
import os
import sys
import time
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

import burning  # noqa: E402
import fire  # noqa: E402
import gfx  # noqa: E402
import plugins  # noqa: E402
import rain  # noqa: E402
from motion import HIT  # noqa: E402


class Recording(plugins.Plugin):
    """A plugin that writes each hook it gets into the game's log."""

    def __init__(self, name, log):
        self.name, self.log = name, log

    def fixed_update(self, ms):
        self.log.append(("fixed", self.name, ms))

    def late_update(self, ms):
        self.log.append(("late", self.name, ms))


class Scene(gfx.Game):
    """A game with two recording plugins; its play writes into the same log."""

    TITLE_MS = 0

    def setup(self):
        self.log = []
        self.plugins = (Recording("a", self.log), Recording("b", self.log))

    def play(self, pressed, held):
        self.log.append(("play", self.ms))


class StagesTest(unittest.TestCase):
    def test_fixed_then_play_then_late_in_the_lists_order(self):
        game = Scene()
        game.step(0, False, False)  # the title ends: no play yet
        self.assertEqual([], game.log)
        game.step(40, False, False)
        self.assertEqual([("fixed", "a", 40), ("fixed", "b", 40), ("play", 40), ("late", "a", 40), ("late", "b", 40)],
                         game.log)

    def test_no_plugin_runs_outside_play(self):
        game = Scene()
        game.TITLE_MS = 10 ** 9
        game.step(0, False, False)
        game.step(40, False, False)  # still the title
        game.state = gfx.OVER
        game.step(80, False, False)
        self.assertEqual([], game.log)

    def test_ms_is_the_old_rounding_capped_at_60(self):
        game = Scene()
        game.step(0, False, False)
        now = 0
        for ms in range(0, 61):
            now += ms
            game.step(now, False, False)
            self.assertEqual(int(game.dt * 1000 + 0.5), game.ms)
            self.assertEqual(ms, game.ms)
        game.step(now + 500, False, False)
        self.assertEqual(60, game.ms)

    def test_a_game_with_no_plugin_plays(self):
        game = gfx.Game()
        self.assertEqual((), game.plugins)
        game.step(0, False, False)
        game.step(2000, False, False)
        self.assertEqual(gfx.PLAY, game.state)


class EngineGuardTest(unittest.TestCase):
    def test_a_module_without_bodies_is_no_engine(self):
        """The Mac imports the repository's engine/ folder as an empty package: no Bodies, so Python's twin steps."""
        saved = sys.modules.get("engine")
        sys.modules["engine"] = types.ModuleType("engine")
        try:
            self.assertIsNone(self.fresh_plugins().engine)
            sys.modules["engine"].Bodies = object
            self.assertIs(sys.modules["engine"], self.fresh_plugins().engine)
        finally:
            if saved is None:
                del sys.modules["engine"]
            else:
                sys.modules["engine"] = saved

    def fresh_plugins(self):
        """A new copy of games/plugins.py, so the plugins module the other tests use keeps its classes."""
        spec = importlib.util.spec_from_file_location("plugins_copy", plugins.__file__)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class PhysicsPluginTest(unittest.TestCase):
    def test_a_frame_under_a_step_still_steps_and_clears_the_events(self):
        plugin = plugins.PhysicsPlugin(1, False)
        plugin.spawn(0, 0.0, 99.5, 0.0, 1000.0, 100.0)
        plugin.fixed_update(plugins.STEP_MS)
        self.assertEqual(1, plugin.events())
        self.assertEqual(HIT, plugin.drained[1])
        plugin.fixed_update(plugins.STEP_MS - 1)  # 0 steps
        self.assertEqual(0, plugin.events())
        self.assertGreater(plugin.step_us, 0)


class FieldStandIn:
    def __init__(self):
        self.steps = []

    def step(self, n, wind):
        self.steps.append(n)


class FirePluginTest(unittest.TestCase):
    def test_the_clock_takes_whole_steps_as_the_old_sum_did(self):
        """Fire's acc before P633: whole 40 ms steps, the rest carried. Game.step caps ms at 60, so 2 a frame at most."""
        plugin = fire.FirePlugin(fire.Fire.LOOK, 1)
        plugin.field = FieldStandIn()
        acc, old = 0, []
        for ms in (40, 20, 60, 60, 60, 13, 27, 0, 59):
            plugin.late_update(ms)
            acc += ms
            if acc // fire.STEP_MS:
                old.append(acc // fire.STEP_MS)
            acc %= fire.STEP_MS
        self.assertEqual(old, plugin.field.steps)

    def test_the_burning_scenes_wind_blows(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = burning.BurningBodies()
            now = 0
            winds = set()
            for _ in range(200):
                game.step(now, False, False)
                winds.add(game.fire_plugin.wind)
                now += 40
        self.assertGreater(len(winds), 1)


class ListedLayersTest(unittest.TestCase):
    """A scene runs only the layers it lists: the rain has no field, the fire no bodies."""

    def test_each_scene_lists_its_layers(self):
        with contextlib.redirect_stdout(io.StringIO()):
            kinds = [tuple(type(p) for p in g().plugins) for g in (rain.Rain, fire.Fire, burning.BurningBodies)]
        self.assertEqual([(plugins.PhysicsPlugin,), (fire.FirePlugin,), (plugins.PhysicsPlugin, fire.FirePlugin)], kinds)


if __name__ == "__main__":
    unittest.main()
