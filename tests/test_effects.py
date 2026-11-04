"""games/effects.py on the Mac (P607): a body carries an effect, the effect runs once a frame at its place, and an
event of the step can start one. The stepper and the field are stand-ins, so no C is built. Run from the repository
root: python3 -m unittest discover tests. --- MVP (P607) ---"""

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
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

from effects import EffectSystem, Effect, FireTrail, cell  # noqa: E402
from motion import HIT, SLEEP  # noqa: E402

SIZE, RADIUS, HEAT, LAG = 8, 3, 200, 0.5


class Stepper:
    """A stand-in for rain.Stepper: the test sets each body's top left corner and the events that events() drains."""

    def __init__(self, n):
        self.n, self.places, self.drained = n, [(0, -100)] * n, []

    def place(self, i):
        return self.places[i]

    def events(self):
        return len(self.drained) // 3


class Field:
    """A stand-in for engine.HeatField: it keeps each burn's arguments."""

    def __init__(self):
        self.burns = []

    def burn(self, *args):
        self.burns.append(args)


class Counter(Effect):
    """A second effect, as P608's blur will be: it only counts where it ran."""

    def __init__(self):
        self.places, self.forgot = [], 0

    def update(self, x, y):
        self.places.append((x, y))

    def reset(self):
        self.forgot += 1


class EffectsTest(unittest.TestCase):
    def setUp(self):
        self.stepper, self.field = Stepper(3), Field()
        self.effects = EffectSystem(self.stepper)

    def trail(self):
        return FireTrail(self.field, SIZE, RADIUS, HEAT, LAG)

    def test_a_body_with_fire_burns_once_a_frame_at_its_place(self):
        self.effects.bodies[1].effect = self.trail()
        self.stepper.places[1] = (100, 100)
        for _ in range(3):
            self.effects.update()
        c = cell(100, 100, SIZE)
        self.assertEqual([(c[0], c[1], c[0], c[1], RADIUS, HEAT)] * 3, self.field.burns)

    def test_a_body_without_an_effect_burns_nothing(self):
        self.stepper.places = [(100, 100)] * 3
        self.effects.update()
        self.assertEqual([], self.field.burns)

    def test_a_moving_body_burns_behind_itself_along_its_path(self):
        self.effects.bodies[0].effect = self.trail()
        self.stepper.places[0] = (100, 100)
        self.effects.update()
        self.stepper.places[0] = (140, 100)  # 20 cells right in a frame
        self.effects.update()
        c0, c1, y = cell(100, 100, SIZE)[0], cell(140, 100, SIZE)[0], cell(100, 100, SIZE)[1]
        lag = c1 - int((c1 - c0) * LAG)
        self.assertLess(lag, c1)  # behind the body
        self.assertEqual((c0, y, lag, y, RADIUS, HEAT), self.field.burns[-1])

    def test_after_reset_the_first_frame_burns_no_streak(self):
        body = self.effects.bodies[0]
        body.effect = self.trail()
        self.stepper.places[0] = (100, 200)
        self.effects.update()
        body.reset()  # a respawn
        self.stepper.places[0] = (60, 4)
        self.effects.update()
        c = cell(60, 4, SIZE)
        self.assertEqual((c[0], c[1], c[0], c[1], RADIUS, HEAT), self.field.burns[-1])

    def test_above_the_screen_it_burns_nothing_and_resets_its_path(self):
        self.effects.bodies[0].effect = self.trail()
        self.stepper.places[0] = (100, 200)
        self.effects.update()
        self.stepper.places[0] = (100, -50)
        self.effects.update()
        self.stepper.places[0] = (60, 4)
        self.effects.update()
        c = cell(60, 4, SIZE)
        self.assertEqual(2, len(self.field.burns))
        self.assertEqual((c[0], c[1], c[0], c[1], RADIUS, HEAT), self.field.burns[-1])

    def test_off_the_screen_below_or_to_the_side_it_burns_nothing(self):
        from fire import H, W

        self.effects.bodies[0].effect = self.trail()
        # its cell at y H, at x 2W and at x -W: off the field, so no burn
        for x, y in ((100, 2 * H - SIZE // 2), (4 * W - SIZE // 2, 100), (-2 * W - SIZE // 2, 100)):
            self.stepper.places[0] = (x, y)
            self.effects.update()
        self.assertEqual([], self.field.burns)
        for x, y in ((100, 2 * H - SIZE // 2 - 2), (4 * W - SIZE // 2 - 2, 100), (-2 * W - SIZE // 2 + 2, 100)):
            body = self.effects.bodies[0]  # cell y H - 1, x 2W - 1, x -W + 1: its flames can reach the screen
            body.reset()
            self.stepper.places[0] = (x, y)
            self.effects.update()
        self.assertEqual(3, len(self.field.burns))

    def test_a_hit_can_start_an_effect(self):
        def catch_fire(body, speed):
            body.effect = self.trail()

        self.stepper.places[2] = (100, 100)
        self.stepper.drained = [2, HIT, 900]
        self.effects.dispatch({HIT: catch_fire})
        self.assertIsInstance(self.effects.bodies[2].effect, FireTrail)
        self.effects.update()
        c = cell(100, 100, SIZE)
        self.assertEqual([(c[0], c[1], c[0], c[1], RADIUS, HEAT)], self.field.burns)

    def test_a_handler_gets_the_body_and_the_speed_of_each_event(self):
        got = []
        self.stepper.drained = [2, HIT, 900, 0, HIT, 700]
        self.effects.dispatch({HIT: lambda body, speed: got.append((body.i, speed))})
        self.assertEqual([(2, 900), (0, 700)], got)

    def test_an_event_kind_without_a_handler_calls_nothing(self):
        got = []
        self.stepper.drained = [1, SLEEP, 0]
        self.effects.dispatch({HIT: lambda body, speed: got.append(body.i)})
        self.assertEqual([], got)

    def test_a_second_effect_runs_with_no_change_to_its_callers(self):
        counter = Counter()
        self.effects.bodies[0].effect, self.effects.bodies[1].effect = counter, self.trail()
        self.stepper.places[0], self.stepper.places[1] = (10, 20), (100, 100)
        self.effects.update()
        self.effects.bodies[0].reset()
        self.assertEqual(([(10, 20)], 1), (counter.places, counter.forgot))
        self.assertEqual(1, len(self.field.burns))


    # --- MVP (P602) ---
    def test_a_scroll_moves_the_path_with_the_world(self):
        """The world moves 3 cells left under a bird that stays at x: its last place and the last burn point move with
        it, so the next segment starts where the old heat went and the flames stream back."""
        trail = self.trail()
        self.effects.bodies[0].effect = trail
        self.stepper.places[0] = (100, 100)
        self.effects.update()
        trail.scroll(-3)
        c, y = cell(100, 100, SIZE)
        self.assertEqual((c - 3, c - 3), (trail.prev_x, trail.trail_x))  # the sign: left is negative
        self.effects.update()
        self.assertEqual((c - 3, y, c - int(3 * LAG), y, RADIUS, HEAT), self.field.burns[-1])

    def test_a_scroll_before_the_first_frame_or_on_another_effect_leaves_no_streak(self):
        trail, counter = self.trail(), Counter()
        trail.scroll(-3)
        counter.scroll(-3)
        self.effects.bodies[0].effect = trail
        self.stepper.places[0] = (100, 100)
        self.effects.update()
        c, y = cell(100, 100, SIZE)
        self.assertEqual([(c, y, c, y, RADIUS, HEAT)], self.field.burns)
        self.assertEqual(([], 0), (counter.places, counter.forgot))

if __name__ == "__main__":
    unittest.main()
