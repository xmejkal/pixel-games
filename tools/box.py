"""The game box's lineup on the board (P817): which games the box plays, in which order, and a deploy that copies
every game's code but only the packs of the lineup's games (packs an earlier deploy copied stay on the board). A
lineup is the ordered names of the games the box plays (games/catalog.py names them all); the board keeps it in
:lineup.py as LINEUP, and app.read_lineup plays every game when there is none. Every board command goes through one
Mpremote runner. From the repository root:
    python3 tools/box.py list [--board]
    python3 tools/box.py deploy NAME... [--py] [--dry-run] [--engine reference[=PART,...]]
    python3 tools/box.py deploy --all [--py] [--dry-run] [--engine reference[=PART,...]]
    python3 tools/box.py log [--seconds N] [--port PORT]
list: each game of the catalog with its art sets and their bytes. --board also reads :lineup.py, which stops the
running game until the board resets.
deploy NAME...: the order of the names is the order the box plays them in. It refuses an unknown, a repeated or an
empty lineup before any command, and an mpy-cross that does not emit mpy v6.3, the board's .mpy version (P821). Then it
runs tools/firmware_probe.py on the board (P848), up to 3 tries while a running game keeps mpremote out, and refuses
a firmware whose C module is still named engine (flash the image of ./build.sh engine first), one that registers
engine beside _engine, one that lacks a name the games need of _engine (Bodies, HeatField, Balls, SoundBank,
HeatField.cool) and an answer it does not know; a firmware with no C module deploys, as the stock image.
Then it makes :packs when the board has none, compiles games/*.py but main.py with mpy-cross into .mpy files (they import in
about half the time of a .py), copies them with games/main.py and games/box_bank.raw (the sound bank) to : and removes
each :<module>.py that now has an .mpy (the board runs a .py before an .mpy of the same name). Each package of PACKAGES,
games/engine/ (P849) and games/drivers/ (P851), goes the same way into its folder, :engine/ or :drivers/, made when the
board has none, each traceback naming engine/<module>.py or drivers/<module>.py, and each .py or .mpy in that folder
that is not the package's goes. Then the .py and .mpy of each flat module that moved into a package (MOVED) go from the
root, after the packages are copied, so a failed copy leaves the old module; any other file at the root stays, the
board's boot.py among them. It copies the crackle,
engine/natmod/crackle/_crackle.mpy (tools/crackle.sh builds it), to :_crackle.mpy, or says none is copied when it is
not built; the board's crackle_c.mpy stays, for a flash of the rollback image. It copies each pack the
lineup needs to :packs (mpremote skips a file whose sha256 is the same), writes :lineup.py and hard-resets the board
(the picture pool is sized at boot). --engine (P850) forces the reference version of parts: `--engine reference` writes
REFERENCE = "all" to :engine_config.py, `--engine reference=volume` (or reference=sum,volume) the named parts; main.py
reads it at boot and its `engine` line says what it chose, such as `engine sum=viper volume=reference(forced)
native=_engine,_crackle.mpy`, with a forced name no part used at its end as unused=<name>. A deploy without --engine
removes :engine_config.py, so a forced setting lasts one deploy. A malformed value is refused before any command.
--py copies games/*.py, games/engine/*.py and games/drivers/*.py instead and removes the board's .mpy files of those
modules (_crackle.mpy and crackle_c.mpy stay). deploy --all copies every game and pack and removes :lineup.py when
the board has one. --dry-run prints each command and runs none, mpy-cross included, as for a board with no :packs, no
:engine, no :drivers, no :lineup.py, no :engine_config.py and no old .py or .mpy files, and never refuses the firmware. The .mpy files fit MicroPython v1.29's mpy v6.3: after a flash of another MicroPython, deploy
again (or with --py). mpy-cross: pip install mpy-cross==1.29.0.post2.
log: resets the board itself (a hard reset, trying again while the board still reboots from a deploy), then prints
its console for N seconds (20 by default), opening the port again while USB comes back: the `engine`, `lineup`,
`import`, `pick`, `game` and `switch` lines, each after the seconds since the log started, on the Mac's clock
(`12.345 pick runner`; logs from before P822 have none). The port is the one mpremote's auto picks: the first USB serial port, sorted.
A deploy tells spark's store (P921): after the last copy and before the reset it runs spark's launcher once, with
this Python, `<store>/launcher/bench.py record pixel-games --json`, which lists the boards on USB and opens no port,
and says one line: `spark's store: recorded pixel-games, <time>`, or `spark's store: not recorded (<reason>)` with
the code of spark's stop (no_port, two_boards, not_registered, launcher_stale, ...), no launcher, or no answer that
box.py can read, or `not known` after 30 s. The deploy goes on whatever the line says. After a recorded line, spark's
`bench.py show` names pixel-games for the box. <store> is SPARK_HOME, else XDG_DATA_HOME/spark, else
~/.local/share/spark. With no launcher there, register once (README, Build and run, step 5).
A failed mpremote command prints its error and box.py exits with 1. Claude picks a lineup with list, then deploy NAME..., then log.
--- MVP (P817) ---"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.join(ROOT, "games")
sys.path.insert(0, GAMES)
import art_index  # noqa: E402  pure data
import catalog  # noqa: E402  pure data
import volume  # noqa: E402  its STEPS, DEFAULT_STEP and the store's file (P866)

SECONDS = 20  # log's default
MPY = "6.3"  # the board's sys.implementation._mpy: version 6, sub-version 3; mpy-cross must emit this (P821)
MPY_CROSS_PIP = "pip install mpy-cross==1.29.0.post2"  # PyPI has no plain 1.29.0
RESET_TRIES, RESET_PAUSE_S = 5, 2  # log's reset, while the board still reboots from a deploy's reset
PROBE = "tools/firmware_probe.py"  # mpremote runs it on the board before a deploy (P848)
FIRMWARE_NAMES = ("Bodies", "HeatField", "Balls", "SoundBank", "HeatField.cool")  # what the games need of _engine
PROBE_TRIES = 3  # the probe, while a running game keeps mpremote out of the raw REPL (P848: the first try failed)
FLASH = "flash the image of ./build.sh engine first (README, Build and run)"
NO_ANSWER = "the board did not answer: close any mpremote or log session, press reset, and deploy again"
ENGINE_LINES = (["engine", "ImportError"], ["engine", "Bodies", "no"], ["engine", "Bodies", "yes"])
CRACKLE = "engine/natmod/crackle/_crackle.mpy"  # the crackle's native module, as tools/crackle.sh builds it (P848)
PACKAGES = ("engine", "drivers")  # the folders of games/ that go to the board as folders of the same name (P849, P851)
MOVED = ("signals", "buttons", "encoder")  # flat modules that moved into a package: the deploy removes their .py and
# .mpy at the root (P849; buttons and encoder into drivers, P851)
ENGINE_VALUE = re.compile(r"reference(=[a-z][a-z0-9_]*(,[a-z][a-z0-9_]*)*)?")  # --engine's whole value (P850)
SPARK_NAME = "pixel-games"  # the name this project has in spark's store, from spark's bench.py register (P921)
RECORD_S = 30  # the launcher's time limit; spark's own list of the boards stops at 15 s
SAYS = "spark's store: "  # how each line about the record starts
ENGINE_USAGE = "--engine takes reference or reference=PART[,PART...], each PART a lower-case name: got %r"


class Refused(Exception):
    """A lineup the box cannot play: nothing ran on the board."""


def engine_reference(value):
    """REFERENCE for :engine_config.py from --engine's value: "all" for `reference`, the part names of
    `reference=sum,volume` as a tuple. Refuses any other value, a repeated name and the name all. The names are not
    checked against main.py's parts: the boot line names a forced one that no part used as unused=."""
    if not ENGINE_VALUE.fullmatch(value):
        raise Refused(ENGINE_USAGE % value)
    if value == "reference":
        return "all"
    names = tuple(value.split("=", 1)[1].split(","))
    if len(set(names)) != len(names) or "all" in names:
        raise Refused(ENGINE_USAGE % value)
    return names


