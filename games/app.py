"""
The game box: the marshmallow roast on the fire effect (P773, P595), the ball pit (P598), the bucket game on the C
engine's bodies (P773, once the rain demo of P593) and ten one-button games on the GDI display.
The BOOT button plays, the board's own button (D14) moves to the next game from any state.
The rotary encoder is the volume's knob (P764): each turn shows the volume over the game for 1 s (overlay.VolumePane).
The step is not saved. App(knob=None) has no volume pane.
The sound (P768): a game emits signals (signals.Signals), and SoundCues plays the game's cues on the Speaker's mixer.
main.py opens the Speaker. run() with no speaker is the silent box.

run() prints `ready` once the display is set up, then `game <name>` at the start and after each D14 press. Its loop
reads the console without waiting (commands/build.md, "The console read"), so mpremote can reach the board while it runs.
Each frame the game paints into a list of recorded draw calls (gfx.Canvas); render.Dirty finds the rectangles that
changed since the last frame, and only those are drawn into one 51,200-byte RGB565 buffer and blitted. Nothing at module level touches hardware.
"""

import gc
import time

import buttons
import encoder
import gdi
import gfx
import pins
from arcade import Flappy, Runner, Snake
from arcade2 import Cave, GravityPong, Stack
from balls import BallPit
from bank import Bank
from box_bank import BOX_BANK_INDEX
from bucket import Bucket
from cues import SoundCues
from fire import Fire  # noqa: F401  the probes and tools/crackle.sh start it as app.Fire
from lcd import open_tft
from marshmallow import Marshmallow
from meteors import Meteors
from overlay import Overlay, VolumePane
from render import StOut
from rescue import Rescue
from signals import Signals
from space3d import CubeTiming, Starfire
from speaker import Speaker
from volume import MasterVolume, VolumeKnob
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
GAMES = (Marshmallow, BallPit, Meteors, Bucket, Rescue, Flappy, Runner, Snake, Stack, Cave, Tunnel, Road, Starfire, CubeTiming, GravityPong)


class App:
    """Owns the display, the two buttons and the current game. frame() is one pass of the loop."""

    def __init__(self, display, read_fire, read_boot, games=GAMES, full=False, gc_floor=0, out=None, knob=None,
                 cues=None):
        self.display, self.games = display, games
        self.fire = buttons.Button(read_fire, buttons.BOOT_BUTTON_ON)  # BOOT plays: holding it is safe once running
        self.boot = buttons.Button(read_boot, pins.ONBOARD_BUTTON_ON)  # D14 switches: a long hold powers the board off
        self.out = out or StOut(display, full)
        self.frames, self.mark, self.us, self.state, self.gc_floor = 0, 0, [0, 0, 0, 0], 0, gc_floor
        self.index = len(games) - 1
        self.game = None
        self.overlay = Overlay()  # --- MVP (P762) --- system information over every game
        self.knob = knob  # --- MVP (P764) --- the volume's knob, or None: then the overlay has no volume pane
        self.volume_pane = self.overlay.add(VolumePane(knob.volume)) if knob else None
        self.signals = Signals()  # --- MVP (P768) --- what the game says happened
        self.cues = cues  # --- MVP (P768) --- a cues.SoundCues, or None: then the box is silent

    def start(self):
        self.out.clear()
        self.switch()

    def switch(self):
        """Move to the next game and say its name."""
        self.index = (self.index + 1) % len(self.games)
        self.game = None
        if self.cues:
            self.cues.stop()  # --- MVP (P768) --- before the next game's setup, so the last game's sound does not play over it
        gc.collect()
        self.game = self.games[self.index]()
        self.signals.clear()  # --- MVP (P768) --- the last game's listeners go
        self.game.signals = self.signals
        if self.cues:
            self.cues.follow(self.game, self.signals)
            self.cues.music()
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
        """One frame in its stages (P633), Unity's order plus Present: Input here; FixedUpdate, Update and LateUpdate in
        Game.step (the game's plugins and its play, only while it plays); Render and Present in out.draw."""
        us, t0 = self.us, time.ticks_us()
        self.worst, self.last = max(self.worst, time.ticks_diff(t0, self.last)), t0
        before = us[:]
        now = time.ticks_ms()
        pressed, switched = self.fire.update(now), self.boot.update(now)  # Input
        if self.knob:
            self.knob.poll(now)  # --- MVP (P764) ---
        if switched:
            self.switch()
        else:
            self.game.step(now, pressed, self.fire.held)  # FixedUpdate, Update, LateUpdate
        self.overlay.update(now)  # after the switch, so a turn shows in this frame and a pane sees this frame's game
        game = self.game
        if game.state != self.state:  # the title and the game over are quiet: collect there
            self.state = game.state
            if self.gc_floor and self.state != 1:
                self.collect()
        us[0] += time.ticks_diff(time.ticks_us(), t0)
        self.out.draw(game, us, self.overlay)  # Render, then Present: one show()
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


# --- MVP (P764) ---
def open_knob():
    """The rotary encoder as the volume's knob, or None when this image has no machine.Encoder.
    The step is not saved."""
    try:
        import machine

        machine.Encoder
    except (ImportError, AttributeError):
        return None
    try:  # the sound's callback applies the volume: the viper scale takes 116 us a block, the plain one 1220 us
        from volume_viper import ViperMasterVolume as Volume
    except (ImportError, AttributeError):
        Volume = MasterVolume
    return VolumeKnob(encoder.Encoder.on_board(pins.ENC_A, pins.ENC_B, encoder.EDGES_PER_DETENT), Volume())


# --- MVP (P768) ---
def open_speaker(knob=None):
    """The game box's Speaker, not yet open. The knob's volume is its master volume."""
    return Speaker(knob.volume if knob else None)


def run(games=GAMES, knob=None, speaker=None):
    """The loop main.py starts. knob: a caller's VolumeKnob (the probe's). With none, the box opens its own, so two
    encoders never share the counter unit. speaker: a Speaker that run() opens after the first game's setup, or None for the
    silent box (P768)."""
    import select
    import sys

    from machine import Pin

    encoder.take_pads(pins.ENC_A, pins.ENC_B)  # first: until here a turn of the knob can type into the console (P757)
    knob = knob or open_knob()  # --- MVP (P764) ---
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
    cues = None
    if speaker:  # --- MVP (P768) ---
        try:
            cues = SoundCues(speaker.mixer, Bank("box_bank.raw", BOX_BANK_INDEX))
        except (OSError, ValueError) as e:  # no bank on the board, or a short one: the silent box
            print("sound off:", repr(e))
            speaker = None
    app = App(display, fire.value, boot.value, games=games, full=full and not out, gc_floor=GC_FLOOR if full else 0, out=out, knob=knob,
              cues=cues)
    app.fire.watch(fire)
    app.boot.watch(boot)
    if full:
        gc.disable()
    console = select.poll()
    console.register(sys.stdin, select.POLLIN)
    print("ready")
    app.start()
    try:
        if speaker:  # after the first game's setup: a refill that waits behind it is late (run192: 14 at the open)
            try:
                speaker.open()
            except Exception as e:  # no I2S: the silent box
                print("sound off:", repr(e))
                speaker = None
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
    finally:
        if speaker:  # the amplifier off, also at Ctrl-C or an error
            speaker.close()
