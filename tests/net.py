"""The net's core (P846, stage N of the engine plan P844): the records that pin what the box shows and plays, made
on the Mac's host, one process per job, NET_WORKERS at a time. Three levels:
- a subject of tools/render_scene.py's SUBJECTS: the sha256 of its frames 1 and 5, its row's shot frame, a frame in
  the middle and its last frame, and the cues it emits over the whole run, (frame, name, value) each;
- the App level: App.frame over the catalog's lineup with lcd.TftOut on the host's display, a fixed button script and
  the frame clock, built on tests/test_pick.py's Box: the game, switch and pick lines, and a frame's sha256 per game
  after the start and after each pick;
- the mixer: a fixed cue list through sound.VoiceSum and volume.MasterVolume, MIXER_BLOCKS blocks, the samples' sha256.
Golden reads and writes tests/golden/; Toolchain is what the hashes were made with (clang, the font, Python). A child
runs as `python3 -B tests/net.py record JOB [fast]` and prints its record as one NET line of JSON.
tools/render_scene.py --golden DIR writes the files; tests/test_golden.py compares a run with them. --- MVP (P846) ---"""

import concurrent.futures
import hashlib
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import render_scene  # noqa: E402  first: it puts games/ and the stubs on the path, through mac_host

FAST, FULL = "fast", "full"  # the tiers: frames 1 and 5 (the story run), or every pinned frame (the full suite)
APP, MIXER = "app", "mixer"  # the jobs that are not subjects
WORKERS = int(os.environ.get("NET_WORKERS", "8"))
MIXER_BLOCKS = 50
APP_SEED = 1  # random's seed before start(): the games draw from it
APP_PLAY_FRAMES = 10  # a game plays this many frames, a BOOT press on the first, before its frame is hashed
FILES = ("frames", "cues", "app", "mixer")  # tests/golden/<name>.json
CLANG_MISSING = "clang is missing: install the Xcode command line tools (xcode-select --install)"
FONT_MISSING = "no font at %s: run ./build.sh from the repository root, which clones MicroPython v1.29.0 there"


class NetError(Exception):
    """The net cannot run, or a child failed: the message says why and what to run."""


def tier():
    """The tier NET_TIER asks for: fast or full (the default)."""
    value = os.environ.get("NET_TIER", FULL)
    if value not in (FAST, FULL):
        raise NetError("NET_TIER is %r: fast or full" % value)
    return value


