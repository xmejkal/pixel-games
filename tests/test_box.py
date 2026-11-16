"""tools/box.py (P817) with a fake runner, so no board: the exact mpremote commands of a deploy with and without
:packs and :lineup.py on the board, --all, --dry-run, each refusal with no command run, list, and the console's read
across a reset. The firmware check (P848) reads the answers tools/firmware_probe.py prints, run here on the Mac with
stand-in modules, and the answers a board gave, kept in tests/fixtures/firmware/. deploy --engine (P850) writes or
removes :engine_config.py. Run from the repository root:
python3 -B -m unittest tests.test_box. --- MVP (P817) ---"""

import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

import box  # noqa: E402

PY = sorted("games/" + n for n in os.listdir(box.GAMES) if n.endswith(".py"))
COPY = ["cp"] + PY + ["games/box_bank.raw", ":"]
PACKAGE = sorted(n for n in os.listdir(os.path.join(box.GAMES, "engine")) if n.endswith(".py"))  # __init__.py first
FOLDER = [["mkdir", ":engine"], ["cp"] + ["games/engine/" + n for n in PACKAGE] + [":engine/"]]  # --py, no :engine/
EMPTY = "         139 boot.py\n"
FULL = "ls :\n         139 boot.py\n           0 packs/\n          31 lineup.py\n"
PROBE = ["run", "tools/firmware_probe.py"]
FIXTURES = os.path.join(HERE, "fixtures", "firmware")
CRACKLE = box.CRACKLE  # before setUpModule's patch
NOT_BUILT = os.path.join(HERE, "fixtures", "no-such-folder", "_crackle.mpy")
FLASH = ": flash the image of ./build.sh engine first (README, Build and run)"
PROBE_LINE = "run `mpremote run tools/firmware_probe.py` and read it"
NO_ANSWER = "the board did not answer: close any mpremote or log session, press reset, and deploy again"
RAW_REPL = """Traceback (most recent call last):
  File "/usr/local/bin/mpremote", line 8, in <module>
    sys.exit(main())
  File "/usr/local/lib/python3.10/site-packages/mpremote/main.py", line 634, in main
    handler_func(state, args)
  File "/usr/local/lib/python3.10/site-packages/mpremote/commands.py", line 510, in do_run
    state.ensure_raw_repl()
  File "/usr/local/lib/python3.10/site-packages/mpremote/main.py", line 552, in ensure_raw_repl
    self.transport.enter_raw_repl(soft_reset=soft_reset)
  File "/usr/local/lib/python3.10/site-packages/mpremote/transport_serial.py", line 210, in enter_raw_repl
    raise TransportError("could not enter raw repl")
mpremote.transport.TransportError: could not enter raw repl
"""  # mpremote 1.29.0's answer while a game runs: its main() catches no TransportError


def stand_in(*without):
    """A firmware's _engine with the classes the games need, but the names in without (HeatField.cool: a HeatField
    with no cool)."""
    heat = type("HeatField", (), {} if "HeatField.cool" in without else {"cool": lambda self: None})
    module = types.ModuleType("_engine")
    for name, value in (("Bodies", object), ("HeatField", heat), ("Balls", object), ("SoundBank", object)):
        if name not in without:
            setattr(module, name, value)
    return module


def probe_answer(underscore, old=None):
    """What tools/firmware_probe.py prints when _engine is underscore and engine is old (None: an ImportError)."""
    with open(os.path.join(box.ROOT, box.PROBE)) as f:
        source = f.read()
    with mock.patch.dict(sys.modules, {"_engine": underscore, "engine": old}), \
            contextlib.redirect_stdout(io.StringIO()) as said:
        exec(compile(source, box.PROBE, "exec"), {"__name__": "__main__"})
    return said.getvalue()


OLD_ENGINE = types.ModuleType("engine")
OLD_ENGINE.Bodies = object
NEW = probe_answer(stand_in())  # every name: the image of ./build.sh engine from pixel-engine 1005249 on
BOTH = probe_answer(stand_in(), OLD_ENGINE)  # an image that registers _engine and engine: a stale build-engine
OLD = probe_answer(None, OLD_ENGINE)  # the image built before: its C module is engine
NO_C = probe_answer(None)  # the stock image


