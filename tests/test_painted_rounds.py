"""Meteors' and Bucket's painted effects do not move the games (P773, story 4): with the art loaded, two rounds drop
their meteors and crates where the flat games of 052d8f7 drop them; gfx.Dice never touches the game's random stream;
pictures.draw passes its alpha down to the driver's blit_buffer; and a new round of Meteors draws no impact's glow
before its first landing. The rounds run in their own process, as loading the art sets module state. Run from the
repository root: python3 -m unittest discover tests. --- MVP (P773) ---"""

import contextlib
import io
import json
import os
import random
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests", "stubs"))
sys.path.insert(0, os.path.join(ROOT, "games"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from test_fire import Tft  # noqa: E402  first: it gives time the ticks functions

import gfx  # noqa: E402
import lcd  # noqa: E402
import meteors as mt  # noqa: E402
import pictures  # noqa: E402
from test_meteors import FRAME_MS, idle, new_game, run, start  # noqa: E402

# The x of each drop in the first two rounds, as the flat games of 052d8f7 drop them on Python's bodies, frames of
# 42 ms: Meteors on seed 30 with a tap every 8 frames, Bucket on seed 5 held 20 frames and let go 20
BASE = {
    "meteors": [[24, 234, 284, 6, 262, 312, 0, 146], [0, 170]],
    "bucket": [[160, 220, 10, 290, 150, 100, 100, 180, 200, 200, 110, 300, 300, 110, 60, 230, 180, 150, 220, 160, 290,
                260, 90, 30, 20, 310, 210, 130, 240, 110, 310, 210, 110],
               [50, 310, 170, 230, 40, 220, 20, 260, 220, 110, 280, 100, 280, 110, 140, 70, 230, 20, 190, 60, 180, 210,
                180, 220]],
}

# Two rounds with the art loaded: the x of every drop (a body spawned above the screen), as JSON.
SCRIPT = r"""
import contextlib, io, json, random, sys, time
sys.path[:0] = ["tests/stubs", "games"]
time.ticks_diff, time.ticks_ms, time.ticks_us = (lambda a, b: a - b), (lambda: 0), (lambda: 0)
import gfx, pictures, plugins
pictures.ROOT = "games/"
assert pictures.load(), "no art"
name, seed, every = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
drops, done = [[], []], [0]
spawn = plugins.Bodies.spawn
def logged(self, i, x, y, *rest):
    if y < 0 and done[0] < 2:
        drops[done[0]].append(int(x))
    return spawn(self, i, x, y, *rest)
plugins.Bodies.spawn = logged
game = __import__(name)
random.seed(seed)
with contextlib.redirect_stdout(io.StringIO()):
    g = getattr(game, name.capitalize())()
    now, state = 0, g.state
    for k in range(20000):
        now += 42
        held = k % every == 0 if name == "meteors" else (k // every) % 2 == 0
        g.step(now, held and k % every == 0, held)
        if state == gfx.PLAY and g.state == gfx.OVER:
            done[0] += 1
            if done[0] == 2:
                break
        state = g.state
print(json.dumps(drops))
"""


def rounds(name, seed, every):
    run_ = subprocess.run([sys.executable, "-B", "-c", SCRIPT, name, str(seed), str(every)], cwd=ROOT,
                          capture_output=True, text=True)
    assert run_.returncode == 0, run_.stderr[-800:]
    return json.loads(run_.stdout.strip().split("\n")[-1])


class SameDropsTest(unittest.TestCase):
    def test_meteors_drops_where_the_flat_game_does_in_two_rounds(self):
        self.assertEqual(BASE["meteors"], rounds("meteors", 30, 8))

    def test_bucket_drops_where_the_flat_game_does_in_two_rounds(self):
        self.assertEqual(BASE["bucket"], rounds("bucket", 5, 20))


class DiceTest(unittest.TestCase):
    def test_dice_never_touch_the_games_random_stream(self):
        random.seed(773)
        state = random.getstate()
        dice = gfx.Dice()
        draws = [dice.below(10) for _ in range(50)] + [dice.spread(3) for _ in range(50)]
        self.assertEqual(state, random.getstate())
        self.assertTrue(all(0 <= v < 10 for v in draws[:50]) and all(-3 <= v <= 3 for v in draws[50:]))
        self.assertGreater(len(set(draws[:50])), 5)  # it varies
        again = gfx.Dice()
        self.assertEqual(draws[:50], [again.below(10) for _ in range(50)])  # the same seed, the same stream


class AlphaTest(unittest.TestCase):
    def test_pictures_draw_passes_its_alpha_to_the_drivers_blit(self):
        blits = []

        class Driver(Tft):
            def blit_buffer(self, *args):
                blits.append(args)

        cv = lcd.TftCanvas(Driver())
        pictures.PICS["test_alpha"] = (3, 2, memoryview(bytearray(12)))
        self.addCleanup(pictures.PICS.pop, "test_alpha")
        self.assertTrue(pictures.draw(cv, "test_alpha", 10, 20, 96))
        self.assertTrue(pictures.draw(cv, "test_alpha", 10, 20))
        self.assertEqual([96, 255], [args[5] for args in blits])  # blit_buffer(buf, x, y, w, h, alpha, key)


class NewRoundGlowTest(unittest.TestCase):
    def test_a_new_round_draws_no_glow_before_its_first_landing(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(773)
        game = new_game()
        game.art = True
        drawn = []

        def draw(cv, name, x, y, alpha=255):
            drawn.append(name)
            return True

        real = pictures.draw
        pictures.draw = draw
        self.addCleanup(setattr, pictures, "draw", real)
        now = start(game)
        now, _ = run(game, now, 2000, idle, FRAME_MS)  # round 1: meteors land, and the walker dies
        self.assertEqual(gfx.OVER, game.state)
        self.assertGreater(max(game.impact), 0)  # round 1 had its landings, late in its time
        now += 1000
        game.step(now, True, True)  # a tap starts round 2, its time from 0 again
        self.assertEqual(gfx.PLAY, game.state)

        class Canvas:
            pictures = True

            def fill(self, *args):
                pass

        landings = []
        burst = game.burst
        game.burst = lambda x: landings.append(x) or burst(x)
        for k in range(200):
            now += FRAME_MS
            game.step(now, False, False)
            if landings:  # round 2's first landing
                break
            del drawn[:]
            with contextlib.redirect_stdout(io.StringIO()):
                game.paint_impacts(Canvas())
            with self.subTest(frame=k):
                self.assertNotIn("meteors_glow", drawn)
        self.assertGreater(k, 10)  # frames were drawn before the landing


if __name__ == "__main__":
    unittest.main()
