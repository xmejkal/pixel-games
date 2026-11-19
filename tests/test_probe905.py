"""probe905_switch.py (P905): the switch prototype on the Mac, with no board. The wrapped FIRE buttons, the edge of a
lean, the seven ways to switch, each threshold pinned on both sides 1 ms or 1 px apart. Run from the repository root:
python3 -B -m unittest tests.test_probe905."""

import ast
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))  # box
sys.path.append(REPO)  # the probe, last: the root's engine/ is the submodule, games/engine the package

from drawing_tft import DrawingTft  # noqa: E402,F401  first: it puts games/ and the stubs on the path

if not hasattr(time, "ticks_add"):  # the stubs give ticks_diff, ticks_us and ticks_ms; app.run and Round add
    time.ticks_add = lambda a, b: a + b

import app  # noqa: E402
import box  # noqa: E402
import gfx  # noqa: E402
import probe905_switch as probe  # noqa: E402
from engine import actions as engine_actions  # noqa: E402
from test_actions import FakeButton, FakeEncoder, FakeStick  # noqa: E402
from test_probe904 import Board  # noqa: E402  the fake runner of P904's probe

T0 = 7919  # ms: the first frame's clock in a test, no round number


class Fire:
    """An Action as the map folds it: pressed and held."""

    def __init__(self, pressed=False, held=False):
        self.pressed, self.held = pressed, held


def frame(fire=False, held=None, pick=False, turn=0, x=0, y=0):
    """One frame's Actions record: FIRE pushed (and held unless held says), PICK pushed, the knob's turn, the axes."""
    return types.SimpleNamespace(fire=Fire(fire, fire if held is None else held), pick=Fire(pick, pick), turn=turn,
                                 x=x, y=y)


def seen(pushed=False, held=False):
    """A wrapped button's last update, as Seen keeps it."""
    return types.SimpleNamespace(pushed=pushed, held=held)


NONE = seen()


class SeenTest(unittest.TestCase):
    """Seen: a FIRE button wrapped, so the game tells BOOT from the click."""

    def test_update_answers_the_push_and_keeps_it_and_the_level(self):
        button = FakeButton(True, False)
        wrapped = probe.Seen(button)
        button.held = True
        self.assertIs(True, wrapped.update(T0))
        self.assertEqual((True, True), (wrapped.pushed, wrapped.held))
        button.held = False
        self.assertIs(False, wrapped.update(T0 + 41))
        self.assertEqual((False, False), (wrapped.pushed, wrapped.held))
        self.assertEqual(2, button.updates)

    def test_forget_goes_through_to_the_button_and_refreshes_the_level(self):
        button = FakeButton(True)
        wrapped = probe.Seen(button)
        button.held = True
        wrapped.update(T0)
        button.held = False
        wrapped.forget()
        self.assertEqual(1, button.forgets)
        self.assertEqual((False, False), (wrapped.pushed, wrapped.held))

    def test_the_action_map_folds_the_wrapped_buttons_as_its_own(self):
        boot, click = FakeButton(False, True), FakeButton(True, False)
        click.held = True
        wrapped = probe.Seen(boot), probe.Seen(click)
        actions = engine_actions.ActionMap(wrapped, ())
        first = actions.poll(T0)
        self.assertEqual((True, True), (first.fire.pressed, first.fire.held))
        self.assertEqual((False, True), (wrapped[0].pushed, wrapped[1].pushed))
        click.held = False
        second = actions.poll(T0 + 41)
        self.assertEqual((True, False), (second.fire.pressed, second.fire.held))
        self.assertEqual((True, False), (wrapped[0].pushed, wrapped[1].pushed))


class LeanEdgeTest(unittest.TestCase):
    """LeanEdge: one answer at each new lean of an axis."""

    def reads(self, values, start=None):
        edge = probe.LeanEdge()
        if start is not None:
            edge.reset(start)
        return [edge.read(v) for v in values]

    def test_the_lean_and_the_rest_are_the_engines_lean_and_20(self):
        self.assertEqual((engine_actions.LEAN, 20), (probe.LEAN, probe.LEAN_REST))

    def test_a_lean_that_stays_answers_once(self):
        self.assertEqual([1, 0, 0, 0], self.reads([73, 88, 100, 41]))

    def test_a_tilt_of_39_answers_nothing_and_40_answers(self):
        self.assertEqual([0, 0, 1], self.reads([3, 39, 40]))
        self.assertEqual([0, 0, -1], self.reads([-3, -39, -40]))

    def test_a_rest_at_20_does_not_rearm_it_and_a_rest_at_19_does(self):
        self.assertEqual([1, 0, 0], self.reads([57, 20, 63]))  # inside: 20 is no rest
        self.assertEqual([1, 0, 1], self.reads([57, 19, 63]))  # inside: 19 rests
        self.assertEqual([-1, 0, 0, 0, -1], self.reads([-57, -20, -63, -19, -44]))

    def test_up_straight_to_down_answers_twice_and_up_is_minus_1(self):
        self.assertEqual([-1, 1, -1], self.reads([-61, 52, -77]))

    def test_reset_on_a_leaning_axis_answers_nothing_until_a_new_lean(self):
        self.assertEqual([0, 0, 0, 1], self.reads([66, 91, 7, 45], start=58))
        self.assertEqual([0, 1], self.reads([-71, 45], start=-58))  # down after up is a new lean
        self.assertEqual([1], self.reads([47], start=33))  # 33 is no lean: 47 is a new one


def way(name):
    """A fresh way of the name, from WAYS."""
    return [w for w in probe.WAYS if w.name == name][0]()


def read(w, now, actions=None, boot=NONE, click=NONE):
    """The way's answer to one frame: (steps, acts)."""
    w.read(now, actions or frame(), boot, click)
    return w.steps, w.acts


