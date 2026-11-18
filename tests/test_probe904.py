"""probe904_figures.py (P904 step 2c): how many 96 px figures the game box moves at once. On the Mac, with no board:
the figure's run and turn on stand-in gaits, the count at each wall time, the frame wrapper's lines, the pack line's
pool or heap, the Mac part's commands with a recording runner (as tests/test_box.py's FakeRunner) and a stand-in for
art/figures.py, and its dry run. And, only when the CMU files are downloaded, the probe's game on the stand-in display
(tests/drawing_tft.py) with the set's written pack: skipped without them, and a skip is not a pass. Run from the
repository root: python3 -B -m unittest tests.test_probe904."""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
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

import box  # noqa: E402
import detailed  # noqa: E402
import figures  # noqa: E402
import gfx  # noqa: E402
import lcd  # noqa: E402
import mocap  # noqa: E402
import pictures  # noqa: E402
import probe904_figures as probe  # noqa: E402
import rescue  # noqa: E402

# stand-in gaits (name, pivot x, stride, speed) and picture sizes: none round, none alike, one pivot left of its
# picture's middle and one right of it, so a mirrored pivot or a margin of the wrong side shows
GAIT_A, SIZE_A = ("fireman", 47, 83, 141.7), (113, 109)
GAIT_B, SIZE_B = ("paramedic", 71, 97, 167.3), (104, 98)
STAND_IN_GAITS = (GAIT_A, GAIT_B, ("footballer", 53, 89, 151.9))
SAID = "probe p904 counts 0,1,2,4,8,16 seconds 30\npack pool 2463997\ncount 0 starts\nfps figures 23\n" \
       "count 16 starts\nfps figures 7\ndone\n"  # a run's output, as the board prints it
LIMIT = 6 * 30 + 120  # the run's time limit: the counts times SECONDS, plus 120 s


class FigureTest(unittest.TestCase):
    """One moving figure on stand-in gaits."""

    def test_the_screens_width_and_the_row_of_the_soles_are_the_games(self):
        self.assertEqual((gfx.WIDTH, rescue.FEET), (probe.WIDTH, probe.FEET))

    def test_it_moves_at_its_speed_the_way_it_faces_and_counts_the_px_it_ran(self):
        for facing in (1, -1):
            with self.subTest(facing=facing):
                figure = probe.Figure(GAIT_A, SIZE_A, 0.5, facing)
                x = figure.x
                figure.step(37)
                self.assertAlmostEqual(x + facing * 141.7 * 0.037, figure.x, places=9)
                self.assertAlmostEqual(141.7 * 0.037, figure.ran, places=9)
                figure.step(23)
                self.assertAlmostEqual(141.7 * 0.060, figure.ran, places=9)

    def test_it_starts_its_share_of_the_way_between_its_bounds(self):
        figure = probe.Figure(GAIT_B, SIZE_B, 0.25, -1)
        self.assertEqual((71, 319 - 71), (figure.lo, figure.hi))  # the pivot, right of the middle, is the margin
        self.assertAlmostEqual(71 + (248 - 71) * 0.25, figure.x, places=9)
        self.assertEqual((65, 319 - 65), (probe.Figure(GAIT_A, SIZE_A, 0, 1).lo, probe.Figure(GAIT_A, SIZE_A, 0, 1).hi))

    def test_it_turns_at_each_edge_and_its_picture_stays_whole_on_the_screen(self):
        for gait, (w, h) in ((GAIT_A, SIZE_A), (GAIT_B, SIZE_B)):
            for facing in (1, -1):
                with self.subTest(character=gait[0], facing=facing):
                    figure = probe.Figure(gait, (w, h), 0.4, facing)
                    turns, xs = [], []
                    for k in range(3000):
                        before, x = figure.facing, figure.x
                        figure.step((23, 41, 60, 17)[k % 4])
                        if figure.facing != before:
                            turns.append(figure.facing)
                        else:  # the facing follows the direction
                            self.assertEqual(figure.facing, 1 if figure.x > x else -1)
                        left, top = figure.corner()
                        self.assertTrue(0 <= left <= probe.WIDTH - w, (k, left))
                        xs.append(figure.x)
                    self.assertGreater(turns.count(1), 5)
                    self.assertGreater(turns.count(-1), 5)
                    self.assertEqual((figure.lo, figure.hi), (min(xs), max(xs)))

    def test_its_pose_follows_the_px_it_ran_and_its_side_its_facing(self):
        figure = probe.Figure(GAIT_A, SIZE_A, 0.5, 1)  # stride 83: 12 poses do not divide it
        for ran, pose in ((0, 0), (6.9, 0), (7.0, 1), (41.6, 5), (83.0, 0), (90.2, 1), (160.0, 11)):
            for facing, side in ((1, "r"), (-1, "l")):
                with self.subTest(ran=ran, facing=facing):
                    figure.ran, figure.facing = ran, facing
                    self.assertEqual("figures_fireman_%s%d" % (side, pose), figure.picture())

    def test_its_corner_puts_its_pivot_on_its_column_and_its_soles_on_row_214(self):
        figure = probe.Figure(GAIT_A, SIZE_A, 0.5, 1)
        figure.x = 150.7
        self.assertEqual((150 - 47, 214 - 109 + 1), figure.corner())
        figure.facing = -1  # the left picture is the right one mirrored: its pivot is w - 1 - 47 from its left
        self.assertEqual((150 - 65, 214 - 109 + 1), figure.corner())


