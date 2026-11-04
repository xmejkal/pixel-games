"""engine/core/world.c (P590) against its twin motion.Bodies: tests/world_lib.py builds the C with clang and steps it
through CBodies, the stand-in for engine.Bodies, beside the twin. Both get the same API tests, and the twin is the one
source of the maths. Run from the repository root: python3 -m unittest discover tests. --- MVP (P590) ---"""

import os
import sys
import unittest
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))

import motion  # noqa: E402
from world_lib import HAVE_CLANG, HIT, MAX_BODIES, MAX_STEPS, SLEEP, CBodies  # noqa: E402

N = 12
PHYSICS = DT, GRAVITY, RESTITUTION, FRICTION = 0.01, 2000.0, 0.35, 0.6  # the rain's: stack's heavy floors (p582-heavy)
Y_PX = 0.01  # the C's y against the twin's
LANDING_PX = 0.01  # each fixture keeps its landings further than this from a step edge


def scene(rest_y, n=N):
    """x = 10 + 20 i, y = -10 (i % 12), vx = 5 (i % 12 - 6), vy 3 (a vy of 0 puts two bodies on a step edge), and
    rest_y(i): past 12 bodies each twelve repeat the first twelve's fall, so their landing margin stays the same."""
    return [(10.0 + 20 * i, -10.0 * (i % 12), 5.0 * (i % 12 - 6), 3.0, float(rest_y(i))) for i in range(n)]


BOUNCE = scene(lambda i: 220 - 14 * (i % 3))
CROWD = scene(lambda i: 220 - 14 * (i % 3), MAX_BODIES)  # n at its cap, full (under 64 events a call: no drop)


def spawned(make, bodies):
    """make(n) with each body spawned in."""
    world = make(len(bodies))
    for i, body in enumerate(bodies):
        world.spawn(i, *body)
    return world


def events(world):
    """The last step call's events as (id, kind, speed)."""
    out = array("i", [0] * (3 * motion.MAX_EVENTS))
    return [tuple(out[3 * k:3 * k + 3]) for k in range(world.drain(out))]


def margin(bodies, steps):
    """The smallest distance from its plane of a y a step integrates, before the step puts it back on the plane, in
    float64 on the twin. A landing on a step edge can split float32 (C) from float64 (the twin): one lands, one not."""
    twin, least = spawned(motion.Bodies, bodies), float("inf")
    for _ in range(steps):
        for i in range(twin.n):
            if not twin.asleep[i]:  # fall_bodies' vy += g dt, then y += vy dt
                least = min(least, abs(twin.y[i] + (twin.vy[i] + GRAVITY * DT) * DT - twin.rest_y[i]))
        twin.step(1, *PHYSICS)
    return least


@unittest.skipUnless(HAVE_CLANG, "clang is missing: engine/core/world.c is not built")
class ParityTest(unittest.TestCase):
    def same(self, c, twin, when):
        """The C and the twin hold the same y and the same events: the twin's events."""
        worst = max(abs(a - b) for a, b in zip(c.ys(), twin.y))
        self.assertLess(worst, Y_PX, "largest y difference %s" % when)
        got, want = events(c), events(twin)
        self.assertEqual([e[:2] for e in want], [e[:2] for e in got], "hits and sleeps %s" % when)
        for a, b in zip(want, got):  # int() of a float32 and of a float64 speed may truncate 1 px/s apart
            self.assertLessEqual(abs(a[2] - b[2]), 1, "impact speed %s" % when)
        self.assertEqual(twin.dropped, c.dropped, "dropped %s" % when)
        return want

    def check(self, bodies):
        """6 steps in one call, then one call per step up to 100: the y and the events after each call."""
        c, twin = spawned(CBodies, bodies), spawned(motion.Bodies, bodies)
        c.step(6, *PHYSICS)
        twin.step(6, *PHYSICS)
        seen = self.same(c, twin, "after 6 steps")
        for step in range(7, 101):
            c.step(1, *PHYSICS)
            twin.step(1, *PHYSICS)
            seen += self.same(c, twin, "after %d steps" % step)
        self.assertGreater(margin(bodies, 100), LANDING_PX)  # 0.0160 on 2026-11-03
        return seen

    def test_the_bounce_scene_matches_the_twin(self):
        kinds = {e[1] for e in self.check(BOUNCE)}
        self.assertEqual({HIT, SLEEP}, kinds)  # the scene reaches both branches, so the test reaches them too

    def test_the_full_cap_matches_the_twin(self):
        self.check(CROWD)


