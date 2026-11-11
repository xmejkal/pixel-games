"""The mixer's voices on the Mac (P768): the slots, the groups, the gains, the clip, and the viper sum against the
plain one. Run from the repository root: python3 -B -m unittest tests.test_voices. --- MVP (P768) ---"""

import os
import sys
import unittest
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "games"))

import sound_viper  # noqa: E402
from bank import BankSound  # noqa: E402
from sound import MUSIC, SFX, Mixer, VoiceSum  # noqa: E402
from sound_viper import ViperVoiceSum  # noqa: E402
from volume import FULL  # noqa: E402


class Ptr:
    """Viper's ptr16 and ptr32 on the Mac: a ptr16 read is unsigned, and a store keeps the low bits."""

    def __init__(self, buf, code, mask):
        self.view, self.mask = memoryview(buf).cast("B").cast(code), mask

    def __getitem__(self, i):
        return self.view[i]

    def __setitem__(self, i, value):
        self.view[i] = value & self.mask if self.mask else value


sound_viper.ptr16 = lambda buf: Ptr(buf, "H", 0xFFFF)
sound_viper.ptr32 = lambda buf: Ptr(buf, "i", 0)

HALF = FULL // 2


def rendered(mixer, n=8):
    buf = array("h", [9] * n)
    mixer.render(buf)
    return list(buf)


class TestVoices(unittest.TestCase):
    def sums(self):
        return (VoiceSum(), ViperVoiceSum())

    def test_two_voices_are_summed_with_their_gains(self):
        for voice_sum in self.sums():
            mixer = Mixer(2, voice_sum)
            mixer.play(array("h", [100, 200, 300]))
            mixer.play(array("h", [10, -20, 30, -40]), gain=HALF)
            self.assertEqual(rendered(mixer), [105, 190, 315, -20, 0, 0, 0, 0])
            self.assertEqual(mixer.voices, [None, None])

    def test_the_sum_clips_once_to_16_bits(self):
        for voice_sum in self.sums():
            mixer = Mixer(4, voice_sum)
            for _ in range(3):
                mixer.play(array("h", [30000, -30000]), loop=True)
            self.assertEqual(rendered(mixer, 8)[:4], [32767, -32768, 32767, -32768])

    def test_the_viper_sum_gives_the_plain_samples_on_each_named_block(self):
        self.assertTrue(sound_viper.sum_match())

    def test_a_bank_sound_plays_as_an_array_does(self):
        samples = array("h", [1000, -1000, 32767, -32768, 5])
        mem = bytearray(bytes(6) + bytes(samples) + bytes(2))
        sound = BankSound(mem, memoryview(mem), 3, 5)
        self.assertEqual(list(sound[i] for i in range(len(sound))), list(samples))
        for voice_sum in self.sums():
            mixer = Mixer(1, voice_sum)
            mixer.play(sound, loop=True)
            self.assertEqual(rendered(mixer), [1000, -1000, 32767, -32768, 5, 1000, -1000, 32767])

    def test_a_full_mixer_gives_the_oldest_voice_to_a_new_play(self):
        mixer = Mixer(2)
        first = mixer.play(array("h", [1] * 20))
        second = mixer.play(array("h", [10] * 20))
        third = mixer.play(array("h", [100] * 20))
        self.assertEqual((first.live, second.live, third.live), (False, True, True))
        self.assertEqual(rendered(mixer, 8), [110] * 8)

    def test_a_protected_voice_stays_and_a_mixer_of_protected_voices_plays_nothing_new(self):
        mixer = Mixer(2)
        music = mixer.play(array("h", [1] * 4), loop=True, group=MUSIC, protect=True)
        mixer.play(array("h", [10] * 20))
        mixer.play(array("h", [100] * 20))
        self.assertTrue(music.live)
        self.assertEqual(rendered(mixer), [101] * 8)
        mixer = Mixer(1)
        mixer.play(array("h", [1] * 4), loop=True, protect=True)
        self.assertIsNone(mixer.play(array("h", [100] * 20)))
        self.assertEqual(rendered(mixer), [1] * 8)

    def test_stop_ends_one_group_or_all(self):
        mixer = Mixer(3)
        music = mixer.play(array("h", [1] * 4), loop=True, group=MUSIC)
        jump = mixer.play(array("h", [10] * 20))
        mixer.stop(SFX)
        self.assertEqual((music.live, jump.live), (True, False))
        self.assertEqual(rendered(mixer), [1] * 8)
        mixer.stop()
        self.assertEqual(rendered(mixer), [0] * 8)

    def test_a_voice_gain_changes_while_it_plays_and_gain_0_ends_it(self):
        mixer = Mixer(2)
        fire = mixer.play(array("h", [1000] * 4), loop=True, gain=HALF)
        self.assertEqual(rendered(mixer), [500] * 8)
        fire.gain = FULL // 4
        self.assertEqual(rendered(mixer), [250] * 8)
        fire.gain = 0
        self.assertEqual(rendered(mixer), [0] * 8)
        self.assertFalse(fire.live)
        self.assertEqual(mixer.voices, [None, None])

    def test_a_group_gain_scales_its_voices_and_0_keeps_them_alive(self):
        mixer = Mixer(2)
        music = mixer.play(array("h", [1000] * 4), loop=True, group=MUSIC)
        mixer.play(array("h", [10] * 4), loop=True)
        mixer.group_gain[MUSIC] = HALF
        self.assertEqual(rendered(mixer), [510] * 8)
        mixer.group_gain[MUSIC] = 0
        self.assertEqual(rendered(mixer), [10] * 8)
        self.assertTrue(music.live)

    def test_a_gain_over_full_is_full(self):
        mixer = Mixer(1)
        mixer.play(array("h", [1000] * 8), gain=4 * FULL)
        self.assertEqual(rendered(mixer), [1000] * 8)

    def test_play_returns_its_voice_and_pending_holds_it_until_the_render(self):
        mixer = Mixer(2)
        voice = mixer.play(array("h", [1] * 4))
        self.assertIs(mixer.pending, voice)
        rendered(mixer)
        self.assertIsNone(mixer.pending)
        self.assertFalse(voice.live)
        mixer.stop()
        self.assertIsNone(mixer.pending)  # a stop is no play


if __name__ == "__main__":
    unittest.main()
