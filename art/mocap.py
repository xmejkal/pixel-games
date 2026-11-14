"""Motion capture to side-view poses (P800): the fireman's cycles in art/sets/rescue.py move as a person moved.

It reads a CMU skeleton (.asf) and its motion (.amc), runs the forward kinematics, looks at the body from the side
(Y up, the way the body faces forward), cuts one loop of the motion and resamples it to the poses a cycle has. Each
pose is a dict of joint name to (forward, up, near) in body heights: the floor at up 0, the hips at forward 0, and
near the depth toward the viewer, who stands at the body's right. A nose joint says the way the face looks. Standard
library only; it writes nothing. The data comes from the CMU Graphics Lab Motion Capture Database,
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
Subject 77 is at 60 fps, the others at 120 (the CMU site).

Run from the repository root: python3 art/mocap.py [--cmu DIR] prints each cycle's source, its loop and its stride.
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


def distance(a, b):
    """How far two side views are apart: the sum of the squared joint distances."""
    return sum((a[n][0] - b[n][0]) ** 2 + (a[n][1] - b[n][1]) ** 2 for n in a)


def blend(a, b, t):
    return {n: tuple(p + (q - p) * t for p, q in zip(a[n], b[n])) for n in a}


class Cycle:
    """One cycle: a trial, the frames it may loop in, the loop's length in frames (least, most), its poses, the
    degrees the body turns over the cycle (the turn), and the degrees it is turned toward the viewer throughout."""

    def __init__(self, name, trial, fps, frames, period, poses, turn=0, view=0):
        self.name, self.trial, self.fps, self.frames = name, trial, fps, frames
        self.period, self.poses, self.turn, self.view = period, poses, turn, view

    def source(self):
        subject, trial = self.trial.split("_")
        return "%d:%d at %d fps" % (int(subject), int(trial), self.fps)


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


class Capture:
    """The CMU files in one folder: each cycle's poses. The kinematics run once per trial and frame span."""

    def __init__(self, folder=CMU_DIR):
        self.folder = os.path.expanduser(folder)
        self.spans = {}  # (trial, frames): (skeleton, the 3D joints of those frames, the floor under them)
        self.loops = {}  # cycle name: (first frame in its span, length in frames)

    def missing(self):
        """The files the cycles need that are not in the folder."""
        cycles = CYCLES + CROWD
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
        """The cycle's first frame in its span and its length in frames: within its period, the loop whose last frame
        comes closest to its first."""
        if cycle.name not in self.loops:
            skeleton, joints, floor = self.span(cycle)
            way, height = forward(joints), skeleton.height()
            views = [side(j, way, floor, height) for j in joints]
            best = None
            for p in range(cycle.period[0], cycle.period[1] + 1):
                for s in range(0, len(views) - p):
                    d = distance(views[s], views[s + p])
                    if best is None or d < best[0]:
                        best = (d, s, p)
            self.loops[cycle.name] = best[1:]
        return self.loops[cycle.name]

    def poses(self, cycle):
        """The cycle's poses: its loop resampled to cycle.poses evenly spaced side views, turned if it turns."""
        skeleton, joints, floor = self.span(cycle)
        start, period = self.loop(cycle)
        window = joints[start:start + period + 1]
        way, height = forward(window), skeleton.height()
        out = []
        for i in range(cycle.poses):
            t = i * period / cycle.poses
            k = int(t)
            a, b = window[k], window[min(k + 1, period)]
            if cycle.turn:
                degrees = cycle.turn * (i + 0.5) / cycle.poses
                a, b = turned(a, degrees), turned(b, degrees)
            if cycle.view:
                a, b = turned(a, cycle.view), turned(b, cycle.view)
            a, b = with_nose(a, height), with_nose(b, height)
            out.append(blend(side(a, way, floor, height), side(b, way, floor, height), t - k))
        return out

    def stride(self, cycle):
        """How far the root travels over one loop, in body heights."""
        skeleton, joints, _ = self.span(cycle)
        start, period = self.loop(cycle)
        (ax, _, az), (bx, _, bz) = joints[start]["root"], joints[start + period]["root"]
        return math.hypot(bx - ax, bz - az) / skeleton.height()


def main():
    parser = argparse.ArgumentParser(description="Print each cycle's source, loop and stride from the CMU files.")
    parser.add_argument("--cmu", default=CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    args = parser.parse_args()
    capture = Capture(args.cmu)
    if capture.missing():
        parser.error("not in %s: %s" % (args.cmu, ", ".join(capture.missing())))
    for cycle in CYCLES + CROWD:
        start, period = capture.loop(cycle)
        start += cycle.frames[0]
        print("%-6s %s, frames %d to %d (%.2f s), %d poses, stride %.3f body heights" % (
            cycle.name, cycle.source(), start, start + period, period / cycle.fps, cycle.poses, capture.stride(cycle)))


if __name__ == "__main__":
    main()
