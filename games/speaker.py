"""
The game box's sound output (P768): the amplifier on the I2S pins of pins.py, fed from one Mixer.
"""

import pins
import sound

IBUF = 2048  # TX DMA bytes: 4 buffers of 256 samples, a ring of 64 ms (bench.md, P748)
VOICES = 4  # the viper sum of 4 voices renders a block in at most 0.9 ms, and of 8 in 1.4 ms (bench.md, P768, run197)


def voice_sum():
    """The fast sum where this Python compiles viper code, else the plain one (D26)."""
    try:
        from sound_viper import ViperVoiceSum as Sum
    except (ImportError, AttributeError, SyntaxError):
        Sum = sound.VoiceSum
    return Sum()


# --- MVP (P768) ---
class Speaker:
    """Adapter: owns the I2S, the Refill and the Mixer. volume: a MasterVolume, or None for the mix as it is.
    Nothing touches hardware before open(). The amplifier stays off until open()'s first write."""

    def __init__(self, volume=None):
        self.mixer, self.volume, self.refill = sound.Mixer(VOICES, voice_sum()), volume, None

    def open(self):
        from machine import I2S, Pin

        shutdown = Pin(pins.AUDIO_SHUTDOWN, Pin.OUT, value=0)
        i2s = I2S(0, sck=Pin(pins.I2S_BCLK), ws=Pin(pins.I2S_LRC), sd=Pin(pins.I2S_DIN), mode=I2S.TX, bits=16,
                  format=I2S.MONO, rate=sound.RATE, ibuf=IBUF)
        refill = sound.CallbackRefill(self.mixer, i2s, shutdown, IBUF // 2, self.volume)
        try:
            refill.open()
        except Exception:  # a failed open leaves no I2S behind
            refill.close()
            raise
        self.refill = refill

    def close(self):
        if self.refill:
            self.refill.close()
            self.refill = None
