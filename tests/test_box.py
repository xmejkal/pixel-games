"""tools/box.py (P817) with a fake runner, so no board: the exact mpremote commands of a deploy with and without
:packs and :lineup.py on the board, --all, --dry-run, each refusal with no command run, list, and the console's read
across a reset. Run from the repository root: python3 -B -m unittest tests.test_box. --- MVP (P817) ---"""

import contextlib
import io
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

import box  # noqa: E402

PY = sorted("games/" + n for n in os.listdir(box.GAMES) if n.endswith(".py"))
COPY = ["cp"] + PY + ["games/box_bank.raw", ":"]
EMPTY = "         139 boot.py\n"
FULL = "ls :\n         139 boot.py\n           0 packs/\n          31 lineup.py\n"


class FakeRunner:
    """Answers `ls :` with listing, records each command, and keeps what a copy of lineup.py held."""

    def __init__(self, listing=EMPTY):
        self.listing, self.commands, self.lineup = listing, [], None

    def run(self, args):
        self.commands.append(args)
        if args[-1] == ":lineup.py" and args[0] == "cp":
            with open(args[1]) as f:
                self.lineup = f.read()
        return self.listing if args == ["ls", ":"] else ""


class DeployTest(unittest.TestCase):
    def test_a_lineup_on_a_board_with_neither_packs_nor_lineup(self):
        runner = FakeRunner()
        box.Deploy(runner).run(["runner", "snake", "flappy", "marshmallow"])
        self.assertEqual([["ls", ":"], ["mkdir", ":packs"], COPY,
                          ["cp", "games/packs/runner.pak", ":packs/runner.pak"],
                          ["cp", "games/packs/snake.pak", ":packs/snake.pak"],
                          ["cp", "games/packs/flappy.pak", ":packs/flappy.pak"]], runner.commands[:6])
        self.assertEqual(":lineup.py", runner.commands[6][-1])
        self.assertEqual([["reset"]], runner.commands[7:])
        self.assertEqual("LINEUP = ('runner', 'snake', 'flappy', 'marshmallow')  # tools/box.py deploy (P817)\n",
                         runner.lineup)

    def test_a_lineup_on_a_board_with_packs_makes_no_folder(self):
        runner = FakeRunner(FULL)
        box.Deploy(runner).run(["cave"])
        self.assertEqual([["ls", ":"], COPY], runner.commands[:2])
        self.assertEqual(["reset"], runner.commands[-1])
        self.assertEqual(4, len(runner.commands))
        self.assertEqual("LINEUP = ('cave',)  # tools/box.py deploy (P817)\n", runner.lineup)

    def test_all_copies_every_pack_and_removes_the_board_s_lineup(self):
        runner = FakeRunner(FULL)
        box.Deploy(runner).run(None)
        packs = [["cp", "games/packs/%s.pak" % s, ":packs/%s.pak" % s]
                 for s in ("runner", "meteors", "bucket", "rescue", "flappy", "snake", "stack", "gravpong")]
        self.assertEqual([["ls", ":"], COPY] + packs + [["rm", ":lineup.py"], ["reset"]], runner.commands)

    def test_all_on_a_board_with_no_lineup_removes_nothing(self):
        runner = FakeRunner()
        box.Deploy(runner).run(None)
        self.assertNotIn("rm", [c[0] for c in runner.commands])
        self.assertEqual(["mkdir", ":packs"], runner.commands[1])

    def test_each_refusal_runs_no_command(self):
        for names, why in ((["nope"], "no game nope"), (["snake", "snake"], "twice"), ([], "empty")):
            with self.subTest(names):
                runner = FakeRunner()
                with self.assertRaisesRegex(box.Refused, why):
                    box.Deploy(runner).run(names)
                self.assertEqual([], runner.commands)

    def test_main_refuses_aloud_and_runs_nothing(self):
        with mock.patch.object(box.subprocess, "run") as run, contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(1, box.main(["deploy", "snake", "nope"]))
        run.assert_not_called()
        self.assertEqual("refused: no game nope in the catalog\n", said.getvalue())

    def test_dry_run_prints_each_command_and_runs_none(self):
        with mock.patch.object(box.subprocess, "run") as run, contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(0, box.main(["deploy", "--dry-run", "snake"]))
        run.assert_not_called()
        lines = said.getvalue().splitlines()
        self.assertEqual(["mpremote ls :", "mpremote mkdir :packs", "mpremote " + " ".join(COPY)], lines[:3])
        self.assertEqual("mpremote cp games/packs/snake.pak :packs/snake.pak", lines[3])
        self.assertRegex(lines[4], r"^mpremote cp \S+lineup\.py :lineup\.py$")
        self.assertEqual(["mpremote reset"], lines[5:])

    def test_the_runner_runs_mpremote_from_the_repository_root(self):
        with mock.patch.object(box.subprocess, "run") as run:
            run.return_value.stdout = "out"
            self.assertEqual("out", box.Mpremote().run(["ls", ":"]))
        run.assert_called_once_with(["mpremote", "ls", ":"], cwd=box.ROOT, check=True, capture_output=True,
                                    text=True)


class ListTest(unittest.TestCase):
    def test_each_game_with_its_sets_and_their_bytes(self):
        lines = box.catalog_lines()
        self.assertEqual(15, len(lines))
        self.assertEqual("marshmallow  runner 739216 B", lines[0])
        self.assertEqual("balls        no art", lines[1])

    def test_the_board_s_lineup_or_none(self):
        runner = FakeRunner(FULL)
        runner.run = lambda args, run=runner.run: "LINEUP = ('cave',)\n" if args[0] == "cat" else run(args)
        self.assertEqual("board: LINEUP = ('cave',)", box.board_lineup(runner))
        self.assertEqual("board: no lineup.py, so it plays every game", box.board_lineup(FakeRunner()))

    def test_the_names_mpremote_ls_shows(self):
        self.assertEqual({"boot.py", "packs/", "lineup.py"}, box.board_names(FULL))


class Port:
    def __init__(self, lines):
        self.lines = list(lines)

    def readline(self):
        if not self.lines:
            raise OSError("USB gone")
        return self.lines.pop(0)

    def close(self):
        pass


class ConsoleTest(unittest.TestCase):
    def test_it_opens_the_port_again_while_usb_comes_back(self):
        ports = [Port([b"before\r\n"]), OSError("no port"), Port([b"lineup 1: cave\r\n", b"", b"ready\r\n"])]
        clock = iter(range(100)).__next__

        def open_port():
            port = ports.pop(0) if ports else Port([])
            if isinstance(port, OSError):
                raise port
            return port

        lines = list(box.Console(open_port, clock=clock, sleep=lambda s: None).lines(12))
        self.assertEqual(["before", "lineup 1: cave", "ready"], lines)


if __name__ == "__main__":
    unittest.main()
