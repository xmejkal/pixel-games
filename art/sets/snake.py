"""Snake's art as FEED (P573): watercolour noir at 10:00 (D4). The play field is a phone's glass, lit from within: an
endless feed of glowing tiles, six kinds of post in six hues, crawls over it and grows by eating red notification
dots, the only red on the screen. The street at ten in the morning, a tram stop in the low sun, shows faintly in the
glass, mirrored, with a cold streak of sky across it. At the end every tile turns over to a grey SEEN, head to tail,
and the card says YOU SAW n. YOU REMEMBER 0. You are eaten by your own feed.

The sprites are drawn pixel by pixel, so each icon's strokes stay whole pixels at 1x; their glow on the glass is
baked in as opaque pixels (the board's keyed blit has no alpha). Only the head's halo is drawn see-through."""

from colorsys import rgb_to_hsv
from math import atan2, cos, hypot, pi, sin

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageOps

from artset import ArtSet, Painting
from brush import ACCENT, H, W, Sprite, Strip, blur, glaze, jitter, lay, rnd
from city import sky_at
from letters import text_width, write

CELL, COLS, ROWS, LEFT, TOP = 12, 26, 18, 4, 21  # games/arcade.py's grid: the glass is its field
FIELD = (LEFT, TOP, LEFT + COLS * CELL, TOP + ROWS * CELL)  # x0, y0, x1, y1: 4, 21, 316, 237
GLASS = (7, 9, 18)  # the glass where nothing lights it
INK, BONE = (14, 14, 22), (240, 232, 214)
KINDS = ("photo", "text", "video", "ad", "chart", "selfie")  # the six posts of the feed
HUES = {"photo": (40, 200, 188), "text": (92, 210, 86), "video": (152, 102, 250), "ad": (250, 178, 40),
        "chart": (60, 134, 250), "selfie": (238, 96, 206)}  # six hues, none red: the dot is the only red
DIRS = ("r", "d", "l", "u")  # games/arcade.py's DIRS order: right, down, left, up
POSES = ("open", "gulp", "chew", "glow")
HEAD = 16  # the head's picture, 2 px past its cell on each side, so the hero reads at 1x
HALO = 36  # the head's see-through glow
BULGE = 16
RIPPLE, RIPPLES = 48, 4  # the glass's ripple where the feed eats: its rings, opaque
PING, PINGS = 28, 3  # the dot's ping: a red ring that spreads from it now and then, calling; opaque
GLOW = 32  # each tile's light on the glass under it, drawn see-through: the street lights up along the feed
BITE, BITES = 56, 2  # the bite's flash where the feed meets itself
DOT_POSES, SEEN_POSES, BULGE_POSES, THUMB_POSES = 3, 3, 2, 3
THUMB = (32, 40)
DIGIT_W, DIGIT_H = 8, 12
CARD = (200, 100)
CARD_PLATE = (122, 12)  # the over card's plate for n, right of YOU SAW
PLATE_W, PLATE_H = 40, 17
TITLE_PLATE = (164, 128)
REFLECTION = 0.16  # the street's mean luminance in the glass, 0 to 1: the pinned band is 0.15 to 0.25


def mix(a, b, t):
    return tuple(int(round(p + (q - p) * t)) for p, q in zip(a, b))


def luma(c):
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255


# --- the street at ten, as the glass mirrors it --------------------------------------------------------------------

STREET = 196  # the pavement's edge in the reflection
HOUSE_COLOURS = ((226, 212, 180), (214, 180, 124), (184, 198, 170), (172, 188, 210), (222, 194, 174), (236, 226, 204))


def morning_at(y):
    return sky_at(10, y / 120)


def paint_houses(s):
    """A row of five-storey houses across the street, their faces in the low sun from the left: cornices, windows in
    rows, steep roofs, chimneys, and the long shadows the sun throws to the right."""
    x, faces = -6.0, []
    while x < W + 6:
        w = rnd.uniform(34, 56)
        top = rnd.uniform(44, 70)
        roof = rnd.uniform(10, 18)
        colour = rnd.choice(HOUSE_COLOURS)
        body = s.mask()
        s.polygon(body, [(x, STREET), (x, top), (x + w, top), (x + w, STREET)])
        s.wash(body, colour, alpha=0.97, rim=0.4, rim_px=3, grain=0.3, cell=10, rough=(1, 0.3, 6), dark=0.8,
               soft=0.5)
        cap = s.mask()
        s.polygon(cap, [(x - 2, top), (x + 4, top - roof), (x + w - 4, top - roof), (x + w + 2, top)])
        s.wash(cap, (112, 84, 78), alpha=0.95, rim=0.3, rim_px=2, grain=0.3, cell=8, rough=None, dark=0.7, soft=0.4)
        if rnd.random() < 0.7:
            cx = x + rnd.uniform(8, w - 8)
            chim = s.mask()
            s.polygon(chim, [(cx, top - roof + 2), (cx, top - roof - 7), (cx + 4, top - roof - 7),
                             (cx + 4, top - roof + 2)])
            s.wash(chim, (96, 72, 70), alpha=0.95, rim=0.2, rim_px=2, grain=0.2, cell=6, rough=None, soft=0.3)
        win = s.mask()
        for wy in range(int(top + 8), STREET - 30, 17):
            for wx in range(int(x + 5), int(x + w - 8), 10):
                s.polygon(win, [(wx, wy), (wx + 4, wy), (wx + 4, wy + 8), (wx, wy + 8)])
        lay(s.rgb, win, (58, 62, 80), 0.9)
        glint = s.mask()  # the morning sun in a few panes
        for wy in range(int(top + 8), STREET - 30, 17):
            for wx in range(int(x + 5), int(x + w - 8), 10):
                if rnd.random() < 0.18:
                    s.polygon(glint, [(wx, wy), (wx + 2, wy), (wx + 2, wy + 4), (wx, wy + 4)])
        lay(s.rgb, blur(glint, 2), (255, 236, 196), 0.8)
        cornice = [([(x, top + 3), (x + w, top + 3)], 2)] + [([(x, wy - 4), (x + w, wy - 4)], 1)
                                                          for wy in range(int(top + 25), STREET - 30, 17)]
        s.pencil(cornice, strength=0.5)
        faces.append((x, w, top))
        x += w
    shade = s.mask()  # the shadows to the right of each house's step, and over the street's far side
    for x, w, top in faces:
        s.polygon(shade, [(x + w * 0.75, STREET), (x + w * 0.75, top + 6), (x + w, top + 18), (x + w, STREET)])
    glaze(s.rgb, blur(shade, 8), (110, 120, 170), 0.35)


