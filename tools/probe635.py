# P635 slice 0 probe (board only): what jointed silhouette figures cost in the burning scene. It times each drawing
# primitive and four ways to draw one figure once, then plays BurningBodies with N figures walking (or burning) for
# SECONDS, drawn the WAY chosen. Run: mpremote run tools/probe635.py; it imports only the board's modules, so it
# copies nothing. N, WAY and BURN are set by sed before each run. The App's own "time" lines are the result.
import math
import time

import app
import burning
from effects import FireTrail
from lcd import PANEL_H, PANEL_W

N = 12  # figures
WAY = 1  # 0 cv.line, 1 tft.line, 2 polygon chains, 3 fill_polygon quads per bone
BURN = 0  # 1: every figure carries a FireTrail, as a burning figure will
SECONDS = 60
PHASES = 16  # baked poses of one walk cycle
SPEED = 30  # px/s, an adult's walk
BLACK = 0

# The figure (game px, y down, origin at the feet, facing right): legs 7 + 7, torso 9, arms 5 + 5, head r 3
THIGH, SHIN, TORSO, UPPER, FORE, HEAD = 7, 7, 9, 5, 5, 3


def point(x, y, length, deg):
    """The end of a bone of this length from (x, y), at deg from straight down, forward positive."""
    a = math.radians(deg)
    return x + length * math.sin(a), y + length * math.cos(a)


def pose(p):
    """The 10 segments and the head's centre at phase p of a walk: a sine walk (P635 plan, Williams' four keys)."""
    s = math.sin(2 * math.pi * p)
    hip = (0.0, -(THIGH + SHIN) + 1.0 * abs(s))
    neck = point(hip[0], hip[1], TORSO, 180 - 4)
    segs = [(hip, neck)]
    for side in (1, -1):
        swing = 25 * s * side
        knee = point(hip[0], hip[1], THIGH, swing)
        foot = point(knee[0], knee[1], SHIN, swing - 5 - 30 * max(0.0, -s * side))
        elbow = point(neck[0], neck[1], UPPER, -20 * s * side)
        hand = point(elbow[0], elbow[1], FORE, -20 * s * side + 20)
        segs += [(hip, knee), (knee, foot), (neck, elbow), (elbow, hand)]
    hand = segs[-1][1]
    segs.append((hand, (hand[0] + 2, 0.0)))  # the cane, to the ground
    head = point(neck[0], neck[1], HEAD, 180)
    return segs, head


def panel(dx, dy, turned):
    """A game offset as a panel offset (lcd.TftCanvas.fill's map without the origin)."""
    return (-dy, dx) if turned else (dy, -dx)


def bake(turned):
    """Per phase: the segments as panel offsets (x0, y0, x1, y1), the second line of each 2 px pair, the head, the
    3 chains as point lists, and one 2 px quad per bone; all made once."""
    poses = []
    for k in range(PHASES):
        segs, head = pose(k / PHASES)
        lines = []
        for (x0, y0), (x1, y1) in segs:
            px0, py0 = panel(x0, y0, turned)
            px1, py1 = panel(x1, y1, turned)
            ox, oy = (0, 1) if abs(px1 - px0) > abs(py1 - py0) else (1, 0)  # the 2 px rule: across the line
            lines.append((int(px0), int(py0), int(px1), int(py1), ox, oy))
        hx, hy = panel(head[0], head[1], turned)
        chains = []
        for f1, b1, b2, f2 in ((2, 1, 5, 6), (4, 3, 7, 8)):  # legs: foot, knee, hip, knee, foot; arms likewise
            ends = (lines[f1][2:4], lines[f1][0:2], lines[b1][0:2], lines[b2][2:4], lines[f2][2:4])
            chains.append([[px, py] for px, py in ends])
        chains.append([[lines[0][0], lines[0][1]], [lines[0][2], lines[0][3]], [lines[9][2], lines[9][3]]])
        quads = [[[a, b], [c, d], [c + ox, d + oy], [a + ox, b + oy]] for a, b, c, d, ox, oy in lines]
        poses.append((lines, (int(hx), int(hy)), chains, quads))
    return poses


def origin(x, turned):
    """The panel point of a figure's feet at game (x, HEIGHT - 1)."""
    y = burning.HEIGHT - 1
    return (PANEL_W - 1 - y, x) if turned else (y, PANEL_H - 1 - x)


