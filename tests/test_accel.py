"""engine.accel's Chooser (P850, stage 0b-2 of the engine plan): it chooses each part's version once, the fast class or
the reference class, and its boot line says what it chose and why, in the order of the choose calls, with the native
code it finds and each forced name that no call used. Run from the repository root:
python3 -B -m unittest tests.test_accel. --- MVP (P850) ---"""

import ast
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))

from engine import accel  # noqa: E402

ACCEL = os.path.join(os.path.dirname(HERE), "games", "engine", "accel.py")


class Plain:
    """A part's reference version."""


class Fast(Plain):
    """Its fast version."""


def fast():
    return Fast


def missing():
    raise ImportError("no module named 'sound_viper'")


def no_native():
    """No _engine and no _crackle.mpy, as on the Mac."""
    return mock.patch.multiple(accel, CRACKLE=os.path.join(HERE, "fixtures", "no-such-folder", "_crackle.mpy")), \
        mock.patch.dict(sys.modules, {"_engine": None})


class ChooserTest(unittest.TestCase):
    def setUp(self):
        for patch in no_native():
            patch.start()
            self.addCleanup(patch.stop)

    def test_no_config_forces_nothing(self):
        chooser = accel.Chooser()
        self.assertIs(Fast, chooser.choose("sum", fast, Plain, "viper"))
        self.assertEqual("engine sum=viper native=none", chooser.line())

    def test_a_forced_part_takes_its_reference(self):
        chooser = accel.Chooser(reference=("volume",))
        self.assertIs(Fast, chooser.choose("sum", fast, Plain, "viper"))
        self.assertIs(Plain, chooser.choose("volume", fast, Plain, "viper"))
        self.assertEqual("engine sum=viper volume=reference(forced) native=none", chooser.line())

    def test_a_forced_part_never_imports_its_fast_version(self):
        chooser = accel.Chooser(reference=("sum",))
        self.assertIs(Plain, chooser.choose("sum", missing, Plain, "viper"))
        self.assertEqual("engine sum=reference(forced) native=none", chooser.line())

    def test_a_missing_fast_version_takes_the_reference_and_says_why(self):
        def broken():
            raise AttributeError("ptr16")

        def unparsed():
            raise SyntaxError("viper")

        chooser = accel.Chooser()
        self.assertIs(Plain, chooser.choose("sum", missing, Plain, "viper"))
        self.assertIs(Plain, chooser.choose("volume", broken, Plain, "viper"))
        self.assertIs(Plain, chooser.choose("bodies", unparsed, Plain, "c"))
        self.assertEqual("engine sum=reference(ImportError) volume=reference(AttributeError) "
                         "bodies=reference(SyntaxError) native=none", chooser.line())

    def test_any_other_error_of_a_fast_version_is_not_hidden(self):
        def failing():
            raise ValueError("a bug in the fast version")

        with self.assertRaises(ValueError):
            accel.Chooser().choose("sum", failing, Plain, "viper")

    def test_the_line_names_the_parts_in_call_order(self):
        chooser = accel.Chooser()
        for part in ("volume", "sum", "bodies"):
            chooser.choose(part, fast, Plain, "viper")
        self.assertEqual("engine volume=viper sum=viper bodies=viper native=none", chooser.line())

    def test_all_forces_every_part(self):
        chooser = accel.Chooser(reference="all")
        self.assertIs(Plain, chooser.choose("sum", fast, Plain, "viper"))
        self.assertIs(Plain, chooser.choose("volume", fast, Plain, "viper"))
        self.assertEqual("engine sum=reference(forced) volume=reference(forced) native=none", chooser.line())

    def test_an_unused_forced_name_shows_in_the_line(self):
        chooser = accel.Chooser(reference=("volume", "bodys", "heat"))
        chooser.choose("sum", fast, Plain, "viper")
        chooser.choose("volume", fast, Plain, "viper")
        self.assertEqual("engine sum=viper volume=reference(forced) native=none unused=bodys,heat", chooser.line())

    def test_a_bare_name_is_one_part_not_its_letters(self):
        chooser = accel.Chooser(reference="volume")
        self.assertIs(Fast, chooser.choose("vol", fast, Plain, "viper"))  # not a part of "volume"'s letters
        self.assertIs(Plain, chooser.choose("volume", fast, Plain, "viper"))
        self.assertEqual("engine vol=viper volume=reference(forced) native=none", chooser.line())

    def test_native_names_engine_and_the_crackle_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            crackle = os.path.join(tmp, "_crackle.mpy")
            open(crackle, "wb").close()
            with mock.patch.object(accel, "CRACKLE", crackle), \
                    mock.patch.dict(sys.modules, {"_engine": types.ModuleType("_engine")}):
                self.assertEqual("engine native=_engine,_crackle.mpy", accel.Chooser().line())
            with mock.patch.object(accel, "CRACKLE", crackle):
                self.assertEqual("engine native=_crackle.mpy", accel.Chooser().line())
        with mock.patch.dict(sys.modules, {"_engine": types.ModuleType("_engine")}):
            self.assertEqual("engine native=_engine", accel.Chooser().line())

    def test_the_crackle_is_looked_for_at_the_board_s_root(self):
        with open(ACCEL) as f:  # setUp patched the module's value
            self.assertIn('\nCRACKLE = "/_crackle.mpy"', f.read())


class NoCrackleTest(unittest.TestCase):
    def test_accel_never_imports_crackle(self):
        """Native code takes executable memory until the next soft reset, so the boot only looks for the file."""
        with open(ACCEL) as f:
            tree = ast.parse(f.read())
        names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        names += [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertEqual(["_engine", "os"], sorted(set(names)))
        with tempfile.TemporaryDirectory() as tmp:
            crackle = os.path.join(tmp, "_crackle.mpy")
            open(crackle, "wb").close()
            with mock.patch.object(accel, "CRACKLE", crackle), mock.patch.dict(sys.modules):
                sys.modules.pop("_crackle", None)
                accel.Chooser().line()
                self.assertNotIn("_crackle", sys.modules)


if __name__ == "__main__":
    unittest.main()
