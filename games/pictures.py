"""
The painted pictures (P562): read from the board's /art folder into PSRAM, drawn by one blit_buffer call each.

art/paint.py makes them on the Mac, already in the panel's layout and byte order, and writes art_index.py. Each game
loads only its own art set (art_index.PICTURE_SETS) when the box switches to it, so the box starts its first game
without reading every set first: 2.9 MB took 15 to 20 s on the board (P773). A game asks draw() for a picture and
draw_layer() for a window of a scrolling strip; both answer False when there is no art (on the Mac, with the st7789
backend, or at ORIENTATION 180), and the game then draws its old shapes.
"""

try:
    import art_index
except ImportError:  # no art made yet
    art_index = None

ROOT = "/"  # where the art folder is: the board's root; a Mac tool points it at games/
PICS = {}  # name: (w, h, memoryview into the block) of the loaded set
SETS = {}  # game name: its layers, each [name, top, w, h, speed, keyed, memoryview], back to front
ready = False
loaded = None  # (set, only) that PICS holds, or None


def files_of(sets, only=None):
    """{path: bytes} of the pictures of these sets (only those named in only, when given) and of their layers."""
    sizes = {}  # each file once: a layer's file is also a picture, and an alias shares its file
    for name in [n for game in sets for n in art_index.PICTURE_SETS[game]]:
        if only is None or name in only:
            w, h, path = art_index.ART[name]
            sizes[path] = w * h * 2
    if only is None:
        for row in [row for game in sets for row in layer_sets().get(game, ())]:
            sizes[row[6]] = row[2] * row[3] * 2
    return sizes


def layer_sets():
    return getattr(art_index, "LAYER_SETS", None) or {"runner": getattr(art_index, "LAYERS", ())}


def free():
    """Drop the loaded set: its pictures go, and the block they were read into is the next set's (P773)."""
    global ready, loaded
    PICS.clear()
    SETS.clear()
    ready, loaded = False, None


def block(n):
    """n bytes to read pictures into: on the board, the start of s3lcd's pool in PSRAM, one block the collector does
    not scan (P562: 733 KB in the heap made each collection cost about 90 ms). It is made once, as big as the largest
    set, and every set is read into it in turn. On the Mac (or an older image) a bytearray."""
    try:
        import s3lcd
        largest = max(sum(files_of((game,)).values()) for game in art_index.PICTURE_SETS)
        return memoryview(s3lcd.pool(max(n, largest)))
    except (ImportError, AttributeError, ValueError):  # no pool (the Mac, an older image, or a pool kept smaller)
        return memoryview(bytearray(n))


def load(game=None, only=None):
    """Read one game's art set once (game: its name in art_index.PICTURE_SETS; only: just these of its pictures), and
    free the set loaded before. game None reads every set, for the tools on the Mac. Answers whether art is there."""
    global ready, loaded
    if art_index is None:
        return False
    if loaded == (game, only):
        return ready
    free()
    sets = tuple(art_index.PICTURE_SETS) if game is None else (game,) if game in art_index.PICTURE_SETS else ()
    sizes = files_of(sets, only)
    total = sum(sizes.values())
    if not total:
        return False
    buf, files, at = block(total), {}, 0  # path: its slice of the block
    try:
        for path, n in sizes.items():
            files[path] = view = buf[at:at + n]
            at += n
            with open(ROOT + path, "rb") as f:
                f.readinto(view)
    except OSError:  # a file missing on the board: no art at all, rather than half of it
        return False
    for name in [n for g in sets for n in art_index.PICTURE_SETS[g]]:
        w, h, path = art_index.ART[name]
        if path in files:
            PICS[name] = (w, h, files[path])
    if only is None:
        for g in sets:
            if g in layer_sets():
                SETS[g] = [[name, top, w, h, speed, keyed, files[path]] for name, top, w, h, speed, keyed, path
                           in layer_sets()[g]]
    ready, loaded = True, (game, only)
    return True


def draw(cv, name, x, y, alpha=255):
    """The picture at game (x, y), its clear colour skipped; under alpha 255 blended over the frame (a glow). False
    when it cannot be drawn this way."""
    pic = PICS.get(name)
    if pic is None or not getattr(cv, "pictures", False):
        return False
    cv.picture(pic[2], int(x), int(y), pic[0], pic[1], art_index.KEY_C565, alpha)
    return True


def draw_cut(cv, name, x, y, w):
    """The first w px of a strip picture at game (x, y): a block of any width cut from a painted texture (P563).
    Opaque, one blit of a contiguous slice. False when it cannot be drawn this way."""
    pic = PICS.get(name)
    if pic is None or not getattr(cv, "pictures", False):
        return False
    sw, h, buf = pic
    w = min(int(w), sw)
    if w > 0:  # game x [0, w) of the strip is panel rows [sw - w, sw)
        cv.picture(buf[(sw - w) * h * 2:sw * h * 2], int(x), int(y), w, h, -1)
    return True


def draw_layers(cv, travelled, moving, game="runner", only=None):
    """A game's still layers (moving False) or its scrolling ones, each moved by travelled px times its speed; only
    those named in only, when given. A strip's game x runs along panel rows, so a window of it is one contiguous
    slice: one blit, or two where the strip wraps."""
    layers = SETS.get(game)
    if not layers or not getattr(cv, "pictures", False):
        return False
    for name, top, w, h, speed, keyed, mv in layers:
        if (speed > 0) != moving or (only and name not in only):
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