class Tool:
    """Runs one command of a tool from the repository root and answers its output; with dry_run it prints the command
    and runs nothing."""

    name = None

    def __init__(self, dry_run=False):
        self.dry_run = dry_run

    def run(self, args, timeout=None):
        """timeout: the seconds the command may take, or None for no limit. Past it subprocess.run kills the command
        and raises TimeoutExpired, whose output is the bytes read so far (P904: a probe's board run)."""
        if self.dry_run:
            print(" ".join([self.name] + args))
            return ""
        limit = {} if timeout is None else {"timeout": timeout}  # no limit: the call as before
        return subprocess.run([self.name] + args, cwd=ROOT, check=True, capture_output=True, text=True,
                              **limit).stdout

    def stream(self, args, each, timeout=None):
        """Runs the command from the repository root with its stdout and stderr as one stream, and calls each(line)
        for each line as it comes (P905: a probe's board run, so its log holds each line at once). Bytes that are
        not UTF-8, as a serial line gives at a reset, come replaced. Past timeout seconds it kills the command and
        raises TimeoutExpired, also when the command ended in that moment. A non-zero exit raises CalledProcessError.
        When each raises, or a KeyboardInterrupt or a SystemExit comes, it kills the command and the exception goes on.
        With dry_run it prints the command and calls nothing."""
        if self.dry_run:
            print(" ".join([self.name] + args))
            return
        command, killed = [self.name] + args, []
        proc = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace")

        def kill():
            killed.append(True)
            proc.kill()

        timer = threading.Timer(timeout, kill) if timeout is not None else None
        try:
            if timer:
                timer.daemon = True
                timer.start()
            for line in proc.stdout:
                each(line)
            proc.wait()
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        finally:
            if timer:
                timer.cancel()
            proc.stdout.close()
        if killed:  # the timer fired: past the limit
            raise subprocess.TimeoutExpired(command, timeout)
        if proc.returncode:
            raise subprocess.CalledProcessError(proc.returncode, command)


