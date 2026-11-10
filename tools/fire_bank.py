"""The fire's sample bank on the Mac (P751): a bed texture and 12 pops, rendered once with the float code of P750 round 2
demo g (pixel-sound docs/discovery/2026-11-09-sound/p750/round2/gen.py), then mixed in C by engine/core/fx_grains.c.

    python3 tools/fire_bank.py [recording.wav]   # 16 kHz mono; default: games/fire16k.wav, the CC0 recording

It writes games/fire_bank.raw (int16, little endian: the bed, then the pops) and games/fire_bank.py (the index).
The recording is "Fire Crackling" by AntumDeluge (CC0), see games/fire16k.SOURCE.txt. Pure Python, under a second.

After the PO's ear on the demos ("a stream of water"): the small crackles are sparse, short and noisy, the pops
crack with a sharp click and a low Q, and a low flame roar (60 to 200 Hz) lies under the grains.
--- MVP (P751) ---"""

import math
import os
import random
import sys
import wave
from array import array

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 16000
BED_S = 6
POP_MAX = 2400  # 150 ms
SIZES = (0.15, 0.5, 0.9)  # the three pop sizes, as ember rise speeds q
POPS_PER_SIZE = 3  # woody pops of each size, and one recording grain
POP_PEAKS = tuple(int(3000 + 19000 * q * q) for q in SIZES)
BED_RMS = 3800
LIMIT = 0.9 * 32767


def lp(hz):
    return 1 - math.exp(-2 * math.pi * hz / SR)


def slow(seed, hz, n):  # slow random signal, unit std after 2 poles, mean 0
    r = random.Random(seed)
    a = b = 0.0
    c = lp(hz)
    out = []
    for _ in range(n):
        a += (r.uniform(-1, 1) - a) * c
        b += (a - b) * c
        out.append(b)
    s = math.sqrt(sum(v * v for v in out) / n)
    return [v / s for v in out]


def resonate(out, t0, fc, q, amp, dur, rg, modes=1, click=0):
    """An impulse into a 2-pole band-pass with a square-law length (Farnell); modes > 1 adds inharmonic partials
    (woody); click samples of broadband noise lead the first mode, a sharp attack."""
    for m in range(modes):
        f = fc * (1.0 if m == 0 else rg.uniform(1.6, 2.9))
        g = amp * (1.0 if m == 0 else 0.5)
        th = 2 * math.pi * f / SR
        rr = math.exp(-math.pi * f / q / SR)
        c1, c2, y1, y2, n = 2 * rr * math.cos(th), rr * rr, 0.0, 0.0, int(dur * SR)
        for k in range(n):
            x = g * (rg.uniform(-1, 1) if k < 8 else 0.0)  # short noise burst as the fracture
            y = x + c1 * y1 - c2 * y2
            y2, y1 = y1, y
            e = 1 - k / n
            if t0 + k < len(out):
                out[t0 + k] += y * e * e
    for k in range(click):  # the broadband attack, before the resonance builds
        if t0 + k < len(out):
            out[t0 + k] += amp * 0.6 * rg.uniform(-1, 1) * (1 - k / click)


def crackles(n):
    """e's small crackles, sparse (3 to 15 a second), in clusters, noisy (Q 2 to 5) and 1 to 5 ms long."""
    rg, o = random.Random(5), [0.0] * (n + 4000)
    m = slow(31, 0.8, n)
    for i in range(n):
        rate = 3 + 12 * min(1.0, max(0.0, 0.4 + 0.9 * m[i])) ** 2  # a second
        if rg.random() < rate / SR:
            t = i
            for _ in range(1 + (rg.random() < 0.35) * rg.randrange(1, 4)):
                u = rg.random()
                fc = math.exp(rg.uniform(math.log(500), math.log(4500)))
                resonate(o, t, fc, rg.uniform(2, 5), 900 * u ** 3 + 60, rg.uniform(0.001, 0.005), rg, click=6)
                t += int(rg.uniform(0.004, 0.04) * SR)
    return o[:n]


def body(n):
    """The flame's low body: a noise roar near 60 to 200 Hz, 3 poles, that flutters slowly (Farnell's lapping), and a
    thin sizzle of tiny ticks. Quieter than the crackles."""
    rg, nm = random.Random(7), random.Random(8)
    m = slow(41, 0.7, n)
    roar, a1, a2, a3, m1, m2, hgt = [], 0.0, 0.0, 0.0, 0.0, 0.0, slow(9, 0.3, n)
    for i in range(n):
        c = lp(130 + 70 * max(-1.0, min(1.0, hgt[i])))  # 60 to 200 Hz
        x = rg.uniform(-1, 1)
        a1 += (x - a1) * c
        a2 += (a1 - a2) * c
        a3 += (a2 - a3) * c
        m1 += (nm.uniform(-1, 1) - m1) * lp(6)
        m2 += (m1 - m2) * lp(6)
        flut = max(0.0, 0.5 + 6.0 * m2) ** 2  # the flutter, 0 to about 6 Hz
        roar.append(a3 * (0.35 + 0.65 * min(1.0, flut)))
    s = math.sqrt(sum(v * v for v in roar) / n)
    sz = [0.0] * (n + 4)
    for i in range(n):
        if rg.random() < (1500 / SR) * (0.3 + 0.7 * max(0.0, 0.5 + 0.8 * m[i])):
            v = rg.random() ** 4 * 700
            sz[i] += v
            sz[i + 1] -= v * 0.6
    v, tick = 0.0, []
    for i in range(n):
        v += (sz[i] - v) * 0.55
        tick.append(sz[i] - v * 0.5)
    return [roar[i] / s * 700 + tick[i] * 0.15 for i in range(n)]