def setUpModule():
    patch = mock.patch.object(box, "CRACKLE", NOT_BUILT)  # box.main's deploys: as for a tree with no _crackle.mpy
    patch.start()
    unittest.addModuleCleanup(patch.stop)


def deploy(runner, compiler=None, crackle=NOT_BUILT, said=None, pauses=None, reference=None):
    """A Deploy that tells said (a list), or no one, what it says, and keeps its pauses in pauses."""
    return box.Deploy(runner, compiler, crackle=crackle, say=(said if said is not None else []).append,
                      sleep=(pauses if pauses is not None else []).append, reference=reference)


class FakeRunner:
    """Answers `ls :` with listing, `ls :<folder>` with folders[folder] and the firmware probe with firmware, records
    each command, and keeps what a copy of lineup.py held."""

    dry_run = False

    def __init__(self, listing=EMPTY, firmware=NEW, folders=None):
        self.listing, self.firmware, self.commands, self.lineup = listing, firmware, [], None
        self.folders, self.config = folders or {}, None

    def run(self, args):
        self.commands.append(args)
        if args[-1] == ":lineup.py" and args[0] == "cp":
            with open(args[1]) as f:
                self.lineup = f.read()
        if args[-1] == ":engine_config.py" and args[0] == "cp":
            with open(args[1]) as f:
                self.config = f.read()
        if args[0] == "ls" and args != ["ls", ":"]:
            return self.folders.get(args[1][1:], "")
        return self.listing if args == ["ls", ":"] else self.firmware if args == PROBE else ""


