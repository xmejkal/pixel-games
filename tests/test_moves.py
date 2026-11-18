"""The moves (P904 step 2b): the jump, the forward jump and the climb of art/mocap.py's MOVES, and art/moves.py's
pictures, sheet and clip of them. On a stand-in capture whose joints the tests compute, so the loop, the poses, the
root motion and the rise run on known numbers, and on stand-in pictures: these hold without the CMU files. And, only
when the CMU files are downloaded, the moves painted from them. Run from the repository root: python3 -m unittest
discover tests."""

import argparse
import contextlib
import dataclasses
import functools
import io
import math
import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names
sys.path.insert(0, os.path.join(REPO, "tests"))

import detailed  # noqa: E402
import mocap  # noqa: E402
import moves  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402
from test_detailed_figure import opaque_rows, standing  # noqa: E402

JUMP, FORWARD_JUMP, CLIMB = (next(c for c in mocap.MOVES if c.name == name) for name in ("jump", "forward jump", "climb"))
JUMP_FRAMES, AHEAD, FLIGHT = 23, 0.02, 0.2  # the jumper's frames, its root's way forward a frame, its highest lift
CLIMB_FRAMES, PERIOD, RISE, LEAN = 300, 288, 0.3, 0.1  # the climber's frames, its loop, and its way up and forward a loop
WAVE, DRIFT = 0.05, 0.02  # how far the climber's hands wave, and how far its left thumb drifts forward a loop
SMALL = 48  # px: the stand-in moves are painted at this height, so the tests run fast


class Height:
    """A stand-in skeleton: one body height is 1."""

    def height(self):
        return 1.0


def flight(t):
    """The jumper's lift at frame t: off the floor from frame 6 to 16, highest at 11."""
    return FLIGHT * max(0.0, 1 - abs(t - 11) / 5)


def jumper(t):
    """The jumper's side view at frame t: the standing pose lifted by flight(t)."""
    return {n: (f, u + flight(t), d) for n, (f, u, d) in standing().items()}


def climber(t):
    """The climber's side view at frame t: the standing pose risen RISE a loop, the hands waving four times a loop (one
    a quarter wave after the other, so no start of a loop but its period brings them back), and the left thumb drifting
    DRIFT forward a loop: the loop's ends are DRIFT apart there and nowhere else."""
    w = 2 * math.pi * 4 * t / PERIOD
    out = {n: (f, u + RISE * t / PERIOD, d) for n, (f, u, d) in standing().items()}
    for joint, wave in (("lhand", math.sin(w)), ("rhand", math.cos(w))):
        f, u, d = out[joint]
        out[joint] = (f, u + WAVE * wave, d)
    f, u, d = out["lthumb"]
    out["lthumb"] = (f + DRIFT * t / PERIOD, u, d)
    return out


def in_3d(view, x):
    """A side view as one frame's 3D joints (Y up), the root at x and facing along x; the capture adds the nose."""
    return {n: (x + f, u, d) for n, (f, u, d) in view.items() if n != "nose"}


def stand_in():
    """A capture whose spans of the jump and the climb are the jumper's and the climber's frames: no file is read."""
    capture = mocap.Capture("stand-in")
    capture.spans[(JUMP.trial, JUMP.frames)] = (Height(), [in_3d(jumper(t), AHEAD * t) for t in range(JUMP_FRAMES)],
                                                0.0)
    capture.spans[(CLIMB.trial, CLIMB.frames)] = (Height(), [in_3d(climber(t), LEAN * t / PERIOD)
                                                             for t in range(CLIMB_FRAMES)], 0.0)
    return capture


@functools.lru_cache(maxsize=None)
def stand_in_moves():
    """The stand-in's jump, its climb, and its jump with legs half as long, painted at SMALL px once for all tests."""
    capture = stand_in()
    half = dataclasses.replace(detailed.FIREMAN, proportions=detailed.Proportions(leg=0.5))
    return (moves.MovePictures(capture, SMALL, detailed.NoRim(), cycle_name="jump"),
            moves.MovePictures(capture, SMALL, detailed.NoRim(), cycle_name="climb"),
            moves.MovePictures(capture, SMALL, detailed.NoRim(), character=half, cycle_name="jump"))


