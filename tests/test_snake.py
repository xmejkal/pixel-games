"""Snake's rules on the Mac (P573): a seeded trace of a round and named checks of the turn, the step's period, the
wrap, the self-collision and the meal. The restyle as FEED draws over these rules and must leave them as they are.
Run from the repository root: python3 -B -m unittest discover tests."""

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
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

import gfx  # noqa: E402
from arcade import Snake  # noqa: E402

FRAME_MS = 40  # app.py's FRAME_MS
SEED, FRAMES, EVERY = 2, 1000, 2  # the trace's seed, its length, and the bot's look: one frame in EVERY
CHECK_EVERY = 100  # a checkpoint each this many frames


def ahead(game, d):
    """The cell the head moves into going d."""
    (hx, hy), (dx, dy) = game.body[0], game.DIRS[d]
    return (hx + dx) % game.COLS, (hy + dy) % game.ROWS


def nearer(game, d):
    """Whether going d brings the head nearer the food, counted across the wrap."""
    def far(cell):
        ax, ay = abs(game.food[0] - cell[0]), abs(game.food[1] - cell[1])
        return min(ax, game.COLS - ax) + min(ay, game.ROWS - ay)
    return far(ahead(game, d)) < far(game.body[0])


def wants_turn(game):
    """The bot turns when the way ahead is blocked or leads no nearer the food, unless the right turn is blocked."""
    blocked = ahead(game, game.d) in game.body[:-1]
    return (blocked or not nearer(game, game.d)) and ahead(game, (game.d + 1) % 4) not in game.body[:-1]


def trace(seed=SEED, frames=FRAMES):
    """A round on the frame clock: the first frame taps, so play starts; then a bot that looks one frame in EVERY and
    turns at most once a step. Answers each meal and the death as (frame, what, score, head, food or length) and each
    CHECK_EVERY-th frame as (frame, state, score, direction, head, tail, length, food)."""
    random.seed(seed)
    game, now, events, checkpoints = Snake(), 0, [], []
    head, turned = None, False
    for k in range(frames):
        now += FRAME_MS
        score = game.score
        if game.body[0] != head:
            head, turned = game.body[0], False
        tap = k == 0 or (game.state == gfx.PLAY and k % EVERY == 0 and not turned and wants_turn(game))
        turned = turned or (tap and k > 0)
        game.step(now, tap, tap)
        if game.score != score:
            events.append((k, "eat", game.score, game.body[0], game.food))
        if k % CHECK_EVERY == 0:
            checkpoints.append((k, game.state, game.score, game.d, game.body[0], game.body[-1], len(game.body),
                                game.food))
        if game.state == gfx.OVER:
            events.append((k, "death", game.score, game.body[0], len(game.body)))
            break
    return events, checkpoints


# The trace on master 4088c42's rules: 15 meals, the period down from 160 ms to 100, several wraps, and the head
# turned into its own body at frame 845. The food after each meal is drawn after the meal's pop (7 sparks), so a pop
# with another count moves every later food.
EVENTS = (
    (80, "eat", 1, (1, 2), (12, 13)),
    (151, "eat", 2, (12, 13), (24, 12)),
    (223, "eat", 3, (24, 12), (15, 9)),
    (275, "eat", 4, (15, 9), (21, 3)),
    (318, "eat", 5, (21, 3), (0, 12)),
    (367, "eat", 6, (0, 12), (3, 0)),
    (431, "eat", 7, (3, 0), (1, 7)),
    (461, "eat", 8, (1, 7), (14, 14)),
    (564, "eat", 9, (14, 14), (11, 9)),
    (588, "eat", 10, (11, 9), (14, 4)),
    (612, "eat", 11, (14, 4), (25, 13)),
    (670, "eat", 12, (25, 13), (4, 9)),
    (718, "eat", 13, (4, 9), (14, 14)),
    (802, "eat", 14, (14, 14), (12, 0)),
    (817, "eat", 15, (12, 0), (21, 13)),
    (845, "death", 15, (13, 17), 18),
)
CHECKPOINTS = (
    (0, 1, 0, 0, (12, 9), (10, 9), 3, (1, 2)),
    (100, 1, 1, 3, (1, 15), (1, 0), 4, (12, 13)),
    (200, 1, 2, 1, (24, 14), (21, 13), 5, (24, 12)),
    (300, 1, 4, 0, (16, 3), (15, 8), 7, (21, 3)),
    (400, 1, 6, 3, (25, 16), (0, 13), 9, (3, 0)),
    (500, 1, 8, 2, (15, 7), (25, 7), 11, (14, 14)),
    (600, 1, 10, 3, (11, 5), (14, 14), 13, (14, 4)),
    (700, 1, 12, 0, (0, 6), (25, 9), 15, (4, 9)),
    (800, 1, 13, 1, (14, 13), (5, 7), 16, (14, 14)),
)