class Mpremote(Tool):
    """Every board command."""

    name = "mpremote"


class MpyCross(Tool):
    """The compiler of .mpy files: the pip package mpy-cross on PATH (P821)."""

    name = "mpy-cross"


def board_names(listing):
    """The names in the output of `mpremote ls :`, a folder's with its trailing /."""
    return {line.split()[-1] for line in listing.splitlines() if line.strip() and line.split()[0].isdigit()}


def firmware_fault(answer):
    """Why a deploy refuses the firmware that answered tools/firmware_probe.py, or None: the games can use its C, or
    it has none (the stock image, the games play without the C). The order of the name lines does not matter. Stage 9
    of the engine plan removes it (P848)."""
    rows = [line.split() for line in answer.strip().splitlines()]
    old = rows[-1:] == [ENGINE_LINES[2]]  # an engine with Bodies: the old C module
    if len(rows) == 2 and rows[0] == ["_engine", "ImportError"] and rows[1] in ENGINE_LINES:
        return "the board's C module is still named engine: " + FLASH if old else None
    said = {row[1]: row[2] for row in rows[:-1] if len(row) == 3 and row[0] == "_engine" and row[2] in ("yes", "no")}
    if len(rows) - 1 == len(said) == len(FIRMWARE_NAMES) and set(said) == set(FIRMWARE_NAMES) and \
            rows[-1] in ENGINE_LINES:
        if old:
            return "the firmware registers engine beside _engine, so a package engine cannot load: flash the image " \
                   "of a clean ./build.sh engine first (README, Build and run)"
        lacks = [name for name in FIRMWARE_NAMES if said[name] == "no"]
        return "the firmware lacks %s: %s" % (", ".join(lacks), FLASH) if lacks else None
    return "unknown firmware answer: %r: flash the image of ./build.sh engine (README, Build and run), or run " \
           "`mpremote run tools/firmware_probe.py` and read it" % answer.strip()


def sets_for(names):
    """The art sets the games of names load, each once, in the lineup's order."""
    return tuple(dict.fromkeys(s for name in names for s in catalog.ROWS[name][3]))


class Compiler:
    """Compiles game modules into .mpy files with mpy-cross (P821), each for the board's chip (-march=xtensawin, which
    the viper modules need and which leaves bytecode files as they are), with -s <name>.py so a traceback names the
    module. tool: an MpyCross, or a test's fake; a dry-run tool compiles nothing."""

    def __init__(self, tool):
        self.tool = tool

    def check(self):
        """Refuses an mpy-cross that does not emit the board's .mpy version."""
        said = self.tool.run(["--version"])
        found = re.search(r"mpy v(\d+\.\d+)", said)
        if not self.tool.dry_run and (found is None or found.group(1) != MPY):
            raise Refused("mpy-cross emits %s, the board needs mpy v%s: %s" % (
                found.group(0) if found else repr(said.strip()), MPY, MPY_CROSS_PIP))

    def compile(self, sources, folder, package=""):
        """Each source (games/<name>.py, or games/<package>/<name>.py) compiled to folder/<name>.mpy, its traceback
        name <name>.py, or <package>/<name>.py; answers the .mpy paths."""
        out = []
        for source in sources:
            name = os.path.basename(source)
            out.append(os.path.join(folder, name[:-3] + ".mpy"))
            self.tool.run(["-march=xtensawin", "-s", package + "/" + name if package else name, "-o", out[-1], source])
        return out


