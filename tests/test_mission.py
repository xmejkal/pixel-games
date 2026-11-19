"""The first mission's count (P924, art/mission.py): the rows of the first mission of P900 as the PO named them, the
painter each row gets, the pack's bytes and what the pass line leaves. On test_moves' stand-in capture, for the painter
of a row. On stand-in pictures of known sizes, each row heavier than all lighter rows together, so a row left out,
counted twice or put in the wrong sum shows. And, only when the CMU files are downloaded, the six rows painted from
them: skipped without the files, and a skip is not a pass. Run from the repository root: python3 -B -m unittest
tests.test_mission."""

import contextlib
import functools
import io
import math
import os
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names
sys.path.insert(0, os.path.join(REPO, "tests"))

import detailed  # noqa: E402
import mission  # noqa: E402
import mocap  # noqa: E402
from artset import ArtSet, Painting  # noqa: E402
from export import Packs, Sheet  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402
from sets.rescue import read_committed  # noqa: E402
from test_detailed_figure import opaque_rows, standing  # noqa: E402
from test_moves import AHEAD, FLIGHT, SMALL, Height, in_3d, stand_in  # noqa: E402

RUN = mocap.named("run")
HOP = 80  # the hopper's period in frames, within the run's (70, 110): its only loop is one hop
STREET = (32, 24)  # a stand-in street's size: 32 * 24 * 2 = 1,536 bytes
# each stand-in row's box and poses, in MISSION's order: 10,368, 1,296, 5,184, 2,688, 720 and 288 bytes with both
# facings. Each is more than all lighter ones together, so no two sets of rows weigh the same. The third row's strip
# is the widest, so a page as wide as its first strip is too narrow
BOXES = (((6, 36), 12), ((6, 9), 6), ((9, 12), 12), ((7, 8), 12), ((5, 6), 6), ((3, 4), 6))
HOLD = "no hold is captured: the spray's stance, both arms held out in front"
IDLE = "no idle is captured: the spray's stance, a standing loop"


def hopper(t):
    """The hopper's side view at frame t: the standing pose lifted by a hop that is on the floor only every HOP
    frames, so a loop is one hop, whatever frame it starts at."""
    up = FLIGHT * (0.5 - 0.5 * math.cos(2 * math.pi * t / HOP))
    return {n: (f, u + up, d) for n, (f, u, d) in standing().items()}


def hopping():
    """test_moves' stand-in capture, and the run's span as the hopper's frames: no file is read."""
    capture = stand_in()
    first, last = RUN.frames
    capture.spans[(RUN.trial, RUN.frames)] = (Height(), [in_3d(hopper(t), AHEAD * t) for t in range(last - first)],
                                              0.0)
    return capture


def soles(pictures):
    """Each picture's lowest opaque row, counted from its last row: 0 when the soles stand on the last row."""
    return [img.height - 1 - opaque_rows(img)[-1] for img in pictures.pictures]


class StandPictures(detailed.Pictures):
    """A stand-in for a row's pictures: plain pictures of one size, so the count runs on known bytes with no CMU
    file. Its bytes are detailed.Pictures' own."""

    def __init__(self, row, size, poses):
        self.character, self.cycle, self.size = row.character, mocap.named(row.cycle), size
        self.pictures = [Image.new("RGBA", size, (200, 20 * i, 60, 255)) for i in range(poses)]
        for img in self.pictures:
            img.putpixel((0, 0), (0, 0, 250, 255))  # so a picture is not its own mirror
        self.left = [ImageOps.mirror(img) for img in self.pictures]


def stand_pack():
    """mission.MissionPack of MISSION's six rows on stand-in pictures and the stand-in street."""
    return mission.MissionPack([(row, StandPictures(row, *box)) for row, box in zip(mission.MISSION, BOXES)], STREET)


