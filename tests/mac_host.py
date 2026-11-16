"""The Mac's host (P846): what runs the games on the Mac in place of the box, as TIC-80, 32blit and Thumby Color run
theirs. MacHost holds the stand-in display (drawing_tft.DrawingTft), the frame clock (FrameClock) and the C engines
through clang (engines). buttons is the press script, and CueRecorder the Signals that keeps every emit.
tools/render_scene.py and tests/net.py run their frames on it. --- MVP (P846) ---"""

import hashlib
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "engine", "tests"))  # pixel-engine: clang_lib, balls_lib, world_lib
from drawing_tft import DrawingTft  # noqa: E402  first: it puts games/ and the stubs on the path
from clang_lib import S3LCD_SRC, build, core  # noqa: E402
from test_fire import Engine  # noqa: E402

FRAME_MS = 40  # app.py's FRAME_MS


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


def modules():
    """The game box's modules that the host and the net use, by their role, imported here and nowhere else in the
    net: a stage that moves a module edits this one function. The games' modules are among them, for the negative
    tests' patches."""
    import app
    import arcade
    import arcade2
    import balls
    import balls_lib
    import bank
    import box_bank
    import catalog
    import cues
    import fire
    import gfx
    import lcd
    import pictures
    import plugins
    import signals
    import sound
    import volume
    import world_lib

    return types.SimpleNamespace(app=app, arcade=arcade, arcade2=arcade2, balls=balls, balls_lib=balls_lib, bank=bank,
                                 box_bank=box_bank, catalog=catalog, cues=cues, fire=fire, gfx=gfx, lcd=lcd,
                                 pictures=pictures, plugins=plugins, signals=signals, sound=sound, volume=volume,
                                 world_lib=world_lib)


def engines():
    """The C engines the board has, through ctypes: the heat field, the balls and the bodies."""
    m = modules()
    m.fire.engine = Engine(build(core("fx_fire"), ("-I", S3LCD_SRC)))
    m.balls.engine, m.plugins.engine = m.balls_lib.engine(), m.world_lib.engine()
    m.pictures.ROOT = os.path.join(ROOT, "games", "")  # the board's /packs/... is games/packs/... here


class CueRecorder:
    """A fresh Signals, as App hands one to a game (app.py's play), that keeps (frame, name, value) of every emit.
    frame is the host's frame number, 1 for the first."""

    def __init__(self):
        self.signals, self.frame, self.heard = modules().signals.Signals(), 0, []

    def listen(self, name, listener):
        self.signals.listen(name, listener)

    def clear(self):
        self.signals.clear()

    def emit(self, name, value=None):
        self.heard.append((self.frame, name, value))
        self.signals.emit(name, value)


class MacHost:
    """The box stood in on the Mac: the display (tft), the clock (clock) and, once started, the C engines. frame(k)
    sets the clock to frame k's time, FRAME_MS apart from the first at FRAME_MS; digest() is the sha256 of the frame
    the panel holds, its native uint16 pixels in the panel's byte order."""

    def __init__(self):
        self.clock, self.tft = FrameClock(), DrawingTft()

    def start(self):
        self.clock.install()
        engines()
        return self

    def frame(self, k):
        now = FRAME_MS * (k + 1)
        self.clock.frame(now)
        return now

    def digest(self):
        return hashlib.sha256(self.tft.frame).hexdigest()
