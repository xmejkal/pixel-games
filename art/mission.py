"""The first mission's pictures, counted (P924): do the whole pictures of the first mission of the figures game
(P900) stay under the PO's pass line? It is in no game and in no art set: art/paint.py does not call it, and it writes
no pack.

The rows are the PO's words of 2026-11-19: "the fireman and the child. The fireman moves to the wall and holds a
ladder, then I switch to the child and the child climbs." A row is one character's cycle of art/mocap.py and the
action it shows in the mission. His words name three actions and no gait: the run is the fireman's gait in
detailed.CAST. They name no way for the child to reach the ladder and no idle cycle, so those rows are marked as not
named. A placeholder (temporary art that stands for art not made yet, https://en.wikipedia.org/wiki/Programmer_art) is
a captured cycle painted in place of a motion that nobody captured: the spray's stance, both arms held out in front,
for the hold of the ladder and for a figure that stands idle. A placeholder row weighs its cycle's poses, and the real
motion can take more or fewer. The wave, the other standing loop, is no placeholder: at 96 px the painter's box cuts
the fireman's raised arm.

Not in the count: a turn (every row holds both facings), the ladder (the Mac clip of art/moves.py draws it as lines,
and how the board draws it is open) and any other picture of the mission, such as the wall. The count says nothing
about the frame rate.

Run from the repository root: python3 art/mission.py [--out DIR] [--storyboard DIR] prints a line a row with its box
and its bytes, the street's line, the bytes of a pack with only the rows that his words name and of one with every row,
and what the pass line leaves beside the pack, or by how much the pack is over it. With --out it writes
mission-sheet.png, each row's poses, for the eye to judge the placeholders. With --storyboard it writes storyboard.png,
the set mission's scene at three moments (below). It needs the CMU files of the rows' cycles in the --cmu folder
(mocap.CMU_DIR when none is given): without one of them it paints nothing and exits 2.

The set mission (P906): the pictures of the ladder mission for probe906_ladder.py, the walking skeleton of P900. It is
in no ART_SETS: art/paint.py does not write it, and no pack of it is committed. painted(capture) paints its four
motions, the first four rows of MISSION; write(folder, painted) writes its pack and an index of that pack alone, as
art/figures.py's write does; numbers(painted) answers what the probe's board part cannot derive, as plain literals for
the probe's copy. Its pictures, in their order: mission_night (Rescue's street, not keyed), mission_ladder, then for
each motion mission_<figure>_<motion>_r<pose> and _l<pose>, each keyed. The hold keeps one pose, the spray's first:
the hose ready, as Rescue's fireman stands (games/rescue.py, Rescue.fireman_picture).
"""

import argparse
import math
import os
import sys
from collections import namedtuple

from PIL import Image, ImageDraw, ImageFont

import mocap
from artset import ArtSet, Painting
from detailed import CHILD, FIREMAN, SEED, TALL, Pictures, on_dark
from export import HEADER, Packs, committed_index, stacked, write_index, write_packs
from moves import Ladder, MovePictures
from sets.rescue import read_committed

# bytes: the PO's pass line for the pack (D28 of P900's discovery). It is the one pack size that the board loaded, into
# a pool made as big as the pack (logs/run-p904-2c.log, line 14), and no limit of the board's memory
PASS_LINE = 2464000
STREET = "rescue_night"  # the committed picture the mission plays on, as the set figures (art/figures.py)
NO_HOLD = "no hold is captured: the spray's stance, both arms held out in front"
NO_IDLE = "no idle is captured: the spray's stance, a standing loop"


class Row(namedtuple("Row", "character cycle action said placeholder", defaults=(True, None))):
    """One row of the count: a character (a detailed.Character), its cycle (a name in mocap.CYCLES, mocap.CROWD or
    mocap.MOVES) and the action that the cycle shows in the mission. said: the PO's words name the action.
    placeholder: why the cycle stands for a motion that nobody captured, or None."""

    def pictures(self, capture, height=TALL):
        """The row's pictures at height px. A move of mocap.MOVES is painted with its poses snapped to the floor
        (moves.MovePictures), as a game places it by its travel; any other cycle's poses are the capture's."""
        maker = MovePictures if mocap.named(self.cycle) in mocap.MOVES else Pictures
        return maker(capture, height, character=self.character, cycle_name=self.cycle)


