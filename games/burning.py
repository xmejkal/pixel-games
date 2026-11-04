"""
Bodies on fire (P596): the fire of fire.py on objects, the proof of concept for effects in the games. A few of the
rain's falling bodies (rain.CStepper on engine/core/world.c, or rain.PythonStepper without the engine) each burn heat
into one screen-wide fire field (HeatField.burn, fx_fire_burn). The heat goes in a little behind each body, LAG
frames of its motion, along the path from the last frame's point, so a body at rest burns straight up and a moving
body's flames stream back against its motion (the PO's yes, 2026-11-03). The field's base is off, so only the bodies
burn. A body that falls asleep rests REST_MS on its plane, then falls again from above.

The HUD and the report are the fire's: `burning B fps <fps> step <ms> draw <ms>`, where step holds the bodies' step,
their read and the burns too.
--- MVP (P596) ---
"""

import random
import time

import rain
from fire import FAST, H, SWAY, W, Fire
from gfx import HEIGHT, WIDTH, c565

N = 8  # bodies on fire
BODY = 8  # px, a body's side
COAL = c565(60, 40, 30)  # a dark body, so its flames show around it
DRIFT = 120  # px/s: a drop's sideways speed is -DRIFT to DRIFT
LAG = 0.5  # the burn trails the body by this many frames of its motion
RADIUS = 3  # cells: the disc each burn writes
HEAT = 200  # orange-yellow: 255 left white columns behind a fall
# The look's feel numbers, set by the lead from Mac frames (tools/render_scene.py): the fire's own look climbs to the top
# of the screen, and decay 31 or less leaves a blob. 32 keeps the heat, and the cooling and the fade cut it into short
# tongues over a resting body and fading streaks behind a falling one.
BURN_DECAY, BURN_COOL, BURN_FADE = 32, 40, 16
REST_MS = 1500  # a sleeping body burns on its plane this long before it falls again
SEED = 596


class BurningBodies(Fire):
    name = "burning"
    LOOK = (BURN_DECAY, BURN_COOL, SWAY, 0, 1, FAST, 0, BURN_FADE)  # no spots, no embers: the base is off
    MODES = ("B",)

    def setup(self):
        random.seed(SEED)
        self.bodies = rain.CStepper(N) if rain.engine is not None else rain.PythonStepper(N)
        self.clock, self.body_acc = 0, 0  # ms played, and the ms the bodies' 10 ms steps have not taken yet
        self.slept = [None] * N  # the clock when each body fell asleep, None while it moves
        self.prev = [None] * N  # each body's centre in cells last frame, None after a drop
        self.trail = [None] * N  # each body's last burn point in cells
        for i in range(N):
            self.drop(i)
        super().setup()
        if self.field is not None:
            self.field.set_base(False)

    def drop(self, i):
        """Body i, anew above the screen with a sideways drift (D12: Python decides the respawn)."""
        self.bodies.spawn(i, random.randrange(WIDTH - BODY), -BODY - random.randrange(HEIGHT),
                          random.randrange(-DRIFT, DRIFT + 1), 0, HEIGHT - BODY - random.randrange(40))
        self.slept[i] = self.prev[i] = self.trail[i] = None

    def sleep(self, i):
        """Body i is asleep: it rests REST_MS, then drops."""
        if self.slept[i] is None:
            self.slept[i] = self.clock
        elif self.clock - self.slept[i] >= REST_MS:
            self.drop(i)

    def play(self, pressed, held):
        if not pressed:
            ms = int(self.dt * 1000 + 0.5)
            self.clock += ms
            self.body_acc += ms
            steps = self.body_acc // rain.STEP_MS
            self.body_acc -= steps * rain.STEP_MS
            t = time.ticks_us()
            self.bodies.step(steps)
            self.bodies.read(self.sleep)
            self.burn()
            self.add(0, t)
        super().play(pressed, held)

    def burn(self):
        """Each body on the screen burns from its last point to its point now, LAG frames of motion behind it."""
        for i in range(N):
            x, y = self.bodies.place(i)
            cx, cy = (x + BODY // 2) // 2, (y + BODY // 2) // 2
            if not (0 <= cy < H and -W < cx < 2 * W):  # above the screen after a drop: no streak from there
                self.prev[i] = self.trail[i] = None
                continue
            p = self.prev[i] or (cx, cy)
            lx, ly = cx - int((cx - p[0]) * LAG), cy - int((cy - p[1]) * LAG)
            t = self.trail[i] or (lx, ly)
            if self.field is not None:
                self.field.burn(t[0], t[1], lx, ly, RADIUS, HEAT)
            self.prev[i], self.trail[i] = (cx, cy), (lx, ly)

    def paint(self, cv):
        super().paint(cv)
        for i in range(N):
            x, y = self.bodies.place(i)
            cv.fill(x, y, BODY, BODY, COAL)
