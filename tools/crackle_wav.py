"""A WAV of the fire's crackle on the Mac (P747), to hear a CRACKLE_LOOK before the board: about 3.9 pops a second at
random, as Fire's embers come, rendered by the C of engine/core/fx_crackle.c (or --python, games/crackle.py).

    python3 tools/crackle_wav.py out.wav [seconds] [--python]

--- MVP (P747) ---"""

import os
import random
import sys
import wave
from array import array

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "games"))
sys.path.insert(0, os.path.join(ROOT, "engine", "tests"))

from crackle import CRACKLE_LOOK, Crackle  # noqa: E402
from crackle_lib import CCrackle  # noqa: E402

RATE, BLOCK, STEP_MS, EMBERS = 16000, 256, 40, 40  # sound.py's RATE and block, fire.py's STEP_MS and EMBERS


def main(path, seconds=10, python=False):
    crackle = Crackle(747) if python else CCrackle(747, CRACKLE_LOOK)
    rng, out, buf = random.Random(747), array("h"), array("h", bytes(2 * BLOCK))
    step_samples, due = RATE * STEP_MS // 1000, 0
    while len(out) < seconds * RATE:
        while due <= len(out):  # a kernel step: an ember is born in EMBERS of 256 steps
            crackle.add_pops(1 if rng.randrange(256) < EMBERS else 0)
            due += step_samples
        crackle.render(buf)
        out.extend(buf)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(out.tobytes())
    print("%s: %d s, %d pops, peak %d" % (path, seconds, crackle.counts()[1], max(map(abs, out))))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--python"]
    main(args[0], int(args[1]) if len(args) > 1 else 10, "--python" in sys.argv)