class DeployTest(unittest.TestCase):
    def test_a_lineup_on_a_board_with_neither_packs_nor_lineup(self):
        runner = FakeRunner()
        deploy(runner).run(["runner", "snake", "flappy", "marshmallow"])
        self.assertEqual([PROBE, ["ls", ":"], ["mkdir", ":packs"], COPY] + FOLDER +
                         [["cp", "games/packs/runner.pak", ":packs/runner.pak"],
                          ["cp", "games/packs/snake.pak", ":packs/snake.pak"],
                          ["cp", "games/packs/flappy.pak", ":packs/flappy.pak"]], runner.commands[:9])
        self.assertEqual(":lineup.py", runner.commands[9][-1])
        self.assertEqual([["reset"]], runner.commands[10:])
        self.assertEqual("LINEUP = ('runner', 'snake', 'flappy', 'marshmallow')  # tools/box.py deploy (P817)\n",
                         runner.lineup)

    def test_a_lineup_on_a_board_with_packs_makes_no_folder(self):
        runner = FakeRunner(FULL)
        deploy(runner).run(["cave"])
        self.assertEqual([PROBE, ["ls", ":"], COPY] + FOLDER, runner.commands[:5])
        self.assertEqual(["reset"], runner.commands[-1])
        self.assertEqual(7, len(runner.commands))
        self.assertEqual("LINEUP = ('cave',)  # tools/box.py deploy (P817)\n", runner.lineup)

    def test_all_copies_every_pack_and_removes_the_board_s_lineup(self):
        runner = FakeRunner(FULL)
        deploy(runner).run(None)
        packs = [["cp", "games/packs/%s.pak" % s, ":packs/%s.pak" % s]
                 for s in ("runner", "meteors", "bucket", "rescue", "flappy", "snake", "stack", "cube", "gravpong")]
        self.assertEqual([PROBE, ["ls", ":"], COPY] + FOLDER + packs + [["rm", ":lineup.py"], ["reset"]],
                         runner.commands)

    def test_all_on_a_board_with_no_lineup_removes_nothing(self):
        runner = FakeRunner()
        deploy(runner).run(None)
        self.assertNotIn("rm", [c[0] for c in runner.commands])
        self.assertEqual(["mkdir", ":packs"], runner.commands[2])

    def test_each_refusal_runs_no_command(self):
        for names, why in ((["nope"], "no game nope"), (["snake", "snake"], "twice"), ([], "empty")):
            with self.subTest(names):
                runner = FakeRunner()
                with self.assertRaisesRegex(box.Refused, why):
                    deploy(runner).run(names)
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
        self.assertEqual(["mpremote run tools/firmware_probe.py", "mpremote ls :", "mpremote mkdir :packs",
                          "mpremote " + " ".join(COPY)] + ["mpremote " + " ".join(c) for c in FOLDER] +
                         ["no _crackle.mpy built, so none is copied: tools/crackle.sh builds it"], lines[:7])
        self.assertEqual("mpremote cp games/packs/snake.pak :packs/snake.pak", lines[7])
        self.assertRegex(lines[8], r"^mpremote cp \S+lineup\.py :lineup\.py$")
        self.assertEqual(["mpremote reset"], lines[9:])

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
        deploy(runner, box.Compiler(mpy_cross)).run(["snake"])
        return runner.commands, mpy_cross.calls

    def test_it_compiles_each_module_but_main_for_the_chip_naming_its_source(self):
        commands, calls = self.deploy(EMPTY)
        self.assertEqual(["mpy-cross", "--version"], calls[0])
        self.assertEqual(len(MODULES) + len(PACKAGE), len(calls) - 1)  # the package's after the root's
        for module, call in zip(MODULES, calls[1:]):
            self.assertEqual(["mpy-cross", "-march=xtensawin", "-s", module + ".py", "-o"], call[:5])
            self.assertEqual((module + ".mpy", "games/%s.py" % module), (os.path.basename(call[5]), call[6]))
        self.assertNotIn("main", [os.path.basename(c[-1])[:-3] for c in calls[1:]])

    def test_the_mpy_files_go_with_main_py_and_no_rm_on_a_clean_board(self):
        commands, calls = self.deploy(EMPTY)
        self.assertEqual([PROBE, ["ls", ":"], ["mkdir", ":packs"]], commands[:3])
        copy = commands[3]
        self.assertEqual([m + ".mpy" for m in MODULES], [os.path.basename(f) for f in copy[1:-3]])
        self.assertEqual(["games/main.py", "games/box_bank.raw", ":"], copy[-3:])
        self.assertEqual(["mkdir", ":engine"], commands[4])
        self.assertEqual(["cp", "games/packs/snake.pak", ":packs/snake.pak"], commands[6])
        self.assertNotIn("rm", [c[0] for c in commands])
        self.assertEqual(["reset"], commands[-1])

    def test_the_board_s_old_py_files_go_after_the_mpy_files_and_main_py_stays(self):
        commands, calls = self.deploy(OLD_PY)
        self.assertEqual("cp", commands[2][0])
        self.assertEqual(["rm", ":app.py", ":arcade.py"], commands[3])

    def test_py_copies_the_sources_and_removes_only_their_mpy_files(self):
        runner = FakeRunner(OLD_MPY)
        deploy(runner).run(["snake"])
        self.assertEqual(COPY, runner.commands[2])
        self.assertEqual(["rm", ":app.mpy", ":gfx.mpy"], runner.commands[3])  # crackle_c.mpy stays (P848: until stage 9)

    def test_an_mpy_cross_of_another_version_is_refused_before_any_board_command(self):
        for version in ("MicroPython v1.22.0; mpy-cross emitting mpy v6.2\n", "mpy-cross 1.0\n"):
            with self.subTest(version):
                runner = FakeRunner()
                with self.assertRaisesRegex(box.Refused, "the board needs mpy v6.3"):
                    deploy(runner, box.Compiler(FakeMpyCross(version))).run(["snake"])
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
        self.assertEqual([PROBE, ["ls", ":"], ["mkdir", ":packs"]], runner.commands)  # no cp, no rm

    def test_a_failed_rm_of_the_old_py_says_deploy_again(self):
        class RmFails(FakeRunner):
            def run(self, args):
                if args[0] == "rm":
                    raise subprocess.CalledProcessError(1, ["mpremote"] + args, stderr="rm: busy\n")
                return super().run(args)
        with self.assertRaises(subprocess.CalledProcessError) as failed:
            deploy(RmFails(OLD_PY), box.Compiler(FakeMpyCross())).run(["snake"])
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
        self.assertEqual(["mpy-cross --version", "mpremote run tools/firmware_probe.py", "mpremote ls :",
                          "mpremote mkdir :packs"], lines[:4])
        self.assertRegex(lines[4], r"^mpy-cross -march=xtensawin -s app\.py -o \S+app\.mpy games/app\.py$")
        self.assertTrue(lines[4 + len(MODULES)].endswith(" games/main.py games/box_bank.raw :"))


