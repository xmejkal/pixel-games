"""Rescue's fires in the frames the README's GIF is made from (P800): in every frame of render_scene's rescue row,
each burning crater's flame comes out of that crater, and once a fire is out no flame floats on over its crater. The
row runs in its own process, as tools/render_scene.py sets module state (the clock, the engines). Needs clang. Run
from the repository root: python3 -m unittest discover tests. --- MVP (P800) ---"""

import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOUCH_PX = 4  # the flame's lowest bright pixel lies this close to the crater's top, at most
SPARKS_PX = 12  # bright pixels a frame after the fire is out may hold: sparks still in the air, not a flame

APART_PX = 40  # px: a dead crater this far from every burning one is checked for a flame floating on
# One line per crater and frame: the frame, the crater's x, whether its fire burns, whether a burning crater is within
# APART_PX of a dead one, the lowest flame row in its columns (-1: none), how many flame pixels there, and the crater's
# top row. A flame pixel is bright orange to yellow and differs from the still street.
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
for k, img in enumerate(itertools.islice(rs.frames(row), row.last)):
    craters = made[0].rules.craters
    for crater in craters:
        low, n = -1, 0
        near = any(c.burning() and abs(c.x - crater.x) <= %d for c in craters if c is not crater)
        for y in range(20, rescue.LANE):
            for x in range(max(0, crater.x - 10), min(320, crater.x + 11)):
                p, q = img.getpixel((x, y)), street.getpixel((x, y))
                if p[0] > 180 and p[0] - p[2] > 60 and sum(abs(a - b) for a, b in zip(p, q)) > 120:
                    low, n = y, n + 1
        print("crater", k, crater.x, int(crater.burning()), int(near), low, n, rescue.LANE - 1)
""" % APART_PX


@unittest.skipUnless(shutil.which("clang"), "clang is missing: the C heat field is not built")
class FireTouchesItsCraterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = subprocess.run([sys.executable, "-B", "-c", SCRIPT], cwd=ROOT, capture_output=True, text=True)
        assert run.returncode == 0, run.stderr[-800:]
        cls.rows = [tuple(int(v) for v in line.split()[1:]) for line in run.stdout.split("\n")
                    if line.startswith("crater ")]

    def test_the_row_burns_and_puts_a_fire_out(self):
        by_crater = {}
        for k, x, burning, *_ in self.rows:
            by_crater.setdefault(x, []).append(burning)
        self.assertTrue(any(1 in b and 0 in b[b.index(1):] for b in by_crater.values()))

    def test_in_every_frame_each_burning_crater_s_flame_comes_out_of_it(self):
        burning = [r for r in self.rows if r[2]]
        self.assertTrue(burning)
        for k, x, _, _, low, _, top in burning:
            with self.subTest(frame=k, crater=x):
                self.assertGreaterEqual(low, top - TOUCH_PX)

    def test_once_a_fire_is_out_no_flame_floats_on_over_its_crater(self):
        for k, x, burning, near, _, n, _ in self.rows:
            if not burning and not near:
                with self.subTest(frame=k, crater=x):
                    self.assertLessEqual(n, SPARKS_PX)


if __name__ == "__main__":
    unittest.main()
