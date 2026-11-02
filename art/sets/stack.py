"""The stack game's art (P563): a dusk-to-night background with a far town, the eight blocks and the mover."""

from math import sin

from PIL import Image, ImageChops, ImageDraw

from brush import H, W, ArtSet, Painting, Strip, autocontrast, blur, glaze, jitter, lay, rnd, scale


STACK_FLOOR, BLOCK_H = 234, 14
PALETTE = ((230, 40, 40), (250, 140, 30), (250, 220, 40), (40, 210, 70), (40, 220, 230), (50, 90, 240),
           (230, 60, 220), (226, 230, 244))  # gfx.PALETTE in its order; white painted as a cool paper white
NIGHT = ((26, 22, 66), (74, 46, 110), (150, 82, 128))  # the sky from the top, to the middle, to the horizon
STACK_INK = (40, 30, 50)  # the pencil, as the game draws the block ends


def night_at(y):
    t = max(0.0, min(1.0, (y - 16) / (STACK_FLOOR - 16)))
    a, b, t = (NIGHT[0], NIGHT[1], t / 0.6) if t < 0.6 else (NIGHT[1], NIGHT[2], (t - 0.6) / 0.4)
    return tuple(int(p + (q - p) * t) for p, q in zip(a, b))


def calm(s, lo=0.35):
    """A mask that is lo across the tower's columns (x 60 to 260) and full at the sides, and 0 over the score bar."""
    m = Image.new("L", s.size, 255)
    d = ImageDraw.Draw(m)
    d.rectangle((60 * s.S, 0, 260 * s.S, s.size[1]), fill=int(255 * lo))
    m = blur(m, 30 * s.S / 4)
    ImageDraw.Draw(m).rectangle((0, 0, s.size[0], 17 * s.S), fill=0)
    return m


