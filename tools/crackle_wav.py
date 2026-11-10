"""A WAV of the fire's crackle on the Mac (P747), to hear a look before the board: about 3.9 pops a second at random,
as Fire's embers come. By default GrainCrackle (P751) with the C of engine/core/fx_grains.c and games/fire_bank.raw;
--crackle is the C of engine/core/fx_crackle.c, and --python is games/crackle.py's Crackle. It prints the RMS, the
peak and the share of samples at the clamp.

    python3 tools/crackle_wav.py out.wav [seconds] [--crackle | --python | --fire-sound]

--fire-sound (P753) is FireSound with the real heat field of engine/core/fx_fire.c on Fire's look: a step every 40 ms
with the gusts of FirePlugin, its births as pops with their rises, and its stats for the bed. The bed is off (crackle.BED), so the WAV holds the
pops alone.
--- MVP (P747, P751, P753) ---"""

import ctypes
import os
import random
import subprocess
import sys
import tempfile
import wave
from array import array

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "games"))
sys.path.insert(0, os.path.join(ROOT, "engine", "tests"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tests", "stubs"))  # fire.py imports gfx, which wants framebuf

import fire  # noqa: E402
from crackle import CRACKLE_LOOK, FireSound, GrainCrackle, Crackle  # noqa: E402
from crackle_lib import CCrackle  # noqa: E402
from grains_lib import GrainsModule  # noqa: E402

RATE, BLOCK, STEP_MS, EMBERS = 16000, 256, 40, 40  # sound.py's RATE and block, fire.py's STEP_MS and EMBERS


class Kernel:
    """--- MVP (P753) --- Fire's heat field, the C of fx_fire.c on Fire's look, with FirePlugin's gusts of wind."""

    def __init__(self, rng):
        from test_fire_core import FIRE_C, MAP_H, MAP_W, Field
        lib_path = os.path.join(tempfile.mkdtemp(), "libfire.so")
        s3lcd = os.path.join(ROOT, "engine", "driver", "src")  # blend565.h
        subprocess.run(["clang", "-std=c99", "-O2", "-shared", "-fPIC", "-I", s3lcd, "-o", lib_path, FIRE_C], check=True)
        self.lib, self.rng, self.f = ctypes.CDLL(lib_path), rng, Field()
        self.heat = (ctypes.c_uint8 * (fire.W * fire.H))()
        self.cooling = (ctypes.c_uint8 * (MAP_W * MAP_H))()
        self.lib.fx_fire_init(ctypes.byref(self.f), self.heat, self.cooling, fire.W, fire.H, fire.SEED)
        self.lib.fx_fire_set_look(ctypes.byref(self.f), *fire.Fire.LOOK)
        self.wind, self.target, self.gust = 0, 0, 0

    def step(self, crackle):
        """One step as FirePlugin.late_update does it: the gust, the field, the births, then the stats."""
        self.gust -= STEP_MS
        if self.gust <= 0:
            self.target = self.rng.randrange(-fire.WIND, fire.WIND + 1)
            self.gust = fire.GUST_MS + self.rng.randrange(fire.GUST_MS)
        d = self.target - self.wind
        self.wind += d // 8 if d < 0 else (d + 7) // 8
        self.lib.fx_fire_step(ctypes.byref(self.f), 1, self.wind)
        rises = array("b", bytes(8))
        n = self.lib.fx_fire_take_births(ctypes.byref(self.f), ctypes.c_void_p(rises.buffer_info()[0]), 8)
        crackle.add_pops(n, rises)
        if hasattr(crackle, "follow_field"):
            total, height = ctypes.c_int32(), ctypes.c_int32()
            self.lib.fx_fire_stats(ctypes.byref(self.f), 48, ctypes.byref(total), ctypes.byref(height))
            crackle.follow_field(total.value, height.value, self.wind)


def main(path, seconds=10, voice="grains"):
    bank = os.path.join(ROOT, "games", "fire_bank.raw")
    rng, out, buf = random.Random(747), array("h"), array("h", bytes(2 * BLOCK))
    crackle = {"python": lambda: Crackle(747), "crackle": lambda: CCrackle(747, CRACKLE_LOOK),
               "grains": lambda: GrainCrackle(747, bank_path=bank, native=GrainsModule()),
               "fire-sound": lambda: FireSound(747, bank_path=bank, native=GrainsModule(), stats=True)}[voice]()
    kernel = Kernel(rng) if voice == "fire-sound" else None
    step_samples, due = RATE * STEP_MS // 1000, 0
    while len(out) < seconds * RATE:
        while due <= len(out):  # a kernel step
            if kernel:
                kernel.step(crackle)
            else:  # an ember is born in EMBERS of 256 steps
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
         "python" if "--python" in sys.argv else "crackle" if "--crackle" in sys.argv else
         "fire-sound" if "--fire-sound" in sys.argv else "grains")