def spark_store(environ=None):
    """spark's store folder, where spark itself looks: SPARK_HOME, else XDG_DATA_HOME/spark, else
    ~/.local/share/spark. An empty value counts as unset."""
    environ = os.environ if environ is None else environ
    return environ.get("SPARK_HOME") or os.path.join(
        environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "spark")


def record_said(stdout):
    """What spark's `bench.py record --json` answered, for a person: its envelope is the last line of stdout. Only the
    entry's time or the stop's code is said: the envelope also holds the board's MAC and port, and logs/ is public.
    It decides on the status and the code, never on a sentence. Raises when the answer has another shape."""
    answer = json.loads(stdout.strip().splitlines()[-1])
    if answer["status"] == "ok":
        deployed = answer["data"]["entry"]["deployed"]  # spark's clock: 2026-11-19T10:15:00+01:00
        if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d([+-]\d\d:\d\d)?", deployed):
            return "recorded %s, %s" % (SPARK_NAME, deployed)
    else:
        code = answer["unchecked"][0]["code"]
        if re.fullmatch(r"[a-z_]+", code):
            return "not recorded (%s)" % code
    raise ValueError("neither a time nor a code")


class SparkLauncher:
    """spark's launcher in spark's store (folder), which bench.py register wrote: it runs spark's bench.py from any
    folder with any python3 (P921). run: subprocess.run when None, looked up at the call; with dry_run record
    answers the command, with <store> for the folder, and runs nothing."""

    def __init__(self, folder, run=None, dry_run=False):
        self.folder, self.run, self.dry_run = os.path.abspath(folder), run, dry_run  # whole: record runs from ROOT

    def record(self):
        """Tells spark's store that this project deployed to the board on USB, and answers the line to say. It
        never raises: a record that could not run leaves the deploy as it is."""
        if self.dry_run:
            return "python3 <store>/launcher/bench.py record %s --json" % SPARK_NAME
        script = os.path.join(self.folder, "launcher", "bench.py")
        if not os.path.isfile(script):
            return SAYS + "not recorded (no launcher: run spark's bench.py register for %s)" % SPARK_NAME
        try:
            done = (self.run or subprocess.run)(
                [sys.executable, script, "record", SPARK_NAME, "--json"], cwd=ROOT, capture_output=True, text=True,
                errors="replace", stdin=subprocess.DEVNULL, timeout=RECORD_S)  # no check: a stop exits 2
            return SAYS + record_said(done.stdout)
        except subprocess.TimeoutExpired:  # the launcher's own child can still write the entry
            return SAYS + "not known (time limit of %d s)" % RECORD_S
        except Exception:  # whatever the answer was, the deploy goes on; no text of the error: it can hold a path
            return SAYS + "not recorded (no answer that box.py can read)"


