"""A stand-in for MicroPython's framebuf, so gfx imports on the Mac: the Stack tests record draw calls on their own
canvas and never draw pixels. An RGB565 buffer holds real pixels for fill and fill_rect (clipped, little-endian, as
the real one), so the HUD tests (P599) can compare a strip with the panel. MONO draws nothing: no font here."""

MONO_HLSB, RGB565 = 0, 1


class FrameBuffer:

    def __init__(self, buf=None, width=0, height=0, format=MONO_HLSB, *args):
        self.buf, self.width, self.height, self.format = buf, width, height, format

    def fill(self, c):
        self.fill_rect(0, 0, self.width, self.height, c)

    def pixel(self, *args):
        return 0

    def text(self, *args):
        pass

    def rect(self, x, y, w, h, c):
        """The outline, as four fill_rects (P762: render.StOut replays a box through it)."""
        for edge in ((x, y, w, 1), (x, y + h - 1, w, 1), (x, y, 1, h), (x + w - 1, y, 1, h)):
            self.fill_rect(*edge, c)

    def fill_rect(self, x, y, w, h, c):
        if self.format != RGB565:
            return
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, self.width), min(y + h, self.height)
        if x1 <= x0 or y1 <= y0:
            return
        row = (c & 0xFFFF).to_bytes(2, "little") * (x1 - x0)
        for yy in range(y0, y1):
            at = 2 * (yy * self.width + x0)
            self.buf[at:at + len(row)] = row
