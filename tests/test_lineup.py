"""The box's lineup (P817) on the Mac: games/catalog.py against the game classes and the packs, app.games_for, which
imports only the games it names, app.Lineup, and app.read_lineup with no lineup.py, a good one and each one it
refuses. Run from the repository root: python3 -B -m unittest tests.test_lineup. --- MVP (P817) ---"""

import contextlib
import importlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
GAMES = os.path.join(os.path.dirname(HERE), "games")
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, GAMES)
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)
if not hasattr(time, "ticks_add"):
    time.ticks_add = lambda a, b: a + b

import app  # noqa: E402
import art_index  # noqa: E402
import catalog  # noqa: E402
import pictures  # noqa: E402

GAME_MODULES = sorted({row[1] for row in catalog.CATALOG})


class CatalogTest(unittest.TestCase):
    def test_each_row_names_its_class_by_the_class_s_name(self):
        for name, module, class_name, sets in catalog.CATALOG:
            with self.subTest(name):
                self.assertEqual(name, getattr(importlib.import_module(module), class_name).name)
        self.assertEqual(15, len(catalog.NAMES))
        self.assertEqual(len(catalog.NAMES), len(set(catalog.NAMES)))

    def test_each_game_s_sets_are_the_ones_its_setup_loads(self):
        seen = []
        load = pictures.load
        pictures.load = lambda game=None, only=None: seen.append(game) or False
        try:
            for name, cls in zip(catalog.NAMES, app.games_for(catalog.NAMES)):
                with self.subTest(name), contextlib.redirect_stdout(io.StringIO()):
                    seen.clear()
                    cls()
                    self.assertEqual(catalog.CATALOG[catalog.NAMES.index(name)][3], tuple(dict.fromkeys(seen)))
        finally:
            pictures.load = load

    def test_each_set_has_a_pack(self):
        for name, module, class_name, sets in catalog.CATALOG:
            for s in sets:
                self.assertTrue(os.path.isfile(os.path.join(GAMES, art_index.PACKS[s][0])), s)

    def test_catalog_imports_nothing(self):
        with open(os.path.join(GAMES, "catalog.py")) as f:
            self.assertNotRegex(f.read(), r"(?m)^\s*(import|from) ")


class GamesForTest(unittest.TestCase):
    def test_it_keeps_the_order_and_imports_only_the_named_games(self):
        code = ("import sys, time; sys.path[:0] = [%r, %r]; time.ticks_ms = lambda: 0; time.ticks_diff = lambda a, b: 0; "
                "import app; print(sorted(m for m in %r if m in sys.modules)); "
                "print([c.name for c in app.games_for(('road', 'balls'))]); "
                "print(sorted(m for m in %r if m in sys.modules))") % (
            GAMES, os.path.join(HERE, "stubs"), GAME_MODULES, GAME_MODULES)
        run = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True)
        self.assertEqual(0, run.returncode, run.stderr[-500:])
        self.assertEqual(["[]", "['road', 'balls']", "['balls', 'world3d']"], run.stdout.split("\n")[-4:-1])

    def test_an_unknown_name_raises_naming_it(self):
        with self.assertRaisesRegex(ValueError, "nope"):
            app.games_for(("snake", "nope"))


class LineupTest(unittest.TestCase):
    def test_a_lineup_of_names_builds_each_game_only_when_asked(self):
        lineup = app.Lineup(("cave", "road"))
        self.assertEqual((2, ("cave", "road")), (len(lineup), lineup.names))
        self.assertEqual("road", lineup.game(1).name)

    def test_a_lineup_of_classes_builds_them(self):
        class Game:
            name = "fake"
        lineup = app.Lineup.of([Game])
        self.assertEqual(("fake",), lineup.names)
        self.assertIsInstance(lineup.game(0), Game)

    def test_the_box_takes_classes_or_a_lineup(self):
        class Out:
            def clear(self):
                pass

            def reset(self):
                pass
        with contextlib.redirect_stdout(io.StringIO()):
            box = app.App(None, lambda: 1, lambda: 1, games=app.Lineup(("cave", "road")), out=Out())
            box.start()
        self.assertEqual("cave", box.game.name)
        self.assertEqual(2, len(box.games))


