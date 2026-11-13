"""games/rescue.py on the Mac (P800, PR 1): the Rules with no display, and the game's crater placement. Run from the
repository root: python3 -m unittest discover tests. --- MVP (P800) ---"""

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

import rescue as rs  # noqa: E402
from rescue import BURNT, OUT, TURNED, Rescue, Rules  # noqa: E402

START = 150  # px: his hips at the start, facing right


def rules_with_crater_at(x):
    return Rules(lambda man_x: x, START)


def hold(rules, ms, frames):
    """frames frames of ms with the button held; the events of each."""
    return [rules.step(ms, True) for _ in range(frames)]


class PressTest(unittest.TestCase):
    def test_a_tap_turns_him_on_the_release_and_he_runs_on(self):
        rules = rules_with_crater_at(300)
        self.assertEqual(0, rules.step(40, True))  # pressed: no turn yet, and he still runs
        self.assertEqual(1, rules.man.facing)
        self.assertGreater(rules.man.x, START)
        x = rules.man.x
        self.assertEqual(TURNED, rules.step(40, False))  # released: the turn, at once
        self.assertEqual(-1, rules.man.facing)
        self.assertLess(rules.man.x, x)  # the same frame he runs the new way

    def test_a_press_just_under_180_ms_is_still_a_tap(self):
        rules = rules_with_crater_at(300)
        hold(rules, 20, 9)  # held 0 to 160 ms
        self.assertFalse(rules.man.spraying())
        self.assertEqual(TURNED, rules.step(20, False))

    def test_a_hold_sprays_from_180_ms_and_stops_him_until_the_release(self):
        rules = rules_with_crater_at(300)
        man = rules.man
        for _ in range(9):  # held 0, 20, ... 160 ms: he runs
            rules.step(20, True)
            self.assertFalse(man.spraying())
        self.assertGreater(man.x, START)
        rules.step(20, True)  # 180 ms
        self.assertTrue(man.spraying())
        x = man.x
        hold(rules, 40, 20)
        self.assertEqual(x, man.x)  # he stands while he sprays
        self.assertEqual(0, rules.step(40, False))  # the release ends the spray, and is no turn
        self.assertFalse(man.spraying())
        self.assertEqual(1, man.facing)
        rules.step(40, False)
        self.assertGreater(man.x, x)  # and he runs again

    def test_the_nozzle_flashes_from_120_ms_until_the_spray(self):
        rules = rules_with_crater_at(300)
        man, seen = rules.man, []
        for _ in range(12):  # held 0 to 220 ms
            rules.step(20, True)
            seen.append((man.down_ms, man.flashing(), man.spraying()))
        for down_ms, flashing, spraying in seen:
            self.assertEqual(120 <= down_ms < 180, flashing, down_ms)
            self.assertEqual(down_ms >= 180, spraying, down_ms)


class HoseTest(unittest.TestCase):
    def spray_at(self, crater_x, frames=40):
        """A crater at crater_x, then 180 ms of press and frames more of spray at 40 ms; the rules and each frame's
        (heat, events) during the spray."""
        rules = rules_with_crater_at(crater_x)
        rules.man.down_ms = rs.TAP_MS  # already held long enough: he sprays from the first frame, at START
        heats = []
        for _ in range(frames):
            events = rules.step(40, True)
            heats.append((rules.crater.heat(), events))
        return rules, heats

    def test_the_spray_within_40_px_lowers_the_fire_and_puts_it_out_in_about_a_second(self):
        rules, heats = self.spray_at(START + rs.REACH_PX)
        burning = [h for h, _ in heats if h]
        self.assertTrue(all(a > b for a, b in zip(burning, burning[1:])))  # down at each frame of water
        out = [i for i, (_, events) in enumerate(heats) if events & OUT]
        self.assertEqual([rs.DOUSE_MS // 40 - 1], out)  # the 25th frame of 40 ms: 1 s of water
        self.assertFalse(rules.crater.burning())

    def test_the_spray_does_not_reach_past_40_px_nor_behind_him(self):
        for x in (START + rs.REACH_PX + 1, START - 10):
            with self.subTest(crater_x=x):
                rules, heats = self.spray_at(x)
                self.assertEqual([rs.HEAT_MAX] * len(heats), [h for h, _ in heats])
                self.assertTrue(rules.crater.burning())

    def test_a_fire_left_alone_burns_out_and_a_new_one_opens_later(self):
        places = iter((300, 120))
        rules = Rules(lambda man_x: next(places), START)
        events = [rules.step(40, False) for _ in range(rs.FIRE_MS // 40)]
        self.assertEqual(BURNT, events[-1])
        self.assertFalse(rules.crater.burning())
        for _ in range((rs.NEXT_MS + 39) // 40):
            rules.step(40, False)
        self.assertEqual(120, rules.crater.x)
        self.assertTrue(rules.crater.burning())


class RunTest(unittest.TestCase):
    def test_the_run_cycle_follows_the_distance_not_the_frame_clock(self):
        poses = []
        for ms in (20, 40, 60):  # the same 1.2 s at three frame paces
            rules = rules_with_crater_at(300)
            for _ in range(1200 // ms):
                rules.step(ms, False)
            poses.append((rules.man.ran, rules.man.run_pose()))
        self.assertEqual(1, len(set(poses)))
        ran, pose = poses[0]
        self.assertEqual(ran * rs.RUN_POSES // rs.STRIDE_PX % rs.RUN_POSES, pose)
        rules = rules_with_crater_at(300)
        rules.man.down_ms = rs.TAP_MS
        hold(rules, 40, 30)  # spraying, he stands: the run's pose stays
        self.assertEqual((0, 0), (rules.man.ran, rules.man.run_pose()))

    def test_one_stride_brings_the_run_back_to_its_first_pose(self):
        man = rs.Fireman(START)
        seen = []
        while man.ran < rs.STRIDE_PX:
            seen.append(man.run_pose())
            man.run(10)
        self.assertEqual(list(range(rs.RUN_POSES)), sorted(set(seen)))
        self.assertEqual(0, man.run_pose())

    def test_he_turns_by_himself_at_each_end_of_the_street(self):
        rules = rules_with_crater_at(300)
        for _ in range(200):
            rules.step(60, False)
            self.assertTrue(rs.LEFT_X <= rules.man.x <= rs.RIGHT_X)
        self.assertGreater(rules.man.ran, rs.RIGHT_X - rs.LEFT_X)  # he reached an end and came back


class PlaceTest(unittest.TestCase):
    def test_a_crater_opens_on_the_street_and_away_from_him(self):
        random.seed(800)
        for man_x in range(rs.LEFT_X, rs.RIGHT_X + 1, 5):
            for _ in range(20):
                x = Rescue.place(man_x)
                self.assertTrue(rs.FIRE_LEFT_X <= x < rs.FIRE_RIGHT_X, x)
                self.assertGreaterEqual(abs(x - man_x), rs.FIRE_GAP_PX, (man_x, x))


if __name__ == "__main__":
    unittest.main()
