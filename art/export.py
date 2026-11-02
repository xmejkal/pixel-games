"""Write the painted art for the board: the RGB565 files, games/art_index.py, and the preview sheets to look at."""

import os

from PIL import Image, ImageDraw, ImageFont

from brush import GROUND, H, KEY, NUDGE, W
from sets.flappy import flappy_scene, morning_at
from sets.runner import JUMP, SCENE
from sets.stack import BLOCK_H, stack_scene


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


# --- the preview sheet -------------------------------------------------------------------------------------------

def frame(layers, sprites, shift, scene=SCENE):
    """One composed game frame: each layer moved by its speed, the sprites on top, as the board would."""
    out = Image.new("RGBA", (W, H))
    for name, img, top, speed, _ in layers:
        x = int(shift * speed) % img.width
        strip = Image.new("RGBA", (img.width * 2, img.height))
        strip.paste(img, (0, 0))
        strip.paste(img, (img.width, 0))
        out.alpha_composite(strip.crop((x, 0, x + W, img.height)), (0, top))
    for name, x, y in scene:
        out.alpha_composite(sprites[name], (x, y))
    return out.convert("RGB")


def checker(w, h, c=8):
    img = Image.new("RGB", (w, h), (240, 240, 240))
    d = ImageDraw.Draw(img)
    for y in range(0, h, c):
        for x in range(0, w, c):
            if (x + y) // c % 2:
                d.rectangle((x, y, x + c - 1, y + c - 1), fill=(200, 200, 200))
    return img


