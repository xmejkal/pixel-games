"""The moves at 96 px (P904 step 2b): the jump, the forward jump and the climb of art/mocap.py's MOVES, painted by
art/detailed.py's painter. It is in no game and in no art set: art/paint.py does not call it.

A play is one pass through a move's poses. Each pose is snapped: its lowest foot joint stands on the picture's last
row, and its lift, how far that joint was over the floor, goes into its travel instead, the px its picture goes from
the play's start (forward, the root motion scaled as a run's stride; up, the lift). The advance is the px from one
play's start to the next: the climb's goes up as well as forward.

Run from the repository root: python3 art/moves.py --out DIR writes moves-sheet.png (the fireman's twelve poses of
each move, each at its lift over a floor line) and moves.webp (a fireman climbing a ladder, a footballer and a child
jumping, and an acrobat jumping forward across Rescue's street, all at once), and prints each of the fireman's moves
with its box, its bytes and its time a pose, each mover's plays in the clip, and the clip's frames. It needs the CMU
files in mocap.CMU_DIR and paints nothing without them.
"""

import argparse
import math
import os
import sys

from PIL import Image, ImageDraw

import mocap
from detailed import (ACROBAT, CHILD, DARK, FIREMAN, FOOTBALLER, FRAME_MS, GAP, SEED, TALL, Committed, Pictures,
                      open_capture, write_clip)
from export import Sheet
from sets.rescue import snapped

MOVERS = ((FIREMAN, "climb", 200, 50), (FOOTBALLER, "jump", 216, 150), (CHILD, "jump", 228, 250),
          (ACROBAT, "forward jump", 238, None))  # character, move, the row its soles start on, its pivot's column