MISSION = (
    Row(FIREMAN, "run", "moves to the wall"),
    Row(FIREMAN, "spray", "holds a ladder", placeholder=NO_HOLD),
    Row(CHILD, "climb", "climbs"),
    Row(CHILD, "child", "runs to the ladder", said=False),
    Row(FIREMAN, "spray", "stands idle", said=False, placeholder=NO_IDLE),
    Row(CHILD, "spray", "stands idle", said=False, placeholder=NO_IDLE),
)


def row_line(row, pictures):
    """A row's line: its character, cycle and trial, its action, its box and its bytes with both facings, then what
    marks it: not named, a placeholder."""
    w, h = pictures.size
    line = "%s's %s (%s), %s: %d poses of %d by %d px, %d bytes with both facings" % (
        row.character.name, row.cycle, pictures.cycle.source(), row.action, len(pictures.pictures), w, h,
        pictures.size_bytes())
    if not row.said:
        line += "; not named by the PO's words"
    if row.placeholder:
        line += "; a placeholder: " + row.placeholder
    return line


class MissionPack:
    """The mission's pack as the count sees it, never written: a pack's header (export.HEADER), the street once, as
    RGB565, and each row's pictures in both facings. painted: (row, its pictures) each, in the rows' order. street:
    the street's size, (w, h) in px."""

    def __init__(self, painted, street):
        self.painted, self.street = painted, street

    def street_bytes(self):
        w, h = self.street
        return w * h * 2

    def said_bytes(self):
        """The bytes of a pack with only the rows that the PO's words name."""
        return HEADER + self.street_bytes() + sum(p.size_bytes() for row, p in self.painted if row.said)

    def size(self):
        """The bytes of the pack with every row."""
        return HEADER + self.street_bytes() + sum(p.size_bytes() for _, p in self.painted)

    def left(self, line=PASS_LINE):
        """The bytes from the pack up to a line of line bytes: under 0, the pack is over the line."""
        return line - self.size()

    def lines(self, line=PASS_LINE):
        """The lines main prints: each row's (row_line), the street's, the two sums and the line with what is left."""
        w, h = self.street
        left = self.left(line)
        return [row_line(row, p) for row, p in self.painted] + [
            "the street: %d by %d px, %d bytes" % (w, h, self.street_bytes()),
            "the rows that the PO's words name, the street and the pack's header of %d bytes: %d bytes" % (
                HEADER, self.said_bytes()),
            "every row, the street and the header: %d bytes" % self.size(),
            "the pass line: %d bytes; the pack %s %d bytes" % (
                line, "leaves" if left >= 0 else "is over by", abs(left))]


class MissionSheet:
    """mission-sheet.png: a strip a row of a MissionPack, the row's poses facing right side by side on the street's
    dark, under a label with its character, action and cycle, and a placeholder marked."""

    def __init__(self, pack):
        self.pack = pack

    def rows(self):
        """Each row's label and strip."""
        return [("%s %s (%s)%s" % (row.character.name, row.action, row.cycle,
                                   ", a placeholder" if row.placeholder else ""), on_dark(p.pictures))
                for row, p in self.pack.painted]

    def image(self):
        return stacked(self.rows())


# --- the set mission (P906) --------------------------------------------------------------------------------------

SET = "mission"  # the set's name: its pack's, its index's and the start of each picture's
# each motion of the set: its figure, its motion, the row of MISSION that paints it, and the poses it keeps (None: all)
MOTIONS = (("fireman", "run", MISSION[0], None), ("fireman", "hold", MISSION[1], 1), ("child", "run", MISSION[3], None),
           ("child", "climb", MISSION[2], None))

