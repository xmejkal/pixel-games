"""Draw a game, a scene or the overlay on the Mac, the board's way, to a PNG sheet and a GIF (P596, P795). Each frame
runs lcd.TftOut.draw on tests/drawing_tft.DrawingTft, the display stood in, with the C engines through ctypes
(fx_fire.c, fx_balls.c, world.c) and the painted art from games/packs, so the frame is the one the board shows. Needs
clang and Pillow; the text needs MicroPython's 8x8 font, read from the clone build.sh makes under ~/esp. From the
repository root:
    python3 -B tools/render_scene.py [--filter nearest|linear] [--tap N | --hold N] [--title] [--seed S]
                                     [--font PATH | --no-text] [--gif OUT.gif --every K] SUBJECT out.png FRAMES...
    python3 -B tools/render_scene.py --list
    python3 -B tools/render_scene.py --all DIR
SUBJECT is one of SUBJECTS: fire, rain, the fifteen games by their lower-case class names, and overlay (the ball pit
with the volume pane over it, the one subject that blends). The sheet holds the frame after each count of FRAMES, side
by side; the GIF holds the frames from the first count to the last, every K-th, at K * 40 ms a frame. The button:
--tap N presses on one frame in every N, --hold N holds N frames and releases N (0 holds every frame); the first frame
presses, so the picture starts in play, unless --title keeps the title. --filter (P608) sets a heat field's filter after
setup, so nearest shows the 2 x 2 px blocks and linear the bilinear filtering. --all DIR writes every subject's PNG and
GIF from its SUBJECTS row, which --list prints, the subjects one after the other in one process (the files are the
same as from single runs), and refuses the flags above: the rows are the source of the README's pictures.
--- MVP (P795) ---"""

import argparse
import contextlib
import io
import itertools
import os
import random
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "engine", "tests"))  # pixel-engine: clang_lib, balls_lib, world_lib
from drawing_tft import DrawingTft  # noqa: E402  first: it puts games/ and the stubs on the path
from clang_lib import S3LCD_SRC, build, core  # noqa: E402
from test_fire import Engine  # noqa: E402

import balls  # noqa: E402
import balls_lib  # noqa: E402
import fire  # noqa: E402
import framebuf  # noqa: E402
import lcd  # noqa: E402
import overlay  # noqa: E402
import pictures  # noqa: E402
import plugins  # noqa: E402
import rain  # noqa: E402
import volume  # noqa: E402
import world_lib  # noqa: E402
from arcade import Flappy, Runner, Snake  # noqa: E402
from arcade2 import Cave, GravityPong, Stack  # noqa: E402
from bucket import Bucket  # noqa: E402
from burning import BurningBodies  # noqa: E402
from marshmallow import Marshmallow  # noqa: E402
from meteors import Meteors  # noqa: E402
from PIL import Image  # noqa: E402
from rescue import Rescue  # noqa: E402
from space3d import CubeTiming, Starfire  # noqa: E402
from world3d import Road, Tunnel  # noqa: E402

FRAME_MS = 40  # app.py's FRAME_MS
FILTERS = {"nearest": fire.NEAREST, "linear": fire.LINEAR}  # --- MVP (P608) ---
FONT_PATH = os.path.expanduser("~/esp/micropython-v1.29.0/extmod/font_petme128_8x8.h")  # build.sh's clone
FONT_BYTES = 96 * 8  # the characters 32 to 127, eight column bytes each
GAP = 10  # px between the sheet's frames
EVERY = 2  # the GIF's frames kept, one in this many, unless --every says
PALETTE_FRAMES = 8  # the images a GIF's palette is taken from