def paint_street(s):
    """The tram wires, the stop's shelter with its sign and its bench, people at the stop with their heads bent over
    their phones, the tracks and the cobbles."""
    wires = []
    for y0, sag in ((84, 5), (92, 6)):
        wires.append(([(x, y0 + sag * (1 - ((x - 160) / 170) ** 2)) for x in range(-10, W + 12, 8)], 2))
    s.pencil(wires, strength=0.8, colour=(40, 40, 54))
    pole = s.mask()
    for px in (36, 250):
        s.polygon(pole, [(px - 1.2, STREET + 6), (px - 1.2, 74), (px + 1.2, 74), (px + 1.2, STREET + 6)])
    s.wash(pole, (70, 74, 88), alpha=1.0, rim=0.2, rim_px=2, grain=0.1, cell=6, rough=None, soft=0.2)
    shelter = s.mask()  # the stop: a glass box on posts, a flat roof
    s.polygon(shelter, [(178, 146), (282, 146), (282, STREET + 4), (178, STREET + 4)])
    lay(s.rgb, blur(shelter, 2), (150, 180, 206), 0.35)
    roof = s.mask()
    s.polygon(roof, [(172, 140), (288, 140), (288, 147), (172, 147)])
    s.wash(roof, (60, 66, 84), alpha=1.0, rim=0.3, rim_px=2, grain=0.2, cell=6, rough=None, soft=0.3)
    s.pencil([([(178, 147), (178, STREET + 4)], 2), ([(282, 147), (282, STREET + 4)], 2),
              ([(230, 147), (230, STREET + 4)], 1)], strength=0.8, colour=(40, 44, 60))
    sign = s.mask()
    s.polygon(sign, [(244, 104), (258, 104), (258, 118), (244, 118)])
    s.wash(sign, (236, 232, 214), alpha=1.0, rim=0.2, rim_px=2, grain=0.1, cell=6, rough=None, soft=0.2)
    band = s.mask()
    s.polygon(band, [(244, 104), (258, 104), (258, 108), (244, 108)])
    lay(s.rgb, band, (40, 92, 170))
    people = s.mask()  # the waiting, each bent over a phone
    for cx, h in ((196, 34), (214, 30), (262, 36), (130, 33), (60, 31)):
        top = STREET - h
        s.ellipse(people, cx + 2, top + 3, 3.2, 3.6)
        s.polygon(people, [(cx - 4, top + 7), (cx + 5, top + 7), (cx + 6, top + h * 0.62), (cx - 5, top + h * 0.62)])
        s.polygon(people, [(cx - 4, top + h * 0.6), (cx - 1, top + h * 0.6), (cx - 1.5, STREET), (cx - 4, STREET)])
        s.polygon(people, [(cx + 1, top + h * 0.6), (cx + 4, top + h * 0.6), (cx + 4, STREET), (cx + 1.5, STREET)])
        s.polygon(people, [(cx + 3, top + 9), (cx + 9, top + 13), (cx + 8, top + 15), (cx + 2, top + 12)])
    s.wash(people, (44, 42, 60), alpha=1.0, rim=0.2, rim_px=2, grain=0.2, cell=6, rough=None, soft=0.3)
    screens = s.mask()  # their phones, lit
    for cx, h in ((196, 34), (214, 30), (262, 36), (130, 33), (60, 31)):
        s.polygon(screens, [(cx + 8, STREET - h + 12), (cx + 10.5, STREET - h + 12), (cx + 10.5, STREET - h + 15.5),
                            (cx + 8, STREET - h + 15.5)])
    lay(s.rgb, blur(screens, 3), (170, 220, 255), 0.7)
    lay(s.rgb, screens, (220, 244, 255))
    road = s.mask()
    s.polygon(road, [(0, STREET), (W, STREET), (W, H + 2), (0, H + 2)])
    s.wash(road, (120, 116, 120), alpha=1.0, rim=0, grain=0.35, cell=6, rough=None, soft=0)
    stones = []
    for y in range(STREET + 4, H + 4, 5):
        stones.append((jitter([(0, y), (W, y + 1)], 0.4), 1))
    s.pencil(stones, strength=0.35)
    s.pencil([([(0, 214), (W, 210)], 3), ([(0, 228), (W, 223)], 3)], strength=0.7, colour=(200, 196, 190))
    curb = s.mask()
    s.polygon(curb, [(0, STREET), (W, STREET), (W, STREET + 2), (0, STREET + 2)])
    lay(s.rgb, curb, (220, 214, 200), 0.8)


def paint_sun(s):
    """The low sun: a hot white disc behind the last roofs, its bloom over the sky and the faces. The glass mirrors
    the street, so in it the sun is low on the left."""
    bloom, disc = s.mask(), s.mask()
    s.ellipse(bloom, W - 10, 40, 90, 70)
    lay(s.rgb, blur(bloom, 60), (255, 226, 176), 0.55)
    s.ellipse(disc, W - 18, 36, 9, 9)
    lay(s.rgb, blur(disc, 6), (255, 250, 236), 0.95)


