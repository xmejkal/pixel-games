"""
P589 (#790): what a C step costs on the board, against today's fall_bodies (p582-heavy games/motion.py, @native), for
the engine discovery's A2, A3 and D16. --- probe, throwaway (P589) ---

    mpremote run probe589.py      # the engine image (./build.sh engine), with p582-heavy's motion.py and fast.py

One line per number: `name value unit`; one run is one set, so run it 3 times in one boot. Each step number uses 6
blocks of one load and 100 steps of 10 ms; the load is outside the timer, and before each bracket gc.collect() runs
and an `_alloc` line prints the gc.mem_alloc() change. The fall scene's planes are out of reach (a number per
body-step); the bounce scene's bodies bounce and sleep, so its number is per awake body-step. FIXED is scalar Q16.16,
the base a PIE path would build on, not a PIE path.
"""

import gc
import time
from array import array

import engine
from motion import Bodies, fall_bodies

N, RATE, STEPS, BLOCKS, FRAME = 12, 100, 100, 6, 6  # bodies, steps per second, steps per block, blocks, steps a frame
GRAVITY, RESTITUTION, FRICTION = 2000.0, 0.35, 0.6  # p582-heavy games/arcade2.py: Stack.G, SLAB_BOUNCE, SLAB_FRICTION
DT = 1 / RATE
CALLS = STEPS // FRAME  # calls of one frame per block: 16, so 96 steps


def scene(rest_y):
    """The plan's twelve bodies: x = 10 + 20 i, y = -10 i, vx = 5 (i - 6), vy 3, and rest_y(i)."""
    return [(10.0 + 20 * i, -10.0 * i, 5.0 * (i - 6), 3.0, float(rest_y(i))) for i in range(N)]


FALL = scene(lambda i: 30000)  # no body reaches its plane; Q16.16 holds it
BOUNCE = scene(lambda i: 220 - 14 * (i % 3))
COLUMNS = {}  # a scene's five array('f') columns for engine.load, made once


def per_call(n, body):
    """Microseconds per call of body(), a loop calling an empty function taken off (body is a lambda too)."""
    nothing = lambda: None
    t = time.ticks_us()
    for _ in range(n):
        nothing()
    empty = time.ticks_diff(time.ticks_us(), t) / n
    t = time.ticks_us()
    for _ in range(n):
        body()
    return time.ticks_diff(time.ticks_us(), t) / n - empty


def say(name, value, unit, digits=2):
    print("%s %.*f %s" % (name, digits, value, unit))


def load_python(bodies, sc):
    for i, b in enumerate(sc):
        bodies.spawn(i, *b)


def load_engine(sc):
    if id(sc) not in COLUMNS:
        COLUMNS[id(sc)] = [array("f", c) for c in zip(*sc)]
    engine.load(*COLUMNS[id(sc)])


def bracket(load, run):
    """6 blocks: load() untimed, then run() timed. The microseconds of all blocks, and the gc.mem_alloc() change."""
    total = alloc = 0
    for _ in range(BLOCKS):
        load()
        gc.collect()
        a = gc.mem_alloc()
        t = time.ticks_us()
        run()
        total += time.ticks_diff(time.ticks_us(), t)
        alloc += gc.mem_alloc() - a
    return total, alloc


def python_steps(bodies):
    for _ in range(STEPS):
        fall_bodies(bodies, DT, GRAVITY, RESTITUTION, FRICTION)


def python_awake(bodies, sc):
    """fall_bodies' awake body-steps in one block, counted in a run outside the timer."""
    load_python(bodies, sc)
    awake = 0
    for _ in range(STEPS):
        awake += sum(1 for i in range(N) if not bodies.asleep[i])
        fall_bodies(bodies, DT, GRAVITY, RESTITUTION, FRICTION)
    return awake


def baseline(name, sc):
    """Number 1: today's fall_bodies, one call per step."""
    bodies = Bodies(N)
    us, alloc = bracket(lambda: load_python(bodies, sc), lambda: python_steps(bodies))
    say("%s_python_body_step" % name, us / (BLOCKS * python_awake(bodies, sc)), "us", 3)
    say("%s_python_frame" % name, us / (BLOCKS * STEPS / FRAME) / 1000, "ms")
    say("%s_python_alloc" % name, alloc, "B")


