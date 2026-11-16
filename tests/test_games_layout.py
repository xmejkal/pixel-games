"""The repository's layout (P632): every path that micropython.cmake and build.sh name exists, each test file imports
alone (a whole-suite run hides a wrong sys.path line, because the first file to set a path serves the rest), and
tools/render_scene.py starts. Run from the repository root: python3 -m unittest discover tests. --- MVP (P632) ---"""

import ast
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CMAKE_PATH = re.compile(r"\$\{CMAKE_CURRENT_LIST_DIR\}/(\S+?)\)")
SCRIPT_PATH = re.compile(r"\$HERE/([\w./-]+)")


def named_paths(name, pattern):
    with open(os.path.join(ROOT, name)) as f:
        return pattern.findall(f.read())


class Paths(unittest.TestCase):
    def test_cmake_includes_exist(self):
        paths = named_paths("micropython.cmake", CMAKE_PATH)
        self.assertIn("engine/driver/src/micropython.cmake", paths)
        for path in paths:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, path)), path)

    def test_build_script_paths_exist(self):
        paths = named_paths("build.sh", SCRIPT_PATH)
        self.assertIn("engine/driver/src/micropython.cmake", paths)
        for path in paths:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, path)), path)


class Names(unittest.TestCase):
    def test_no_module_shares_a_name_with_the_engines(self):
        # engine/tests is on the path of these tests, so a shared name imports the wrong module (P632)
        ours = {n for n in os.listdir(HERE) if n.endswith(".py")}
        engines = {n for n in os.listdir(os.path.join(ROOT, "engine", "tests")) if n.endswith(".py")}
        self.assertEqual(ours & engines, set())


class OldCNames(unittest.TestCase):
    """--- MVP (P848) --- the firmware's C module is _engine and the crackle _crackle (stage 0a), so a package named
    engine can load on the board: a game that imports the old names finds no C. It catches `import engine`,
    `import crackle_c` and `from crackle_c import`. It does not catch `import engine.x`, `__import__` or importlib,
    nor, on purpose, `from engine import x`, which is the package's from stage 0b-1."""

    OLD = {"engine", "crackle_c"}

    def test_no_game_imports_the_old_c_names(self):
        games = os.path.join(ROOT, "games")
        found = []
        for name in sorted(n for n in os.listdir(games) if n.endswith(".py")):
            with open(os.path.join(games, name)) as f:
                tree = ast.parse(f.read(), name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found += ["%s:%d %s" % (name, node.lineno, a.name) for a in node.names if a.name in self.OLD]
                elif isinstance(node, ast.ImportFrom) and node.module == "crackle_c":
                    found.append("%s:%d %s" % (name, node.lineno, node.module))
        self.assertEqual([], found)


class ComposedParts(unittest.TestCase):
    """--- MVP (P850) --- main.py composes the knob and the speaker from the versions it chose (stage 0b-2), so no
    caller opens them another way: app.open_speaker and speaker.voice_sum are gone, open_knob takes the chosen volume,
    and app.run opens no knob of its own, so each probe's run passes one (main.compose builds it)."""

    def callers(self):
        names = sorted(n for n in os.listdir(ROOT) if n.startswith("probe") and n.endswith(".py"))
        names += sorted("tools/" + n for n in os.listdir(os.path.join(ROOT, "tools")) if n.endswith(".py"))
        names += sorted("games/" + n for n in os.listdir(os.path.join(ROOT, "games")) if n.endswith(".py"))
        for name in names:
            with open(os.path.join(ROOT, name)) as f:
                yield name, ast.parse(f.read(), name)

    def test_no_caller_opens_a_part_another_way(self):
        found = []
        for name, tree in self.callers():
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                where = "%s:%d" % (name, node.lineno)
                owner = node.func.value.id if isinstance(node.func.value, ast.Name) else None
                if node.func.attr == "open_speaker" or (owner, node.func.attr) == ("speaker", "voice_sum"):
                    found.append("%s %s" % (where, node.func.attr))
                elif node.func.attr == "open_knob" and not node.args:
                    found.append("%s open_knob() without the chosen volume" % where)
                elif (owner, node.func.attr) == ("app", "run") and "knob" not in [k.arg for k in node.keywords]:
                    found.append("%s app.run without knob=" % where)
        self.assertEqual([], found)


class ModuledefsCheck(unittest.TestCase):
    """tools/check_moduledefs.sh, which build.sh engine runs on the image's moduledefs.h (P848)."""

    NEW = "#define MODULE_DEF__ENGINE { MP_ROM_QSTR(MP_QSTR__engine), MP_ROM_PTR(&engine_user_cmodule) },\n"
    OLD = "#define MODULE_DEF_ENGINE { MP_ROM_QSTR(MP_QSTR_engine), MP_ROM_PTR(&engine_user_cmodule) },\n"
    STOCK = "#define MODULE_DEF_MACHINE { MP_ROM_QSTR(MP_QSTR_machine), MP_ROM_PTR(&mp_module_machine) },\n"

    def check(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            header = os.path.join(tmp, "moduledefs.h")
            if text is not None:
                with open(header, "w") as f:
                    f.write(self.STOCK + text)
            return subprocess.run(["bash", os.path.join(ROOT, "tools", "check_moduledefs.sh"), header],
                                  capture_output=True, text=True)

    def test_only_an_image_with_underscore_engine_alone_passes(self):
        self.assertEqual(0, self.check(self.NEW).returncode)
        for name, text in (("old", self.OLD), ("both", self.NEW + self.OLD), ("stock", ""), ("missing", None)):
            with self.subTest(name):
                run = self.check(text)
                self.assertEqual(1, run.returncode)
                self.assertTrue(run.stderr.startswith("check_moduledefs.sh: "), run.stderr)

    def test_build_sh_runs_it_on_the_engine_image(self):
        with open(os.path.join(ROOT, "build.sh")) as f:
            self.assertIn('"$HERE/tools/check_moduledefs.sh" "$MPY/ports/esp32/build-engine/genhdr/moduledefs.h"',
                          f.read())


class AloneImports(unittest.TestCase):
    def test_each_test_file_imports_alone(self):
        names = sorted(n[:-3] for n in os.listdir(HERE) if n.startswith("test_") and n != "test_games_layout.py")
        for name in names:
            with self.subTest(name):
                run = subprocess.run([sys.executable, "-B", "-c", "import " + name], cwd=HERE, capture_output=True,
                                     text=True)
                self.assertEqual(run.returncode, 0, run.stderr[-500:])

    def test_render_scene_starts(self):
        run = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "tools", "render_scene.py"), "--help"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr[-500:])


if __name__ == "__main__":
    unittest.main()