class ApiTests:
    """The API both sides share: make is CBodies or motion.Bodies."""

    make = None

    def test_n_outside_1_to_256_is_refused(self):
        for n in (0, -1, MAX_BODIES + 1):
            with self.subTest(n=n), self.assertRaises(ValueError):
                self.make(n)
        self.assertEqual(MAX_BODIES, self.make(MAX_BODIES).read(array("h", [0] * (3 * MAX_BODIES))))

    def test_a_new_body_sleeps_at_0_0(self):
        world = self.make(3)
        world.step(5, *PHYSICS)
        out = array("h", [9] * 9)
        self.assertEqual(3, world.read(out))
        self.assertEqual([0, 0, 1] * 3, list(out))
        self.assertEqual([], events(world))

    def test_read_truncates_toward_0(self):
        world = spawned(self.make, [(37.9, -5.5, 0.0, 0.0, 30000.0), (-3.2, 219.9, 0.0, 0.0, 220.0)])
        out = array("h", [0] * 6)
        world.read(out)
        self.assertEqual([37, -5, 0, -3, 219, 0], list(out))
        world.step(1, *PHYSICS)  # body 1 reaches its plane under the rest speed: it sleeps there
        world.read(out)
        self.assertEqual([37, -5, 0, -3, 220, 1], list(out))
        self.assertEqual([(1, SLEEP, 0)], events(world))

    def test_a_spawn_wakes_a_sleeper(self):
        world = self.make(1)
        world.spawn(0, 5.0, 10.0, 0.0, 0.0, 1000.0)
        world.step(1, *PHYSICS)
        out = array("h", [0] * 3)
        world.read(out)
        self.assertEqual([5, 10, 0], list(out))  # awake: 0.2 px down, still 10 as an int

    def test_a_spawn_outside_0_to_n_minus_1_is_refused(self):
        world = self.make(4)
        for i in (-1, 4):
            with self.subTest(i=i), self.assertRaises(IndexError):
                world.spawn(i, 1.0, 2.0, 0.0, 0.0, 300.0)

    def test_steps_outside_0_to_64_are_refused(self):
        world = self.make(1)
        for steps in (-1, MAX_STEPS + 1):
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                world.step(steps, *PHYSICS)

    def test_a_short_read_array_is_refused(self):
        with self.assertRaises(ValueError):
            self.make(2).read(array("h", [0] * 5))

    def hits(self, n):
        """n bodies 0.5 px over their plane at 1,000 px/s down: one step and each hits at 1,020 px/s."""
        return spawned(self.make, [(0.0, 99.5, 0.0, 1000.0, 100.0)] * n)

    def test_a_hit_reports_its_speed(self):
        world = self.hits(1)
        world.step(1, *PHYSICS)
        self.assertEqual([(0, HIT, 1020)], events(world))

    def test_the_rest_speed_is_1_5_steps_of_gravity(self):
        # 30 px/s here: at the plane, body 0 has 35 px/s and bounces, body 1 has 25 px/s and rests (refuter, P590)
        world = spawned(self.make, [(0.0, 99.7, 0.0, 15.0, 100.0), (0.0, 99.8, 0.0, 5.0, 100.0)])
        world.step(1, *PHYSICS)
        self.assertEqual([(0, HIT, 35), (1, SLEEP, 0)], events(world))

    def test_a_hit_keeps_friction_times_its_vx(self):
        world = spawned(self.make, [(0.0, 99.5, 100.0, 1000.0, 100.0)])
        world.step(2, *PHYSICS)  # 1 px across before the hit, then 0.6 px at 60 px/s: 1.6, not 2
        out = array("h", [0] * 3)
        world.read(out)
        self.assertEqual(1, out[0])

    def test_a_step_clears_the_events_first(self):
        world = self.hits(2)
        world.step(1, *PHYSICS)
        self.assertEqual([(0, HIT, 1020), (1, HIT, 1020)], events(world))
        world.step(1, *PHYSICS)  # both rise now
        self.assertEqual([], events(world))

    def test_a_step_of_0_clears_them_too(self):
        world = self.hits(2)
        world.step(1, *PHYSICS)
        world.step(0, *PHYSICS)
        self.assertEqual([], events(world))

    def test_drain_into_a_short_buffer_returns_what_fits(self):
        world = self.hits(2)
        world.step(1, *PHYSICS)
        out = array("i", [0] * 5)
        self.assertEqual(1, world.drain(out))
        self.assertEqual([0, HIT, 1020], list(out[:3]))

    def test_the_65th_event_only_counts_in_dropped(self):
        world = self.hits(70)
        world.step(1, *PHYSICS)
        self.assertEqual(list(range(motion.MAX_EVENTS)), [e[0] for e in events(world)])
        self.assertEqual(70 - motion.MAX_EVENTS, world.dropped)
        world.step(1, *PHYSICS)
        self.assertEqual(0, world.dropped)


@unittest.skipUnless(HAVE_CLANG, "clang is missing: engine/core/world.c is not built")
class CBodiesTest(ApiTests, unittest.TestCase):
    make = CBodies

    def test_a_wrong_array_type_is_refused(self):
        world = self.make(1)
        with self.assertRaises(ValueError):
            world.read(array("i", [0] * 3))
        with self.assertRaises(ValueError):
            world.drain(array("h", [0] * 3))


class TwinTest(ApiTests, unittest.TestCase):
    make = motion.Bodies

    def test_its_kinds_and_cap_are_the_engines(self):
        self.assertEqual((HIT, SLEEP, 64), (motion.HIT, motion.SLEEP, motion.MAX_EVENTS))


class StepClockTest(unittest.TestCase):
    def test_whole_steps_and_the_rest_waits(self):
        clock = motion.StepClock(10, 8)
        self.assertEqual(4, clock.take(40))
        self.assertEqual(4, clock.take(45))
        self.assertEqual(1, clock.take(5))  # 5 ms left over and 5 more

    def test_the_cap_drops_the_rest(self):
        clock = motion.StepClock(10, 8)
        self.assertEqual(8, clock.take(200))
        self.assertEqual(0, clock.take(5))  # the 12 steps over the cap are gone, not owed


if __name__ == "__main__":
    unittest.main()