class Deploy:
    """Puts a lineup's games on the board through a runner: names, or None for every game and no lineup.py. With a
    compiler the modules go as .mpy files and main.py as itself; with None (--py) every module goes as its .py.
    crackle: the path of _crackle.mpy from the repository root (CRACKLE when None); say: where a note goes; sleep:
    the pause between the probe's tries (time.sleep when None); reference: REFERENCE for :engine_config.py
    (engine_reference's), or None to remove the board's file (P850); launcher: a SparkLauncher that records the
    deploy in spark's store after the last copy, or None to record nothing (P921)."""

    def __init__(self, runner, compiler=None, games=GAMES, crackle=None, say=print, sleep=None, reference=None,
                 volume=None, launcher=None):
        self.runner, self.compiler, self.games = runner, compiler, games  # games: the folder, named as games/<file>
        self.crackle, self.say = CRACKLE if crackle is None else crackle, say
        self.sleep, self.reference, self.volume = sleep or time.sleep, reference, volume
        self.launcher = launcher

    def run(self, names):
        if names is not None:
            names = tuple(names)
            why = catalog.lineup_fault(names)
            if why:
                raise Refused(why)
        if self.compiler:
            self.compiler.check()  # before any board command
        self.check_firmware()
        on_board = board_names(self.runner.run(["ls", ":"]))
        if "packs/" not in on_board:
            self.runner.run(["mkdir", ":packs"])
        self.copy_code(on_board)
        for package in PACKAGES:
            self.copy_package(package, package + "/" in on_board)
        self.remove([":%s%s" % (m, kind) for m in MOVED for kind in (".py", ".mpy") if m + kind in on_board])
        self.copy_crackle()
        for s in sets_for(catalog.NAMES if names is None else names):
            path = art_index.PACKS[s][0]
            self.runner.run(["cp", "games/" + path, ":" + path])
        if names is not None:
            self.write_lineup(names)
        elif "lineup.py" in on_board:
            self.runner.run(["rm", ":lineup.py"])
        if self.reference is not None:
            self.write_config(self.reference)
        elif "engine_config.py" in on_board:  # a forced setting lasts one deploy
            self.runner.run(["rm", ":engine_config.py"])
        if self.volume is not None:  # the start step (P866); without --volume the board keeps its own
            write_file(self.runner, VOLUME_FILE, str(self.volume))
        if self.launcher:  # before the reset: the board is on USB for certain, and the record opens no port
            self.say(self.launcher.record())
        self.runner.run(["reset"])

    def copy_code(self, on_board):
        """The modules as .mpy files, then the board's .py of each goes; or (no compiler) as .py files, then the
        board's .mpy of each goes. main.py and the sound bank go as they are. Any other file at the root stays (the
        board's boot.py, which MicroPython wrote); run removes the modules of MOVED once their package is copied."""
        sources = sorted(n for n in os.listdir(self.games) if n.endswith(".py"))
        modules = [n[:-3] for n in sources if n != "main.py"]
        if self.compiler is None:
            self.runner.run(["cp"] + ["games/" + n for n in sources] + ["games/box_bank.raw", ":"])
            stale = [n[:-3] + ".mpy" for n in sources]
        else:
            with tempfile.TemporaryDirectory() as tmp:
                compiled = self.compiler.compile(["games/%s.py" % m for m in modules], tmp)
                self.runner.run(["cp"] + compiled + ["games/main.py", "games/box_bank.raw", ":"])
            stale = [m + ".py" for m in modules]
        self.remove([":" + n for n in stale if n in on_board])

    def copy_package(self, package, has_folder):
        """games/<package>/*.py into the folder :<package>/, made when the board has none (has_folder False): as .mpy
        files, or (no compiler) as .py files. Then each .py or .mpy in the folder that is not one of these goes: a .py
        that now has an .mpy (the board runs the .py first), an .mpy after a deploy with --py, and a module whose
        source is gone."""
        folder = os.path.join(self.games, package)
        sources = sorted(n for n in os.listdir(folder) if n.endswith(".py"))
        if self.compiler is None:
            self.make_folder(package, has_folder)
            self.runner.run(["cp"] + ["games/%s/%s" % (package, n) for n in sources] + [":%s/" % package])
            kept = sources
        else:
            with tempfile.TemporaryDirectory() as tmp:
                compiled = self.compiler.compile(["games/%s/%s" % (package, n) for n in sources], tmp, package)
                self.make_folder(package, has_folder)
                self.runner.run(["cp"] + compiled + [":%s/" % package])
            kept = [n[:-3] + ".mpy" for n in sources]
        if has_folder:
            there = board_names(self.runner.run(["ls", ":" + package]))
            self.remove(sorted(":%s/%s" % (package, n) for n in there
                               if n.endswith((".py", ".mpy")) and n not in kept))

    def make_folder(self, package, has_folder):
        if not has_folder:
            self.runner.run(["mkdir", ":" + package])

    def remove(self, paths):
        """The board's files at paths, if any."""
        if not paths:
            return
        try:
            self.runner.run(["rm"] + paths)
        except subprocess.CalledProcessError as e:
            if self.compiler:  # the board runs a .py before an .mpy of the same name
                e.stderr = "%s; deploy again: until then the board runs the old .py of some modules" % (
                    (e.stderr or "").strip())
            raise

    def check_firmware(self):
        """Refuses the board's firmware by firmware_fault, before any other board command, after PROBE_TRIES tries
        that mpremote could not run. A dry run never refuses."""
        try:
            answer = retried(self.runner, ["run", PROBE], PROBE_TRIES, RESET_PAUSE_S, self.sleep)
        except subprocess.CalledProcessError as e:
            said = [line for line in (e.stderr or "").splitlines() if line.strip()]
            e.stderr = "%s; %s" % (said[-1].strip() if said else "exit %d" % e.returncode, NO_ANSWER)
            raise
        if self.runner.dry_run:
            return
        fault = firmware_fault(answer)
        if fault:
            raise Refused(fault)

    def copy_crackle(self):
        """_crackle.mpy to :_crackle.mpy when it is built; the board's crackle_c.mpy stays until stage 9, so a flash of
        the rollback image keeps its crackle."""
        if os.path.isfile(os.path.join(ROOT, self.crackle)):
            self.runner.run(["cp", self.crackle, ":_crackle.mpy"])
        else:
            self.say("no _crackle.mpy built, so none is copied: tools/crackle.sh builds it")

    def write_lineup(self, names):
        self.write("lineup.py", "LINEUP = %r  # tools/box.py deploy (P817)\n" % (names,))

    def write_config(self, reference):
        self.write("engine_config.py", "REFERENCE = %s  # tools/box.py deploy --engine\n" % (
            '"all"' if reference == "all" else repr(reference)))

    def write(self, name, text):
        """A file of text at :<name>."""
        write_file(self.runner, name, text)


