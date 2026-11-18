"""The set figures (P904 step 2c, art/figures.py): Rescue's still street and the eight characters of art/detailed.py's
CAST, each running facing right and facing left, written as one pack and an index of that pack alone for
probe904_figures.py. The cast is painted from the CMU files once for every test here (about 53 s on the Mac) and
written once: skipped without the files, and a skip is not a pass. Run from the repository root:
python3 -B -m unittest tests.test_figures."""

import os
import sys
import tempfile
import time
import types
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "art"))  # the art modules import each other by their plain names
sys.path.insert(0, os.path.join(REPO, "tests", "stubs"))
sys.path.insert(0, os.path.join(REPO, "games"))
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)

import detailed  # noqa: E402
import figures  # noqa: E402
import mocap  # noqa: E402
import pictures  # noqa: E402
from export import HEADER, MAGIC, build_id, to_bin  # noqa: E402
from sets import ART_SETS  # noqa: E402
from sets.rescue import read_committed  # noqa: E402

POSES = 12  # a run's poses
FOLDER = tempfile.TemporaryDirectory()  # the written pack and index, once for the module
WRITTEN = {}  # "paths": what figures.write answered


def setUpModule():
    unittest.addModuleCleanup(FOLDER.cleanup)


def written():
    """figures.write into FOLDER, once: (the pack's path, the index's path)."""
    if "paths" not in WRITTEN:
        WRITTEN["paths"] = figures.write(FOLDER.name)
    return WRITTEN["paths"]


def index_module(path):
    """The written art_index.py as a module, as the board imports it."""
    module = types.ModuleType("art_index")
    with open(path) as f:
        exec(f.read(), module.__dict__)
    return module


def names():
    """The set's names as the plan orders them: the street, then each character's run facing right, then left."""
    return ["figures_night"] + ["figures_%s_%s%d" % (c.name, side, i) for c, _ in detailed.CAST for side in "rl"
                                for i in range(POSES)]


class SetTest(unittest.TestCase):
    """The set's record: no paint."""

    def test_the_set_is_figures_on_its_own_seed_and_in_no_art_set(self):
        self.assertEqual(("figures", detailed.SEED), (figures.ART_SET.name, figures.ART_SET.seed))
        self.assertNotIn("figures", [art_set.name for art_set in ART_SETS])
        self.assertFalse(figures.ART_SET.index_layers)


class FiguresFromCaptureTest(unittest.TestCase):
    """The set painted from the CMU files: skipped without them, and a skip is not a pass."""

    @classmethod
    def setUpClass(cls):
        if mocap.Capture().missing():
            raise unittest.SkipTest("the CMU files are not in %s" % mocap.CMU_DIR)
        cls.runs = figures.cast(None)
        cls.painting = figures.ART_SET.paint()

    def test_its_pictures_are_the_193_names_in_order_and_only_the_street_is_not_keyed(self):
        self.assertEqual(names(), list(self.painting.pictures))
        self.assertEqual(193, len(set(self.painting.pictures)))
        self.assertEqual([False] + [True] * 192, [keyed for _, keyed in self.painting.pictures.values()])
        self.assertEqual([], self.painting.layers)

    def test_the_street_is_rescues_committed_night(self):
        street = read_committed(["rescue_night"])["rescue_night"]
        self.assertEqual(street.tobytes(), self.painting.pictures["figures_night"][0].tobytes())

    def test_each_characters_pictures_are_its_runs_poses_right_and_left(self):
        self.assertEqual([c for c, _ in detailed.CAST], [run.character for run in self.runs])
        for run in self.runs:
            for i in range(POSES):
                with self.subTest(character=run.character.name, pose=i):
                    right = self.painting.pictures["figures_%s_r%d" % (run.character.name, i)][0]
                    left = self.painting.pictures["figures_%s_l%d" % (run.character.name, i)][0]
                    self.assertEqual(run.pictures[i].tobytes(), right.tobytes())
                    self.assertEqual(run.left[i].tobytes(), left.tobytes())
                    self.assertNotEqual(right.tobytes(), left.tobytes())  # a pose is no mirror of itself

    def test_the_gaits_are_each_runs_name_pivot_stride_and_speed(self):
        gaits = figures.gaits(None)
        self.assertEqual([(run.character.name, run.pivot[0], run.stride, run.speed) for run in self.runs],
                         list(gaits))
        # a gait is its cycle's: two characters on one cycle at full size move alike, and the five cycles do not
        self.assertEqual(5, len({cycle for _, cycle in detailed.CAST}))
        self.assertEqual(5, len({gait[1:] for gait in gaits}))

    def test_the_pack_holds_the_header_the_street_and_every_run_with_both_facings(self):
        pack, _ = written()
        size = os.path.getsize(pack)
        self.assertEqual(HEADER + 320 * 240 * 2 + sum(run.size_bytes() for run in self.runs), size)
        with open(pack, "rb") as f:
            data = f.read()
        self.assertEqual(MAGIC + build_id(data[HEADER:]), data[:HEADER])
        self.assertEqual(os.path.join(FOLDER.name, "packs", "figures.pak"), pack)

    def test_the_index_names_the_pack_on_the_boards_path_with_its_size_and_build(self):
        pack, path = written()
        index = index_module(path)
        with open(pack, "rb") as f:
            data = f.read()
        self.assertEqual({"figures": ("packs/figures.pak", len(data), data[len(MAGIC):HEADER].hex())}, index.PACKS)
        self.assertEqual({"figures": tuple(names())}, index.PICTURE_SETS)
        self.assertEqual({"figures": []}, index.LAYER_SETS)
        self.assertEqual(os.path.join(FOLDER.name, "art_index.py"), path)

    def test_pictures_load_reads_the_written_pack_through_the_written_index(self):
        pack, path = written()
        old_index, old_root = pictures.art_index, pictures.ROOT
        pictures.art_index, pictures.ROOT = index_module(path), os.path.join(FOLDER.name, "")
        pictures.free()
        try:
            self.assertTrue(pictures.load("figures"))
            self.assertEqual(set(names()), set(pictures.PICS))
            for name in ("figures_night", "figures_paramedic_l7", "figures_acrobat_r11", "figures_child_l0"):
                with self.subTest(name=name):
                    img, keyed = self.painting.pictures[name]
                    w, h, view = pictures.PICS[name]
                    self.assertEqual(img.size, (w, h))
                    self.assertEqual(to_bin(img, keyed), bytes(view))
        finally:
            pictures.free()
            pictures.art_index, pictures.ROOT = old_index, old_root


if __name__ == "__main__":
    unittest.main()
