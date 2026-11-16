"""tools/box.py (P817) with a fake runner, so no board: the exact mpremote commands of a deploy with and without
:packs and :lineup.py on the board, --all, --dry-run, each refusal with no command run, list, and the console's read
across a reset. Run from the repository root: python3 -B -m unittest tests.test_box. --- MVP (P817) ---"""

import contextlib
import io
import os
import subprocess
import sys
import types
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
                 for s in ("runner", "meteors", "bucket", "rescue", "flappy", "snake", "stack", "cube", "gravpong")]
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
            self.assertEqual(0, box.main(["deploy", "--py", "--dry-run", "snake"]))
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


VERSION = "MicroPython v1.29.0 on 2026-08-29; mpy-cross emitting mpy v6.3\n"
MODULES = [n[:-3] for n in sorted(os.listdir(box.GAMES)) if n.endswith(".py") and n != "main.py"]
OLD_PY = "ls :\n         139 boot.py\n           0 packs/\n        9000 app.py\n        2000 main.py\n       31000 arcade.py\n" \
         "        4000 crackle_c.mpy\n"
OLD_MPY = "ls :\n           0 packs/\n        5000 app.mpy\n        2000 main.py\n        4000 crackle_c.mpy\n" \
          "        3000 gfx.mpy\n"


class FakeMpyCross:
    """The mpy-cross tool: answers --version with version and records each command whole."""

    dry_run = False

    def __init__(self, version=VERSION):
        self.version, self.calls = version, []

    def run(self, args):
        self.calls.append(["mpy-cross"] + args)
        return self.version if args == ["--version"] else ""


def real_mpy_cross(version=VERSION, fail=None):
    """subprocess.run as mpy-cross answers it: raises only under check=True, as subprocess.run does."""
    def run(args, **kw):
        if args[0] == "mpremote":
            raise AssertionError("no board command in this test")
        if fail and fail in args:
            if kw.get("check"):
                raise subprocess.CalledProcessError(1, args, stderr="SyntaxError: invalid syntax\n")
            return types.SimpleNamespace(stdout="", returncode=1)
        return types.SimpleNamespace(stdout=version if args[1:] == ["--version"] else "", returncode=0)
    return run


