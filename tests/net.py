"""The net's core (P846, stage N of the engine plan P844): the records that pin what the box shows and plays, made
on the Mac's host, one process per job, NET_WORKERS at a time. Three levels:
- a subject of ROWS (tools/render_scene.py's SUBJECTS and OVER_ROWS): the sha256 of its frames 1 and 5, its row's
  shot frame, a frame in the middle, its last frame and, when it reaches game over, the frame its card shows on; one
  sha256 chained over every frame of the run (and one over frames 1 to 5); its game's cue table; the cues it emits
  over the whole run, (frame, name, value) each; and those cues played through its table on the mixer, the samples'
  sha256;
- the App level: App.frame over the catalog's lineup with lcd.TftOut on the host's display, a fixed button script and
  the frame clock, built on tests/test_pick.py's Box: the game, switch and pick lines, a frame's sha256 per game after
  the start and after each pick, then HOLD_GAME held for HOLD_FRAMES frames, run to its game over and restarted;
- the mixer: a fixed cue list through sound.VoiceSum and volume.MasterVolume, MIXER_BLOCKS blocks, the samples' sha256.
Golden reads and writes tests/golden/; Toolchain is what the hashes were made with (clang, the font, Python). A child
runs as `python3 -B tests/net.py record JOB [fast]` and prints its record as one NET line of JSON. The game box's
modules come from mac_host.modules() alone.
tools/render_scene.py --golden DIR writes the files; tests/test_golden.py compares a run with them. --- MVP (P846) ---"""

import concurrent.futures
import hashlib
import json
import os
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
from mac_host import FRAME_MS, CueRecorder, MacHost, modules  # noqa: E402

FAST, FULL = "fast", "full"  # the tiers: frames 1 to 5 (the story run), or the whole run (the full suite)
FAST_COUNTS = (1, 5)  # the frames the fast tier pins; it plays to the last of them
APP, MIXER = "app", "mixer"  # the jobs that are not subjects
WORKERS = int(os.environ.get("NET_WORKERS", "8"))
MIXER_BLOCKS = 50
APP_SEED = 1  # random's seed before start(): the games draw from it
APP_PLAY_FRAMES = 10  # a game plays this many frames, a BOOT press on the first, before its frame is hashed
APP_FRAMES = 700  # about the frames the App level plays: its cost beside a subject's, for the order of the run
HOLD_GAME, HOLD_FRAMES, OVER_LIMIT = "cave", 30, 500  # the App's second script: the game held, then run to its end
CARD_MARGIN = 2  # frames after a card's CARD_MS (0 for the shared box) at which the over frame is pinned
FILES = ("frames", "cues", "app", "mixer")  # tests/golden/<name>.json
CLANG_MISSING = "clang is missing: install the Xcode command line tools (xcode-select --install)"
FONT_MISSING = "no font at %s: run ./build.sh from the repository root, which clones MicroPython v1.29.0 there"

_m = modules()
OVER_ROWS = {  # the net's own rows, not pictures: each reaches game over, so the card it draws is pinned
    "cave_over": render_scene.Subject(_m.arcade2.Cave, "no press: the shared game-over box", 1, 40),
    "stack_over": render_scene.Subject(_m.arcade2.Stack, "early drops: stack's own card", 1, 60, tap=7),
}
ROWS = dict(render_scene.SUBJECTS, **OVER_ROWS)


class NetError(Exception):
    """The net cannot run, or a child failed: the message says why and what to run."""


def tier():
    """The tier NET_TIER asks for: fast or full (the default)."""
    value = os.environ.get("NET_TIER", FULL)
    if value not in (FAST, FULL):
        raise NetError("NET_TIER is %r: fast or full" % value)
    return value


