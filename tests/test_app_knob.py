"""The volume knob in the game box (P764) on the Mac, through App.frame itself: a fake encoder, a fake output and a
fake game. A turn of the knob makes the volume pane visible in the same frame, and with no knob there is no pane.
Run from the repository root: python3 -B -m unittest tests.test_app_knob. --- MVP (P764) ---"""

import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)
if not hasattr(time, "ticks_add"):
    time.ticks_add = lambda a, b: a + b

import app  # noqa: E402
import gfx  # noqa: E402
import volume  # noqa: E402


class Encoder:
    """take_detents gives the next of `turns`, then 0."""

    def __init__(self, *turns):
        self.turns = list(turns)

    def take_detents(self, now_ms):
        return self.turns.pop(0) if self.turns else 0


class Game:
    name, state = "fake", gfx.PLAY

    def step(self, now, pressed, held):
        pass


class Out:
    """The output: it records which panes were visible when the frame was drawn."""

    def __init__(self):
        self.seen = []

    def clear(self):
        pass

    def reset(self):
        pass

    def draw(self, game, us, overlay):
        self.seen.append([pane.visible for pane in overlay.panes])


def make(knob=None):
    box = app.App(None, lambda: 99, lambda: 99, games=(Game,), out=Out(), knob=knob)
    box.start()
    return box


class TestAppKnob(unittest.TestCase):
    def test_a_turn_shows_the_pane_in_the_same_frame(self):
        box = make(volume.VolumeKnob(Encoder(0, 1), volume.MasterVolume(8)))
        box.frame()
        box.frame()
        self.assertEqual(box.out.seen, [[False], [True]])
        self.assertEqual(box.knob.volume.step, 8 + volume.LOUDER)

    def test_no_turn_shows_nothing(self):
        box = make(volume.VolumeKnob(Encoder(), volume.MasterVolume(8)))
        box.frame()
        box.frame()
        self.assertEqual(box.out.seen, [[False], [False]])

    def test_the_pane_watches_the_knobs_volume(self):
        knob = volume.VolumeKnob(Encoder(), volume.MasterVolume(8))
        box = make(knob)
        self.assertIs(box.volume_pane.volume, knob.volume)
        self.assertEqual(box.overlay.panes, [box.volume_pane])

    def test_no_knob_makes_no_pane(self):
        box = make()
        box.frame()
        self.assertIsNone(box.volume_pane)
        self.assertEqual(box.overlay.panes, [])
        self.assertEqual(box.out.seen, [[]])

    def test_open_knob_is_none_without_machine_encoder(self):
        self.assertIsNone(app.open_knob())  # the Mac has no machine module


if __name__ == "__main__":
    unittest.main()
