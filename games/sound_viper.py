"""
The mixer's fast sum (P768): VoiceSum's two loops as viper code. --- MVP (P768) ---

ViperVoiceSum keeps VoiceSum's add and clip, so a caller swaps the class and nothing else. It is in its own module
because only MicroPython compiles viper code: sound.py imports on any Python. sum_match() runs both sums on the same
named blocks, on the board and in the Mac's test.
"""

from array import array

import micropython
from sound import VoiceSum

CORNERS = (32767, -32767, -32768, 1, -1, 0, 12345, -12345)  # the samples of each named block
GAINS = (0, 1, 16384, 23198, 32767, 32768)


class ViperVoiceSum(VoiceSum):
    def add(self, acc, k, voice, n, gain):
        add_block(acc, k, voice.mem, voice.first + voice.at, n, gain)

    def clip(self, acc, buf, n):
        clip_block(acc, buf, n)


@micropython.viper
def add_block(acc, k: int, mem, at: int, n: int, gain: int):
    """acc[k + i] += mem[at + i] * gain >> 15, with mem as int16 samples. ptr16 reads unsigned, so the sign comes back
    by hand. No product is over 2^30, so all of it fits viper's 32-bit int."""
    a = ptr32(acc)  # noqa: F821, a viper built-in
    s = ptr16(mem)  # noqa: F821
    end = k + n
    while k < end:
        x = int(s[at])
        if x >= 32768:
            x -= 65536
        a[k] = int(a[k]) + ((x * gain) >> 15)
        k += 1
        at += 1


@micropython.viper
def clip_block(acc, buf, n: int):
    a = ptr32(acc)  # noqa: F821
    p = ptr16(buf)  # noqa: F821
    i = 0
    while i < n:
        x = int(a[i])
        if x > 32767:
            x = 32767
        elif x < -32768:
            x = -32768
        p[i] = x
        a[i] = 0
        i += 1


def sum_match():
    """True when the viper sum gives the plain sum's samples: each corner sample at each gain, alone and as 8 voices
    that clip, from an array and from a bank's bytes. The Mac cannot see a 32-bit overflow, so the board runs it too."""
    from bank import BankSound
    from sound import Voice

    samples = array("h", CORNERS * 32)
    n, mem = len(samples), bytearray(bytes(4) + bytes(samples))  # the bank's sound starts at its sample 2
    for sound in (samples, BankSound(mem, memoryview(mem), 2, n)):
        for voices in (1, 8):
            for gain in GAINS:
                out = []
                for voice_sum in (VoiceSum(), ViperVoiceSum()):
                    acc, buf, voice = array("i", bytes(4 * n)), array("h", bytes(2 * n)), Voice(sound, False, "", gain, False, 0)
                    voice.at = 8
                    for _ in range(voices):
                        voice_sum.add(acc, 8, voice, n - 8, gain)
                    voice_sum.clip(acc, buf, n)
                    out.append(bytes(buf) + bytes(acc))
                if out[0] != out[1] or not any(out[0]) and gain:
                    return False
    return True
