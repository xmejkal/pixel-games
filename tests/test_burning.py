"""The bodies on fire (P596) on the Mac: the scene on fx_fire.c through test_fire's engine stand-in, its bodies on
rain.PythonStepper (no engine world here), and its burns. Run from the repository root:
python3 -m unittest discover tests. --- MVP (P596) ---"""

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

REPORT = re.compile(r"^burning B fps \d+ step \d+\.\d\d draw \d+\.\d\d$", re.M)


class Bodies:
    """A stand-in stepper: each body's top left corner is set by the test, and read() reports the sleepers."""

    def __init__(self, places):
        self.places, self.asleep, self.spawned = places, set(), []

    def spawn(self, i, *args):
        self.spawned.append(i)

    def step(self, steps):
        pass

    def read(self, drop):
        for i in sorted(self.asleep):
            drop(i)

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
        game.bodies = Bodies([(0, -100)] * burning.N)  # every body above the screen: no burn until a test moves one
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

    def test_a_body_at_rest_burns_at_itself(self):
        game = self.scene()
        game.bodies.places[0] = (100, 100)
        game.burn()
        game.burn()
        c = (100 + burning.BODY // 2) // 2, (100 + burning.BODY // 2) // 2
        self.assertEqual([(c[0], c[1], c[0], c[1], burning.RADIUS, burning.HEAT)] * 2, fire.engine.burns)

    def test_a_moving_body_burns_behind_itself_along_its_path(self):
        game = self.scene()
        game.bodies.places[0] = (100, 100)
        game.burn()
        game.bodies.places[0] = (140, 100)  # 20 cells right in a frame
        game.burn()
        c0, c1 = (100 + burning.BODY // 2) // 2, (140 + burning.BODY // 2) // 2
        lag = c1 - int((c1 - c0) * burning.LAG)
        self.assertLess(lag, c1)  # behind the body
        y = (100 + burning.BODY // 2) // 2
        self.assertEqual((c0, y, lag, y, burning.RADIUS, burning.HEAT), fire.engine.burns[-1])

    def test_a_sleeping_body_rests_before_its_drop(self):
        game = self.scene()
        game.bodies.asleep = {3}
        game.clock = 0
        game.bodies.read(game.sleep)
        game.clock = burning.REST_MS - 1
        game.bodies.read(game.sleep)
        self.assertEqual([], game.bodies.spawned)
        game.clock = burning.REST_MS
        game.bodies.read(game.sleep)
        self.assertEqual([3], game.bodies.spawned)

    def test_the_frame_after_a_drop_burns_no_streak(self):
        game = self.scene()
        game.bodies.places[0] = (100, 200)
        game.burn()
        game.bodies.places[0] = (100, -50)  # dropped: above the screen
        game.burn()
        game.bodies.places[0] = (60, 4)  # the first frame back on the screen
        game.burn()
        c = (60 + burning.BODY // 2) // 2, (4 + burning.BODY // 2) // 2
        self.assertEqual((c[0], c[1], c[0], c[1], burning.RADIUS, burning.HEAT), fire.engine.burns[-1])
        self.assertEqual(2, len(fire.engine.burns))


if __name__ == "__main__":
    unittest.main()
