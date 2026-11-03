"""
P582 on the bench: RENT that plays itself, so a long run logs paint, fps and the collapse without a hand on the
button. Bench only, like the probe*.py files: the game box does not import it. On the board:

    import app, bench582; app.run(games=(bench582.Bot,))

Bot is a Stack that keeps the name "stack" (so BEST and the art are RENT's) and taps by itself: in play when no floor
is falling and the hanging floor, after this frame's slide, is within half a frame's slide of the top floor's drawn
x; over, once the retry is allowed. Stack itself is unchanged.
"""

import time

from arcade2 import Stack
from gfx import OVER, PLAY


class Bot(Stack):

    def step(self, now_ms, pressed, held):
        return Stack.step(self, now_ms, pressed or self.wants(now_ms), held)

    def wants(self, now_ms):
        """Whether to tap on the frame at now_ms."""
        if self.state == OVER:
            return self.age >= self.OVER_MS
        if self.state != PLAY or self.drop or self.hold or self.last is None:
            return False
        dt = min(time.ticks_diff(now_ms, self.last), 60) / 1000  # this frame's dt, as Game.step works it out
        slide = self.speed * dt
        x = self.x + self.dir * slide  # where play() moves it before it reads the tap
        return abs(x - self.floor_x(len(self.floors) - 1)) <= slide / 2 + 1
