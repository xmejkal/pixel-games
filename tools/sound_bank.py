#!/usr/bin/env python3
"""
The game box's sound bank (P768), made on the Mac:

    python3 tools/sound_bank.py            # writes games/box_bank.raw and games/box_bank.py
    python3 tools/sound_bank.py --wav DIR  # also one WAV file per sound in DIR, to hear them on the Mac

Each sound is generated here, from a sine sweep and seeded noise, so no sound has a license of another owner.
The bank is 16 kHz mono int16, little-endian. The index gives each sound's first sample and its length.
--- MVP (P768) ---
"""

import math
import os
import random
import struct
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATE = 16000
FADE = 80  # samples of fade in, 5 ms, so a sound does not click


def sweep(ms, hz_from, hz_to, peak, noise=0.0, seed=768):
    """A sine that glides from hz_from to hz_to and dies away, with a share of noise."""
    n, phase, out, rand = RATE * ms // 1000, 0.0, [], random.Random(seed)
    for i in range(n):
        k = i / n
        phase += 2 * math.pi * (hz_from + (hz_to - hz_from) * k) / RATE
        level = min(1.0, i / FADE) * (1 - k) ** 2
        out.append(int(peak * level * ((1 - noise) * math.sin(phase) + noise * rand.uniform(-1, 1))))
    return out


SOUNDS = (
    ("jump", sweep(130, 330, 990, 9000)),
    ("die", sweep(500, 520, 70, 11000, noise=0.35)),
)


def main(argv):
    index, at = [], 0
    with open(os.path.join(ROOT, "games", "box_bank.raw"), "wb") as f:
        for name, samples in SOUNDS:
            f.write(struct.pack("<%dh" % len(samples), *samples))
            index.append('    "%s": (%d, %d),' % (name, at, len(samples)))
            at += len(samples)
    with open(os.path.join(ROOT, "games", "box_bank.py"), "w") as f:
        f.write("# Written by tools/sound_bank.py. Regenerate it; do not edit it.\n"
                "# name: (first sample, samples) in box_bank.raw, 16 kHz mono int16\n"
                "BOX_BANK_INDEX = {\n%s\n}\n" % "\n".join(index))
    if len(argv) == 2 and argv[0] == "--wav":
        for name, samples in SOUNDS:
            with wave.open(os.path.join(argv[1], name + ".wav"), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes(struct.pack("<%dh" % len(samples), *samples))
    print("box_bank.raw: %d sounds, %d samples, %d bytes" % (len(SOUNDS), at, 2 * at))


if __name__ == "__main__":
    main(sys.argv[1:])
