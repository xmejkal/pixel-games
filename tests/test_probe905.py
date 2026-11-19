"""probe905_switch.py (P905): the switch prototype on the Mac, with no board. The wrapped FIRE buttons, the edge of a
lean, the seven ways to switch, each threshold pinned on both sides 1 ms or 1 px apart. Run from the repository root:
python3 -B -m unittest tests.test_probe905."""

import os
import sys
import time
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))  # box
sys.path.append(REPO)  # the probe, last: the root's engine/ is the submodule, games/engine the package

from drawing_tft import DrawingTft  # noqa: E402,F401  first: it puts games/ and the stubs on the path

import probe905_switch as probe  # noqa: E402
from engine import actions as engine_actions  # noqa: E402
from test_actions import FakeButton  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
