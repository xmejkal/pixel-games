"""
The system overlay (P762): one small picture over the running game, for system information. --- MVP (P762) ---

Overlay holds one view and hides it HOLD_MS after the last show(). A view is any object with draw(cv). VolumeView is
the first one: the master volume's step as a bar of STEPS cells and a number. A view draws with cv.keep, as a game's
score bar does (P599), so it is painted again only when its key changes. VolumeView keeps two pictures: the still
part, painted once, and the cells with the number, painted at each new step (2.2 ms on the board against 3.8 ms for
the whole picture, bench.md, P762). With VolumeView.alpha under 255 the game shows through the still part on lcd.py.
The cells and the number stay solid: they read well, and their copy stays on the driver's fast path. On render.py
both parts are solid.

The app owns the overlay (App.overlay). Each output draws it after the game and before the frame goes to the display.
Nothing here erases a hidden view: each output sends the areas of the frame before again (render.Dirty, and the
driver's tiles in lcd.py).

HOLD_MS, RECT and the colours are choices for the PO's eye, not measured facts.
"""

import time

from gfx import DARK, GREY, HEIGHT, WHITE, WIDTH, c565
from volume import STEPS

HOLD_MS = 1000  # the PO: "and for like a second afterwards"
RECT = (WIDTH // 2 - 100, HEIGHT - 44, 200, 28)  # the volume's picture: low, clear of a game's score bar at the top
LEVEL_RECT = (RECT[0] + 40, RECT[1] + 8, 156, 12)  # inside RECT: the cells and the number, the part a new step changes
EMPTY = c565(60, 60, 70)  # a cell above the step


class Overlay:
    """The layer over every game. show() is the caller's, at each change; update() and draw() are the frame's."""

    def __init__(self, hold_ms=HOLD_MS):
        self.hold_ms, self.view, self.until = hold_ms, None, 0

    def show(self, view, now_ms):
        """Show view from the next frame on, until hold_ms after now_ms. A second show() moves the end."""
        self.view, self.until = view, time.ticks_add(now_ms, self.hold_ms)

    def update(self, now_ms):
        if self.view is not None and time.ticks_diff(now_ms, self.until) >= 0:
            self.view = None

    def draw(self, cv):
        if self.view is not None:
            self.view.draw(cv)


class VolumeView:
    """The master volume's step, `volume.step` of a MasterVolume: `vol`, one cell per step, and the number."""

    alpha = 255  # how solid the still part is over the game on lcd.py. Under 255 the game shows through (bench.md)

    def __init__(self, volume):
        self.volume = volume

    def draw(self, cv):
        cv.keep("volume", RECT, self.paint, self.alpha)
        cv.keep(("level", self.volume.step), LEVEL_RECT, self.paint_level)

    def paint(self, cv):
        """The still part. Covers RECT, as keep() asks, with fill, box and text only: a kept strip of lcd.py takes no
        more."""
        x, y, w, h = RECT
        cv.fill(x, y, w, h, DARK)
        cv.box(x, y, w, h, GREY)
        cv.text("vol", x + 8, y + 10, WHITE)

    def paint_level(self, cv):
        """The part that a new step changes. Covers LEVEL_RECT."""
        x, y, w, h = LEVEL_RECT
        step = self.volume.step
        cv.fill(x, y, w, h, DARK)
        for i in range(STEPS):
            cv.fill(x + 8 * i, y, 6, h, WHITE if i < step else EMPTY)
        cv.text(str(step), x + 136, y + 2, WHITE)
