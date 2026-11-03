"""A stand-in for MicroPython's framebuf, so gfx imports on the Mac: the Stack tests record draw calls on their own
canvas and never draw pixels."""

MONO_HLSB, RGB565 = 0, 1


class FrameBuffer:

    def __init__(self, *args):
        pass

    def fill(self, *args):
        pass

    def pixel(self, *args):
        return 0

    def text(self, *args):
        pass

    def fill_rect(self, *args):
        pass
