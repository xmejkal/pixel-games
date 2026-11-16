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


def stand_in_pads(a, b):
    """encoder.take_pads on the Mac, which has no machine.Pin: the boot takes the pads first (P850)."""
    return a, b


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

    def test_the_line_is_printed_before_the_knob_opens(self):
        """The engine line comes first even when the encoder fails: an error from Encoder.on_board stops the boot."""
        said = io.StringIO()
        with mock.patch.object(app, "open_knob", side_effect=OSError("no counter unit")), \
                contextlib.redirect_stdout(said), self.assertRaises(OSError):
            main.compose(Chooser())
        self.assertEqual("engine sum=viper volume=viper native=none\n", said.getvalue())

    def test_the_twins_of_the_choose_calls_are_the_classes_the_twin_tests_compare(self):
        self.assertIs(ViperVoiceSum, main.viper_sum())
        self.assertIs(ViperMasterVolume, main.viper_volume())


class Saved:
    """A VolumeStore that holds step (None: no file on the board) and refuses a save: the box reads it, never writes."""

    def __init__(self, step):
        self.step = step

    def load(self):
        return self.step

    def save(self, step):
        raise AssertionError("the box saves no step (a save stalls the loop, bench.md P764)")


class StartVolumeTest(NoNative):
    """The box starts at the step `box.py volume N` wrote to :volume.txt (P866), read once at boot and never saved."""

    def start(self, step, encoder=True):
        with contextlib.ExitStack() as stack:
            if encoder:
                stack.enter_context(a_board_with_an_encoder())
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            return main.compose(Chooser(), store=Saved(step))

    def test_a_saved_step_is_the_knob_s_start(self):
        for step in (0, 3, volume.STEPS):
            with self.subTest(step=step):
                knob, speaker = self.start(step)
                self.assertEqual(step, knob.volume.step)
                self.assertIs(knob.volume, speaker.volume)

    def test_no_saved_step_starts_at_the_default(self):
        knob, speaker = self.start(None)
        self.assertEqual(volume.DEFAULT_STEP, knob.volume.step)

    def test_the_knob_saves_nothing(self):
        knob, speaker = self.start(0)
        self.assertIsNone(knob.store)

    def test_a_box_with_no_encoder_still_starts_silent(self):
        knob, speaker = self.start(0, encoder=False)
        self.assertIsNone(knob)
        self.assertEqual(0, speaker.volume.step)


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

    def test_a_list_of_names_is_read_as_a_tuple(self):
        with config('REFERENCE = ["volume"]\n'):
            self.assertEqual(("volume",), main.read_reference())

    def test_a_malformed_reference_is_refused_aloud_and_the_box_boots(self):
        for value in ("None", "5", "[1]", '("sum", 3)', '"volume"', "{'sum'}"):
            with self.subTest(value), config("REFERENCE = %s\n" % value), \
                    contextlib.redirect_stdout(io.StringIO()) as said:
                self.assertEqual((), main.read_reference())
                self.assertEqual("engine_config refused: REFERENCE = %r\n" % (eval(value),), said.getvalue())
                knob, speaker = main.compose()  # the box boots with every fast version
                self.assertIs(ViperVoiceSum, type(speaker.mixer.sum))

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
                mock.patch.object(app.encoder, "take_pads", stand_in_pads), contextlib.redirect_stdout(said):
            runpy.run_path(os.path.join(GAMES, "main.py"), run_name="__main__")
        self.assertEqual(1, len(runs))
        printed, parts = runs[0]
        self.assertEqual("engine sum=viper volume=viper native=none\n", printed)
        self.assertEqual(["knob", "speaker"], sorted(parts))
        self.assertIsNone(parts["knob"])
        self.assertIs(ViperVoiceSum, type(parts["speaker"].mixer.sum))

    def test_the_boot_takes_the_knob_s_pads_before_anything_else(self):
        """The knob's pads are the console's RX and TX: until they are taken, a turn types into the console (P757).
        The PO's turn on the board found it (P850): the boot takes them before app's imports and the knob."""
        said, events = io.StringIO(), []

        class Counter:
            def __init__(self, *args, **kw):
                events.append("Encoder")

        machine = types.ModuleType("machine")
        machine.Encoder = Counter
        with mock.patch.dict(sys.modules, {"machine": machine, "engine_config": None, "app": None}), \
                mock.patch.object(app.encoder, "take_pads",
                                  lambda a, b: events.append(("take_pads", a, b, said.getvalue())) or (a, b)), \
                contextlib.redirect_stdout(said):
            del sys.modules["app"]  # main imports app after the pads are taken
            real_import = __import__

            def importing(name, *args, **kw):
                if name == "app" and "app" not in sys.modules:
                    events.append("import app")
                    sys.modules["app"] = app
                return real_import(name, *args, **kw)

            with mock.patch("builtins.__import__", importing), \
                    mock.patch.object(app, "run", lambda **parts: events.append("run")):
                runpy.run_path(os.path.join(GAMES, "main.py"), run_name="__main__")
        pads = ("take_pads", app.pins.ENC_A, app.pins.ENC_B, "")
        self.assertEqual([pads, "import app", pads[:3] + (said.getvalue(),), "Encoder", "run"], events)

    def test_the_boot_reads_the_board_s_engine_config(self):
        said = io.StringIO()
        runs = []
        with config('REFERENCE = ("sum", "heat")  # tools/box.py deploy --engine\n'), \
                mock.patch.object(app, "run", lambda **parts: runs.append(parts)), \
                mock.patch.object(app.encoder, "take_pads", stand_in_pads), contextlib.redirect_stdout(said):
            runpy.run_path(os.path.join(GAMES, "main.py"), run_name="__main__")
        self.assertEqual("engine sum=reference(forced) volume=viper native=none unused=heat\n", said.getvalue())
        self.assertIs(sound.VoiceSum, type(runs[0]["speaker"].mixer.sum))


if __name__ == "__main__":
    unittest.main()
