"""The net (P846, stage N of the engine plan P844): every game's frames, its cues, the box's game and switch lines and
the mixer's samples, pinned by hashes on the Mac in tests/golden/. A move that changes a picture or a sound fails here.
Each subject renders in its own process, NET_WORKERS (8) at a time. NET_TIER=fast compares frames 1 and 5 and the
cues up to frame 5 (the story run); the full tier, the default, compares every pinned frame and the cues of the whole
run. The net fails, never skips: with no clang or no font it names the command that brings it. A hash change is its own
PR, written by `python3 -B tools/render_scene.py --golden tests/golden` on the baseline commit.
Run from the repository root: python3 -B -m unittest tests.test_golden. --- MVP (P846) ---"""

import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import net  # noqa: E402  first: it puts games/, the stubs and tools/ on the path

import catalog  # noqa: E402
import render_scene  # noqa: E402

GOLDEN = os.path.join(HERE, "golden")
TIER = net.tier()
TWICE = "cave"  # the subject rendered twice in one run
# Each negative test: a short subject, full tier, with one patch made in its process before the render
COLOUR = "import arcade2\narcade2.Cave.bg = arcade2.c565(15, 10, 28)"  # its background, one step of blue more
MOVED = "import arcade\narcade.Flappy.X = 81"  # the bird one px to the right
PRESS = "import render_scene\nrender_scene.SUBJECTS['flappy'].tap = 13"  # a tap every 13 frames, not 12
CUE = ("import arcade\nemit = arcade.Runner.emit\n"  # the jump says hop: a cue no table plays
       "arcade.Runner.emit = lambda self, name, value=None: emit(self, 'hop' if name == 'jump' else name, value)")
NEGATIVE = {"colour": ("cave", COLOUR), "moved": ("flappy", MOVED), "press": ("flappy", PRESS), "cue": ("runner", CUE)}


class CatalogTest(unittest.TestCase):
    def test_subjects_match_the_catalog(self):
        games = {row.game for row in render_scene.SUBJECTS.values()}
        missing = [name for name, module, cls, _ in catalog.CATALOG if getattr(__import__(module), cls) not in games]
        self.assertEqual([], missing, "a game of catalog.py with no row in render_scene.SUBJECTS")


class GoldenFlagTest(unittest.TestCase):
    def test_golden_refuses_the_other_flags_and_writes_nothing(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "golden")
            for flags in (("--tap", "3"), ("--no-text",), ("--font", "x.h"), ("snake",)):
                with self.subTest(flags):
                    run = subprocess.run([sys.executable, "-B", render_scene.__file__, "--golden", out, *flags],
                                         capture_output=True, text=True)
                    self.assertEqual(2, run.returncode)
                    self.assertIn(flags[0], run.stderr)
                    self.assertFalse(os.path.exists(out))


class FilesTest(unittest.TestCase):
    """What tests/golden holds, read without a render."""

    @classmethod
    def setUpClass(cls):
        cls.golden = net.Golden.read(GOLDEN)

    def test_every_subject_has_hashes(self):
        for name, row in render_scene.SUBJECTS.items():
            with self.subTest(name):
                self.assertEqual(net.counts(row, net.FULL), sorted(int(n) for n in self.golden.frames.get(name, {})))
                self.assertIn(name, self.golden.cues)
        self.assertEqual(len(catalog.NAMES) + 1, len(self.golden.app.get("frames", {})))  # the start and each pick
        self.assertEqual(64, len(self.golden.mixer.get("sha256", "")))

    def test_every_game_with_cues_records_one(self):
        for name, row in render_scene.SUBJECTS.items():
            if row.game.cues:
                with self.subTest(name):
                    heard = [signal for _, signal, _ in self.golden.cues.get(name, ())]
                    self.assertTrue(set(heard) & set(row.game.cues), "%s's run plays none of its cues" % name)

    def test_the_toolchain_is_recorded(self):
        self.assertEqual(sorted(net.Toolchain.FIELDS), sorted(self.golden.meta))


class ToolchainTest(unittest.TestCase):
    """The net fails, never skips, when a tool is missing or not the one the hashes were made with."""

    def test_no_clang_fails_and_names_the_command(self):
        with mock.patch.object(net.shutil, "which", return_value=None):
            with self.assertRaisesRegex(net.NetError, "xcode-select --install"):
                net.Toolchain.here()

    def test_no_font_fails_and_names_the_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(net.NetError, "build.sh"):
                net.Toolchain.here(os.path.join(tmp, "none.h"))

    def test_a_changed_toolchain_fails_and_says_regenerate(self):
        here = net.Toolchain.here()
        for field in net.Toolchain.FIELDS:
            with self.subTest(field):
                recorded = dict(here.record, **{field: "another"})
                with self.assertRaisesRegex(net.NetError, "toolchain changed: regenerate on the baseline commit first"):
                    here.check(recorded)
        here.check(dict(here.record))


class NetTest(unittest.TestCase):
    """One run of every subject, the App level, the mixer, a second run of TWICE and the negative tests' renders,
    all in one pool."""

    @classmethod
    def setUpClass(cls):
        cls.golden = net.Golden.read(GOLDEN)
        net.Toolchain.here().check(cls.golden.meta)
        jobs = [net.Job(name, TIER) for name in render_scene.SUBJECTS] + [net.Job(net.APP), net.Job(net.MIXER)]
        jobs.append(net.Job(TWICE, TIER))
        jobs += [net.Job(name, net.FULL, patch) for name, patch in NEGATIVE.values()]
        results = net.run(jobs)
        cls.subjects = dict(zip(render_scene.SUBJECTS, results))
        n = len(render_scene.SUBJECTS)
        cls.app, cls.mixer, cls.twice = results[n:n + 3]
        cls.negative = dict(zip(NEGATIVE, results[n + 3:]))

    def test_every_subject_matches_its_hashes_and_cues(self):
        for name, got in self.subjects.items():
            with self.subTest(name):
                self.assertEqual([], net.differences(self.golden.subject(name, TIER), got))

    def test_the_app_level_matches(self):
        self.assertEqual(self.golden.app["lines"], self.app["lines"])
        self.assertEqual(self.golden.app["frames"], self.app["frames"])

    def test_the_mixer_matches(self):
        self.assertEqual(self.golden.mixer, self.mixer)

    def test_two_runs_give_the_same_hashes(self):
        self.assertEqual(self.subjects[TWICE], self.twice)

    def caught(self, kind):
        name = NEGATIVE[kind][0]
        return net.differences(self.golden.subject(name, net.FULL), self.negative[kind])

    def test_a_changed_colour_is_caught(self):
        self.assertTrue(any(d.startswith("frame 1 ") for d in self.caught("colour")), self.caught("colour"))

    def test_a_moved_sprite_is_caught(self):
        self.assertTrue(any(d.startswith("frame ") for d in self.caught("moved")), self.caught("moved"))

    def test_a_changed_press_timing_is_caught(self):
        self.assertTrue(self.caught("press"))
        self.assertNotIn("frame 1 differs", self.caught("press"))  # the first press is the same: later frames differ

    def test_a_changed_cue_is_caught(self):
        self.assertEqual(["cues differ"], [d.split(":")[0] for d in self.caught("cue")])  # the frames are the same


if __name__ == "__main__":
    unittest.main()
