"""
The sounds of the game box by name (P768). tools/sound_bank.py makes one file of 16 kHz mono int16 samples and its
index on the Mac, and the Bank reads the file on the board.
"""

import os


# --- MVP (P768) ---
class BankSound:
    """One sound of a bank: `samples` int16 samples, little-endian, from sample `first` of `mem`. The plain sum
    reads sound[i], and the viper sum reads `mem` from `first`. It holds `mem`, so the bank's memory lives as long
    as the sound."""

    def __init__(self, mem, view, first, samples):
        self.mem, self.view, self.first, self.samples = mem, view, first, samples

    def __len__(self):
        return self.samples

    def __getitem__(self, i):
        if not 0 <= i < self.samples:
            raise IndexError(i)
        at = 2 * (self.first + i)
        x = self.view[at] | self.view[at + 1] << 8
        return x - 65536 if x >= 32768 else x


class Bank:
    """index: name -> (first sample, samples). The whole file is one block of bytes in an engine.SoundBank, outside
    the GC heap: a 300 KB array on the heap made each collection 10 to 19 ms (bench.md, P768, run196). A firmware
    with no SoundBank, and the Mac, get a bytearray. `where` says which."""

    def __init__(self, path, index, engine=None):
        if engine is None:
            try:
                import engine
            except ImportError:
                pass
        nbytes = os.stat(path)[6]
        mem = None
        if hasattr(engine, "SoundBank"):
            try:
                mem = engine.SoundBank(nbytes)
            except MemoryError:
                pass  # no room outside the heap: the heap's bytearray, slower collections
        self.where = "heap" if mem is None else getattr(mem, "where", "bank")
        if mem is None:
            mem = bytearray(nbytes)
        with open(path, "rb") as f:
            if f.readinto(mem) != nbytes:
                raise OSError("a short read of " + path)
        view, self.sounds = memoryview(mem), {}
        for name, (first, samples) in index.items():
            if first < 0 or samples <= 0 or 2 * (first + samples) > nbytes:
                raise ValueError("%s: %s ends before its %d samples" % (path, name, samples))
            self.sounds[name] = BankSound(mem, view, first, samples)

    def get(self, name):
        return self.sounds[name]
