"""
P582: what motion.py's steps allocate on the board, where every float is boxed. The collector is off while the steps
run, so gc.mem_alloc() before and after counts every byte they took; nothing else runs between the two reads.

    mpremote run probe582.py

One line per number: `name value unit`. The pool is full: all five bodies fall the whole time (their plane is far
below), so no body sleeps and each step does all its work.
"""

import gc

from motion import Bodies, Spring

N = 200  # steps per measure
DT, G = 0.04, 2000.0


def say(name, value, unit):
    print("%s %s %s" % (name, value, unit))


def nothing():
    pass


def allocated(step):
    """Bytes N calls of step() take, with the collector off, less what N empty calls take."""
    gc.collect()
    gc.disable()
    try:
        before = gc.mem_alloc()
        for _ in range(N):
            nothing()
        empty = gc.mem_alloc() - before
        before = gc.mem_alloc()
        for _ in range(N):
            step()
        return gc.mem_alloc() - before - empty
    finally:
        gc.enable()


bodies = Bodies(5)
for i in range(5):
    bodies.spawn(i, 40 * i, 0, 40, 0, 1e9)
spring = Spring(150, 9)
spring.kick(200)
took = allocated(lambda: bodies.step(DT, G, 0.35, 0.6))
say("bodies_step_full_pool_200", took, "B")
say("bodies_step_per_call", took // N, "B")
took = allocated(lambda: spring.step(DT))
say("spring_step_200", took, "B")
say("spring_step_per_call", took // N, "B")
