"""
Motion for the games (P582): one damped spring, and a pool of falling rectangles that bounce on a resting plane.

It draws nothing and imports nothing from gfx, so the Mac tests run it as it is. The pool keeps its numbers in parallel
lists made once, so a frame does not build a list or a tuple; on the board each float is still boxed, so what a step
allocates is measured there (probe582.py), not assumed.
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


@native
def fall_bodies(bodies, dt, gravity, restitution, friction):
    """One step of every live, awake body; Bodies.step says what it does. It takes the pool, not its lists, so the
    call has five arguments: few enough for any emitter."""
    x, y, vx, vy, rest_y = bodies.x, bodies.y, bodies.vx, bodies.vy, bodies.rest_y
    live, asleep, hit = bodies.live, bodies.asleep, bodies.hit
    rest_speed = 1.5 * gravity * dt
    for i in range(bodies.n):
        hit[i] = 0
        if not live[i] or asleep[i]:
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
            else:
                hit[i] = int(v)
                vy[i] = -v * restitution
                vx[i] *= friction


class Bodies:
    """A fixed pool of n falling rectangles. Body i is its top-left x, y, its speed vx, vy, and rest_y, the y its top
    stops at (the plane it bounces on). live, asleep and hit are int lists: hit[i] is the impact speed in px/s of the
    bounce in the last step, else 0, for the game to read after step()."""

    def __init__(self, n):
        self.n = n
        self.x, self.y, self.vx, self.vy, self.rest_y = [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n
        self.live, self.asleep, self.hit = [0] * n, [0] * n, [0] * n

    def spawn(self, i, x, y, vx, vy, rest_y):
        self.x[i], self.y[i], self.vx[i], self.vy[i] = float(x), float(y), float(vx), float(vy)
        self.rest_y[i] = float(rest_y)
        self.live[i], self.asleep[i], self.hit[i] = 1, 0, 0

    def free(self, i):
        self.live[i], self.hit[i] = 0, 0

    def step(self, dt, gravity, restitution, friction):
        """Fall under gravity for dt s. At the plane a body bounces back up with restitution times its speed and
        friction times its vx, its impact speed written into hit; under 1.5 * gravity * dt it sleeps instead, so a
        body at rest fires no hit. hit is cleared first, so each hit is reported in one step only."""
        fall_bodies(self, dt, gravity, restitution, friction)