def paint_street_scene():
    """The street at 10:00 as seen straight on, 320 x 240, before the glass dims and mirrors it."""
    s = Strip(W, 0, H, False, morning_at)
    paint_sun(s)
    paint_houses(s)
    paint_street(s)
    s.paper(0.06)
    return s.rgb.resize((W, H), Image.LANCZOS)


# --- the glass -----------------------------------------------------------------------------------------------------

def inside(x, y):
    """Whether the game pixel (x, y) is on the glass: the field, its corners rounded 6 px."""
    x0, y0, x1, y1 = FIELD
    if not (x0 <= x < x1 and y0 <= y < y1):
        return False
    r = 6
    cx = min(max(x + 0.5, x0 + r), x1 - r)
    cy = min(max(y + 0.5, y0 + r), y1 - r)
    return hypot(x + 0.5 - cx, y + 0.5 - cy) <= r


def glass(street):
    """The glass: the street mirrored in it at REFLECTION's luminance over the dark, a faint light from within, the
    cold streak of the sky across it from the lower left, and a dot at each cell's corner, the screen's grid."""
    mirrored = ImageEnhance.Color(ImageOps.mirror(street).convert("RGB")).enhance(1.7)
    mirrored = mirrored.point(lambda v: int(255 * (v / 255) ** 1.8))  # the glass keeps the lights, drops the greys
    lum = sum(luma(p) for p in mirrored.get_flattened_data()) / (W * H)
    k = (REFLECTION - luma(GLASS)) / lum
    base = Image.new("RGB", (W, H), GLASS)
    out = ImageChops.add(base, mirrored.point(lambda v: int(v * k)))
    within = Image.new("L", (W, H), 0)
    ImageDraw.Draw(within).ellipse((40, 40, 280, 220), fill=255)
    lay(out, blur(within, 50), (24, 34, 66), 0.5)
    streak = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(streak)
    d.polygon([(40, H), (110, H), (300, 0), (230, 0)], fill=255)
    out = ImageChops.add(out, Image.composite(Image.new("RGB", (W, H), (60, 76, 104)), Image.new("RGB", (W, H)),
                                              blur(streak, 18).point(lambda v: v * 6 // 10)))
    sharp = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sharp).polygon([(118, H), (126, H), (318, 0), (310, 0)], fill=255)
    out = ImageChops.add(out, Image.composite(Image.new("RGB", (W, H), (70, 90, 120)), Image.new("RGB", (W, H)),
                                              blur(sharp, 1.5).point(lambda v: v * 5 // 10)))
    flare = Image.new("L", (W, H), 0)  # the low sun on the glass itself: a warm bloom from the upper left
    ImageDraw.Draw(flare).ellipse((-60, -40, 110, 120), fill=255)
    out = ImageChops.add(out, Image.composite(Image.new("RGB", (W, H), (150, 92, 34)), Image.new("RGB", (W, H)),
                                              blur(flare, 36).point(lambda v: v * 8 // 10)))
    core = Image.new("L", (W, H), 0)
    ImageDraw.Draw(core).ellipse((4, 18, 40, 54), fill=255)
    out = ImageChops.add(out, Image.composite(Image.new("RGB", (W, H), (190, 150, 90)), Image.new("RGB", (W, H)),
                                              blur(core, 8)))
    for (fx, fy, r, colour) in ((96, 92, 16, (60, 40, 14)), (150, 132, 9, (14, 50, 54)), (196, 170, 22, (30, 16, 40)),
                                (228, 192, 6, (60, 60, 40))):  # the sun's ghosts in the lens, down the glass
        ghost = Image.new("L", (W, H), 0)
        ImageDraw.Draw(ghost).regular_polygon((fx, fy, r), 6, rotation=15, fill=255)
        out = ImageChops.add(out, Image.composite(Image.new("RGB", (W, H), colour), Image.new("RGB", (W, H)),
                                                  blur(ghost, 1.2)))
    edge = Image.new("L", (W, H), 255)  # the glass darker toward its edges, so the middle reads lit from within
    ImageDraw.Draw(edge).rounded_rectangle((20, 34, 300, 224), 30, fill=0)
    glaze(out, blur(edge, 24), (90, 90, 120), 0.6)
    px = out.load()
    for j in range(ROWS + 1):
        for i in range(COLS + 1):
            x, y = LEFT + i * CELL, TOP + j * CELL
            if 0 <= x < W and 0 <= y < H:
                px[x, y] = mix(px[x, y], (110, 130, 170), 0.35)
    return out


def bezel(img):
    """The phone round the glass: a black bezel with a cold glint on its inner edge, the status bar's band under the
    score bar, and the corners rounded."""
    px = img.load()
    for y in range(H):
        for x in range(W):
            if not inside(x, y):
                near = any(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                px[x, y] = (54, 60, 78) if near else mix((12, 12, 16), (26, 26, 34), y / H)
    for x in range(W):  # the bezel's top edge under the status bar catches the light
        px[x, 17] = (36, 38, 50)
    return img


def paint_morning():
    """The glass at 10:00, 320 x 240: the street mirrored and dimmed, lit from within, the streak, the bezel."""
    return bezel(glass(paint_street_scene())).convert("RGBA")


# --- the feed's tiles ----------------------------------------------------------------------------------------------

GLYPHS = {  # each post's mark, 8 x 8 inside its icon: w bone, y the sun, d the icon's dark
    "photo": ("wwwwwwww", "w....yyw", "w....yyw", "w..d...w", "w.ddd..w", "wddddd.w", "wddddddw", "wwwwwwww"),
    "text": (".wwwwww.", "wwwwwwww", "wddddddw", "wwwwwwww", "wddddwww", ".wwwwww.", ".ww.....", "w......."),
    "video": ("........", ".ww.....", ".wwww...", ".wwwwww.", ".wwwwww.", ".wwww...", ".ww.....", "........"),
    "ad": ("ww..ww..", "w..ww..w", "..ww..ww", ".ww..ww.", "ww..ww..", "w..ww..w", "..ww..ww", ".ww..ww."),
    "chart": ("......ww", "......ww", "...ww.ww", "...ww.ww", "ww.ww.ww", "ww.ww.ww", "ww.ww.ww", "wwwwwwww"),
    "selfie": ("..wwww..", ".wwwwww.", "wwdwwdww", "wwwwwwww", "wdwwwwdw", "wwddddww", ".wwwwww.", "..wwww.."),
}
SUN = (255, 236, 150)


def icon(hue, glyph=None, back=False):
    """A tile, 12 x 12 keyed and opaque: a 1 px glow of its hue on the glass round a 10 x 10 rounded icon, lit from
    its top left, with its mark. back: the tile's back, plain."""
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    light, dark = mix(hue, (255, 255, 255), 0.3), mix(hue, (0, 0, 0), 0.3)
    corners = {(1, 1), (10, 1), (1, 10), (10, 10)}
    for j in range(CELL):
        for i in range(CELL):
            edge = i in (0, 11) or j in (0, 11)
            if edge or (i, j) in corners:
                far = (i in (0, 11)) and (j in (0, 11))
                img.putpixel((i, j), mix(GLASS, hue, 0.2 if far else 0.5 if (i, j) not in corners else 0.66) + (255,))
                continue
            c = mix(light, dark, (i + j - 2) / 18)
            if j == 1:
                c = mix(hue, (255, 255, 255), 0.55)
            img.putpixel((i, j), c + (255,))
    if glyph:
        mark, shade = mix(BONE, (255, 255, 255), 0.4), mix(hue, (0, 0, 0), 0.55)
        for j, row in enumerate(glyph):
            for i, ch in enumerate(row):
                if ch != ".":
                    img.putpixel((2 + i, 2 + j), {"w": mark, "y": SUN, "d": shade}[ch] + (255,))
    return img


def tile(kind):
    return icon(HUES[kind], GLYPHS[kind])


SEEN_GREY = (96, 98, 112)


def squeezed(img, w=6):
    """A 12 x 12 tile turned half away: w px wide in the middle of its cell, its near edge lit."""
    narrow = img.resize((w, CELL), Image.NEAREST)
    out = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    out.paste(narrow, ((CELL - w) // 2, 0))
    for j in range(1, CELL - 1):
        out.putpixel(((CELL - w) // 2, j), (255, 255, 255, 255))
    return out


def turn(kind):
    """The flip's first pose, 12 x 12 keyed: the tile itself turned half away, so the flip reads as a turn."""
    return squeezed(tile(kind))


def seen(k):
    """The flip to SEEN, 12 x 12 keyed: 0 the grey back half turned; 1 edge-on, a bright line; 2 the grey tile with
    the two ticks of a message read. The game turns each tile through turn, 1, 0 and 2."""
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    if k == 0:
        for j in range(1, 11):
            for i in range(3, 9):
                c = mix((176, 178, 192), (96, 98, 112), (j - 1) / 10)
                img.putpixel((i, j), (mix(c, (255, 255, 255), 0.3) if i == 3 else c) + (255,))
        for j in range(1, 11):
            img.putpixel((2, j), mix(GLASS, (200, 200, 220), 0.4) + (255,))
            img.putpixel((9, j), mix(GLASS, (200, 200, 220), 0.4) + (255,))
        return img
    if k == 1:
        for j in range(0, 12):
            for i in (5, 6):
                img.putpixel((i, j), (255, 255, 255, 255) if 1 <= j <= 10 else mix(GLASS, (230, 240, 255), 0.5) + (255,))
            for i in (4, 7):
                if 1 <= j <= 10:
                    img.putpixel((i, j), mix(GLASS, (200, 220, 255), 0.45) + (255,))
        return img
    ticks = ("........", "........", ".......w", "..w...ww", ".www.ww.", "..wwww..", "...ww...", "........")
    base = icon(SEEN_GREY)
    for j, row in enumerate(ticks):
        for i, ch in enumerate(row):
            if ch == "w":
                base.putpixel((2 + i, 2 + j), (178, 184, 200, 255))
                if i + 3 < 10 and row[min(7, i + 1)] == ".":
                    pass
    for j, row in enumerate(ticks):  # the second tick, 3 px to the left of the first
        for i, ch in enumerate(row):
            if ch == "w" and i >= 3:
                base.putpixel((2 + i - 3, 2 + j), (150, 156, 174, 255))
    return base


# --- the head ------------------------------------------------------------------------------------------------------

HEAD_POSE = {  # (mouth's half-angle in degrees, the body's half width, half height, brightness)
    "open": (32, 6.6, 6.6, 0.0), "gulp": (42, 7.0, 7.2, 0.3), "chew": (0, 7.6, 6.9, 0.1), "glow": (38, 6.8, 6.8, 1.0)}


def head(pose):
    """The head facing right, 16 x 16 keyed: a white-hot screen with a cyan rim, one eye, and a mouth that opens to
    the right; gulp: wide, the red dot in it; chew: shut and puffed, the mouth a zigzag of teeth; glow: whiter, when a
    dot is near."""
    half, rx, ry, bright = HEAD_POSE[pose]
    n, c = HEAD, (HEAD - 1) / 2
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))

    def body(i, j):
        u, v = abs(i - c) / rx, abs(j - c) / ry
        return u ** 4 + v ** 4 <= 1  # a squircle: an icon's rounded square

    lit_a, lit_b = mix((255, 252, 240), (255, 255, 255), bright), mix((176, 226, 250), (226, 248, 255), bright)
    rim, glow = mix((96, 210, 255), (200, 244, 255), bright), mix((40, 110, 170), (90, 170, 220), bright)
    for j in range(n):
        for i in range(n):
            if body(i, j):
                edge = any(not body(i + di, j + dj) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                img.putpixel((i, j), (rim if edge else mix(lit_a, lit_b, (i + j) / (2 * n))) + (255,))
            elif any(body(i + di, j + dj) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                img.putpixel((i, j), glow + (255,))
    if half:
        for j in range(n):
            for i in range(n):
                a = atan2(j - c, i - c + 1.5) * 180 / pi
                if i > c - 2 and abs(a) <= half and body(i, j):
                    deep = max(0.0, min(1.0, (i - c + 1.5) / 7))
                    img.putpixel((i, j), mix((70, 18, 86), (14, 6, 24), deep) + (255,))
        for i in range(int(c) + 2, n - 1):  # the teeth along the mouth's edges
            for sign in (-1, 1):
                j = int(round(c + sign * (i - c + 1.5) * sin(half * pi / 180) / max(0.3, cos(half * pi / 180))))
                if 0 <= j < n and body(i, j) and i % 2 == 0:
                    img.putpixel((i, j), (255, 255, 255, 255))
        if pose == "gulp":  # the red dot in the mouth, going down
            for i, j in ((9, 7), (10, 7), (9, 8), (10, 8), (11, 7), (11, 8), (10, 6), (10, 9)):
                img.putpixel((i, j), ACCENT + (255,))
    else:  # shut and chewing: the mouth a zigzag of teeth
        for k, i in enumerate(range(int(c) + 1, n - 1)):
            j = int(c) + (k % 2)
            if body(i, j):
                img.putpixel((i, j), (34, 12, 46, 255))
                img.putpixel((i, j + 1 - 2 * (k % 2)), (255, 255, 255, 255))
    ex, ey = int(c) - 1, int(c) - 4  # the eye, above the mouth
    for i, j in ((ex, ey), (ex + 1, ey), (ex, ey + 1), (ex + 1, ey + 1)):
        img.putpixel((i, j), (16, 16, 34, 255))
    img.putpixel((ex + 1, ey), (255, 255, 255, 255) if pose != "glow" else (120, 240, 255, 255))
    return img


def facing(img, d):
    """The right-facing head turned to d: left is the mirror (the eye stays up), down and up are turns."""
    return {"r": img, "l": ImageOps.mirror(img), "d": img.transpose(Image.Transpose.ROTATE_270),
            "u": img.transpose(Image.Transpose.ROTATE_90)}[d]


def halo():
    """The head's glow on the glass, 36 x 36 keyed, drawn see-through: cold white in the middle to blue at its edge."""
    img = Image.new("RGBA", (HALO, HALO), (0, 0, 0, 0))
    for j in range(HALO):
        for i in range(HALO):
            r = hypot(i + 0.5 - HALO / 2, j + 0.5 - HALO / 2) / (HALO / 2)
            if r < 1:
                img.putpixel((i, j), mix((200, 240, 255), (30, 70, 160), r ** 0.7) + (255,))
    return img


def bulge(k):
    """The swallowed dot going down the feed, 16 x 16 keyed: a swollen white tile ringed in the accent, the red dot
    big in it, wide (0) or tall (1), so it reads at 1x."""
    rx, ry = (7.9, 6.9) if k == 0 else (6.9, 7.9)
    n, c = BULGE, (BULGE - 1) / 2
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))

    def body(i, j):
        return (abs(i - c) / rx) ** 2 + (abs(j - c) / ry) ** 2 <= 1

    for j in range(n):
        for i in range(n):
            if body(i, j):
                r = hypot(i - c, j - c)
                col = ACCENT if r < 3.4 else (255, 255, 255) if r < 4.6 else mix((255, 236, 236), (226, 240, 255),
                                                                                  min(1.0, (r - 4.6) / 3))
                edge = any(not body(i + di, j + dj) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                img.putpixel((i, j), (ACCENT if edge else col) + (255,))
    return img


def dot(k):
    """The notification dot, 12 x 12 keyed, three sizes of its pulse: the accent, a glint of bone and a white 1."""
    r = (3.4, 4.3, 5.2)[k]
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    c = (CELL - 1) / 2
    for j in range(CELL):
        for i in range(CELL):
            d = hypot(i - c, j - c)
            if d <= r:
                img.putpixel((i, j), ACCENT + (255,))
    if k:
        for j in range(int(c) - 1, int(c) + 3):  # the 1
            img.putpixel((int(c) + 1, j), (255, 250, 240, 255))
        img.putpixel((int(c), int(c) - 1), (255, 250, 240, 255))
    img.putpixel((int(c - r * 0.55), int(c - r * 0.55)), BONE + (255,))
    return img


def ripple(k):
    """The glass rippling where the feed eats, 48 x 48 keyed, ring k of RIPPLES, each wider and thinner, opaque, so it
    reads at 1x on the dark glass with no blend."""
    n, c = RIPPLE, RIPPLE / 2
    r, w = 8 + k * 5, 3.6 - k * 0.8
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    for j in range(n):
        for i in range(n):
            d = hypot(i + 0.5 - c, j + 0.5 - c)
            if abs(d - r) <= w / 2:
                inner = d < r
                img.putpixel((i, j), mix((240, 250, 255) if inner else (150, 210, 255), (110, 170, 250), k / 3) + (255,))
    return img


def ping(k):
    """The dot calling, 28 x 28 keyed, ring k of PINGS in the accent, each wider and thinner, opaque."""
    n, c = PING, PING / 2
    r, w = 7 + k * 3.2, 2.2 - k * 0.5
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    for j in range(n):
        for i in range(n):
            if abs(hypot(i + 0.5 - c, j + 0.5 - c) - r) <= w / 2:
                img.putpixel((i, j), ACCENT + (255,))
    return img


def glow(kind):
    """A tile's light on the glass, 32 x 32 keyed, drawn see-through under it: its hue, lightened, softest at the
    edge, so the street in the glass lights up along the feed and where it has been."""
    hue = mix(HUES[kind], (255, 255, 255), 0.2)
    img = Image.new("RGBA", (GLOW, GLOW), (0, 0, 0, 0))
    c = GLOW / 2
    for j in range(GLOW):
        for i in range(GLOW):
            u, v = abs(i + 0.5 - c) / c, abs(j + 0.5 - c) / c
            r = (u ** 3 + v ** 3) ** (1 / 3)
            if r < 1:
                img.putpixel((i, j), mix(hue, mix(GLASS, HUES[kind], 0.5), r) + (255,))
    return img


def bite(k):
    """The bite, 56 x 56 keyed: a white-hot jagged burst with the accent at its heart (0), then its rays thrown wider
    and broken (1)."""
    n, c = BITE, BITE / 2
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    state = rnd.getstate()
    rnd.seed(7)  # the same rays in both poses
    rays = [(k2 * 2 * pi / 14 + rnd.uniform(-0.15, 0.15), rnd.uniform(0.6, 1.0)) for k2 in range(14)]
    rnd.setstate(state)
    if k == 0:
        pts = []
        for m, (a, far) in enumerate(rays):
            r = (c - 3) * far if m % 2 == 0 else (c - 3) * far * 0.42
            pts.append((c + r * cos(a), c + r * sin(a)))
        d.polygon(pts, fill=(255, 250, 236, 255))
        d.ellipse((c - 9, c - 9, c + 9, c + 9), fill=(255, 255, 255, 255))
        d.ellipse((c - 4, c - 4, c + 4, c + 4), fill=ACCENT + (255,))
        return img
    for m, (a, far) in enumerate(rays):
        r0, r1 = (c - 3) * far * 0.55, (c - 2) * far
        d.line([(c + r0 * cos(a), c + r0 * sin(a)), (c + r1 * cos(a), c + r1 * sin(a))],
               fill=((255, 250, 236) if m % 3 else ACCENT) + (255,), width=2)
    return img


# --- the thumb, the digits, the title and the card -----------------------------------------------------------------

SKIN, SKIN_LIT, NAIL = (214, 160, 132), (246, 206, 180), (250, 226, 218)


def thumb(k):
    """The thumb that flicks the feed, 32 x 40 keyed, from below: 0 down on the glass, 1 flicking up, 2 lifted and
    bent, lit by the screen."""
    s = Sprite(*THUMB)
    angle, tip = ((0, 6), (-14, 3), (-26, 9))[k]
    s.part(s.shape("line", (17, 44), (16.5, tip + 8), width=12), SKIN, light=(10, tip + 6, 10, SKIN_LIT), rim=0.4)
    s.part(s.shape("ellipse", 11, tip, 22, tip + 13), SKIN, light=(13, tip + 3, 6, SKIN_LIT), rim=0.4)
    s.part(s.shape("ellipse", 12.6, tip + 1.2, 20.4, tip + 8.4), NAIL, light=(14, tip + 2, 3, (255, 246, 240)),
           rim=0.3, grain=0)
    s.part(s.shape("line", (12.5, tip + 20), (20.5, tip + 21), width=0.7), (170, 116, 96), rim=0, grain=0)
    s.turn(angle, (16, 40))
    return s.cut(ink=(30, 22, 30))


def digit(n):
    """One digit, 8 x 12 keyed: bone strokes, for the plates."""
    k = 8
    m = Image.new("L", (DIGIT_W * k, DIGIT_H * k), 0)
    write(m, str(n), 1.2 * k, 1.2 * k, 1.5 * k, 1.5 * k)
    a = m.resize((DIGIT_W, DIGIT_H), Image.BOX).point(lambda v: 255 if v >= 100 else 0)
    out = Image.new("RGBA", (DIGIT_W, DIGIT_H), BONE + (255,))
    out.putalpha(a)
    return out


def words(s, text, cx, y, unit, width, colour, alpha=1.0):
    """Stroke letters on strip s, centred on game x cx, the top at game y; answers their mask."""
    m = s.mask()
    write(m, text, (cx - text_width(text, unit) / 2) * s.S, y * s.S, unit * s.S, width * s.S)
    lay(s.rgb, m, colour, alpha)
    return m


def plate(s, x, y, w=PLATE_W, h=PLATE_H):
    """A dark number plate with a cold border, for the digits the game writes."""
    m = s.mask()
    s.polygon(m, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
    lay(s.rgb, m, (16, 18, 30))
    s.pencil([([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], 2)], strength=0.9, colour=(140, 150, 180))


def neon(s, text, cx, y, unit, width):
    """text as a lit sign on strip s: a glow in the six hues from left to right, a white-hot core, a bone edge."""
    m = s.mask()
    write(m, text, (cx - text_width(text, unit) / 2) * s.S, y * s.S, unit * s.S, width * s.S)
    x0 = (cx - text_width(text, unit) / 2) * s.S
    span = text_width(text, unit) * s.S
    hues = [HUES[k] for k in ("photo", "chart", "video", "selfie")]
    for k, hue in enumerate(hues):
        part = s.mask()
        ImageDraw.Draw(part).rectangle((x0 + span * k / 4 - 10 * s.S, 0, x0 + span * (k + 1) / 4 + 10 * s.S,
                                        s.size[1]), fill=255)
        part = blur(part, 8 * s.S)
        lay(s.rgb, ImageChops.multiply(blur(m, 7 * s.S), part), hue, 0.9)
        lay(s.rgb, ImageChops.multiply(blur(m, 2 * s.S), part), mix(hue, (255, 255, 255), 0.3), 0.9)
    lay(s.rgb, m, (255, 252, 246))
    return m


def paint_title(morning):
    """The title, 320 x 240: the glass dimmed, FEED as a lit sign in the feed's hues with the red dot on its D, the
    accent's rule, TAP TURNS RIGHT, and BEST with a plate. The game scrolls tiles up the glass under it and the
    thumb flicks them."""
    s = Strip(W, 0, H, False, (0, 0, 0))
    s.rgb = morning.convert("RGB").resize(s.size, Image.LANCZOS)
    glaze(s.rgb, Image.new("L", s.size, 255), (60, 64, 96), 0.55)
    unit, width = 9.0, 4.2
    neon(s, "FEED", 160, 34, unit, width)
    right = 160 + text_width("FEED", unit) / 2
    badge = s.mask()
    s.ellipse(badge, right + 4, 34, 9, 9)
    lay(s.rgb, blur(badge, 6), ACCENT, 0.5)
    lay(s.rgb, badge, ACCENT)
    words(s, "1", right + 4, 30, 1.2, 1.3, (255, 250, 240))
    rule = s.mask()
    s.polygon(rule, [(70, 104), (250, 104), (250, 106.5), (70, 106.5)])
    lay(s.rgb, rule, ACCENT)
    words(s, "TAP TURNS RIGHT", 160, 112, 1.6, 1.2, BONE)
    words(s, "BEST", TITLE_PLATE[0] - 20, TITLE_PLATE[1] + 5, 1.4, 1.1, BONE)
    plate(s, *TITLE_PLATE)
    return s.rgb.resize((W, H), Image.LANCZOS).convert("RGBA")


def paint_over():
    """The over card, 200 x 100: YOU SAW with a plate for n, then YOU REMEMBER 0. with the 0 in the accent, on a
    dark glass wash with a cold border."""
    w, h = CARD
    s = Strip(w, 0, h, False, INK)
    m = s.mask()
    s.polygon(m, [(0, 0), (w, 0), (w, h), (0, h)])
    s.wash(m, (24, 26, 42), alpha=0.9, rim=0.0, grain=0.5, cell=10, rough=None, soft=0)
    border = s.mask()
    ImageDraw.Draw(border).rectangle((2 * s.S, 2 * s.S, (w - 2) * s.S, (h - 2) * s.S), outline=255, width=s.S)
    lay(s.rgb, border, (150, 170, 210))
    unit = 2.4
    words(s, "YOU SAW", 66, 15, unit, 1.8, BONE)
    plate(s, *CARD_PLATE)
    dot_m = s.mask()
    s.ellipse(dot_m, CARD_PLATE[0] + PLATE_W + 6, CARD_PLATE[1] + PLATE_H - 2, 1.4, 1.4)
    lay(s.rgb, dot_m, BONE)
    text = "YOU REMEMBER "
    full = text + "0."
    x0 = w / 2 - text_width(full, 1.9) / 2
    mm = s.mask()
    write(mm, text, x0 * s.S, 44 * s.S, 1.9 * s.S, 1.5 * s.S)
    lay(s.rgb, mm, BONE)
    zero = s.mask()
    write(zero, "0", (x0 + len(text) * 6 * 1.9) * s.S, 44 * s.S, 1.9 * s.S, 1.8 * s.S)
    lay(s.rgb, blur(zero, 3 * s.S), ACCENT, 0.5)
    lay(s.rgb, zero, ACCENT)
    stop = s.mask()
    write(stop, ".", (x0 + (len(text) + 1) * 6 * 1.9) * s.S, 44 * s.S, 1.9 * s.S, 1.5 * s.S)
    lay(s.rgb, stop, BONE)
    rule = s.mask()
    s.polygon(rule, [(30, 70), (w - 30, 70), (w - 30, 71.5), (30, 71.5)])
    lay(s.rgb, rule, (90, 100, 140))
    return s.rgb.resize(CARD, Image.LANCZOS).convert("RGBA")


# --- the set -------------------------------------------------------------------------------------------------------

def head_name(d, pose):
    return "snake_head_%s_%s" % (d, pose)


def paint_snake():
    morning = paint_morning()
    pics = {"snake_morning": (morning, False)}
    for d in DIRS:
        for pose in POSES:
            pics[head_name(d, pose)] = (facing(head(pose), d), True)
    pics["snake_halo"] = (halo(), True)
    for kind in KINDS:
        pics["snake_tile_" + kind] = (tile(kind), True)
    for k in range(BULGE_POSES):
        pics["snake_bulge_%d" % k] = (bulge(k), True)
    for k in range(SEEN_POSES):
        pics["snake_seen_%d" % k] = (seen(k), True)
    for kind in KINDS:
        pics["snake_turn_" + kind] = (turn(kind), True)
        pics["snake_glow_" + kind] = (glow(kind), True)
    for k in range(BITES):
        pics["snake_bite_%d" % k] = (bite(k), True)
    for k in range(DOT_POSES):
        pics["snake_dot_%d" % k] = (dot(k), True)
    for k in range(RIPPLES):
        pics["snake_ripple_%d" % k] = (ripple(k), True)
    for k in range(PINGS):
        pics["snake_ping_%d" % k] = (ping(k), True)
    for n in range(10):
        pics["snake_digit_%d" % n] = (digit(n), True)
    for k in range(THUMB_POSES):
        pics["snake_thumb_%d" % k] = (thumb(k), True)
    pics["snake_title"] = (paint_title(morning), False)
    pics["snake_over"] = (paint_over(), False)
    return Painting(pics)


# --- the preview sheet ---------------------------------------------------------------------------------------------

HALO_ALPHA, GLOW_ALPHA = 70, 84  # games/arcade.py's


def over(out, img, x, y):
    out.paste(img, (x, y), img)


def seen_through(out, img, x, y, alpha):
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    layer.paste(img, (x, y))
    out.paste(layer.convert("RGB"), (0, 0), layer.getchannel("A").point(lambda v: v * alpha // 255))


def cell_xy(cell):
    return LEFT + cell[0] * CELL, TOP + cell[1] * CELL


BODY = [(14, 9), (13, 9), (12, 9), (11, 9), (10, 9), (10, 10), (10, 11), (10, 12), (11, 12), (12, 12), (13, 12),
        (14, 12), (15, 12), (16, 12), (17, 12), (17, 13), (17, 14), (16, 14), (15, 14), (14, 14), (13, 14), (12, 14)]


def snake_scene(pics, pose="open", flip=0):
    """A frame of play: the feed crawling right with a dot bulging down it, the head's glow, a dot ahead."""
    out = pics["snake_morning"].copy()
    for k, cell in enumerate(BODY[1:], 1):
        x, y = cell_xy(cell)
        seen_through(out, pics["snake_glow_" + KINDS[(len(BODY) - k) * 5 % 6]], x + 6 - GLOW // 2, y + 6 - GLOW // 2,
                     GLOW_ALPHA)
    for k, cell in enumerate(BODY[1:], 1):
        name = "snake_tile_" + KINDS[(len(BODY) - k) * 5 % 6]
        if k <= flip:
            name = "snake_seen_2"
        over(out, pics[name], *cell_xy(cell))
    bx, by = cell_xy(BODY[6])
    over(out, pics["snake_bulge_0"], bx - 2, by - 2)
    hx, hy = cell_xy(BODY[0])
    seen_through(out, pics["snake_halo"], hx + 6 - HALO // 2, hy + 6 - HALO // 2, HALO_ALPHA)
    over(out, pics[head_name("r", pose)], hx - 2, hy - 2)
    over(out, pics["snake_dot_1"], *cell_xy((19, 9)))
    return out.convert("RGB")


def snake_frame(painting):
    return snake_scene(painting.images())


def snake_sheet(painting, sheet, y):
    """A frame of play at 2x; the tiles, the heads, the bulge, the flip and the dot at 4x; the thumb; the title and
    the card."""
    pics = painting.images()
    sheet.put("snake (FEED): snake_morning in play, the feed, the head and its glow, a dot, at 2x",
              snake_scene(pics).resize((W * 2, H * 2), Image.NEAREST), 10, y)
    x = W * 2 + 30
    row = Image.new("RGB", (2 * len(KINDS) * 13 + 3 * 13 + 3 * 13, 14), GLASS)
    for k, kind in enumerate(KINDS):
        over(row, pics["snake_tile_" + kind], k * 13 + 1, 1)
        over(row, pics["snake_turn_" + kind], (len(KINDS) + SEEN_POSES + DOT_POSES + k) * 13 + 1, 1)
    for k in range(SEEN_POSES):
        over(row, pics["snake_seen_%d" % k], (len(KINDS) + k) * 13 + 1, 1)
    for k in range(DOT_POSES):
        over(row, pics["snake_dot_%d" % k], (len(KINDS) + SEEN_POSES + k) * 13 + 1, 1)
    at = sheet.put("snake_tile_<kind>, snake_seen_0..2, snake_dot_0..2, snake_turn_<kind>, at 2x",
                   row.resize((row.width * 2, row.height * 2), Image.NEAREST), x, y) + 10
    heads = Image.new("RGB", (len(POSES) * 18 + 2 * 18, len(DIRS) * 18), GLASS)
    for j, d in enumerate(DIRS):
        for i, pose in enumerate(POSES):
            over(heads, pics[head_name(d, pose)], i * 18 + 1, j * 18 + 1)
    for k in range(BULGE_POSES):
        over(heads, pics["snake_bulge_%d" % k], (len(POSES) + k) * 18 + 1, 1)
    at = sheet.put("snake_head_<dir>_<pose> (open, gulp, chew, glow) and snake_bulge_0..1, at 4x",
                   heads.resize((heads.width * 4, heads.height * 4), Image.NEAREST), x, at) + 10
    thumbs = Image.new("RGB", (THUMB_POSES * 34 + 10 * (DIGIT_W + 2) + BITES * (BITE + 2), BITE), GLASS)
    for k in range(BITES):
        over(thumbs, pics["snake_bite_%d" % k], THUMB_POSES * 34 + 10 * (DIGIT_W + 2) + k * (BITE + 2), 0)
    for k in range(THUMB_POSES):
        over(thumbs, pics["snake_thumb_%d" % k], k * 34, 0)
    for n in range(10):
        over(thumbs, pics["snake_digit_%d" % n], THUMB_POSES * 34 + n * (DIGIT_W + 2), 14)
    sheet.put("snake_thumb_0..2, snake_digit_0..9, snake_bite_0..1, at 2x (the glows are in the frame)",
              thumbs.resize((thumbs.width * 2, thumbs.height * 2), Image.NEAREST), x, at)
    y += H * 2 + 32
    title = pics["snake_title"].copy()
    number(title, pics, 42, TITLE_PLATE[0] + PLATE_W - 3, TITLE_PLATE[1] + 3)
    sheet.put("snake_title, best 42", title.convert("RGB"), 10, y)
    end = snake_scene(pics, "gulp", flip=12).convert("RGBA")
    end.paste(pics["snake_over"], (60, 70))
    number(end, pics, 21, 60 + CARD_PLATE[0] + PLATE_W - 3, 70 + CARD_PLATE[1] + 3)
    sheet.put("game over: the flip to SEEN and snake_over", end.convert("RGB"), 350, y)
    return y + H + 32


def number(out, pics, value, right, top):
    for k, ch in enumerate(reversed(str(value))):
        over(out, pics["snake_digit_" + ch], right - DIGIT_W * (k + 1), top)


def is_red(rgb):
    """Whether a colour reads as red: a red hue, strong and lit. The accent is the only red the feed may hold."""
    h, s, v = rgb_to_hsv(*(c / 255 for c in rgb))
    return (h < 15 / 360 or h > 345 / 360) and s > 0.5 and v > 0.3


ART_SET = ArtSet("snake", 5731, paint_snake, sheet_fn=snake_sheet, scene_fn=snake_frame)