def paint_stack_bg():
    """Dusk to night: violet and indigo washes, soft stars, a pale moon, a far town with lit windows, a stone floor."""
    s = Strip(W, 0, H, False, night_at)
    blooms = autocontrast(blur(s.noise(160), 24))
    sides = calm(s)
    glaze(s.rgb, ImageChops.multiply(scale(blooms, 1.5, -150), sides), (150, 120, 220), 0.45)  # indigo blooms
    glaze(s.rgb, ImageChops.multiply(scale(ImageChops.invert(blooms), 1.4, -170), sides), (220, 150, 210), 0.35)
    mx, my, mr = 266, 50, 12
    halo = s.mask()
    s.ellipse(halo, mx, my, mr * 3, mr * 3, 110)
    lay(s.rgb, blur(halo, mr * 5), (176, 160, 214))
    moon = s.mask()
    s.ellipse(moon, mx, my, mr, mr)
    s.wash(moon, (244, 238, 214), alpha=0.98, rim=0.35, rim_px=6, grain=0.15, cell=12, rough=(2, 0.3, 10), dark=0.9,
           soft=1.5)
    craters = s.mask()
    for cx, cy, r in ((-4, -3, 3.2), (3, 2, 2.4), (-2, 6, 1.8), (6, -5, 1.4)):
        s.ellipse(craters, mx + cx, my + cy, r, r * 0.9)
    glaze(s.rgb, ImageChops.multiply(blur(craters, 3), moon), (214, 204, 196), 0.6)
    stars, twinkles = s.mask(), []
    for _ in range(46):
        x, y = rnd.uniform(4, W - 4), rnd.uniform(22, 170)
        middle = 64 < x < 256
        if middle and rnd.random() < 0.55:
            continue
        r = rnd.uniform(0.5, 0.9) * (0.7 if middle else 1.0)
        s.ellipse(stars, x, y, r, r, 255 if not middle else 170)
        if not middle and r > 0.8 and len(twinkles) < 6 and abs(x - mx) > 22:
            twinkles.append((x, y))
    lay(s.rgb, blur(stars, 2.2), (255, 246, 214))
    rays = s.mask()
    d = ImageDraw.Draw(rays)
    for x, y in twinkles:  # a four-pointed twinkle
        px, py = x * s.S, y * s.S
        d.line([(px - 14, py), (px + 14, py)], fill=230, width=2)
        d.line([(px, py - 14), (px, py + 14)], fill=230, width=2)
    lay(s.rgb, blur(rays, 1.2), (255, 250, 230))
    # The far hills, low in the middle, and a little town at each side with warm windows.
    hill = [(x, 214 - 10 * (0.5 + 0.5 * sin(x / 34 + 1.3)) * (1.0 if not 60 < x < 260 else 0.5)) for x in range(0, W + 1, 2)]
    m = s.mask()
    s.polygon(m, hill + [(W, STACK_FLOOR + 2), (0, STACK_FLOOR + 2)])
    s.wash(m, (70, 44, 92), alpha=0.95, rim=0.6, rim_px=6, grain=0.3, cell=16, rough=(1.5, 0.35, 8), dark=0.8, soft=1)
    town, windows = s.mask(), []
    for x0, x1 in ((0, 64), (250, W)):
        x = x0
        while x < x1:
            w, h = rnd.uniform(8, 16), rnd.choice((rnd.uniform(8, 16), rnd.uniform(18, 34)))
            gy = 222
            body = [(x, gy + 14), (x, gy - h), (x + w / 2, gy - h - w * 0.45), (x + w, gy - h), (x + w, gy + 14)]
            s.polygon(town, body)
            for wy in range(int(gy - h + 4), int(gy - 2), 6):
                for wx in (x + 2.5, x + w - 4.5):
                    if rnd.random() < 0.4:
                        windows.append((wx, wy))
            x += w + rnd.uniform(-1, 2)
    s.wash(town, (46, 32, 70), alpha=0.97, rim=0.5, rim_px=4, grain=0.25, cell=10, rough=(1, 0.3, 6), dark=0.78,
           soft=0.8)
    lit = s.mask()
    for wx, wy in windows:
        s.polygon(lit, [(wx, wy), (wx + 2, wy), (wx + 2, wy + 2.4), (wx, wy + 2.4)])
    lay(s.rgb, blur(lit, 3), (255, 170, 80), 0.5)  # the glow
    lay(s.rgb, lit, (255, 214, 120))
    # The stone floor from row 234: a grey-violet wash, a pencil line on top, joints between the stones.
    floor = s.mask()
    s.polygon(floor, [(0, STACK_FLOOR), (W, STACK_FLOOR), (W, H + 2), (0, H + 2)])
    s.wash(floor, (122, 110, 132), alpha=1.0, rim=0.0, grain=0.35, cell=12, rough=None, soft=0)
    stones = s.mask()
    for x in range(0, W, 18):  # each stone a little lighter on top
        s.ellipse(stones, x + 9, STACK_FLOOR + 2.5, 7, 1.6)
    lay(s.rgb, ImageChops.multiply(blur(stones, 3), floor), (160, 150, 172), 0.6)
    joints = [([(x, STACK_FLOOR + 0.5), (x + rnd.uniform(-0.5, 0.5), H)], 2) for x in range(18, W, 18)]
    joints.append((jitter([(0, STACK_FLOOR + 0.3), (W, STACK_FLOOR + 0.3)], 0.2), 3))
    s.pencil(joints, strength=0.7, colour=STACK_INK)
    s.paper(0.06)
    return s.rgb.resize((W, H), Image.LANCZOS).convert("RGBA")


