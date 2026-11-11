"""
The game's sound (P748, P768): one Mixer that sums its voices, and the drivers that feed its samples to the I2S ring.

A sound is an array("h") of 16 kHz mono samples, or a bank.BankSound. The game calls mixer.play(sound), which returns its Voice, and a driver calls
mixer.render(buf) when the ring has room. FrameRefill refills once per frame from the game loop: the naive path, which
stays working (D26). CallbackRefill refills from the stock I2S.irq callback, so a slow frame does not starve the ring
(D25). A later C mixer, or a C task on the second core (P747, D27), keeps the same render(buf).

The stock callback (MicroPython v1.29.0): after i2s.irq(handler), write(buf) returns at once, and a FreeRTOS task
copies buf into the DMA ring as room frees (ports/esp32/machine_i2s.c:241). When all of buf is in, the task schedules
the handler (:274). The handler runs at the next bytecode boundary, never inside a C call such as a display send or
gc.collect(). The task's queue holds one buffer, so only the handler writes. The game box plays through speaker.Speaker
(P768). probe733_games.py and crackle.py's SampledCrackle (P747) use this module too.
"""

import time
from array import array

from volume import FULL

RATE = 16000
REFILL_SAMPLES = 256  # one DMA buffer, 16 ms, a multiple of 8 samples (D27)


# --- MVP (P768) ---
MUSIC, SFX = "music", "sfx"  # the groups: voices that share one gain


class Voice:
    """One sound that plays now. A caller that keeps its Voice can set `gain` (Q15, one store) while it plays: 0 ends
    it. `live` is False once the mixer dropped it. `protect`: the full case never takes it."""

    def __init__(self, sound, loop, group, gain, protect, born):
        self.sound, self.at, self.loop, self.group, self.gain = sound, 0, loop, group, gain
        self.mem, self.first = getattr(sound, "mem", sound), getattr(sound, "first", 0)  # for the viper sum
        self.protect, self.born, self.live = protect, born, True


class VoiceSum:
    """The strategy that sums the voices: plain Python, the reference (D26). sound_viper.ViperVoiceSum gives the
    same samples faster. One overflow rule on every path: each product is shifted by 15 before it is added, the sum
    is a 32-bit int, and one clip brings it to 16 bits."""

    def add(self, acc, k, voice, n, gain):
        """acc[k:k + n] += the voice's next n samples * gain >> 15."""
        sound, at = voice.sound, voice.at
        for i in range(n):
            acc[k + i] += (sound[at + i] * gain) >> 15

    def clip(self, acc, buf, n):
        """buf[:n] = acc[:n] clipped to 16 bits, and acc[:n] = 0 for the next block."""
        for i in range(n):
            x = acc[i]
            buf[i] = 32767 if x > 32767 else -32768 if x < -32768 else x
            acc[i] = 0


class Mixer:
    """`voices` sounds at once, summed by `voice_sum` (a VoiceSum). The mixer picks the slot of a play: a free one,
    else the oldest voice that is not protected, so Mixer() has one voice and the last play wins. render(buf) renders
    sound, not the screen. Its contract holds for every mixer, also a later one in C: buf is an array("h") of int16
    mono samples at RATE, len(buf) is a multiple of 8, buf is aligned to 16 bytes, and render fills all of buf and
    never waits. `pending` is not None while a play waits for the next render: the drivers read it to time a play
    (Refill.stamp). A driver's callback runs render between two bytecodes of the game, so play and stop change a
    slot with one store, and render never allocates."""

    def __init__(self, voices=1, voice_sum=None):
        self.voices, self.sum = [None] * voices, voice_sum or VoiceSum()
        self.group_gain = {MUSIC: FULL, SFX: FULL}
        self.acc = array("i", bytes(4 * REFILL_SAMPLES))
        self.pending, self.born = None, 0

    def play(self, sound, loop=False, group=SFX, gain=FULL, protect=False):
        """Starts the sound at the next render and returns its Voice, or None when nothing plays: an empty sound, or
        every slot protected."""
        slot = self.slot() if len(sound) else None
        if slot is None:
            return None
        self.born += 1
        voice, old = Voice(sound, loop, group, gain, protect, self.born), self.voices[slot]
        if old:
            old.live = False
        self.voices[slot] = voice
        self.pending = voice  # last, so a callback sees a whole voice in its slot
        return voice

    def slot(self):
        oldest = None
        for i, voice in enumerate(self.voices):
            if voice is None:
                return i
            if not voice.protect and (oldest is None or voice.born < self.voices[oldest].born):
                oldest = i
        return oldest

    def stop(self, group=None):
        """Ends the voices of the group, or all of them, at the next render."""
        voices = self.voices
        for i in range(len(voices)):
            voice = voices[i]
            if voice and (group is None or voice.group == group):
                voice.live = False
                voices[i] = None

    def render(self, buf):
        self.pending = None
        n, voices, add = len(buf), self.voices, self.sum.add
        if len(self.acc) < n:  # only a block longer than the drivers' own
            self.acc = array("i", bytes(4 * n))
        acc = self.acc
        for i in range(len(voices)):
            voice = voices[i]
            if voice is None:
                continue
            gain = min(voice.gain, FULL) * min(self.group_gain[voice.group], FULL) >> 15
            size, k, done = len(voice.sound), 0, voice.gain <= 0
            while k < n and not done:
                m = min(n - k, size - voice.at)
                if gain > 0:
                    add(acc, k, voice, m, gain)
                k += m
                voice.at += m
                if voice.at == size:
                    voice.at, done = 0, not voice.loop
            if done:
                voice.live = False
                voices[i] = None
        self.sum.clip(acc, buf, n)
