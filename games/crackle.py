"""The fire's crackle (P747): a soft roar and one pop per ember, so the pops come with the sparks on screen.

All the classes meet the Mixer contract of sound.py (render(buf), pending), so a Refill driver feeds any of them to
the I2S. add_pops(n) queues n pops, and the next render starts them. counts() gives (popped, started, dropped).

- Crackle is plain Python and the reference. It takes 21 ms for 16 ms of sound on the board (run145b), so on the board
  it only renders SampledCrackle's pops.
- NativeCrackle runs the same integer math in C, engine/core/fx_crackle.c, loaded from crackle_c.mpy with no firmware
  rebuild: 0.4 ms a block. A Mac test wants it equal to Crackle sample for sample, so a change to one is a change to
  both, by fx_crackle.h's rules: every value under 2^30, signed values shift only with >>, no / or %.
- GrainCrackle (P751) is the fire of P750's demo g: a low flame roar (the bed, played in grains) and one bank pop per
  ember, mixed in C by engine/core/fx_grains.c from the same crackle_c.mpy, out of a sample bank (fire_bank.raw, made
  on the Mac by tools/fire_bank.py). No filter, so nothing rings or overflows.
- FireSound (P753) is GrainCrackle's pops plus smooth noise in integer C, engine/core/fx_noise.c, in the same
  crackle_c.mpy. follow_bodies sets one whoosh per falling burning body from its airspeed (BurningBodies). The bed
  of noise, set by follow_field from HeatField.stats, is off (BED = False): the PO heard it as wind. So on Fire,
  FireSound plays the pops alone, with no grain bed either. On a firmware with no stats it is a GrainCrackle.
- SampledCrackle is the naive path on the board, which stays working (D26, the PO chose it on 2026-11-10): Crackle
  renders a few pops once, and a sound.Mixer plays one per frame that has births. No roar, no overlap.

The pop queue has two counters with one writer each: add_pops only adds to popped, render only adds to started and
dropped. A refill callback between two bytecodes of add_pops so loses no pop and plays none twice.
"""

import math
from array import array

# --- MVP (P747) ---
# roar_shift, roar_gain, pop_min, pop_max, decay_min, decay_max, tails, tail_gap, gain: see fx_crackle_init in
# fx_crackle.h
CRACKLE_LOOK = (6, 24, 6000, 12000, 28400, 31600, 3, 4000, 224)  # the PO chose the deep roar, try B (run145d)
SAMPLED_LOOK = (6, 0, 6000, 12000, 28400, 31600, 1, 1600, 224)  # no roar, one click after the burst
SAMPLED_POPS = 4
SAMPLED_SAMPLES = 2560  # 160 ms: by the look's ranges, a pop and its click end by about sample 2200
SLOTS = 8  # FX_CRACKLE_SLOTS
PEAK = 32767  # FX_CRACKLE_PEAK

# --- MVP (P751) ---
# bed_gain, pop_gain: see fx_grains_init in fx_grains.h, Q15 (32768 is the bank as it is)
GRAIN_LOOK = (32768, 32768)
BANK_FILE = "fire_bank.raw"


def check_look(look):
    """fx_crackle_init's ranges, which keep the C defined and every Python value under 2^30. ValueError if not."""
    roar_shift, roar_gain, pop_min, pop_max, decay_min, decay_max, tails, tail_gap, gain = look
    if not (1 <= roar_shift <= 8 and 0 <= roar_gain <= 255 and 0 <= pop_min <= pop_max < 16384
            and 0 <= decay_min <= decay_max < 32768 and decay_max - decay_min < 16384 and 0 <= tails <= 3
            and 0 <= tail_gap < 16384 and 0 <= gain <= 1023):
        raise ValueError("a look out of fx_crackle_init's ranges: %r" % (look,))