def counts(row, tier=FULL):
    """The frames pinned for a SUBJECTS row, 1 for the first: 1 and 5, then the shot, the middle and the last."""
    if tier == FAST:
        return [1, 5]
    return sorted({1, 5, row.shot, row.last // 2, row.last})


class Toolchain:
    """What the hashes depend on beyond the code: clang's version, the font header's sha256 and Python's version."""

    FIELDS = ("clang", "font_sha256", "python")

    def __init__(self, record):
        self.record = record

    @classmethod
    def here(cls, font=render_scene.FONT_PATH):
        """This Mac's, or NetError naming the command that brings what is missing."""
        if not shutil.which("clang"):
            raise NetError(CLANG_MISSING)
        if not os.path.exists(font):
            raise NetError(FONT_MISSING % font)
        clang = subprocess.run(["clang", "--version"], capture_output=True, text=True, check=True).stdout
        with open(font, "rb") as f:
            font_sha = hashlib.sha256(f.read()).hexdigest()
        return cls({"clang": clang.splitlines()[0], "font_sha256": font_sha, "python": platform.python_version()})

    def check(self, recorded):
        """NetError when the recorded toolchain is not this one."""
        changed = ["%s %r, here %r" % (k, recorded.get(k), self.record[k]) for k in self.FIELDS
                   if recorded.get(k) != self.record[k]]
        if changed:
            raise NetError("toolchain changed: regenerate on the baseline commit first (recorded %s)" % "; ".join(changed))


class Golden:
    """tests/golden's four files: meta (a Toolchain's record) and frames ({subject: {frame: sha256}}) from
    frames.json, cues ({subject: [[frame, name, value]]}), app ({"lines": [...], "frames": {key: sha256}}) and mixer
    ({"blocks": n, "sha256": ...}). A missing file reads as empty."""

    def __init__(self, meta, frames, cues, app, mixer):
        self.meta, self.frames, self.cues, self.app, self.mixer = meta, frames, cues, app, mixer

    @classmethod
    def read(cls, folder):
        data = {}
        for name in FILES:
            path = os.path.join(folder, name + ".json")
            data[name] = {}
            if os.path.exists(path):
                with open(path) as f:
                    data[name] = json.load(f)
        frames = data["frames"]
        return cls(frames.get("meta", {}), frames.get("frames", {}), data["cues"], data["app"], data["mixer"])

    def subject(self, name, tier=FULL):
        """The subject's record as a run of the tier makes it: its frames' hashes, and its cues up to its last frame."""
        frames = self.frames.get(name, {})
        last = 5 if tier == FAST else None
        keep = {n: h for n, h in frames.items() if last is None or int(n) <= last}
        return {"frames": keep, "cues": [c for c in self.cues.get(name, []) if last is None or c[0] <= last]}

    def write(self, folder):
        os.makedirs(folder, exist_ok=True)
        content = {"frames": {"meta": self.meta, "frames": self.frames}, "cues": self.cues, "app": self.app,
                   "mixer": self.mixer}
        for name in FILES:
            with open(os.path.join(folder, name + ".json"), "w") as f:
                json.dump(content[name], f, indent=1, sort_keys=True)
                f.write("\n")


def differences(want, got):
    """What differs between two subject records, one line each: "frame N differs", "frame N missing", "cues differ:
    ..."; [] when they match."""
    found = []
    for n in sorted(set(want["frames"]) | set(got["frames"]), key=int):
        if n not in got["frames"] or n not in want["frames"]:
            found.append("frame %s missing" % n)
        elif want["frames"][n] != got["frames"][n]:
            found.append("frame %s differs" % n)
    if want["cues"] != got["cues"]:
        k = next((i for i, (a, b) in enumerate(zip(want["cues"], got["cues"])) if a != b),
                 min(len(want["cues"]), len(got["cues"])))
        found.append("cues differ: %d recorded, %d now, first at #%d: %s now %s" % (
            len(want["cues"]), len(got["cues"]), k, want["cues"][k:k + 1], got["cues"][k:k + 1]))
    return found


# --- the records, each made in its own process ---
def record_subject(name, tier=FULL):
    """A subject's frames' hashes and its cues, as its SUBJECTS row plays it (the PNGs' and GIFs' settings of --all)."""
    from mac_host import CueRecorder

    row = render_scene.SUBJECTS[name]
    pinned, last = counts(row, tier), max(counts(row, tier))
    heard, hashes = CueRecorder(), {}
    for k, host in enumerate(render_scene.play(row, hold_ms=row.last * render_scene.FRAME_MS, signals=heard), 1):
        if k in pinned:
            hashes[str(k)] = host.digest()
        if k == last:
            break
    return {"frames": hashes, "cues": [list(c) for c in heard.heard if c[0] <= last]}


def record_app():
    """The App level: the catalog's lineup on the host, its first game from start(), then a D14 pick of each next game
    through the whole lineup and back to the first. A pick is settled by a BOOT press in the next frame; once the game
    plays, it gets a BOOT press and APP_PLAY_FRAMES frames, and the last is hashed."""
    import app
    import catalog
    import lcd
    from mac_host import MacHost
    from test_pick import Box

    host = MacHost().start()
    random.seed(APP_SEED)

    class HostBox(Box):
        """Box on the host's clock: ticks_us counts on the frame clock, so the switch lines' times repeat."""

        def frame(self, ms, d14=False, boot=False):
            host.clock.frame(ms)
            return super().frame(ms, d14, boot)

    box = HostBox(games=app.Lineup(catalog.NAMES), out=lcd.TftOut(host.tft))
    hashes = {}
    try:
        for n in range(len(catalog.NAMES) + 1):
            if n:
                box.frame(box.ms + app.FRAME_MS, d14=True)
                box.frame(box.ms + app.FRAME_MS, boot=True)
                box.run_build()
            for k in range(APP_PLAY_FRAMES):
                box.frame(box.ms + app.FRAME_MS, boot=k == 0)
            hashes["%02d %s" % (n, box.app.game.name)] = host.digest()
    finally:
        box.close()
    lines = [line for line in box.said.getvalue().splitlines() if line.split()[:1] in (["game"], ["switch"], ["pick"])]
    return {"lines": lines, "frames": hashes}


# The mixer's cue list: (block, signal, value), each emitted before the block renders; the volume's step by block
MIXER_CUES = ((0, "jump", None), (2, "hose", 256), (6, "land", None), (9, "pickup", None), (12, "hose", 64),
              (15, "siren", None), (16, "jump", None), (17, "land", None), (20, "hose", 0), (24, "boom", None),
              (30, "die", None), (38, "hose", 200), (44, "whoosh", None))
MIXER_STEPS = {0: 8, 18: 12, 33: 16, 41: 5}


def record_mixer():
    """MIXER_CUES through SoundCues on a four-voice Mixer with the reference VoiceSum, the box bank's sounds and its
    music, each block then through the reference MasterVolume at MIXER_STEPS: the samples' sha256."""
    from array import array

    import bank
    import box_bank
    import cues
    import signals
    import sound
    import volume

    mixer = sound.Mixer(4, sound.VoiceSum())
    sounds = bank.Bank(os.path.join(ROOT, "games", "box_bank.raw"), box_bank.BOX_BANK_INDEX)
    player, said = cues.SoundCues(mixer, sounds), signals.Signals()

    table = {name: cues.Cue(name, loop=name == "hose") for _, name, _ in MIXER_CUES}
    table["land"] = cues.Cue("land", volume.FULL // 2)  # one cue at half its gain
    player.follow(types.SimpleNamespace(cues=table), said)
    player.music()
    master, samples = volume.MasterVolume(), hashlib.sha256()
    for block in range(MIXER_BLOCKS):
        if block in MIXER_STEPS:
            master.set(MIXER_STEPS[block])
        for _, name, value in (c for c in MIXER_CUES if c[0] == block):
            said.emit(name, value)
        buf = array("h", bytes(2 * sound.REFILL_SAMPLES))
        mixer.render(buf)
        master.apply(buf)
        samples.update(buf.tobytes())
    return {"blocks": MIXER_BLOCKS, "sha256": samples.hexdigest()}


def record(job, tier=FULL):
    render_scene.Font(render_scene.FONT_PATH).install()  # the letters, as on the board
    if job == APP:
        return record_app()
    if job == MIXER:
        return record_mixer()
    return record_subject(job, tier)


# --- the run: one process per job ---
class Job:
    """A record to make in a child process: a subject's (at a tier) or APP or MIXER; patch is Python run in the
    child before the record, a negative test's change."""

    def __init__(self, name, tier=FULL, patch=""):
        self.name, self.tier, self.patch = name, tier, patch

    def command(self):
        args = ["record", self.name, self.tier]
        if not self.patch:
            return [sys.executable, "-B", os.path.abspath(__file__), *args]
        code = "import sys\nsys.path.insert(0, %r)\nimport net\n%s\nnet.main(%r)" % (HERE, self.patch, args)
        return [sys.executable, "-B", "-c", code]

    def run(self):
        env = dict(os.environ, PYTHONHASHSEED="0")  # a set's order, the same in every process
        done = subprocess.run(self.command(), cwd=ROOT, capture_output=True, text=True, env=env)
        lines = [line for line in done.stdout.splitlines() if line.startswith("NET ")]
        if done.returncode or not lines:
            raise NetError("the net's %s failed (exit %d): %s" % (self.name, done.returncode, done.stderr[-1500:]))
        return json.loads(lines[-1][4:])


def run(jobs, workers=WORKERS):
    """Each job's record, in the jobs' order, made workers at a time; the longest jobs start first."""
    def cost(job):
        row = render_scene.SUBJECTS.get(job.name)
        return 0 if row is None else (max(counts(row, job.tier)) if not job.patch else 0)

    order = sorted(range(len(jobs)), key=lambda i: (jobs[i].name != APP, -cost(jobs[i])))
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures = {i: pool.submit(jobs[i].run) for i in order}
        return [futures[i].result() for i in range(len(jobs))]


def make(workers=WORKERS):
    """Every record of the full tier, with this Mac's toolchain: a Golden to write."""
    meta = Toolchain.here().record
    names = list(render_scene.SUBJECTS)
    results = run([Job(name) for name in names] + [Job(APP), Job(MIXER)], workers)
    subjects = dict(zip(names, results))
    return Golden(meta, {n: r["frames"] for n, r in subjects.items()}, {n: r["cues"] for n, r in subjects.items()},
                  results[-2], results[-1])


def main(argv):
    if len(argv) not in (2, 3) or argv[0] != "record":
        raise SystemExit("usage: net.py record JOB [fast|full]")
    print("NET " + json.dumps(record(argv[1], argv[2] if len(argv) > 2 else FULL), sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