class Subject:
    """One row of SUBJECTS: the game class, the hint the README shows, and what makes its pictures. The GIF runs from
    frame first to frame last, every every-th frame; the PNG is frame shot (last when not given). tap or hold is the
    button's pattern (see buttons), or presses its own: (first frame, frames held) each; seed seeds random before the
    game is made; show is the frame the volume pane shows on, None for no overlay."""

    def __init__(self, game, hint, first, last, every=2, tap=None, hold=None, seed=1, shot=None, show=None,
                 presses=None):
        self.game, self.hint, self.first, self.last, self.every = game, hint, first, last, every
        self.tap, self.hold, self.seed, self.shot, self.show = tap, hold, seed, shot or last, show
        self.presses = presses

    def __str__(self):
        press = "tap %d" % self.tap if self.tap else "hold %d" % self.hold if self.hold is not None else "first frame"
        if self.presses:
            press = "presses " + " ".join("%d+%d" % p for p in self.presses)
        return "frames %d to %d every %d, shot %d, %s, seed %d" % (self.first, self.last, self.every, self.shot, press,
                                                                    self.seed)


SUBJECTS = {  # the fire, the rain, app.GAMES in their order, the overlay; the presses and counts set by eye (P795)
    "fire": Subject(fire.Fire, "tap: next mode", 30, 84, seed=fire.SEED),
    "rain": Subject(rain.Rain, "tap: again", 10, 110),
    "marshmallow": Subject(Marshmallow, Marshmallow.hint, 5, 200, every=4, hold=40, shot=195),
    "ballpit": Subject(balls.BallPit, "tap pours, hold shakes", 5, 130, every=3, tap=10),
    "burningbodies": Subject(BurningBodies, "tap: next mode", 20, 100),
    "bucket": Subject(Bucket, Bucket.hint, 90, 222, every=6, hold=20, seed=5, shot=216),
    "meteors": Subject(Meteors, Meteors.hint, 90, 200, every=3, tap=17, seed=18, shot=148),
    "rescue": Subject(Rescue, Rescue.hint, 60, 214, every=3, presses=((0, 1), (145, 32)), shot=112),
    "flappy": Subject(Flappy, Flappy.hint, 5, 70, every=3, tap=12, shot=60),
    "runner": Subject(Runner, Runner.hint, 10, 75, every=3, hold=40),
    "snake": Subject(Snake, Snake.hint, 5, 80, tap=20, shot=45),
    "stack": Subject(Stack, Stack.hint, 5, 72, tap=25),
    "cave": Subject(Cave, Cave.hint, 3, 28, every=1, hold=1, shot=25),
    "tunnel": Subject(Tunnel, Tunnel.hint, 5, 62, tap=25, shot=60),
    "road": Subject(Road, Road.hint, 5, 105),
    "starfire": Subject(Starfire, Starfire.hint, 5, 105, hold=3),
    "cubetiming": Subject(CubeTiming, CubeTiming.hint, 5, 99, tap=25),
    "gravitypong": Subject(GravityPong, GravityPong.hint, 5, 99, tap=16),
    "overlay": Subject(balls.BallPit, "turn the knob", 5, 80, every=3, tap=10, show=0),
}


class Font:
    """The board's 8x8 font, framebuf's: the FONT_BYTES of font_petme128_8x8.h, read in their order (not by the
    `// N=` comments), for the framebuf stub."""

    def __init__(self, path):
        with open(path) as f:
            parts = f.read().split("[] = {", 1)
        if len(parts) < 2:
            raise ValueError("%s is not a font header" % path)
        self.bytes = bytes(int(h, 16) for h in re.findall(r"0x([0-9a-fA-F]{2})", parts[1]))
        if len(self.bytes) != FONT_BYTES:
            raise ValueError("%s holds %d font bytes, not %d" % (path, len(self.bytes), FONT_BYTES))

    def install(self):
        framebuf.FONT = self.bytes


