"""CubeTiming's art as SMILE (P573): night ink at 22:00 (D4, D5), ink, bone and one accent. A city square at night,
drawn as an etching: bone line work on ink, lit windows, grain where the haze and the lamps glow. Over the square a
city camera hangs in a web of cables; the game draws its housing (the turning cube) and puts the lens on its marked
corner. A ring of people walks round the square under it. In the corner a monitor shows the one it watches: you.
Smile on time and the camera stamps you COMPLIANT; miss and it stamps you FLAGGED in the accent. At the end it zooms
into your face and the face pixelates: nobody is hurt, the profile is complete.

Every picture is painted here in ink and bone (the accent only on the recording light, the FLAGGED stamp and the
lives), and the set's look is NightInk(ACCENT), so what the board gets is those three colours and nothing else. Tones
are grain, bone dots laid at 1x with the chance of the tone, like a night camera's noise."""

from math import atan2, cos, hypot, pi, sin

from PIL import Image, ImageDraw

from artset import ArtSet, Painting
from brush import ACCENT, H, W, rnd
from city import sky_at
from letters import text_width, write
from looks import NightInk

INK, BONE = NightInk.INK, NightInk.BONE
LOOK = NightInk(ACCENT)
S = 4  # shapes are drawn at 4x and cut at half cover, so their edges are sampled, not stepped

# --- the places the game copies (tests/test_paint.py pins them against games/space3d.py) ---------------------------
VP = (160, 96)  # the square's vanishing point
FAR_BASE = 150  # the far side's foot
MOON = (160, 106, 84)  # the full moon behind the camera: its middle and radius
JOINT = (160, 24)  # where the cables meet over the camera; the stub hangs from it to the housing's top
ANCHORS = ((14, 52), (306, 52), (30, 112), (290, 112))  # the cables' wall plates
FACE_BOX = (256, 168, 316, 234)  # the monitor in the corner: its frame
FACE = 48  # the face picture, and where it sits in the monitor
FACE_AT = (262, 180)
LIVES_AT = (311, 171)  # the right end of the lives' marks, in the monitor's label row
BOARD = (6, 22, 94, 60)  # the scoring billboard
BOARD_PLATE = (40, 42, 90, 56)  # its plate for the score's digits
BAR_X, BAR_Y, BAR_HALF = 150, 228, 100  # the timing bar: its middle, its top row and its half width
LENS_SIZES = (22, 30, 38)  # far, middle, near
IRIS = ("shut", "half", "open")
LIGHT = 7
TARGET = 48  # the brackets frame the nearest lens (38 px) with room
WALKER = (12, 22)
RING = (160, 212, 132, 8)  # the walkers' ring: its middle, and its radii across and deep
STAMP = (128, 40)
STAMP_AT = (188, 188)  # over the monitor, its right end on the monitor's
FLARE = 40
ZOOM = 128
ZOOM_AT = (96, 24)
DIGIT_W, DIGIT_H = 8, 12
TITLE_IRIS = 72
TITLE_IRIS_AT = (124, 74)
TITLE_PLATE = (170, 200, 40, 17)  # x, y, w, h
CARD = (190, 78)
CARD_AT = (58, 158)
CARD_PLATES = ((36, 46), (114, 46))
PLATE_W, PLATE_H = 40, 17


# --- the plate: drawing in ink and bone at 1x, shapes cut from 4x masks ---------------------------------------------

class Etch:
    """A picture drawn in order at 1x: each shape is drawn at S times on a mask, shrunk and cut at half cover, then
    filled in one colour, so a later shape covers an earlier one. A tone is engraved as rows of dashes, every other
    row, each dash as long as the tone is bright."""

    def __init__(self, w, h, ground=INK):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w, h), ground)

    def mask(self, draw):
        """The 1x mask of what draw(d, s) draws at S times (d an ImageDraw on L, s the scale)."""
        big = Image.new("L", (self.w * S, self.h * S), 0)
        draw(ImageDraw.Draw(big), S)
        return big.resize((self.w, self.h), Image.BOX).point(lambda v: 255 if v >= 128 else 0)

    def fill(self, m, colour=BONE):
        self.img.paste(colour, (0, 0), m)

    def poly(self, pts, colour=BONE):
        self.fill(self.mask(lambda d, s: d.polygon([(x * s, y * s) for x, y in pts], fill=255)), colour)

    def line(self, pts, width=1.0, colour=BONE):
        self.fill(self.mask(lambda d, s: d.line([(x * s, y * s) for x, y in pts], fill=255,
                                                  width=max(1, round(width * s)), joint="curve")), colour)

    def ellipse(self, cx, cy, rx, ry, colour=BONE, width=0):
        def draw(d, s):
            box = ((cx - rx) * s, (cy - ry) * s, (cx + rx) * s, (cy + ry) * s)
            if width:
                d.ellipse(box, outline=255, width=max(1, round(width * s)))
            else:
                d.ellipse(box, fill=255)
        self.fill(self.mask(draw), colour)

    def words(self, text, x, y, unit, width, colour=BONE, centre=True):
        left = x - text_width(text, unit) / 2 if centre else x
        self.fill(self.mask(lambda d, s: write(d._image, text, left * s, y * s, unit * s, width * s)), colour)

    def px(self, x, y, colour=BONE):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.img.putpixel((int(x), int(y)), colour)

    def rect(self, x0, y0, x1, y1, colour=BONE):
        """Game px x0 to x1 - 1 and y0 to y1 - 1, exactly."""
        if x1 > x0 and y1 > y0:
            self.img.paste(colour, (int(x0), int(y0), int(x1), int(y1)))

    def frame(self, x0, y0, x1, y1, colour=BONE):
        """A 1 px frame round x0..x1 - 1, y0..y1 - 1."""
        self.rect(x0, y0, x1, y0 + 1, colour)
        self.rect(x0, y1 - 1, x1, y1, colour)
        self.rect(x0, y0, x0 + 1, y1, colour)
        self.rect(x1 - 1, y0, x1, y1, colour)

    def engrave(self, tone, colour=BONE, period=7, rows=2, where=None):
        """tone(x, y) -> 0 to 1, engraved: on every rows-th row, dashes period px apart, each tone * period long, the
        rows' dashes offset so they do not stack into columns; only where where(x, y) is true (all when None)."""
        px = self.img.load()
        for y in range(0, self.h, rows):
            phase = (y * 0.618) % 1.0
            for x in range(self.w):
                t = tone(x, y)
                if t > 0 and (x / period + phase) % 1.0 < t and (where is None or where(x, y)):
                    px[x, y] = colour

    def keyed(self, ground=INK):
        """The picture as a sprite: every ground pixel clear."""
        out = self.img.convert("RGBA")
        out.putdata([(0, 0, 0, 0) if p[:3] == ground else p for p in out.get_flattened_data()])
        return out

    def done(self):
        return self.img.convert("RGBA")


