"""
The master volume (P757): one gain on the whole mix, just before the I2S. --- MVP (P757) ---

A Refill of sound.py calls volume.apply(block) after the mixer's render. The volume has STEPS steps: step 0 is
silent, step STEPS is the mix as it is, and each step between is DB_PER_STEP dB. A change of step ramps across one
block (16 ms), so it does not click. MasterVolume is the naive path, plain MicroPython bytecode, which stays working
(D26). A faster class keeps apply(buf) and overrides scale: ViperMasterVolume of volume_viper.py.
VolumeKnob turns the step with the rotary encoder (encoder.py), 1 step per detent, and saves it in a VolumeStore,
so the step survives a restart. Step 0 is saved like any step: a board that was turned to 0 starts silent.

DB_PER_STEP, DEFAULT_STEP, LOUDER and SAVE_AFTER_MS are choices for the PO's ear and hand, not measured facts.
"""

import time

STEPS = 16
DB_PER_STEP = 3
DEFAULT_STEP = 8
LOUDER = 1  # the sign of the encoder's louder direction
SAVE_AFTER_MS = 3000  # the knob saves the step this long after its last change, so a turn of 16 detents is one write
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


class VolumeStore:
    """The volume's step in one small file on the board. The board's file system is littlefs2, which commits a file
    when it closes, so a power cut leaves the old file or the new one. A caller starts its MasterVolume at load()."""

    def __init__(self, path="volume.txt"):
        self.path = path

    def load(self):
        """The saved step, or None: no file, text that is no number, or a number outside 0 to STEPS."""
        try:
            with open(self.path) as f:
                step = int(f.read())
        except (OSError, ValueError):
            return None
        return step if 0 <= step <= STEPS else None

    def save(self, step):
        with open(self.path, "w") as f:
            f.write(str(step))


class VolumeKnob:
    """The encoder's detents turn the volume's step, 1 step per detent. poll(now_ms) is the game loop's, once per
    frame: it is True when the step changed. A turn past an end is dropped, so the first detent back counts.
    With a store, the step is saved SAVE_AFTER_MS after its last change, when it differs from the saved one."""

    def __init__(self, encoder, volume, store=None, louder=LOUDER):
        self.encoder, self.volume, self.store, self.louder = encoder, volume, store, louder
        self.saved, self.changed_ms = volume.step, None  # the caller started the volume at the stored step
        self.saves = self.save_errors = 0

    def poll(self, now_ms):
        step = self.volume.step
        turned = self.encoder.take_detents(now_ms)
        if turned:
            self.volume.set(step + self.louder * turned)
        changed = self.volume.step != step
        if changed:
            self.changed_ms = now_ms
        elif self.changed_ms is not None and time.ticks_diff(now_ms, self.changed_ms) >= SAVE_AFTER_MS:
            self.changed_ms = None
            if self.store and self.volume.step != self.saved:
                self.save()
        return changed

    def save(self):
        """The step into the store. An OSError is counted, not raised, so the sound goes on. The step then counts
        as saved: the next try is at the next change, not at each frame."""
        try:
            self.store.save(self.volume.step)
            self.saves += 1
        except OSError:
            self.save_errors += 1
        self.saved = self.volume.step
