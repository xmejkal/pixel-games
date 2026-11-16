"""The game box's composition root (P850, stage 0b-2 of the engine plan): the one place that chooses each part's version
and builds the parts. The board runs it at boot. It reads the board's engine_config.py (tools/box.py deploy --engine
writes it, a deploy without --engine removes it), chooses the mixer's sum and the master volume through
engine.accel's Chooser, prints the Chooser's `engine` line before the box's own lines, and hands the knob and the
speaker to app.run. A probe imports it and calls compose() for the same parts: importing it starts nothing.
At boot it first takes the knob's pads, the console's RX and TX, before app's imports of some seconds: until then a
turn of the knob types into the console (P757; the PO's knob turn on the board found it, P850).
--- MVP (P850) ---"""

import sound
import volume
from engine.accel import Chooser
from speaker import Speaker


def read_reference():
    """REFERENCE of the board's engine_config.py: "all", or its part names as a tuple (from a tuple or a list of
    strings), or () when there is no file or no REFERENCE. A file that fails, or any other REFERENCE, prints
    `engine_config refused: <why>` and forces nothing, so the box never stays dark."""
    try:
        import engine_config
    except ImportError:
        return ()
    except Exception as e:  # a syntax error, or one the file raised
        print("engine_config refused:", repr(e))
        return ()
    reference = getattr(engine_config, "REFERENCE", ())
    if reference == "all":
        return reference
    if isinstance(reference, (tuple, list)) and all(isinstance(name, str) for name in reference):
        return tuple(reference)
    print("engine_config refused: REFERENCE = %r" % (reference,))
    return ()


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
    import app

    chooser = chooser or Chooser(read_reference())
    voice_sum, master = choose(chooser)
    print(chooser.line())
    knob = app.open_knob(master)
    return knob, Speaker(voice_sum(), knob.volume if knob else None)


if __name__ == "__main__":
    import encoder
    import pins

    encoder.take_pads(pins.ENC_A, pins.ENC_B)  # first, before app's imports and the knob (P757, P850)
    knob, speaker = compose()
    import app

    app.run(knob=knob, speaker=speaker)