class MissionTest(unittest.TestCase):
    """MISSION and PASS_LINE against the PO's words of 2026-11-19 (D29 and D28 of P900's discovery), as literals."""

    def test_the_rows_are_his_three_actions_then_the_three_that_his_words_do_not_name(self):
        rows = [(r.character.name, r.cycle, r.action, r.said, r.placeholder) for r in mission.MISSION]
        self.assertEqual([("fireman", "run", "moves to the wall", True, None),
                          ("fireman", "spray", "holds a ladder", True, HOLD),
                          ("child", "climb", "climbs", True, None),
                          ("child", "child", "runs to the ladder", False, None),
                          ("fireman", "spray", "stands idle", False, IDLE),
                          ("child", "spray", "stands idle", False, IDLE)], rows)

    def test_the_pass_line_is_his(self):
        self.assertEqual(2464000, mission.PASS_LINE)

    def test_the_street_is_rescues_night(self):
        self.assertEqual("rescue_night", mission.STREET)


class RowPicturesTest(unittest.TestCase):
    """Row.pictures on the stand-in capture at SMALL px: a move's poses are snapped to the floor, any other cycle's
    are the capture's, and the row's character is the one painted. The climb is MISSION's own row."""

    @classmethod
    def setUpClass(cls):
        capture = hopping()
        cls.climb = mission.MISSION[2].pictures(capture, SMALL)
        cls.tall = mission.Row(detailed.FIREMAN, "climb", "climbs").pictures(capture, SMALL)
        cls.hop = mission.Row(detailed.FIREMAN, "run", "runs").pictures(capture, SMALL)

    def test_a_moves_soles_are_on_the_last_row_in_every_pose_though_it_rises(self):
        self.assertEqual([0] * 12, soles(self.climb))
        self.assertEqual([0] * 12, soles(self.tall))

    def test_a_cycle_that_is_no_move_keeps_its_lift(self):
        # one of twelve poses over a hop is near its top, whatever frame the loop starts at
        self.assertGreaterEqual(max(soles(self.hop)), round(0.5 * FLIGHT * self.hop.painter.PX))

    def test_the_rows_character_is_painted_at_the_height(self):
        self.assertIs(detailed.CHILD, self.climb.character)
        self.assertEqual(SMALL, self.climb.height)
        self.assertLess(self.climb.size[1], self.tall.size[1])


class MissionPackTest(unittest.TestCase):
    """MissionPack on the stand-in pictures: the two sums and what a line leaves, as literals."""

    def test_the_said_bytes_are_the_header_the_street_and_the_rows_that_his_words_name(self):
        self.assertEqual(16 + 1536 + 10368 + 1296 + 5184, stand_pack().said_bytes())

    def test_the_size_is_the_header_the_street_and_every_row(self):
        self.assertEqual(16 + 1536 + 10368 + 1296 + 5184 + 2688 + 720 + 288, stand_pack().size())

    def test_a_line_leaves_what_the_pack_does_not_take_and_a_lower_line_leaves_less_than_nothing(self):
        pack = stand_pack()
        self.assertEqual([7904, 0, -2096], [pack.left(line) for line in (30000, 22096, 20000)])

    def test_with_no_line_given_it_is_the_pass_line(self):
        self.assertEqual(2464000 - 22096, stand_pack().left())


class LinesTest(unittest.TestCase):
    """MissionPack.lines on the stand-in pictures: every line, as literals."""

    def test_a_line_a_row_then_the_street_the_two_sums_and_the_pass_line(self):
        self.assertEqual([
            "fireman's run (9:1 at 120 fps), moves to the wall: 12 poses of 6 by 36 px, 10368 bytes with both "
            "facings",
            "fireman's spray (13:27 at 120 fps), holds a ladder: 6 poses of 6 by 9 px, 1296 bytes with both facings; "
            "a placeholder: " + HOLD,
            "child's climb (13:33 at 120 fps), climbs: 12 poses of 9 by 12 px, 5184 bytes with both facings",
            "child's child (9:2 at 120 fps), runs to the ladder: 12 poses of 7 by 8 px, 2688 bytes with both "
            "facings; not named by the PO's words",
            "fireman's spray (13:27 at 120 fps), stands idle: 6 poses of 5 by 6 px, 720 bytes with both facings; "
            "not named by the PO's words; a placeholder: " + IDLE,
            "child's spray (13:27 at 120 fps), stands idle: 6 poses of 3 by 4 px, 288 bytes with both facings; "
            "not named by the PO's words; a placeholder: " + IDLE,
            "the street: 32 by 24 px, 1536 bytes",
            "the rows that the PO's words name, the street and the pack's header of 16 bytes: 18400 bytes",
            "every row, the street and the header: 22096 bytes",
            "the pass line: 30000 bytes; the pack leaves 7904 bytes"], stand_pack().lines(30000))

    def test_a_pack_as_big_as_the_line_passes_and_one_byte_more_is_over(self):
        pack = stand_pack()
        self.assertEqual("the pass line: 22096 bytes; the pack leaves 0 bytes", pack.lines(22096)[-1])
        self.assertEqual("the pass line: 22095 bytes; the pack is over by 1 bytes", pack.lines(22095)[-1])

    def test_with_no_line_given_the_last_line_holds_the_pass_line(self):
        self.assertEqual("the pass line: 2464000 bytes; the pack leaves 2441904 bytes", stand_pack().lines()[-1])


