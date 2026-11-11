"""
Which rectangles of the screen changed since the last frame, from the Canvas's recorded tuples.

A tuple that is in this frame and not in the last (or the reverse) dirties its box. Boxes that touch are joined; if
there are many, or joining saves little, one box covers them all. The game that follows a switch starts from nothing,
so its first frame is the whole screen. chunks() cuts a rectangle into pieces that fit the Canvas's buffer.
"""

import time

from fast import native
from gfx import HEIGHT, WIDTH, Canvas

MARGIN, MANY, CELL = 4, 24, 32


@native
def touches(a, b, margin):
    return a[0] <= b[2] + margin and b[0] <= a[2] + margin and a[1] <= b[3] + margin and b[1] <= a[3] + margin


def area(r):
    return (r[2] - r[0]) * (r[3] - r[1])


def union(rects):
    return (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))


def cells(rects):
    """Many boxes become the 32x32 cells they touch, and the cells in a row become one box."""
    touched = set()
    for x0, y0, x1, y1 in rects:
        for cy in range(y0 // CELL, (y1 - 1) // CELL + 1):
            for cx in range(x0 // CELL, (x1 - 1) // CELL + 1):
                touched.add((cy, cx))
    runs, last = [], None
    for cy, cx in sorted(touched):
        if last and last[0] == cy and last[1] == cx - 1:
            runs[-1][2] = (cx + 1) * CELL
        else:
            runs.append([cx * CELL, cy * CELL, (cx + 1) * CELL, (cy + 1) * CELL])
        last = (cy, cx)
    return [tuple(r) for r in runs]


def merge(rects):
    if not rects:
        return []
    whole = union(rects)
    if len(rects) > MANY:
        rects = cells(rects)
        if len(rects) > MANY:
            return [whole]
    out = []
    for r in rects:
        joined = True
        while joined:
            joined = False
            for o in out:
                if touches(r, o, MARGIN):
                    out.remove(o)
                    r = union((r, o))
                    joined = True
                    break
        out.append(r)
    if sum(area(r) for r in out) * 10 >= area(whole) * 9:
        return [whole]
    return out


def spans(rects):
    """Boxes that share rows become one full-width box when that sends at most half again as many bytes: one window
    command and one long write cost less than several short ones."""
    out, group = [], []
    for r in sorted(rects, key=lambda r: r[1]) + [None]:
        if group and (r is None or r[1] > max(g[3] for g in group)):
            top, bottom = min(g[1] for g in group), max(g[3] for g in group)
            if len(group) > 1 and WIDTH * (bottom - top) * 2 <= sum(area(g) for g in group) * 3:
                out.append((0, top, WIDTH, bottom))
            else:
                out.extend(group)
            group = []
        if r is not None:
            group.append(r)
    return out


def chunks(rects, limit):
    """Each rectangle cut into (x, y, w, h) pieces of at most limit pixels, inside the screen."""
    for x0, y0, x1, y1 in rects:
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(WIDTH, x1), min(HEIGHT, y1)
        w = x1 - x0
        if w <= 0:
            continue
        rows, y = limit // w, y0
        while y < y1:
            h = min(rows, y1 - y)
            yield (x0, y, w, h)
            y += h


class Dirty:
    def __init__(self):
        self.last = self.seen = None

    def reset(self):
        self.last = self.seen = None

    def changed(self, ops):
        seen = set(ops)
        if self.last is None:
            rects = [(0, 0, WIDTH, HEIGHT)]
        else:
            rects = [op[:4] for op in ops if op not in self.seen] + [op[:4] for op in self.last if op not in seen]
        self.last, self.seen = ops, seen
        return merge(rects)


class StOut:
    """The st7789 backend: record the frame, find what changed, blit those boxes (dirty boxes, or bands without PSRAM)."""

    def __init__(self, display, full):
        self.display, self.canvas, self.dirty = display, Canvas(full), Dirty()

    def clear(self):
        self.display.fill_rect(0, 0, WIDTH, HEIGHT, 0)

    def reset(self):
        self.dirty.reset()
        self.canvas.reset_background()

    def draw(self, game, us, overlay=None):
        """Paint one frame and send it; adds the paint and send microseconds to us[1] and us[2]."""
        t1, cv = time.ticks_us(), self.canvas
        cv.start()
        if cv.full and not cv.bg_ok:  # the still picture, drawn once
            game.paint_static(cv)
            cv.build_background(game.bg)
        game.draw(cv)
        if overlay:  # --- MVP (P762) --- over the game, in the same frame
            overlay.draw(cv)
        rects = self.dirty.changed(cv.ops)
        t2 = time.ticks_us()
        for x, y, w, h in chunks(spans(rects) if cv.full else rects, cv.px):
            cv.begin(x, y, w, h, game.bg)
            cv.render(x, y, w, h)
            self.display.blit(cv.view, x, y, w, h)
        us[1] += time.ticks_diff(t2, t1)
        us[2] += time.ticks_diff(time.ticks_us(), t2)
