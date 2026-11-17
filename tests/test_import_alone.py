"""Each module of the engine package and of the drivers package (P851) imports alone (P849, stage 0b-1 of the engine
plan): a later board takes only the modules it needs (the T-Display, only input and the link), so no module may lean
on one that another imported first.
Each import runs in a fresh interpreter with -I -B (no user site, no PYTHONPATH, no .pyc), all of them in one pool of
threads, with games/ and the stubs on the path as the tests put them. Run from the repository root:
python3 -B -m unittest tests.test_import_alone. --- MVP (P849) ---"""

import os
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_engine_boundary import GAMES, package_modules  # noqa: E402

PATH = [GAMES, os.path.join(HERE, "stubs")]
DRIVERS = os.path.join(GAMES, "drivers")


def driver_modules():
    """Each module of the drivers package (P851) as drivers.<name>, and the package itself."""
    names = sorted(n[:-3] for n in os.listdir(DRIVERS) if n.endswith(".py") and n != "__init__.py")
    return ["drivers"] + ["drivers." + n for n in names]


def import_alone(name):
    """The run of a fresh interpreter that imports engine.<name> (the package itself for __init__), or a driver's
    module named in full (drivers.<name>)."""
    module = name if name.split(".")[0] == "drivers" else "engine" if name == "__init__" else "engine." + name
    return subprocess.run([sys.executable, "-I", "-B", "-c", "import sys; sys.path[:0] = %r; import %s" % (PATH, module)],
                          cwd=HERE, capture_output=True, text=True)


class ImportAlone(unittest.TestCase):
    def test_each_package_module_imports_alone(self):
        names = sorted(package_modules()) + driver_modules()
        self.assertIn("signals", names)
        self.assertIn("actions", names)
        self.assertIn("drivers.stick", names)
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            runs = dict(zip(names, pool.map(import_alone, names)))
        for name, run in runs.items():
            with self.subTest(name):
                self.assertEqual(0, run.returncode, run.stderr[-500:])


if __name__ == "__main__":
    unittest.main()