IN_FOLDER = "ls :engine\n        1200 signals.mpy\n         900 signals.py\n          40 __init__.mpy\n" \
            "         700 old.mpy\n         800 old.py\n         600 clock.mpy\n         100 notes.txt\n"


class PackageTest(unittest.TestCase):
    """The package games/engine/ goes into its folder :engine/ (P849, stage 0b-1): compiled with -s engine/<name>.py,
    copied, and cleaned of a .py that now has an .mpy and of a module whose source is gone; the flat modules of MOVED
    leave the board's root, and nothing else there does (the board's boot.py stays)."""

    def deploy(self, listing=EMPTY, folder=None, compiler=True):
        runner = FakeRunner(listing, folders={"engine": folder} if folder is not None else None)
        mpy_cross = FakeMpyCross()
        deploy(runner, box.Compiler(mpy_cross) if compiler else None).run(["snake"])
        return runner.commands, mpy_cross.calls

    def test_the_package_goes_into_its_folder(self):
        commands, calls = self.deploy()
        package = calls[-len(PACKAGE):]
        for name, call in zip(PACKAGE, package):
            self.assertEqual(["mpy-cross", "-march=xtensawin", "-s", "engine/" + name, "-o"], call[:5])
            self.assertEqual((name[:-3] + ".mpy", "games/engine/" + name), (os.path.basename(call[5]), call[6]))
        at = commands.index(["mkdir", ":engine"])
        self.assertEqual([c[5] for c in package] + [":engine/"], commands[at + 1][1:])
        self.assertNotIn(["ls", ":engine"], commands)  # a folder just made has nothing to clean
        self.assertIn("__init__.py", PACKAGE)

    def test_a_board_with_the_folder_gets_no_mkdir(self):
        commands, _ = self.deploy("ls :\n           0 packs/\n           0 engine/\n", "ls :engine\n")
        self.assertNotIn(["mkdir", ":engine"], commands)
        at = commands.index(["ls", ":engine"])
        self.assertEqual("cp", commands[at - 1][0])
        self.assertEqual(":engine/", commands[at - 1][-1])
        self.assertEqual(["cp", "games/packs/snake.pak", ":packs/snake.pak"], commands[at + 1])  # nothing to remove

    def test_a_stale_py_in_the_folder_goes(self):
        commands, _ = self.deploy("ls :\n           0 packs/\n           0 engine/\n", IN_FOLDER)
        rm = [c for c in commands if c[0] == "rm"]
        self.assertEqual([["rm", ":engine/old.mpy", ":engine/old.py", ":engine/signals.py"]], rm)

    def test_a_removed_module_goes(self):
        commands, _ = self.deploy("ls :\n           0 packs/\n           0 engine/\n",
                                  "ls :engine\n         700 old.mpy\n          40 __init__.mpy\n")
        self.assertIn(["rm", ":engine/old.mpy"], commands)
        self.assertNotIn(":engine/__init__.mpy", [n for c in commands if c[0] == "rm" for n in c])

    def test_a_moved_module_goes_from_the_root(self):
        listing = "ls :\n         139 boot.py\n           0 packs/\n        1200 signals.mpy\n         900 signals.py\n" \
                  "        5000 app.py\n"
        for compiler in (True, False):
            with self.subTest(compiler=compiler):
                commands, _ = self.deploy(listing, compiler=compiler)
                rm = [c for c in commands if c[0] == "rm"]
                self.assertEqual([":signals.mpy", ":signals.py"], sorted(rm[-1][1:]))
                self.assertEqual(1, len([c for c in rm if ":signals.py" in c or ":signals.mpy" in c]))

    def test_a_moved_module_goes_only_after_the_package_is_copied(self):
        """A copy that fails before the folder is full leaves the old flat module, which the old app still imports:
        the board's app.mpy never finds signals nowhere."""
        listing = "ls :\n           0 packs/\n        1200 signals.mpy\n"
        for compiler in (True, False):
            with self.subTest(compiler=compiler):
                commands, _ = self.deploy(listing, compiler=compiler)
                copied = [i for i, c in enumerate(commands) if c[0] == "cp" and c[-1] == ":engine/"]
                self.assertEqual(1, len(copied))
                self.assertLess(copied[0], commands.index(["rm", ":signals.mpy"]))

    def test_boot_py_stays(self):
        listing = "ls :\n         139 boot.py\n           0 packs/\n         300 notes.mpy\n        1200 signals.mpy\n"
        for compiler in (True, False):
            with self.subTest(compiler=compiler):
                commands, _ = self.deploy(listing, compiler=compiler)
                removed = [n for c in commands if c[0] == "rm" for n in c[1:]]
                self.assertEqual([":signals.mpy"], removed)  # boot.py and a root module the games lack stay

    def test_py_copies_the_folder_s_sources(self):
        commands, calls = self.deploy("ls :\n           0 packs/\n           0 engine/\n", IN_FOLDER, compiler=False)
        self.assertEqual([], calls)
        self.assertIn(FOLDER[1], commands)
        rm = [c for c in commands if c[0] == "rm"]
        self.assertEqual([["rm", ":engine/__init__.mpy", ":engine/clock.mpy", ":engine/old.mpy", ":engine/old.py",
                           ":engine/signals.mpy"]], rm)

    def test_the_moved_table_names_modules_that_left_the_root_for_a_package(self):
        self.assertEqual(("signals",), box.MOVED)
        for name in box.MOVED:
            with self.subTest(name):
                self.assertFalse(os.path.exists(os.path.join(box.GAMES, name + ".py")))
                self.assertTrue([p for p in box.PACKAGES if os.path.isfile(os.path.join(box.GAMES, p, name + ".py"))])

    def test_dry_run_makes_the_folder_and_lists_nothing(self):
        with mock.patch.object(box.subprocess, "run") as run, contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(0, box.main(["deploy", "--dry-run", "snake"]))
        run.assert_not_called()
        lines = said.getvalue().splitlines()
        at = lines.index("mpremote mkdir :engine")
        self.assertRegex(lines[at - 1], r"^mpy-cross -march=xtensawin -s engine/signals\.py -o \S+signals\.mpy "
                                        r"games/engine/signals\.py$")
        self.assertRegex(lines[at + 1], r"^mpremote cp \S+__init__\.mpy \S+accel\.mpy \S+clock\.mpy \S+signals\.mpy "
                                        r":engine/$")
        self.assertNotIn("mpremote ls :engine", lines)


