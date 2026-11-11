"""The system overlay (P762, P764) on the Mac: how long a pane shows, that panes show side by side, what VolumePane
paints and when it shows itself, and that both outputs draw the overlay after the game and send its area again in the
frame after it hides. framebuf comes from tests/stubs and
time gets the MicroPython ticks functions, as in test_hud.
Run from the repository root: python3 -B -m unittest tests.test_overlay. --- MVP (P764) ---"""

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

import gfx  # noqa: E402
import lcd  # noqa: E402
import overlay  # noqa: E402
import render  # noqa: E402
import volume  # noqa: E402

GAME_RECT = (4, 4, 10, 10)  # what the fake game draws, away from the overlay's RECT


class Count(overlay.Pane):
    """A pane that counts its draws, into a list that the test can share."""

    def __init__(self, name="pane", log=None):
        self.name, self.log = name, [] if log is None else log

    def draw(self, cv):
        self.log.append(self.name)


class Clip:
    """The least canvas that Overlay.draw asks for."""

    clip = None


class PaintCount(overlay.VolumePane):
    paints = levels = 0

    def paint(self, cv):
        self.paints += 1
        super().paint(cv)

    def paint_level(self, cv):
        self.levels += 1
        super().paint_level(cv)


def shown(step=8, now=0):
    """A VolumePane that is visible from now on, for HOLD_MS."""
    pane = overlay.VolumePane(volume.MasterVolume(step))
    pane.show(now)
    return pane


class Game:
    """The least that an output asks of a game: a still frame with one rectangle."""

    bg, covers, state = 0, False, gfx.PLAY

    def paint_static(self, cv):
        pass

    def draw(self, cv):
        cv.fill(*GAME_RECT, gfx.RED)


class Display:
    """The st7789 display of render.StOut: it keeps the rectangles of each blit."""

    def __init__(self):
        self.sent = []

    def blit(self, view, x, y, w, h):
        self.sent.append((x, y, w, h))


class Tft:
    """The s3lcd display of lcd.TftOut: it keeps the order of the calls that reach it."""

    def __init__(self):
        self.calls = []

    def track(self, on):
        pass

    def fill(self, c):
        self.calls.append("fill")

    def fill_rect(self, x, y, w, h, c):
        self.calls.append("fill_rect")

    def blit_buffer(self, buf, x, y, w, h, alpha=255, key=-1):
        self.calls.append(("blit", x, y, w, h, alpha))

    def show(self):
        self.calls.append("show")
        return 3


def covers(sent, rect):
    """True when the blitted rectangles cover each pixel of rect."""
    x, y, w, h = rect
    left = {(i, j) for i in range(x, x + w) for j in range(y, y + h)}
    for sx, sy, sw, sh in sent:
        left -= {(i, j) for i in range(max(sx, x), min(sx + sw, x + w)) for j in range(max(sy, y), min(sy + sh, y + h))}
    return not left


def touches(sent, rect):
    x, y, w, h = rect
    return any(sx < x + w and sx + sw > x and sy < y + h and sy + sh > y for sx, sy, sw, sh in sent)


class OverlayTest(unittest.TestCase):
    def test_a_pane_shows_for_hold_ms_after_show(self):
        layer, cv = overlay.Overlay(), Clip()
        pane = layer.add(Count())
        pane.show(5000)
        layer.update(5000 + overlay.HOLD_MS - 1)
        layer.draw(cv)
        self.assertEqual(len(pane.log), 1)
        self.assertEqual(cv.clip, gfx.FULL)  # the pane draws on the whole screen, whatever clip the game left
        layer.update(5000 + overlay.HOLD_MS)
        layer.draw(cv)
        self.assertEqual(len(pane.log), 1)
        self.assertFalse(pane.visible)

    def test_a_second_show_moves_the_end(self):
        layer = overlay.Overlay()
        pane = layer.add(Count())
        pane.show(5000)
        pane.show(5600)
        layer.update(5000 + overlay.HOLD_MS)
        self.assertTrue(pane.visible)
        layer.update(5600 + overlay.HOLD_MS)
        self.assertFalse(pane.visible)

    def test_each_pane_has_its_own_hold_ms(self):
        layer = overlay.Overlay()
        short, long = layer.add(Count()), layer.add(Count())
        long.hold_ms = 3 * overlay.HOLD_MS
        short.show(0)
        long.show(0)
        layer.update(overlay.HOLD_MS)
        self.assertEqual((short.visible, long.visible), (False, True))

    def test_two_panes_show_at_once_and_draw_in_the_order_of_add(self):
        layer, log = overlay.Overlay(), []
        first, second, hidden = (layer.add(Count(name, log)) for name in ("first", "second", "hidden"))
        second.show(0)
        first.show(0)
        layer.update(1)
        layer.draw(Clip())
        self.assertEqual(log, ["first", "second"])

    def test_a_pane_with_no_end_stays_visible(self):
        layer = overlay.Overlay()
        pane = layer.add(Count())
        pane.visible = True  # no show(): until stays None
        layer.update(1000 * overlay.HOLD_MS)
        layer.draw(Clip())
        self.assertEqual((pane.visible, len(pane.log)), (True, 1))

    def test_with_no_visible_pane_draw_does_nothing(self):
        layer = overlay.Overlay()
        layer.update(0)
        layer.draw(None)  # a canvas would raise here
        layer.add(Count())
        layer.update(0)
        layer.draw(None)


