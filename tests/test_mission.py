"""The first mission's count (P924, art/mission.py): the rows of the first mission of P900 as the PO named them, the
painter each row gets, the pack's bytes and what the pass line leaves. On test_moves' stand-in capture, for the painter
of a row. On stand-in pictures of known sizes, each row heavier than all lighter rows together, so a row left out,
counted twice or put in the wrong sum shows. And, only when the CMU files are downloaded, the six rows painted from
them: skipped without the files, and a skip is not a pass. The set mission (P906): its places, the ladder, its pack
and index, its numbers for the probe and the storyboard, on the stand-in capture and, only with the CMU files, from
them. Run from the repository root: python3 -B -m unittest tests.test_mission."""

import ast
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
import moves  # noqa: E402
import sets  # noqa: E402
from artset import ArtSet, Painting  # noqa: E402
from export import HEADER, Packs, Sheet, pack_bytes, to_bin  # noqa: E402
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


# --- the set mission (P906) --------------------------------------------------------------------------------------

NAMES = ["mission_night", "mission_ladder"] + [
    "mission_%s_%s_%s%d" % (figure, motion, side, i)
    for figure, motion, poses in (("fireman", "run", 12), ("fireman", "hold", 1), ("child", "run", 12),
                                  ("child", "climb", 12))
    for side in "rl" for i in range(poses)]  # the set's pictures in the pack's order


def set_capture():
    """hopping()'s capture, with the hopper's frames as the child's run and as the spray too: the set's four motions
    with no file read."""
    capture = hopping()
    for cycle in (mocap.named("child"), mocap.named("spray")):
        first, last = cycle.frames
        capture.spans[(cycle.trial, cycle.frames)] = (
            Height(), [in_3d(hopper(t), AHEAD * t) for t in range(last - first)], 0.0)
    return capture


@functools.lru_cache(maxsize=None)
def set_painted():
    """The set's motions painted at SMALL px from the stand-in capture, once for all the tests that read them."""
    return mission.painted(set_capture(), SMALL)


@functools.lru_cache(maxsize=None)
def set_captured():
    """The set's motions painted at 96 px from the CMU files, once; None without the files."""
    capture = mocap.Capture()
    if capture.missing([mocap.named(row.cycle) for row in mission.MISSION]):
        return None
    return mission.painted(capture)


def opaque(img, row):
    """The columns of img's opaque pixels on a row."""
    return [x for x in range(img.width) if img.getpixel((x, row))[3]]


class SetTest(unittest.TestCase):
    """The set mission's name, its motions and its places, as literals: a change of a place is a change of this test."""

    def test_the_set_is_mission_and_in_no_art_sets(self):
        self.assertEqual("mission", mission.SET)
        self.assertNotIn("mission", [art_set.name for art_set in sets.ART_SETS])

    def test_its_motions_are_the_first_four_rows_and_the_hold_keeps_one_pose(self):
        self.assertEqual([("fireman", "run", 0, None), ("fireman", "hold", 1, 1), ("child", "run", 3, None),
                          ("child", "climb", 2, None)],
                         [(f, m, mission.MISSION.index(row), keep) for f, m, row, keep in mission.MOTIONS])

    def test_the_places_are_the_storyboards_start_values(self):
        self.assertEqual((214, 111, 96, (220, 282), 115, 117, 54, (115, 222), (80, 88)),
                         (mission.FEET, mission.LADDER_FOOT, mission.LADDER_TOP, mission.START, mission.HOLD_PLACE,
                          mission.FOOT_PLACE, mission.END_UP, mission.MARK_HOLD, mission.MARK_ROOF))
        self.assertEqual({"fireman": 8, "child": 0}, mission.STAND)

    def test_the_places_at_96_px_are_the_constants(self):
        constants = (mission.START, (mission.HOLD_PLACE, mission.FOOT_PLACE), mission.END_UP,
                     (mission.MARK_HOLD, mission.MARK_ROOF))
        self.assertEqual([constants, constants], [mission.places(), mission.places(96)])

    def test_the_places_at_80_64_and_48_px_scale_the_px_from_the_ladders_foot_and_to_the_roof_a_half_up(self):
        self.assertEqual([((220, 282), (114, 116), 65, ((114, 222), (80, 88))),
                          ((220, 282), (114, 115), 75, ((114, 222), (80, 88))),
                          ((220, 282), (113, 114), 86, ((113, 222), (80, 88)))],
                         [mission.places(height) for height in (80, 64, 48)])
        self.assertEqual(((114, 115), 75), (mission.places(64).place, mission.places(64).end))