def playing(body=((12, 9), (11, 9), (10, 9)), d=0, food=(0, 0)):
    """A game in play, its frame 40 ms long, its step due on the next play."""
    game = Snake()
    game.state, game.dt = gfx.PLAY, FRAME_MS / 1000
    game.body, game.d, game.food = list(body), d, food
    game.acc = 1000.0
    return game


class TraceTest(unittest.TestCase):
    def test_the_seeded_round_is_as_pinned(self):
        events, checkpoints = trace()
        self.assertEqual(EVENTS, tuple(events))
        self.assertEqual(CHECKPOINTS, tuple(checkpoints))


class RulesTest(unittest.TestCase):
    def test_a_tap_turns_right_and_four_taps_go_round(self):
        game = playing()
        moves = []
        for _ in range(4):
            game.play(True, True)
            moves.append(game.DIRS[game.d])
        self.assertEqual([(0, 1), (-1, 0), (0, -1), (1, 0)], moves)  # down, left, up, right: clockwise on the screen
        game = playing()
        game.play(True, True)
        self.assertEqual((12, 10), game.body[0])  # the turn counts in the step of the tap

    def test_the_step_comes_each_160_ms_less_4_a_point_and_never_under_70(self):
        for score, period in ((0, 160), (10, 120), (22, 72), (23, 70), (40, 70)):
            game = playing()
            game.score, game.acc = score, 0.0
            game.dt = 0.001
            ms = 0
            while game.body[0] == (12, 9):
                game.play(False, False)
                ms += 1
            with self.subTest(score=score):
                self.assertEqual(period, ms)
                self.assertAlmostEqual(0.0, game.acc)  # the rest is kept for the next step

    def test_the_head_wraps_at_every_edge(self):
        for head, d, after in (((25, 5), 0, (0, 5)), ((5, 17), 1, (5, 0)), ((0, 5), 2, (25, 5)), ((5, 0), 3, (5, 17))):
            game = playing(body=(head,), d=d, food=(20, 3))
            game.play(False, False)
            with self.subTest(head=head, d=d):
                self.assertEqual([after], game.body)

    def test_the_head_into_its_body_ends_the_round_but_into_the_tail_it_does_not(self):
        ring = ((5, 5), (5, 6), (6, 6), (6, 5))  # the head at (5, 5) going down meets (5, 6)
        game = playing(body=ring, d=1, food=(20, 3))
        game.play(False, False)
        self.assertEqual(gfx.OVER, game.state)
        self.assertEqual(24, len(game.fx.p))  # the death's two bursts, 14 and 10
        self.assertEqual(list(ring), game.body)  # the body stays where it was
        game = playing(body=ring, d=0, food=(20, 3))  # going right meets (6, 5), the tail, which moves away
        game.play(False, False)
        self.assertEqual(gfx.PLAY, game.state)
        self.assertEqual([(6, 5), (5, 5), (5, 6), (6, 6)], game.body)

    def test_a_meal_grows_the_body_scores_pops_and_puts_the_food_off_the_body(self):
        random.seed(4)
        game = playing(food=(13, 9))
        game.play(False, False)
        self.assertEqual(1, game.score)
        self.assertEqual([(13, 9), (12, 9), (11, 9), (10, 9)], game.body)
        self.assertEqual(7, len(game.fx.p))  # the pop: 7 sparks
        self.assertNotIn(game.food, game.body)
        game.play(False, False)
        self.assertEqual(4, len(game.body))  # no meal: the tail goes as the head comes


if __name__ == "__main__":
    unittest.main()
