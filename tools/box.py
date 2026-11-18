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
A failed mpremote command prints its error and box.py exits with 1. Claude picks a lineup with list, then deploy NAME..., then log.
--- MVP (P817) ---"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
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


class Deploy:
    """Puts a lineup's games on the board through a runner: names, or None for every game and no lineup.py. With a
    compiler the modules go as .mpy files and main.py as itself; with None (--py) every module goes as its .py.
    crackle: the path of _crackle.mpy from the repository root (CRACKLE when None); say: where a note goes; sleep:
    the pause between the probe's tries (time.sleep when None); reference: REFERENCE for :engine_config.py
    (engine_reference's), or None to remove the board's file (P850)."""

    def __init__(self, runner, compiler=None, games=GAMES, crackle=None, say=print, sleep=None, reference=None,
                 volume=None):
        self.runner, self.compiler, self.games = runner, compiler, games  # games: the folder, named as games/<file>
        self.crackle, self.say = CRACKLE if crackle is None else crackle, say
        self.sleep, self.reference, self.volume = sleep or time.sleep, reference, volume

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
                   reference=reference, volume=step).run(None if args.all else args.names)
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
