"""
P905 (#1284): the switch prototype. The game box runs a small test game with two of Rescue's figures, the fireman and
the child, and seven ways to switch between them. The game counts each switch, so the log shows for each way whether
the PO met his pass line: 10 switches in a row with no wrong figure (D35). The app, the catalog and the box's lineup
do not change.
"""

import sys
import time

# --- the rules, in ms, px and small ints ---
LEAN = 40  # engine.actions.LEAN: an axis this far from the middle, of 100, leans
LEAN_REST = 20  # an axis under this far from the middle rests: the next lean is a new one
DOUBLE_MS = 300  # a second push at most this long after the first is a double tap (Android's DOUBLE_TAP_TIMEOUT)
HOLD_MS = 400  # FIRE held this long is a hold (Android's DEFAULT_LONG_PRESS_TIMEOUT)


class Quit(Exception):
    """QUIT pressed twice in the menu: the run ends."""


class Seen:
    """A FIRE button wrapped, so the game tells BOOT from the click. It keeps its last update in two attributes:
    pushed, whether that update saw a push, and held, the button's level. engine.actions.fold reads held as an
    attribute, so update() and forget() both refresh it."""

    def __init__(self, button):
        self.button, self.pushed, self.held = button, False, button.held

    def update(self, now_ms):
        self.pushed = self.button.update(now_ms)
        self.held = self.button.held
        return self.pushed

    def forget(self):
        """The button drops its pushes (the box was busy), so no push waits here either."""
        self.button.forget()
        self.pushed, self.held = False, self.button.held


class LeanEdge:
    """The edge of an axis: read(v) answers -1 or 1 once when a new lean starts, else 0. A lean starts at LEAN or more
    from the middle, and the axis rests under LEAN_REST, so a lean that wavers between the two answers once. A lean the
    other way is a new lean at once. v is the stick's x or y, -100 to 100: up and left read negative. It is not
    engine.actions.lean, which answers the level and which the walk uses."""

    def __init__(self):
        self.on = 0  # the lean that answered and has not rested since: -1, 0 or 1

    def reset(self, v):
        """Starts from the axis as it is: a lean now is no new lean."""
        self.on = 1 if v >= LEAN else -1 if v <= -LEAN else 0

    def read(self, v):
        side = 1 if v >= LEAN else -1 if v <= -LEAN else 0
        if side and side != self.on:
            self.on = side
            return side
        if -LEAN_REST < v < LEAN_REST:
            self.on = 0
        return 0


class Way:
    """One way to switch, a strategy. reset(now_ms, actions, boot, click) starts it from the inputs as they are: the
    lean now is no new lean, a FIRE that is down needs a new push, and a push that waits is dropped. read(now_ms,
    actions, boot, click) reads one frame and leaves its answer in steps (along the list of the figures: + toward the
    child, - toward the fireman) and acts (whether FIRE acts), so a frame makes no tuple. actions is the frame's
    engine.actions.Actions, boot and click the two Seen FIRE buttons. name: the log's word; label: the screen's; hint:
    one line of the top bar, 40 characters at most; wraps: whether a step past the list's end comes round (false for
    the stick and the knob, whose list stops at its ends); control: true for the way that is no test."""

    name = label = hint = ""
    wraps, control = True, False

    def __init__(self):
        self.steps, self.acts = 0, False

    def reset(self, now_ms, actions, boot, click):
        self.steps, self.acts = 0, False

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = 0, actions.fire.pressed


class StickWay(Way):
    """A new lean of the stick's y picks by direction: up the fireman, down the child."""

    name, label, hint, wraps = "stick", "STICK UP/DOWN", "up: FIREMAN, down: CHILD  act: FIRE", False

    def __init__(self):
        Way.__init__(self)
        self.edge = LeanEdge()

    def reset(self, now_ms, actions, boot, click):
        Way.reset(self, now_ms, actions, boot, click)
        self.edge.reset(actions.y)

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = self.edge.read(actions.y), actions.fire.pressed


class ClickWay(Way):
    """A push of the click (the stick's push-button) takes the other figure, and a push of BOOT acts."""

    name, label, hint = "click", "STICK CLICK", "click: switch  act: BOOT"

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = 1 if click.pushed else 0, boot.pushed


class DoubleWay(Way):
    """A second push of FIRE at most DOUBLE_MS after the first takes the other figure. A push with no second one acts
    DOUBLE_MS later. A frame reads its push before the time, so a second push at exactly DOUBLE_MS switches. After a
    double tap the count starts again, so a third push is a first one. A push past DOUBLE_MS is a new first one, and
    the push before it acts in that frame."""

    name, label, hint = "double", "DOUBLE TAP", "FIRE twice: switch  FIRE once: act"

    def __init__(self):
        Way.__init__(self)
        self.waiting, self.first_ms = False, 0  # a first push that waits for a second, and its frame's clock

    def reset(self, now_ms, actions, boot, click):
        Way.reset(self, now_ms, actions, boot, click)
        self.waiting = False

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = 0, False
        late = self.waiting and time.ticks_diff(now_ms, self.first_ms) > DOUBLE_MS
        if actions.fire.pressed:
            if self.waiting and not late:
                self.steps, self.waiting = 1, False
                return
            self.acts = late
            self.waiting, self.first_ms = True, now_ms
            return
        if self.waiting and time.ticks_diff(now_ms, self.first_ms) >= DOUBLE_MS:
            self.acts, self.waiting = True, False


class HoldWay(Way):
    """FIRE held for HOLD_MS or longer takes the other figure, once for each hold. A hold starts at a push and ends
    when both FIRE buttons are up. A release before HOLD_MS acts, and a release after it does not. A tap so short that
    the box saw no level acts at once. The length is the frame's clock, so a release that a frame sees at HOLD_MS or
    later is a hold."""

    name, label, hint = "hold", "HOLD FIRE", "hold FIRE: switch  tap FIRE: act"

    def __init__(self):
        Way.__init__(self)
        self.down, self.since_ms, self.switched = False, 0, False

    def reset(self, now_ms, actions, boot, click):
        Way.reset(self, now_ms, actions, boot, click)
        self.down = False

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = 0, False
        fire = actions.fire
        if fire.pressed and not self.down:
            if not fire.held:
                self.acts = True
                return
            self.down, self.since_ms, self.switched = True, now_ms, False
            return
        if not self.down:
            return
        long = time.ticks_diff(now_ms, self.since_ms) >= HOLD_MS
        if long and not self.switched:
            self.steps, self.switched = 1, True
        if not fire.held:
            self.down, self.acts = False, not long


class PickWay(Way):
    """A push of PICK (the board's D14 button) takes the other figure, and FIRE acts. Never a hold: a hold of about 5 s
    powered an older board off (bench.md)."""

    name, label, hint = "pick", "PICK (D14)", "press PICK, never hold  act: FIRE"

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = 1 if actions.pick.pressed else 0, actions.fire.pressed


class KnobWay(Way):
    """A turn of the knob picks by direction: its positive detents step toward the child. Which way that is on the box
    follows the encoder's sign, so the hint names no direction."""

    name, label, hint, wraps = "knob", "KNOB", "knob: one way FIREMAN, other way CHILD", False

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = actions.turn, actions.fire.pressed


class AutoWay(Way):
    """The control: the game makes the wanted figure active at each task's start (Round), so no input switches."""

    name, label, hint, control = "auto", "AUTO (control)", "the game switches for you  act: FIRE", True


WAYS = (StickWay, ClickWay, DoubleWay, HoldWay, PickWay, KnobWay, AutoWay)  # the menu's order