def write_file(runner, name, text):
    """A file of text at :<name>, through the runner."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, name)
        with open(path, "w") as f:
            f.write(text)
        runner.run(["cp", path, ":" + name])


VOLUME_FILE = volume.VolumeStore().path  # the step the box starts at: volume.VolumeStore reads it at boot


def volume_step(text):
    """The volume step in text: a whole number from 0 (silent) to volume.STEPS (full). Refused otherwise, before any
    board command (P866)."""
    if not re.fullmatch(r"[0-9]{1,2}", text) or int(text) > volume.STEPS:
        raise Refused("volume is a step from 0 (silent) to %d (full), not %r" % (volume.STEPS, text))
    return int(text)


class Volume:
    """The box's start volume from the Mac (P866): set writes the step that main.py reads once at boot (through
    volume.VolumeStore), then resets the board, so it starts at that step; show reads it. 0 starts the box silent, for
    work without sound. The knob still turns the volume while the box runs but saves nothing."""

    def __init__(self, runner):
        self.runner = runner

    def set(self, step):
        write_file(self.runner, VOLUME_FILE, str(step))
        self.runner.run(["reset"])

    def show(self):
        if VOLUME_FILE not in board_names(self.runner.run(["ls", ":"])):
            return "board: no %s, so the box starts at step %d" % (VOLUME_FILE, volume.DEFAULT_STEP)
        text = self.runner.run(["cat", ":" + VOLUME_FILE]).strip()
        try:
            return "board: volume step %d" % volume_step(text)
        except Refused:
            return "board: %s holds %r, which the box ignores: it starts at step %d" % (VOLUME_FILE, text,
                                                                                         volume.DEFAULT_STEP)


def catalog_lines():
    """One line per game of the catalog: its name, then each art set with its pack's bytes, or none."""
    lines = []
    for name, module, class_name, sets in catalog.CATALOG:
        art = ", ".join("%s %d B" % (s, art_index.PACKS[s][1]) for s in sets) or "no art"
        lines.append("%-12s %s" % (name, art))
    return lines


def board_lineup(runner):
    """What the board's :lineup.py says, or that it has none."""
    if "lineup.py" not in board_names(runner.run(["ls", ":"])):
        return "board: no lineup.py, so it plays every game"
    return "board: " + runner.run(["cat", ":lineup.py"]).strip()


def retried(runner, args, tries, pause, sleep):
    """The runner's answer to args, tried again after pause while mpremote cannot reach the board."""
    for i in range(tries):
        try:
            return runner.run(args)
        except subprocess.CalledProcessError:
            if i == tries - 1:
                raise
            sleep(pause)


def reset(runner, tries=RESET_TRIES, pause=RESET_PAUSE_S, sleep=time.sleep):
    """A hard reset through the runner, tried again after pause while mpremote cannot reach the board yet."""
    return retried(runner, ["reset"], tries, pause, sleep)


class Console:
    """The board's console over USB for some seconds, line by line (pyserial, as mpremote uses it). The port is
    opened again while USB comes back after a reset. open_port answers an object with readline() and close()."""

    def __init__(self, open_port, clock=time.monotonic, sleep=time.sleep):
        self.open_port, self.clock, self.sleep = open_port, clock, sleep

    def lines(self, seconds):
        end, port = self.clock() + seconds, None
        while self.clock() < end:
            try:
                port = port or self.open_port()
                line = port.readline()
            except OSError:  # USB gone: the board is resetting
                port = self.close(port)
                self.sleep(0.2)
                continue
            if line:
                yield line.decode("utf-8", "replace").rstrip()
        self.close(port)

    @staticmethod
    def close(port):
        if port:
            try:
                port.close()
            except OSError:
                pass
        return None


