"""
The game box: the marshmallow roast on the fire effect (P773, P595), the ball pit (P598), the bucket game on the C
engine's bodies (P773, once the rain demo of P593) and ten one-button games on the GDI display.
The box plays a lineup (P817): the ordered names of the games it holds, from the board's lineup.py (LINEUP), or every
game of catalog.CATALOG when the board has none. A game's module is imported only when the box builds that game, so
the boot imports no game. A game that fails to build (its module missing or of another build, a MemoryError in its
load) is refused aloud, and the box moves to the next one (P817, P823).
tools/box.py deploy writes lineup.py and copies every game's code but only the packs of the lineup's games; packs an
earlier deploy copied stay on the board.
The BOOT button plays. The board's own button (D14) picks the next game of the lineup from any state (P818): the last
game goes, a NameCard shows the picked name, and nothing is imported or loaded yet. The pick settles when no press came
for SETTLE_MS, or at a BOOT press (which then does not reach the game): only then is the game built. So pressing
through four games to the fifth loads only the fifth. The music plays on over a pick.
The build after a settle runs behind the card (P822): the settle's frame draws "loading", the next imports the game's
module (it cannot be split), and each later frame reads BUILD_CHUNKS chunks of its art set (Lineup.game_steps,
pictures.load_steps) while the card shows a bar, until the game plays. A D14 press during it stops it and picks the
next game; a BOOT press goes nowhere. start() and switch() still build at once.
The rotary encoder is the volume's knob (P764): each turn shows the volume over the game for 1 s (overlay.VolumePane).
The step is not saved. App(knob=None) has no volume pane.
The sound (P768): a game emits signals (signals.Signals), and SoundCues plays the game's cues on the Speaker's mixer.
main.py opens the Speaker. run() with no speaker is the silent box.

run() prints `lineup <n>: <names>` and `import <ms> ms` (how long this module's own imports took), then `ready` once
the display is set up, then `pick <name>` at each D14 press, and `game <name>` with
`switch <name> <ms> ms, load <ms> ms, import <ms> ms` at the start: how long the build took, the time the art's reads
took in it (P814) and the import of the game's module in it (P818). A build behind the card adds
`, frames <n>, worst <ms> ms, longest <ms> ms` (P822): its ms run from the settle to the game, frames are the card's
frames during the build, worst the longest gap between two frame starts, and longest the build's longest share of
one frame (the import or the setup shows there). Its loop
reads the console without waiting (commands/build.md, "The console read"), so mpremote can reach the board while it runs.
Each frame the game paints into a list of recorded draw calls (gfx.Canvas); render.Dirty finds the rectangles that
changed since the last frame, and only those are drawn into one 51,200-byte RGB565 buffer and blitted. Nothing at module level touches hardware.
"""

import gc
import time

STARTED = time.ticks_ms() if hasattr(time, "ticks_ms") else 0  # for run()'s import line; CPython has no ticks (P817)

import buttons
import encoder
import gdi
import gfx
import pictures
import pins
from bank import Bank
from box_bank import BOX_BANK_INDEX
from catalog import NAMES, ROWS, lineup_fault
from cues import SoundCues
from lcd import open_tft
from overlay import Overlay, VolumePane
from render import StOut
from signals import Signals
from speaker import Speaker
from volume import MasterVolume, VolumeKnob

IMPORT_MS = pictures.since(STARTED)  # this module's imports: no game's module is among them (P817)

FPS_EVERY_MS = 5000
FRAME_MS = 40  # each frame starts this long after the last, so objects move in equal steps; 0 = as fast as it goes. 110 while a send took 63 to 71 ms, 60 at 31 ms, 40 since partial show (P533 slice 5)
FULL_FRAME_FREE = 400_000
GC_FLOOR = 1_000_000  # with PSRAM gc is off in the loop; below this much free heap it runs at once
BUILD_CHUNKS = 3  # the chunks (pictures.CHUNK_SIZE each) a frame reads during a build behind the card (P822): about 20 ms of 40.
# A measured value: 2 when the switch line's worst passes a card frame's baseline worst by over 2 ms or its longest
# passes 22 ms on a revisit (import 0 ms); 4 when both keep over 10 ms to spare
SETTLE_MS = 700  # a pick builds its game once no D14 press came for this long; the one feel value: the PO's play decides (P818)
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