def c_step(name, sc, mode, label):
    """Numbers 2 and 3: one engine.step of 100 steps per block (no call cost), then 16 calls of 6 steps (with it)."""
    awake = [0]

    def whole():
        awake[0] = engine.step(mode, STEPS, RATE, GRAVITY, RESTITUTION, FRICTION)

    def frames():
        for _ in range(CALLS):
            engine.step(mode, FRAME, RATE, GRAVITY, RESTITUTION, FRICTION)

    us, alloc = bracket(lambda: load_engine(sc), whole)
    say("%s_%s_body_step" % (name, label), us / (BLOCKS * awake[0]), "us", 3)
    say("%s_%s_frame" % (name, label), us / (BLOCKS * STEPS) * FRAME / 1000, "ms")
    say("%s_%s_alloc" % (name, label), alloc, "B")
    us, alloc = bracket(lambda: load_engine(sc), frames)
    say("%s_%s_frame_call" % (name, label), us / (BLOCKS * CALLS) / 1000, "ms")
    say("%s_%s_frame_call_alloc" % (name, label), alloc, "B")


def sanity(steps):
    """The largest y difference between fall_bodies and each C mode on the bounce scene after steps steps."""
    bodies = Bodies(N)
    load_python(bodies, BOUNCE)
    for _ in range(steps):
        fall_bodies(bodies, DT, GRAVITY, RESTITUTION, FRICTION)
    out = array("f", [0.0] * N)
    for mode, label in ((engine.FLOAT, "float"), (engine.FIXED, "fixed")):
        load_engine(BOUNCE)
        engine.step(mode, steps, RATE, GRAVITY, RESTITUTION, FRICTION)
        engine.read_y(mode, out)
        say("sanity_y_%s_%d" % (label, steps), max(abs(out[i] - bodies.y[i]) for i in range(N)), "px", 4)


def drain():
    """Number 4: a drain of 16 events into an array('i'), each read in Python, after a 1 s bounce block."""
    load_engine(BOUNCE)
    engine.step(engine.FLOAT, STEPS, RATE, GRAVITY, RESTITUTION, FRICTION)
    buf = array("i", [0] * 48)
    say("drain_events", engine.drain(buf, 16), "events", 0)  # 16, or the drain number below is for fewer

    def drain_and_read():
        m = engine.drain(buf, 16)
        s = 0
        for k in range(3 * m):
            s += buf[k]

    gc.collect()
    a = gc.mem_alloc()
    say("drain_16", per_call(1000, drain_and_read), "us")
    say("drain_16_alloc", gc.mem_alloc() - a, "B")


def on_event(i):
    pass


def call_back():
    """Number 5: one C-to-Python call, engine.call_back(fn, 1000) minus engine.call_back(fn, 0), over 1,000."""
    gc.collect()
    a = gc.mem_alloc()
    t = time.ticks_us()
    engine.call_back(on_event, 0)
    zero = time.ticks_diff(time.ticks_us(), t)
    t = time.ticks_us()
    engine.call_back(on_event, 1000)
    full = time.ticks_diff(time.ticks_us(), t)
    say("call_back", (full - zero) / 1000, "us")
    say("call_back_alloc", gc.mem_alloc() - a, "B")


def reads():
    """A2's reads: 12 Python reads of bodies.y[i], against one engine.read_y and 12 reads of its array."""
    bodies = Bodies(N)
    load_python(bodies, BOUNCE)
    load_engine(BOUNCE)
    out = array("f", [0.0] * N)

    def python_reads():
        y = bodies.y
        for i in range(N):
            y[i]

    def engine_reads():
        engine.read_y(engine.FLOAT, out)
        for i in range(N):
            out[i]

    gc.collect()
    say("reads_python_12", per_call(1000, python_reads), "us")
    say("reads_engine_12", per_call(1000, engine_reads), "us")


def empty_call():
    """The empty Python-to-C call (5.5 us in run26): engine.nothing(), and an empty lambda, each with its loop."""
    nothing = lambda: None
    for name, body in (("empty_lambda_loop", nothing), ("nothing_loop", engine.nothing)):
        t = time.ticks_us()
        for _ in range(1000):
            body()
        say(name, time.ticks_diff(time.ticks_us(), t) / 1000, "us")


def main():
    sanity(FRAME)
    sanity(STEPS)
    for name, sc in (("fall", FALL), ("bounce", BOUNCE)):
        baseline(name, sc)
        c_step(name, sc, engine.FLOAT, "float")
        c_step(name, sc, engine.FIXED, "fixed")
    drain()
    call_back()
    reads()
    empty_call()


main()
