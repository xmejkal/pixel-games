"""Detailed characters at 96 px (P904's spike): the runs of art/mocap.py painted with a face, hands, clothes, a
headwear and gear, to see whether the detail shows at that size. The fireman has a turnout coat, gloves, a helmet
and an air tank; CAST holds him and the other characters, each a Character record with its own cycle. It is in no
game and in no art set: art/paint.py does not call it, and the packs stay as they are.

One number, the height in px from the soles to the helmet's top, sets the size; a character's scale is its share
of it, and its headwear sits on top of its head. Every width and offset is a share of the body height, so the same
painter gives any height. The detail needs about 96 px: at 48 px the eye and the sole are under 1 px and do not
show.

Run from the repository root: python3 art/detailed.py --out DIR [--rim outline|none|lit] writes figure-sheet.png
(the fireman's twelve run poses, today's 26 px fireman beside them, two poses at 3x and one pose with each rim),
run.webp (both firemen run over Rescue's street at the captured speed), run-close.webp (the run in place at 2x and
about half speed), characters-sheet.png (each character of CAST in one pose of its run at 2x) and characters.webp
(all of them run over the street at once), and prints each run's box and bytes and the cast's total. The clips are
lossless animated WebP: a GIF's 256 colours band the street's night sky. It needs the CMU files in mocap.CMU_DIR
and paints nothing without them.
"""

import argparse
import os
import sys
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageOps

import mocap
from brush import Sprite, rnd
from export import Sheet, committed_index, from_bin, pack_bytes, q565
from sets.rescue import FEET, HELMET, HELMET_L, HELMET_TOP, Figure, along, dist, lighter

TALL = 96  # px from the soles to the helmet's top, standing
SEED = 904  # the grain's seed: two runs write the same files
COAT, TROUSERS = (198, 158, 84), (168, 132, 72)  # a tan turnout coat: shade shows on it after RGB565, on black not
BOOT, TREAD = (30, 28, 36), (92, 88, 100)  # TREAD: the boot's sole
SKIN, EYE, MOUTH = (236, 184, 146), (36, 28, 30), (150, 84, 74)
GLOVE = (104, 60, 40)
SEAM = (74, 62, 52)  # round the near arm where it lies on the body
TANK, STRAP, BUCKLE = (108, 124, 152), (44, 42, 52), (214, 190, 120)
SHIELD = (206, 48, 40)  # the helmet's front shield
FRAME_MS = 40  # one frame of the game
GAP, DARK = 6, (30, 16, 40)  # the sheets' gap between pictures; DARK: the street's sky at its middle (NIGHT)
CLOSE_MS = 120  # a pose of run-close.webp: about half the captured speed (a pose is 61 ms of the capture)


def box(height):
    """The picture a pose is painted in, w and h: wide enough for a stride, high enough for the run's flight."""
    return (round(height * 1.4), round(height * 1.2))


def darker(colour, k=0.7):
    return tuple(int(c * k) for c in colour)


def shade(colour):
    """A far limb's colour: darker, or lighter for a colour near black, which the dark street would swallow."""
    return darker(colour, 1.5 if max(colour) < 64 else 0.7)


COAT_DARK = darker(COAT, 0.62)  # the collar and the helmet's neck flap


def unit(a, b):
    d = dist(a, b)
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d)


def union(*masks):
    out = masks[0]
    for m in masks[1:]:
        out = ImageChops.lighter(out, m)
    return out


def pose_index(ran, stride, poses):
    """The pose after ran px of running, of poses in a cycle of stride px: as games/rescue.py picks it."""
    return ran * poses // stride % poses


class LitRim:
    """Today's rim (Figure.rim): 1 px left and right of the shape, warm on the side he faces and cool behind."""

    def apply(self, figure, img, right):
        return Figure.rim(figure, img, right)


class NoRim:
    """The shape alone."""

    def apply(self, figure, img, right):
        return img


class Outline:
    """A 1 px outline outside the shape: each pixel a dark shade of the colours it borders, so the dark boots and
    gloves keep their shape on a dark street. It adds a row over the helmet and a column at each side. Under the
    soles there is none: they stand on the picture's last row."""

    SHADE = 0.35

    def apply(self, figure, img, right):
        out, px = img.copy(), img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                if px[x, y][3]:
                    continue
                near = [px[q] for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                        if 0 <= q[0] < w and 0 <= q[1] < h and px[q][3]]
                if near:
                    out.putpixel((x, y), tuple(int(sum(c[i] for c in near) / len(near) * self.SHADE)
                                               for i in range(3)) + (255,))
        return out


RIMS = {"outline": Outline, "none": NoRim, "lit": LitRim}  # --rim's names; the first is the default


class Gear:
    """Something a character carries, painted at two hooks of DetailedFigure.paint: under, after the far leg and
    before the near leg and the torso (on the back), and over, after the torso (on the body). ahead: 1 facing right,
    -1 left, 0 at us. Each does nothing here."""

    def under(self, figure, s, p, ahead):
        pass

    def over(self, figure, s, p, ahead):
        pass


@dataclass(frozen=True)
class Tank(Gear):
    """The air tank on the back, under the coat's edge: a cylinder beside the spine, a valve under it."""

    colour: tuple = TANK
    valve: tuple = STRAP
    W, OUT = 0.085, 0.105  # its width, and how far behind the spine it is, in body heights

    def under(self, figure, s, p, ahead):
        out = -ahead * self.OUT * figure.PX
        top, low = p["thorax"], along(p["lowerback"], p["upperback"], 0.1)
        a, b = (top[0] + out, top[1]), (low[0] + out, low[1])
        figure.detail(s, s.shape("line", b, along(a, b, 1.22), width=self.W * figure.PX * 0.45), self.valve)
        figure.part(s, s.shape("line", a, b, width=self.W * figure.PX), self.colour)


