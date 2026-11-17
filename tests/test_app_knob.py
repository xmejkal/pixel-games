"""The volume knob in the game box (P764) on the Mac, through App.frame itself: a fake encoder, a fake output and a
fake game. A turn of the knob makes the volume pane visible in the same frame, and with no knob there is no pane.
Run from the repository root: python3 -B -m unittest tests.test_app_knob. --- MVP (P764) ---"""

import os
import sys
import time
import unittest
from unittest import mock

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
import overlay  # noqa: E402
import volume  # noqa: E402
from engine.actions import ActionMap  # noqa: E402


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


class D14:
    """D14 as the action map binds it: update(now) is True while down is."""

    held, down = False, False

    def update(self, now_ms):
        return self.down

    def forget(self):
        pass


def make(knob=None, encoder=None):
    """A box with the knob, its encoder in the action map (P851) feeding the knob's turn."""
    box = app.App(None, ActionMap((), (), encoder), games=(Game,), out=Out(), knob=knob)
    box.start()
    return box


class TestAppKnob(unittest.TestCase):
    def test_a_turn_shows_the_pane_in_the_same_frame(self):
        box = make(volume.VolumeKnob(volume.MasterVolume(8)), Encoder(0, 1))
        box.frame()
        box.frame()
        self.assertEqual(box.out.seen, [[False], [True]])
        self.assertEqual(box.knob.volume.step, 8 + volume.LOUDER)

    def test_no_turn_shows_nothing(self):
        box = make(volume.VolumeKnob(volume.MasterVolume(8)), Encoder())
        box.frame()
        box.frame()
        self.assertEqual(box.out.seen, [[False], [False]])

    def test_the_pane_watches_the_knobs_volume(self):
        knob = volume.VolumeKnob(volume.MasterVolume(8))
        box = make(knob, Encoder())
        self.assertIs(box.volume_pane.volume, knob.volume)
        self.assertEqual(box.overlay.panes, [box.volume_pane])

    def test_no_knob_makes_no_pane(self):
        box = make()
        box.frame()
        self.assertIsNone(box.volume_pane)
        self.assertEqual(box.overlay.panes, [])
        self.assertEqual(box.out.seen, [[]])

    def test_a_pane_updates_after_the_switch(self):
        class Other(Game):
            name = "other"

        class Watch(overlay.Pane):
            def update(self, now_ms):
                names.append(box.game.name)
                games.append(box.game)

        names, games, d14 = [], [], D14()
        box = app.App(None, ActionMap((), (d14,)), games=(Game, Other), out=Out())
        box.start()
        box.overlay.add(Watch())
        d14.down = True  # a D14 press in this frame: a pick (P818)
        box.frame()
        self.assertEqual(names, ["other"])  # the NameCard of the picked game
        self.assertIsInstance(box.game, app.NameCard)
        d14.down = False
        with mock.patch.object(app, "SETTLE_MS", 0):  # the pick settles in the next frame
            box.frame()
            for _ in range(10):  # and the build ends behind the card (P822)
                if not isinstance(box.game, app.NameCard):
                    break
                box.frame()
        self.assertNotIsInstance(box.game, app.NameCard)
        self.assertIsInstance(box.game, Other)
        self.assertEqual(["other"] * len(names), names)  # the card of the picked game, then the game
        self.assertLess(2, len(games))  # the pick's frame, the settle's and the build's
        self.assertTrue(all(isinstance(game, app.NameCard) for game in games[:-1]), games)
        self.assertIs(box.game, games[-1])  # the pane saw the built game in the frame it was built

    def test_a_byte_that_is_no_utf8_is_read_as_a_byte_and_the_loop_goes_on(self):
        """A knob turn on the RX pad types noise into the console (P850, found on the board by the PO's knob turn).
        MicroPython's text stdin takes 0xFF or 0x80 as the start of a 5-byte character and waits for 4 more bytes,
        then raises UnicodeError: the loop reads one byte from stdin.buffer, which never decodes nor waits."""

        class Console:
            def poll(self, timeout):
                return True

        class Bytes:
            def __init__(self, *reads):
                self.reads = list(reads)

            def read(self, n):
                return self.reads.pop(0)[:n]

        class TextStdin:
            def __init__(self, *reads):
                self.buffer = Bytes(*reads)

            def read(self, n):
                raise AssertionError("the text read waits for the rest of a character that never comes")

        stdin = TextStdin(b"\xff", b"\x80", b"a")
        for _ in range(3):
            app.read_console(Console(), stdin)
        self.assertEqual([], stdin.buffer.reads)

    def test_nothing_is_read_when_the_console_is_quiet(self):
        class Quiet:
            def poll(self, timeout):
                return False

        app.read_console(Quiet(), None)  # no read: stdin is not touched

    def test_run_s_loop_reads_the_console_through_read_console(self):
        import ast
        import inspect

        calls = [n.func.id for n in ast.walk(ast.parse(inspect.getsource(app.run)))
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertIn("read_console", calls)
        self.assertNotIn("sys.stdin.read(", inspect.getsource(app.run))

    def test_open_knob_is_none_without_machine_encoder(self):
        self.assertIsNone(app.open_knob(volume.MasterVolume))  # the Mac has no machine module


if __name__ == "__main__":
    unittest.main()