class LadderPictureTest(unittest.TestCase):
    """ladder(advance): art/moves.py's Ladder from the foot on the soles' row up to the roof's row, at the climb's
    slant, cut to the px it uses."""

    def test_at_the_climbs_slant_it_is_39_by_119_px_from_x_75_on_the_roofs_row(self):
        img, place = mission.ladder((5, 19))
        self.assertEqual(((39, 119), (75, 96)), (img.size, place))

    def test_its_rail_stands_on_the_foot_and_leans_on_the_stations_corner(self):
        img, (x, y) = mission.ladder((5, 19))
        self.assertEqual([110 - x, 111 - x], opaque(img, 214 - y))  # the foot: the rail's 2 px round x 111
        self.assertEqual([79 - x, 80 - x], opaque(img, 96 - y))  # the top: the corner, x 80

    def test_another_slant_keeps_the_foot_and_the_roofs_row(self):
        img, (x, y) = mission.ladder((7, 23))
        self.assertEqual((96, 214 - 96 + 1), (y, img.height))
        self.assertIn(111 - x, opaque(img, img.height - 1))
        self.assertEqual(round(111 - 118 * 7 / 23) - 1 - x, opaque(img, 0)[0])

    def test_it_is_keyed_and_in_one_colour_of_wood(self):
        img, _ = mission.ladder((5, 19))
        self.assertEqual({(0, 0, 0, 0), moves.Ladder.COLOUR + (255,)}, set(img.get_flattened_data()))


