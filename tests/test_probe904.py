"""probe904_figures.py (P904 step 2c): how many 96 px figures the game box moves at once. On the Mac, with no board:
the figure's steps and turns on stand-in gait rows, the count at each wall time, the count clock's lines, the pack
line's pool or heap, board() on stand-in board modules, the Mac part's commands with a recording runner (as
tests/test_box.py's FakeRunner) and a stand-in for art/figures.py, mac() and its dry run. And, only when the CMU files
are downloaded, the probe's game on the stand-in display (tests/drawing_tft.py) with the set's written pack: skipped
without them, and a skip is not a pass. Run from the repository root: python3 -B -m unittest tests.test_probe904."""

import argparse
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
sys.path.insert(0, os.path.join(REPO, "art"))  # art/figures.py and its modules
sys.path.insert(0, os.path.join(REPO, "tools"))  # box
sys.path.append(REPO)  # the probe, last: the root's engine/ is the submodule, games/engine the package

from drawing_tft import DrawingTft  # noqa: E402  first: it puts games/ and the stubs on the path

import app  # noqa: E402
import box  # noqa: E402
import detailed  # noqa: E402
import figures  # noqa: E402
import gfx  # noqa: E402
import lcd  # noqa: E402
import mocap  # noqa: E402
import pictures  # noqa: E402
import probe904_figures as probe  # noqa: E402
import rescue  # noqa: E402
from engine.actions import ActionMap  # noqa: E402  no button pressed

# stand-in gait rows (name, pivot x, stride, speed) and picture sizes: none round, none alike, one pivot left of its
# picture's middle and one right of it, so a mirrored pivot or a margin of the wrong side shows
ROW_A, SIZE_A = ("fireman", 47, 83, 141.7), (113, 109)
ROW_B, SIZE_B = ("paramedic", 71, 97, 167.3), (104, 98)
STAND_IN_ROWS = (ROW_A, ROW_B, ("footballer", 53, 89, 151.9))
SAID = "probe p904 counts 0,1,2,4,8,16 seconds 30\npack pool 2463997\ncount 0 starts\nfps figures 23\n" \
       "count 16 starts\nfps figures 7\ndone\n"  # a board run's output, as the board prints it
LIMIT = 6 * 30 + 120  # the board run's time limit: the counts times SECONDS, plus 120 s
STEPS = (37, 23, 41, 60, 17)  # ms: 142 px a second times none of them is a whole px


class FigureTest(unittest.TestCase):
    """One moving figure on stand-in gait rows."""

    def test_the_screens_width_and_the_row_of_the_soles_are_the_games(self):
        self.assertEqual((gfx.WIDTH, rescue.FEET), (probe.WIDTH, probe.FEET))

    def test_it_moves_at_its_whole_speed_with_a_carry_in_thousandths(self):
        # 141.7 px a second is 142; 178 ms of it is 25.276 px. Facing right the floors give 25 px and keep 276
        # thousandths; facing left each step floors toward the left: 26 px, and 724 thousandths kept
        for facing, moved, ran, rest in ((1, 25, 25, 276), (-1, -26, 26, 724)):
            with self.subTest(facing=facing):
                figure = probe.Figure(ROW_A, SIZE_A, 0.5, facing)
                self.assertEqual(142, figure.speed)
                x = figure.x
                for ms in STEPS:
                    figure.step(ms)
                self.assertEqual((x + moved, ran, rest), (figure.x, figure.ran, figure.rest))

    def test_many_steps_leave_whole_numbers_and_a_pose_is_one_name_made_once(self):
        figure = probe.Figure(ROW_B, SIZE_B, 0.3, -1)
        self.assertIs(int, type(figure.x))
        names = {}
        for k in range(2000):
            figure.step(STEPS[k % len(STEPS)])
            self.assertEqual((int, int, int), (type(figure.x), type(figure.ran), type(figure.rest)), k)
            name = figure.picture()
            self.assertIs(names.setdefault((name, figure.facing), name), name)  # the same pose: the same object
            self.assertIs(name, figure.picture())
        self.assertEqual(2 * probe.POSES, len(names))

    def test_it_starts_its_share_of_the_way_between_its_bounds_on_a_whole_column(self):
        figure = probe.Figure(ROW_B, SIZE_B, 0.25, -1)
        self.assertEqual((71, 319 - 71), (figure.lo, figure.hi))  # the pivot, right of the middle, is the margin
        self.assertEqual(int(71 + (248 - 71) * 0.25), figure.x)
        self.assertEqual((65, 319 - 65), (probe.Figure(ROW_A, SIZE_A, 0, 1).lo, probe.Figure(ROW_A, SIZE_A, 0, 1).hi))

    def test_it_turns_at_each_edge_and_its_picture_stays_whole_on_the_screen(self):
        for row, (w, h) in ((ROW_A, SIZE_A), (ROW_B, SIZE_B)):
            for facing in (1, -1):
                with self.subTest(character=row[0], facing=facing):
                    figure = probe.Figure(row, (w, h), 0.4, facing)
                    turns, xs = [], []
                    for k in range(3000):
                        before, x = figure.facing, figure.x
                        figure.step(STEPS[k % len(STEPS)])
                        if figure.facing != before:
                            turns.append(figure.facing)
                            self.assertEqual(0, figure.rest)  # a turn drops the carry, as rescue.py's run
                        else:  # the facing follows the direction
                            self.assertEqual(figure.facing, 1 if figure.x > x else -1)
                        left, top = figure.corner()
                        self.assertTrue(0 <= left <= probe.WIDTH - w, (k, left))
                        xs.append(figure.x)
                    self.assertGreater(turns.count(1), 5)
                    self.assertGreater(turns.count(-1), 5)
                    self.assertEqual((figure.lo, figure.hi), (min(xs), max(xs)))

    def test_its_pose_follows_the_px_it_ran_and_its_side_its_facing(self):
        figure = probe.Figure(ROW_A, SIZE_A, 0.5, 1)  # stride 83: 12 poses do not divide it
        for ran, pose in ((0, 0), (6, 0), (7, 1), (41, 5), (83, 0), (90, 1), (160, 11)):
            for facing, side in ((1, "r"), (-1, "l")):
                with self.subTest(ran=ran, facing=facing):
                    figure.ran, figure.facing = ran, facing
                    self.assertEqual("figures_fireman_%s%d" % (side, pose), figure.picture())

    def test_its_corner_puts_its_pivot_on_its_column_and_its_soles_on_row_214(self):
        figure = probe.Figure(ROW_A, SIZE_A, 0.5, 1)
        figure.x = 150
        self.assertEqual((150 - 47, 214 - 109 + 1), figure.corner())
        figure.facing = -1  # the left picture is the right one mirrored: its pivot is w - 1 - 47 from its left
        self.assertEqual((150 - 65, 214 - 109 + 1), figure.corner())


