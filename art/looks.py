"""Looks: how a painted picture is seen in the end. A set paints in watercolour; another look re-inks the same
pictures without painting them again, so a game can change its style and keep its shapes and its random stream."""

import colorsys

from PIL import Image


class Look:
    """Takes a game picture (RGBA) and returns how it is seen. Alpha stays as it is, so a hard mask stays hard."""

    def apply(self, img):
        raise NotImplementedError


class Watercolour(Look):
    """The look the sets are painted in: the picture itself, so the board files do not change."""

    def apply(self, img):
        return img


class NightInk(Look):
    """Ink black and bone white, with the pixels near one accent hue kept in that accent: the second look, for the
    space games (P565 D5)."""

    INK, BONE = (18, 16, 26), (232, 224, 204)

    def __init__(self, accent, reach=0.07, light=120):
        self.accent, self.reach, self.light = tuple(accent), reach, light  # reach: hue distance, light: bone from luma
        self.hue = colorsys.rgb_to_hsv(*(c / 255 for c in accent))[0]

    def ink(self, p):
        r, g, b, a = p
        if a == 0:
            return p
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s > 0.4 and v > 0.3 and min(abs(h - self.hue), 1 - abs(h - self.hue)) < self.reach:
            return self.accent + (a,)
        luma = (299 * r + 587 * g + 114 * b) // 1000
        return (self.BONE if luma >= self.light else self.INK) + (a,)

    def apply(self, img):
        out = Image.new("RGBA", img.size)
        out.putdata([self.ink(p) for p in img.convert("RGBA").get_flattened_data()])
        return out
