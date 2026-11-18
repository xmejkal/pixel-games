"""Motion capture to side-view poses (P800): the fireman's cycles in art/sets/rescue.py move as a person moved, and so
do the moves that art/moves.py paints (P904).

It reads a CMU skeleton (.asf) and its motion (.amc), runs the forward kinematics, looks at the body from the side
(Y up, the way the body faces forward), cuts one loop of the motion, or a move's whole span, and resamples it to the
poses a cycle has. Each pose is a dict of joint name to (forward, up, near) in body heights: the floor at up 0, the
hips at forward 0, and near the depth toward the viewer, who stands at the body's right. A nose joint says the way the
face looks. Standard library only; it writes nothing. The data comes from the CMU Graphics Lab Motion Capture Database,
http://mocap.cs.cmu.edu, downloaded once into CMU_DIR (never into the repository: "The motion capture data may be
copied, modified, or redistributed without permission", and the database asks for this line: "The data used in this
project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217.").

The cycles, as CYCLES lists them:
    run    subject 9, trial 1 ("run"), 120 fps: one stride (two steps), the loop with the closest ends.
    spray  subject 13, trial 27 ("direct traffic, wave, point"), 120 fps: both arms held out in front at chest
           height in a staggered stance, frames 760 to 1240, the loop with the closest ends. The hands hold the nozzle.
    turn   the run's poses turned about the up axis, from facing forward to facing back, a step of 180 / 4 degrees
           a pose: a turn made from the run, as no straight-running trial here turns.
    carry  subject 2, trial 3 ("run/jog"), 120 fps: one stride of a jog, the legs and the body; the arms that hold the
           person on his shoulder are posed in art/sets/rescue.py. The suitcase trials of subject 70 stand still.
The people's cycles, as CROWD lists them (pictures rescue_<who>_run and rescue_<who>_wave):
    man     subject 16, trial 35 ("run/jog")         woman   subject 35, trial 17 ("run/jog")
    child   subject 9, trial 2 ("run")               granny  subject 35, trial 1 ("walk"), leant and with a cane
    dogman  subject 35, trial 22 ("run/jog")
    wave    subject 13, trial 27 ("direct traffic, wave, point"), frames 1850 to 2030: the right arm up over the head,
            waving, seen turned VIEW degrees toward the viewer, so the wave across the body shows; every person's.
The moves, as MOVES lists them: a Cycle loops on the floor, a Rising loop also goes up, and a OneShot plays once.
    jump          subject 13, trial 39 ("jump"), 120 fps, a one-shot: frames 86 to 247, from the crouch to the crouch
                  after the landing.
    forward jump  subject 13, trial 11 ("forward jump"), 120 fps, a one-shot: frames 200 to 320, the flight.
    climb         subject 13, trial 33 ("climb ladder"), 120 fps, a rising loop: one climbing cycle in frames 240 to
                  740, the loop with the closest ends once the rise is taken out.
Subject 77 is at 60 fps, the others at 120 (the CMU site).

Run from the repository root: python3 art/mocap.py [--cmu DIR] prints each cycle's source, its loop and its stride,
and each move's source, its frames and how far its root goes forward and up a play.
"""

import argparse
import math
import os

CMU_DIR = os.path.join("~", ".cache", "pixel-games", "cmu")  # where the CMU files are downloaded; ~ is the home


def rotation(axis, degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return {"X": ((1, 0, 0), (0, c, -s), (0, s, c)), "Y": ((c, 0, s), (0, 1, 0), (-s, 0, c)),
            "Z": ((c, -s, 0), (s, c, 0), (0, 0, 1))}[axis]


def mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def transpose(m):
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))


def euler(order, angles):
    """The rotation of angles about fixed axes, the first axis applied first (the ASF/AMC convention)."""
    m = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    for axis, a in zip(order, angles):
        m = mul(rotation(axis, a), m)
    return m


class Bone:
    def __init__(self):
        self.name, self.direction, self.length, self.dof = "", (0, 0, 0), 0.0, ()
        self.axis = self.unaxis = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        self.parent = "root"


