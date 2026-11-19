"""probe906_ladder.py (P906): the walking skeleton on the Mac, with no board. Its thin version (step 3): the wrapped
FIRE buttons and the edge of a lean as P905's, the picture source on an index that art/mission.py writes from the
stand-in capture, the walker, the round that starts (READY and the pick), the game through the real app.App with the
fake buttons of tests/test_actions.py and pictures stood in by that index (no pack, so it never skips), board() on
stand-in modules, the Mac part with P905's fake runner and a stand-in for art/mission.py, and mpy-cross on the file
(skipped without mpy-cross, and a skip is not a pass). Each threshold is pinned on both sides, 1 ms or 1 px apart. Run
from the repository root: python3 -B -m unittest tests.test_probe906."""

import ast
import contextlib
import functools
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
sys.path.insert(0, os.path.join(REPO, "art"))  # art/mission.py and its modules
sys.path.insert(0, os.path.join(REPO, "tools"))  # box
sys.path.append(REPO)  # the probe, last: the root's engine/ is the submodule, games/engine the package

from drawing_tft import DrawingTft  # noqa: E402,F401  first: it puts games/ and the stubs on the path

if not hasattr(time, "ticks_add"):  # the stubs give ticks_diff, ticks_us and ticks_ms. app.run adds
    time.ticks_add = lambda a, b: a + b

import app  # noqa: E402
import box  # noqa: E402
import gfx  # noqa: E402
import mission  # noqa: E402
import probe906_ladder as probe  # noqa: E402
import rescue  # noqa: E402
from engine import actions as engine_actions  # noqa: E402
from engine.subpixel import SubPixel  # noqa: E402
from test_actions import FakeButton, FakeEncoder, FakeStick  # noqa: E402
from test_mission import set_painted  # noqa: E402  the set painted from the stand-in capture
from test_probe905 import Out, StreamBoard, frame, seen  # noqa: E402  P905's fakes

T0 = 7919  # ms: the first frame's clock in a test, no round number
NONE = seen()
STEPS = (37, 23, 41, 60, 17)  # ms: 57 px a second times none of them is a whole px


@functools.lru_cache(maxsize=None)
def written():
    """The set written once by art/mission.py from the stand-in capture: (its index as a module's dict, numbers)."""
    painted = set_painted()
    with tempfile.TemporaryDirectory() as folder:
        _, index = mission.write(folder, painted)
        art = {}
        with open(index) as f:
            exec(f.read(), art)
    return types.SimpleNamespace(ART=art["ART"], PACKS=art["PACKS"]), mission.numbers(painted)


class SeenTest(unittest.TestCase):
    """Seen: a FIRE button wrapped, so the game tells BOOT from the click (P905's)."""

    def test_update_answers_the_push_and_keeps_it_and_the_level(self):
        button = FakeButton(True, False)
        wrapped = probe.Seen(button)
        button.held = True
        self.assertIs(True, wrapped.update(T0))
        self.assertEqual((True, True), (wrapped.pushed, wrapped.held))
        button.held = False
        self.assertIs(False, wrapped.update(T0 + 41))
        self.assertEqual((False, False), (wrapped.pushed, wrapped.held))

    def test_forget_goes_through_to_the_button_and_refreshes_the_level(self):
        button = FakeButton(True)
        wrapped = probe.Seen(button)
        button.held = True
        wrapped.update(T0)
        button.held = False
        wrapped.forget()
        self.assertEqual((1, False, False), (button.forgets, wrapped.pushed, wrapped.held))


class LeanEdgeTest(unittest.TestCase):
    """LeanEdge: one answer at each new lean of an axis (P905's)."""

    def reads(self, values, start=None):
        edge = probe.LeanEdge()
        if start is not None:
            edge.reset(start)
        return [edge.read(v) for v in values]

    def test_the_lean_and_the_rest_are_the_engines_lean_and_20_and_up_is_minus_1(self):
        self.assertEqual((engine_actions.LEAN, 20, -1), (probe.LEAN, probe.LEAN_REST, probe.UP))

    def test_lean_is_the_engines_lean(self):
        for v in (-100, -41, -40, -39, -1, 0, 1, 39, 40, 41, 100):
            self.assertEqual(engine_actions.lean(v), probe.lean(v), v)

    def test_a_tilt_of_39_answers_nothing_and_40_answers(self):
        self.assertEqual([0, 0, 1], self.reads([3, 39, 40]))
        self.assertEqual([0, 0, -1], self.reads([-3, -39, -40]))

    def test_a_rest_at_20_does_not_rearm_it_and_a_rest_at_19_does(self):
        self.assertEqual([1, 0, 0], self.reads([57, 20, 63]))
        self.assertEqual([1, 0, 1], self.reads([57, 19, 63]))

    def test_up_straight_to_down_answers_twice(self):
        self.assertEqual([-1, 1, -1], self.reads([-61, 52, -77]))

    def test_reset_on_a_leaning_axis_answers_nothing_until_a_new_lean(self):
        self.assertEqual([0, 0, 0, 1], self.reads([66, 91, 7, 45], start=58))
        self.assertEqual([0, 1], self.reads([-71, 45], start=-58))

    def test_reset_takes_a_stick_at_20_or_more_as_the_lean_it_was_and_at_19_as_none(self):
        self.assertEqual([0], self.reads([45], start=35))  # it sagged from a lean: no new lean
        self.assertEqual([0], self.reads([-45], start=-20))
        self.assertEqual([1], self.reads([40], start=19))  # it came under 20: a new lean
        self.assertEqual([-1], self.reads([-40], start=-19))
        self.assertEqual([-1], self.reads([-45], start=35))  # the other way is a new lean at once


class PackSourceTest(unittest.TestCase):
    """PackSource on the index that art/mission.py writes from the stand-in capture."""

    def setUp(self):
        self.index, self.numbers = written()
        self.source = probe.PackSource(self.index.ART, self.numbers["pivot"])

    def test_every_picture_it_makes_is_in_the_index_and_each_motion_has_its_poses(self):
        for (figure, motion), poses in (((f, m), n) for f, m, n in (("fireman", "run", 12), ("fireman", "hold", 1),
                                                                    ("child", "run", 12), ("child", "climb", 12))):
            right, left = self.source.poses(figure, motion)
            with self.subTest(figure=figure, motion=motion):
                self.assertEqual((poses, poses), (len(right), len(left)))
                for name, _, _ in right + left:
                    self.assertIn(name, self.index.ART)

    def test_each_picture_is_its_name_and_its_top_left_from_the_place_on_the_soles_row(self):
        for (figure, motion), pivot in self.numbers["pivot"].items():
            w, h = self.index.ART["mission_%s_%s_r0" % (figure, motion)][:2]
            with self.subTest(figure=figure, motion=motion):
                self.assertEqual(("mission_%s_%s_r0" % (figure, motion), -pivot, 1 - h),
                                 self.source.picture(figure, motion, 0, 1))
                self.assertEqual(("mission_%s_%s_l0" % (figure, motion), -(w - 1 - pivot), 1 - h),
                                 self.source.picture(figure, motion, 0, -1))

    def test_a_picture_is_the_entry_made_once(self):
        self.assertIs(self.source.poses("child", "run")[1][5], self.source.picture("child", "run", 5, -1))

    def test_an_index_without_a_motion_is_refused_naming_it(self):
        art = {name: row for name, row in self.index.ART.items() if "_climb_" not in name}
        with self.assertRaisesRegex(RuntimeError, "mission_child_climb_r0"):
            probe.PackSource(art, self.numbers["pivot"])


RUN_R = tuple(("run_r%d" % i, -21, -40) for i in range(12))
RUN_L = tuple(("run_l%d" % i, -17, -40) for i in range(12))
HOLD = (("hold_r", -9, -38), ("hold_l", -27, -38))


def walker(x=200, facing=-1, lo=127, hi=283):
    """A walker at 57 px a second, a stride of 41 px, its walk from lo to hi, on stand-in pictures."""
    w = probe.Walker(SubPixel(), 57, 41, lo, hi, (RUN_R, RUN_L), (RUN_R[7], RUN_L[7]), HOLD)
    w.put(x, facing)
    return w