class VolumePaneTest(unittest.TestCase):
    def lit(self, step):
        cv, x, y = gfx.Canvas(), overlay.RECT[0], overlay.RECT[1]
        cv.start()
        overlay.VolumePane(volume.MasterVolume(step)).draw(cv)
        cells = [op for op in cv.ops if op[4] == 0 and (op[2] - op[0], op[3] - op[1]) == (6, 12)]
        self.assertEqual(len(cells), volume.STEPS)
        self.assertEqual([op[0] for op in cells], [x + 40 + 8 * i for i in range(volume.STEPS)])
        self.assertTrue(all(op[1] == y + 8 for op in cells))
        return [op[5] == gfx.WHITE for op in cells], cv.ops

    def test_the_first_step_cells_are_lit(self):
        for step in (0, 1, 8, 16):
            lit, _ = self.lit(step)
            self.assertEqual(lit, [i < step for i in range(volume.STEPS)], step)

    def test_the_picture_covers_its_rect_and_stays_inside_it(self):
        _, ops = self.lit(16)
        x, y, w, h = overlay.RECT
        self.assertEqual(ops[0][:6], (x, y, x + w, y + h, 0, gfx.DARK))
        for op in ops:
            self.assertTrue(x <= op[0] and op[2] <= x + w and y <= op[1] and op[3] <= y + h, op)
        self.assertTrue(0 <= x and x + w <= gfx.WIDTH and gfx.HUD_RECT[3] <= y and y + h <= gfx.HEIGHT)

    def test_the_number_is_the_step(self):
        _, ops = self.lit(7)
        self.assertEqual([op[5] for op in ops if op[4] == 3], ["vol", "7"])

    def test_a_new_step_paints_only_the_cells_and_the_number_again(self):
        for cv in (gfx.Canvas(), lcd.TftCanvas(Tft())):
            vol = volume.MasterVolume(8)
            pane = PaintCount(vol)
            cv.start()
            pane.draw(cv)
            pane.draw(cv)
            self.assertEqual((pane.paints, pane.levels), (1, 1))
            vol.set(9)
            pane.draw(cv)
            self.assertEqual((pane.paints, pane.levels), (1, 2))

    def test_a_change_of_the_step_shows_the_pane_and_the_start_does_not(self):
        vol = volume.MasterVolume(8)
        layer = overlay.Overlay()
        pane = layer.add(overlay.VolumePane(vol))
        layer.update(0)
        self.assertFalse(pane.visible)  # the step at the start is no change
        vol.set(9)  # no show() call: the pane watches the step
        layer.update(40)
        self.assertTrue(pane.visible)
        layer.update(40 + overlay.HOLD_MS - 1)
        self.assertTrue(pane.visible)
        vol.set(9)  # the same step moves no end
        layer.update(40 + overlay.HOLD_MS)
        self.assertFalse(pane.visible)
        vol.set(8)
        layer.update(5000)
        layer.update(5000 + overlay.HOLD_MS - 1)
        self.assertTrue(pane.visible)

    def test_the_level_part_lies_inside_the_picture_and_holds_the_cells_and_the_number(self):
        x, y, w, h = overlay.RECT
        lx, ly, lw, lh = overlay.LEVEL_RECT
        self.assertTrue(x < lx and lx + lw < x + w and y < ly and ly + lh < y + h)
        cv = gfx.Canvas()
        cv.start()
        overlay.VolumePane(volume.MasterVolume(16)).paint_level(cv)
        self.assertEqual(cv.ops[0][:6], (lx, ly, lx + lw, ly + lh, 0, gfx.DARK))
        for op in cv.ops:
            self.assertTrue(lx <= op[0] and op[2] <= lx + lw and ly <= op[1] and op[3] <= ly + lh, op)