# --- MVP (P768) ---


# --- MVP ---
class Refill:
    """The strategy that feeds the mixer's samples to the I2S ring. open() starts the sound and then the amplifier.
    close() stops them in PHYS-13's order. A refill later than the ring minus one block can find the ring empty: that
    is a `late` count, and the probe's `lag_max` is between_max minus one block. play_between is the gap before the
    refill that took the last play. `written` counts samples handed to the I2S, in CallbackRefill up to one block
    before they reach the DMA ring. `volume` (P757) is a MasterVolume of volume.py, or None for the mix as it is."""

    def __init__(self, mixer, i2s, sd, ring_samples, volume=None):
        self.mixer, self.i2s, self.sd, self.volume = mixer, i2s, sd, volume
        self.block = array("h", (0 for _ in range(REFILL_SAMPLES)))
        self.late_us = (ring_samples - REFILL_SAMPLES) * 1000 // (RATE // 1000)
        self.written = self.sent_count = self.late = self.between = self.play_between = self.last = 0
        self.reset()

    def reset(self):
        self.between_max = 0

    def open(self):
        self.last = time.ticks_us()
        self.start()
        self.sd.value(1)

    def start(self):
        """The driver's first write."""
        raise NotImplementedError

    def render_block(self):
        """The mixer's next block, then the master volume: the last gain before the I2S (P757)."""
        try:
            self.mixer.render(self.block)
        finally:  # a render that failed part way still gets the volume: no block is louder than the step
            if self.volume is not None:
                self.volume.apply(self.block)

    def stamp(self):
        now = time.ticks_us()
        self.between, self.last = time.ticks_diff(now, self.last), now
        self.between_max = max(self.between_max, self.between)
        if self.between > self.late_us:
            self.late += 1
        if self.mixer.pending is not None:
            self.play_between = self.between

    def stalled(self, ring_us):
        """True when no refill came for longer than twice the ring: a callback chain that a lost schedule or an error
        ended, which nothing restarts. The game loop can check it and report."""
        return time.ticks_diff(time.ticks_us(), self.last) > 2 * ring_us

    def close(self):
        """The amplifier off before the clocks stop. The 10 ms is a margin with no datasheet figure."""
        self.sd.value(0)
        time.sleep_ms(10)
        self.i2s.deinit()


class FrameRefill(Refill):
    """Once per frame, from the game loop: the naive path (D26). A poll makes the writes return at once with what fits
    (extmod/machine_i2s.c:622), so refill() fills the free DMA buffers and keeps the rest of its block for the next.
    A write renders at most one ring of blocks, so a mixer slower than real time slows the game but never locks it
    (P747: the Python Crackle took 21 ms a block, and Fire never finished a frame)."""

    def __init__(self, mixer, i2s, sd, ring_samples, volume=None):
        super().__init__(mixer, i2s, sd, ring_samples, volume)
        self.ring_blocks = max(1, ring_samples // REFILL_SAMPLES)  # P747
        self.rest = 0  # samples at the end of the block not yet written
        self.poll = None

    def start(self):
        import select

        self.poll = select.poll()
        self.poll.register(self.i2s, select.POLLOUT)
        self.poll.poll(0)
        self.write()

    def refill(self):
        self.stamp()
        self.sent_count += 1
        self.write()

    def write(self):
        for _ in range(self.ring_blocks):
            if not self.rest:
                self.render_block()
                self.rest = REFILL_SAMPLES
            n = (self.i2s.write(memoryview(self.block)[REFILL_SAMPLES - self.rest:]) or 0) // 2
            self.written += n
            self.rest -= n
            if self.rest:
                return


class CallbackRefill(Refill):
    """From the stock I2S.irq callback: the refill does not wait for a frame (D25). It never polls, because a poll
    makes the task's writes stop waiting (ports/esp32/machine_i2s.c:239). close() never calls irq(None): that deletes
    the task while it holds the write lock, and deinit then waits forever."""

    def __init__(self, mixer, i2s, sd, ring_samples, volume=None):
        super().__init__(mixer, i2s, sd, ring_samples, volume)
        self.closed = False

    def start(self):
        self.i2s.irq(self.sent)
        self.write()

    def sent(self, i2s):
        if self.closed:
            return
        self.stamp()
        self.sent_count += 1
        self.write()

    def write(self):
        try:
            self.render_block()  # the task finished with the block before it scheduled sent
        finally:  # an error in render still queues a block, so the chain goes on
            self.i2s.write(self.block)
            self.written += REFILL_SAMPLES

    def close(self):
        self.closed = True
        super().close()
# --- MVP ---
# --- Later, not MVP: a row in bench.md P748, not code: a C mixer (P747), a C task
# on the second core (D27) ---
