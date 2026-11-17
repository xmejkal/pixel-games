"""
Sub-pixel motion (P872): a speed in px a second, stepped by a frame's ms, answered in whole px, with the part short of
the next whole px kept for the next frame. So a slow speed still moves, a px now and then, and a frame of any length
moves as far as its ms say. Bucket, meteors and starfire move through it (P885). --- MVP (P872) ---
"""


class SubPixel:
    """rest: px times ms short of the next whole px, 0 to 999 (floor division keeps it there for a negative speed too).
    Ints only, so a step makes nothing."""

    def __init__(self):
        self.rest = 0

    def step(self, px_s, ms):
        """ms at px_s px a second, + or -: the whole px moved in them, an int; the rest waits for the next step."""
        self.rest += px_s * ms
        px = self.rest // 1000
        self.rest -= px * 1000
        return px

    def reset(self):
        """No rest: the next step starts at a whole px (a stop at an edge, a restart)."""
        self.rest = 0
