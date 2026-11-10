"""
The rotary encoder (P758): the knob's turns as a count of detents. --- MVP (P758) ---

machine.Encoder decodes both channels in the ESP32-S3's pulse counter (PCNT), so no interrupt runs and a busy frame
loses no step (MicroPython v1.29, ports/esp32/modules/machine.py). Esp32 pin interrupts are soft and run late (see
buttons.py), so a decoder in Python could miss steps. The pins are pins.ENC_A and pins.ENC_B, from spark's
requirements.json, each with the internal pull-up (pins.ENC_A_PULL). How many edges fall in one detent is not
published (the part record cjmcu-111-rotary-encoder): the bench measures it, and the caller passes it.
"""

FILTER_NS = 12000  # the counter's glitch filter at its maximum, 1023 ticks of 80 MHz: drops contact spikes under 12 us


class Encoder:
    """edges() is the raw count of contact edges, detents() the nearest whole detent: + one way, - the other."""

    def __init__(self, counter, edges_per_detent):
        self.counter, self.edges_per_detent = counter, edges_per_detent

    @classmethod
    def on_board(cls, pin_a, pin_b, edges_per_detent, unit=0):
        from machine import Encoder as PulseCounter, Pin

        a, b = Pin(pin_a, Pin.IN, Pin.PULL_UP), Pin(pin_b, Pin.IN, Pin.PULL_UP)
        return cls(PulseCounter(unit, a, b, phases=4, filter_ns=FILTER_NS), edges_per_detent)

    def edges(self):
        return self.counter.value()

    def detents(self):
        return round(self.edges() / self.edges_per_detent)
