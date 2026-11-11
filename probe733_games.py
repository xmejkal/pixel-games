"""
P733 steps 2 and 3, P746, P748, P747 and P757: a sound beside the game loop, fed by a driver of games/sound.py through
stock machine.I2S, and heard by a microphone.

    mpremote cp games/sound.py :sound.py
    mpremote cp games/volume.py :volume.py + cp games/volume_viper.py :volume_viper.py   # for a run with VOLUME (P757)
    mpremote cp games/encoder.py :encoder.py + cp games/pins.py :pins.py                 # for a run with KNOB (P757)
    mpremote run probe733_games.py      # after sed set GAME, TONE, MIC, HITS, REFILL, IBUF, VOICE, VOLUME, LEVEL,
                                        # KNOB, SAVE and SECONDS

tools/crackle.sh runs it with a crackle (P747): it builds crackle_c.mpy and copies it and games/crackle.py first.

It changes no file in games/. It replaces App.frame with a hook that runs after each frame: the per-frame refill, the
microphone's read, the 5 s report, a switch to a new copy of the game every 30 s (the heavy frame of D19, none with
HITS), and a press of BOOT on the game-over screen, so the game plays most of the time. TONE = 0 is the control run:
the same game and presses, with no I2S.

REFILL picks the driver by its class name (P748). FrameRefill refills once per frame, after a poll that makes the
writes return at once. CallbackRefill refills from the stock I2S.irq callback, about every 16 ms. IBUF sets the ring:
2048 bytes are 4 DMA buffers of 256 samples, 64 ms (machine_i2s.c:152). A refill later than the ring minus one buffer
can find the ring empty: that is a `late` count. `short` is the samples the clock expected minus the samples written.
It moves by up to one ring with no break, so only a larger rise means that the speaker played silence.

Lines every 5 s: `sound <game> sent <n> of <expected> between_max <ms> lag_max <ms> late <n> short <samples> pushes
<n>`. `sent` counts the blocks of 256 samples written since the last line (since the open, in the first line), and
`expected` is one per 16 ms. `lag_max` is between_max minus one buffer: how long the handler waited. A `late` refill
has a lag over the ring minus two buffers. `pushes` counts the raw BOOT interrupts since the start. The callback chain
has no restart: a lost schedule stops it, and the probe prints `stall <ms> pushes <n>` once. Also `switch <n> <ms>`, `align <n>` at open (the block's address modulo 16, which must be 0, D27), and at the end `written <samples>
short <samples>`, then `done`. The App prints its own fps and time lines.

With MIC = 1 (D18, D22) the microphone on the second controller hears the speaker. It opens on the first frame, and the
sound opens 2.5 s later, so the run measures the room first. Lines: `mic dma_free <B> largest <B>` before it opens,
`gap <ms since the microphone opened> <length ms>`, and `mic <game> gaps <n> open <ms> lost <samples> blind <n>
tone_mean <n> floor <n>` every 5 s and at the end. `open` is the length of a gap that has not ended yet, so a dead
callback shows.

HITS = "auto" or "press" (with MIC = 1, P746): silence instead of the tone, and a 60 ms beep at each hit, a game
event. The beep waits behind the ring. An onset is the first of 3 loud blocks in a row after a quiet block. Lines:
`hit <n> seen <ms> delay <ms> total <ms> between <ms> loud <n>`: push to frame, frame to beep, push to beep (seen and
total are -1 for an auto hit), the refill gap before the refill that took the beep, and the loudest block in the
window. Also `hit <n> missed loud <n>`, `skip <n>` for a hit while the last one waits, and at the end `hits <n> median
<ms> max <ms> missed <n> total_median <ms>`. No game restarts in these runs.

VOICE (P747) is what the driver renders: "tone", "silent" (a Mixer with no play: the control run of the I2S), or
"Crackle", "NativeCrackle", "SampledCrackle", "GrainCrackle" (P751) or "FireSound" (P753), a class name in crackle. A
crackle gets the Fire field's embers through fire.FirePlugin.crackle, one pop per birth. Lines: `first pop <ms>` (from the open to the first render that starts a
pop) once, and every 5 s `crackle <game> render_max <us> pop_median <ms> pop_max <ms> pops <n> dropped <n>`.
`pop` is the delay from add_pops to the start of the render that starts that pop, one per pop. The pop itself starts 1 to 128
samples into that render, and the ring holds it for up to 64 ms (IBUF 2048) before the speaker.
FireSound (P753) plays the pops, and with GAME BurningBodies one whoosh per body by its airspeed. Its noise bed, which
follows the heat field, is off (crackle.BED), so Fire plays the pops alone. TimedCrackle forwards follow_field (only with
the bed on) and follow_bodies to it and counts the calls, and adds a line to every 5 s line,
`follow <game> follow_field <n> follow_bodies <n> level <n> coef <n> whoosh <n>`: the calls of the window, the bed's
targets now and the loudest whoosh's level now.

VOLUME (P757) is the master volume's class name: "MasterVolume" (in volume, the naive path), "ViperMasterVolume" (in
volume_viper), or "" for the mix as it is: then the probe imports neither. LEVEL is its start step, 0 (silent) to 16
(the mix as it is), or None for the saved step (with SAVE), else volume.DEFAULT_STEP. It is LEVEL because a step in
this probe is a bench step.
One more line every 5 s: `volume level <n> gain <n> apply_max <us>`: the step, the gain that the last block ended at
(32768 is the mix as it is), and the longest apply of the window. With ViperMasterVolume, the first line is `scale
match <1 or 0>`: 1 when the viper scale gave the naive scale's samples on the named blocks of volume_viper.
With KNOB = 1 (and a VOLUME) the rotary encoder on pins.ENC_A and pins.ENC_B turns the step, 1 step per detent, read
once per frame. Lines: `level <n> edges <n>` at each change of the step, and `edges <n> windows_max <n>` at the end of
the 5 s volume line: the most windows that one show() of the window sent (P762). Each change of the step also shows
the volume on the screen for 1 s (games/overlay.py, P762).
With SAVE = 1 (and a VOLUME) the step lives in volume.txt on the board. A line at the start is
`stored level <n or None>`, the file's step, when LEVEL is None. With KNOB, the knob saves the step 3 s after its last
change, and the 5 s volume line ends with `saves <n> save_max <ms> save_errors <n>`: the saves and the failed saves of
the run, and the longest save of the window. With SAVE = 0 the probe reads and writes no file, so an old volume.txt
never changes a measured run.
SAVE_EVERY_MS (with SAVE and KNOB) is the stress run: a save at this period, whatever the knob does.
"""

