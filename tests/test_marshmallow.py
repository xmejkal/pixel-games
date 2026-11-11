"""games/marshmallow.py on the Mac (P773): the Roast's rules, the two flames, and the game with no engine and on the
ctypes stand-in for engine.HeatField of test_fire.py. Run from the repository root: python3 -m unittest discover tests.
--- MVP (P773) ---"""

import contextlib
import io
import shutil
import sys
import unittest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import test_fire  # noqa: E402  (puts games/ and stubs/ on the path)
from test_fire import Engine, Recorder, Tft  # noqa: E402

import cues  # noqa: E402
import fire  # noqa: E402
import gfx  # noqa: E402
import lcd  # noqa: E402
import marshmallow as mm  # noqa: E402
import signals  # noqa: E402
from marshmallow import BURN, DARK, GOLDEN, LATE, SERVE, WHITE, Roast  # noqa: E402

FLAME_TOP = gfx.HEIGHT - mm.BOTTOM_Y  # a flame whose top is the marshmallow's bottom edge at depth 0: under is 0 there


def roast_at(depth, browned=0):
    roast = Roast()
    roast.depth, roast.browned = depth, browned
    return roast


class RoastTest(unittest.TestCase):
    def test_held_lowers_it_and_released_lifts_it_in_whole_px(self):
        roast = Roast()
        for _ in range(10):
            roast.update(100, True, 0)
        self.assertEqual(mm.LOWER_PX_S, roast.depth)  # one second held
        for _ in range(5):
            roast.update(100, False, 0)
        self.assertEqual(mm.LOWER_PX_S - mm.LIFT_PX_S // 2, roast.depth)  # half a second released
        roast.update(7, True, 0)  # 7 ms is under a pixel: the rest is carried, not lost
        roast.update(7, True, 0)
        self.assertEqual(mm.LOWER_PX_S - mm.LIFT_PX_S // 2 + mm.LOWER_PX_S * 14 // 1000, roast.depth)

    def test_depth_stays_between_the_top_and_the_deepest_place(self):
        roast = Roast()
        roast.update(60, False, 0)
        self.assertEqual(0, roast.depth)
        for _ in range(100):
            roast.update(60, True, 0)
        self.assertEqual(mm.DEPTH_MAX, roast.depth)
        roast.update(60, False, 0)  # lifting from the stop starts at once: no debt is carried
        self.assertEqual(mm.DEPTH_MAX - mm.LIFT_PX_S * 60 // 1000, roast.depth)

    def test_under_is_the_px_of_the_bottom_edge_below_the_flame_top_and_never_negative(self):
        roast = roast_at(50)
        roast.update(10, True, FLAME_TOP + 20)  # 1 px lower, 51: the flame top is 20 px above the edge's y at depth 0
        self.assertEqual(10 * (51 + 20), roast.browned)
        roast = roast_at(50)
        roast.update(10, True, FLAME_TOP - 100)  # a flame far below the bottom edge
        self.assertEqual(0, roast.browned)

    def test_browned_grows_by_under_times_ms(self):
        roast = roast_at(100)
        roast.update(40, False, gfx.HEIGHT)  # a flame to the top of the screen: under is the whole bottom edge's y
        depth = roast.depth  # 100 - 8 px lifted
        self.assertEqual(40 * (mm.BOTTOM_Y + depth), roast.browned)

    def test_the_colour_is_white_then_golden_then_dark_from_half_of_the_way_to_black(self):
        half = (mm.GOLDEN_AT + mm.BLACK_AT + 1) // 2
        for browned, colour in ((0, WHITE), (mm.GOLDEN_AT - 1, WHITE), (mm.GOLDEN_AT, GOLDEN), (half - 1, GOLDEN),
                                (half, DARK), (mm.BLACK_AT - 1, DARK)):
            self.assertEqual(colour, roast_at(0, browned).colour(), browned)

    def test_black_is_a_burn_a_lost_one_and_a_white_one_at_the_top(self):
        roast = roast_at(100, mm.BLACK_AT - 1)
        roast.age = 500
        self.assertEqual(BURN, roast.update(40, True, gfx.HEIGHT))
        self.assertEqual((1, 0, 0, 0, WHITE), (roast.lost, roast.depth, roast.browned, roast.age, roast.colour()))

    def test_a_hold_with_no_end_burns_one_after_the_other(self):
        roast = Roast()
        outcomes = [roast.update(40, True, mm.FLAME_MAX_PX) for _ in range(1000)]
        self.assertGreaterEqual(outcomes.count(BURN), mm.LIVES)
        self.assertEqual(0, outcomes.count(SERVE))

    def test_each_served_one_brings_black_nearer_down_to_the_least(self):
        roast = Roast()
        self.assertEqual(mm.BLACK_AT, roast.black_at())
        roast.served = 3
        self.assertEqual(mm.BLACK_AT - 3 * mm.BLACK_STEP, roast.black_at())
        roast.browned, roast.depth = roast.black_at() - 1, 100
        self.assertEqual(BURN, roast.update(40, True, gfx.HEIGHT))  # under the first limit, over this one
        roast.served = 1000
        self.assertEqual(mm.BLACK_MIN, roast.black_at())
        self.assertGreater(mm.BLACK_MIN, mm.GOLDEN_AT)

    def test_a_marshmallow_whose_time_ran_out_is_late_and_lost(self):
        roast = Roast()
        outcomes = [roast.update(40, False, 0) for _ in range(mm.TIME_MS // 40)]
        self.assertEqual([None] * (len(outcomes) - 1) + [LATE], outcomes)
        self.assertEqual((1, 0), (roast.lost, roast.age))

    def test_each_served_one_shortens_the_time_down_to_the_least(self):
        roast = Roast()
        self.assertEqual(mm.TIME_MS, roast.time_ms())
        roast.served = 2
        self.assertEqual(mm.TIME_MS - 2 * mm.TIME_STEP_MS, roast.time_ms())
        roast.served = 1000
        self.assertEqual(mm.TIME_MIN_MS, roast.time_ms())

    def test_the_least_time_is_enough_for_the_way_down_and_up(self):
        way = mm.DEPTH_MAX * 1000 // mm.LOWER_PX_S + mm.DEPTH_MAX * 1000 // mm.LIFT_PX_S
        self.assertGreater(mm.TIME_MIN_MS, way)

    def test_a_golden_one_at_the_top_is_served_and_a_white_one_comes(self):
        roast = roast_at(1, mm.GOLDEN_AT)
        self.assertEqual(SERVE, roast.update(40, False, FLAME_TOP))
        self.assertEqual((0, 0, WHITE, 0), (roast.depth, roast.browned, roast.colour(), roast.lost))
        self.assertEqual((1, 0), (roast.served, roast.age))  # a new time for the white one

    def test_a_white_one_at_the_top_is_neither(self):
        roast = roast_at(1, mm.GOLDEN_AT - 1)
        self.assertIsNone(roast.update(40, False, FLAME_TOP))
        self.assertEqual(mm.GOLDEN_AT - 1, roast.browned)  # it keeps what it had

    def test_the_highest_flame_never_reaches_a_marshmallow_at_the_top(self):
        self.assertLessEqual(gfx.HEIGHT - mm.FLAME_MAX_PX, mm.BOTTOM_Y)
        roast = Roast()
        roast.update(60, False, mm.FLAME_MAX_PX)
        self.assertEqual(0, roast.browned)

    def test_lift_speed_saves_a_golden_one_from_the_deepest_place_under_the_highest_flame(self):
        """By the constants, for the first marshmallows: lifting from DEPTH_MAX at a still flame of FLAME_MAX_PX adds
        under_max squared over twice the lift speed (px times ms), and golden plus that stays under the first black.
        Under BLACK_MIN it does not: late in a round the deepest place under the highest flame is a burn."""
        under_max = mm.BOTTOM_Y + mm.DEPTH_MAX - (gfx.HEIGHT - mm.FLAME_MAX_PX)
        self.assertGreater(under_max, 0)
        extra = under_max * under_max * 1000 // (2 * mm.LIFT_PX_S)
        self.assertLess(mm.GOLDEN_AT + extra, mm.BLACK_AT)
        self.assertGreater(mm.GOLDEN_AT + extra, mm.BLACK_MIN)
        for ms in (40, 60):  # and by steps of the longest frame, with the rounding of whole px
            roast = roast_at(mm.DEPTH_MAX, mm.GOLDEN_AT)
            outcomes = []
            while roast.depth:
                outcomes.append(roast.update(ms, False, mm.FLAME_MAX_PX))
            self.assertEqual([None] * (len(outcomes) - 1) + [SERVE], outcomes, ms)


class FakeField:
    """Records the burns, answers a set stats(): (total, height in cells)."""

    def __init__(self):
        self.burns, self.thresholds, self.height = [], [], 0

    def burn(self, *args):
        self.burns.append(args)

    def stats(self, threshold):
        self.thresholds.append(threshold)
        return 0, self.height


class FakePlugin:
    """A FirePlugin that stepped (step_us) or not, with a field that is a FakeField."""

    def __init__(self):
        self.field, self.step_us, self.drawn = FakeField(), 0, 0

    def take_step_us(self):
        us, self.step_us = self.step_us, 0
        return us

    def draw(self, cv):
        self.drawn += 1


class WaveTest(unittest.TestCase):
    def heats(self, wild, ms=40, frames=200):
        flame = mm.PlainFlame()
        out = []
        for _ in range(frames):
            flame.update(ms, wild)
            out.append(flame.top_px + mm.PLAIN_PX)
        return out

    def test_the_heat_swings_between_the_low_and_the_high_heat_of_the_wild(self):
        for wild in (0, 3, mm.WILD_MAX):
            heats = self.heats(wild)
            self.assertEqual((mm.HEAT_LOW, mm.HEAT_HIGH + wild * mm.HEAT_WILD), (min(heats), max(heats)), wild)

    def test_a_wilder_campfire_swings_faster(self):
        def crossings(wild):  # how often the heat passes the middle going up, in 20 s
            heats = self.heats(wild, frames=500)
            mid = (mm.HEAT_LOW + mm.HEAT_HIGH + wild * mm.HEAT_WILD) // 2
            return sum(1 for a, b in zip(heats, heats[1:]) if a < mid <= b)
        self.assertLess(crossings(0), crossings(mm.WILD_MAX))
        self.assertEqual(20000 // mm.WAVE_MS, crossings(0))

    def test_a_reset_starts_the_wave_again(self):
        flame = mm.PlainFlame()
        flame.update(1000, 0)
        first = flame.top_px
        flame.reset()
        flame.update(1000, 0)
        self.assertEqual(first, flame.top_px)

    def test_the_plain_flame_is_the_heat_less_plain_px_and_is_drawn_as_three_bars_that_get_shorter(self):
        flame = mm.PlainFlame()
        flame.update(40, 0)
        heat = mm.HEAT_LOW + (mm.HEAT_HIGH - mm.HEAT_LOW) * 40 // (mm.WAVE_MS // 2)
        self.assertEqual(heat - mm.PLAIN_PX, flame.top_px)
        cv = Recorder(Tft())
        flame.draw(cv)
        self.assertEqual(3, len(cv.fills))
        tops = [y for _, y, _, _ in cv.fills]
        self.assertEqual(sorted(tops), tops)
        self.assertEqual(gfx.HEIGHT - flame.top_px, tops[0])
        self.assertTrue(all(y + h == gfx.HEIGHT for _, y, _, h in cv.fills))

    def test_the_plain_flame_stays_inside_the_highest_flame_the_roast_trusts(self):
        top = mm.HEAT_HIGH + mm.WILD_MAX * mm.HEAT_WILD - mm.PLAIN_PX
        self.assertLessEqual(top, mm.FLAME_MAX_PX)


class CampfireTest(unittest.TestCase):
    def test_each_frame_burns_a_line_at_the_bottom_middle_at_the_waves_heat(self):
        plugin = FakePlugin()
        flame = mm.Campfire(plugin)
        flame.update(40, 0)
        flame.update(40, 0)
        y = fire.H - 1 - mm.BURN_RADIUS
        x0, x1 = fire.W // 2 - mm.BURN_HALF, fire.W // 2 + mm.BURN_HALF
        heat = mm.HEAT_LOW + (mm.HEAT_HIGH - mm.HEAT_LOW) * 40 // (mm.WAVE_MS // 2)
        self.assertEqual((x0, y, x1, y, mm.BURN_RADIUS, heat), plugin.field.burns[0])
        self.assertEqual(2, len(plugin.field.burns))
        self.assertGreater(plugin.field.burns[1][5], heat)  # the wave rises

    def test_the_height_is_read_only_after_a_step_in_px_and_cut_at_the_highest_flame(self):
        plugin = FakePlugin()
        flame = mm.Campfire(plugin)
        plugin.field.height = 50
        flame.update(40, 0)  # the field did not step: no read
        self.assertEqual(([], 0), (plugin.field.thresholds, flame.top_px))
        plugin.step_us = 450
        flame.update(40, 0)
        self.assertEqual(([mm.THRESHOLD], 100), (plugin.field.thresholds, flame.top_px))
        flame.update(40, 0)  # the step was taken: no second read
        self.assertEqual(1, len(plugin.field.thresholds))
        plugin.field.height, plugin.step_us = 120, 450  # 240 px, the whole field
        flame.update(40, 0)
        self.assertEqual(mm.FLAME_MAX_PX, flame.top_px)

    def test_it_draws_through_the_plugin(self):
        plugin = FakePlugin()
        mm.Campfire(plugin).draw(Recorder(Tft()))
        self.assertEqual(1, plugin.drawn)


def run(game, now, frames, hold, pressed_first=False):
    """frames frames of 40 ms from now, or until the round is over. hold(game) says whether BOOT is down. The first
    frame may be a tap. Answers the last frame's time."""
    for k in range(frames):
        now += test_fire.FRAME_MS
        game.step(now, pressed_first and k == 0, hold(game))
        if game.state == gfx.OVER:
            break
    return now


def cook(game):
    """Hold while the marshmallow is white: it comes up golden and is lifted."""
    return game.roast.colour() == WHITE


def burn_them(game):
    """A hold with no end: every marshmallow goes black."""
    return True


def idle(game):
    return False


class Log:
    """A signals.Signals with every signal of the cues noted as (name, value)."""

    def __init__(self, game):
        self.log, self.signals = [], signals.Signals()
        for name in ("serve", "burn", "flame", "die"):
            self.signals.listen(name, lambda n, v: self.log.append((n, v)))
        game.signals = self.signals

    def names(self):
        return [n for n, _ in self.log]


class MarshmallowNoEngineTest(unittest.TestCase):
    def setUp(self):
        fire.engine = None
        with contextlib.redirect_stdout(io.StringIO()):
            self.game = mm.Marshmallow()
        self.log = Log(self.game)

    def test_it_is_a_scene_on_fire_with_one_mode_a_title_and_a_plain_flame(self):
        game = self.game
        self.assertIsInstance(game, fire.Fire)
        self.assertEqual(("marshmallow", "hold to roast", gfx.Game.TITLE_MS), (game.name, game.hint, game.TITLE_MS))
        self.assertEqual(1, len(game.MODES))
        self.assertIsInstance(game.flame, mm.PlainFlame)
        self.assertFalse(game.covers)
        self.assertEqual({"serve", "burn", "die", "flame"}, set(game.cues))
        self.assertTrue(game.cues["flame"].loop)

    def test_a_whole_round_to_a_death_by_three_lost_marshmallows(self):
        game = self.game
        run(game, 0, 3000, burn_them, pressed_first=True)
        self.assertEqual(gfx.OVER, game.state)
        self.assertEqual((mm.LIVES, 0), (game.roast.lost, game.score))
        self.assertEqual(mm.LIVES, self.log.names().count("burn"))
        self.assertEqual(1, self.log.names().count("die"))
        self.assertEqual(0, self.log.names().count("serve"))

    def test_a_player_who_does_nothing_loses_by_the_time(self):
        game = self.game
        now = run(game, 0, 3000, idle, pressed_first=True)
        self.assertEqual(gfx.OVER, game.state)
        self.assertEqual((mm.LIVES, 0), (game.roast.lost, game.score))
        self.assertEqual(mm.LIVES * mm.TIME_MS, now - test_fire.FRAME_MS)  # the first frame is the tap
        self.assertEqual(mm.LIVES, self.log.names().count("burn"))  # a late one sounds as a burnt one

    def test_flame_0_is_emitted_just_before_the_death(self):
        run(self.game, 0, 3000, burn_them, pressed_first=True)
        self.assertEqual([("burn", None), ("flame", 0), ("die", None)], self.log.log[-3:])

    def test_a_cooked_one_is_a_point_and_the_campfire_gets_wilder(self):
        game = self.game
        seen = []
        real = game.flame.update
        game.flame.update = lambda ms, wild: (seen.append(wild), real(ms, wild))[1]
        now = run(game, 0, 600, cook, pressed_first=True)
        self.assertGreaterEqual(game.score, 2)
        self.assertEqual(game.score, self.log.names().count("serve"))
        self.assertEqual(min(game.score, mm.WILD_MAX), seen[-1])
        game.score = 9
        run(game, now, 3, cook)
        self.assertEqual(mm.WILD_MAX, seen[-1])

    def test_the_flame_signal_carries_the_level_when_it_moved_by_a_step(self):
        run(self.game, 0, 200, cook, pressed_first=True)
        levels = [v for n, v in self.log.log if n == "flame"]
        self.assertTrue(levels)
        self.assertTrue(all(0 <= v <= cues.LEVELS for v in levels))
        self.assertTrue(all(abs(a - b) >= mm.FLAME_STEP for a, b in zip(levels, levels[1:])), levels)

    def test_a_new_round_starts_a_new_roast_and_a_silent_flame(self):
        game = self.game
        now = run(game, 0, 3000, burn_them, pressed_first=True)
        before = game.flame
        n = len(self.log.log)
        game.step(now + 1000, True, False)  # past OVER_MS
        self.assertEqual(gfx.PLAY, game.state)
        self.assertIs(before, game.flame)
        self.assertEqual((0, 0, 0), (game.roast.lost, game.roast.depth, game.score))
        self.assertEqual(("flame", 0), self.log.log[n])

    def test_the_hud_key_holds_the_lost_ones(self):
        keys = []

        class Cv:
            def keep(self, key, rect, draw, alpha=255):
                keys.append((key, rect))

        game = self.game
        game.hud(Cv())
        game.roast.lost = 2
        game.hud(Cv())
        self.assertEqual(0, keys[0][0][-1])
        self.assertEqual(2, keys[1][0][-1])
        self.assertEqual((gfx.HUD_RECT, gfx.HUD_RECT), (keys[0][1], keys[1][1]))

    def test_the_title_the_play_and_the_game_over_draw_without_an_error(self):
        game = self.game
        for steps in (0, 3, 3000):
            if steps:
                run(game, 0, steps, burn_them, pressed_first=True)
            tft = Tft()
            game.draw(lcd.TftCanvas(tft))
            self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame), game.state)
        self.assertEqual(gfx.OVER, game.state)

    def test_the_marshmallow_is_drawn_at_its_depth(self):
        game = self.game
        game.roast.depth, game.roast.browned = 100, mm.GOLDEN_AT
        cv = Recorder(Tft())
        cv.box = lambda *args: None
        game.paint(cv)
        self.assertIn((mm.CENTRE - mm.SIZE // 2, mm.BOTTOM_Y - mm.SIZE + 100, mm.SIZE, mm.SIZE), cv.fills)

    def test_the_time_bar_shrinks_with_the_marshmallows_age(self):
        game = self.game

        def bar():
            cv = Recorder(Tft())
            cv.box = lambda *args: None
            game.paint(cv)
            return cv.fills[-1][2]

        self.assertEqual(mm.TIME_BAR_PX, bar())
        game.roast.age = mm.TIME_MS // 2
        self.assertEqual(mm.TIME_BAR_PX // 2, bar())


@unittest.skipUnless(shutil.which("clang"), "clang is missing: engine/core/fx_fire.c is not built")
class MarshmallowEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_fire.FireTest.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        fire.engine = Engine(self.lib)
        self.base = []
        field = fire.engine.HeatField
        set_base = field.set_base
        field.set_base = lambda f, on: (self.base.append(on), set_base(f, on))[1]
        with contextlib.redirect_stdout(io.StringIO()):
            self.game = mm.Marshmallow()
        self.log = Log(self.game)

    def tearDown(self):
        fire.engine = None

    def test_the_game_has_a_campfire_on_the_field_with_its_base_off(self):
        game = self.game
        self.assertIsInstance(game.flame, mm.Campfire)
        self.assertEqual([False], self.base)
        self.assertEqual([mm.LOOK], fire.engine.looks)

    def test_the_title_gets_its_fill_and_the_field_covers_the_screen_in_play(self):
        game = self.game
        self.assertFalse(game.covers)
        game.step(0, True, False)  # the tap leaves the title
        game.step(40, False, False)
        self.assertTrue(game.covers)

    def test_no_fixed_rhythm_of_hold_and_release_plays_on(self):
        """The refuter's find (P773): with no time limit and a fixed black, a player who never looked scored with no
        end. The rhythms here are the ones that scored best then. The plain flame is not held to this: it is even,
        and 4 of 175 rhythms still played on for 10 minutes there (Mac trial)."""
        import random
        random.seed(773)
        best = 0
        for release in (25, 30):  # frames
            for hold in range(36, 58, 4):
                with contextlib.redirect_stdout(io.StringIO()):
                    game = mm.Marshmallow()
                period = hold + release
                frame = [0]

                def rhythm(game):
                    frame[0] += 1
                    return frame[0] % period < hold

                run(game, 0, 7500, rhythm, pressed_first=True)  # 5 minutes
                self.assertEqual(gfx.OVER, game.state, (hold, release, game.score))
                best = max(best, game.score)
        self.assertLess(best, 40)

    def test_one_field_over_two_rounds_it_burns_and_the_signals_come(self):
        game = self.game
        field = game.fire_plugin.field
        now = run(game, 0, 3000, burn_them, pressed_first=True)
        self.assertEqual(gfx.OVER, game.state)
        self.assertEqual(mm.LIVES, self.log.names().count("burn"))
        self.assertEqual([("flame", 0), ("die", None)], self.log.log[-2:])
        burns = len(fire.engine.burns)
        self.assertGreater(burns, 0)
        self.assertEqual((fire.W // 2 - mm.BURN_HALF, fire.W // 2 + mm.BURN_HALF),
                         (fire.engine.burns[0][0], fire.engine.burns[0][2]))
        game.step(now + 1000, True, False)  # past OVER_MS: a new round
        self.assertEqual(gfx.PLAY, game.state)
        self.assertIs(field, game.fire_plugin.field)  # the same field: the round did not make a new one
        self.assertTrue(any(bytes(field.heat[:fire.W * fire.H])))  # and it did not start cold
        run(game, now + 1000, 600, cook)
        self.assertGreater(len(fire.engine.burns), burns)
        self.assertGreaterEqual(game.score, 1)
        self.assertGreaterEqual(self.log.names().count("serve"), 1)
        self.assertEqual([False], self.base)  # set_base(False) once, not each round
        self.assertEqual([mm.LOOK], fire.engine.looks)
        self.assertTrue(all(0 <= v <= cues.LEVELS for n, v in self.log.log if n == "flame"))

    def test_the_campfire_rises_into_the_range_the_rules_trust_and_is_drawn(self):
        game = self.game
        now = run(game, 0, 200, lambda g: False, pressed_first=True)
        tops = []
        for _ in range(200):
            now = run(game, now, 1, lambda g: False)
            tops.append(game.flame.top_px)
        self.assertTrue(min(tops) > 0 and max(tops) <= mm.FLAME_MAX_PX, (min(tops), max(tops)))
        tft = Tft()
        game.draw(lcd.TftCanvas(tft))
        self.assertEqual({"tft"}, set(fire.engine.targets))
        self.assertNotEqual(bytes(len(tft.frame)), bytes(tft.frame))


if __name__ == "__main__":
    unittest.main()
