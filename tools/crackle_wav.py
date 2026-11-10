"""A WAV of the fire's crackle on the Mac (P747), to hear a look before the board: about 3.9 pops a second at random,
as Fire's embers come. By default GrainCrackle (P751) with the C of engine/core/fx_grains.c and games/fire_bank.raw;
--crackle is the C of engine/core/fx_crackle.c, and --python is games/crackle.py's Crackle. It prints the RMS, the
peak and the share of samples at the clamp.

    python3 tools/crackle_wav.py out.wav [seconds] [--crackle | --python]

--- MVP (P747, P751) ---"""

import os
import random
import sys
import wave
from array import array

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "games"))
sys.path.insert(0, os.path.join(ROOT, "engine", "tests"))

from crackle import CRACKLE_LOOK, GrainCrackle, Crackle  # noqa: E402
from crackle_lib import CCrackle  # noqa: E402
from grains_lib import GrainsModule  # noqa: E402

RATE, BLOCK, STEP_MS, EMBERS = 16000, 256, 40, 40  # sound.py's RATE and block, fire.py's STEP_MS and EMBERS


def main(path, seconds=10, voice="grains"):
    crackle = {"python": lambda: Crackle(747), "crackle": lambda: CCrackle(747, CRACKLE_LOOK),
               "grains": lambda: GrainCrackle(747, bank_path=os.path.join(ROOT, "games", "fire_bank.raw"),
                                              native=GrainsModule())}[voice]()
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
    rms = (sum(v * v for v in out) / len(out)) ** 0.5
    clamp = sum(abs(v) >= 32767 for v in out) / len(out)
    print("%s: %d s, %d pops, rms %.0f, peak %d, clamp %.4f %%" % (
        path, seconds, crackle.counts()[1], rms, max(map(abs, out)), 100 * clamp))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0], int(args[1]) if len(args) > 1 else 10,
         "python" if "--python" in sys.argv else "crackle" if "--crackle" in sys.argv else "grains")
