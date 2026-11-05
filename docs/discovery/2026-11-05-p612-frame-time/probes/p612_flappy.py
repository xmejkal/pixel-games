# P612 probe (throwaway): flappy's paint split by part, with no frame cap or a chosen one, optionally with P602's fire.
# Run: set FIRE and CAP, then `mpremote connect /dev/cu.usbmodem1101 run p612_flappy.py > run109-p612-r1-flappy-nocap.log`.
# R1: FIRE 0, CAP 0 (run109). R2: FIRE 1, CAP 0 (run110). R4: FIRE 0, CAP 33 (run111).
import time

import app
import pictures
from arcade import Flappy
from gfx import PLAY

FIRE = 0  # 1: P602's FireLayer + FireTrail, copied verbatim from 324c23d games/arcade.py
CAP = 0  # app.FRAME_MS for this run; 0 still sleeps 1 ms a frame
SECONDS = 47

if FIRE:
    from effects import FireTrail
    from fire import FireLayer

    FIRE_LOOK = (32, 40, 1, 0, 1, 128, 0, 16)
    FIRE_RADIUS = 3
    FIRE_HEAT = 200
    FIRE_LAG = 0.5
    FIRE_SEED = 602
    BIRD_BOX = 14

CAPPED = [0, 0]  # play frames at the 60 ms dt cap, play frames
T = {}  # part -> [sum us, max us, calls], play frames only
ORDER = []


def mark(name, t):
    now = time.ticks_us()
    d = time.ticks_diff(now, t)
    s = T.get(name)
    if s is None:
        s = T[name] = [0, 0, 0]
        ORDER.append(name)
    s[0] += d
    s[2] += 1
    if d > s[1]:
        s[1] = d
    return now


class Probe(Flappy):
    def __init__(self):
        if FIRE:
            self.layer = FireLayer(FIRE_LOOK, FIRE_SEED)
            self.trail = None
            if self.layer.field is not None:
                self.trail = FireTrail(self.layer.field, BIRD_BOX, FIRE_RADIUS, FIRE_HEAT, FIRE_LAG)
        super().__init__()

    def setup(self):
        super().setup()
        if FIRE:
            self.layer.clear()
            if self.trail is not None:
                self.trail.reset()

    def die(self, x=None, y=None, colours=None):
        pass  # the autopilot plays on

    def step(self, now_ms, pressed, held):
        if self.state == PLAY and self.last is not None:
            CAPPED[1] += 1
            if time.ticks_diff(now_ms, self.last) >= 60:
                CAPPED[0] += 1
        super().step(now_ms, pressed, held)

    def play(self, pressed, held):
        t = time.ticks_us()
        nxt = [p for p in self.pipes if p[0] + self.PW > self.X - 8][0]
        pressed = self.vy > 0 and self.y > nxt[1] + 8  # the autopilot
        Flappy.play(self, pressed, held)
        t = mark("play", t)
        if FIRE:
            speed = 95 + min(self.score, 20) * 3
            cells = self.layer.update(int(self.dt * 1000 + 0.5), speed)
            if self.trail is not None:
                self.trail.scroll(-cells)
                self.trail.update(self.X - BIRD_BOX // 2, int(self.y) - BIRD_BOX // 2)
            mark("fire update", t)

    def paint_art(self, cv):
        t = time.ticks_us()
        for name in self.BACK:
            if not pictures.draw_layers(cv, self.dist, True, "flappy", (name,)):
                return False
            t = mark(name, t)
        half = self.GAP // 2
        for x, gap_y, _ in self.pipes:
            pictures.draw(cv, "flappy_pipe_top", x, gap_y - half - 240)
            pictures.draw(cv, "flappy_pipe_bottom", x, gap_y + half)
        t = mark("pipes", t)
        pictures.draw_layers(cv, self.dist, True, "flappy", ("flappy_ground",))
        t = mark("ground", t)
        if FIRE:
            self.layer.draw(cv)
            t = mark("fire draw", t)
        tilt = 0 if self.vy < -60 else 2 if self.vy > 120 else 1
        wing = 0 if self.t - self.flapped < 0.12 else int(self.t * 6) % 2
        pictures.draw(cv, self.BIRDS[tilt][wing], self.X - 9, self.y - 7)
        mark("bird", t)
        return True


class Done(Exception):
    pass


START = time.ticks_ms()
_frame = app.App.frame


def frame(self):
    _frame(self)
    if time.ticks_diff(time.ticks_ms(), START) > SECONDS * 1000:
        raise Done


app.App.frame = frame
app.FRAME_MS = CAP
print("probe p612 fire %d cap %d" % (FIRE, CAP))
try:
    app.run(games=(Probe,))
except Done:
    pass
for name in ORDER:
    s = T[name]
    print("part %s calls %d avg %.2f max %.2f ms" % (name, s[2], s[0] / s[2] / 1000, s[1] / 1000))
print("capped %d of %d play frames" % tuple(CAPPED))