class SetPaintTest(unittest.TestCase):
    """The set painted from the stand-in capture at SMALL px: its motions, its pack and index (write), and its numbers
    for the probe."""

    def test_each_motion_is_its_rows_pictures_and_only_the_climb_is_a_move(self):
        painted = set_painted()
        self.assertEqual([("fireman", "run"), ("fireman", "hold"), ("child", "run"), ("child", "climb")],
                         list(painted))
        self.assertEqual(["Pictures", "Pictures", "Pictures", "MovePictures"],
                         [type(p).__name__ for p in painted.values()])
        self.assertEqual([("fireman", "run"), ("fireman", "spray"), ("child", "child"), ("child", "climb")],
                         [(p.character.name, p.cycle.name) for p in painted.values()])
        self.assertEqual([SMALL] * 4, [p.height for p in painted.values()])

    def test_write_puts_the_pack_and_an_index_of_it_alone_where_the_board_has_them(self):
        painted = set_painted()
        with tempfile.TemporaryDirectory() as folder:
            pack, index = mission.write(folder, painted)
            self.assertEqual((os.path.join(folder, "packs", "mission.pak"), os.path.join(folder, "art_index.py")),
                             (pack, index))
            art = {}
            with open(index) as f:
                exec(f.read(), art)
            with open(pack, "rb") as f:
                data = f.read()
        self.assertEqual(NAMES, list(art["PICTURE_SETS"]["mission"]))
        self.assertEqual(["mission"], list(art["PACKS"]))
        self.assertEqual(("packs/mission.pak", len(data)), art["PACKS"]["mission"][:2])
        ladder_img, _ = mission.ladder(painted["child", "climb"].advance)
        motions = sum(w * h * 2 * poses * 2 for (w, h), poses in (
            (painted["fireman", "run"].size, 12), (painted["fireman", "hold"].size, 1),
            (painted["child", "run"].size, 12), (painted["child", "climb"].size, 12)))
        self.assertEqual(HEADER + 320 * 240 * 2 + ladder_img.width * ladder_img.height * 2 + motions, len(data))

        def at(name):
            w, h, _, offset = art["ART"][name]
            return data[offset:offset + w * h * 2]

        self.assertTrue(at("mission_night") == pack_bytes("rescue_night"))
        self.assertTrue(at("mission_fireman_hold_l0") == to_bin(painted["fireman", "hold"].left[0], True))
        self.assertTrue(at("mission_child_climb_r7") == to_bin(painted["child", "climb"].pictures[7], True))
        self.assertTrue(at("mission_ladder") == to_bin(ladder_img, True))

    def test_the_numbers_are_the_runs_gaits_the_pivots_the_climbs_travel_and_the_places(self):
        painted, capture = set_painted(), set_capture()
        got = mission.numbers(painted)
        runs = {figure: detailed.RunPictures(capture, SMALL, character=character, cycle_name=cycle)
                for figure, character, cycle in (("fireman", detailed.FIREMAN, "run"),
                                                 ("child", detailed.CHILD, "child"))}
        climb = painted["child", "climb"]
        self.assertEqual({figure: run.stride for figure, run in runs.items()}, got["stride"])
        self.assertEqual({figure: round(run.speed) for figure, run in runs.items()}, got["speed"])
        self.assertEqual({key: p.pivot[0] for key, p in painted.items()}, got["pivot"])
        self.assertEqual((round(climb.pose_ms), tuple(climb.travel), climb.advance), got["climb"])
        self.assertEqual(mission.ladder(climb.advance)[1], got["ladder"])
        self.assertEqual(({"fireman": 8, "child": 0}, (220, 282), (115, 117), 54, ((115, 222), (80, 88))),
                         (got["stand"], got["start"], got["place"], got["end"], got["mark"]))

    def test_the_numbers_at_another_height_hold_its_places_and_no_height(self):
        got = mission.numbers(set_painted(), 64)
        self.assertEqual(((220, 282), (114, 115), 75, ((114, 222), (80, 88))),
                         (got["start"], got["place"], got["end"], got["mark"]))
        self.assertNotIn("height", got)

    def test_the_numbers_are_plain_literals_for_the_probes_copy(self):
        got = mission.numbers(set_painted())
        self.assertEqual(got, ast.literal_eval(repr(got)))


class SetFromCaptureTest(unittest.TestCase):
    """The set painted from the CMU files at 96 px: the pack's bytes part by part, as the plan counts them, and the
    numbers the probe gets. Skipped without the files, and a skip is not a pass."""

    @classmethod
    def setUpClass(cls):
        if set_captured() is None:
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)

    def test_the_pack_is_773470_bytes_the_plans_count_part_by_part(self):
        with tempfile.TemporaryDirectory() as folder:
            pack, index = mission.write(folder, set_captured())
            size = os.path.getsize(pack)
            art = {}
            with open(index) as f:
                exec(f.read(), art)
        parts = {}
        for name in art["PICTURE_SETS"]["mission"]:
            w, h = art["ART"][name][:2]
            part = "_".join(name.split("_")[1:3]) if name.count("_") > 1 else name.split("_")[1]
            parts[part] = parts.get(part, 0) + w * h * 2
        self.assertEqual({"night": 153600, "fireman_run": 328032, "fireman_hold": 19788, "child_run": 145152,
                          "child_climb": 117600, "ladder": 9282}, parts)
        self.assertEqual(773470, size)
        self.assertEqual(16 + sum(parts.values()), size)

    def test_the_numbers_from_the_capture(self):
        got = mission.numbers(set_captured())
        self.assertEqual(({"fireman": 146, "child": 80}, {"fireman": 199, "child": 108}), (got["stride"], got["speed"]))
        self.assertEqual({("fireman", "run"): 39, ("fireman", "hold"): 15, ("child", "run"): 23,
                          ("child", "climb"): 6}, got["pivot"])
        self.assertEqual((201, ((0, 5), (1, 13), (1, 13), (1, 13), (1, 12), (2, 12), (2, 11), (3, 11), (4, 14),
                                (5, 19), (5, 23), (5, 23)), (5, 19)), got["climb"])
        self.assertEqual((75, 96), got["ladder"])


