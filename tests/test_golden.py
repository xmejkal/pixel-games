"""The net (P846, stage N of the engine plan P844): every game's frames, its cues, the box's game and switch lines and
the mixer's samples, pinned by hashes on the Mac in tests/golden/. A move that changes a picture or a sound fails here.
Each subject renders in its own process, NET_WORKERS (8) at a time. NET_TIER=fast compares frames 1 to 5 and the cues
up to frame 5 (the story run); the negative tests, which prove that the net catches a change, live in
tests/test_golden_negative.py, which the full suite and the full tier run. The full tier, the default, compares
every pinned frame, the chained run, the game-over cards, the cues and their sound over the whole run. The net fails,
never skips, when a tool is missing: with no clang or no font it names the command that brings it. A hash change is
its own PR, written by `python3 -B tools/render_scene.py --golden tests/golden` on the baseline commit.
Run from the repository root: NET_TIER=fast python3 -B -m unittest tests.test_golden (the story run), or the full tier:
python3 -B -m unittest tests.test_golden tests.test_golden_negative. --- MVP (P846) ---"""

import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import net  # noqa: E402  first: it puts games/, the stubs and tools/ on the path

import render_scene  # noqa: E402

m = net.modules()
GOLDEN = os.path.join(HERE, "golden")
TWICE = "cave"  # the subject rendered twice in one run
OWN_CARDS = ("snake", "stack", "gravpong", "cube")  # the games that draw their own game-over card, by catalog name
# The cues of a game's table that no run of the net emits: pinned here so the thin spots stay in sight
UNRECORDED = {"bucket": ["die"], "marshmallow": ["burn", "die"], "meteors": ["die"], "rescue": ["help", "help_child"],
              "runner": ["die", "pickup"]}


class CatalogTest(unittest.TestCase):
    def test_subjects_match_the_catalog(self):
        games = {row.game for row in render_scene.SUBJECTS.values()}
        missing = [name for name, module, cls, _ in m.catalog.CATALOG if getattr(__import__(module), cls) not in games]
        self.assertEqual([], missing, "a game of catalog.py with no row in render_scene.SUBJECTS")


class GoldenFlagTest(unittest.TestCase):
    def test_golden_refuses_the_other_flags_and_writes_nothing(self):
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
        for name, row in net.ROWS.items():
            with self.subTest(name):
                record = self.golden.subjects.get(name, {})
                over = record.get("over")
                want = sorted(set(net.counts(row, net.FULL)) | ({over[1]} if over else set()))
                self.assertEqual(want, sorted(int(n) for n in record.get("frames", {})))
                for key in ("run", "run_to_5"):
                    self.assertEqual(64, len(record.get(key) or ""), key)
                self.assertIsNotNone(record.get("table"))
                self.assertEqual(bool(record["table"]), record.get("sound") is not None)  # a game with cues: its sound
        names = m.catalog.NAMES
        self.assertEqual(len(names) + 3, len(self.golden.app.get("frames", {})))  # the start, each pick, over, restart
        self.assertEqual(64, len(self.golden.mixer.get("sha256", "")))

    def test_every_kind_of_game_over_card_is_pinned(self):
        reached = {row.game for name, row in net.ROWS.items() if self.golden.subjects.get(name, {}).get("over")}
        own = {getattr(__import__(m.catalog.ROWS[n][1]), m.catalog.ROWS[n][2]) for n in OWN_CARDS}
        self.assertEqual(set(), own - reached, "a game's own card with no subject that reaches it")
        shared = [g for g in reached if g.draw_over is m.gfx.Game.draw_over]
        self.assertTrue(shared, "no subject reaches the shared game-over box")
        for game in own:
            self.assertIsNot(m.gfx.Game.draw_over, game.draw_over, game.name)

    def test_every_game_with_cues_records_one(self):
        for name, row in net.ROWS.items():
            if row.game.cues:
                with self.subTest(name):
                    heard = [signal for _, signal, _ in self.golden.subjects.get(name, {}).get("cues") or ()]
                    self.assertTrue(set(heard) & set(row.game.cues), "%s's run plays none of its cues" % name)

    def test_the_cues_no_run_emits_are_the_listed_ones(self):
        heard, tables = {}, {}
        for name, row in net.ROWS.items():
            record = self.golden.subjects.get(name, {})
            tables[row.game.name] = set(record.get("table") or ())
            heard.setdefault(row.game.name, set()).update(c[1] for c in record.get("cues") or ())
        silent = {game: sorted(tables[game] - heard[game]) for game in tables if tables[game] - heard[game]}
        self.assertEqual(UNRECORDED, silent)

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
    """One run, at NET_TIER's tier, of every subject, the App level, the mixer and a second run of TWICE, in one pool."""

    @classmethod
    def setUpClass(cls):
        cls.tier = net.tier()
        cls.golden = net.Golden.read(GOLDEN)
        net.Toolchain.here().check(cls.golden.meta)
        jobs = [net.Job(name, cls.tier) for name in net.ROWS] + [net.Job(net.APP), net.Job(net.MIXER)]
        results = net.run(jobs + [net.Job(TWICE, cls.tier)])
        cls.subjects = dict(zip(net.ROWS, results))
        cls.app, cls.mixer, cls.twice = results[len(net.ROWS):]

    def test_every_subject_matches_its_hashes_and_cues(self):
        for name, got in self.subjects.items():
            with self.subTest(name):
                self.assertEqual([], net.differences(self.golden.subject(name, self.tier), got))

    def test_the_app_level_matches(self):
        self.assertEqual(self.golden.app["lines"], self.app["lines"])
        self.assertEqual(self.golden.app["frames"], self.app["frames"])

    def test_the_mixer_matches(self):
        self.assertEqual(self.golden.mixer, self.mixer)

    def test_two_runs_give_the_same_hashes(self):
        self.assertEqual(self.subjects[TWICE], self.twice)


class ChosenMixerTest(unittest.TestCase):
    """The mixer golden through the classes main.py chooses with no engine_config (P850, stage 0b-2): the fast sum and
    the fast volume, viper code that the Mac runs as plain Python with test_voices' pointers. The Mac cannot see a
    32-bit overflow, so sum_match and scale_match also run on the board."""

    def test_the_reference_and_the_chosen_class_give_equal_samples(self):
        import main
        import sound_viper
        import volume_viper
        from engine.accel import Chooser
        from test_voices import Ptr

        chosen = main.choose(Chooser())
        self.assertEqual((sound_viper.ViperVoiceSum, volume_viper.ViperMasterVolume), chosen)
        with mock.patch.object(sound_viper, "ptr16", lambda buf: Ptr(buf, "H", 0xFFFF), create=True), \
                mock.patch.object(sound_viper, "ptr32", lambda buf: Ptr(buf, "i", 0), create=True), \
                mock.patch.object(volume_viper, "ptr16", lambda buf: Ptr(buf, "H", 0xFFFF), create=True):
            got = net.record_mixer(*chosen)
        self.assertEqual(net.Golden.read(GOLDEN).mixer, got)
        self.assertEqual(net.record_mixer(), got)


if __name__ == "__main__":
    unittest.main()