class Wall:
    """A wall seen at an angle, from its near edge to its far one: (u, v) on it, u 0 near to 1 far and v 0 top to 1
    foot, to the screen, with the far part foreshortened as perspective does (heights fall as 1 / depth)."""

    def __init__(self, nx, nt, nb, fx, ft, fb):
        self.nx, self.nt, self.nb, self.fx, self.ft, self.fb = nx, nt, nb, fx, ft, fb

    def at(self, u, v):
        hn, hf = self.nb - self.nt, self.fb - self.ft
        k = u * hf / ((1 - u) * hn + u * hf)
        top, bottom = self.nt + (self.ft - self.nt) * k, self.nb + (self.fb - self.nb) * k
        return self.nx + (self.fx - self.nx) * k, top + (bottom - top) * v

    def quad(self, u0, v0, u1, v1):
        return [self.at(u0, v0), self.at(u1, v0), self.at(u1, v1), self.at(u0, v1)]


def luma(c):
    return (299 * c[0] + 587 * c[1] + 114 * c[2]) / 1000


def haze(y):
    """The night's haze at row y, from the sky script's 22:00, as an engraving's tone: none at the top, a little over
    the roofs."""
    return max(0.0, (luma(sky_at(22, (y - 16) / (FAR_BASE - 16))) - 20) / 160)


# --- the square at 22:00 -----------------------------------------------------------------------------------------

def paint_sky(e):
    """The night: the haze low over the roofs, a few stars, and the full moon, engraved round its edge so it is a
    ball, its seas faint, and its halo in rows of dashes."""
    mx, my, r = MOON
    e.engrave(lambda x, y: haze(y) if FAR_BASE - 70 < y < FAR_BASE else 0, period=13, rows=4)
    for _ in range(30):
        x, y = rnd.uniform(0, W), rnd.uniform(17, 70)
        if hypot(x - mx, y - my) > r + 30:
            e.px(x, y)
    e.engrave(lambda x, y: max(0.0, 0.62 - (hypot(x - mx, y - my) - r) / 44) if hypot(x - mx, y - my) > r + 2 else 0,
              period=6)
    e.ellipse(mx, my, r, r)
    seas = Etch(W, H)  # the moon's seas: soft blots, engraved in ink
    for cx, cy, rx, ry in ((136, 70, 22, 14), (190, 60, 14, 10), (118, 120, 12, 18), (204, 128, 20, 12),
                           (176, 92, 10, 8), (100, 82, 8, 12)):
        seas.ellipse(cx, cy, rx, ry)
    seas_px = seas.img.load()
    e.engrave(lambda x, y: 0.35 if seas_px[x, y] == BONE else 0, INK, period=5,
              where=lambda x, y: hypot(x - mx, y - my) < r - 1)
    e.engrave(lambda x, y: max(0.0, (hypot(x - mx + 30, y - my + 26) - r * 0.98) / 34), INK, period=6,
              where=lambda x, y: hypot(x - mx, y - my) < r)  # the moon's far edge in shade


def rooftop(e, x, top, w):
    """What stands on a roof against the moon: a chimney, an aerial, a water tank or a camera on a pole."""
    kind = rnd.random()
    if kind < 0.25:
        e.rect(x + w * 0.3, top - 6, x + w * 0.3 + 3, top, INK)
    elif kind < 0.45:
        e.rect(x + w * 0.5, top - 12, x + w * 0.5 + 1, top, INK)
        e.rect(x + w * 0.5 - 3, top - 10, x + w * 0.5 + 4, top - 9, INK)
        e.rect(x + w * 0.5 - 2, top - 7, x + w * 0.5 + 3, top - 6, INK)
    elif kind < 0.6:
        e.rect(x + w * 0.2, top - 9, x + w * 0.2 + 8, top - 3, INK)
        e.rect(x + w * 0.2 + 1, top - 3, x + w * 0.2 + 2, top, INK)
        e.rect(x + w * 0.2 + 6, top - 3, x + w * 0.2 + 7, top, INK)
        e.poly([(x + w * 0.2 - 1, top - 9), (x + w * 0.2 + 4, top - 12), (x + w * 0.2 + 9, top - 9)], INK)
    else:
        px = x + w * 0.6
        e.rect(px, top - 10, px + 1, top, INK)
        e.rect(px - 1, top - 13, px + 5, top - 10, INK)
        e.rect(px + 5, top - 12, px + 6, top - 11, INK)


