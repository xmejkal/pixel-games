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

import arcade  # noqa: E402
import gfx  # noqa: E402
from arcade import Flip, Meals, Slide, Snake, StatusBar, Trail  # noqa: E402

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
    game.last = 0  # the frame clock's ms, for the effects
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



class Drawn:
    """arcade.pictures.draw logged: each picture's (name, x, y, alpha), and a canvas that takes pictures."""

    pictures = True

    def __init__(self, test):
        self.calls, saved = [], arcade.pictures.draw
        arcade.pictures.draw = lambda cv, name, x, y, alpha=255: self.calls.append((name, x, y, alpha)) or True
        test.addCleanup(setattr, arcade.pictures, "draw", saved)

    def fill(self, *args):
        pass

    def named(self, prefix):
        return [c for c in self.calls if c[0].startswith(prefix)]


def painted(game, drawn):
    drawn.calls.clear()
    game.paint(drawn)
    return drawn


def fed():
    """A game in play on the frame clock that has just eaten: (game, now). The dot was one cell ahead."""
    random.seed(4)
    game, now = Snake(), FRAME_MS
    game.step(now, True, True)
    game.covers = True
    game.food = (13, 9)
    while game.score == 0:
        now += FRAME_MS
        game.step(now, False, False)
    return game, now


