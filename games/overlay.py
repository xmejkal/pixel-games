"""
The system overlay (P762, P764): small pictures over the running game, for system information. --- MVP (P764) ---

Overlay holds a list of panes. A pane is one piece of system information. Each pane decides when it shows (update),
paints itself (draw) and has its own settings (alpha, hold_ms). The overlay draws each visible pane, in the order of
add(). A new pane is one class and one overlay.add(...) line. show() makes a pane visible for hold_ms. A pane that
sets visible itself, with no show(), has no end and stays on.

VolumePane is the first pane: the master volume's step as a bar of STEPS cells and a number. It watches the volume's
step, so each change of the step shows it, from the knob or from anything else, and no caller shows it. A pane draws
with cv.keep, as a game's score bar does (P599), so it is painted again only when its key changes. VolumePane keeps
two pictures: the still part, painted once, and the cells with the number, painted at each new step (2.2 ms on the
board against 3.8 ms for the whole picture, bench.md, P762). The first show paints both parts (4.4 ms). On lcd.py the
two kept strips stay in memory after the pane hides, about 15 KB. With an alpha under 255 the game shows through the
still part on lcd.py. The cells and the number stay solid: they read well, and their copy stays on the driver's fast
path. On render.py both parts are solid.

The app owns the overlay (App.overlay). Each output draws it after the game and before the frame goes to the display.
Nothing here erases a hidden pane: each output sends the areas of the frame before again (render.Dirty, and the
driver's tiles in lcd.py).

HOLD_MS, RECT, the colours and VolumePane.alpha are choices for the PO's eye, not measured facts.
"""

import time

from gfx import DARK, FULL, GREY, HEIGHT, WHITE, WIDTH, c565
from volume import STEPS

HOLD_MS = 1000  # the PO: "and for like a second afterwards"
RECT = (WIDTH // 2 - 100, HEIGHT - 44, 200, 28)  # the volume's picture: low, clear of a game's score bar at the top
LEVEL_RECT = (RECT[0] + 40, RECT[1] + 8, 156, 12)  # inside RECT: the cells and the number, the part a new step changes
EMPTY = c565(60, 60, 70)  # a cell above the step


class Pane:
    """One piece of system information over the game. A subclass paints in draw(cv) and can show itself in update."""

    alpha = 255  # how solid the pane is over the game on lcd.py. Under 255 the game shows through (bench.md, P762)
    hold_ms = HOLD_MS  # how long one show() keeps the pane on the screen
    visible, until = False, None  # until None: no end, so a pane that sets visible itself stays on

    def show(self, now_ms):
        """Visible from the next draw on, until hold_ms after now_ms. A second show() moves the end."""
        self.visible, self.until = True, time.ticks_add(now_ms, self.hold_ms)

    def update(self, now_ms):
        if self.until is not None and time.ticks_diff(now_ms, self.until) >= 0:
            self.visible, self.until = False, None

    def draw(self, cv):
        pass


class Overlay:
    """The layer over every game: its panes. add() is the caller's, once; update() and draw() are the frame's."""

    def __init__(self):
        self.panes = []

    def add(self, pane):
        self.panes.append(pane)
        return pane

    def update(self, now_ms):
        for pane in self.panes:
            pane.update(now_ms)

    def draw(self, cv):
        for pane in self.panes:
            if pane.visible:
                cv.clip = FULL  # a game or a pane can leave its own clip, and keep() asks for the whole screen
                pane.draw(cv)


class VolumePane(Pane):
    """The master volume's step, `volume.step` of a MasterVolume: `vol`, one cell per step, and the number. It shows
    at each change of the step."""

    alpha = 128  # the PO: "see through, it should be setting of each pane". At 192: "it could be more see through"

    def __init__(self, volume):
        self.volume, self.seen = volume, volume.step  # seen: the step of the last update, so the start shows nothing

    def update(self, now_ms):
        if self.volume.step != self.seen:
            self.seen = self.volume.step
            self.show(now_ms)
        super().update(now_ms)

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
