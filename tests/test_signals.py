"""The game box's sound path on the Mac (P768): Signals, Bank, SoundCues, and App with a game that emits.
Run from the repository root: python3 -B -m unittest tests.test_signals. --- MVP (P768) ---"""

import os
import struct
import sys
import tempfile
import time
import unittest
from array import array

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
import arcade  # noqa: E402
import bank  # noqa: E402
import box_bank  # noqa: E402
import cues  # noqa: E402
import gfx  # noqa: E402
import signals  # noqa: E402
import sound  # noqa: E402

GAMES = os.path.join(os.path.dirname(HERE), "games")


class Out:
    def clear(self):
        pass

    def reset(self):
        pass

    def draw(self, game, us, overlay):
        pass


class Quiet(gfx.Game):
    name = "quiet"


class Loud(gfx.Game):
    name = "loud"
    cues = {"die": cues.Cue("low"), "jump": cues.Cue("high")}


class FakeBank:
    sounds = {"low": array("h", [1, 2, 3]), "high": array("h", [7, 8])}

    def get(self, name):
        return self.sounds[name]


def rendered(mixer, n=4):
    buf = array("h", [9] * n)
    mixer.render(buf)
    return list(buf)


class TestSignals(unittest.TestCase):
    def test_emit_calls_each_listener_of_the_name_with_the_value(self):
        s, seen = signals.Signals(), []
        s.listen("jump", lambda name, value: seen.append((1, name, value)))
        s.listen("jump", lambda name, value: seen.append((2, name, value)))
        s.listen("die", lambda name, value: seen.append((3, name, value)))
        s.emit("jump", 5)
        s.emit("nobody listens")
        self.assertEqual(seen, [(1, "jump", 5), (2, "jump", 5)])

    def test_clear_drops_the_listeners(self):
        s, seen = signals.Signals(), []
        s.listen("jump", lambda name, value: seen.append(name))
        s.clear()
        s.emit("jump")
        self.assertEqual(seen, [])

    def test_a_game_with_no_signals_emits_nothing_and_does_not_fail(self):
        game = Loud()
        game.emit("jump")
        game.die()
        self.assertEqual(game.state, gfx.OVER)


class TestBank(unittest.TestCase):
    def test_each_sound_is_its_own_samples(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bank.raw")
            with open(path, "wb") as f:
                f.write(struct.pack("<5h", 10, -20, 30, -32768, 32767))
            b = bank.Bank(path, {"a": (0, 2), "b": (2, 3)})
            self.assertEqual(list(b.get("a")), [10, -20])
            self.assertEqual(list(b.get("b")), [30, -32768, 32767])
            with self.assertRaises(ValueError):
                bank.Bank(path, {"long": (3, 3)})

    def test_the_box_bank_holds_every_sound_that_a_game_asks_for(self):
        b = bank.Bank(os.path.join(GAMES, "box_bank.raw"), box_bank.BOX_BANK_INDEX)
        self.assertEqual(os.path.getsize(os.path.join(GAMES, "box_bank.raw")),
                         2 * sum(n for _, n in box_bank.BOX_BANK_INDEX.values()))
        for game in app.GAMES:
            for cue in game.cues.values():
                self.assertTrue(len(b.get(cue.sound)), "%s: %s" % (game.name, cue.sound))


class TestSoundCues(unittest.TestCase):
    def box(self, *games):
        mixer = sound.Mixer()
        box = app.App(None, lambda: 99, lambda: 99, games=games, out=Out(), cues=cues.SoundCues(mixer, FakeBank()))
        box.start()
        return box, mixer

    def test_a_signal_with_a_cue_plays_its_sound(self):
        box, mixer = self.box(Loud)
        box.game.emit("jump")
        self.assertEqual(rendered(mixer), [7, 8, 0, 0])

    def test_die_plays_its_cue(self):
        box, mixer = self.box(Loud)
        box.game.die()
        self.assertEqual(rendered(mixer), [1, 2, 3, 0])

    def test_a_signal_with_no_cue_plays_nothing(self):
        box, mixer = self.box(Quiet)
        box.game.die()
        box.game.emit("jump")
        self.assertEqual(rendered(mixer), [0, 0, 0, 0])

    def test_a_switch_stops_the_sound_and_the_last_games_cues(self):
        box, mixer = self.box(Loud, Quiet)
        loud = box.game
        loud.emit("die")
        rendered(mixer, 2)  # the sound has begun
        box.switch()
        self.assertEqual(rendered(mixer), [0, 0, 0, 0])
        loud.emit("jump")  # the old game's listeners are gone
        box.game.emit("jump")
        self.assertEqual(rendered(mixer), [0, 0, 0, 0])

    def test_the_box_with_no_cues_is_silent_and_runs(self):
        box = app.App(None, lambda: 99, lambda: 99, games=(Loud,), out=Out())
        box.start()
        box.game.emit("jump")
        box.frame()
        self.assertIsNone(box.cues)
        self.assertIs(box.game.signals, box.signals)  # the game still emits, and nobody listens

    def test_the_runner_emits_jump_at_a_press_and_die_at_its_death(self):
        seen = []
        game = arcade.Runner()
        game.signals = signals.Signals()
        for name in game.cues:
            game.signals.listen(name, lambda name, value: seen.append(name))
        game.state, game.dt, game.t = gfx.PLAY, 0.04, 1.0
        game.play(True, False)
        self.assertEqual(seen, ["jump"])
        game.die()
        self.assertEqual(seen, ["jump", "die"])


if __name__ == "__main__":
    unittest.main()