@dataclass(frozen=True)
class Collar(Gear):
    """A turned-up collar round the neck."""

    colour: tuple = COAT_DARK

    def over(self, figure, s, p, ahead):
        figure.detail(s, s.shape("line", p["lowerneck"], along(p["lowerneck"], p["upperneck"], 0.3),
                                 width=figure.NECK * figure.PX * 1.7), self.colour)


@dataclass(frozen=True)
class Strap(Gear):
    """The tank's strap over the shoulder and down the chest."""

    colour: tuple = STRAP
    W = 0.022  # its width, in body heights

    def over(self, figure, s, p, ahead):
        _, torso, front = figure.trunk(s, p, ahead)
        px, shoulder, chest = figure.PX, p["lowerneck"], p["upperback"]
        strap = s.shape("line", (shoulder[0] - front * 0.5, shoulder[1] + self.W * px),
                        (chest[0] + front * 0.12, chest[1]), (p["lowerback"][0] + front * 0.2, p["lowerback"][1]),
                        width=self.W * px)
        figure.detail(s, ImageChops.multiply(strap, torso), self.colour)


@dataclass(frozen=True)
class Belt(Gear):
    """The belt round the waist, its buckle and a pouch."""

    colour: tuple = STRAP
    buckle: tuple = BUCKLE
    pouch: tuple = darker(STRAP, 1.5)
    W = 0.034  # its width, in body heights

    def over(self, figure, s, p, ahead):
        hips, torso, front = figure.trunk(s, p, ahead)
        px = figure.PX
        waist = along(hips, p["lowerback"], 0.75)
        ux, uy = unit(hips, p["lowerback"])
        half = figure.TORSO * px
        belt = s.shape("line", (waist[0] - uy * half, waist[1] + ux * half), (waist[0] + uy * half, waist[1] - ux * half),
                       width=self.W * px)
        figure.detail(s, ImageChops.multiply(belt, torso), self.colour)
        r = self.W * px * 0.42
        bx, by = waist[0] + front * 0.34, waist[1]
        figure.detail(s, s.shape("rect", bx - r, by - r, bx + r, by + r, r * 0.3), self.buckle)
        qx, qy, qw = waist[0] - front * 0.1, waist[1] + self.W * px * 0.5, self.W * px * 0.75
        figure.detail(s, s.shape("rect", qx - qw, qy, qx + qw, qy + qw * 2.2, qw * 0.3), self.pouch)


@dataclass(frozen=True)
class Bag(Gear):
    """A bag at the hip on a strap over the shoulder, with a cross on its side."""

    colour: tuple = (52, 128, 72)
    cross: tuple = (244, 244, 240)
    W, H, STRAP_W = 0.11, 0.085, 0.018  # its width and height, and its strap's width, in body heights

    def over(self, figure, s, p, ahead):
        hips, torso, front = figure.trunk(s, p, ahead)
        px = figure.PX
        cx, cy = hips[0] - front * 0.3, hips[1] - self.H * px * 0.2
        strap = s.shape("line", (p["lowerneck"][0] - front * 0.4, p["lowerneck"][1]), (cx + front * 0.2, cy),
                        width=self.STRAP_W * px)
        figure.detail(s, ImageChops.multiply(strap, torso), darker(self.colour, 0.6))
        w, h = self.W * px / 2, self.H * px / 2
        figure.part(s, s.shape("rect", cx - w, cy - h, cx + w, cy + h, h * 0.4), self.colour)
        arm, thick = h * 0.62, max(1.0, h * 0.34)
        figure.detail(s, union(s.shape("line", (cx - arm, cy), (cx + arm, cy), width=thick),
                               s.shape("line", (cx, cy - arm), (cx, cy + arm), width=thick)), self.cross)


class HeadView:
    """Where the head is and how it is turned, for the headwear's hooks: at(a, b), a place a head radii toward the
    screen's right of the head's up and b up; r, its radius in px; ahead, 1 facing right, -1 left, 0 at us; way, the
    side it faces (1 right, -1 left); frontal, how much it faces the viewer (0 in profile, 1 full face)."""

    def __init__(self, at, r, ahead):
        self.at, self.r, self.ahead = at, r, ahead
        self.way, self.frontal = (1 if ahead >= 0 else -1), 1 - abs(ahead)


class Headwear:
    """What a character wears on its head: rise, its top over the head joint; and three hooks of
    DetailedFigure.head, each given the HeadView: under, before the head's skin (behind the head); nape, after the
    skin and before the face; over, after the face. Each hook does nothing here."""

    def rise(self, head):
        """Its top over the head joint, in body heights, on a head of that radius (body heights)."""
        raise NotImplementedError

    def under(self, figure, s, view):
        pass

    def nape(self, figure, s, view):
        pass

    def over(self, figure, s, view):
        pass


