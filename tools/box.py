"""The game box's lineup on the board (P817): which games the box holds, and a deploy that copies only theirs. A
lineup is the ordered names of the games the box plays (games/catalog.py names them all); the board keeps it in
:lineup.py as LINEUP, and app.read_lineup plays every game when there is none. Every board command goes through one
Mpremote runner. From the repository root:
    python3 tools/box.py list [--board]
    python3 tools/box.py deploy NAME... [--dry-run]
    python3 tools/box.py deploy --all [--dry-run]
    python3 tools/box.py log [--seconds N] [--port PORT]
list: each game of the catalog with its art sets and their bytes. --board also reads :lineup.py, which stops the
running game until the board resets.
deploy NAME...: refuses an unknown, a repeated or an empty lineup before any command; then makes :packs when the board
has none, copies games/*.py and games/box_bank.raw (the sound bank) to :, each pack the lineup needs to :packs (mpremote
skips a file whose sha256 is the same), writes :lineup.py and hard-resets the board (the picture pool is sized at boot).
deploy --all copies every game and pack and removes :lineup.py when the board has one. --dry-run prints each command
and runs none, as for a board with no :packs and no :lineup.py.
log: resets the board, then prints its console for N seconds (20 by default), opening the port again while USB comes
back: the `lineup`, `import`, `game` and `switch` lines. Claude picks a lineup with list, then deploy NAME..., then log.
--- MVP (P817) ---"""

import argparse
import os
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


class Refused(Exception):
    """A lineup the box cannot play: nothing ran on the board."""


class Mpremote:
    """Runs one mpremote command from the repository root and answers its output; with dry_run it prints the command
    and runs nothing."""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run

    def run(self, args):
        if self.dry_run:
            print("mpremote " + " ".join(args))
            return ""
        return subprocess.run(["mpremote"] + args, cwd=ROOT, check=True, capture_output=True, text=True).stdout


def board_names(listing):
    """The names in the output of `mpremote ls :`, a folder's with its trailing /."""
    return {line.split()[-1] for line in listing.splitlines() if line.strip() and line.split()[0].isdigit()}


def sets_for(names):
    """The art sets the games of names load, each once, in the lineup's order."""
    rows = {row[0]: row for row in catalog.CATALOG}
    return tuple(dict.fromkeys(s for name in names for s in rows[name][3]))


class Deploy:
    """Puts a lineup's games on the board through a runner: names, or None for every game and no lineup.py."""

    def __init__(self, runner, games=GAMES):
        self.runner, self.games = runner, games  # games: the folder whose files go, named as games/<file>

    def run(self, names):
        if names is not None:
            names = tuple(names)
            why = catalog.lineup_fault(names)
            if why:
                raise Refused(why)
        on_board = board_names(self.runner.run(["ls", ":"]))
        if "packs/" not in on_board:
            self.runner.run(["mkdir", ":packs"])
        sources = ["games/" + n for n in sorted(os.listdir(self.games)) if n.endswith(".py")] + ["games/box_bank.raw"]
        self.runner.run(["cp"] + sources + [":"])
        for s in sets_for(catalog.NAMES if names is None else names):
            path = art_index.PACKS[s][0]
            self.runner.run(["cp", "games/" + path, ":" + path])
        if names is not None:
            self.write_lineup(names)
        elif "lineup.py" in on_board:
            self.runner.run(["rm", ":lineup.py"])
        self.runner.run(["reset"])

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
        found = name or next((p.device for p in list_ports.comports() if p.vid), None)
        if found is None:
            raise OSError("no board on USB")
        return serial.Serial(found, 115200, timeout=0.2)
    return open_port


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    shown = sub.add_parser("list", help="the catalog's games and their art")
    shown.add_argument("--board", action="store_true", help="also read :lineup.py (stops the running game until "
                                                            "the board resets)")
    deploy = sub.add_parser("deploy", help="copy a lineup's games and write :lineup.py")
    deploy.add_argument("names", nargs="*", metavar="NAME")
    deploy.add_argument("--all", action="store_true", help="every game, and no :lineup.py")
    deploy.add_argument("--dry-run", action="store_true", help="print each command, run none")
    log = sub.add_parser("log", help="reset the board and print its console")
    log.add_argument("--seconds", type=float, default=SECONDS)
    log.add_argument("--port", help="the serial port (default: the first USB one)")
    args = parser.parse_args(argv)
    if args.command == "list":
        print("\n".join(catalog_lines()))
        if args.board:
            print(board_lineup(Mpremote()))
    elif args.command == "deploy":
        if args.all == bool(args.names):
            parser.error("deploy takes NAME... or --all")
        try:
            Deploy(Mpremote(args.dry_run)).run(None if args.all else args.names)
        except Refused as e:
            print("refused:", e)
            return 1
    else:
        Mpremote().run(["reset"])
        for line in Console(serial_port(args.port)).lines(args.seconds):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