class Out:
    def clear(self):
        pass

    def reset(self):
        pass


class MissingModuleTest(unittest.TestCase):
    """A lineup name whose module the board lacks (a copy by hand left it out) is refused, and the box goes on."""

    GHOST = {"ghost": ("ghost", "no_such_module_p817", "Ghost", ())}

    def test_the_box_refuses_it_aloud_and_builds_the_next_game(self):
        with mock.patch.dict(catalog.ROWS, self.GHOST), contextlib.redirect_stdout(io.StringIO()) as said:
            box = app.App(None, lambda: 1, lambda: 1, games=app.Lineup(("ghost", "cave")), out=Out())
            box.start()
            self.assertEqual(("cave", 1), (box.game.name, box.index))
            box.switch()
            self.assertEqual(("cave", 1), (box.game.name, box.index))
        self.assertEqual(2, said.getvalue().count("game ghost refused: No module named 'no_such_module_p817'\n"))

    def test_when_every_game_fails_the_error_is_raised_once(self):
        with mock.patch.dict(catalog.ROWS, self.GHOST), contextlib.redirect_stdout(io.StringIO()) as said:
            box = app.App(None, lambda: 1, lambda: 1, games=app.Lineup(("ghost",)), out=Out())
            with self.assertRaises(ImportError):
                box.start()
        self.assertEqual(1, said.getvalue().count("game ghost refused"))


class SayLineupTest(unittest.TestCase):
    def test_the_lineup_and_import_lines(self):
        with contextlib.redirect_stdout(io.StringIO()) as said:
            app.say_lineup(app.Lineup(("cave", "road")))
        self.assertEqual("lineup 2: cave road\nimport %d ms\n" % app.IMPORT_MS, said.getvalue())


class ReadLineupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        sys.path.insert(0, self.tmp.name)
        sys.modules.pop("lineup", None)

    def tearDown(self):
        sys.path.remove(self.tmp.name)
        sys.modules.pop("lineup", None)
        self.tmp.cleanup()

    def read(self, text=None):
        if text is not None:
            with open(os.path.join(self.tmp.name, "lineup.py"), "w") as f:
                f.write(text)
        shutil.rmtree(os.path.join(self.tmp.name, "__pycache__"), ignore_errors=True)  # two texts of one size
        importlib.invalidate_caches()
        with contextlib.redirect_stdout(io.StringIO()) as said:
            names = app.read_lineup()
        return names, said.getvalue()

    def test_no_lineup_is_every_game(self):
        self.assertEqual((catalog.NAMES, ""), self.read())

    def test_a_good_lineup_is_its_names_in_its_order(self):
        self.assertEqual((("snake", "flappy"), ""), self.read("LINEUP = ('snake', 'flappy')\n"))

    def test_each_broken_lineup_is_refused_aloud_and_the_box_plays_every_game(self):
        for text, why in (("LINEUP = (\n", "SyntaxError"), ("raise OSError(5)\n", "OSError"),
                          ("GAMES = ('snake',)\n", "not a tuple"), ("LINEUP = ['snake']\n", "not a tuple"),
                          ("LINEUP = ('snake', 3)\n", "not a tuple"), ("LINEUP = ()\n", "empty"),
                          ("LINEUP = ('snake', 'nope')\n", "no game nope"),
                          ("LINEUP = ('snake', 'cave', 'snake')\n", "snake is in LINEUP twice")):
            with self.subTest(text):
                sys.modules.pop("lineup", None)
                names, said = self.read(text)
                self.assertEqual(catalog.NAMES, names)
                self.assertTrue(said.startswith("lineup refused: "), said)
                self.assertIn(why, said)


if __name__ == "__main__":
    unittest.main()
