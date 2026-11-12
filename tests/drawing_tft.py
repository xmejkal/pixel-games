"""The s3lcd display stood in for a render on the Mac (P795): test_fire's Tft with the driver's fill, line and
blit_buffer, so lcd.TftOut.draw runs a frame as it does on the board and image() gives the frame as the game's view.
The frame holds a native uint16 per pixel in the panel's byte order, as the driver's does; blit_buffer copies rows
when a picture lies wholly on the panel at full alpha, else it clips, keys and blends each pixel as blend565.h does.
tools/render_scene.py and tests/test_render_scene.py share it. --- MVP (P795) ---"""

from array import array

from test_fire import Tft  # first: it puts games/ and the stubs on the path and gives time the ticks functions

import lcd  # noqa: E402

W, H = lcd.PANEL_W, lcd.PANEL_H


def swap(v):
    return ((v & 0xFF) << 8) | (v >> 8)


def blend(fg, bg, alpha):
    """blend565.h's alpha_blend_565: the bytes of both colours swapped in, each channel mixed, the result swapped back."""
    if alpha == 0:
        return bg
    if alpha == 255:
        return fg
    fg, bg = swap(fg), swap(bg)
    r = ((fg >> 11) * alpha + (bg >> 11) * (255 - alpha)) >> 8
    g = (((fg >> 5) & 0x3F) * alpha + ((bg >> 5) & 0x3F) * (255 - alpha)) >> 8
    b = ((fg & 0x1F) * alpha + (bg & 0x1F) * (255 - alpha)) >> 8
    return swap((r << 11) | (g << 5) | b)


class DrawingTft(Tft):
    """test_fire's Tft with the calls lcd.TftOut.draw makes: fill, line, blit_buffer, track and show."""

    def fill(self, c):
        self.fill_rect(0, 0, W, H, c)

    def track(self, on):
        pass

    def show(self):
        return 0  # the windows sent: none on the Mac

    def pixel(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            memoryview(self.frame).cast("H")[y * W + x] = c

    def line(self, x0, y0, x1, y1, c):
        """s3lcd.c's line: Bresenham with the end points in, each pixel off the panel dropped."""
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0, x1, y1 = y0, x0, y1, x1
        if x0 > x1:
            x0, x1, y0, y1 = x1, x0, y1, y0
        dx, dy = x1 - x0, abs(y1 - y0)
        err, ystep = dx >> 1, 1 if y0 < y1 else -1
        for x in range(x0, x1 + 1):
            if steep:
                self.pixel(y0, x, c)
            else:
                self.pixel(x, y0, c)
            err -= dy
            if err < 0:
                err += dx
                y0 += ystep

    def blit_buffer(self, buf, x, y, w, h, alpha=255, key=-1):
        """s3lcd.c's blit_buffer: buf holds w * h uint16 pixels, row by row, in the frame's own byte order. Wholly on
        the panel at alpha 255 it copies rows (every pixel but the key); else each pixel is clipped, keyed and blended."""
        if w <= 0 or h <= 0:
            return
        if w > len(buf) // 2 // h:
            raise ValueError("buffer smaller than width * height * 2")
        src, dst = memoryview(buf).cast("H"), memoryview(self.frame).cast("H")
        if alpha == 255 and 0 <= x <= W - w and 0 <= y <= H - h:
            for yy in range(h):
                at, row = (y + yy) * W + x, src[yy * w:(yy + 1) * w]
                if key < 0:
                    dst[at:at + w] = row
                else:
                    for xx, v in enumerate(row):
                        if v != key:
                            dst[at + xx] = v
            return
        for yy in range(max(0, -y), min(h, H - y)):
            for xx in range(max(0, -x), min(w, W - x)):
                v = src[yy * w + xx]
                if key < 0 or v != key:
                    at = (y + yy) * W + x + xx
                    dst[at] = blend(v, dst[at], alpha)

    def image(self):
        """The frame (panel byte order, portrait) as the game's landscape view, a Pillow image."""
        from PIL import Image

        px = array("H", bytes(self.frame))
        px.byteswap()  # the panel's byte order, read back to normal
        img = Image.new("RGB", (W, H))
        img.putdata([((v >> 11) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31) for v in px])
        return img.rotate(-90, expand=True)