def stamped(lines, clock=time.monotonic):
    """Each of lines after the seconds since the log started, on the Mac's clock: `12.345 pick runner` (P822)."""
    start = clock()
    for line in lines:
        yield "%.3f %s" % (clock() - start, line)


def serial_port(name=None):
    """A function that opens the board's port: name, or the first USB serial port mpremote would pick."""
    import serial
    from serial.tools import list_ports

    def open_port():
        found = name or next((p.device for p in sorted(list_ports.comports())
                              if p.vid is not None and p.pid is not None), None)  # mpremote's auto
        if found is None:
            raise OSError("no board on USB")
        return serial.Serial(found, 115200, timeout=0.2)
    return open_port


class ProbeRun:
    """For a probe's Mac part: one file run once on the box through a runner (an Mpremote, or a test's) within a time
    limit, its lines kept (P905, from P904's probe). run(path, limit_s) opens the first free log before the command
    starts, then prints each line as it comes and writes it to the log at once, so a Ctrl-C or a killed Mac session
    keeps every line that came. It answers how the run ended: DONE (the file ended), LIMIT (the limit stopped mpremote;
    the box runs on until a reset) or FAILED (mpremote failed: the file raised, or the board did not answer). The caller
    decides what each end means. lines: the run's lines, stripped, with no blank one; logged: the log's path, or None (a
    dry run writes none); why: how a LIMIT or a FAILED came, or None. A missing mpremote raises FileNotFoundError and
    leaves no log."""

    DONE, LIMIT, FAILED = 1, 2, 3

    def __init__(self, runner, log):
        self.runner, self.log = runner, log  # log: the first log's path (free_log picks the one written)
        self.lines, self.logged, self.why, self.file = [], None, None, None

    def run(self, path, limit_s):
        self.lines, self.why, end = [], None, self.DONE
        if not self.runner.dry_run:
            self.logged = self.free_log(self.log)
            self.file = open(self.logged, "w", encoding="utf-8")
        try:
            self.runner.stream(["run", path], self.keep, timeout=limit_s)
        except subprocess.TimeoutExpired as e:
            end, self.why = self.LIMIT, "the run took over %d s" % e.timeout
        except subprocess.CalledProcessError as e:
            end, self.why = self.FAILED, "the run failed with exit %d" % e.returncode
        except FileNotFoundError:
            self.close()
            if self.logged:
                os.remove(self.logged)  # empty: the command never started
                self.logged = None
            raise
        finally:
            self.close()
        return end

    def keep(self, line):
        """One line of the run: stripped, a blank one dropped, kept, written to the log at once and then printed, so a
        print that fails (a broken pipe, a closed terminal) loses no line of the log."""
        line = line.strip()
        if not line:
            return
        self.lines.append(line)
        if self.file:
            self.file.write(line + "\n")
            self.file.flush()
        print(line, flush=True)

    def close(self):
        if self.file:
            self.file.close()
            self.file = None

    @staticmethod
    def free_log(path):
        """path, or the first of its -2, -3, ... that no file has: a later run never overwrites a log."""
        stem, ext = os.path.splitext(path)
        k = 1
        while os.path.exists(path):
            k += 1
            path = "%s-%d%s" % (stem, k, ext)
        return path


class LentPack:
    """For a probe's Mac part: a pack that the box has for one sitting, through a runner (an Mpremote, or a test's)
    (P906, the copy and the clean of P904's probe). The set's pack goes to :packs/<name>.pak and its index to
    :art_index.py, the shadow index: the board imports a .py before the .mpy of the same name, so the pool is made as
    big as this pack alone, and meanwhile the lineup's games find no art. check() refuses a box that has an
    :art_index.py, before any copy, as the removal would delete it. lend(pack, index) copies the pack first, so a failed
    copy leaves no index that names it. remove() removes each copy that the box holds (a dry run's box holds both): the
    caller's in every case once lend began. The reads and the removal are tried again while a running probe keeps
    mpremote out. The resets are the caller's. sleep: the pause between two tries."""

    INDEX = "art_index.py"

    def __init__(self, runner, name, sleep=time.sleep):
        self.runner, self.sleep, self.pack = runner, sleep, "packs/%s.pak" % name

    def tried(self, args):
        return retried(self.runner, args, PROBE_TRIES, RESET_PAUSE_S, self.sleep)

    def recovery(self):
        """The way out by hand when the removal failed."""
        return "`mpremote rm :%s :%s`, then `mpremote reset`" % (self.INDEX, self.pack)

    def check(self):
        if self.INDEX in board_names(self.tried(["ls", ":"])):
            raise Refused("the box has an :%s. It is its real index (a deploy with --py: deploy without --py first) "
                          "or a shadow index that a failed removal left (remove it: %s)" % (self.INDEX,
                                                                                           self.recovery()))

    def lend(self, pack, index):
        self.runner.run(["cp", pack, ":" + self.pack])
        self.runner.run(["cp", index, ":" + self.INDEX])

    def remove(self):
        dry = self.runner.dry_run
        root = board_names(self.tried(["ls", ":"]))
        folder, name = self.pack.split("/")
        packs = board_names(self.tried(["ls", ":" + folder])) if dry or folder + "/" in root else set()
        there = [":" + path for path, names, file in ((self.INDEX, root, self.INDEX), (self.pack, packs, name))
                 if dry or file in names]
        if there:
            self.tried(["rm"] + there)