class Skeleton:
    """An ASF file: the bones in their rest pose and the hierarchy. joints(frame) is the forward kinematics."""

    def __init__(self, path):
        self.bones, self.root_order = {}, ()
        section, bone = None, None
        with open(path) as f:
            for line in f:
                words = line.split()
                if not words or words[0].startswith("#"):
                    continue
                if words[0].startswith(":"):
                    section = words[0]
                elif section == ":root" and words[0] == "order":
                    self.root_order = tuple(words[1:])
                elif section == ":bonedata":
                    bone = self.bone_line(words, bone)
                elif section == ":hierarchy" and words[0] not in ("begin", "end"):
                    for child in words[1:]:
                        self.bones[child].parent = words[0]
        self.order = []  # parents before children
        while len(self.order) < len(self.bones):
            for name, b in self.bones.items():
                if name not in self.order and (b.parent == "root" or b.parent in self.order):
                    self.order.append(name)

    def bone_line(self, words, bone):
        if words[0] == "begin":
            return Bone()
        if words[0] == "end":
            self.bones[bone.name] = bone
        elif words[0] == "name":
            bone.name = words[1]
        elif words[0] == "direction":
            bone.direction = tuple(float(v) for v in words[1:4])
        elif words[0] == "length":
            bone.length = float(words[1])
        elif words[0] == "axis":
            bone.axis = euler(words[4], [float(v) for v in words[1:4]])
            bone.unaxis = transpose(bone.axis)
        elif words[0] == "dof":
            bone.dof = tuple(d.upper() for d in words[1:])
        return bone

    def joints(self, frame):
        """frame: bone name to its AMC values. The end of every bone, and the root, as (x, y, z), Y up."""
        root = dict(zip(self.root_order, frame["root"]))
        pos = {"root": (root["TX"], root["TY"], root["TZ"])}
        mat = {"root": euler("XYZ", (root["RX"], root["RY"], root["RZ"]))}
        for name in self.order:
            b = self.bones[name]
            angles = dict(zip(b.dof, frame.get(name, ())))
            local = euler("XYZ", [angles.get(a, 0.0) for a in ("RX", "RY", "RZ")])
            mat[name] = mul(mul(mul(mat[b.parent], b.axis), local), b.unaxis)
            d = apply(mat[name], b.direction)
            pos[name] = tuple(p + b.length * v for p, v in zip(pos[b.parent], d))
        return pos

    def height(self):
        """From the toes to the head's end in the rest pose, in the file's units."""
        rest = self.joints({"root": [0.0] * len(self.root_order)})
        return rest["head"][1] - min(rest["ltoes"][1], rest["rtoes"][1])


def read_motion(path):
    """An AMC file: one dict of bone name to its values per frame."""
    frames = []
    with open(path) as f:
        for line in f:
            words = line.split()
            if not words or words[0][0] in "#:":
                continue
            if words[0].isdigit() and len(words) == 1:
                frames.append({})
            else:
                frames[-1][words[0]] = [float(v) for v in words[1:]]
    return frames


def turned(joints, degrees):
    """The joints turned about the up axis through the root."""
    rx, _, rz = joints["root"]
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return {n: (rx + (x - rx) * c + (z - rz) * s, y, rz - (x - rx) * s + (z - rz) * c) for n, (x, y, z) in joints.items()}


def facing(joints):
    """The horizontal way the hips face: square to the line from the right hip to the left hip."""
    (lx, _, lz), (rx, _, rz) = joints["lhipjoint"], joints["rhipjoint"]
    fx, fz = rz - lz, lx - rx
    n = math.hypot(fx, fz) or 1.0
    return fx / n, fz / n


def forward(frames):
    """The way the hips face on average over frames of joints: the side view looks across it."""
    fx, fz = sum(facing(j)[0] for j in frames), sum(facing(j)[1] for j in frames)
    n = math.hypot(fx, fz) or 1.0
    return fx / n, fz / n


def side(joints, way, floor, height):
    """The side view from the body's right: (forward, up, near) per joint in body heights, the root at forward 0, the
    floor at up 0, and near the depth toward the viewer, so a painter knows which limb is in front."""
    fx, fz = way
    rx, _, rz = joints["root"]
    return {n: (((x - rx) * fx + (z - rz) * fz) / height, (y - floor) / height, ((z - rz) * fx - (x - rx) * fz) / height)
            for n, (x, y, z) in joints.items()}


def with_nose(joints, height):
    """The joints and a nose, a tenth of the body ahead of the head the way the hips face: the way the face looks."""
    fx, fz = facing(joints)
    hx, hy, hz = joints["head"]
    return dict(joints, nose=(hx + 0.1 * height * fx, hy, hz + 0.1 * height * fz))


def distance(a, b, up=0):
    """How far two side views are apart, the second lowered by up: the sum of the squared joint distances."""
    return sum((a[n][0] - b[n][0]) ** 2 + (a[n][1] - (b[n][1] - up)) ** 2 for n in a)


def blend(a, b, t):
    return {n: tuple(p + (q - p) * t for p, q in zip(a[n], b[n])) for n in a}