WITH_CONFIG = "ls :\n         139 boot.py\n           0 packs/\n          40 engine_config.py\n"


class EngineTest(unittest.TestCase):
    """deploy --engine (P850, stage 0b-2): `reference` forces every part's reference version, `reference=PART,...`
    the named parts, in :engine_config.py, which main.py reads at boot. A deploy without --engine removes the file,
    so a forced setting lasts one deploy."""

    def deploy(self, reference, listing=EMPTY):
        runner = FakeRunner(listing)
        deploy(runner, reference=reference).run(["snake"])
        return runner

    def test_engine_reference_writes_all(self):
        runner = self.deploy(box.engine_reference("reference"))
        self.assertEqual('REFERENCE = "all"  # tools/box.py deploy --engine\n', runner.config)
        self.assertEqual(["reset"], runner.commands[-1])
        self.assertEqual(":engine_config.py", runner.commands[-2][-1])

    def test_engine_reference_names_writes_them(self):
        for value, names in (("reference=volume", "('volume',)"), ("reference=sum,volume", "('sum', 'volume')")):
            with self.subTest(value):
                runner = self.deploy(box.engine_reference(value), WITH_CONFIG)
                self.assertEqual("REFERENCE = %s  # tools/box.py deploy --engine\n" % names, runner.config)
                self.assertNotIn(["rm", ":engine_config.py"], runner.commands)

    def test_a_deploy_without_engine_removes_the_config(self):
        runner = self.deploy(None, WITH_CONFIG)
        self.assertEqual([["rm", ":engine_config.py"], ["reset"]], runner.commands[-2:])
        self.assertIsNone(runner.config)

    def test_a_deploy_without_engine_on_a_board_without_the_config_removes_nothing(self):
        runner = self.deploy(None)
        self.assertNotIn(":engine_config.py", [n for c in runner.commands for n in c])

    def test_the_engine_value_is_read(self):
        self.assertEqual("all", box.engine_reference("reference"))
        self.assertEqual(("volume",), box.engine_reference("reference=volume"))
        self.assertEqual(("sum", "volume"), box.engine_reference("reference=sum,volume"))

    def test_a_malformed_engine_value_is_refused_before_any_board_command(self):
        for value in ("fast", "reference=", "reference=,volume", "reference=sum,,volume", "reference=Volume",
                      "reference=vol ume", "reference=volume;import os", "reference=volume,volume", "reference=all"):
            with self.subTest(value):
                with mock.patch.object(box.subprocess, "run") as run, \
                        contextlib.redirect_stdout(io.StringIO()) as said:
                    self.assertEqual(1, box.main(["deploy", "--engine", value, "snake"]))
                run.assert_not_called()
                self.assertTrue(said.getvalue().startswith("refused: --engine takes reference or "
                                                           "reference=PART[,PART...]"), said.getvalue())

    def test_main_passes_the_engine_value_to_the_deploy(self):
        with mock.patch.object(box.subprocess, "run") as run, contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(0, box.main(["deploy", "--py", "--dry-run", "--engine", "reference=volume", "snake"]))
        run.assert_not_called()
        lines = said.getvalue().splitlines()
        self.assertRegex(lines[-2], r"^mpremote cp \S+engine_config\.py :engine_config\.py$")
        self.assertEqual("mpremote reset", lines[-1])