def window_grid(e, x0, y0, x1, y1, cw, ch, lit):
    """Lit windows in rows and columns in the box, a share lit of them: bone blocks, now and then with someone in
    them, a dark head and shoulders against the light."""
    y = y0
    while y + ch <= y1:
        x = x0
        while x + cw <= x1:
            if rnd.random() < lit:
                e.rect(x, y, x + cw, y + ch)
                if cw >= 3 and ch >= 5 and rnd.random() < 0.3:
                    e.rect(x + cw // 2 - 1, y + ch - 2, x + cw // 2 + 2, y + ch, INK)
                    e.px(x + cw // 2, y + ch - 3, INK)
            x += cw + 2
        y += ch + 3


def paint_far(e):
    """The far side of the square in silhouette against the moon: old houses, their roofs crowded with chimneys,
    aerials and cameras on poles, lit windows low down, and the town hall's tower with its clock at ten."""
    x = 44.0
    while x < 276:
        w, top = rnd.uniform(16, 30), rnd.uniform(58, 92)
        if 98 < x + w and x < 138:
            x = 138.0  # the tower's place
            continue
        e.rect(x, top, x + w, FAR_BASE, INK)
        if rnd.random() < 0.45:  # a gable
            e.poly([(x - 1, top + 0.5), (x + w / 2, top - w * 0.42), (x + w + 1, top + 0.5)], INK)
        else:
            e.rect(x - 1, top - 2, x + w + 1, top, INK)
            rooftop(e, x, top - 2, w)
        window_grid(e, x + 3, max(top + 6, 104), x + w - 2, FAR_BASE - 9, 2, 4, 0.3)
        x += w + rnd.uniform(0, 3)
    tx0, tx1, cx = 100, 136, 118  # the town hall's tower
    e.rect(tx0, 40, tx1, FAR_BASE, INK)
    e.poly([(tx0 - 3, 41), (cx, 8), (tx1 + 3, 41)], INK)
    e.rect(cx, 2, cx + 1, 10, INK)
    e.rect(tx0 - 3, 40, tx1 + 3, 43, INK)
    e.ellipse(cx, 56, 11, 11)
    e.ellipse(cx, 56, 9.4, 9.4, INK)
    for k in range(12):
        a = k * pi / 6
        e.px(cx + 8 * cos(a), 56 + 8 * sin(a))
    e.line([(cx, 56), (cx, 49)], 1.2)  # the minute hand at twelve
    e.line([(cx, 56), (cx - 4.6, 53.4)], 1.5)  # the hour hand at ten
    for y in range(76, FAR_BASE - 12, 12):  # its tall windows
        for wx in (tx0 + 6, tx1 - 10):
            e.rect(wx, y, wx + 4, y + 8, BONE if rnd.random() < 0.4 else INK)
    e.rect(tx0, FAR_BASE - 10, tx1, FAR_BASE - 9)


def paint_wall(e, wall, floors, bays, lit):
    """A near house front in perspective: its mass in ink, the roof edge and a cornice at each floor in bone, tall
    windows (lit ones bone, some with someone looking out; dark ones a bone sill), and an arcade at the foot."""
    e.poly(wall.quad(0, 0, 1, 1), INK)
    e.line([wall.at(0, 0), wall.at(1, 0)], 2.0)
    e.line([wall.at(1, 0), wall.at(1, 1)], 1.2)
    top = 0.07
    step = (1 - top - 0.22) / floors
    for f in range(floors + 1):
        v = top + f * step
        e.line([wall.at(0, v), wall.at(1, v)], 1.0 if f else 1.6)
    for f in range(floors):
        for b in range(bays):
            u0, u1 = (b + 0.22) / bays, (b + 0.78) / bays
            v0 = top + f * step + step * 0.18
            v1 = v0 + step * 0.66
            q = wall.quad(u0, v0, u1, v1)
            if rnd.random() < lit:
                e.poly(q)
                if rnd.random() < 0.35:  # someone at the window, dark against the lamp inside
                    (hx, hy) = wall.at((u0 + u1) / 2, v0 + (v1 - v0) * 0.55)
                    size = (q[1][0] - q[0][0]) * 0.22
                    e.ellipse(hx, hy, abs(size), abs(size) * 1.1, INK)
                    e.poly([wall.at(u0 + (u1 - u0) * 0.2, v1), wall.at((u0 + u1) / 2, v0 + (v1 - v0) * 0.6),
                            wall.at(u1 - (u1 - u0) * 0.2, v1)], INK)
            else:
                e.line([q[3], q[2]], 1.0)
    v0 = 1 - 0.22 + 0.03
    arches = bays + 1
    for b in range(arches):
        u0, u1 = (b + 0.1) / arches, (b + 0.9) / arches
        (x0, y0), (x1, _) = wall.at(u0, v0 + 0.05), wall.at(u1, v0 + 0.05)
        (_, ya), (_, yb) = wall.at(u0, 1), wall.at(u1, 1)
        top_y = y0 + abs(x1 - x0) * 0.3
        e.line([(x0, ya), (x0, top_y), ((x0 + x1) / 2, y0), (x1, top_y), (x1, yb)], 1.0)


def camera_icon(e, x, y, facing):
    """A small wall camera on its bracket: a bone box with its hood, the lens toward facing (1 right, -1 left)."""
    e.rect(x, y - 1, x + 2, y + 5)
    bx = x + (2 if facing > 0 else -8)
    e.rect(bx, y - 3, bx + 8, y + 1)
    e.rect(bx - (1 if facing < 0 else 0), y - 4, bx + 9 - (0 if facing < 0 else 1), y - 3)
    e.px(bx + (8 if facing > 0 else -1), y - 2)
    e.px(bx + (8 if facing > 0 else -1), y - 1)


def paint_sides(e):
    """The two near house fronts, the left and the right, cameras on brackets on both watching the square."""
    for wall in (Wall(0, 18, 178, 52, 44, FAR_BASE), Wall(320, 18, 178, 268, 44, FAR_BASE)):
        paint_wall(e, wall, 4, 3, 0.42)
    for x, y in ((38, 70), (20, 104), (44, 124)):
        camera_icon(e, x, y, 1)
    for x, y in ((280, 70), (298, 104), (274, 124)):
        camera_icon(e, x, y, -1)


def reflect(e, cx, half, y0, y1, density):
    """A light's reflection in the wet paving, as water shows one: on every other row from y0 to y1, a few dashes
    round cx, longer near it, the column narrowing as it comes near."""
    for y in range(y0, y1, 2):
        depth = (y - y0) / max(1, y1 - y0)
        reach = half * (1 - 0.5 * depth)
        for _ in range(int(density * (1 - 0.6 * depth)) + 1):
            x = cx + rnd.gauss(0, reach * 0.45)
            length = max(1, int((reach - abs(x - cx)) * rnd.uniform(0.15, 0.5)))
            e.rect(x - length / 2, y, x + length / 2, y + 1)


def paint_ground(e):
    """The square's wet paving: the setts' joints as short dashes, the moon's long reflection under the camera in
    broken dashes, the lamps' narrow ones, and the walkers' ring worn into it."""
    y, gap = float(FAR_BASE + 4), 3.0
    while y < H:  # the setts' joints: short dashes, further apart as they come near
        for x in range(0, W, 5):
            if rnd.random() < 0.3:
                e.rect(x, int(y), x + 2, int(y) + 1)
        y += gap
        gap *= 1.22
    reflect(e, MOON[0], 70, FAR_BASE + 2, 196, 6)
    for x in (67, 255):
        reflect(e, x, 8, FAR_BASE + 2, 214, 2)
    for x in range(0, W, 2):  # the walkers' ring: a worn ellipse
        a = (x - RING[0]) / (RING[2] + 6)
        if abs(a) < 1:
            dy = (RING[3] + 3) * (1 - a * a) ** 0.5
            for yy in (RING[1] + 1 + dy, RING[1] + 1 - dy):
                e.px(x, yy)
    e.rect(0, FAR_BASE, W, FAR_BASE + 1)


def paint_lamps(e):
    """Two street lamps in front of the far side: posts and heads, each glow engraved round its head."""
    for x in (66, 254):
        e.engrave(lambda px, py, x=x: max(0.0, 0.75 - hypot(px - x, (py - 102) * 1.3) / 20), period=5)
        e.rect(x, 104, x + 2, 172)
        e.rect(x - 5, 99, x + 7, 101)
        e.rect(x - 3, 101, x + 5, 104)
        e.rect(x - 2, 172, x + 4, 174)
        e.rect(x - 1, 112, x + 3, 113)


def paint_billboard(e):
    """The scoring billboard on the left house: CITIZEN SCORE in ink on a bone band, an empty plate the game writes
    the score on, a row of ranks, and its two struts to the wall."""
    x0, y0, x1, y1 = BOARD
    e.rect(x0 + 10, y1, x0 + 12, y1 + 10)
    e.rect(x1 - 14, y1, x1 - 12, y1 + 6)
    e.rect(x0, y0, x1, y1, INK)
    e.frame(x0, y0, x1, y1)
    e.frame(x0 + 2, y0 + 2, x1 - 2, y1 - 2)
    e.rect(x0 + 3, y0 + 3, x1 - 3, y0 + 14)
    e.words("CITIZEN SCORE", (x0 + x1) / 2, y0 + 5, 1.0, 1.2, INK)
    px0, py0, px1, py1 = BOARD_PLATE
    e.frame(px0, py0, px1, py1)
    for k in range(4):  # the ranks: bars
        h = (3, 6, 9, 5)[k]
        e.rect(x0 + 6 + k * 7, py1 - h, x0 + 10 + k * 7, py1)


def paint_monitor(e):
    """The monitor in the corner that shows the one the camera watches: a double bone frame and YOU over it."""
    x0, y0, x1, y1 = FACE_BOX
    e.rect(x0, y0, x1, y1, INK)
    e.frame(x0, y0, x1, y1)
    e.frame(FACE_AT[0] - 2, FACE_AT[1] - 2, FACE_AT[0] + FACE + 2, FACE_AT[1] + FACE + 2)
    e.words("YOU", x0 + 4, y0 + 3.5, 0.8, 0.9, BONE, centre=False)


def paint_bar(e):
    """The timing bar's track: a row of ticks, the middle one long."""
    x0, x1, y0 = BAR_X - BAR_HALF, BAR_X + BAR_HALF, BAR_Y
    e.rect(x0 - 2, y0 - 2, x1 + 3, y0 + 8, INK)
    for x in range(x0, x1 + 1, 10):
        tall = 4 if x == BAR_X else 1
        e.rect(x, y0 + 5 - tall, x + 1, y0 + 6)
    e.rect(x0, y0 + 5, x1 + 1, y0 + 6)


def paint_plates(e):
    """The cables' wall plates."""
    for x, y in ANCHORS:
        e.rect(x - 2, y - 2, x + 3, y + 3)
        e.rect(x - 1, y - 1, x + 2, y + 2, INK)


def paint_square():
    """The square at 22:00, 320 x 240: the sky and the moon, the far side and its tower, the near house fronts, the
    paving, the lamps, the billboard, the cables' plates, the monitor and the bar's track."""
    e = Etch(W, H)
    for painter in (paint_sky, paint_far, paint_sides, paint_ground, paint_lamps, paint_billboard, paint_plates,
                    paint_monitor, paint_bar):
        painter(e)
    return e.done()


# --- the camera's sprites ----------------------------------------------------------------------------------------

def lens(size, pose):
    """The lens, size px across, keyed: an ink collar that parts it from whatever is behind, a thick bone rim, the
    hood's shade over its top, the barrel in ink, and the iris: shut (bone blades round a pinhole), half, or open (a
    wide black pupil in a bone ring with a big glint): the camera staring at you."""
    e = Etch(size, size, (0, 0, 0))
    c, r = size / 2, size / 2 - 0.2
    e.ellipse(c, c, r, r, INK)  # the collar
    e.ellipse(c, c, r - 1.6, r - 1.6)  # the rim
    e.ellipse(c, c + 0.8, r - 3.6, r - 3.8, INK)  # the barrel, the hood's shade on its top
    glass = r - 5.2
    if pose == "open":
        e.ellipse(c, c, glass, glass, BONE, width=1.2)
        e.ellipse(c - glass * 0.34, c - glass * 0.36, max(1.2, glass * 0.28), max(1.0, glass * 0.22))
        e.ellipse(c + glass * 0.38, c + glass * 0.36, max(0.7, glass * 0.1), max(0.7, glass * 0.1))
    else:
        hole = glass * (0.28 if pose == "shut" else 0.6)
        e.ellipse(c, c, glass, glass)
        e.ellipse(c, c, hole, hole, INK)
        for k in range(6):  # the blades' edges, spiralling to the hole
            a = k * pi / 3
            e.line([(c + hole * cos(a + 1.2), c + hole * sin(a + 1.2)), (c + glass * cos(a), c + glass * sin(a))],
                   0.7, INK)
    return e.keyed((0, 0, 0))


def light(k):
    """The recording light, 7 x 7 keyed: its accent core, and with k 1 its glow round it."""
    e = Etch(LIGHT, LIGHT)
    if k:
        for x, y in ((3, 0), (0, 3), (6, 3), (3, 6), (1, 1), (5, 1), (1, 5), (5, 5)):
            e.px(x, y, ACCENT)
    e.rect(2, 2, 5, 5, ACCENT)
    if k:
        e.px(2, 2, BONE)
    return e.keyed()


def target(k):
    """The target's brackets, 32 x 32 keyed, where the lens must be when you smile: thin corners, or with k 1 locked,
    thick corners drawn in with ticks to the middle."""
    e = Etch(TARGET, TARGET)
    n, inset, t = TARGET, (0 if k == 0 else 3), (1 if k == 0 else 2)
    arm = 7 if k == 0 else 6
    for sx in (0, 1):
        for sy in (0, 1):
            x = inset if sx == 0 else n - inset - t
            y = inset if sy == 0 else n - inset - t
            x0 = inset if sx == 0 else n - inset - arm
            y0 = inset if sy == 0 else n - inset - arm
            e.rect(x0, y, x0 + arm, y + t)
            e.rect(x, y0, x + t, y0 + arm)
    if k:
        for a, b in ((n // 2 - 1, 0), (n // 2 - 1, n - 4)):
            e.rect(a, b, a + 2, b + 4)
            e.rect(b, a, b + 4, a + 2)
    return e.keyed()


# The walkers, 12 x 22, drawn by hand: b bone, k ink, . clear. Pale coats, as the prisoners' round in Van Gogh's
# yard; a back is a dark head of hair, a face turned to you a bone face with dark eyes. Two steps each.
WALKER_HEADS = {
    "back": ("....kkkk....", "...kkkkkk...", "..kkkkkkkk..", "..kkkkkkkk..", "..kkkkkkkk..", "...kkkkkk...",
             "....kkkk...."),
    "face": ("....kkkk....", "...kkkkkk...", "..kbbbbbbk..", "..kbkbbkbk..", "..kbbbbbbk..", "...kbkkbk...",
             "....kbbk...."),
}
WALKER_BODY = ("..kkkkkkkk..", ".kbbbbbbbbk.", "kbbbbbbbbbbk", "kbbbkbbbbbbk", "kbbbkbbbbbbk", "kbbbkbbbbbbk",
               "kbbbkbbbbbbk", ".kbbkbbbbbk.", ".kbbkbbbbbk.", ".kbbbbbbbbk.")
WALKER_LEGS = (("..kbk..kbk..", ".kbk....kbk.", ".kbk....kbk.", ".kkk....kkk.", "............"),
               ("...kbkkbk...", "...kbkkbk...", "...kbkkbk...", "...kkkkkk...", "............"))


def walker(kind, step):
    """One of the walkers round the square, kind back or face, in step 0 or 1."""
    rows = WALKER_HEADS[kind] + WALKER_BODY + WALKER_LEGS[step]
    img = Image.new("RGBA", WALKER, (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                img.putpixel((x, y), (BONE if ch == "b" else INK) + (255,))
    return img


def flare(k):
    """The camera's flash at the lens when it takes you, 40 x 40 keyed: a bone sparkle edged in ink, so it reads on
    the moon's light as on the night: four long rays and four short ones round a white core; k 1 is it fading."""
    e = Etch(FLARE, FLARE, (0, 0, 0))
    c = FLARE / 2
    long, short, core, base = ((19, 11, 8, 4.5), (13, 7, 5, 3.0))[k]
    for colour, grow in ((INK, 1.3), (BONE, 0.0)):
        for a in range(8):
            ang = a * pi / 4
            reach, half = (long, base) if a % 2 == 0 else (short, base * 0.7)
            reach, half = reach + grow, half + grow
            e.poly([(c + cos(ang) * reach, c + sin(ang) * reach),
                    (c + cos(ang + pi / 2) * half, c + sin(ang + pi / 2) * half),
                    (c - cos(ang) * 2, c - sin(ang) * 2),
                    (c - cos(ang + pi / 2) * half, c - sin(ang + pi / 2) * half)], colour)
        e.ellipse(c, c, core + grow, core + grow, colour)
    return e.keyed((0, 0, 0))


# --- the face in the monitor, and the zoom -----------------------------------------------------------------------

def paint_face(e, n, pose, x0=0.0, y0=0.0, flash=False):
    """A face n px tall in e from (x0, y0), in stencil, as a poster prints one: bone where the camera's light falls
    (from the left), ink in the shadow, the hair a dark mass; with flash, the camera's flash full on it, no shade.
    pose: neutral, smile (forced: a wide grin with teeth, the brows still worried) or frozen (the eyes wide, the
    mouth open)."""
    def p(x, y):
        return x0 + x * n, y0 + y * n

    def poly(pts, colour=BONE):
        e.poly([p(x, y) for x, y in pts], colour)

    def oval(cx, cy, rx, ry, colour=BONE):
        x, y = p(cx, cy)
        e.ellipse(x, y, rx * n, ry * n, colour)

    poly([(0.02, 1.02), (0.1, 0.86), (0.32, 0.79), (0.68, 0.79), (0.9, 0.86), (0.98, 1.02)])  # the shoulders
    if not flash:
        poly([(0.56, 0.79), (0.68, 0.79), (0.9, 0.86), (0.98, 1.02), (0.6, 1.02)], INK)  # their shade
    poly([(0.4, 0.79), (0.5, 0.94), (0.6, 0.79)], INK)  # the collar's V
    poly([(0.4, 0.62), (0.6, 0.62), (0.6, 0.82), (0.5, 0.9), (0.4, 0.82)])  # the neck
    poly([(0.52, 0.66), (0.6, 0.62), (0.6, 0.82), (0.52, 0.86)] if not flash else
         [(0.4, 0.62), (0.6, 0.62), (0.6, 0.68), (0.4, 0.68)], INK)  # under the jaw
    oval(0.5, 0.43, 0.25, 0.31)  # the face
    if not flash:
        poly([(0.6, 0.2), (0.78, 0.3), (0.78, 0.55), (0.62, 0.76), (0.53, 0.75), (0.6, 0.66), (0.58, 0.6),
              (0.6, 0.52), (0.57, 0.44), (0.62, 0.38)], INK)  # the shade, along the nose
    poly([(0.23, 0.46), (0.21, 0.26), (0.3, 0.12), (0.46, 0.05), (0.64, 0.07), (0.78, 0.18), (0.8, 0.36),
          (0.76, 0.5), (0.72, 0.28), (0.58, 0.2), (0.44, 0.21), (0.33, 0.26), (0.28, 0.46)], INK)  # the hair
    e.line([p(0.3, 0.2), p(0.42, 0.12), p(0.56, 0.11)], max(1.0, n * 0.022))  # its lit strand
    wide = pose == "frozen"
    for cx in (0.385, 0.615) if flash else (0.385,):  # the lit eye, or both in the flash
        oval(cx, 0.42, 0.085, 0.05 if not wide else 0.07, INK)
        if wide:
            oval(cx, 0.42, 0.06, 0.05)
            oval(cx, 0.42, 0.018, 0.018, INK)
        else:
            oval(cx + 0.02, 0.415, 0.02, 0.016)
    if not flash:
        oval(0.63, 0.43, 0.022, 0.016)  # the shaded eye: its glint
    brow = 0.335 if wide else 0.35
    lift = 0.04 if pose == "smile" else 0.0  # forced: the brows go up in the middle
    e.line([p(0.3, brow + 0.01), p(0.46, brow - lift)], max(1.2, n * 0.04), INK)
    if flash:
        e.line([p(0.7, brow + 0.01), p(0.54, brow - lift)], max(1.2, n * 0.04), INK)
    poly([(0.47, 0.55), (0.58, 0.54), (0.58, 0.6), (0.5, 0.6)], INK)  # under the nose
    if pose == "neutral":
        e.line([p(0.39, 0.675), p(0.58, 0.675)], max(1.2, n * 0.04), INK)
    elif pose == "smile":
        poly([(0.32, 0.62), (0.66, 0.62), (0.6, 0.72), (0.5, 0.75), (0.4, 0.72)], INK)
        poly([(0.36, 0.635), (0.62, 0.635), (0.6, 0.67), (0.38, 0.67)])  # the teeth
        e.line([p(0.29, 0.56), p(0.32, 0.63)], max(1.0, n * 0.025), INK)  # the cheek pushed up
    else:
        oval(0.48, 0.685, 0.055, 0.06, INK)


def face(pose):
    """The one the camera watches, 48 x 48: neutral, smile or frozen."""
    e = Etch(FACE, FACE)
    paint_face(e, FACE, pose)
    return e.done()


def viewfinder(e, n):
    """The camera's marks over the zoom: corner brackets, a crosshair, REC and the light."""
    for sx in (0, 1):
        for sy in (0, 1):
            x = 3 if sx == 0 else n - 13
            y = 3 if sy == 0 else n - 5
            e.rect(x, y, x + 10, y + 2)
            x = 3 if sx == 0 else n - 5
            y = 3 if sy == 0 else n - 13
            e.rect(x, y, x + 2, y + 10)
    e.rect(7, 7, 34, 15, INK)
    e.rect(9, 9, 13, 13, ACCENT)
    e.words("REC", 16, 9, 0.9, 1.0, BONE, centre=False)


def zoom(k):
    """The camera zoomed into the face in its flash, 128 x 128: k 0 sharp, k 1 in 8 px blocks, k 2 in 16 px blocks,
    each block bone or ink by the share of bone in it, under the viewfinder's marks."""
    n = ZOOM
    e = Etch(n, n)
    big = n * 1.12
    paint_face(e, big, "frozen", n / 2 - big * 0.5, n * 0.5 - big * 0.46, flash=True)
    if k:
        block = 8 * k
        src = e.img.copy()
        for by in range(0, n, block):
            for bx in range(0, n, block):
                cut = src.crop((bx, by, bx + block, by + block)).convert("L")
                share = sum(1 for v in cut.get_flattened_data() if v > 120) / (block * block)
                e.rect(bx, by, bx + block, by + block, BONE if share > 0.5 else INK)
        for y in range(0, n, block):  # the blocks' seams
            for x in range(0, n):
                if e.img.getpixel((x, y)) == BONE and x % 2:
                    e.px(x, y, INK)
    viewfinder(e, n)
    if k == 2:
        e.rect(30, n - 24, n - 30, n - 13, INK)
        e.words("ID 4471", n / 2, n - 22, 1.0, 1.0)
    return e.done()


# --- the stamps, the digits, the title and the card ---------------------------------------------------------------

def stamp(word, colour):
    """A rubber stamp, 128 x 40 keyed: the word in a double frame, tilted, the ink worn in specks."""
    w, h = STAMP
    big = Image.new("L", (w * S, h * S), 0)
    d = ImageDraw.Draw(big)
    bw, bh = 116, 28
    x0, y0 = (w - bw) / 2, (h - bh) / 2
    d.rectangle((x0 * S, y0 * S, (x0 + bw) * S, (y0 + bh) * S), outline=255, width=3 * S)
    d.rectangle(((x0 + 4) * S, (y0 + 4) * S, (x0 + bw - 4) * S, (y0 + bh - 4) * S), outline=255, width=S)
    unit = 2.1 if len(word) <= 7 else 1.75
    write(big, word, (w / 2 - text_width(word, unit) / 2) * S, (h / 2 - 3 * unit) * S, unit * S, 2.6 * S)
    big = big.rotate(6, Image.BICUBIC, center=(w * S / 2, h * S / 2))
    m = big.resize((w, h), Image.BOX).point(lambda v: 255 if v >= 128 else 0)
    e = Etch(w, h)
    e.fill(m, colour)
    for _ in range(10):  # the worn specks
        e.px(rnd.uniform(0, w), rnd.uniform(0, h), INK)
    return e.keyed()


def digit(n):
    """One digit, 8 x 12 keyed, bone strokes."""
    k = 8
    m = Image.new("L", (DIGIT_W * k, DIGIT_H * k), 0)
    write(m, str(n), 1.2 * k, 1.2 * k, 1.5 * k, 1.5 * k)
    a = m.resize((DIGIT_W, DIGIT_H), Image.BOX).point(lambda v: 255 if v >= 100 else 0)
    out = Image.new("RGBA", (DIGIT_W, DIGIT_H), BONE + (255,))
    out.putalpha(a)
    return out


def iris(k):
    """The title's great lens, 72 x 72 keyed: the iris shut, half open, open (k 0, 1, 2)."""
    n = TITLE_IRIS
    e = Etch(n, n, (0, 0, 0))
    c = n / 2
    e.ellipse(c, c, c - 0.5, c - 0.5)
    e.ellipse(c, c, c - 3, c - 3, INK)
    e.ellipse(c, c, c - 6, c - 6, BONE, width=1.2)
    for a in range(0, 360, 15):  # the focus ring's knurls
        r = c - 1.8
        e.px(c + r * cos(a * pi / 180), c + r * sin(a * pi / 180), INK)
    glass = c - 9
    hole = glass * (0.16, 0.5, 0.86)[k]
    if k < 2:
        e.ellipse(c, c, glass, glass)
        for b in range(8):  # the blades, each a curved edge to the hole
            a = b * pi / 4
            pts = [(c + (hole + (glass - hole) * t) * cos(a + 0.9 * (1 - t)),
                    c + (hole + (glass - hole) * t) * sin(a + 0.9 * (1 - t))) for t in (0, 0.25, 0.5, 0.75, 1)]
            e.line(pts, 1.1, INK)
    e.ellipse(c, c, hole, hole, INK)
    if k == 2:
        e.ellipse(c, c, hole, hole, BONE, width=1.0)
        e.ellipse(c, c, hole * 0.55, hole * 0.55, BONE, width=0.8)
    e.ellipse(c - glass * 0.38, c - glass * 0.42, 3.2, 2.2)  # the glint
    e.ellipse(c + glass * 0.3, c + glass * 0.36, 1.4, 1.0)
    return e.keyed((0, 0, 0))


def plate(e, x, y, w=PLATE_W, h=PLATE_H):
    e.rect(x, y, x + w, y + h, INK)
    e.frame(x, y, x + w, y + h)


def paint_title():
    """The title, 320 x 240: the night, the full moon with its halo, the camera's cables crossing it to the corners
    (bone on the sky, ink on the moon) and the roofs in silhouette across its foot; SMILE in great bone letters over
    it, TAP WHEN THE LENS FACES YOU and BEST with a plate under it. The game opens the great lens on the moon."""
    e = Etch(W, H)
    cx, cy, r = TITLE_IRIS_AT[0] + TITLE_IRIS // 2, TITLE_IRIS_AT[1] + TITLE_IRIS // 2, 62
    for _ in range(40):
        x, y = rnd.uniform(0, W), rnd.uniform(16, 150)
        if hypot(x - cx, y - cy) > r + 26:
            e.px(x, y)
    e.engrave(lambda x, y: max(0.0, 0.62 - (hypot(x - cx, y - cy) - r) / 40) if hypot(x - cx, y - cy) > r + 2 else 0,
              period=6)
    ends = ((0, 76), (W, 76), (0, 150), (W, 150))
    for x, y in ends:
        e.line([(cx, cy), (x, y)], 1.0)
    e.ellipse(cx, cy, r, r)
    e.engrave(lambda x, y: max(0.0, (hypot(x - cx + 10, y - cy + 9) - r * 0.96) / 16), INK, period=6,
              where=lambda x, y: hypot(x - cx, y - cy) < r)
    for x, y in ends:
        k = r / hypot(x - cx, y - cy)
        e.line([(cx, cy), (cx + (x - cx) * k, cy + (y - cy) * k)], 1.0, INK)
    x = 0.0
    while x < W:  # the roofs across the moon's foot
        w, top = rnd.uniform(14, 30), rnd.uniform(140, 156)
        e.rect(x, top, x + w, 170, INK)
        if rnd.random() < 0.45:
            e.poly([(x - 1, top + 0.5), (x + w / 2, top - w * 0.4), (x + w + 1, top + 0.5)], INK)
        else:
            rooftop(e, x, top, w)
        x += w + rnd.uniform(0, 2)
    e.rect(0, 16, W, 70, INK)
    e.rect(0, 69, W, 70)
    e.rect(0, 160, W, H, INK)
    e.rect(0, 160, W, 161)
    unit, width = 8.0, 5.0
    e.words("SMILE", 160 - text_width("SMILE", unit) / 2, 20, unit, width, BONE, centre=False)
    e.words("TAP WHEN THE LENS FACES YOU", 160, 172, 1.4, 1.2)
    e.words("BEST", TITLE_PLATE[0] - 18, TITLE_PLATE[1] + 5, 1.4, 1.1)
    plate(e, *TITLE_PLATE)
    return e.done()


def paint_over():
    """The card, 190 x 78: PROFILE COMPLETE in bone, a rule, and plates for the score and the best; the game writes
    tap to retry under them."""
    w, h = CARD
    e = Etch(w, h)
    e.frame(0, 0, w, h)
    e.frame(2, 2, w - 2, h - 2)
    e.words("PROFILE COMPLETE", w / 2, 9, 1.7, 1.4)
    e.rect(30, 26, w - 30, 27)
    for (x, y), label in zip(CARD_PLATES, ("SCORE", "BEST")):
        e.words(label, x + PLATE_W / 2, y - 12, 1.2, 1.0)
        plate(e, x, y)
    return e.done()


# --- the preview sheet: the game's frame drawn here, as the game draws it ----------------------------------------

F, D, TILT, MARK = 200, 5.0, 0.6, 7  # games/space3d.py's CubeTiming
CENTRE = (160, 116)
VERTS = [((i & 1) * 2 - 1, ((i >> 1) & 1) * 2 - 1, ((i >> 2) & 1) * 2 - 1) for i in range(8)]
FACES = ((1, 3, 7, 5), (4, 5, 7, 6), (0, 2, 6, 4), (0, 1, 3, 2), (0, 1, 5, 4))  # x+, z+, x-, z-, top
NORMALS = ((1, 0, 0), (0, 0, 1), (-1, 0, 0), (0, 0, -1), (0, -1, 0))
SHADES = ((42, 39, 56), (27, 25, 38), (66, 62, 82))  # games/space3d.py's: the sides, lit and shaded, and the top


def project(v, yaw):
    x, y, z = v
    c, s = cos(yaw), sin(yaw)
    x, z = x * c + z * s, -x * s + z * c
    y, z = y * cos(TILT) - z * sin(TILT), y * sin(TILT) + z * cos(TILT)
    k = F / (z + D)
    return CENTRE[0] + x * k, CENTRE[1] + y * k, z


def over(out, img, x, y):
    out.paste(img, (int(x), int(y)), img)


def cube_scene(pics, yaw=2.25, face_pose="neutral", stamp_name=None, lit=True):
    """A frame of play: the square, the walkers, the cables, the housing's faces and edges, the lens, the light and
    the monitor."""
    out = pics["cube_square"].copy()
    for i in range(16):
        a = yaw * 0.7 + i * pi / 8
        over(out, pics["cube_walker_%s_%d" % ("back" if sin(a) > 0 else "face", i % 2)],
             RING[0] + RING[2] * cos(a) - WALKER[0] // 2, RING[1] + RING[3] * sin(a) - WALKER[1] + 2)
    d = ImageDraw.Draw(out)
    for ax, ay in ANCHORS:
        d.line([JOINT, (ax, ay)], fill=(100, 96, 112))
    pts = [project(v, yaw) for v in VERTS]
    for k, quad in enumerate(FACES):
        if project(NORMALS[k], yaw)[2] < -0.2:
            d.polygon([pts[i][:2] for i in quad], fill=SHADES[2] if k == 4 else SHADES[k % 2])
            for a, b in zip(quad, quad[1:] + quad[:1]):
                d.line([pts[a][:2], pts[b][:2]], fill=BONE)
    d.line([JOINT, project((0, -1, 0), yaw)[:2]], fill=BONE)
    x, y, z = pts[MARK]
    size = LENS_SIZES[0 if z > 1 else 1 if z > 0 else 2]
    over(out, pics["cube_lens_%d_%s" % (size, "open" if lit else "half")], x - size // 2, y - size // 2)
    over(out, pics["cube_face_" + face_pose], *FACE_AT)
    if stamp_name:
        over(out, pics[stamp_name], *STAMP_AT)
    return out.convert("RGB")


def cube_frame(painting):
    return cube_scene(painting.images())


def cube_sheet(painting, sheet, y):
    """A frame of play at 2x; the lens's sizes and poses, the light, the target and the walkers at 4x; the faces, the
    stamps and the zooms; the title and the card."""
    pics = painting.images()
    sheet.put("cube (SMILE): cube_square in play, the housing drawn as the game draws it, at 2x",
              cube_scene(pics, 3 * pi / 4, "smile", "cube_stamp_ok").resize((W * 2, H * 2), Image.NEAREST), 10, y)
    cell = 30
    grid = Image.new("RGB", (cell * len(IRIS), cell * len(LENS_SIZES)), INK)
    for k, size in enumerate(LENS_SIZES):
        for m, pose in enumerate(IRIS):
            over(grid, pics["cube_lens_%d_%s" % (size, pose)], m * cell + (cell - size) // 2,
                 k * cell + (cell - size) // 2)
    at = sheet.put("cube_lens_<size>_<pose> at 4x", grid.resize((grid.width * 4, grid.height * 4), Image.NEAREST),
                   W * 2 + 30, y)
    small = Image.new("RGB", (TARGET * 2 + LIGHT * 2 + 12 + WALKER[0] * 4 + 12, TARGET), (60, 56, 70))
    for k in range(2):
        over(small, pics["cube_target_%d" % k], k * TARGET, 0)
        over(small, pics["cube_light_%d" % k], TARGET * 2 + 4 + k * (LIGHT + 4), 4)
    for k, name in enumerate(("back_0", "back_1", "face_0", "face_1")):
        over(small, pics["cube_walker_" + name], TARGET * 2 + LIGHT * 2 + 12 + k * (WALKER[0] + 3), 10)
    sheet.put("cube_target_0..1, cube_light_0..1, cube_walker_<kind>_<step> at 4x",
              small.resize((small.width * 4, small.height * 4), Image.NEAREST), W * 2 + 30, at + 10)
    y = max(at + 30 + TARGET * 4, y + 18 + H * 2) + 14
    row = Image.new("RGB", (FACE * 3 + 20 + FLARE * 2 + 10, max(FACE, FLARE)), (60, 56, 70))
    for k, pose in enumerate(("neutral", "smile", "frozen")):
        over(row, pics["cube_face_" + pose], k * (FACE + 10), 0)
    for k in range(2):
        over(row, pics["cube_flare_%d" % k], FACE * 3 + 30 + k * (FLARE + 10), 0)
    at = sheet.put("cube_face_neutral/smile/frozen 48x48 and cube_flare_0..1, at 3x",
                   row.resize((row.width * 3, row.height * 3), Image.NEAREST), 10, y)
    stamps = Image.new("RGB", (STAMP[0], STAMP[1] * 2 + 4), (60, 56, 70))
    over(stamps, pics["cube_stamp_ok"], 0, 0)
    over(stamps, pics["cube_stamp_flag"], 0, STAMP[1] + 4)
    sheet.put("cube_stamp_ok / flag at 2x", stamps.resize((STAMP[0] * 2, stamps.height * 2), Image.NEAREST),
              row.width * 3 + 30, y)
    y = max(at, y + 18 + stamps.height * 2) + 12
    zooms = Image.new("RGB", (ZOOM * 3 + 20, ZOOM), INK)
    for k in range(3):
        zooms.paste(pics["cube_zoom_%d" % k].convert("RGB"), (k * (ZOOM + 10), 0))
    y = sheet.put("cube_zoom_0..2 128x128", zooms, 10, y) + 12
    title = pics["cube_title"].copy()
    over(title, pics["cube_iris_2"], *TITLE_IRIS_AT)
    sheet.put("cube_title with the great lens open", title.convert("RGB"), 10, y)
    end = cube_scene(pics, 1.0, "frozen")
    end.paste(pics["cube_zoom_2"].convert("RGB"), ZOOM_AT)
    end.paste(pics["cube_over"].convert("RGB"), CARD_AT)
    sheet.put("game over: cube_zoom_2 and cube_over", end, 350, y)
    return y + H + 32


def paint_cube():
    pics = {"cube_square": (paint_square(), False)}
    for size in LENS_SIZES:
        for pose in IRIS:
            pics["cube_lens_%d_%s" % (size, pose)] = (lens(size, pose), True)
    for k in range(2):
        pics["cube_light_%d" % k] = (light(k), True)
        pics["cube_target_%d" % k] = (target(k), True)
        pics["cube_flare_%d" % k] = (flare(k), True)
    for kind in ("back", "face"):
        for step in range(2):
            pics["cube_walker_%s_%d" % (kind, step)] = (walker(kind, step), True)
    for pose in ("neutral", "smile", "frozen"):
        pics["cube_face_" + pose] = (face(pose), False)
    pics["cube_stamp_ok"] = (stamp("COMPLIANT", BONE), True)
    pics["cube_stamp_flag"] = (stamp("FLAGGED", ACCENT), True)
    for k in range(3):
        pics["cube_zoom_%d" % k] = (zoom(k), False)
        pics["cube_iris_%d" % k] = (iris(k), True)
    for n in range(10):
        pics["cube_digit_%d" % n] = (digit(n), True)
    pics["cube_title"] = (paint_title(), False)
    pics["cube_over"] = (paint_over(), False)
    return Painting(pics)


ART_SET = ArtSet("cube", 5733, paint_cube, look=LOOK, sheet_fn=cube_sheet, scene_fn=cube_frame)