import math
import time
from array import array

import micropython
import sound
import uctypes
from micropython import const
from machine import I2S, Pin

GAME = "Fire"  # Fire, BallPit, Road or BurningBodies: a name in app
TONE = 1  # 0: the control run, no I2S
MIC = 0  # 1: the microphone counts the gaps (step 3), or measures the delays (HITS)
HITS = 0  # "auto": a hit every 2 s from 4 s on, "press": a hit at each BOOT press, 0: the tone (P746)
REFILL = "FrameRefill"  # or "CallbackRefill": a driver's class name in sound (P748)
IBUF = 4096  # TX DMA bytes: 8 buffers of 256 samples, a ring of 128 ms; 2048 gives 4 buffers, 64 ms
VOICE = "tone"  # "silent", "Crackle", "NativeCrackle", "SampledCrackle", "GrainCrackle" or "FireSound" (P747, P751, P753)
VOLUME = ""  # "MasterVolume" or "ViperMasterVolume": the master volume's class; "": the mix as it is (P757)
LEVEL = None  # the volume's start step, 0 to 16; None: the saved step (with SAVE), else volume.DEFAULT_STEP
KNOB = 0  # 1: the rotary encoder turns the volume's step (P757)
SAVE = 0  # 1: the volume's step is read from volume.txt, and the knob saves it there (P757)
SAVE_EVERY_MS = 0  # the stress run of the save: a save at this period (P757)
SECONDS = 120
SWITCH_MS = 30_000
REPORT_MS = 5000
RATE = sound.RATE
RING = IBUF // 2  # samples in the TX DMA buffers
RING_MS = RING // (RATE // 1000)
BUFFER_MS = sound.REFILL_SAMPLES // (RATE // 1000)  # 16
CYCLE = 400  # exactly 11 cycles of 440 Hz at 16 kHz, so the looping tone has no seam
AMPLITUDE = 6000  # of 32767: the PO finds 10000 annoying, and 3000 read 351 against a room of 268 (entry 3c)
BEEP = 6000  # a beep's amplitude: 20000 was "really annoying" (the PO); the 24-bit microphone hears 6000 well over the room
FADE = 80  # samples of fade in and out, 5 ms, so a beep does not click
BEEP_SAMPLES = 960  # 60 ms
HIT_EVERY_MS = 2000
HIT_FROM_MS = 4000  # after the sound opens (2.5 s) and the microphone's floor is set
ONSET_MS = 2 * RING_MS + 200  # a hit with no beep heard in this time is missed: the beep waits up to one ring
ONSET_BLOCKS = 3  # loud blocks in a row that make an onset


