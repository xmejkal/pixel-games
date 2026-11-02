"""
The painted pictures (P562): loaded once from the board's /art folder into PSRAM, drawn by one blit_buffer call each.

art/paint.py makes them on the Mac, already in the panel's layout and byte order, and writes art_index.py. A game asks
draw() for a picture and draw_layer() for a window of a scrolling strip; both answer False when there is no art (on the
Mac, with the st7789 backend, or at ORIENTATION 180), and the game then draws its old shapes.
"""

try:
    import art_index
except ImportError:  # no art made yet
    art_index = None

PICS = {}  # name: (w, h, bytearray)
LAYERS = []  # [name, top, w, h, speed, keyed, memoryview], back to front
ready = False


def load():
    """Read every picture once. Answers whether art is there."""
    global ready
    if ready or art_index is None:
        return ready
    try:
        for name, (w, h, path) in art_index.ART.items():
            buf = bytearray(w * h * 2)
            with open("/" + path, "rb") as f:
                f.readinto(buf)
            PICS[name] = (w, h, buf)
        for name, top, w, h, speed, keyed, path in getattr(art_index, "LAYERS", ()):
            buf = bytearray(w * h * 2)
            with open("/" + path, "rb") as f:
                f.readinto(buf)
            LAYERS.append([name, top, w, h, speed, keyed, memoryview(buf)])
    except OSError:  # a file missing on the board: no art at all, rather than half of it
        PICS.clear()
        LAYERS.clear()
        return False
    ready = True
    return True


def draw(cv, name, x, y):
    """The picture at game (x, y), its clear colour skipped. False when it cannot be drawn this way."""
    pic = PICS.get(name)
    if pic is None or not getattr(cv, "pictures", False):
        return False
    cv.picture(pic[2], int(x), int(y), pic[0], pic[1], art_index.KEY_C565)
    return True


def draw_layers(cv, travelled, moving):
    """The still layers (moving False) or the scrolling ones, each moved by travelled px times its speed. A strip's
    game x runs along panel rows, so a window of it is one contiguous slice: one blit, or two where the strip wraps."""
    if not LAYERS or not getattr(cv, "pictures", False):
        return False
    for _, top, w, h, speed, keyed, mv in LAYERS:
        if (speed > 0) != moving:
            continue
        key = art_index.KEY_C565 if keyed else -1
        o = int(travelled * speed) % w
        first = min(320, w - o)  # the window [o, o + 320) of the strip, up to its end
        _window(cv, mv, w, h, o, o + first, 0, top, key)
        if first < 320:  # and the rest from its start
            _window(cv, mv, w, h, 0, 320 - first, first, top, key)
    return True


def _window(cv, mv, w, h, a, b, x, top, key):
    # game x [a, b) of the strip is panel rows [w - b, w - a): contiguous bytes
    cv.picture(mv[(w - b) * h * 2:(w - a) * h * 2], x, top, b - a, h, key)