class CountTest(unittest.TestCase):
    def test_the_counts_and_their_seconds(self):
        self.assertEqual(((0, 1, 2, 4, 8, 16), 30, None), (probe.COUNTS, probe.SECONDS, probe.GAITS))

    def test_each_counts_first_and_last_millisecond_and_none_after_the_last(self):
        for k, count in enumerate((0, 1, 2, 4, 8, 16)):
            with self.subTest(count=count):
                self.assertEqual(count, probe.count_at(k * 30000))
                self.assertEqual(count, probe.count_at(k * 30000 + 29999))
        self.assertIsNone(probe.count_at(180000))
        self.assertIsNone(probe.count_at(9876543))


class Clock:
    """ticks_ms on a list of frame times."""

    def __init__(self, times):
        self.times = list(times)

    def ticks_ms(self):
        return self.times.pop(0)


class CountsTest(unittest.TestCase):
    """The frame wrapper's work, on a stand-in App and a stand-in clock."""

    def test_it_prints_the_pack_line_once_then_each_count_and_starts_an_interval_at_each(self):
        start = 1234
        times = [start + 41 * k for k in range(4500)]
        clock = Clock(times)
        game = types.SimpleNamespace(count=None)
        app = types.SimpleNamespace(game=game, intervals=[])
        app.new_interval = lambda: app.intervals.append(game.count)
        counts = probe.Counts(clock.ticks_ms, lambda a, b: a - b, lambda: "pack pool 2463997")
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
        counts = probe.Counts(clock.ticks_ms, lambda a, b: a - b, lambda: "pack heap 7")
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


@contextlib.contextmanager
def figures_art(folder):
    """pictures reads the set written to folder through its own index, as the board does with the shadow index."""
    pack, path = figures.write(folder)
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
        cls.folder = tempfile.TemporaryDirectory()
        cls.art = figures_art(cls.folder.name)
        cls.index = cls.art.__enter__()
        cls.gaits = figures.gaits(None)
        cls.Probe = probe.game_class(cls.gaits)

    @classmethod
    def tearDownClass(cls):
        cls.art.__exit__(None, None, None)
        cls.folder.cleanup()

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
                name, pivot, stride, speed = self.gaits[i % 8]
                self.assertEqual(detailed.CAST[i % 8][0].name, name)
                self.assertEqual((name, pivot, stride, speed), (figure.name, figure.pivot, figure.stride, figure.speed))
                self.assertEqual(self.index.ART["figures_%s_r0" % name][:2], (figure.w, figure.h))

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
                moved = figure.speed * 0.043 * figure.facing
                if i < 2:
                    self.assertAlmostEqual(min(max(xs[i] + moved, figure.lo), figure.hi), figure.x, places=9)
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