# --- MVP ---
class Done(Exception):
    """Raised in the hook to end app.run(): at SECONDS, or when the microphone hears no tone."""


MIC_BLOCK = const(64)  # samples per block mean, 1 << MIC_BLOCK_SHIFT: 4 ms, so any gap of 8 ms or more holds one whole quiet block
MIC_BLOCK_SHIFT = const(6)
MIC_BYTES = 4  # a 32-bit read keeps all 24 bits of the INMP441; a 16-bit read kept the top 16, 256 times coarser (run144i)
TONE_OPEN_MS = 2500  # the sound opens this long after the microphone
FLOOR_MS = (1500, 2500)  # the room, after the microphone settles (about 1.3 s, run141), before the sound opens
TONE_MS = (3000, 4000)  # the tone: it starts one ring after it opens, after a frame and the click
# Levels are 24-bit block means. run144i: the tone at 10000 about 2840, the room 250 to 700. The 16-bit reads gave
# the same divided by 256: the tone 6 to 21, beeps 25 to 33, claps up to 11.
TONE_MIN = 500  # keeps a dead line out: with a floor of 0, 0 passed 4 x floor. The tone read 351 at 3000, 901 to 976 at 6000
BEEP_MIN = 700  # the onset threshold with HITS, about 2.5 x the room (262 to 268). A beep at 6000 read 568 to 1243 in
# entry 5b, where 1200 missed 52 of 72 hits. 700 is not tested on the bench. A clap (about 2800) also passes
QUIET = 0.3 # a block is quiet below floor + QUIET x (tone_mean - floor)
BLIND_US = 13 * 16_000  # a wait of 13 or more DMA buffers: ESP-IDF can skip or drop buffers without a report


@micropython.viper
def block_mean(buf, offset: int) -> int:
    """The mean |x - m| of MIC_BLOCK 24-bit samples from offset (in samples), with m their mean, so the microphone's
    constant offset does not count as sound (run141f). Each 32-bit word holds the sample in its top 24 bits, and the
    arithmetic shift keeps the sign. 64 sums of 24 bits fit in a 32-bit int."""
    p = ptr32(buf)  # noqa: F821, a viper built-in
    s = 0
    i = offset
    end = offset + MIC_BLOCK
    while i < end:
        s += int(p[i]) >> 8
        i += 1
    m = s >> MIC_BLOCK_SHIFT
    s = 0
    i = offset
    while i < end:
        x = (int(p[i]) >> 8) - m
        if x < 0:
            x = 0 - x
        s += x
        i += 1
    return s >> MIC_BLOCK_SHIFT


