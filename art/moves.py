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
from collections import namedtuple

from PIL import Image, ImageDraw

import mocap
from detailed import (ACROBAT, CHILD, DARK, FIREMAN, FOOTBALLER, FRAME_MS, GAP, SEED, TALL, CharacterClip, Committed,
                      Pictures, write_clip)
from export import stacked
from sets.rescue import snapped

# each mover's character, its move, the row of its lift 0 (its span's floor) and the column its pivot starts at (None:
# it crosses the street), from the farthest row to the nearest
MOVERS = ((FIREMAN, "climb", CharacterClip.TOP, 50), (FOOTBALLER, "jump", 216, 150), (CHILD, "jump", 228, 250),
          (ACROBAT, "forward jump", CharacterClip.BOTTOM, None))


class MovePictures(Pictures):
    """A character's move (cycle_name: a name in mocap.MOVES): the Pictures of its snapped poses, and where each goes.
    lifts: each pose's lift, in body heights. travel: px (forward, up) that each pose's picture goes from the play's
    start. advance: px (forward, up) from one play's start to the next. pose_ms: the capture's time from one pose to
    the next, which a one-shot's last pose also lasts; play_ms: a play's. posed: the snapped poses."""

    def __init__(self, capture, height, rim=None, seed=SEED, character=FIREMAN, cycle_name="jump"):
        raw = capture.poses(mocap.named(cycle_name))
        self.posed = [snapped(pose) for pose in raw]  # each with its lowest foot joint on the floor
        # each pose's lift: the root's up before the snap less after it
        self.lifts = [a["root"][1] - b["root"][1] for a, b in zip(raw, self.posed)]
        super().__init__(capture, height, rim, seed, character, cycle_name)
        px, leg = self.painter.PX, character.proportions.leg  # forward as the run's stride, so the feet keep still
        motion = capture.root_motion(self.cycle)
        self.travel = [(round(ahead * px * leg), round(lift * px)) for ahead, lift in zip(motion, self.lifts)]
        self.advance = (round(motion[-1] * px * leg), round(capture.rise(self.cycle) * px))
        self.pose_ms = self.cycle.frame(1, capture.loop(self.cycle)[1]) * 1000 / self.cycle.fps
        self.play_ms = len(self.pictures) * self.pose_ms

    def poses(self):
        """The poses to paint: the snapped ones."""
        return self.posed

    def toes(self):
        """The middle between the toe joints of pose 0, px from its pivot."""
        pose = self.character.proportions.fit(self.posed[0])
        (lx, ly), (rx, ry) = (self.painter.at(pose[n]) for n in ("ltoes", "rtoes"))
        x0, y0, _ = self.used
        return (lx + rx) / 2 - x0 - self.pivot[0], (ly + ry) / 2 - y0 - self.pivot[1]

    def pose_at(self, ms):
        """The pose ms into the move, played again and again, and its place: the whole plays times the advance, plus
        its travel. The place changes only with the pose."""
        plays, index = divmod(int(ms // self.pose_ms), len(self.pictures))
        (f, u), (af, au) = self.travel[index], self.advance
        return index, (plays * af + f, plays * au + u)


def nearest_plays(clip_ms, play_ms):
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

    def __init__(self, move_pictures):
        self.move_pictures = move_pictures

    def strip(self, move):
        """The move's poses on the dark, GAP px apart, each at its lift over the floor line, GAP px over the bottom."""
        w, h = move.size
        top = max(up for _, up in move.travel)
        strip = Image.new("RGB", (len(move.pictures) * (w + GAP) + GAP, h + top + 2 * GAP), DARK)
        floor = strip.height - GAP
        ImageDraw.Draw(strip).line((0, floor, strip.width - 1, floor), fill=self.FLOOR)
        for i, (img, (_, up)) in enumerate(zip(move.pictures, move.travel)):
            strip.paste(img, (GAP + i * (w + GAP), floor - h - up), img)
        return strip

    def rows(self):
        """Each move's label and strip."""
        return [(move_line(move), self.strip(move)) for move in self.move_pictures]

    def image(self):
        return stacked(self.rows())


class Mover(namedtuple("Mover", "move row column plays", defaults=(1,))):
    """One mover of the clip: a MovePictures, the row of its lift 0 (its span's floor), the column its pivot starts at,
    and how many times it plays in the clip. The crosser has column None: its picture starts just off the street's
    left edge, and it crosses the street."""

    @property
    def crosses(self):
        return self.column is None


class MoveClip:
    """moves.webp's frames: the movers (each a Mover) on Rescue's street, a frame of the game apart, each facing
    right, the farther pasted first. The clip lasts the least whole number of the crosser's plays that takes its
    picture off the street's right edge by the last frame. Every other mover plays the whole number of times nearest
    to the clip's length, its time stretched to fill it. A mover that goes up climbs a ladder, drawn on the street
    (ground) before any mover. When the clip starts again, every mover starts its first play again from its start
    place."""

    W = CharacterClip.W

    def __init__(self, movers, street):
        movers = sorted(movers, key=lambda m: m.row)  # the farther first
        n, self.count = self.crossing(next(m for m in movers if m.crosses))
        ms = self.count * FRAME_MS
        self.movers = [m._replace(plays=n if m.crosses else nearest_plays(ms, m.move.play_ms)) for m in movers]
        self.ground = street.copy()
        for mover in self.movers:
            if mover.move.advance[1] > 0:
                self.ladder(mover).draw(self.ground)

    def at(self, mover, count, i):
        """Where a mover's picture is pasted at frame i of a clip of count frames (its pivot on its place), and the
        picture."""
        move = mover.move
        start = move.pivot[0] - move.size[0] if mover.crosses else mover.column
        index, (f, u) = move.pose_at(i * mover.plays * move.play_ms / count)
        return start + f - move.pivot[0], mover.row - u - move.pivot[1], move.pictures[index]

    def crossing(self, mover):
        """The crosser's plays, and the clip's frames for them."""
        for n in range(1, self.W + 1):
            count = max(1, round(n * mover.move.play_ms / FRAME_MS))
            if self.at(mover._replace(plays=n), count, count - 1)[0] >= self.W:
                return n, count
        raise ValueError("the crosser does not cross the street")

    def ladder(self, mover):
        """The ladder of a mover that goes up: its rail leans along the advance through the middle between the toes of
        pose 0, a rung lies under the lowest foot then and one every half advance, and its foot is a rung lower."""
        move = mover.move
        (f, u), (af, au) = move.travel[0], move.advance
        dx, dy = move.toes()
        tx, ty = mover.column + f + dx, mover.row - u + dy
        y = mover.row - u + 1  # the row under the soles in pose 0
        x = tx + (ty - y) * af / au
        return Ladder((x - af / 2, y + au / 2), (af, au), math.hypot(af, au) / 2)

    def places(self, i):
        """Frame i's movers, the farthest first: (x, y, picture) each, (x, y) where the picture is pasted."""
        return [self.at(m, self.count, i) for m in self.movers]

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
    time, the clip's length over that of its plays, then the clip's frames."""
    lines = [move_line(move) for move in moves]
    lines += ["%s's %s on row %d: %d plays, its time stretched by %.3f" % (
        m.move.character.name, m.move.cycle.name, m.row, m.plays, clip.count * FRAME_MS / (m.plays * m.move.play_ms))
        for m in clip.movers]
    return lines + ["the clip: %d frames of %d ms" % (clip.count, FRAME_MS)]


def painted(capture):
    """The fireman's moves, and the clip's movers as MoveClip takes them: each character's move painted once."""
    made = {}

    def move(character, name):
        if (character, name) not in made:
            made[character, name] = MovePictures(capture, TALL, character=character, cycle_name=name)
        return made[character, name]

    return ([move(FIREMAN, c.name) for c in mocap.MOVES],
            [Mover(move(c, name), row, column) for c, name, row, column in MOVERS])


def main():
    parser = argparse.ArgumentParser(description="Paint the moves at %d px: a sheet of the fireman's and a clip of "
                                                 "four characters on Rescue's street." % TALL)
    parser.add_argument("--out", required=True, metavar="DIR", help="the folder the two pictures are written to")
    parser.add_argument("--cmu", default=mocap.CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    args = parser.parse_args()
    fireman, movers = painted(mocap.open_capture(parser, args.cmu, mocap.MOVES))
    clip = MoveClip(movers, Committed().street)
    os.makedirs(args.out, exist_ok=True)
    MoveSheet(fireman).image().save(os.path.join(args.out, "moves-sheet.png"))
    write_clip(clip.frames(), os.path.join(args.out, "moves.webp"), FRAME_MS)
    print("\n".join(move_lines(fireman, clip)))


if __name__ == "__main__":
    sys.exit(main())
