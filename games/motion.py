"""
Motion for the games (P582, P590): one damped spring, a pool of falling rectangles that bounce on a resting plane, and
the clock that turns frame times into fixed steps.

The pool, Bodies, is the twin of the engine's engine.Bodies (engine/core/world.c): the same API, the same maths and
the same events, so a game runs on either, and the Mac tests hold the C to it. It draws nothing and imports nothing
from gfx, so the Mac tests run it as it is. It keeps its numbers in lists made once, so a step builds no list; on the
board each float is still boxed, so what a step allocates is measured there, not assumed.
--- MVP (P590) ---
"""

from fast import native


class Spring:
    """One value pulled back to 0 and damped: a tower's sway, or its press at a landing. step() is the semi-implicit
    Euler the sway always used, so the sway moved onto it unchanged. It stays stable while damping * dt and
    sqrt(k) * dt are both under 1: at the 60 ms frame clamp, k up to about 270 and damping up to about 16."""

    def __init__(self, k, damping):
        self.k, self.damping = k, damping
        self.value, self.speed = 0.0, 0.0

    def step(self, dt):
        self.speed -= (self.k * self.value + self.damping * self.speed) * dt
        self.value += self.speed * dt

    def kick(self, dv):
        """A blow: it changes the speed only, so the value moves from where it is, with no jump."""
        self.speed += dv

    def settled(self):
        """Under half a pixel and slower than 5 px/s: nothing a frame would show."""
        return -0.5 < self.value < 0.5 and -5.0 < self.speed < 5.0


HIT, SLEEP = 1, 2  # the kinds of event, engine.HIT and engine.SLEEP: a bounce, and a body come to rest
MAX_EVENTS = 64  # world.h's WORLD_MAX_EVENTS: a step call keeps its first 64 events, the rest only count in dropped
MAX_BODIES, MAX_STEPS = 256, 64  # binding.c's limits on n and on the steps of one call


@native
def fall_bodies(bodies, dt, gravity, restitution, friction):
    """One step of every awake body, its events after the pool's; Bodies.step says what it does. It takes the pool,
    not its lists, so the call has five arguments: few enough for any emitter."""
    x, y, vx, vy, rest_y, asleep = bodies.x, bodies.y, bodies.vx, bodies.vy, bodies.rest_y, bodies.asleep
    events, k, dropped = bodies.events, bodies.n_events, bodies.dropped
    rest_speed = 1.5 * gravity * dt
    for i in range(bodies.n):
        if asleep[i]:
            continue
        vy[i] += gravity * dt
        x[i] += vx[i] * dt
        y[i] += vy[i] * dt
        if y[i] >= rest_y[i]:  # through the plane in this step: back onto it, so nothing tunnels
            y[i] = rest_y[i]
            v = vy[i]
            if v < rest_speed:  # too slow to leave the plane again: it rests, and a resting body gains nothing
                vy[i] = 0.0
                vx[i] = 0.0
                asleep[i] = 1
                kind, speed = SLEEP, 0
            else:
                kind, speed = HIT, int(v)
                vy[i] = -v * restitution
                vx[i] *= friction
            if k < MAX_EVENTS:
                events[3 * k] = i
                events[3 * k + 1] = kind
                events[3 * k + 2] = speed
                k += 1
            else:
                dropped += 1
    bodies.n_events, bodies.dropped = k, dropped


class Bodies:
    """The twin of engine.Bodies: n falling rectangles, each asleep at (0, 0) until spawned. Body i is its top-left
    x, y, its speed vx, vy, and rest_y, the y its top stops at (the plane it bounces on). The lists are the bodies, and
    events holds the last step call's events as id, kind, speed, n_events of them."""

    def __init__(self, n):
        if not 1 <= n <= MAX_BODIES:
            raise ValueError("n is 1 to %d" % MAX_BODIES)
        self.n = n
        self.x, self.y, self.vx, self.vy, self.rest_y = [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n
        self.asleep = [1] * n
        self.events, self.n_events, self.dropped = [0] * (3 * MAX_EVENTS), 0, 0

    def spawn(self, i, x, y, vx, vy, rest_y):
        """Body i at this state, awake."""
        if not 0 <= i < self.n:
            raise IndexError("a body index is 0 to n - 1")
        self.x[i], self.y[i], self.vx[i], self.vy[i] = float(x), float(y), float(vx), float(vy)
        self.rest_y[i] = float(rest_y)
        self.asleep[i] = 0

    def step(self, steps, dt, gravity, restitution, friction):
        """Clear the events, then steps steps of dt s each. A body falls under gravity; at its plane it bounces back
        up with restitution times its speed and friction times its vx, an event (i, HIT, speed in px/s); under
        1.5 * gravity * dt it rests there instead, an event (i, SLEEP, 0), and moves no more until a spawn. Past
        MAX_EVENTS an event only counts in dropped."""
        if not 0 <= steps <= MAX_STEPS:
            raise ValueError("steps is 0 to %d" % MAX_STEPS)
        self.n_events = self.dropped = 0
        for _ in range(steps):
            fall_bodies(self, dt, gravity, restitution, friction)

    @native
    def read(self, out):
        """Each body's x, y (truncated toward 0) and asleep into out, 3n ints; returns n. MicroPython's array has no
        typecode, so only the length is checked here; engine.Bodies also needs an array('h')."""
        n = self.n
        if len(out) < 3 * n:
            raise ValueError("an array('h') of 3n ints is needed")
        x, y, asleep = self.x, self.y, self.asleep
        for i in range(n):
            out[3 * i] = int(x[i])
            out[3 * i + 1] = int(y[i])
            out[3 * i + 2] = asleep[i]
        return n

    def drain(self, out):
        """Up to len(out) // 3 of the last step call's events into out as id, kind, speed; returns how many."""
        m = min(len(out) // 3, self.n_events)
        events = self.events
        for j in range(3 * m):
            out[j] = events[j]
        return m


class StepClock:
    """Whole fixed steps of step_ms out of the frames' ms (D18). The ms under a step wait for the next frame; steps past
    cap in one frame are dropped, so a long frame slows the world instead of stepping it in a burst."""

    def __init__(self, step_ms, cap):
        self.step_ms, self.cap, self.ms = step_ms, cap, 0

    def take(self, frame_ms):
        """The steps that frame_ms more hold, at most cap."""
        self.ms += frame_ms
        steps = self.ms // self.step_ms
        self.ms -= steps * self.step_ms
        return min(steps, self.cap)
