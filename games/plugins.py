"""
Plugins (P633): the engine's layers, each one a game turns on by listing it in Game.plugins and leaves off by not
making it. Bevy's word: a plugin adds systems to the app (https://bevy.org/learn/quick-start/getting-started/plugins/).
Here those systems are the plugin's hooks, one Update Method per stage (Nystrom, Game Programming Patterns), in Unity's
order (https://docs.unity.com/en-us/engine/current/manual/scripting/managing-update-order/execution-order):
    FixedUpdate  plugin.fixed_update(ms)   each plugin steps by its own clock
    Update       game.play(pressed, held)  the game's decisions: reads, events, respawns, burns
    LateUpdate   plugin.late_update(ms)    a layer that takes the game's burns, then steps
Game.step runs the three while the game plays. The render stays the game's: its paint calls each plugin's draw where it
wants it, so the order of the layers is open (P638).

PhysicsPlugin is the bodies on engine.Bodies (engine/core/world.c) or on its twin motion.Bodies. FirePlugin, the heat
field, is in fire.py beside its palette.
--- MVP (P633) ---
"""

import time
from array import array

from motion import MAX_EVENTS, Bodies, StepClock

try:
    import engine
except ImportError:  # an image without the engine module: Python only
    engine = None
# The import above succeeds on the Mac too: it finds the repository's engine/ folder, an empty package. Only the C
# engine has Bodies
if not hasattr(engine, "Bodies"):
    engine = None

RATE = 100  # steps a second, so a step is STEP_MS (D18)
STEP_MS, DT = 1000 // RATE, 1 / RATE
STEP_CAP = 8  # steps a frame at most (D18); Game.step caps a frame at 60 ms, so it never acts in a game today
GRAVITY, RESTITUTION, FRICTION = 2000.0, 0.35, 0.6  # stack's heavy floors (p582-heavy)


class Plugin:
    """One layer of the engine. Game.step calls its hooks once a frame while the game plays, in the list's order."""

    def fixed_update(self, ms):
        """FixedUpdate: ms of play passed since the last frame; step by the plugin's own clock."""

    def late_update(self, ms):
        """LateUpdate: after the game's play in the same frame, with the same ms."""


class PhysicsPlugin(Plugin):
    """n bodies, on engine.Bodies when c is true (one C call steps every body), else on its twin motion.Bodies.
    fixed_update steps them every frame, also with 0 steps: that clears the last step's events, so no event is drained
    twice. read() copies x, y and asleep out as ints into one array('h'), and events() the last step's events into
    one array('i'), drained, so a frame makes no list. step_us sums the steps' µs until the game takes it."""

    def __init__(self, n, c, gravity=GRAVITY, restitution=RESTITUTION, friction=FRICTION):
        self.n, self.name = n, "c" if c else "python"
        self.bodies = engine.Bodies(n) if c else Bodies(n)
        self.spawn = self.bodies.spawn
        self.world = (DT, gravity, restitution, friction)
        self.clock, self.step_us = StepClock(STEP_MS, STEP_CAP), 0
        self.out, self.drained = array("h", [0] * (3 * n)), array("i", [0] * (3 * MAX_EVENTS))

    def fixed_update(self, ms):
        t = time.ticks_us()
        self.step(self.clock.take(ms))
        self.step_us += time.ticks_diff(time.ticks_us(), t)

    def step(self, steps):
        """steps steps of DT."""
        dt, gravity, restitution, friction = self.world
        self.bodies.step(steps, dt, gravity, restitution, friction)

    def read(self, drop):
        """The bodies out, then drop(i) for each one asleep."""
        out = self.out
        self.bodies.read(out)
        for i in range(self.n):
            if out[3 * i + 2]:
                drop(i)  # out still holds its resting place, so draw shows it there one more frame

    def events(self):
        """The last step call's events into drained as id, kind, speed (motion.HIT or SLEEP); how many."""
        return self.bodies.drain(self.drained)

    def place(self, i):
        """Body i's top left corner in px, as read."""
        return self.out[3 * i], self.out[3 * i + 1]

    def draw(self, cv, size, colours):
        """Each body as a box of side size px, body i in colours[i]."""
        out, fill = self.out, cv.fill
        for i in range(self.n):
            j = 3 * i
            fill(out[j], out[j + 1], size, size, colours[i])