# --- MVP (P817) ---
def games_for(names):
    """The game classes for names, in their order, each one's module imported only now. An unknown name raises
    ValueError naming it."""
    classes = []
    for name in names:
        if name not in ROWS:
            raise ValueError("no game %s in the catalog" % name)
        classes.append(getattr(__import__(ROWS[name][1]), ROWS[name][2]))
    return tuple(classes)


class Lineup:
    """The games the box plays, in order: their names, and game(i), which builds the i-th, importing its module only
    then, or game_steps(i), which builds it in steps (P822). Lineup.of(classes) is one of classes already imported (a
    test's or a probe's)."""

    def __init__(self, names, classes=None):
        self.names, self.classes = tuple(names), classes

    @classmethod
    def of(cls, classes):
        return cls([c.name for c in classes], tuple(classes))

    def __len__(self):
        return len(self.names)

    import_ms = 0  # how long the last game_steps(i) took to import its module (P818)

    def game(self, i):
        """The i-th game, built at once: game_steps(i) run to its end."""
        steps = self.game_steps(i)
        while True:
            try:
                next(steps)
            except StopIteration as built:
                return built.value

    def game_steps(self, i):
        """The i-th game's build in steps (P822), a generator: its first step imports the game's module (timed into
        import_ms, 0 for classes; an import cannot yield), then a step per chunk of its art set (pictures.load_steps of
        its ART), each yielding the load's progress 0 to 1, then it returns the game, built: its setup finds its set
        loaded and reads nothing. A game with no ART yields nothing."""
        start = time.ticks_ms()
        c = self.classes[i] if self.classes is not None else games_for((self.names[i],))[0]
        self.import_ms = time.ticks_diff(time.ticks_ms(), start)
        art = getattr(c, "ART", None)  # a probe's or a test's class may be no gfx.Game
        if art:
            yield from pictures.load_steps(*art)
        return c()


def read_lineup():
    """The names the box plays: LINEUP of the board's lineup.py, or every game of the catalog when there is none. A
    lineup.py that fails (it raises, has no LINEUP, or lineup_fault refuses it) prints `lineup refused: <why>` and
    the box plays every game, so it never stays dark."""
    try:
        import lineup
    except ImportError:
        return NAMES
    except Exception as e:  # a syntax error, or one the file raised
        return refuse_lineup(repr(e))
    why = lineup_fault(getattr(lineup, "LINEUP", None))
    return refuse_lineup(why) if why else lineup.LINEUP


def refuse_lineup(why):
    print("lineup refused:", why)
    return NAMES


def say_lineup(games):
    """The lines run() prints before `ready`: the lineup the box plays, and how long this module's imports took."""
    print("lineup %d: %s" % (len(games), " ".join(games.names)))
    print("import %d ms" % IMPORT_MS)
# --- MVP ---