class Crackle:
    """The crackle in plain Python, step for step fx_crackle.c. A crackle has no play, so pending stays None."""

    pending = None

    def __init__(self, seed, look=CRACKLE_LOOK):
        check_look(look)
        self.rng = (seed & 0xFFFF) or 1
        self.roar1 = self.roar2 = 0
        (self.roar_shift, self.roar_gain, self.pop_min, self.pop_max, self.decay_min, self.decay_max, self.tails,
         self.tail_gap, self.gain) = look
        self.popped = self.started = self.dropped = 0
        self.wait, self.armed, self.env = [0] * SLOTS, [0] * SLOTS, [0] * SLOTS
        self.decay, self.lp, self.shift, self.tails_left = [0] * SLOTS, [0] * SLOTS, [0] * SLOTS, [0] * SLOTS

    def draw(self):
        """xorshift16 (shifts 7, 9, 8): 1 to 65535."""
        x = self.rng
        x ^= (x << 7) & 0xFFFF
        x ^= x >> 9
        x ^= (x << 8) & 0xFFFF
        self.rng = x
        return x

    def between(self, lo, hi):
        return lo + ((self.draw() * (hi - lo)) >> 16)

    def add_pops(self, n):
        self.popped += n

    def counts(self):
        return self.popped, self.started, self.dropped

    def start_pops(self):
        while self.started + self.dropped < self.popped:
            i = 0
            while i < SLOTS and (self.wait[i] or self.env[i]):
                i += 1
            if i == SLOTS:
                self.dropped += 1
                continue
            self.armed[i] = self.between(self.pop_min, self.pop_max)
            self.decay[i] = self.between(self.decay_min, self.decay_max)
            self.shift[i] = self.between(1, 4)
            self.tails_left[i] = self.between(0, self.tails + 1)
            self.wait[i] = 1 + (self.draw() & 127)
            self.lp[i] = 0
            self.started += 1

    def render(self, buf):
        self.start_pops()
        wait, armed, env, decay, lp, shift, tails_left = (self.wait, self.armed, self.env, self.decay, self.lp,
                                                          self.shift, self.tails_left)
        roar_shift, roar_gain = self.roar_shift, self.roar_gain
        for k in range(len(buf)):
            noise = self.draw() - 32768
            self.roar1 += (noise - self.roar1) >> roar_shift
            self.roar2 += (self.roar1 - self.roar2) >> roar_shift
            total = (self.roar2 * roar_gain) >> 8
            for i in range(SLOTS):
                if wait[i]:
                    wait[i] -= 1
                    if wait[i] == 0:
                        env[i] = armed[i]
                    continue
                if env[i] == 0:
                    continue
                lp[i] += (noise - lp[i]) >> shift[i]
                total += (lp[i] * env[i]) >> 15
                env[i] = (env[i] * decay[i]) >> 15
                if env[i] < 8:
                    env[i] = 0
                    if tails_left[i]:
                        tails_left[i] -= 1
                        armed[i] >>= 1
                        wait[i] = 32 + self.between(0, self.tail_gap)
            total = (total * self.gain) >> 6
            buf[k] = PEAK if total > PEAK else -PEAK if total < -PEAK else total


class NativeCrackle:
    """The same crackle in C: crackle_c.mpy, built by engine/natmod/crackle. Its state is a bytearray, which the heap
    aligns to 16 bytes, so the C reads its int32 fields aligned. ImportError when crackle_c.mpy is not on the board."""

    pending = None

    def __init__(self, seed, look=CRACKLE_LOOK):
        import crackle_c
        check_look(look)
        self.c = crackle_c
        self.state = bytearray(crackle_c.SIZE)
        crackle_c.init(self.state, seed, *look)

    def add_pops(self, n):
        self.c.add_pops(self.state, n)

    def render(self, buf):
        self.c.render(self.state, buf)

    def counts(self):
        return self.c.counts(self.state)


def check_grain_look(look):
    """fx_grains_init's look ranges. ValueError if not."""
    if not (len(look) == 2 and all(0 <= v <= 32768 for v in look)):
        raise ValueError("a look out of fx_grains_init's ranges: %r" % (look,))


def ticks():
    """Milliseconds from a clock: MicroPython's on the board, the Mac's otherwise."""
    import time
    return time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.monotonic() * 1000)