class StoryboardTest(unittest.TestCase):
    """The storyboard's three moments on the set painted from the stand-in capture: what each frame shows and where."""

    def setUp(self):
        self.painted = set_painted()
        self.board = mission.Storyboard(self.painted, Image.new("RGB", (320, 240), (9, 7, 5)))

    def standing(self, figure, x):
        p = self.painted[figure, "run"]
        pose = mission.STAND[figure]
        return p.left[pose], x - (p.size[0] - 1 - p.pivot[0]), 214 - p.size[1] + 1

    def test_the_start_both_stand_at_their_start_places_the_child_active_the_mark_over_the_fireman(self):
        first = self.board.moments()[0]
        self.assertEqual((self.standing("fireman", 220), self.standing("child", 282)),
                         (first["figures"][0], first["figures"][1]))
        self.assertEqual((1, 1), (first["active"], first["task"]))
        self.assertEqual(("over", 0), first["mark"])

    def test_the_hold_the_fireman_holds_at_his_place_and_the_mark_is_over_the_child(self):
        second = self.board.moments()[1]
        hold = self.painted["fireman", "hold"]
        self.assertEqual((hold.left[0], 115 - (hold.size[0] - 1 - hold.pivot[0]), 214 - hold.size[1] + 1),
                         second["figures"][0])
        self.assertEqual(self.standing("child", 282), second["figures"][1])
        self.assertEqual((0, 2, ("over", 1)), (second["active"], second["task"], second["mark"]))

    def test_the_end_the_child_at_its_first_pose_54_px_up_or_more_and_the_mark_on_the_roofs_edge(self):
        third = self.board.moments()[2]
        climb = self.painted["child", "climb"]
        (af, au), w, h = climb.advance, climb.size[0], climb.size[1]
        plays, pose = next((k, i) for k in range(99) for i in range(12) if k * au + climb.travel[i][1] >= 54)
        f, u = plays * af + climb.travel[pose][0], plays * au + climb.travel[pose][1]
        self.assertGreaterEqual(u, 54)
        self.assertEqual((climb.left[pose], 117 - f - (w - 1 - climb.pivot[0]), 214 - u - h + 1),
                         third["figures"][1])
        self.assertEqual((1, 2, ("at", (80, 88))), (third["active"], third["task"], third["mark"]))

    def test_the_arrow_and_the_mark_are_their_rows_each_over_a_dark_rim_of_1_px(self):
        self.assertEqual(((7, 5, 3, 1), (1, 3, 5, 7, 9, 7, 5, 3, 1)),
                         (mission.Storyboard.ARROW, mission.Storyboard.MARK))
        frame, (x, y) = self.board.frame(2), mission.MARK_ROOF  # the mark's middle on the roof's edge
        yellow, rim = mission.Storyboard.YELLOW, mission.Storyboard.RIM
        self.assertEqual([rim, yellow, yellow, rim], [frame.getpixel((x, row)) for row in (y - 5, y - 4, y + 4, y + 5)])
        self.assertEqual([rim, yellow, yellow, rim], [frame.getpixel((col, y)) for col in (x - 5, x - 4, x + 4, x + 5)])

    def test_at_48_px_the_hold_and_the_end_are_its_places_and_the_third_label_names_its_end(self):
        board = mission.Storyboard(self.painted, Image.new("RGB", (320, 240), (9, 7, 5)), 48)
        _, second, third = board.moments()
        hold, climb = self.painted["fireman", "hold"], self.painted["child", "climb"]
        self.assertEqual((hold.left[0], 113 - (hold.size[0] - 1 - hold.pivot[0]), 214 - hold.size[1] + 1),
                         second["figures"][0])
        self.assertEqual(113, second["columns"][0])
        (af, au), w, h = climb.advance, climb.size[0], climb.size[1]
        plays, pose = next((k, i) for k in range(99) for i in range(12) if k * au + climb.travel[i][1] >= 86)
        f, u = plays * af + climb.travel[pose][0], plays * au + climb.travel[pose][1]
        self.assertGreaterEqual(u, 86)
        self.assertEqual((climb.left[pose], 114 - f - (w - 1 - climb.pivot[0]), 214 - u - h + 1),
                         third["figures"][1])
        self.assertEqual(((113, 114 - f), ("at", (80, 88))), (third["columns"], third["mark"]))
        self.assertEqual(["the child at its first pose %d px up or more: the round's end" % up
                          for up in (86, 54)], [board.labels[2], self.board.labels[2]])

    def test_the_image_hands_on_the_three_labels_with_the_end_of_48_px(self):
        board = mission.Storyboard(self.painted, Image.new("RGB", (320, 240), (9, 7, 5)), 48)
        with mock.patch.object(mission, "stacked", lambda rows: [label for label, _ in rows]):
            self.assertEqual(["a round's start: the child is active, task 1 wants the fireman",
                              "the fireman holds the ladder: task 2 wants the child",
                              "the child at its first pose 86 px up or more: the round's end"], board.image())

    def test_the_storyboards_name_has_its_height_unless_it_is_96_px(self):
        self.assertEqual(["storyboard.png", "storyboard.png", "storyboard-64.png"],
                         [mission.storyboard_name(), mission.storyboard_name(96), mission.storyboard_name(64)])

    def test_the_image_is_the_three_frames_at_twice_the_size_under_their_labels(self):
        image = self.board.image()
        self.assertEqual((640 + 20, 3 * (480 + 28) + 10), image.size)
        frame = self.board.frame(0)
        self.assertEqual((320, 240), frame.size)
        self.assertEqual(moves.Ladder.COLOUR, frame.getpixel((111, 214)))  # the ladder's foot, under no figure