@dataclass(frozen=True)
class Helmet(Headwear):
    """A fireman's helmet: the dome down to the brow, a short brim ahead and one tail head radii long behind, the
    shield at the front, and a neck flap over the back of the head down to the collar."""

    colour: tuple = HELMET
    light: tuple = HELMET_L
    shield: tuple = SHIELD
    tail: float = 2.15
    flap: tuple = COAT_DARK

    def rise(self, head):
        return HELMET_TOP

    def nape(self, figure, s, view):
        at, ahead, back = view.at, view.ahead, -view.way
        if view.frontal < 0.7:  # the neck flap, over the back of the head and down to the collar
            figure.detail(s, s.shape("poly", at(back * 0.25, 0.1), at(back * 1.7 * abs(ahead), -0.1),
                                     at(back * 1.3 * abs(ahead), -1.5), at(back * 0.1, -1.4)), self.flap)

    def over(self, figure, s, view):
        at, r, ahead, way, frontal = view.at, view.r, view.ahead, view.way, view.frontal
        top = self.rise(figure.HEAD) / figure.HEAD  # the dome's top, in head radii above the head joint
        dome = s.shape("poly", *[at(1.22 * c, 0.12 + (top - 0.12) * v) for c, v in
                                 ((-1.0, 0.0), (-0.92, 0.45), (-0.7, 0.78), (-0.38, 0.95), (0.0, 1.0), (0.38, 0.95),
                                  (0.7, 0.78), (0.92, 0.45), (1.0, 0.0))])
        peak, tail = abs(ahead) * 1.75 + frontal * 1.4, abs(ahead) * self.tail + frontal * 1.4
        brim = s.shape("line", at(way * peak, 0.08), at(0.0, 0.2), at(-way * tail, -0.12 * abs(ahead) + 0.08 * frontal),
                       width=r * 0.34)
        lx, ly = at(ahead * 0.5, top * 0.7)
        figure.detail(s, union(dome, brim), self.colour, light=(lx, ly, r * 0.9, self.light), rim=0.4)
        sx, sy = at(ahead * 0.78, 0.62)
        figure.detail(s, s.shape("ellipse", sx - r * 0.3, sy - r * 0.36, sx + r * 0.3, sy + r * 0.36), self.shield)


@dataclass(frozen=True)
class Hair(Headwear):
    """Hair: a cap over the top and the back of the head, and down head radii of it hanging behind the neck (0: short
    hair)."""

    colour: tuple = (70, 50, 36)
    down: float = 0.0
    TOP = 1.3  # the cap's top over the head joint, in head radii
    CAP = ((1.0, 0.42), (0.9, 0.85), (0.55, 1.18), (0.0, TOP), (-0.6, 1.2), (-1.02, 0.78), (-1.14, 0.1),
           (-0.98, -0.62), (-0.5, -0.66), (-0.2, -0.1), (0.35, 0.36))  # across and up in head radii, facing right

    def rise(self, head):
        return head * self.TOP

    def under(self, figure, s, view):
        if self.down:  # behind the head and the neck, so the head's skin is over its front
            at, back = view.at, -view.way
            figure.part(s, s.shape("poly", at(back * 0.2, 0.9), at(back * 1.1, 0.4), at(back * 1.2, -self.down),
                                   at(back * 0.25, -self.down * 0.92)), self.colour)

    def nape(self, figure, s, view):
        figure.part(s, s.shape("poly", *[view.at(view.way * a, b) for a, b in self.CAP]), self.colour)


@dataclass(frozen=True)
class Proportions:
    """A character's limbs against the capture's: leg, the share of each thigh and shin; arm, of each upper arm and
    forearm. fit(pose) gives a pose these proportions; a child's are shorter than an adult's."""

    leg: float = 1.0
    arm: float = 1.0
    LEG, FOOT = ("hipjoint", "femur", "tibia"), ("foot", "toes")  # a limb's joints, and those that follow its end
    ARM, HAND = ("clavicle", "humerus", "radius"), ("wrist", "hand", "fingers", "thumb")
    FEET = ("lfoot", "ltoes", "rfoot", "rtoes")

    def fit(self, pose):
        """The pose with each limb's two pieces scaled by its share in all three coordinates, a foot or a hand
        following its limb's end unchanged, then moved up or down so that its lowest foot joint is as high as before:
        a planted foot stays on the ground, a flight keeps its height. With both shares 1, the pose itself."""
        if (self.leg, self.arm) == (1, 1):
            return pose
        out = dict(pose)
        for share, limb, follow in ((self.leg, self.LEG, self.FOOT), (self.arm, self.ARM, self.HAND)):
            for side in "lr":
                joints = [side + n for n in limb]
                for a, b in zip(joints, joints[1:]):
                    out[b] = tuple(o + (q - p) * share for o, p, q in zip(out[a], pose[a], pose[b]))
                end = joints[-1]
                for n in (side + n for n in follow if side + n in pose):
                    out[n] = tuple(o + q - p for o, p, q in zip(out[end], pose[end], pose[n]))
        lift = min(pose[n][1] for n in self.FEET) - min(out[n][1] for n in self.FEET)
        return {n: (f, u + lift, d) for n, (f, u, d) in out.items()}


@dataclass(frozen=True)
class Character:
    """How a character looks on the detailed painter. scale: its height as a share of the painter's; head: its
    head's radius in body heights. The colours of its skin, its top, its legs, its boots and its hands (None: bare
    hands). sleeve and trouser: the share of the arm and of the leg in cloth, from the shoulder and the hip, the rest
    bare. shaft: a tall boot's or a sock's colour from the boot up the shin (None: a shoe). hem: how far down the
    thighs its top hangs, a share of them. bands: reflective bands on its top and trousers. Its headwear (a Headwear),
    its gear (Gear, in paint order) and its limbs' proportions (Proportions). The defaults are the fireman's. It is
    not art/sets/rescue.py's Look, which
    is how Rescue's 25 px people look."""

    name: str = "fireman"
    scale: float = 1.0
    head: float = 0.068
    skin: tuple = SKIN
    top: tuple = COAT
    legs: tuple = TROUSERS
    boots: tuple = BOOT
    hands: tuple = GLOVE
    sleeve: float = 1.0
    trouser: float = 1.0
    shaft: tuple = BOOT
    hem: float = 0.4
    bands: bool = True
    headwear: Headwear = Helmet()
    gear: tuple = (Tank(), Collar(), Strap(), Belt())  # the strap after the collar, or his 12 turned poses change
    proportions: Proportions = Proportions()