class Board:
    """A recording runner for the Mac part: it keeps each command and its time limit, answers `ls :` and `ls :packs`
    with what the board holds (each copy lands, each rm removes), reads the probe's copy at its run and answers said.
    fails: commands (joined by spaces) that raise a CalledProcessError, once each time they are named. copy_fails: a
    copy's destination and how it fails: "before" lands nothing, "halfway" leaves its file. run_error: what the run
    raises instead of answering."""

    dry_run = False

    def __init__(self, root=("boot.py", "main.py", "app.mpy", "art_index.mpy", "packs/"), packs=("rescue.pak",),
                 said=SAID, fails=(), copy_fails=None, run_error=None):
        self.root, self.packs, self.said = set(root), set(packs), said
        self.fails, self.copy_fails, self.run_error = list(fails), copy_fails or {}, run_error
        self.commands, self.limits, self.copy = [], [], None

    def listing(self, names):
        return "".join("%12d %s\n" % (1000 + len(n), n) for n in sorted(names))

    def run(self, args, timeout=None):
        self.commands.append(args)
        self.limits.append(timeout)
        line = " ".join(args)
        if line in self.fails:
            self.fails.remove(line)
            raise subprocess.CalledProcessError(1, ["mpremote"] + args, output="", stderr="could not enter raw repl")
        if args[0] == "cp":
            how = self.copy_fails.get(args[-1])
            if how != "before":
                (self.packs if args[-1].startswith(":packs/") else self.root).add(args[-1].split("/")[-1].lstrip(":"))
            if how:
                raise subprocess.CalledProcessError(1, ["mpremote"] + args, output="", stderr="no space left")
        if args[0] == "rm":
            for path in args[1:]:
                (self.packs if path.startswith(":packs/") else self.root).discard(path.split("/")[-1].lstrip(":"))
        if args == ["ls", ":"]:
            return "ls :\n" + self.listing(self.root)
        if args == ["ls", ":packs"]:
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
    answers STAND_IN_GAITS. It keeps the captures it was given."""

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
        return STAND_IN_GAITS


def cleanup():
    return [["ls", ":"], ["ls", ":packs"], ["rm", ":art_index.py", ":packs/figures.pak"], ["reset"]]


class MacTest(unittest.TestCase):
    """The Mac part with a recording runner and a stand-in for art/figures.py: no board, no paint."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.log = os.path.join(self.folder.name, "run-p904-2c.log")
        self.art, self.sleeps = StandInArt(), []
        self.capture = object()

    def bench(self, board):
        return probe.Bench(board, self.art, self.log, sleep=self.sleeps.append)

    def run_bench(self, board):
        """check() then run(), as mac() calls them: what it printed, and the SystemExit it raised or None."""
        with contextlib.redirect_stdout(io.StringIO()) as said:
            try:
                bench = self.bench(board)
                bench.check()
                bench.run(self.capture)
            except SystemExit as e:
                return said.getvalue(), e
        return said.getvalue(), None

    def logged(self):
        with open(self.log) as f:
            return f.read()

    def test_a_run_copies_the_pack_then_the_index_waits_runs_once_and_cleans_up(self):
        board = Board()
        said, refused = self.run_bench(board)
        self.assertIsNone(refused)
        copy = board.commands[5][1]
        self.assertEqual([["ls", ":"], ["cp", board.commands[1][1], ":packs/figures.pak"],
                          ["cp", board.commands[2][1], ":art_index.py"], ["reset"], ["exec", "pass"], ["run", copy]]
                         + cleanup(), board.commands)
        self.assertTrue(board.commands[1][1].endswith(os.path.join("packs", "figures.pak")))
        self.assertTrue(board.commands[2][1].endswith("art_index.py"))
        self.assertEqual({"boot.py", "main.py", "app.mpy", "art_index.mpy", "packs/"}, board.root)
        self.assertEqual({"rescue.pak"}, board.packs)
        self.assertEqual([self.capture, self.capture], self.art.captures)
        self.assertEqual(SAID, self.logged())
        self.assertEqual(SAID, said)
        self.assertFalse(os.path.exists(copy))  # the temporary folder is gone

    def test_the_time_limit_is_on_the_run_and_only_on_it(self):
        board = Board()
        self.run_bench(board)
        self.assertEqual([None] * 5 + [LIMIT] + [None] * 4, board.limits)
        self.assertEqual(LIMIT, probe.LIMIT_S)

    def test_the_copy_is_the_probe_with_the_gaits_filled_in(self):
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
        self.assertEqual(STAND_IN_GAITS, module["GAITS"])

    def test_a_box_with_its_own_art_index_is_refused_before_any_copy(self):
        board = Board(root=("boot.py", "main.py", "art_index.py", "packs/"))
        said, refused = self.run_bench(board)
        self.assertIn("art_index.py", str(refused.code))
        self.assertEqual([["ls", ":"]], board.commands)
        self.assertIn("art_index.py", board.root)
        self.assertFalse(os.path.exists(self.log))

    def test_missing_cmu_files_are_refused_with_the_captures_message_before_any_copy(self):
        board, empty = Board(), self.folder.name  # the log's folder holds no CMU file
        missing = ", ".join(mocap.Capture(empty).missing())
        with contextlib.redirect_stderr(io.StringIO()) as err, mock.patch.object(probe, "LOG", self.log), \
                self.assertRaises(SystemExit):
            probe.mac(["--cmu", empty], runner=board)
        self.assertIn("not in %s: %s" % (empty, missing), err.getvalue())
        self.assertIn("09_01.amc", missing)
        self.assertEqual([["ls", ":"]], board.commands)
        self.assertFalse(os.path.exists(self.log))

    def test_a_failed_pack_copy_copies_no_index_and_resets_the_box(self):
        board = Board(copy_fails={":packs/figures.pak": "before"})
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_bench(board)
        self.assertEqual([["ls", ":"], ["cp", board.commands[1][1], ":packs/figures.pak"], ["ls", ":"],
                          ["ls", ":packs"], ["reset"]], board.commands)
        self.assertFalse(os.path.exists(self.log))

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
        self.assertEqual(({"boot.py", "main.py", "app.mpy", "art_index.mpy", "packs/"}, {"rescue.pak"}),
                         (board.root, board.packs))

    def test_a_failed_run_is_logged_cleaned_up_and_refused(self):
        out = "probe p904 counts 0,1,2,4,8,16 seconds 30\ngame figures refused: MemoryError('no PSRAM for the pool')\n"
        board = Board(run_error=subprocess.CalledProcessError(1, ["mpremote", "run"], output=out,
                                                              stderr="Traceback: the board raised\n"))
        said, refused = self.run_bench(board)
        self.assertIn("exit 1", str(refused.code))
        self.assertEqual(out + "Traceback: the board raised\n", self.logged())
        self.assertEqual(cleanup(), board.commands[6:])
        self.assertNotIn("art_index.py", board.root)

    def test_a_timed_out_run_is_logged_from_its_bytes_cleaned_up_and_refused(self):
        out = b"probe p904 counts 0,1,2,4,8,16 seconds 30\npack pool 2463997\ncount 0 starts\ncount 1 starts\n"
        board = Board(run_error=subprocess.TimeoutExpired(["mpremote", "run"], LIMIT, output=out, stderr=None))
        said, refused = self.run_bench(board)
        self.assertIn("over %d s" % LIMIT, str(refused.code))
        self.assertEqual(out.decode(), self.logged())
        self.assertIn("count 1 starts", said)
        self.assertEqual(cleanup(), board.commands[6:])

    def test_a_run_that_did_not_end_with_done_is_logged_and_refused(self):
        out = "probe p904 counts 0,1,2,4,8,16 seconds 30\npack heap 2463997\ncount 0 starts\n"
        board = Board(said=out)
        said, refused = self.run_bench(board)
        self.assertIn("done", str(refused.code))
        self.assertIn("count 0 starts", str(refused.code))
        self.assertEqual(out, self.logged())
        self.assertEqual(cleanup(), board.commands[6:])

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
        lines = said.splitlines()
        self.assertEqual(10, len(lines), lines)
        self.assertEqual("mpremote ls :", lines[0])
        self.assertRegex(lines[1], r"^mpremote cp \S+/packs/figures\.pak :packs/figures\.pak$")
        self.assertRegex(lines[2], r"^mpremote cp \S+/art_index\.py :art_index\.py$")
        self.assertEqual(["mpremote reset", "mpremote exec pass"], lines[3:5])
        self.assertRegex(lines[5], r"^mpremote run \S+/probe904_figures\.py$")
        self.assertEqual(["mpremote ls :", "mpremote ls :packs", "mpremote rm :art_index.py :packs/figures.pak",
                          "mpremote reset"], lines[6:])
        self.assertFalse(os.path.exists(self.log))


if __name__ == "__main__":
    unittest.main()
