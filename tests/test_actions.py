"""games/engine/actions.py on the Mac (P851, stage 1 of the engine plan): the action map's bindings with fake driver
buttons, a fake encoder and a fake stick. FIRE's two bindings OR their pushes and their levels, both made fresh each
frame; turn is the frame's change; every binding is updated in every poll; forget() reaches each binding. Run from the
repository root: python3 -B -m unittest tests.test_actions. --- MVP (P851) ---"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))

from engine.actions import ActionMap  # noqa: E402


class FakeButton:
    """A driver button: update(now) answers the next of pushes (then False) and counts its calls; held is set by the
    test; forget() is counted."""

    def __init__(self, *pushes):
        self.pushes, self.held, self.updates, self.forgets = list(pushes), False, 0, 0

    def update(self, now_ms):
        self.updates += 1
        return self.pushes.pop(0) if self.pushes else False

    def forget(self):
        self.forgets += 1


class FakeEncoder:
    """take_detents gives the next of turns, then 0."""

    def __init__(self, *turns):
        self.turns = list(turns)

    def take_detents(self, now_ms):
        return self.turns.pop(0) if self.turns else 0


class FakeStick:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def read_x(self):
        return self.x

    def read_y(self):
        return self.y


class ActionMapTest(unittest.TestCase):
    def test_either_binding_presses_fire(self):
        boot, switch = FakeButton(True, False), FakeButton(False, True)
        actions = ActionMap((boot, switch), ())
        self.assertEqual([True, True, False], [actions.poll(k).fire.pressed for k in range(3)])

    def test_either_binding_holds_fire_and_both_released_clear_it(self):
        boot, switch = FakeButton(), FakeButton()
        actions = ActionMap((boot, switch), ())
        seen = []
        for boot_held, switch_held in ((True, False), (True, True), (False, True), (False, False)):
            boot.held, switch.held = boot_held, switch_held
            seen.append(actions.poll(0).fire.held)
        self.assertEqual([True, True, True, False], seen)

    def test_pressed_and_turn_last_one_frame(self):
        actions = ActionMap((FakeButton(True),), (FakeButton(True),), FakeEncoder(2))
        first = actions.poll(0)
        self.assertEqual((True, True, 2), (first.fire.pressed, first.pick.pressed, first.turn))
        second = actions.poll(40)
        self.assertEqual((False, False, 0), (second.fire.pressed, second.pick.pressed, second.turn))

    def test_every_binding_is_updated_though_the_first_was_pushed(self):
        boot, switch, d14 = FakeButton(True), FakeButton(True), FakeButton(True)
        actions = ActionMap((boot, switch), (d14,))
        actions.poll(0)
        self.assertEqual((1, 1, 1), (boot.updates, switch.updates, d14.updates))
        self.assertEqual([], switch.pushes)  # its push was taken in this frame, not left for the next

    def test_fire_reads_its_own_bindings_and_pick_its_own(self):
        actions = ActionMap((FakeButton(),), (FakeButton(True),))
        got = actions.poll(0)
        self.assertEqual((False, True), (got.fire.pressed, got.pick.pressed))

    def test_the_stick_s_axes_and_none_without_a_stick(self):
        got = ActionMap((), (), stick=FakeStick(-40, 100)).poll(0)
        self.assertEqual((-40, 100), (got.x, got.y))
        got = ActionMap((), ()).poll(0)
        self.assertEqual((0, 0, 0), (got.x, got.y, got.turn))

    def test_the_same_record_each_frame(self):
        actions = ActionMap((), ())
        self.assertIs(actions.poll(0), actions.poll(40))

    def test_forget_reaches_every_binding(self):
        buttons = FakeButton(), FakeButton(), FakeButton()
        ActionMap(buttons[:2], buttons[2:]).forget()
        self.assertEqual([1, 1, 1], [b.forgets for b in buttons])


if __name__ == "__main__":
    unittest.main()