class App:
    """Owns the display, the two buttons and the current game. frame() is one pass of the loop."""

    steps = None  # --- MVP (P822) --- the build behind the card (Lineup.game_steps) from a settle until its game plays

    def __init__(self, display, read_fire, read_boot, games, full=False, gc_floor=0, out=None, knob=None,
                 cues=None):
        self.display = display
        self.games = games if isinstance(games, Lineup) else Lineup.of(games)  # a Lineup, or a tuple of classes
        self.fire = buttons.Button(read_fire, buttons.BOOT_BUTTON_ON)  # BOOT plays: holding it is safe once running
        self.boot = buttons.Button(read_boot, pins.ONBOARD_BUTTON_ON)  # D14 picks: a long hold powers the board off
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
        """Move to the next game and build it at once (start() and the probes)."""
        self.index = (self.index + 1) % len(self.games)
        self.build()

    def leave(self):
        """The current game goes, or the build behind the card stops: its art set, its sounds and its listeners. The music
        plays on."""
        if self.steps is not None:  # --- MVP (P822) --- a build stopped (a pick, switch() or build()): its pack file closes
            self.steps.close()
            self.steps = None
        self.game = None
        pictures.free()  # the last game's art set goes: the next game loads its own (P773)
        if self.cues:
            self.cues.stop()  # --- MVP (P768) --- before the next game's setup, so the last game's sound does not play over it
        self.signals.clear()  # --- MVP (P768) --- the last game's listeners go

    # --- MVP (P818) ---
    def pick(self, now):
        """A D14 press: the next name of the lineup, on a NameCard. The game goes, and nothing is imported or loaded:
        the picked game is built when the pick settles (frame())."""
        self.index = (self.index + 1) % len(self.games)
        self.leave()
        self.game = NameCard(self.games.names[self.index], self.index + 1, len(self.games), now)
        self.out.reset()
        self.new_interval()  # the fps and time lines never name a card
        print("pick", self.game.name)

    def build(self):
        """Build the game at index at once (start() and switch()) and say its name, then how long the build took, its
        art's load and its module's import in it (P814, P818)."""
        start = time.ticks_ms()
        self.leave()
        gc.collect()
        self.play(self.new_game())
        print("switch %s %d ms, load %d ms, import %d ms" % (self.game.name, time.ticks_diff(self.mark, start),
                                                            pictures.load_ms, self.games.import_ms))

    def play(self, game):
        """The built game plays: its signals, cues and music, a clean output, a new interval, and no press from
        before; then its name."""
        self.game = game
        game.signals = self.signals
        if self.cues:
            self.cues.follow(game, self.signals)
            self.cues.music()
        self.out.reset()
        self.new_interval()
        self.fire.forget()  # --- MVP (P818) --- a press during the import and the load was for the frozen screen
        self.boot.forget()
        print("game", game.name)

    # --- MVP (P822) ---
    def settle(self):
        """The pick settled: its build starts behind the card. Nothing is imported in this frame, so the card is drawn
        saying "loading" before the import freezes the next one."""
        gc.collect()
        self.settled_at, self.failures, self.longest = time.ticks_ms(), 0, 0
        self.steps = self.games.game_steps(self.index)
        self.game.stage = NameCard.LOADING

    def build_step(self):
        """BUILD_CHUNKS steps of the build behind the card; the card shows the progress. When the steps end, the game
        plays and the switch line says the build's frames, worst and longest. Answers whether the game plays."""
        t, k, game = time.ticks_us(), 0, None
        try:
            while k < BUILD_CHUNKS:
                self.game.stage = next(self.steps)
                k += 1
        except StopIteration as built:
            game = built.value
        except Exception as e:  # refused as new_game refuses: the next game goes on the card, built from next frame
            self.steps = None
            self.failures += 1
            self.refuse(e)
            if self.failures >= len(self.games):
                raise e
            self.game = NameCard(self.games.names[self.index], self.index + 1, len(self.games), self.game.at)
            self.game.stage = NameCard.LOADING
            self.steps = self.games.game_steps(self.index)
        self.longest = max(self.longest, time.ticks_diff(time.ticks_us(), t))
        if game is None:
            return False
        self.steps = None
        frames, worst = self.frames, self.worst  # the build's, before play() starts the game's interval
        self.play(game)
        print("switch %s %d ms, load %d ms, import %d ms, frames %d, worst %d ms, longest %d ms" % (
            game.name, time.ticks_diff(self.mark, self.settled_at), pictures.load_ms, self.games.import_ms, frames,
            worst // 1000, self.longest // 1000))
        return True

    def new_interval(self):
        """The fps and time lines count from now."""
        self.frames, self.mark, self.us = 0, time.ticks_ms(), [0, 0, 0, 0]
        self.last, self.worst, self.slow = time.ticks_us(), 0, [0, 0, 0, 0, 0]  # the longest gap between two frame starts: a freeze shows here

    def new_game(self):
        """The game at index, built. One that fails, in its import (a module a copy by hand left out, an .mpy of
        another build, a wrong class name) or in its setup (a MemoryError in its load), is refused aloud, its memory
        goes, and the next one is built; when every game fails, the last error is raised (P817, P823). Ctrl-C still
        stops the box: KeyboardInterrupt is no Exception."""
        for _ in range(len(self.games)):
            try:
                return self.games.game(self.index)
            except Exception as e:
                error = e
                self.refuse(e)
        raise error

    def refuse(self, e):
        """The game at index failed to build: said aloud, its memory gone, and the index on the next game."""
        pictures.free()  # a half-loaded set goes
        gc.collect()  # and the half-built game (run() may have turned the collector off), before the line
        print("game %s refused: %r" % (self.games.names[self.index], e))  # is built on a heap with room
        self.index = (self.index + 1) % len(self.games)

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
        pressed, switched = self.fire.update(now), self.boot.update(now) and len(self.games) > 1  # Input; one game: no pick
        if self.knob:
            self.knob.poll(now)  # --- MVP (P764) ---
        settled = self.steps is None and isinstance(self.game, NameCard) and (
            pressed or time.ticks_diff(now, self.game.at) >= SETTLE_MS)  # a card during its build never settles again
        built = False
        if switched:
            self.pick(now)  # --- MVP (P818) ---
        elif settled:
            self.settle()  # a BOOT press that settles a pick is used up here (P822: the build runs in later frames)
        elif self.steps is not None:
            built = self.build_step()  # --- MVP (P822) --- in place of the game's step; a BOOT press goes nowhere
        else:
            self.game.step(now, pressed, self.fire.held)  # FixedUpdate, Update, LateUpdate
        if switched or settled or built:  # the new interval's stages: a build's time is not this frame's
            us, t0, before = self.us, time.ticks_us(), self.us[:]
        self.overlay.update(now)  # after the switch, so a turn shows in this frame and a pane sees this frame's game
        game = self.game
        if game.state != self.state:  # the title and the game over are quiet: collect there
            self.state = game.state
            if self.gc_floor and self.state != 1 and not isinstance(game, NameCard):  # build() collects after a card
                self.collect()
        us[0] += time.ticks_diff(time.ticks_us(), t0)
        self.out.draw(game, us, self.overlay)  # Render, then Present: one show()
        self.frames += 1
        took = time.ticks_diff(time.ticks_us(), t0)
        if took > self.slow[0]:  # the slowest frame of the interval, and where its time went
            self.slow = [took] + [a - b for a, b in zip(us, before)]
        if self.steps is not None:  # --- MVP (P822) --- a build behind the card: no timed collect and no fps lines,
            if settled:  # and its frames and worst count from the end of the settle's frame
                self.new_interval()
            return
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


# --- MVP (P818) ---
class NameCard(gfx.Game):
    """The picked game's name from the pick until the game plays: the name big in the middle, "n / N" under it, and
    under that its stage (P822): "BOOT loads" while the pick waits to settle, "loading" during the import, then a bar
    of the load's progress, on the plain background. It stays in TITLE, loads nothing and has no cues. at: the pick's
    time.ticks_ms(), from which the pick settles."""

    WAITING, LOADING = "BOOT loads", "loading"  # --- MVP (P822) --- the stages it says: waiting to settle, the import
    BAR_W, BAR_H = 160, 8  # the progress bar's outline: only its fill changes between two frames

    def __init__(self, name, n, count, at=0):
        self.name, self.n, self.count, self.at, self.stage = name, n, count, at, self.WAITING
        self.place = "%d / %d" % (n, count)  # made once: the card's frames format nothing
        super().__init__()

    def step(self, now_ms, pressed, held):
        pass  # never leaves TITLE: the box builds the game instead

    def draw_title(self, cv):
        cx, cy = gfx.WIDTH // 2, gfx.HEIGHT // 2
        cv.big(self.name, cx - 12 * len(self.name), cy - 30, gfx.WHITE, 3)
        cv.big(self.place, cx - 8 * len(self.place), cy + 6, gfx.GREY, 2)
        if isinstance(self.stage, str):
            cv.text(self.stage, cx - 4 * len(self.stage), cy + 34, gfx.YELLOW)
            return
        x, y = cx - self.BAR_W // 2, cy + 34  # a progress 0 to 1: the bar
        cv.box(x, y, self.BAR_W, self.BAR_H, gfx.GREY)
        cv.fill(x + 1, y + 1, int((self.BAR_W - 2) * self.stage), self.BAR_H - 2, gfx.YELLOW)


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


def run(games=None, knob=None, speaker=None):
    """The loop main.py starts. games: a Lineup, a tuple of classes (a probe's), or None for the board's lineup
    (read_lineup). knob: a caller's VolumeKnob (the probe's). With none, the box opens its own, so two
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
    app = App(display, fire.value, boot.value, games=Lineup(read_lineup()) if games is None else games, full=full and not out, gc_floor=GC_FLOOR if full else 0, out=out, knob=knob,
              cues=cues)
    say_lineup(app.games)  # --- MVP (P817) ---
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
