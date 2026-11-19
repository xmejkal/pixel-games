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

Run from the repository root: python3 art/mission.py [--out DIR] prints a line a row with its box and its bytes, the
street's line, the bytes of a pack with only the rows that his words name and of one with every row, and what the pass
line leaves beside the pack, or by how much the pack is over it. With --out it writes mission-sheet.png, each row's
poses, for the eye to judge the placeholders. It needs the CMU files of the rows' cycles in the --cmu folder
(mocap.CMU_DIR when none is given): without one of them it paints nothing and exits 2.
"""

import argparse
import os
import sys
from collections import namedtuple

import mocap
from detailed import CHILD, FIREMAN, TALL, Pictures, on_dark
from export import HEADER, committed_index, stacked
from moves import MovePictures

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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count the bytes of the first mission's pictures at %d px against "
                                                 "the pass line of %d bytes." % (TALL, PASS_LINE))
    parser.add_argument("--out", metavar="DIR", help="the folder mission-sheet.png is written to (none: no sheet)")
    parser.add_argument("--cmu", default=mocap.CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    args = parser.parse_args(argv)
    capture = mocap.open_capture(parser, args.cmu, [mocap.named(row.cycle) for row in MISSION])
    pack = MissionPack([(row, row.pictures(capture)) for row in MISSION], committed_index()["ART"][STREET][:2])
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        MissionSheet(pack).image().save(os.path.join(args.out, "mission-sheet.png"))
    print("\n".join(pack.lines()))


if __name__ == "__main__":
    sys.exit(main())
