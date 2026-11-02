"""Write the painted art for the board: the RGB565 files, games/art_index.py, and the preview sheets to look at."""

import os

from PIL import Image, ImageDraw, ImageFont

from brush import H, KEY, NUDGE, W
from looks import NightInk


# --- the board's format ------------------------------------------------------------------------------------------

def c565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def to_bin(img, keyed):
    """Game image (w, h) -> panel bytes (h by w after a 90 degree turn), RGB565 big-endian."""
    panel = img.transpose(Image.ROTATE_90)
    out = bytearray()
    for px in panel.get_flattened_data():
        if keyed and px[3] == 0:
            v = KEY
        else:
            v = c565(*px[:3])
            if v == KEY:
                v = NUDGE
        out += bytes((v >> 8, v & 0xFF))
    return bytes(out)


def from_bin(data, w, h):
    """The reverse, to check: panel bytes -> game RGBA image, the key as transparent."""
    panel = Image.new("RGBA", (h, w))
    px = []
    for i in range(0, len(data), 2):
        v = (data[i] << 8) | data[i + 1]
        if v == KEY:
            px.append((0, 0, 0, 0))
        else:
            px.append((((v >> 11) & 31) << 3, ((v >> 5) & 63) << 2, (v & 31) << 3, 255))
    panel.putdata(px)
    return panel.transpose(Image.ROTATE_270)


def q565(img):
    """What the board shows: each opaque pixel cut to RGB565 (the key nudged), the rest transparent."""
    def one(p):
        if p[3] == 0:
            return (0, 0, 0, 0)
        r, g, b = p[0] & 0xF8, p[1] & 0xFC, p[2] & 0xF8
        return (r, g, b - 8, 255) if (r, g, b) == (248, 0, 248) else (r, g, b, 255)
    out = Image.new("RGBA", img.size)
    out.putdata([one(p) for p in img.get_flattened_data()])
    return out


# --- the preview sheets ------------------------------------------------------------------------------------------

class Sheet:
    """A paper page that each set draws its rows on: a label in pencil, the picture 18 px below it."""

    PAPER, INK = (245, 240, 230), (40, 40, 40)

    def __init__(self, w, h):
        self.font = ImageFont.load_default(size=14)
        self.image = Image.new("RGB", (w, h), self.PAPER)
        self.draw = ImageDraw.Draw(self.image)

    def put(self, label, img, x, y):
        self.draw.text((x, y), label, fill=self.INK, font=self.font)
        self.image.paste(img, (x, y + 18))
        return y + 18 + img.height


def checker(w, h, c=8):
    img = Image.new("RGB", (w, h), (240, 240, 240))
    d = ImageDraw.Draw(img)
    for y in range(0, h, c):
        for x in range(0, w, c):
            if (x + y) // c % 2:
                d.rectangle((x, y, x + c - 1, y + c - 1), fill=(200, 200, 200))
    return img


def preview(sets, paintings, path):
    """preview.png: each set's rows in the table's order, then the tails (the runner's sprite grid), cropped."""
    sheet = Sheet(1320, 3000)
    y = 8
    for art_set in sets:
        if art_set.sheet_fn:
            y = art_set.sheet_fn(paintings[art_set.name], sheet, y)
    for art_set in sets:
        if art_set.tail_fn:
            y = art_set.tail_fn(paintings[art_set.name], sheet, y)
    sheet.image.crop((0, 0, sheet.image.width, y + 40)).save(path)


def preview_ink(sets, paintings, path):
    """preview-ink.png: the second look, to judge it. Each set with an ink accent, as painted and through NightInk.
    Only this sheet uses night ink; no board file changes."""
    shown = [art_set for art_set in sets if art_set.ink_accent]
    sheet = Sheet(W * 4 + 40, len(shown) * (H * 2 + 28) + 8)
    y = 8
    for art_set in shown:
        painted = paintings[art_set.name]
        inked = painted.through(NightInk(art_set.ink_accent))
        for x, label, painting in ((10, "as painted", painted), (W * 2 + 30, "in night ink", inked)):
            sheet.put("%s, %s, at 2x" % (art_set.name, label),
                      art_set.scene_fn(painting).resize((W * 2, H * 2), Image.NEAREST), x, y)
        y += H * 2 + 28
    sheet.image.save(path)


# --- checks ------------------------------------------------------------------------------------------------------