FIREMAN = Character()
RED = (200, 40, 44)
PARAMEDIC = Character("paramedic", skin=(246, 204, 176), top=RED, legs=RED, boots=(28, 26, 30), hands=(70, 130, 200),
                      shaft=None, hem=0.15, headwear=Hair((92, 56, 34), down=1.6), gear=(Bag(),))
FOOTBALLER = Character("footballer", skin=(150, 100, 68), top=(40, 160, 80), legs=(236, 236, 236), boots=(24, 24, 26),
                       hands=None, sleeve=0.45, trouser=0.45, shaft=(40, 160, 80), hem=0.0, bands=False,
                       headwear=Hair((26, 22, 24)), gear=())
CHILD = Character("child", scale=0.75, head=0.095, skin=(240, 194, 158), top=(250, 210, 60), legs=(60, 100, 200),
                  boots=(210, 50, 50), hands=None, sleeve=0.3, trouser=0.35, shaft=None, hem=0.0, bands=False,
                  headwear=Hair((150, 104, 60)), gear=(), proportions=Proportions(leg=0.75, arm=0.85))
CAST = ((FIREMAN, "run"), (PARAMEDIC, "woman"), (FOOTBALLER, "dogman"), (CHILD, "child"))  # each with its cycle


class DetailedFigure(Figure):
    """One pose of a character with detail, facing the way the pose does: a top with a hem, trousers, boots with
    soles or shoes, reflective bands, hands from the wrist to the fingers, a face on the side the nose is, and the
    character's headwear and gear (the fireman: a tan coat, gloves, a helmet with a neck flap, an air tank, a collar
    and a belt). The numbers below are shares of the body height. Figure gives the joints' places and the bands as
    whole pixels. The part and the band here are not Figure's: a part is shaded, and a band scales with the height.
    rim is the figure's edge, one of RIMS; character is a Character."""

    SOLE = 0.038  # from the toe joint down to the boot's underside
    THIGH, SHIN, UPPER, FORE = (0.115, 0.095), (0.095, 0.075), (0.095, 0.08), (0.08, 0.07)  # each limb's two widths
    TORSO, NECK = 0.17, 0.05  # the torso's and the neck's width
    SHAFT_W, FOOT_W, SOLE_W = 0.086, 0.06, 0.018
    GLOVE_W, CUFF = 0.066, 0.022
    BAND, SEAM_W = 0.024, 0.014

    def __init__(self, size, height=TALL, rim=None, character=FIREMAN):
        super().__init__(size)
        self.character, self.HEAD = character, character.head  # HEAD: the head's radius
        self.PX = height * character.scale / (1 + HELMET_TOP + self.SOLE)
        self.edge = rim or Outline()

    def at(self, joint):
        x, y, _ = joint
        return (self.w / 2 + self.HIPS + x * self.PX, self.h - (self.SOLE + y) * self.PX)

    def paint(self, pose):
        pose = self.character.proportions.fit(pose)
        s = Sprite(self.w, self.h)
        self.bands = Image.new("L", s.size, 0)
        p = {n: self.at(v) for n, v in pose.items()}
        near = "r" if pose["rhipjoint"][2] >= pose["lhipjoint"][2] else "l"
        far = "l" if near == "r" else "r"
        ahead = max(-1.0, min(1.0, (p["nose"][0] - p["head"][0]) / (0.1 * self.PX)))  # 1 right, -1 left, 0 at us
        toward = pose["nose"][2] >= pose["head"][2]  # the face is on our side of the head, or level with it
        self.arm(s, p, far, True)
        self.leg(s, p, far, True)
        for gear in self.character.gear:
            gear.under(self, s, p, ahead)
        self.leg(s, p, near, False)
        self.torso(s, p)
        for gear in self.character.gear:
            gear.over(self, s, p, ahead)
        self.head(s, p, ahead, toward)
        self.arm(s, p, near, False)
        return self.edge.apply(self, self.banded(s.cut(outline=False)), ahead >= 0)

    # --- the brush -----------------------------------------------------------------------------------------------

    def part(self, s, mask, colour, band=None):
        """A shaded part over what is painted: a light on its upper half, a darker wet rim, a faint grain. It hides
        the bands under it. band: the mask of its own band."""
        found = mask.getbbox()
        if found is None:
            return
        x0, y0, x1, y1 = (v / s.S for v in found)
        light = ((x0 + x1) / 2, y0 + (y1 - y0) * 0.35, max(x1 - x0, y1 - y0) * 0.4, lighter(colour))
        s.part(mask, colour, light=light, rim=0.45, grain=0.05)
        self.bands = ImageChops.subtract(self.bands, mask)
        if band is not None:
            self.bands = ImageChops.lighter(self.bands, ImageChops.multiply(mask, band))

    def detail(self, s, mask, colour, light=None, rim=0):
        """A part with no grain: a small flat one (an eye, a mouth, a buckle), or one with a light and a rim (the
        helmet's dome, light and rim as brush.Sprite.part takes them). It hides the bands under it."""
        s.part(mask, colour, light=light, rim=rim, grain=0)
        self.bands = ImageChops.subtract(self.bands, mask)

    def taper(self, s, a, b, widths, square=False):
        """A limb from a to b with round ends, widths[0] of a body height wide at a and widths[1] at b. square: the
        end at b cut square."""
        wa, wb = (w * self.PX / 2 for w in widths)
        ux, uy = unit(a, b)
        quad = s.shape("poly", (a[0] - uy * wa, a[1] + ux * wa), (a[0] + uy * wa, a[1] - ux * wa),
                       (b[0] + uy * wb, b[1] - ux * wb), (b[0] - uy * wb, b[1] + ux * wb))
        if square:
            return union(quad, s.shape("ellipse", a[0] - wa, a[1] - wa, a[0] + wa, a[1] + wa))
        return union(quad, s.shape("ellipse", a[0] - wa, a[1] - wa, a[0] + wa, a[1] + wa),
                     s.shape("ellipse", b[0] - wb, b[1] - wb, b[0] + wb, b[1] + wb))

    def cover(self, s, joints, widths, share):
        """The cloth of a short sleeve or of shorts: the first share of a limb's length along its three joints,
        cut square. widths: each of its two pieces' (taper)."""
        a, b, c = joints
        first, second = dist(a, b), dist(b, c)
        reach = share * (first + second)
        if reach <= first:
            t = reach / first
            return self.taper(s, a, along(a, b, t), (widths[0][0], widths[0][0] + (widths[0][1] - widths[0][0]) * t),
                              True)
        t = (reach - first) / second
        return union(self.taper(s, a, b, widths[0]),
                     self.taper(s, b, along(b, c, t), (widths[1][0], widths[1][0] + (widths[1][1] - widths[1][0]) * t),
                                True))

    def band(self, s, a, b, t):
        """A reflective band across the limb from a to b, at t of the way: the mask of a line square to it, longer
        than any limb is wide."""
        cx, cy = along(a, b, t)
        ux, uy = unit(a, b)
        half = self.TORSO * self.PX
        return s.shape("line", (cx - uy * half, cy + ux * half), (cx + uy * half, cy - ux * half),
                       width=self.BAND * self.PX)

    def spine(self, s, p):
        """The middle of the hips, and the torso's mask from there to the neck."""
        hips = along(p["lhipjoint"], p["rhipjoint"], 0.5)
        return hips, s.shape("line", hips, p["lowerback"], p["upperback"], p["thorax"], p["lowerneck"],
                             width=self.TORSO * self.PX)

    def trunk(self, s, p, ahead):
        """The middle of the hips, the torso's mask, and front: px from the spine toward the side it faces."""
        hips, torso = self.spine(s, p)
        return hips, torso, ahead * self.TORSO * self.PX

    # --- the body ------------------------------------------------------------------------------------------------

    def limb(self, s, pieces, joints, widths, share, cloth, skin, band):
        """An arm or a leg: its two pieces in cloth, the second with its band; or, with share under 1, in skin with
        the cloth over the first share of it. A skin part gets no band."""
        if share < 1:
            self.part(s, union(*pieces), skin)
            self.part(s, self.cover(s, joints, widths, share), cloth, band)
            return
        self.part(s, pieces[0], cloth)
        self.part(s, pieces[1], cloth, band)

    def leg(self, s, p, side, far):
        c = self.character
        hip, knee, ankle = p[side + "hipjoint"], p[side + "femur"], p[side + "tibia"]
        ball, toe = p[side + "foot"], p[side + "toes"]
        cloth, boot, skin = (shade(c.legs), shade(c.boots), shade(c.skin)) if far else (c.legs, c.boots, c.skin)
        band = None if far or not c.bands else self.band(s, knee, ankle, 0.42)
        self.limb(s, (self.taper(s, hip, knee, self.THIGH), self.taper(s, knee, ankle, self.SHIN)), (hip, knee, ankle),
                  (self.THIGH, self.SHIN), c.trouser, cloth, skin, band)
        shaft = c.shaft  # None: a shoe
        if shaft is not None:
            self.part(s, self.taper(s, along(knee, ankle, 0.62), ankle, (self.SHAFT_W, self.SHAFT_W)),
                      shade(shaft) if far else shaft)
        self.part(s, s.shape("line", ankle, ball, toe, width=self.FOOT_W * self.PX), boot)
        ux, uy = unit(ankle, toe)  # the sole: under the foot, on the side away from the knee
        down = 1 if (ankle[0] - knee[0]) * -uy + (ankle[1] - knee[1]) * ux >= 0 else -1
        off = (self.FOOT_W / 2 + self.SOLE_W / 4) * self.PX * down
        heel = (ankle[0] - ux * self.FOOT_W * self.PX / 2, ankle[1] - uy * self.FOOT_W * self.PX / 2)
        self.detail(s, s.shape("line", (heel[0] - uy * off, heel[1] + ux * off), (toe[0] - uy * off, toe[1] + ux * off),
                               width=self.SOLE_W * self.PX), TREAD)

    def arm(self, s, p, side, far):
        c = self.character
        shoulder, elbow, wrist = p[side + "clavicle"], p[side + "humerus"], p[side + "radius"]
        cloth, skin = (shade(c.top), shade(c.skin)) if far else (c.top, c.skin)
        upper, fore = self.taper(s, shoulder, elbow, self.UPPER), self.taper(s, elbow, wrist, self.FORE)
        if not far:  # the near arm over the body: a seam round it, where it lies on what is painted
            seam = self.SEAM_W * 2
            wide = union(self.taper(s, shoulder, elbow, tuple(w + seam for w in self.UPPER)),
                         self.taper(s, elbow, wrist, tuple(w + seam for w in self.FORE)))
            self.detail(s, ImageChops.multiply(wide, s.alpha), SEAM)
        band = None if far or not c.bands else self.band(s, elbow, wrist, 0.62)
        self.limb(s, (upper, fore), (shoulder, elbow, wrist), (self.UPPER, self.FORE), c.sleeve, cloth, skin, band)
        self.hand(s, p, side, far)

    def hand(self, s, p, side, far):
        """From the wrist joint (radius) through the palm (wrist, hand) to the fingers: a glove with a cuff, or a bare
        hand of the glove's shape."""
        c = self.character
        colour = c.skin if c.hands is None else c.hands
        colour = shade(colour) if far else colour
        wrist, palm, hand, fingers = p[side + "radius"], p[side + "wrist"], p[side + "hand"], p[side + "fingers"]
        ux, uy = unit(palm, fingers)
        tip = (fingers[0] + ux * self.GLOVE_W * self.PX * 0.3, fingers[1] + uy * self.GLOVE_W * self.PX * 0.3)
        self.part(s, s.shape("line", wrist, palm, hand, tip, width=self.GLOVE_W * self.PX), colour)
        if c.hands is not None:  # the glove's cuff
            cx, cy = unit(wrist, palm)
            half = self.GLOVE_W * self.PX * 0.62
            self.detail(s, s.shape("line", (wrist[0] - cy * half, wrist[1] + cx * half),
                                   (wrist[0] + cy * half, wrist[1] - cx * half), width=self.CUFF * self.PX),
                        darker(colour, 0.6))

    def torso(self, s, p):
        """The top: the torso from the hips to the neck, and a hem that hangs over the tops of both thighs."""
        c = self.character
        _, torso = self.spine(s, p)
        half, margin = self.TORSO * self.PX / 2, self.THIGH[0] * self.PX * 0.62
        hems = sorted(along(p[k + "hipjoint"], p[k + "femur"], c.hem) for k in "lr")
        back, front = (hems[0][0] - margin, hems[0][1]), (hems[1][0] + margin, hems[1][1])
        waist = p["lowerback"]
        hem = s.shape("poly", (waist[0] - half, waist[1]), (waist[0] + half, waist[1]), front, back)
        lift = self.BAND * self.PX
        bands = union(self.band(s, p["upperback"], p["thorax"], 0.5),
                      s.shape("line", (back[0], back[1] - lift), (front[0], front[1] - lift), width=lift))
        self.part(s, union(torso, hem), c.top, bands if c.bands else None)

    # --- the head ------------------------------------------------------------------------------------------------

    def head(self, s, p, ahead, toward):
        """The neck, the head with its face, and the headwear at its three hooks. The head's own up is the line from
        the upper neck to the head joint, so the face tilts as the head does; ahead moves the face across the head as
        it turns toward the viewer."""
        c = self.character
        centre, r = p["head"], self.HEAD * self.PX
        ux, uy = unit(p["upperneck"], centre)  # the head's up, on the screen

        def at(a, b):
            """A place on the head: a head radii toward the screen's right of its up, b up."""
            return (centre[0] - uy * a * r + ux * b * r, centre[1] + ux * a * r + uy * b * r)

        view = HeadView(at, r, ahead)
        self.part(s, s.shape("line", p["lowerneck"], centre, width=self.NECK * self.PX), darker(c.skin, 0.85))
        c.headwear.under(self, s, view)
        cx, cy = centre
        self.part(s, s.shape("ellipse", cx - r, cy - r * 1.12, cx + r, cy + r * 1.12), c.skin)
        c.headwear.nape(self, s, view)
        if toward or view.frontal < 0.5:
            self.face(s, view)
        c.headwear.over(self, s, view)

    def face(self, s, view):
        """An eye (two as it turns to us), a nose past the head's edge and a mouth."""
        at, r, ahead, frontal = view.at, view.r, view.ahead, view.frontal
        e = r * 0.17
        for k in ((-1, 1) if frontal > 0.15 else (0,)):
            ex, ey = at(ahead * 0.5 + k * frontal * 0.42, -0.02)
            self.detail(s, s.shape("ellipse", ex - e, ey - e * 1.25, ex + e, ey + e * 1.25), EYE)
        self.detail(s, s.shape("poly", at(ahead * 0.86, 0.02), at(ahead * 1.24 + 0.18 * view.way * frontal, -0.34),
                               at(ahead * 0.8, -0.44)), darker(self.character.skin, 0.9))
        wide = 0.2 + 0.2 * frontal
        self.detail(s, s.shape("line", at(ahead * 0.62 - wide, -0.62), at(ahead * 0.62 + wide, -0.62), width=max(1.0, r * 0.14)),
                    MOUTH)


