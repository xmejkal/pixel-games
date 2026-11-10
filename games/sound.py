"""
The game's sound (P748): one Mixer, and the drivers that feed its samples to the I2S ring.

A sound is an array("h") of 16 kHz mono samples. The game calls mixer.play(sound), and a driver calls
mixer.render(buf) when the ring has room. FrameRefill refills once per frame from the game loop: the naive path, which
stays working (D26). CallbackRefill refills from the stock I2S.irq callback, so a slow frame does not starve the ring
(D25). A later C mixer, or a C task on the second core (P747, D27), keeps the same render(buf).

The stock callback (MicroPython v1.29.0): after i2s.irq(handler), write(buf) returns at once, and a FreeRTOS task
copies buf into the DMA ring as room frees (ports/esp32/machine_i2s.c:241). When all of buf is in, the task schedules
the handler (:274). The handler runs at the next bytecode boundary, never inside a C call such as a display send or
gc.collect(). The task's queue holds one buffer, so only the handler writes. No game imports this module yet. Only
probe733_games.py does.
"""

import time
from array import array

RATE = 16000
REFILL_SAMPLES = 256  # one DMA buffer, 16 ms, a multiple of 8 samples (D27)


# --- MVP ---
class Mixer:
    """One voice: the last play wins. render(buf) renders sound, not the screen. Its contract holds for every mixer,
    also a later one in C: buf is an array("h") of int16 mono samples at RATE, len(buf) is a multiple of 8, buf is
    aligned to 16 bytes, and render fills all of buf and never waits. Its slices allocate small views. `pending` is not
    None while a play waits for the next render: the drivers read it to time a play (Refill.stamp)."""

    def __init__(self):
        self.pending = None  # (sound, loop): play's one store, so a callback between two bytecodes sees all of it or none
        self.sound, self.loop, self.at = None, False, 0
        self.zeros = memoryview(array("h"))

    def play(self, sound, loop=False):
        self.pending = (memoryview(sound), loop) if len(sound) else (None, False)  # an empty loop never ends a render

    def render(self, buf):
        if self.pending is not None:
            (self.sound, self.loop), self.at, self.pending = self.pending, 0, None
        out, n, k = memoryview(buf), len(buf), 0
        while k < n and self.sound is not None:
            m = min(n - k, len(self.sound) - self.at)
            out[k:k + m] = self.sound[self.at:self.at + m]
            k += m
            self.at += m
            if self.at == len(self.sound):
                self.at = 0
                if not self.loop:
                    self.sound = None
        if k < n:
            if len(self.zeros) < n:
                self.zeros = memoryview(array("h", (0 for _ in range(n))))
            out[k:] = self.zeros[:n - k]


class Refill:
    """The strategy that feeds the mixer's samples to the I2S ring. open() starts the sound and then the amplifier.
    close() stops them in PHYS-13's order. A refill later than the ring minus one block can find the ring empty: that
    is a `late` count, and the probe's `lag_max` is between_max minus one block. play_between is the gap before the
    refill that took the last play. `written` counts samples handed to the I2S, in CallbackRefill up to one block
    before they reach the DMA ring."""

    def __init__(self, mixer, i2s, sd, ring_samples):
        self.mixer, self.i2s, self.sd = mixer, i2s, sd
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
    (extmod/machine_i2s.c:622), so refill() fills the free DMA buffers and keeps the rest of its block for the next."""

    def __init__(self, mixer, i2s, sd, ring_samples):
        super().__init__(mixer, i2s, sd, ring_samples)
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
        while True:
            if not self.rest:
                self.mixer.render(self.block)
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

    def __init__(self, mixer, i2s, sd, ring_samples):
        super().__init__(mixer, i2s, sd, ring_samples)
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
            self.mixer.render(self.block)  # the task finished with the block before it scheduled sent
        finally:  # an error in render still queues a block, so the chain goes on
            self.i2s.write(self.block)
            self.written += REFILL_SAMPLES

    def close(self):
        self.closed = True
        super().close()
# --- MVP ---
# --- Later, not MVP: a row in bench.md P748, not code: more than one voice summed, volume, a C mixer (P747), a C task
# on the second core (D27) ---
