"""engine/core/world.c (P589 probe) against the maths of p582-heavy's fall_bodies: clang builds it into a temporary
folder and ctypes steps both modes beside a Python reference. Run from the repository root: python3 -m unittest
discover tests. --- probe, throwaway (P589) ---"""

import ctypes
import os
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLD_C = os.path.join(REPO, "engine", "core", "world.c")

N, RATE, STEPS = 12, 100, 100  # the plan's scene: 12 bodies, 100 steps per second, one 1 s block
GRAVITY, RESTITUTION, FRICTION = 2000.0, 0.35, 0.6  # p582-heavy games/arcade2.py: Stack.G, SLAB_BOUNCE, SLAB_FRICTION
HIT, SLEEP = 1, 2  # world.h's WORLD_EVENT_HIT and WORLD_EVENT_SLEEP
Q_MAX = 32768  # Q16.16 holds |value| < 2^15 px
FLOAT_PX, FIXED_PX = 0.01, 0.1  # the plan's limits against the reference


def scene(rest_y):
    """x = 10 + 20 i, y = -10 i, vx = 5 (i - 6), vy 3 (a vy of 0 puts two bodies on a step edge), and rest_y(i)."""
    return [(10.0 + 20 * i, -10.0 * i, 5.0 * (i - 6), 3.0, float(rest_y(i))) for i in range(N)]


FALL = scene(lambda i: 30000)  # no body reaches its plane
BOUNCE = scene(lambda i: 220 - 14 * (i % 3))


def reference(bodies):
    """fall_bodies' maths in Python floats, one step at a time: the y after each step, its events as (id, kind, speed),
    the awake body-steps, and the smallest distance of an integrated y from its plane (a landing's margin)."""
    x, y, vx, vy, rest_y = (list(c) for c in zip(*bodies))
    asleep, ys, events, awake, margin = [0] * N, [], [], 0, float("inf")
    dt = 1.0 / RATE
    rest_speed = 1.5 * GRAVITY * dt
    for _ in range(STEPS):
        step_events = []
        for i in range(N):
            if asleep[i]:
                continue
            awake += 1
            vy[i] += GRAVITY * dt
            x[i] += vx[i] * dt
            y[i] += vy[i] * dt
            margin = min(margin, abs(y[i] - rest_y[i]))
            if y[i] >= rest_y[i]:
                y[i] = rest_y[i]
                v = vy[i]
                if v < rest_speed:
                    vy[i], vx[i], asleep[i] = 0.0, 0.0, 1
                    step_events.append((i, SLEEP, 0))
                else:
                    step_events.append((i, HIT, int(v)))
                    vy[i] = -v * RESTITUTION
                    vx[i] *= FRICTION
        ys.append(list(y))
        events.append(step_events)
    return ys, events, awake, margin


class World:
    """One world of the library in one mode, stepped one step per call, as the test reads it after each step."""

    def __init__(self, lib, mode, bodies):
        self.lib, self.mode = lib, mode
        size = getattr(lib, "world_%s_size" % mode)()
        self.buf = ctypes.create_string_buffer(size)
        columns = [(ctypes.c_float * N)(*c) for c in zip(*bodies)]
        getattr(lib, "world_load_%s" % mode)(self.buf, N, *columns)

    def step(self):
        getattr(self.lib, "world_step_%s" % self.mode)(
            self.buf, 1, RATE, ctypes.c_float(GRAVITY), ctypes.c_float(RESTITUTION), ctypes.c_float(FRICTION))

    def y(self):
        out = (ctypes.c_float * N)()
        getattr(self.lib, "world_read_y_%s" % self.mode)(self.buf, out)
        return list(out)

    def events(self):
        out = (ctypes.c_int32 * (3 * 64))()
        m = self.lib.world_drain(self.buf, out, 64)  # world_state_t is first in each world
        return [tuple(out[3 * k:3 * k + 3]) for k in range(m)]

    def awake_steps(self):
        return ctypes.c_uint32.from_buffer(self.buf, 4).value  # world_state_t: int32 n, then uint32 awake_steps


def run(world):
    ys, events = [], []
    for _ in range(STEPS):
        world.step()
        ys.append(world.y())
        events.append(world.events())
    return ys, events


@unittest.skipUnless(shutil.which("clang"), "clang is missing: engine/core/world.c is not built")
class WorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        lib_path = os.path.join(cls.tmp.name, "libworld.so")
        subprocess.run(["clang", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-o", lib_path,
                        WORLD_C], check=True)
        cls.lib = ctypes.CDLL(lib_path)
        cls.lib.world_float_size.restype = cls.lib.world_fixed_size.restype = ctypes.c_size_t

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def check_scene(self, bodies):
        ref_ys, ref_events, ref_awake, margin = reference(bodies)
        for mode, limit in (("float", FLOAT_PX), ("fixed", FIXED_PX)):
            world = World(self.lib, mode, bodies)
            ys, events = run(world)
            with self.subTest(mode=mode):
                worst = max(abs(a - b) for ref, got in zip(ref_ys, ys) for a, b in zip(ref, got))
                self.assertLess(worst, limit, "largest y difference from the reference")
                for step, (ref, got) in enumerate(zip(ref_events, events)):
                    self.assertEqual([e[:2] for e in ref], [e[:2] for e in got], "hits and sleeps in step %d" % step)
                    for a, b in zip(ref, got):  # int(v) of a float32 or Q16.16 speed may truncate 1 px/s apart
                        self.assertLessEqual(abs(a[2] - b[2]), 1, "impact speed in step %d" % step)
                self.assertEqual(ref_awake, world.awake_steps(), "awake body-steps")
        return ref_ys, ref_events, margin

    def test_bounce_scene_matches_the_reference(self):
        _, events, margin = self.check_scene(BOUNCE)
        kinds = [e[1] for step in events for e in step]
        self.assertIn(HIT, kinds)
        self.assertIn(SLEEP, kinds)  # the scene reaches both branches, so the test reaches them too
        print("\nbounce scene: smallest landing margin %.4f px" % margin)

    def test_fall_scene_stays_in_q16_range(self):
        ys, events, _ = self.check_scene(FALL)
        self.assertLess(max(b[4] for b in FALL), Q_MAX)  # rest_y 30,000 fits Q16.16
        self.assertLess(max(max(step) for step in ys), 1100)  # and y in 1 s stays under 1,100 px
        self.assertEqual([], [e for step in events for e in step])  # no body reaches its plane


if __name__ == "__main__":
    unittest.main()