class MovePictures(Pictures):
    """A character's move (cycle_name: a name in mocap.MOVES): the Pictures of its snapped poses, and where each goes.
    lifts: each pose's lift, in body heights. travel: px (forward, up) that each pose's picture goes from the play's
    start. advance: px (forward, up) from one play's start to the next. pose_ms: the capture's time from one pose to
    the next, which a one-shot's last pose also lasts; play_ms: a play's. toes: the middle between the toe joints of
    pose 0, px from its pivot."""

    def __init__(self, capture, height, rim=None, seed=SEED, character=FIREMAN, cycle_name="jump"):
        super().__init__(capture, height, rim, seed, character, cycle_name)
        px, leg = self.painter.PX, character.proportions.leg  # forward as the run's stride, so the feet keep still
        motion = capture.root_motion(self.cycle)
        self.travel = [(round(ahead * px * leg), round(lift * px)) for ahead, lift in zip(motion, self.lifts)]
        self.advance = (round(motion[-1] * px * leg), round(capture.rise(self.cycle) * px))
        self.pose_ms = self.cycle.frame(1, capture.loop(self.cycle)[1]) * 1000 / self.cycle.fps
        self.play_ms = len(self.pictures) * self.pose_ms
        pose = character.proportions.fit(self.posed[0])
        (lx, ly), (rx, ry) = (self.painter.at(pose[n]) for n in ("ltoes", "rtoes"))
        x0, y0, _ = self.used
        self.toes = ((lx + rx) / 2 - x0 - self.pivot[0], (ly + ry) / 2 - y0 - self.pivot[1])

    def poses(self):
        """The capture's poses, each snapped: its lowest foot joint on the floor. It keeps them (posed) and each one's
        lift, the root's up before the snap less after it."""
        raw = self.capture.poses(self.cycle)
        self.posed = [snapped(pose) for pose in raw]
        self.lifts = [a["root"][1] - b["root"][1] for a, b in zip(raw, self.posed)]
        return self.posed

    def pose_at(self, ms):
        """The pose ms into the move, played again and again, and its place: the whole plays times the advance, plus
        its travel. The place changes only with the pose."""
        plays, index = divmod(int(ms // self.pose_ms), len(self.pictures))
        (f, u), (af, au) = self.travel[index], self.advance
        return index, (plays * af + f, plays * au + u)


def plays(clip_ms, play_ms):
    """The whole number of plays nearest to a clip's length, at least one."""
    return max(1, round(clip_ms / play_ms))


class Ladder:
    """A ladder seen from the side, drawn on a picture: one rail from its foot (base, a place) along a lean (px forward
    and up) to the picture's top, and a rung across it every step px along it from the foot."""

    COLOUR = (128, 96, 72)  # weathered wood: it shows on the street's dark and is no character's colour
    RAIL = 2  # the rail's width and a rung's thickness, px
    RUNG = 12  # a rung's length, px: a toe up to 6 px off the rail still stands on it

    def __init__(self, base, lean, step):
        self.base, self.lean, self.step = base, lean, step

    def draw(self, img):
        (bx, by), (af, au) = self.base, self.lean
        draw = ImageDraw.Draw(img)
        for y in range(round(by) + 1):
            x = round(bx + (by - y) * af / au - self.RAIL / 2)
            draw.line((x, y, x + self.RAIL - 1, y), fill=self.COLOUR)
        length, k = math.hypot(af, au), 1
        while by - k * self.step * au / length >= 0:
            x, y = bx + k * self.step * af / length, round(by - k * self.step * au / length)
            left = round(x - self.RUNG / 2)
            draw.rectangle((left, y, left + self.RUNG - 1, y + self.RAIL - 1), fill=self.COLOUR)
            k += 1


def move_line(move):
    """A move's trial, box, bytes with both facings and time a pose: the sheet's label and a line that main prints."""
    w, h = move.size
    return "%s's %s (%s): %d poses of %d by %d px, %d bytes with both facings, %d ms a pose" % (
        move.character.name, move.cycle.name, move.cycle.source(), len(move.pictures), w, h, move.size_bytes(),
        round(move.pose_ms))


class MoveSheet:
    """moves-sheet.png: a row per move, its poses side by side on the street's dark, each at its lift over the row's
    floor line, under a label with the trial, the box, the bytes and the time a pose."""

    FLOOR = (96, 80, 92)  # the floor line: lighter than the dark

    def __init__(self, moves):
        self.moves = moves

    def strip(self, move):
        """The move's poses on the dark, GAP px apart, each at its lift over the floor line, and the floor line's row."""
        w, h = move.size
        top = max(up for _, up in move.travel)
        strip = Image.new("RGB", (len(move.pictures) * (w + GAP) + GAP, h + top + 2 * GAP), DARK)
        floor = strip.height - GAP
        ImageDraw.Draw(strip).line((0, floor, strip.width - 1, floor), fill=self.FLOOR)
        for i, (img, (_, up)) in enumerate(zip(move.pictures, move.travel)):
            strip.paste(img, (GAP + i * (w + GAP), floor - h - up), img)
        return strip, floor

    def rows(self):
        """Each move's label and strip."""
        return [(move_line(move), self.strip(move)[0]) for move in self.moves]

    def image(self):
        rows = self.rows()
        sheet = Sheet(max(img.width for _, img in rows) + 20, sum(img.height + 28 for _, img in rows) + 10)
        y = 6
        for label, img in rows:
            y = sheet.put(label, img, 10, y) + 10
        return sheet.image


class MoveClip:
    """moves.webp's frames: the movers on Rescue's street, a frame of the game apart, each facing right, the farther
    pasted first. A mover is (pictures, row, column): a MovePictures, the row its soles stand on when it starts and
    the column its pivot starts at. The crosser, column None, starts with its picture just off the street's left edge,
    and the clip lasts the least whole number of its plays that takes its picture off the right edge by the last
    frame. Every other mover plays the whole number of times nearest to the clip's length, its time stretched to fill
    it. A mover that goes up climbs a ladder, drawn on the street (ground) before any mover. When the clip starts
    again, every mover starts its first play again from its start place."""

    W = 320

    def __init__(self, movers, street):
        self.movers = sorted(movers, key=lambda m: m[1])  # the farther first
        crosser = next(m for m in self.movers if m[2] is None)
        crossing, self.count = self.crossing(crosser)
        ms = self.count * FRAME_MS
        self.plays = [crossing if m is crosser else plays(ms, m[0].play_ms) for m in self.movers]
        self.stretch = [ms / (k * m[0].play_ms) for k, m in zip(self.plays, self.movers)]
        self.ground = street.copy()
        for mover in self.movers:
            if mover[0].advance[1] > 0:
                self.ladder(mover).draw(self.ground)

    def at(self, mover, plays, count, i):
        """Where a mover's picture is pasted at frame i of a clip of count frames over which it plays plays times (its
        pivot on its place), and the picture."""
        move, row, column = mover
        start = move.pivot[0] - move.size[0] if column is None else column
        index, (f, u) = move.pose_at(i * plays * move.play_ms / count)
        return start + f - move.pivot[0], row - u - move.pivot[1], move.pictures[index]

    def crossing(self, mover):
        """The crosser's plays, and the clip's frames for them."""
        for n in range(1, self.W + 1):
            count = max(1, round(n * mover[0].play_ms / FRAME_MS))
            if self.at(mover, n, count, count - 1)[0] >= self.W:
                return n, count
        raise ValueError("the crosser does not cross the street")

    def ladder(self, mover):
        """The ladder of a mover that goes up: its rail leans along the advance through the middle between the toes of
        pose 0, a rung lies under the lowest foot then and one every half advance, and its foot is a rung lower."""
        move, row, column = mover
        (f, u), (af, au) = move.travel[0], move.advance
        tx, ty = column + f + move.toes[0], row - u + move.toes[1]
        y = row - u + 1  # the row under the soles in pose 0
        x = tx + (ty - y) * af / au
        return Ladder((x - af / 2, y + au / 2), (af, au), math.hypot(af, au) / 2)

    def places(self, i):
        """Frame i's movers, the farthest first: (x, y, picture) each, (x, y) where the picture is pasted."""
        return [self.at(m, k, self.count, i) for m, k in zip(self.movers, self.plays)]

    def frames(self):
        out = []
        for i in range(self.count):
            frame = self.ground.copy()
            for x, y, img in self.places(i):
                frame.paste(img, (x, y), img)
            out.append(frame)
        return out


def move_lines(moves, clip):
    """The lines main prints: each move's (move_line), then each mover's plays in the clip and the stretch of its
    time, then the clip's frames."""
    lines = [move_line(move) for move in moves]
    lines += ["%s's %s on row %d: %d plays, its time stretched by %.3f" % (move.character.name, move.cycle.name, row,
                                                                           k, stretch)
              for (move, row, _), k, stretch in zip(clip.movers, clip.plays, clip.stretch)]
    return lines + ["the clip: %d frames of %d ms" % (clip.count, FRAME_MS)]


def painted(capture):
    """The fireman's moves, and the clip's movers as MoveClip takes them: each character's move painted once."""
    made = {}

    def move(character, name):
        if (character, name) not in made:
            made[character, name] = MovePictures(capture, TALL, character=character, cycle_name=name)
        return made[character, name]

    return ([move(FIREMAN, c.name) for c in mocap.MOVES],
            [(move(c, name), row, column) for c, name, row, column in MOVERS])


def main():
    parser = argparse.ArgumentParser(description="Paint the moves at %d px: a sheet of the fireman's and a clip of four "
                                                 "characters on Rescue's street." % TALL)
    parser.add_argument("--out", required=True, metavar="DIR", help="the folder the two pictures are written to")
    parser.add_argument("--cmu", default=mocap.CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    args = parser.parse_args()
    fireman, movers = painted(open_capture(parser, args.cmu, mocap.MOVES))
    clip = MoveClip(movers, Committed().street)
    os.makedirs(args.out, exist_ok=True)
    MoveSheet(fireman).image().save(os.path.join(args.out, "moves-sheet.png"))
    write_clip(clip.frames(), os.path.join(args.out, "moves.webp"), FRAME_MS)
    print("\n".join(move_lines(fireman, clip)))


if __name__ == "__main__":
    sys.exit(main())
