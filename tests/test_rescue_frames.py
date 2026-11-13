"""Rescue's fires in the frames of render_scene's rescue row and of a round left alone, where a fire burns out by
itself (P800): in every frame each burning crater's flame comes out of that crater, a hosed fire's flame is one piece
from the crater up, and once a fire is out no flame floats on over its crater. Two planted rounds (P803) end one fire
beside another that burns on: a near one keeps one flame from its crater up and nothing floats over the dead crater,
and a far one's flame in the frame the other ends is the same as in the round where the other burns on. Each row runs
in its own process, as tools/render_scene.py sets module state (the clock, the engines). Needs clang. Run from the
repository root: python3 -m unittest discover tests. --- MVP (P800) ---"""

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
# --- MVP (P803) --- two craters planted at frame PLANT_K with no meteor and nobody coming: the second fire ends after
# END_MS (frame END_K), the first burns on. NEAR is 15 cells apart, so its heat reaches the dead crater's columns; FAR
# is 40 cells apart, out of its reach
PLANT_K, END_MS, PLANT_LAST = 5, 2000, 110
END_K = PLANT_K + END_MS // 40
NEAR = (PLANT_K, ((180, 6000), (150, END_MS)))
FAR = (PLANT_K, ((200, 6000), (120, END_MS)))
FAR_ON = (PLANT_K, ((200, 6000), (120, 6000)))  # the same round, where the second fire burns on
# One line per crater and frame: the frame, the crater's x, whether its fire burns, whether a burning crater is within
# APART_PX of a dead one, the lowest bright row in its columns (-1: none), how many bright pixels there (sparks
# included), the crater's top row, whether it was hosed, the flame pixels above the first run of more than GAP_PX rows
# with no flame up from the crater (a "help!" plate over the flame counts as flame), and its flame pixels (P803). A
# bright pixel is bright orange to yellow and differs from the still street; a flame pixel is a bright pixel not of a
# spark's colour (sparks fly free of the flame).
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
presses, last, plant = eval(sys.argv[1]), int(sys.argv[2]), eval(sys.argv[3])
if presses:
    row.presses, row.last = presses, last
made, make = [], row.game
row.game = lambda: made.append(make()) or made[-1]
spark = None
for k, img in enumerate(itertools.islice(rs.frames(row), row.last)):
    rules = made[0].rules
    if plant and k == plant[0]:  # P803: the planted craters, in order, and nothing else comes
        rules.meteor_ms = rules.come_ms = 10 ** 9
        for x, left_ms in plant[1]:
            rules.craters.append(rescue.Crater(x))
            rules.craters[-1].left_ms = left_ms
    craters = rules.craters
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
              apart, sum(rows.values()))
""" % (APART_PX, GAP_PX)


def run_row(presses=None, last=0, plant=None):
    run = subprocess.run([sys.executable, "-B", "-c", SCRIPT, repr(presses), str(last), repr(plant)], cwd=ROOT,
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
            for k, x, burning, *_, hosed, _, _ in rows:
                by_crater.setdefault(x, []).append((burning, hosed))
            self.assertTrue(any((1, wet) in b and (0, wet) in b[b.index((1, wet)):] for b in by_crater.values()))

    def test_in_every_frame_each_burning_crater_s_flame_comes_out_of_it(self):
        burning = [r for r in self.rows if r[2]]
        self.assertTrue(burning)
        for k, x, _, _, low, _, top, *_ in burning:
            with self.subTest(frame=k, crater=x):
                self.assertGreaterEqual(low, top - TOUCH_PX)

    def test_a_hosed_fire_s_flame_is_one_piece_from_its_crater_up(self):
        hosed = [r for r in self.rows if r[2] and r[7]]
        self.assertTrue(hosed)
        for k, x, *_, apart, _ in hosed:
            with self.subTest(frame=k, crater=x):
                self.assertLessEqual(apart, SPARKS_PX)

    def test_once_a_fire_is_out_no_flame_floats_on_over_its_crater(self):
        for k, x, burning, near, _, n, *_ in self.rows:
            if not burning and not near:
                with self.subTest(frame=k, crater=x):
                    self.assertLessEqual(n, SPARKS_PX)


# --- MVP (P803) ---
@unittest.skipUnless(shutil.which("clang"), "clang is missing: the C heat field is not built")
class FireEndsBesideAnotherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.near = run_row(ALONE, PLANT_LAST, NEAR)
        cls.far, cls.far_on = run_row(ALONE, PLANT_LAST, FAR), run_row(ALONE, END_K + 1, FAR_ON)

    def test_the_planted_fire_ends_at_end_k_and_the_other_burns_on(self):
        for rows, (on_x, _), (end_x, _) in ((self.near, *NEAR[1]), (self.far, *FAR[1])):
            burning = {(k, x): b for k, x, b, *_ in rows}
            self.assertEqual((1, 1, 0, 1), (burning[END_K - 1, end_x], burning[END_K - 1, on_x], burning[END_K, end_x],
                                            burning[PLANT_LAST - 1, on_x]))

    def test_near_a_fire_that_burns_on_nothing_floats_over_the_dead_crater(self):
        end_x = NEAR[1][1][0]
        dead = [r for r in self.near if r[1] == end_x and not r[2]]
        self.assertTrue(dead and all(r[3] for r in dead))  # a burning crater is near in every frame
        for k, *_, flame in dead:  # its own sparks fly on: a burning crater within SPARK_PX keeps them
            with self.subTest(frame=k):
                self.assertLessEqual(flame, SPARKS_PX)

    def test_the_near_fire_keeps_one_flame_from_its_crater_up(self):
        on_x = NEAR[1][0][0]
        for k, x, burning, *_, apart, _ in self.near:
            if x == on_x and k >= END_K:
                with self.subTest(frame=k):
                    self.assertLessEqual(apart, SPARKS_PX)

    def test_the_far_fire_s_flame_is_untouched_in_the_frame_the_other_ends(self):
        """Its crater comes first, so its random draws in that frame are the same in both rounds."""
        on_x = FAR[1][0][0]
        n = [{k: n for k, x, _, _, _, n, *_ in rows if x == on_x} for rows in (self.far, self.far_on)]
        self.assertEqual(n[1][END_K - 1], n[0][END_K - 1])  # the rounds are one up to the end
        self.assertEqual(n[1][END_K], n[0][END_K])


if __name__ == "__main__":
    unittest.main()
