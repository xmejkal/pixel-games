"""
The game box: ten one-button games on the GDI display. The board's own button plays, the BOOT button moves to the
next game from any state.

run() prints `ready` once the display is set up, then `game <name>` at the start and after each BOOT press. Its loop
reads the console without waiting (commands/build.md, "The console read"), so mpremote can reach the board while it runs.
Each frame the game paints into a list of recorded draw calls (gfx.Canvas); render.Dirty finds the rectangles that
changed since the last frame, and only those are drawn into one 51,200-byte RGB565 buffer and blitted. Nothing at module level touches hardware.
"""

import gc
import time

import buttons
import gdi
import pins
from arcade import Flappy, Runner, Snake
from arcade2 import Cave, GravityPong, Stack
from lcd import open_tft
from render import StOut
from space3d import CubeTiming, Starfire
from world3d import Road, Tunnel

FPS_EVERY_MS = 5000
FULL_FRAME_FREE = 400_000
GC_FLOOR = 1_000_000  # with PSRAM gc is off in the loop; below this much free heap it runs at once
# The bench decides the SPI clock. 80 MHz showed a dark screen on 2026-11-01 (the panel's write cycle limit is 16 ns,
# 62.5 MHz) and 40 MHz worked; 60 MHz is under the limit. If the picture breaks, go back to 40_000_000.
SPI_HZ = 60_000_000
# "auto" picks the whole-screen path when the heap is big (PSRAM), "bands" forces the small-buffer path, "full" the other.
# On a PSRAM build the whole heap is PSRAM, so try "bands" if the send time stays high.
FRAME_MODE = "auto"
# "s3lcd" is russhughes' C driver (smooth on the bench); "st7789" is our driver with dirty boxes. s3lcd falls back to
# st7789 when the image has no such module.
BACKEND = "s3lcd"
GAMES = (Flappy, Runner, Snake, Stack, Cave, Tunnel, Road, Starfire, CubeTiming, GravityPong)


class App:
    """Owns the display, the two buttons and the current game. frame() is one pass of the loop."""

    def __init__(self, display, read_fire, read_boot, games=GAMES, full=False, gc_floor=0, out=None):
        self.display, self.games = display, games
        self.fire = buttons.Button(read_fire, pins.ONBOARD_BUTTON_ON)
        self.boot = buttons.Button(read_boot, buttons.BOOT_BUTTON_ON)
        self.out = out or StOut(display, full)
        self.frames, self.mark, self.us, self.state, self.gc_floor = 0, 0, [0, 0, 0, 0], 0, gc_floor
        self.index = len(games) - 1
        self.game = None

    def start(self):
        self.out.clear()
        self.switch()

    def switch(self):
        """Move to the next game and say its name."""
        self.index = (self.index + 1) % len(self.games)
        self.game = None
        gc.collect()
        self.game = self.games[self.index]()
        self.out.reset()
        self.frames, self.mark, self.us = 0, time.ticks_ms(), [0, 0, 0, 0]
        print("game", self.game.name)

    def collect(self):
        """gc.collect(), timed. Called at quiet moments, so a pause lands where nobody is playing."""
        t = time.ticks_us()
        gc.collect()
        self.us[3] += time.ticks_diff(time.ticks_us(), t)

    def frame(self):
        us, t0 = self.us, time.ticks_us()
        now = time.ticks_ms()
        pressed, switched = self.fire.update(now), self.boot.update(now)
        if switched:
            self.switch()
        else:
            self.game.step(now, pressed, self.fire.held)
        game = self.game
        if game.state != self.state:  # the title and the game over are quiet: collect there
            self.state = game.state
            if self.gc_floor and self.state != 1:
                self.collect()
        us[0] += time.ticks_diff(time.ticks_us(), t0)
        self.out.draw(game, us)
        self.frames += 1
        if self.gc_floor and self.frames % 30 == 0 and gc.mem_free() < self.gc_floor:
            self.collect()
        elapsed = time.ticks_diff(now, self.mark)
        if elapsed >= FPS_EVERY_MS:  # the real rate, for a log or the console
            fps = self.frames * 1000 // elapsed
            print("fps", game.name, fps)
            n = 1000 * self.frames  # microseconds to milliseconds per frame
            print("time %s step %.1f paint %.1f send %.1f gc %.1f fps %d" % (
                game.name, us[0] / n, us[1] / n, us[2] / n, us[3] / n, fps))
            self.frames, self.mark, self.us = 0, now, [0, 0, 0, 0]


def open_st7789():
    """Our driver over machine.SPI: (display, full), where full says the heap is big enough for whole-screen buffers."""
    from machine import SPI, Pin

    from st7789 import ST7789

    Pin(gdi.SD_CS, Pin.OUT, value=1)
    Pin(gdi.BL, Pin.OUT, value=1)
    spi = SPI(1, baudrate=SPI_HZ, sck=Pin(gdi.SCLK), mosi=Pin(gdi.MOSI), miso=Pin(gdi.MISO))
    print("spi", spi)  # MicroPython's SPI prints the baudrate it set
    display = ST7789(spi, Pin(gdi.CS, Pin.OUT), Pin(gdi.DC, Pin.OUT), Pin(gdi.RST, Pin.OUT))
    display.init()
    gc.collect()
    free = gc.mem_free()
    print("mem", free)
    return display, FRAME_MODE == "full" or (FRAME_MODE == "auto" and free > FULL_FRAME_FREE)


def run():
    """The loop main.py starts."""
    import select
    import sys

    from machine import Pin

    out = open_tft(SPI_HZ) if BACKEND == "s3lcd" else None  # None: no s3lcd in this image
    display, full = None, False
    if out:
        gc.collect()
        print("backend s3lcd")
        print("mem", gc.mem_free())
        full = gc.mem_free() > FULL_FRAME_FREE  # only decides whether gc stays off in the loop
        print("frame tft")
    else:
        print("backend st7789")
        display, full = open_st7789()
        print("frame", "full" if full else "bands")
    app = App(display, Pin(pins.ONBOARD_BUTTON, Pin.IN, Pin.PULL_UP).value,
              Pin(buttons.BOOT_BUTTON, Pin.IN, Pin.PULL_UP).value, full=full and not out,
              gc_floor=GC_FLOOR if full else 0, out=out)
    if full:
        gc.disable()
    console = select.poll()
    console.register(sys.stdin, select.POLLIN)
    print("ready")
    app.start()
    while True:  # the s3lcd port may lose USB at init; the lines still print in case it stays
        app.frame()
        if console.poll(0):
            sys.stdin.read(1)
        time.sleep_ms(1)