class GrainCrackle:
    """The grains in C: crackle_c.mpy's grains_ functions. The bank is read once into a bytearray (print: its load
    time), and the state is a bytearray too, so the C keeps no pointer. native is the module, crackle_c on the board
    and a Mac stand-in in tests (engine/tests/grains_lib.py). ImportError when crackle_c.mpy is not on the board.
    render and counts are NativeCrackle's. --- MVP (P751) --- The bank lives in an engine.SoundBank, outside the GC
    heap, which a collection would otherwise walk for 7.6 ms; a firmware without one, and the Mac, get a bytearray.
    takes_rises tells FirePlugin that add_pops takes the births' rises."""

    pending = None
    takes_rises = True

    def __init__(self, seed, look=GRAIN_LOOK, bank_path=BANK_FILE, native=None, engine=None):
        import os
        from fire_bank import FIRE_BANK_INDEX

        if native is None:
            import crackle_c as native
        if engine is None:
            try:
                import engine
            except ImportError:
                pass
        check_grain_look(look)
        t = ticks()
        nbytes = os.stat(bank_path)[6]
        self.bank = None
        if hasattr(engine, "SoundBank"):
            try:
                self.bank = engine.SoundBank(nbytes)  # outside the GC heap: a bytearray made each collection 7.6 ms
            except MemoryError:
                pass  # no PSRAM: the heap's bytearray, slower collections
        if self.bank is None:
            self.bank = bytearray(nbytes)
        with open(bank_path, "rb") as f:
            if f.readinto(self.bank) != nbytes:
                raise OSError("a short read of " + bank_path)
        print("bank load %d ms, %d bytes, %s" % (ticks() - t, nbytes, getattr(self.bank, "where", "heap")))
        self.c = native
        self.state = bytearray(native.GRAINS_SIZE)
        native.grains_init(self.state, seed, array("i", look), array("i", FIRE_BANK_INDEX))

    def add_pops(self, n, rises=None):
        """rises: an array("b") of the births' ember rises (2 to 5), or None."""
        if rises is None:
            self.c.grains_add_pops(self.state, n)
        else:
            self.c.grains_add_pops(self.state, n, rises)

    def render(self, buf):
        self.c.grains_render(self.state, self.bank, buf)

    def counts(self):
        return self.c.grains_counts(self.state)


# --- Later, not MVP: the bed's constants and follow_field work and are tested, but BED is off (see BED below) ---
# FireSound's bed constants, from engine/core/fx_noise.h and the Mac twin of step 0 (a scratch script that ran the real
# fx_fire.c on Fire's look and on BurningBodies' look, 5,000 steps each, stats at threshold 48):
# Fire: total 554,000 to 829,000 (5 % to 95 %: 598,000 to 776,000), height 71 to 120 rows (median 103, often the full
# 120), height's step change 1 row at the median, 6 at the 95th percentile, 34 at most. 23 % of the power of that change
# is at 1 to 5 Hz (25 steps a second), 74 % above 5 Hz. BurningBodies: total 0 to 118,000 (95 %: 67,000), height 0 to
# 120, change 24 to 31 rows at the 95th percentile, 34 % of the power at 1 to 5 Hz.
TOTAL_FULL = 800000  # a total at or over this is the loudest bed: Fire sits at 0.7 to 1.0 of it, bodies at 0 to 0.15
HEIGHT_LOW, HEIGHT_HIGH = 60, 120  # rows: a flame this low has the brightest bed, this tall the darkest
STEPS = 64  # the cutoff and gain tables
CUTOFF_DARK, CUTOFF_BRIGHT = 250, 900  # Hz of the bed's two low-passes
BED_BASE = 6800  # the level of a bed of TOTAL_FULL at the darkest cutoff: rms 0.36 of it, peaks 1.5 of it (fx_noise.h)
FLUTTER, FLUTTER_CAP = 100, 8  # level per row of height's change since the last step, up to 8 rows: at most 800
WIND_LEVEL, WIND_CAP = 6, 60  # level per unit of |wind|, up to Fire's WIND of 60: at most 360
BED_MAX = 8000  # the bed's level at most: 6800 + 800 + 360 stay under it
SAMPLE_RATE = 16000
# --- MVP (P753) ---
# The whooshes (P753): a body's airspeed s is its speed against the air, in px/s. Bodies fall at up to about 1,400 px/s
# (burning.py's FLARE numbers) and drift at most 120 px/s. All integer math in follow_bodies, tables made once.
VOICES = 8  # whoosh voices, one per body index (FX_NOISE_VOICES)
WIND_AIR = 5  # px/s of airspeed per unit of wind: wind 60 gives 300 px/s, a sound-only number
S2_FLOOR = 100 * 100  # s^2 under this (100 px/s) is silent
S2_FULL = 2000000  # s^2 at or over this (1,414 px/s) is the loudest whoosh
WHOOSH_MAX = 3000  # one voice's level at most: 8 voices stay under 24000 of the 32768 (the bed has 8000 of its own)
CENTRE_LOW, CENTRE_HIGH = 300, 2000  # Hz of the band-pass: s = 0 gets the low one, S2_FULL the high one
S2_SHIFT = 10  # the centre table has one coefficient per 1024 of s^2, so the square root costs no code
V_CAP = 2047  # px/s: a speed component is cut here, so every square stays under 2^23
# --- Later, not MVP: the bed works and is tested, but the PO heard every noise bed as wind on the board's speaker
# (run147, 2026-11-10: "sounds like a lot of wind in the background", and a quiet bed that flaps: "Still wind"). So
# Fire plays the pops alone. Kept for a wind sound that follows the gusts, or a bed the PO likes later. ---
BED = False