def seam(img):
    """The mean colour step across the wrap, and the worst mean step between two neighbour columns inside."""
    cols = [[img.getpixel((x, y)) for y in range(img.height)] for x in range(img.width)]

    def step(a, b):
        d = [abs(p - q) for pa, pb in zip(a, b) if pa[3] and pb[3] for p, q in zip(pa[:3], pb[:3])]
        return sum(d) / max(1, len(d))
    return step(cols[-1], cols[0]), max(step(cols[x], cols[x + 1]) for x in range(img.width - 1))


def check_seams(paintings):
    """Each wrapped layer (every layer but the still sky) joins at its edges no harder than it steps inside."""
    for painting in paintings.values():
        for name, img, *_ in painting.layers[1:]:
            step, inside = seam(img)
            assert step <= inside, name  # the wrap is no harder a step than one inside the strip
            print("%s: seam step %.1f, worst step inside %.1f" % (name, step, inside))


# --- writing the files -------------------------------------------------------------------------------------------

def write_bins(paintings, out_dir):
    """Every picture of every set as its .bin file, each checked to decode back to the picture. Returns the bytes."""
    total = 0
    for painting in paintings.values():
        for name, (img, keyed) in painting.pictures.items():
            for p in img.get_flattened_data():  # a hard mask: no pixel is half there
                assert p[3] in ((0, 255) if keyed else (255,)), name
            data = to_bin(img, keyed)
            w, h = img.size
            assert len(data) == w * h * 2, name
            assert from_bin(data, w, h).tobytes() == q565(img).tobytes(), name  # the file decodes back to the picture
            if not keyed:
                assert all((data[i] << 8 | data[i + 1]) != KEY for i in range(0, len(data), 2)), name
            with open(os.path.join(out_dir, name + ".bin"), "wb") as f:
                f.write(data)
            total += len(data)
    return total


def layer_rows(layers, indent):
    """One index row per layer: (name, top, width, height, speed, keyed, path)."""
    row = '%s("%s", %d, %d, %d, %s, %s, "art/%s.bin"),'
    return [row % (indent, name, top, img.width, img.height, speed, keyed, name)
            for name, img, top, speed, keyed in layers]


def write_index(sets, paintings, path):
    """games/art_index.py: ART (each set's pictures in its own order, then every set's aliases), LAYERS (the layers
    of the one set with index_layers, the runner's), LAYER_SETS (every set with layers). Returns the names in ART."""
    index = {}
    for painting in paintings.values():
        for name, (img, _) in painting.pictures.items():
            index[name] = (img.width, img.height, "art/%s.bin" % name)
    for art_set in sets:
        for old, new in art_set.aliases.items():  # an old name the game may still ask for, the same file
            index[old] = index[new]
    lines = ['"""Generated by art/paint.py: do not edit. The painted pictures, as RGB565 files the board copies."""',
             "",
             "KEY = 0x%04X  # the transparent pixel as written in the .bin files (big-endian bytes F8 1F)" % KEY,
             "KEY_C565 = 0x%04X  # the same key as the board's colour int (c565 values are the byte-swapped v)"
             % (((KEY & 0xFF) << 8) | (KEY >> 8)),
             "",
             "# name: (game width, game height, path on the board). A file is the picture turned to the panel: h x w,",
             "# so a strip's game x runs along the file's rows, and a 320 px window of a strip is one contiguous slice.",
             "ART = {"]
    lines += ['    "%s": (%d, %d, "%s"),' % (n, w, h, p) for n, (w, h, p) in index.items()]
    owners = [art_set for art_set in sets if art_set.index_layers]
    assert len(owners) == 1, "exactly one set's layers are LAYERS"
    owner = owners[0]
    lines += ["}", "",
              "# The parallax layers, back to front: (name, top game row, width, height, speed as a fraction of the",
              "# runner's, keyed, path). A strip wider than 320 tiles: its left and right edges join. bg is the fallback.",
              "LAYERS = ["]
    lines += layer_rows(paintings[owner.name].layers, "    ")
    lines += ["]", "",
              "# Every game's layers, the same shape as LAYERS, back to front.",
              "LAYER_SETS = {",
              '    "%s": LAYERS,' % owner.name]
    for art_set in sets:
        layers = paintings[art_set.name].layers
        if layers and art_set is not owner:
            lines += ['    "%s": [' % art_set.name] + layer_rows(layers, "        ") + ["    ],"]
    lines += ["}", ""]
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return len(index)
