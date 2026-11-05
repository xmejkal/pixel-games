"""The repository's layout (P632): every path that micropython.cmake and build.sh name exists, each test file imports
alone (a whole-suite run hides a wrong sys.path line, because the first file to set a path serves the rest), and
tools/render_scene.py starts. Run from the repository root: python3 -m unittest discover tests. --- MVP (P632) ---"""

import os
import re
import subprocess
import sys
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
