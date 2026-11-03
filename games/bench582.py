"""
P582 on the bench: RENT that plays itself, so a long run logs paint, fps and the collapse without a hand on the
button. Bench only, like the probe*.py files: the game box does not import it. On the board:

    import app, bench582; app.run(games=(bench582.Bot,))

Bot is a Stack that keeps the name "stack" (so BEST and the art are RENT's) and taps by itself. In play it taps when
no floor is falling and the hanging floor, after this frame's slide, is within half a frame's slide of its target:
the top floor's drawn x, or on every third tap a quarter of the floor's width off it, so cut-off slabs fall too
(once the floor is under 16 px wide, a quarter of it is inside the 4 px perfect window, and that tap lands perfect).
Over, it taps retry once the SOLD OUT card is shown and the retry is allowed. Stack itself is unchanged.
"""

import time

from arcade2 import W, Stack
from gfx import OVER, PLAY


class Bot(Stack):

    OFF_EVERY, OFF_SHARE = 3, 4  # every third tap lands a quarter of the floor's width off the top floor

    def setup(self):
        Stack.setup(self)
        self.taps = 0  # taps in this round: which one lands off-centre

    def step(self, now_ms, pressed, held):
        return Stack.step(self, now_ms, pressed or self.wants(now_ms), held)

    def wants(self, now_ms):
        """Whether to tap on the frame at now_ms."""
        if self.state == OVER:
            # self.age is the last frame's, so its paint has shown the card, and this frame's age allows the retry
            return self.age >= self.CARD_MS and self.age >= self.OVER_MS
        if self.state != PLAY or self.drop or self.hold or self.last is None:
            return False
        dt = min(time.ticks_diff(now_ms, self.last), 60) / 1000  # this frame's dt, as Game.step works it out
        slide = self.speed * dt
        x = self.x + self.dir * slide  # where play() moves it before it reads the tap
        target = self.floor_x(len(self.floors) - 1)
        if (self.taps + 1) % self.OFF_EVERY == 0:  # off-centre, to the side the hanging floor can reach
            off = self.w // self.OFF_SHARE
            target = target + off if target + off <= W - self.w else target - off
        if abs(x - target) > slide / 2 + 1:
            return False
        self.taps += 1
        return True