class FirmwareTest(unittest.TestCase):
    """The firmware check (P848, stage 0a): the probe runs before ls, and the deploy refuses a firmware whose C module
    the games cannot import."""

    def refused(self, answer):
        runner = FakeRunner(firmware=answer)
        with self.assertRaises(box.Refused) as refusal:
            deploy(runner).run(["snake"])
        self.assertEqual([PROBE], runner.commands)  # nothing after the probe
        return str(refusal.exception)

    def test_the_old_firmware_is_refused_before_ls(self):
        self.assertEqual("the board's C module is still named engine" + FLASH, self.refused(OLD))
        runner = FakeRunner(firmware=OLD)
        with mock.patch.object(box, "Mpremote", lambda dry_run=False: runner), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(1, box.main(["deploy", "--py", "snake"]))
        self.assertEqual("refused: the board's C module is still named engine" + FLASH + "\n", said.getvalue())
        self.assertEqual([PROBE], runner.commands)

    def test_a_missing_name_is_refused(self):
        for name in box.FIRMWARE_NAMES:
            with self.subTest(name):
                self.assertRegex(self.refused(probe_answer(stand_in(name))),
                                 r"^the firmware lacks (\S+, )*%s(, \S+)*%s$" % (re.escape(name), re.escape(FLASH)))
        self.assertEqual("the firmware lacks SoundBank" + FLASH, self.refused(probe_answer(stand_in("SoundBank"))))

    def test_an_unknown_answer_is_refused(self):
        lines = NEW.splitlines()
        for answer in ("", "Traceback (most recent call last):\n", NEW.replace("yes", "maybe", 1),
                       "\n".join(lines[:-1]), "\n".join(lines + lines[-1:]), OLD + "engine Bodies yes\n",
                       NEW.replace("_engine", "engine"), NEW.replace("Balls yes", "Balls"),
                       NEW.replace("Balls yes", "Bodies yes"), NEW.replace("Balls yes", "Rocks yes"), "\n".join(lines[:-1] + ["engine Balls yes"]),
                       "\n".join(lines[:-1] + lines[:1]), "_engine ImportError\nengine Bodies yes\n" + lines[0],
                       "_engine ImportError\n_engine Bodies yes"):
            with self.subTest(answer):
                self.assertEqual("unknown firmware answer: %r: flash the image of ./build.sh engine (README, Build and "
                                 "run), or %s" % (answer.strip(), PROBE_LINE), self.refused(answer))

    def test_a_firmware_without_our_c_deploys_as_today(self):
        package = types.ModuleType("engine")  # a package engine on a stock image (stage 0b-1): no Bodies
        for answer in (NO_C, probe_answer(None, package), NEW, NEW.replace("\n", "\r\n")):
            with self.subTest(answer):
                runner = FakeRunner(firmware=answer)
                deploy(runner).run(["snake"])
                self.assertEqual([PROBE, ["ls", ":"], ["mkdir", ":packs"], COPY], runner.commands[:4])
                self.assertEqual(["reset"], runner.commands[-1])

    def test_an_image_that_also_registers_the_old_name_is_refused(self):
        self.assertEqual(["_engine %s yes" % name for name in box.FIRMWARE_NAMES] + ["engine Bodies yes"],
                         BOTH.splitlines())
        self.assertEqual("the firmware registers engine beside _engine, so a package engine cannot load: flash the "
                         "image of a clean ./build.sh engine first (README, Build and run)", self.refused(BOTH))

    def test_the_probe_is_tried_again_while_a_game_holds_the_board(self):
        runner, pauses = FailingRunner(1), []
        deploy(runner, pauses=pauses).run(["snake"])
        self.assertEqual([PROBE, PROBE, ["ls", ":"]], runner.commands[:3])
        self.assertEqual([box.RESET_PAUSE_S], pauses)
        self.assertEqual(["reset"], runner.commands[-1])

    def test_a_board_that_never_answers_says_what_to_do(self):
        runner, pauses = FailingRunner(99), []
        with self.assertRaises(subprocess.CalledProcessError) as failed:
            deploy(runner, pauses=pauses).run(["snake"])
        self.assertEqual("mpremote.transport.TransportError: could not enter raw repl; " + NO_ANSWER,
                         failed.exception.stderr)
        self.assertEqual([PROBE] * box.PROBE_TRIES, runner.commands)
        self.assertEqual([box.RESET_PAUSE_S] * (box.PROBE_TRIES - 1), pauses)

    def test_spaces_around_the_words_change_nothing(self):
        spaced = "".join("  %s  \r\n" % "   ".join(line.split()) for line in NEW.splitlines())
        self.assertIsNone(box.firmware_fault(spaced))
        self.assertEqual("the firmware lacks Balls" + FLASH,
                         box.firmware_fault(" " + probe_answer(stand_in("Balls")).replace("\n", " \n ")))

    def test_the_order_of_the_names_does_not_matter(self):
        lines = probe_answer(stand_in("Bodies")).splitlines()
        self.assertEqual("the firmware lacks Bodies" + FLASH,
                         box.firmware_fault("\n".join(lines[-2::-1] + lines[-1:])))

    def test_a_dry_run_never_refuses(self):
        class DryRun(FakeRunner):
            dry_run = True
        for answer in ("", OLD, probe_answer(stand_in("Balls"))):
            with self.subTest(answer):
                runner = DryRun(firmware=answer)
                deploy(runner).run(["snake"])
                self.assertEqual(["reset"], runner.commands[-1])

    def test_a_broken_package_folder_never_answers_for_the_firmware(self):
        """The box's own :engine/ folder (stage 0b-1): a half-copied __init__.mpy raises ValueError on the board. The
        probe asks for built-in modules only, with an empty sys.path, so the folder never answers."""
        with open(os.path.join(box.ROOT, box.PROBE)) as f:
            source = f.read()
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(os.path.join(tmp, "engine"))
            with open(os.path.join(tmp, "engine", "__init__.py"), "w") as f:
                f.write("raise ValueError('incompatible .mpy file')\n")
            with mock.patch.dict(sys.modules, {"_engine": stand_in()}), mock.patch.object(sys, "path", [tmp]), \
                    contextlib.redirect_stdout(io.StringIO()) as said:
                sys.modules.pop("engine", None)
                exec(compile(source, box.PROBE, "exec"), {"__name__": "__main__"})
                self.assertEqual([tmp], sys.path)  # restored
        self.assertEqual(NEW, said.getvalue())

    def test_the_probe_asks_for_the_names_the_check_reads(self):
        self.assertEqual(["_engine %s yes" % name for name in box.FIRMWARE_NAMES] + ["engine ImportError"],
                         NEW.splitlines())
        self.assertEqual(["_engine ImportError", "engine Bodies yes"], OLD.splitlines())
        self.assertEqual(["_engine ImportError", "engine ImportError"], NO_C.splitlines())

    def test_the_answers_a_board_gave(self):
        """The kept answers of tests/fixtures/firmware/: stock.txt written by hand from the probe's text (no stock
        image is flashed for it), old.txt captured before the flash of stage 0a, new.txt after it."""
        for name, fault in (("stock.txt", None), ("old.txt", "the board's C module is still named engine" + FLASH),
                            ("new.txt", None)):
            with self.subTest(name):
                path = os.path.join(FIXTURES, name)
                if not os.path.exists(path):
                    self.skipTest("not captured yet: mpremote run tools/firmware_probe.py > tests/fixtures/firmware/"
                                  + name)
                with open(path, newline="") as f:
                    self.assertEqual(fault, box.firmware_fault(f.read()))


