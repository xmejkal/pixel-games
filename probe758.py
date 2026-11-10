"""
P758 bench: the rotary encoder's raw edges, one line each time the count changes, for SECONDS. --- MVP (P758) ---

    mpremote cp games/pins.py :pins.py
    mpremote cp games/encoder.py :encoder.py
    mpremote run probe758.py | tee run150-p758-encoder.log

The PO turns the knob 20 detents one way, waits, then 20 back, then leaves it at rest for 2 minutes. The edges per
detent are read from the 20 detents back. The probe prints raw edges only, so it passes edges_per_detent=1.
"""

import time

import pins
from encoder import Encoder

SECONDS = 180  # run150 ran 180 s: about 55 s of turns, then 125 s at rest

knob = Encoder.on_board(pins.ENC_A, pins.ENC_B, edges_per_detent=1)
print("p758 encoder on GPIO%d (ENC_A), GPIO%d (ENC_B), %d s" % (pins.ENC_A, pins.ENC_B, SECONDS))
start = time.ticks_ms()
last = knob.edges()
print("t_ms 0 edges %d" % last)
while time.ticks_diff(time.ticks_ms(), start) < SECONDS * 1000:
    edges = knob.edges()
    if edges != last:
        print("t_ms %d edges %d" % (time.ticks_diff(time.ticks_ms(), start), edges))
        last = edges
    time.sleep_ms(5)
print("end edges %d" % last)