class StOutTest(unittest.TestCase):
    def test_the_frame_after_the_hide_sends_the_rect_again(self):
        display, layer, game = Display(), overlay.Overlay(), Game()
        out = render.StOut(display, False)
        vol = volume.MasterVolume(8)
        layer.add(overlay.VolumePane(vol))

        def frame(now):
            del display.sent[:]
            layer.update(now)
            out.draw(game, [0, 0, 0, 0], layer)
            return list(display.sent)

        frame(0)  # the first frame sends the whole screen
        self.assertEqual(frame(40), [])  # a still game sends nothing
        vol.set(9)  # the pane shows from the next update on, at 80
        self.assertTrue(covers(frame(80), overlay.RECT))
        self.assertFalse(touches(frame(120), overlay.RECT))  # shown and not changed: nothing to send
        self.assertTrue(covers(frame(80 + overlay.HOLD_MS), overlay.RECT))  # hidden: the game shows there again
        self.assertEqual(frame(120 + overlay.HOLD_MS), [])

    def test_only_a_shown_overlay_draws_its_picture(self):
        x, y, w, h = overlay.RECT
        layer, out = overlay.Overlay(), render.StOut(Display(), False)

        def pictures():
            return [op for op in out.canvas.ops if op[:4] == (x, y, x + w, y + h)]

        out.draw(Game(), [0, 0, 0, 0])
        self.assertFalse(pictures())
        out.draw(Game(), [0, 0, 0, 0], layer)  # hidden
        self.assertFalse(pictures())
        pane = layer.add(overlay.VolumePane(volume.MasterVolume(8)))
        out.draw(Game(), [0, 0, 0, 0], layer)  # added and not visible
        self.assertFalse(pictures())
        pane.show(0)
        out.draw(Game(), [0, 0, 0, 0], layer)
        self.assertTrue(pictures())


class TftOutTest(unittest.TestCase):
    def test_the_overlay_is_drawn_after_the_game_and_before_show(self):
        tft, layer = Tft(), overlay.Overlay()
        out = lcd.TftOut(tft)
        layer.add(shown())
        out.draw(Game(), [0, 0, 0, 0], layer)
        blits = [i for i, call in enumerate(tft.calls) if call[0] == "blit"]
        self.assertEqual(len(blits), 2)  # the still part, then the cells and the number over it
        self.assertEqual(tft.calls[blits[0]][3:5], (overlay.RECT[3], overlay.RECT[2]))  # the picture's w and h: turned
        self.assertEqual(tft.calls[blits[1]][3:5], (overlay.LEVEL_RECT[3], overlay.LEVEL_RECT[2]))
        self.assertLess(tft.calls.index("fill_rect"), blits[0])  # the game's rectangle
        self.assertEqual(tft.calls[-1], "show")
        self.assertEqual(out.windows, 3)

    def test_the_still_part_blends_at_the_panes_alpha_and_the_level_part_stays_solid(self):
        self.assertEqual(overlay.VolumePane.alpha, 192)
        for alpha, want in ((None, 192), (255, 255), (128, 128)):  # None: the class's own value
            tft, layer = Tft(), overlay.Overlay()
            pane = layer.add(shown())
            if alpha is not None:
                pane.alpha = alpha
            lcd.TftOut(tft).draw(Game(), [0, 0, 0, 0], layer)
            self.assertEqual([call[5] for call in tft.calls if call[0] == "blit"], [want, 255])
        self.assertEqual(overlay.VolumePane.alpha, 192)  # a value set on one pane stays that pane's

    def test_a_hidden_overlay_and_two_arguments_blit_nothing(self):
        tft, layer = Tft(), overlay.Overlay()
        out = lcd.TftOut(tft)
        layer.add(overlay.VolumePane(volume.MasterVolume(8)))
        out.draw(Game(), [0, 0, 0, 0], layer)
        out.draw(Game(), [0, 0, 0, 0])
        self.assertFalse([call for call in tft.calls if call[0] == "blit"])


if __name__ == "__main__":
    unittest.main()
