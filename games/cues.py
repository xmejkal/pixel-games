"""
Which sound a signal plays (P768). A game lists its cues in a class attribute, `cues`: signal name -> Cue. SoundCues
listens for them and plays each cue's sound from the bank on the mixer.
"""

from sound import SFX
from volume import FULL

LEVELS = 256  # a looping cue's signal value: 0 (off) to LEVELS (the cue's gain)


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
        elif gain > 0:  # protected, so a burst of short sounds never takes the loop's voice
            self.voices[name] = self.mixer.play(self.bank.get(cue.sound), True, cue.group, gain, True)
