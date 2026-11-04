"""The bodies on fire (P596, P607) and their flares (P590) on the Mac: the scene on fx_fire.c through test_fire's engine
stand-in, its bodies on rain.Stepper over motion.Bodies or over world.c (tests/world_lib.py), and its burns. The trail
itself is tested in test_effects.py. Run from the repository root: python3 -m unittest discover tests.
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
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_fire import FIRE_C, S3LCD_SRC, Engine, Tft, play  # noqa: E402  (also puts games/ and stubs/ on the path)

import burning  # noqa: E402
import fire  # noqa: E402
import rain  # noqa: E402
import world_lib  # noqa: E402
from motion import HIT, SLEEP  # noqa: E402

REPORT = re.compile(r"^burning B fps \d+ step \d+\.\d\d draw \d+\.\d\d$", re.M)


class StepperStandIn:
    """A stand-in for rain.Stepper: each body's top left corner is set by the test, read() reports the sleepers, and
    a step makes the test's next events the ones events() drains, as Bodies.step clears the last ones first."""

    def __init__(self, places):
        self.n, self.places, self.asleep, self.spawned = len(places), places, set(), []
        self.next, self.drained = [], []

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
        self.world, rain.engine = rain.engine, None  # the repository's engine/ folder imports as an empty package here

    def tearDown(self):
        fire.engine, rain.engine = None, self.world

    def scene(self):
        with contextlib.redirect_stdout(io.StringIO()):
            game = burning.BurningBodies()
        game.stepper = StepperStandIn([(0, -100)] * burning.N)  # every body above the screen: no burn until a test moves one
        game.light()  # the effects on the stand-in
        fire.engine.burns = []
        return game

    def test_the_bodies_burn_and_report(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            game = burning.BurningBodies()
            tft = Tft()
            play(game, 150, 0, tft)  # 6 s: past REPORT_MS, and the bodies have landed
        self.assertRegex(out.getvalue(), REPORT)
        self.assertRegex(game.label, r"^burning B \d+\.\d ms \d+ fps$")
        self.assertEqual([burning.BurningBodies.LOOK], fire.engine.looks)
        self.assertEqual(0, game.field.f.base)  # only the bodies burn
        self.assertTrue(fire.engine.burns)
        self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame))  # the flames reached the frame
        self.assertTrue(self.flares(), "a first landing flares")

    @unittest.skipUnless(world_lib.HAVE_CLANG, "clang is missing: engine/core/world.c is not built")
    def test_a_landing_in_c_flares_in_python(self):
        rain.engine = world_lib.engine()
        with contextlib.redirect_stdout(io.StringIO()):
            game = burning.BurningBodies()
            play(game, 150, 0, Tft())
        self.assertEqual("c", game.stepper.name)
        self.assertTrue(self.flares())

    def test_without_the_engine_the_bodies_land_with_no_error(self):
        fire.engine = None
        with contextlib.redirect_stdout(io.StringIO()):
            game = burning.BurningBodies()
            play(game, 150, 0, Tft())  # past the first hard landings, as in test_the_bodies_burn_and_report
        self.assertIsNone(game.field)
        self.assertEqual({}, game.reactions)

    def flares(self):
        """The burns that are flares: a disc wider than a body's burn."""
        return [b for b in fire.engine.burns if b[4] > burning.RADIUS]

    def landing(self, speed, kind=HIT):
        """A scene whose body 0 rests on its plane at y 200 and has bounced back up to y 190 since its event."""
        game = self.scene()
        game.rest_y[0] = 200
        game.stepper.places[0] = (100, 190)
        game.stepper.next = [(0, kind, speed)]
        game.stepper.step(1)
        return game

    def test_a_fast_landing_flares_at_its_plane(self):
        game = self.landing(burning.FLARE_MIN)
        game.effects.react(game.reactions)
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
        game.effects.react(game.reactions)
        self.assertEqual([], fire.engine.burns)

    def test_a_sleep_does_not_flare(self):
        game = self.landing(1000, SLEEP)  # a sleep's speed is 0; 1,000 here shows that the kind is checked
        game.effects.react(game.reactions)
        self.assertEqual([], fire.engine.burns)

    def test_no_event_no_flare(self):
        game = self.scene()
        game.stepper.step(1)
        game.effects.react(game.reactions)
        self.assertEqual([], fire.engine.burns)

    def test_a_frame_of_0_steps_does_not_flare_again(self):
        game = self.scene()
        game.rest_y[0], game.stepper.places[0] = 200, (100, -100)  # above the screen, so only its flare burns
        game.stepper.next = [(0, HIT, 1000)]
        game.dt = 0.04  # 4 steps
        game.play(False, False)
        self.assertEqual(1, len(fire.engine.burns))
        game.dt = 0.004  # under a step: 0 steps, and still a step call, which clears the events
        game.play(False, False)
        self.assertEqual(1, len(fire.engine.burns))

    def test_a_sleeping_body_rests_before_its_drop(self):
        game = self.scene()
        game.stepper.asleep = {3}
        game.clock = 0
        game.stepper.read(game.sleep)
        game.clock = burning.REST_MS - 1
        game.stepper.read(game.sleep)
        self.assertEqual([], game.stepper.spawned)
        game.clock = burning.REST_MS
        game.stepper.read(game.sleep)
        self.assertEqual([3], game.stepper.spawned)

    def test_a_frame_flares_then_burns_each_trail_once(self):
        game = self.scene()
        game.rest_y[0], game.stepper.places[0] = 200, (100, 100)
        game.stepper.next = [(0, HIT, 1000)]
        game.play(False, False)
        x, plane, y = (100 + burning.BODY // 2) // 2, (200 + burning.BODY // 2) // 2, (100 + burning.BODY // 2) // 2
        r, heat = burning.flare_size(1000)
        self.assertEqual([(x, plane, x, plane, r, heat), (x, y, x, y, burning.RADIUS, burning.HEAT)], fire.engine.burns)

    def test_a_drop_burns_no_streak_from_the_last_place(self):
        game = self.scene()
        game.stepper.places[0] = (100, 200)
        game.effects.apply()
        game.drop(0)  # a respawn: its trail forgets the path
        game.stepper.places[0] = (60, 4)
        game.effects.apply()
        c = (60 + burning.BODY // 2) // 2, (4 + burning.BODY // 2) // 2
        self.assertEqual((c[0], c[1], c[0], c[1], burning.RADIUS, burning.HEAT), fire.engine.burns[-1])

if __name__ == "__main__":
    unittest.main()