class CountTest(unittest.TestCase):
    def test_the_counts_and_their_seconds(self):
        self.assertEqual(((0, 1, 2, 4, 8, 16), 30), (probe.COUNTS, probe.SECONDS))

    def test_the_source_holds_no_gait_rows_the_mac_part_fills_them_in_a_copy(self):
        self.assertIsNone(probe.GAITS)

    def test_each_counts_first_and_last_millisecond_and_none_after_the_last(self):
        for k, count in enumerate((0, 1, 2, 4, 8, 16)):
            with self.subTest(count=count):
                self.assertEqual(count, probe.count_at(k * 30000))
                self.assertEqual(count, probe.count_at(k * 30000 + 29999))
        self.assertIsNone(probe.count_at(180000))
        self.assertIsNone(probe.count_at(9876543))


class CountsArgTest(unittest.TestCase):
    """--counts' value (counts_arg): whole numbers of 0 or more, at least one, no repeat, in the order given."""

    def test_the_counts_come_as_a_tuple_in_the_order_given(self):
        for text, counts in (("16,20,24,28,32,36,40,48,64", (16, 20, 24, 28, 32, 36, 40, 48, 64)),
                             ("24,0,7", (24, 0, 7)), ("2", (2,)), ("3,08", (3, 8))):
            with self.subTest(text=text):
                self.assertEqual(counts, probe.counts_arg(text))

    def test_anything_but_whole_numbers_of_0_or_more_by_commas_is_refused(self):
        for text in ("", ",", "4,", ",4", "4,,8", "-1,4", "+4", "4.0", " 4", "4, 8", "four", "0x10", "4;8", "٣"):
            with self.subTest(text=text), self.assertRaisesRegex(argparse.ArgumentTypeError, "whole numbers"):
                probe.counts_arg(text)

    def test_a_count_that_repeats_is_refused(self):
        for text in ("4,8,4", "0,0,2", "3,03"):
            with self.subTest(text=text), self.assertRaisesRegex(argparse.ArgumentTypeError, "repeat"):
                probe.counts_arg(text)

    def test_a_largest_count_under_2_or_a_multiple_of_5_is_refused(self):
        # the start rule: figure i's share is i * 5 % n / (n - 1), n the largest count
        for text in ("0", "1", "1,0", "5", "0,10", "64,3,80", "15,7"):
            with self.subTest(text=text), self.assertRaisesRegex(argparse.ArgumentTypeError, "largest count"):
                probe.counts_arg(text)
        for text in ("1,2", "0,4", "64,3,40"):  # a smaller count may be any
            with self.subTest(text=text):
                self.assertEqual(tuple(int(n) for n in text.split(",")), probe.counts_arg(text))


class Clock:
    """ticks_ms on a list of frame times."""

    def __init__(self, times):
        self.times = list(times)

    def ticks_ms(self):
        return self.times.pop(0)


