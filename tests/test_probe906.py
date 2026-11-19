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

if not hasattr(time, "ticks_add"):  # the stubs give ticks_diff, ticks_us and ticks_ms; app.run adds
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
        self.round.step(self.now, ms, frame(**inputs), boot, click)
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
                drawn = [(op[:4], op[5]) for op in box.out.cv.ops if op[4] == 0 and op[5] in (gfx.WHITE, gfx.BLACK)]
                self.assertEqual(rim + white, drawn)  # the rim first, the arrow over it
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
    return [["ls", ":"], ["ls", ":packs"], ["rm", ":art_index.py", ":packs/mission.pak"]]


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
        self.assertEqual([None] * 5 + [3600] + [None] * 4, board.limits)
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
        self.assertEqual(removal() + [["reset"]], board.commands[-4:])
        self.assertEqual(out.decode(), self.logged())

    def test_a_limit_with_no_p906_round_line_is_refused_with_its_last_line_and_the_log(self):
        out = b"p906 rules lean 40\ngame ladder\np906 intro ends time\n"
        board = StreamBoard(run_error=subprocess.TimeoutExpired(["mpremote", "run"], 3600, output=out, stderr=None))
        said, err, refused = self.mac([], board)
        self.assertEqual("refused: the run took over 3600 s: p906 intro ends time; the log is %s" % self.log,
                         refused.code)
        self.assertEqual(removal() + [["reset"]], board.commands[-4:])

    def test_a_failed_run_is_refused_with_its_last_line_and_the_log(self):
        board = StreamBoard(run_error=subprocess.CalledProcessError(
            1, ["mpremote", "run"], output="p906 rules lean 40\n",
            stderr="Traceback (most recent call last):\nRuntimeError: p906 refused: no stick in the pin map\n"))
        said, err, refused = self.mac([], board)
        self.assertEqual("refused: the run failed with exit 1: RuntimeError: p906 refused: no stick in the pin map; "
                         "the log is %s" % self.log, refused.code)
        self.assertEqual(removal() + [["reset"]], board.commands[-4:])

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
                         "the run failed with exit 1; :art_index.py and :packs/mission.pak may still be on the box: "
                         "run `mpremote rm :art_index.py :packs/mission.pak`, then `mpremote reset`; the log is %s"
                         % self.log, refused.code)
        self.assertEqual(["reset"], board.commands[-1])

    def test_a_ctrl_c_keeps_the_log_removes_both_and_resets_the_box(self):
        board = StreamBoard(said="p906 rules lean 40\n", run_error=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            self.mac([], board)
        self.assertEqual("p906 rules lean 40\n", self.logged())
        self.assertEqual(removal() + [["reset"]], board.commands[-4:])

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
                          "mpremote ls :", "mpremote ls :packs", "mpremote rm :art_index.py :packs/mission.pak",
                          "mpremote reset"], lines)
        self.assertFalse(os.path.exists(self.log))



class MacValuesTest(unittest.TestCase):
    def test_the_log_and_the_time_limit_are_the_plans(self):
        self.assertEqual(("logs/run-p906-ladder.log", 60), (probe.LOG, probe.MINUTES))


if __name__ == "__main__":
    unittest.main()
