"""Gravity pong's art as BUBBLE (P573): watercolour noir at midnight (D17). An exchange floor after hours: a glass wall
onto the city at midnight, the sodium glow low on it, a dead ticker board whose chart still climbs in the accent, empty
desks in shadow. Two night workers in pale overalls carry a net between them and keep a soap bubble in the air: the
bubble is the hero, see-through, its film in bone, the accent and one cool tone, the tall windows in it. It pops into
banknotes; the board's chart crashes; the card says IT WAS NEVER REAL.

The workers are posed by hand (P573's first preview sheet): the motion capture's spray stance (CMU 13_27) holds both
arms straight out at the shoulders, which at 24 px reads as pointing or aiming, not as holding a net at the waist."""

from math import atan2, cos, hypot, pi, sin

from PIL import Image, ImageChops, ImageDraw, ImageOps

from artset import ArtSet, Painting
from brush import ACCENT, GRAPHITE, H, W, Sprite, Strip, autocontrast, blur, glaze, jitter, lay, rnd, scale
from city import SODIUM, sky_at
from letters import text_width, write
from sets.rescue import Look, Person, leant

INK, BONE = (16, 14, 26), (232, 224, 204)  # midnight's pair: the ink is bluer than noon's
COOL = (112, 178, 226)  # the film's one cool tone, and the glass
LAMP = (255, 178, 96)  # a sodium lamp seen close: the glow's bright core
GLASS_TOP, GLASS_BOTTOM = 18, 192  # the glass wall's rows: the HUD covers 0 to 16
MULLIONS = tuple(range(0, W + 1, 40))  # the glass wall's posts
TRANSOM = 58  # the bar across the glass
BOARD = (92, 22, 228, 92)  # the ticker board: x0, y0, x1, y1, hung in front of the glass
PLATE = (164, 74, 222, 88)  # the board's number plate: the bubble's index, seven digits right-aligned
DESK_TOP = 206  # the desks' tops
FLOOR = 236  # the floor's first row: the workers' soles stand on the row above it
NET_Y = 216  # games/arcade2.py's PY less NET_TOP: the net picture's top row
NET_TOP = 2  # the net's end ropes are on the picture's rows NET_TOP and NET_TOP + 1, the game's hit row PY
NET = (70, 12)  # games/arcade2.py's PW, and the deepest sag
SIZES = (12, 16, 20, 24, 28)  # the bubble's diameters, one per radius 6, 8, 10, 12, 14
POSES = ("round", "squash", "stretch", "wobblea", "wobbleb")
BOX = {d: (-(-d * 126 // 100) + 3) // 2 * 2 for d in SIZES}  # each size's square picture, even, so the
# bubble's middle is on a pixel corner: room for the squash and the stretch
POP, POP_FRAMES = 40, 5
NOTE, NOTE_POSES = (8, 5), 3
WORKER = (22, 28)  # px; the hips at the picture's middle, the soles on its last row
DIGIT_W, DIGIT_H = 8, 12
CARD = (200, 100)
CARD_PLATES = ((40, 64), (120, 64))  # the over card's plates for the score and the best
PLATE_W, PLATE_H = 40, 17
TITLE_PLATE = (164, 134)


# --- the midnight floor --------------------------------------------------------------------------------------------

def midnight_at(y):
    """The night through the glass, the haze at the glass's foot."""
    return sky_at(24, (y - GLASS_TOP) / (GLASS_BOTTOM - GLASS_TOP))


def towers(s, x, x1, base, low, high, wide):
    """Towers side by side from x to x1, standing on base: (their mask, their window places)."""
    m, windows = s.mask(), []
    while x < x1:
        w, h = rnd.uniform(*wide), rnd.uniform(low, high)
        top = base - h
        s.polygon(m, [(x, base), (x, top), (x + w, top), (x + w, base)])
        if rnd.random() < 0.25:  # a spire or a stepped crown
            s.polygon(m, [(x + w / 2 - 1, top), (x + w / 2, top - rnd.uniform(6, 14)), (x + w / 2 + 1, top)])
        elif rnd.random() < 0.3:
            s.polygon(m, [(x + 2, top), (x + 2, top - 4), (x + w - 2, top - 4), (x + w - 2, top)])
        for wy in range(int(top + 3), int(base) - 3, 4):
            for wx in range(int(x + 2), int(x + w - 2), 3):
                windows.append((wx, wy))
        x += w + rnd.uniform(-1, 6)
    return m, windows


def lights(s, windows, share, colour, alpha=0.9, glow=0.0):
    """A share of the window places lit in colour, with a soft glow round them when glow is over 0."""
    m = s.mask()
    for wx, wy in windows:
        if rnd.random() < share:
            s.polygon(m, [(wx, wy), (wx + 1.2, wy), (wx + 1.2, wy + 1.6), (wx, wy + 1.6)])
    if glow:
        lay(s.rgb, blur(m, 3), colour, glow)
    lay(s.rgb, m, colour, alpha)


def paint_city(s):
    """Through the glass: stars, a high moon, searchlights crossing the sky, the far towers pale in the haze, the
    sodium glow rising between them and the near towers, the near towers dark against it with their windows lit
    here and there, two cranes, and the street's lamps in a row at the glass's foot."""
    stars = s.mask()
    for _ in range(60):
        s.ellipse(stars, rnd.uniform(0, W), rnd.uniform(GLASS_TOP + 2, 110), 0.3, 0.3)
    lay(s.rgb, blur(stars, 0.8), (220, 220, 246), 0.75)
    halo, moon, bite = s.mask(), s.mask(), s.mask()
    s.ellipse(halo, 288, 40, 16, 16)
    lay(s.rgb, blur(halo, 30), (120, 120, 170), 0.35)
    s.ellipse(moon, 288, 40, 5.5, 5.5)
    s.ellipse(bite, 290.5, 38, 5.5, 5.5)
    lay(s.rgb, blur(ImageChops.subtract(moon, bite), 1.2), (236, 232, 222))
    for x0, x1, top in ((70, 150, GLASS_TOP), (110, 30, GLASS_TOP), (236, 300, GLASS_TOP)):  # the searchlights
        beam = s.mask()
        s.polygon(beam, [(x0 - 1.5, GLASS_BOTTOM - 20), (x0 + 1.5, GLASS_BOTTOM - 20), (x1 + 9, top), (x1 - 9, top)])
        fade = s.mask()
        s.polygon(fade, [(0, top), (W, top), (W, GLASS_BOTTOM - 20), (0, GLASS_BOTTOM - 20)])
        fade = ImageChops.multiply(fade, Image.linear_gradient("L").resize(s.size).point(lambda v: 255 - v // 2))
        lay(s.rgb, ImageChops.multiply(blur(beam, 6), fade), (150, 160, 210), 0.22)
    far, windows = towers(s, -4.0, W, GLASS_BOTTOM - 8, 40, 104, (8, 20))
    s.wash(far, (58, 44, 78), alpha=0.85, rim=0.4, rim_px=3, grain=0.25, cell=12, rough=(1, 0.3, 6), dark=0.85,
           soft=0.6)
    lights(s, windows, 0.05, (150, 140, 170), 0.6)
    glow = s.mask()  # the sodium glow, rising from the streets between the far and the near towers
    for cx, r in ((40, 90), (170, 130), (300, 80)):
        s.ellipse(glow, cx, GLASS_BOTTOM + 10, r, 58)
    lay(s.rgb, blur(glow, 40), SODIUM, 0.9)
    lay(s.rgb, blur(glow, 18), (190, 110, 64), 0.45)
    near, windows = towers(s, -6.0, W, GLASS_BOTTOM, 16, 62, (16, 34))
    s.wash(near, (14, 12, 26), alpha=1.0, rim=0.5, rim_px=3, grain=0.15, cell=10, rough=(1, 0.3, 6), dark=0.8,
           soft=0.5)
    rim = ImageChops.subtract(near, ImageChops.offset(near, 0, -2 * s.S))  # the near towers' tops catch the glow
    lay(s.rgb, blur(rim, 1), (140, 84, 60), 0.6)
    lights(s, windows, 0.07, (190, 206, 236), 0.8)
    lights(s, windows, 0.08, (255, 214, 150), 0.95, glow=0.3)
    s.pencil([([(28, GLASS_BOTTOM - 40), (28, 84)], 2), ([(4, 88), (78, 88)], 2), ([(28, 84), (8, 88)], 1),
              ([(28, 84), (78, 88)], 1), ([(64, 88), (64, 108)], 1)], strength=0.8, colour=(20, 16, 34))
    s.pencil([([(254, GLASS_BOTTOM - 50), (254, 100)], 2), ([(230, 104), (308, 104)], 2), ([(254, 100), (308, 104)], 1),
              ([(292, 104), (292, 122)], 1)], strength=0.8, colour=(20, 16, 34))
    tip = s.mask()  # each crane's red light
    for x, y in ((28, 83.5), (254, 99.5)):
        s.ellipse(tip, x, y, 0.8, 0.8)
    lay(s.rgb, blur(tip, 6), ACCENT, 0.5)
    lay(s.rgb, tip, ACCENT)
    lamps = s.mask()  # the street's lamps, a row of sodium points at the glass's foot
    for x in range(3, W, 9):
        s.ellipse(lamps, x + rnd.uniform(-1, 1), GLASS_BOTTOM - 2.5, 0.7, 0.6)
    lay(s.rgb, blur(lamps, 5), LAMP, 0.5)
    lay(s.rgb, lamps, (255, 226, 170))


def paint_glass(s):
    """The glass wall: posts every 40 px, the transom, a cold sheen across the panes, and the sodium light that falls
    in, warm on the posts' inner faces."""
    sheen = s.mask()
    for x0 in range(-80, W, 120):  # the cold sheen: wide slanted bands
        s.polygon(sheen, [(x0, GLASS_BOTTOM), (x0 + 40, GLASS_BOTTOM), (x0 + 130, GLASS_TOP), (x0 + 90, GLASS_TOP)])
    lay(s.rgb, blur(sheen, 16), (120, 140, 190), 0.07)
    frame = s.mask()
    for x in MULLIONS:
        s.polygon(frame, [(x - 2, GLASS_TOP), (x + 2, GLASS_TOP), (x + 2, GLASS_BOTTOM), (x - 2, GLASS_BOTTOM)])
    s.polygon(frame, [(0, TRANSOM - 1.5), (W, TRANSOM - 1.5), (W, TRANSOM + 1.5), (0, TRANSOM + 1.5)])
    s.polygon(frame, [(0, GLASS_TOP), (W, GLASS_TOP), (W, GLASS_TOP + 3), (0, GLASS_TOP + 3)])
    s.wash(frame, (22, 20, 34), alpha=1.0, rim=0.3, rim_px=2, grain=0.2, cell=6, rough=None, soft=0.4)
    edge = s.mask()  # the posts' faces toward the glow below catch it
    for x in MULLIONS:
        s.polygon(edge, [(x + 1.2, TRANSOM + 2), (x + 2, TRANSOM + 2), (x + 2, GLASS_BOTTOM), (x + 1.2, GLASS_BOTTOM)])
    lay(s.rgb, ImageChops.multiply(edge, scale(blur(rows(s, TRANSOM, GLASS_BOTTOM), 1), 1)), (170, 100, 60),
        0.6)


def paint_board(s):
    """The ticker board hung from the ceiling: dark, a faint grid, dead rows of tickers, the chart's line climbing in
    the accent to a last spike at the right, and an empty plate where the game writes the bubble's index."""
    x0, y0, x1, y1 = BOARD
    s.pencil([([(x0 + 14, GLASS_TOP), (x0 + 14, y0)], 2), ([(x1 - 14, GLASS_TOP), (x1 - 14, y0)], 2)], strength=0.9,
             colour=(40, 36, 54))
    board = s.mask()
    s.polygon(board, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    s.wash(board, (14, 12, 22), alpha=1.0, rim=0.3, rim_px=3, grain=0.25, cell=6, rough=None, soft=0)
    grid = [([(x, y0 + 16), (x, y1 - 4)], 1) for x in range(x0 + 8, x1 - 2, 12)]
    grid += [([(x0 + 4, y), (x1 - 4, y)], 1) for y in range(y0 + 20, y1 - 2, 10)]
    s.pencil(grid, strength=0.5, colour=(54, 50, 86))
    dead = s.mask()  # the rows of dead tickers along the top: unlit dots
    for y in (y0 + 4, y0 + 9):
        for x in range(x0 + 5, x1 - 4, 3):
            if rnd.random() < 0.8:
                s.ellipse(dead, x, y, 0.55, 0.55)
    lay(s.rgb, dead, (44, 40, 64), 0.9)
    pts, x, y = [], x0 + 6, y1 - 12.0
    while x < x1 - 8:  # the chart: a ragged climb, steeper and steeper
        pts.append((x, y))
        x += rnd.uniform(2.5, 4.5)
        y -= (x - x0) / (x1 - x0) * rnd.uniform(-0.6, 2.6) + rnd.uniform(-1.4, 0.8)
        y = max(y0 + 18, min(y1 - 6, y))
    pts.append((x1 - 6, y0 + 16))
    glow = s.mask()
    ImageDraw.Draw(glow).line([s.pt(px, py)[0] for px, py in pts], fill=255, width=4 * s.S, joint="curve")
    lay(s.rgb, blur(glow, 10), ACCENT, 0.45)
    line = s.mask()
    ImageDraw.Draw(line).line([s.pt(px, py)[0] for px, py in pts], fill=255, width=int(1.3 * s.S), joint="curve")
    lay(s.rgb, line, ACCENT)
    tip = s.mask()
    s.ellipse(tip, x1 - 6, y0 + 16, 1.4, 1.4)
    lay(s.rgb, blur(tip, 6), (255, 220, 200), 0.7)
    lay(s.rgb, tip, (255, 236, 226))
    px0, py0, px1, py1 = PLATE
    plate = s.mask()
    s.polygon(plate, [(px0, py0), (px1, py0), (px1, py1), (px0, py1)])
    lay(s.rgb, plate, (26, 22, 36))
    s.pencil([([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], 3),
              ([(px0, py0), (px1, py0), (px1, py1), (px0, py1), (px0, py0)], 1)], strength=0.9, colour=(70, 64, 96))
    words(s, "INDEX", px0 - 15, py0 + 4.5, 0.9, 0.8, (110, 100, 140))


def paint_desks(s):
    """The desks against the glass's foot, in shadow: their tops catch the glow, dead screens, chairs pushed back,
    paper on the floor."""
    wall = s.mask()  # the wall under the glass: panels, lit from the glass above and dark at the floor
    s.polygon(wall, [(0, GLASS_BOTTOM), (W, GLASS_BOTTOM), (W, FLOOR), (0, FLOOR)])
    s.wash(wall, (48, 36, 52), alpha=1.0, rim=0.0, grain=0.08, cell=16, rough=None, soft=0)
    dim = ImageChops.multiply(rows(s, GLASS_BOTTOM, FLOOR), Image.linear_gradient("L").resize(s.size).point(
        lambda v: min(255, max(0, (v - 200) * 5))))
    glaze(s.rgb, blur(dim, 6), (40, 30, 60), 0.9)
    s.pencil([([(x, GLASS_BOTTOM + 3), (x, FLOOR)], 1) for x in range(20, W, 40)], strength=0.35, colour=INK)
    sill = s.mask()
    s.polygon(sill, [(0, GLASS_BOTTOM), (W, GLASS_BOTTOM), (W, GLASS_BOTTOM + 2), (0, GLASS_BOTTOM + 2)])
    lay(s.rgb, sill, (150, 96, 70), 0.85)
    body, screens, tops, x = s.mask(), s.mask(), s.mask(), 4.0
    while x < W:
        w = rnd.uniform(46, 60)
        s.polygon(body, [(x, DESK_TOP), (x + w, DESK_TOP), (x + w, DESK_TOP + 3), (x + w - 3, DESK_TOP + 3),
                         (x + w - 3, FLOOR), (x + w - 5, FLOOR), (x + w - 5, DESK_TOP + 3), (x + 5, DESK_TOP + 3),
                         (x + 5, FLOOR), (x + 3, FLOOR), (x + 3, DESK_TOP + 3), (x, DESK_TOP + 3)])
        s.polygon(tops, [(x, DESK_TOP), (x + w, DESK_TOP), (x + w, DESK_TOP + 0.8), (x, DESK_TOP + 0.8)])
        for k in range(rnd.choice((2, 3))):  # screens on stands, their backs to us
            sx = x + 6 + k * (w - 16) / 2 + rnd.uniform(-2, 2)
            sw, sh = rnd.uniform(10, 14), rnd.uniform(7, 9)
            s.polygon(screens, [(sx, DESK_TOP - 2 - sh), (sx + sw, DESK_TOP - 2 - sh), (sx + sw, DESK_TOP - 2),
                                (sx, DESK_TOP - 2)])
            s.polygon(body, [(sx + sw / 2 - 0.6, DESK_TOP - 2), (sx + sw / 2 + 0.6, DESK_TOP - 2),
                             (sx + sw / 2 + 2, DESK_TOP), (sx + sw / 2 - 2, DESK_TOP)])
        cx = x + w * rnd.uniform(0.3, 0.7)  # a chair pushed back
        seat, top = DESK_TOP + 8, DESK_TOP - 2
        s.polygon(body, [(cx - 4, seat), (cx + 4, seat), (cx + 4, seat + 2), (cx - 4, seat + 2)])
        s.polygon(body, [(cx + 3, top), (cx + 5, top), (cx + 4.5, seat + 1), (cx + 3, seat + 1)])
        s.polygon(body, [(cx - 0.6, seat + 2), (cx + 0.6, seat + 2), (cx + 0.6, FLOOR - 2), (cx - 0.6, FLOOR - 2)])
        s.polygon(body, [(cx - 4, FLOOR - 2), (cx + 4, FLOOR - 2), (cx + 4, FLOOR - 1), (cx - 4, FLOOR - 1)])
        x += w + rnd.uniform(8, 16)
    s.wash(body, (12, 10, 20), alpha=1.0, rim=0.2, rim_px=2, grain=0.2, cell=6, rough=None, soft=0.3)
    s.wash(screens, (12, 10, 20), alpha=1.0, rim=0.3, rim_px=2, grain=0.2, cell=6, rough=None, soft=0.3)
    edge = ImageChops.subtract(screens, ImageChops.offset(screens, 0, 1 * s.S))  # their top edges catch the glow
    lay(s.rgb, edge, (130, 84, 66), 0.8)
    lay(s.rgb, tops, (170, 104, 70), 0.85)
    paper = s.mask()  # sheets and ticker tape on the floor
    for _ in range(26):
        x, w = rnd.uniform(0, W), rnd.uniform(2, 5)
        s.polygon(paper, [(x, FLOOR - 0.8), (x + w, FLOOR - 1.2), (x + w + 0.4, FLOOR), (x, FLOOR)])
    lay(s.rgb, paper, (150, 140, 150), 0.6)


def paint_floor(s):
    """The polished floor: the glass's glow mirrored in long smears, and the edge line."""
    floor = s.mask()
    s.polygon(floor, [(0, FLOOR), (W, FLOOR), (W, H + 2), (0, H + 2)])
    s.wash(floor, (34, 28, 44), alpha=1.0, rim=0.0, grain=0.3, cell=6, rough=None, soft=0)
    shine = s.mask()
    for x in range(10, W, 40):
        s.polygon(shine, [(x, FLOOR + 1), (x + 18, FLOOR + 1), (x + 16, H), (x + 2, H)])
    lay(s.rgb, ImageChops.multiply(blur(shine, 4), rows(s, FLOOR, H + 2)), (120, 76, 60), 0.45)
    s.pencil([(jitter([(0, FLOOR + 0.2), (W, FLOOR + 0.2)], 0.15), 2)], strength=0.8, colour=(8, 6, 14))


def paint_midnight():
    """The exchange floor at midnight, 320 x 240: the city through the glass, the glass wall, the ticker board, the
    desks and the floor, painted at 4x and shrunk."""
    s = Strip(W, 0, H, False, midnight_at)
    for painter in (paint_city, paint_glass, paint_board, paint_desks, paint_floor):
        painter(s)
    s.paper(0.05)
    return s.rgb.resize((W, H), Image.LANCZOS).convert("RGBA")


def words(s, text, cx, y, unit, width, colour):
    """Stroke letters on strip s, centred on game x cx, the top at game y."""
    m = s.mask()
    write(m, text, (cx - text_width(text, unit) / 2) * s.S, y * s.S, unit * s.S, width * s.S)
    lay(s.rgb, m, colour)


def rows(s, y0, y1):
    """A mask of the game rows y0 to y1 on strip s."""
    m = s.mask()
    s.polygon(m, [(0, y0), (s.w, y0), (s.w, y1), (0, y1)])
    return m



# --- the bubble ----------------------------------------------------------------------------------------------------

FILM_PHASES = 4  # the round bubble's film turns through these, so it shimmers as it flies
FILMS = ["round%d" % k for k in range(FILM_PHASES)] + list(POSES[1:])  # the films: the round one's turns, the rest


def outline(d, pose):
    """The pose's shape for a bubble d px across: (rx, ry, dy, egg). dy moves the middle down (a squash keeps its
    bottom where the round one's is); egg makes the bottom fuller (above 0) or the top (below)."""
    r = d / 2
    return {"round": (r, r, 0, 0), "squash": (r * 1.24, r * 0.76, r * 0.24, 0.12),
            "stretch": (r * 0.84, r * 1.2, 0, -0.1), "wobblea": (r * 1.09, r * 0.92, r * 0.08, 0.1),
            "wobbleb": (r * 0.92, r * 1.09, -r * 0.04, -0.12)}[pose]


def bubble_field(d, pose):
    """Each pixel of the pose's box: (rho, u, v), rho 1 on the outline, u and v the place across the shape from -1 to
    1. Pixels outside are None."""
    b = BOX[d]
    rx, ry, dy, egg = outline(d, pose)
    out = {}
    for j in range(b):
        for i in range(b):
            u, v = (i + 0.5 - b / 2) / rx, (j + 0.5 - b / 2 - dy) / ry
            rho = hypot(u, v) / (1 + egg * max(-1.0, min(1.0, v)))
            if rho <= 1:
                out[i, j] = (rho, u, v)
    return out


def mix(a, b, t):
    return tuple(int(p + (q - p) * t) for p, q in zip(a, b))


def sheen(angle, turn=0.0):
    """The rim's colour at angle (radians, 0 to the right, down positive): bone where the light is, upper left;
    the cool tone up right; the sodium glow mirrored low right; the accent low left."""
    stops = ((-2.4, (250, 246, 236)), (-0.8, COOL), (0.9, LAMP), (2.3, ACCENT), (3.88, (250, 246, 236)))
    a = (angle + turn + pi) % (2 * pi) - pi
    if a < stops[0][0]:
        a += 2 * pi
    for (a0, c0), (a1, c1) in zip(stops, stops[1:]):
        if a <= a1:
            return mix(c0, c1, (a - a0) / (a1 - a0))
    return stops[-1][1]


def bubble(d, pose):
    """The bubble's keyed picture: a 1 px rim in the sheen's colours, the tall windows of the exchange mirrored in its
    upper left, a glint, and the sodium glow mirrored in a thin crescent low on the right. The film inside is its own
    picture, drawn see-through under this one."""
    b = BOX[d]
    field = bubble_field(d, pose)
    img = Image.new("RGBA", (b, b), (0, 0, 0, 0))
    big = d >= 20
    for (i, j), (rho, u, v) in field.items():
        edge = any((i + di, j + dj) not in field for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            img.putpixel((i, j), sheen(atan2(v, u)) + (255,))
            continue
        if -0.66 < u < -0.18 and -0.72 < v < -0.12 and rho < 0.86:  # the window
            bar = big and (abs(u + 0.42) < 1.0 / d * 2 or abs(v + 0.4) < 1.0 / d * 2)
            if not bar:
                img.putpixel((i, j), mix((255, 252, 244), COOL, max(0.0, (v + 0.5) * 1.6)) + (255,))
        elif 0.3 < u and 0.42 < v and 0.8 < rho:  # the sodium crescent
            img.putpixel((i, j), mix(LAMP, (255, 232, 190), 0.3) + (255,))
    if big:  # a glint over the window
        gx, gy = int(b / 2 - d * 0.1), int(b / 2 - d * 0.32 + outline(d, pose)[2])
        img.putpixel((gx, gy), (255, 255, 255, 255))
    return img


def film(d, name):
    """The film inside the rim, drawn see-through: bands of the cool tone, the accent and bone that drain down and
    swirl, thickest near the rim, the middle clear. name: round<k> (the film turned k quarters of a swirl) or a pose."""
    pose = "round" if name.startswith("round") else name
    k = int(name[5:]) if name.startswith("round") else POSES.index(name)
    field = bubble_field(d, pose)
    b = BOX[d]
    img = Image.new("RGBA", (b, b), (0, 0, 0, 0))
    stops = (COOL, (196, 170, 220), ACCENT, (236, 170, 110), (240, 232, 214), COOL)
    phase = k * pi / 2
    for (i, j), (rho, u, v) in field.items():
        if rho < 0.5:
            continue
        f = (v * 2.2 + 0.55 * sin(u * 3.4 + phase) + 0.25 * cos(v * 5 - phase) + k * 0.31) % 1.0
        x = f * (len(stops) - 1)
        c = mix(stops[int(x)], stops[int(x) + 1], x - int(x))
        if rho > 0.78:  # the film is brighter where it is seen edge-on
            c = mix(c, (255, 255, 255), 0.25)
        img.putpixel((i, j), c + (255,))
    return img


RINGS = (26, 16, 8)  # px the glow's three rings reach past the bubble, outer first, each drawn see-through


def halo(d, ring):
    """One ring of the glow behind the bubble: a disc ring px wider than the bubble, warm bone in the middle to
    sodium at its edge. The game draws the three over each other, each see-through, so the glow steps up to the
    bubble."""
    n = d + ring
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    for j in range(n):
        for i in range(n):
            r = hypot(i + 0.5 - n / 2, j + 0.5 - n / 2) / (n / 2)
            if r < 1:
                img.putpixel((i, j), mix((255, 226, 186), (210, 120, 72), r) + (255,))
    return img


# --- the workers ---------------------------------------------------------------------------------------------------

OVERALLS, OVERALLS_FAR = (176, 176, 186), (112, 112, 130)  # pale overalls: the near side, and the far limbs in shade
FACE, CAP, BOOTS = (168, 124, 108), (58, 58, 84), (20, 18, 28)
HAND_UP, HAND_AHEAD = 0.72, 0.31  # the hands, in body heights over the soles and ahead of the hips: the net's end
WORKER_LOOK = Look(24, OVERALLS, OVERALLS, limb=2.3, torso=4.2, hair="cap")
STRIDE = 4  # the run's poses
LEGS = (  # each pose of the run: the near leg's knee, ankle and toes, the far leg's, and the hips' rise; facing right
    ((0.12, 0.29), (0.21, 0.05), (0.28, 0.02), (-0.05, 0.27), (-0.17, 0.11), (-0.12, 0.04), -0.02),
    ((0.07, 0.28), (0.0, 0.05), (0.07, 0.01), (0.14, 0.34), (0.03, 0.17), (0.09, 0.14), 0.01),
    ((-0.05, 0.27), (-0.17, 0.11), (-0.12, 0.04), (0.12, 0.29), (0.21, 0.05), (0.28, 0.02), -0.02),
    ((0.14, 0.34), (0.03, 0.17), (0.09, 0.14), (0.07, 0.28), (0.0, 0.05), (0.07, 0.01), 0.01),
)
STAND_LEGS = ((0.06, 0.28), (0.04, 0.04), (0.11, 0.0), (0.0, 0.28), (-0.04, 0.04), (0.03, 0.0), 0.0)
WORKER_POSES = ("stand", "tired") + tuple("%s%d" % (kind, k) for kind in ("run", "back", "trun", "tback")
                                          for k in range(STRIDE))


def worker_pose(legs, tired, lean):
    """A worker's pose, facing right, in body heights (forward, up, near): the legs of one pose of the run, the
    hands on the net's end, tired (0 fresh, 1 spent: the head bowed, the shoulders sunk, the knees bent) and leant
    by lean degrees (forward above 0)."""
    (nk, na, nt, fk, fa, ft, rise), t = legs, tired
    hip = 0.52 + rise - 0.03 * t
    p = {"lhipjoint": (0.0, hip, -0.06), "rhipjoint": (0.0, hip, 0.06)}
    for side, knee, ankle, toes in (("r", nk, na, nt), ("l", fk, fa, ft)):
        z = 0.08 if side == "r" else -0.08
        p[side + "femur"] = (knee[0] + 0.03 * t, knee[1] - 0.02 * t, z)
        p[side + "tibia"] = ankle + (z,)
        p[side + "foot"] = (ankle[0] + 0.04, max(0.0, ankle[1] - 0.04), z)
        p[side + "toes"] = toes + (z,)
    bow, sink = 0.08 * t, 0.05 * t
    p.update({"lowerback": (-0.01, hip + 0.1, 0), "upperback": (0.0 + 0.02 * t, hip + 0.2 - 0.01 * t, 0),
              "thorax": (0.02 + 0.05 * t, hip + 0.27 - 0.03 * t, 0),
              "lowerneck": (0.04 + 0.08 * t, hip + 0.33 - sink, 0),
              "upperneck": (0.06 + bow, hip + 0.38 - sink - 0.02 * t, 0),
              "head": (0.07 + bow * 1.2, hip + 0.42 - sink - 0.04 * t, 0),
              "nose": (0.16 + bow * 1.1, hip + 0.4 - sink - 0.13 * t, 0)})
    for side, z in (("l", -0.11), ("r", 0.11)):
        p[side + "clavicle"] = (0.03 + 0.05 * t, hip + 0.31 - sink, z)
        p[side + "humerus"] = (0.08, hip + 0.15 - sink * 0.5, z)
        p[side + "radius"] = (HAND_AHEAD - 0.05, HAND_UP - 0.01, z)
        p[side + "wrist"] = p[side + "hand"] = p[side + "fingers"] = p[side + "thumb"] = (HAND_AHEAD, HAND_UP, z)
    out = leant(p, lean) if lean else p
    for side in "lr":  # the hands stay on the net, however the body leans
        out[side + "radius"], out[side + "wrist"] = p[side + "radius"], p[side + "wrist"]
    return out


class Worker(Person):
    """A night worker, facing right, in the fireman's style: pale overalls, the far limbs in shade, a dark cap, the
    face in shadow, a 1 px rim warm ahead and cool behind. The hands hold the net's end."""

    def __init__(self):
        super().__init__(WORKER, WORKER_LOOK)
        self.NEAR, self.FAR, self.SEAM, self.BOOT = OVERALLS, OVERALLS_FAR, (70, 70, 92), BOOTS

    def sleeve(self, colour):
        return OVERALLS if colour == self.NEAR else OVERALLS_FAR

    def head(self, s, p):
        hx, hy = p["head"]
        r = self.look.head * self.PX
        ahead = 1 if p["nose"][0] >= hx else -1
        cy = hy + r * 0.1
        self.part(s, s.shape("ellipse", hx - r, cy - r * 1.1, hx + r, cy + r * 1.1), FACE)
        top = cy - r * 1.15
        self.part(s, s.shape("ellipse", hx - r * 1.1, top - r * 0.2, hx + r * 1.1, cy + r * 0.1), CAP)
        self.part(s, s.shape("poly", (hx, top + r * 0.5), (hx + ahead * r * 2.0, top + r * 0.8),
                             (hx + ahead * r * 2.0, top + r * 1.15), (hx, top + r * 1.0)), CAP)


def worker(name):
    """One of WORKER_POSES, facing right: stand and tired stand still; run<k> runs forward, back<k> backs away (the
    run's poses in turn: the game plays them backward), each leant its way; trun and tback the same, spent."""
    kind, k = name.rstrip("0123456789"), int(name[-1]) if name[-1].isdigit() else 0
    tired = 1.0 if kind in ("tired", "trun", "tback") else 0.0
    legs = STAND_LEGS if kind in ("stand", "tired") else LEGS[k]
    lean = {"run": 9, "trun": 14, "back": -7, "tback": -3}.get(kind, 0)
    return Worker().paint(worker_pose(legs, tired, lean))


# --- the net, the pop, the notes, the digits ------------------------------------------------------------------------

NET_DEPTHS = (-1.0, 1.5, 3.5, 6.0)  # px the net's middle hangs below its ends: up (the recoil), flat, sag, deep
ROPE, MESH, MESH_ROPE = (236, 226, 202), (150, 140, 128), (186, 174, 152)


def net(depth):
    """The net between the workers' hands, 70 x 12 keyed: its ends on rows NET_TOP and NET_TOP + 1, the top rope in
    a curve depth px down at the middle, a band of diamond mesh under it, deepest in the middle, and the bottom
    rope. Drawn pixel by pixel, so each strand stays one whole pixel."""
    w, h = NET
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for x in range(w):
        k = 1 - ((x + 0.5 - w / 2) / (w / 2)) ** 2  # 0 at the ends, 1 in the middle
        top = round(NET_TOP + 0.4 + depth * k)
        bottom = min(h - 1, top + round(1 + 3.4 * k ** 0.6))
        for y in range(max(0, top), bottom + 1):
            if y == top or y == top + 1 and x in (0, 1, w - 2, w - 1):
                c = ROPE
            elif y == bottom:
                c = MESH_ROPE
            elif (x + y) % 3 == 0 or (x - y) % 3 == 0:
                c = MESH
            else:
                continue
            img.putpixel((x, y), c + (255,))
    for x in (0, 1, w - 2, w - 1):  # the ends in the hands: whole pixels on the hit rows
        for y in (NET_TOP, NET_TOP + 1):
            img.putpixel((x, y), ROPE + (255,))
    return img


SPOT = (48, 10)


def spot():
    """The bubble's light on the floor under it, 48 x 10 keyed: a warm oval, drawn see-through, brighter the lower
    the bubble flies."""
    w, h = SPOT
    img = Image.new("RGBA", SPOT, (0, 0, 0, 0))
    for j in range(h):
        for i in range(w):
            r = hypot((i + 0.5 - w / 2) / (w / 2), (j + 0.5 - h / 2) / (h / 2))
            if r < 1:
                img.putpixel((i, j), mix((255, 214, 160), (190, 104, 66), r) + (255,))
    return img


def pop(frame):
    """The bubble bursting, 40 x 40 keyed, frame 0 to POP_FRAMES - 1: a white flash ring with rays, then the film torn
    into arcs in the sheen's colours that fly out and break into drops, then a mist of drops."""
    n, c = POP, POP / 2
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    state = rnd.getstate()
    rnd.seed(5)  # the same tears and drops in every frame, so they fly and do not jump
    arcs = [(rnd.uniform(0, 2 * pi), rnd.uniform(0.25, 0.6)) for _ in range(9)]
    drops = [(rnd.uniform(0, 2 * pi), rnd.uniform(0.75, 1.15)) for _ in range(26)]
    rnd.setstate(state)
    d = ImageDraw.Draw(img)
    if frame == 0:  # the flash: a white-hot disc in a ring of the sheen's colours, and short rays
        for k in range(48):
            a = k * pi / 24
            d.line([(c, c), (c + 13 * cos(a), c + 13 * sin(a))], fill=sheen(a) + (255,), width=2)
        d.ellipse((c - 11, c - 11, c + 11, c + 11), fill=(255, 250, 236, 255))
        for k in range(8):
            a = k * pi / 4 + pi / 8
            d.line([(c + 15 * cos(a), c + 15 * sin(a)), (c + 19 * cos(a), c + 19 * sin(a))],
                   fill=sheen(a) + (255,), width=1)
        return img
    r = 13 + frame * 2.5
    if frame < 4:  # the torn film: arcs, shorter each frame
        for a0, span in arcs:
            span *= 1 - frame * 0.22
            pts = [(c + r * cos(a0 + span * t / 6), c + r * sin(a0 + span * t / 6) + frame * 0.6) for t in range(7)]
            d.line(pts, fill=sheen(a0) + (255,), width=2 if frame == 1 else 1)
    for k, (a, far) in enumerate(drops):  # the drops, falling a little as they fly
        if frame == 4 and k % 2:
            continue
        rr = min(c - 1.5, r * far + frame)
        x, y = c + rr * cos(a), c + rr * sin(a) + frame * frame * 0.4
        if 0 <= x < n and 0 <= y < n:
            img.putpixel((int(x), int(y)), sheen(a) + (255,))
    return img


NOTE_PAPER, NOTE_INK = (214, 224, 190), (70, 92, 66)


def note(k):
    """A banknote, 8 x 5 keyed, as it flips: 0 flat, 1 tilted, 2 edge-on."""
    w, h = NOTE
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if k == 0:
        d.rectangle((0, 0, w - 1, h - 1), fill=NOTE_PAPER + (255,), outline=NOTE_INK + (255,))
        d.point([(3, 2), (4, 2)], fill=NOTE_INK + (255,))  # the portrait
        d.point([(1, 1)], fill=ACCENT + (255,))  # the serial number's red
    elif k == 1:
        d.polygon([(2, 0), (w - 1, 0), (w - 3, h - 1), (0, h - 1)], fill=NOTE_PAPER + (255,), outline=NOTE_INK + (255,))
        d.point([(4, 2)], fill=NOTE_INK + (255,))
    else:
        d.line([(0, 3), (w - 1, 1)], fill=NOTE_PAPER + (255,), width=1)
        d.line([(0, 4), (w - 1, 2)], fill=NOTE_INK + (255,), width=1)
    return img


def digit(n):
    """One digit, 8 x 12 keyed: the ticker's red strokes, for the board's plate and the card's."""
    k = 8
    m = Image.new("L", (DIGIT_W * k, DIGIT_H * k), 0)
    write(m, str(n), 1.2 * k, 1.2 * k, 1.5 * k, 1.5 * k)
    a = m.resize((DIGIT_W, DIGIT_H), Image.BOX).point(lambda v: 255 if v >= 100 else 0)
    out = Image.new("RGBA", (DIGIT_W, DIGIT_H), (255, 70, 70, 255))
    out.putalpha(a)
    return out


COIN = 10


def coin():
    """The coin the title's bubble grows from, 10 x 10 keyed: brass in the sodium light, a rim and a glint."""
    s = Sprite(COIN, COIN)
    s.part(s.shape("ellipse", 0.5, 0.5, COIN - 0.5, COIN - 0.5), (196, 140, 70), light=(3.5, 3.5, 3, (255, 222, 150)),
           rim=0.5, grain=0.1)
    s.part(s.shape("ellipse", 2.6, 2.6, COIN - 2.6, COIN - 2.6), (176, 120, 60), light=(4, 4, 2, (240, 200, 130)),
           rim=0.2, grain=0)
    s.dot(3, 3, (255, 248, 220))
    return s.cut(ink=INK)


def crash(midnight):
    """The ticker board when the bubble pops, the size of BOARD: the board as painted, its chart's last climb wiped
    and the line fallen off a cliff to the bottom, a red glow along the fall."""
    x0, y0, x1, y1 = BOARD
    w, h = x1 - x0, y1 - y0
    s = Strip(w, 0, h, False, (0, 0, 0))
    s.rgb = midnight.crop(BOARD).convert("RGB").resize(s.size, Image.LANCZOS)
    wipe = s.mask()
    s.polygon(wipe, [(w * 0.55, 14), (w - 3, 14), (w - 3, h - 3), (w * 0.55, h - 3)])
    lay(s.rgb, wipe, (14, 12, 22))
    s.pencil([([(x, 16), (x, h - 4)], 1) for x in range(8, w - 2, 12) if x > w * 0.55]
             + [([(w * 0.55, y), (w - 4, y)], 1) for y in range(20, h - 2, 10)], strength=0.5, colour=(54, 50, 86))
    fall = [(w * 0.55, h * 0.42), (w * 0.62, h * 0.3), (w * 0.7, h * 0.22), (w * 0.73, h * 0.26), (w * 0.75, h * 0.2),
            (w * 0.78, h * 0.62), (w * 0.82, h * 0.55), (w * 0.86, h * 0.86), (w - 6, h - 5)]
    glow = s.mask()
    ImageDraw.Draw(glow).line([s.pt(px, py)[0] for px, py in fall], fill=255, width=4 * s.S, joint="curve")
    lay(s.rgb, blur(glow, 10), ACCENT, 0.6)
    line = s.mask()
    ImageDraw.Draw(line).line([s.pt(px, py)[0] for px, py in fall], fill=255, width=int(1.3 * s.S), joint="curve")
    lay(s.rgb, line, ACCENT)
    return s.rgb.resize((w, h), Image.LANCZOS).convert("RGBA")


# --- the title and the card ----------------------------------------------------------------------------------------

def plate(s, x, y, w=PLATE_W, h=PLATE_H):
    """A small dark number plate with a pale border, for digits the game writes."""
    m = s.mask()
    s.polygon(m, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
    lay(s.rgb, m, (22, 18, 32))
    s.pencil([([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], 2)], strength=0.9, colour=(150, 140, 160))


def paint_title(midnight, pics):
    """The title, 320 x 240: the midnight floor dimmed, BUBBLE in the film's colours with a bone edge and an ink
    shadow, the accent's rule, TAP TURNS THE NET, BEST with a plate, and the two workers holding the empty net at
    the bottom: the game inflates the bubble over it."""
    s = Strip(W, 0, H, False, (0, 0, 0))
    s.rgb = midnight.convert("RGB").resize(s.size, Image.LANCZOS)
    glaze(s.rgb, Image.new("L", s.size, 255), (60, 54, 90), 0.6)
    band = s.mask()
    s.polygon(band, [(0, 30), (W, 30), (W, 112), (0, 112)])
    glaze(s.rgb, blur(s.roughen(band, 3, 0.5, 14), 6), INK, 0.85)
    unit, width = 7.6, 3.6
    x = 160 - text_width("BUBBLE", unit) / 2
    shadow = s.mask()
    write(shadow, "BUBBLE", (x + 3) * s.S, 41 * s.S, unit * s.S, width * s.S)
    lay(s.rgb, shadow, (6, 4, 12))
    edge = s.mask()
    write(edge, "BUBBLE", x * s.S, 38 * s.S, unit * s.S, (width + 1.4) * s.S)
    lay(s.rgb, edge, BONE)
    word = s.mask()
    write(word, "BUBBLE", x * s.S, 38 * s.S, unit * s.S, width * s.S)
    stops = (COOL, (196, 170, 220), ACCENT, LAMP)
    for k in range(3):  # the film's colours, top to bottom, in three bands
        y0, y1 = 36 + 26 * k / 3, 36 + 26 * (k + 1) / 3
        lay(s.rgb, ImageChops.multiply(word, blur(rows(s, y0, y1), 6)), stops[k], 0.9)
    lay(s.rgb, ImageChops.multiply(word, rows(s, 60, 100)), stops[3])
    shine = s.mask()  # a window glint in each letter's top left
    for k in range(6):
        s.ellipse(shine, x + k * 6 * unit + 5, 42, 1.8, 2.8)
    lay(s.rgb, ImageChops.multiply(shine, word), (255, 250, 240), 0.9)
    rule = s.mask()
    s.polygon(rule, [(60, 104), (260, 104), (260, 106.5), (60, 106.5)])
    lay(s.rgb, rule, ACCENT)
    words(s, "TAP TURNS THE NET", 160, 114, 1.6, 1.2, BONE)
    words(s, "BEST", TITLE_PLATE[0] - 20, TITLE_PLATE[1] + 5, 1.4, 1.1, BONE)
    plate(s, *TITLE_PLATE)
    s.paper(0.06)
    img = s.rgb.resize((W, H), Image.LANCZOS).convert("RGBA")
    over(img, pics["gravpong_net_1"], 125, NET_Y)
    over(img, pics["gravpong_worker_l_tired"], 125 - WORKER[0] // 2 - hand_dx(), FLOOR - WORKER[1])
    over(img, pics["gravpong_worker_r_tired"], 195 + hand_dx() - WORKER[0] // 2, FLOOR - WORKER[1])
    return img


def paint_over():
    """The over card, 200 x 100: IT WAS NEVER REAL in bone, the accent's rule, and dark plates for the score and the
    best, on an ink wash with a bone border."""
    w, h = CARD
    s = Strip(w, 0, h, False, INK)
    m = s.mask()
    s.polygon(m, [(0, 0), (w, 0), (w, h), (0, h)])
    s.wash(m, (34, 28, 48), alpha=0.9, rim=0.0, grain=0.5, cell=10, rough=None, soft=0)
    border = s.mask()
    ImageDraw.Draw(border).rectangle((2 * s.S, 2 * s.S, (w - 2) * s.S, (h - 2) * s.S), outline=255, width=s.S)
    lay(s.rgb, border, BONE)
    words(s, "IT WAS", w / 2, 9, 2.2, 1.7, BONE)
    words(s, "NEVER REAL", w / 2, 27, 2.2, 1.7, BONE)
    rule = s.mask()
    s.polygon(rule, [(30, 45), (w - 30, 45), (w - 30, 46.6), (30, 46.6)])
    lay(s.rgb, rule, ACCENT)
    for (x, y), label in zip(CARD_PLATES, ("SCORE", "BEST")):
        words(s, label, x + PLATE_W / 2, y - 12, 1.2, 1.0, BONE)
        plate(s, x, y)
    return s.rgb.resize(CARD, Image.LANCZOS).convert("RGBA")


def hand_dx():
    """px from a worker's hips (the picture's middle) to the hands, which hold the net's end."""
    return round(HAND_AHEAD * WORKER_LOOK.height / (1 + 0.06))


def over(out, img, x, y):
    """img on out at (x, y), its clear pixels skipped, as the board's keyed blit draws it."""
    out.paste(img, (x, y), img)


# --- the preview sheet ---------------------------------------------------------------------------------------------

GLOW_ALPHAS = (34, 42, 54)  # games/arcade2.py's: each of the glow's RINGS, outer first
FILM_ALPHA = 120


def seen(out, img, x, y, alpha):
    """img on out at (x, y) see-through at alpha, its clear pixels skipped, as the board's blend draws it."""
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    layer.paste(img, (x, y))
    out.paste(layer.convert("RGB"), (0, 0), layer.getchannel("A").point(lambda v: v * alpha // 255))


def show_bubble(out, pics, cx, cy, d, pose, film_name):
    """The bubble d px across with its middle at (cx, cy), as the game draws it: the glow's rings, the film, the rim."""
    for ring, alpha in zip(RINGS, GLOW_ALPHAS):
        n = d + ring
        seen(out, pics["gravpong_halo_%d_%d" % (d, ring)], cx - n // 2, cy - n // 2, alpha)
    b = BOX[d]
    seen(out, pics["gravpong_film_%d_%s" % (d, film_name)], cx - b // 2, cy - b // 2, FILM_ALPHA)
    over(out, pics["gravpong_bubble_%d_%s" % (d, pose)], cx - b // 2, cy - b // 2)


def number(out, pics, value, right, top):
    """value in digit pictures, right-aligned at right, the last digit first, as the game writes it."""
    for k, ch in enumerate(reversed(str(value))):
        over(out, pics["gravpong_digit_" + ch], right - DIGIT_W * (k + 1), top)


def show_workers(out, pics, px, left, right):
    """The two workers on the net's ends at px, and the net between them."""
    over(out, pics["gravpong_worker_l_" + left], px - WORKER[0] // 2 - hand_dx(), FLOOR - WORKER[1])
    over(out, pics["gravpong_worker_r_" + right], px + NET[0] + hand_dx() - WORKER[0] // 2, FLOOR - WORKER[1])


def gravpong_scene(pics, d=24, pose="stretch", film_name="stretch"):
    """A frame of play: the bubble rising off the net, the workers running right, the index on the board."""
    out = pics["gravpong_midnight"].copy()
    number(out, pics, 4826, PLATE[2] - 3, PLATE[1] + 2)
    show_workers(out, pics, 150, "run1", "back3")
    over(out, pics["gravpong_net_1"], 150, NET_Y)
    show_bubble(out, pics, 196, 120, d, pose, film_name)
    return out.convert("RGB")


def gravpong_end(pics):
    """The round's end: the board crashed, the pop on the floor, the notes falling, the workers tired with the empty
    net, and the card."""
    out = pics["gravpong_midnight"].copy()
    out.paste(pics["gravpong_crash"], BOARD[:2])
    show_workers(out, pics, 120, "tired", "tired")
    over(out, pics["gravpong_net_0"], 120, NET_Y)
    over(out, pics["gravpong_pop_2"], 230 - POP // 2, FLOOR - 12 - POP // 2)
    for k, (x, y) in enumerate(((40, 60), (90, 140), (150, 100), (200, 170), (250, 80), (280, 150), (70, 200),
                                (180, 214), (300, 226), (130, 228))):
        over(out, pics["gravpong_note_%d" % (k % NOTE_POSES)], x, y)
    return out


def gravpong_frame(painting):
    return gravpong_scene(painting.images())


def gravpong_sheet(painting, sheet, y):
    """A frame of play at 2x; the bubble's sizes and poses at 4x on the floor's colours; the pop, the net, the
    workers, the notes and the digits enlarged; the title and the round's end with the card."""
    pics = painting.images()
    sheet.put("gravpong (BUBBLE): gravpong_midnight in play, the bubble, the net and the workers, at 2x",
              gravpong_scene(pics).resize((W * 2, H * 2), Image.NEAREST), 10, y)
    cell = 44
    grid = Image.new("RGB", (cell * len(POSES), cell * len(SIZES)))
    for k, d in enumerate(SIZES):
        for m, pose in enumerate(POSES):
            x0, y0 = m * cell, k * cell
            grid.paste(pics["gravpong_midnight"].crop((40 + m * 50, 110 + k * 16, 40 + m * 50 + cell,
                                                       110 + k * 16 + cell)).convert("RGB"), (x0, y0))
            show_bubble(grid, pics, x0 + cell // 2, y0 + cell // 2, d, pose, "round0" if pose == "round" else pose)
    at = sheet.put("gravpong_bubble_<size>_<pose>, film and glow, 12 to 28 px, at 2x",
                   grid.resize((grid.width * 2, grid.height * 2), Image.NEAREST), W * 2 + 30, y)
    y = max(at, y + 18 + H * 2) + 14
    strip = Image.new("RGB", (POP * POP_FRAMES + 8 * (POP_FRAMES - 1), POP), INK)
    for k in range(POP_FRAMES):
        over(strip, pics["gravpong_pop_%d" % k], k * (POP + 8), 0)
    at = sheet.put("gravpong_pop_0..4 40x40, at 3x", strip.resize((strip.width * 3, POP * 3), Image.NEAREST), 10, y)
    nets = Image.new("RGB", (NET[0], len(NET_DEPTHS) * 14), (60, 50, 70))
    for k in range(len(NET_DEPTHS)):
        over(nets, pics["gravpong_net_%d" % k], 0, k * 14)
    sheet.put("gravpong_net_0..3 70x12, at 4x", nets.resize((NET[0] * 4, nets.height * 4), Image.NEAREST),
              strip.width * 3 + 30, y)
    y = max(at, y + 18 + nets.height * 4) + 12
    poses = Image.new("RGB", (len(WORKER_POSES) * (WORKER[0] + 2), WORKER[1]), (60, 50, 70))
    for k, name in enumerate(WORKER_POSES):
        over(poses, pics["gravpong_worker_l_" + name], k * (WORKER[0] + 2), 0)
    y = sheet.put("gravpong_worker_l_<pose>: stand, tired, run0..3, back0..3, trun0..3, tback0..3 (r: mirrored), at 3x",
                  poses.resize((poses.width * 3, WORKER[1] * 3), Image.NEAREST), 10, y) + 12
    small = Image.new("RGB", (NOTE_POSES * 10 + 10 * (DIGIT_W + 2), DIGIT_H), (34, 28, 48))
    for k in range(NOTE_POSES):
        over(small, pics["gravpong_note_%d" % k], k * 10, 3)
    for n in range(10):
        over(small, pics["gravpong_digit_%d" % n], NOTE_POSES * 10 + n * (DIGIT_W + 2), 0)
    y = sheet.put("gravpong_note_0..2 8x5 and gravpong_digit_0..9 8x12, at 4x",
                  small.resize((small.width * 4, DIGIT_H * 4), Image.NEAREST), 10, y) + 12
    title = pics["gravpong_title"].copy()
    show_bubble(title, pics, 160, 204, 28, "round", "round0")
    number(title, pics, 26, TITLE_PLATE[0] + PLATE_W - 3, TITLE_PLATE[1] + 3)
    sheet.put("gravpong_title, the bubble inflated, best 26", title.convert("RGB"), 10, y)
    end = gravpong_end(pics)
    end.paste(pics["gravpong_over"], (60, 70))
    for (px, py), value in zip(CARD_PLATES, (26, 31)):
        number(end, pics, value, 60 + px + PLATE_W - 3, 70 + py + 3)
    sheet.put("game over: gravpong_crash, the pop, the notes and gravpong_over", end.convert("RGB"), 350, y)
    return y + H + 32


def paint_gravpong():
    pics = {"gravpong_midnight": (paint_midnight(), False)}
    for d in SIZES:
        for ring in RINGS:
            pics["gravpong_halo_%d_%d" % (d, ring)] = (halo(d, ring), True)
        for pose in POSES:
            pics["gravpong_bubble_%d_%s" % (d, pose)] = (bubble(d, pose), True)
        for name in FILMS:
            pics["gravpong_film_%d_%s" % (d, name)] = (film(d, name), True)
    for name in WORKER_POSES:
        right = worker(name)
        pics["gravpong_worker_l_%s" % name] = (right, True)  # the left worker faces right, toward the net
        pics["gravpong_worker_r_%s" % name] = (ImageOps.mirror(right), True)
    for k, depth in enumerate(NET_DEPTHS):
        pics["gravpong_net_%d" % k] = (net(depth), True)
    for k in range(POP_FRAMES):
        pics["gravpong_pop_%d" % k] = (pop(k), True)
    for k in range(NOTE_POSES):
        pics["gravpong_note_%d" % k] = (note(k), True)
    for n in range(10):
        pics["gravpong_digit_%d" % n] = (digit(n), True)
    pics["gravpong_coin"] = (coin(), True)
    pics["gravpong_spot"] = (spot(), True)
    pics["gravpong_crash"] = (crash(pics["gravpong_midnight"][0]), False)
    pics["gravpong_title"] = (paint_title(pics["gravpong_midnight"][0], {n: img for n, (img, _) in pics.items()}),
                              False)
    pics["gravpong_over"] = (paint_over(), False)
    return Painting(pics)


ART_SET = ArtSet("gravpong", 5732, paint_gravpong, sheet_fn=gravpong_sheet, scene_fn=gravpong_frame)
