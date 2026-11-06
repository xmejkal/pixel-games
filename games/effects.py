"""
Effects on bodies (P607): a body of a plugins.PhysicsPlugin carries an effect, and an engine event can start one. A
scene writes `body.effect = FireTrail(field, ...)`, then each frame calls EffectSystem.dispatch(handlers) for the
step's events and EffectSystem.update() for the effects. Python decides what an event causes (engine D12): handlers
maps an event kind (motion.HIT or SLEEP) to a call of (body, speed), which can set body.effect or burn a flare. A new
effect is one more Effect, and its callers do not change. A scene whose world moves under the screen calls
effect.scroll(dx) each frame, so a path moves with the world (P602, the Runner does, P651).
--- MVP (P607) ---
"""

from fire import H, W


def cell(x, y, size):
    """The fire cell under the centre of a box of side size px with its top left corner at x, y in px."""
    return (x + size // 2) // 2, (y + size // 2) // 2


class Effect:
    """Strategy: one look a body carries. update runs once a frame at the body's place, reset when the body jumps."""

    def update(self, x, y):
        """Draw or burn at the body's top left corner x, y in px."""

    def reset(self):
        """The body jumped, for example a respawn: no path from its last place."""

    # --- MVP (P651): the Runner scrolls its trail with the world (P602) ---
    def scroll(self, dx):
        """The world moved under the screen by dx fire cells, negative to the left: move what the effect holds."""


class FireTrail(Effect):
    """The fire as a trail (D16): heat burned into a HeatField a little behind the body, lag frames of its motion,
    along the path from the last frame's point, so a body at rest burns straight up and a moving body's flames stream
    back against its motion. One per body, because it holds that body's path."""

    def __init__(self, field, size, radius, heat, lag):
        self.field, self.size, self.radius, self.heat, self.lag = field, size, radius, heat, lag
        self.reset()

    def update(self, x, y):
        cx, cy = cell(x, y, self.size)
        if not (0 <= cy < H and -W < cx < 2 * W):  # above the screen after a drop: no streak from there
            self.reset()
            return
        if not self.has_path:
            self.prev_x, self.prev_y = cx, cy
        lx, ly = cx - int((cx - self.prev_x) * self.lag), cy - int((cy - self.prev_y) * self.lag)
        if not self.has_path:
            self.trail_x, self.trail_y = lx, ly
        self.field.burn(self.trail_x, self.trail_y, lx, ly, self.radius, self.heat)
        # --- MVP (P602) --- the path in ints, not tuples, so scroll moves it in place
        self.prev_x, self.prev_y = cx, cy
        self.trail_x, self.trail_y = lx, ly
        self.has_path = True

    def reset(self):
        self.has_path = False  # then prev, the body's centre in cells last frame, and trail, the last burn point
        self.prev_x = self.prev_y = self.trail_x = self.trail_y = 0

    def scroll(self, dx):  # --- Later, not MVP: kept for other games, the PO 2026-11-04 (P602) ---
        self.prev_x += dx
        self.trail_x += dx


class Body:
    """Body i of a physics plugin, with the effect it carries (None for none)."""

    def __init__(self, physics_plugin, i):
        self.physics_plugin, self.i, self.effect = physics_plugin, i, None

    def place(self):
        """The top left corner in px, as read."""
        return self.physics_plugin.place(self.i)

    def reset(self):
        if self.effect is not None:
            self.effect.reset()


class EffectSystem:
    """A system, as in the entity-component-system pattern: the bodies of one physics plugin with their effects, made
    once, so a frame makes no list. dispatch sends the step's events to their handlers (the observer pattern), and
    update runs each effect once a frame (the update method pattern)."""

    def __init__(self, physics_plugin):
        self.physics_plugin = physics_plugin
        self.bodies = [Body(physics_plugin, i) for i in range(physics_plugin.n)]

    def dispatch(self, handlers):
        """Each event of the last step call to handlers[kind](body, speed), for the kinds handlers holds."""
        k, events = self.physics_plugin.events(), self.physics_plugin.drained
        for j in range(0, 3 * k, 3):
            handler = handlers.get(events[j + 1])
            if handler is not None:
                handler(self.bodies[events[j]], events[j + 2])

    def update(self):
        """Each body's effect at its place."""
        for body in self.bodies:
            if body.effect is not None:
                x, y = body.place()
                body.effect.update(x, y)
