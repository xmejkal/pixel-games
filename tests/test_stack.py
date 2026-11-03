"""RENT (arcade2.Stack) on the Mac: the slabs. framebuf comes from tests/stubs and time gets the two MicroPython
ticks functions, so gfx imports here; the paint is recorded on a canvas of plain calls. Run from the repository root:
python3 -m unittest discover tests."""

import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)

from arcade2 import Stack  # noqa: E402
from gfx import OVER, PLAY  # noqa: E402

H = 240


class Recorder:
    """A canvas that keeps each fill as (x, y, w, h) and ignores the rest; pictures.draw answers False on it."""

    def __init__(self):
        self.fills = []

    def fill(self, x, y, w, h, c):
        self.fills.append((int(x), int(y), int(w), int(h)))

    def line(self, *args):
        pass

    def text(self, *args):
        pass


def playing(cls=Stack):
    game = cls()
    game.state, game.dt = PLAY, 0.04
    return game


class SlabTest(unittest.TestCase):

    def test_a_fifth_frees_the_oldest(self):
        game = playing()
        for k in range(5):
            game.cut_off(10 * k, 100, 20 + k, k, 40.0, 400.0)
        s = game.slabs
        self.assertEqual(sum(s.live), 4)
        self.assertEqual(sorted(game.slab_w), [21, 22, 23, 24])  # the first, 20 px wide, is gone

    def test_a_free_body_is_taken_before_the_oldest(self):
        game = playing()
        for k in range(4):
            game.cut_off(10 * k, 100, 20 + k, k, 40.0, 400.0)
        game.slabs.free(2)
        game.cut_off(0, 100, 30, 0, 40.0, 400.0)
        self.assertEqual(sorted(game.slab_w), [20, 21, 23, 30])

    def test_a_slab_bounces_then_sleeps_on_the_street(self):
        for dt in (0.04, 0.06):
            with self.subTest(dt=dt):
                game = playing()
                hits = []
                game.slab_hit = lambda x, y, speed: hits.append(speed)
                game.cut_off(100, 94, 30, 0, 40.0, 400.0)
                for _ in range(int(1.0 / dt)):
                    game.move_slabs(dt)
                    self.assertLessEqual(game.slabs.y[0], game.BASE)
                self.assertTrue(hits)
                self.assertEqual(game.slabs.asleep[0], 1)
                self.assertEqual(game.slabs.y[0], game.BASE)

    def test_a_slab_off_the_screen_is_freed(self):
        game = playing()
        game.cut_off(-25, 200, 20, 0, -40.0, 0.0)
        game.move_slabs(0.04)
        self.assertEqual(game.slabs.live[0], 0)

    def test_the_cot_lies_on_a_side_frame_at_rest(self):
        game = playing()
        game.cut_off(100, 200, 30, 0, 40.0, 400.0)
        for _ in range(40):
            game.move_slabs(0.04)
        self.assertEqual(game.slabs.asleep[0], 1)
        drawn = []
        import pictures
        draw = pictures.draw
        pictures.draw = lambda cv, name, x, y: drawn.append(name) or False
        try:
            game.paint(Recorder())
        finally:
            pictures.draw = draw
        cots = [n for n in drawn if n.startswith("stack_cot")]
        self.assertEqual(len(cots), 1)
        self.assertIn(cots[0], ("stack_cot1", "stack_cot3"))

    def test_nothing_drawn_below_the_screen(self):
        game = playing()
        for k in range(4):
            game.cut_off(40 * k, 100, 30, k, 40.0, 400.0)
        for _ in range(50):
            game.move_slabs(0.04)
            cv = Recorder()
            game.paint(cv)
            self.assertFalse([f for f in cv.fills if f[1] >= H])


if __name__ == "__main__":
    unittest.main()