class WaysTest(unittest.TestCase):
    """The seven ways, each on its own frames."""

    def test_the_seven_ways_in_the_tables_order_with_their_labels(self):
        self.assertEqual(["stick", "click", "double", "hold", "pick", "knob", "auto"], [w.name for w in probe.WAYS])
        self.assertEqual(["STICK UP/DOWN", "STICK CLICK", "DOUBLE TAP", "HOLD FIRE", "PICK (D14)", "KNOB",
                          "AUTO (control)"], [w.label for w in probe.WAYS])
        self.assertEqual([False, True, True, True, True, False, True], [w.wraps for w in probe.WAYS])
        self.assertEqual([False] * 6 + [True], [w.control for w in probe.WAYS])

    def test_each_hint_is_one_line_of_the_bar_and_the_picks_says_never_hold(self):
        for w in probe.WAYS:
            with self.subTest(way=w.name):
                self.assertLessEqual(len(w.hint), 40)
                self.assertTrue(w.hint)
        self.assertIn("never hold", way("pick").hint)
        self.assertIn("one way FIREMAN, other way CHILD", way("knob").hint)

    def test_the_stick_steps_up_minus_1_and_down_plus_1_once_a_lean_and_fire_acts(self):
        w = way("stick")
        w.reset(T0, frame(), NONE, NONE)
        self.assertEqual([(-1, False), (0, False), (0, False), (1, False), (0, True)],
                         [read(w, T0 + 41 * k, a) for k, a in enumerate(
                             [frame(y=-64), frame(y=-88), frame(y=11), frame(y=53), frame(fire=True, y=50)])])

    def test_the_click_takes_the_other_and_boot_acts(self):
        w = way("click")
        w.reset(T0, frame(), NONE, NONE)
        self.assertEqual((1, False), read(w, T0 + 41, frame(fire=True), click=seen(True, True)))
        self.assertEqual((0, True), read(w, T0 + 83, frame(fire=True), boot=seen(True, True)))
        self.assertEqual((1, True), read(w, T0 + 127, frame(fire=True), boot=seen(True, True), click=seen(True, True)))
        self.assertEqual((0, False), read(w, T0 + 167, frame(held=True), boot=seen(False, True)))

    def test_pick_takes_the_other_and_fire_acts(self):
        w = way("pick")
        w.reset(T0, frame(), NONE, NONE)
        self.assertEqual([(1, False), (0, True), (0, False)],
                         [read(w, T0 + 41 * k, a) for k, a in enumerate([frame(pick=True), frame(fire=True), frame()])])

    def test_the_knob_steps_by_its_turn_and_fire_acts(self):
        w = way("knob")
        w.reset(T0, frame(), NONE, NONE)
        self.assertEqual([(1, False), (-2, False), (0, True)],
                         [read(w, T0 + 41 * k, a) for k, a in enumerate(
                             [frame(turn=1), frame(turn=-2), frame(fire=True)])])

    def test_auto_never_steps_and_fire_acts(self):
        w = way("auto")
        w.reset(T0, frame(), NONE, NONE)
        self.assertEqual([(0, False), (0, True), (0, False)],
                         [read(w, T0 + 41 * k, a) for k, a in enumerate(
                             [frame(y=77, turn=3, pick=True), frame(fire=True), frame(x=-90)])])

    def test_a_second_push_300_ms_after_the_first_switches_and_301_does_not(self):
        w = way("double")
        w.reset(T0, frame(), NONE, NONE)
        self.assertEqual((0, False), read(w, T0 + 13, frame(fire=True)))
        self.assertEqual((1, False), read(w, T0 + 13 + 300, frame(fire=True)))  # inside: exactly 300 switches
        self.assertEqual((0, False), read(w, T0 + 13 + 300 + 299, frame()))  # nothing waits: no act
        w = way("double")
        w.reset(T0, frame(), NONE, NONE)
        read(w, T0 + 13, frame(fire=True))
        self.assertEqual((0, True), read(w, T0 + 13 + 301, frame(fire=True)))  # too late: the first acts, a new first
        self.assertEqual((1, False), read(w, T0 + 13 + 301 + 177, frame(fire=True)))

    def test_one_push_acts_at_300_ms_and_not_at_299(self):
        w = way("double")
        w.reset(T0, frame(), NONE, NONE)
        read(w, T0 + 17, frame(fire=True))
        self.assertEqual((0, False), read(w, T0 + 17 + 299, frame()))  # outside: 299 waits on
        self.assertEqual((0, True), read(w, T0 + 17 + 300, frame()))  # inside: 300 acts
        self.assertEqual((0, False), read(w, T0 + 17 + 343, frame()))  # once

    def test_after_a_double_tap_a_third_push_is_a_first_one(self):
        w = way("double")
        w.reset(T0, frame(), NONE, NONE)
        got = [read(w, T0 + ms, frame(fire=True)) for ms in (23, 131, 239)]
        self.assertEqual([(0, False), (1, False), (0, False)], got)
        self.assertEqual((0, True), read(w, T0 + 239 + 300, frame()))

    def test_a_hold_of_399_ms_does_not_switch_and_400_does_once(self):
        w = way("hold")
        w.reset(T0, frame(), NONE, NONE)
        self.assertEqual((0, False), read(w, T0 + 7, frame(fire=True)))
        self.assertEqual((0, False), read(w, T0 + 7 + 399, frame(held=True)))  # outside: 399 is no hold
        self.assertEqual((1, False), read(w, T0 + 7 + 400, frame(held=True)))  # inside: 400 switches
        self.assertEqual((0, False), read(w, T0 + 7 + 853, frame(held=True)))  # once for each hold
        self.assertEqual((0, False), read(w, T0 + 7 + 901, frame()))  # its release does not act

    def test_a_release_at_399_ms_acts_and_at_401_does_not(self):
        w = way("hold")
        w.reset(T0, frame(), NONE, NONE)
        read(w, T0 + 7, frame(fire=True))
        self.assertEqual((0, True), read(w, T0 + 7 + 399, frame()))  # inside: a release at 399 acts
        read(w, T0 + 1009, frame(fire=True))
        self.assertEqual((1, False), read(w, T0 + 1009 + 401, frame()))  # outside: 401 is a hold, no act

    def test_a_hold_lasts_while_either_fire_button_is_down(self):
        w = way("hold")
        w.reset(T0, frame(), NONE, NONE)
        read(w, T0 + 7, frame(fire=True))
        self.assertEqual((0, False), read(w, T0 + 7 + 211, frame(fire=True, held=True)))  # the other button: no new hold
        self.assertEqual((1, False), read(w, T0 + 7 + 433, frame(held=True)))

    def test_a_push_with_no_level_acts_at_once(self):
        w = way("hold")
        w.reset(T0, frame(), NONE, NONE)
        self.assertEqual((0, True), read(w, T0 + 7, frame(fire=True, held=False)))
        self.assertEqual((0, False), read(w, T0 + 7 + 433, frame()))

    def test_each_ways_reset_starts_from_the_inputs_as_they_are(self):
        # a lean that is there, a FIRE that is down and a push of this frame give nothing in the next frame
        down = frame(fire=True, pick=True, turn=1, y=73)
        for w in probe.WAYS:
            with self.subTest(way=w.name):
                w = w()
                read(w, T0, frame(fire=True))  # a push waits in the double tap, a hold starts in the hold
                w.reset(T0 + 41, down, seen(True, True), seen(True, True))
                self.assertEqual((0, False), read(w, T0 + 83, frame(held=True, y=79), seen(False, True),
                                                  seen(False, True)))
                self.assertEqual((0, False), read(w, T0 + 83 + 600, frame(held=True, y=81), seen(False, True),
                                                  seen(False, True)))


