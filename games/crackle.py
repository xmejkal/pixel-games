"""The fire's crackle (P747): a soft roar and one pop per ember, so the pops come with the sparks on screen.

All three classes meet the Mixer contract of sound.py (render(buf), pending), so a Refill driver feeds any of them to
the I2S. add_pops(n) queues n pops, and the next render starts them. counts() gives (popped, started, dropped).

- Crackle is plain Python and the reference. It takes 21 ms for 16 ms of sound on the board (run145b), so on the board
  it only renders SampledCrackle's pops.
- NativeCrackle runs the same integer math in C, engine/core/fx_crackle.c, loaded from crackle_c.mpy with no firmware
  rebuild: 0.4 ms a block. A Mac test wants it equal to Crackle sample for sample, so a change to one is a change to
  both, by fx_crackle.h's rules: every value under 2^30, signed values shift only with >>, no / or %.
- GrainCrackle (P751) is the fire of P750's demo g: a bed of grains and one bank pop per ember, mixed in C by
  engine/core/fx_grains.c from the same crackle_c.mpy, out of a sample bank (fire_bank.raw, made on the Mac by
  tools/fire_bank.py). No filter, so nothing rings or overflows.
- SampledCrackle is the naive path on the board, which stays working (D26, the PO chose it on 2026-11-10): Crackle
  renders a few pops once, and a sound.Mixer plays one per frame that has births. No roar, no overlap.

The pop queue has two counters with one writer each: add_pops only adds to popped, render only adds to started and
dropped. A refill callback between two bytecodes of add_pops so loses no pop and plays none twice.
"""

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
    add_pops, render and counts are NativeCrackle's."""

    pending = None

    def __init__(self, seed, look=GRAIN_LOOK, bank_path=BANK_FILE, native=None):
        import os
        from fire_bank import FIRE_BANK_INDEX

        if native is None:
            import crackle_c as native
        check_grain_look(look)
        t = ticks()
        self.bank = bytearray(os.stat(bank_path)[6])
        with open(bank_path, "rb") as f:
            f.readinto(self.bank)
        print("bank load %d ms, %d bytes" % (ticks() - t, len(self.bank)))
        self.c = native
        self.state = bytearray(native.GRAINS_SIZE)
        native.grains_init(self.state, seed, array("i", look), array("i", FIRE_BANK_INDEX))

    def add_pops(self, n):
        self.c.grains_add_pops(self.state, n)

    def render(self, buf):
        self.c.grains_render(self.state, self.bank, buf)

    def counts(self):
        return self.c.grains_counts(self.state)


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
