"""A D14 press picks (P818) on the Mac, through App.frame itself with a clock the test sets: the game goes and a
NameCard shows the next name, nothing is imported or loaded, and the picked game is built once the pick settles
(SETTLE_MS with no press, or a BOOT press, which is used up). The cues stop at a pick and the music plays on, and the
knob's pane works over a NameCard. Run from the repository root: python3 -B -m unittest tests.test_pick.
--- MVP (P818) ---"""

import contextlib
import io
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_app_knob import Encoder  # noqa: E402  also puts games/ and the stubs on the path, and time's ticks
from test_signals import Loud, MusicBank, rendered  # noqa: E402

import app  # noqa: E402
import catalog  # noqa: E402
import cues  # noqa: E402
import gfx  # noqa: E402
import pictures  # noqa: E402
import sound  # noqa: E402
import volume  # noqa: E402

BUILT = []  # each counting game's name, as it is built


def counting(name):
    class Counting(gfx.Game):
        presses = None

        def setup(self):
            if self.presses is None:
                BUILT.append(self.name)
                self.presses = []

        def step(self, now_ms, pressed, held):
            self.presses.append(pressed)

    Counting.name = name
    return Counting


GAMES = tuple(counting(n) for n in "abcdef")


class Out:
    def __init__(self):
        self.resets, self.seen = 0, []

    def clear(self):
        pass

    def reset(self):
        self.resets += 1

    def draw(self, game, us, overlay):
        self.seen.append([pane.visible for pane in overlay.panes])


class Box:
    """An App on a clock the test sets, with D14 and BOOT pressed when the test says."""

    def __init__(self, games=GAMES, **kw):
        self.ms, self.d14, self.boot = 0, False, False
        self.clock = mock.patch.object(app.time, "ticks_ms", lambda: self.ms)
        self.clock.start()
        self.said = io.StringIO()
        with contextlib.redirect_stdout(self.said):
            self.app = app.App(None, lambda: 99, lambda: 99, games=games, out=Out(), **kw)
            self.app.fire.update = lambda now: self.boot
            self.app.boot.update = lambda now: self.d14
            self.app.start()

    def frame(self, ms, d14=False, boot=False):
        self.ms, self.d14, self.boot = ms, d14, boot
        with contextlib.redirect_stdout(self.said):
            self.app.frame()
        return self.app.game

    def lines(self, word):
        return [line for line in self.said.getvalue().splitlines() if line.split()[0] == word]

    def close(self):
        self.clock.stop()


class PickTest(unittest.TestCase):
    def setUp(self):
        BUILT.clear()
        self.box = Box()
        self.addCleanup(self.box.close)

    def test_four_presses_in_a_row_build_only_the_fifth_game(self):
        box = self.box
        for k in range(4):
            box.frame(100 * k, d14=True)
        self.assertEqual(["a"], BUILT)  # the first game, built by start(); nothing for the four picks
        game = box.frame(300 + app.SETTLE_MS)
        self.assertEqual(["a", "e"], BUILT)
        self.assertEqual("e", game.name)
        self.assertEqual(["pick b", "pick c", "pick d", "pick e"], box.lines("pick"))
        self.assertEqual(2, len(box.lines("switch")))  # start's and the settled pick's
        self.assertRegex(box.lines("switch")[1], r"^switch e \d+ ms, load \d+ ms, import \d+ ms$")

    def test_the_pick_settles_at_settle_ms_not_before(self):
        box = self.box
        box.frame(1000, d14=True)
        card = box.frame(1000 + app.SETTLE_MS - 1)
        self.assertIsInstance(card, app.NameCard)
        self.assertEqual(("b", gfx.TITLE), (card.name, card.state))
        self.assertEqual("b", box.frame(1000 + app.SETTLE_MS).name)
        self.assertEqual(["a", "b"], BUILT)

    def test_each_press_starts_the_wait_again(self):
        box = self.box
        box.frame(0, d14=True)
        box.frame(app.SETTLE_MS - 1, d14=True)
        self.assertIsInstance(box.frame(app.SETTLE_MS + 10), app.NameCard)
        self.assertEqual("c", box.frame(2 * app.SETTLE_MS - 1).name)

    def test_boot_on_a_card_builds_at_once_and_the_press_does_not_reach_the_game(self):
        box = self.box
        box.frame(0, d14=True)
        game = box.frame(10, boot=True)
        self.assertEqual("b", game.name)
        self.assertEqual([], game.presses)  # the build frame does not step the game
        box.frame(50)
        self.assertEqual([False], game.presses)
        self.assertEqual(gfx.TITLE, game.state)

    def test_the_pick_resets_the_output_and_the_card_shows_its_place(self):
        box = self.box
        before = box.app.out.resets
        card = box.frame(0, d14=True)
        self.assertEqual(before + 1, box.app.out.resets)
        self.assertEqual((2, 6), (card.n, card.count))

    def test_a_press_in_play_reaches_the_game(self):
        game = self.box.frame(0, boot=True)
        self.assertEqual([True], game.presses)


