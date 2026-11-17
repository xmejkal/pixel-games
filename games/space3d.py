"""Two more 3D games for one button: starfire (tap fires at the sweeping crosshair) and SMILE (tap when the city
camera's lens faces you). With the joystick (P872), starfire's crosshair goes the way the stick leans, faster the
further it leans, and stays where it is when the stick rests; FIRE fires at it."""

import math
import random
import time

import pictures
from cues import Cue
from engine.subpixel import SubPixel
from gfx import (ACCENT, BEST, CYAN, GREEN, GREY, HEIGHT, ORANGE, OVER, RED, WHITE, WIDTH, YELLOW, Dice, Game,
                 Particles, c565, shade)

W, H = WIDTH, HEIGHT
CX, CY = W // 2, 128


def stop(motion, v, low, high):
    """v, a place that motion (a SubPixel) moved to, kept from low to high; at a bound motion keeps no rest. --- MVP
    (P872) ---"""
    if v < low or v > high:
        motion.reset()
        return low if v < low else high
    return v


class Starfire(Game):
    name = "starfire"
    hint = "tap fires"
    stick_hint = "stick aims, fire fires"  # --- MVP (P872) ---
    bg = c565(2, 2, 10)
    accent = CYAN
    F, STARS = 150, 40
    AREA = (50, 40, 270, 200)
    # --- MVP (P872) --- the stick's aim: px a second at a full lean, and the crosshair's middle at most, so its wings
    # (15 px across, 10 px down) stay in AREA
    AIM_PX_S = 240
    AIM_LEFT, AIM_RIGHT = 65, 255
    AIM_TOP, AIM_BOTTOM = 55, 185
    HEX = [(math.cos(i * 1.047), math.sin(i * 1.047)) for i in range(6)]

    def setup(self):
        self.stars = [[random.uniform(-4, 4), random.uniform(-3, 3), random.uniform(0.3, 4)] for _ in range(self.STARS)]
        self.rocks, self.booms, self.lives, self.spawn, self.shot = [], [], 3, 0.8, 0.0
        self.aim = (CX, CY)
        self.aim_x, self.aim_y = SubPixel(), SubPixel()  # --- MVP (P872) --- the stick's aim, each axis's rest

    def project(self, x, y, z):
        k = self.F / z
        return CX + x * k, CY + y * k

    def play(self, pressed, held):
        dt, t = self.dt, self.t
        if self.stick is None:
            self.aim = (CX + 95 * math.sin(t * 1.9), CY + 55 * math.sin(t * 1.3 + 1))
        else:  # --- MVP (P872) --- before the shot, so a press fires at this frame's aim
            self.steer(self.stick.x, self.stick.y)
        for s in self.stars:
            s[2] -= 1.6 * dt
            if s[2] < 0.2:
                s[:] = [random.uniform(-4, 4), random.uniform(-3, 3), 4.0]
        speed = 0.9 + min(self.score, 30) * 0.03
        for r in self.rocks:
            r[2] -= speed * dt
            r[3] += dt * 2
        for r in [r for r in self.rocks if r[2] < 0.6]:
            self.rocks.remove(r)
            self.lives -= 1
            self.fx.burst(CX, H - 20, RED, 10, 120.0, 0.5)
        if self.lives <= 0:
            return self.die(CX, H - 40)
        self.spawn -= dt
        if self.spawn <= 0 and len(self.rocks) < 4:
            self.rocks.append([random.uniform(-1.6, 1.6), random.uniform(-1.0, 1.0), 6.0, 0.0])
            self.spawn = max(0.5, 1.6 - self.score * 0.04)
        self.shot = max(0.0, self.shot - dt)
        for b in self.booms:
            b[2] += dt
        self.booms = [b for b in self.booms if b[2] < 0.35]
        if pressed:
            self.fire()

    # --- MVP (P872) ---
    def steer(self, x, y):
        """The stick's x and y, -100 to 100 (up reads negative), move the crosshair at AIM_PX_S * x // 100 px a second
        across and the same for y down, in whole px, so it rests when the stick rests. It stops at the AIM_ bounds, with
        no rest kept there. aim is a new tuple only when a px moved, so a stick at rest makes nothing."""
        ax, ay = self.aim
        nx = stop(self.aim_x, ax + self.aim_x.step(self.AIM_PX_S * x // 100, self.ms), self.AIM_LEFT, self.AIM_RIGHT)
        ny = stop(self.aim_y, ay + self.aim_y.step(self.AIM_PX_S * y // 100, self.ms), self.AIM_TOP, self.AIM_BOTTOM)
        if nx != ax or ny != ay:
            self.aim = (nx, ny)

    def fire(self):
        self.shot = 0.1
        ax, ay = self.aim
        for r in sorted(self.rocks, key=lambda r: r[2]):
            sx, sy = self.project(r[0], r[1], r[2])
            reach = self.F * 0.25 / r[2] + 9
            if abs(sx - ax) < reach and abs(sy - ay) < reach:
                self.rocks.remove(r)
                self.booms.append([sx, sy, 0.0])
                self.fx.burst(sx, sy, ORANGE, 12, 140.0, 0.6, 0.0)
                self.score += 1
                return

    def paint_static(self, cv):
        cv.clip = self.AREA
        cv.gradient(40, 200, (4, 2, 24), (24, 6, 40), 16)  # a faint nebula
        cv.disc(236, 76, 20, c565(60, 50, 110))  # a far planet with a shadow
        cv.disc(242, 72, 14, c565(100, 90, 170))
        cv.clip = (0, 0, W, H)
        cv.box(49, 39, 222, 162, c565(60, 60, 110))
        cv.line(CX - 24, 215, CX, 201, GREY)  # the nose of your ship, under the picture
        cv.line(CX + 24, 215, CX, 201, GREY)

    def paint(self, cv):
        cv.clip = self.AREA
        for x, y, z in self.stars:
            sx, sy = self.project(x, y, z)
            px, py = self.project(x, y, z + 0.25)
            if not (50 < sx < 270 and 40 < sy < 200 and 50 < px < 270 and 40 < py < 200):
                continue
            cv.line(px, py, sx, sy, shade(200, 220, 255, 1.2 - z / 4))
        for x, y, z, spin in sorted(self.rocks, key=lambda r: -r[2]):
            sx, sy = self.project(x, y, z)
            r = self.F * 0.25 / z
            c, s = math.cos(spin), math.sin(spin)
            pts = [(sx + r * (hc * c - hs * s), sy + r * (hs * c + hc * s)) for hc, hs in self.HEX]
            colour = shade(255, 140, 60, 1.4 - z / 6)
            for i in range(6):
                a, b = pts[i], pts[(i + 1) % 6]
                cv.line(a[0], a[1], b[0], b[1], colour)
                cv.line(a[0], a[1], sx, sy, shade(160, 80, 40, 1.4 - z / 6))
            cv.fill(sx - 1, sy - 1, 3, 3, WHITE)
        for bx, by, age in self.booms:
            r = 6 + age * 160
            cv.box(bx - r, by - r, 2 * r, 2 * r, YELLOW if age < 0.18 else ORANGE)
        ax, ay = self.aim
        if self.shot > 0:
            cv.line(CX, 196, ax, ay, WHITE)
        cv.box(ax - 10, ay - 10, 20, 20, GREEN)
        cv.fill(ax - 15, ay, 8, 1, GREEN)
        cv.fill(ax + 7, ay, 8, 1, GREEN)
        for i in range(self.lives):
            cv.fill(W - 16 - i * 14, 22, 10, 10, RED)


# SMILE's picture names, made once (P573): no formatting while drawing. The lens in its three sizes (far, middle,
# near), each in its three iris poses; the walkers' backs and faces, each in two steps; the face in the monitor.
LENS_SIZES = (22, 30, 38)
IRIS_POSES = ("shut", "half", "open")
LENSES = tuple(tuple("cube_lens_%d_%s" % (d, pose) for pose in IRIS_POSES) for d in LENS_SIZES)
LIGHTS = ("cube_light_0", "cube_light_1")
TARGETS = ("cube_target_0", "cube_target_1")
FLARES = ("cube_flare_0", "cube_flare_1")
WALKERS = (("cube_walker_back_0", "cube_walker_back_1"), ("cube_walker_face_0", "cube_walker_face_1"))
FACES = ("cube_face_neutral", "cube_face_smile", "cube_face_frozen")
STAMPS = ("cube_stamp_ok", "cube_stamp_flag")
ZOOMS = ("cube_zoom_0", "cube_zoom_1", "cube_zoom_2")
IRISES = ("cube_iris_0", "cube_iris_1", "cube_iris_2")
CUBE_DIGITS = tuple("cube_digit_%d" % d for d in range(10))


class Housing:
    """The camera's housing as drawn: its eight corners, the top's middle and the recording light projected into
    lists made once (the rules' project, its sums in the same order, so the lens is where the rules say), which of its
    faces face you (a face of the cube, seen from the eye D away, faces you when its turned normal points toward you
    by more than 1 / D), and each visible face's corners as a polygon's points."""

    # each face's corners in order round it: x+, z+, x-, z-, the top (the bottom never faces you)
    FACES = ((1, 3, 7, 5), (4, 5, 7, 6), (0, 2, 6, 4), (0, 1, 3, 2), (0, 1, 5, 4))
    TOP = 4
    CENTRE, LIGHT = 8, 9  # the points after the corners: the top's middle, the recording light

    def __init__(self, game):
        self.game = game
        self.points3d = tuple(game.VERTS) + ((0, -1, 0), (0.55, -1, 0.55))
        n = len(self.points3d)
        self.x, self.y, self.z = [0.0] * n, [0.0] * n, [0.0] * n
        self.seen = [False] * 5
        self.facing = [0.0] * 5  # each side's turned normal across the screen: below 0 it faces left
        self.points = [[[0, 0] for _ in range(4)] for _ in range(5)]
        edges = []  # each edge: its two corners and the two faces it joins (-1: the bottom, never seen)
        for a, b in game.EDGES:
            joined = [k for k in range(5) if a in self.FACES[k] and b in self.FACES[k]]
            edges.append((a, b, joined[0], joined[1] if len(joined) > 1 else -1))
        self.edges = tuple(edges)

    def update(self, yaw):
        g = self.game
        c, s = math.cos(yaw), math.sin(yaw)
        tc, ts, f, d = g.TC, g.TS, g.F, g.D
        for i in range(len(self.points3d)):  # CubeTiming.project, written out: no tuple a corner
            x, y, z = self.points3d[i]
            x, z = x * c + z * s, -x * s + z * c
            y, z = y * tc - z * ts, y * ts + z * tc
            k = f / (z + d)
            self.x[i] = CX + x * k
            self.y[i] = 116 + y * k
            self.z[i] = z
        limit = -1 / d
        self.seen[0], self.facing[0] = -s * tc < limit, c  # x+: its normal (1, 0, 0) turned
        self.seen[1], self.facing[1] = c * tc < limit, s  # z+
        self.seen[2], self.facing[2] = s * tc < limit, -c  # x-
        self.seen[3], self.facing[3] = -c * tc < limit, -s  # z-
        self.seen[self.TOP] = -ts < limit
        for k in range(5):
            if self.seen[k]:
                corners, pts = self.FACES[k], self.points[k]
                for j in range(4):
                    pts[j][0] = self.x[corners[j]]
                    pts[j][1] = self.y[corners[j]]

    def lens_seen(self):
        """Whether the marked corner (7) faces you: one of its faces, x+ or z+, does."""
        return self.seen[0] or self.seen[1]


class Sway:
    """The cables' sway: a damped spring (stack's), kicked sideways by each speed-up, so the camera's web shivers
    when it turns faster. The housing itself stays at its exact projection: it is the timing cue."""

    SPRING, DAMP, KICK = 60.0, 4.0, 90.0  # about 1.2 Hz, settled in about 1.5 s; a kick swings it about 8 px

    def __init__(self):
        self.x, self.v = 0.0, 0.0

    def kick(self):
        self.v += self.KICK

    def update(self, dt):
        self.v -= (self.SPRING * self.x + self.DAMP * self.v) * dt
        self.x += self.v * dt


class Verdict:
    """The camera's last verdict on you: COMPLIANT at a good tap, FLAGGED at a miss, and when (ms), for the stamp,
    the flash and the face in the monitor."""

    NONE, OK, FLAG = 0, 1, 2
    SHOW_MS = 700  # the stamp and the face's pose hold this long
    SLAM_MS = 80  # the stamp lands: its first 2 frames drawn off its place, the flash at the lens
    FLASH_MS = 40  # COMPLIANT: the monitor white this long, one frame at the box's 40 ms pace

    def __init__(self):
        self.kind, self.at = self.NONE, 0

    def give(self, kind, ms):
        self.kind, self.at = kind, ms

    def age(self, now):
        """ms since the verdict, or -1 when there is none or it has passed."""
        if self.kind == self.NONE:
            return -1
        age = time.ticks_diff(now, self.at)
        return age if age < self.SHOW_MS else -1


class CubeTiming(Game):
    """SMILE (P573): a city camera hangs in a web of cables over a square at 22:00, against the full moon, and turns.
    When its lens faces you, smile: tap. On time it flashes and stamps you COMPLIANT, and turns faster; too early,
    too late or not at all and it stamps you FLAGGED, and the walkers round the square turn to look at you. The third
    flag ends it: the camera zooms into your face, the face pixelates, and the card says PROFILE COMPLETE. Night ink:
    ink, bone and one accent, the recording light's."""

    name = "cube"
    ART = ("cube", None)  # its own art set, all of it (P822)
    hint = "tap when the lens faces you"
    bg = c565(8, 8, 24)
    accent = c565(230, 60, 220)
    INK, BONE = c565(18, 16, 26), c565(232, 224, 204)  # art/looks.py's NightInk, with gfx's ACCENT
    HUD_SCORE, HUD_BEST = BONE, BONE
    cues = {"good": Cue("pickup"), "miss": Cue("siren"), "die": Cue("die")}
    F, D, TILT, MARK = 200, 5.0, 0.6, 7
    TC, TS = math.cos(0.6), math.sin(0.6)
    _yaw, _c, _s = None, 1.0, 0.0
    TARGET = 3 * math.pi / 4  # the yaw at which vertex 7, (1, 1, 1), looks straight at you
    VERTS = [((i & 1) * 2 - 1, ((i >> 1) & 1) * 2 - 1, ((i >> 2) & 1) * 2 - 1) for i in range(8)]
    EDGES = [(a, a | b) for a in range(8) for b in (1, 2, 4) if not a & b]

    # --- the painted look: art/sets/cube.py's sizes and places, which the board has no art/ to read
    # (tests/test_paint.py pins them), and the feel's numbers, set by eye on Mac frames of tools/render_scene.py
    SHADES = (c565(42, 39, 56), c565(27, 25, 38), c565(66, 62, 82))  # the sides, lit and shaded, and the top
    PANEL, CABLE = c565(84, 80, 100), c565(100, 96, 112)  # the housing's inset panels; the cables
    JOINT = (160, 24)  # the cables meet here; the stub hangs from it to the top's middle
    ANCHORS = ((14, 52), (306, 52), (30, 112), (290, 112))
    SAG = 6  # px the cables hang at their middles
    DEPTHS = (0.6, 0.0)  # the lens is far beyond the first z, near under the second
    LIGHT, TARGET_PX, FLARE, WALKER_W, WALKER_H = 7, 48, 40, 12, 22
    RING = (160, 212, 132, 8)  # the walkers' ring: its middle and radii
    FACE_BOX, FACE, FACE_X, FACE_Y = (256, 168, 316, 234), 48, 262, 180
    LIVES_RIGHT, LIVES_TOP = 311, 171
    BOARD_RIGHT, BOARD_TOP, DIGIT_W = 87, 45, 8  # the billboard's plate for the score
    BAR_X, BAR_Y, BAR_HALF = 150, 228, 100
    STAMP_W, STAMP_H, STAMP_X, STAMP_Y = 128, 40, 188, 188
    CONE_ALPHA, CONE_LOCK_ALPHA = 46, 120  # the lens's light toward the monitor; brighter inside the window
    NEAR = 2.0  # the iris is half open within this many tolerances of the target
    SPARKS = 6  # the flash's bone sparks at a good tap, on the game's own Dice
    ZOOM, ZOOM_X, ZOOM_Y, ZOOM_MS = 128, 96, 24, 150  # the zoom into the face: three pictures, 150 ms each
    CARD_X, CARD_Y, CARD_MS = 58, 158, 500
    SCORE_RIGHT, BEST_RIGHT, CARD_PLATE_TOP = 131, 209, 207  # the card's plates' right ends and top
    TITLE_IRIS, TITLE_IRIS_X, TITLE_IRIS_Y = 72, 124, 74
    TITLE_BEST_RIGHT, TITLE_BEST_TOP = 207, 203
    IRIS_MS, LIGHT_ON_MS = 200, 900  # the title's iris opens a pose each IRIS_MS; its light comes on at LIGHT_ON_MS
    BLINK_MS = 300  # the recording light's blink, on the game's clock (age: ms since play or the title began)

    def setup(self):
        self.yaw, self.w, self.lives, self.done, self.flash, self.rev = 0.0, 2.2, 3, False, 0.0, 0
        self.good = False
        self.covers = pictures.load(*self.ART)  # the painted square covers the screen, so no fill goes under it
        self.housing = Housing(self)
        self.sway, self.verdict = Sway(), Verdict()
        self.dice = Dice(5733)  # the effects' own random stream: the rules' draws stay as they are
        self.glints = Particles()  # the flash's bone sparks, apart from the rules' fx
        self.cone = [[0, 0], [0, 0], [0, 0]]  # the lens's light: a triangle made once
        tx, ty, _ = self.project(self.VERTS[self.MARK], self.TARGET)
        self.target_x, self.target_y = int(tx), int(ty)  # where the lens must be when you smile

    def tol(self):
        return min(0.5, self.w * 0.12)

    def err(self):
        return (self.yaw - self.TARGET + math.pi) % (2 * math.pi) - math.pi

    def project(self, v, yaw):
        if yaw != self._yaw:  # the sine and cosine of one yaw serve all eight corners
            self._yaw, self._c, self._s = yaw, math.cos(yaw), math.sin(yaw)
        x, y, z = v
        x, z = x * self._c + z * self._s, -x * self._s + z * self._c
        y, z = y * self.TC - z * self.TS, y * self.TS + z * self.TC
        k = self.F / (z + self.D)
        return CX + x * k, 116 + y * k, z

    def miss(self):
        self.lives -= 1
        self.flash, self.good = 0.25, False
        x, y, _ = self.project(self.VERTS[self.MARK], self.yaw)
        self.fx.burst(x, y, ACCENT, 8, 100.0, 0.4)
        self.verdict.give(Verdict.FLAG, self.last)
        if self.lives <= 0:
            self.die(x, y, (ACCENT, self.BONE))
        else:
            self.emit("miss")

    def play(self, pressed, held):
        self.yaw += self.w * self.dt
        self.flash = max(0.0, self.flash - self.dt)
        rev = int((self.yaw - self.TARGET + math.pi) // (2 * math.pi))
        if rev != self.rev:  # the mark went round again
            self.rev = rev
            if not self.done:
                self.miss()
            self.done = False
        if pressed:
            if self.done or abs(self.err()) > self.tol():
                self.miss()
                self.done = True
            else:
                self.done, self.good, self.flash = True, True, 0.25
                self.score += 1
                x, y, _ = self.project(self.VERTS[self.MARK], self.yaw)
                self.pop(x, y, self.BONE)
                self.w = min(5.5, self.w * 1.08)
                self.smiled(x, y)

    def smiled(self, x, y):
        """A good tap at the lens (x, y): the sound, COMPLIANT, the cables kicked by the speed-up, the flash's
        sparks."""
        self.emit("good")
        self.verdict.give(Verdict.OK, self.last)
        self.sway.kick()
        dice = self.dice
        for _ in range(self.SPARKS):
            self.glints.add(x + dice.spread(3), y + dice.spread(3), dice.spread(110), dice.spread(110), self.BONE,
                            0.2 + dice.below(25) / 100, 60.0)

    def step(self, now_ms, pressed, held):
        """Game.step; then the cables sway and the flash's sparks fly."""
        super().step(now_ms, pressed, held)
        self.sway.update(self.dt)
        if self.glints.p:
            self.glints.update(self.dt)

    def over_ms(self):
        """ms since the last life went: age is read before the frame's play, so in the frame of the loss it is still
        play's."""
        return time.ticks_diff(self.last, self.since)

    def inside(self):
        """Whether a tap now would be on time: the lap not tapped yet and the mark within the tolerance."""
        return not self.done and abs(self.err()) <= self.tol()

    def iris(self):
        """The lens's iris: open inside the window, half open as the mark comes near it, else shut."""
        e = abs(self.err())
        if e <= self.tol():
            return 2
        return 1 if e <= self.tol() * self.NEAR else 0

    def lens_size(self, z):
        """The lens's size for the marked corner's depth: 0 far, 1 middle, 2 near."""
        return 0 if z > self.DEPTHS[0] else 1 if z > self.DEPTHS[1] else 2

    def face_pose(self):
        """The face in the monitor: frozen at a flag and at the end, a forced smile at COMPLIANT, else neutral."""
        if self.state == OVER:
            return 2
        age = self.verdict.age(self.last)
        if age < 0:
            return 0
        return 1 if self.verdict.kind == Verdict.OK else 2

    def paint_static(self, cv):
        if pictures.draw(cv, "cube_square", 0, 0):  # the painted square (P573)
            return
        cv.fill(CX - 100, 229, 200, 3, c565(50, 50, 70))  # the timing bar's track

    def paint(self, cv):
        """The walkers round the square, the cables, the lens's light, the housing's faces, panels and edges, the
        stub, the recording light, the lens and its flash, the target, the monitor and its stamp, the lives, the bar,
        the billboard's score and the flash's sparks."""
        if not (self.covers and getattr(cv, "pictures", False)):
            return self.paint_flat(cv)
        h = self.housing
        h.update(self.yaw)
        mark = self.MARK
        mx, my, mz = h.x[mark], h.y[mark], h.z[mark]
        seen, age = h.lens_seen(), self.verdict.age(self.last)
        flagged = self.state == OVER or (age >= 0 and self.verdict.kind == Verdict.FLAG)
        self.draw_walkers(cv, flagged)
        jx = self.JOINT[0] + int(self.sway.x)
        self.draw_cables(cv, jx)
        lock = self.inside()
        if seen:
            self.draw_cone(cv, mx, my, lock)
        self.draw_housing(cv, h)
        tx, ty = h.x[h.CENTRE], h.y[h.CENTRE]
        cv.line(jx, self.JOINT[1], tx, ty, self.BONE)  # the stub
        cv.line(jx + 1, self.JOINT[1], tx + 1, ty, self.INK)
        pictures.draw(cv, LIGHTS[self.age // self.BLINK_MS % 2], int(h.x[h.LIGHT]) - 3, int(h.y[h.LIGHT]) - 3)
        if seen:
            k = self.lens_size(mz)
            half = LENS_SIZES[k] // 2
            pictures.draw(cv, LENSES[k][self.iris()], int(mx) - half, int(my) - half)
            if age >= 0 and age < Verdict.SLAM_MS and self.verdict.kind == Verdict.OK:
                half = self.FLARE // 2
                pictures.draw(cv, FLARES[age * 2 // Verdict.SLAM_MS], int(mx) - half, int(my) - half)
        half = self.TARGET_PX // 2
        pictures.draw(cv, TARGETS[1 if lock else 0], self.target_x - half, self.target_y - half)
        self.draw_monitor(cv, age, lock)
        self.draw_bar(cv, lock)
        self.number(cv, self.score, self.BOARD_RIGHT, self.BOARD_TOP)
        self.glints.draw(cv)

    def draw_walkers(self, cv, flagged):
        """The walkers' ring, turning with the camera: each faces the camera (its back to you) on the near half and
        you on the far half; at a flag and at the end every one has turned to look at you. Each steps as it goes."""
        cx, cy, rx, ry = self.RING
        spin = self.yaw * 0.7
        for near in (0, 1):  # the far half first, so the near walkers stand in front
            for i in range(16):
                a = spin + i * math.pi / 8
                s = math.sin(a)
                if (s > 0) != near:
                    continue
                kind = 1 if flagged or s <= 0 else 0
                step = int(a * 4) % 2
                pictures.draw(cv, WALKERS[kind][step], int(cx + rx * math.cos(a)) - self.WALKER_W // 2,
                              int(cy + ry * s) - self.WALKER_H + 2)

    def draw_cables(self, cv, jx):
        """The cables from the joint to the wall plates, each sagging at its middle."""
        jy = self.JOINT[1]
        for ax, ay in self.ANCHORS:
            mx, my = (jx + ax) // 2, (jy + ay) // 2 + self.SAG
            cv.line(jx, jy, mx, my, self.CABLE)
            cv.line(mx, my, ax, ay, self.CABLE)

    def draw_cone(self, cv, mx, my, lock):
        """The lens's light toward the monitor's face: one see-through triangle, brighter inside the window."""
        cone = self.cone
        cone[0][0], cone[0][1] = int(mx), int(my)
        cone[1][0], cone[1][1] = self.FACE_X, self.FACE_Y
        cone[2][0], cone[2][1] = self.FACE_X, self.FACE_Y + self.FACE
        cv.poly(cone, self.BONE, self.CONE_LOCK_ALPHA if lock else self.CONE_ALPHA)

    def draw_housing(self, cv, h):
        """The housing's faces that face you, filled in their ink shades (the top lightest, a side lit when it faces
        left), an inset panel on each side, then their edges in bone: the exact projection, the timing's truth."""
        for k in range(5):
            if not h.seen[k]:
                continue
            pts = h.points[k]
            shade_ = self.SHADES[2] if k == h.TOP else self.SHADES[0 if h.facing[k] < 0 else 1]
            cv.poly(pts, shade_)
            if k != h.TOP:  # the panel: the face's corners drawn a quarter of the way in toward its middle
                mx = (pts[0][0] + pts[1][0] + pts[2][0] + pts[3][0]) / 4
                my = (pts[0][1] + pts[1][1] + pts[2][1] + pts[3][1]) / 4
                for j in range(4):
                    a, b = pts[j], pts[(j + 1) % 4]
                    cv.line(mx + (a[0] - mx) * 0.74, my + (a[1] - my) * 0.74, mx + (b[0] - mx) * 0.74,
                            my + (b[1] - my) * 0.74, self.PANEL)
        for a, b, f, g in h.edges:
            if h.seen[f] or (g >= 0 and h.seen[g]):
                cv.line(h.x[a], h.y[a], h.x[b], h.y[b], self.BONE)

    def draw_monitor(self, cv, age, lock):
        """The face in the monitor in its pose; the white frame of COMPLIANT's flash; a bone frame round the face
        while a tap would be on time; the stamp, landing off its place for its first frames; the lives."""
        x, y, n = self.FACE_X, self.FACE_Y, self.FACE
        ok = self.verdict.kind == Verdict.OK
        if age >= 0 and age < Verdict.FLASH_MS and ok:
            cv.fill(x, y, n, n, self.BONE)
        else:
            pictures.draw(cv, FACES[self.face_pose()], x, y)
        if lock:
            cv.box(x - 2, y - 2, n + 4, n + 4, self.BONE)
        if age >= 0:
            slam = 4 if age < Verdict.SLAM_MS else 0
            pictures.draw(cv, STAMPS[0 if ok else 1], self.STAMP_X - slam, self.STAMP_Y - slam)
        for i in range(3):
            x = self.LIVES_RIGHT - 6 - i * 9
            if i < self.lives:
                cv.fill(x, self.LIVES_TOP, 6, 6, ACCENT)
            else:
                cv.box(x, self.LIVES_TOP, 6, 6, self.CABLE)

    def draw_bar(self, cv, lock):
        """The timing bar: the window (the tolerance) as a box, filled bone while a tap would be on time, and the
        mark's place in it, a bone needle."""
        bar = int(self.tol() * 60)
        x, y = self.BAR_X, self.BAR_Y
        if lock:
            cv.fill(x - bar, y, 2 * bar, 6, self.BONE)
        else:
            cv.box(x - bar, y, 2 * bar, 6, self.BONE)
        needle = x + int(max(-self.BAR_HALF, min(self.BAR_HALF, self.err() * 60)))
        cv.fill(needle - 1, y - 3, 3, 12, self.INK if lock else self.BONE)

    def number(self, cv, value, right, top):
        """value in digit pictures, right-aligned at right, the last digit first."""
        x, rest = right, value
        while True:
            x -= self.DIGIT_W
            pictures.draw(cv, CUBE_DIGITS[rest % 10], x, top)
            rest //= 10
            if not rest:
                return

    def paint_flat(self, cv):
        """The look before SMILE, where there is no art: a wire cube over a ring of dots, a box where the mark must
        be, a full-screen flash at each tap. It stays for the st7789 backend, ORIENTATION 180 and a board without the
        cube pack, where pictures.draw answers False; lcd.TftOut clears the frame under it each time, as it does for
        a canvas without pictures however covers stands."""
        if self.flash > 0:
            cv.fill(0, 16, W, H, c565(0, 70, 20) if self.good else c565(90, 10, 10))
        for i in range(16):  # a ring of dots turns under the cube
            a = self.yaw * 0.7 + i * math.pi / 8
            cv.fill(CX + 120 * math.cos(a), 210 + 8 * math.sin(a), 3, 3, shade(130, 60, 170, 0.5 + 0.5 * math.sin(a)))
        pts = [self.project(v, self.yaw) for v in self.VERTS]
        for a, b in self.EDGES:
            marked = self.MARK in (a, b)
            near = 1.2 - (pts[a][2] + pts[b][2] + 2.8) / 5.6  # nearer edges are brighter
            colour = WHITE if marked else shade(230, 60, 220, near)
            cv.line(pts[a][0], pts[a][1], pts[b][0], pts[b][1], colour)
        tx, ty, _ = self.project(self.VERTS[self.MARK], self.TARGET)  # where the mark must be when you tap
        inside = abs(self.err()) <= self.tol()
        cv.box(tx - 14, ty - 14, 28, 28, GREEN if inside else c565(90, 90, 100))
        mx, my, _ = pts[self.MARK]
        cv.fill(mx - 4, my - 4, 9, 9, GREEN if inside else YELLOW)
        bar = int(self.tol() * 60)  # a timing bar: the mark runs through the green zone
        cv.fill(CX - bar, 227, 2 * bar, 6, c565(30, 140, 60))
        cv.fill(CX + max(-100, min(100, self.err() * 60)) - 1, 224, 3, 10, YELLOW)
        for i in range(self.lives):
            cv.fill(W - 16 - i * 14, 22, 10, 10, RED)

    def draw_hud(self, cv):
        """The score bar as the camera's own overlay: the recording light and REC, the score, CAM 07 at 22:00 and
        the best, drawn again only when the score or the best change."""
        if not self.covers:
            return Game.draw_hud(self, cv)
        cv.fill(0, 0, WIDTH, 16, self.INK)
        cv.fill(6, 5, 6, 6, ACCENT)
        cv.text("REC", 16, 4, self.BONE)
        cv.big(str(self.score), 48, 0, self.BONE, 2)
        cv.text("CAM 07  22:00", 108, 4, self.CABLE)
        best = "best %d" % max(self.score, BEST.get(self.name, 0))
        cv.text(best, WIDTH - 8 * len(best) - 6, 4, self.BONE)
        cv.fill(0, 15, WIDTH, 1, self.CABLE)

    def draw_title(self, cv):
        """SMILE: the title card; the great lens on the moon opens its iris a pose each IRIS_MS, and the recording
        light comes on at LIGHT_ON_MS and blinks; the best on its plate."""
        if not pictures.draw(cv, "cube_title", 0, 0):
            return Game.draw_title(self, cv)
        a = self.age
        pictures.draw(cv, IRISES[min(2, a // self.IRIS_MS)], self.TITLE_IRIS_X, self.TITLE_IRIS_Y)
        if a >= self.LIGHT_ON_MS:
            pictures.draw(cv, LIGHTS[a // self.BLINK_MS % 2], self.TITLE_IRIS_X + self.TITLE_IRIS - 10,
                          self.TITLE_IRIS_Y + 2)
        self.number(cv, BEST.get(self.name, 0), self.TITLE_BEST_RIGHT, self.TITLE_BEST_TOP)

    def draw_over(self, cv):
        """The camera zooms into your face, three pictures ZOOM_MS each, the face pixelating; then PROFILE
        COMPLETE with the score and the best."""
        ms = self.over_ms()
        if not pictures.draw(cv, ZOOMS[min(2, ms // self.ZOOM_MS)], self.ZOOM_X, self.ZOOM_Y):
            return Game.draw_over(self, cv)
        if ms < self.CARD_MS:
            return
        pictures.draw(cv, "cube_over", self.CARD_X, self.CARD_Y)
        self.number(cv, self.score, self.SCORE_RIGHT, self.CARD_PLATE_TOP)
        self.number(cv, BEST.get(self.name, 0), self.BEST_RIGHT, self.CARD_PLATE_TOP)
        if self.age >= self.OVER_MS and (self.age // 400) % 2 == 0:
            cv.text("tap to retry", self.CARD_X + 47, self.CARD_Y + 66, self.BONE)
