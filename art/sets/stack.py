"""The stack game's art as RENT (P568): watercolour noir at noon. A bleached sky, a hard white sun, the town in long
grey-violet shadows, a billboard that sells flats from an empty plate, and the floors of a tower nobody lives in:
the top one lit, the show flat, every one below dark. The only saturated colour is the accent."""

from math import sin

from PIL import Image, ImageChops, ImageDraw

from artset import ArtSet, Painting
from brush import ACCENT, H, W, Sprite, Strip, autocontrast, blur, glaze, jitter, lay, rnd, scale
from letters import text_width, write


STACK_FLOOR, BLOCK_H = 234, 14
INK, BONE = (24, 20, 30), (236, 230, 214)  # the noir pair: the pencil and the paper in the sun
SHADOW = (96, 86, 116)  # grey-violet, every shadow at noon
NOON = ((128, 120, 150), (196, 192, 208), (238, 234, 226))  # the sky from the top, to the middle, to the haze
CONCRETE = ((178, 174, 170), (164, 166, 174), (186, 180, 172), (156, 154, 164), (172, 170, 178), (190, 186, 180),
            (160, 156, 154), (170, 172, 168))  # eight greys a little warm or cool, one per floor in turn
LIT, DARK = (250, 232, 188), INK  # a window of the show flat, and one where nobody lives
BOARD = (222, 20, 314, 57)  # the billboard under the score bar: x0, y0, x1, y1
PLATE = (248, 35, 305, 53)  # its empty number plate; the game writes the rent on it, right-aligned at x 301, y 38
DIGIT_W, DIGIT_H = 8, 12
SOLD = (58, 18)  # the plate at game over, in the accent, drawn over the empty one at (248, 36)
CARD = (200, 100)  # the over card, at (60, 70); its plates for the floors and the best at x 64 and 140, y 50
CARD_PLATES = ((64, 50), (140, 50))
TITLE_PLATE = (156, 158)  # the title's plate for the best
PLATE_W, PLATE_H = 40, 17


def noon_at(y):
    t = max(0.0, min(1.0, y / STACK_FLOOR))
    a, b, t = (NOON[0], NOON[1], t / 0.5) if t < 0.5 else (NOON[1], NOON[2], (t - 0.5) / 0.5)
    return tuple(int(p + (q - p) * t) for p, q in zip(a, b))


def calm(s, lo=0.35):
    """A mask that is lo across the tower's columns (x 60 to 260) and full at the sides, and 0 over the score bar."""
    m = Image.new("L", s.size, 255)
    d = ImageDraw.Draw(m)
    d.rectangle((60 * s.S, 0, 260 * s.S, s.size[1]), fill=int(255 * lo))
    m = blur(m, 30 * s.S / 4)
    ImageDraw.Draw(m).rectangle((0, 0, s.size[0], 17 * s.S), fill=0)
    return m


def town(x0, x1, base, tall):
    """Houses and blocks from x0 to x1 standing on base: (body polygons, their shadow faces, windows)."""
    bodies, faces, windows = [], [], []
    x = x0
    while x < x1:
        w = rnd.uniform(9, 18)
        h = rnd.choice((rnd.uniform(10, 18), rnd.uniform(20, tall)))
        roof = rnd.random() < 0.5  # a pitched roof, else a flat block
        top = base - h
        body = [(x, base), (x, top)] + ([(x + w / 2, top - w * 0.45)] if roof else []) + [(x + w, top), (x + w, base)]
        bodies.append(body)
        faces.append([(x + w * 0.62, base), (x + w * 0.62, top + (w * 0.2 if roof else 0)), (x + w, top),
                      (x + w, base)])
        for wy in range(int(top + 4), int(base - 3), 5):
            for wx in (x + 2.5, x + w * 0.62 - 3.5):
                if rnd.random() < 0.55:
                    windows.append((wx, wy))
        x += w + rnd.uniform(-1, 2)
    return bodies, faces, windows


