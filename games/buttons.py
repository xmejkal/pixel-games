"""
The two buttons of the game box: a debounced Button class and the pin of the BOOT button.

The game button is the board's own button, pins.ONBOARD_BUTTON (GPIO47, reads 0 when pressed). The switch button is
the BOOT button on GPIO0. Spark's board record (boards/firebeetle2-esp32s3.json, pin_roles.strapping.note) says "D9 is
GPIO0, the BOOT pin ... usable as ordinary I/O once running". pins.py does not name it, so it is named here. Holding it
at reset enters the bootloader, so read it with Pin.IN and PULL_UP only after the firmware has started.
"""

import time

BOOT_BUTTON = 0
BOOT_BUTTON_ON = 0  # reads 0 when pressed

DEBOUNCE_MS = 20


class Button:
    """update(now) is True once per push, after the level read pressed for DEBOUNCE_MS; held is the steady level."""

    def __init__(self, read, pressed_level, debounce_ms=DEBOUNCE_MS):
        self.read, self.pressed_level, self.debounce_ms = read, pressed_level, debounce_ms
        self.held = False
        self.raw = False
        self.since = 0

    def update(self, now_ms):
        raw = self.read() == self.pressed_level
        if raw != self.raw:
            self.raw, self.since = raw, now_ms
        if raw != self.held and time.ticks_diff(now_ms, self.since) >= self.debounce_ms:
            self.held = raw
            return raw
        return False
