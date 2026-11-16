"""A D14 press picks (P818) on the Mac, through App.frame itself with a clock the test sets: the game goes and a
NameCard shows the next name, nothing is imported or loaded, and the picked game is built once the pick settles
(SETTLE_MS with no press, or a BOOT press, which is used up). The cues stop at a pick and the music plays on, and the
knob's pane works over a NameCard. Run from the repository root: python3 -B -m unittest tests.test_pick.
--- MVP (P818) ---"""

import contextlib
import io
import os
import re
import sys
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_app_knob import Encoder  # noqa: E402  also puts games/ and the stubs on the path, and time's ticks
from test_signals import Loud, MusicBank, rendered  # noqa: E402

import app  # noqa: E402
import catalog  # noqa: E402
import cues  # noqa: E402
import gfx  # noqa: E402
import pictures  # noqa: E402
import sound  # noqa: E402
import volume  # noqa: E402

BUILT = []  # each counting game's name, as it is built


def counting(name):
    class Counting(gfx.Game):
        presses = None

        def setup(self):
            if self.presses is None:
                BUILT.append(self.name)
                self.presses = []

        def step(self, now_ms, pressed, held):
            self.presses.append(pressed)

    Counting.name = name
    return Counting


GAMES = tuple(counting(n) for n in "abcdef")


class Out:
    def __init__(self):
        self.resets, self.seen = 0, []

    def clear(self):
        pass

    def reset(self):
        self.resets += 1

    def draw(self, game, us, overlay):
        self.seen.append([pane.visible for pane in overlay.panes])


class Box:
    """An App on a clock the test sets, with D14 and BOOT pressed when the test says."""

    def __init__(self, games=GAMES, **kw):
        self.ms, self.d14, self.boot = 0, False, False
        self.clock = mock.patch.object(app.time, "ticks_ms", lambda: self.ms)
        self.clock.start()
        self.said = io.StringIO()
        with contextlib.redirect_stdout(self.said):
            self.app = app.App(None, lambda: 99, lambda: 99, games=games, out=Out(), **kw)
            self.app.fire.update = lambda now: self.boot
            self.app.boot.update = lambda now: self.d14
            self.app.start()

    def frame(self, ms, d14=False, boot=False):
        self.ms, self.d14, self.boot = ms, d14, boot
        with contextlib.redirect_stdout(self.said):
            self.app.frame()
        return self.app.game

    def run_build(self, limit=1000):
        """Frames FRAME_MS apart until the build behind the card ends: the game it built (P822). The settle that
        starts the build is the frame before."""
        for _ in range(limit):
            game = self.frame(self.ms + app.FRAME_MS)
            if not isinstance(game, app.NameCard):
                return game
        raise AssertionError("the build did not end in %d frames" % limit)

    def lines(self, word):
        return [line for line in self.said.getvalue().splitlines() if line.split()[0] == word]

    def close(self):
        self.clock.stop()


class PickTest(unittest.TestCase):
    def setUp(self):
        BUILT.clear()
        self.box = Box()
        self.addCleanup(self.box.close)

    def test_four_presses_in_a_row_build_only_the_fifth_game(self):
        box = self.box
        for k in range(4):
            box.frame(100 * k, d14=True)
        self.assertEqual(["a"], BUILT)  # the first game, built by start(); nothing for the four picks
        box.frame(300 + app.SETTLE_MS)
        game = box.run_build()
        self.assertNotIsInstance(game, app.NameCard)
        self.assertEqual(["a", "e"], BUILT)
        self.assertEqual("e", game.name)
        self.assertEqual(["pick b", "pick c", "pick d", "pick e"], box.lines("pick"))
        self.assertEqual(2, len(box.lines("switch")))  # start's and the settled pick's
        self.assertRegex(box.lines("switch")[1],
                         r"^switch e \d+ ms, load \d+ ms, import \d+ ms, frames \d+, worst \d+ ms, longest \d+ ms$")

    def test_the_pick_settles_at_settle_ms_not_before(self):
        box = self.box
        box.frame(1000, d14=True)
        card = box.frame(1000 + app.SETTLE_MS - 1)
        self.assertIsInstance(card, app.NameCard)
        self.assertEqual(("b", gfx.TITLE), (card.name, card.state))
        box.frame(1000 + app.SETTLE_MS)
        self.assertEqual(["a"], BUILT)  # settled in this frame, not before: its build has not run yet
        game = box.run_build()
        self.assertNotIsInstance(game, app.NameCard)
        self.assertEqual("b", game.name)
        self.assertEqual(["a", "b"], BUILT)

    def test_each_press_starts_the_wait_again(self):
        box = self.box
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS - 1, d14=True)
        self.assertIsInstance(box.frame(app.SETTLE_MS + 10), app.NameCard)
        box.frame(2 * app.SETTLE_MS - 1)
        self.assertEqual(["a"], BUILT)  # settled in this frame, not at the first press's SETTLE_MS
        game = box.run_build()
        self.assertNotIsInstance(game, app.NameCard)
        self.assertEqual("c", game.name)

    def test_boot_on_a_card_builds_at_once_and_the_press_does_not_reach_the_game(self):
        box = self.box
        box.frame(0, d14=True)
        box.frame(10, boot=True)
        game = box.run_build()
        self.assertNotIsInstance(game, app.NameCard)
        self.assertEqual("b", game.name)
        self.assertEqual([], game.presses)  # the build frames do not step the game
        box.frame(box.ms + app.FRAME_MS)
        self.assertEqual([False], game.presses)
        self.assertEqual(gfx.TITLE, game.state)

    def test_the_pick_resets_the_output_and_the_card_shows_its_place(self):
        box = self.box
        before = box.app.out.resets
        card = box.frame(0, d14=True)
        self.assertEqual(before + 1, box.app.out.resets)
        self.assertEqual((2, 6), (card.n, card.count))

    def test_a_press_in_play_reaches_the_game(self):
        game = self.box.frame(0, boot=True)
        self.assertEqual([True], game.presses)