class FireSound(GrainCrackle):
    """GrainCrackle's pops and a bed of filtered noise that follows the heat field (P753). follow_field(total, height,
    wind) sets targets in ints and C glides to them over 32 ms: the level follows the total (a darker bed is not
    quieter, a table of sqrt(CUTOFF_DARK / cutoff) keeps the loudness), plus a flutter from the change of height and a
    little from |wind|, and the cutoff goes from CUTOFF_BRIGHT to CUTOFF_DARK as the flame grows taller. The tables are
    made once here, the integer math is in follow_field. With a HeatField that has stats, the grain bed is off (look
    (0, pop_gain)). With an older one, FireSound is a GrainCrackle and follow_field does nothing. stats=None asks the
    engine; a test passes True or False. bed=False (BED, the default) keeps the noise bed off, so Fire plays the pops
    alone."""

    def __init__(self, seed, look=GRAIN_LOOK, bank_path=BANK_FILE, native=None, engine=None, stats=None, bed=BED):
        if native is None:
            import crackle_c as native
        if stats is None:
            if engine is None:
                try:
                    import engine
                except ImportError:
                    pass
            stats = hasattr(getattr(engine, "HeatField", None), "stats")
        self.has_bed = stats and bed  # BED off: the pops alone, with no grain bed and no noise bed
        super().__init__(seed, (0, look[1]) if stats else look, bank_path, native, engine)
        self.noise = bytearray(native.NOISE_SIZE)
        native.noise_init(self.noise, seed)
        self.coefs, self.gains = array("H"), array("H")
        for ci in range(STEPS):
            cutoff = CUTOFF_BRIGHT - (CUTOFF_BRIGHT - CUTOFF_DARK) * ci // (STEPS - 1)
            self.coefs.append(min(16384, int(32768 * (1 - math.exp(-2 * math.pi * cutoff / SAMPLE_RATE)))))
            self.gains.append(int(32768 * math.sqrt(CUTOFF_DARK / cutoff)))
        self.height = None  # the last step's, for the flutter
        self.level = self.coef = 0  # the bed's targets now, for the probe
        # --- MVP (P753) --- the whooshes: Q15 2 sin(pi f / 16000) for the centre f of each s^2 >> S2_SHIFT
        self.centres = array("H")
        for k in range((S2_FULL >> S2_SHIFT) + 1):
            f = CENTRE_LOW + (CENTRE_HIGH - CENTRE_LOW) * math.sqrt(k << S2_SHIFT) / math.sqrt(S2_FULL)
            self.centres.append(min(25080, int(32768 * 2 * math.sin(math.pi * min(f, CENTRE_HIGH) / SAMPLE_RATE))))
        self.whoosh = array("H", bytes(2 * VOICES))  # each voice's level target now, for the tests and the probe
        self.centre = array("H", [self.centres[0]] * VOICES)  # each voice's centre target now: a fading voice keeps it
        self.whoosh_level = 0  # the loudest of them

    def follow_field(self, total, height, wind):
        """--- Later, not MVP: the bed is off, see BED --- The bed's targets from one step's stats and the wind (-60 to 60)."""
        if not self.has_bed:
            return
        ci = min(max((height - HEIGHT_LOW) * (STEPS - 1) // (HEIGHT_HIGH - HEIGHT_LOW), 0), STEPS - 1)
        base = (min(total, TOTAL_FULL) >> 4) * BED_BASE // (TOTAL_FULL >> 4)  # the shift keeps the product under 2^30
        flutter = 0 if self.height is None else min(abs(height - self.height), FLUTTER_CAP) * FLUTTER
        self.height = height
        self.level = min(BED_MAX, (base * self.gains[ci] >> 15) + flutter + min(abs(wind), WIND_CAP) * WIND_LEVEL)
        self.coef = self.coefs[ci]
        self.c.noise_bed(self.noise, self.level, self.coef)

    def follow_bodies(self, moves, ms, wind):
        """--- MVP (P753) --- The whooshes' targets from one frame: moves holds dx, dy in px per body (body i is voice i),
        ms is the physics time behind them and wind is the wind now (-60 to 60). A body's airspeed is its velocity
        against the air, which the wind moves at WIND_AIR px/s a unit. A body that does not move is silent, and ms 0
        changes nothing."""
        if ms <= 0:
            return
        loudest = 0
        for i in range(min(len(moves) >> 1, VOICES)):
            dx, dy = moves[2 * i], moves[2 * i + 1]
            level = 0
            if dx or dy:
                vx = max(-V_CAP, min(V_CAP, dx * 1000 // ms - wind * WIND_AIR))
                vy = max(-V_CAP, min(V_CAP, dy * 1000 // ms))
                s2 = min(vx * vx + vy * vy, S2_FULL)
                if s2 >= S2_FLOOR:
                    level = (s2 >> 4) * WHOOSH_MAX // (S2_FULL >> 4)  # the shift keeps the product under 2^30
                    self.centre[i] = self.centres[s2 >> S2_SHIFT]
            self.c.noise_whoosh(self.noise, i, level, self.centre[i])
            self.whoosh[i] = level
            loudest = max(loudest, level)
        self.whoosh_level = loudest

    def render(self, buf):
        super().render(buf)
        self.c.noise_mix(self.noise, buf)  # an idle noise (no bed, no whoosh) leaves buf as it is


class SampledCrackle:
    """The naive path on the board: SAMPLED_POPS pops rendered once by Crackle with SAMPLED_LOOK (about 0.2 s each on the
    board, at start), then a sound.Mixer that plays the next one when a frame adds births. The Mixer has one voice, so the
    births of one frame make one pop, and a new pop cuts the last: started counts the pops played, dropped the rest."""

    def __init__(self, seed):
        import sound

        maker, self.pops = Crackle(seed, SAMPLED_LOOK), []
        for _ in range(SAMPLED_POPS):
            pop = array("h", bytes(2 * SAMPLED_SAMPLES))
            maker.add_pops(1)
            maker.render(pop)
            self.pops.append(pop)
        self.mixer, self.next_pop = sound.Mixer(), 0
        self.popped = self.started = self.dropped = 0

    @property
    def pending(self):
        return self.mixer.pending

    def add_pops(self, n):
        if n:
            self.mixer.play(self.pops[self.next_pop])  # first, so a render between the two never counts an unplayed pop
            self.popped += n
            self.next_pop = (self.next_pop + 1) % SAMPLED_POPS

    def render(self, buf):
        waiting = self.popped - self.started - self.dropped
        if waiting:
            self.started += 1
            self.dropped += waiting - 1
        self.mixer.render(buf)

    def counts(self):
        return self.popped, self.started, self.dropped