# The places, in screen px: start values, set by eye on docs/screenshots/p906/storyboard.png, and the one spot to change
# them. A figure's place is the column of its pivot, its hips on the soles' row (detailed.Pictures.pivot). Both figures
# face left at a round's start, toward the ladder.
FEET = 214  # the row the soles stand on (games/rescue.py's FEET)
LADDER_FOOT = 111  # the ladder's foot on the soles' row
LADDER_TOP = 96  # the ladder's top row: the station's roof at its right corner, x 80 (art/sets/rescue.py, paint_station)
START = (220, 282)  # each figure's place at a round's start, the fireman first
HOLD_PLACE = 115  # the fireman's place by the ladder: in the hold his near hand is on the rail
FOOT_PLACE = 117  # the child's place at the ladder's foot: in the climb's first pose its toes are on the rail
END_UP = 54  # px: the climb ends at its first pose this far up or more, the child's head over the roof's edge
MARK_HOLD = (115, 222)  # the yellow mark's middle at the fireman's place: on the street under his feet
MARK_ROOF = (80, 88)  # the yellow mark's middle at the roof's edge: over the station's right corner
STAND = {"fireman": 8, "child": 0}  # each figure's standing picture: the pose of its run with the feet together


def painted(capture, height=TALL):
    """The set's motions painted from capture at height px: {(figure, motion): its row's pictures} in MOTIONS' order.
    The climb is a moves.MovePictures, each other motion a detailed.Pictures (Row.pictures)."""
    return {(figure, motion): row.pictures(capture, height) for figure, motion, row, _ in MOTIONS}


def capture(parser, folder=mocap.CMU_DIR):
    """The CMU files of the set's motions in folder, or the parser's error that names the files it lacks (exit 2)."""
    return mocap.open_capture(parser, folder, [mocap.named(row.cycle) for _, _, row, _ in MOTIONS])


def ladder(advance):
    """The ladder's picture and its top left on the screen: moves.Ladder from (LADDER_FOOT, FEET) up to LADDER_TOP, at
    the slant of advance, the climb's (forward, up) a play, leaning back toward the station, with a rung every half
    advance from the foot (moves.MoveClip.ladder's slant and step), cut to the columns it uses. Keyed: the wood on
    clear."""
    af, au = advance
    img = Image.new("RGBA", (320, FEET - LADDER_TOP + 1), (0, 0, 0, 0))
    Ladder((LADDER_FOOT, FEET - LADDER_TOP), (-af, au), math.hypot(af, au) / 2).draw(img)
    x0, _, x1, _ = img.getchannel("A").getbbox()
    return img.crop((x0, 0, x1, img.height)), (x0, LADDER_TOP)


def paint_set(painted):
    """The set's Painting: the street, the ladder, then each motion's kept poses facing right, then facing left."""
    pictures = {SET + "_night": (read_committed([STREET])[STREET], False),
                SET + "_ladder": (ladder(painted["child", "climb"].advance)[0], True)}
    for figure, motion, _, keep in MOTIONS:
        p = painted[figure, motion]
        for side, poses in (("r", p.pictures), ("l", p.left)):
            pictures.update({"%s_%s_%s_%s%d" % (SET, figure, motion, side, i): (img, True)
                             for i, img in enumerate(poses[:keep])})
    return Painting(pictures)


def write(folder, painted):
    """The set's pack as folder/packs/mission.pak and its index as folder/art_index.py, by the product's writers on a
    set that owns the index's layers (it has none; write_index asks for one owner), as art/figures.py's write. The
    folder is laid out as the board's root, so the index's path to the pack holds in both. Answers the two paths."""
    art_set = ArtSet(SET, SEED, lambda: paint_set(painted), index_layers=True)
    paintings = {SET: art_set.paint()}
    packs = Packs([art_set], paintings)
    os.makedirs(os.path.join(folder, "packs"), exist_ok=True)
    write_packs(packs, os.path.join(folder, "packs"))
    index = os.path.join(folder, "art_index.py")
    write_index([art_set], paintings, packs, index)
    return os.path.join(folder, "packs", SET + ".pak"), index


def gait(run):
    """A run's stride in px a cycle and its speed in px a second, both as captured: detailed.RunPictures' numbers, for
    a run that a Row painted as detailed.Pictures."""
    stride = round(run.capture.stride(run.cycle) * run.painter.PX * run.character.proportions.leg)
    return stride, stride * run.cycle.fps / run.capture.loop(run.cycle)[1]