class ReviewTest(unittest.TestCase):
    """The review's cases (P818): what a build after a pick must do, and what must not happen around it."""

    def setUp(self):
        BUILT.clear()

    def box(self, games=GAMES, **kw):
        box = Box(games, **kw)
        self.addCleanup(box.close)
        return box

    def test_later_frames_do_not_build_the_settled_game_again(self):
        box = self.box()
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        game = box.run_build()
        self.assertNotIsInstance(game, app.NameCard)
        for _ in range(3):
            self.assertIs(game, box.frame(box.ms + app.FRAME_MS))
        self.assertEqual(["a", "b"], BUILT)
        self.assertEqual(2, len(box.lines("switch")))

    def test_the_build_after_a_pick_resets_the_output(self):
        box = self.box()
        box.frame(0, d14=True)
        before = box.app.out.resets
        box.frame(app.SETTLE_MS)
        self.assertNotIsInstance(box.run_build(), app.NameCard)
        self.assertEqual(before + 1, box.app.out.resets)  # the card's frame used up the last reset

    def test_the_build_collects(self):
        box = self.box()
        box.frame(0, d14=True)
        with mock.patch.object(app.gc, "collect") as collect:
            box.frame(app.SETTLE_MS)
        collect.assert_called()

    def test_import_ms_is_the_import_s_time_alone(self):
        class Timed(gfx.Game):
            name = "p"

            def setup(self):
                box.ms += 7  # the build after the import

        def games_for(names):
            box.ms += 50  # the import
            return (Timed,)
        box = Box.__new__(Box)  # its clock first: games_for moves it
        with mock.patch.object(app, "games_for", games_for):
            Box.__init__(box, app.Lineup(("p", "q")))
        self.addCleanup(box.close)
        self.assertEqual(50, box.app.games.import_ms)
        self.assertRegex(box.lines("switch")[0], r"^switch p 57 ms, load 0 ms, import 50 ms$")

    def test_presses_during_a_build_are_dropped(self):
        holder = []

        class Pushy(gfx.Game):
            name = "pushy"
            steps = []

            def setup(self):  # a press of each button while the box is frozen in the build
                if holder:
                    holder[0].boot.pushes += 1
                    holder[0].fire.pushes += 1

            def step(self, now_ms, pressed, held):
                self.steps.append(pressed)

        box = app.App(None, lambda: 99, lambda: 99, games=(Pushy, GAMES[0]), out=Out())
        holder.append(box)
        box.boot.watched = box.fire.watched = True  # pushes counted as the pin interrupt counts them
        with contextlib.redirect_stdout(io.StringIO()) as said:
            box.start()
            box.frame()
        self.assertNotIn("pick", said.getvalue())
        self.assertEqual("pushy", box.game.name)
        self.assertEqual([False], box.game.steps)

    def test_one_game_makes_d14_do_nothing(self):
        box = self.box(GAMES[:1])
        for ms in (0, 100, 200):
            game = box.frame(ms, d14=True)
        self.assertEqual(("a", ["a"], []), (game.name, BUILT, box.lines("pick")))
        self.assertEqual([False] * 3, game.presses)

    def test_the_fps_lines_never_name_a_card(self):
        box = self.box()
        box.frame(app.FPS_EVERY_MS - 100, d14=True)
        box.frame(app.FPS_EVERY_MS)
        self.assertEqual([], box.lines("fps"))
        self.assertEqual(app.FPS_EVERY_MS - 100, box.app.mark)

    def test_the_build_is_not_the_slowest_frame_of_the_new_interval(self):
        class Slow(gfx.Game):
            name = "slow"

            def setup(self):
                time.sleep(0.05)

        box = self.box((GAMES[0], Slow))
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        self.assertNotIsInstance(box.run_build(), app.NameCard)
        self.assertLess(box.app.slow[0], 40000)  # us: the 50 ms setup is not in it

    def test_no_collect_on_the_card_frame(self):
        box = self.box(gc_floor=1)
        box.app.game.state = gfx.PLAY
        box.frame(0)
        with mock.patch.object(box.app, "collect") as collect:
            box.frame(10, d14=True)
        collect.assert_not_called()