class RunPictures:
    """A character's run (cycle_name: a name in mocap.CYCLES or mocap.CROWD), its twelve poses from the capture, each
    painted on its own picture and all cut to the one box they use: pictures (RGBA, in the board's RGB565 colours)
    facing right and left, each the mirror of the right one, size, stride (px a cycle) and speed (px a second), both
    the capture's."""

    def __init__(self, capture, height, rim=None, seed=SEED, character=FIREMAN, cycle_name="run"):
        self.capture, self.height, self.rim, self.seed, self.character = capture, height, rim, seed, character
        self.cycle = next(c for c in mocap.CYCLES + mocap.CROWD if c.name == cycle_name)
        figure = self.figure()
        painted = [figure.paint(pose) for pose in capture.poses(self.cycle)]
        used = [img.getchannel("A").getbbox() for img in painted]
        x0, y0, x1 = min(b[0] for b in used), min(b[1] for b in used), max(b[2] for b in used)
        self.pictures = [q565(img.crop((x0, y0, x1, img.height))) for img in painted]
        self.left = [ImageOps.mirror(img) for img in self.pictures]  # as CapturedPictures.add in art/sets/rescue.py
        self.size = self.pictures[0].size
        self.stride = round(capture.stride(self.cycle) * figure.PX * character.proportions.leg)  # the feet keep still
        self.speed = self.stride * self.cycle.fps / capture.loop(self.cycle)[1]

    def figure(self, rim=None):
        """A painter of this run's height on the run's seed, with the run's rim or another."""
        rnd.seed(self.seed)
        return DetailedFigure(box(self.height), self.height, rim or self.rim, self.character)

    def size_bytes(self):
        """The run in a pack: RGB565, both facings."""
        w, h = self.size
        return w * h * 2 * len(self.pictures) * 2

    def picture(self, ran, left=False):
        """The picture after ran px of running, facing right or, with left, left."""
        return (self.left if left else self.pictures)[pose_index(ran, self.stride, len(self.pictures))]

    def alone(self, index, rim=None, turned=False):
        """One pose alone, cut to its own shape: with another rim, or turned toward the viewer as the wave is
        (mocap.VIEW)."""
        c = self.cycle
        cycle = mocap.Cycle(c.name, c.trial, c.fps, c.frames, c.period, c.poses, view=mocap.VIEW) if turned else c
        img = q565(self.figure(rim).paint(self.capture.poses(cycle)[index]))
        return img.crop(img.getchannel("A").getbbox())


