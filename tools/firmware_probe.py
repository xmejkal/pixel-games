"""The firmware probe that tools/box.py deploy runs on the board first (P848, stage 0a of the engine plan): which C
module the firmware has, and which names the games need of it. `mpremote run tools/firmware_probe.py` sends this file
to the board and prints what it prints. It writes nothing on the board. Its answer, one line each:
    _engine <name> yes|no      for each name, when the firmware has _engine (built from pixel-engine 1005249 on)
    _engine ImportError        when it has not
then, in both cases, one more line:
    engine Bodies yes|no       an engine imports: the old C module with Bodies (built before 1005249, or a stale
                               build-engine that registers both names), or a package engine without it
    engine ImportError         no engine
It asks for built-in modules only: sys.path is empty while it imports, so the box's own package folder :engine/ (stage
0b-1, P849) never answers, not even a half-copied one that raises ValueError. Stage 9 of the plan removes it.
--- MVP (P848) ---"""

import sys

NAMES = ("Bodies", "HeatField", "Balls", "SoundBank", "HeatField.cool")  # tools/box.py's FIRMWARE_NAMES


def has(module, name):
    for part in name.split("."):
        if not hasattr(module, part):
            return False
        module = getattr(module, part)
    return True


path = list(sys.path)
sys.path.clear()  # a built-in module only: no folder on the board answers
try:
    try:
        import _engine
    except ImportError:
        print("_engine ImportError")
    else:
        for name in NAMES:
            print("_engine", name, "yes" if has(_engine, name) else "no")
    try:
        import engine
    except ImportError:
        print("engine ImportError")
    else:
        print("engine Bodies", "yes" if hasattr(engine, "Bodies") else "no")
finally:
    sys.path.extend(path)