class MissionSheetTest(unittest.TestCase):
    """MissionSheet on the stand-in pictures: a labelled strip a row, each row's poses facing right."""

    def setUp(self):
        self.pack = stand_pack()
        self.sheet = mission.MissionSheet(self.pack)

    def test_a_label_a_row_with_its_character_action_and_cycle_and_a_placeholder_marked(self):
        self.assertEqual(["fireman moves to the wall (run)", "fireman holds a ladder (spray), a placeholder",
                          "child climbs (climb)", "child runs to the ladder (child)",
                          "fireman stands idle (spray), a placeholder", "child stands idle (spray), a placeholder"],
                         [label for label, _ in self.sheet.rows()])

    def test_a_rows_strip_is_its_poses_facing_right_on_the_dark(self):
        for (_, pictures), (_, strip) in zip(self.pack.painted, self.sheet.rows()):
            with self.subTest(size=pictures.size):
                expected = detailed.on_dark(pictures.pictures)
                self.assertEqual(expected.size, strip.size)
                self.assertTrue(expected.tobytes() == strip.tobytes())

    def test_the_page_holds_each_strip_18_px_under_its_label_the_next_10_px_under_the_strip(self):
        strips = [strip for _, strip in self.sheet.rows()]
        image, y = self.sheet.image(), 6
        self.assertEqual((max(s.width for s in strips) + 20, sum(s.height + 28 for s in strips) + 10), image.size)
        for strip in strips:
            with self.subTest(y=y):
                pasted = image.crop((10, y + 18, 10 + strip.width, y + 18 + strip.height))
                self.assertTrue(strip.tobytes() == pasted.tobytes())
            y += 18 + strip.height + 10


