"""
The s3lcd backend: russhughes' C driver for the ESP32-S3, in our MicroPython image (v1.29.0, ESP32_GENERIC_S3 SPIRAM_OCT).

Each frame the game draws straight into the driver's framebuffer (TftCanvas, which keeps gfx.Canvas's clipping and its
shapes but draws at once), and show() sends it by DMA. With PARTIAL, the driver marks the 16 px tiles each draw touches,
and show() sends only the tiles drawn in this frame or the one before (P533 slice 5). The still picture repaints the
same pixels every frame, so TftOut draws it with tracking off. `import s3lcd` is inside open_tft(), because spark's Mac
stand-ins have no such module; it answers None then, and the app falls back to the st7789 driver.

With FRAMEBUFFER "double", show() returns once the send starts, so the "send" in the time log is the copy (about 3.4 ms
for a full frame) plus any wait for the last send.

Colours: the games use gfx.c565's values, already in the panel's byte order, so the bus sends the framebuffer as it is
(swap_color_bytes=False) and no colour is swapped on the way in or out. Painted pictures (pictures.py) go through blit_buffer
with a clear colour (P562); the old row sprites are drawn as runs of fill_rect. s3lcd's text needs a font module that may not be in the image, so
text uses the 8x8 font of framebuf, drawn as fill_rect runs (Canvas.big with scale 1).

Orientation: the driver stays at rotation 0, the panel's own order, so the panel writes each frame in the order it
scans (P533 slice 2). TftCanvas turns game coordinates into panel coordinates as it draws, which costs nothing per pixel.
A game column is a panel row, so a tear is one vertical line instead of a slanted break.
"""

import time

import framebuf

import gdi
import gfx
from gfx import FULL, Canvas, clamp

ORIENTATION = 0  # 0: upright in the PO's playing hold, the panel's row 0 along the right edge (bench.md); 180: turned
PANEL_W, PANEL_H = 240, 320  # the panel's own width and height at rotation 0
PARTIAL = True  # False sends the whole frame each show(), for a comparison on the bench
# Where the driver keeps the frame. "double" (P556; needs that firmware): in PSRAM, and show() copies it into an internal
# buffer, starts the send and returns, so the next frame paints during the send. "dma": internal, show() waits for the
# send. "strips": PSRAM, sent through two small buffers.
FRAMEBUFFER = "double"
# Past this many windows of changed tiles, show() sends the whole frame. esp_lcd starts a window only when the last one
# ended, so with "double" a whole frame (sent in the background, 3.4 ms of copy) beats many windows (show() waits for
# all but the last). Tunnel: 13 fps at 40 windows, 17 at 4, 16 at 1; stack 24 at each (bench.md, P556). 4 is one run per
# value, so it is a first pick, not a measured best. 40 is the driver's own default.
WINDOWS = 4 if FRAMEBUFFER == "double" else 40


# --- MVP (P599) ---
class Strip:
    """A panel rectangle with its own pixels. A TftCanvas draws into it as into the panel, and blit() copies it to the
    panel by rows, blit_buffer's memcpy path. A new strip is black, so each draw must cover its whole rect. It takes
    fill_rect only, so a draw into it uses fill, box, text, big and sprite, not line or picture."""

    def __init__(self, px, py, pw, ph):
        self.px, self.py, self.pw, self.ph = px, py, pw, ph
        self.buf = bytearray(pw * ph * 2)
        self.fb = framebuf.FrameBuffer(self.buf, pw, ph, framebuf.RGB565)

    def fill_rect(self, x, y, w, h, c):
        """The panel rectangle, moved to the strip's origin. The FrameBuffer clips what lies outside."""
        self.fb.fill_rect(x - self.px, y - self.py, w, h, c)

    def blit(self, tft):
        tft.blit_buffer(self.buf, self.px, self.py, self.pw, self.ph)


