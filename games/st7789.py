"""
A small ST7789 driver: reset, init, fill a rectangle, and draw text scaled up from framebuf's 8x8 font.

Written by the conversation for walk 4. The command codes are from the Sitronix ST7789V2 datasheet v1.0, which the
research kept in the store: SWRESET 0x01, SLPOUT 0x11, COLMOD 0x3A, MADCTL 0x36, INVON 0x21, NORON 0x13, DISPON 0x29,
CASET 0x2A, RASET 0x2B, RAMWR 0x2C. The panel is 240x320 in portrait; MADCTL 0x20 (MV) turns it to landscape, 320x240. An IPS panel shows true colours with
inversion on. Colours are RGB565, sent high byte first.
"""

import time

import framebuf

SEND_BYTES = 16384  # one SPI write; 0 writes the whole span in one go
WIDTH, HEIGHT = 320, 240  # landscape: MADCTL below turns the 240x320 panel on its side


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


class ST7789:
    def __init__(self, spi, cs, dc, rst):
        self.spi, self.cs, self.dc, self.rst = spi, cs, dc, rst
        self.cs.value(1)
        # Made here, before the big frames, so it sits low in the heap. On a PSRAM build the whole MicroPython heap is
        # PSRAM, so this cannot be forced into internal RAM; the chunks at least keep each SPI write the same small size.
        self.send = bytearray(SEND_BYTES)
        self.send_view = memoryview(self.send)

    def command(self, code, data=None):
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytes([code]))
        if data:
            self.dc.value(1)
            self.spi.write(bytes(data))
        self.cs.value(1)

    def init(self):
        self.rst.value(0)
        time.sleep_ms(20)
        self.rst.value(1)
        time.sleep_ms(150)
        self.command(0x01)
        time.sleep_ms(150)
        self.command(0x11)
        time.sleep_ms(120)
        self.command(0x3A, [0x55])
        self.command(0x36, [0xA0])  # MV (bit 5) swaps rows and columns, MY (bit 7) flips rows. On the bench on 2026-11-01,
        # 0x60 (MV + MX) showed the picture turned 180 degrees and 0x20 (MV) showed it mirrored
        self.command(0x21)
        self.command(0x13)
        self.command(0x29)
        time.sleep_ms(20)

    def window(self, x, y, w, h):
        x1, y1 = x + w - 1, y + h - 1
        self.command(0x2A, [x >> 8, x & 0xFF, x1 >> 8, x1 & 0xFF])
        self.command(0x2B, [y >> 8, y & 0xFF, y1 >> 8, y1 & 0xFF])
        self.command(0x2C)

    def pixels(self, data):
        self.cs.value(0)
        self.dc.value(1)
        self.spi.write(data)
        self.cs.value(1)

    def fill_rect(self, x, y, w, h, colour):
        self.window(x, y, w, h)
        row = bytes([colour >> 8, colour & 0xFF]) * w
        self.cs.value(0)
        self.dc.value(1)
        for _ in range(h):
            self.spi.write(row)
        self.cs.value(1)

    def text(self, words, x, y, colour, background, scale=3):
        """Draw words with framebuf's 8x8 font, each dot as a scale x scale block."""
        w = 8 * len(words)
        mono = framebuf.FrameBuffer(bytearray(w), w, 8, framebuf.MONO_VLSB)
        mono.text(words, 0, 0, 1)
        on, off = bytes([colour >> 8, colour & 0xFF]) * scale, bytes([background >> 8, background & 0xFF]) * scale
        self.window(x, y, w * scale, 8 * scale)
        for row in range(8):
            line = b"".join(on if mono.pixel(col, row) else off for col in range(w))
            for _ in range(scale):
                self.pixels(line)

    def blit(self, buf, x, y, w, h):
        """Send w*h pixels, already RGB565 high byte first, to the window at x, y: one window command, then the bytes in
        SEND_BYTES pieces copied through self.send. buf may be a memoryview."""
        self.window(x, y, w, h)
        if not SEND_BYTES:
            return self.pixels(buf)
        n, off, send = w * h * 2, 0, self.send_view
        self.cs.value(0)
        self.dc.value(1)
        while off < n:
            m = min(SEND_BYTES, n - off)
            send[:m] = buf[off:off + m]
            self.spi.write(send if m == SEND_BYTES else send[:m])
            off += m
        self.cs.value(1)

    def scroll_area(self, top, scroll, bottom):
        """VSCRDEF (0x33): top fixed + scrolling + bottom fixed lines of the panel's 320-line axis; they must add to 320.
        ST7789V2 datasheet v1.0 p.210: MADCTL MV should be 0 in scrolling mode, so check this on the bench with 0xA0."""
        self.command(0x33, [top >> 8, top & 0xFF, scroll >> 8, scroll & 0xFF, bottom >> 8, bottom & 0xFF])

    def scroll_start(self, line):
        """VSCSAD (0x37): the frame-memory line shown first in the scrolling area (datasheet p.220)."""
        self.command(0x37, [line >> 8, line & 0xFF])