class CountClockTest(unittest.TestCase):
    """The count clock, on a stand-in App and a stand-in clock."""

    def test_it_prints_the_pack_line_once_then_each_count_and_starts_an_interval_at_each(self):
        start = 1234
        times = [start + 41 * k for k in range(4500)]
        clock = Clock(times)
        game = types.SimpleNamespace(count=None)
        app = types.SimpleNamespace(game=game, intervals=[])
        app.new_interval = lambda: app.intervals.append(game.count)
        counts = probe.CountClock(clock.ticks_ms, lambda a, b: a - b, lambda: "pack pool 2463997")
        frames = 0
        with contextlib.redirect_stdout(io.StringIO()) as said, self.assertRaises(probe.Done):
            while True:
                counts.after_frame(app)
                frames += 1
        self.assertEqual(["pack pool 2463997"] + ["count %d starts" % n for n in (0, 1, 2, 4, 8, 16)],
                         said.getvalue().splitlines())
        self.assertEqual([0, 1, 2, 4, 8, 16], app.intervals)
        self.assertEqual(16, game.count)
        self.assertEqual(180000 // 41 + 1, frames)  # the frame at 180,031 ms raises

    def test_a_count_starts_on_the_first_frame_past_its_seconds(self):
        clock = Clock([5000, 5000 + 29999, 5000 + 30000, 5000 + 30001])
        game = types.SimpleNamespace(count=None)
        app = types.SimpleNamespace(game=game, new_interval=lambda: None)
        counts = probe.CountClock(clock.ticks_ms, lambda a, b: a - b, lambda: "pack heap 7")
        seen = []
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(4):
                counts.after_frame(app)
                seen.append(game.count)
        self.assertEqual([0, 0, 1, 1], seen)


class Pool:
    """s3lcd's pool: made at the first call's size, a larger size later raises ValueError (s3lcd.c's pool)."""

    def __init__(self, size):
        self.size = size

    def pool(self, n):
        if n > self.size:
            raise ValueError("the pool is smaller: reset the board")
        return bytearray(0)


class PackLineTest(unittest.TestCase):
    def test_the_pack_is_in_the_pool_when_the_pool_holds_its_size_else_in_the_heap(self):
        self.assertEqual("pack pool 2463997", probe.pack_line(Pool(2463997).pool, 2463997))
        self.assertEqual("pack pool 2463997", probe.pack_line(Pool(2470001).pool, 2463997))
        self.assertEqual("pack heap 2463997", probe.pack_line(Pool(739213).pool, 2463997))


# the board's modules for board(): PSRAM's regions are over 1 MB, the internal heap's under it, every value different
HEAP_DATA, HEAP_EXEC = 4, 1
REGIONS = [(8388603, 6747503, 6553597, 6000001), (327673, 188419, 160001, 150007),
           (4194301, 2000003, 1900007, 1800011), (31991, 20011, 19997, 18013)]
PACKS = {"other": ("packs/other.pak", 739213, "aa"), "figures": ("packs/figures.pak", 2463997, "bb"),
         "third": ("packs/third.pak", 1507149, "cc")}  # the largest neither first nor last


CAP_41 = 180000 // 41 + 100  # frames: a little past the 4,392 that the six counts take at 41 ms a frame


def board_modules(fail_at=None):
    """Stand-ins for the modules board() imports, as a dict for sys.modules, and the list of the pool's sizes asked.
    The App's frame prints `frame N` and moves the clock 41 ms; with fail_at, that frame raises a RuntimeError. run()
    builds the one game and calls frame() until it raises, and raises an AssertionError past CAP_41 frames, so a Done
    that never comes fails the test at once."""
    clock, asked, frees = [7777], [], [6603371, 6402313]
    time_ = types.SimpleNamespace(ticks_ms=lambda: clock[0], ticks_diff=lambda a, b: a - b)

    class App:
        def __init__(self, game):
            self.game, self.frames = game, 0

        def frame(self):
            self.frames += 1
            clock[0] += 41
            print("frame %d" % self.frames)
            if self.frames == fail_at:
                raise RuntimeError("figures_fireman_r3 did not draw: no art")

        def new_interval(self):
            print("interval")

    def run(games, knob, speaker):
        print("run %s %s %d" % (knob, speaker, len(games)))
        app = App(games[0]())
        for _ in range(CAP_41):
            app.frame()
        raise AssertionError("no Done after %d frames" % CAP_41)

    art = {"figures_%s_r0" % row[0]: size + ("figures", 16) for row, size in
           zip(STAND_IN_ROWS, (SIZE_A, SIZE_B, (98, 107)))}
    index = types.SimpleNamespace(ART=art, PACKS=PACKS)
    pictures_ = types.SimpleNamespace(art_index=index, load=lambda *art: True, draw=lambda *a: True)
    esp32 = types.SimpleNamespace(HEAP_DATA=HEAP_DATA, HEAP_EXEC=HEAP_EXEC,
                                  idf_heap_info=lambda kind: REGIONS if kind == HEAP_DATA else [(9, 9, 9, 9)])
    gc_ = types.SimpleNamespace(collect=lambda: None, mem_free=lambda: frees.pop(0),
                                mem_alloc=lambda: 279361 - len(frees))
    modules = {"app": types.SimpleNamespace(App=App, run=run), "main": types.SimpleNamespace(
        compose=lambda: ("knob", "speaker")), "pictures": pictures_, "s3lcd": types.SimpleNamespace(
        pool=lambda n: asked.append(n) or bytearray(1)), "esp32": esp32, "gc": gc_, "time": time_, "gfx": gfx}
    return modules, asked


class BoardTest(unittest.TestCase):
    """board() on stand-in board modules: the App, main, pictures, s3lcd, esp32, gc and time."""

    def board(self, fail_at=None):
        """board() run: what it printed, the pool's sizes asked, and the error it left with or None."""
        modules, asked = board_modules(fail_at)
        error = None
        with mock.patch.dict(sys.modules, modules), mock.patch.object(probe, "GAITS", STAND_IN_ROWS), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            try:
                probe.board()
            except Exception as e:  # noqa: BLE001  the test reads which one
                error = e
        return said.getvalue().splitlines(), asked, error

    def test_it_runs_the_game_with_mains_parts_and_ends_on_done_after_the_last_count(self):
        lines, asked, error = self.board()
        self.assertIsNone(error)
        psram = "psram free %d largest %d" % (6747503 + 2000003, 6553597)
        self.assertEqual(["probe p904 counts 0,1,2,4,8,16 seconds 30", psram, "gc free 6603371 alloc 279360",
                          "run knob speaker 1", "frame 1", "pack pool 2463997", "count 0 starts", "interval",
                          "frame 2"], lines[:9])
        self.assertEqual(["frame %d" % (180000 // 41 + 2), psram, "gc free 6402313 alloc 279361", "done"], lines[-4:])
        self.assertEqual([2463997], asked)  # the largest pack's size, asked once
        starts = [line for line in lines if line.startswith("count ")]
        self.assertEqual(["count %d starts" % n for n in (0, 1, 2, 4, 8, 16)], starts)

    def test_the_apps_own_frame_runs_before_the_count_clock(self):
        lines, _, _ = self.board()
        for n in (0, 1, 16):
            with self.subTest(count=n):
                at = lines.index("count %d starts" % n)
                self.assertTrue(lines[at - 1].startswith("frame ") or lines[at - 1].startswith("pack "), lines[at - 1])
        self.assertLess(lines.index("frame 1"), lines.index("pack pool 2463997"))

    def test_any_other_error_of_a_frame_leaves_board_as_itself_with_no_done(self):
        lines, asked, error = self.board(fail_at=3)
        self.assertIsInstance(error, RuntimeError)
        self.assertIn("figures_fireman_r3", str(error))
        self.assertEqual("frame 3", lines[-1])
        self.assertNotIn("done", lines)
        self.assertEqual(1, len([line for line in lines if line.startswith("psram ")]))


WRITTEN = {}  # the set's pack and index, written once for every test of the module that paints


def tearDownModule():
    if "folder" in WRITTEN:
        WRITTEN["folder"].cleanup()


@contextlib.contextmanager
def figures_art():
    """pictures reads the set through its own index, as the board does with the shadow index: the set written once
    for the module (figures.write into a temporary folder)."""
    if "folder" not in WRITTEN:
        WRITTEN["folder"] = tempfile.TemporaryDirectory()
        WRITTEN["paths"] = figures.write(WRITTEN["folder"].name)
    folder, (pack, path) = WRITTEN["folder"].name, WRITTEN["paths"]
    index = types.ModuleType("art_index")
    with open(path) as f:
        exec(f.read(), index.__dict__)
    old_index, old_root = pictures.art_index, pictures.ROOT
    pictures.art_index, pictures.ROOT = index, os.path.join(folder, "")
    pictures.free()
    try:
        yield index
    finally:
        pictures.free()
        pictures.art_index, pictures.ROOT = old_index, old_root


class Recorder:
    """A canvas that keeps each picture call: (buffer, x, y, w, h)."""

    pictures = True

    def __init__(self):
        self.calls = []

    def picture(self, buf, x, y, w, h, key, alpha=255):
        self.calls.append((buf, x, y, w, h))


class GameFromCaptureTest(unittest.TestCase):
    """The probe's game with the set painted from the CMU files and written to a temporary folder: skipped without the
    files, and a skip is not a pass."""

    @classmethod
    def setUpClass(cls):
        if mocap.Capture().missing():
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.art = figures_art()
        cls.index = cls.art.__enter__()
        cls.rows = figures.gaits(None)
        cls.Probe = probe.game_class(cls.rows)

    @classmethod
    def tearDownClass(cls):
        cls.art.__exit__(None, None, None)

    def setUp(self):
        pictures.load("figures")  # each test's game finds the set loaded, as after the box's build
        self.game = self.Probe()
        self.game.step(1000, False, False)  # out of the title, into play: no figure moves in this step

    def frame(self):
        """The game drawn on the stand-in display the board's way (lcd.TftOut), as the game's view."""
        tft = DrawingTft()
        lcd.TftOut(tft).draw(self.game, [0, 0, 0, 0])
        return tft.image()

    def test_the_game_is_figures_on_its_set_and_starts_in_play_over_the_covering_street(self):
        game = self.Probe()
        self.assertEqual(("figures", ("figures", None), 0), (game.name, self.Probe.ART, self.Probe.TITLE_MS))
        self.assertIs(True, game.covers)
        self.assertEqual(gfx.TITLE, game.state)
        game.step(4321, False, False)
        self.assertEqual(gfx.PLAY, game.state)

    def test_its_sixteen_figures_are_the_cast_in_turn_each_with_its_gait_and_size(self):
        self.assertEqual(16, len(self.game.figures))
        for i, figure in enumerate(self.game.figures):
            with self.subTest(figure=i):
                name, pivot, stride, speed = self.rows[i % 8]
                self.assertEqual(detailed.CAST[i % 8][0].name, name)
                self.assertEqual((name, pivot, stride, round(speed)),
                                 (figure.name, figure.pivot, figure.stride, figure.speed))
                self.assertEqual(self.index.ART["figures_%s_r0" % name][:2], (figure.w, figure.h))

    def test_the_sixteen_start_places_differ_and_none_faces_the_edge_it_starts_at(self):
        places = [(figure.x, figure.facing) for figure in self.game.figures]
        self.assertEqual(16, len({x for x, _ in places}))
        for figure in self.game.figures:
            with self.subTest(figure=figure.name, x=figure.x):
                self.assertFalse(figure.x == figure.hi and figure.facing == 1)
                self.assertFalse(figure.x == figure.lo and figure.facing == -1)
        self.assertEqual([1, -1] * 8, [facing for _, facing in places])

    def test_each_drawn_figure_is_its_pose_whole_on_screen_with_its_soles_on_row_214(self):
        for count in (1, 2, 4, 16):
            self.game.count = count
            for k in range(5):
                with self.subTest(count=count, frame=k):
                    cv = Recorder()
                    self.game.paint(cv)
                    self.assertEqual(count, len(cv.calls))
                    for figure, (buf, x, y, w, h) in zip(self.game.figures, cv.calls):
                        self.assertIs(pictures.PICS[figure.picture()][2], buf)
                        self.assertEqual((figure.w, figure.h), (w, h))
                        self.assertEqual(214, y + h - 1)
                        self.assertTrue(0 <= x <= 320 - w, x)
                self.game.ms = 47
                self.game.play(False, False)

    def test_count_n_changes_the_frame_only_inside_the_first_n_figures_boxes(self):
        self.game.count = 0
        still = self.frame()
        for count in (1, 2, 4):
            with self.subTest(count=count):
                self.game.count = count
                cv = Recorder()
                self.game.paint(cv)
                boxes = [(x, y, x + w, y + h) for _, x, y, w, h in cv.calls]
                frame = self.frame()
                changed = [(x, y) for y in range(240) for x in range(320)
                           if frame.getpixel((x, y)) != still.getpixel((x, y))]
                self.assertTrue(changed)
                self.assertEqual([], [p for p in changed if not any(a <= p[0] < c and b <= p[1] < d
                                                                     for a, b, c, d in boxes)])
                for a, b, c, d in boxes:  # each figure shows
                    self.assertTrue(any(a <= x < c and b <= y < d for x, y in changed), (a, b))

    def test_play_moves_only_the_counted_figures(self):
        self.game.count = 2
        xs = [figure.x for figure in self.game.figures]
        self.game.ms = 43
        self.game.play(False, False)
        for i, figure in enumerate(self.game.figures):
            with self.subTest(figure=i):
                moved = figure.speed * 43 * figure.facing // 1000  # from no carry
                if i < 2:
                    self.assertEqual(min(max(xs[i] + moved, figure.lo), figure.hi), figure.x)
                else:
                    self.assertEqual(xs[i], figure.x)

    def test_a_picture_that_does_not_draw_raises(self):
        self.game.count = 1
        flat = types.SimpleNamespace(pictures=False)  # a canvas with no pictures: pictures.draw answers False
        with self.assertRaisesRegex(RuntimeError, "figures_night"):
            self.game.paint_static(flat)
        with self.assertRaisesRegex(RuntimeError, "figures_fireman_"):
            self.game.paint(flat)
        name = self.game.figures[0].picture()
        kept = pictures.PICS.pop(name)
        try:
            with self.assertRaisesRegex(RuntimeError, name):
                self.game.paint(Recorder())
        finally:
            pictures.PICS[name] = kept


FRAME_MS = app.FRAME_MS  # 40: the stand-in clock gives every frame exactly this
CAP_40 = 180000 // FRAME_MS + 100  # frames: a little past the 4,500 that the six counts take at 40 ms a frame
PSRAM = "psram free %d largest %d" % (6747503 + 2000003, 6553597)


class CPool:
    """s3lcd.pool by the C rules (s3lcd.c's pool): the first call makes the block at its size, a larger size later
    raises ValueError, a size it holds answers the same block."""

    def __init__(self):
        self.buf = None

    def pool(self, n):
        if self.buf is None:
            self.buf = bytearray(n)
        elif n > len(self.buf):
            raise ValueError("the pool is smaller: reset the board")
        return memoryview(self.buf)[:n]


@contextlib.contextmanager
def real_board(rows, missing=()):
    """board() on the real App (games/app.py, gfx, pictures, lcd.TftOut on DrawingTft) with only the hardware stood
    in: a clock whose frames are exactly FRAME_MS apart (app.run's sleep_ms moves it; past CAP_40 frames it raises an
    AssertionError), s3lcd's pool by the C rules, PSRAM's and the heap's numbers, no knob and no speaker (main), no
    buttons, no console, and pictures.draw answering whether the picture is loaded and not in missing, with no blit, so
    the 4,500 frames take seconds. The set is the module's written pack. App.frame, which board() wraps, is put back."""
    clock = {"ms": 1000, "us": 0, "frames": 0}

    def ticks_us():
        clock["us"] += 1
        return clock["ms"] * 1000 + clock["us"] % 1000

    def sleep_ms(ms):
        clock["frames"] += 1
        if clock["frames"] > CAP_40:
            raise AssertionError("no Done after %d frames" % CAP_40)
        clock["ms"] += ms

    frees = [6603371, 6402313]  # the probe's memory lines, at the start and at the end
    gc_ = types.SimpleNamespace(collect=lambda: None, mem_free=lambda: frees.pop(0), mem_alloc=lambda: 279361)
    app_gc = types.SimpleNamespace(collect=lambda: None, disable=lambda: None, mem_free=lambda: 7000003,
                                   mem_alloc=lambda: 279367)  # the App's own: its mem line and its heap lines
    poll = types.SimpleNamespace(register=lambda *a: None, poll=lambda ms: [])
    hardware = {"gc": gc_, "main": types.SimpleNamespace(compose=lambda: (None, None)),
                "s3lcd": types.SimpleNamespace(pool=CPool().pool),
                "esp32": types.SimpleNamespace(HEAP_DATA=HEAP_DATA, idf_heap_info=lambda kind: REGIONS),
                "select": types.SimpleNamespace(poll=lambda: poll, POLLIN=1)}

    def draw(cv, name, x, y, alpha=255):
        return name in pictures.PICS and name not in missing

    with figures_art(), mock.patch.dict(sys.modules, hardware), mock.patch.object(probe, "GAITS", rows), \
            mock.patch.object(app.App, "frame", app.App.frame), mock.patch.object(app, "gc", app_gc), \
            mock.patch.object(app, "open_tft", lambda hz: lcd.TftOut(DrawingTft())), \
            mock.patch.object(app.encoder, "take_pads", lambda a, b: None), \
            mock.patch.object(app, "open_action_map", lambda: ActionMap((), ())), \
            mock.patch.object(pictures, "draw", draw), \
            mock.patch.object(time, "ticks_ms", lambda: clock["ms"]), mock.patch.object(time, "ticks_us", ticks_us), \
            mock.patch.object(time, "ticks_diff", lambda a, b: a - b), \
            mock.patch.object(time, "ticks_add", lambda a, b: a + b, create=True), \
            mock.patch.object(time, "sleep_ms", sleep_ms, create=True):
        yield clock


class RealAppBoardTest(unittest.TestCase):
    """board() on games/app.py itself, with only the hardware stood in (real_board) and the set's pack written from
    the CMU files: skipped without them, and a skip is not a pass."""

    @classmethod
    def setUpClass(cls):
        if mocap.Capture().missing():
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.rows = figures.gaits(None)

    def board(self, missing=()):
        """board() on the real App: its lines, and the error it left with or None."""
        error = None
        with real_board(self.rows, missing), contextlib.redirect_stdout(io.StringIO()) as said:
            try:
                probe.board()
            except Exception as e:  # noqa: BLE001  the test reads which one
                error = e
        return said.getvalue().splitlines(), error

    def test_its_lines_come_in_order_and_each_counts_fps_lines_are_its_own(self):
        lines, error = self.board()
        self.assertIsNone(error)
        kinds = ("probe p904", "psram ", "gc free", "switch figures", "pack ", "count ", "done")
        said = [line.split(" ", 2)[0] + " " + line.split(" ", 2)[1] if line.startswith("switch ") else line
                for line in lines if line.startswith(kinds)]
        self.assertEqual(["probe p904 counts 0,1,2,4,8,16 seconds 30", PSRAM, "gc free 6603371 alloc 279361",
                          "switch figures", "pack pool 2464000"] + ["count %d starts" % n for n in (0, 1, 2, 4, 8, 16)]
                         + [PSRAM, "gc free 6402313 alloc 279361", "done"], said)
        starts = [lines.index("count %d starts" % n) for n in (0, 1, 2, 4, 8, 16)] + [len(lines) - 3]
        self.assertEqual([], [line for line in lines[:starts[0]] if line.startswith("fps ")])
        for n, a, b in zip((0, 1, 2, 4, 8, 16), starts, starts[1:]):
            with self.subTest(count=n):  # 30 s of 40 ms frames: 6 lines of 125 frames in 5 s, each 25 fps
                self.assertEqual(["fps figures 25"] * 6, [line for line in lines[a:b] if line.startswith("fps ")])

    def test_the_copy_with_other_counts_says_them_and_gives_each_its_seconds(self):
        # the copy for the board, filled with counts in no order and a largest count over 16 (3 counts: 2,250 frames,
        # under CAP_40); its own board() on the real App
        counts = (24, 0, 7)
        with open(os.path.join(REPO, "probe904_figures.py")) as f:
            copy = probe.filled(f.read(), self.rows, counts)
        module, error = {"__name__": "copy"}, None
        with real_board(self.rows), contextlib.redirect_stdout(io.StringIO()) as said:
            exec(compile(copy, "copy", "exec"), module)
            try:
                module["board"]()
            except Exception as e:  # noqa: BLE001  the test reads which one
                error = e
        lines = said.getvalue().splitlines()
        self.assertIsNone(error)
        self.assertEqual("probe p904 counts 24,0,7 seconds 30", lines[0])
        self.assertEqual(["count %d starts" % n for n in counts], [line for line in lines if line.startswith("count ")])
        starts = [lines.index("count %d starts" % n) for n in counts] + [len(lines) - 3]
        for n, a, b in zip(counts, starts, starts[1:]):
            with self.subTest(count=n):
                self.assertEqual(["fps figures 25"] * 6, [line for line in lines[a:b] if line.startswith("fps ")])
        self.assertEqual("done", lines[-1])

    def test_a_draw_that_answers_false_leaves_board_as_the_error_with_no_done(self):
        missing = {"figures_paramedic_%s%d" % (side, i) for side in "rl" for i in range(12)}
        lines, error = self.board(missing)
        self.assertIsInstance(error, RuntimeError)
        self.assertRegex(str(error), r"^figures_paramedic_[rl]\d+ did not draw: no art$")
        self.assertEqual("count 2 starts", [line for line in lines if line.startswith("count ")][-1])
        self.assertNotIn("done", lines)


ROOT = ("boot.py", "main.py", "app.mpy", "art_index.mpy", "packs/")


class Board:
    """A recording runner for the Mac part: it keeps each command and its time limit, answers `ls :` and `ls :packs`
    with what the board holds (each copy lands, each rm removes; `ls :packs` fails on a board with no packs folder),
    reads the probe's copy at its board run and answers said. fails: commands (joined by spaces) that raise a
    CalledProcessError, once each time they are named. broken: commands that raise it every time once a copy began.
    copy_fails: a copy's destination and how it fails: "before" lands nothing, "halfway" leaves its file. run_error:
    what the board run raises instead of answering."""

    dry_run = False

    def __init__(self, root=ROOT, packs=("rescue.pak",), said=SAID, fails=(), broken=(), copy_fails=None,
                 run_error=None):
        self.root, self.packs, self.said = set(root), set(packs), said
        self.fails, self.broken, self.copy_fails, self.run_error = list(fails), set(broken), copy_fails or {}, run_error
        self.commands, self.limits, self.copy, self.copied = [], [], None, False

    def listing(self, names):
        return "".join("%12d %s\n" % (1000 + len(n), n) for n in sorted(names))

    def fail(self, args, why):
        raise subprocess.CalledProcessError(1, ["mpremote"] + args, output="", stderr=why)

    def run(self, args, timeout=None):
        self.commands.append(args)
        self.limits.append(timeout)
        line = " ".join(args)
        if line in self.fails:
            self.fails.remove(line)
            self.fail(args, "could not enter raw repl")
        if self.copied and line in self.broken:
            self.fail(args, "could not enter raw repl")
        if args[0] == "cp":
            self.copied = True
            how = self.copy_fails.get(args[-1])
            if args[-1].startswith(":packs/") and "packs/" not in self.root:
                self.fail(args, "OSError: [Errno 2] ENOENT")
            if how != "before":
                (self.packs if args[-1].startswith(":packs/") else self.root).add(args[-1].split("/")[-1].lstrip(":"))
            if how:
                self.fail(args, "no space left")
        if args[0] == "rm":
            for path in args[1:]:
                (self.packs if path.startswith(":packs/") else self.root).discard(path.split("/")[-1].lstrip(":"))
        if args == ["ls", ":"]:
            return "ls :\n" + self.listing(self.root)
        if args == ["ls", ":packs"]:
            if "packs/" not in self.root:
                self.fail(args, "OSError: [Errno 2] ENOENT")
            return "ls :packs\n" + self.listing(self.packs)
        if args[0] == "run":
            with open(args[1]) as f:
                self.copy = f.read()
            if self.run_error:
                raise self.run_error
            return self.said
        return ""


class StandInArt:
    """art/figures.py stood in: write puts small files where figures.write puts the pack and the index, and gaits
    answers STAND_IN_ROWS. It keeps the captures it was given."""

    def __init__(self):
        self.captures = []

    def write(self, folder, capture):
        self.captures.append(capture)
        os.makedirs(os.path.join(folder, "packs"))
        pack, index = os.path.join(folder, "packs", "figures.pak"), os.path.join(folder, "art_index.py")
        with open(pack, "wb") as f:
            f.write(b"PIXPACK1" + bytes(range(37)))
        with open(index, "w") as f:
            f.write("PACKS = {}\n")
        return pack, index

    def gaits(self, capture):
        self.captures.append(capture)
        return STAND_IN_ROWS


def cleanup():
    return [["ls", ":"], ["ls", ":packs"], ["rm", ":art_index.py", ":packs/figures.pak"], ["reset"]]


RECOVERY = ("mpremote rm :art_index.py :packs/figures.pak", "mpremote reset")


class MacTest(unittest.TestCase):
    """The Mac part with a recording runner and a stand-in for art/figures.py: no board, no paint."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.log = os.path.join(self.folder.name, "run-p904-2c.log")
        self.art, self.sleeps = StandInArt(), []
        self.capture = object()

    def bench(self, board, **counts):
        return probe.Bench(board, self.art, self.log, sleep=self.sleeps.append, **counts)

    def run_bench(self, board, **counts):
        """check() then run(), as mac() calls them: what it printed, and the SystemExit it raised or None."""
        with contextlib.redirect_stdout(io.StringIO()) as said:
            try:
                bench = self.bench(board, **counts)
                bench.check()
                bench.run(self.capture)
            except SystemExit as e:
                return said.getvalue(), e
        return said.getvalue(), None

    def logged(self, path=None):
        with open(path or self.log) as f:
            return f.read()

    def test_a_board_run_copies_the_pack_then_the_index_waits_runs_once_and_cleans_up(self):
        board = Board()
        said, refused = self.run_bench(board)
        self.assertIsNone(refused)
        copy = board.commands[5][1]
        self.assertEqual([["ls", ":"], ["cp", board.commands[1][1], ":packs/figures.pak"],
                          ["cp", board.commands[2][1], ":art_index.py"], ["reset"], ["exec", "pass"], ["run", copy]]
                         + cleanup(), board.commands)
        self.assertTrue(board.commands[1][1].endswith(os.path.join("packs", "figures.pak")))
        self.assertTrue(board.commands[2][1].endswith("art_index.py"))
        self.assertEqual(set(ROOT), board.root)
        self.assertEqual({"rescue.pak"}, board.packs)
        self.assertEqual([self.capture, self.capture], self.art.captures)
        self.assertEqual(SAID, self.logged())
        self.assertEqual(SAID + "the log is %s\n" % self.log, said)
        self.assertFalse(os.path.exists(copy))  # the temporary folder is gone

    def test_a_later_board_run_writes_the_first_free_log_and_leaves_the_earlier_ones(self):
        stem = os.path.join(self.folder.name, "run-p904-2c")
        for path, text in ((self.log, "the first board run\n"), (stem + "-2.log", "the second board run\n")):
            with open(path, "w") as f:
                f.write(text)
        said, refused = self.run_bench(Board())
        self.assertIsNone(refused)
        self.assertEqual(("the first board run\n", "the second board run\n", SAID),
                         (self.logged(), self.logged(stem + "-2.log"), self.logged(stem + "-3.log")))
        self.assertEqual("the log is %s-3.log" % stem, said.splitlines()[-1])

    def test_the_time_limit_is_on_the_board_run_and_only_on_it(self):
        board = Board()
        self.run_bench(board)
        self.assertEqual([None] * 5 + [LIMIT] + [None] * 4, board.limits)
        self.assertEqual(LIMIT, probe.LIMIT_S)

    def test_the_copy_is_the_probe_with_the_gait_rows_filled_in(self):
        board = Board()
        self.run_bench(board)
        with open(os.path.join(REPO, "probe904_figures.py")) as f:
            source = f.read().splitlines()
        copy = board.copy.splitlines()
        self.assertEqual(len(source), len(copy))
        differ = [(a, b) for a, b in zip(source, copy) if a != b]
        self.assertEqual(1, len(differ))
        self.assertTrue(differ[0][0].startswith("GAITS = None"))
        module = {"__name__": "copy"}
        exec(compile(board.copy, "copy", "exec"), module)
        self.assertEqual(STAND_IN_ROWS, module["GAITS"])

    def test_the_time_limit_follows_the_counts(self):
        board = Board()
        self.run_bench(board, counts=(16, 20, 24, 28, 32, 36, 40, 48, 64))
        self.assertEqual([None] * 5 + [9 * 30 + 120] + [None] * 4, board.limits)

    def test_the_copy_holds_the_given_counts_as_a_tuple_and_its_counts_line_keeps_its_comment(self):
        board = Board()
        self.run_bench(board, counts=[24, 0, 7])
        with open(os.path.join(REPO, "probe904_figures.py")) as f:
            source = f.read().splitlines()
        copy = board.copy.splitlines()
        self.assertEqual(len(source), len(copy))
        differ = [(a, b) for a, b in zip(source, copy) if a != b]
        self.assertEqual(["COUNTS = (24, 0, 7)  # figures at once, one count after the other"],
                         [b for a, b in differ if a.startswith("COUNTS = ")])
        self.assertEqual(["COUNTS", "GAITS"], sorted(a.split(" = ")[0] for a, _ in differ))
        module = {"__name__": "copy"}
        exec(compile(board.copy, "copy", "exec"), module)
        self.assertEqual(((24, 0, 7), STAND_IN_ROWS), (module["COUNTS"], module["GAITS"]))

    def test_filled_refuses_a_source_without_exactly_one_gaits_line_and_one_counts_line(self):
        with open(os.path.join(REPO, "probe904_figures.py")) as f:
            source = f.read()
        for old in ("\nGAITS = None", "\nCOUNTS = (0, 1, 2, 4, 8, 16)"):
            for case, broken in (("none", source.replace(old, "\n# gone", 1)), ("two", source.replace(old, old * 2, 1))):
                with self.subTest(line=old.strip(), case=case), self.assertRaises(ValueError):
                    probe.filled(broken, STAND_IN_ROWS, (24, 0, 7))

    def test_a_box_with_an_art_index_is_refused_before_any_copy_naming_both_kinds(self):
        board = Board(root=("boot.py", "main.py", "art_index.py", "packs/"))
        said, refused = self.run_bench(board)
        self.assertIn("real index", str(refused.code))
        self.assertIn("shadow index", str(refused.code))
        for line in RECOVERY:
            self.assertIn(line, str(refused.code))
        self.assertEqual([["ls", ":"]], board.commands)
        self.assertIn("art_index.py", board.root)
        self.assertFalse(os.path.exists(self.log))

    def test_a_failed_pack_copy_copies_no_index_and_resets_the_box(self):
        board = Board(copy_fails={":packs/figures.pak": "before"})
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_bench(board)
        self.assertEqual([["ls", ":"], ["cp", board.commands[1][1], ":packs/figures.pak"], ["ls", ":"],
                          ["ls", ":packs"], ["reset"]], board.commands)
        self.assertFalse(os.path.exists(self.log))

    def test_a_box_with_no_packs_folder_fails_the_first_copy_and_the_cleanup_reads_no_packs_folder(self):
        board = Board(root=("boot.py", "main.py", "app.mpy"))
        with self.assertRaisesRegex(subprocess.CalledProcessError, "") as caught:
            self.run_bench(board)
        self.assertIn(":packs/figures.pak", caught.exception.cmd)
        self.assertEqual([["ls", ":"], ["cp", board.commands[1][1], ":packs/figures.pak"], ["ls", ":"], ["reset"]],
                         board.commands)
        self.assertEqual([], self.sleeps)

    def test_a_pack_copy_that_failed_halfway_leaves_its_file_and_the_cleanup_removes_only_it(self):
        board = Board(copy_fails={":packs/figures.pak": "halfway"})
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_bench(board)
        self.assertEqual([["ls", ":"], ["ls", ":packs"], ["rm", ":packs/figures.pak"], ["reset"]],
                         board.commands[2:])
        self.assertEqual({"rescue.pak"}, board.packs)

    def test_an_index_copy_that_failed_halfway_is_removed_with_the_pack(self):
        board = Board(copy_fails={":art_index.py": "halfway"})
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_bench(board)
        self.assertEqual(cleanup(), board.commands[3:])
        self.assertEqual((set(ROOT), {"rescue.pak"}), (board.root, board.packs))

    def test_a_failed_board_run_is_logged_cleaned_up_and_refused(self):
        out = "probe p904 counts 0,1,2,4,8,16 seconds 30\ngame figures refused: MemoryError('no PSRAM for the pool')\n"
        board = Board(run_error=subprocess.CalledProcessError(1, ["mpremote", "run"], output=out,
                                                              stderr="Traceback: the board raised\n"))
        said, refused = self.run_bench(board)
        self.assertIn("exit 1", str(refused.code))
        self.assertIn(self.log, str(refused.code))
        self.assertEqual(out + "Traceback: the board raised\n", self.logged())
        self.assertEqual(cleanup(), board.commands[6:])
        self.assertNotIn("art_index.py", board.root)

    def test_a_failed_cleanup_says_the_first_error_what_may_be_left_and_the_recovery(self):
        run_error = subprocess.CalledProcessError(1, ["mpremote", "run"], output="probe p904 counts\n", stderr="")
        for case, board, first in (
                ("a failed board run", Board(run_error=run_error, broken={"ls :"}), "the board run failed with exit 1"),
                ("a failed copy", Board(copy_fails={":art_index.py": "before"}, broken={"ls :"}),
                 "mpremote cp %s :art_index.py failed: no space left")):
            with self.subTest(case=case):
                said, refused = self.run_bench(board)
                text = str(refused.code)
                if "%s" in first:
                    first = first % board.commands[2][1]
                self.assertIn(first, text)
                self.assertIn("the cleanup failed: mpremote ls : failed: could not enter raw repl", text)
                self.assertIn(":art_index.py and :packs/figures.pak may still be on the box", text)
                for line in RECOVERY:
                    self.assertIn(line, text)
                if case == "a failed board run":  # its lines were logged before the cleanup: the message names the log
                    self.assertTrue(text.endswith("; the log is %s" % self.log), text)
                else:
                    self.assertNotIn("the log is", text)

    def test_a_timed_out_board_run_is_logged_from_its_bytes_cleaned_up_and_refused(self):
        out = b"probe p904 counts 0,1,2,4,8,16 seconds 30\npack pool 2463997\ncount 0 starts\ncount 1 starts\n"
        board = Board(run_error=subprocess.TimeoutExpired(["mpremote", "run"], LIMIT, output=out, stderr=None))
        said, refused = self.run_bench(board)
        self.assertIn("over %d s" % LIMIT, str(refused.code))
        self.assertEqual(out.decode(), self.logged())
        self.assertIn("count 1 starts", said)
        self.assertEqual(cleanup(), board.commands[6:])

    def test_a_board_run_that_did_not_end_with_done_is_logged_and_refused(self):
        out = "probe p904 counts 0,1,2,4,8,16 seconds 30\npack heap 2463997\ncount 0 starts\n"
        board = Board(said=out)
        said, refused = self.run_bench(board)
        self.assertIn("done", str(refused.code))
        self.assertIn("count 0 starts", str(refused.code))
        self.assertEqual(out, self.logged())
        self.assertEqual(cleanup(), board.commands[6:])

    def test_done_inside_another_line_is_no_done(self):
        out = "probe p904 counts 0,1,2,4,8,16 seconds 30\ngame figures refused: abandoned\nundone\n"
        said, refused = self.run_bench(Board(said=out))
        self.assertIsNotNone(refused)
        self.assertIn("did not end with done", str(refused.code))

    def test_the_wait_and_the_cleanup_try_again_while_the_board_reboots_or_the_probe_still_runs(self):
        board = Board(fails=["exec pass", "exec pass", "ls :packs", "rm :art_index.py :packs/figures.pak"])
        said, refused = self.run_bench(board)
        self.assertIsNone(refused)
        self.assertEqual([["exec", "pass"]] * 3 + [["run", board.commands[7][1]], ["ls", ":"], ["ls", ":packs"],
                                                   ["ls", ":packs"], ["rm", ":art_index.py", ":packs/figures.pak"],
                                                   ["rm", ":art_index.py", ":packs/figures.pak"], ["reset"]],
                         board.commands[4:])
        self.assertEqual([box.RESET_PAUSE_S] * 4, self.sleeps)
        self.assertNotIn("figures.pak", board.packs)

    def test_a_dry_run_prints_every_command_in_order_and_runs_none_nor_writes_a_log(self):
        with mock.patch.object(box.subprocess, "run") as run:
            said, refused = self.run_bench(box.Mpremote(True))
        run.assert_not_called()
        self.assertIsNone(refused)
        self.assertEqual(dry_lines(), [dry_line(line) for line in said.splitlines()])
        self.assertFalse(os.path.exists(self.log))


def dry_lines():
    """A dry run's lines, each temporary path as TMP."""
    return ["mpremote ls :", "mpremote cp TMP/packs/figures.pak :packs/figures.pak",
            "mpremote cp TMP/art_index.py :art_index.py", "mpremote reset", "mpremote exec pass",
            "mpremote run TMP/probe904_figures.py", "mpremote ls :", "mpremote ls :packs",
            "mpremote rm :art_index.py :packs/figures.pak", "mpremote reset"]


def dry_line(line):
    import re

    return re.sub(r"\S+(/packs/figures\.pak|/art_index\.py|/probe904_figures\.py)", r"TMP\1", line)


def cmu_folder(folder):
    """folder with an empty file of each name the cast's cycles need: open_capture finds them; nothing reads them."""
    for name in mocap.Capture(folder).missing():
        open(os.path.join(folder, name), "w").close()
    return folder


class MacMainTest(unittest.TestCase):
    """mac(): its refusals and its error lines, and its dry run, with a stand-in for art/figures.py: no paint."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.log = os.path.join(self.folder.name, "run-p904-2c.log")
        patch = mock.patch.object(probe, "LOG", self.log)
        patch.start()
        self.addCleanup(patch.stop)

    def mac(self, argv, runner):
        """mac(argv) with runner and the stand-in art: what it printed, what it said on stderr, and its SystemExit."""
        with contextlib.redirect_stdout(io.StringIO()) as said, contextlib.redirect_stderr(io.StringIO()) as err:
            try:
                probe.mac(argv, runner=runner, art=StandInArt())
            except SystemExit as e:
                return said.getvalue(), err.getvalue(), e
        return said.getvalue(), err.getvalue(), None

    def test_missing_cmu_files_are_refused_with_the_captures_message_before_any_copy(self):
        board, empty = Board(), self.folder.name  # the log's folder holds no CMU file
        missing = ", ".join(mocap.Capture(empty).missing())
        said, err, refused = self.mac(["--cmu", empty], board)
        self.assertEqual(2, refused.code)
        self.assertIn("not in %s: %s" % (empty, missing), err)
        self.assertIn("09_01.amc", missing)
        self.assertEqual([["ls", ":"]], board.commands)
        self.assertFalse(os.path.exists(self.log))

    def test_a_failed_command_is_said_as_box_main_says_it(self):
        board = Board(copy_fails={":art_index.py": "before"})
        said, err, refused = self.mac(["--cmu", cmu_folder(self.folder.name)], board)
        self.assertEqual("mpremote cp %s :art_index.py failed: no space left" % board.commands[2][1], refused.code)
        self.assertEqual([["ls", ":"], ["ls", ":packs"], ["rm", ":packs/figures.pak"], ["reset"]], board.commands[3:])

    def test_a_missing_mpremote_is_said_as_box_main_says_it(self):
        def run(args, timeout=None):
            raise FileNotFoundError(2, "No such file or directory", "mpremote")

        said, err, refused = self.mac(["--cmu", cmu_folder(self.folder.name)], types.SimpleNamespace(
            dry_run=False, run=run))
        self.assertEqual("no mpremote: [Errno 2] No such file or directory: 'mpremote'", refused.code)

    def test_its_dry_run_prints_every_command_and_runs_none(self):
        with mock.patch.object(box.subprocess, "run") as run:
            said, err, refused = self.mac(["--dry-run", "--cmu", cmu_folder(self.folder.name)], None)
        run.assert_not_called()
        self.assertIsNone(refused)
        self.assertEqual(dry_lines(), [dry_line(line) for line in said.splitlines()])
        self.assertFalse(os.path.exists(self.log))

    def test_its_dry_run_with_counts_prints_the_same_commands(self):
        with mock.patch.object(box.subprocess, "run") as run:
            said, err, refused = self.mac(["--dry-run", "--counts", "16,20,24,28,32,36,40,48,64", "--cmu",
                                           cmu_folder(self.folder.name)], None)
        run.assert_not_called()
        self.assertIsNone(refused)
        self.assertEqual(dry_lines(), [dry_line(line) for line in said.splitlines()])

    def test_the_counts_go_to_the_copy_and_to_the_time_limit(self):
        board = Board()
        said, err, refused = self.mac(["--counts", "24,0,7", "--cmu", cmu_folder(self.folder.name)], board)
        self.assertIsNone(refused)
        self.assertEqual([None] * 5 + [3 * 30 + 120] + [None] * 4, board.limits)
        module = {"__name__": "copy"}
        exec(compile(board.copy, "copy", "exec"), module)
        self.assertEqual(((24, 0, 7), STAND_IN_ROWS), (module["COUNTS"], module["GAITS"]))

    def test_counts_it_refuses_stop_it_before_any_board_command(self):
        for text, why in (("0,20", "largest count"), ("4,8,4", "repeat"), ("4,x", "whole numbers")):
            with self.subTest(counts=text):
                board = Board()
                said, err, refused = self.mac(["--counts", text, "--cmu", cmu_folder(self.folder.name)], board)
                self.assertEqual(2, refused.code)
                self.assertIn("argument --counts: ", err)
                self.assertIn(why, err)
                self.assertEqual([], board.commands)
                self.assertFalse(os.path.exists(self.log))


if __name__ == "__main__":
    unittest.main()