class TftCanvas(Canvas):
    def __init__(self, tft):  # no big buffers: the driver owns the framebuffer; bg_ok, because TftOut paints the still picture
        self.tft, self.full, self.bg_ok, self.clip, self.ops, self.cache, self.kept = tft, False, True, FULL, (), {}, {}
        self.mono = framebuf.FrameBuffer(bytearray(16 * 8), 16 * 8, 8, framebuf.MONO_HLSB)
        if ORIENTATION not in (0, 180):
            raise ValueError("ORIENTATION must be 0 or 180, not %r" % ORIENTATION)
        self.turned = ORIENTATION == 180
        self.pictures = not self.turned  # art/paint.py makes the pictures for ORIENTATION 0 only

    def start(self):
        self.clip = FULL

    def fill(self, x, y, w, h, c):
        """The game rectangle, clipped, as a panel rectangle: game x runs along the panel's y, game y against its x."""
        # One name per line and no max() or min(): a four-name assignment built a 32-byte tuple on every call, and the
        # call took twice as long (P550, run28-p550-lean.log: 169 against 87 us for 8 x 8)
        x0 = int(x)
        y0 = int(y)
        x1 = x0 + int(w)
        y1 = y0 + int(h)
        clip = self.clip
        if x0 < clip[0]:
            x0 = clip[0]
        if y0 < clip[1]:
            y0 = clip[1]
        if x1 > clip[2]:
            x1 = clip[2]
        if y1 > clip[3]:
            y1 = clip[3]
        if x1 > x0 and y1 > y0:  # the map is written out, not a helper: a returned tuple would allocate on every fill
            if self.turned:
                self.tft.fill_rect(PANEL_W - y1, x0, y1 - y0, x1 - x0, c)
            else:
                self.tft.fill_rect(y0, PANEL_H - x1, y1 - y0, x1 - x0, c)

    # --- MVP (P599) ---
    def panel_rect(self, x, y, w, h):
        """The game rectangle as (x, y, w, h) on the panel: fill's map, unclipped."""
        if self.turned:
            return PANEL_W - y - h, x, h, w
        return y, PANEL_H - x - w, h, w

    def keep(self, key, rect, draw):
        """draw(canvas) fills rect. It runs into a Strip only when key changes, and the Strip is blitted every frame
        (P599). The key names the caller, such as the game's name."""
        kept = self.kept.get(rect)
        if kept is None:
            strip = Strip(*self.panel_rect(*rect))
            kept = self.kept[rect] = [None, strip, TftCanvas(strip)]  # key, strip, the canvas that draws into it
        key_now, strip, canvas = kept
        if key_now != key:
            draw(canvas)
            kept[0] = key
        strip.blit(self.tft)

    def box(self, x, y, w, h, c):
        x, y, w, h = int(x), int(y), int(w), int(h)
        if w > 0 and h > 0:  # four edges, each clipped and placed by fill
            self.fill(x, y, w, 1, c)
            self.fill(x, y + h - 1, w, 1, c)
            self.fill(x, y, 1, h, c)
            self.fill(x + w - 1, y, 1, h, c)

    def picture(self, buf, x, y, w, h, key):
        """A picture made for ORIENTATION 0 (pictures.py), game (x, y) as its top left; pixels of the key colour are
        skipped (-1: none). The driver clips it and copies it by rows when it is wholly on the panel."""
        self.tft.blit_buffer(buf, y, PANEL_H - x - w, h, w, 255, key)

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
        self.tft, self.canvas, self.fresh = tft, TftCanvas(tft), True

    def clear(self):
        self.tft.fill(0)

    def reset(self):
        self.fresh = True  # another game: another still picture, which no draw of the new game marks

    def draw(self, game, us):
        t1, cv, tft = time.ticks_us(), self.canvas, self.tft
        tft.track(self.fresh)  # untracked, the background fill and the still picture mark nothing; fresh, fill marks all
        self.fresh = False
        if not game.covers:  # a game whose still picture covers the whole screen needs no fill under it
            tft.fill(game.bg)
        game.paint_static(cv)
        gfx.slowest(0, t1)  # the background fill and the still picture: no phase in Game.draw times them here (bg_ok)
        tft.track(True)
        cv.start()
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
    tft.config(framebuffer=FRAMEBUFFER, partial=PARTIAL, windows=WINDOWS)  # the framebuffer is read at init()
    tft.init()
    print("size", tft.width(), tft.height(), tft.config())
    return TftOut(tft)