class MissingTest(unittest.TestCase):
    """main with no CMU file: the parser's error names the files of the rows' cycles, and of no other cycle."""

    def test_it_asks_for_the_trials_of_the_run_the_childs_run_the_spray_and_the_climb_and_exits_2(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as stop:
                mission.main(["--cmu", folder])
        self.assertEqual(2, stop.exception.code)
        self.assertIn(": 09.asf, 09_01.amc, 09_02.amc, 13.asf, 13_27.amc, 13_33.amc\n", err.getvalue())


@functools.lru_cache(maxsize=None)
def captured():
    """MISSION's rows painted from the CMU files at 96 px, once for all the tests that read them: (row, its
    pictures) each; None without the files."""
    capture = mocap.Capture()
    if capture.missing([mocap.named(row.cycle) for row in mission.MISSION]):
        return None
    return tuple((row, row.pictures(capture)) for row in mission.MISSION)


class MissionFromCaptureTest(unittest.TestCase):
    """The six rows painted from the CMU files at 96 px, and main on them: the lines of the run of 2026-11-19, the
    file that the product's writer makes of them, and the sheet. Skipped without the files, and a skip is not a pass.
    For main, a row's painter is replaced by one that hands out the pictures painted once here, so main does not paint
    them again."""

    LINES = [
        "fireman's run (9:1 at 120 fps), moves to the wall: 12 poses of 67 by 102 px, 328032 bytes with both facings",
        "fireman's spray (13:27 at 120 fps), holds a ladder: 6 poses of 51 by 97 px, 118728 bytes with both facings; "
        "a placeholder: " + HOLD,
        "child's climb (13:33 at 120 fps), climbs: 12 poses of 35 by 70 px, 117600 bytes with both facings",
        "child's child (9:2 at 120 fps), runs to the ladder: 12 poses of 42 by 72 px, 145152 bytes with both "
        "facings; not named by the PO's words",
        "fireman's spray (13:27 at 120 fps), stands idle: 6 poses of 51 by 97 px, 118728 bytes with both facings; "
        "not named by the PO's words; a placeholder: " + IDLE,
        "child's spray (13:27 at 120 fps), stands idle: 6 poses of 33 by 67 px, 53064 bytes with both facings; "
        "not named by the PO's words; a placeholder: " + IDLE,
        "the street: 320 by 240 px, 153600 bytes",
        "the rows that the PO's words name, the street and the pack's header of 16 bytes: 717976 bytes",
        "every row, the street and the header: 1034920 bytes",
        "the pass line: 2464000 bytes; the pack leaves 1429080 bytes"]

    @classmethod
    def setUpClass(cls):
        if captured() is None:
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.pictures = dict(captured())

    def setUp(self):
        self.folders = []  # the folder of the capture that main hands to each row's painter

    def painter(self, row, capture):
        self.folders.append(capture.folder)
        return self.pictures[row]

    def main(self, *argv):
        """What main prints with these arguments, as lines. It answers nothing: its exit code is 0."""
        out = io.StringIO()
        with mock.patch.object(mission.Row, "pictures", lambda row, capture: self.painter(row, capture)):
            with contextlib.redirect_stdout(out):
                self.assertIsNone(mission.main(list(argv)))
        return out.getvalue().splitlines()

    def test_every_row_is_painted_from_the_capture_of_the_cmu_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            link = os.path.join(folder, "cmu")
            os.symlink(os.path.expanduser(mocap.CMU_DIR), link)
            self.main("--cmu", link)
        self.assertEqual([link] * 6, self.folders)

    def test_it_prints_the_rows_the_street_the_sums_and_what_the_pass_line_leaves(self):
        self.assertEqual(self.LINES, self.main())

    def test_only_the_climb_is_painted_as_a_move(self):
        self.assertEqual(["Pictures", "Pictures", "MovePictures", "Pictures", "Pictures", "Pictures"],
                         [type(pictures).__name__ for _, pictures in captured()])

    def test_the_packs_size_is_the_size_of_the_file_that_the_products_writer_makes(self):
        pictures = {"street": (read_committed(["rescue_night"])["rescue_night"], False)}
        for i, (_, row) in enumerate(captured()):
            for side, poses in (("r", row.pictures), ("l", row.left)):
                pictures.update({"row%d_%s%d" % (i, side, k): (img, True) for k, img in enumerate(poses)})
        painting = Painting(pictures)
        packs = Packs([ArtSet("mission", 0, lambda: painting)], {"mission": painting})
        self.assertEqual(packs.row("mission")[1], mission.MissionPack(captured(), (320, 240)).size())

    def test_no_pose_of_a_row_is_cut_by_the_painters_box(self):
        for row, pictures in captured():
            with self.subTest(character=row.character.name, cycle=row.cycle):
                x0, y0, x1 = pictures.used
                self.assertTrue(x0 > 0 and y0 > 0 and x1 < detailed.box(detailed.TALL)[0])

    def test_out_writes_the_sheet_wide_enough_for_each_label(self):
        sheet = mission.MissionSheet(mission.MissionPack(captured(), (320, 240)))
        with tempfile.TemporaryDirectory() as folder:
            out = os.path.join(folder, "new")
            self.main("--out", out)
            self.assertEqual(["mission-sheet.png"], os.listdir(out))
            with Image.open(os.path.join(out, "mission-sheet.png")) as image:
                expected = sheet.image()
                self.assertEqual(expected.size, image.size)
                self.assertTrue(expected.tobytes() == image.convert("RGB").tobytes())
        font = Sheet(1, 1).font
        for label, _ in sheet.rows():
            with self.subTest(label=label):
                self.assertLessEqual(font.getlength(label), expected.width - 20)


if __name__ == "__main__":
    unittest.main()