def counts(row, tier=FULL):
    """The frames pinned for a row, 1 for the first: 1 and 5, then the shot, the middle and the last. The frame a
    game-over card shows on is found in the run."""
    if tier == FAST:
        return list(FAST_COUNTS)
    return sorted(set(FAST_COUNTS) | {row.shot, row.last // 2, row.last})


class Toolchain:
    """What the hashes depend on beyond the code: clang's version, the font header's sha256 and Python's major and
    minor version."""

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
        return cls({"clang": clang.splitlines()[0], "font_sha256": font_sha, "python": "%d.%d" % sys.version_info[:2]})

    def check(self, recorded):
        """NetError when the recorded toolchain is not this one."""
        changed = ["%s %r, here %r" % (k, recorded.get(k), self.record[k]) for k in self.FIELDS
                   if recorded.get(k) != self.record[k]]
        if changed:
            raise NetError("toolchain changed: regenerate on the baseline commit first (recorded %s)" % "; ".join(changed))


class Golden:
    """tests/golden's four files. frames.json: meta (a Toolchain's record) and subjects ({name: {"frames": {frame:
    sha256}, "run": sha256, "run_to_5": sha256, "over": [over frame, card frame] or None}}); cues.json ({name:
    {"table": {signal: [sound, gain, loop, group]}, "heard": [[frame, signal, value]]}}); app.json ({"lines": [...],
    "frames": {key: sha256}}); mixer.json ({"blocks": n, "sha256": ..., "subjects": {name: sha256 or None}}). A missing
    file reads as empty."""

    def __init__(self, meta, subjects, app, mixer):
        self.meta, self.subjects, self.app, self.mixer = meta, subjects, app, mixer  # subjects: name -> full record

    @classmethod
    def read(cls, folder):
        data = {}
        for name in FILES:
            path = os.path.join(folder, name + ".json")
            data[name] = {}
            if os.path.exists(path):
                with open(path) as f:
                    data[name] = json.load(f)
        frames, sounds = data["frames"].get("subjects", {}), data["mixer"].get("subjects", {})
        subjects = {}
        for name, pinned in frames.items():
            cues = data["cues"].get(name, {})
            subjects[name] = dict(pinned, table=cues.get("table"), cues=cues.get("heard"), sound=sounds.get(name))
        mixer = {k: v for k, v in data["mixer"].items() if k != "subjects"}
        return cls(data["frames"].get("meta", {}), subjects, data["app"], mixer)

    def subject(self, name, tier=FULL):
        """The subject's record as a run of the tier makes it ({} for a subject with none)."""
        record = self.subjects.get(name)
        return {} if record is None else project(record, tier)

    def write(self, folder):
        os.makedirs(folder, exist_ok=True)
        pinned = {n: {k: r[k] for k in ("frames", "run", "run_to_5", "over")} for n, r in self.subjects.items()}
        content = {"frames": {"meta": self.meta, "subjects": pinned},
                   "cues": {n: {"table": r["table"], "heard": r["cues"]} for n, r in self.subjects.items()},
                   "app": self.app,
                   "mixer": dict(self.mixer, subjects={n: r["sound"] for n, r in self.subjects.items()})}
        for name in FILES:
            with open(os.path.join(folder, name + ".json"), "w") as f:
                json.dump(content[name], f, indent=1, sort_keys=True)
                f.write("\n")


def project(record, tier):
    """A full record cut to what a run of the tier makes: the fast tier keeps frames 1 to 5, their chained run, the
    cue table and the cues up to frame 5."""
    if tier == FULL:
        return record
    last = FAST_COUNTS[-1]
    return {"frames": {n: h for n, h in record["frames"].items() if int(n) <= last}, "run_to_5": record["run_to_5"],
            "table": record["table"], "cues": [c for c in record["cues"] if c[0] <= last]}


def differences(want, got):
    """What differs between two subject records, one line each: "frame N differs", "frame N missing", "run differs",
    "run to frame 5 differs", "sound differs", "over differs: ...", "cue table differs: ...", "cues differ: ...";
    [] when they match."""
    if not want or not got:
        return ["no record" if not want else "no run"]
    found = []
    for n in sorted(set(want["frames"]) | set(got["frames"]), key=int):
        if n not in got["frames"] or n not in want["frames"]:
            found.append("frame %s missing" % n)
        elif want["frames"][n] != got["frames"][n]:
            found.append("frame %s differs" % n)
    for key, line in (("run", "run differs"), ("run_to_5", "run to frame 5 differs"), ("sound", "sound differs")):
        if want.get(key) != got.get(key):
            found.append(line)
    if want.get("over") != got.get("over"):
        found.append("over differs: %s now %s" % (want.get("over"), got.get("over")))
    if want["table"] != got["table"]:
        changed = sorted(k for k in set(want["table"]) | set(got["table"]) if want["table"].get(k) != got["table"].get(k))
        found.append("cue table differs: %s" % ", ".join(changed))
    if want["cues"] != got["cues"]:
        k = next((i for i, (a, b) in enumerate(zip(want["cues"], got["cues"])) if a != b),
                 min(len(want["cues"]), len(got["cues"])))
        found.append("cues differ: %d recorded, %d now, first at #%d: %s now %s" % (
            len(want["cues"]), len(got["cues"]), k, want["cues"][k:k + 1], got["cues"][k:k + 1]))
    return found


# --- the records, each made in its own process ---
def cue_table(cues):
    """A game's cue table as data: signal -> [sound, gain, loop, group]."""
    return {name: [cue.sound, cue.gain, cue.loop, cue.group] for name, cue in sorted(cues.items())}


class CueSound:
    """A cue table played as the box plays it: SoundCues on a four-voice Mixer with the reference VoiceSum, the box
    bank's sounds and its music; each block of REFILL_SAMPLES then through the reference MasterVolume. digest() is
    the sha256 of every block's samples."""

    def __init__(self, table):
        m = modules()
        self.m, self.mixer = m, m.sound.Mixer(4, m.sound.VoiceSum())
        sounds = m.bank.Bank(os.path.join(ROOT, "games", "box_bank.raw"), m.box_bank.BOX_BANK_INDEX)
        player, self.said = m.cues.SoundCues(self.mixer, sounds), m.signals.Signals()
        cues = {name: m.cues.Cue(*row) for name, row in table.items()}
        player.follow(types.SimpleNamespace(cues=cues), self.said)
        player.music()
        self.master, self.samples = m.volume.MasterVolume(), hashlib.sha256()

    def emit(self, name, value=None):
        self.said.emit(name, value)

    def block(self):
        from array import array

        buf = array("h", bytes(2 * self.m.sound.REFILL_SAMPLES))
        self.mixer.render(buf)
        self.master.apply(buf)
        self.samples.update(buf.tobytes())

    def digest(self):
        return self.samples.hexdigest()


def play_heard(table, heard, frames):
    """The cues a run emitted, played through the game's table in time: a cue of frame k before the first block that
    starts at or after k * FRAME_MS; frames * FRAME_MS of sound. None for a game with no cues."""
    if not table:
        return None
    m = modules()
    block_ms = 1000 * m.sound.REFILL_SAMPLES // m.sound.RATE
    out, at = CueSound(table), 0
    for block in range(frames * FRAME_MS // block_ms):
        while at < len(heard) and heard[at][0] * FRAME_MS <= block * block_ms:
            out.emit(heard[at][1], heard[at][2])
            at += 1
        out.block()
    return out.digest()


def record_subject(name, tier=FULL):
    """A subject's record, as its row plays it (the PNGs' and GIFs' settings of --all): the pinned frames' hashes,
    the chained runs, the frame of its game over and of its card, its cue table, its cues and their sound."""
    gfx, row = modules().gfx, ROWS[name]
    pinned, heard, hashes = counts(row, tier), CueRecorder(), {}
    last, run, run_to_5, over = pinned[-1], hashlib.sha256(), None, None
    for k, host in enumerate(render_scene.play(row, hold_ms=row.last * FRAME_MS, signals=heard), 1):
        run.update(host.tft.frame)
        if k == FAST_COUNTS[-1]:
            run_to_5 = run.hexdigest()
        game = host.game
        if over is None and game.state == gfx.OVER and tier == FULL:
            over = [k, k + -(-getattr(game, "CARD_MS", 0) // FRAME_MS) + CARD_MARGIN]
        if k in pinned or (over and k == over[1]):
            hashes[str(k)] = host.digest()
        if k == last:
            break
    table, cues = cue_table(game.cues), [list(c) for c in heard.heard]
    record = {"frames": hashes, "run_to_5": run_to_5, "table": table, "cues": cues}
    if tier == FULL:
        record.update(run=run.hexdigest(), over=over, sound=play_heard(table, cues, last))
    return record


def record_app():
    """The App level: the catalog's lineup on the host, its first game from start(), then a D14 pick of each next game
    through the whole lineup and back to the first. A pick is settled by a BOOT press in the next frame; once the game
    plays, it gets a BOOT press and APP_PLAY_FRAMES frames, and the last is hashed. Then HOLD_GAME is picked: BOOT
    starts it and is held HOLD_FRAMES frames, the game runs to its game over (hashed once OVER_MS passed), and a BOOT
    press then restarts it (hashed after APP_PLAY_FRAMES frames)."""
    m = modules()
    from test_pick import Box

    host = MacHost().start()
    random.seed(APP_SEED)

    class HostBox(Box):
        """Box on the host's clock: ticks_us counts on the frame clock, so the switch lines' times repeat. held is
        BOOT's level, which Box leaves as it is."""

        def frame(self, ms, d14=False, boot=False, held=False):
            host.clock.frame(ms)
            self.app.fire.held = held or boot
            return super().frame(ms, d14, boot)

        def step(self, **buttons):
            return self.frame(self.ms + FRAME_MS, **buttons)

    names = m.catalog.NAMES
    box = HostBox(games=m.app.Lineup(names), out=m.lcd.TftOut(host.tft))
    hashes = {}
    try:
        for n in range(len(names) + 1):
            if n:
                box.step(d14=True)
                box.step(boot=True)
                box.run_build()
            for k in range(APP_PLAY_FRAMES):
                box.step(boot=k == 0)
            hashes["%02d %s" % (n, box.app.game.name)] = host.digest()
        while box.app.games.names[box.app.index] != HOLD_GAME:  # --- the second script: hold, game over, restart
            box.step(d14=True)
        box.step(boot=True)
        game = box.run_build()
        box.step(boot=True)
        for _ in range(HOLD_FRAMES):
            box.step(held=True)
        for _ in range(OVER_LIMIT):
            if game.state == m.gfx.OVER:
                break
            box.step()
        else:
            raise NetError("%s did not reach its game over in %d frames" % (game.name, OVER_LIMIT))
        for _ in range(game.OVER_MS // FRAME_MS + CARD_MARGIN):
            box.step()
        hashes["%02d %s over" % (len(names) + 1, game.name)] = host.digest()
        box.step(boot=True)
        if game.state != m.gfx.PLAY:
            raise NetError("%s did not restart at a BOOT press after OVER_MS" % game.name)
        for _ in range(APP_PLAY_FRAMES):
            box.step()
        hashes["%02d %s restart" % (len(names) + 2, game.name)] = host.digest()
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
    """MIXER_CUES through CueSound, with the volume's step set at MIXER_STEPS: the samples' sha256."""
    full = modules().volume.FULL
    table = {name: [name, full, name == "hose", "sfx"] for _, name, _ in MIXER_CUES}
    table["land"][1] = full // 2  # one cue at half its gain
    out = CueSound(table)
    for block in range(MIXER_BLOCKS):
        if block in MIXER_STEPS:
            out.master.set(MIXER_STEPS[block])
        for _, name, value in (c for c in MIXER_CUES if c[0] == block):
            out.emit(name, value)
        out.block()
    return {"blocks": MIXER_BLOCKS, "sha256": out.digest()}


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
    child before the record, a negative test's change, with `m` the game box's modules (mac_host.modules())."""

    def __init__(self, name, tier=FULL, patch=""):
        self.name, self.tier, self.patch = name, tier, patch

    def cost(self):
        """The frames the job plays, about: the run starts the costliest first."""
        if self.name == APP:
            return APP_FRAMES
        row = ROWS.get(self.name)
        return 0 if row is None else counts(row, self.tier)[-1]

    def command(self):
        args = ["record", self.name, self.tier]
        if not self.patch:
            return [sys.executable, "-B", os.path.abspath(__file__), *args]
        code = "import sys\nsys.path.insert(0, %r)\nimport net\nm = net.modules()\n%s\nnet.main(%r)" % (
            HERE, self.patch, args)
        return [sys.executable, "-B", "-c", code]

    def run(self):
        env = dict(os.environ, PYTHONHASHSEED="0")  # a set's order, the same in every process
        done = subprocess.run(self.command(), cwd=ROOT, capture_output=True, text=True, env=env)
        lines = [line for line in done.stdout.splitlines() if line.startswith("NET ")]
        if done.returncode or not lines:
            raise NetError("the net's %s failed (exit %d): %s" % (self.name, done.returncode, done.stderr[-1500:]))
        return json.loads(lines[-1][4:])


def run(jobs, workers=WORKERS):
    """Each job's record, in the jobs' order, made workers at a time; the costliest jobs (Job.cost) start first."""
    order = sorted(range(len(jobs)), key=lambda i: -jobs[i].cost())
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures = {i: pool.submit(jobs[i].run) for i in order}
        return [futures[i].result() for i in range(len(jobs))]


def make(workers=WORKERS):
    """Every record of the full tier, with this Mac's toolchain: a Golden to write."""
    meta = Toolchain.here().record
    results = run([Job(name) for name in ROWS] + [Job(APP), Job(MIXER)], workers)
    return Golden(meta, dict(zip(ROWS, results)), results[-2], results[-1])


def main(argv):
    if len(argv) not in (2, 3) or argv[0] != "record":
        raise SystemExit("usage: net.py record JOB [fast|full]")
    print("NET " + json.dumps(record(argv[1], argv[2] if len(argv) > 2 else FULL), sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
