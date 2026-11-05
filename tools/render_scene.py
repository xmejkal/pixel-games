"""Draw a C scene on the Mac to a PNG, to set a look from frames before the board (P596). It plays the scene with the
tests' engine stand-ins (fx_fire.c or fx_balls.c through ctypes) and writes the panel frame in the game's view. Needs
clang and Pillow. From the repository root:
    python3 -B tools/render_scene.py [--filter nearest|linear] burning out.png [frames ...]
The scene is fire, burning or balls (P598); one PNG per frame count, side by side. --filter (P608) sets a heat field's
filter after setup, so nearest shows the 2 x 2 px blocks and linear the bilinear filtering; without it the scene's
first mode draws. The balls pour again every POUR_FRAMES frames, as taps would. --- MVP (P596) ---"""

import argparse
import contextlib
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "engine", "tests"))  # pixel-engine: clang_lib
from clang_lib import S3LCD_SRC, build, core  # noqa: E402
from test_fire import Engine, Tft, play  # noqa: E402

import balls  # noqa: E402
import balls_lib  # noqa: E402
import burning  # noqa: E402
import fire  # noqa: E402
import plugins  # noqa: E402
from PIL import Image  # noqa: E402

SCENES = {"fire": fire.Fire, "burning": burning.BurningBodies, "balls": balls.BallPit}
FILTERS = {"nearest": fire.NEAREST, "linear": fire.LINEAR}  # --- MVP (P608) ---
POUR_FRAMES = 25  # --- MVP (P598) --- a pour every second, so 12 fill the pit by frame 300


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
    parser = argparse.ArgumentParser(description="Draw a C scene on the Mac to a PNG.")
    parser.add_argument("--filter", choices=sorted(FILTERS), help="the field's filter (P608)")
    parser.add_argument("scene", choices=sorted(SCENES))
    parser.add_argument("out")
    parser.add_argument("frames", type=int, nargs="*", default=[100])
    args = parser.parse_args()
    name, out, counts = args.scene, args.out, args.frames
    fire.engine = Engine(build(core("fx_fire"), ("-I", S3LCD_SRC)))
    balls.engine, plugins.engine = balls_lib.engine(), None  # bodies on a PhysicsPlugin over motion.Bodies
    fire.random.seed(fire.SEED)  # the fire's gusts too, so a render with each filter shows the same flames
    with contextlib.redirect_stdout(io.StringIO()):
        game, tft, now, shots = SCENES[name](), Tft(), 0, []
        if args.filter:
            game.fire_plugin.set_filter(FILTERS[args.filter])
        for n in counts:
            while now // 40 < n:
                _, now = play(game, 1, now, tft)
                if name == "balls" and (now // 40) % POUR_FRAMES == 0:
                    game.pour()  # play() takes one pressed flag, so the scene pours itself
            shots.append(frame_image(tft))
    sheet = Image.new("RGB", (330 * len(shots), 240))
    for k, shot in enumerate(shots):
        sheet.paste(shot, (330 * k, 0))
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