class StoryboardMainTest(unittest.TestCase):
    """main's --storyboard on stand-ins, so no CMU file is read and no scene is drawn: the capture is a word, each row's
    pictures are StandPictures that note the height they were painted at (None: none), and the storyboard notes its
    height and saves a small picture."""

    def setUp(self):
        self.painted_at, self.drawn_at = [], []
        test = self

        class Board:
            def __init__(self, painted, street, height=None):
                test.drawn_at.append(height)

            def image(self):
                return Image.new("RGB", (2, 2))

        def pictures(row, capture, height=None):
            self.painted_at.append(height)
            return StandPictures(row, (3, 4), 2)

        for patch in (mock.patch.object(mission.mocap, "open_capture", lambda parser, folder, cycles: "a capture"),
                      mock.patch.object(mission.Row, "pictures", pictures),
                      mock.patch.object(mission, "Storyboard", Board)):
            patch.start()
            self.addCleanup(patch.stop)

    def saved(self, *argv):
        """The files that main with --storyboard and argv saves in a new folder."""
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(mission.main(["--storyboard", folder] + list(argv)))
            return os.listdir(folder)

    def test_a_height_paints_the_storyboard_at_it_and_names_its_file_by_it(self):
        self.assertEqual(["storyboard-64.png"], self.saved("--height", "64"))
        self.assertEqual(([None] * 6 + [64] * 4, [64]), (self.painted_at, self.drawn_at))  # the count's rows first

    def test_a_bare_storyboard_is_96_px_and_storyboard_png(self):
        self.assertEqual(["storyboard.png"], self.saved())
        self.assertEqual(([None] * 6 + [96] * 4, [96]), (self.painted_at, self.drawn_at))

    def test_a_height_that_is_not_one_of_the_four_exits_2_and_paints_nothing(self):
        for value in ("200", "72", "x"):
            with self.subTest(height=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as stop:
                    self.saved("--height", value)
                self.assertEqual((2, [], []), (stop.exception.code, self.painted_at, self.drawn_at))

    def test_the_heights_are_48_64_80_and_96_px(self):
        self.assertEqual((48, 64, 80, 96), mission.HEIGHTS)


if __name__ == "__main__":
    unittest.main()