class Probe(burning.BurningBodies):
    def setup(self):
        super().setup()
        self.fx_x = [(i * 320 // max(N, 1) + 7) % 320 for i in range(N)]
        self.fx_phase = [i * 5 % PHASES for i in range(N)]
        self.trails = [FireTrail(self.field, 8, burning.RADIUS, burning.HEAT, burning.LAG) for _ in range(N)] \
            if BURN and self.field is not None else []
        self.poses = None
        self.walk = 0.0
        self.figure_us = [0, 0]

    def play(self, pressed, held):
        super().play(pressed, held)
        self.walk += self.dt * SPEED
        step = int(self.walk)
        self.walk -= step
        for i in range(N):
            self.fx_x[i] = (self.fx_x[i] + step) % 320
            self.fx_phase[i] = (self.fx_phase[i] + 1) % PHASES
        for i, trail in enumerate(self.trails):
            trail.update(self.fx_x[i] - 4, burning.HEIGHT - 20)

    def paint(self, cv):
        super().paint(cv)
        if self.poses is None:
            self.poses = bake(cv.turned)
            bench(cv, self.poses)
        t = time.ticks_us()
        for i in range(N):
            draw(cv, WAY, self.poses[self.fx_phase[i]], self.fx_x[i])
        self.figure_us[0] += time.ticks_diff(time.ticks_us(), t)
        self.figure_us[1] += 1


def draw(cv, way, baked, x):
    lines, head, chains, quads = baked
    tft, turned = cv.tft, cv.turned
    ox0, oy0 = origin(x, turned)
    if way == 0:  # through the canvas, in game coordinates: the wrapper's cost per call
        gy = burning.HEIGHT - 1
        for a, b, c, d, ox, oy in lines:
            ga, gb = (b, -a) if turned else (-b, a)  # the panel offset back to a game offset
            gc, gd = (d, -c) if turned else (-d, c)
            cv.line(x + ga, gy + gb, x + gc, gy + gd, BLACK)
            cv.line(x + ga + oy, gy + gb + ox, x + gc + oy, gy + gd + ox, BLACK)
    elif way == 1:  # the driver's line, twice for 2 px, with the map done once per figure
        line = tft.line
        for a, b, c, d, ox, oy in lines:
            line(ox0 + a, oy0 + b, ox0 + c, oy0 + d, BLACK)
            line(ox0 + a + ox, oy0 + b + oy, ox0 + c + ox, oy0 + d + oy, BLACK)
    elif way == 2:  # 3 polygon chains, 1 px; the driver closes each, so this times the cost, not the look
        for pts in chains:
            tft.polygon(pts, ox0, oy0, BLACK)
    else:  # one 2 px quad per bone, filled
        for q in quads:
            tft.fill_polygon(q, ox0, oy0, BLACK)
    tft.fill_circle(ox0 + head[0], oy0 + head[1], HEAD, BLACK)


def timed(label, n, fn):
    t = time.ticks_us()
    for _ in range(n):
        fn()
    print("call %s %.1f us" % (label, time.ticks_diff(time.ticks_us(), t) / n))


def bench(cv, poses):
    tft = cv.tft
    quad = [[100, 100], [112, 100], [112, 102], [100, 102]]
    five = [[100, 100], [106, 107], [100, 114], [94, 107], [100, 100]]
    timed("tft.line 12px", 500, lambda: tft.line(100, 100, 112, 106, BLACK))
    timed("tft.line 12px x2", 500, lambda: (tft.line(100, 100, 112, 106, BLACK), tft.line(100, 101, 112, 107, BLACK)))
    timed("cv.line 12px", 500, lambda: cv.line(100, 100, 112, 106, BLACK))
    timed("fill_circle r3", 500, lambda: tft.fill_circle(100, 100, 3, BLACK))
    timed("polygon 5", 500, lambda: tft.polygon(five, 0, 0, BLACK))
    timed("fill_polygon 4", 500, lambda: tft.fill_polygon(quad, 0, 0, BLACK))
    for way in range(4):
        timed("figure way %d" % way, 200, lambda: draw(cv, way, poses[3], 160))


class Done(Exception):
    pass


START = time.ticks_ms()
_frame = app.App.frame
GAME = []


def frame(self):
    _frame(self)
    if not GAME and isinstance(self.game, Probe):
        GAME.append(self.game)
    if time.ticks_diff(time.ticks_ms(), START) > SECONDS * 1000:
        raise Done


app.App.frame = frame
print("probe p635 n %d way %d burn %d" % (N, WAY, BURN))
try:
    app.run(games=(Probe,))
except Done:
    pass
if GAME and GAME[0].figure_us[1]:
    us, frames = GAME[0].figure_us
    print("figures %d way %d burn %d: %.2f ms a frame over %d frames" % (N, WAY, BURN, us / frames / 1000, frames))