class CrackleTest(unittest.TestCase):
    """The crackle's native module (P848): the deploy copies _crackle.mpy when it is built and keeps the board's
    crackle_c.mpy, so a flash of the rollback image still finds its crackle (until stage 9)."""

    def test_the_crackle_goes_as_underscore_crackle_and_the_old_one_stays(self):
        with tempfile.TemporaryDirectory() as tmp:
            built = os.path.join(tmp, "_crackle.mpy")
            open(built, "wb").close()
            for compiler in (None, box.Compiler(FakeMpyCross())):
                with self.subTest(compiler=compiler):
                    runner, said = FakeRunner(OLD_MPY), []
                    deploy(runner, compiler, crackle=built, said=said).run(["snake"])
                    at = runner.commands.index(["cp", built, ":_crackle.mpy"])
                    self.assertEqual(["cp", "games/packs/snake.pak", ":packs/snake.pak"], runner.commands[at + 1])
                    self.assertFalse([c for c in runner.commands if ":crackle_c.mpy" in c])
                    self.assertEqual([], said)

    def test_no_crackle_built_says_so_and_deploys_the_rest(self):
        runner, said = FakeRunner(), []
        deploy(runner, said=said).run(["snake"])
        self.assertEqual(["no _crackle.mpy built, so none is copied: tools/crackle.sh builds it"], said)
        self.assertFalse([c for c in runner.commands if ":_crackle.mpy" in c])
        self.assertIn(["cp", "games/packs/snake.pak", ":packs/snake.pak"], runner.commands)
        self.assertEqual(["reset"], runner.commands[-1])

    def test_a_crackle_path_is_read_from_the_repository_root(self):
        with tempfile.NamedTemporaryFile(dir=HERE, suffix=".mpy") as built, tempfile.TemporaryDirectory() as away:
            named = os.path.relpath(built.name, box.ROOT)  # tests/tmpXXXX.mpy
            cwd = os.getcwd()
            os.chdir(away)  # box.py's commands run from the root, wherever the deploy was started
            try:
                runner = FakeRunner()
                deploy(runner, crackle=named).run(["snake"])
            finally:
                os.chdir(cwd)
        self.assertIn(["cp", named, ":_crackle.mpy"], runner.commands)

    def test_the_crackle_is_the_one_crackle_sh_builds(self):
        self.assertEqual("engine/natmod/crackle/_crackle.mpy", CRACKLE)
        with open(os.path.join(box.ROOT, "tools", "crackle.sh")) as f:
            self.assertIn('"$ROOT/%s"' % CRACKLE, f.read())


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
        if not self.fails:
            return super().run(args)
        self.commands.append(args)
        self.fails -= 1
        raise subprocess.CalledProcessError(1, ["mpremote"] + args, stderr=RAW_REPL)


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
        with mock.patch.object(box.time, "sleep") as pause:
            code, said = self.main(["deploy", "--py", "snake"], FailingRunner(99))
        self.assertEqual((1, "mpremote run tools/firmware_probe.py failed: mpremote.transport.TransportError: could not "
                             "enter raw repl; " + NO_ANSWER + "\n"), (code, said))
        self.assertEqual(box.PROBE_TRIES - 1, pause.call_count)

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
