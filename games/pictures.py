"""
The painted pictures (P562): read from the board's /packs folder into PSRAM, drawn by one blit_buffer call each.

art/paint.py makes them on the Mac, already in the panel's layout and byte order, and writes art_index.py. Each game
loads only its own art set (art_index.PICTURE_SETS) when the box switches to it, so the box starts its first game
without reading every set first: 2.9 MB took 15 to 20 s on the board (P773). A set is one pack file (P814): one open,
where a folder of 681 picture files cost up to 88 ms an open and 22 s for Rescue's set, then reads of CHUNK_SIZE
bytes, each short enough that the sound's callback runs between two of them and the music stays fed. A game asks
draw() for a picture and draw_layer() for a window of a scrolling strip; both answer False when there is no art (on the
Mac, with the st7789 backend, or at ORIENTATION 180), and the game then draws its old shapes.
"""

import time
from binascii import hexlify

try:
    import art_index
except ImportError:  # no art made yet
    art_index = None

ROOT = "/"  # where the packs folder is: the board's root; a Mac tool points it at games/
MAGIC = b"PIXPACK1"  # a pack's first 8 bytes (art/export.py writes them); the next 8 are its build id
HEADER = 16
CHUNK_SIZE = 8192  # bytes per read: about 6 ms on the board, well under the 48 ms the sound counts late (P814)
PICS = {}  # name: (w, h, memoryview into the block) of the loaded set
SETS = {}  # game name: its layers, each [name, top, w, h, speed, keyed, memoryview], back to front
ready = False
loaded = None  # (set, only) that PICS holds, or None
load_ms = 0  # how long the last load read, in ms; 0 after free(): App.switch prints it


def free():
    """Drop the loaded set: its pictures go, and the block they were read into is the next set's (P773)."""
    global ready, loaded, load_ms
    PICS.clear()
    SETS.clear()
    ready, loaded, load_ms = False, None, 0


def block(n):
    """n bytes to read pictures into: on the board, the start of s3lcd's pool in PSRAM, one block the collector does
    not scan (P562: 733 KB in the heap made each collection cost about 90 ms). It is made once, as big as the largest
    pack, and every set is read into it in turn. On the Mac (or an older image) a bytearray."""
    try:
        import s3lcd
        largest = max(total for path, total, build_id in art_index.PACKS.values())
        return memoryview(s3lcd.pool(max(n, largest)))
    except (ImportError, AttributeError, ValueError):  # no pool: no s3lcd on the Mac (ImportError), an older image
        # without s3lcd.pool (AttributeError), or a pool a soft reset kept smaller (ValueError): a bytearray instead
        return memoryview(bytearray(n))


def spans(game, only=None):
    """The (offset, length) spans of the game's pack to read after its header: all of it, or the pictures in only."""
    path, total, build_id = art_index.PACKS[game]
    if only is None:
        return [(HEADER, total - HEADER)]
    out = {}  # each entry once: an alias shares its picture's entry
    for name in art_index.PICTURE_SETS[game]:
        if name in only:
            w, h, _, at = art_index.ART[name]
            out[at] = w * h * 2
    return sorted(out.items())


def read_chunks(f, view):
    """Fill view from f, CHUNK_SIZE bytes a call into a slice of the block (no copy: each chunk is a small memoryview
    of the block), so the sound's callback runs between two calls. Returns the bytes read: fewer than len(view) at
    the file's end."""
    got = 0
    while got < len(view):
        n = f.readinto(view[got:got + CHUNK_SIZE])
        if not n:
            break
        got += n
    return got


def read_pack(game, parts, buf, at):
    """Read the game's pack into buf from at: its header, checked against PACKS, then each of parts. Returns each
    part read as (offset in the pack, length, place in buf), or None when the pack's size or header is not this
    build's."""
    path, total, build_id = art_index.PACKS[game]
    out = []
    with open(ROOT + path, "rb") as f:
        if f.seek(0, 2) != total:
            return None
        f.seek(0)
        head = buf[at:at + HEADER]
        if read_chunks(f, head) != HEADER or bytes(head[:len(MAGIC)]) != MAGIC or \
                hexlify(head[len(MAGIC):]).decode() != build_id:
            return None
        at += HEADER
        for offset, n in parts:
            f.seek(offset)
            if read_chunks(f, buf[at:at + n]) != n:
                return None
            out.append((offset, n, at))
            at += n
    return out


def view(buf, parts, offset, n):
    """The n bytes at offset in a pack, in the part read that holds them, or None when none does."""
    for start, length, at in parts:
        if start <= offset and offset + n <= start + length:
            return buf[at + offset - start:at + offset - start + n]
    return None


def since(start):
    """The ms from start (time.ticks_ms()) to now; 0 on the Mac, where CPython's time has no ticks."""
    return time.ticks_diff(time.ticks_ms(), start) if hasattr(time, "ticks_diff") else 0


def refuse(message):
    """No art, said aloud: the set half read goes."""
    PICS.clear()
    SETS.clear()
    print(message)
    return False


def place(game, parts, buf, only):
    """The game's pictures (only those in only, when given) and its layers, as views of the parts read into buf."""
    for name in art_index.PICTURE_SETS[game]:
        w, h, _, offset = art_index.ART[name]
        if only is None or name in only:
            PICS[name] = (w, h, view(buf, parts, offset, w * h * 2))
    if only is None and game in art_index.LAYER_SETS:
        SETS[game] = [[name, top, w, h, speed, keyed, view(buf, parts, offset, w * h * 2)]
                      for name, top, w, h, speed, keyed, _, offset in art_index.LAYER_SETS[game]]


def load(game=None, only=None):
    """Read one game's art set once (game: its name in art_index.PICTURE_SETS; only: just these of its pictures), and
    free the set loaded before. game None reads every pack, for the tools on the Mac. A missing pack, or one whose size
    or header is not this build's, is refused aloud, naming the game: no art, rather than another build's. A refused
    load is kept like a loaded one, so asked again it answers False with no read and no message; free() forgets it.
    Answers whether art is there."""
    global ready, loaded, load_ms
    if art_index is None:
        return False
    if loaded == (game, only):
        return ready
    free()
    loaded = (game, only)
    start = time.ticks_ms() if hasattr(time, "ticks_ms") else 0  # the Mac's CPython has no ticks
    if not hasattr(art_index, "PACKS") or any(len(row) != 4 for row in art_index.ART.values()):
        return refuse("art: games/art_index.py is from before the packs: copy games/*.py and games/packs, "
                      "then hard reset")
    if game is None:
        sets = tuple(art_index.PICTURE_SETS)
    elif game in art_index.PICTURE_SETS:
        sets = (game,)
    else:
        sets = ()
    reads = [(g, spans(g, only)) for g in sets]
    if not any(n for _, parts in reads for _, n in parts):
        return False
    buf, at = block(sum(HEADER + sum(n for _, n in parts) for _, parts in reads)), 0
    for g, parts in reads:
        try:
            got = read_pack(g, parts, buf, at)
        except OSError:  # no pack there
            return refuse("art: %s has no pack: copy games/packs to the board" % g)
        if got is None:
            return refuse("art: %s pack is not this build: copy games/*.py and games/packs, then hard reset" % g)
        place(g, got, buf, only)
        at += HEADER + sum(n for _, n in parts)
    ready, load_ms = True, since(start)
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