class WalkerTest(unittest.TestCase):
    """One figure that the stick's x runs."""

    def test_it_runs_in_whole_px_with_the_carry_in_its_subpixel(self):
        # 57 px a second over 178 ms is 10.146 px: to the right the floors give 10 px and keep 146 thousandths, to
        # the left each step floors toward the left, 11 px, and 854 kept
        for lean, x, ran, rest in ((1, 210, 10, 146), (-1, 189, 11, 854)):
            with self.subTest(lean=lean):
                w = walker()
                for ms in STEPS:
                    w.walk(ms, lean)
                self.assertEqual((x, ran, rest, lean), (w.x, w.ran, w.sub.rest, w.facing))

    def test_it_stops_at_both_ends_of_its_walk_and_the_carry_goes(self):
        for lean, start, end in ((1, 270, 283), (-1, 140, 127)):
            with self.subTest(lean=lean):
                w = walker(start)
                for _ in range(20):
                    w.walk(47, lean)
                self.assertEqual((end, abs(end - start), 0), (w.x, w.ran, w.sub.rest))

    def test_its_run_pose_follows_the_px_it_ran_and_its_side_its_facing(self):
        w = walker()
        w.walk(41, 1)
        for ran, pose in ((0, 0), (3, 0), (4, 1), (20, 5), (41, 0), (45, 1), (81, 11)):
            for facing, side in ((1, RUN_R), (-1, RUN_L)):
                with self.subTest(ran=ran, facing=facing):
                    w.ran, w.facing = ran, facing
                    self.assertIs(side[pose], w.picture())

    def test_at_rest_or_leaning_into_an_end_it_shows_its_standing_picture(self):
        w = walker(facing=1)
        w.walk(43, 0)
        self.assertIs(RUN_R[7], w.picture())
        w = walker(127)
        w.walk(43, -1)
        self.assertEqual((127, RUN_L[7]), (w.x, w.picture()))

    def test_fire_holds_at_24_px_from_the_place_and_not_at_25(self):
        for x, holds in ((127 + 24, True), (127 + 25, False), (127 - 24, True), (127 - 25, False)):
            with self.subTest(x=x):
                w = walker(x, lo=90)
                self.assertIs(holds, w.hold(127))
                self.assertEqual((127 if holds else x, holds), (w.x, w.holds))

    def test_a_hold_faces_the_ladder_whichever_way_he_ran(self):
        w = walker(141, facing=1)
        w.hold(127)
        self.assertEqual((-1, HOLD[1]), (w.facing, w.picture()))

    def test_while_he_holds_he_does_not_move_and_shows_the_hold(self):
        w = walker(141)
        w.hold(127)
        w.walk(60, 1)
        w.walk(60, -1)
        self.assertEqual((127, 0, -1, HOLD[1]), (w.x, w.ran, w.facing, w.picture()))

    def test_put_starts_it_again_standing_at_a_place_with_no_carry(self):
        w = walker(141)
        w.walk(37, 1)
        w.hold(127)
        w.put(233, -1)
        self.assertEqual((233, -1, 0, 0, False, 0, 0), (w.x, w.facing, w.ran, w.sub.rest, w.holds, w.lean, w.up))


def walkers(numbers=None):
    """The fireman and the child on stand-in pictures at the start places: the fireman at 233, the child at 281."""
    fireman = walker(233, lo=127, hi=270)
    child = probe.Walker(SubPixel(), 43, 29, 131, 283, (RUN_R, RUN_L), (RUN_R[3], RUN_L[3]), None)
    child.put(281, -1)
    return [fireman, child]


class Play:
    """One round on scripted frames: its lines in a list, a clock that moves 41 ms a frame unless a frame names its
    time, and the two stand-in walkers."""

    def __init__(self, number=1, ended=None):
        self.lines, self.now = [], T0
        self.figures = walkers()
        self.round = probe.Round(number, ended, self.figures, self.lines.append)

    def frame(self, at=None, ms=41, boot=NONE, click=NONE, **inputs):
        self.now = T0 + at if at is not None else self.now + ms
        self.round.step(self.now, ms, frame(**inputs), boot)
        return self

    def ready(self):
        return self.frame(at=0).frame(at=600)


class RoundTest(unittest.TestCase):
    """The round that starts (step 3): its line, READY and the pick, on scripted frames."""

    def test_its_values_are_the_plans(self):
        self.assertEqual((600, 15000, 24, 2, ("fireman", "child")),
                         (probe.READY_MS, probe.TITLE_MS, probe.HOLD_PX, probe.PACE, probe.FIGURES))

    def test_its_first_frame_starts_it_round_1_after_0_with_the_child_active(self):
        p = Play()
        self.assertEqual([], p.lines)  # made in setup: no clock yet
        p.frame(at=0)
        self.assertEqual(["p906 round 1 starts after 0"], p.lines)
        self.assertEqual((probe.CHILD, 1, True), (p.round.active, p.round.task, p.round.ready))

    def test_a_later_round_says_the_ms_since_the_last_rounds_end(self):
        p = Play(3, T0 - 2140)
        p.frame(at=0)
        self.assertEqual(["p906 round 3 starts after 2140"], p.lines)

    def test_ready_lasts_600_ms_from_its_first_frame_and_nobody_runs_in_it(self):
        p = Play().frame(at=13, x=-80).frame(at=13 + 599, x=-80)
        self.assertEqual((True, 281), (p.round.ready, p.figures[1].x))
        p.frame(at=13 + 600, x=-80, ms=43)
        self.assertEqual((False, 281 - 2), (p.round.ready, p.figures[1].x))  # 43 px a second over 43 ms: 1.849 px

    def test_a_lean_that_starts_in_ready_at_599_ms_is_a_pick_at_600(self):
        p = Play().frame(at=0).frame(at=599, y=70)
        self.assertEqual(probe.CHILD, p.round.active)
        p.frame(at=600, y=72)
        self.assertEqual(probe.FIREMAN, p.round.active)

    def test_a_lean_from_before_ready_is_no_pick(self):
        p = Play().frame(at=0, y=70).frame(at=599, y=75).frame(at=600, y=77).frame(at=641, y=81)
        self.assertEqual(probe.CHILD, p.round.active)

    def test_up_picks_the_child_and_down_the_fireman_from_each_figure(self):
        for first, y, active in ((probe.CHILD, -70, probe.CHILD), (probe.CHILD, 70, probe.FIREMAN),
                                 (probe.FIREMAN, -70, probe.CHILD), (probe.FIREMAN, 70, probe.FIREMAN)):
            with self.subTest(first=first, y=y):
                p = Play().ready()
                p.round.active = first
                p.frame(y=y)
                self.assertEqual(active, p.round.active)

    def test_only_the_active_figure_runs_with_the_sticks_x_and_39_is_no_lean(self):
        p = Play().ready()
        p.frame(x=-80, ms=43)
        self.assertEqual((233, 281 - 2, 0, -1), (p.figures[0].x, p.figures[1].x, p.figures[0].lean,
                                                  p.figures[1].lean))
        p.frame(y=70).frame(x=-39, ms=47).frame(x=-40, ms=47)
        self.assertEqual(233 - 3, p.figures[0].x)  # 57 px a second over 47 ms is 2.679 px: floored to the left, 3


class Pictures:
    """pictures stood in: the set's index that art/mission.py wrote from the stand-in capture, every set loaded, and
    every draw recorded and answered by whether the index has the picture."""

    load_ms = 0

    def __init__(self, index):
        self.art_index, self.drawn = index, []

    def load(self, game=None, only=None):
        return True

    def load_steps(self, game=None, only=None):
        return iter(())

    def free(self):
        pass

    def draw(self, cv, name, x, y, alpha=255):
        self.drawn.append((name, x, y))
        return name in self.art_index.ART


class Box:
    """The real app.App with the probe's game in a lineup of one: the FIRE buttons wrapped (Seen), PICK, the knob's
    encoder and the stick, the fakes of tests/test_actions.py, pictures stood in by the written index, and no knob in
    the App. The clock moves by each frame's ms. It stands in the intro after its first frame."""

    def __init__(self, test, pool=None):
        index, self.numbers = written()
        self.now, self.said, self.pictures = T0, io.StringIO(), Pictures(index)
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
                           games=(probe.game_class(boot, click, self.numbers, pool),), out=self.out)
        self.app.start()
        self.frame()

    def frame(self, ms=41, fire=False, held=False, boot=False, click=False, pick=False, x=0, y=0):
        self.now += ms
        for button, pushed in ((self.boot, fire or boot), (self.click, click), (self.d14, pick)):
            button.pushes.append(pushed)
        self.boot.held = held or fire or boot
        self.click.held = click
        self.stick.x, self.stick.y = x, y
        self.app.frame()
        return self

    def lines(self):
        return [line for line in self.said.getvalue().splitlines() if line.startswith("p906 ")]

    def play(self):
        """FIRE ends the intro, the next frame starts round 1, and READY's 600 ms."""
        return self.frame(fire=True).frame().frame(ms=600)


def words(box):
    """The frame's text and big words, kept ones too, each as (words, x, y, colour)."""
    return [(op[5], op[7], op[8], op[6]) for op in box.out.cv.ops if op[4] == 3]


