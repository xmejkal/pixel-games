"""
Which sound a signal plays (P768). A game lists its cues in a class attribute, `cues`: signal name -> Cue. SoundCues
listens for them and plays each cue's sound from the bank on the mixer.
"""


# --- MVP (P768) ---
class Cue:
    """Value: one signal name tied to one sound of the bank."""

    def __init__(self, sound):
        self.sound = sound


class SoundCues:
    """The listener between a game's signals and the mixer. mixer: a sound.Mixer. bank: a bank.Bank."""

    def __init__(self, mixer, bank):
        self.mixer, self.bank, self.cues = mixer, bank, {}

    def stop(self):
        """The sound stops, and no cue plays until the next follow()."""
        self.cues = {}
        self.mixer.stop()

    def follow(self, game, signals):
        """This game's cues are listened for."""
        self.cues = game.cues
        for name in self.cues:
            signals.listen(name, self.on)

    def on(self, name, value):
        self.mixer.play(self.bank.get(self.cues[name].sound))
