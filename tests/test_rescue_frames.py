"""Rescue's fire in the frames the README's GIF is made from (P800): in every frame of render_scene's rescue row where
the crater burns, the flame comes out of the crater, and once the fire is out no flame floats on. The row runs in its
own process, as tools/render_scene.py sets module state (the clock, the engines). Needs clang. Run from the
repository root: python3 -m unittest discover tests. --- MVP (P800) ---"""

import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOUCH_PX = 4  # the flame's lowest bright pixel lies this close to the crater's top, at most
SPARKS_PX = 12  # bright pixels a frame after the fire is out may hold: sparks still in the air, not a flame

# One line per frame: whether the fire burns, the lowest flame row in the crater's columns (-1: none), how many flame
# pixels there, and the crater's top row. A flame pixel is bright orange to yellow and differs from the still street.
SCRIPT = r"""
import itertools, sys
sys.path.insert(0, "tools")
sys.path.insert(0, "art")
import render_scene as rs
from export import from_bin
import rescue
with open("games/art/rescue_night.bin", "rb") as f:
    street = from_bin(f.read(), 320, 240).convert("RGB")
row = rs.SUBJECTS["rescue"]
made, make = [], row.game
row.game = lambda: made.append(make()) or made[-1]
for img in itertools.islice(rs.frames(row), row.last):
    crater = made[0].rules.crater
    low, n = -1, 0
    for y in range(20, rescue.LANE):
        for x in range(crater.x - 10, crater.x + 11):
            p, q = img.getpixel((x, y)), street.getpixel((x, y))
            if p[0] > 180 and p[0] - p[2] > 60 and sum(abs(a - b) for a, b in zip(p, q)) > 120:
                low, n = y, n + 1
    print(int(crater.burning()), low, n, rescue.LANE - 1)
"""


@unittest.skipUnless(shutil.which("clang"), "clang is missing: the C heat field is not built")
class FireTouchesItsCraterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = subprocess.run([sys.executable, "-B", "-c", SCRIPT], cwd=ROOT, capture_output=True, text=True)
        assert run.returncode == 0, run.stderr[-800:]
        cls.frames = [tuple(int(v) for v in line.split()) for line in run.stdout.split("\n")
                      if line[:2] in ("0 ", "1 ")]

    def test_the_row_burns_and_puts_the_fire_out(self):
        burning = [b for b, *_ in self.frames]
        self.assertIn(1, burning)
        self.assertIn(0, burning[burning.index(1):])

    def test_in_every_burning_frame_the_flame_comes_out_of_the_crater(self):
        for k, (burning, low, _, top) in enumerate(self.frames[1:], 1):  # frame 0 is the title's press: no step yet
            if burning:
                with self.subTest(frame=k):
                    self.assertGreaterEqual(low, top - TOUCH_PX)

    def test_once_the_fire_is_out_no_flame_floats_on(self):
        out = [k for k, (burning, *_) in enumerate(self.frames) if not burning]
        for k in out:
            with self.subTest(frame=k):
                self.assertLessEqual(self.frames[k][2], SPARKS_PX)


if __name__ == "__main__":
    unittest.main()
