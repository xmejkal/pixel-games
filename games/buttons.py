"""
The two buttons of the game box: a debounced Button class and the pin of the BOOT button.

The game button is the BOOT button on GPIO0. The switch button is the board's own button, pins.ONBOARD_BUTTON (GPIO47,
reads 0 when pressed), only pressed briefly: it also drives the power chip's PWRON, and a hold of about 5 s powered the
board off on 2026-11-02. Spark's board record (boards/firebeetle2-esp32s3.json, pin_roles.strapping.note) says "D9 is
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
        self.watched, self.pushes, self.taken = False, 0, 0

    def watch(self, pin):
        """Count each edge toward the pressed level in a pin interrupt. The loop reads the pin once per frame, about
        140 ms, so a short tap fell between two reads; now every push counts, at most one frame late."""
        self.watched = True
        pin.irq(self.edge, pin.IRQ_FALLING if self.pressed_level == 0 else pin.IRQ_RISING)

    def edge(self, pin):
        self.pushes += 1  # a soft interrupt, run after the current C call: too late to read the pin itself

    def update(self, now_ms):
        raw = self.read() == self.pressed_level
        if self.watched:  # an edge since the last frame is a push, unless it is the bounce of a release seen now
            edged, self.taken = self.pushes != self.taken, self.pushes
            pushed, self.held = edged and (raw or not self.held), raw
            return pushed
        if raw != self.raw:
            self.raw, self.since = raw, now_ms
        if raw != self.held and time.ticks_diff(now_ms, self.since) >= self.debounce_ms:
            self.held = raw
            return raw
        return False