class MpyTest(unittest.TestCase):
    """The deploy of .mpy files (P821), with a fake mpy-cross and the fake runner."""

    def deploy(self, listing, version=VERSION):
        runner, mpy_cross = FakeRunner(listing), FakeMpyCross(version)
        box.Deploy(runner, box.Compiler(mpy_cross)).run(["snake"])
        return runner.commands, mpy_cross.calls

    def test_it_compiles_each_module_but_main_for_the_chip_naming_its_source(self):
        commands, calls = self.deploy(EMPTY)
        self.assertEqual(["mpy-cross", "--version"], calls[0])
        self.assertEqual(len(MODULES), len(calls) - 1)
        for module, call in zip(MODULES, calls[1:]):
            self.assertEqual(["mpy-cross", "-march=xtensawin", "-s", module + ".py", "-o"], call[:5])
            self.assertEqual((module + ".mpy", "games/%s.py" % module), (os.path.basename(call[5]), call[6]))
        self.assertNotIn("main", [os.path.basename(c[-1])[:-3] for c in calls[1:]])

    def test_the_mpy_files_go_with_main_py_and_no_rm_on_a_clean_board(self):
        commands, calls = self.deploy(EMPTY)
        self.assertEqual([["ls", ":"], ["mkdir", ":packs"]], commands[:2])
        copy = commands[2]
        self.assertEqual([m + ".mpy" for m in MODULES], [os.path.basename(f) for f in copy[1:-3]])
        self.assertEqual(["games/main.py", "games/box_bank.raw", ":"], copy[-3:])
        self.assertEqual(["cp", "games/packs/snake.pak", ":packs/snake.pak"], commands[3])
        self.assertNotIn("rm", [c[0] for c in commands])
        self.assertEqual(["reset"], commands[-1])

    def test_the_board_s_old_py_files_go_after_the_mpy_files_and_main_py_stays(self):
        commands, calls = self.deploy(OLD_PY)
        self.assertEqual("cp", commands[1][0])
        self.assertEqual(["rm", ":app.py", ":arcade.py"], commands[2])

    def test_py_copies_the_sources_and_removes_only_their_mpy_files(self):
        runner = FakeRunner(OLD_MPY)
        box.Deploy(runner).run(["snake"])
        self.assertEqual(COPY, runner.commands[1])
        self.assertEqual(["rm", ":app.mpy", ":gfx.mpy"], runner.commands[2])  # crackle_c.mpy stays

    def test_an_mpy_cross_of_another_version_is_refused_before_any_board_command(self):
        for version in ("MicroPython v1.22.0; mpy-cross emitting mpy v6.2\n", "mpy-cross 1.0\n"):
            with self.subTest(version):
                runner = FakeRunner()
                with self.assertRaisesRegex(box.Refused, "the board needs mpy v6.3"):
                    box.Deploy(runner, box.Compiler(FakeMpyCross(version))).run(["snake"])
                self.assertEqual([], runner.commands)

    def test_no_mpy_cross_says_so_and_exits_1(self):
        missing = FileNotFoundError(2, "No such file or directory", "mpy-cross")
        runner = FakeRunner()
        with mock.patch.object(box, "Mpremote", lambda dry_run=False: runner), \
                mock.patch.object(box.subprocess, "run", side_effect=missing), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(1, box.main(["deploy", "snake"]))
        self.assertTrue(said.getvalue().startswith("no mpy-cross: "), said.getvalue())
        self.assertIn("install it: pip install mpy-cross==1.29.0.post2\n", said.getvalue())
        self.assertEqual([], runner.commands)

    def test_a_failed_compile_names_mpy_cross_and_copies_nothing(self):
        runner = FakeRunner()
        with mock.patch.object(box, "Mpremote", lambda dry_run=False: runner), \
                mock.patch.object(box.subprocess, "run", real_mpy_cross(fail="games/gfx.py")), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(1, box.main(["deploy", "snake"]))
        self.assertRegex(said.getvalue(), r"^mpy-cross -march=xtensawin -s gfx\.py -o \S+gfx\.mpy games/gfx\.py failed: "
                                          r"SyntaxError: invalid syntax\n$")
        self.assertEqual([["ls", ":"], ["mkdir", ":packs"]], runner.commands)  # no cp, no rm

    def test_a_failed_rm_of_the_old_py_says_deploy_again(self):
        class RmFails(FakeRunner):
            def run(self, args):
                if args[0] == "rm":
                    raise subprocess.CalledProcessError(1, ["mpremote"] + args, stderr="rm: busy\n")
                return super().run(args)
        with self.assertRaises(subprocess.CalledProcessError) as failed:
            box.Deploy(RmFails(OLD_PY), box.Compiler(FakeMpyCross())).run(["snake"])
        self.assertEqual("rm: busy; deploy again: until then the board runs the old .py of some modules",
                         failed.exception.stderr)

    def test_the_refusal_names_the_pip_package_that_exists(self):
        with self.assertRaisesRegex(box.Refused, r"pip install mpy-cross==1\.29\.0\.post2$"):
            box.Compiler(FakeMpyCross("mpy v6.2")).check()

    def test_dry_run_prints_the_compiles_and_runs_nothing(self):
        with mock.patch.object(box.subprocess, "run") as run, contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(0, box.main(["deploy", "--dry-run", "snake"]))
        run.assert_not_called()
        lines = said.getvalue().splitlines()
        self.assertEqual(["mpy-cross --version", "mpremote ls :", "mpremote mkdir :packs"], lines[:3])
        self.assertRegex(lines[3], r"^mpy-cross -march=xtensawin -s app\.py -o \S+app\.mpy games/app\.py$")
        self.assertTrue(lines[3 + len(MODULES)].endswith(" games/main.py games/box_bank.raw :"))


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


class FailingRunner(FakeRunner):
    """Fails each command, as mpremote does while the board still reboots, the first fails times."""

    def __init__(self, fails, listing=EMPTY):
        super().__init__(listing)
        self.fails = fails

    def run(self, args):
        self.commands.append(args)
        if self.fails:
            self.fails -= 1
            raise subprocess.CalledProcessError(1, ["mpremote"] + args, stderr="could not enter raw repl\n")
        return ""


