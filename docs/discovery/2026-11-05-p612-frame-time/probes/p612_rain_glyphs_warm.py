# P612 probe R3 (throwaway, P604): the rain's paint traced per frame, with its HUD label redraw or without it, and
# where each kept strip's buffer lands. Run: mpremote run p612_rain.py. REDRAW is set by sed before each run.
import time

import uctypes

import app
import rain

REDRAW = 0  # 0: the label is drawn once and never again (as P599's E10)
SECONDS = 45
TRACE_FROM, TRACE_N = 250, 150  # frames: after the warm-up, the trace's length

if not REDRAW:
    rain.HUD_MS = 1_000_000_000

FRAME = [0]
REDRAWN = set()  # frames with a label redraw
GCS = set()  # frames that ended with a timed gc
TRACE = []
WHERE = []


class Probe(rain.Rain):
    def paint(self, cv):
        t = time.ticks_us()
        rain.Rain.paint(self, cv)
        if TRACE_FROM <= FRAME[0] < TRACE_FROM + TRACE_N:
            TRACE.append((FRAME[0], time.ticks_diff(time.ticks_us(), t)))

    def draw_hud(self, cv):
        REDRAWN.add(FRAME[0])
        rain.Rain.draw_hud(self, cv)

    def hud(self, cv):
        rain.Rain.hud(self, cv)
        if not WHERE:  # R3d: fill the glyph cache once, as many glyphs as the redraws build, then never redraw
            canvas = cv.kept[rain.LABEL_RECT][2]
            canvas.text("C step 0123456789. ms fps python, no", 0, 0, 0)
        if not WHERE:
            for rect, kept in cv.kept.items():
                WHERE.append((rect, hex(uctypes.addressof(kept[1].buf)), len(kept[1].buf)))


class Done(Exception):
    pass


START = time.ticks_ms()
_frame, _collect = app.App.frame, app.App.collect


def collect(self):
    GCS.add(FRAME[0])
    _collect(self)


def frame(self):
    _frame(self)
    FRAME[0] += 1
    if time.ticks_diff(time.ticks_ms(), START) > SECONDS * 1000:
        raise Done


app.App.frame, app.App.collect = frame, collect
print("probe p612 rain R3d: no redraw, glyph cache filled once at the start")
try:
    app.run(games=(Probe,))
except Done:
    pass
for rect, addr, n in WHERE:
    print("strip", rect, addr, n)
print("trace frame paint_us flags (h a label redraw in this frame, g a gc at the end of the frame before)")
for f, us in TRACE:
    print("tr", f, us, ("h" if f in REDRAWN else "") + ("g" if f - 1 in GCS else ""))