class Steps:
    """A build's steps as Lineup.game_steps makes them: each of values, then the game built (StopIteration's value).
    Each step sleeps pause seconds; close() is counted."""

    def __init__(self, values, cls, pause=0):
        self.values, self.cls, self.pause, self.closed = list(values), cls, pause, 0

    def __iter__(self):
        return self

    def __next__(self):
        time.sleep(self.pause)
        if self.values:
            return self.values.pop(0)
        raise StopIteration(self.cls())

    def close(self):
        self.closed += 1


class Stepped(app.Lineup):
    """A lineup of classes whose builds take n steps each, a progress of k / n each; made keeps each build's Steps."""

    def __init__(self, classes, n, pause=0):
        super().__init__([c.name for c in classes], tuple(classes))
        self.n, self.pause, self.made = n, pause, []

    def game_steps(self, i):
        self.made.append(Steps([k / self.n for k in range(1, self.n + 1)], self.classes[i], self.pause))
        return self.made[-1]


def flaky(name):
    class Flaky(gfx.Game):
        fails = []  # while it holds an error, every Flaky's setup raises it named

        def setup(self):
            if self.fails:
                raise self.fails[0](self.name)

    Flaky.name = name
    return Flaky


class Painted(gfx.Game):
    name = "painted"
    ART = ("bucket", None)

    def setup(self):
        self.covers = pictures.load(*self.ART)


