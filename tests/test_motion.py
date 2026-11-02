"""games/motion.py on the Mac: how a body falls, bounces and sleeps, and how a spring settles. Behaviour only: what a
step allocates is measured on the board (probe582.py). Run from the repository root: python3 -m unittest discover tests."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "games"))

from motion import Bodies, Spring  # noqa: E402

G = 2000.0  # RENT's gravity, px/s^2
STEPS = (0.04, 0.06)  # the 40 ms pace and the 60 ms clamp in gfx.Game.step


def drop(dt, height=200.0, restitution=0.35, friction=0.6):
    """One body dropped from height px above its plane, stepped for 2 s: its y and hit after each step."""
    b = Bodies(1)
    b.spawn(0, 10, 0, 40, 0, height)
    ys, hits = [], []
    for _ in range(int(2 / dt)):
        b.step(dt, G, restitution, friction)
        ys.append(b.y[0])
        hits.append(b.hit[0])
    return b, ys, hits


class BodiesTest(unittest.TestCase):

    def test_falls_with_gravity(self):
        for dt in STEPS:
            with self.subTest(dt=dt):
                b = Bodies(1)
                b.spawn(0, 0, 0, 0, 0, 1e6)
                for n in range(1, 11):
                    b.step(dt, G, 0.35, 0.6)
                    t = n * dt
                    self.assertAlmostEqual(b.vy[0], G * t, delta=G * dt)
                    self.assertAlmostEqual(b.y[0], G * t * t / 2, delta=G * t * dt)

    def test_each_bounce_peaks_lower_and_it_sleeps(self):
        for dt in STEPS:
            with self.subTest(dt=dt):
                b, ys, hits = drop(dt)
                speeds = [h for h in hits if h]
                self.assertGreaterEqual(len(speeds), 2)
                self.assertEqual(speeds, sorted(speeds, reverse=True))
                self.assertTrue(all(a > c for a, c in zip(speeds, speeds[1:])))
                peaks, low = [], None  # the highest point (the least y) between two touches of the plane
                for y in ys:
                    if y >= 200.0:
                        if low is not None:
                            peaks.append(low)
                        low = None
                    else:
                        low = y if low is None else min(low, y)
                self.assertTrue(all(a < c for a, c in zip(peaks, peaks[1:])), peaks)
                self.assertEqual(b.asleep[0], 1)

    def test_a_sleeping_body_reports_nothing_and_gains_nothing(self):
        for dt in STEPS:
            with self.subTest(dt=dt):
                b, _, _ = drop(dt)
                x, y = b.x[0], b.y[0]
                for _ in range(50):
                    b.step(dt, G, 0.35, 0.6)
                    self.assertEqual(b.hit[0], 0)
                self.assertEqual((b.x[0], b.y[0], b.vx[0], b.vy[0]), (x, y, 0.0, 0.0))

    def test_hit_lasts_one_step(self):
        for dt in STEPS:
            with self.subTest(dt=dt):
                _, _, hits = drop(dt)
                self.assertTrue(any(hits))
                self.assertTrue(all(not (a and c) for a, c in zip(hits, hits[1:])))

    def test_never_below_its_plane(self):
        for dt in STEPS:
            with self.subTest(dt=dt):
                _, ys, _ = drop(dt, height=37.0)
                self.assertLessEqual(max(ys), 37.0)

    def test_friction_slows_the_slide_at_each_bounce(self):
        b = Bodies(1)
        b.spawn(0, 0, 190, 40, 0, 200)
        while not b.hit[0]:
            b.step(0.04, G, 0.35, 0.6)
        self.assertAlmostEqual(b.vx[0], 24.0)

    def test_a_free_body_does_not_move(self):
        b = Bodies(2)
        b.spawn(0, 0, 0, 0, 0, 100)
        b.spawn(1, 0, 0, 0, 0, 100)
        b.free(1)
        b.step(0.04, G, 0.35, 0.6)
        self.assertGreater(b.y[0], 0.0)
        self.assertEqual(b.y[1], 0.0)


class SpringTest(unittest.TestCase):

    def test_kick_adds_speed_only(self):
        s = Spring(150, 9)
        s.value, s.speed = 2.0, 3.0
        s.kick(10)
        self.assertEqual((s.value, s.speed), (2.0, 13.0))

    def test_press_settles_with_one_overshoot(self):
        """RENT's press: k 150, damping 9, kicked by half the 400 px/s landing."""
        for dt in STEPS:
            with self.subTest(dt=dt):
                s = Spring(150, 9)
                s.kick(200)
                values = []
                for _ in range(int(1 / dt)):
                    s.step(dt)
                    values.append(s.value)
                self.assertTrue(s.settled())
                self.assertLess(max(values), 12)  # never at the drawing's clamp, LEVEL_H - 2
                self.assertLess(abs(values[-1]), 0.5)
                self.assertTrue(any(v < -0.5 for v in values))  # the one overshoot shows
                first = next(i for i, v in enumerate(values) if v < 0)
                self.assertFalse(any(v > 0.5 for v in values[first:]))  # and no second one

    def test_sway_as_before(self):
        """The sway moved onto Spring: the same numbers as the inline spring it replaced."""
        s, value, speed = Spring(250.0, 11.0), 0.0, 0.0
        s.kick(70.0)
        speed += 70.0
        for _ in range(30):
            s.step(0.04)
            speed -= (250.0 * value + 11.0 * speed) * 0.04
            value += speed * 0.04
            self.assertEqual((s.value, s.speed), (value, speed))


if __name__ == "__main__":
    unittest.main()
