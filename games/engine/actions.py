"""
The action map (P851, stage 1 of the engine plan): the box's inputs bound to the actions a frame reads, so the App, and
from P872 a game, reads actions, never pins. --- MVP (P851) ---

The bindings follow Unity's Input System, where one action has several bindings: FIRE is BOOT and the stick's switch,
PICK is D14. A binding is a driver's button (drivers.buttons.Button): update(now_ms) says whether it was pushed, held
is its level, and forget() drops its pushes. The map imports no driver: app.open_actions builds them from the pin map
and hands them in. One map is one player's: a remote board gets a second map (P832).
"""


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


class ActionMap:
    """fire and pick: the driver buttons bound to each action; encoder: the knob's (drivers.encoder.Encoder), or None;
    stick: a drivers.stick.Stick, or None. poll(now_ms), once per frame, updates every binding and answers the frame's
    Actions: the same record each frame, so a frame allocates nothing (gc is off in the box's loop)."""

    def __init__(self, fire, pick, encoder=None, stick=None):
        self.fire_bindings, self.pick_bindings = tuple(fire), tuple(pick)
        self.encoder, self.stick = encoder, stick
        self.actions = Actions()

    def poll(self, now_ms):
        actions = self.actions
        self.read(self.fire_bindings, actions.fire, now_ms)
        self.read(self.pick_bindings, actions.pick, now_ms)
        actions.turn = self.encoder.take_detents(now_ms) if self.encoder else 0
        if self.stick:
            actions.x, actions.y = self.stick.read_x(), self.stick.read_y()
        return actions

    @staticmethod
    def read(bindings, action, now_ms):
        """action from its bindings. Each is updated, never skipped after a push: update() counts and debounces.
        pressed is the OR of their pushes and held the OR of their levels, both made fresh each frame, so a binding's
        release clears held unless another binding holds it."""
        pressed = held = False
        for button in bindings:
            if button.update(now_ms):
                pressed = True
            if button.held:
                held = True
        action.pressed, action.held = pressed, held

    def forget(self):
        """Each binding drops the pushes made until now (Button.forget): the box was busy in a build (P818)."""
        for button in self.fire_bindings:
            button.forget()
        for button in self.pick_bindings:
            button.forget()
