"""
The s3lcd backend: russhughes' C driver for the ESP32-S3, in our MicroPython image (v1.29.0, ESP32_GENERIC_S3 SPIRAM_OCT).

Each frame the game draws straight into the driver's framebuffer (TftCanvas, which keeps gfx.Canvas's clipping and its
shapes but draws at once), and show() sends it by DMA. No dirty boxes, no bands. `import s3lcd` is inside open_tft(),
because spark's Mac stand-ins have no such module; it answers None then, and the app falls back to the st7789 driver.

Colours: the games use gfx.c565's values, already in the panel's byte order, so the bus sends the framebuffer as it is
(swap_color_bytes=False) and no colour is swapped on the way in or out. Sprites need a clear colour and blit_buffer has
none, so they are drawn as the same runs of fill_rect. s3lcd's text needs a font module that may not be in the image, so
text uses the 8x8 font of framebuf, drawn as fill_rect runs (Canvas.big with scale 1).

Orientation: the driver stays at rotation 0, the panel's own order, so the panel writes each frame in the order it
scans (P533 slice 2). TftCanvas turns game coordinates into panel coordinates as it draws, which costs nothing per pixel.
A game column is a panel row, so a tear is one vertical line instead of a slanted break.
"""

import time

import framebuf

import gdi
from gfx import FULL, Canvas, clamp

ORIENTATION = 0  # 0: upright in the PO's playing hold, the panel's row 0 along the right edge (bench.md); 180: turned
PANEL_W, PANEL_H = 240, 320  # the panel's own width and height at rotation 0


class TftCanvas(Canvas):
    immediate = True

    def __init__(self, tft):  # no big buffers: the driver owns the framebuffer
        self.tft, self.full, self.bg_ok, self.clip, self.ops, self.cache = tft, False, False, FULL, (), {}
        self.mono = framebuf.FrameBuffer(bytearray(16 * 8), 16 * 8, 8, framebuf.MONO_HLSB)
        if ORIENTATION not in (0, 180):
            raise ValueError("ORIENTATION must be 0 or 180, not %r" % ORIENTATION)
        self.turned = ORIENTATION == 180

    def start(self):
        self.clip = FULL

    def fill(self, x, y, w, h, c):
        """The game rectangle, clipped, as a panel rectangle: game x runs along the panel's y, game y against its x."""
        x0, y0 = int(x), int(y)
        x1, y1 = x0 + int(w), y0 + int(h)
        cx0, cy0, cx1, cy1 = self.clip
        x0, y0, x1, y1 = max(x0, cx0), max(y0, cy0), min(x1, cx1), min(y1, cy1)
        if x1 > x0 and y1 > y0:  # the map is written out, not a helper: a returned tuple would allocate on every fill
            if self.turned:
                self.tft.fill_rect(PANEL_W - y1, x0, y1 - y0, x1 - x0, c)
            else:
                self.tft.fill_rect(y0, PANEL_H - x1, y1 - y0, x1 - x0, c)

    def box(self, x, y, w, h, c):
        x, y, w, h = int(x), int(y), int(w), int(h)
        if w > 0 and h > 0:  # four edges, each clipped and placed by fill
            self.fill(x, y, w, 1, c)
            self.fill(x, y + h - 1, w, 1, c)
            self.fill(x, y, 1, h, c)
            self.fill(x + w - 1, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = [clamp(int(v), -2000, 2000) for v in (x0, y0, x1, y1)]
        cx0, cy0, cx1, cy1 = self.clip
        if max(x0, x1) >= cx0 and min(x0, x1) < cx1 and max(y0, y1) >= cy0 and min(y0, y1) < cy1:
            if self.turned:  # the same map as fill, for two points; the driver drops the pixels off the panel
                self.tft.line(PANEL_W - 1 - y0, x0, PANEL_W - 1 - y1, x1, c)
            else:
                self.tft.line(y0, PANEL_H - 1 - x0, y1, PANEL_H - 1 - x1, c)

    def text(self, words, x, y, c):
        self.big(words, x, y, c, 1)

    def sprite(self, rows, palette, x, y, scale=1):
        # Keyed by the rows, not id(rows): runner builds its rows anew each frame, and an id key grew the cache
        # by one entry per frame (P533 run 16) and could hit a freed object's old entry.
        key = (rows, scale)
        rects = self.cache.get(key)
        if rects is None:
            rects = self.cache[key] = []
            for j, row in enumerate(rows):
                i = 0
                while i < len(row):
                    ch, start = row[i], i
                    while i < len(row) and row[i] == ch:
                        i += 1
                    if ch != ".":
                        rects.append((start * scale, j * scale, (i - start) * scale, scale, palette[ch]))
        for dx, dy, w, h, c in rects:
            self.fill(x + dx, y + dy, w, h, c)


class TftOut:
    """Same job as render.StOut: draw the frame, then one show()."""

    def __init__(self, tft):
        self.tft, self.canvas = tft, TftCanvas(tft)

    def clear(self):
        self.tft.fill(0)

    def reset(self):
        pass

    def draw(self, game, us):
        t1, cv = time.ticks_us(), self.canvas
        cv.start()
        self.tft.fill(game.bg)
        game.draw(cv)
        t2 = time.ticks_us()
        self.tft.show()
        us[1] += time.ticks_diff(t2, t1)
        us[2] += time.ticks_diff(time.ticks_us(), t2)


def open_tft(spi_hz):
    """The ready TftOut, or None when this image has no s3lcd."""
    try:
        import s3lcd
    except ImportError:
        return None
    from machine import Pin

    Pin(gdi.SD_CS, Pin.OUT, value=1)
    Pin(gdi.BL, Pin.OUT, value=1)
    bus = s3lcd.SPI_BUS(1, mosi=gdi.MOSI, sck=gdi.SCLK, dc=gdi.DC, cs=gdi.CS, pclk=spi_hz, swap_color_bytes=False)
    tft = s3lcd.ESPLCD(bus, 240, 320, inversion_mode=True, color_space=s3lcd.RGB, reset=gdi.RST, rotation=0)
    tft.init()
    print("size", tft.width(), tft.height())
    return TftOut(tft)
