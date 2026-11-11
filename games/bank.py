"""
The sounds of the game box by name (P768). tools/sound_bank.py makes one file of 16 kHz mono int16 samples and its
index on the Mac, and the Bank reads them on the board.
"""

from array import array


# --- MVP (P768) ---
class Bank:
    """index: name -> (first sample, samples). Each sound is an array("h") on the heap: the bank is 23 KB today.
    A bigger bank goes to engine.SoundBank, outside the GC heap, after a measurement (the plan of P768, step 6)."""

    def __init__(self, path, index):
        self.sounds = {}
        with open(path, "rb") as f:
            for name, (first, samples) in index.items():
                f.seek(2 * first)
                self.sounds[name] = array("h", f.read(2 * samples))
                if len(self.sounds[name]) != samples:
                    raise ValueError("%s: %s ends before its %d samples" % (path, name, samples))

    def get(self, name):
        return self.sounds[name]
