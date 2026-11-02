"""
The game box: ten one-button games on the GDI display. The BOOT button plays, the board's own button (D14) moves to
the next game from any state.

run() prints `ready` once the display is set up, then `game <name>` at the start and after each D14 press. Its loop
reads the console without waiting (commands/build.md, "The console read"), so mpremote can reach the board while it runs.
Each frame the game paints into a list of recorded draw calls (gfx.Canvas); render.Dirty finds the rectangles that
changed since the last frame, and only those are drawn into one 51,200-byte RGB565 buffer and blitted. Nothing at module level touches hardware.
"""

import gc
import time

import buttons
import gdi
import gfx
import pins
from arcade import Flappy, Runner, Snake
from arcade2 import Cave, GravityPong, Stack
from lcd import open_tft
from render import StOut
from space3d import CubeTiming, Starfire
from world3d import Road, Tunnel

FPS_EVERY_MS = 5000
FRAME_MS = 40  # each frame starts this long after the last, so objects move in equal steps; 0 = as fast as it goes. 110 while a send took 63 to 71 ms, 60 at 31 ms, 40 since partial show (P533 slice 5)
FULL_FRAME_FREE = 400_000
GC_FLOOR = 1_000_000  # with PSRAM gc is off in the loop; below this much free heap it runs at once
GC_FRAMES = 5  # with gc off, a timed collection every this many frames: small ones often, not one long pause over 8 MB
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
        self.fire = buttons.Button(read_fire, buttons.BOOT_BUTTON_ON)  # BOOT plays: holding it is safe once running
        self.boot = buttons.Button(read_boot, pins.ONBOARD_BUTTON_ON)  # D14 switches: a long hold powers the board off
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
        self.last, self.worst, self.slow = time.ticks_us(), 0, [0, 0, 0, 0, 0]  # the longest gap between two frame starts: a freeze shows here
        print("game", self.game.name)

    def collect(self):
        """gc.collect(), timed. Called at quiet moments, so a pause lands where nobody is playing."""
        t = time.ticks_us()
        gc.collect()
        self.us[3] += time.ticks_diff(time.ticks_us(), t)

    def frame(self):
        us, t0 = self.us, time.ticks_us()
        self.worst, self.last = max(self.worst, time.ticks_diff(t0, self.last)), t0
        before = us[:]
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
        took = time.ticks_diff(time.ticks_us(), t0)
        if took > self.slow[0]:  # the slowest frame of the interval, and where its time went
            self.slow = [took] + [a - b for a, b in zip(us, before)]
        if self.gc_floor and self.frames % GC_FRAMES == 0:  # no gc.mem_free(): it costs about 20 ms per MB allocated
            self.collect()
        elapsed = time.ticks_diff(now, self.mark)
        if elapsed >= FPS_EVERY_MS:  # the real rate, for a log or the console
            fps = self.frames * 1000 // elapsed
            print("fps", game.name, fps)
            n = 1000 * self.frames  # microseconds to milliseconds per frame
            print("time %s step %.1f paint %.1f send %.1f gc %.1f fps %d worst %d slowest %d = step %d paint %d send %d gc %d" % ((
                game.name, us[0] / n, us[1] / n, us[2] / n, us[3] / n, fps, self.worst // 1000)
                + tuple(x // 1000 for x in self.slow)))
            print("phases %s static %d paint %d fx %d hud %d over %d title %d" % ((game.name,) + tuple(x // 1000 for x in gfx.PHASES)))
            gfx.PHASES[:] = [0] * 6
            print("avg %s static %.1f paint %.1f fx %.1f hud %.1f over %.1f title %.1f" % ((game.name,) + tuple(x / n for x in gfx.PHASE_SUM)))
            gfx.PHASE_SUM[:] = [0] * 6
            # Once per interval: does the heap fill during play? (P533 run 16; gc.mem_alloc costs about 20 ms per MB)
            print("heap %s alloc %d glyphs %d" % (game.name, gc.mem_alloc(), len(gfx.GLYPHS)))
            self.frames, self.mark, self.us, self.worst, self.slow = 0, now, [0, 0, 0, 0], 0, [0, 0, 0, 0, 0]


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


def run(games=GAMES):
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
    # D14 also drives the power chip's PWRON (boards/firebeetle2-esp32s3.json, hardware_revisions, V1.1 and earlier):
    # held about 5 s, it powered the board off on 2026-11-02. So BOOT is the game button and D14 only a short press.
    fire, boot = Pin(buttons.BOOT_BUTTON, Pin.IN, Pin.PULL_UP), Pin(pins.ONBOARD_BUTTON, Pin.IN, Pin.PULL_UP)
    app = App(display, fire.value, boot.value, games=games, full=full and not out, gc_floor=GC_FLOOR if full else 0, out=out)
    app.fire.watch(fire)
    app.boot.watch(boot)
    if full:
        gc.disable()
    console = select.poll()
    console.register(sys.stdin, select.POLLIN)
    print("ready")
    app.start()
    due = time.ticks_ms()
    while True:  # the s3lcd port may lose USB at init; the lines still print in case it stays
        app.frame()
        if console.poll(0):
            sys.stdin.read(1)
        due = time.ticks_add(due, FRAME_MS)
        wait = time.ticks_diff(due, time.ticks_ms())
        if wait > 0:
            time.sleep_ms(wait)
        else:  # a slow frame: start again from now, never rush to catch up
            due = time.ticks_ms()
            time.sleep_ms(1)