def index_of(pictures, img):
    """The index of the picture that is img itself, not one equal to it."""
    return next(i for i, picture in enumerate(pictures) if picture is img)


class PoseTest(unittest.TestCase):
    def assertPose(self, expected, pose):
        self.assertEqual(set(expected), set(pose))
        for joint in expected:
            for a, b in zip(expected[joint], pose[joint]):
                self.assertAlmostEqual(a, b, places=9, msg=joint)


class OneShotTest(PoseTest):
    """The jump on the stand-in: its loop is its whole span, and pose i is frame 2i of it."""

    def setUp(self):
        self.capture = stand_in()

    def test_its_loop_is_its_whole_span(self):
        self.assertEqual((0, JUMP_FRAMES - 1), self.capture.loop(JUMP))

    def test_pose_0_and_the_last_pose_are_the_spans_ends(self):
        poses = self.capture.poses(JUMP)
        self.assertEqual(12, len(poses))
        self.assertPose(jumper(0), poses[0])
        self.assertPose(jumper(JUMP_FRAMES - 1), poses[-1])

    def test_a_pose_in_flight_keeps_its_height(self):
        pose = self.capture.poses(JUMP)[5]
        self.assertPose(jumper(10), pose)
        self.assertAlmostEqual(flight(10), min(pose[n][1] for n in ("ltoes", "rtoes", "lfoot", "rfoot")))

    def test_the_root_motion_is_the_roots_path_with_its_last_two_numbers_equal(self):
        motion = self.capture.root_motion(JUMP)
        self.assertEqual(13, len(motion))
        for i, ahead in enumerate(motion):
            with self.subTest(pose=i):
                self.assertAlmostEqual(AHEAD * min(2 * i, JUMP_FRAMES - 1), ahead)
        self.assertEqual(motion[-2], motion[-1])

    def test_it_does_not_rise(self):
        self.assertEqual(0, self.capture.rise(JUMP))


