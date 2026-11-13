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
    def test_a_tap_turns_him_on_the_release_on_the_spot_then_he_runs_the_other_way(self):
        rules = rules_with_crater_at(300)
        self.assertEqual(0, rules.step(40, True))  # pressed: no turn yet, and he still runs
        self.assertEqual(1, rules.man.facing)
        self.assertGreater(rules.man.x, START)
        x = rules.man.x
        self.assertEqual(TURNED, rules.step(40, False))  # released: the turn, at once
        self.assertEqual(-1, rules.man.facing)
        for _ in range(rs.TURN_MS // 40 - 1):  # the turn's poses: he turns on the spot
            self.assertTrue(rules.man.turning())
            rules.step(40, False)
            self.assertEqual(x, rules.man.x)
        rules.step(40, False)
        self.assertFalse(rules.man.turning())
        self.assertLess(rules.man.x, x)  # then he runs the new way

    def test_the_tap_ends_at_180_ms_of_real_time_at_any_frame_pace(self):
        for ms in (20, 40, 90):
            last_tap = (rs.TAP_MS - 1) // ms  # the most frames held that are still under 180 ms
            for frames, turns in ((last_tap, True), (last_tap + 1, False)):
                with self.subTest(frame_ms=ms, held_ms=frames * ms):
                    rules = rules_with_crater_at(300)
                    hold(rules, ms, frames)
                    self.assertEqual(not turns, rules.man.spraying())
                    self.assertEqual(TURNED if turns else 0, rules.step(ms, False))

    def test_a_200_ms_press_at_40_ms_frames_sprays_and_does_not_turn(self):
        rules = rules_with_crater_at(300)
        hold(rules, 40, 5)
        self.assertTrue(rules.man.spraying())
        self.assertEqual(0, rules.step(40, False))
        self.assertEqual(1, rules.man.facing)

    def test_a_hold_sprays_from_180_ms_and_stops_him_until_the_release(self):
        rules = rules_with_crater_at(300)
        man = rules.man
        for _ in range(8):  # held 20, 40, ... 160 ms: he runs
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
        for _ in range(12):  # held 20 to 240 ms
            rules.step(20, True)
            seen.append((man.down_ms, man.flashing(), man.spraying()))
        for down_ms, flashing, spraying in seen:
            self.assertEqual(120 <= down_ms < 180, flashing, down_ms)
            self.assertEqual(down_ms >= 180, spraying, down_ms)

    def test_no_spray_while_he_turns(self):
        rules = rules_with_crater_at(300)
        rules.step(40, True)
        rules.step(40, False)  # a tap: the turn starts
        rules.man.down_ms = rs.TAP_MS  # as if held long enough already
        rules.step(40, True)
        self.assertTrue(rules.man.turning())
        self.assertFalse(rules.man.spraying())
        while rules.man.turning():
            rules.step(40, True)
        self.assertTrue(rules.man.spraying())  # the hold sprays once the turn is over


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

    def test_after_a_turn_the_run_goes_on_from_the_phase_the_turn_ends_in(self):
        rules = rules_with_crater_at(300)
        for _ in range(7):
            rules.step(40, False)
        self.assertNotEqual(0, rules.man.run_pose())  # mid-stride when he turns
        rules.step(40, True)
        rules.step(40, False)
        while rules.man.turning():
            rules.step(40, False)
        # the turn's last pose is the run's phase 9 of 12, so the run goes on at phase 0 and on from there
        self.assertEqual(0, rules.man.run_pose())
        rules.step(40, False)
        self.assertIn(rules.man.run_pose(), (0, 1))

    def test_he_turns_by_himself_at_each_end_of_the_street(self):
        rules = rules_with_crater_at(300)
        man = rules.man
        for wall, facing in ((rs.RIGHT_X, 1), (rs.LEFT_X, -1)):
            with self.subTest(wall=wall):
                self.assertEqual(facing, man.facing)
                while man.x != wall:
                    rules.step(40, False)
                self.assertEqual(-facing, man.facing)  # he faces the other way at the wall
                while man.turning():
                    rules.step(40, False)
                rules.step(40, False)
                self.assertEqual(-facing, (man.x - wall) // abs(man.x - wall))  # and runs back off it


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