def median(values):
    values = sorted(values)
    return values[len(values) // 2] if values else 0


class Mic:
    """The microphone on the second controller: it reads all that is ready each frame, without waiting, and counts
    the runs of quiet blocks while the tone plays. Its time is the count of samples received."""

    def __init__(self):
        import esp32
        import select

        heaps = esp32.idf_heap_info(8)  # MALLOC_CAP_DMA: the 32 KB come from here, not from the PSRAM heap
        print("mic dma_free %d largest %d" % (sum(h[1] for h in heaps), max(h[2] for h in heaps)))
        self.buf = bytearray(16384)  # before the I2S, so the clock below starts with the DMA
        self.i2s = I2S(1, sck=Pin(8), ws=Pin(11), sd=Pin(10), mode=I2S.RX, bits=32, format=I2S.MONO, rate=RATE,
                       ibuf=32768)
        self.opened_us = time.ticks_us()  # the sample clock starts here (run143d: 0 to 192 samples behind)
        try:
            self.poll = select.poll()
            self.poll.register(self.i2s, select.POLLIN)
            self.poll.poll(0)  # a poll switches the I2S to reads that return at once (extmod/machine_i2s.c:621)
        except Exception:
            self.i2s.deinit()
            raise
        self.view = memoryview(self.buf)
        self.fill = self.samples = self.gaps = self.blind = 0
        self.last = self.opened_us
        self.floors, self.tones, self.threshold, self.quiet_from = [], [], None, None
        self.floor = self.tone_mean = 0
        self.refill = None  # set when the sound opens: the hit line reads its play_between
        self.hits, self.delays, self.totals, self.missed, self.pending = 0, [], [], 0, None
        self.seen = self.loud = self.run = self.run_from = 0
        self.quiet = self.rising = False

    def read(self):
        now = time.ticks_us()
        if time.ticks_diff(now, self.last) >= BLIND_US:
            self.blind += 1
        self.last = now
        while True:
            n = self.i2s.readinto(self.view[self.fill:])
            if not n:
                return
            self.fill += n
            whole = self.fill // (MIC_BYTES * MIC_BLOCK)
            for k in range(whole):
                self.add_mean(block_mean(self.buf, k * MIC_BLOCK))
            rest = self.fill - whole * MIC_BYTES * MIC_BLOCK
            self.buf[:rest] = self.buf[whole * MIC_BYTES * MIC_BLOCK:self.fill]
            self.fill = rest

    def now_ms(self):
        return self.samples // (RATE // 1000)  # no long int

    def add_mean(self, mean):
        t = self.now_ms()
        self.samples += MIC_BLOCK
        if not TONE:  # the control run: the microphone's cost, with no tone to calibrate on
            return
        if self.threshold is None:
            if FLOOR_MS[0] <= t < FLOOR_MS[1]:
                self.floors.append(mean)
            elif TONE_MS[0] <= t < TONE_MS[1]:
                self.tones.append(mean)
            elif t >= (FLOOR_MS[1] if HITS else TONE_MS[1]):
                self.calibrate()
            return
        if HITS:
            self.onset(t, mean)
            return
        if mean < self.threshold:
            if self.quiet_from is None:
                self.quiet_from = t
        elif self.quiet_from is not None:
            self.gaps += 1
            print("gap %d %d" % (self.quiet_from, t - self.quiet_from))
            self.quiet_from = None

    def open_gap(self):
        """The length of a gap that has not ended yet, or 0."""
        return 0 if self.quiet_from is None else self.now_ms() - self.quiet_from

    def hit(self, at_us, seen):
        """A hit at at_us (ticks_us): its time in the microphone's sample clock, in ms. seen is push to frame, or -1."""
        self.hits += 1
        self.pending, self.seen, self.loud = time.ticks_diff(at_us, self.opened_us) // 1000, seen, 0

    def onset(self, t, mean):
        """A beep's onset is the first of ONSET_BLOCKS loud blocks in a row after a quiet block (a rising edge), at or
        after the pending hit's time. The loudest block in the window goes into the hit line."""
        if mean < self.threshold:
            self.run, self.quiet = 0, True
        else:
            if not self.run:
                self.run_from, self.rising = t, self.quiet
            self.run += 1
            self.quiet = False
        if self.pending is None or t < self.pending:
            return
        self.loud = max(self.loud, mean)
        if self.run == ONSET_BLOCKS and self.rising and self.run_from >= self.pending:
            delay = self.run_from - self.pending
            total = delay + self.seen if self.seen >= 0 else -1
            self.delays.append(delay)
            if total >= 0:
                self.totals.append(total)
            print("hit %d seen %d delay %d total %d between %d loud %d" % (
                self.hits, self.seen, delay, total, self.refill.play_between // 1000, self.loud))
            self.pending = None
        elif t - self.pending > ONSET_MS:
            self.missed += 1
            print("hit %d missed loud %d" % (self.hits, self.loud))
            self.pending = None

    def calibrate(self):
        if HITS:
            self.floor = median(self.floors)
            self.threshold = max(4 * self.floor, BEEP_MIN)
            return
        self.floor, self.tone_mean = median(self.floors), median(self.tones)
        if self.tone_mean < 3 * self.floor or self.tone_mean < TONE_MIN:
            print("mic slot empty tone_mean %d floor %d" % (self.tone_mean, self.floor))
            raise Done
        self.threshold = self.floor + QUIET * (self.tone_mean - self.floor)

    def lost(self):
        return time.ticks_diff(time.ticks_us(), self.opened_us) // 1000 * (RATE // 1000) - self.samples - self.fill // MIC_BYTES

    def report(self, name):
        print("mic %s gaps %d open %d lost %d blind %d tone_mean %d floor %d" % (
            name, self.gaps, self.open_gap(), self.lost(), self.blind, self.tone_mean, self.floor))

    def close(self):
        self.i2s.deinit()


class TimedCrackle:
    """A crackle with the probe's clocks (P747): add_pops stamps each new pop's time, render times itself and takes
    the stamps that its started count passes. The stamp goes in before the pops, so a render between the two never
    passes a pop with no stamp."""

    pending = None

    def __init__(self, crackle):
        self.crackle, self.stamps, self.pops_us = crackle, [], []
        self.takes_rises = getattr(crackle, "takes_rises", False)  # P751
        # --- MVP (P753) --- follow_field and follow_bodies exist only when the inner crackle has them, so FirePlugin's
        # hasattr sees what it would on the crackle itself
        self.field_calls = self.bodies_calls = 0
        if hasattr(crackle, "follow_field") and getattr(crackle, "has_bed", True):
            self.follow_field = self.forward_field
        if hasattr(crackle, "follow_bodies"):
            self.follow_bodies = self.forward_bodies
        self.render_max = self.renders = 0
        self.first = None  # ticks_us of the first render that started a pop

    def add_pops(self, n, rises=None):
        if n:
            popped, t = self.crackle.counts()[0], time.ticks_us()
            for k in range(1, n + 1):
                self.stamps.append((popped + k, t))  # one stamp per pop, so `pops` counts pops
            if rises is None:
                self.crackle.add_pops(n)
            else:
                self.crackle.add_pops(n, rises)

    def forward_field(self, total, height, wind):
        self.field_calls += 1
        self.crackle.follow_field(total, height, wind)

    def forward_bodies(self, moves, ms, wind):
        self.bodies_calls += 1
        self.crackle.follow_bodies(moves, ms, wind)

    def render(self, buf):
        t = time.ticks_us()
        self.crackle.render(buf)
        self.render_max = max(self.render_max, time.ticks_diff(time.ticks_us(), t))
        _, started, dropped = self.crackle.counts()
        while self.stamps and self.stamps[0][0] <= started + dropped:
            self.pops_us.append(time.ticks_diff(t, self.stamps.pop(0)[1]))
            if self.first is None:
                self.first = t

    def report(self, name):
        """The 5 s line, then a new window. A render between a read and its reset here can lose one render_max."""
        pops, self.pops_us = self.pops_us, []
        render_max, self.render_max = self.render_max, 0
        print("crackle %s render_max %d pop_median %d pop_max %d pops %d dropped %d" % (
            name, render_max, median(pops) // 1000, max(pops or [0]) // 1000, len(pops), self.crackle.counts()[2]))
        if hasattr(self.crackle, "follow_field") or hasattr(self.crackle, "follow_bodies"):  # P753
            print("follow %s follow_field %d follow_bodies %d level %d coef %d whoosh %d" % (
                name, self.field_calls, self.bodies_calls, getattr(self.crackle, "bed_level", 0),
                getattr(self.crackle, "bed_coef", 0), getattr(self.crackle, "whoosh_level", 0)))
            self.field_calls = self.bodies_calls = 0


class TimedVolume:
    """A master volume with the probe's clock (P757): apply times itself. --- MVP (P757) ---"""

    knob = None  # the probe's VolumeKnob, with KNOB
    view, windows_max = None, 0  # with KNOB (P762): the overlay's VolumeView, and the most windows of one show()

    def __init__(self, volume):
        self.volume, self.apply_max = volume, 0

    def apply(self, buf):
        t = time.ticks_us()
        self.volume.apply(buf)
        self.apply_max = max(self.apply_max, time.ticks_diff(time.ticks_us(), t))

    def report(self):
        """The 5 s line, then a new window. An apply between a read and its reset here can lose one apply_max."""
        apply_max, self.apply_max = self.apply_max, 0
        line, knob = "volume level %d gain %d apply_max %d" % (self.volume.step, self.volume.gain, apply_max), self.knob
        if knob:
            windows_max, self.windows_max = self.windows_max, 0
            line += " edges %d windows_max %d" % (knob.encoder.edges(), windows_max)
            if knob.store:
                save_max, knob.store.save_max = knob.store.save_max, 0
                line += " saves %d save_max %d save_errors %d" % (knob.saves, save_max, knob.save_errors)
        print(line)


class TimedStore:
    """A VolumeStore with the probe's clock (P757): save times itself, in ms. --- MVP (P757) ---"""

    def __init__(self, store):
        self.store, self.save_max = store, 0

    def load(self):
        return self.store.load()

    def save(self, step):
        t = time.ticks_ms()
        try:
            self.store.save(step)
        finally:  # a failed save has a time too
            self.save_max = max(self.save_max, time.ticks_diff(time.ticks_ms(), t))


class Probe:
    """The hook around App.frame: the sound's open and per-frame refill, the microphone's read, the 5 s report, the
    switch every 30 s (none with HITS), the press on game over, the push stamps, the hits, and the end."""

    def __init__(self):
        self.sd = Pin(6, Pin.OUT, value=0)  # the amplifier stays off through the display setup
        self.mixer, self.refill, self.mic, self.volume = sound.Mixer(), None, None, None
        if VOLUME:  # P757
            import volume
            home = volume
            if VOLUME == "ViperMasterVolume":
                import volume_viper as home
                print("scale match %d" % home.scale_match())
            store, level = TimedStore(volume.VolumeStore()) if SAVE else None, LEVEL
            if store and level is None:
                level = store.load()
                print("stored level %s" % level)
            self.volume = TimedVolume(getattr(home, VOLUME)(volume.DEFAULT_STEP if level is None else level))
            if KNOB:
                import encoder
                import pins
                self.volume.knob = volume.VolumeKnob(
                    encoder.Encoder.on_board(pins.ENC_A, pins.ENC_B, encoder.EDGES_PER_DETENT), self.volume.volume,
                    store)
                import overlay
                self.volume.view = overlay.VolumeView(self.volume.volume)  # P762
        self.first_pop_shown = False
        if VOICE in ("Crackle", "NativeCrackle", "SampledCrackle", "GrainCrackle", "FireSound"):  # P747, P751, P753
            import crackle
            import fire
            self.mixer = fire.FirePlugin.crackle = TimedCrackle(getattr(crackle, VOICE)(747))
        self.tone = array("h", (int(AMPLITUDE * math.sin(2 * math.pi * 11 * i / CYCLE)) for i in range(CYCLE)))
        self.beep = array("h", (int(BEEP * min(1, i / FADE, (BEEP_SAMPLES - i) / FADE) * math.sin(2 * math.pi * 440 * i / RATE))
                                for i in range(BEEP_SAMPLES)))
        self.switches = self.pushes = self.skips = self.written_at = 0
        self.push_us, self.stalled = None, False
        self.start = self.report = self.next_switch = self.next_hit = self.open_at = self.opened_ms = self.sent_at = None
        self.next_save = None

    def first(self, box, now):
        self.start = self.report = now
        self.next_switch = None if HITS else time.ticks_add(now, SWITCH_MS)
        self.next_hit = time.ticks_add(now, HIT_FROM_MS)
        self.open_at = time.ticks_add(now, TONE_OPEN_MS if MIC else 0)
        self.next_save = time.ticks_add(now, SAVE_EVERY_MS)
        self.press_on_over(box)
        self.stamp_pushes(box)
        if MIC:
            self.mic = Mic()

    def open(self):
        """The I2S, the driver, a first write, then the amplifier on (Refill.open)."""
        i2s = I2S(0, sck=Pin(12), ws=Pin(13), sd=Pin(14), mode=I2S.TX, bits=16, format=I2S.MONO, rate=RATE, ibuf=IBUF)
        self.refill = r = getattr(sound, REFILL)(self.mixer, i2s, self.sd, RING, self.volume)
        print("align %d" % (uctypes.addressof(r.block) % 16))
        if not HITS and VOICE == "tone":
            self.mixer.play(self.tone, loop=True)
        self.opened_us = time.ticks_us()  # P747: the first pop's clock
        self.opened_ms = self.sent_at = time.ticks_ms()  # the first `sent` window starts here, not at the first frame
        r.open()
        if self.mic:
            self.mic.refill = r

    def short(self):
        """The samples the clock expected minus the samples written."""
        return time.ticks_diff(time.ticks_ms(), self.opened_ms) * (RATE // 1000) - self.refill.written  # no long int

    def after(self, box, now):
        if self.start is None:
            self.first(box, now)
        r, m = self.refill, self.mic
        if r is None:
            if TONE and time.ticks_diff(now, self.open_at) >= 0:
                self.open()
        elif isinstance(r, sound.FrameRefill):
            r.refill()
        elif not self.stalled and r.stalled(1000 * RING_MS):
            self.stalled = True  # a lost schedule ends the callback chain for good (refuter): report, never write again
            print("stall %d pushes %d" % (time.ticks_diff(time.ticks_us(), r.last) // 1000, self.pushes))
        if m:
            m.read()
        knob = self.volume and self.volume.knob
        if knob and knob.poll(now):  # P757
            print("level %d edges %d" % (knob.volume.step, knob.encoder.edges()))
            box.overlay.show(self.volume.view, now)  # P762: on the screen from the next frame, for 1 s
        if knob:
            self.volume.windows_max = max(self.volume.windows_max, getattr(box.out, "windows", 0) or 0)
        if SAVE_EVERY_MS and knob and knob.store and time.ticks_diff(now, self.next_save) >= 0:  # the stress run
            self.next_save = time.ticks_add(now, SAVE_EVERY_MS)
            knob.save()
        if not self.first_pop_shown and getattr(self.mixer, "first", None) is not None:
            self.first_pop_shown = True
            print("first pop %d" % (time.ticks_diff(self.mixer.first, self.opened_us) // 1000))
        if time.ticks_diff(now, self.report) >= REPORT_MS:
            r = self.refill
            if r:
                between_max = r.between_max // 1000
                r.reset()  # first: a callback during the print below keeps its between for the next line
                print("sound %s sent %d of %d between_max %d lag_max %d late %d short %d pushes %d" % (
                    box.game.name, (r.written - self.written_at) // sound.REFILL_SAMPLES,
                    time.ticks_diff(now, self.sent_at) // BUFFER_MS, between_max, between_max - BUFFER_MS, r.late,
                    self.short(), self.pushes))
                self.written_at, self.sent_at = r.written, now
            if m:
                m.report(box.game.name)
            if isinstance(self.mixer, TimedCrackle):
                self.mixer.report(box.game.name)
            if self.volume and r:
                self.volume.report()
            self.report = now
        if self.next_switch is not None and time.ticks_diff(now, self.next_switch) >= 0:
            self.next_switch = time.ticks_add(self.next_switch, SWITCH_MS)
            t = time.ticks_us()
            box.switch()
            self.switches += 1
            print("switch %d %d" % (self.switches, time.ticks_diff(time.ticks_us(), t) // 1000))
        if time.ticks_diff(now, self.start) >= SECONDS * 1000:
            raise Done

    def stamp_pushes(self, box):
        """The push's own time (P746). This handler replaces Button.edge, which app.run registered on BOOT, and counts
        the push for Button.update as Button.edge does. It keeps the first stamp until a frame takes it, so a release
        bounce does not move it. It is a scheduled handler too (no hard interrupt on this port), so it is late by the
        current C call, but earlier than the frame that reads the push."""
        import buttons

        fire = box.fire

        def edge(pin):
            fire.pushes += 1
            self.pushes += 1
            if self.push_us is None:
                self.push_us = time.ticks_us()

        Pin(buttons.BOOT_BUTTON, Pin.IN, Pin.PULL_UP).irq(edge, Pin.IRQ_FALLING)

    def press_on_over(self, box):
        """Nobody presses BOOT, and a game waits on its game-over screen for a press (gfx.Game.step)."""
        import gfx

        update = box.fire.update

        def pressing(now_ms):
            game = box.game
            now_us = time.ticks_us()
            pressed = update(now_ms)  # a real press: the probe's own press below is not a hit
            stamp, self.push_us = self.push_us, None
            seen = -1 if stamp is None else time.ticks_diff(now_us, stamp) // 1000
            if pressed and HITS:
                print("press %d" % now_ms)  # before any check: run143 entries 6 and 7 counted no hit
            if HITS == "press" and pressed:
                self.hit(now_us, seen)
            elif HITS == "auto" and self.due(now_ms):
                self.hit(now_us, -1)
            return pressed or (game.state == gfx.OVER and game.age >= game.OVER_MS)

        box.fire.update = pressing

    def due(self, now_ms):
        if self.next_hit is None or time.ticks_diff(now_ms, self.next_hit) < 0:
            return False
        self.next_hit = time.ticks_add(self.next_hit, HIT_EVERY_MS)
        return True

    def hit(self, now_us, seen):
        """Stamped at the start of the frame that sees it. Not counted until the sound opens and the floor is set. A hit
        while the last one waits for its beep is a skip."""
        m = self.mic
        if not (m and self.refill and m.threshold is not None):
            return
        if m.pending is not None:
            self.skips += 1
            print("skip %d" % self.skips)
            return
        m.hit(now_us, seen)
        self.mixer.play(self.beep)

    def close(self):
        if self.refill:
            self.refill.close()
        else:
            self.sd.value(0)
        if self.mic:
            self.mic.close()

    def summary(self):
        r, m = self.refill, self.mic
        if r:
            print("written %d short %d" % (r.written, self.short()))
        if m:
            m.report(GAME)
            if HITS:
                print("hits %d median %d max %d missed %d total_median %d" % (
                    m.hits, median(m.delays), max(m.delays or [0]), m.missed, median(m.totals)))


def main():
    import app

    probe = Probe()
    frame = app.App.frame

    def hooked(self):
        frame(self)
        probe.after(self, time.ticks_ms())

    app.App.frame = hooked
    try:
        app.run(games=(getattr(app, GAME),))
    except Done:
        pass
    finally:
        probe.close()
    probe.summary()
    print("done")
# --- MVP ---


if __name__ == "__main__":
    main()
