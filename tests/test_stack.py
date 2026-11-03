"""RENT (arcade2.Stack) on the Mac: the slabs, the collapse's pile and the bench bot (bench582.Bot). framebuf comes from tests/stubs and time gets the two MicroPython
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

import bench582  # noqa: E402
from arcade2 import Pile, Stack, pile_under  # noqa: E402
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


class PileTest(unittest.TestCase):
    """The wreck's pool on its own: a floor that release() lets go, the floors still standing, the street and the
    edge of the screen. RENT's wreck numbers: gravity 2000, restitution 0.25, friction 0.5, drag 4."""

    G, BOUNCE, FRICTION, DRAG, STREET = 2000.0, 0.25, 0.5, 4.0, 220

    def tower(self, n=3, x=90):
        pile = Pile(n, 14, self.STREET)
        for i in range(n):
            pile.add(x, self.STREET - 14 * (i + 1), 140, i)
        return pile

    def step(self, pile, dt=0.04):
        pile.step(dt, self.G, self.BOUNCE, self.FRICTION, self.DRAG)

    def test_a_released_floor_starts_falling_at_its_push(self):
        for dt in (0.04, 0.06):
            with self.subTest(dt=dt):
                pile = self.tower()
                b = pile.bodies
                x, y = b.x[2], b.y[2]
                pile.release(2, 150.0)
                self.step(pile, dt)
                self.assertAlmostEqual(b.vx[2], 150.0)
                self.assertAlmostEqual(b.x[2], x + 150.0 * dt)
                self.assertAlmostEqual(b.vy[2], self.G * dt)
                self.assertGreater(b.y[2], y)

    def test_a_standing_floor_stays_put(self):
        pile = self.tower()
        b = pile.bodies
        before = [(b.x[j], b.y[j]) for j in range(2)]
        pile.release(2, 150.0)
        for _ in range(50):
            self.step(pile)
            self.assertEqual([(b.x[j], b.y[j]) for j in range(2)], before)
        self.assertEqual(b.y[2], self.STREET)  # a standing floor holds nothing up: the released one reached the street

    def test_a_floor_bounces_on_the_street_then_sleeps(self):
        for dt in (0.04, 0.06):
            with self.subTest(dt=dt):
                pile = self.tower(1)
                b = pile.bodies
                b.y[0] = 60.0  # high over the street, so it lands hard enough to bounce
                pile.release(0, 0.0)
                bounces = 0
                for _ in range(int(2 / dt)):
                    self.step(pile, dt)
                    self.assertLessEqual(b.y[0], self.STREET)
                    if b.hit[0]:
                        bounces += 1
                        self.assertAlmostEqual(b.vy[0], -b.hit[0] * self.BOUNCE, delta=self.BOUNCE)
                self.assertGreaterEqual(bounces, 1)
                self.assertEqual((b.asleep[0], b.y[0]), (1, self.STREET))
                self.assertTrue(pile.still())

    def test_a_floor_thrown_off_the_screen_leaves_the_pool(self):
        pile = self.tower(2, x=W - 40)  # 40 px on the screen: a 300 px/s throw takes it all the way off
        b = pile.bodies
        pile.release(1, 300.0)
        for _ in range(50):
            self.step(pile)
            if not b.live[1]:
                break
        self.assertEqual(b.live[1], 0)
        self.assertEqual(b.live[0], 1)
        self.assertTrue(pile.still())  # what left the pool no longer holds the collapse open