def paint_block(colour, edge=None):
    """A 320 x 14 block strip: a light top, a darker foot, grain and a gentle change along it, pencil top and bottom.
    Any width is cut from its left end, so the change along it is slow and even."""
    s = Strip(W, 0, BLOCK_H, False, colour)
    body = s.mask()
    s.polygon(body, [(0, 0), (W, 0), (W, BLOCK_H), (0, BLOCK_H)])
    s.wash(body, colour, alpha=1.0, rim=0.0, grain=0.45, cell=6, rough=None, soft=0)
    drift = autocontrast(blur(s.noise(90), 10))  # slow light and dark along the length
    glaze(s.rgb, scale(drift, 1.2, -110), tuple(int(c * 0.82) for c in colour), 0.7)
    light = tuple(min(255, int(c + (255 - c) * 0.55)) for c in colour)
    top = s.mask()
    s.polygon(top, [(0, 1), (W, 1), (W, 3.2), (0, 3.2)])
    broken = blur(s.noise(14), 2).point(lambda v: 255 if v > 105 else 90)  # a dry-brush highlight, not a stripe
    lay(s.rgb, ImageChops.multiply(blur(top, 2), broken), light, 0.7)
    blooms = blur(scale(s.noise(28), 2.4, -330), 3)  # pale wet blooms here and there
    lay(s.rgb, blooms, light, 0.25)
    foot = s.mask()
    s.polygon(foot, [(0, 10.5), (W, 10.5), (W, 13), (0, 13)])
    glaze(s.rgb, blur(foot, 3), tuple(int(c * 0.62) for c in colour), 0.9)
    if edge:  # the mover: a warm glow along its top and foot
        glow = s.mask()
        s.polygon(glow, [(0, 0), (W, 0), (W, 2.5), (0, 2.5)])
        s.polygon(glow, [(0, 11), (W, 11), (W, 14), (0, 14)])
        glaze(s.rgb, blur(glow, 3), edge, 0.6)
    strokes = []
    for _ in range(14):  # a few faint dry-brush streaks
        x, y = rnd.uniform(-10, W), rnd.uniform(4.5, 9.5)
        strokes.append(([(x, y), (x + rnd.uniform(14, 30), y + rnd.uniform(-0.4, 0.4))], 2))
    s.pencil(strokes, strength=0.12, colour=tuple(int(c * 0.5) for c in colour))
    img = s.rgb.resize((W, BLOCK_H), Image.LANCZOS)
    ink = tuple(int(i * 0.8 + c * 0.2) for i, c in zip(STACK_INK, colour))
    for x in range(W):  # the pencil rows, a little uneven
        k = 1.0 + 0.12 * sin(x * 0.7) * sin(x * 0.13)
        for y in (0, BLOCK_H - 1):
            img.putpixel((x, y), tuple(max(0, min(255, int(c * k))) for c in ink))
    return img.convert("RGBA")


def stack_scene(pics):
    """A tower of ten blocks, narrower as it grows, and the mover, as the game draws them (its pencil ends too)."""
    out = pics["stack_bg"].copy()
    x, w = 90, 140
    rows = []
    for i in range(10):
        rows.append((x, 220 - (i + 1) * BLOCK_H, w, "stack_block%d" % (i % 8)))
        cut = (3, 7, 2, 11, 5, 9, 4, 6, 8, 3)[i]
        x, w = (x + cut, w - cut) if i % 2 else (x, w - cut)
    rows.append((150, 220 - 11 * BLOCK_H, w, "stack_mover"))
    d = ImageDraw.Draw(out)
    for x, y, w, name in rows:
        out.paste(pics[name].crop((0, 0, w, BLOCK_H)), (x, y))
        d.line([(x, y), (x, y + BLOCK_H - 1)], fill=STACK_INK)
        d.line([(x + w - 1, y), (x + w - 1, y + BLOCK_H - 1)], fill=STACK_INK)
    return out.convert("RGB")


def paint_stack():
    """Every stack picture: the background, the eight blocks in the game's palette order, the mover."""
    pics = {"stack_bg": paint_stack_bg()}
    for i, colour in enumerate(PALETTE):
        pics["stack_block%d" % i] = paint_block(colour)
    pics["stack_mover"] = paint_block((255, 248, 230), edge=(255, 196, 120))
    return Painting({n: (img, False) for n, img in pics.items()})


ART_SET = ArtSet("stack", 563, paint_stack)
