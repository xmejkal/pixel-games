"""RENT (arcade2.Stack) on the Mac: the slabs and the collapse's pile. framebuf comes from tests/stubs and time gets the two MicroPython
ticks functions, so gfx imports here; the paint is recorded on a canvas of plain calls. Run from the repository root:
python3 -m unittest discover tests."""

import os
import random
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)

from arcade2 import Pile, Stack, pile_plane  # noqa: E402
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

    def box(self, *args):
        pass

    def big(self, *args):
        pass

    def text(self, *args):
        pass


def block_tops(game):
    """The top y of every floor and slab one paint draws."""
    tops, block = [], game.block
    game.block = lambda cv, x, y, w, i, lit: tops.append(y) or block(cv, x, y, w, i, lit)
    try:
        game.paint(Recorder())
    finally:
        del game.block
    return tops


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
            self.assertFalse([y for y in block_tops(game) if y >= H])


def tower(seed, n=14):
    """A game over with n floors standing as a round leaves them: each lands near the one under it, cut narrower."""
    rnd = random.Random(seed)
    game = playing()
    game.wreck = Pile(n, game.LEVEL_H, game.BASE)
    x, w = 90.0, 140
    for i in range(n):
        game.wreck.add(x, game.BASE - (i + 1) * game.LEVEL_H, w, i)
        off = rnd.randint(-6, 6)
        x, w = x + max(0, off), max(30, w - abs(off))
    game.state, game.age, game.lean = OVER, 0, rnd.choice((-1, 1))
    return game


def collapse(game, dt, seconds):
    """Run the collapse for seconds at dt; after each step, the wreck's bodies and when each floor was released."""
    released, ms = {}, 0
    for _ in range(int(round(seconds / dt))):
        ms += int(dt * 1000)
        game.age = ms
        before = game.released
        game.collapse(dt)
        for r in range(before, game.released):
            released[game.wreck.count - 1 - r] = ms
        yield game.wreck.bodies, released


class PileTest(unittest.TestCase):

    def test_the_rule(self):
        x, y, w = [0.0, 0.0, 100.0, 0.0], [100.0, 50.0, 80.0, 20.0], [50, 50, 50, 50]
        rest_y, live = [100.0, 50.0, 80.0, 20.0], [1, 1, 1, 1]
        self.assertEqual(pile_plane(1, x, y, w, rest_y, live, 200, 14, 8), (86.0, 0))  # floor 2 does not overlap
        rest_y[0] = 150.0  # floor 0 falls: floor 1 lands where floor 0 will stop
        self.assertEqual(pile_plane(1, x, y, w, rest_y, live, 200, 14, 8), (136.0, 0))
        x[1] = 43.0  # 7 px over floor 0: too little
        self.assertEqual(pile_plane(1, x, y, w, rest_y, live, 200, 14, 8), (200, -1))
        self.assertEqual(pile_plane(0, x, y, w, rest_y, live, 200, 14, 8), (200, -1))  # floor 3 is above it
        y[1] = 210.0
        self.assertEqual(pile_plane(1, x, y, w, rest_y, live, 200, 14, 8), (210.0, -1))  # never above where it is

    def test_all_asleep_by_1_4_s(self):
        for dt in (0.04, 0.06):
            for seed in range(8):
                with self.subTest(dt=dt, seed=seed):
                    game = tower(seed)
                    for _ in collapse(game, dt, 1.4):
                        pass
                    self.assertEqual(game.released, 14)
                    self.assertTrue(game.wreck.still())
                    for b, _ in collapse(game, dt, 1.0):  # and it stays at rest
                        self.assertTrue(game.wreck.still())

    def test_none_below_its_plane(self):
        for dt in (0.04, 0.06):
            for seed in range(8):
                with self.subTest(dt=dt, seed=seed):
                    game = tower(seed)
                    for b, _ in collapse(game, dt, 1.4):
                        for j in range(game.wreck.count):
                            self.assertLessEqual(b.y[j], b.rest_y[j])
                            self.assertLessEqual(b.y[j], game.BASE)

    def test_top_down_and_the_street_floor_last(self):
        game = tower(0)
        for _, released in collapse(game, 0.04, 1.4):
            pass
        self.assertEqual(len(released), 14)
        order = sorted(released, key=lambda j: (released[j], -j))
        self.assertEqual(order, list(range(13, -1, -1)))
        self.assertGreater(released[0], released[1])

    def test_every_floor_falls(self):
        """Each floor ends lower than it stood: the street floor drops onto the street, and the rest with it."""
        for seed in range(8):
            with self.subTest(seed=seed):
                game = tower(seed)
                start = list(game.wreck.bodies.y)
                for b, _ in collapse(game, 0.04, 1.4):
                    pass
                for j in range(14):
                    self.assertTrue(not b.live[j] or b.y[j] > start[j], j)

    def test_no_floor_ends_inside_another(self):
        for dt in (0.04, 0.06):
            for seed in range(8):
                with self.subTest(dt=dt, seed=seed):
                    game = tower(seed)
                    for b, _ in collapse(game, dt, 1.4):
                        pass
                    w, h = game.wreck.w, game.LEVEL_H
                    for i in range(14):
                        for j in range(i):
                            if b.live[i] and b.live[j]:
                                across = min(b.x[i] + w[i], b.x[j] + w[j]) - max(b.x[i], b.x[j])
                                self.assertFalse(across > 0 and abs(b.y[i] - b.y[j]) < h, (i, j))

    def test_hits_are_throttled(self):
        game = tower(3)
        hits = []
        game.collapse_hit = lambda x, y, speed: hits.append(game.age)
        for _ in collapse(game, 0.04, 1.4):
            pass
        self.assertTrue(hits)
        self.assertTrue(all(b - a >= game.HIT_MS for a, b in zip(hits, hits[1:])))

    def test_the_wreck_draws_nothing_below_the_screen(self):
        game = tower(1)
        for _ in collapse(game, 0.04, 2.0):
            self.assertFalse([y for y in block_tops(game) if y >= H])


if __name__ == "__main__":
    unittest.main()
