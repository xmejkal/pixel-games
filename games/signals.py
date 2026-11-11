"""
What a game says happened (P768): a game emits a signal by its name, and each listener of that name is called at once,
in the same frame. No queue (the finding of P766: a direct listener for a change of state). The word is Godot's. An
"event" in this code is a C physics event (plugins.PhysicsPlugin.events), which is another thing.
"""


# --- MVP (P768) ---
class Signals:
    """The listeners by signal name. A listener is called as listener(name, value). emit makes nothing new."""

    def __init__(self):
        self.listeners = {}

    def listen(self, name, listener):
        self.listeners.setdefault(name, []).append(listener)

    def emit(self, name, value=None):
        for listener in self.listeners.get(name, ()):
            listener(name, value)

    def clear(self):
        self.listeners = {}
