#!/usr/bin/env python3
"""
The game box's sound bank (P768), made on the Mac:

    python3 tools/sound_bank.py            # writes games/box_bank.raw and games/box_bank.py
    python3 tools/sound_bank.py --wav DIR  # also one WAV file per sound in DIR, to hear them on the Mac

Each sound is generated here, from soft sine notes, so no sound has a license of another owner.
The bank is 16 kHz mono int16, little-endian. The index gives each sound's first sample and its length.
--- MVP (P768) ---
"""

import math
import os
import struct
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATE = 16000
ATTACK = 160  # samples of a smooth rise, 10 ms, so a sound starts soft and does not click


def note(ms, hz_from, hz_to, peak):
    """A soft sine note: it glides from hz_from to hz_to, rises smoothly, and fades to nothing at its end."""
    n, phase, out = RATE * ms // 1000, 0.0, []
    for i in range(n):
        k = i / n
        phase += 2 * math.pi * (hz_from + (hz_to - hz_from) * k) / RATE
        rise = 0.5 - 0.5 * math.cos(math.pi * min(1.0, i / ATTACK))
        out.append(int(peak * rise * (1 - k) ** 2 * math.sin(phase)))
    return out


# The PO, 2026-11-11: "the sounds should be nice and not aggressive". So: pure sines, no noise, low peaks (of 32767).
SOUNDS = (
    ("jump", note(120, 440, 660, 3000)),  # a small rising "boop"
    ("die", note(140, 659, 659, 3200) + note(140, 523, 523, 3200) + note(320, 392, 370, 3200)),  # three notes down
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
