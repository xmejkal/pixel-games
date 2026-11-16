"""The game box's composition root (P850, stage 0b-2 of the engine plan): the one place that chooses each part's version
and builds the parts. The board runs it at boot. It reads the board's engine_config.py (tools/box.py deploy --engine
writes it, a deploy without --engine removes it), chooses the mixer's sum and the master volume through
engine.accel's Chooser, prints the Chooser's `engine` line before the box's own lines, and hands the knob and the
speaker to app.run. A probe imports it and calls compose() for the same parts: importing it starts nothing.
--- MVP (P850) ---"""

import app
import sound
import volume
from engine.accel import Chooser
from speaker import Speaker


def read_reference():
    """REFERENCE of the board's engine_config.py: "all", a tuple of part names, or () when there is no file. A file
    that fails prints `engine_config refused: <why>` and forces nothing, so the box never stays dark."""
    try:
        import engine_config
    except ImportError:
        return ()
    except Exception as e:  # a syntax error, or one the file raised
        print("engine_config refused:", repr(e))
        return ()
    return getattr(engine_config, "REFERENCE", ())


def viper_sum():
    from sound_viper import ViperVoiceSum

    return ViperVoiceSum


def viper_volume():
    from volume_viper import ViperMasterVolume

    return ViperMasterVolume


def choose(chooser):
    """The mixer's sum class and the master volume's class, in this order, each with its twin test
    (tests/test_twins.py)."""
    return (chooser.choose("sum", viper_sum, sound.VoiceSum, "viper"),
            chooser.choose("volume", viper_volume, volume.MasterVolume, "viper"))


def compose(chooser=None):
    """The knob (None when this image has no encoder) and the Speaker, not yet open, built from the chosen classes,
    after the Chooser's line is printed. chooser: the board's, from engine_config, when None."""
    chooser = chooser or Chooser(read_reference())
    voice_sum, master = choose(chooser)
    print(chooser.line())
    knob = app.open_knob(master)
    return knob, Speaker(voice_sum(), knob.volume if knob else None)


if __name__ == "__main__":
    knob, speaker = compose()
    app.run(knob=knob, speaker=speaker)