def paint_noon():
    """Noon in the city: a bleached sky with grey washes, a hard white sun, a far skyline and a crane, the town in long
    shadows, the billboard with its empty plate, a pavement and the tarmac from row 234."""
    s = Strip(W, 0, H, False, noon_at)
    sides = calm(s)
    blooms = autocontrast(blur(s.noise(150), 26))
    glaze(s.rgb, ImageChops.multiply(scale(blooms, 1.5, -150), sides), (170, 160, 196), 0.4)  # grey-violet washes
    sx, sy, sr = 52, 46, 14
    glow = s.mask()  # the white-out: the sun bleaches the sky close round it, the rest stays heavy
    s.ellipse(glow, sx, sy, sr * 2.2, sr * 2.2)
    lay(s.rgb, blur(glow, sr * 3), (246, 244, 240), 0.9)
    sun = s.mask()
    s.ellipse(sun, sx, sy, sr, sr)
    lay(s.rgb, sun, (255, 255, 255))
    s.pencil([([(sx + sr * 1.25 * sin(a / 10 + 1.571), sy + sr * 1.25 * sin(a / 10)) for a in range(64)], 2)],
             strength=0.25, colour=SHADOW)  # a faint ring: the sun is a hole in the sky
    # The far skyline across the middle, pale and flat: it says city, and keeps out of the tower's way.
    far, x = s.mask(), 0.0
    while x < W:
        w, h = rnd.uniform(10, 22), rnd.uniform(26, 70)
        s.polygon(far, [(x, 224), (x, 224 - h), (x + w, 224 - h), (x + w, 224)])
        x += w + rnd.uniform(0, 6)
    s.wash(far, (204, 200, 214), alpha=0.8, rim=0.5, rim_px=4, grain=0.25, cell=14, rough=(1, 0.3, 8), dark=0.9,
           soft=0.8)
    # A tower crane on the left, in ink: who builds here builds for nobody.
    crane = [([(30, 224), (30, 92)], 5), ([(36, 224), (36, 92)], 5), ([(8, 92), (128, 92)], 5),
             ([(8, 98), (128, 98)], 3), ([(33, 92), (33, 78), (8, 92)], 3), ([(33, 78), (128, 92)], 2),
             ([(96, 98), (96, 126)], 2)]
    crane += [([(30, y), (36, y - 8)], 2) for y in range(220, 100, -8)]
    crane += [([(x, 92), (x + 6, 98)], 2) for x in range(40, 128, 8)]
    s.pencil(crane, strength=0.9, colour=INK)
    weight = s.mask()
    s.polygon(weight, [(8, 99), (20, 99), (20, 108), (8, 108)])
    s.wash(weight, (110, 102, 122), alpha=1.0, rim=0.3, rim_px=3, grain=0.2, cell=6, rough=None, soft=0.5)
    x0, y0, x1, y1 = BOARD  # the billboard's posts, down behind the right-hand blocks
    s.pencil([([(x0 + 18, y1), (x0 + 18, 224)], 6), ([(x1 - 18, y1), (x1 - 18, 224)], 6),
              ([(x0 + 18, y1 + 20), (x1 - 18, y1 + 8)], 3), ([(x0 + 18, y1 + 8), (x1 - 18, y1 + 20)], 3)],
             strength=0.9, colour=INK)
    # The town at each side: lit fronts, grey-violet shadow faces, dark windows, and long shadows thrown to the right.
    for x0, x1, tall in ((0, 66, 44), (248, W, 90)):
        bodies, faces, windows = town(x0, x1, 222, tall)
        m = s.mask()
        for body in bodies:
            s.polygon(m, body)
        s.wash(m, (214, 208, 202), alpha=0.97, rim=0.5, rim_px=4, grain=0.3, cell=10, rough=(1, 0.3, 6), dark=0.8,
               soft=0.8)
        f = s.mask()
        for face in faces:
            s.polygon(f, face)
        glaze(s.rgb, ImageChops.multiply(blur(f, 1.5), m), SHADOW, 0.85)
        throw = s.mask()
        for body in bodies:  # each shadow lies along the pavement, three times as long as the body is wide
            left, right = body[0][0], body[-1][0]
            s.polygon(throw, [(left, 222), (right, 222), (right + (right - left) * 3, 234), (left + 6, 234)])
        glaze(s.rgb, blur(throw, 2), SHADOW, 0.6)
        dark = s.mask()
        for wx, wy in windows:
            s.polygon(dark, [(wx, wy), (wx + 2, wy), (wx + 2, wy + 2.4), (wx, wy + 2.4)])
        lay(s.rgb, dark, INK, 0.85)
        s.pencil([(jitter(b, 0.25), 2) for b in bodies], strength=0.45, colour=INK)
    # The billboard: FLATS FROM, a red rule, and the empty plate.
    x0, y0, x1, y1 = BOARD
    board = s.mask()
    s.polygon(board, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    s.wash(board, BONE, alpha=1.0, rim=0.6, rim_px=4, grain=0.3, cell=8, rough=None, dark=0.86, soft=0)
    words = s.mask()
    unit = 1.25
    write(words, "FLATS FROM", ((x0 + x1) / 2 - text_width("FLATS FROM", unit) / 2) * s.S, (y0 + 4) * s.S, unit * s.S,
          1.3 * s.S)
    lay(s.rgb, words, INK)
    rule = s.mask()
    s.polygon(rule, [(x0 + 5, y0 + 13.5), (x1 - 5, y0 + 13.5), (x1 - 5, y0 + 15), (x0 + 5, y0 + 15)])
    lay(s.rgb, rule, ACCENT)
    px0, py0, px1, py1 = PLATE
    plate = s.mask()
    s.polygon(plate, [(px0, py0 + 1), (px1, py0 + 1), (px1, py1), (px0, py1)])
    lay(s.rgb, plate, (250, 248, 242))
    s.pencil([([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], 3),
              ([(px0, py0 + 1), (px1, py0 + 1), (px1, py1), (px0, py1), (px0, py0 + 1)], 2)], strength=0.9, colour=INK)
    # The street: the tarmac from row 234, with a white lane.
    tar = s.mask()
    s.polygon(tar, [(0, STACK_FLOOR), (W, STACK_FLOOR), (W, H + 2), (0, H + 2)])
    s.wash(tar, (58, 54, 66), alpha=1.0, rim=0.0, grain=0.4, cell=6, rough=None, soft=0)
    lane = s.mask()
    for x in range(6, W, 26):
        s.polygon(lane, [(x, 236.6), (x + 13, 236.6), (x + 13, 237.8), (x, 237.8)])
    lay(s.rgb, lane, (226, 222, 214), 0.85)
    s.pencil([(jitter([(0, STACK_FLOOR + 0.3), (W, STACK_FLOOR + 0.3)], 0.2), 3)], strength=0.8, colour=INK)
    s.paper(0.08)
    return s.rgb.resize((W, H), Image.LANCZOS).convert("RGBA")


def paint_flat(colour, lit):
    """A 320 x 14 floor of flats: concrete, a sunlit slab on top and a shadow under it, 3 x 3 windows every 8 px from
    the left end, so a floor cut to any width ends where the game draws its pencil end. Lit: the show flat, its
    windows warm. Dark: a floor below it, the concrete greyer, the windows ink: nobody lives there."""
    if not lit:
        colour = tuple(int(c * 0.72 + s * 0.28 * 0.6) for c, s in zip(colour, SHADOW))
    s = Strip(W, 0, BLOCK_H, False, colour)
    body = s.mask()
    s.polygon(body, [(0, 0), (W, 0), (W, BLOCK_H), (0, BLOCK_H)])
    s.wash(body, colour, alpha=1.0, rim=0.0, grain=0.5, cell=5, rough=None, soft=0)
    drift = autocontrast(blur(s.noise(70), 9))  # stains along the length
    glaze(s.rgb, scale(drift, 1.3, -120), SHADOW, 0.45)
    slab = s.mask()
    s.polygon(slab, [(0, 1), (W, 1), (W, 2.6), (0, 2.6)])
    lay(s.rgb, blur(slab, 1.5), BONE if lit else tuple(min(255, c + 30) for c in colour), 0.75)
    under = s.mask()
    s.polygon(under, [(0, 2.8), (W, 2.8), (W, 4.2), (0, 4.2)])
    glaze(s.rgb, blur(under, 1.5), SHADOW, 0.7)
    foot = s.mask()
    s.polygon(foot, [(0, 10), (W, 10), (W, 13), (0, 13)])
    glaze(s.rgb, blur(foot, 2), SHADOW, 0.75)
    drips = s.mask()  # rain streaks under the windows, here and there
    for x in range(2, W, 8):
        if rnd.random() < 0.35:
            s.polygon(drips, [(x + 0.6, 8), (x + 1.6, 8), (x + 1.3, 11.5), (x + 0.9, 11.5)])
    glaze(s.rgb, blur(drips, 1.2), SHADOW, 0.5)
    img = s.rgb.resize((W, BLOCK_H), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    for x in range(2, W, 8):  # the windows at 1x, so each stays a hard 3 x 3
        if lit:
            d.rectangle((x, 5, x + 2, 7), fill=LIT if rnd.random() < 0.8 else (236, 214, 170))
            d.point((x, 5), fill=(255, 246, 222))  # a glint in its corner
        else:
            d.rectangle((x, 5, x + 2, 7), fill=DARK)
        d.line([(x, 8), (x + 2, 8)], fill=tuple(min(255, c + 24) for c in colour))  # the sill in the sun
    ink = tuple(int(i * 0.85 + c * 0.15) for i, c in zip(INK, colour))
    for x in range(W):  # the pencil rows, a little uneven
        k = 1.0 + 0.15 * sin(x * 0.7) * sin(x * 0.13)
        for y in (0, BLOCK_H - 1):
            img.putpixel((x, y), tuple(max(0, min(255, int(c * k))) for c in ink))
    return img.convert("RGBA")


def paint_hook():
    """The crane hook, 16 x 16 keyed: a steel block with a red band, a shank, and the hook's curve."""
    sp = Sprite(16, 16)
    sp.part(sp.shape("rect", 3.5, 0, 12.5, 6.5, 1), (124, 120, 134), light=(11, 1, 4, (190, 186, 196)))
    sp.part(sp.shape("rect", 3.5, 2.6, 12.5, 4.2, 0), ACCENT, rim=0.2, grain=0)
    for x in range(5, 12):  # the band's middle row at 1x, so the accent stays the accent after the shrink
        sp.dot(x, 3, ACCENT)
    sp.part(sp.shape("line", (8, 6), (8, 10), width=1.8), (96, 92, 106), rim=0.1)
    sp.part(sp.shape("line", (8, 9.5), (8.4, 12.5), (7, 14.4), (4.8, 14.6), (3.6, 13), (3.8, 11.6), width=1.7),
            (96, 92, 106), light=(8, 12, 3, (170, 166, 178)), rim=0.2)
    return sp.cut(ink=INK)


def paint_digit(d):
    """One digit of the rent, 8 x 12 keyed: ink strokes, cut to a hard mask, for the billboard's plate."""
    k = 8
    m = Image.new("L", (DIGIT_W * k, DIGIT_H * k), 0)
    write(m, str(d), 1.2 * k, 1.2 * k, 1.5 * k, 1.5 * k)
    a = m.resize((DIGIT_W, DIGIT_H), Image.BOX).point(lambda v: 255 if v >= 100 else 0)
    out = Image.new("RGBA", (DIGIT_W, DIGIT_H), INK + (255,))
    out.putalpha(a)
    return out


def words(s, text, cx, y, unit, width, colour):
    """Stroke letters on strip s, centred on game x cx, the top at game y."""
    m = s.mask()
    write(m, text, (cx - text_width(text, unit) / 2) * s.S, y * s.S, unit * s.S, width * s.S)
    lay(s.rgb, m, colour)


def plate(s, x, y, w=PLATE_W, h=PLATE_H):
    """A small empty number plate in bone with a pencil border, for digits the game writes."""
    m = s.mask()
    s.polygon(m, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
    lay(s.rgb, m, (250, 248, 242))
    s.pencil([([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], 2)], strength=0.9, colour=INK)


def paint_title(noon):
    """The title, 320 x 240: the noon gone dark round its white sun, RENT in bone with an ink shadow and a red rule,
    TAP TO DROP, and BEST with a plate. The billboard stays, so the SOLD plate lands on it."""
    s = Strip(W, 0, H, False, (0, 0, 0))
    s.rgb = noon.convert("RGB").resize(s.size, Image.LANCZOS)
    glaze(s.rgb, Image.new("L", s.size, 255), (70, 62, 92), 0.75)
    m = s.mask()
    s.polygon(m, [(0, 60), (W, 60), (W, 182), (0, 182)])
    glaze(s.rgb, blur(s.roughen(m, 3, 0.5, 14), 6), INK, 0.8)  # a band of night across the noon, for the word
    words(s, "RENT", 163, 73, 10, 4.5, INK)  # the shadow first
    words(s, "RENT", 160, 70, 10, 4.5, BONE)
    rule = s.mask()
    s.polygon(rule, [(50, 136), (270, 136), (270, 138.5), (50, 138.5)])
    lay(s.rgb, rule, ACCENT)
    words(s, "TAP TO DROP", 160, 144, 1.6, 1.2, BONE)
    words(s, "BEST", 136, 163, 1.4, 1.1, BONE)
    plate(s, *TITLE_PLATE)
    s.paper(0.06)
    return s.rgb.resize((W, H), Image.LANCZOS).convert("RGBA")


def paint_over():
    """The over card, 200 x 100: SOLD OUT in the accent, 0 RESIDENTS in bone, and plates for the floors and the
    best, on an ink wash with a bone border."""
    w, h = CARD
    s = Strip(w, 0, h, False, INK)
    m = s.mask()
    s.polygon(m, [(0, 0), (w, 0), (w, h), (0, h)])
    s.wash(m, (40, 34, 50), alpha=0.9, rim=0.0, grain=0.5, cell=10, rough=None, soft=0)
    border = s.mask()
    ImageDraw.Draw(border).rectangle((2 * s.S, 2 * s.S, (w - 2) * s.S, (h - 2) * s.S), outline=255, width=s.S)
    lay(s.rgb, border, BONE)
    words(s, "SOLD OUT", w / 2, 9, 3, 2.2, ACCENT)
    words(s, "· 0 RESIDENTS", w / 2, 33, 1.5, 1.1, BONE)
    words(s, "FLOORS", 41, 55, 1.2, 1.0, BONE)
    words(s, "BEST", 123, 55, 1.2, 1.0, BONE)
    for x, y in CARD_PLATES:
        plate(s, x, y)
    return s.rgb.resize(CARD, Image.LANCZOS).convert("RGBA")


def paint_sold():
    """The plate at game over, 58 x 18: SOLD in bone on the accent, an ink border."""
    w, h = SOLD
    s = Strip(w, 0, h, False, ACCENT)
    words(s, "SOLD", w / 2, 4.5, 1.6, 1.4, BONE)
    s.pencil([([(0.5, 0.5), (w - 0.5, 0.5), (w - 0.5, h - 0.5), (0.5, h - 0.5), (0.5, 0.5)], 4)], strength=1.0,
             colour=INK)
    return s.rgb.resize(SOLD, Image.LANCZOS).convert("RGBA")


def paint_cot(degrees):
    """A cot, 16 x 16 keyed, turned by degrees: an empty bed, its blanket in the accent. It rides a cut-off slab
    down to the street: nobody was ever in it."""
    sp = Sprite(16, 16)
    sp.part(sp.shape("line", (2.5, 9.6), (2.5, 12.6), width=1.1), (96, 92, 106), rim=0)
    sp.part(sp.shape("line", (13.5, 9.6), (13.5, 12.6), width=1.1), (96, 92, 106), rim=0)
    sp.part(sp.shape("rect", 1.5, 8.6, 14.5, 10.2, 0.4), (110, 104, 120), rim=0.1)
    sp.part(sp.shape("rect", 2, 5.6, 14, 9, 0.8), BONE, rim=0.3)
    sp.part(sp.shape("ellipse", 2.4, 4.6, 6.2, 7.4), (250, 246, 236), rim=0.3)
    sp.part(sp.shape("rect", 6.6, 5.2, 14.2, 9.2, 0.6), ACCENT, rim=0, grain=0)
    sp.turn(degrees, (8, 8))
    return sp.cut(ink=INK)


def paint_stack():
    """Every stack picture: the noon backdrop, the lit and the dark floors in turn, the hook, the rent's digits, the
    cot's four turns, the SOLD plate, the title and the over card."""
    pics = {"stack_noon": (paint_noon(), False)}
    for i, colour in enumerate(CONCRETE):
        pics["stack_lit%d" % i] = (paint_flat(colour, True), False)
    for i, colour in enumerate(CONCRETE):
        pics["stack_dark%d" % i] = (paint_flat(colour, False), False)
    pics["stack_hook"] = (paint_hook(), True)
    for d in range(10):
        pics["stack_digit%d" % d] = (paint_digit(d), True)
    for k in range(4):  # a quarter turn a frame: it tumbles end over end
        pics["stack_cot%d" % k] = (paint_cot(90 * k), True)
    pics["stack_sold"] = (paint_sold(), False)
    pics["stack_title"] = (paint_title(pics["stack_noon"][0]), False)
    pics["stack_over"] = (paint_over(), False)
    return Painting(pics)


def over(out, img, x, y):
    """img on out at (x, y), its clear pixels skipped, as the board's keyed blit draws it."""
    out.paste(img, (x, y), img)


def stack_scene(pics, floors=10):
    """The tower as the game draws it: the dark floors, the lit show flat on top, the next one on the hook, its cable,
    and the rent on the plate."""
    out = pics["stack_noon"].copy()
    x, w = 90, 140
    rows = []
    for i in range(floors):
        rows.append((x, 220 - (i + 1) * BLOCK_H, w, ("stack_lit%d" if i == floors - 1 else "stack_dark%d") % (i % 8)))
        cut = (3, 7, 2, 11, 5, 9, 4, 6, 8, 3)[i % 10]
        x, w = (x + cut, w - cut) if i % 2 else (x, w - cut)
    hx, hy = 150, 220 - (floors + 1) * BLOCK_H
    rows.append((hx, hy, w, "stack_lit%d" % (floors % 8)))
    d = ImageDraw.Draw(out)
    d.line([(hx + w // 2 - 6, 16), (hx + w // 2, hy - 12)], fill=INK)
    over(out, pics["stack_hook"], hx + w // 2 - 8, hy - 16)
    for x, y, w, name in rows:
        out.paste(pics[name].crop((0, 0, w, BLOCK_H)), (x, y))
        d.line([(x, y), (x, y + BLOCK_H - 1)], fill=INK)
        d.line([(x + w - 1, y), (x + w - 1, y + BLOCK_H - 1)], fill=INK)
    for k, ch in enumerate(reversed(str(900 + 140 * floors))):
        over(out, pics["stack_digit" + ch], PLATE[2] - 4 - DIGIT_W * (k + 1), PLATE[1] + 3)
    return out.convert("RGB")


def stack_frame(painting):
    return stack_scene(painting.images())


def stack_sheet(painting, sheet, y):
    """The tower as the game draws it, then a lit and a dark floor, the hook and the digits, enlarged."""
    pics = painting.images()
    sheet.put("stack (RENT): stack_noon with ten floors, the hook and the rent, at 2x",
              stack_scene(pics).resize((W * 2, H * 2), Image.NEAREST), 10, y)
    x, at = W * 2 + 30, y
    for name in ("stack_lit0", "stack_lit3", "stack_dark0", "stack_dark3"):
        at = sheet.put("%s 320x14, first 160 px at 4x" % name,
                       pics[name].convert("RGB").crop((0, 0, 160, BLOCK_H)).resize((640, BLOCK_H * 4), Image.NEAREST),
                       x, at) + 10
    strip = Image.new("RGB", (16 + 10 * (DIGIT_W + 2), 16), BONE)
    over(strip, pics["stack_hook"], 0, 0)
    for k in range(10):
        over(strip, pics["stack_digit%d" % k], 18 + k * (DIGIT_W + 2), 2)
    sheet.put("stack_hook 16x16 and stack_digit0..9 8x12, at 4x", strip.resize((strip.width * 4, 64), Image.NEAREST),
              x, at)
    y += H * 2 + 32
    put = (900 + 140 * 12, 12)
    title = pics["stack_title"].copy()
    title.paste(pics["stack_lit0"].crop((0, 0, 140, BLOCK_H)), (90, 206))
    over(title, pics["stack_hook"], 152, 190)
    title.paste(pics["stack_sold"], (248, 36))
    number(title, pics, put[1], TITLE_PLATE)
    sheet.put("stack_title, the floor landed, SOLD, best 12", title.convert("RGB"), 10, y)
    end = stack_scene(pics, 6).convert("RGBA")
    end.paste(pics["stack_sold"], (248, 36))
    end.paste(pics["stack_over"], (60, 70))
    for (px, py), value in zip(CARD_PLATES, (6, 12)):
        number(end, pics, value, (60 + px, 70 + py))
    sheet.put("game over: stack_over and stack_sold", end.convert("RGB"), 350, y)
    strip = Image.new("RGB", (4 * 18 + SOLD[0], 18), BONE)
    for k in range(4):
        over(strip, pics["stack_cot%d" % k], k * 18, 1)
    strip.paste(pics["stack_sold"], (72, 0))
    sheet.put("stack_cot0..3 and stack_sold, at 4x", strip.resize((strip.width * 4, 72), Image.NEAREST), 690, y)
    return y + H + 32


def number(out, pics, value, at):
    """value in digit pictures on a plate at (x, y), right-aligned, as the game writes it."""
    x, y = at
    for k, ch in enumerate(reversed(str(value))):
        over(out, pics["stack_digit" + ch], x + PLATE_W - 3 - DIGIT_W * (k + 1), y + 3)


ART_SET = ArtSet("stack", 563, paint_stack, sheet_fn=stack_sheet, scene_fn=stack_frame, ink_accent=ACCENT)