class TallyTest(unittest.TestCase):
    """The count of one round: each switch and each act gets its word, and a task is wrong once."""

    def clean(self, tally, n=1):
        for _ in range(n):
            tally.start()
            tally.switch(True)
            tally.act(True, True)

    def test_a_clean_task_is_one_first_switch_and_a_reached_act(self):
        tally = probe.Tally()
        tally.start()
        self.assertEqual(probe.FIRST, tally.switch(True))
        self.assertEqual(probe.REACHED, tally.act(True, True))
        self.assertEqual((1, 1, 0, 1), (tally.streak, tally.best, tally.wrong, tally.tasks))

    def test_an_extra_switch_makes_the_task_wrong_and_the_streak_0_at_once(self):
        tally = probe.Tally()
        self.clean(tally, 4)
        tally.start()
        tally.switch(True)
        self.assertEqual(probe.EXTRA, tally.switch(False))
        self.assertEqual((0, 4, 1, 4), (tally.streak, tally.best, tally.wrong, tally.tasks))

    def test_the_switch_back_is_neither_and_a_fourth_switch_is_extra_but_the_task_is_wrong_once(self):
        tally = probe.Tally()
        tally.start()
        self.assertEqual([probe.FIRST, probe.EXTRA, probe.BACK, probe.EXTRA, probe.BACK],
                         [tally.switch(to) for to in (True, False, True, False, True)])
        self.assertEqual(1, tally.wrong)
        self.assertEqual(probe.REACHED, tally.act(True, True))
        self.assertEqual((0, 1, 1), (tally.streak, tally.wrong, tally.tasks))

    def test_an_act_of_the_figure_the_task_does_not_want_is_other_and_wrong(self):
        tally = probe.Tally()
        self.clean(tally, 3)
        tally.start()
        self.assertEqual(probe.OTHER, tally.act(False, True))
        self.assertEqual((0, 1), (tally.streak, tally.wrong))
        self.assertEqual(probe.OTHER, tally.act(False, False))  # away from the ring too
        self.assertEqual(1, tally.wrong)

    def test_an_act_of_the_wanted_figure_away_from_the_ring_is_stray_and_not_wrong(self):
        tally = probe.Tally()
        self.clean(tally, 2)
        tally.start()
        tally.switch(True)
        self.assertEqual(probe.STRAY, tally.act(True, False))
        self.assertEqual(probe.REACHED, tally.act(True, True))
        self.assertEqual((3, 0, 3), (tally.streak, tally.wrong, tally.tasks))

    def test_a_task_with_an_extra_and_an_other_is_wrong_once(self):
        tally = probe.Tally()
        tally.start()
        self.assertEqual(probe.OTHER, tally.act(False, True))
        tally.switch(True)
        self.assertEqual(probe.EXTRA, tally.switch(False))
        self.assertEqual(1, tally.wrong)

    def test_the_streak_starts_again_after_a_wrong_task_and_the_best_stays(self):
        tally = probe.Tally()
        self.clean(tally, 2)
        tally.start()
        tally.act(False, True)
        tally.switch(True)
        tally.act(True, True)
        self.clean(tally)
        self.assertEqual((1, 2, 1, 4), (tally.streak, tally.best, tally.wrong, tally.tasks))

    def test_a_pass_at_a_streak_of_10_and_not_at_9(self):
        tally = probe.Tally()
        self.clean(tally, 9)
        self.assertFalse(tally.passed())  # outside: 9
        self.clean(tally)
        self.assertTrue(tally.passed())  # inside: 10
        self.assertEqual((10, 3), (probe.STREAK_TO_PASS, probe.WRONG_MAX))

    def test_a_fail_at_the_event_of_the_third_wrong_task_and_not_at_the_second(self):
        tally = probe.Tally()
        for _ in range(2):
            tally.start()
            tally.switch(True)
            tally.switch(False)
            tally.switch(True)
            tally.act(True, True)
        self.assertFalse(tally.failed())  # outside: 2 wrong tasks
        tally.start()
        tally.switch(True)
        self.assertFalse(tally.failed())
        tally.switch(False)
        self.assertTrue(tally.failed())  # inside: the third

    def test_each_word_of_the_log_is_its_constants(self):
        self.assertEqual(["first", "extra", "back", "same", "reached", "other", "stray"],
                         [probe.WORDS[k] for k in (probe.FIRST, probe.EXTRA, probe.BACK, probe.SAME, probe.REACHED,
                                                   probe.OTHER, probe.STRAY)])


class Dice:
    """gfx.Dice stood in: below(n) answers the next of its values, which must be under n."""

    def __init__(self, *values):
        self.values, self.asked = list(values), []

    def below(self, n):
        self.asked.append(n)
        v = self.values.pop(0)
        assert v < n, (v, n)
        return v


class RingTest(unittest.TestCase):
    """ring_x: the next ring on the walk, at least TASK_MIN_PX from the wanted figure, and the reach."""

    def test_its_values_are_the_plans(self):
        self.assertEqual((60, 8, 96, 304), (probe.TASK_MIN_PX, probe.REACH_PX, probe.WALK_LEFT, probe.WALK_RIGHT))

    def test_one_draw_picks_a_place_left_or_right_of_the_figure(self):
        # x 200: 96 to 140 on the left (45 places), 260 to 304 on the right (45)
        for value, ring in ((0, 96), (44, 140), (45, 260), (89, 304), (17, 113)):
            with self.subTest(value=value):
                dice = Dice(value)
                self.assertEqual(ring, probe.ring_x(dice, 200))
                self.assertEqual([90], dice.asked)

    def test_a_ring_is_60_px_away_and_never_59_and_always_on_the_walk(self):
        import gfx

        for x in (96, 131, 200, 263, 304):
            with self.subTest(x=x):
                dice = gfx.Dice(905)
                rings = [probe.ring_x(dice, x) for _ in range(3000)]
                self.assertEqual(60, min(abs(r - x) for r in rings))  # inside: 60; 59 never
                self.assertEqual(96 if x - 60 >= 96 else x + 60, min(rings))
                self.assertEqual(304 if x + 60 <= 304 else x - 60, max(rings))

    def test_a_ring_is_in_reach_for_a_figure_at_96_at_200_and_at_304(self):
        for x in (96, 200, 304):
            with self.subTest(x=x):
                dice = gfx_dice()
                for _ in range(500):
                    ring = probe.ring_x(dice, x)
                    self.assertTrue(probe.WALK_LEFT <= ring <= probe.WALK_RIGHT, ring)

    def test_a_reach_at_8_px_and_not_at_9(self):
        self.assertEqual([True, True, True, False, False], [probe.reaches(x, 173) for x in (165, 181, 173, 164, 182)])


def gfx_dice():
    import gfx

    return gfx.Dice(1284)


RUN_R = tuple(("run_r%d" % i, 26) for i in range(12))
RUN_L = tuple(("run_l%d" % i, 26) for i in range(12))
ACT_R = tuple(("act_r%d" % i, 40) for i in range(6))
ACT_L = tuple(("act_l%d" % i, 40) for i in range(6))
STAND = (("stand_r", 38), ("stand_l", 38))
STEPS = (37, 23, 41, 60, 17)  # ms: 56 px a second times none of them is a whole px


def figure(x=200, facing=1, stands=STAND):
    """A figure at the fireman's speed and stride, on stand-in pictures."""
    return probe.SteeredFigure(x, facing, 56, 41, 30, (RUN_R, RUN_L), (ACT_R, ACT_L), 83, stands)