class BuildTest(unittest.TestCase):
    """The build behind the card (P822): a settled pick starts it, and each later frame runs BUILD_CHUNKS of its
    steps under the card, until the game starts."""

    def setUp(self):
        BUILT.clear()

    def box(self, games=GAMES, **kw):
        box = Box(games, **kw)
        self.addCleanup(box.close)
        return box

    def painted(self):
        """The real packs, each file the box opens kept."""
        root, files = pictures.ROOT, []

        def opened(path, mode):
            files.append(open(path, mode))
            return files[-1]

        def restore():
            del pictures.open
            pictures.free()
            pictures.ROOT = root
        pictures.ROOT = os.path.join(os.path.dirname(HERE), "games", "")
        pictures.free()
        pictures.open = opened
        self.addCleanup(restore)
        return files

    def test_the_settle_frame_draws_loading_and_imports_nothing(self):
        imports, games_for = [], app.games_for
        with mock.patch.object(app, "games_for", lambda names: imports.append(names) or games_for(names)):
            box = self.box(app.Lineup(("cave", "road")))
            box.frame(0, d14=True)
            card = box.frame(app.SETTLE_MS)
            self.assertIsInstance(card, app.NameCard)
            self.assertEqual((app.NameCard.LOADING, None), (card.caption, card.progress))
            self.assertEqual([("cave",)], imports)  # start's alone
            cv = gfx.Canvas()
            card.draw_title(cv)
            self.assertIn("loading", [op[5] for op in cv.ops if op[4] == 3])
            self.assertEqual("road", box.run_build().name)
        self.assertEqual([("cave",), ("road",)], imports)

    def test_a_card_frame_during_a_build_never_settles_again(self):
        box = self.box(Stepped(GAMES, 10 * app.BUILD_CHUNKS))
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        for k in range(1, 5):
            card = box.frame(app.SETTLE_MS + k * app.FRAME_MS, boot=True)  # BOOT would settle a waiting card
            self.assertIsInstance(card, app.NameCard)
        self.assertEqual(2, len(box.app.games.made))  # start's build and the settled pick's, once
        self.assertEqual(["a"], BUILT)

    def test_the_bar_grows_and_the_game_starts_when_the_steps_end(self):
        box = self.box(Stepped(GAMES, 3 * app.BUILD_CHUNKS))
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        shown = [box.frame(app.SETTLE_MS + k * app.FRAME_MS).progress for k in (1, 2, 3)]
        self.assertEqual([k * app.BUILD_CHUNKS / (3 * app.BUILD_CHUNKS) for k in (1, 2, 3)], shown)
        self.assertEqual(["a"], BUILT)
        game = box.frame(app.SETTLE_MS + 4 * app.FRAME_MS)
        self.assertEqual("b", game.name)
        self.assertEqual(["a", "b"], BUILT)

    def test_a_painted_game_s_set_loads_behind_the_card_a_few_chunks_a_frame(self):
        files = self.painted()
        box = self.box((GAMES[0], Painted))
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        shown, game = [], box.app.game
        while isinstance(game, app.NameCard):
            game = box.frame(box.ms + app.FRAME_MS)
            if isinstance(game, app.NameCard):
                shown.append(game.progress)
        self.assertLess(3, len(shown))  # the bucket's set takes several frames
        self.assertEqual(shown, sorted(shown))
        self.assertEqual(1, len(files))  # setup found the set loaded
        self.assertTrue(files[0].closed)
        self.assertIn("bucket_scene", pictures.PICS)
        frames = int(box.lines("switch")[-1].split("frames ")[1].split(",")[0])
        self.assertEqual(len(shown), frames)

    def test_d14_during_a_build_closes_its_steps_frees_the_set_and_picks_the_next(self):
        box = self.box(Stepped(GAMES, 10 * app.BUILD_CHUNKS))
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        box.frame(app.SETTLE_MS + app.FRAME_MS)
        steps = box.app.games.made[-1]
        with mock.patch.object(pictures, "free", wraps=pictures.free) as free:
            card = box.frame(app.SETTLE_MS + 2 * app.FRAME_MS, d14=True)
        self.assertEqual(1, steps.closed)
        free.assert_called()
        self.assertEqual(("c", app.NameCard.WAITING, None), (card.name, card.caption, card.progress))
        self.assertEqual(["pick b", "pick c"], box.lines("pick"))
        self.assertEqual(["game a"], box.lines("game"))
        box.frame(box.ms + app.SETTLE_MS)
        self.assertEqual("c", box.run_build().name)
        self.assertEqual(["a", "c"], BUILT)

    def test_d14_during_a_painted_build_closes_the_pack_and_keeps_no_set(self):
        files = self.painted()
        box = self.box((GAMES[0], Painted, GAMES[1]))
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        box.frame(app.SETTLE_MS + app.FRAME_MS)
        self.assertFalse(files[0].closed)
        steps = box.app.steps  # held: only close() can close the pack, not CPython's refcount
        box.frame(app.SETTLE_MS + 2 * app.FRAME_MS, d14=True)
        self.assertTrue(files[0].closed)
        self.assertIsNotNone(steps)
        self.assertEqual(({}, None), (pictures.PICS, pictures.loaded))

    def test_switch_and_build_during_a_build_close_its_steps(self):
        for move in ("switch", "build"):
            with self.subTest(move):
                BUILT.clear()
                box = self.box(Stepped(GAMES, 10 * app.BUILD_CHUNKS))
                box.frame(0, d14=True)
                box.frame(app.SETTLE_MS)
                box.frame(app.SETTLE_MS + app.FRAME_MS)
                steps = box.app.steps
                with contextlib.redirect_stdout(box.said):
                    getattr(box.app, move)()
                game = box.app.game
                self.assertEqual((1, None), (steps.closed, box.app.steps))
                for k in range(2, 20):  # the stopped build never ends and replaces the game
                    self.assertIs(game, box.frame(app.SETTLE_MS + k * app.FRAME_MS))

    def test_each_settle_counts_its_own_refusals(self):
        X, Y = flaky("x"), flaky("y")
        box = self.box((X, Y))
        Y.fails.append(ValueError)  # y always fails, x never: each build refuses y once and builds x
        for k in range(3):
            box.frame(box.ms + app.FRAME_MS, d14=True)
            box.frame(box.ms + app.SETTLE_MS)
            self.assertEqual("x", box.run_build().name)
        self.assertEqual(3, box.said.getvalue().count("game y refused"))

    def test_a_build_s_frames_keep_no_slowest(self):
        box = self.box(Stepped(GAMES, 10 * app.BUILD_CHUNKS, pause=0.001))
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        for k in (1, 2, 3):
            box.frame(app.SETTLE_MS + k * app.FRAME_MS)
        self.assertEqual([0] * 5, box.app.slow)

    def test_boot_during_a_build_does_not_reach_the_game(self):
        box = self.box(Stepped(GAMES, 3 * app.BUILD_CHUNKS))
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        game = box.app.game
        while isinstance(game, app.NameCard):
            game = box.frame(box.ms + app.FRAME_MS, boot=True)
        self.assertEqual([], game.presses)
        box.frame(box.ms + app.FRAME_MS)
        self.assertEqual([False], game.presses)

    def test_no_timed_collect_during_a_build(self):
        box = self.box(Stepped(GAMES, 10 * app.BUILD_CHUNKS), gc_floor=1)
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        with mock.patch.object(box.app, "collect") as collect:
            self.assertEqual("b", box.run_build().name)
        collect.assert_not_called()

    def test_the_switch_line_counts_the_build_s_frames_worst_and_longest(self):
        box = self.box(Stepped(GAMES, 3 * app.BUILD_CHUNKS, pause=0.003))
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        box.run_build()
        line = box.lines("switch")[-1]
        found = re.match(r"^switch b (\d+) ms, load 0 ms, import 0 ms, frames (\d+), worst (\d+) ms, longest (\d+) ms$",
                         line)
        self.assertIsNotNone(found, line)
        ms, frames, worst, longest = (int(x) for x in found.groups())
        self.assertEqual(4 * app.FRAME_MS, ms)  # from the settle to the game, on the box's clock
        self.assertEqual(3, frames)  # the card's frames after the settle; the fourth is the game's
        self.assertLessEqual(3 * app.BUILD_CHUNKS, worst)  # the steps of a frame, each 3 ms
        self.assertLessEqual(3 * app.BUILD_CHUNKS, longest)

    def test_a_game_refused_during_a_build_puts_the_next_name_on_the_card_and_builds_it(self):
        Broken = flaky("broken")
        box = self.box((GAMES[0], Broken, GAMES[1]))
        Broken.fails = [ValueError]
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        card = box.frame(app.SETTLE_MS + app.FRAME_MS)
        self.assertIsInstance(card, app.NameCard)
        self.assertEqual(("b", 3, 3, app.NameCard.LOADING, None),
                         (card.name, card.n, card.count, card.caption, card.progress))
        self.assertEqual(["game broken refused: ValueError('broken')"],
                         [line for line in box.said.getvalue().splitlines() if "refused" in line])
        self.assertEqual("b", box.run_build().name)
        self.assertEqual(["a", "b"], BUILT)

    def test_when_every_game_fails_during_a_build_the_last_error_is_raised(self):
        X, Y = flaky("x"), flaky("y")
        box = self.box((X, Y))
        X.fails.append(ValueError)  # after start() built x: from now on both fail
        Y.fails.append(ValueError)
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        box.frame(app.SETTLE_MS + app.FRAME_MS)  # y is refused, and x is on the card
        with self.assertRaisesRegex(ValueError, "^x$"):
            box.frame(app.SETTLE_MS + 2 * app.FRAME_MS)
        self.assertEqual(["game y refused: ValueError('y')", "game x refused: ValueError('x')"],
                         [line for line in box.said.getvalue().splitlines() if "refused" in line])

    def test_no_fps_line_names_a_card_during_a_build(self):
        box = self.box(Stepped(GAMES, app.BUILD_CHUNKS * (2 * app.FPS_EVERY_MS // app.FRAME_MS)))
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS)
        self.assertEqual("b", box.run_build(limit=10 ** 4).name)
        self.assertLess(2 * app.FPS_EVERY_MS, box.ms)
        self.assertEqual([], box.lines("fps"))


class CardTest(unittest.TestCase):
    def test_it_stays_in_title_loads_nothing_and_has_no_cues(self):
        with mock.patch.object(pictures, "load") as load:
            card = app.NameCard("snake", 3, 5)
            card.step(0, True, True)
            card.step(5000, True, False)
        load.assert_not_called()
        self.assertEqual((gfx.TITLE, {}), (card.state, card.cues))

    def test_it_draws_the_name_its_place_and_boot_plays(self):
        cv = gfx.Canvas()
        with mock.patch.object(cv, "big", wraps=cv.big) as big:
            app.NameCard("snake", 3, 5).draw_title(cv)
        self.assertEqual(["snake", "3 / 5"], [c.args[0] for c in big.call_args_list])
        self.assertIn("BOOT loads", [op[5] for op in cv.ops if op[4] == 3])


    def ops(self, caption=app.NameCard.WAITING, progress=None):
        card = app.NameCard("snake", 3, 5)
        card.caption, card.progress = caption, progress
        cv = gfx.Canvas()
        card.draw_title(cv)
        return cv.ops

    def bar(self, ops):
        """The bar's outline and its fill: the box op, and the fills inside it."""
        boxes = [op for op in ops if op[4] == 1]
        if not boxes:
            return None, []
        x0, y0, x1, y1 = boxes[0][:4]
        return boxes[0], [op for op in ops if op[4] == 0 and x0 < op[0] and op[2] < x1 and y0 < op[1] and op[3] < y1]

    def test_loading_says_so_with_no_bar(self):
        ops = self.ops(app.NameCard.LOADING)
        self.assertIn("loading", [op[5] for op in ops if op[4] == 3])
        self.assertEqual((None, []), self.bar(ops))

    def test_a_progress_is_a_bar_under_the_place_that_grows_and_says_no_words(self):
        place = gfx.HEIGHT // 2 + 6 + 2 * 8  # where "3 / 5" ends: drawn big at scale 2 from the middle's y + 6
        widths = []
        for progress in (0.0, 0.25, 0.75, 1.0):
            ops = self.ops(app.NameCard.LOADING, progress)
            outline, fills = self.bar(ops)
            self.assertEqual([], [op for op in ops if op[4] == 3])
            self.assertLess(place, outline[1])
            widths.append(sum(op[2] - op[0] for op in fills))
        inside = outline[2] - outline[0] - 2
        self.assertEqual([0, inside // 4, inside * 3 // 4, inside], widths)

    def test_only_the_bar_changes_between_two_progresses(self):
        a, b = self.ops(progress=0.25), self.ops(progress=0.5)
        changed = [op for op in a if op not in b] + [op for op in b if op not in a]
        self.assertTrue(self.bar(a)[1] and self.bar(b)[1])
        self.assertEqual(self.bar(a)[1] + self.bar(b)[1], changed)


class NothingImportedTest(unittest.TestCase):
    def test_a_pick_imports_nothing_and_a_missing_module_is_refused_when_it_settles(self):
        ghost = {"ghost": ("ghost", "no_such_module_p818", "Ghost", ())}
        with mock.patch.dict(catalog.ROWS, ghost):
            box = Box(app.Lineup(("cave", "ghost")))
            self.addCleanup(box.close)
            self.assertEqual("ghost", box.frame(0, d14=True).name)  # the card: no import yet
            self.assertNotIn("refused", box.said.getvalue())
            box.frame(app.SETTLE_MS)
            game = box.run_build()
            self.assertNotIsInstance(game, app.NameCard)
            self.assertEqual("cave", game.name)
        self.assertIn("game ghost refused", box.said.getvalue())


class SoundTest(unittest.TestCase):
    def test_a_pick_stops_the_games_cues_and_the_music_plays_on(self):
        mixer = sound.Mixer(2)
        box = Box((Loud, Loud), cues=cues.SoundCues(mixer, MusicBank()))
        self.addCleanup(box.close)
        loud, voice = box.app.game, box.app.cues.music_voice
        loud.emit("die")
        rendered(mixer, 1)
        box.frame(0, d14=True)
        self.assertEqual({}, box.app.cues.cues)
        loud.emit("jump")  # the old game's listeners are gone
        self.assertIs(box.app.cues.music_voice, voice)
        self.assertEqual(rendered(mixer), [6, 5, 6, 5])  # only the music


class KnobTest(unittest.TestCase):
    def test_the_volume_pane_shows_over_a_card(self):
        box = Box(knob=volume.VolumeKnob(Encoder(0, 1), volume.MasterVolume(8)))
        self.addCleanup(box.close)
        box.frame(0, d14=True)
        card = box.frame(10)
        self.assertIsInstance(card, app.NameCard)
        self.assertEqual([[False], [True]], box.app.out.seen)


if __name__ == "__main__":
    unittest.main()