def numbers(painted):
    """What the probe's board part cannot derive, as plain ints, tuples and dicts, so repr gives its copy a literal
    (probe906_ladder.py's NUMBERS): each run's stride and speed (rounded to a whole px a second), each motion's pivot
    column facing right, each standing pose, the climb's (ms a pose, (forward, up) of each pose from a play's start,
    (forward, up) a play), the ladder's top left, and the places: start, place (the fireman's by the ladder and the
    child's at its foot), end (END_UP) and mark (MARK_HOLD and MARK_ROOF)."""
    gaits = {figure: gait(painted[figure, "run"]) for figure in ("fireman", "child")}
    climb = painted["child", "climb"]
    return {"stride": {figure: stride for figure, (stride, _) in gaits.items()},
            "speed": {figure: round(speed) for figure, (_, speed) in gaits.items()},
            "pivot": {key: p.pivot[0] for key, p in painted.items()},
            "stand": dict(STAND),
            "climb": (round(climb.pose_ms), tuple(climb.travel), climb.advance),
            "ladder": ladder(climb.advance)[1],
            "start": START, "place": (HOLD_PLACE, FOOT_PLACE), "end": END_UP, "mark": (MARK_HOLD, MARK_ROOF)}


class Storyboard:
    """storyboard.png (P906): the set's scene at three moments, put together from its pictures at the places above, for
    the eye that sets them: a round's start, the fireman holding the ladder at his place, and the child at the climb's
    first pose END_UP px up or more. Each frame has the bar's three rows with the task block, the white arrow over the
    active figure and the yellow mark, as probe906_ladder.py draws them. The bar's words are in PIL's default font,
    not the box's 8x8 one. painted: painted()'s pictures; street: the street's picture."""

    BAR = ("1 FIREMAN: stick DOWN to ladder, FIRE", "2 CHILD: stick UP to ladder, UP climbs", "PICK twice: quit")
    LABELS = ("a round's start: the child is active, task 1 wants the fireman",
              "the fireman holds the ladder: task 2 wants the child",
              "the child at its first pose %d px up or more: the round's end" % END_UP)
    WHITE, YELLOW, DARK, RIM = (255, 255, 255), (250, 220, 40), (30, 30, 40), (0, 0, 0)  # games/gfx.py's, BLACK
    GAP = 6  # px from the arrow's tip, and the mark's lowest row, to the top of the picture under it
    # each shape's rows, from the top: probe906_ladder.py's ARROW and MARK (a Mac test pins them alike). Each has a dark
    # rim of 1 px all round, drawn first, so it reads on the street's lit windows and on the sky
    ARROW = (7, 5, 3, 1)  # the white arrow: its tip lowest
    MARK = (1, 3, 5, 7, 9, 7, 5, 3, 1)  # the yellow mark: a diamond 9 px high and wide

    def __init__(self, painted, street):
        self.painted, self.street = painted, street

    def placed(self, figure, motion, pose, x, up=0):
        """A picture of the figure facing left with its pivot on column x, its soles up px over FEET: (img, left, top)."""
        p = self.painted[figure, motion]
        w, h = p.size
        return p.left[pose], x - (w - 1 - p.pivot[0]), FEET - up - h + 1

    def end(self):
        """The climb's first pose END_UP px up or more: its pose and its (forward, up) from the foot."""
        climb = self.painted["child", "climb"]
        (af, au), plays = climb.advance, 0
        while True:
            for pose, (f, u) in enumerate(climb.travel):
                if plays * au + u >= END_UP:
                    return pose, (plays * af + f, plays * au + u)
            plays += 1

    def moments(self):
        """Each frame's figures (the fireman's, then the child's (img, left, top)), the column of each one's place, its
        active figure (0 the fireman, 1 the child), its task, and its mark: ("over", figure) or ("at", (x, y))."""
        fireman, child = (self.placed(figure, "run", STAND[figure], x) for figure, x in zip(("fireman", "child"), START))
        hold = self.placed("fireman", "hold", 0, HOLD_PLACE)
        pose, (f, u) = self.end()
        return [{"figures": (fireman, child), "columns": START, "active": 1, "task": 1, "mark": ("over", 0)},
                {"figures": (hold, child), "columns": (HOLD_PLACE, START[1]), "active": 0, "task": 2,
                 "mark": ("over", 1)},
                {"figures": (hold, self.placed("child", "climb", pose, FOOT_PLACE - f, u)),
                 "columns": (HOLD_PLACE, FOOT_PLACE - f), "active": 1, "task": 2, "mark": ("at", MARK_ROOF)}]

    def frame(self, k):
        """Moment k as the box shows it: 320 by 240 px."""
        moment = self.moments()[k]
        img = self.street.convert("RGB")
        ladder_img, at = ladder(self.painted["child", "climb"].advance)
        img.paste(ladder_img, at, ladder_img)
        for picture, x, y in moment["figures"]:  # the fireman first, the child in front of him
            img.paste(picture, (x, y), picture)
        draw = ImageDraw.Draw(img)
        tops = [(x, figure[2]) for x, figure in zip(moment["columns"], moment["figures"])]
        self.over(draw, tops[moment["active"]], self.ARROW, self.WHITE)
        kind, where = moment["mark"]
        if kind == "over":
            self.over(draw, tops[where], self.MARK, self.YELLOW)
        else:
            self.rows(draw, where[0], where[1] - len(self.MARK) // 2, self.MARK, self.YELLOW)
        draw.rectangle((0, 0, 319, 23), fill=self.DARK)
        font = ImageFont.load_default(size=8)
        for row, words in enumerate(self.BAR):
            draw.text((10, 8 * row), words, fill=self.WHITE, font=font)
        task_y = 8 * (moment["task"] - 1) + 1
        draw.rectangle((2, task_y, 7, task_y + 5), fill=self.YELLOW)  # the task block
        return img

    def over(self, draw, top, widths, colour):
        """Rows of widths on column x of top, the last one GAP px over the top row of the picture under it."""
        x, y = top
        self.rows(draw, x, y - self.GAP - len(widths) + 1, widths, colour)

    def rows(self, draw, x, y, widths, colour):
        """Rows of widths from row y down, each centred on column x, over its rim: first, for each row, a dark rect
        1 px wider on both sides and 1 px higher and lower, as the probe's shape draws it."""
        for k, w in enumerate(widths):
            draw.rectangle((x - w // 2 - 1, y + k - 1, x + w // 2 + 1, y + k + 1), fill=self.RIM)
        for k, w in enumerate(widths):
            draw.rectangle((x - w // 2, y + k, x + w // 2, y + k), fill=colour)

    def image(self):
        """The three frames at twice the size, one under the other, each under its label."""
        return stacked([(label, self.frame(k).resize((640, 480), Image.Resampling.NEAREST))
                        for k, label in enumerate(self.LABELS)])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count the bytes of the first mission's pictures at %d px against "
                                                 "the pass line of %d bytes." % (TALL, PASS_LINE))
    parser.add_argument("--out", metavar="DIR", help="the folder mission-sheet.png is written to (none: no sheet)")
    parser.add_argument("--storyboard", metavar="DIR", help="the folder storyboard.png is written to (none: none)")
    parser.add_argument("--cmu", default=mocap.CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    args = parser.parse_args(argv)
    capture = mocap.open_capture(parser, args.cmu, [mocap.named(row.cycle) for row in MISSION])
    pack = MissionPack([(row, row.pictures(capture)) for row in MISSION], committed_index()["ART"][STREET][:2])
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        MissionSheet(pack).image().save(os.path.join(args.out, "mission-sheet.png"))
    if args.storyboard:  # the set's motions are the count's first four rows: painted once
        rows = dict(pack.painted)
        os.makedirs(args.storyboard, exist_ok=True)
        Storyboard({(figure, motion): rows[row] for figure, motion, row, _ in MOTIONS},
                   read_committed([STREET])[STREET]).image().save(os.path.join(args.storyboard, "storyboard.png"))
    print("\n".join(pack.lines()))


if __name__ == "__main__":
    sys.exit(main())