def fallen(n, width, dt, lean=1):
    """A real round: n floors of width px by perfect drops through Stack's own release() and fall(), the press left to
    settle, then a miss on the lean side, played until the tower is over."""
    step = int(dt * 1000)
    game, now = playing(), 0
    game.floors, game.w = [(160 - width // 2, width)], width
    game.step(now, False, False)
    while len(game.floors) < n:
        if not game.drop and not game.hold:
            game.x = float(game.floor_x(len(game.floors) - 1))
            game.release()
        now += step
        game.step(now, False, False)
    for _ in range(15):
        now += step
        game.step(now, False, False)
    tx = game.floor_x(len(game.floors) - 1)
    game.x = float(tx + width + 5) if (lean > 0 and tx + 2 * width + 5 <= W) or tx < width + 5 else 0.0
    game.release()
    while game.state == PLAY:
        now += step
        game.step(now, False, False)
    return game, now


W = 320


class CollapseTest(unittest.TestCase):
    """The collapse of a real round, 12 floors at 140 and at 60 px, at dt 0.04 and 0.06: every floor above the street
    comes down (14 px lower or 20 px aside), the basement stays, no two floors of the wreck end inside each other,
    none below its plane or the street, all at rest within SETTLE_MS (1.44 s measured on the Mac)."""

    SETTLE_MS = 1500

    def each(self):
        for width in (140, 60):
            for dt in (0.04, 0.06):
                for lean in (1, -1):
                    yield width, dt, lean

    def test_the_tower_comes_down(self):
        for width, dt, lean in self.each():
            with self.subTest(width=width, dt=dt, lean=lean):
                game, now = fallen(12, width, dt, lean)
                wreck, low = game.wreck, game.basement
                b, n = wreck.bodies, wreck.count
                self.assertGreater(low, 0)  # 12 floors reach below the street
                x0, y0 = list(b.x[:n]), list(b.y[:n])
                still = None
                for k in range(int(2.0 / dt)):
                    now += int(dt * 1000)
                    game.step(now, False, False)
                    for j in range(n):
                        self.assertLessEqual(b.y[j], b.rest_y[j])
                        if j >= low:
                            self.assertLessEqual(b.y[j], game.BASE)
                    if still is None and game.collapsed():
                        still = (k + 1) * dt * 1000
                self.assertIsNotNone(still)
                self.assertLessEqual(still, self.SETTLE_MS)
                for j in range(n):
                    if j < low:
                        self.assertEqual((b.x[j], b.y[j]), (x0[j], y0[j]))
                    elif b.live[j]:
                        self.assertTrue(b.y[j] - y0[j] >= game.LEVEL_H or abs(b.x[j] - x0[j]) >= 20, j)
                for i in range(low, n):
                    for j in range(low, i):
                        if b.live[i] and b.live[j]:
                            across = min(b.x[i] + wreck.w[i], b.x[j] + wreck.w[j]) - max(b.x[i], b.x[j])
                            self.assertFalse(across > 0 and abs(b.y[i] - b.y[j]) < game.LEVEL_H, (i, j))

    def test_the_rule_keeps_the_tower_order(self):
        game, _ = fallen(5, 140, 0.04)
        wreck = game.wreck
        self.assertEqual(game.basement, 0)
        self.assertEqual(pile_under(wreck, 0), -1)  # nothing released: the street
        wreck.released[0] = wreck.released[3] = 1
        self.assertEqual(pile_under(wreck, 2), 0)  # floor 3 stood above it, so it holds nothing up
        self.assertEqual(pile_under(wreck, 0), -1)
        wreck.bodies.x[0] += 140 - 7  # 7 px of overlap: too little
        self.assertEqual(pile_under(wreck, 2), -1)

    def test_hits_are_throttled(self):
        game, now = fallen(12, 60, 0.04)
        hits = []
        game.collapse_hit = lambda x, y, speed: hits.append(game.age)
        for _ in range(50):
            now += 40
            game.step(now, False, False)
        self.assertTrue(hits)
        self.assertTrue(all(b - a >= game.HIT_MS for a, b in zip(hits, hits[1:])))

    def test_the_wreck_draws_nothing_below_the_screen(self):
        game, now = fallen(12, 140, 0.04)
        for _ in range(50):
            now += 40
            game.step(now, False, False)
            self.assertFalse([y for y in block_tops(game) if y >= H])


class BotTest(unittest.TestCase):

    def test_a_long_round_then_a_retry(self):
        """At the 40 ms pace, with Stack's own speed rule: 20 floors or more, then it taps itself into a new round."""
        game, now, rounds = playing(bench582.Bot), 0, []
        self.assertEqual(game.name, "stack")
        before = game.state
        for _ in range(8000):
            now += 40
            game.step(now, False, False)
            if before == PLAY and game.state == OVER:
                rounds.append(game.score)
            if before == OVER and game.state == PLAY:
                self.assertEqual(game.score, 0)
                break
            before = game.state
        self.assertEqual(len(rounds), 1)
        self.assertGreaterEqual(rounds[0], 20)
        self.assertEqual(game.state, PLAY)


if __name__ == "__main__":
    unittest.main()
