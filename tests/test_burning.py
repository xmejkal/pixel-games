"""The bodies on fire (P596, P607) and their flares (P590) on the Mac: the scene on fx_fire.c through test_fire's engine
stand-in, its bodies on a PhysicsPlugin over motion.Bodies or over world.c (engine/tests/world_lib.py), and its burns.
The trail itself is tested in test_effects.py. Run from the repository root: python3 -m unittest discover tests.
--- MVP (P607) ---"""

import contextlib
import ctypes
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_fire import FIRE_C, S3LCD_SRC, Engine, Recorder, Tft, play  # noqa: E402  (also puts games/ and stubs/ on the path)

import burning  # noqa: E402
import fire  # noqa: E402
import plugins  # noqa: E402
import world_lib  # noqa: E402
from motion import HIT, SLEEP  # noqa: E402

REPORT = re.compile(r"^burning (linear|picture|nearest) fps \d+ step \d+\.\d\d draw \d+\.\d\d$", re.M)


class PhysicsPluginStandIn(plugins.Plugin):
    """A stand-in for plugins.PhysicsPlugin: each body's top left corner is set by the test, read() reports the
    sleepers, and a step makes the test's next events the ones events() drains, as Bodies.step clears the last ones
    first. fixed_update steps every frame, also with 0 steps, as the plugin does."""

    def __init__(self, places):
        self.n, self.places, self.asleep, self.spawned = len(places), places, set(), []
        self.next, self.drained = [], []

    def fixed_update(self, ms):
        self.step(ms // 10)

    def spawn(self, i, *args):
        self.spawned.append(i)

    def step(self, steps):
        self.drained, self.next = [v for event in self.next for v in event], []

    def read(self, drop):
        for i in sorted(self.asleep):
            drop(i)

    def events(self):
        return len(self.drained) // 3

    def place(self, i):
        return self.places[i]


@unittest.skipUnless(shutil.which("clang"), "clang is missing: engine/core/fx_fire.c is not built")
class BurningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        lib_path = os.path.join(cls.tmp.name, "libfire.so")
        subprocess.run(["clang", "-std=c99", "-O2", "-shared", "-fPIC", "-I", S3LCD_SRC, "-o", lib_path, FIRE_C],
                       check=True)
        cls.lib = ctypes.CDLL(lib_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        fire.engine = Engine(self.lib)
        self.world, plugins.engine = plugins.engine, None

    def tearDown(self):
        fire.engine, plugins.engine = None, self.world

    def scene(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = burning.BurningBodies()
        # every body above the screen: no burn until a test moves one
        game.physics_plugin = PhysicsPluginStandIn([(0, -100)] * burning.N)
        game.plugins = (game.physics_plugin, game.fire_plugin)
        game.attach_effects()  # the effects on the stand-in
        fire.engine.burns = []
        return game

    def test_a_tap_frame_keeps_its_bodies_step_time(self):
        """Fire.play's tap starts a new interval, so the scene takes it before it counts the bodies' step (P633)."""
        game = self.scene()
        game.physics_plugin.step_us = 7
        game.ms = 40
        with mock.patch.object(time, "ticks_us", lambda: 0):  # the read's own time is 0, so the sums are exact
            game.play(True, True)
        self.assertEqual("picture", game.mode_name)
        self.assertEqual((7, 7), (game.us[0], game.hud_us))

    def test_the_scene_counts_the_ms_it_played(self):
        """A body rests REST_MS of played time before it drops, so played_ms grows by each frame's ms."""
        game = self.scene()
        for _ in range(3):
            self.frame(game, 20)
        self.assertEqual(60, game.played_ms)

    def frame(self, game, ms):
        """One frame's FixedUpdate and Update, as Game.step runs them while the game plays (P633)."""
        game.ms = ms
        game.physics_plugin.fixed_update(ms)
        game.play(False, False)

    def test_the_bodies_burn_and_report(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            game = burning.BurningBodies()
            tft = Tft()
            play(game, 150, 0, tft)  # 6 s: past REPORT_MS, and the bodies have landed
        self.assertRegex(out.getvalue(), REPORT)
        self.assertRegex(game.label, r"^burning linear \d+\.\d ms \d+ fps$")
        self.assertEqual([burning.BurningBodies.LOOK], fire.engine.looks)
        self.assertEqual(0, game.fire_plugin.field.f.base)  # only the bodies burn
        self.assertTrue(fire.engine.burns)
        self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame))  # the flames reached the frame
        self.assertTrue(self.flares(), "a first landing flares")

    # --- MVP (P639) ---
    def frame_log(self, game, tft, now, pressed=False):
        """One frame whose fills and field draws go into one log, in their order: the log and now."""
        def canvas(tft):
            cv = Recorder(tft)
            cv.fills = fire.engine.targets
            return cv

        fire.engine.targets, fire.engine.filters = [], []
        _, now = play(game, 1, now, tft, pressed=pressed, canvas=canvas)
        return fire.engine.targets, now

    def test_each_mode_draws_the_flames_the_bodies_then_the_flames_in_front(self):
        """Linear and nearest draw the field opaque, picture blends it over the sky (black on the Mac, which has no
        art). Then the eight bodies, then the field again in front of them at FRONT_ALPHA."""
        bodies = [(burning.BODY, burning.BODY)] * burning.N
        blends = []
        draw = fire.FirePlugin.draw_over
        with contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.object(fire.FirePlugin, "draw_over", lambda p, cv, a: blends.append(a) or draw(p, cv, a)):
            game = burning.BurningBodies()
            tft = Tft()
            _, now = play(game, 5, 0, tft)
            seen = []
            for pressed in (False, True, True):
                log, now = self.frame_log(game, tft, now, pressed)
                sky = log[:1] == [(0, 0, fire.WIDTH, fire.HEIGHT)]
                log = log[1:] if sky else log
                seen.append((game.mode_name, sky, fire.engine.filters, log[0], [f[2:] for f in log[1:-1]], log[-1]))
        self.assertEqual([
            ("linear", False, [], "tft", bodies, "tft alpha"),
            ("picture", True, [fire.LINEAR], "tft alpha", bodies, "tft alpha"),
            ("nearest", False, [fire.NEAREST], "tft", bodies, "tft alpha"),
        ], seen)
        self.assertEqual([fire.ALPHA, burning.FRONT_ALPHA], blends[-3:-1])  # picture: behind, then in front
        self.assertIs(burning.FRONT_ALPHA, blends[-1])

    def test_the_front_flames_stay_at_most_half_opaque(self):
        """The fire's ramp up to ALPHA_FULL, then FRONT_MAX for every hotter heat, so a body shows through."""
        self.assertEqual((0, burning.FRONT_MAX, burning.FRONT_MAX), (burning.FRONT_ALPHA[0],
                         burning.FRONT_ALPHA[fire.ALPHA_FULL], burning.FRONT_ALPHA[255]))
        self.assertEqual(64, burning.FRONT_ALPHA[fire.ALPHA_FULL // 2])

    @unittest.skipUnless(world_lib.HAVE_CLANG, "clang is missing: engine/core/world.c is not built")
    def test_a_landing_in_c_flares_in_python(self):
        plugins.engine = world_lib.engine()
        with contextlib.redirect_stdout(io.StringIO()):
            game = burning.BurningBodies()
            play(game, 150, 0, Tft())
        self.assertEqual("c", game.physics_plugin.name)
        self.assertTrue(self.flares())

    def test_without_the_engine_the_bodies_land_with_no_error(self):
        fire.engine = None
        with contextlib.redirect_stdout(io.StringIO()):
            game = burning.BurningBodies()
            play(game, 150, 0, Tft())  # past the first hard landings, as in test_the_bodies_burn_and_report
        self.assertIsNone(game.fire_plugin.field)
        self.assertEqual({}, game.handlers)

    def flares(self):
        """The burns that are flares: a disc wider than a body's burn."""
        return [b for b in fire.engine.burns if b[4] > burning.RADIUS]

    def landing(self, speed, kind=HIT):
        """A scene whose body 0 rests on its plane at y 200 and has bounced back up to y 190 since its event."""
        game = self.scene()
        game.rest_y[0] = 200
        game.physics_plugin.places[0] = (100, 190)
        game.physics_plugin.next = [(0, kind, speed)]
        game.physics_plugin.step(1)
        return game

    def test_a_fast_landing_flares_at_its_plane(self):
        game = self.landing(burning.FLARE_MIN)
        game.effects.dispatch(game.handlers)
        c = (100 + burning.BODY // 2) // 2, (200 + burning.BODY // 2) // 2  # its read x, its plane's y
        r, heat = burning.flare_size(burning.FLARE_MIN)
        self.assertEqual([(c[0], c[1], c[0], c[1], r, heat)], fire.engine.burns)
        self.assertGreater(r, burning.RADIUS)
        self.assertLessEqual(r, burning.FLARE_RADIUS_MAX)
        self.assertLessEqual(heat, 255)

    def test_a_faster_landing_flares_wider_and_hotter(self):
        slow, fast = burning.flare_size(700), burning.flare_size(1300)
        self.assertGreater(fast[0], slow[0])
        self.assertGreater(fast[1], slow[1])
        self.assertEqual((burning.FLARE_RADIUS_MAX, 255), burning.flare_size(100000))

    def test_a_slow_landing_does_not_flare(self):
        game = self.landing(burning.FLARE_MIN - 1)
        game.effects.dispatch(game.handlers)
        self.assertEqual([], fire.engine.burns)

    def test_a_sleep_does_not_flare(self):
        game = self.landing(1000, SLEEP)  # a sleep's speed is 0; 1,000 here shows that the kind is checked
        game.effects.dispatch(game.handlers)
        self.assertEqual([], fire.engine.burns)

    def test_no_event_no_flare(self):
        game = self.scene()
        game.physics_plugin.step(1)
        game.effects.dispatch(game.handlers)
        self.assertEqual([], fire.engine.burns)

    def test_a_frame_of_0_steps_does_not_flare_again(self):
        game = self.scene()
        game.rest_y[0], game.physics_plugin.places[0] = 200, (100, -100)  # above the screen, so only its flare burns
        game.physics_plugin.next = [(0, HIT, 1000)]
        self.frame(game, 40)  # 4 steps
        self.assertEqual(1, len(fire.engine.burns))
        self.frame(game, 4)  # under a step: 0 steps, and still a step call, which clears the events
        self.assertEqual(1, len(fire.engine.burns))

    def test_a_sleeping_body_rests_before_its_drop(self):
        game = self.scene()
        game.physics_plugin.asleep = {3}
        game.played_ms = 0
        game.physics_plugin.read(game.sleep)
        game.played_ms = burning.REST_MS - 1
        game.physics_plugin.read(game.sleep)
        self.assertEqual([], game.physics_plugin.spawned)
        game.played_ms = burning.REST_MS
        game.physics_plugin.read(game.sleep)
        self.assertEqual([3], game.physics_plugin.spawned)

    def test_a_frame_flares_then_burns_each_trail_once(self):
        game = self.scene()
        game.rest_y[0], game.physics_plugin.places[0] = 200, (100, 100)
        game.physics_plugin.next = [(0, HIT, 1000)]
        self.frame(game, 40)
        x, plane, y = (100 + burning.BODY // 2) // 2, (200 + burning.BODY // 2) // 2, (100 + burning.BODY // 2) // 2
        r, heat = burning.flare_size(1000)
        self.assertEqual([(x, plane, x, plane, r, heat), (x, y, x, y, burning.RADIUS, burning.HEAT)], fire.engine.burns)

    def test_a_drop_burns_no_streak_from_the_last_place(self):
        game = self.scene()
        game.physics_plugin.places[0] = (100, 200)
        game.effects.update()
        game.drop(0)  # a respawn: its trail resets its path
        game.physics_plugin.places[0] = (60, 4)
        game.effects.update()
        c = (60 + burning.BODY // 2) // 2, (4 + burning.BODY // 2) // 2
        self.assertEqual((c[0], c[1], c[0], c[1], burning.RADIUS, burning.HEAT), fire.engine.burns[-1])

if __name__ == "__main__":
    unittest.main()
