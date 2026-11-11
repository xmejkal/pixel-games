# Plays 16 kHz mono int16 raw files from the board's flash on the P733 amplifier (BCLK 12, WS 13, DIN 14, SD 6).
from machine import I2S, Pin
import time

FILES = ("a.raw",)
sd = Pin(6, Pin.OUT, value=0)
i2s = I2S(0, sck=Pin(12), ws=Pin(13), sd=Pin(14), mode=I2S.TX, bits=16, format=I2S.MONO, rate=16000, ibuf=8192)
buf = bytearray(4096)
view = memoryview(buf)
for name in FILES:
    print("play", name, time.ticks_ms())
    with open(name, "rb") as f:
        while True:
            n = f.readinto(buf)
            if not n:
                break
            i2s.write(view[:n])
            sd.value(1)
    i2s.write(bytearray(8192))  # silence, so the end of the file plays out
    time.sleep_ms(1500)
sd.value(0)
time.sleep_ms(10)
i2s.deinit()
print("done")
