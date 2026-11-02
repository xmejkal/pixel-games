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

PICS = {}  # name: (w, h, memoryview into the pool)
LAYERS = []  # [name, top, w, h, speed, keyed, memoryview], back to front
ready = False


def load():
    """Read every picture once, into one block the collector does not scan (s3lcd.pool, P562): 733 KB in the heap
    made each collection cost about 90 ms. Answers whether art is there."""
    global ready
    if ready or art_index is None:
        return ready
    pics = list(art_index.ART.items())
    layers = list(getattr(art_index, "LAYERS", ()))
    sizes = {}  # path: bytes, each file once: a layer's file is also a picture
    for _, (w, h, path) in pics:
        sizes[path] = w * h * 2
    for row in layers:
        sizes[row[6]] = row[2] * row[3] * 2
    total = sum(sizes.values())
    if not total:
        return False
    try:
        import s3lcd
        block = memoryview(s3lcd.pool(total))
    except (ImportError, AttributeError, ValueError):  # no pool (the Mac, an older image, or a pool kept smaller)
        block = memoryview(bytearray(total))
    files, at = {}, 0  # path: its slice of the block
    try:
        for path, n in sizes.items():
            files[path] = buf = block[at:at + n]
            at += n
            with open("/" + path, "rb") as f:
                f.readinto(buf)
    except OSError:  # a file missing on the board: no art at all, rather than half of it
        return False
    for name, (w, h, path) in pics:
        PICS[name] = (w, h, files[path])
    for name, top, w, h, speed, keyed, path in layers:
        LAYERS.append([name, top, w, h, speed, keyed, files[path]])
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