class FrameClock:
    """time's ticks on the frame clock: ticks_ms reads the frame's time, and ticks_us counts one microsecond per call
    from it, so a step takes time (Marshmallow's Campfire reads the flame only after a step that took time) and the
    fps labels say the frame rate, not the Mac's speed."""

    def __init__(self):
        self.ms, self.calls = 0, 0

    def frame(self, ms):
        self.ms, self.calls = ms, 0

    def ticks_us(self):
        self.calls += 1
        return self.ms * 1000 + self.calls

    def install(self):
        time.ticks_ms, time.ticks_us = lambda: self.ms, self.ticks_us
        time.ticks_diff, time.ticks_add = lambda a, b: a - b, lambda a, b: a + b


def buttons(frame, tap=None, hold=None, title=False, presses=None):
    """The button on frame k: (pressed, held). tap N: a press (pressed and held) on one frame in every N, N the
    period. hold N: held N frames, then released N, and so on, N the half period; 0 holds every frame. presses: each
    (first frame, frames held). Without any, frame 0 presses, so the picture starts in play. title keeps frame 0
    unpressed, so the title shows."""
    if title and frame == 0:
        return False, False
    if presses:
        return any(frame == a for a, _ in presses), any(a <= frame < a + n for a, n in presses)
    if tap:
        on = frame % tap == 0
        return on, on
    if hold is not None:
        held = hold == 0 or (frame // hold) % 2 == 0
        return held and (frame == 0 if hold == 0 else frame % hold == 0), held
    return frame == 0, frame == 0


def engines():
    """The C engines the board has, through ctypes: the heat field, the balls and the bodies."""
    fire.engine = Engine(build(core("fx_fire"), ("-I", S3LCD_SRC)))
    balls.engine, plugins.engine = balls_lib.engine(), world_lib.engine()
    pictures.ROOT = os.path.join(ROOT, "games", "")  # the board's /packs/... is games/packs/... here


def frames(row, tap=None, hold=None, title=False, seed=None, mag_filter=None, hold_ms=0):
    """Each frame's image of the row's subject, FRAME_MS apart, as lcd.TftOut.draw draws it on the board. The flags
    override the row's presses and seed; hold_ms keeps the volume pane shown that long (the GIF's length)."""
    clock = FrameClock()
    clock.install()
    engines()
    random.seed(row.seed if seed is None else seed)
    tap, hold, presses = (row.tap, row.hold, row.presses) if tap is None and hold is None else (tap, hold, None)
    ov = pane = None
    if row.show is not None:  # --- MVP (P762) --- the volume pane over the game, as App.overlay draws it
        ov = overlay.Overlay()
        pane = ov.add(overlay.VolumePane(volume.MasterVolume()))
        pane.hold_ms = hold_ms
    quiet = contextlib.redirect_stdout(io.StringIO())  # the games' own lines (the stepper, the mode, the reports)
    with quiet:
        game = row.game()
        if mag_filter is not None:
            game.fire_plugin.set_filter(mag_filter)
    tft, us = DrawingTft(), [0, 0, 0, 0]
    out = lcd.TftOut(tft)  # one per subject: its kept strips live on its canvas
    for k in itertools.count():
        now = FRAME_MS * (k + 1)
        clock.frame(now)
        pressed, held = buttons(k, tap, hold, title, presses)
        with quiet:
            game.step(now, pressed, held)
            if pane:
                if k == row.show:
                    pane.show(now)
                ov.update(now)
            out.draw(game, us, ov)
        yield tft.image()


def write_sheet(images, path):
    """The images side by side, GAP px apart."""
    sheet = Image.new("RGB", (330 * len(images) - GAP, 240))
    for k, img in enumerate(images):
        sheet.paste(img, (330 * k, 0))
    sheet.save(path)


def write_gif(images, path, every):
    """Every every-th image as a GIF frame of every * FRAME_MS ms, looping, on one palette taken from PALETTE_FRAMES
    images spread over the run (a pit gains a colour with each pour)."""
    run = images[::every]
    spread = run[::max(1, len(run) // PALETTE_FRAMES)][:PALETTE_FRAMES]
    sample = Image.new("RGB", (320 * len(spread), 240))
    for k, img in enumerate(spread):
        sample.paste(img, (320 * k, 0))
    palette = sample.quantize(256)
    run = [img.quantize(palette=palette) for img in run]
    run[0].save(path, save_all=True, append_images=run[1:], duration=every * FRAME_MS, loop=0, optimize=True)


def main():
    parser = argparse.ArgumentParser(description="Draw a game, a scene or the overlay on the Mac, the board's way.")
    parser.add_argument("--list", action="store_true", help="print each subject's row and stop")
    parser.add_argument("--all", metavar="DIR", help="write every subject's PNG and GIF into DIR from its row")
    parser.add_argument("--filter", choices=sorted(FILTERS), help="a heat field's filter (P608)")
    press = parser.add_mutually_exclusive_group()
    press.add_argument("--tap", type=int, metavar="N", help="press on one frame in every N")
    press.add_argument("--hold", type=int, metavar="N", help="hold N frames, release N; 0 holds every frame")
    parser.add_argument("--title", action="store_true", help="no press on the first frame: the title shows")
    parser.add_argument("--seed", type=int, help="random's seed before the game is made (the row's, else 1)")
    text = parser.add_mutually_exclusive_group()
    text.add_argument("--font", default=FONT_PATH, metavar="PATH", help="font_petme128_8x8.h (default: %(default)s)")
    text.add_argument("--no-text", action="store_true", help="draw without letters")
    parser.add_argument("--gif", metavar="OUT.gif", help="also a GIF of the frames from the first count to the last")
    parser.add_argument("--every", type=int, metavar="K", help="the GIF keeps every K-th frame (default %d)" % EVERY)
    parser.add_argument("subject", nargs="?", choices=sorted(SUBJECTS))
    parser.add_argument("out", nargs="?", help="the PNG sheet, one frame per count")
    parser.add_argument("counts", type=int, nargs="*", metavar="FRAMES", help="the frames to show")
    args = parser.parse_args()
    if args.list:
        for name, row in SUBJECTS.items():
            print("%-14s %-24s %s" % (name, row.hint, row))
        return
    if not args.no_text:
        try:
            Font(args.font).install()
        except OSError:
            parser.error("no font at %s: build.sh clones it, or give --font PATH or --no-text" % args.font)
        except ValueError as e:
            parser.error("%s: give --font PATH or --no-text" % e)
    mag_filter = FILTERS[args.filter] if args.filter else None
    if args.all:
        given = [flag for flag, value in (("--tap", args.tap), ("--hold", args.hold), ("--title", args.title),
                                          ("--seed", args.seed), ("--gif", args.gif), ("--every", args.every))
                 if value is not None and value is not False]  # 0 is a seed
        if given or args.subject:
            parser.error("--all takes every setting from the SUBJECTS rows, not %s" % " ".join(given or [args.subject]))
        os.makedirs(args.all, exist_ok=True)
        for name, row in SUBJECTS.items():
            images = list(itertools.islice(frames(row, hold_ms=row.last * FRAME_MS), row.last))
            write_sheet([images[row.shot - 1]], os.path.join(args.all, name + ".png"))
            write_gif(images[row.first - 1:row.last], os.path.join(args.all, name + ".gif"), row.every)
            print(name)
        return
    if not (args.subject and args.out and args.counts):
        parser.error("SUBJECT, out.png and FRAMES... are needed (or --list, or --all DIR)")
    row, first, last = SUBJECTS[args.subject], min(args.counts), max(args.counts)
    if mag_filter is not None and not issubclass(row.game, fire.Fire):
        parser.error("--filter is a heat field's: fire, burningbodies or marshmallow")
    images = list(itertools.islice(frames(row, args.tap, args.hold, args.title, args.seed, mag_filter, last * FRAME_MS),
                                   last))
    write_sheet([images[n - 1] for n in args.counts], args.out)
    print(args.out)
    if args.gif:
        write_gif(images[first - 1:last], args.gif, args.every or EVERY)
        print(args.gif)


if __name__ == "__main__":
    main()
