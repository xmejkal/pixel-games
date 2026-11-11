"""
The rotary encoder (P758): the knob's turns as a count of detents. --- MVP (P758) ---

machine.Encoder decodes both channels in the ESP32-S3's pulse counter (PCNT), so no interrupt runs per edge and a busy
frame loses no step (MicroPython v1.29, ports/esp32/modules/machine.py: its one interrupt fires at 32000 counts and
adds the overflow back). Esp32 pin interrupts are soft and run late (see buttons.py), so a decoder in Python could
miss steps. The pins are pins.ENC_A and pins.ENC_B, from spark's requirements.json. The pin map asks for the internal
pull-up (pins.ENC_A_PULL is "up"), and take_pads sets it. How many edges fall in one detent is not published (the part
record cjmcu-111-rotary-encoder), so the bench measured it.

Two limits, both from the bench and the board record (bench.md, P758):
- The knob does not rest on a multiple of 4 edges. In run150 it rested at 9, 85 and 5, and the count stepped back by
  1 edge inside a turn. So detents() can change by 1 at rest. A use that must not flicker, such as the volume
  (P757), calls take_detents(), which has a dead band.
- ENC_A and ENC_B are the board's RX and TX pads (P757), which the image gives to its serial console at each
  reset. take_pads() makes them plain inputs, and from then on the console's input no longer follows the RX pad
  (run174). So a program that has an encoder on these pads calls take_pads() at its start: app.run and on_board do.
  Until that call, a turn of the knob can type into the console. bench.md, P757, has why SDA and SCL did not work.
"""

import time

EDGES_PER_DETENT = 4  # the PO's CJMCU-111, 2026-11-10 (run150): 20 clicks back read 80 edges, 4 per click
FILTER_NS = 12000  # the glitch filter: 960 ticks of 80 MHz (the port stops at 1023), drops contact spikes under 12 us
DEAD_EDGES = 2  # take_detents: up to this many edges from the rest point are no turn (P757). Not tuned on the bench
REST_MS = 500  # take_detents: the knob rests when its count did not change for this long. Not tuned on the bench
REST_EDGES = 1  # take_detents: the rest point follows the count at most this far from a whole detent. Not tuned


# --- MVP (P757) ---
def take_pads(pin_a, pin_b):
    """Both pads as plain inputs with the chip's pull-up: (a, b), two machine.Pin. On the RX and TX pads this takes
    them from the serial console."""
    from machine import Pin

    return Pin(pin_a, Pin.IN, Pin.PULL_UP), Pin(pin_b, Pin.IN, Pin.PULL_UP)


class Encoder:
    """edges() is the raw count of contact edges, detents() the nearest detent, a half up: + one way, - the other.
    take_detents() gives the turn since its last call, for a caller that steps a value."""

    def __init__(self, counter, edges_per_detent):
        self.counter, self.edges_per_detent = counter, edges_per_detent
        self.anchor = None  # take_detents: the edge count where the knob rests
        self.drift = 0  # the rest point minus its whole detent: -REST_EDGES to REST_EDGES
        self.last_edges = self.changed_ms = 0

    @classmethod
    def on_board(cls, pin_a, pin_b, edges_per_detent, unit=0):
        from machine import Encoder as PulseCounter

        a, b = take_pads(pin_a, pin_b)
        return cls(PulseCounter(unit, a, b, phases=4, filter_ns=FILTER_NS), edges_per_detent)

    def edges(self):
        return self.counter.value()

    def detents(self):
        return (self.edges() + self.edges_per_detent // 2) // self.edges_per_detent  # round() gives uneven detents

    # --- MVP (P757) ---
    def take_detents(self, now_ms):
        """The whole detents turned since the last call, + one way and - the other. The first call sets the rest
        point and gives 0. A move of up to DEAD_EDGES edges from the rest point is no turn, so a knob that rests
        between two detents does not flicker: with 4 edges per detent, 3 to 6 edges are 1 detent. The rest point
        moves by whole detents, and it follows the count when the count did not change for REST_MS, because a
        knob does not rest on a multiple of 4 (run150). It follows at most REST_EDGES from its whole detent, so a
        slow turn, or a hand that stops in the middle of a click, loses no edge. now_ms is a time.ticks_ms()."""
        edges = self.edges()
        if self.anchor is None:
            self.anchor, self.last_edges, self.changed_ms = edges, edges, now_ms
            return 0
        if edges != self.last_edges:
            self.last_edges, self.changed_ms = edges, now_ms
        moved = edges - self.anchor
        n = (abs(moved) + self.edges_per_detent - 1 - DEAD_EDGES) // self.edges_per_detent
        if moved < 0:
            n = -n
        if n:
            self.anchor += n * self.edges_per_detent
        elif (moved and abs(self.drift + moved) <= REST_EDGES
              and time.ticks_diff(now_ms, self.changed_ms) >= REST_MS):
            self.anchor, self.drift = edges, self.drift + moved
        return n