def load(path):
    w = wave.open(path)
    a = array("h")
    a.frombytes(w.readframes(w.getnframes()))
    return [v / 32768 for v in a]


def onsets(x, win=48):  # energy per 3 ms; an onset where it jumps 6x over the mean of the 20 ms before
    e = [sum(v * v for v in x[i:i + win]) / win for i in range(0, len(x) - win, win)]
    floor = sorted(e)[len(e) // 2] * 4 + 1e-9
    found, last = [], -99
    for k in range(7, len(e)):
        if e[k] > 6 * (sum(e[k - 7:k - 1]) / 6 + 1e-9) and e[k] > floor and k - last > 12:
            found.append(k * win)
            last = k
    return found


def grain_bed(src, free, n):
    """The recording's grains where no loud onset is: 50 to 300 ms, a Hann window, half overlap."""
    rg, o, t = random.Random(3), [0.0] * (n + SR), 0
    while t < n:
        length = int(rg.uniform(0.05, 0.3) * SR)
        for _ in range(30):
            p = rg.randrange(0, len(src) - length)
            if all(free[p:p + length:40]):
                break
        sp, gain = rg.uniform(0.85, 1.15), rg.uniform(0.6, 1.0)
        for k in range(length):
            j = p + k * sp
            ji = int(j)
            if ji + 1 >= len(src):
                break
            w = 0.5 - 0.5 * math.cos(2 * math.pi * k / (length - 1))
            o[t + k] += (src[ji] * (1 - (j - ji)) + src[ji + 1] * (j - ji)) * w * gain
        t += length // 2
    return o[:n]


def limited(x, rms):
    """x at this RMS, tanh-limited to 90 % of full scale, as gen.py's write()."""
    g = rms / math.sqrt(sum(v * v for v in x) / len(x))
    y = [LIMIT * math.tanh(v * g / LIMIT) for v in x]
    for _ in range(8):
        g *= rms / math.sqrt(sum(v * v for v in y) / len(y))
        y = [LIMIT * math.tanh(v * g / LIMIT) for v in x]
    return [int(v) for v in y]


def pop(q, rg):
    """One woody pop: a sharp click, 3 modes at a low Q, then 2 to 6 small after-crackles; under POP_MAX samples."""
    o = [0.0] * POP_MAX
    fc = 700 + 1800 * (1 - q) + rg.uniform(-150, 150)  # bigger: lower, woodier
    resonate(o, 0, fc, 2 + 3 * q, 9000, 0.012 + 0.03 * q, rg, modes=3, click=rg.randrange(8, 17))  # 0.5 to 1 ms
    for _ in range(int(2 + 4 * q)):
        resonate(o, int(rg.uniform(0.01, 0.12) * SR), rg.uniform(900, 3500), 3, rg.uniform(300, 1500), 0.004, rg,
                 modes=2, click=4)
    return o


def main(path):
    src = load(path)
    ons = onsets(src)
    free = [True] * len(src)
    for t in ons:
        for k in range(max(0, t - 200), min(len(src), t + int(0.2 * SR))):
            free[k] = False
    n = BED_S * SR
    grains = grain_bed(src, free, n)
    cr = crackles(n)
    base = body(n)
    bed = limited([grains[i] * 3000 * 0.8 + cr[i] * 0.9 + base[i] for i in range(n)], BED_RMS)
    # the recording's own crackle grains, sorted by strength, one per size
    grain_pops = []
    for t in ons:
        g = src[max(0, t - 40):t + int(0.12 * SR)]
        g = [g[k] * (1.0 if k < 80 else math.exp(-(k - 80) / (0.05 * SR))) for k in range(len(g))]
        grain_pops.append((max(abs(v) for v in g), g))
    grain_pops.sort(key=lambda p: p[0])
    rg, pops = random.Random(11), []  # (samples, size)
    for size, q in enumerate(SIZES):
        for _ in range(POPS_PER_SIZE):
            pops.append((pop(q, rg), size))
        pops.append((grain_pops[int(q * (len(grain_pops) - 0.01))][1][:POP_MAX], size))
    bank, index, off = array("h", bed), [n], n
    for samples, size in pops:
        peak = max(abs(v) for v in samples)
        scaled = [int(v * POP_PEAKS[size] / peak) for v in samples]
        bank.extend(scaled)
        index += [off, len(scaled), size]
        off += len(scaled)
    bank_path = os.path.join(ROOT, "games", "fire_bank.raw")
    with open(bank_path, "wb") as f:
        f.write(bank.tobytes())
    with open(os.path.join(ROOT, "games", "fire_bank.py"), "w") as f:
        f.write('"""The index of fire_bank.raw (P751), written by tools/fire_bank.py: the bed\'s length, then each pop\'s\n'
                'offset, length and size (0 small to 2 big), all in samples. --- MVP (P751) ---"""\n\n')
        f.write("FIRE_BANK_INDEX = (%d,\n" % n)
        for k in range(0, len(index) - 1, 3):
            f.write("    %d, %d, %d,\n" % tuple(index[1 + k:4 + k]))
        f.write(")\n")
    print("%d onsets, bed %d samples, %d pops, bank %d samples = %.1f KB" % (len(ons), n, len(pops), len(bank),
                                                                           len(bank) * 2 / 1024))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "games", "fire16k.wav"))
