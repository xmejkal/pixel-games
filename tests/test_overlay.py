"""The system overlay (P762) on the Mac: how long a view shows, what VolumeView paints, and that both outputs draw
the overlay after the game and send its area again in the frame after it hides. framebuf comes from tests/stubs and
time gets the MicroPython ticks functions, as in test_hud.
Run from the repository root: python3 -B -m unittest tests.test_overlay. --- MVP (P762) ---"""

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


class View:
    """A view that counts its draws."""

    draws = 0

    def draw(self, cv):
        self.draws += 1


class PaintCount(overlay.VolumeView):
    paints = 0

    def paint(self, cv):
        self.paints += 1
        super().paint(cv)


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
    def test_a_view_shows_for_hold_ms_after_show(self):
        layer, view, cv = overlay.Overlay(), View(), None
        layer.show(view, 5000)
        layer.update(5000 + overlay.HOLD_MS - 1)
        layer.draw(cv)
        self.assertEqual(view.draws, 1)
        layer.update(5000 + overlay.HOLD_MS)
        layer.draw(cv)
        self.assertEqual(view.draws, 1)
        self.assertIsNone(layer.view)

    def test_a_second_show_moves_the_end(self):
        layer, view = overlay.Overlay(), View()
        layer.show(view, 5000)
        layer.show(view, 5600)
        layer.update(5000 + overlay.HOLD_MS)
        self.assertIs(layer.view, view)
        layer.update(5600 + overlay.HOLD_MS)
        self.assertIsNone(layer.view)

    def test_with_no_view_draw_does_nothing(self):
        layer = overlay.Overlay()
        layer.update(0)
        layer.draw(None)  # a canvas would raise here

    def test_hold_ms_is_one_second(self):
        self.assertEqual(overlay.HOLD_MS, 1000)


class VolumeViewTest(unittest.TestCase):
    def lit(self, step):
        cv, x, y = gfx.Canvas(), overlay.RECT[0], overlay.RECT[1]
        cv.start()
        overlay.VolumeView(volume.MasterVolume(step)).draw(cv)
        cells = [op for op in cv.ops if op[4] == 0 and (op[2] - op[0], op[3] - op[1]) == (6, 12)]
        self.assertEqual(len(cells), volume.STEPS)
        self.assertEqual([op[0] for op in cells], [x + 40 + 8 * i for i in range(volume.STEPS)])
        self.assertTrue(all(op[1] == y + 8 for op in cells))
        return [op[5] == gfx.WHITE for op in cells], cv.ops

    def test_the_first_step_cells_are_lit(self):
        for step in (0, 1, 8, 16):
            lit, _ = self.lit(step)
            self.assertEqual(lit, [i < step for i in range(volume.STEPS)], step)

    def test_the_panel_covers_its_rect_and_stays_inside_it(self):
        _, ops = self.lit(16)
        x, y, w, h = overlay.RECT
        self.assertEqual(ops[0][:6], (x, y, x + w, y + h, 0, gfx.DARK))
        for op in ops:
            self.assertTrue(x <= op[0] and op[2] <= x + w and y <= op[1] and op[3] <= y + h, op)
        self.assertTrue(0 <= x and x + w <= gfx.WIDTH and gfx.HUD_RECT[3] <= y and y + h <= gfx.HEIGHT)

    def test_the_number_is_the_step(self):
        _, ops = self.lit(7)
        self.assertEqual([op[5] for op in ops if op[4] == 3], ["vol", "7"])

    def test_paint_runs_only_when_the_step_changes(self):
        for cv in (gfx.Canvas(), lcd.TftCanvas(Tft())):
            vol = volume.MasterVolume(8)
            view = PaintCount(vol)
            cv.start()
            view.draw(cv)
            view.draw(cv)
            self.assertEqual(view.paints, 1)
            vol.set(9)
            view.draw(cv)
            self.assertEqual(view.paints, 2)


class StOutTest(unittest.TestCase):
    def test_the_frame_after_the_hide_sends_the_rect_again(self):
        display, layer, game = Display(), overlay.Overlay(), Game()
        out = render.StOut(display, False)
        view = overlay.VolumeView(volume.MasterVolume(8))

        def frame(now):
            del display.sent[:]
            layer.update(now)
            out.draw(game, [0, 0, 0, 0], layer)
            return list(display.sent)

        frame(0)  # the first frame sends the whole screen
        self.assertEqual(frame(40), [])  # a still game sends nothing
        layer.show(view, 40)
        self.assertTrue(covers(frame(80), overlay.RECT))
        self.assertFalse(touches(frame(120), overlay.RECT))  # shown and not changed: nothing to send
        self.assertTrue(covers(frame(40 + overlay.HOLD_MS), overlay.RECT))  # hidden: the game shows there again
        self.assertEqual(frame(80 + overlay.HOLD_MS), [])

    def test_two_arguments_draw_no_overlay(self):
        display = Display()
        out = render.StOut(display, False)
        out.draw(Game(), [0, 0, 0, 0])
        self.assertTrue(all(op[:4] != overlay.RECT[:4] for op in out.canvas.ops))


class TftOutTest(unittest.TestCase):
    def test_the_overlay_is_drawn_after_the_game_and_before_show(self):
        tft, layer = Tft(), overlay.Overlay()
        out = lcd.TftOut(tft)
        layer.show(overlay.VolumeView(volume.MasterVolume(8)), 0)
        out.draw(Game(), [0, 0, 0, 0], layer)
        blits = [i for i, call in enumerate(tft.calls) if call[0] == "blit"]
        self.assertEqual(len(blits), 1)
        self.assertEqual(tft.calls[blits[0]][3:5], (overlay.RECT[3], overlay.RECT[2]))  # the panel's w and h: turned
        self.assertLess(tft.calls.index("fill_rect"), blits[0])  # the game's rectangle
        self.assertEqual(tft.calls[-1], "show")
        self.assertEqual(out.windows, 3)

    def test_a_hidden_overlay_and_two_arguments_blit_nothing(self):
        tft, layer = Tft(), overlay.Overlay()
        out = lcd.TftOut(tft)
        out.draw(Game(), [0, 0, 0, 0], layer)
        out.draw(Game(), [0, 0, 0, 0])
        self.assertFalse([call for call in tft.calls if call[0] == "blit"])


if __name__ == "__main__":
    unittest.main()
