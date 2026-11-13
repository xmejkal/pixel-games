"""games/rescue.py on the Mac (P800): the fireman's press, hose and run (PR 1), and the game's rules: the people, the
carry, the meteors, the ramp, and bots that play whole rounds (PR 2). Run from the repository root:
python3 -m unittest discover tests. --- MVP (P800) ---"""

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
from rescue import BURNT, OUT, TURNED, Crater, Rules  # noqa: E402

START = 150  # px: his hips at the start, facing right
NEVER = 10 ** 9  # ms: a clock set this far never runs out in a test


def calm(rules):
    """No meteor falls and nobody comes out: a test with its own craters and people keeps them alone."""
    rules.meteor_ms = rules.come_ms = NEVER
    return rules


def rules_with_crater_at(x):
    """PR 1's street: the fireman at START and one burning crater at x, with nothing else coming."""
    rules = calm(Rules(random.Random(800).randrange, START))
    rules.craters.append(Crater(x))
    return rules


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
            heats.append((rules.craters[0].heat(), events))
        return rules, heats

    def test_the_spray_within_40_px_lowers_the_fire_and_puts_it_out_in_about_a_second(self):
        rules, heats = self.spray_at(START + rs.REACH_PX)
        burning = [h for h, _ in heats if h]
        self.assertTrue(all(a > b for a, b in zip(burning, burning[1:])))  # down at each frame of water
        out = [i for i, (_, events) in enumerate(heats) if events & OUT]
        self.assertEqual([rs.DOUSE_MS // 40 - 1], out)  # the 25th frame of 40 ms: 1 s of water
        self.assertFalse(rules.craters[0].burning())

    def test_the_spray_does_not_reach_past_40_px_nor_behind_him(self):
        for x in (START + rs.REACH_PX + 1, START - 10):
            with self.subTest(crater_x=x):
                rules, heats = self.spray_at(x)
                self.assertEqual([rs.HEAT_MAX] * len(heats), [h for h, _ in heats])
                self.assertTrue(rules.craters[0].burning())

    def test_a_fire_left_alone_burns_out_after_fire_ms(self):
        rules = rules_with_crater_at(300)
        events = [rules.step(40, False) for _ in range(rs.FIRE_MS // 40)]
        self.assertEqual(BURNT, events[-1] & BURNT)
        self.assertFalse(any(e & BURNT for e in events[:-1]))
        self.assertFalse(rules.craters[0].burning())


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


def street(*people, x=START):
    """Rules with nothing coming, the fireman at x facing right, and these people: (kind, x, facing) each."""
    rules = calm(Rules(random.Random(800).randrange, x))
    for kind, px, facing in people:
        rules.people.append(rs.Person(kind, px, facing, NEVER))
    return rules


def fire_at(rules, *xs):
    for x in xs:
        rules.craters.append(Crater(x))
    return rules


class PeopleTest(unittest.TestCase):
    def test_a_person_turns_back_at_a_fire_and_never_comes_within_block_px(self):
        rules = fire_at(street((rs.WOMAN, 250, 1), x=100), 290)
        rules.man.down_ms = rs.TAP_MS  # he sprays where he stands, so he picks nobody up
        person, closest = rules.people[0], NEVER
        for _ in range(60):
            rules.step(40, True)
            closest = min(closest, 290 - person.x)
        self.assertEqual(-1, person.facing)
        self.assertGreaterEqual(closest, rs.BLOCK_PX)
        self.assertEqual(rs.RUN, person.state)

    def test_between_two_fires_a_person_stops_and_waves_and_runs_again_when_one_goes_out(self):
        rules = fire_at(street((rs.MAN, 230, 1), x=100), 260, 200)
        person = rules.people[0]
        seen = 0
        for _ in range(10):
            seen |= rules.step(40, False)
        self.assertTrue(seen & rs.TRAPPED)
        self.assertEqual((rs.WAVING, rs.MAN), (person.state, rules.trapped_kind))
        x = person.x
        rules.step(40, False)
        self.assertEqual(x, person.x)  # waving, they stand
        self.assertGreater(person.wave_ms, 0)
        rules.craters[0].left_ms = 1  # the fire ahead of them burns out
        rules.step(40, False)
        self.assertEqual(rs.RUN, person.state)
        rules.step(40, False)
        self.assertGreater(person.x, x)  # and they run toward where it was

    def test_the_wave_and_the_run_pose_follow_the_clock_and_the_distance(self):
        person = rs.Person(rs.GRANNY, 200, 1, NEVER)
        person.wave_ms = rs.WAVE_MS // 2
        self.assertEqual(rs.WAVE_POSES // 2, person.wave_pose())
        while person.ran < rs.PERSON_STRIDE_PX[rs.GRANNY]:
            person.run(20)
        self.assertEqual(0, person.pose())

    def test_people_stay_on_the_street_and_out_of_the_station(self):
        rules = Rules(random.Random(3).randrange)
        rules.meteor_ms = NEVER
        for _ in range(3000):
            rules.step(40, False)
            for p in rules.people:
                if p.state != rs.CARRIED:
                    self.assertTrue(rs.STREET_LEFT <= p.x <= rs.STREET_RIGHT, p.x)

    def test_a_person_comes_out_away_from_fires_and_the_fireman_and_no_more_than_the_tier_allows(self):
        rules = fire_at(Rules(random.Random(5).randrange), 200)
        rules.meteor_ms = NEVER
        for _ in range(500):
            if rules.step(40, False) & rs.CAME:
                self.assertGreaterEqual(abs(rules.came_x - 200), rs.COME_GAP_PX)
                self.assertGreaterEqual(abs(rules.came_x - rules.man.x), rs.COME_GAP_PX)
            self.assertLessEqual(len(rules.people), rs.CROWD[0])


class CarryTest(unittest.TestCase):
    def test_a_touch_picks_a_person_up(self):
        rules = street((rs.MAN, START + 30, -1))
        events = 0
        while not events & rs.PICKED:
            events = rules.step(40, False)
        man = rules.man
        self.assertIs(rules.people[0], man.carrying)
        self.assertEqual(rs.CARRIED, rules.people[0].state)
        self.assertLessEqual(abs(rules.people[0].x - man.x), rs.TOUCH_PX)

    def test_a_trapped_person_is_picked_up_too(self):
        rules = fire_at(street((rs.WOMAN, 230, 1), x=100), 260, 200)
        for _ in range(10):
            rules.step(40, False)
        self.assertEqual(rs.WAVING, rules.people[0].state)
        rules.man.x = rules.people[0].x - 5
        self.assertTrue(rules.step(40, False) & rs.PICKED)

    def test_carrying_slows_him_and_blocks_the_spray_and_he_runs_through_a_fire(self):
        rules = fire_at(street((rs.MAN, START, 1)), START + 60)
        rules.step(40, False)
        man = rules.man
        self.assertIsNotNone(man.carrying)
        x = man.x
        for _ in range(25):  # 1 s
            rules.step(40, False)
        self.assertEqual(x + rs.CARRY_PX_S, man.x)  # slower than his run, and past the fire
        for _ in range(10):  # 400 ms held: no spray, no flash; he runs on
            rules.step(40, True)
            self.assertFalse(man.spraying())
            self.assertFalse(man.flashing())
        self.assertGreater(man.x, x + rs.CARRY_PX_S)
        self.assertTrue(rules.craters[0].burning())

    def test_a_tap_turns_him_at_once_while_he_carries(self):
        rules = street((rs.MAN, START, 1))
        rules.step(40, False)
        rules.step(40, True)
        self.assertEqual(TURNED, rules.step(40, False) & TURNED)
        self.assertFalse(rules.man.turning())  # no turn's poses: nobody would be in his arms
        x = rules.man.x
        rules.step(40, False)
        self.assertLess(rules.man.x, x)

    def test_no_pickup_while_he_sprays(self):
        rules = street((rs.MAN, START + 5, 1))
        rules.man.down_ms = rs.TAP_MS
        rules.people[0].x = START + 30
        rules.people[0].facing = -1
        for _ in range(30):
            rules.step(40, True)
        self.assertIsNone(rules.man.carrying)

    def test_without_carrying_a_fire_stops_him_and_the_hose_opens_the_way(self):
        rules = fire_at(street(), START + 50)
        man = rules.man
        for _ in range(25):
            rules.step(40, False)
        self.assertTrue(man.blocked)
        self.assertEqual(START + 50 - rs.BLOCK_PX, man.x)
        while rules.craters[0].burning():
            rules.step(40, True)
        rules.step(40, False)
        rules.step(40, False)
        self.assertGreater(man.x, START + 50 - rs.BLOCK_PX)

    def test_the_door_scores_one_and_a_child_two(self):
        for kind, points in ((rs.WOMAN, 1), (rs.CHILD, 2), (rs.GRANNY, 1)):
            with self.subTest(kind=rs.KINDS[kind]):
                rules = street((kind, 110, 1), x=120)
                rules.man.facing = -1
                events = 0
                for _ in range(100):
                    events |= rules.step(40, False)
                self.assertTrue(events & rs.SAVED)
                self.assertEqual((1, points, kind), (rules.saved, rules.points, rules.saved_kind))
                self.assertEqual([], rules.people)
                self.assertIsNone(rules.man.carrying)


class MeteorTest(unittest.TestCase):
    def test_a_meteor_lands_after_its_shadow_and_opens_a_burning_crater(self):
        rules = street()
        rules.meteors.append(rs.Meteor(250))
        events = [rules.step(40, False) for _ in range(rs.FALL_MS // 40)]
        self.assertFalse(any(e & rs.LANDED for e in events[:-1]))
        self.assertTrue(events[-1] & rs.LANDED)
        self.assertEqual(250, rules.landed_x)
        self.assertEqual([250], [c.x for c in rules.burning()])

    def trapped(self):
        """A man trapped between two fires, waving where he stands: he cannot run from a meteor."""
        rules = fire_at(street((rs.MAN, 250, 1), x=100), 290, 210)
        while rules.people[0].state != rs.WAVING:
            rules.step(40, False)
        return rules

    def test_a_meteor_on_a_person_loses_one(self):
        rules = self.trapped()
        rules.meteors.append(rs.Meteor(rules.people[0].x + rs.HIT_PX))
        events = 0
        for _ in range(rs.FALL_MS // 40):
            events |= rules.step(40, False)
        self.assertTrue(events & rs.LOST)
        self.assertEqual(([], 1), (rules.people, rules.lost_count))

    def test_a_meteor_beside_a_person_misses(self):
        rules = self.trapped()
        rules.meteors.append(rs.Meteor(rules.people[0].x + rs.HIT_PX + 1))
        for _ in range(rs.FALL_MS // 40):
            rules.step(40, False)
        self.assertEqual(0, rules.lost_count)

    def test_a_running_person_turns_away_from_a_shadow_ahead(self):
        rules = street((rs.WOMAN, 200, 1), x=100)
        rules.meteors.append(rs.Meteor(215))
        rules.step(40, False)
        self.assertEqual(-1, rules.people[0].facing)
        for _ in range(rs.FALL_MS // 40):
            rules.step(40, False)
        self.assertEqual(0, rules.lost_count)

    def test_the_person_he_carries_has_grace_then_a_meteor_on_him_takes_them(self):
        for grace, lost in ((True, 0), (False, 1)):
            with self.subTest(grace=grace):
                rules = street((rs.MAN, START, 1))
                rules.step(40, False)
                man = rules.man
                if not grace:
                    man.carried_ms = rs.GRACE_MS
                rules.land(man.x)
                self.assertEqual(lost, rules.lost_count)
                self.assertEqual(grace, man.carrying is not None)

    def test_three_lost_end_the_round(self):
        rules = street(*[(rs.MAN, x, 1) for x in (120, 180, 240, 300)], x=80)
        for k, x in enumerate((120, 180, 240)):
            rules.land(x)
            events = rules.step(1, False)
            self.assertEqual(k == 2, bool(events & rs.OVER))
        self.assertEqual(rs.LOST_MAX, rules.lost_count)

    def test_meteors_land_on_the_street(self):
        rules = Rules(random.Random(9).randrange)
        for _ in range(5000):
            if rules.step(40, False) & rs.FELL:
                self.assertTrue(rs.METEOR_LEFT <= rules.meteors[-1].x <= rs.METEOR_RIGHT)
            rules.lost_count = 0  # the round never ends here


class RampTest(unittest.TestCase):
    def test_the_ramp_numbers(self):
        self.assertEqual((2400, 900), (rs.METEOR_MS[0], rs.METEOR_MS[-1]))
        self.assertEqual((2, 5), (rs.CROWD[0], rs.CROWD[-1]))
        self.assertEqual(len(rs.METEOR_MS), len(rs.CROWD))
        self.assertEqual(sorted(rs.METEOR_MS, reverse=True), list(rs.METEOR_MS))
        self.assertEqual(sorted(rs.CROWD), list(rs.CROWD))
        self.assertEqual((3, 6000), (rs.SAVES_A_STEP, rs.FIRE_MS))
        self.assertEqual(800, rs.FALL_MS)

    def test_a_step_every_three_people_saved_up_to_the_last_tier(self):
        rules = street()
        for saved, tier in ((0, 0), (2, 0), (3, 1), (5, 1), (6, 2), (15, 5), (99, 5)):
            rules.saved = saved
            self.assertEqual(tier, rules.tier())

    def test_the_meteors_come_at_the_tier_s_pace(self):
        for tier in (0, len(rs.METEOR_MS) - 1):
            with self.subTest(tier=tier):
                rules = Rules(random.Random(1).randrange)
                rules.saved, rules.come_ms = tier * rs.SAVES_A_STEP, NEVER
                falls = []
                for k in range(1, 3000):
                    if rules.step(10, False) & rs.FELL:
                        falls.append(10 * k)
                    rules.lost_count = 0
                self.assertEqual(rs.FIRST_MS, falls[0])
                self.assertEqual({rs.METEOR_MS[tier]}, {b - a for a, b in zip(falls, falls[1:])})


# Bots over whole rounds, as Bucket's header records its trials: seeds SEEDS, frames of each pace in PACES (0: random
# 20 to 90 ms a frame). The results on the Mac when the numbers were set (saved/lost/round length per seed):
#   carrier at 40 ms: 16/3/83 s 12/3/58 s 13/3/77 s 11/3/72 s 15/3/78 s 8/3/60 s 14/3/70 s 11/3/73 s
#   idle at 40 ms: 4/3/56 s 6/3/85 s 3/3/48 s 1/3/43 s 6/3/84 s 2/3/26 s 5/3/86 s 2/3/38 s (the fireman runs by himself,
#   so he picks up whoever he meets); over every pace the idle round ends by 131 s, the carrier at the hardest tier by
#   59 s, and one who only sprays never picks anyone up.
SEEDS, PACES = range(8), (20, 40, 60, 90, 0)


class Carrier:
    """A bot that plays as a person would: it faces the nearest person (one who waves first) or, carrying, the door;
    it taps to turn, holds to spray a fire between it and the person, and carrying, backs off from a shadow ahead."""

    def __init__(self):
        self.tapped = False

    def __call__(self, rules):
        man = rules.man
        if self.tapped:  # the tap's release
            self.tapped = False
            return False
        if man.carrying is not None:
            goal, want = rs.LEFT_X, -1
            if any(0 <= (m.x - man.x) * man.facing <= 36 for m in rules.meteors):
                want = -man.facing
        else:
            out = [p for p in rules.people if p.state != rs.CARRIED]
            if not out:
                return False
            p = min(out, key=lambda p: (p.state != rs.WAVING, abs(p.x - man.x)))
            goal, want = p.x, (1 if p.x > man.x else -1)
        if want != man.facing and abs(goal - man.x) > rs.TOUCH_PX and not man.turning():
            if man.down_ms >= 0:
                return False
            self.tapped = True
            return True
        fire = rules.fire_ahead(man.x, man.facing, rs.REACH_PX)
        return fire is not None and man.carrying is None and (goal - fire) * man.facing > 0


def play(bot, seed, pace, limit_ms=600000, tier=0, until_ms=None):
    """A round of the bot: (saved, lost, ms) at its end, or at until_ms."""
    rules, frames = Rules(random.Random(seed).randrange), random.Random(seed + 1)
    rules.saved = tier * rs.SAVES_A_STEP
    t = 0
    while t < limit_ms:
        ms = pace or frames.randrange(20, 91)
        events = rules.step(ms, bot(rules))
        t += ms
        if events & rs.OVER or (until_ms and t >= until_ms):
            break
    return rules.saved - tier * rs.SAVES_A_STEP, rules.lost_count, t


class BotTest(unittest.TestCase):
    def rounds(self, make, **kw):
        return {(seed, pace): play(make(), seed, pace, **kw) for seed in SEEDS for pace in PACES}

    def test_a_bot_that_carries_saves_people_over_60_s(self):
        rounds = self.rounds(Carrier, until_ms=60000)
        for key, (saved, lost, ms) in rounds.items():
            with self.subTest(seed=key[0], pace=key[1]):
                self.assertGreaterEqual(saved, 3)
        self.assertGreaterEqual(sorted(s for s, _, _ in rounds.values())[len(rounds) // 2], 8)  # the median round

    def test_the_bot_that_carries_does_better_than_an_idle_player(self):
        carrier = self.rounds(Carrier)
        idle = self.rounds(lambda: lambda rules: False)
        self.assertGreater(sum(s for s, _, _ in carrier.values()), 2 * sum(s for s, _, _ in idle.values()))
        self.assertGreater(sum(ms for _, _, ms in carrier.values()) / len(carrier), 60000)

    def test_an_idle_player_loses_within_a_bound(self):
        for key, (_, lost, ms) in self.rounds(lambda: lambda rules: False).items():
            with self.subTest(seed=key[0], pace=key[1]):
                self.assertGreaterEqual(lost, rs.LOST_MAX)
                self.assertLess(ms, 180000)

    def test_a_player_who_only_sprays_saves_none(self):
        for key, (saved, _, _) in self.rounds(lambda: lambda rules: True, limit_ms=120000).items():
            with self.subTest(seed=key[0], pace=key[1]):
                self.assertEqual(0, saved)

    def test_the_bot_at_the_hardest_tier_loses_within_a_bound(self):
        for key, (_, lost, ms) in self.rounds(Carrier, tier=len(rs.METEOR_MS) - 1).items():
            with self.subTest(seed=key[0], pace=key[1]):
                self.assertGreaterEqual(lost, rs.LOST_MAX)
                self.assertLess(ms, 90000)


class GameTest(unittest.TestCase):
    """The game itself on the Mac, without the heat field or the art: the flat shapes, the cues, a whole round."""

    def test_a_round_plays_draws_and_ends_with_its_sounds(self):
        import gfx  # noqa: E402

        class Heard:
            def __init__(self):
                self.names = []

            def emit(self, name, value=None):
                self.names.append(name)

        heard = Heard()
        rs.Rescue.signals = heard
        try:
            random.seed(800)
            game, cv, bot = rs.Rescue(), gfx.Canvas(), Carrier()
            now, frames = 0, 0
            game.step(now, True, True)  # the title's press
            while game.state != gfx.OVER and frames < 20000:
                now += 40
                frames += 1
                held = bot(game.rules)
                game.step(now, held, held)
                cv.start()
                game.draw(cv)
        finally:
            rs.Rescue.signals = None
        self.assertEqual(gfx.OVER, game.state)
        self.assertEqual(game.rules.points, game.score)
        for name in ("siren", "whoosh", "boom", "pickup", "cheer", "die"):
            self.assertIn(name, heard.names)
        self.assertTrue({"help", "help_child"} & set(heard.names))
        self.assertTrue(set(heard.names) - {"die"} <= set(rs.Rescue.cues))

    def test_the_title_s_rules_fit_the_screen_on_two_lines(self):
        import gfx  # noqa: E402
        lines = gfx.hint_lines(rs.Rescue.hint)
        self.assertEqual(("tap turns, hold sprays,", "carry people to the station"), lines)
        self.assertTrue(all(8 * len(line) <= gfx.WIDTH for line in lines))
        self.assertEqual(("tap to play",), gfx.hint_lines("tap to play"))



if __name__ == "__main__":
    unittest.main()