class RisingTest(PoseTest):
    """The climb on the stand-in: it rises RISE a loop of PERIOD frames, and its loop's ends are DRIFT apart at the
    left thumb."""

    def setUp(self):
        self.capture = stand_in()

    def test_the_loop_has_the_climbers_period_and_rises_its_rise(self):
        self.assertEqual(PERIOD, self.capture.loop(CLIMB)[1])
        self.assertAlmostEqual(RISE, self.capture.rise(CLIMB))

    def test_a_plain_cycle_on_the_same_climber_finds_another_period(self):
        """Without the end lowered by the rise, every joint's rise hides the pose: a shorter loop looks closer."""
        plain = mocap.Cycle("plain climb", CLIMB.trial, CLIMB.fps, CLIMB.frames, CLIMB.period, CLIMB.poses)
        self.assertNotEqual(PERIOD, self.capture.loop(plain)[1])

    def test_each_pose_is_the_raw_pose_less_its_share_of_the_gap(self):
        start = self.capture.loop(CLIMB)[0]
        poses = self.capture.poses(CLIMB)
        self.assertEqual(12, len(poses))
        for i, pose in enumerate(poses):
            with self.subTest(pose=i):
                raw = climber(start + i * PERIOD // 12)
                f, u, d = raw["lthumb"]
                self.assertPose(dict(raw, lthumb=(f - DRIFT * i / 12, u, d)), pose)

    def test_the_root_motion_is_the_climbers_forward_path(self):
        motion = self.capture.root_motion(CLIMB)
        self.assertEqual(13, len(motion))
        for i, ahead in enumerate(motion):
            with self.subTest(pose=i):
                self.assertAlmostEqual(LEAN * i / 12, ahead)

    def test_a_loop_does_not_rise(self):
        capture = stand_in()
        capture.spans[("09_01", (0, 148))] = (Height(), [in_3d(climber(t), 0.0) for t in range(148)], 0.0)
        self.assertEqual(0, capture.rise(mocap.CYCLES[0]))


class MissingTest(unittest.TestCase):
    """The files a capture asks for, and open_capture, on an empty folder."""

    def test_with_no_argument_it_asks_for_the_files_of_the_cycles_and_the_crowd_only(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = mocap.Capture(folder).missing()
        self.assertIn("09_01.amc", missing)
        self.assertIn("13_27.amc", missing)
        self.assertEqual([], [n for n in ("13_11.amc", "13_33.amc", "13_39.amc") if n in missing])

    def test_the_moves_ask_for_subject_13_and_their_three_trials(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(["13.asf", "13_11.amc", "13_33.amc", "13_39.amc"], mocap.Capture(folder).missing(mocap.MOVES))

    def test_open_capture_ends_with_the_parsers_error_naming_a_missing_file(self):
        parser = argparse.ArgumentParser(prog="moves")
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit):
                detailed.open_capture(parser, folder, mocap.MOVES)
        self.assertIn("13_39.amc", err.getvalue())

    def test_open_capture_gives_the_capture_when_the_files_are_there(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in mocap.Capture(folder).missing(mocap.MOVES):
                open(os.path.join(folder, name), "w").close()
            capture = detailed.open_capture(argparse.ArgumentParser(prog="moves"), folder, mocap.MOVES)
            self.assertEqual(folder, capture.folder)


class MovePicturesTest(unittest.TestCase):
    """The stand-in's moves painted at SMALL px."""

    @classmethod
    def setUpClass(cls):
        cls.jump, cls.climb, cls.half = stand_in_moves()

    def test_the_soles_are_on_the_last_row_in_every_pose_also_in_flight(self):
        for move in (self.jump, self.climb):
            for i, img in enumerate(move.pictures):
                with self.subTest(move=move.cycle.name, pose=i):
                    self.assertEqual(img.height - 1, opaque_rows(img)[-1])
        self.assertGreater(self.jump.travel[5][1], 0)

    def test_the_travel_holds_the_root_motion_and_the_lift(self):
        px = self.jump.painter.PX
        self.assertEqual([(round(AHEAD * min(2 * i, JUMP_FRAMES - 1) * px), round(flight(2 * i) * px)) for i in range(12)],
                         self.jump.travel)
        self.assertEqual((round(AHEAD * (JUMP_FRAMES - 1) * px), 0), self.jump.advance)

    def test_the_advance_holds_the_rise(self):
        px = self.climb.painter.PX
        self.assertEqual((round(LEAN * px), round(RISE * px)), self.climb.advance)
        self.assertEqual([round(RISE * i / 12 * px) for i in range(12)], [up for _, up in self.climb.travel])

    def test_a_leg_share_of_a_half_halves_the_forward_travel_only(self):
        px = self.jump.painter.PX
        self.assertEqual([round(AHEAD * min(2 * i, JUMP_FRAMES - 1) * px * 0.5) for i in range(12)],
                         [ahead for ahead, _ in self.half.travel])
        self.assertEqual([up for _, up in self.jump.travel], [up for _, up in self.half.travel])

    def test_a_one_shots_pose_lasts_its_span_over_its_poses_less_one_and_a_loops_its_period_over_its_poses(self):
        self.assertAlmostEqual((JUMP_FRAMES - 1) / 11 / JUMP.fps * 1000, self.jump.pose_ms)
        self.assertAlmostEqual(PERIOD / 12 / CLIMB.fps * 1000, self.climb.pose_ms)
        self.assertAlmostEqual(12 * self.climb.pose_ms, self.climb.play_ms)

    def test_the_pose_at_a_time_and_its_place_one_advance_further_each_play(self):
        move = self.climb
        (af, au), ms = move.advance, move.pose_ms
        for at, plays, index in ((0, 0, 0), (2.5 * ms, 0, 2), (move.play_ms + 0.5 * ms, 1, 0),
                                 (2 * move.play_ms + 3.5 * ms, 2, 3)):
            with self.subTest(ms=at):
                f, u = move.travel[index]
                self.assertEqual((index, (plays * af + f, plays * au + u)), move.pose_at(at))

    def test_the_pivot_is_the_hips_column_on_the_last_row(self):
        move = self.jump
        hips = move.painter.at((0.0, 0.0, 0.0))[0] - move.used[0]
        self.assertLessEqual(abs(move.pivot[0] - hips), 0.5)
        self.assertEqual(move.size[1] - 1, move.pivot[1])


class PlaysTest(unittest.TestCase):
    def test_the_nearest_whole_number_of_plays_and_never_none(self):
        for clip_ms, play_ms, plays in ((1000, 1000, 1), (1000, 450, 2), (1000, 300, 3), (1000, 260, 4),
                                        (7636, 1463.6, 5), (7636, 2408, 3), (100, 3000, 1)):
            with self.subTest(clip_ms=clip_ms, play_ms=play_ms):
                self.assertEqual(plays, moves.plays(clip_ms, play_ms))


class LadderTest(unittest.TestCase):
    def test_the_rail_follows_the_lean_and_the_rungs_are_the_step_apart(self):
        img = Image.new("RGB", (60, 120), (0, 0, 0))
        base, (af, au), step = (10, 110), (9, 25), 13.3
        moves.Ladder(base, (af, au), step).draw(img)
        on = [(x, y) for y in range(img.height) for x in range(img.width) if img.getpixel((x, y)) == moves.Ladder.COLOUR]
        rows = {}
        for x, y in on:
            rows.setdefault(y, []).append(x)
        rungs = {y for y, xs in rows.items() if len(xs) >= moves.Ladder.RUNG}
        rail = sorted(set(rows) - rungs)
        self.assertEqual(list(range(0, base[1] + 1)), sorted(rows))
        for y in rail:
            with self.subTest(row=y):
                self.assertLessEqual(abs(sum(rows[y]) / len(rows[y]) - (base[0] + (base[1] - y) * af / au)), 1)
        tops = sorted((y for y in rungs if y - 1 not in rungs), reverse=True)
        self.assertGreaterEqual(len(tops), 6)
        middles = [(sum(rows[y]) / len(rows[y]), y) for y in tops]
        for (x0, y0), (x1, y1) in zip(middles, middles[1:]):
            with self.subTest(rung=y0):
                self.assertLessEqual(abs(math.hypot(x1 - x0, y1 - y0) - step), 1)
        self.assertLessEqual(abs(math.hypot(middles[0][0] - base[0], middles[0][1] - base[1]) - step), 1)


class StandMove(moves.MovePictures):
    """A stand-in for MovePictures: one plain picture a pose, each its own shade of colour, and the travel, the advance,
    the time a pose and the toes given, so the sheet and the clip are tested with no CMU file."""

    def __init__(self, colour, travel, advance=(0, 0), pose_ms=100, size=(10, 20), toes=(0, -2), cycle=JUMP,
                 character=detailed.FIREMAN):
        self.cycle, self.character, self.size, self.toes = cycle, character, size, toes
        self.travel, self.advance, self.pose_ms, self.play_ms = travel, advance, pose_ms, len(travel) * pose_ms
        self.pictures = [Image.new("RGBA", size, colour + (10 + 20 * i, 255)) for i in range(len(travel))]
        self.left = [ImageOps.mirror(img) for img in self.pictures]
        self.pivot = (size[0] // 2, size[1] - 1)


class MoveSheetTest(unittest.TestCase):
    def setUp(self):
        self.moves = [StandMove((200, 0), [(0, 7 if i == 1 else 0) for i in range(12)]),
                      StandMove((0, 200), [(0, 0)] * 12, cycle=CLIMB)]

    def test_a_row_per_move_named_with_its_trial_its_box_and_its_bytes(self):
        rows = moves.MoveSheet(self.moves).rows()
        self.assertEqual(2, len(rows))
        for move, (label, _) in zip(self.moves, rows):
            with self.subTest(move=move.cycle.name):
                for part in (move.cycle.name, move.cycle.source(), "%d by %d px" % move.size,
                             "%d bytes" % move.size_bytes(), "%d ms" % round(move.pose_ms)):
                    self.assertIn(part, label)

    def test_a_pose_with_a_lift_of_k_px_stands_k_px_over_the_floor_line(self):
        move = self.moves[0]
        img, floor = moves.MoveSheet(self.moves).strip(move)
        w = move.size[0]
        for i in range(3):
            with self.subTest(pose=i):
                x = detailed.GAP + i * (w + detailed.GAP)
                colour = move.pictures[i].getpixel((0, 0))[:3]
                low = max(y for y in range(img.height) if img.getpixel((x, y)) == colour)
                self.assertEqual(floor - 1 - move.travel[i][1], low)
        self.assertEqual({moves.MoveSheet.FLOOR}, {img.getpixel((x, floor)) for x in range(img.width)})


class MoveClipTest(unittest.TestCase):
    """The clip on stand-in pictures: a crosser that jumps forward on the nearest row, a climber on the farthest, and a
    jumper between them."""

    def setUp(self):
        self.crosser = StandMove((200, 0), [(2 * i, 0) for i in range(12)], (24, 0), 50, (20, 30), cycle=FORWARD_JUMP)
        self.climber = StandMove((0, 200), [(0, i) for i in range(12)], (4, 12), 110, toes=(0, -3), cycle=CLIMB)
        self.jumper = StandMove((0, 0), [(0, 3 if 3 < i < 8 else 0) for i in range(12)], (1, 0), 70)
        self.street = Image.new("RGB", (moves.MoveClip.W, 240), (40, 40, 40))
        self.clip = moves.MoveClip([(self.crosser, 238, None), (self.climber, 200, 40), (self.jumper, 220, 150)],
                                   self.street)

    def test_the_farther_mover_is_pasted_first(self):
        places = self.clip.places(0)
        self.assertEqual([self.climber, self.jumper, self.crosser], [m for m, _, _ in self.clip.movers])
        self.assertEqual([0, 0, 0], [index_of(move.pictures, img) for (_, _, img), move
                                     in zip(places, (self.climber, self.jumper, self.crosser))])

    def test_the_ladder_is_under_the_climber(self):
        frame = self.clip.frames()[0]
        x, y, img = self.clip.places(0)[0]
        box = [(x + i, y + j) for j in range(img.height) for i in range(img.width)]
        under = [q for q in box if self.clip.ground.getpixel(q) == moves.Ladder.COLOUR]
        self.assertTrue(under)
        self.assertEqual({img.getpixel((0, 0))[:3]}, {frame.getpixel(q) for q in under})
        self.assertIn(moves.Ladder.COLOUR, {frame.getpixel((q[0], q[1] - img.height)) for q in box})

    def test_each_mover_plays_a_whole_number_of_times(self):
        """Its poses start at the first, end at the last, and go round as many times as its plays."""
        for k, (move, _, _) in enumerate(self.clip.movers):
            with self.subTest(move=move.cycle.name):
                shown = [index_of(move.pictures, self.clip.places(i)[k][2]) for i in range(self.clip.count)]
                self.assertEqual((0, len(move.pictures) - 1), (shown[0], shown[-1]))
                self.assertEqual(self.clip.plays[k] - 1, sum(1 for a, b in zip(shown, shown[1:]) if b < a))
                self.assertAlmostEqual(self.clip.count * detailed.FRAME_MS,
                                       self.clip.plays[k] * move.play_ms * self.clip.stretch[k])

    def test_the_crossers_picture_is_off_the_street_in_the_first_and_the_last_frame_with_the_least_plays(self):
        k = [m for m, _, _ in self.clip.movers].index(self.crosser)
        first, last = self.clip.places(0)[k], self.clip.places(self.clip.count - 1)[k]
        self.assertLessEqual(first[0] + first[2].width, 0)
        self.assertGreaterEqual(last[0], moves.MoveClip.W)
        fewer = self.clip.plays[k] - 1
        count = round(fewer * self.crosser.play_ms / detailed.FRAME_MS)
        self.assertLess(self.clip.at(self.clip.movers[k], fewer, count, count - 1)[0], moves.MoveClip.W)


class MoveLinesTest(unittest.TestCase):
    def test_each_number_in_a_line_is_its_sources(self):
        jump = StandMove((200, 0), [(0, 0)] * 12, pose_ms=122.4)
        climb = StandMove((0, 200), [(0, i) for i in range(12)], (4, 12), 110, toes=(0, -3), cycle=CLIMB)
        crosser = StandMove((0, 0), [(2 * i, 0) for i in range(12)], (24, 0), 50, (20, 30), cycle=FORWARD_JUMP)
        clip = moves.MoveClip([(climb, 200, 40), (crosser, 238, None)], Image.new("RGB", (moves.MoveClip.W, 240)))
        lines = moves.move_lines([jump, climb], clip)
        self.assertEqual(2 + 2 + 1, len(lines))
        for move, line in zip((jump, climb), lines):
            with self.subTest(move=move.cycle.name):
                for part in (move.cycle.name, "%d by %d px" % move.size, " %d bytes" % move.size_bytes(),
                             " %d ms" % round(move.pose_ms)):
                    self.assertIn(part, line)
        for (move, row, _), plays, stretch, line in zip(clip.movers, clip.plays, clip.stretch, lines[2:]):
            with self.subTest(mover=move.cycle.name):
                for part in (move.cycle.name, "row %d" % row, " %d plays" % plays, "%.3f" % stretch):
                    self.assertIn(part, line)
        self.assertIn("%d frames" % clip.count, lines[-1])


@functools.lru_cache(maxsize=None)
def captured():
    """The capture, the fireman's moves and the clip's movers painted from the CMU files, once for all the tests that
    read them; None without the files."""
    capture = mocap.Capture()
    if capture.missing(mocap.CYCLES + mocap.CROWD + mocap.MOVES):
        return None
    return (capture,) + moves.painted(capture)


class MovesFromCaptureTest(unittest.TestCase):
    """The moves painted from the CMU files: skipped without them, and a skip is not a pass."""

    @classmethod
    def setUpClass(cls):
        if captured() is None:
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.capture, cls.moves, cls.movers = captured()
        cls.by_name = {move.cycle.name: move for move in cls.moves}

    def test_each_move_has_twelve_poses_in_one_box_none_cut_and_each_left_picture_is_the_mirror(self):
        for move in self.moves + [m for m, _, _ in self.movers]:
            with self.subTest(character=move.character.name, move=move.cycle.name):
                self.assertEqual(12, len(move.pictures))
                self.assertEqual({move.size}, {img.size for img in move.pictures + move.left})
                x0, y0, x1 = move.used
                self.assertTrue(x0 > 0 and y0 > 0 and x1 < detailed.box(detailed.TALL)[0])
                for right, left in zip(move.pictures, move.left):
                    self.assertEqual(ImageOps.mirror(right).tobytes(), left.tobytes())

    def test_the_jump_starts_and_ends_on_the_floor_and_flies_in_the_middle(self):
        lifts = [up for _, up in self.by_name["jump"].travel]
        self.assertLessEqual(max(lifts[0], lifts[-1]), 2)
        self.assertGreaterEqual(max(lifts[1:-1]), 12)

    def test_the_forward_jump_goes_forward_and_flies(self):
        travel = self.by_name["forward jump"].travel
        self.assertGreaterEqual(min(b[0] - a[0] for a, b in zip(travel, travel[1:])), -1)
        self.assertTrue(50 <= travel[-1][0] <= 70)
        self.assertGreaterEqual(max(up for _, up in travel), 6)

    def test_the_climb_goes_up_and_forward_a_play_and_its_lift_never_falls_by_more_than_a_px(self):
        climb = self.by_name["climb"]
        (af, au), lifts = climb.advance, [up for _, up in climb.travel]
        self.assertTrue(5 <= af <= 14 and 20 <= au <= 30)
        ups = lifts + [lifts[0] + au]
        self.assertGreaterEqual(min(b - a for a, b in zip(ups, ups[1:])), -1)

    def test_the_runs_loop_is_where_it_was_before_the_search_moved_into_the_cycle(self):
        self.assertEqual((0, 88), self.capture.loop(mocap.CYCLES[0]))

    def test_in_the_clip_the_climbers_picture_is_inside_the_frame_in_every_frame(self):
        clip = moves.MoveClip(self.movers, detailed.Committed().street)
        k = [m.cycle.name for m, _, _ in clip.movers].index("climb")
        for i in range(clip.count):
            x, y, img = clip.places(i)[k]
            with self.subTest(frame=i):
                self.assertTrue(0 <= x and 0 <= y and x + img.width <= clip.W and y + img.height <= 240)


if __name__ == "__main__":
    unittest.main()
