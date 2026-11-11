"""
The master volume's fast scale (P757): MasterVolume's loop as viper code. --- MVP (P757) ---

ViperMasterVolume keeps MasterVolume's apply(buf) and overrides scale, so a caller swaps the class and nothing else.
It is in its own module because only MicroPython compiles viper code: volume.py imports on any Python. scale_match()
runs both scales on the same named blocks, on the board and in the Mac's test.
"""

from array import array

import micropython
from volume import RAMP_BITS, MasterVolume

CORNERS = (32767, -32767, -32768, 1, -1, 0, 12345, -12345)  # the samples of each named block
CASES = ((0, 0), (1, 1), (32767, 32767), (32768, 32768), (0, 32768), (32768, 0), (23198, 16423), (1000, 1002))


class ViperMasterVolume(MasterVolume):
    def scale(self, buf, start, end):
        n = len(buf)
        inc = (abs(end - start) << RAMP_BITS) // n  # 0 for a steady gain: one loop does both
        scale_block(buf, n, start << RAMP_BITS, -inc if end < start else inc)


@micropython.viper
def scale_block(buf, n: int, acc: int, inc: int):
    """buf[i] times the gain acc >> 14 (RAMP_BITS), which moves by inc each sample. ptr16 reads unsigned, so the sign
    comes back by hand. No product is over 2^30, so all of it fits viper's 32-bit int."""
    p = ptr16(buf)  # noqa: F821, a viper built-in
    i = 0
    while i < n:
        acc += inc
        x = int(p[i])
        if x >= 32768:
            x -= 65536
        p[i] = (x * (acc >> 14)) >> 15
        i += 1


def scale_match():
    """True when the viper scale gives the naive scale's samples on each named block: the corner samples at steady
    gains, and ramps up and down. The Mac cannot see a 32-bit overflow, so the board runs it too."""
    naive, viper = MasterVolume(), ViperMasterVolume()
    for start, end in CASES:
        a, b = array("h", CORNERS * 32), array("h", CORNERS * 32)
        naive.scale(a, start, end)
        viper.scale(b, start, end)
        if bytes(a) != bytes(b):
            return False
    return True