class Cycle:
    """One cycle: a trial, the frames it may loop in, the loop's length in frames (least, most), its poses, the
    degrees the body turns over the cycle (the turn), and the degrees it is turned toward the viewer throughout. A loop
    that travels forward on the floor: a run or a walk. Capture asks it four things: its loop, the frame of a pose,
    the poses as it keeps them, and how far it rises."""

    def __init__(self, name, trial, fps, frames, period, poses, turn=0, view=0):
        self.name, self.trial, self.fps, self.frames = name, trial, fps, frames
        self.period, self.poses, self.turn, self.view = period, poses, turn, view

    def source(self):
        subject, trial = self.trial.split("_")
        return "%d:%d at %d fps" % (int(subject), int(trial), self.fps)

    def loop(self, views):
        """The loop's first view and its length in views: within its period, the loop whose last view, lowered by the
        rise, comes closest to its first."""
        best = None
        for p in range(self.period[0], self.period[1] + 1):
            for s in range(0, len(views) - p):
                d = distance(views[s], views[s + p], self.rise(views[s], views[s + p]))
                if best is None or d < best[0]:
                    best = (d, s, p)
        return best[1:]

    def frame(self, i, period):
        """The frame of pose i in a loop of period frames, i from 0 to poses: the poses evenly spaced over the loop."""
        return i * period / self.poses

    def settle(self, poses, first, last):
        """The poses as the cycle keeps them, given the loop's first and last view: as they are."""
        return poses

    def rise(self, first, last):
        """How far the root goes up from the first view to the last: a loop on the floor does not rise."""
        return 0


class Rising(Cycle):
    """A loop where the body also goes up: the climb. Its loop is found with the end lowered by the root's rise, and
    its poses are closed: the gap between the loop's ends, the rise taken out, is spread over them, so that after one
    loop every joint is one rise higher."""

    def settle(self, poses, first, last):
        """Pose i less i / poses of the gap between the last view, lowered by the rise, and the first."""
        up = self.rise(first, last)
        gap = {n: (lf - ff, lu - up - fu, ld - fd) for n, ((ff, fu, fd), (lf, lu, ld)) in
               ((n, (first[n], last[n])) for n in first)}
        return [{n: tuple(v - g * i / self.poses for v, g in zip(pose[n], gap[n])) for n in pose}
                for i, pose in enumerate(poses)]

    def rise(self, first, last):
        return last["root"][1] - first["root"][1]


class OneShot(Cycle):
    """A move that plays once and does not loop: a jump. It takes no period: its loop is its whole span, and its first
    and last poses are the span's ends."""

    def __init__(self, name, trial, fps, frames, poses):
        super().__init__(name, trial, fps, frames, None, poses)

    def loop(self, views):
        return (0, len(views) - 1)

    def frame(self, i, period):
        """The poses from the first frame to the last, i up to poses; past the last pose, the last frame."""
        return min(period, i * period / (self.poses - 1))


CYCLES = (
    Cycle("run", "09_01", 120, (0, 148), (70, 110), 12),
    Cycle("spray", "13_27", 120, (760, 1240), (60, 150), 6),
    Cycle("turn", "09_01", 120, (0, 148), (70, 110), 4, turn=180),
    Cycle("carry", "02_03", 120, (0, 175), (60, 120), 12),
)
VIEW = -60  # degrees the wave is turned toward the viewer
CROWD = (
    Cycle("man", "16_35", 120, (0, 162), (60, 120), 12),
    Cycle("woman", "35_17", 120, (0, 167), (60, 110), 12),
    Cycle("child", "09_02", 120, (0, 130), (60, 110), 12),
    Cycle("granny", "35_01", 120, (0, 358), (100, 160), 12),
    Cycle("dogman", "35_22", 120, (0, 160), (60, 110), 12),
    Cycle("wave", "13_27", 120, (1850, 2030), (120, 170), 12, view=VIEW),
)
MOVES = (
    OneShot("jump", "13_39", 120, (86, 248), 12),
    OneShot("forward jump", "13_11", 120, (200, 321), 12),
    Rising("climb", "13_33", 120, (240, 740), (250, 330), 12),
)