class Committed:
    """Today's Rescue from the committed pack: the street and the 26 px fireman's run."""

    RUN_POSES, STRIDE_PX, SPEED_PX_S = 12, 41, 56  # games/rescue.py's numbers

    def __init__(self):
        self.art = committed_index()["ART"]
        self.street = self.read("rescue_night").convert("RGB")
        self.run = [self.read("rescue_run_r%d" % i) for i in range(self.RUN_POSES)]

    def read(self, name):
        return from_bin(pack_bytes(name), *self.art[name][:2])

    def picture(self, ran):
        return self.run[pose_index(ran, self.STRIDE_PX, self.RUN_POSES)]


def on_dark(pictures, zoom=1):
    """The pictures in a row on the street's dark, GAP px apart, their bottoms on one line, at zoom: so they read as
    on the board."""
    w = sum(img.width for img in pictures) + GAP * (len(pictures) + 1)
    h = max(img.height for img in pictures) + 2 * GAP
    row, x = Image.new("RGB", (w, h), DARK), GAP
    for img in pictures:
        row.paste(img, (x, h - GAP - img.height), img)
        x += img.width + GAP
    return row.resize((w * zoom, h * zoom), Image.Resampling.NEAREST)


class FigureSheet:
    """figure-sheet.png: the twelve poses in a row with today's fireman at their end, then one run pose and the
    pose turned toward the viewer at 3x, then that pose with each rim, on the street's dark."""

    ZOOM, POSE = 3, 3

    def __init__(self, run, old):
        self.run, self.old = run, old

    def image(self):
        run, (w, h) = self.run, self.run.size
        rows = [("the run's twelve poses at %d px, each %d by %d px, and today's 26 px fireman" % (run.height, w, h),
                 on_dark(run.pictures + [self.old.run[0]])),
                ("pose %d of the run, and the same pose turned toward the viewer, at %dx" % (self.POSE, self.ZOOM),
                 on_dark([run.alone(self.POSE), run.alone(self.POSE, turned=True)], self.ZOOM)),
                ("the rims (--rim): %s, at %dx" % (", ".join(RIMS), self.ZOOM),
                 on_dark([run.alone(self.POSE, rim()) for rim in RIMS.values()], self.ZOOM))]
        sheet = Sheet(max(img.width for _, img in rows) + 20, sum(img.height + 28 for _, img in rows) + 10)
        y = 6
        for label, img in rows:
            y = sheet.put(label, img, 10, y) + 10
        return sheet.image