def failure(e):
    """The line that says a tool's command failed (a CalledProcessError) or that the tool is missing (a
    FileNotFoundError: mpremote or mpy-cross)."""
    if isinstance(e, FileNotFoundError):
        return "no %s: %s" % (e.filename or "mpremote", e)
    return "%s failed: %s" % (" ".join(e.cmd), (e.stderr or "").strip() or "exit %d" % e.returncode)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    shown = sub.add_parser("list", help="the catalog's games and their art")
    shown.add_argument("--board", action="store_true", help="also read :lineup.py (stops the running game until "
                                                            "the board resets)")
    deploy = sub.add_parser("deploy", help="copy the games' code and the lineup's packs, write :lineup.py")
    deploy.add_argument("names", nargs="*", metavar="NAME", help="the lineup: the box plays them in this order")
    deploy.add_argument("--all", action="store_true", help="every game, and no :lineup.py")
    deploy.add_argument("--py", action="store_true", help="copy the .py sources, not .mpy files built by mpy-cross: "
                                                         "to debug on the board, where a traceback then shows the "
                                                         "source line and a file can be edited in place")
    deploy.add_argument("--dry-run", action="store_true", help="print each command, run none")
    deploy.add_argument("--engine", metavar="reference[=PART,...]",
                        help="force the reference version of every part (reference) or of the named parts "
                             "(reference=volume) in :engine_config.py; a deploy without it removes the file")
    deploy.add_argument("--volume", metavar="STEP",
                        help="the step the box starts at, 0 (silent) to %d (full), written to :%s; without it the "
                             "board keeps its own" % (volume.STEPS, VOLUME_FILE))
    loud = sub.add_parser("volume", help="the box's start volume: with STEP, write it and reset the board (0 is "
                                         "silent, for work without sound); alone, print the board's step")
    loud.add_argument("step", nargs="?", metavar="STEP", help="0 (silent) to %d (full); none: print the board's step"
                                                              % volume.STEPS)
    log = sub.add_parser("log", help="reset the board (a hard reset), then print its console, each line after the "
                                     "seconds since the log started")
    log.add_argument("--seconds", type=float, default=SECONDS)
    log.add_argument("--port", help="the serial port (default: the first USB one)")
    args = parser.parse_args(argv)
    if args.command == "deploy" and args.all == bool(args.names):
        parser.error("deploy takes NAME... or --all")
    try:
        if args.command == "list":
            print("\n".join(catalog_lines()))
            if args.board:
                print(board_lineup(Mpremote()))
        elif args.command == "deploy":
            reference = None if args.engine is None else engine_reference(args.engine)  # before any command
            step = None if args.volume is None else volume_step(args.volume)
            Deploy(Mpremote(args.dry_run), None if args.py else Compiler(MpyCross(args.dry_run)),
                   reference=reference, volume=step,
                   launcher=SparkLauncher(spark_store(), dry_run=args.dry_run)).run(None if args.all else args.names)
        elif args.command == "volume":
            if args.step is None:
                print(Volume(Mpremote()).show())
            else:
                step = volume_step(args.step)  # before any command
                Volume(Mpremote()).set(step)
                print("volume step %d written; the board resets and starts at it" % step)
        else:
            reset(Mpremote())
            for line in stamped(Console(serial_port(args.port)).lines(args.seconds)):
                print(line)
    except Refused as e:
        print("refused:", e)
        return 1
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(failure(e))
        if isinstance(e, FileNotFoundError) and e.filename == MpyCross.name:
            print("install it:", MPY_CROSS_PIP)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
