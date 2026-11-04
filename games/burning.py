"""
Bodies on fire (P596, P607): the fire of fire.py on objects, the proof of concept for effects in the games. A few of
the rain's falling bodies (rain.Stepper, on engine.Bodies or without the engine on motion.Bodies) each carry an
effects.FireTrail, which burns heat into one screen-wide fire field (HeatField.burn, fx_fire_burn). The heat goes in a
little behind each body, LAG frames of its motion, so a body at rest burns straight up and a moving body's flames
stream back against its motion (the PO's yes, 2026-11-03). The field's base is off, so only the bodies burn. A body
that falls asleep rests REST_MS on its plane, then falls again from above.

A hard landing flares up (P590): C reports each hit with its speed as an event, and this scene's handler for it,
through effects.EffectSystem.dispatch, decides what it causes (D12). A hit at FLARE_MIN px/s or more burns one disc
at the body's x and its plane, wider and hotter the faster it hit.

The HUD and the report are the fire's: `burning B fps <fps> step <ms> draw <ms>`, where step holds the bodies' step,
their read and the burns too.
--- MVP (P607) ---
"""

import random
import time

import rain
from effects import EffectSystem, FireTrail, cell
from fire import FAST, SWAY, Fire
from gfx import HEIGHT, WIDTH, c565
from motion import HIT, StepClock

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
# The flare's feel numbers, which the PO saw on the panel on 2026-11-04 ("Oh, nice!!!"). A drop of 200 to
# 480 px under the rain's GRAVITY lands at about 900 to 1,400 px/s, and each bounce keeps 0.35 of that, so FLARE_MIN
# lets first landings flare and no bounce after them.
FLARE_MIN = 600  # px/s: a hit this fast or faster flares
FLARE_SPEED_PER_CELL = 150  # px/s of impact per cell of the flare's radius: 600 px/s is 4 cells, 1,400 px/s 9
FLARE_RADIUS_MAX = 12  # cells; HeatField.burn takes up to 16
FLARE_SPEED_PER_HEAT = 8  # the heat climbs from HEAT at FLARE_MIN by 1 for each 8 px/s more, up to 255
SEED = 596


def flare_size(speed):
    """The flare of a hit at speed px/s: its radius in cells and its heat."""
    radius = min(FLARE_RADIUS_MAX, speed // FLARE_SPEED_PER_CELL)
    return radius, min(255, HEAT + max(0, speed - FLARE_MIN) // FLARE_SPEED_PER_HEAT)


class BurningBodies(Fire):
    name = "burning"
    LOOK = (BURN_DECAY, BURN_COOL, SWAY, 0, 1, FAST, 0, BURN_FADE)  # no spots, no embers: the base is off
    MODES = ("B",)

    def setup(self):
        random.seed(SEED)
        self.stepper = rain.Stepper(N, rain.engine is not None)
        self.clock, self.step_clock = 0, StepClock(rain.STEP_MS, rain.STEP_CAP)  # ms played, and the bodies' steps
        self.slept = [None] * N  # the clock when each body fell asleep, None while it moves
        self.rest_y = [0] * N  # each body's plane: the y its top rests at, where it flares
        super().setup()  # the field first: Fire.setup draws no random number, so the drops below get today's
        if self.field is not None:
            self.field.set_base(False)
        self.attach_effects()
        for i in range(N):
            self.drop(i)

    def attach_effects(self):
        """Each body carries a FireTrail, and a hit flares, when the field exists; without it, no handler runs."""
        self.effects, self.handlers = EffectSystem(self.stepper), {}  # both made once, so a frame makes none
        if self.field is not None:
            for body in self.effects.bodies:
                body.effect = FireTrail(self.field, BODY, RADIUS, HEAT, LAG)
            self.handlers[HIT] = self.flare

    def drop(self, i):
        """Body i, anew above the screen with a sideways drift and its plane (D12: Python decides the respawn)."""
        x, y, vx = random.randrange(WIDTH - BODY), -BODY - random.randrange(HEIGHT), random.randrange(-DRIFT, DRIFT + 1)
        self.rest_y[i] = HEIGHT - BODY - random.randrange(40)
        self.stepper.spawn(i, x, y, vx, 0, self.rest_y[i])
        self.slept[i] = None
        self.effects.bodies[i].reset()

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
            t = time.ticks_us()
            self.stepper.step(self.step_clock.take(ms))  # every frame, also with 0 steps (rain.Stepper.step)
            self.stepper.read(self.sleep)
            self.effects.dispatch(self.handlers)
            self.effects.update()
            self.add(0, t)
        super().play(pressed, held)

    def flare(self, body, speed):
        """A hit at FLARE_MIN or faster burns a disc at the body's x, as read, and its plane: it has bounced up since,
        so its read y is not where it landed. Only a scene with a field has it as a handler."""
        if speed >= FLARE_MIN:
            cx, cy = cell(body.place()[0], self.rest_y[body.i], BODY)
            radius, heat = flare_size(speed)
            self.field.burn(cx, cy, cx, cy, radius, heat)

    def paint(self, cv):
        super().paint(cv)
        for i in range(N):
            x, y = self.stepper.place(i)
            cv.fill(x, y, BODY, BODY, COAL)
