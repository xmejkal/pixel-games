"""Draw a heat-field scene on the Mac to a PNG, to set a look from frames before the board (P596). It plays the scene
with tests/test_fire.py's engine stand-in (fx_fire.c through ctypes) and writes the panel frame in the game's view.
Needs clang and Pillow. From the repository root:
    python3 -B tools/render_scene.py [--filter nearest|linear] burning out.png [frames ...]
The scene is fire, burning or flappy; one PNG per frame count, side by side. --filter (P608) sets the field's filter
after setup, so nearest shows the 2 x 2 px blocks and linear the bilinear filtering; without it the scene's first mode
draws. Flappy (P602) draws through the real lcd.TftCanvas on its plain sky (no art on the Mac), taps whenever the bird
sinks below y 120, and never dies, so the frames show its fire trail. --- MVP (P596) ---"""

import argparse
import contextlib
import ctypes
import io
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from test_fire import FIRE_C, S3LCD_SRC, Engine, Tft, fly, play  # noqa: E402

import arcade  # noqa: E402
import burning  # noqa: E402
import fire  # noqa: E402
import rain  # noqa: E402
from PIL import Image  # noqa: E402

SCENES = {"fire": fire.Fire, "burning": burning.BurningBodies, "flappy": arcade.Flappy}
DRIVERS = {"flappy": fly}  # --- MVP (P602) --- how a scene plays its frames, play (tests/test_fire.py) when not here
FILTERS = {"nearest": fire.NEAREST, "linear": fire.LINEAR}  # --- MVP (P608) ---


def frame_image(tft):
    """The s3lcd frame (panel byte order, portrait) as the game's landscape view."""
    img = Image.new("RGB", (240, 320))
    px = []
    for k in range(0, len(tft.frame), 2):
        v = tft.frame[k] << 8 | tft.frame[k + 1]  # the panel's byte order, read back to normal
        px.append(((v >> 11) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31))
    img.putdata(px)
    return img.rotate(-90, expand=True)


def main():
    parser = argparse.ArgumentParser(description="Draw a heat-field scene on the Mac to a PNG.")
    parser.add_argument("--filter", choices=sorted(FILTERS), help="the field's filter (P608)")
    parser.add_argument("scene", choices=sorted(SCENES))
    parser.add_argument("out")
    parser.add_argument("frames", type=int, nargs="*", default=[100])
    args = parser.parse_args()
    name, out, counts = args.scene, args.out, args.frames
    with tempfile.TemporaryDirectory() as tmp:
        lib_path = os.path.join(tmp, "libfire.so")
        subprocess.run(["clang", "-std=c99", "-O2", "-shared", "-fPIC", "-I", S3LCD_SRC, "-o", lib_path, FIRE_C],
                       check=True)
        fire.engine, rain.engine = Engine(ctypes.CDLL(lib_path)), None  # bodies on rain.Stepper over motion.Bodies
        fire.random.seed(fire.SEED)  # the fire's gusts too, so a render with each filter shows the same flames
        with contextlib.redirect_stdout(io.StringIO()):
            game, tft, now, shots = SCENES[name](), Tft(), 0, []
            field = game.layer.field if hasattr(game, "layer") else game.field  # P602: flappy's field is its layer's
            game.die = lambda *args: None  # the bird flies on through the pipes; the fire scenes never die
            if args.filter:
                field.set_filter(FILTERS[args.filter])
            for n in counts:
                if name in DRIVERS:
                    now = DRIVERS[name](game, n - (now // 40), now, tft)
                else:
                    _, now = play(game, n - (now // 40), now, tft)
                shots.append(frame_image(tft))
    sheet = Image.new("RGB", (330 * len(shots), 240))
    for k, shot in enumerate(shots):
        sheet.paste(shot, (330 * k, 0))
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
