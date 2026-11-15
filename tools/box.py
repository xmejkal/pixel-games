"""The game box's lineup on the board (P817): which games the box plays, in which order, and a deploy that copies
every game's code but only the packs of the lineup's games (packs an earlier deploy copied stay on the board). A
lineup is the ordered names of the games the box plays (games/catalog.py names them all); the board keeps it in
:lineup.py as LINEUP, and app.read_lineup plays every game when there is none. Every board command goes through one
Mpremote runner. From the repository root:
    python3 tools/box.py list [--board]
    python3 tools/box.py deploy NAME... [--py] [--dry-run]
    python3 tools/box.py deploy --all [--py] [--dry-run]
    python3 tools/box.py log [--seconds N] [--port PORT]
list: each game of the catalog with its art sets and their bytes. --board also reads :lineup.py, which stops the
running game until the board resets.
deploy NAME...: the order of the names is the order the box plays them in. It refuses an unknown, a repeated or an
empty lineup before any command, and an mpy-cross that does not emit mpy v6.3, the board's .mpy version (P821). Then it
makes :packs when the board has none, compiles games/*.py but main.py with mpy-cross into .mpy files (they import in
about half the time of a .py), copies them with games/main.py and games/box_bank.raw (the sound bank) to : and removes
each :<module>.py that now has an .mpy (the board runs a .py before an .mpy of the same name). It copies each pack the
lineup needs to :packs (mpremote skips a file whose sha256 is the same), writes :lineup.py and hard-resets the board
(the picture pool is sized at boot). --py copies games/*.py instead and removes the board's .mpy files of those
modules (crackle_c.mpy stays). deploy --all copies every game and pack and removes :lineup.py when the board has one.
--dry-run prints each command and runs none, mpy-cross included, as for a board with no :packs, no :lineup.py and no
old .py or .mpy files. The .mpy files fit MicroPython v1.29's mpy v6.3: after a flash of another MicroPython, deploy
again (or with --py). mpy-cross: pip install mpy-cross==1.29.0.post2.
log: resets the board itself (a hard reset, trying again while the board still reboots from a deploy), then prints
its console for N seconds (20 by default), opening the port again while USB comes back: the `lineup`, `import`,
`game` and `switch` lines. The port is the one mpremote's auto picks: the first USB serial port, sorted.
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

SECONDS = 20  # log's default
MPY = "6.3"  # the board's sys.implementation._mpy: version 6, sub-version 3; mpy-cross must emit this (P821)
MPY_CROSS_PIP = "pip install mpy-cross==1.29.0.post2"  # PyPI has no plain 1.29.0
RESET_TRIES, RESET_PAUSE_S = 5, 2  # log's reset, while the board still reboots from a deploy's reset


class Refused(Exception):
    """A lineup the box cannot play: nothing ran on the board."""


class Tool:
    """Runs one command of a tool from the repository root and answers its output; with dry_run it prints the command
    and runs nothing."""

    name = None

    def __init__(self, dry_run=False):
        self.dry_run = dry_run

    def run(self, args):
        if self.dry_run:
            print(" ".join([self.name] + args))
            return ""
        return subprocess.run([self.name] + args, cwd=ROOT, check=True, capture_output=True, text=True).stdout


class Mpremote(Tool):
    """Every board command."""

    name = "mpremote"


class MpyCross(Tool):
    """The compiler of .mpy files: the pip package mpy-cross on PATH (P821)."""

    name = "mpy-cross"


def board_names(listing):
    """The names in the output of `mpremote ls :`, a folder's with its trailing /."""
    return {line.split()[-1] for line in listing.splitlines() if line.strip() and line.split()[0].isdigit()}


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

    def compile(self, sources, folder):
        """Each source (games/<name>.py) compiled to folder/<name>.mpy; answers the .mpy paths."""
        out = []
        for source in sources:
            name = os.path.basename(source)
            out.append(os.path.join(folder, name[:-3] + ".mpy"))
            self.tool.run(["-march=xtensawin", "-s", name, "-o", out[-1], source])
        return out


class Deploy:
    """Puts a lineup's games on the board through a runner: names, or None for every game and no lineup.py. With a
    compiler the modules go as .mpy files and main.py as itself; with None (--py) every module goes as its .py."""

    def __init__(self, runner, compiler=None, games=GAMES):
        self.runner, self.compiler, self.games = runner, compiler, games  # games: the folder, named as games/<file>

    def run(self, names):
        if names is not None:
            names = tuple(names)
            why = catalog.lineup_fault(names)
            if why:
                raise Refused(why)
        if self.compiler:
            self.compiler.check()  # before any board command
        on_board = board_names(self.runner.run(["ls", ":"]))
        if "packs/" not in on_board:
            self.runner.run(["mkdir", ":packs"])
        self.copy_code(on_board)
        for s in sets_for(catalog.NAMES if names is None else names):
            path = art_index.PACKS[s][0]
            self.runner.run(["cp", "games/" + path, ":" + path])
        if names is not None:
            self.write_lineup(names)
        elif "lineup.py" in on_board:
            self.runner.run(["rm", ":lineup.py"])
        self.runner.run(["reset"])

    def copy_code(self, on_board):
        """The modules as .mpy files, then the board's .py of each goes; or (no compiler) as .py files, then the
        board's .mpy of each goes. main.py and the sound bank go as they are."""
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
        stale = [":" + n for n in stale if n in on_board]
        if stale:
            try:
                self.runner.run(["rm"] + stale)
            except subprocess.CalledProcessError as e:
                if self.compiler:  # the board runs a .py before an .mpy of the same name
                    e.stderr = "%s; deploy again: until then the board runs the old .py of some modules" % (
                        (e.stderr or "").strip())
                raise

    def write_lineup(self, names):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "lineup.py")
            with open(path, "w") as f:
                f.write("LINEUP = %r  # tools/box.py deploy (P817)\n" % (names,))
            self.runner.run(["cp", path, ":lineup.py"])


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


def reset(runner, tries=RESET_TRIES, pause=RESET_PAUSE_S, sleep=time.sleep):
    """A hard reset through the runner, tried again after pause while mpremote cannot reach the board yet."""
    for i in range(tries):
        try:
            return runner.run(["reset"])
        except subprocess.CalledProcessError:
            if i == tries - 1:
                raise
            sleep(pause)


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
    log = sub.add_parser("log", help="reset the board (a hard reset), then print its console")
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
            Deploy(Mpremote(args.dry_run), None if args.py else Compiler(MpyCross(args.dry_run))).run(
                None if args.all else args.names)
        else:
            reset(Mpremote())
            for line in Console(serial_port(args.port)).lines(args.seconds):
                print(line)
    except Refused as e:
        print("refused:", e)
        return 1
    except subprocess.CalledProcessError as e:
        print("%s failed: %s" % (" ".join(e.cmd), (e.stderr or "").strip() or "exit %d" % e.returncode))
        return 1
    except FileNotFoundError as e:
        print("no %s:" % (e.filename or "mpremote"), e)  # mpremote or mpy-cross
        if e.filename == MpyCross.name:
            print("install it:", MPY_CROSS_PIP)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
