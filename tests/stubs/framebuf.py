"""A stand-in for MicroPython's framebuf, so gfx imports on the Mac: the Stack tests record draw calls on their own
canvas and never draw pixels. An RGB565 buffer holds real pixels for fill and fill_rect (clipped, little-endian, as
the real one), so the HUD tests (P599) can compare a strip with the panel. A MONO_HLSB buffer holds real bits for fill,
fill_rect and pixel, and text draws into it from FONT, the 768 bytes of MicroPython's font_petme128_8x8.h (96
characters from 32, eight column bytes each, bit 0 the top row), which tools/render_scene.py sets (P795). With FONT
None, as in the tests, text draws nothing and pixel reads 0."""

MONO_HLSB, RGB565 = 0, 1
FONT = None


class FrameBuffer:

    def __init__(self, buf=None, width=0, height=0, format=MONO_HLSB, *args):
        self.buf, self.width, self.height, self.format = buf, width, height, format

    def fill(self, c):
        self.fill_rect(0, 0, self.width, self.height, c)

    def pixel(self, x, y, *c):
        """The bit at (x, y) of a MONO_HLSB buffer; 0 off it, 0 for RGB565. It reads only."""
        if self.format != MONO_HLSB or not (0 <= x < self.width and 0 <= y < self.height):
            return 0
        return (self.buf[(x + y * self.width) >> 3] >> (7 - (x & 7))) & 1

    def text(self, s, x, y, c=1):
        """modframebuf.c's text into a MONO_HLSB buffer: a character outside 32..127 draws as 127."""
        if self.format != MONO_HLSB or FONT is None:
            return
        for ch in s:
            code = ord(ch)
            if code < 32 or code > 127:
                code = 127
            for column in FONT[(code - 32) * 8:(code - 31) * 8]:
                for row in range(8):
                    if column >> row & 1:
                        self.fill_rect(x, y + row, 1, 1, c)
                x += 1

    def rect(self, x, y, w, h, c):
        """The outline, as four fill_rects (P762: render.StOut replays a box through it)."""
        for edge in ((x, y, w, 1), (x, y + h - 1, w, 1), (x, y, 1, h), (x + w - 1, y, 1, h)):
            self.fill_rect(*edge, c)

    def fill_rect(self, x, y, w, h, c):
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, self.width), min(y + h, self.height)
        if x1 <= x0 or y1 <= y0:
            return
        if self.format == MONO_HLSB:
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    at, bit = (xx + yy * self.width) >> 3, 1 << (7 - (xx & 7))
                    self.buf[at] = self.buf[at] | bit if c else self.buf[at] & ~bit
            return
        row = (c & 0xFFFF).to_bytes(2, "little") * (x1 - x0)
        for yy in range(y0, y1):
            at = 2 * (yy * self.width + x0)
            self.buf[at:at + len(row)] = row