class GameTest(unittest.TestCase):
    """The probe's game through app.App, with no pack: it never skips."""

    def test_it_is_ladder_on_the_set_mission_and_starts_in_its_intro(self):
        box = Box(self)
        game = box.app.game
        self.assertEqual(("ladder", ("mission", None), 15000), (game.name, game.ART, game.TITLE_MS))
        self.assertEqual(gfx.TITLE, game.state)
        self.assertEqual((None, None), (box.app.knob, box.app.volume_pane))

    def test_the_intro_names_both_tasks_fire_and_the_way_out_on_a_kept_panel(self):
        box = Box(self)
        seen = box.out.cv.seen
        for line in probe.INTRO:
            self.assertIn(line, seen)
        self.assertIn("FIRE = BOOT or the stick's click", seen)
        self.assertIn("PICK twice: quit", seen)
        box.frame()
        self.assertEqual([], box.out.cv.words)  # kept: not drawn again
        self.assertEqual(1, seen.count(probe.INTRO[0]))

    def test_the_intro_ends_at_fire_and_its_fire_does_not_reach_play(self):
        box = Box(self)
        box.frame(fire=True)
        self.assertEqual((gfx.PLAY, ["p906 intro ends fire"]), (box.app.game.state, box.lines()))
        self.assertIsNone(box.app.game.round.start_ms)  # no frame of play yet
        box.frame(fire=True)
        self.assertEqual(["p906 intro ends fire", "p906 round 1 starts after 0"], box.lines())

    def test_the_intro_ends_at_15000_ms_and_not_at_14999(self):
        box = Box(self)
        box.frame(ms=14999)
        self.assertEqual(gfx.TITLE, box.app.game.state)
        box.frame(ms=1)
        self.assertEqual((gfx.PLAY, ["p906 intro ends time"]), (box.app.game.state, box.lines()))

    def test_round_1_starts_with_the_child_active_and_both_figures_standing_at_their_start_places(self):
        box = Box(self)
        box.frame(fire=True).frame()
        game, start = box.app.game, box.numbers["start"]
        self.assertEqual("p906 round 1 starts after 0", box.lines()[-1])
        self.assertEqual((probe.CHILD, [start[0], start[1]], [-1, -1]), (
            game.round.active, [f.x for f in game.figures], [f.facing for f in game.figures]))
        self.assertIs(game.figures, game.round.figures)

    def test_each_figure_has_its_numbers(self):
        box = Box(self)
        fireman, child = box.app.game.figures
        n = box.numbers
        self.assertEqual((n["speed"]["fireman"] // 2, n["stride"]["fireman"], n["place"][0]),
                         (fireman.speed, fireman.stride, fireman.lo))
        self.assertEqual((n["speed"]["child"] // 2, n["stride"]["child"], n["place"][1]),
                         (child.speed, child.stride, child.lo))
        self.assertNotEqual((fireman.speed, fireman.stride, fireman.lo), (child.speed, child.stride, child.lo))
        self.assertIsNone(child.hold_poses)

    def test_the_climb_goes_at_twice_the_captured_pace_and_ends_at_the_places_height(self):
        box = Box(self)
        climb, (pose_ms, travel, advance) = box.app.game.climb, box.numbers["climb"]
        self.assertEqual((pose_ms // 2, travel, advance, 54), (climb.pose_ms, climb.travel, climb.advance, climb.end))
        self.assertEqual((2, 900), (probe.CLIMB_PACE, box.app.game.OVER_MS))

    def test_the_last_place_of_each_walk_keeps_both_its_pictures_whole_on_the_screen(self):
        box = Box(self)
        for f in box.app.game.figures:
            with self.subTest(lo=f.lo):
                for side in f.run:
                    for name, dx, dy in side:
                        w = box.pictures.art_index.ART[name][0]
                        self.assertTrue(0 <= f.hi + dx and f.hi + dx + w - 1 <= 319, (name, f.hi))
                self.assertEqual(319, max(f.hi + dx + box.pictures.art_index.ART[n][0] - 1 for side in f.run
                                          for n, dx, _ in side))

    def test_ready_shows_its_word_for_600_ms_and_then_no_word_in_a_frame_of_play(self):
        box = Box(self)
        box.frame(fire=True).frame()
        self.assertIn("READY", box.out.cv.words)
        box.frame(ms=599)
        self.assertIn("READY", box.out.cv.words)
        box.frame(ms=1)
        self.assertEqual([], box.out.cv.words)
        box.frame(y=70).frame(x=-90)
        self.assertEqual([], box.out.cv.words)

    def test_the_street_and_the_ladder_then_the_fireman_then_the_child_each_at_its_place(self):
        box = Box(self).play()
        box.pictures.drawn.clear()
        box.frame()
        game, (lx, ly) = box.app.game, box.numbers["ladder"]
        expected = [("mission_night", 0, 0), ("mission_ladder", lx, ly)]
        for f in game.figures:
            name, dx, dy = f.picture()
            expected.append((name, f.x + dx, probe.FEET + dy))
        self.assertEqual(expected, box.pictures.drawn)
        self.assertEqual(["mission_fireman_run_l%d" % mission.STAND["fireman"],
                          "mission_child_run_l%d" % mission.STAND["child"]], [n for n, _, _ in expected[2:]])

    def test_the_arrow_is_white_6_px_over_the_active_figures_picture(self):
        box = Box(self).play()
        game = box.app.game
        for active in (probe.CHILD, probe.FIREMAN):
            with self.subTest(active=active):
                box.frame(y=70 if active == probe.FIREMAN else -70)
                f = game.figures[active]
                x, tip = f.x, probe.FEET + f.picture()[2] - 6
                rows = ((7, tip - 3), (5, tip - 2), (3, tip - 1), (1, tip))
                rim = [((x - w // 2 - 1, r - 1, x + w // 2 + 2, r + 2), gfx.BLACK) for w, r in rows]
                white = [((x - w // 2, r, x + w // 2 + 1, r + 1), gfx.WHITE) for w, r in rows]
                drawn = [(op[:4], op[5]) for op in box.out.cv.ops if op[4] == 0 and op[5] in (gfx.WHITE, gfx.BLACK)
                         and x - 4 <= op[0] and op[2] <= x + 5 and tip - 4 <= op[1] and op[3] <= tip + 2]
                self.assertEqual(rim + white, drawn)  # the rim first, the arrow over it. the mark's rim is elsewhere
                box.frame()

    def test_the_shapes_the_gap_and_the_bar_are_the_storyboards(self):
        board = mission.Storyboard
        self.assertEqual((board.ARROW, board.MARK, board.GAP, board.BAR),
                         (probe.ARROW, probe.MARK, probe.ARROW_GAP, probe.BAR))

    def test_the_bar_is_three_rows_drawn_once_and_the_task_block_comes_after_its_copy(self):
        box = Box(self)
        box.out.cv.seen.clear()  # the intro's words: its last line is the bar's last row too
        box.play()
        for k in range(30):
            box.frame(x=-80 if k % 2 else 0, y=70 if k % 3 else -70)
        self.assertEqual([1, 1, 1], [box.out.cv.seen.count(row) for row in probe.BAR])
        ops = box.out.cv.ops
        bar = [i for i, op in enumerate(ops) if op[4] == 3 and op[5] in probe.BAR]
        block = [i for i, op in enumerate(ops) if op[:6] == (2, 1, 8, 7, 0, gfx.YELLOW)]
        self.assertEqual(1, len(block))
        self.assertGreater(block[0], max(bar))  # after the kept rows, which the bar's copy draws again here

    def test_each_row_of_the_bar_and_the_intro_fits_the_screen(self):
        for row in probe.BAR:
            self.assertLessEqual(probe.BAR_X + 8 * len(row), 314, row)
        x, _, w, _ = probe.INTRO_RECT
        for line in probe.INTRO:
            self.assertLessEqual(x + 8 + 8 * len(line), x + w - 4, line)

    def test_only_the_active_figure_runs_and_the_pick_is_the_sticks_y(self):
        box = Box(self).play()
        game = box.app.game
        xs = [f.x for f in game.figures]
        box.frame(x=-90, ms=43)
        self.assertEqual(xs[0], game.figures[0].x)
        self.assertLess(game.figures[1].x, xs[1])
        box.frame(y=80).frame(x=-90, ms=43)
        self.assertEqual(probe.FIREMAN, game.round.active)
        self.assertLess(game.figures[0].x, xs[0])

    def test_a_picture_that_does_not_draw_raises_with_its_name(self):
        box = Box(self)
        box.pictures.draw = lambda cv, name, x, y, alpha=255: False
        with self.assertRaises(RuntimeError) as raised:
            box.app.game.paint_static(box.out.cv)
        self.assertEqual("mission_night did not draw: no art", str(raised.exception))

    def test_with_the_boxs_pool_the_first_setup_says_where_the_pack_sits(self):
        asked = []
        box = Box(self, pool=lambda n: asked.append(n) or bytearray(1))
        size = box.pictures.art_index.PACKS["mission"][1]
        self.assertEqual(["pack pool %d" % size], [line for line in box.said.getvalue().splitlines()
                                                    if line.startswith("pack ")])
        self.assertEqual([size], asked)

    def test_the_feet_are_the_streets(self):
        self.assertEqual((rescue.FEET, mission.FEET), (probe.FEET, probe.FEET))


class PackLineTest(unittest.TestCase):
    def test_the_pack_is_in_the_pool_when_the_pool_holds_its_size_else_in_the_heap(self):
        def pool(size):
            def answer(n):
                if n > size:
                    raise ValueError("the pool is smaller: reset the board")
                return bytearray(0)
            return answer

        self.assertEqual("pack pool 773470", probe.pack_line(pool(773470), 773470))
        self.assertEqual("pack heap 773470", probe.pack_line(pool(773469), 773470))


class BoardTest(unittest.TestCase):
    """board() on stand-in modules: pins, the encoder's pads, the App's map and run, s3lcd's pool."""

    def board(self, stick=True, ends=probe.Quit):
        """board() run: what it did in order, what it printed, the map and game run got, and the error it left with."""
        did, got = [], {}
        boot, click, d14 = FakeButton(), FakeButton(), FakeButton()

        def open_action_map():
            did.append("map")
            fire = (boot, click) if stick else (boot,)
            return engine_actions.ActionMap(fire, (d14,), "the encoder", FakeStick(0, 0) if stick else None)

        def run(games, knob, speaker, action_map):
            did.append("run")
            got.update(games=games, knob=knob, speaker=speaker, map=action_map)
            raise ends

        modules = {"pins": types.SimpleNamespace(ENC_A=44, ENC_B=43),
                   "drivers": types.SimpleNamespace(encoder=types.SimpleNamespace(
                       take_pads=lambda a, b: did.append("pads %d %d" % (a, b)))),
                   "app": types.SimpleNamespace(open_action_map=open_action_map, run=run),
                   "s3lcd": types.SimpleNamespace(pool="the pool")}
        error = None
        with mock.patch.dict(sys.modules, modules), mock.patch.object(probe, "NUMBERS", written()[1]), \
                mock.patch.object(probe, "game_class", lambda *a: types.SimpleNamespace(name="ladder", args=a)), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            try:
                probe.board()
            except Exception as e:  # noqa: BLE001  the test reads which one
                error = e
        return did, said.getvalue().splitlines(), got, error, (boot, click, d14)

    def test_it_takes_the_pads_first_then_the_map_then_runs_one_game_silent_with_no_knob_and_ends_on_done(self):
        did, lines, got, error, (boot, click, d14) = self.board()
        self.assertIsNone(error)
        self.assertEqual(["pads 44 43", "map", "run"], did)
        self.assertEqual(["p906 rules lean 40 rest 20 ready 600 intro 15000 hold 24 pace 2", "done"], lines)
        self.assertEqual((None, None, 1), (got["knob"], got["speaker"], len(got["games"])))
        wrapped_boot, wrapped_click, numbers, pool = got["games"][0].args
        self.assertEqual(([boot, click], written()[1], "the pool"),
                         ([wrapped_boot.button, wrapped_click.button], numbers, pool))
        self.assertEqual([wrapped_boot, wrapped_click], list(got["map"].fire_bindings))
        self.assertEqual(((d14,), "the encoder"), (got["map"].pick_bindings, got["map"].encoder))

    def test_a_pin_map_with_no_stick_is_refused_in_one_line_and_runs_nothing(self):
        did, lines, got, error, _ = self.board(stick=False)
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(1, len(str(error).splitlines()))
        self.assertIn("no stick", str(error))
        self.assertEqual((["pads 44 43", "map"], []), (did, lines))

    def test_an_error_of_the_run_leaves_board_as_itself_with_no_done(self):
        did, lines, got, error, _ = self.board(ends=RuntimeError("mission_night did not draw: no art"))
        self.assertIsInstance(error, RuntimeError)
        self.assertNotIn("done", lines)


class SourceTest(unittest.TestCase):
    """The file also runs on the board under MicroPython, sent from RAM."""

    def test_at_module_level_it_imports_only_sys_and_time(self):
        with open(os.path.join(REPO, "probe906_ladder.py")) as f:
            tree = ast.parse(f.read())
        imports = [alias.name for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
                   for alias in node.names]
        self.assertEqual(["sys", "time"], imports)

    def test_mpy_cross_compiles_it_so_its_syntax_is_micropythons(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                out = box.Compiler(box.MpyCross()).compile(["probe906_ladder.py"], tmp)
            except FileNotFoundError:
                self.skipTest("no mpy-cross: %s" % box.MPY_CROSS_PIP)  # a skip is not a pass
            self.assertGreater(os.path.getsize(out[0]), 1000)

    def test_the_source_holds_no_numbers_the_mac_part_fills_them_in_a_copy(self):
        self.assertIsNone(probe.NUMBERS)


STAND_IN_NUMBERS = {"stride": {"fireman": 141, "child": 79}, "speed": {"fireman": 197, "child": 109},
                    "pivot": {("fireman", "run"): 37, ("fireman", "hold"): 13, ("child", "run"): 21,
                              ("child", "climb"): 5},
                    "stand": {"fireman": 7, "child": 3}, "climb": (199, ((0, 4), (1, 11)), (3, 17)),
                    "ladder": (73, 97), "start": (223, 279), "place": (113, 119), "end": 53,
                    "mark": ((113, 221), (81, 87))}  # none round, none alike


class StandInArt:
    """art/mission.py stood in: the capture, the paint, write (small files where mission.write puts the pack and the
    index) and numbers (STAND_IN_NUMBERS). It keeps what it was asked."""

    SET = "mission"

    def __init__(self):
        self.asked = []

    def capture(self, parser):
        self.asked.append("capture")
        return "the capture"

    def painted(self, capture):
        self.asked.append(capture)
        return "the painted set"

    def write(self, folder, painted):
        self.asked.append(painted)
        os.makedirs(os.path.join(folder, "packs"))
        pack, index = os.path.join(folder, "packs", "mission.pak"), os.path.join(folder, "art_index.py")
        for path in (pack, index):
            with open(path, "w") as f:
                f.write("stand-in\n")
        return pack, index

    def numbers(self, painted):
        self.asked.append(painted)
        return STAND_IN_NUMBERS


ROOT = ("boot.py", "main.py", "app.mpy", "art_index.mpy", "packs/")
DONE = "p906 rules lean 40 rest 20 ready 600 intro 15000 hold 24 pace 2\npack pool 773470\ngame ladder\n" \
       "p906 intro ends fire\np906 round 1 starts after 0\ndone\n"


def removal():
    return [["ls", ":"], ["ls", ":packs"], ["rm", ":art_index.py"], ["rm", ":packs/mission.pak"]]


LEFT = (":art_index.py and :packs/mission.pak may still be on the box: run `mpremote rm :art_index.py`, `mpremote rm "
        ":packs/mission.pak`, then `mpremote reset`")  # a failed removal's way out by hand


class MacTest(unittest.TestCase):
    """The Mac part with P905's fake runner and a stand-in for art/mission.py: no board, no paint."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.log = os.path.join(self.folder.name, "run-p906-ladder.log")
        patch = mock.patch.object(probe, "LOG", self.log)
        patch.start()
        self.addCleanup(patch.stop)
        self.sleeps, self.art = [], StandInArt()

    def mac(self, argv, runner):
        """mac(argv) with runner: what it printed, what it said on stderr, and its SystemExit or None."""
        with contextlib.redirect_stdout(io.StringIO()) as said, contextlib.redirect_stderr(io.StringIO()) as err:
            try:
                probe.mac(argv, runner=runner, sleep=self.sleeps.append, art=self.art)
            except SystemExit as e:
                return said.getvalue(), err.getvalue(), e
        return said.getvalue(), err.getvalue(), None

    def logged(self):
        with open(self.log) as f:
            return f.read()

    def test_a_sitting_paints_lends_resets_runs_the_copy_once_removes_and_resets(self):
        board = StreamBoard(said=DONE)
        said, err, refused = self.mac([], board)
        self.assertIsNone(refused)
        pack, index, copy = board.commands[1][1], board.commands[2][1], board.commands[5][1]
        self.assertEqual([["ls", ":"], ["cp", pack, ":packs/mission.pak"], ["cp", index, ":art_index.py"],
                          ["reset"], ["exec", "pass"], ["run", copy]] + removal() + [["reset"]], board.commands)
        self.assertTrue(pack.endswith(os.path.join("packs", "mission.pak")) and index.endswith("art_index.py"))
        self.assertTrue(copy.endswith("probe906_ladder.py"))
        self.assertEqual([None] * 5 + [3600] + [None] * 5, board.limits)  # each rm on its own
        self.assertEqual((set(ROOT), {"rescue.pak"}), (board.root, board.packs))
        self.assertEqual(["capture", "the capture", "the painted set", "the painted set"], self.art.asked)
        self.assertEqual(DONE, self.logged())
        self.assertEqual(DONE + "the log is %s\n" % self.log, said)
        self.assertFalse(os.path.exists(copy))  # the temporary folder is gone

    def test_the_copy_is_the_probe_with_the_numbers_filled_in(self):
        board = StreamBoard(said=DONE)
        self.mac([], board)
        with open(os.path.join(REPO, "probe906_ladder.py")) as f:
            source = f.read().splitlines()
        copy = board.copy.splitlines()
        differ = [(a, b) for a, b in zip(source, copy) if a != b]
        self.assertEqual((len(source), 1), (len(copy), len(differ)))
        self.assertTrue(differ[0][0].startswith("NUMBERS = None  #"), differ)
        module = {"__name__": "copy"}
        exec(compile(board.copy, "copy", "exec"), module)
        self.assertEqual(STAND_IN_NUMBERS, module["NUMBERS"])

    def test_filled_refuses_a_source_without_exactly_one_numbers_line(self):
        with open(os.path.join(REPO, "probe906_ladder.py")) as f:
            source = f.read()
        old = "\nNUMBERS = None"
        for case, broken in (("none", source.replace(old, "\n# gone", 1)), ("two", source.replace(old, old * 2, 1))):
            with self.subTest(case=case), self.assertRaises(ValueError):
                probe.filled(broken, STAND_IN_NUMBERS)

    def test_minutes_set_the_time_limit_and_a_bad_value_runs_nothing(self):
        board = StreamBoard(said=DONE)
        self.mac(["--minutes", "7"], board)
        self.assertEqual(7 * 60, board.limits[5])
        for value in ("0", "-3", "x"):
            with self.subTest(minutes=value):
                board = StreamBoard(said=DONE)
                said, err, refused = self.mac(["--minutes", value], board)
                self.assertEqual((2, []), (refused.code, board.commands))

    def test_a_box_with_an_index_is_refused_before_any_copy_and_reset(self):
        board = StreamBoard(root=("boot.py", "main.py", "art_index.py", "packs/"))
        said, err, refused = self.mac([], board)
        self.assertTrue(str(refused.code).startswith("refused: the box has an :art_index.py"), refused.code)
        self.assertEqual([["ls", ":"], ["reset"]], board.commands)
        self.assertFalse(os.path.exists(self.log))

    def test_a_failed_copy_is_said_as_box_main_says_it_and_both_go_and_the_box_is_reset(self):
        board = StreamBoard(copy_fails={":art_index.py": "halfway"})
        said, err, refused = self.mac([], board)
        self.assertEqual("mpremote cp %s :art_index.py failed: no space left" % board.commands[2][1], refused.code)
        self.assertEqual(removal() + [["reset"]], board.commands[3:])
        self.assertEqual((set(ROOT), {"rescue.pak"}), (board.root, board.packs))

    def test_a_limit_with_a_p906_round_line_is_a_sitting_and_exits_0(self):
        out = b"p906 rules lean 40\np906 intro ends time\np906 round 1 starts after 0\n"
        board = StreamBoard(run_error=subprocess.TimeoutExpired(["mpremote", "run"], 3600, output=out, stderr=None))
        said, err, refused = self.mac([], board)
        self.assertIsNone(refused)
        self.assertIn("the time limit of 60 minutes ended the sitting", said)
        self.assertEqual(removal() + [["reset"]], board.commands[-5:])
        self.assertEqual(out.decode(), self.logged())

    def test_a_limit_with_no_p906_round_line_is_refused_with_its_last_line_and_the_log(self):
        out = b"p906 rules lean 40\ngame ladder\np906 intro ends time\n"
        board = StreamBoard(run_error=subprocess.TimeoutExpired(["mpremote", "run"], 3600, output=out, stderr=None))
        said, err, refused = self.mac([], board)
        self.assertEqual("refused: the run took over 3600 s: p906 intro ends time; the log is %s" % self.log,
                         refused.code)
        self.assertEqual(removal() + [["reset"]], board.commands[-5:])

    def test_a_failed_run_is_refused_with_its_last_line_and_the_log(self):
        board = StreamBoard(run_error=subprocess.CalledProcessError(
            1, ["mpremote", "run"], output="p906 rules lean 40\n",
            stderr="Traceback (most recent call last):\nRuntimeError: p906 refused: no stick in the pin map\n"))
        said, err, refused = self.mac([], board)
        self.assertEqual("refused: the run failed with exit 1: RuntimeError: p906 refused: no stick in the pin map; "
                         "the log is %s" % self.log, refused.code)
        self.assertEqual(removal() + [["reset"]], board.commands[-5:])

    def test_a_run_that_ends_without_done_is_refused(self):
        board = StreamBoard(said="p906 rules lean 40\np906 round 1 starts after 0\n")
        said, err, refused = self.mac([], board)
        self.assertEqual("refused: the run ended with no done line: p906 round 1 starts after 0; the log is %s"
                         % self.log, refused.code)

    def test_a_failed_removal_says_the_first_error_what_may_be_left_and_the_way_out(self):
        run_error = subprocess.CalledProcessError(1, ["mpremote", "run"], output="p906 rules\n", stderr="")
        board = StreamBoard(run_error=run_error, broken={"ls :"})
        said, err, refused = self.mac([], board)
        self.assertEqual("refused: the removal failed: mpremote ls : failed: could not enter raw repl; before it: "
                         "the run failed with exit 1; " + LEFT + "; the log is %s" % self.log, refused.code)
        self.assertEqual(["reset"], board.commands[-1])

    def test_a_failed_copy_and_then_a_failed_removal_name_both(self):
        board = StreamBoard(copy_fails={":art_index.py": "before"}, broken={"ls :"})
        said, err, refused = self.mac([], board)
        self.assertEqual("refused: the removal failed: mpremote ls : failed: could not enter raw repl; before it: "
                         "mpremote cp %s :art_index.py failed: no space left; %s" % (board.commands[2][1], LEFT),
                         refused.code)
        self.assertEqual(["reset"], board.commands[-1])

    def test_a_stop_inside_the_removal_is_refused_with_what_may_be_left(self):
        class Stopped(StreamBoard):
            def run(self, args, timeout=None):
                if args == ["ls", ":"] and self.copy is not None:  # the removal's first read, after the run
                    self.commands.append(args)
                    raise SystemExit("stopped by signal 15")
                return StreamBoard.run(self, args, timeout)

        board = Stopped(said=DONE)
        said, err, refused = self.mac([], board)
        self.assertEqual("refused: the removal failed: stopped by signal 15; " + LEFT + "; the log is %s" % self.log,
                         refused.code)
        self.assertEqual([["ls", ":"], ["reset"]], board.commands[-2:])

    def test_a_ctrl_c_keeps_the_log_removes_both_and_resets_the_box(self):
        board = StreamBoard(said="p906 rules lean 40\n", run_error=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            self.mac([], board)
        self.assertEqual("p906 rules lean 40\n", self.logged())
        self.assertEqual(removal() + [["reset"]], board.commands[-5:])

    def test_a_missing_capture_refuses_before_any_board_command(self):
        class NoCapture(StandInArt):
            def capture(self, parser):
                parser.error("not in the folder: 13_33.amc")

        self.art = NoCapture()
        board = StreamBoard(said=DONE)
        said, err, refused = self.mac([], board)
        self.assertEqual((2, []), (refused.code, board.commands))
        self.assertIn("13_33.amc", err)

    def test_its_dry_run_prints_every_command_in_order_and_runs_none_nor_writes_a_log(self):
        with mock.patch.object(box.subprocess, "run") as run, mock.patch.object(box.subprocess, "Popen") as popen:
            said, err, refused = self.mac(["--dry-run"], None)
        run.assert_not_called()
        popen.assert_not_called()
        self.assertIsNone(refused)
        lines = said.splitlines()
        tmp = os.path.dirname(lines[5].split()[-1])  # the copy's folder
        self.assertEqual(["mpremote ls :", "mpremote cp %s :packs/mission.pak" % os.path.join(tmp, "packs",
                                                                                              "mission.pak"),
                          "mpremote cp %s :art_index.py" % os.path.join(tmp, "art_index.py"), "mpremote reset",
                          "mpremote exec pass", "mpremote run %s" % os.path.join(tmp, "probe906_ladder.py"),
                          "mpremote ls :", "mpremote ls :packs", "mpremote rm :art_index.py",
                          "mpremote rm :packs/mission.pak", "mpremote reset"], lines)
        self.assertFalse(os.path.exists(self.log))



# --- the whole round (step 5) ----------------------------------------------------------------------------------

STAND_TRAVEL = tuple((1 + k // 3, 1 + k) for k in range(12))  # a stand-in climb: 1 px up a pose, across plays too
REAL_CLIMB = (201, ((0, 5), (1, 13), (1, 13), (1, 13), (1, 12), (2, 12), (2, 11), (3, 11), (4, 14), (5, 19), (5, 23),
                    (5, 23)), (5, 19))  # art/mission.py's numbers from the CMU files (test_mission)
ON = seen(True, True)  # a FIRE button pushed in this frame


def stand_climb(end=54):
    """The stand-in climb at 43 ms a pose, so no frame of 41 ms is a whole pose: pose n of the climb is n + 1 px
    up."""
    return probe.Climb(43, STAND_TRAVEL, (5, 12), end)


class ClimbTest(unittest.TestCase):
    """Climb: the child's pose and place on the ladder from the ms it climbed."""

    def test_the_travel_at_1_ms_before_a_poses_end_and_at_it(self):
        climb = stand_climb()
        climb.set(43 * 5 - 1)
        self.assertEqual((4, 2, 5), (climb.pose, climb.forward, climb.up))
        climb.set(43 * 5)
        self.assertEqual((5, 2, 6), (climb.pose, climb.forward, climb.up))

    def test_a_play_starts_one_advance_further(self):
        climb = stand_climb()
        climb.set(43 * 12 + 40)
        self.assertEqual((0, 5 + 1, 12 + 1), (climb.pose, climb.forward, climb.up))

    def test_the_end_at_54_px_and_not_at_53(self):
        climb = stand_climb()
        climb.set(43 * 52)
        self.assertEqual((53, False), (climb.up, climb.done()))
        climb.set(43 * 53)
        self.assertEqual((54, True), (climb.up, climb.done()))

    def test_on_the_real_climbs_numbers_the_end_comes_at_57_px(self):
        pose_ms, travel, advance = REAL_CLIMB
        climb = probe.Climb(pose_ms // probe.CLIMB_PACE, travel, advance, 54)
        ups = []
        for n in range(60):
            climb.set(climb.pose_ms * n)
            ups.append(climb.up)
            if climb.done():
                break
        self.assertEqual((57, 33, 3300), (climb.up, n, climb.ms))
        self.assertNotIn(54, ups)
        self.assertEqual(52, ups[-2])

    def test_reset_puts_it_at_the_foot(self):
        climb = stand_climb()
        climb.set(999)
        climb.reset()
        self.assertEqual((0, 0, 0, 0), (climb.ms, climb.pose, climb.forward, climb.up))


class TallyTest(unittest.TestCase):
    """The tally of a sitting: a round is wrong at its first wrong pick, once, and the streak counts clean rounds."""

    def test_a_wrong_pick_makes_its_task_and_its_round_wrong_once(self):
        tally = probe.Tally()
        tally.pick(False)
        tally.pick(False)
        self.assertEqual((True, False), (tally.task_ends(), tally.task_ends()))
        self.assertTrue(tally.round_wrong)
        tally.round_ends(4321)
        self.assertEqual(0, tally.streak)

    def test_the_streak_counts_clean_rounds_and_starts_again_after_a_wrong_one(self):
        tally = probe.Tally()
        for wrong in (False, False, True, False):
            tally.start()
            tally.pick(not wrong)
            tally.round_ends(5000)
        self.assertEqual(1, tally.streak)

    def test_streak_5_is_met_at_5_and_not_at_4_and_only_once(self):
        tally = probe.Tally()
        met = []
        for k in range(12):
            tally.start()
            tally.pick(k != 6)
            met.append(tally.round_ends(5000 + k))
        self.assertEqual([4], [k for k, m in enumerate(met) if m])  # the fifth round. after the wrong 7th, no second
        self.assertEqual((True, 5), (tally.met, probe.STREAK))

    def test_the_best_time_is_the_shortest_round(self):
        tally = probe.Tally()
        for ms in (8460, 7013, 9002):
            tally.start()
            tally.round_ends(ms)
        self.assertEqual(7013, tally.best_ms)


class Run(Play):
    """A whole round on scripted frames, with the sitting's tally and a climb: Play's walkers, the fireman's place 127
    and the child's foot 131."""

    def __init__(self, number=1, ended=None, tally=None, climb=None):
        self.lines, self.now = [], T0
        self.figures = walkers()
        self.tally, self.climb = tally or probe.Tally(), climb or stand_climb()
        self.round = probe.Round(number, ended, self.figures, self.lines.append, self.tally, self.climb)

    def holds(self):
        """The fireman picked, at his place, and FIRE: task 1 ends."""
        self.frame(y=70)
        self.figures[probe.FIREMAN].x = 127
        return self.frame(y=70, boot=ON, fire=True)

    def at_foot(self):
        self.figures[probe.CHILD].x = 131
        return self

    def ms(self):
        """The ms since READY's end, at 600 ms."""
        return self.now - T0 - 600


def climbs(p, frames=400):
    """Frames with the stick up until the round ends: a round that does not end in frames is a failure."""
    for _ in range(frames):
        if p.round.ended:
            return p
        p.frame(y=-70)
    raise AssertionError("the round did not end in %d frames" % frames)


class WholeRoundTest(unittest.TestCase):
    """The whole round on scripted frames: the pick's words, FIRE, the climb, the end line and READY."""

    def test_the_four_pairs_of_right_or_wrong_and_switch_or_same(self):
        p = Run().ready()
        p.frame(y=-70).frame().frame(y=70).frame().frame(y=70)  # task 1 wants the fireman. the child is active
        self.assertEqual(["p906 pick child wrong same ground 41", "p906 pick fireman right switch ground 123",
                          "p906 pick fireman right same ground 205"], p.lines[1:])
        p.figures[probe.FIREMAN].x = 127
        p.frame(fire=True, boot=ON).frame(y=-70).frame().frame(y=-70).frame(y=70)  # task 2 wants the child
        self.assertEqual(["p906 pick child right switch ground 287", "p906 pick child right same ground 369",
                          "p906 pick fireman wrong switch ground 410"], p.lines[-3:])

    def test_ready_a_lean_that_starts_at_599_ms_is_a_pick_at_600_with_0_ms(self):
        p = Run().frame(at=0).frame(at=599, y=70).frame(at=600, y=72)
        self.assertEqual(["p906 round 1 starts after 0", "p906 pick fireman right switch ground 0"], p.lines)

    def test_ready_a_lean_from_before_ready_is_no_pick(self):
        p = Run().frame(at=0, y=-70).frame(at=599, y=-75).frame(at=600, y=-77).frame(at=641, y=-81)
        self.assertEqual(["p906 round 1 starts after 0"], p.lines)

    def test_fire_holds_within_24_px_and_ends_task_1_and_at_25_px_it_holds_nothing_and_is_not_scored(self):
        p = Run().ready()
        p.frame(y=70)
        p.figures[probe.FIREMAN].x = 127 + 25
        p.frame(y=70, fire=True, click=ON)
        p.figures[probe.FIREMAN].x = 127 - 24
        p.frame(y=70, fire=True, boot=ON)
        self.assertEqual(["p906 act none click 82", "p906 act hold boot 123", "p906 task 1 ends clean"],
                         p.lines[2:])
        self.assertEqual((2, 127, False), (p.round.task, p.figures[probe.FIREMAN].x, p.tally.round_wrong))

    def test_a_fire_of_the_child_or_a_second_fire_of_the_holding_fireman_is_listed_and_not_scored(self):
        p = Run().ready()
        p.frame(fire=True, boot=ON)
        p.holds().frame(y=70, fire=True, click=ON)
        self.assertEqual(["p906 act none boot 41", "p906 act hold boot 123", "p906 task 1 ends clean",
                          "p906 act none click 164"], [line for line in p.lines if " act " in line or " task " in line])
        self.assertFalse(p.tally.round_wrong)

    def test_in_one_frame_the_fire_comes_first_and_the_pick_after_it(self):
        p = Run().ready()
        p.frame(y=70)
        p.figures[probe.FIREMAN].x = 127
        p.frame(y=-70, fire=True, boot=ON)
        self.assertEqual(["p906 act hold boot 82", "p906 task 1 ends clean", "p906 pick child right switch ground 82"],
                         p.lines[2:])

    def test_no_climb_before_the_hold(self):
        p = Run().ready().at_foot()
        p.frame(y=-70).frame(y=-70)
        self.assertEqual((False, []), (p.figures[probe.CHILD].on_ladder, [ln for ln in p.lines if " climb " in ln]))

    def test_no_climb_1_px_from_the_foot_and_a_climb_at_it(self):
        p = Run().ready().holds()
        p.figures[probe.CHILD].x = 132
        p.frame(y=-70).frame(y=-70)
        self.assertFalse(p.figures[probe.CHILD].on_ladder)
        p.at_foot().frame(y=-70)
        self.assertEqual(("p906 climb starts 0 205", True), (p.lines[-1], p.figures[probe.CHILD].on_ladder))

    def test_the_climb_starts_at_a_lean_of_40_and_not_at_39(self):
        p = Run().ready().holds()
        p.frame(y=-70).frame().at_foot().frame(y=-39)
        self.assertFalse(p.figures[probe.CHILD].on_ladder)
        p.frame(y=-40)
        self.assertEqual(["p906 pick child right same ground %d" % p.ms(), "p906 climb starts 0 %d" % p.ms()],
                         p.lines[-2:])

    def test_the_climb_goes_on_at_20_and_stops_at_19_and_the_child_stays(self):
        p = Run().ready().holds()
        p.frame(y=-70).at_foot().frame(y=-70).frame(y=-60)
        child = p.figures[probe.CHILD]
        self.assertEqual((41, 1), (p.climb.ms, child.up))
        p.frame(y=-20)
        self.assertEqual((82, 2), (p.climb.ms, child.up))
        p.frame(y=-19)
        self.assertEqual("p906 climb stops 2 %d" % p.ms(), p.lines[-1])
        p.frame(y=-3)
        self.assertEqual((82, 2, True), (p.climb.ms, child.up, child.on_ladder))
        self.assertEqual((131 - 1, -1), (child.x, child.facing))  # forward is left, toward the station

    def test_a_lean_up_that_lasts_from_the_pick_through_the_run_climbs_at_the_foot(self):
        p = Run().ready().holds()
        child = p.figures[probe.CHILD]
        child.x = 131 + 4
        p.frame(y=-70, x=-80, ms=60)  # the pick, and 43 px a second over 60 ms: 3 px to the left
        self.assertEqual((132, False), (child.x, child.on_ladder))
        p.frame(y=-70, x=-80, ms=60)  # past the foot: it stops at it, and climbs in this frame
        self.assertTrue(child.on_ladder)
        self.assertEqual("p906 climb starts 0 %d" % p.ms(), p.lines[-1])

    def test_on_the_ladder_a_lean_down_picks_the_fireman_and_the_child_stays(self):
        p = Run().ready().holds()
        p.frame(y=-70).at_foot()
        for _ in range(9):
            p.frame(y=-70)
        child = p.figures[probe.CHILD]
        x, up = child.x, child.up
        p.frame(y=70)
        self.assertEqual(["p906 pick fireman wrong switch ladder %d %d" % (up, p.ms()),
                          "p906 climb stops %d %d" % (up, p.ms())], p.lines[-2:])
        p.frame(y=70, x=80)
        self.assertEqual((x, up, probe.FIREMAN), (child.x, child.up, p.round.active))

    def test_the_end_at_the_first_pose_54_px_up_with_its_lines_in_order(self):
        tally = probe.Tally()
        tally.streak = 3
        p = Run(tally=tally).ready().holds()
        p.frame(y=-70).at_foot()
        climbs(p)
        child = p.figures[probe.CHILD]
        self.assertEqual((54, 41 * 56), (child.up, p.climb.ms))  # 2296 // 43 is pose 53, 2255 // 43 pose 52
        self.assertEqual(["p906 climb stops 54 %d" % p.ms(), "p906 task 2 ends clean"], p.lines[-3:-1])
        self.assertTrue(p.lines[-1].startswith("p906 round 1 ends clean ms %d gaps " % p.ms()), p.lines[-1])
        self.assertTrue(p.lines[-1].endswith(" streak 4"), p.lines[-1])
        lines = len(p.lines)
        p.frame(y=70, fire=True, boot=ON)
        self.assertEqual(lines, len(p.lines))  # an ended round reads nothing

    def test_the_end_lines_gaps_ms_worst_and_slow_from_the_frames_clock(self):
        p = Run().ready().holds()
        p.frame(y=-70).at_foot()
        frames = 3  # after READY's end: the two of holds() and the pick
        for gap in (52, 53, 300) + (41,) * 200:  # a gap of 52 is not slow, 53 and 300 are. the ms is capped at 60
            p.frame(at=p.now - T0 + gap, ms=min(gap, 60), y=-70)
            frames += 1
            if p.round.ended:
                break
        self.assertTrue(p.round.ended, "the round did not end")
        words = p.lines[-1].split()
        self.assertEqual((["ms", "gaps", "worst", "slow"], [p.ms(), frames, 300, 2]),
                         (words[5:13:2], [int(n) for n in words[6:13:2]]))

    def test_no_round_ends_by_itself(self):
        p = Run().ready()
        for _ in range(1500):
            p.frame()
        self.assertEqual((False, 1), (p.round.ended, len(p.lines)))

    def test_streak_5_met_comes_right_after_its_rounds_end_line(self):
        tally = probe.Tally()
        tally.streak = 4
        p = Run(number=5, tally=tally).ready().holds()
        p.frame(y=-70).at_foot()
        climbs(p)
        self.assertTrue(p.lines[-2].startswith("p906 round 5 ends clean "), p.lines[-2])
        self.assertEqual("p906 streak 5 met", p.lines[-1])


def schedule(*stops):
    """Frame times from READY's end: each stop (time, n) reached in n gaps as even as whole ms allow."""
    times, last = [0], 0
    for to, n in stops:
        times += [last + (to - last) * k // n for k in range(1, n + 1)]
        last = to
    return times


EXAMPLE = """p906 round 3 starts after 2140
p906 pick fireman right switch ground 610
p906 act hold boot 2980
p906 task 1 ends clean
p906 pick child right switch ground 3350
p906 climb starts 0 5120
p906 climb stops 57 8460
p906 task 2 ends clean
p906 round 3 ends clean ms 8460 gaps 199 worst 96 slow 2 streak 3
p906 round 4 starts after 1310
p906 pick child wrong same ground 420
p906 pick fireman right switch ground 980
p906 act hold click 2710
p906 task 1 ends wrong
p906 pick child right switch ground 3020
p906 climb starts 0 4700
p906 climb stops 57 8010
p906 task 2 ends clean
p906 round 4 ends wrong ms 8010 gaps 188 worst 88 slow 1 streak 0""".splitlines()  # the plan's example log


class ExampleTest(unittest.TestCase):
    """The plan's example log, from round 3's start line on, from the events it names on scripted frames, on the real
    climb's numbers."""

    def play(self, lines, number, ended, start, tally, stops, events):
        """One round: its first frame at start, READY, then the schedule's frames with each event at its ms (the
        stick's y from then on, FIRE with its button, or a figure put at its place before the frame). Answers the
        clock of its end."""
        figures = walkers()
        pose_ms, travel, advance = REAL_CLIMB
        r = probe.Round(number, ended, figures, lines.append, tally,
                        probe.Climb(pose_ms // probe.CLIMB_PACE, travel, advance, 54))
        r.step(start, 41, frame(), NONE)
        r.step(start + 300, 41, frame(), NONE)
        y, last = 0, None
        for t in schedule(*stops):
            now, fire, boot, click = start + 600 + t, False, NONE, NONE
            for what in events.get(t, ()):
                if what in ("up", "down"):
                    y = -70 if what == "up" else 70
                elif what in ("boot", "click"):
                    fire, boot, click = True, ON if what == "boot" else NONE, ON if what == "click" else NONE
                else:
                    figures[what].x = figures[what].lo
            r.step(now, 41 if last is None else min(now - last, 60), frame(fire=fire, y=y), boot)
            last = now
            if r.ended:
                return now
        raise AssertionError("the round did not end")

    def test_the_plans_example_line_by_line(self):
        lines, tally = [], probe.Tally()
        tally.streak = 2
        end = self.play(lines, 3, T0 - 2140, T0, tally,
                        ((96, 1), (153, 1), (610, 10), (2980, 56), (3350, 9), (5120, 42), (8460, 80)),
                        {610: ("down",), 2980: (probe.FIREMAN, "boot"), 3350: ("up",), 5120: (probe.CHILD,)})
        self.play(lines, 4, end, end + 1310, tally,
                  ((88, 1), (420, 8), (980, 13), (2710, 41), (3020, 7), (4700, 40), (8010, 78)),
                  {420: ("up",), 980: ("down",), 2710: (probe.FIREMAN, "click"), 3020: ("up",),
                   4700: (probe.CHILD,)})
        for k, (expected, line) in enumerate(zip(EXAMPLE, lines)):
            with self.subTest(line=k):
                self.assertEqual(expected, line)
        self.assertEqual(len(EXAMPLE), len(lines))


class ExitTest(unittest.TestCase):
    """Exit: PICK twice within 3 s."""

    def test_a_second_pick_at_3000_ms_quits_and_at_3001_it_arms_again(self):
        lines = []
        door = probe.Exit(lines.append)
        self.assertFalse(door.step(T0, True))
        self.assertTrue(door.step(T0 + 3000, True))
        door = probe.Exit(lines.append)
        door.step(T0, True)
        self.assertFalse(door.step(T0 + 3001, True))
        self.assertEqual(["p906 quit armed"] * 3, lines)

    def test_it_shows_armed_for_3000_ms_and_not_at_3001(self):
        door = probe.Exit(lambda line: None)
        door.step(T0, True)
        door.step(T0 + 3000, False)
        self.assertTrue(door.armed)
        door.step(T0 + 3001, False)
        self.assertFalse(door.armed)


def finish(box):
    """A clean round through the App from READY's end: down picks the fireman, he stands at his place and FIRE holds.
    up picks the child, it stands at the foot and climbs until the round ends."""
    game = box.app.game
    fireman, child = game.figures
    box.frame(y=70)
    fireman.x = fireman.lo
    box.frame(y=70, fire=True)
    box.frame(y=-70)
    child.x = child.lo
    for _ in range(3000):
        box.frame(y=-70)
        if game.state == gfx.OVER:
            return box
    raise AssertionError("the round did not end")


def again(box):
    """FIRE on the result screen at 900 ms, then the next round's first frame and READY."""
    return box.frame(ms=900, fire=True).frame().frame(ms=600)


class WholeGameTest(unittest.TestCase):
    """The whole game through app.App: rounds, the result screen, the marks and the way out."""

    def test_the_bar_is_drawn_once_in_three_rounds_and_the_task_block_follows_its_copy(self):
        box = Box(self)
        box.out.cv.seen.clear()
        box.play()
        for _ in range(3):
            finish(box)
            again(box)
        self.assertEqual([1, 1, 1], [box.out.cv.seen.count(row) for row in probe.BAR])
        box.frame(y=70)
        box.app.game.figures[0].x = box.app.game.figures[0].lo
        box.frame(y=70, fire=True).frame()  # task 2: the block on the second row
        ops = box.out.cv.ops
        bar = [i for i, op in enumerate(ops) if op[4] == 3 and op[5] in probe.BAR]
        block = [i for i, op in enumerate(ops) if op[:6] == (2, 9, 8, 15, 0, gfx.YELLOW)]
        self.assertEqual(1, len(block))
        self.assertGreater(block[0], max(bar))

    def test_fire_on_the_result_screen_starts_the_next_round_at_900_ms_and_not_at_899(self):
        box = finish(Box(self).play())
        box.frame(ms=899, fire=True)
        self.assertEqual(gfx.OVER, box.app.game.state)
        box.frame(ms=1, fire=True)
        self.assertEqual(gfx.PLAY, box.app.game.state)
        box.frame()
        self.assertEqual("p906 round 2 starts after 941", box.lines()[-1])

    def test_the_next_round_starts_with_the_child_active_and_both_figures_at_their_start_places(self):
        box = again(finish(Box(self).play()))
        game, start = box.app.game, box.numbers["start"]
        self.assertEqual((probe.CHILD, [start[0], start[1]], [False, False], [0, 0]), (
            game.round.active, [f.x for f in game.figures], [f.holds or f.on_ladder for f in game.figures],
            [f.up for f in game.figures]))

    def test_the_result_screen_is_kept_with_the_rounds_time_the_best_and_the_streak(self):
        box = finish(Box(self).play())
        r = box.app.game.round
        ms = int(box.lines()[-1].split()[6])
        box.frame()
        seen = box.out.cv.seen
        self.assertIn("time %d.%d s" % (ms // 1000, ms % 1000 // 100), seen)
        self.assertIn("best %d.%d s" % (ms // 1000, ms % 1000 // 100), seen)
        self.assertIn("clean 1/5", seen)
        self.assertNotIn("5 IN A ROW", seen)
        self.assertNotIn("FIRE: again", seen)
        box.frame()
        self.assertEqual([], box.out.cv.words)  # kept
        box.frame(ms=900)
        self.assertIn("FIRE: again", box.out.cv.words)
        self.assertIs(r, box.app.game.round)

    def test_after_five_clean_rounds_the_log_says_streak_5_met_once_and_the_screen_5_in_a_row(self):
        box = Box(self).play()
        for k in range(6):
            finish(box)
            box.frame(ms=900)
            if k < 5:
                again(box)
        lines = box.lines()
        self.assertEqual(1, lines.count("p906 streak 5 met"))
        self.assertTrue(lines[lines.index("p906 streak 5 met") - 1].startswith("p906 round 5 ends clean "))
        self.assertIn("5 IN A ROW", box.out.cv.seen)

    def test_a_pick_pair_quits_in_the_intro_in_play_and_on_the_result_screen(self):
        for where in ("intro", "play", "result"):
            with self.subTest(where=where):
                box = Box(self)
                if where != "intro":
                    box.play()
                if where == "result":
                    finish(box)
                box.frame(pick=True)
                self.assertEqual("p906 quit armed", box.lines()[-1])
                self.assertIn("PICK again: quit", box.out.cv.words)
                with self.assertRaises(probe.Quit):
                    box.frame(ms=2959, pick=True)

    def test_the_mark_is_over_the_figure_to_pick_then_at_the_place_to_run_to(self):
        box = Box(self).play()
        fireman, child = box.app.game.figures

        def mark():
            """The yellow fills but the task block: their middle column and their lowest row."""
            fills = [op for op in box.out.cv.ops if op[4] == 0 and op[5] == gfx.YELLOW and op[0] > 8]
            return (min(op[0] for op in fills) + max(op[2] for op in fills)) // 2, max(op[3] for op in fills) - 1

        def over(f):
            return f.x, probe.FEET - f.up + f.picture()[2] - 6

        box.frame()
        self.assertEqual(over(fireman), mark())  # task 1, the child active: pick the fireman
        box.frame(y=70)
        self.assertEqual((115, 222 + 4), mark())  # run to his place
        fireman.x = fireman.lo
        box.frame(y=70, fire=True)
        self.assertEqual(over(child), mark())  # task 2: pick the child
        box.frame(y=-70)
        self.assertEqual((80, 88 + 4), mark())  # run to the roof's edge

    def test_the_child_climbs_in_its_climbs_pictures_and_the_fireman_holds_in_his_hold(self):
        box = Box(self).play()
        fireman, child = box.app.game.figures
        box.frame(y=70)
        fireman.x = fireman.lo
        box.frame(y=70, fire=True).frame(y=-70)
        child.x = child.lo
        box.frame(y=-70).frame(y=-70)
        box.pictures.drawn.clear()
        box.frame(y=-70)
        names = [name for name, _, _ in box.pictures.drawn]
        self.assertEqual("mission_fireman_hold_l0", names[2])
        self.assertTrue(names[3].startswith("mission_child_climb_l"), names)
        name, dx, dy = child.picture()
        self.assertEqual((name, child.x + dx, probe.FEET - child.up + dy), box.pictures.drawn[3])


class ReviewRoundTest(unittest.TestCase):
    """The review's points on the round (P906, PR 118): READY keeps every lean and every FIRE, the clock starts at the
    frame where READY ends, and the child on the ladder does not run."""

    def test_every_lean_that_starts_in_ready_is_a_pick_at_its_end_in_order(self):
        p = Run().frame(at=0).frame(at=100, y=-70).frame(at=200).frame(at=300, y=70).frame(at=600, y=72)
        self.assertEqual(["p906 round 1 starts after 0", "p906 pick child wrong same ground 0",
                          "p906 pick fireman right switch ground 0"], p.lines)
        self.assertTrue(p.tally.round_wrong)

    def test_a_ninth_lean_in_one_ready_is_dropped(self):
        p = Run().frame(at=0)
        for k in range(9):  # up, down, up, ...: each a new lean at once
            p.frame(at=10 + 20 * k, y=-70 if k % 2 == 0 else 70)
        p.frame(at=600, y=0)
        self.assertEqual(8, len([line for line in p.lines if " pick " in line]))
        self.assertEqual(8, probe.READY_WAITS)

    def test_a_fire_in_ready_is_listed_at_its_end_as_act_none_with_0_ms(self):
        p = Run().frame(at=0).frame(at=300, fire=True, boot=ON).frame(at=600)
        self.assertEqual(["p906 round 1 starts after 0", "p906 act none boot 0"], p.lines)
        self.assertFalse(p.tally.round_wrong)

    def test_in_ready_the_fires_come_before_the_picks(self):
        p = Run().frame(at=0).frame(at=100, y=70).frame(at=300, fire=True, click=ON, y=70).frame(at=600, y=70)
        self.assertEqual(["p906 act none click 0", "p906 pick fireman right switch ground 0"], p.lines[1:])

    def test_fire_with_the_child_active_holds_nothing_though_the_fireman_stands_at_his_place(self):
        p = Run().ready()
        p.figures[probe.FIREMAN].x = 127
        p.frame(fire=True, boot=ON)
        self.assertEqual("p906 act none boot 41", p.lines[-1])
        self.assertEqual((False, 1), (p.figures[probe.FIREMAN].holds, p.round.task))

    def test_the_clock_starts_at_the_frame_where_ready_ends_at_623_ms(self):
        p = Run().frame(at=0).frame(at=311).frame(at=623)
        p.holds().frame(y=-70).at_foot()
        frames = 3
        for _ in range(400):
            p.frame(y=-70)
            frames += 1
            if p.round.ended:
                break
        words = p.lines[-1].split()
        self.assertEqual([p.now - T0 - 623, frames], [int(words[6]), int(words[8])])
        self.assertIn("p906 act hold boot 82", p.lines)

    def test_on_the_ladder_a_lean_of_the_sticks_x_does_not_move_the_child(self):
        p = Run().ready().holds()
        p.frame(y=-70).at_foot().frame(y=-70).frame(y=-70)
        child = p.figures[probe.CHILD]
        x = child.x
        p.frame(x=-80).frame(x=80, y=3)
        self.assertEqual((x, True, probe.CHILD), (child.x, child.on_ladder, p.round.active))


class ReviewGameTest(unittest.TestCase):
    """The review's points through app.App: the streak across rounds, a lean that sags into the next round, and the
    pack line."""

    def test_a_wrong_round_and_then_a_clean_one_end_with_streak_1(self):
        box = Box(self).play()
        box.frame(y=-70).frame()  # task 1 wants the fireman: a wrong pick
        again(finish(box))
        finish(box)
        ends = [line.split() for line in box.lines() if line.startswith("p906 round ") and " ends " in line]
        self.assertEqual([("wrong", "0"), ("clean", "1")], [(words[4], words[-1]) for words in ends])

    def test_a_lean_up_held_from_the_last_climb_that_sags_to_35_is_no_pick_in_the_next_round(self):
        box = finish(Box(self).play())
        box.frame(ms=900, fire=True, y=-35).frame(y=-35).frame(ms=600, y=-45).frame(y=-50)
        lines = box.lines()
        after = lines[lines.index("p906 round 2 starts after 941"):]
        self.assertEqual([], [line for line in after if " pick " in line])

    def test_the_pack_line_is_said_once_in_a_sitting(self):
        box = Box(self, pool=lambda n: bytearray(1))
        again(finish(box.play()))
        finish(box)
        self.assertEqual(1, len([line for line in box.said.getvalue().splitlines() if line.startswith("pack ")]))


STAND_IN_MPREMOTE = """#!PYTHON -u
import os, sys, time
record = os.environ["P906_RECORD"]
said = open(record).read().splitlines() if os.path.exists(record) else []
with open(record, "a") as f:  # each command, so the test sees the removal and the final reset
    f.write(" ".join(sys.argv[1:]) + "\\n")
lent = [line for line in said if line.startswith("cp ") and line.endswith(":art_index.py")]
if sys.argv[1:] == ["ls", ":"]:
    print("        0 packs/")
    if lent:
        print("     1234 art_index.py")
elif sys.argv[1:] == ["ls", ":packs"]:
    print("   660008 rescue.pak")
    if lent:
        print("   773470 mission.pak")
elif sys.argv[1] == "run":
    print("p906 rules lean 40")
    with open(record, "a") as f:
        f.write("pid %d\\n" % os.getpid())
    time.sleep(30)
"""

MAC_CHILD = """import os, sys
sys.path.insert(0, %r)
import probe906_ladder as probe


class Art:
    SET = "mission"

    def capture(self, parser):
        return None

    def painted(self, capture):
        return None

    def write(self, folder, painted):
        os.makedirs(os.path.join(folder, "packs"))
        pack, index = os.path.join(folder, "packs", "mission.pak"), os.path.join(folder, "art_index.py")
        for path in (pack, index):
            open(path, "w").close()
        return pack, index

    def numbers(self, painted):
        return {}


probe.LOG = %r
mac = probe.mac
probe.mac = lambda argv: mac(argv, art=Art())
probe.main([])
"""


class SignalTest(unittest.TestCase):
    """The Mac part from the command line in a real process, with a stand-in mpremote on PATH and a stand-in for
    art/mission.py: a SIGTERM or a SIGHUP ends it as a Ctrl-C does, with the removal and then the reset."""

    def test_a_sigterm_or_a_sighup_kills_the_run_removes_both_copies_and_resets_the_box(self):
        import signal

        for signum in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=signum), tempfile.TemporaryDirectory() as tmp:
                record, log = os.path.join(tmp, "record"), os.path.join(tmp, "run.log")
                stand_in = os.path.join(tmp, "mpremote")
                with open(stand_in, "w") as f:
                    f.write(STAND_IN_MPREMOTE.replace("PYTHON", sys.executable))
                os.chmod(stand_in, 0o755)
                child = os.path.join(tmp, "child.py")
                with open(child, "w") as f:
                    f.write(MAC_CHILD % (REPO, log))
                env = dict(os.environ, PATH=tmp + os.pathsep + os.environ["PATH"], P906_RECORD=record)
                mac = subprocess.Popen([sys.executable, "-B", child], env=env, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                self.addCleanup(mac.kill)
                end = time.monotonic() + 20
                while time.monotonic() < end and mac.poll() is None and not (
                        os.path.exists(log) and open(log).read()):
                    time.sleep(0.05)  # the run's first line is in the log: the Mac part reads its lines
                mac.send_signal(signum)
                self.assertNotEqual(0, mac.wait(timeout=20))
                with open(record) as f:
                    said = [line for line in f.read().splitlines() if not line.startswith("pid ")]
                with open(record) as f:
                    pid = int([line for line in f.read().splitlines() if line.startswith("pid ")][0].split()[1])
                self.addCleanup(end_if_left, pid)
                run = [k for k, line in enumerate(said) if line.startswith("run ")][0]
                self.assertEqual(["ls :", "reset", "exec pass"], [said[0], said[3], said[4]])
                self.assertEqual(["ls :", "ls :packs", "rm :art_index.py", "rm :packs/mission.pak", "reset"],
                                 said[run + 1:])
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)  # no child left


def end_if_left(pid):
    try:
        os.kill(pid, 9)
    except ProcessLookupError:
        pass


class MacValuesTest(unittest.TestCase):
    def test_the_log_and_the_time_limit_are_the_plans(self):
        self.assertEqual(("logs/run-p906-ladder.log", 60), (probe.LOG, probe.MINUTES))


if __name__ == "__main__":
    unittest.main()
