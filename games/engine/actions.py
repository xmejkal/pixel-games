"""
The action map (P851, stage 1 of the engine plan): the box's inputs bound to the actions a frame reads, so the App, and
from P872 a game, reads actions, never pins. --- MVP (P851) ---

The bindings follow Unity's Input System, where one action has several bindings: FIRE is BOOT and the stick's switch,
PICK is D14. A binding is a driver's button (drivers.buttons.Button): update(now_ms) says whether it was pushed, held
is its level, and forget() drops its pushes. The map imports no driver: app.open_action_map builds them from the pin map
and hands them in. One map is one player's: a remote board gets a second map (P832).
A game reads the stick's x and y from the Actions that App.play hands it as game.stick (P872): bucket reads x as a
speed and starfire x and y, through rate(), the one rule for a speed, and meteors, rescue, snake, gravpong, tunnel and
road read their way through lean(), the one rule for a direction.
"""

# --- MVP (P872) ---
LEAN = 40  # an axis this far from the middle, of 100, leans: a direction. A smaller tilt is no direction


def lean(v):
    """The direction an axis leans: -1, 0 or 1. v: the stick's x or y, -100 to 100. Small ints only, so a frame makes
    nothing."""
    return 1 if v >= LEAN else -1 if v <= -LEAN else 0


def rate(top, v):
    """The speed an axis sets: top * |v| // 100 with the sign of v, so a tilt and its mirror are as fast (top * v // 100
    floors, so the minus side would be 1 faster). top: the speed at a full tilt. v: the stick's x or y, -100 to 100.
    Small ints only, so a frame makes nothing."""
    s = top * abs(v) // 100
    return s if v >= 0 else -s


class Action:
    """One action in one frame: pressed, a binding was pushed in this frame; held, a binding's level is pressed."""

    def __init__(self):
        self.pressed = self.held = False


class Actions:
    """What the inputs say in one frame: fire and pick, an Action each; turn, the knob's detents in this frame (+ one
    way, - the other: a change, not a position); x and y, the stick's axes, -100 to 100 (0 with no stick)."""

    def __init__(self):
        self.fire, self.pick = Action(), Action()
        self.turn = self.x = self.y = 0


def fold(buttons, now_ms, action):
    """Fold the frame's state of buttons into action: each button is updated, never skipped after a push, since update()
    counts and debounces. action.pressed is the OR of their pushes and action.held the OR of their levels, both made
    fresh each frame, so a button's release clears held unless another button holds it."""
    pressed = held = False
    for button in buttons:
        if button.update(now_ms):
            pressed = True
        if button.held:
            held = True
    action.pressed, action.held = pressed, held


class ActionMap:
    """fire_buttons and pick_buttons: the driver buttons bound to each action; encoder: the knob's
    (drivers.encoder.Encoder), or None; stick: a drivers.stick.Stick, or None. poll(now_ms), once per frame, updates
    every binding and answers the frame's Actions, the same record each frame. gc is off in the box's loop, so a poll
    must allocate nothing: by a reading of the code it makes no object (small ints, a for over a tuple, a two-name
    assignment), and P851's bench step checks that the heap line stays flat with the poll on."""

    def __init__(self, fire_buttons, pick_buttons, encoder=None, stick=None):
        self.fire_bindings, self.pick_bindings = tuple(fire_buttons), tuple(pick_buttons)
        self.encoder, self.stick = encoder, stick
        self.actions = Actions()

    def poll(self, now_ms):
        actions = self.actions
        fold(self.fire_bindings, now_ms, actions.fire)
        fold(self.pick_bindings, now_ms, actions.pick)
        actions.turn = self.encoder.take_detents(now_ms) if self.encoder else 0
        if self.stick:
            actions.x, actions.y = self.stick.read_x(), self.stick.read_y()
        return actions

    def forget(self):
        """Each binding drops the pushes made until now (Button.forget): the box was busy in a build (P818)."""
        for button in self.fire_bindings:
            button.forget()
        for button in self.pick_bindings:
            button.forget()
