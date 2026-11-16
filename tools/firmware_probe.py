"""The firmware probe that tools/box.py deploy runs on the board first (P848, stage 0a of the engine plan): which C
module the firmware has, and which names the games need of it. `mpremote run tools/firmware_probe.py` sends this file
to the board and prints what it prints. It writes nothing on the board. Its answer, one line each:
    _engine <name> yes|no      for each name, when the firmware has _engine (built from pixel-engine 1005249 on)
    _engine ImportError        then one more line:
    engine Bodies yes|no       the firmware's C module still has its old name engine (built before 1005249)
    engine ImportError         no C module: the stock image
Stage 9 of the plan removes it. --- MVP (P848) ---"""

NAMES = ("Bodies", "HeatField", "Balls", "SoundBank", "HeatField.cool")  # tools/box.py's FIRMWARE_NAMES


def has(module, name):
    for part in name.split("."):
        if not hasattr(module, part):
            return False
        module = getattr(module, part)
    return True


try:
    import _engine
except ImportError:
    print("_engine ImportError")
    try:
        import engine
    except ImportError:
        print("engine ImportError")
    else:
        print("engine Bodies", "yes" if hasattr(engine, "Bodies") else "no")
else:
    for name in NAMES:
        print("_engine", name, "yes" if has(_engine, name) else "no")
