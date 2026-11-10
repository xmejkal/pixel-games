"""The fire's crackle (P747): a soft roar and one pop per ember, so the pops come with the sparks on screen.

Both classes meet the Mixer contract of sound.py (render(buf), pending), so a Refill driver feeds either to the I2S.
add_pops(n) queues n pops, and the next render starts them. Crackle is plain Python: the naive path, which stays
working (D26), and the reference. NativeCrackle runs the same integer math in C, engine/core/fx_crackle.c, loaded from
crackle_c.mpy with no firmware rebuild. A Mac test wants the two equal sample for sample, so a change to one is a change
to both, by fx_crackle.h's rules: every value under 2^30, signed values shift only with >>, no / or %.

The pop queue has two counters with one writer each: add_pops only adds to popped, render only adds to started and
dropped. A refill callback between two bytecodes of add_pops so loses no pop and plays none twice.
"""

# --- MVP (P747) ---
# roar_shift, roar_gain, pop_min, pop_max, decay_min, decay_max, tails, tail_gap: see fx_crackle_init in fx_crackle.h
CRACKLE_LOOK = (4, 48, 6000, 12000, 28400, 31600, 3, 4000)
SLOTS = 8  # FX_CRACKLE_SLOTS
PEAK = 32767  # FX_CRACKLE_PEAK


class Crackle:
    """The crackle in plain Python, step for step fx_crackle.c. A crackle has no play, so pending stays None."""

    pending = None

    def __init__(self, seed, look=CRACKLE_LOOK):
        self.rng = (seed & 0xFFFF) or 1
        self.roar1 = self.roar2 = 0
        (self.roar_shift, self.roar_gain, self.pop_min, self.pop_max, self.decay_min, self.decay_max, self.tails,
         self.tail_gap) = look
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
            buf[k] = PEAK if total > PEAK else -PEAK if total < -PEAK else total


class NativeCrackle:
    """The same crackle in C: crackle_c.mpy, built by engine/natmod/crackle. Its state is a bytearray, which the heap
    aligns to 16 bytes, so the C reads its int32 fields aligned. ImportError when crackle_c.mpy is not on the board."""

    pending = None

    def __init__(self, seed, look=CRACKLE_LOOK):
        import crackle_c
        self.c = crackle_c
        self.state = bytearray(crackle_c.SIZE)
        crackle_c.init(self.state, seed, *look)

    def add_pops(self, n):
        self.c.add_pops(self.state, n)

    def render(self, buf):
        self.c.render(self.state, buf)

    def counts(self):
        return self.c.counts(self.state)
