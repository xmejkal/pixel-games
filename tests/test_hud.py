"""The kept HUD (P599) on the Mac: a HUD drawn once into a strip and blitted each frame must give the same panel
pixels as the same HUD drawn straight onto the panel, at ORIENTATION 0 and 180. The recording canvas replays the same
tuples. framebuf comes from tests/stubs (its RGB565 buffers hold pixels) and time gets the MicroPython ticks functions,
so gfx imports here. Run from the repository root: python3 -m unittest discover tests. --- MVP (P599) ---"""

import contextlib
import os
import string
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

import fire  # noqa: E402
import gfx  # noqa: E402
import lcd  # noqa: E402
import rain  # noqa: E402

BACKGROUND = 0x1234  # not DARK and not black, so a strip larger or smaller than its rect shows
OFF_ORIGIN = (20, 30, 100, 14)
SAVED_GLYPHS = {}


def setUpModule():
    """The stub draws no font, so each printable character gets its own two runs: text then has pixels to compare."""
    SAVED_GLYPHS.update(gfx.GLYPHS)
    for ch in string.printable:
        k = ord(ch)
        gfx.GLYPHS[ch] = ((k % 4, k % 8, k % 5 + 1), (1, (k // 8) % 8, 2))


def tearDownModule():
    gfx.GLYPHS.clear()
    gfx.GLYPHS.update(SAVED_GLYPHS)


class Tft:
    """The s3lcd display: a 240 x 320 frame of native uint16, fill_rect clipped, and blit_buffer's memcpy path only."""

    def __init__(self):
        self.frame = bytearray(BACKGROUND.to_bytes(2, "little") * (lcd.PANEL_W * lcd.PANEL_H))
        self.blits = 0

    def fill_rect(self, x, y, w, h, c):
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, lcd.PANEL_W), min(y + h, lcd.PANEL_H)
        row = (c & 0xFFFF).to_bytes(2, "little") * max(x1 - x0, 0)
        for yy in range(y0, y1):
            at = 2 * (yy * lcd.PANEL_W + x0)
            self.frame[at:at + len(row)] = row

    def blit_buffer(self, buf, x, y, w, h, alpha=255, key=-1):
        """s3lcd.c's memcpy path: alpha 255, no key, wholly on the panel. Anything else fails the test."""
        assert alpha == 255 and key == -1, (alpha, key)
        assert 0 <= x <= lcd.PANEL_W - w and 0 <= y <= lcd.PANEL_H - h, (x, y, w, h)
        assert len(buf) == 2 * w * h, (len(buf), w, h)
        for yy in range(h):
            at = 2 * ((y + yy) * lcd.PANEL_W + x)
            self.frame[at:at + 2 * w] = buf[2 * w * yy:2 * w * (yy + 1)]
        self.blits += 1


@contextlib.contextmanager
def orientation(degrees):
    """lcd.ORIENTATION for the canvases made inside: TftCanvas reads it when it is made."""
    old, lcd.ORIENTATION = lcd.ORIENTATION, degrees
    try:
        yield
    finally:
        lcd.ORIENTATION = old


class Game(gfx.Game):
    name = "probe"


def scenes():
    """A Game with a score and a best, the rain and the fire, each with its HUD's text set."""
    game = Game()
    game.score, gfx.BEST[game.name] = 12, 345
    drops = rain.Rain.__new__(rain.Rain)  # no stepper: draw_hud reads only the label and the bar
    drops.label, drops.bar = "c step 0.2 ms 24 fps", 37
    flames = fire.Fire.__new__(fire.Fire)  # no pictures and no field: draw_hud reads only the label
    flames.label = "fire B 11.5 ms 24 fps"
    return game, drops, flames


def off_origin(cv):
    """A HUD away from the panel's corner that covers its rect, as every real HUD does."""
    x, y, w, h = OFF_ORIGIN
    cv.fill(x, y, w, h, gfx.DARK)
    cv.text("12 ok", x + 3, y + 2, gfx.WHITE)


class StripTest(unittest.TestCase):
    def test_a_kept_hud_gives_the_pixels_of_a_drawn_one(self):
        for degrees in (0, 180):
            cases = [(s.name, s.hud, s.draw_hud) for s in scenes()]
            cases.append(("off", lambda cv: cv.keep("off", OFF_ORIGIN, off_origin), off_origin))
            for name, kept, drawn in cases:
                with self.subTest(orientation=degrees, scene=name), orientation(degrees):
                    straight, strip = Tft(), Tft()
                    drawn(lcd.TftCanvas(straight))
                    kept(lcd.TftCanvas(strip))
                    self.assertEqual(1, strip.blits)
                    self.assertNotEqual(Tft().frame, straight.frame)  # the HUD drew something
                    self.assertEqual(straight.frame, strip.frame)

    def test_the_same_key_blits_without_a_redraw_and_a_new_key_redraws(self):
        tft, calls = Tft(), []
        cv = lcd.TftCanvas(tft)

        def draw(c):
            calls.append(1)
            off_origin(c)

        for key in ("a", "a", "a", "b", "b"):
            cv.keep(key, OFF_ORIGIN, draw)
        self.assertEqual(2, len(calls))
        self.assertEqual(5, tft.blits)

    def test_another_game_with_the_same_score_redraws(self):
        tft = Tft()
        cv = lcd.TftCanvas(tft)
        first, other = Game(), Game()
        other.name = "other"
        first.hud(cv)
        other.hud(cv)
        straight = Tft()
        other.draw_hud(lcd.TftCanvas(straight))
        self.assertEqual(straight.frame, tft.frame)


class RecordingTest(unittest.TestCase):
    def test_the_recording_canvas_replays_the_same_tuples(self):
        game = scenes()[0]
        cv, fresh = gfx.Canvas(), gfx.Canvas()
        game.draw_hud(fresh)
        game.hud(cv)
        first = list(cv.ops)
        cv.start()
        game.hud(cv)
        self.assertEqual(fresh.ops, first)
        self.assertEqual(len(first), len(cv.ops))
        self.assertTrue(all(a is b for a, b in zip(first, cv.ops)))  # the same objects: Dirty sees no change
        game.score += 1
        cv.start()
        game.hud(cv)
        self.assertNotEqual(first, cv.ops)


if __name__ == "__main__":
    unittest.main()