class FeelTest(unittest.TestCase):
    """The look's feel (P573): the head's slide and poses, the tail's slide, the bulge, the ripple, the dot's pulse
    and ping, the flip and the card, and the status bar's battery."""

    def test_the_slide_eases_out_in_60_ms_and_never_passes_the_cell(self):
        eased = [Slide.eased(ms) for ms in range(0, 200, 10)]
        self.assertEqual(0, eased[0])
        self.assertEqual([256] * 14, eased[6:])  # all the way from SLIDE_MS on
        self.assertEqual(sorted(eased), eased)
        self.assertGreater(eased[1] - eased[0], eased[5] - eased[4])  # fast at first, slow into the cell
        self.assertEqual(60, Slide.SLIDE_MS)
        self.assertEqual(100 + 12 * 128 // 256, Slide.at(100, 112, 128, 12))
        self.assertEqual(4, Slide.at(304, 4, 128, 12))  # across a wrap: at the new cell

    def test_the_head_slides_from_its_last_cell_into_its_new_one_each_step(self):
        game, now = fed()
        drawn = Drawn(self)
        xs = []
        for _ in range(8):
            now += FRAME_MS
            game.step(now, False, False)
            name, x, y, alpha = painted(game, drawn).named("snake_head_")[0]
            last, new = game.x_of(game.body[1]) - 2, game.x_of(game.body[0]) - 2
            self.assertTrue(last <= x <= new, (last, x, new))
            self.assertEqual(new if game.acc >= Slide.SLIDE_MS else x, x)
            xs.append(x)
        self.assertGreater(len(set(xs)), 4)  # it moves on frames between the steps, not only at them

    def test_the_head_gulps_then_chews_then_glows_near_a_dot_else_is_open(self):
        game, now = fed()
        self.assertEqual(Snake.GULP, game.head_pose())
        steps = game.steps
        while game.steps == steps:
            now += FRAME_MS
            game.step(now, False, False)
        self.assertEqual(Snake.CHEW, game.head_pose())
        while game.steps == steps + 1:
            now += FRAME_MS
            game.step(now, False, False)
        hx, hy = game.body[0]
        game.food = ((hx + 2) % Snake.COLS, hy)
        self.assertEqual(Snake.GLOW, game.head_pose())
        game.food = ((hx + 3) % Snake.COLS, hy)
        self.assertEqual(Snake.OPEN, game.head_pose())

    def test_the_tail_tile_slides_into_the_tail_while_the_head_slides_then_goes(self):
        game = playing()
        game.covers, game.last = True, 0
        game.play(False, False)  # a step: the tail at (10, 9) goes
        self.assertEqual((10, 9), game.gone)
        drawn = Drawn(self)
        tail = game.x_of(game.body[-1])
        for acc, on in ((0.0, True), (30.0, True), (60.0, False)):
            game.acc = acc
            first = painted(game, drawn).named("snake_tile_")[0]
            with self.subTest(acc=acc):
                if on:  # the popped tile, Slide.eased(acc) of the way into the tail's cell, first, under the feed
                    self.assertEqual(Slide.at(game.x_of((10, 9)), tail, Slide.eased(int(acc)), 12), first[1])
                    self.assertEqual(arcade.TILES[(game.made - len(game.body)) % 12], first[0])
                    self.assertEqual(len(game.body) - 1 + 1, len(drawn.named("snake_tile_")))
                else:
                    self.assertEqual(len(game.body) - 1, len(drawn.named("snake_tile_")))
        self.assertGreater(Slide.at(game.x_of((10, 9)), tail, Slide.eased(30), 12), game.x_of((10, 9)))

    def test_a_bulge_goes_down_the_feed_one_tile_a_step_and_the_glass_ripples_four_rings(self):
        game, now = fed()
        drawn = Drawn(self)
        meal, rings = game.steps, []
        for _ in range(40):  # 10 steps: past the tail of the 4-tile feed
            now += FRAME_MS
            game.step(now, False, False)
            painted(game, drawn)
            bulges = drawn.named("snake_bulge_")
            i = game.steps - meal
            if len(game.body) > i > 1 or (i == 1 and game.acc >= Slide.SLIDE_MS):
                self.assertEqual([(arcade.BULGES[i % 2], game.x_of(game.body[i]) - 2, game.y_of(game.body[i]) - 2,
                                   255)], bulges)
            else:
                self.assertEqual([], bulges)
            rings += [c[0] for c in drawn.named("snake_ripple_")]
        self.assertEqual(list(arcade.RIPPLES), sorted(set(rings)))
        self.assertLessEqual(len(rings), 4 * -(-Meals.RIPPLE_MS // FRAME_MS))  # four rings, RIPPLE_MS each, then none

    def test_the_dot_pulses_and_pings(self):
        game = playing()
        game.covers = True
        drawn = Drawn(self)
        dots, pings = [], []
        for t in range(0, 2400, FRAME_MS):
            game.last = t
            painted(game, drawn)
            (name, x, y, _), = drawn.named("snake_dot_")
            self.assertEqual((game.x_of(game.food), game.y_of(game.food)), (x, y))
            dots.append(name[-1])
            pings.append(drawn.named("snake_ping_"))
        self.assertEqual("0000111122221111", "".join(dots[:16]))  # 160 ms a pose, out and back
        rang = [t * FRAME_MS for t, p in enumerate(pings) if p]
        self.assertEqual([0, 40, 80, 120, 160, 200, 1200, 1240, 1280, 1320, 1360, 1400], rang)  # 3 rings of 80 ms

    def test_the_flip_holds_the_bite_then_turns_head_to_tail_to_seen_inside_the_over_window(self):
        self.assertLessEqual(Flip.END_MS - Flip.HOLD_MS, 600)
        self.assertLess(Flip.END_MS, Snake.CARD_MS)
        self.assertLess(Snake.CARD_MS, Snake.OVER_MS)
        for n in (3, 10, 40, 300):
            starts = [next(ms for ms in range(5000) if Flip.pose(i, n, ms) == 0) for i in range(n)]
            seen = [next(ms for ms in range(5000) if Flip.pose(i, n, ms) == 3) for i in range(n)]
            with self.subTest(n=n):
                self.assertEqual(Flip.HOLD_MS, starts[0])  # the head first, after the bite
                self.assertEqual(sorted(starts), starts)  # head to tail
                self.assertEqual(min(30, Flip.LAST_MS // (n - 1)), starts[1] - starts[0])  # 30 ms a tile, less when long
                self.assertLessEqual(max(seen), Flip.END_MS)

    def test_over_the_head_bites_then_flips_and_the_card_comes_after(self):
        game = playing()
        game.covers = True
        game.play(False, False)
        game.state, game.since = gfx.OVER, 1000
        drawn = Drawn(self)
        turn = arcade.TURNS[game.made % 12]  # the head's tile number is made
        for ms, head, seen in ((0, "snake_head_r_chew", 0), (Flip.HOLD_MS, turn, 0),
                               (Flip.HOLD_MS + Flip.POSE_MS, "snake_seen_1", 1),
                               (Flip.HOLD_MS + 2 * Flip.POSE_MS, "snake_seen_0", 2), (Flip.END_MS, "snake_seen_2", 3)):
            game.last = 1000 + ms
            painted(game, drawn)
            with self.subTest(ms=ms):
                self.assertIn(head, [c[0] for c in drawn.calls])
                self.assertEqual(seen, len(drawn.named("snake_seen_")))
                self.assertEqual(ms < Flip.HOLD_MS, bool(drawn.named("snake_bite_")))  # the bite's flash in the hold
                lights = [c for c in drawn.named("snake_glow_") if c[3] == Snake.GLOW_ALPHA]
                self.assertEqual(ms < Flip.HOLD_MS + 2 * Flip.STAGGER_MS, bool(lights))  # out as each lit tile turns
                self.assertEqual([], drawn.named("snake_dot_"))
            drawn.calls.clear()
            game.age = ms
            game.draw_over(drawn)
            self.assertEqual(ms >= Snake.CARD_MS, "snake_over" in [c[0] for c in drawn.calls])

    def test_the_battery_drains_as_the_feed_grows(self):
        self.assertEqual([18, 18, 17, 9, 1, 1], [StatusBar.charge(s) for s in (0, 1, 2, 18, 34, 90)])
        for score, width, colour in ((0, 18, StatusBar.BONE), (18, 9, StatusBar.BONE), (26, 5, gfx.ACCENT),
                                     (90, 1, gfx.ACCENT)):
            bar = Bar()
            StatusBar.draw(bar, score, score)
            with self.subTest(score=score):
                self.assertIn((282, 6, width, 5, colour), bar.fills)  # the charge drawn, its colour low in the accent

    def test_the_score_bar_is_the_status_bar_where_there_is_art(self):
        game = playing()
        game.covers, game.score = True, 7
        bar = Bar()
        game.draw_hud(bar)
        self.assertIn((112, 0, 96, 13, gfx.BLACK), bar.fills)  # the notch, not Game's score bar
        self.assertIn(("7", 143, 3), bar.texts)
        self.assertIn(("10:00", 10, 4), bar.texts)

    def test_the_head_faces_each_of_the_four_ways(self):
        drawn = Drawn(self)
        for d, way in enumerate("rdlu"):
            game = playing(d=d)
            game.covers, game.acc = True, 100.0
            game.food = (0, 0)
            with self.subTest(way=way):
                self.assertEqual("snake_head_%s_open" % way, painted(game, drawn).named("snake_head_")[0][0])

    def test_a_tile_keeps_its_kind_as_the_feed_crawls(self):
        game = playing()
        game.covers, game.last = True, 0
        drawn = Drawn(self)
        game.acc = 100.0
        before = {(c[1], c[2]): c[0] for c in painted(game, drawn).named("snake_tile_")}
        game.acc = 1000.0
        game.play(False, False)  # a step, no meal
        game.acc = 100.0
        after = {(c[1], c[2]): c[0] for c in painted(game, drawn).named("snake_tile_")}
        shared = set(before) & set(after)
        self.assertTrue(shared)
        self.assertEqual({k: before[k] for k in shared}, {k: after[k] for k in shared})
        self.assertGreater(len(set(after.values())), 1)  # and not every tile the same

    def test_the_halo_is_brighter_when_a_dot_is_near(self):
        drawn = Drawn(self)
        for food, alpha in (((14, 9), Snake.HALO_NEAR_ALPHA), ((20, 3), Snake.HALO_ALPHA)):
            game = playing(food=food)
            game.covers, game.acc, game.steps = True, 100.0, 5
            with self.subTest(food=food):
                self.assertEqual(alpha, painted(game, drawn).named("snake_halo")[0][3])
        self.assertGreater(Snake.HALO_NEAR_ALPHA, Snake.HALO_ALPHA)

    def test_a_meal_throws_bone_sparks_that_are_drawn(self):
        game, now = fed()
        drawn = Drawn(self)
        fills = []
        drawn.fill = lambda x, y, w, h, c: fills.append(c)
        painted(game, drawn)
        self.assertEqual(Snake.SPARKS, fills.count(Snake.BONE))
        self.assertEqual(7, len(game.fx.p))  # the rules' pop stays apart

    def test_the_card_writes_the_score(self):
        game = playing()
        game.covers, game.score = True, 7
        game.body = game.body * 4  # 12 long: the card must not count the tiles
        game.state, game.since, game.last, game.age = gfx.OVER, 0, Snake.CARD_MS, Snake.CARD_MS
        drawn = Drawn(self)
        game.draw_over(drawn)
        self.assertEqual(["snake_digit_7"], [c[0] for c in drawn.named("snake_digit_")])

    def test_the_feed_lights_the_glass_and_leaves_a_fading_trail(self):
        game = playing()
        game.covers, game.last, game.made = True, 0, 4  # the tail's tile is number 4 - 2: even, so lit
        game.play(False, False)  # a step: the tail's cell goes into the trail
        drawn = Drawn(self)
        glows = painted(game, drawn).named("snake_glow_")
        half = Snake.GLOW_PX // 2 - 6
        lit = [i for i in range(1, len(game.body)) if (game.made - i) % 2 == 0]  # every other tile, by its number
        self.assertTrue(lit)
        under = [(arcade.GLOWS[(game.made - i) % 12], game.x_of(game.body[i]) - half, game.y_of(game.body[i]) - half)
                 for i in lit]
        self.assertEqual(under, [(name, x, y) for name, x, y, a in glows if a == Snake.GLOW_ALPHA])
        trail = [g for g in glows if g[3] != Snake.GLOW_ALPHA]
        self.assertEqual([(game.x_of((10, 9)) - half, game.y_of((10, 9)) - half, Trail.ALPHA)],
                         [g[1:] for g in trail])  # the tail's lit tile left its light
        fades = []
        for t in (300, 600, Trail.FADE_MS):
            game.last = t
            fades.append([g[3] for g in painted(game, drawn).named("snake_glow_") if g[3] != Snake.GLOW_ALPHA])
        self.assertEqual([[Trail.ALPHA * 2 // 3], [Trail.ALPHA // 3], []], fades)

    def test_the_bite_kicks_the_feed_in_the_hold(self):
        self.assertEqual([3, 3, -3, -3, 2, 2, 0], [Flip.kick(ms) for ms in range(0, 140, 20)])
        game = playing()
        game.covers = True
        game.play(False, False)
        game.state, game.since = gfx.OVER, 1000
        drawn = Drawn(self)
        for ms in (0, 40, 80, Flip.HOLD_MS):
            game.last = 1000 + ms
            tiles = painted(game, drawn).named("snake_tile_")
            with self.subTest(ms=ms):
                self.assertEqual([game.x_of(c) + Flip.kick(ms) for c in game.body[1:]], [t[1] for t in tiles])


class Bar:
    """A canvas for the score bar: its fills and its texts."""

    def __init__(self):
        self.fills, self.texts = [], []

    def fill(self, x, y, w, h, c):
        self.fills.append((x, y, w, h, c))

    def box(self, x, y, w, h, c):
        pass

    def text(self, words, x, y, c):
        self.texts.append((words, x, y))


class Heard:
    """signals.Signals as the game box gives it: the names emitted, in order."""

    def __init__(self):
        self.names = []

    def emit(self, name, value=None):
        self.names.append(name)


class SoundTest(unittest.TestCase):
    def test_a_turn_steps_a_meal_picks_up_and_the_bite_dies(self):
        self.assertEqual({"eat": "pickup", "turn": "footstep", "die": "die"},
                         {k: c.sound for k, c in Snake.cues.items()})
        game = playing(food=(13, 9))
        game.signals = Heard()
        game.play(False, False)  # a meal
        game.play(True, True)  # a turn, down
        game.body = [(5, 5), (5, 6), (6, 6), (6, 5), (6, 4)]
        game.d = 1
        game.play(False, False)  # into its own body
        self.assertEqual(["eat", "turn", "die"], game.signals.names)


if __name__ == "__main__":
    unittest.main()