def preview(paintings, path):
    """The sheet to look at: the runner's background, layers and sprites, stack, flappy, then every other runner
    sprite. One function knows the whole sheet; a new game adds its rows here."""
    runner, stack, flappy = paintings["runner"], paintings["stack"].images(), paintings["flappy"]
    bg, layers = runner.images()["bg"], runner.layers
    strips = {name for name, *_ in layers}
    sprites = {n: img for n, img in runner.images().items() if n != "bg" and n not in strips}
    font = ImageFont.load_default(size=14)
    ink = (40, 40, 40)
    width = 1320
    sheet = Image.new("RGB", (width, 3000), (245, 240, 230))
    d = ImageDraw.Draw(sheet)

    def put(label, img, x, y):
        d.text((x, y), label, fill=ink, font=font)
        sheet.paste(img, (x, y + 18))
        return y + 18 + img.height

    y = 8
    put("bg 320x240 (the fallback) at 2x", bg.convert("RGB").resize((W * 2, H * 2), Image.NEAREST), 10, y)
    f = frame(layers, sprites, 900)
    y = put("parallax layers composed, a frame at 2x, with sprites", f.resize((W * 2, H * 2), Image.NEAREST),
            W * 2 + 30, y) + 14
    for name, img, top, speed, _ in layers:  # each strip alone at 2x, on a checkerboard, twice so the seam shows
        if img.width == W:
            continue
        two = Image.new("RGBA", (img.width * 2, img.height))
        two.paste(img, (0, 0))
        two.paste(img, (img.width, 0))
        two = two.crop((img.width - 330, 0, img.width + 330, img.height)).resize((660 * 2, img.height * 2),
                                                                                Image.NEAREST)
        ch = checker(*two.size)
        ch.paste(two, (0, 0), two)
        y = put("%s %dx%d, rows %d to %d, speed %.2f: the seam in the middle, at 2x" %
                (name, img.width, img.height, top, top + img.height, speed), ch, 0, y) + 10
        d.line([(660, y - 10 - ch.height), (660, y - 14)], fill=(255, 0, 0), width=1)
    def frames(names, k=4, gap=6):
        """Sprites side by side at k times, each on the background where it would stand."""
        w, h = sprites[names[0]].size
        out = Image.new("RGB", (len(names) * (w * k + gap), h * k), (245, 240, 230))
        for i, name in enumerate(names):
            under = bg.convert("RGBA").crop((60, GROUND - h, 60 + w, GROUND))
            under.alpha_composite(sprites[name])
            out.paste(under.convert("RGB").resize((w * k, h * k), Image.NEAREST), (i * (w * k + gap), 0))
        return out

    run = ["runner_run%d" % i for i in range(6)]
    jump = ["runner_" + n for n in JUMP]
    put("the run cycle, runner_run0 to runner_run5, at 4x", frames(run), 10, y)
    y = put("the jump: " + ", ".join(jump) + ", at 4x", frames(jump), 10 + 6 * 70 + 30, y) + 14
    cacti = [n for n in sprites if n.startswith("cactus")]
    scene = [(n, 14 + i * 44, GROUND - sprites[n].height) for i, n in enumerate(cacti)] + [(run[0], 300, GROUND - 24)]
    over = frame(layers, sprites, 0, scene).crop((0, 110, W, H)).resize((W * 3, (H - 110) * 3), Image.NEAREST)
    y = put("every cactus over the hills band, a composed frame at 3x", over, 10, y) + 14
    put("stack: stack_bg with ten blocks and the mover, at 2x", stack_scene(stack).resize((W * 2, H * 2), Image.NEAREST),
        10, y)
    for i, name in enumerate(["stack_block%d" % k for k in range(8)] + ["stack_mover"]):
        put("%s 320x14, at 2x" % name, stack[name].convert("RGB").resize((W * 2, BLOCK_H * 2), Image.NEAREST),
            W * 2 + 30, y + i * 52)
    y += H * 2 + 32
    pics, flappy_layers = flappy.images(), flappy.layers
    put("flappy: a frame with two pipe pairs and the bird, at 2x", flappy_scene(pics, flappy_layers).resize(
        (W * 2, H * 2), Image.NEAREST), 10, y)
    for i, name in enumerate("flappy_bird%d%d" % (a, b) for a in range(3) for b in range(2)):
        under = Image.new("RGBA", (18, 14), morning_at(100) + (255,))
        under.alpha_composite(pics[name])
        put(name, under.convert("RGB").resize((72, 56), Image.NEAREST), W * 2 + 30 + (i % 2) * 110, y + (i // 2) * 84)
    for i, name in enumerate(("flappy_pipe_top", "flappy_pipe_bottom")):
        pipe = pics[name]
        under = checker(32, 240)
        under.paste(pipe, (0, 0), pipe)
        put(name, under.resize((64, 480), Image.NEAREST), W * 2 + 270 + i * 120, y)
    y += H * 2 + 32
    x = 10
    tallest = 0
    for name, img in sprites.items():
        if name.startswith("runner"):
            continue  # shown in the strips above
        w, h = img.size
        big = img.resize((w * 4, h * 4), Image.NEAREST)
        cell = 2 * w * 4 + 6
        if x + cell > width - 10:
            x, y, tallest = 10, y + tallest + 30, 0
        ch = checker(w * 4, h * 4)
        ch.paste(big, (0, 0), big)
        gy = GROUND - h if name.startswith(("runner", "cactus")) else 100
        under = bg.convert("RGB").crop((60, gy, 60 + w, gy + h)).resize((w * 4, h * 4), Image.NEAREST)
        under.paste(big, (0, 0), big)
        d.text((x, y), "%s %dx%d" % (name, w, h), fill=ink, font=font)
        sheet.paste(ch, (x, y + 18))
        sheet.paste(under, (x + w * 4 + 6, y + 18))
        x += max(cell, 120) + 14
        tallest = max(tallest, h * 4)
    sheet.crop((0, 0, width, y + tallest + 40)).save(path)


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
    return ['%s("%s", %d, %d, %d, %s, %s, "art/%s.bin"),' % (indent, name, top, img.width, img.height, speed, keyed, name)
            for name, img, top, speed, keyed in layers]


def write_index(sets, paintings, path):
    """games/art_index.py: ART (each set's pictures in its own order, then every set's aliases), LAYERS (the first
    set with layers, the runner's), LAYER_SETS (every set with layers). Returns the number of names in ART."""
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
    layered = [(art_set.name, paintings[art_set.name].layers) for art_set in sets if paintings[art_set.name].layers]
    lines += ["}", "",
              "# The parallax layers, back to front: (name, top game row, width, height, speed as a fraction of the",
              "# runner's, keyed, path). A strip wider than 320 tiles: its left and right edges join. bg is the fallback.",
              "LAYERS = ["]
    lines += layer_rows(layered[0][1], "    ")
    lines += ["]", "",
              "# Every game's layers, the same shape as LAYERS, back to front.",
              "LAYER_SETS = {",
              '    "%s": LAYERS,' % layered[0][0]]
    for name, layers in layered[1:]:
        lines += ['    "%s": [' % name] + layer_rows(layers, "        ") + ["    ],"]
    lines += ["}", ""]
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return len(index)