class ResetTest(unittest.TestCase):
    def test_it_tries_again_after_a_pause_while_the_board_reboots(self):
        runner, pauses = FailingRunner(2), []
        box.reset(runner, sleep=pauses.append)
        self.assertEqual([["reset"]] * 3, runner.commands)
        self.assertEqual([box.RESET_PAUSE_S] * 2, pauses)

    def test_it_gives_up_after_its_tries(self):
        runner, pauses = FailingRunner(99), []
        with self.assertRaises(subprocess.CalledProcessError):
            box.reset(runner, sleep=pauses.append)
        self.assertEqual(box.RESET_TRIES, len(runner.commands))


class MainTest(unittest.TestCase):
    def main(self, argv, runner, open_port=None):
        with mock.patch.object(box, "Mpremote", lambda dry_run=False: runner), \
                mock.patch.object(box, "serial_port", lambda name=None: open_port), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            code = box.main(argv)
        return code, said.getvalue()

    def test_deploy_with_all_and_a_name_is_a_usage_error(self):
        runner = FakeRunner()
        with self.assertRaises(SystemExit) as stop, contextlib.redirect_stderr(io.StringIO()) as said:
            self.main(["deploy", "--all", "snake"], runner)
        self.assertEqual(2, stop.exception.code)
        self.assertIn("deploy takes NAME... or --all", said.getvalue())
        self.assertEqual([], runner.commands)

    def test_log_resets_the_board_first_then_reads_its_console(self):
        runner, events = FakeRunner(), []

        def open_port():
            events.append(list(runner.commands))
            return Port([b"lineup 3: bucket rescue snake\r\n"] if len(events) == 1 else [])
        code, said = self.main(["log", "--seconds", "0.3"], runner, open_port)
        self.assertEqual(0, code)
        self.assertEqual([["reset"]], events[0])  # the reset ran before the port opened
        self.assertRegex(said, r"^\d+\.\d{3} lineup 3: bucket rescue snake\n$")  # after its seconds (P822)

    def test_a_failed_mpremote_prints_its_error_and_exits_1(self):
        code, said = self.main(["deploy", "--py", "snake"], FailingRunner(99))
        self.assertEqual((1, "mpremote ls : failed: could not enter raw repl\n"), (code, said))

    def test_no_mpremote_exits_1(self):
        with mock.patch.object(box.subprocess, "run", side_effect=FileNotFoundError("mpremote")), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(1, box.main(["list", "--board"]))
        self.assertIn("no mpremote: mpremote", said.getvalue())

    def test_list_board_reads_the_board_s_lineup(self):
        runner = FakeRunner(FULL)
        runner.run = lambda args, run=runner.run: run(args) or ("LINEUP = ('cave',)\n" if args[0] == "cat" else "")
        code, said = self.main(["list", "--board"], runner)
        self.assertEqual(0, code)
        self.assertEqual([["ls", ":"], ["cat", ":lineup.py"]], runner.commands)
        self.assertEqual("board: LINEUP = ('cave',)", said.splitlines()[-1])


class SerialPortTest(unittest.TestCase):
    def test_it_opens_the_port_mpremote_s_auto_picks(self):
        from serial.tools.list_ports_common import ListPortInfo

        def port(device, vid=None, pid=None):
            info = ListPortInfo(device, skip_link_detection=True)
            info.vid, info.pid = vid, pid
            return info
        ports = [port("/dev/cu.usbmodem2101", 0x303A, 0x1001), port("/dev/cu.Bluetooth"),
                 port("/dev/cu.usbmodem1101", 0x303A, 0x1001), port("/dev/cu.debug", 0x303A)]
        with mock.patch("serial.tools.list_ports.comports", return_value=ports), mock.patch("serial.Serial") as opened:
            box.serial_port()()
            box.serial_port("/dev/cu.other")()
        self.assertEqual([mock.call("/dev/cu.usbmodem1101", 115200, timeout=0.2),
                          mock.call("/dev/cu.other", 115200, timeout=0.2)], opened.call_args_list)

    def test_no_usb_port_is_an_os_error(self):
        with mock.patch("serial.tools.list_ports.comports", return_value=[]):
            with self.assertRaisesRegex(OSError, "no board on USB"):
                box.serial_port()()


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

    def test_log_puts_the_seconds_since_it_started_before_each_line(self):
        clock = iter([100.0, 100.5, 112.3456]).__next__
        self.assertEqual(["0.500 lineup 1: cave", "12.346 ready"],
                         list(box.stamped(iter(["lineup 1: cave", "ready"]), clock)))


if __name__ == "__main__":
    unittest.main()
