"""
P768 (#1058): what the sum of N voices costs, with no game beside it. --- MVP (P768) ---

Copy games/sound.py, games/sound_viper.py and games/volume.py to the board, then, from the repository root:

    mpremote run probe768_sum.py

Lines: `sum match <1 or 0>` (the viper sum gives the plain sum's samples, sound_viper.sum_match), `viper args 6 <1 or
0>` (this image compiles a viper function with 6 arguments), then for each sum and each count of looping voices
`render <VoiceSum or ViperVoiceSum> voices <n> mean <us> max <us>`: Mixer.render of one block of 256 samples, BLOCKS
times, each voice at gain 20000. `voices 0` is the silent render. Then `gc free <us> ...` three times, `gc bank
<bytes> <us> ...` three times with a bank of BANK_SAMPLES samples as one array("h") on the heap, `gc soundbank <bytes> <us> ...` with
the same bytes in an engine.SoundBank, and `done`. Copy games/bank.py too.
"""

import gc
import time
from array import array

import sound
import sound_viper

BLOCKS = 100
BANK_SAMPLES = 150000  # 300 KB, the plan's largest bank


def timed(f, *args):
    t = time.ticks_us()
    f(*args)
    return time.ticks_diff(time.ticks_us(), t)


def main():
    print("sum match %d" % sound_viper.sum_match())
    try:
        exec("import micropython\n@micropython.viper\ndef six(a, b, c: int, d: int, e: int, f: int) -> int:\n    return c + d + e + f\n", {})
        print("viper args 6 1")
    except Exception as e:
        print("viper args 6 0", repr(e))
    buf = array("h", bytes(2 * sound.REFILL_SAMPLES))
    sounds = [array("h", (((i * 37 + k * 11) % 2000) - 1000 for i in range(1000 + 37 * k))) for k in range(8)]
    for voice_sum in (sound.VoiceSum, sound_viper.ViperVoiceSum):
        for count in (0, 1, 2, 4, 8):
            mixer = sound.Mixer(max(count, 1), voice_sum())
            for k in range(count):
                mixer.play(sounds[k], True, sound.SFX, 20000)
            gc.collect()
            total = worst = 0
            for _ in range(BLOCKS):
                us = timed(mixer.render, buf)
                total, worst = total + us, max(worst, us)
            print("render %s voices %d mean %d max %d" % (voice_sum.__name__, count, total // BLOCKS, worst))
    del sounds, mixer
    gc.collect()
    print("gc free", timed(gc.collect), timed(gc.collect), timed(gc.collect))
    bank = array("h", bytes(2 * BANK_SAMPLES))
    print("gc bank", 2 * len(bank), timed(gc.collect), timed(gc.collect), timed(gc.collect))
    del bank
    gc.collect()
    import engine

    bank = engine.SoundBank(2 * BANK_SAMPLES)
    print("gc soundbank", 2 * BANK_SAMPLES, timed(gc.collect), timed(gc.collect), timed(gc.collect))
    print("done")


main()