class SteeredFigureTest(unittest.TestCase):
    """One figure that the stick's x walks."""

    def test_it_walks_in_whole_px_with_a_carry_in_thousandths(self):
        # 56 px a second over 178 ms is 9.968 px. To the right the floors give 9 px and keep 968 thousandths; to the
        # left each step floors toward the left: 10 px, and 32 thousandths kept, as games/rescue.py's Fireman.run
        for lean, x, ran, rest in ((1, 209, 9, 968), (-1, 190, 10, 32)):
            with self.subTest(lean=lean):
                f = figure()
                for ms in STEPS:
                    f.walk(ms, lean)
                self.assertEqual((x, ran, rest, lean), (f.x, f.ran, f.rest, f.facing))

    def test_a_lean_of_0_stands_and_keeps_its_facing(self):
        f = figure(facing=-1)
        f.walk(43, 0)
        self.assertEqual((200, 0, -1), (f.x, f.ran, f.facing))

    def test_it_stops_at_both_ends_of_the_walk(self):
        for lean, start, end in ((1, 290, 304), (-1, 110, 96)):
            with self.subTest(lean=lean):
                f = figure(start)
                for _ in range(20):
                    f.walk(47, lean)
                self.assertEqual((end, abs(end - start), 0), (f.x, f.ran, f.rest))

    def test_its_run_pose_follows_the_px_it_ran_and_its_side_its_facing(self):
        f = figure()
        f.walk(41, 1)  # it runs: the run's poses
        for ran, pose in ((0, 0), (3, 0), (4, 1), (20, 5), (41, 0), (45, 1), (81, 11)):
            for facing, side in ((1, "r"), (-1, "l")):
                with self.subTest(ran=ran, facing=facing):
                    f.ran, f.facing = ran, facing
                    self.assertEqual(("run_%s%d" % (side, pose), 26), f.picture(-1))

    def test_standing_it_shows_its_stand_picture_or_its_run_pose_where_it_stopped(self):
        f = figure(facing=-1)
        f.ran = 20
        f.walk(43, 0)
        self.assertEqual(("stand_l", 38), f.picture(-1))
        f = figure(stands=None)
        f.ran = 20
        f.walk(43, 0)
        self.assertEqual(("run_r5", 26), f.picture(-1))

    def test_acting_it_shows_its_act_poses_by_the_ms_since_the_act(self):
        f = figure()
        self.assertEqual([("act_r0", 40), ("act_r0", 40), ("act_r1", 40), ("act_r4", 40)],
                         [f.picture(ms) for ms in (0, 82, 83, 399)])

    def test_each_picture_is_one_pair_made_once(self):
        f = figure()
        f.walk(41, 1)
        self.assertIs(RUN_R[f.ran * 12 // 41 % 12], f.picture(-1))


class FallbackDice:
    """Its values first, then gfx.Dice's stream."""

    def __init__(self, *values):
        self.values, self.dice = list(values), gfx_dice()

    def below(self, n):
        return self.values.pop(0) if self.values else self.dice.below(n)


class Play:
    """One round on scripted frames: its lines in a list (the emit), a clock that moves 41 ms a frame unless a frame
    names its time, and the fireman (at 140, active first) and the child (at 260) on stand-in pictures."""

    def __init__(self, name, *dice):
        self.lines, self.now = [], T0
        self.figures = [figure(140, 1), figure(260, -1, stands=None)]
        self.round = probe.Round(way(name), self.figures, FallbackDice(*dice), self.lines.append, T0)

    def frame(self, at=None, ms=41, boot=NONE, click=NONE, **inputs):
        self.now = T0 + at if at is not None else self.now + ms
        self.round.step(self.now, ms, frame(**inputs), boot, click)
        return self

    def ready(self):
        return self.frame(at=600)

    def to_ring(self):
        """The wanted figure stands on its ring."""
        self.figures[self.round.wanted].x = self.round.ring
        return self

    def task(self, lean):
        """A clean task: a lean toward the wanted figure, a rest, the ring, FIRE."""
        self.frame(y=lean).to_ring().frame(fire=True)
        return self


EXAMPLE = """p905 round stick starts
p905 task 1 wants child at 152
p905 switch child first
p905 act child stray
p905 act child reached
p905 task 1 clean streak 1 wrong 0
p905 task 2 wants fireman at 236
p905 act child other
p905 switch fireman first
p905 switch child extra
p905 switch child same
p905 switch fireman back
p905 act fireman reached
p905 task 2 wrong streak 0 wrong 1""".splitlines()  # the plan's example, from the board's lines on


class RoundTest(unittest.TestCase):
    """One round of one way on scripted frames, with no drawing."""

    def test_its_values_are_the_plans(self):
        self.assertEqual((600, 400, 400, 20000, (140, 260), ("fireman", "child")),
                         (probe.READY_MS, probe.ACT_MS, probe.MARK_MS, probe.IDLE_MS, probe.START_X, probe.NAMES))

    def test_lean_is_the_engines_lean(self):
        for v in (-100, -41, -40, -39, -1, 0, 1, 39, 40, 41, 100):
            self.assertEqual(engine_actions.lean(v), probe.lean(v), v)

    def test_ready_drops_the_inputs_of_599_ms_and_reads_at_600(self):
        p = Play("stick")
        p.frame(at=311, fire=True, y=-80, x=90).frame(at=599, fire=True)
        self.assertEqual(["p905 round stick starts"], p.lines)
        self.assertEqual((140, 260), (p.figures[0].x, p.figures[1].x))
        p.frame(at=600, y=66)
        self.assertEqual(["p905 task 1 wants", "p905 switch child first"], [line[:17] if "task" in line else line
                                                                              for line in p.lines[1:]])

    def test_the_way_starts_from_the_inputs_of_readys_last_frame(self):
        p = Play("stick")
        p.frame(at=599, y=66).frame(at=600, y=71).frame(at=641, y=88)
        self.assertEqual(2, len(p.lines))  # the round and its first task: the lean was there before
        p = Play("double")
        p.frame(at=599, fire=True).frame(at=600).frame(at=941)
        self.assertEqual(2, len(p.lines))  # READY's push waits for no second one

    def test_an_act_and_a_switch_in_one_frame_at_the_ring_give_a_clean_task_and_the_next_tasks_first(self):
        p = Play("stick").ready()
        p.frame(y=70).to_ring().frame(fire=True, y=-70)
        self.assertEqual(["p905 act child reached", "p905 task 1 clean streak 1 wrong 0"], p.lines[3:5])
        self.assertTrue(p.lines[5].startswith("p905 task 2 wants fireman at "), p.lines[5])
        self.assertEqual("p905 switch fireman first", p.lines[6])
        self.assertEqual((1, 0), (p.round.tally.streak, p.round.tally.wrong))

    def test_the_same_pair_at_a_tasks_start_gives_other_then_first(self):
        p = Play("stick").ready()
        p.frame(fire=True, y=70)
        self.assertEqual(["p905 act fireman other", "p905 switch child first"], p.lines[2:])
        self.assertEqual((0, 1), (p.round.tally.streak, p.round.tally.wrong))

    def test_the_lines_of_a_wrong_task_and_of_a_round_that_passes_are_the_plans_example(self):
        p = Play("stick", 56, 36).ready()
        p.frame(y=70).frame(fire=True)  # the child: away from its ring
        p.to_ring().frame(fire=True)
        p.frame(fire=True)  # the child, but the task wants the fireman
        p.frame(y=-70).frame().frame(y=70).frame().frame(y=70).frame().frame(y=-70)
        p.to_ring().frame(fire=True)
        self.assertEqual(EXAMPLE, p.lines[:len(EXAMPLE)])
        for k in range(10):
            p.frame().task(70 if k % 2 == 0 else -70)
        self.assertEqual("p905 task 12 clean streak 10 wrong 1", p.lines[-2])
        self.assertEqual("p905 round stick ends pass streak 10 best 10 tasks 12 wrong 1", p.lines[-1])
        self.assertEqual(probe.PASS, p.round.end)
        tasks = [line for line in p.lines if " task " in line and " wants " not in line]
        self.assertEqual(["p905 task %d clean streak %d wrong 1" % (k + 3, k + 1) for k in range(10)], tasks[2:])
        lines = len(p.lines)
        p.frame(fire=True, y=70)
        self.assertEqual(lines, len(p.lines))  # an ended round reads nothing

    def test_a_round_ends_with_fail_at_the_event_of_its_third_wrong_task_and_the_frame_stops_there(self):
        p, on = Play("click").ready(), seen(True, True)
        for _ in range(2):  # an other, then the switch, the ring and the act
            p.frame(boot=on).frame(click=on).to_ring().frame(boot=on)
        self.assertEqual((2, 2, probe.PLAYING), (p.round.tally.wrong, p.round.tally.tasks, p.round.end))
        lines = len(p.lines)
        p.frame(boot=on, click=on)  # the act is the event; the click in its frame is not read
        self.assertEqual(["p905 act fireman other", "p905 round click ends fail streak 0 best 0 tasks 2 wrong 3"],
                         p.lines[lines:])
        self.assertEqual(probe.FAIL, p.round.end)

    def test_idle_at_20000_ms_and_not_at_19999_from_readys_end(self):
        p = Play("knob").ready()
        p.frame(at=600 + 19999)
        self.assertEqual(probe.PLAYING, p.round.end)  # outside
        p.frame(at=600 + 20000)  # inside
        self.assertEqual("p905 round knob ends idle streak 0 best 0 tasks 0 wrong 0", p.lines[-1])
        self.assertEqual(probe.IDLE, p.round.end)

    def test_idle_is_counted_from_the_last_tasks_end(self):
        p = Play("knob").ready()
        p.frame(at=13001, turn=1).to_ring().frame(at=17003, fire=True)
        p.frame(at=17003 + 19999)
        self.assertEqual(probe.PLAYING, p.round.end)
        p.frame(at=17003 + 20000)
        self.assertEqual(probe.IDLE, p.round.end)

    def test_auto_switches_at_each_tasks_start_and_ends_with_control_never_pass(self):
        p = Play("auto").ready()
        self.assertEqual("p905 switch child first", p.lines[2])
        for _ in range(10):
            p.to_ring().frame(fire=True)
        self.assertEqual("p905 round auto ends control streak 10 best 10 tasks 10 wrong 0", p.lines[-1])
        self.assertEqual(probe.CONTROL, p.round.end)
        self.assertEqual([], [line for line in p.lines if "pass" in line])
        self.assertEqual(10, len([line for line in p.lines if line.endswith(" first")]))

    def test_the_knob_and_the_stick_stop_at_the_lists_ends_and_say_same(self):
        p = Play("knob").ready()
        p.frame(turn=-1).frame(turn=2).frame(turn=3)
        self.assertEqual(["p905 switch fireman same", "p905 switch child first", "p905 switch child same"],
                         p.lines[2:])

    def test_a_button_way_takes_the_other_figure(self):
        p = Play("click").ready()
        on = seen(True, True)
        p.frame(click=on).frame().frame(click=on).frame().frame(click=on)
        self.assertEqual(["p905 switch child first", "p905 switch fireman extra", "p905 switch child back"],
                         p.lines[2:])

    def test_only_the_active_figure_walks_with_the_sticks_x(self):
        p = Play("stick").ready()
        p.frame(x=80, ms=43)
        self.assertEqual((140 + 56 * 43 // 1000, 260), (p.figures[0].x, p.figures[1].x))
        self.assertEqual((1, 0), (p.figures[0].lean, p.figures[1].lean))
        p.frame(y=70).frame(x=-39, ms=47).frame(x=-40, ms=47)
        self.assertEqual(260 - 3, p.figures[1].x)  # -39 is no lean, -40 is: 2.632 px floor to 3 to the left

    def test_the_act_shows_for_400_ms_and_the_wrong_mark_for_400_ms_on_the_frames_clock(self):
        p = Play("stick").ready()
        p.frame(at=1013, fire=True)
        self.assertEqual(0, p.round.act_ms(probe.FIREMAN))
        self.assertEqual(-1, p.round.act_ms(probe.CHILD))
        self.assertTrue(p.round.marking())
        p.frame(at=1013 + 399)
        self.assertEqual((399, True), (p.round.act_ms(probe.FIREMAN), p.round.marking()))  # inside
        p.frame(at=1013 + 400)
        self.assertEqual((-1, False), (p.round.act_ms(probe.FIREMAN), p.round.marking()))  # outside

    def test_a_stray_act_shows_no_wrong_mark(self):
        p = Play("stick").ready()
        p.frame(y=70).frame(fire=True)
        self.assertEqual("p905 act child stray", p.lines[-1])
        self.assertFalse(p.round.marking())
        self.assertEqual(0, p.round.act_ms(probe.CHILD))


class MenuTest(unittest.TestCase):
    """The menu: the seven ways and QUIT, with no drawing."""

    def menu(self):
        m = probe.Menu()
        m.reset(frame())
        return m

    def move(self, m, *ys):
        for y in ys:
            m.step(frame(y=y))
        return m.cursor

    def test_it_holds_a_row_for_each_way_and_quit_last(self):
        self.assertEqual(len(probe.WAYS), probe.QUIT)
        self.assertEqual((0, [0] * 7, [False] * 7), (self.menu().cursor, self.menu().best, self.menu().marked))

    def test_the_cursor_moves_one_row_for_each_new_lean_and_stops_at_both_ends(self):
        m = self.menu()
        self.assertEqual(1, self.move(m, 70, 88, 95))  # one lean: one row
        self.assertEqual(3, self.move(m, 3, 70, 5, 70))
        self.assertEqual(7, self.move(m, *([3, 70] * 9)))  # stops at QUIT
        self.assertEqual(0, self.move(m, *([3, -70] * 11)))  # stops at the first way

    def test_fire_starts_the_rows_way(self):
        m = self.menu()
        self.move(m, 70, 3, 70, 3, 70, 3)
        self.assertIsNone(m.step(frame(held=True)))
        self.assertEqual(3, m.step(frame(fire=True)))

    def test_quit_needs_fire_twice_and_a_cursor_move_takes_the_first_press_back(self):
        m = self.menu()
        self.move(m, *([70, 3] * 7))
        self.assertEqual(probe.QUIT, m.cursor)
        self.assertIsNone(m.step(frame(fire=True)))
        self.assertTrue(m.armed)
        self.assertEqual(probe.QUIT, m.step(frame(fire=True)))
        m = self.menu()
        self.move(m, *([70, 3] * 7))
        m.step(frame(fire=True))
        self.move(m, -70, 3, 70, 3)  # away and back: the first press is gone
        self.assertFalse(m.armed)
        self.assertIsNone(m.step(frame(fire=True)))
        self.assertEqual(probe.QUIT, m.step(frame(fire=True)))

    def test_reset_with_a_leaning_stick_and_fire_down_moves_nothing_and_starts_nothing(self):
        m = self.menu()
        self.move(m, 70, 3, 70)
        m.reset(frame(fire=True, y=75))
        self.assertIsNone(m.step(frame(held=True, y=80)))
        self.assertEqual(2, m.cursor)
        m = self.menu()
        self.move(m, *([70, 3] * 7))
        m.step(frame(fire=True))
        m.reset(frame())  # the menu comes back: QUIT's first press is gone
        self.assertIsNone(m.step(frame(fire=True)))

    def test_it_records_each_ways_best_and_its_mark(self):
        m = self.menu()
        m.record(2, probe.FAIL, 4)
        m.record(2, probe.PASS, 10)
        m.record(2, probe.IDLE, 6)
        m.record(6, probe.CONTROL, 10)
        m.record(5, probe.IDLE, 3)
        self.assertEqual([0, 0, 10, 0, 0, 3, 10], m.best)
        self.assertEqual([False, False, True, False, False, False, True], m.marked)


class Pictures:
    """pictures stood in: every set is loaded, and every draw is recorded and answers True."""

    load_ms = 0

    def __init__(self):
        self.drawn = []

    def load(self, game=None, only=None):
        return True

    def load_steps(self, game=None, only=None):
        return iter(())

    def free(self):
        pass

    def draw(self, cv, name, x, y, alpha=255):
        self.drawn.append((name, x, y))
        return True


class WordsCanvas(gfx.Canvas):
    """gfx.Canvas that also keeps the words of each text and big call: words since its start, seen since it was made.
    A kept rect's words show only in the frame that draws it. big records one op with its words in place of its
    glyphs' fills, which need the board's font (the stub's framebuf has none), so a big word shows in the ops."""

    seen = None

    def start(self):
        gfx.Canvas.start(self)
        self.words = []
        if self.seen is None:
            self.seen = []

    def text(self, words, x, y, c):
        self.words.append(words)
        self.seen.append(words)
        gfx.Canvas.text(self, words, x, y, c)

    def big(self, words, x, y, c, scale=2):
        self.words.append(words)
        self.seen.append(words)
        self.ops.append((x, y, x + 8 * scale * len(words), y + 8 * scale, 3, words, c, x, y))


class Out:
    """The App's output: each frame the game draws on a WordsCanvas, as Game.draw does on the board."""

    def __init__(self):
        self.cv = WordsCanvas()
        self.cv.start()

    def clear(self):
        pass

    def reset(self):
        pass

    def draw(self, game, us, overlay):
        self.cv.start()
        game.draw(self.cv)


class Box:
    """The real app.App with the probe's game in a lineup of one: the FIRE buttons wrapped (Seen), PICK, the knob's
    encoder and the stick, the fakes of tests/test_actions.py, pictures stood in, and no knob in the App. The clock
    moves by each frame's ms."""

    def __init__(self, test):
        self.now, self.said, self.pictures = T0, io.StringIO(), Pictures()
        stack = contextlib.ExitStack()
        test.addCleanup(stack.close)
        stack.enter_context(contextlib.redirect_stdout(self.said))
        stack.enter_context(mock.patch.object(app, "pictures", self.pictures))
        stack.enter_context(mock.patch.dict(sys.modules, {"pictures": self.pictures}))
        stack.enter_context(mock.patch.object(app, "gc", types.SimpleNamespace(
            collect=lambda: None, mem_alloc=lambda: 279361, mem_free=lambda: 7000003)))
        stack.enter_context(mock.patch.object(time, "ticks_ms", lambda: self.now))
        self.boot, self.click, self.d14 = FakeButton(), FakeButton(), FakeButton()
        self.encoder, self.stick = FakeEncoder(), FakeStick(0, 0)
        boot, click = probe.Seen(self.boot), probe.Seen(self.click)
        self.out = Out()
        self.app = app.App(None, engine_actions.ActionMap((boot, click), (self.d14,), self.encoder, self.stick),
                           games=(probe.game_class(boot, click),), out=self.out)
        self.app.start()
        self.frame()  # out of the title: TITLE_MS is 0
        self.frame()  # the menu's reset

    def frame(self, ms=41, fire=False, held=False, boot=False, click=False, pick=False, turn=0, x=0, y=0):
        self.now += ms
        for button, pushed in ((self.boot, fire or boot), (self.click, click), (self.d14, pick)):
            button.pushes.append(pushed)
        self.boot.held = held or fire or boot
        self.click.held = click
        self.encoder.turns.append(turn)
        self.stick.x, self.stick.y = x, y
        self.app.frame()
        return self

    def lines(self):
        return [line for line in self.said.getvalue().splitlines() if line.startswith("p905 ")]

    def start(self, row):
        """The menu's cursor down to row, FIRE, and READY's 600 ms."""
        for _ in range(row - self.app.game.menu.cursor):
            self.frame(y=70).frame()
        self.frame(fire=True).frame().frame(ms=600)
        return self.app.game.round

    def to_ring(self):
        r = self.app.game.round
        r.figures[r.wanted].x = r.ring
        return self


def card(box):
    """The frame's ops from the card's first fill, which covers OVER_RECT, on."""
    x, y, w, h = gfx.OVER_RECT
    ops = box.out.cv.ops
    return ops[[i for i, op in enumerate(ops) if op[:5] == (x, y, x + w, y + h, 0)][-1]:]


class GameTest(unittest.TestCase):
    """The probe's game through app.App, with no pack: it never skips."""

    def test_the_game_is_switchtest_on_rescues_set_and_starts_in_play(self):
        box = Box(self)
        game = box.app.game
        self.assertEqual(("switchtest", ("rescue", None), 0), (game.name, game.ART, game.TITLE_MS))
        self.assertEqual(gfx.PLAY, game.state)
        self.assertIsNone(box.app.knob)
        self.assertIsNone(box.app.volume_pane)

    def test_pick_reaches_the_game_in_a_lineup_of_one(self):
        box = Box(self)
        box.start(4)
        box.frame(pick=True)
        self.assertEqual("p905 switch child first", box.lines()[-1])
        self.assertNotIn("pick switchtest", box.said.getvalue())

    def test_the_knobs_turn_reaches_the_game_with_no_knob_in_the_app(self):
        box = Box(self)
        box.start(5)
        box.frame(turn=1)
        self.assertEqual("p905 switch child first", box.lines()[-1])
        box.frame(turn=-1)
        self.assertEqual("p905 switch fireman extra", box.lines()[-1])

    def test_the_click_and_boot_reach_the_game_apart(self):
        box = Box(self)
        box.start(1)
        box.frame(boot=True)
        self.assertEqual("p905 act fireman other", box.lines()[-1])
        box.frame(click=True)
        self.assertEqual("p905 switch child first", box.lines()[-1])

    def test_a_round_draws_the_street_both_figures_the_ring_and_the_task(self):
        box = Box(self)
        box.start(0)
        box.pictures.drawn.clear()
        box.frame()
        names = [name for name, _, _ in box.pictures.drawn]
        self.assertEqual("rescue_night", names[0])
        self.assertTrue(names[1].startswith("rescue_spray_r"), names)  # the fireman stands, facing right
        self.assertTrue(names[2].startswith("rescue_child_run_l"), names)
        self.assertIn("CHILD", box.out.cv.words)

    def test_the_top_bar_is_drawn_again_when_only_the_wrong_tasks_change(self):
        box = Box(self)
        box.start(0)
        box.frame()
        self.assertEqual([], [w for w in box.out.cv.words if w.startswith("wrong ")])  # kept: not drawn again
        box.frame(fire=True)  # the fireman acts, but the task wants the child: wrong, the streak stays 0
        self.assertEqual("p905 act fireman other", box.lines()[-1])
        self.assertIn("wrong 1", box.out.cv.words)
        self.assertIn("streak 0/10", box.out.cv.words)
        box.frame()
        self.assertEqual([], [w for w in box.out.cv.words if w.startswith("wrong ")])

    def test_two_cards_with_the_same_streak_and_another_end_draw_differently_with_no_game_over(self):
        box = Box(self)
        box.start(1)
        for _ in range(500):  # no input: idle
            box.frame()
        self.assertEqual("p905 round click ends idle streak 0 best 0 tasks 0 wrong 0", box.lines()[-1])
        box.frame(ms=900)
        first = card(box)
        box.frame(fire=True).frame()  # the menu, and its reset
        box.start(1)
        for _ in range(2):  # an other, the switch, the ring and the act: two wrong tasks
            box.frame(boot=True).frame(click=True).to_ring().frame(boot=True).frame()
        box.frame(boot=True)
        self.assertEqual("p905 round click ends fail streak 0 best 0 tasks 2 wrong 3", box.lines()[-1])
        box.frame(ms=900)
        self.assertNotEqual(first, card(box))
        self.assertEqual(["IDLE", "3 WRONG"], [w for w in box.out.cv.seen if w in probe.CARD_WORDS])
        self.assertEqual([], [w for w in box.out.cv.seen if w in ("game over", "tap to retry")])
        self.assertIn("FIRE: menu", box.out.cv.seen)

    def test_after_a_passed_round_fire_at_900_ms_not_899_shows_the_menu_with_its_best_and_pass_on_its_row(self):
        box = Box(self)
        box.start(5)
        for k in range(10):
            box.frame(turn=1 if k % 2 == 0 else -1).to_ring().frame(fire=True)
        self.assertEqual("p905 round knob ends pass streak 10 best 10 tasks 10 wrong 0", box.lines()[-1])
        box.frame(ms=899, fire=True)
        self.assertEqual(gfx.OVER, box.app.game.state)  # outside
        self.assertNotIn("FIRE: menu", box.out.cv.words)
        box.frame(ms=1, fire=True)  # inside: 900
        self.assertEqual(gfx.PLAY, box.app.game.state)
        rows = [w for w in box.out.cv.words if "best" in w]
        self.assertEqual(8, len([w for w in box.out.cv.words if w.startswith(("> ", "  "))]))
        self.assertEqual([w for w in rows if w.startswith("> ")], [w for w in rows if "KNOB" in w])
        knob = [w for w in rows if "KNOB" in w][0]
        self.assertIn("best 10", knob)
        self.assertIn("PASS", knob)
        self.assertIsNone(box.app.game.round)
        self.assertEqual(5, box.app.game.menu.cursor)

    def test_the_menu_comes_back_with_its_own_reset_so_a_push_or_a_lean_then_starts_nothing(self):
        box = Box(self)
        box.start(5)
        for _ in range(500):
            box.frame()
        box.frame(ms=900, fire=True)  # the card goes
        box.frame(fire=True, y=70).frame(held=True, y=75)  # the menu's first frame: its reset drops both
        self.assertIsNone(box.app.game.round)
        self.assertEqual(5, box.app.game.menu.cursor)

    def test_quit_pressed_twice_raises_quit(self):
        box = Box(self)
        for _ in range(7):
            box.frame(y=70).frame()
        box.frame(fire=True).frame()
        with self.assertRaises(probe.Quit):
            box.frame(fire=True)


class BoardTest(unittest.TestCase):
    """board() on stand-in modules: pins, the encoder's pads, the App's map and run."""

    def board(self, stick=True, encoder="the encoder", ends=probe.Quit):
        """board() run: what it did in order, what it printed, the map and game run got, and the error it left with."""
        did, got = [], {}
        boot, click, d14 = FakeButton(), FakeButton(), FakeButton()

        def open_action_map():
            did.append("map")
            fire = (boot, click) if stick else (boot,)
            return engine_actions.ActionMap(fire, (d14,), encoder, FakeStick(0, 0) if stick else None)

        def run(games, knob, speaker, action_map):
            did.append("run")
            got.update(games=games, knob=knob, speaker=speaker, map=action_map)
            raise ends

        modules = {"pins": types.SimpleNamespace(ENC_A=44, ENC_B=43),
                   "drivers": types.SimpleNamespace(encoder=types.SimpleNamespace(
                       take_pads=lambda a, b: did.append("pads %d %d" % (a, b)))),
                   "app": types.SimpleNamespace(open_action_map=open_action_map, run=run)}
        error = None
        with mock.patch.dict(sys.modules, modules), contextlib.redirect_stdout(io.StringIO()) as said:
            try:
                probe.board()
            except Exception as e:  # noqa: BLE001  the test reads which one
                error = e
        return did, said.getvalue().splitlines(), got, error, (boot, click, d14)

    def test_it_takes_the_pads_first_then_the_map_then_runs_one_game_silent_with_no_knob_and_ends_on_done(self):
        did, lines, got, error, _ = self.board()
        self.assertIsNone(error)
        self.assertEqual(["pads 44 43", "map", "run"], did)
        self.assertEqual(["p905 ways stick,click,double,hold,pick,knob,auto streak 10 wrong 3 double 300 hold 400",
                          "p905 inputs stick yes knob yes", "done"], lines)
        self.assertEqual((None, None, 1), (got["knob"], got["speaker"], len(got["games"])))
        self.assertEqual("switchtest", got["games"][0].name)

    def test_both_fire_buttons_are_wrapped_and_the_rest_of_the_map_is_its_own(self):
        did, lines, got, error, (boot, click, d14) = self.board()
        fire = got["map"].fire_bindings
        self.assertEqual([probe.Seen, probe.Seen], [type(b) for b in fire])
        self.assertEqual([boot, click], [b.button for b in fire])
        self.assertEqual(((d14,), "the encoder"), (got["map"].pick_bindings, got["map"].encoder))
        self.assertIsNotNone(got["map"].stick)

    def test_a_box_with_no_knob_says_so(self):
        did, lines, got, error, _ = self.board(encoder=None)
        self.assertEqual("p905 inputs stick yes knob no", lines[1])

    def test_a_pin_map_with_no_stick_is_refused_in_one_line_and_runs_nothing(self):
        did, lines, got, error, _ = self.board(stick=False)
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(1, len(str(error).splitlines()))
        self.assertIn("no stick", str(error))
        self.assertEqual(["pads 44 43", "map"], did)
        self.assertEqual([], lines)

    def test_an_error_of_the_run_leaves_board_as_itself_with_no_done(self):
        did, lines, got, error, _ = self.board(ends=RuntimeError("rescue_night did not draw: no art"))
        self.assertIsInstance(error, RuntimeError)
        self.assertNotIn("done", lines)


class SourceTest(unittest.TestCase):
    """The file also runs on the board under MicroPython, sent from RAM."""

    def test_at_module_level_it_imports_only_sys_and_time(self):
        with open(os.path.join(REPO, "probe905_switch.py")) as f:
            tree = ast.parse(f.read())
        imports = [alias.name for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
                   for alias in node.names]
        self.assertEqual(["sys", "time"], imports)

    def test_mpy_cross_compiles_it_so_its_syntax_is_micropythons(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                out = box.Compiler(box.MpyCross()).compile(["probe905_switch.py"], tmp)
            except FileNotFoundError:
                self.skipTest("no mpy-cross: %s" % box.MPY_CROSS_PIP)  # a skip is not a pass
            self.assertGreater(os.path.getsize(out[0]), 1000)


SAID = "p905 ways stick,click,double,hold,pick,knob,auto streak 10 wrong 3 double 300 hold 400\n" \
       "p905 inputs stick yes knob yes\ngame switchtest\np905 round knob starts\ndone\n"


class MacTest(unittest.TestCase):
    """The Mac part with the fake runner of P904's probe: no board."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.log = os.path.join(self.folder.name, "run-p905-switch.log")
        patch = mock.patch.object(probe, "LOG", self.log)
        patch.start()
        self.addCleanup(patch.stop)
        self.sleeps = []

    def mac(self, argv, runner):
        """mac(argv) with runner: what it printed, what it said on stderr, and its SystemExit or None."""
        with contextlib.redirect_stdout(io.StringIO()) as said, contextlib.redirect_stderr(io.StringIO()) as err:
            try:
                probe.mac(argv, runner=runner, sleep=self.sleeps.append)
            except SystemExit as e:
                return said.getvalue(), err.getvalue(), e
        return said.getvalue(), err.getvalue(), None

    def logged(self):
        with open(self.log) as f:
            return f.read()

    def test_a_run_reads_the_box_resets_waits_runs_the_file_once_and_resets_again(self):
        board = Board(said=SAID)
        said, err, refused = self.mac([], board)
        self.assertIsNone(refused)
        self.assertEqual([["ls", ":"], ["ls", ":packs"], ["reset"], ["exec", "pass"], ["run", "probe905_switch.py"],
                          ["reset"]], board.commands)
        self.assertEqual([None] * 4 + [3600, None], board.limits)
        self.assertEqual(SAID, self.logged())
        self.assertEqual(SAID + "the log is %s\n" % self.log, said)
        with open(os.path.join(REPO, "probe905_switch.py")) as f:
            self.assertEqual(f.read(), board.copy)  # the file itself, with nothing filled in

    def test_minutes_set_the_time_limit(self):
        board = Board(said=SAID)
        self.mac(["--minutes", "7"], board)
        self.assertEqual(7 * 60, board.limits[4])
        for value in ("0", "-3", "x"):
            with self.subTest(minutes=value):
                board = Board(said=SAID)
                said, err, refused = self.mac(["--minutes", value], board)
                self.assertEqual(2, refused.code)
                self.assertEqual([], board.commands)

    def test_a_box_without_the_rescue_pack_is_refused_and_reset(self):
        board = Board(packs=("meteors.pak",))
        said, err, refused = self.mac([], board)
        self.assertIn("deploy first: python3 tools/box.py deploy --all", str(refused.code))
        self.assertEqual([["ls", ":"], ["ls", ":packs"], ["reset"]], board.commands)
        self.assertFalse(os.path.exists(self.log))

    def test_a_box_without_the_packs_folder_is_refused_and_reset(self):
        board = Board(root=("boot.py", "main.py", "app.mpy"))
        said, err, refused = self.mac([], board)
        self.assertIn("deploy first", str(refused.code))
        self.assertEqual([["ls", ":"], ["reset"]], board.commands)

    def test_the_box_is_read_again_while_a_game_keeps_mpremote_out(self):
        board = Board(said=SAID, fails=["ls :", "ls :"])
        said, err, refused = self.mac([], board)
        self.assertIsNone(refused)
        self.assertEqual([["ls", ":"]] * 3 + [["ls", ":packs"]], board.commands[:4])
        self.assertEqual([box.RESET_PAUSE_S] * 2, self.sleeps)

    def test_a_limit_with_a_p905_ways_line_is_a_play_and_exits_0(self):
        out = b"p905 ways stick,click\np905 inputs stick yes knob yes\np905 round stick starts\n"
        board = Board(run_error=subprocess.TimeoutExpired(["mpremote", "run"], 3600, output=out, stderr=None))
        said, err, refused = self.mac([], board)
        self.assertIsNone(refused)
        self.assertIn("the time limit of 60 minutes ended the run", said)
        self.assertEqual(["reset"], board.commands[-1])
        self.assertEqual(out.decode(), self.logged())

    def test_a_limit_with_no_p905_ways_line_is_refused(self):
        out = b"lineup 1: switchtest\nimport 3012 ms\n"
        board = Board(run_error=subprocess.TimeoutExpired(["mpremote", "run"], 3600, output=out, stderr=None))
        said, err, refused = self.mac([], board)
        self.assertIn("the run took over 3600 s", str(refused.code))
        self.assertIn("import 3012 ms", str(refused.code))
        self.assertIn(self.log, str(refused.code))
        self.assertEqual(["reset"], board.commands[-1])

    def test_a_failed_run_is_refused_with_its_last_line_and_the_log(self):
        board = Board(run_error=subprocess.CalledProcessError(
            1, ["mpremote", "run"], output="p905 ways stick\n",
            stderr="Traceback (most recent call last):\nRuntimeError: p905 refused: no stick in the pin map\n"))
        said, err, refused = self.mac([], board)
        text = str(refused.code)
        self.assertIn("the run failed with exit 1", text)
        self.assertIn("RuntimeError: p905 refused: no stick in the pin map", text)
        self.assertTrue(text.endswith("the log is %s" % self.log), text)
        self.assertEqual(["reset"], board.commands[-1])

    def test_a_failed_command_is_said_as_box_main_says_it_and_the_box_is_reset(self):
        board = Board(fails=["exec pass"] * 3 + ["exec pass"] * 2)
        said, err, refused = self.mac([], board)
        self.assertEqual("mpremote exec pass failed: could not enter raw repl", refused.code)
        self.assertEqual(["reset"], board.commands[-1])

    def test_its_dry_run_prints_every_command_and_runs_none(self):
        with mock.patch.object(box.subprocess, "run") as run:
            said, err, refused = self.mac(["--dry-run"], None)
        run.assert_not_called()
        self.assertIsNone(refused)
        self.assertEqual(["mpremote ls :", "mpremote ls :packs", "mpremote reset", "mpremote exec pass",
                          "mpremote run probe905_switch.py", "mpremote reset"], said.splitlines())
        self.assertFalse(os.path.exists(self.log))


if __name__ == "__main__":
    unittest.main()