class Capture:
    """The CMU files in one folder: each cycle's poses. The kinematics run once per trial and frame span."""

    def __init__(self, folder=CMU_DIR):
        self.folder = os.path.expanduser(folder)
        self.spans = {}  # (trial, frames): (skeleton, the 3D joints of those frames, the floor under them)
        self.loops = {}  # cycle name: (first frame in its span, length in frames)

    def missing(self, cycles=None):
        """The files the cycles need (None: those of CYCLES and CROWD) that are not in the folder."""
        cycles = CYCLES + CROWD if cycles is None else cycles
        names = sorted({c.trial[:2] + ".asf" for c in cycles} | {c.trial + ".amc" for c in cycles})
        return [n for n in names if not os.path.exists(os.path.join(self.folder, n))]

    def span(self, cycle):
        key = (cycle.trial, cycle.frames)
        if key not in self.spans:
            skeleton = Skeleton(os.path.join(self.folder, cycle.trial[:2] + ".asf"))
            first, last = cycle.frames
            frames = read_motion(os.path.join(self.folder, cycle.trial + ".amc"))[first:last]
            joints = [skeleton.joints(f) for f in frames]
            floor = min(min(j["ltoes"][1], j["rtoes"][1]) for j in joints)
            self.spans[key] = (skeleton, joints, floor)
        return self.spans[key]

    def loop(self, cycle):
        """The cycle's first frame in its span and its length in frames, as the cycle finds them in the span's side
        views (Cycle.loop); found once per cycle."""
        if cycle.name not in self.loops:
            skeleton, joints, floor = self.span(cycle)
            way, height = forward(joints), skeleton.height()
            self.loops[cycle.name] = cycle.loop([side(j, way, floor, height) for j in joints])
        return self.loops[cycle.name]

    def window(self, cycle):
        """The loop's frames of 3D joints, from its first to its last, the way the body faces over them, the floor and
        the body height."""
        skeleton, joints, floor = self.span(cycle)
        start, period = self.loop(cycle)
        window = joints[start:start + period + 1]
        return window, forward(window), floor, skeleton.height()

    def poses(self, cycle):
        """The cycle's poses: its loop resampled to cycle.poses side views at the cycle's frames, turned if it turns,
        as the cycle keeps them (Cycle.settle)."""
        window, way, floor, height = self.window(cycle)
        period = len(window) - 1

        def view(joints, degrees=0):
            """One frame's side view, turned by degrees and by the cycle's view, with a nose."""
            if degrees:
                joints = turned(joints, degrees)
            if cycle.view:
                joints = turned(joints, cycle.view)
            return side(with_nose(joints, height), way, floor, height)

        out = []
        for i in range(cycle.poses):
            t = cycle.frame(i, period)
            k = int(t)
            degrees = cycle.turn * (i + 0.5) / cycle.poses
            out.append(blend(view(window[k], degrees), view(window[min(k + 1, period)], degrees), t - k))
        return cycle.settle(out, view(window[0]), view(window[period]))

    def root_motion(self, cycle):
        """The root's place along the way the body faces at the frame of each pose, and of one more after the last
        (Cycle.frame), from the loop's first frame, in body heights: the body's own way through the world. For a loop
        the last number is the forward part of the stride."""
        window, (fx, fz), _, height = self.window(cycle)
        period = len(window) - 1
        x0, _, z0 = window[0]["root"]

        def ahead(joints):
            x, _, z = joints["root"]
            return ((x - x0) * fx + (z - z0) * fz) / height

        out = []
        for i in range(cycle.poses + 1):
            t = cycle.frame(i, period)
            k = int(t)
            a, b = ahead(window[k]), ahead(window[min(k + 1, period)])
            out.append(a + (b - a) * (t - k))
        return out

    def rise(self, cycle):
        """How far the root goes up over one loop, in body heights (Cycle.rise): 0 but for a rising loop."""
        window, way, floor, height = self.window(cycle)
        return cycle.rise(side(window[0], way, floor, height), side(window[-1], way, floor, height))

    def stride(self, cycle):
        """How far the root travels over one loop, in body heights."""
        skeleton, joints, _ = self.span(cycle)
        start, period = self.loop(cycle)
        (ax, _, az), (bx, _, bz) = joints[start]["root"], joints[start + period]["root"]
        return math.hypot(bx - ax, bz - az) / skeleton.height()


def loop_line(capture, cycle):
    """The cycle's source and its loop's frames, length and poses, as main prints them."""
    start, period = capture.loop(cycle)
    start += cycle.frames[0]
    return "%s, frames %d to %d (%.2f s), %d poses" % (cycle.source(), start, start + period, period / cycle.fps,
                                                       cycle.poses)


def main():
    parser = argparse.ArgumentParser(description="Print each cycle's and each move's source, loop and way from the "
                                                 "CMU files.")
    parser.add_argument("--cmu", default=CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    args = parser.parse_args()
    capture = Capture(args.cmu)
    missing = capture.missing(CYCLES + CROWD + MOVES)
    if missing:
        parser.error("not in %s: %s" % (args.cmu, ", ".join(missing)))
    for cycle in CYCLES + CROWD:
        print("%-6s %s, stride %.3f body heights" % (cycle.name, loop_line(capture, cycle), capture.stride(cycle)))
    for move in MOVES:
        print("%-12s %s, %.3f body heights forward and %.3f up a play" % (
            move.name, loop_line(capture, move), capture.root_motion(move)[-1], capture.rise(move)))


if __name__ == "__main__":
    main()