class RunClip:
    """The fireman's clips' frames. frames(): both firemen run left to right over Rescue's street, each at its
    captured speed, a frame of the game apart. close(): the big run in place over the street at 2x, a pose a frame."""

    W = 320

    def __init__(self, run, old):
        self.run, self.old = run, old

    def frames(self):
        w, h = self.run.size
        count = int((self.W + w) / self.run.speed * 1000 / FRAME_MS) + 1
        out = []
        for i in range(count):
            frame = self.old.street.copy()
            small = self.old.SPEED_PX_S * i * FRAME_MS // 1000
            before = self.old.picture(small)
            frame.paste(before, (150 + small - before.width // 2, FEET - before.height + 1), before)
            ran = int(self.run.speed * i * FRAME_MS / 1000)
            frame.paste(self.run.picture(ran), (ran - w, FEET - h + 1), self.run.picture(ran))
            out.append(frame)
        return out

    def close(self, zoom=2):
        w, h = self.run.size
        left, top = (self.W - w) // 2 - 10, FEET - h - 9
        out = []
        for img in self.run.pictures:
            frame = self.old.street.crop((left, top, left + w + 20, FEET + 11))
            frame.paste(img, (10, 10), img)
            out.append(frame.resize((frame.width * zoom, frame.height * zoom), Image.Resampling.NEAREST))
        return out


class CharacterSheet:
    """characters-sheet.png: each runner of the cast in pose POSE of its run at ZOOM on the street's dark, its name
    under it."""

    ZOOM, POSE = 2, 3

    def __init__(self, runners):
        self.runners = runners

    def image(self):
        strip = on_dark([run.pictures[self.POSE] for run in self.runners], self.ZOOM)
        sheet = Sheet(strip.width + 20, strip.height + 52)
        y = sheet.put("pose %d of each character's run at %dx" % (self.POSE, self.ZOOM), strip, 10, 6)
        x = 10 + GAP * self.ZOOM
        for run in self.runners:
            sheet.draw.text((x, y + 4), run.character.name, fill=sheet.INK, font=sheet.font)
            x += (run.size[0] + GAP) * self.ZOOM
        return sheet.image


class CharacterClip:
    """characters.webp's frames: each runner over Rescue's street on its own row from TOP to BOTTOM (the row its soles
    are on), every second one running left on its left pictures, each at its own speed, a frame of the game apart.
    The smaller a runner's picture, the farther up the street its row, whatever order the runners come in. The farther
    runner is pasted first, so the nearer one is over it. The clip lasts as long as the slowest runner takes to cross
    the street once; each runner goes round a lap that its run over the clip fills a whole number of times, so every
    runner is at its start place again when the clip starts again (its place loops, its pose need not)."""

    W, TOP, BOTTOM = 320, 200, 238

    def __init__(self, runners, street):
        self.runners, self.street = runners, street
        n = len(runners)
        rank = sorted(range(n), key=lambda k: runners[k].size[1])  # the smallest picture first
        self.rows = [0] * n
        for place, k in enumerate(rank):
            self.rows[k] = self.TOP + (self.BOTTOM - self.TOP) * place // max(1, n - 1)
        self.runs_left = [k % 2 == 1 for k in range(n)]
        slow = min(runners, key=lambda run: run.speed)
        self.count = int((self.W + slow.size[0]) / slow.speed * 1000 / FRAME_MS) + 1
        self.laps = [self.lap(run) for run in runners]

    def ran(self, run, i):
        """px a runner has run at frame i."""
        return int(run.speed * i * FRAME_MS / 1000)

    def lap(self, run):
        """px a runner goes round in: its run over the clip, or the shortest whole share of it that is at least the
        street and its picture wide, so that it waits off the street and is back at its start when the clip ends."""
        whole = self.ran(run, self.count)
        laps = max(1, whole // (self.W + run.size[0]))
        while whole % laps:
            laps -= 1
        return whole // laps

    def places(self, i):
        """Frame i's runners, the farthest first: (x, row, picture) each, x the picture's left column."""
        n, out = len(self.runners), []
        for row, k in sorted(zip(self.rows, range(n))):
            run, w, lap = self.runners[k], self.runners[k].size[0], self.laps[k]
            ran = self.ran(run, i)
            at = (k * lap // n + ran) % lap  # each starts its own share of the way round
            out.append((self.W - at if self.runs_left[k] else at - w, row, run.picture(ran, self.runs_left[k])))
        return out

    def frames(self):
        out = []
        for i in range(self.count):
            frame = self.street.copy()
            for x, row, img in self.places(i):
                frame.paste(img, (x, row - img.height + 1), img)
            out.append(frame)
        return out


def cast_bytes(runners):
    """The lines main prints for the cast: each runner's box and bytes with both facings, then the total."""
    lines = ["%s (%s) at %d px: 12 poses of %d by %d px, %d bytes with both facings" % (
        run.character.name, run.cycle.name, run.height, run.size[0], run.size[1], run.size_bytes()) for run in runners]
    return lines + ["the cast: %d characters, %d bytes" % (len(runners), sum(run.size_bytes() for run in runners))]


def write_clip(frames, path, ms):
    """A looping animated WebP of the frames, ms each, lossless: every pixel is the frame's."""
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=ms, loop=0, lossless=True)


def main():
    parser = argparse.ArgumentParser(description="Paint the detailed characters' runs at %d px: two sheets and three "
                                                 "clips." % TALL)
    parser.add_argument("--out", required=True, metavar="DIR", help="the folder the five pictures are written to")
    parser.add_argument("--rim", choices=list(RIMS), default=next(iter(RIMS)),
                        help="the figure's edge: outline, a dark 1 px line all round; none; lit, today's warm and "
                             "cool rim (%(default)s)")
    parser.add_argument("--cmu", default=mocap.CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    args = parser.parse_args()
    capture = mocap.Capture(args.cmu)
    if capture.missing():
        parser.error("not in %s: %s" % (args.cmu, ", ".join(capture.missing())))
    runners = [RunPictures(capture, TALL, RIMS[args.rim](), character=c, cycle_name=name) for c, name in CAST]
    run, old = next(r for r in runners if r.character == FIREMAN), Committed()
    os.makedirs(args.out, exist_ok=True)
    FigureSheet(run, old).image().save(os.path.join(args.out, "figure-sheet.png"))
    clip = RunClip(run, old)
    write_clip(clip.frames(), os.path.join(args.out, "run.webp"), FRAME_MS)
    write_clip(clip.close(), os.path.join(args.out, "run-close.webp"), CLOSE_MS)
    CharacterSheet(runners).image().save(os.path.join(args.out, "characters-sheet.png"))
    write_clip(CharacterClip(runners, old.street).frames(), os.path.join(args.out, "characters.webp"), FRAME_MS)
    print("the rim: %s" % args.rim)
    print("\n".join(cast_bytes(runners)))


if __name__ == "__main__":
    sys.exit(main())
