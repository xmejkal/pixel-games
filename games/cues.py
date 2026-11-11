"""
Which sound a signal plays (P768). A game lists its cues in a class attribute, `cues`: signal name -> Cue. SoundCues
listens for them and plays each cue's sound from the bank on the mixer.
"""

from sound import MUSIC, SFX
from volume import FULL

LEVELS = 256  # a looping cue's signal value: 0 (off) to LEVELS (the cue's gain)
MUSIC_SOUND = "music"  # the bank's background loop, the same in every game


# --- MVP (P768) ---
class Cue:
    """Value: one signal name tied to one sound of the bank. gain is Q15. A cue with `loop` is one voice that plays
    on: its signal carries a level, 0 to LEVELS, which scales the gain, and 0 ends the voice."""

    def __init__(self, sound, gain=FULL, loop=False, group=SFX):
        self.sound, self.gain, self.loop, self.group = sound, gain, loop, group


class SoundCues:
    """The listener between a game's signals and the mixer. mixer: a sound.Mixer. bank: a bank.Bank."""

    def __init__(self, mixer, bank):
        self.mixer, self.bank, self.cues, self.voices = mixer, bank, {}, {}
        self.music_voice = None

    def music(self):
        """The background music plays: one protected loop in the group music. It plays on over a switch of the
        game, so a second call does nothing. A bank with no music is a box with no music."""
        if self.music_voice is not None and self.music_voice.live:
            return
        try:
            sound = self.bank.get(MUSIC_SOUND)
        except KeyError:
            return
        self.music_voice = self.mixer.play(sound, True, MUSIC, FULL, True)

    def stop(self):
        """The game's sounds stop, and no cue plays until the next follow()."""
        self.cues, self.voices = {}, {}
        self.mixer.stop(SFX)

    def follow(self, game, signals):
        """This game's cues are listened for."""
        self.cues = game.cues
        for name in self.cues:
            signals.listen(name, self.on)

    def on(self, name, value):
        cue = self.cues[name]
        if not cue.loop:
            self.mixer.play(self.bank.get(cue.sound), False, cue.group, cue.gain)
            return
        gain, voice = cue.gain * value // LEVELS, self.voices.get(name)
        if voice is not None and voice.live:
            voice.gain = gain  # one store: the voice plays on at its new gain, and 0 ends it
            if voice.live or gain <= 0:
                return
        if gain > 0:  # also when a render ended the voice at its old gain of 0, just before the store  # protected, so a burst of short sounds never takes the loop's voice
            self.voices[name] = self.mixer.play(self.bank.get(cue.sound), True, cue.group, gain, True)
