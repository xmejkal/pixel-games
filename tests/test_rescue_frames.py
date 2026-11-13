"""Rescue's fires in the frames of render_scene's rescue row and of a round left alone, where a fire burns out by
itself (P800): in every frame each burning crater's flame comes out of that crater, a hosed fire's flame is one piece
from the crater up, and once a fire is out no flame floats on over its crater. Each row runs in its own process, as
tools/render_scene.py sets module state (the clock, the engines). Needs clang. Run from the repository root:
python3 -m unittest discover tests. --- MVP (P800) ---"""

import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOUCH_PX = 4  # the flame's lowest bright pixel lies this close to the crater's top, at most
SPARKS_PX = 12  # bright pixels a frame after the fire is out may hold: sparks still in the air, not a flame
GAP_PX = 4  # rows with no flame a hosed fire's flame may hold and still be one piece
APART_PX = 40  # px: a dead crater this far from every burning one is checked for a flame floating on
ALONE = ((0, 1),)  # a press to start, then nothing: the first fire burns out by itself (frame 208)
ALONE_LAST = 230
# One line per crater and frame: the frame, the crater's x, whether its fire burns, whether a burning crater is within
# APART_PX of a dead one, the lowest flame row in its columns (-1: none), how many flame pixels there, the crater's top
# row, whether it was hosed, and the flame pixels above the first run of more than GAP_PX rows with no flame up from
# the crater (a "help!" plate over the flame counts as flame). A flame pixel is bright orange to yellow, differs from
# the still street and is not a spark's colour (sparks fly free of the flame).
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
presses, last = eval(sys.argv[1]), int(sys.argv[2])
if presses:
    row.presses, row.last = presses, last
made, make = [], row.game
row.game = lambda: made.append(make()) or made[-1]
spark = None
for k, img in enumerate(itertools.islice(rs.frames(row), row.last)):
    craters = made[0].rules.craters
    for crater in craters:
        low, n, rows = -1, 0, {}
        near = any(c.burning() and abs(c.x - crater.x) <= %d for c in craters if c is not crater)
        for y in range(20, rescue.LANE):
            for x in range(max(0, crater.x - 10), min(320, crater.x + 11)):
                p, q = img.getpixel((x, y)), street.getpixel((x, y))
                if p[0] > 180 and p[0] - p[2] > 60 and sum(abs(a - b) for a, b in zip(p, q)) > 120:
                    low, n = y, n + 1
                    if p != (255, 190, 82):  # SPARK as the canvas draws it
                        rows[y] = rows.get(y, 0) + 1
        for p in made[0].rules.people:
            if p.state == rescue.WAVING and p.wave_ms %% 1000 < 600 and abs(p.x - crater.x) <= 31:
                rows.update((y, rows.get(y, 0)) for y in range(rescue.PLATE_Y, rescue.PLATE_Y + 11))
        y, miss = rescue.LANE - 1, 0
        while y >= 20 and miss <= %d:
            miss = 0 if y in rows else miss + 1
            y -= 1
        apart = sum(v for r, v in rows.items() if r <= y)
        print("crater", k, crater.x, int(crater.burning()), int(near), low, n, rescue.LANE - 1, int(crater.wet_ms > 0),
              apart)
""" % (APART_PX, GAP_PX)


def run_row(presses=None, last=0):
    run = subprocess.run([sys.executable, "-B", "-c", SCRIPT, repr(presses), str(last)], cwd=ROOT,
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-800:]
    return [tuple(int(v) for v in line.split()[1:]) for line in run.stdout.split("\n") if line.startswith("crater ")]


@unittest.skipUnless(shutil.which("clang"), "clang is missing: the C heat field is not built")
class FireTouchesItsCraterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shown, cls.alone = run_row(), run_row(ALONE, ALONE_LAST)
        cls.rows = cls.shown + cls.alone

    def test_the_row_puts_a_fire_out_and_one_left_alone_burns_out(self):
        for rows, wet in ((self.shown, 1), (self.alone, 0)):
            by_crater = {}
            for k, x, burning, *_, hosed, _ in rows:
                by_crater.setdefault(x, []).append((burning, hosed))
            self.assertTrue(any((1, wet) in b and (0, wet) in b[b.index((1, wet)):] for b in by_crater.values()))

    def test_in_every_frame_each_burning_crater_s_flame_comes_out_of_it(self):
        burning = [r for r in self.rows if r[2]]
        self.assertTrue(burning)
        for k, x, _, _, low, _, top, _, _ in burning:
            with self.subTest(frame=k, crater=x):
                self.assertGreaterEqual(low, top - TOUCH_PX)

    def test_a_hosed_fire_s_flame_is_one_piece_from_its_crater_up(self):
        hosed = [r for r in self.rows if r[2] and r[7]]
        self.assertTrue(hosed)
        for k, x, *_, apart in hosed:
            with self.subTest(frame=k, crater=x):
                self.assertLessEqual(apart, SPARKS_PX)

    def test_once_a_fire_is_out_no_flame_floats_on_over_its_crater(self):
        for k, x, burning, near, _, n, *_ in self.rows:
            if not burning and not near:
                with self.subTest(frame=k, crater=x):
                    self.assertLessEqual(n, SPARKS_PX)


if __name__ == "__main__":
    unittest.main()
