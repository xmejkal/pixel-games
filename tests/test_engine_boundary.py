"""The engine package's boundary (P849, stage 0b-1 of the engine plan): a module of games/engine/ imports only other
modules of the package that its row in DIRECTION names, MicroPython's built-in modules (BUILT_IN) and, for a row that
names it, the C module _engine. It never imports a game's module, engine_config (main.py reads it) or anything through
importlib or __import__, which an ast walk cannot read. The walk reads every Import and ImportFrom at any depth.
tests/boundary_fixtures/ holds one module per kind of fault; its names do not start with test, so discovery skips it.
Two folders are named engine until stage 9: the package in games/ and the pixel-engine submodule at the root, which
must stay a namespace package (no __init__.py), so the package wins on the Mac, under CPython. On the board games/ is
the root, so no second engine folder exists there. Run from the repository root:
python3 -B -m unittest tests.test_engine_boundary. --- MVP (P849) ---"""

import ast
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAMES = os.path.join(ROOT, "games")
PACKAGE = os.path.join(GAMES, "engine")
FIXTURES = os.path.join(HERE, "boundary_fixtures")
C_MODULE = "_engine"
# The modules each package module may import besides BUILT_IN: other modules of the package and the C module. It grows
# with each stage of the plan. accel (0b-2) imports _engine to name it in the boot line, and never _crackle. actions
# (stage 1, P851) imports nothing: app.open_actions hands it the drivers' buttons, encoder and stick.
DIRECTION = {"__init__": (), "signals": (), "clock": (), "accel": ("_engine",), "actions": ()}
# MicroPython v1.29's built-in modules that the engine may use on the ESP32-S3; a new one enters when a module needs it
BUILT_IN = ("array", "binascii", "builtins", "collections", "errno", "esp", "esp32", "framebuf", "gc", "io", "machine",
            "math", "micropython", "os", "random", "select", "struct", "sys", "time", "uctypes")
FIXTURE_ROW = ("signals",)  # each fixture's row: a bare `import signals` is caught though the row names signals


def package_modules():
    """Each module of the package by its name below engine/ (signals, or input.buttons from stage 1), with its path."""
    found = {}
    for folder, _, files in os.walk(PACKAGE):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(folder, name)
                found[os.path.relpath(path, PACKAGE)[:-3].replace(os.sep, ".")] = path
    return found


def faults(source, row, name="<module>"):
    """Each import in source that the boundary refuses, as 'name:line why', for a module whose DIRECTION row is row."""
    out = []

    def refuse(node, why):
        out.append("%s:%d %s" % (name, node.lineno, why))

    def allow(node, module):
        top, _, inner = module.partition(".")
        if top == "engine":
            if inner and inner.split(".")[0] not in row:
                refuse(node, "imports engine.%s, which its row in DIRECTION does not name" % inner)
        elif top not in BUILT_IN and not (top == C_MODULE and top in row):
            refuse(node, "imports %s: neither engine.<module>, a built-in module nor the C module its row names" % module)

    for node in ast.walk(ast.parse(source, name)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                allow(node, alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level > 1:
                refuse(node, "imports from outside the package (%s)" % ("." * node.level + (node.module or "")))
            elif node.level == 1:
                for inner in ([node.module] if node.module else [a.name for a in node.names]):
                    allow(node, "engine." + inner)
            elif node.module == "engine":
                for alias in node.names:
                    allow(node, "engine." + alias.name)
            else:
                allow(node, node.module)
        elif isinstance(node, ast.Name) and node.id == "__import__" or \
                isinstance(node, ast.Attribute) and node.attr == "__import__":
            refuse(node, "imports through __import__")
    return out


def read(path):
    with open(path) as f:
        return f.read()


class Boundary(unittest.TestCase):
    def test_no_package_module_imports_outside_the_engine(self):
        found = []
        for name, path in sorted(package_modules().items()):
            found += faults(read(path), DIRECTION.get(name, ()), name)
        self.assertEqual([], found)

    def test_each_fixture_is_caught(self):
        names = sorted(n for n in os.listdir(FIXTURES) if n.endswith(".py"))
        self.assertLessEqual(13, len(names))
        for name in names:
            with self.subTest(name):
                self.assertFalse(name.startswith("test"), "discovery would run it")
                self.assertEqual(1, len(faults(read(os.path.join(FIXTURES, name)), FIXTURE_ROW, name)))

    def test_a_fixture_s_import_passes_when_its_row_names_it(self):
        """The C module is allowed by a row (accel's, from 0b-2), engine_config and importlib by none."""
        self.assertEqual([], faults("import _engine\nfrom engine import signals\n", ("_engine", "signals")))
        self.assertEqual([], faults("from . import signals\nfrom .signals import Signals\nimport time\n", ("signals",)))
        self.assertEqual(1, len(faults("import engine_config\n", ("engine_config",))))
        self.assertEqual(1, len(faults("import importlib\n", ("importlib",))))
        self.assertEqual(1, len(faults("import signals\n", ("signals",))))  # a sibling only as engine.signals
        self.assertEqual(1, len(faults("import gfx\n", ("gfx",))))  # a row names no game

    def test_the_imports_follow_the_direction_table(self):
        modules = package_modules()
        self.assertEqual(sorted(modules), sorted(DIRECTION), "each package module has a row, each row a module")
        for name, row in DIRECTION.items():
            for allowed in row:
                with self.subTest(name=name, allowed=allowed):
                    self.assertIn(allowed, set(modules) - {name} | {C_MODULE})


class TwoEngines(unittest.TestCase):
    """The package in games/ against the submodule at the root, which has no __init__.py and so is a namespace
    package: on CPython a regular package wins over it wherever each stands on sys.path. MicroPython takes the first
    folder on the path, but on the board games/ is the root, so the board has no second engine folder."""

    def test_engine_is_the_package_in_games(self):
        for path in ([GAMES], [ROOT, GAMES], [GAMES, ROOT]):
            with self.subTest(path=path):
                run = subprocess.run([sys.executable, "-I", "-B", "-c",
                                      "import sys; sys.path[:0] = %r; import engine; print(engine.__file__)" % path],
                                     cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(0, run.returncode, run.stderr)
                self.assertEqual(os.path.join(PACKAGE, "__init__.py"), run.stdout.strip())

    def test_the_submodule_has_no_init(self):
        self.assertTrue(os.path.isdir(os.path.join(ROOT, "engine", "core")), "the submodule is checked out")
        self.assertFalse(os.path.exists(os.path.join(ROOT, "engine", "__init__.py")))


if __name__ == "__main__":
    unittest.main()
