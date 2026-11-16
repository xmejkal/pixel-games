"""games/main.py, the composition root (P850, stage 0b-2 of the engine plan), on the Mac: it reads the board's
engine_config.py, chooses each part's version through engine.accel's Chooser, prints the engine line before the box
starts, and builds the knob and the speaker from the chosen classes. Importing it starts nothing. Run from the
repository root: python3 -B -m unittest tests.test_main. --- MVP (P850) ---"""

import contextlib
import io
import os
import runpy
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
GAMES = os.path.join(os.path.dirname(HERE), "games")
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, GAMES)

import app  # noqa: E402
import main  # noqa: E402
import sound  # noqa: E402
import volume  # noqa: E402
from engine import accel  # noqa: E402
from engine.accel import Chooser  # noqa: E402
from sound_viper import ViperVoiceSum  # noqa: E402
from volume_viper import ViperMasterVolume  # noqa: E402


class FakeEncoder:
    pass


@contextlib.contextmanager
def a_board_with_an_encoder():
    """machine.Encoder exists, and Encoder.on_board answers a fake encoder."""
    machine = types.ModuleType("machine")
    machine.Encoder = object
    with mock.patch.dict(sys.modules, {"machine": machine}), \
            mock.patch.object(app.encoder.Encoder, "on_board", classmethod(lambda cls, *a, **k: FakeEncoder())):
        yield


def composed(reference=()):
    """main.compose() with a Chooser of reference, and what it printed."""
    with contextlib.redirect_stdout(io.StringIO()) as said:
        knob, speaker = main.compose(Chooser(reference))
    return knob, speaker, said.getvalue()


@contextlib.contextmanager
def config(source):
    """A board's engine_config.py that holds source."""
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "engine_config.py"), "w") as f:
            f.write(source)
        sys.path.insert(0, tmp)
        sys.modules.pop("engine_config", None)
        try:
            yield
        finally:
            sys.path.remove(tmp)
            sys.modules.pop("engine_config", None)


class NoNative(unittest.TestCase):
    """No _engine and no _crackle.mpy, as on the Mac, whatever another test left in sys.modules."""

    def setUp(self):
        for patch in (mock.patch.dict(sys.modules, {"_engine": None}),
                      mock.patch.object(accel, "CRACKLE", os.path.join(HERE, "fixtures", "no-such-folder", "x"))):
            patch.start()
            self.addCleanup(patch.stop)


class ComposeTest(NoNative):
    def test_the_knob_gets_the_chosen_volume(self):
        with a_board_with_an_encoder():
            knob, speaker, _ = composed()
            self.assertIs(ViperMasterVolume, type(knob.volume))
            self.assertIsInstance(knob.encoder, FakeEncoder)
            knob, speaker, _ = composed(("volume",))
            self.assertIs(volume.MasterVolume, type(knob.volume))

    def test_the_speaker_gets_the_chosen_sum(self):
        knob, speaker, _ = composed()
        self.assertIs(ViperVoiceSum, type(speaker.mixer.sum))
        knob, speaker, _ = composed(("sum",))
        self.assertIs(sound.VoiceSum, type(speaker.mixer.sum))
        self.assertIsNone(speaker.refill)  # nothing opens before open()

    def test_the_speaker_gets_the_knob_s_volume(self):
        with a_board_with_an_encoder():
            knob, speaker, _ = composed()
        self.assertIs(knob.volume, speaker.volume)

    def test_no_encoder_means_no_knob_and_the_mix_as_it_is(self):
        knob, speaker, _ = composed()  # the Mac has no machine module
        self.assertIsNone(knob)
        self.assertIsNone(speaker.volume)

    def test_the_line_says_what_was_chosen(self):
        self.assertEqual("engine sum=viper volume=reference(forced) native=none\n", composed(("volume",))[2])
        self.assertEqual("engine sum=reference(forced) volume=reference(forced) native=none\n", composed("all")[2])

    def test_the_twins_of_the_choose_calls_are_the_classes_the_twin_tests_compare(self):
        self.assertIs(ViperVoiceSum, main.viper_sum())
        self.assertIs(ViperMasterVolume, main.viper_volume())


class ConfigTest(unittest.TestCase):
    def test_no_config_forces_nothing(self):
        with mock.patch.dict(sys.modules, {"engine_config": None}):
            self.assertEqual((), main.read_reference())

    def test_the_config_s_reference_is_read(self):
        with config('REFERENCE = ("volume",)  # tools/box.py deploy --engine\n'):
            self.assertEqual(("volume",), main.read_reference())
        with config('REFERENCE = "all"  # tools/box.py deploy --engine\n'):
            self.assertEqual("all", main.read_reference())

    def test_a_broken_config_is_refused_aloud_and_forces_nothing(self):
        with config("REFERENCE = (\n"), contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual((), main.read_reference())
        self.assertTrue(said.getvalue().startswith("engine_config refused: SyntaxError("), said.getvalue())

    def test_a_config_with_no_reference_forces_nothing(self):
        with config("X = 1\n"):
            self.assertEqual((), main.read_reference())


class BootTest(NoNative):
    def test_importing_main_starts_nothing(self):
        with mock.patch.object(app, "run") as run, contextlib.redirect_stdout(io.StringIO()) as said:
            runpy.run_path(os.path.join(GAMES, "main.py"), run_name="main")
        run.assert_not_called()
        self.assertEqual("", said.getvalue())

    def test_the_engine_line_comes_first_then_the_box_runs_with_the_parts(self):
        said = io.StringIO()
        runs = []

        def run(**parts):
            runs.append((said.getvalue(), parts))

        with mock.patch.object(app, "run", run), mock.patch.dict(sys.modules, {"engine_config": None}), \
                contextlib.redirect_stdout(said):
            runpy.run_path(os.path.join(GAMES, "main.py"), run_name="__main__")
        self.assertEqual(1, len(runs))
        printed, parts = runs[0]
        self.assertEqual("engine sum=viper volume=viper native=none\n", printed)
        self.assertEqual(["knob", "speaker"], sorted(parts))
        self.assertIsNone(parts["knob"])
        self.assertIs(ViperVoiceSum, type(parts["speaker"].mixer.sum))

    def test_the_boot_reads_the_board_s_engine_config(self):
        said = io.StringIO()
        runs = []
        with config('REFERENCE = ("sum", "heat")  # tools/box.py deploy --engine\n'), \
                mock.patch.object(app, "run", lambda **parts: runs.append(parts)), contextlib.redirect_stdout(said):
            runpy.run_path(os.path.join(GAMES, "main.py"), run_name="__main__")
        self.assertEqual("engine sum=reference(forced) volume=viper native=none unused=heat\n", said.getvalue())
        self.assertIs(sound.VoiceSum, type(runs[0]["speaker"].mixer.sum))


if __name__ == "__main__":
    unittest.main()
