# P550 (#754): what runner's paint is made of. Copy beside the games, then run each from a soft reset, so main.py
# stays off and the driver from the last run is freed:
#   mpremote soft-reset exec "import probe550; probe550.count()"   the PO plays runner: draw calls per play frame
#   mpremote soft-reset exec "import probe550; probe550.bench()"   no play: the cost of one call, by size
import gc
import time

import app
import gfx
import lcd

SMALL = 64  # panel pixels: a call up to this size is priced at the 8 x 8 cost, a larger one at the 16 x 240 cost (D7)
EVERY = 125  # play frames per printed line, about 6 s at 20 fps


class CountingCanvas(lcd.TftCanvas):
    """TftCanvas that also counts what it sends to the driver, in play frames only. Per part (the still picture, then
    the game): [calls up to SMALL px, their area, larger calls, their area, lines]. Counting adds Python time, so the
    paint time of this run is not used."""

    def __init__(self, tft):
        super().__init__(tft)
        self.static, self.game, self.frames, self.on = [0] * 5, [0] * 5, 0, False
        self.part = self.static

    def begin(self, play):
        """Called before each frame's draw: a report every EVERY play frames, then the still picture's count starts."""
        if self.frames == EVERY:
            for name, part in (("static", self.static), ("game", self.game)):
                print("count runner %s small %.1f area %.0f large %.1f area %.0f lines %.1f" % (
                    (name,) + tuple(v / EVERY for v in part)))
                part[:] = [0] * 5
            self.frames = 0
        self.on, self.part = play, self.static
        if play:
            self.frames += 1

    def start(self):  # TftOut.draw calls it between the still picture and the game's own draw
        super().start()
        self.part = self.game

    def fill(self, x, y, w, h, c):
        if self.on:  # the same clip as TftCanvas.fill, so the area is what the driver gets
            x0, y0 = int(x), int(y)
            cx0, cy0, cx1, cy1 = self.clip
            cw = min(x0 + int(w), cx1) - max(x0, cx0)
            ch = min(y0 + int(h), cy1) - max(y0, cy0)
            if cw > 0 and ch > 0:
                k = 0 if cw * ch <= SMALL else 2
                self.part[k] += 1
                self.part[k + 1] += cw * ch
        super().fill(x, y, w, h, c)

    def line(self, x0, y0, x1, y1, c):
        if self.on:
            self.part[4] += 1
        super().line(x0, y0, x1, y1, c)


class CountingOut(lcd.TftOut):
    def draw(self, game, us, overlay=None):
        self.canvas.begin(game.state == gfx.PLAY)
        super().draw(game, us, overlay)


def count():
    lcd.TftCanvas, lcd.TftOut = CountingCanvas, CountingOut  # open_tft and TftOut look both names up when called
    app.run(games=(app.Runner,))


def bench():
    """Microseconds per call, the empty loop's share taken off. The driver tracks tiles as it does in the games."""
    out = lcd.open_tft(app.SPI_HZ)
    tft, cv, c = out.tft, out.canvas, gfx.c565(90, 55, 25)
    tft.track(True)
    cv.start()
    fill_rect, fill = tft.fill_rect, cv.fill
    gc.collect()
    n = 1000
    t = time.ticks_us()
    for _ in range(n):
        pass
    empty = time.ticks_diff(time.ticks_us(), t) / n
    t = time.ticks_us()
    for _ in range(n):
        fill_rect(100, 100, 8, 8, c)
    rect8 = time.ticks_diff(time.ticks_us(), t) / n - empty
    t = time.ticks_us()
    for _ in range(n):
        fill_rect(100, 40, 16, 240, c)  # a game row 240 wide and 16 high, as the panel gets it
    rect240 = time.ticks_diff(time.ticks_us(), t) / n - empty
    t = time.ticks_us()
    for _ in range(n):
        fill(100, 100, 8, 8, c)
    canvas8 = time.ticks_diff(time.ticks_us(), t) / n - empty
    t = time.ticks_us()
    for _ in range(n):
        fill(40, 100, 240, 16, c)
    canvas240 = time.ticks_diff(time.ticks_us(), t) / n - empty
    t = time.ticks_us()
    for _ in range(100):
        tft.fill(c)
    screen = time.ticks_diff(time.ticks_us(), t) / 100 - empty
    gc.collect()
    a = gc.mem_alloc()
    for _ in range(n):
        fill(100, 100, 8, 8, c)
    per_fill = (gc.mem_alloc() - a) // n  # 32 on 2026-11-02: lcd.py's four-name assignment builds a tuple per call
    gc.collect()
    a = gc.mem_alloc()
    for _ in range(n):
        fill_rect(100, 100, 8, 8, c)
    per_rect = (gc.mem_alloc() - a) // n
    print("bench bytes allocated per call: canvas.fill %d fill_rect %d" % (per_fill, per_rect))
    print("bench us per call: empty loop %.2f fill_rect 8x8 %.2f 16x240 %.2f canvas.fill 8x8 %.2f 240x16 %.2f screen fill %.1f" % (
        empty, rect8, rect240, canvas8, canvas240, screen))
