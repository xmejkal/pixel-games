"""The net's negative tests (P846): each patch below, made in its subject's own process before a full-tier render,
changes one thing, and the net must report it against tests/golden. They prove that tests/test_golden.py's net catches a
changed colour, a moved sprite, a changed press timing, a changed cue, a change in a frame it does not pin, a swapped or
quieter cue and a moved game-over card. Every render here is full tier, whatever NET_TIER says, so the story run's fast
tier (NET_TIER=fast python3 -B -m unittest tests.test_golden) leaves this module out; the full suite and the full tier
run it. Run from the repository root: python3 -B -m unittest tests.test_golden_negative. --- MVP (P846) ---"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import net  # noqa: E402  first: it puts games/, the stubs and tools/ on the path

GOLDEN = os.path.join(HERE, "golden")
# Each negative test: a short subject, full tier, with one patch made in its process before the render; m is
# mac_host.modules()
COLOUR = "m.arcade2.Cave.bg = m.arcade2.c565(15, 10, 28)"  # its background, one step of blue more
MOVED = "m.arcade.Flappy.X = 81"  # the bird one px to the right
PRESS = "__import__('render_scene').SUBJECTS['flappy'].tap = 13"  # a tap every 13 frames, not 12
CUE = ("emit = m.arcade.Runner.emit\n"  # the jump says hop: a cue no table plays
       "m.arcade.Runner.emit = lambda self, name, value=None: emit(self, 'hop' if name == 'jump' else name, value)")
UNPINNED = ("draw = m.pictures.draw\n"  # one bird picture 1 px down: flappy draws it only in frames the net does not pin
            "m.pictures.draw = lambda cv, name, x, y, alpha=255: draw(cv, name, x, y + (name == 'flappy_bird00'), alpha)")
SWAPPED = "c = m.arcade.Runner.cues\nc['jump'], c['land'] = c['land'], c['jump']"  # each plays the other's sound
QUIETER = "m.arcade.Runner.cues['fire'] = m.cues.Cue('fire', m.arcade.FIRE_SOUND_GAIN // 2, True)"  # the fire at half
CARD = "m.arcade2.Stack.CARD_X += 1"  # stack's game-over card 1 px to the right
NEGATIVE = {"colour": ("cave", COLOUR), "moved": ("flappy", MOVED), "press": ("flappy", PRESS), "cue": ("runner", CUE),
            "unpinned": ("flappy", UNPINNED), "swapped": ("runner", SWAPPED), "quieter": ("runner", QUIETER),
            "card": ("stack_over", CARD)}


class NegativeTest(unittest.TestCase):
    """Each NEGATIVE patch, rendered at the full tier whatever NET_TIER says, is caught by the net."""

    @classmethod
    def setUpClass(cls):
        cls.golden = net.Golden.read(GOLDEN)
        net.Toolchain.here().check(cls.golden.meta)
        cls.negative = dict(zip(NEGATIVE, net.run([net.Job(name, net.FULL, patch) for name, patch in NEGATIVE.values()])))

    def caught(self, kind):
        name = NEGATIVE[kind][0]
        return net.differences(self.golden.subject(name, net.FULL), self.negative[kind])

    def test_a_changed_colour_is_caught(self):
        self.assertIn("frame 1 differs", self.caught("colour"))

    def test_a_moved_sprite_is_caught(self):
        self.assertTrue(any(d.startswith("frame ") for d in self.caught("moved")), self.caught("moved"))

    def test_a_changed_press_timing_is_caught(self):
        self.assertTrue(self.caught("press"))
        self.assertNotIn("frame 1 differs", self.caught("press"))  # the first press is the same: later frames differ

    def test_a_changed_cue_is_caught(self):
        self.assertIn("cues differ", [d.split(":")[0] for d in self.caught("cue")])

    def test_a_change_in_a_frame_the_net_does_not_pin_is_caught_by_the_run(self):
        found = self.caught("unpinned")
        self.assertIn("run differs", found)
        self.assertEqual([], [d for d in found if d.startswith("frame ")], "the shift reached a pinned frame")

    def test_a_swapped_cue_table_is_caught(self):
        found = self.caught("swapped")
        self.assertIn("cue table differs: jump, land", found)
        self.assertIn("sound differs", found)

    def test_a_quieter_cue_is_caught(self):
        found = self.caught("quieter")
        self.assertIn("cue table differs: fire", found)
        self.assertIn("sound differs", found)

    def test_a_moved_game_over_card_is_caught(self):
        card = self.golden.subjects["stack_over"]["over"][1]
        self.assertIn("frame %d differs" % card, self.caught("card"))


if __name__ == "__main__":
    unittest.main()
