"""Draw a heat-field scene on the Mac to a PNG, to set a look from frames before the board (P596). It plays the scene
with tests/test_fire.py's engine stand-in (fx_fire.c through ctypes) and writes the panel frame in the game's view.
Needs clang and Pillow. From the repository root:
    python3 -B tools/render_scene.py burning out.png [frames ...]
The scene is fire or burning; one PNG per frame count, side by side. --- MVP (P596) ---"""

import contextlib
import ctypes
import io
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from test_fire import FIRE_C, S3LCD_SRC, Engine, Tft, play  # noqa: E402

import burning  # noqa: E402
import fire  # noqa: E402
import rain  # noqa: E402
from PIL import Image  # noqa: E402

SCENES = {"fire": fire.Fire, "burning": burning.BurningBodies}


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
    name, out, counts = sys.argv[1], sys.argv[2], [int(a) for a in sys.argv[3:]] or [100]
    with tempfile.TemporaryDirectory() as tmp:
        lib_path = os.path.join(tmp, "libfire.so")
        subprocess.run(["clang", "-std=c99", "-O2", "-shared", "-fPIC", "-I", S3LCD_SRC, "-o", lib_path, FIRE_C],
                       check=True)
        fire.engine, rain.engine = Engine(ctypes.CDLL(lib_path)), None  # bodies on rain.Stepper over motion.Bodies
        with contextlib.redirect_stdout(io.StringIO()):
            game, tft, now, shots = SCENES[name](), Tft(), 0, []
            for n in counts:
                _, now = play(game, n - (now // 40), now, tft)
                shots.append(frame_image(tft))
    sheet = Image.new("RGB", (330 * len(shots), 240))
    for k, shot in enumerate(shots):
        sheet.paste(shot, (330 * k, 0))
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