class CardTest(unittest.TestCase):
    def test_it_stays_in_title_loads_nothing_and_has_no_cues(self):
        with mock.patch.object(pictures, "load") as load:
            card = app.NameCard("snake", 3, 5)
            card.step(0, True, True)
            card.step(5000, True, False)
        load.assert_not_called()
        self.assertEqual((gfx.TITLE, {}), (card.state, card.cues))

    def test_it_draws_the_name_its_place_and_boot_plays(self):
        cv = gfx.Canvas()
        with mock.patch.object(cv, "big", wraps=cv.big) as big:
            app.NameCard("snake", 3, 5).draw_title(cv)
        self.assertEqual(["snake", "3 / 5"], [c.args[0] for c in big.call_args_list])
        self.assertIn("BOOT loads", [op[5] for op in cv.ops if op[4] == 3])


class NothingImportedTest(unittest.TestCase):
    def test_a_pick_imports_nothing_and_a_missing_module_is_refused_when_it_settles(self):
        ghost = {"ghost": ("ghost", "no_such_module_p818", "Ghost", ())}
        with mock.patch.dict(catalog.ROWS, ghost):
            box = Box(app.Lineup(("cave", "ghost")))
            self.addCleanup(box.close)
            self.assertEqual("ghost", box.frame(0, d14=True).name)  # the card: no import yet
            self.assertNotIn("refused", box.said.getvalue())
            self.assertEqual("cave", box.frame(app.SETTLE_MS).name)
        self.assertIn("game ghost refused", box.said.getvalue())


class SoundTest(unittest.TestCase):
    def test_a_pick_stops_the_games_cues_and_the_music_plays_on(self):
        mixer = sound.Mixer(2)
        box = Box((Loud, Loud), cues=cues.SoundCues(mixer, MusicBank()))
        self.addCleanup(box.close)
        loud, voice = box.app.game, box.app.cues.music_voice
        loud.emit("die")
        rendered(mixer, 1)
        box.frame(0, d14=True)
        self.assertEqual({}, box.app.cues.cues)
        loud.emit("jump")  # the old game's listeners are gone
        self.assertIs(box.app.cues.music_voice, voice)
        self.assertEqual(rendered(mixer), [6, 5, 6, 5])  # only the music


class KnobTest(unittest.TestCase):
    def test_the_volume_pane_shows_over_a_card(self):
        box = Box(knob=volume.VolumeKnob(Encoder(0, 1), volume.MasterVolume(8)))
        self.addCleanup(box.close)
        box.frame(0, d14=True)
        card = box.frame(10)
        self.assertIsInstance(card, app.NameCard)
        self.assertEqual([[False], [True]], box.app.out.seen)


if __name__ == "__main__":
    unittest.main()
