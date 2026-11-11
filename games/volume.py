"""
The master volume (P757): one gain on the whole mix, just before the I2S. --- MVP (P757) ---

A Refill of sound.py calls volume.apply(block) after the mixer's render. The volume has STEPS steps: step 0 is
silent, step STEPS is the mix as it is, and each step between is DB_PER_STEP dB. A change of step ramps across one
block (16 ms), so it does not click. MasterVolume is the naive path, plain MicroPython bytecode, which stays working
(D26). A faster class keeps apply(buf) and overrides scale: ViperMasterVolume of volume_viper.py.

DB_PER_STEP and DEFAULT_STEP are choices for the PO's ear, not measured facts.
"""

STEPS = 16
DB_PER_STEP = 3
DEFAULT_STEP = 8
FULL = 32768  # a gain is Q15: FULL is the mix as it is
RAMP_BITS = 14  # the ramp's fraction bits: FULL << RAMP_BITS is 2^29
GAINS = (0,) + tuple(int(FULL * 10 ** (-DB_PER_STEP * (STEPS - step) / 20) + 0.5) for step in range(1, STEPS + 1))


class MasterVolume:
    """The gain of step `step`, applied to each block. `gain` is the gain that the last block ended at: it starts at
    0, so the first block fades in. set() is the game loop's, apply() the refill's: each stores one int, so a callback
    between two bytecodes sees a whole value."""

    def __init__(self, step=DEFAULT_STEP):
        self.step, self.gain = 0, 0
        self.set(step)

    def set(self, step):
        self.step = min(max(step, 0), STEPS)

    def apply(self, buf):
        end = GAINS[self.step]
        if self.gain != FULL or end != FULL:  # the mix as it is costs nothing
            self.scale(buf, self.gain, end)
            self.gain = end

    def scale(self, buf, start, end):
        """buf times a gain that goes from start to end across the block. No product is over 2^30, and the loop
        divides nothing. The ramp never passes end: it stops at end, or 1 under it on the way up. >> rounds down,
        so a small negative sample stops at -1: 1 LSB."""
        n = len(buf)
        if start == end:
            for i in range(n):
                buf[i] = (buf[i] * start) >> 15
            return
        acc, inc = start << RAMP_BITS, (abs(end - start) << RAMP_BITS) // n
        if end < start:
            inc = -inc
        for i in range(n):
            acc += inc
            buf[i] = (buf[i] * (acc >> RAMP_BITS)) >> 15
