"""
P733 step 1: a 440 Hz tone on the DFR0954 amplifier through stock machine.I2S, with no new C.

    mpremote run probe733.py

Pads (the wiring page, 2026-11-09): BCLK D12 (GPIO12), LRC D11 (GPIO13), DIN D10 (GPIO14), SD A2 (GPIO6), power on
3V3. The tone plays for 5 s, then SD goes low and the clocks run 1 s more, so the tone must stop about 1 s before the
end. That proves GPIO6 shuts the amplifier down. The listen is the only proof of the wiring: the ESP32 makes its own
clocks, so write() completes with nothing connected.

One line per number: `name value unit`. Expected bytes over the 5 s: 160,000 to 164,896 B (5 s x 32,000 B/s, plus the
4,096 B queue and one 800 B write). This proves the clock rate only.
"""

import math
import time
from array import array

from machine import I2S, Pin

# --- MVP ---
RATE = 16000
CYCLE = 400  # exactly 11 cycles of 440 Hz at 16 kHz, so the loop has no seam
AMPLITUDE = 3000  # of 32767, to start quiet

wave = array("h", (int(AMPLITUDE * math.sin(2 * math.pi * 11 * i / CYCLE)) for i in range(CYCLE)))


def play(i2s, ms):
    """Write the wave for ms milliseconds. Returns the bytes written and the longest write in ms."""
    total, longest = 0, 0
    end = time.ticks_add(time.ticks_ms(), ms)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        t = time.ticks_ms()
        total += i2s.write(wave)
        longest = max(longest, time.ticks_diff(time.ticks_ms(), t))
    return total, longest


def say(name, value, unit):
    print("%s %d %s" % (name, value, unit))


sd = Pin(6, Pin.OUT, value=0)  # amplifier off until the clocks run
i2s = None
start = time.ticks_ms()
try:
    i2s = I2S(0, sck=Pin(12), ws=Pin(13), sd=Pin(14), mode=I2S.TX, bits=16, format=I2S.MONO, rate=RATE, ibuf=4096)
    sd.value(1)
    total, longest = play(i2s, 5000)
    sd.value(0)
    play(i2s, 1000)  # clocks still running: the tone must be gone
    say("bytes", total, "B")
    say("longest_write", longest, "ms")
finally:
    # Shut the amplifier down before the clocks stop: a stopped LRCLK with BCLK running can harm the speaker
    # (PHYS-13). The 10 ms is a margin with no datasheet figure.
    sd.value(0)
    time.sleep_ms(10)
    if i2s:
        i2s.deinit()
say("elapsed_ms", time.ticks_diff(time.ticks_ms(), start), "ms")
print("done")
