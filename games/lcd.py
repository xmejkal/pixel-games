"""
The s3lcd backend: russhughes' C driver for the ESP32-S3, in the MicroPython image (v1.22.2, GENERIC_S3_OCT_16M).

Each frame the game draws straight into the driver's framebuffer (TftCanvas, which keeps gfx.Canvas's clipping and its
shapes but draws at once), and show() sends it by DMA. No dirty boxes, no bands. `import s3lcd` is inside open_tft(),
because spark's Mac stand-ins have no such module; it answers None then, and the app falls back to the st7789 driver.

Colours: the games use gfx.c565's pre-swapped values; s3lcd takes plain RGB565 and swaps the bytes itself
(swap_color_bytes=True), so every colour is swapped back on the way in. Sprites need a clear colour and blit_buffer has
none, so they are drawn as the same runs of fill_rect. s3lcd's text needs a font module that may not be in the image, so
text uses the 8x8 font of framebuf, drawn as fill_rect runs (Canvas.big with scale 1).
"""

import time

import framebuf

import gdi
from gfx import FULL, HEIGHT, WIDTH, Canvas, clamp

ROTATION = 1  # which way up the panel sits is not confirmed on the bench; change only this


class TftCanvas(Canvas):
    immediate = True

    def __init__(self, tft):  # no big buffers: the driver owns the framebuffer
        self.tft, self.full, self.bg_ok, self.clip, self.ops, self.cache = tft, False, False, FULL, (), {}
        self.mono = framebuf.FrameBuffer(bytearray(16 * 8), 16 * 8, 8, framebuf.MONO_HLSB)

    def start(self):
        self.clip = FULL

    def fill(self, x, y, w, h, c):
        x0, y0 = int(x), int(y)
        x1, y1 = x0 + int(w), y0 + int(h)
        cx0, cy0, cx1, cy1 = self.clip
        x0, y0, x1, y1 = max(x0, cx0), max(y0, cy0), min(x1, cx1), min(y1, cy1)
        if x1 > x0 and y1 > y0:
            self.tft.fill_rect(x0, y0, x1 - x0, y1 - y0, ((c & 255) << 8) | (c >> 8))

    def box(self, x, y, w, h, c):
        x0, y0, w, h = int(x), int(y), int(w), int(h)
        cx0, cy0, cx1, cy1 = self.clip
        if w > 0 and h > 0 and x0 + w > cx0 and x0 < cx1 and y0 + h > cy0 and y0 < cy1:
            n = ((c & 255) << 8) | (c >> 8)
            for rx, ry, rw, rh in ((x0, y0, w, 1), (x0, y0 + h - 1, w, 1), (x0, y0, 1, h), (x0 + w - 1, y0, 1, h)):
                if rx < WIDTH and ry < HEIGHT and rx + rw > 0 and ry + rh > 0:
                    self.tft.fill_rect(max(rx, 0), max(ry, 0), min(rw, WIDTH - max(rx, 0)), min(rh, HEIGHT - max(ry, 0)), n)

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = [clamp(int(v), -2000, 2000) for v in (x0, y0, x1, y1)]
        cx0, cy0, cx1, cy1 = self.clip
        if max(x0, x1) >= cx0 and min(x0, x1) < cx1 and max(y0, y1) >= cy0 and min(y0, y1) < cy1:
            self.tft.line(x0, y0, x1, y1, ((c & 255) << 8) | (c >> 8))

    def text(self, words, x, y, c):
        self.big(words, x, y, c, 1)

    def sprite(self, rows, palette, x, y, scale=1):
        rects = self.cache.get((id(rows), scale))
        if rects is None:
            rects = self.cache[(id(rows), scale)] = []
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
        bg = game.bg
        self.tft.fill(((bg & 255) << 8) | (bg >> 8))
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
    bus = s3lcd.SPI_BUS(1, mosi=gdi.MOSI, sck=gdi.SCLK, dc=gdi.DC, cs=gdi.CS, pclk=spi_hz, swap_color_bytes=True)
    tft = s3lcd.ESPLCD(bus, 240, 320, inversion_mode=True, color_space=s3lcd.RGB, reset=gdi.RST, rotation=ROTATION)
    tft.init()
    print("size", tft.width(), tft.height())
    return TftOut(tft)
