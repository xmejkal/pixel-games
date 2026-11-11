# Sound in the game box (P768)

The short version: a game says what happened, and the box plays the sound. The music plays in every game.

```mermaid
flowchart LR
  G[game: self.emit 'jump'] --> S[Signals]
  S --> C[SoundCues: the game's cues]
  A[App.switch] -- "cues.music()" --> C
  B[Bank: box_bank.raw] --> C
  C --> M[Mixer: 4 voices, groups music and sfx]
  M --> V[MasterVolume: the knob] --> R[CallbackRefill] --> I[I2S, MAX98357]
```

## Give a game a sound

1. Add the sound to `SOUNDS` in `tools/sound_bank.py`: a name, the samples and the source with its license.
2. Run `python3 tools/sound_bank.py`. It writes `games/box_bank.raw`, `games/box_bank.py` and
   `games/box_bank.SOURCES.md`. Add `--wav DIR` to hear each sound on the Mac.
3. Name the cue in the game: `cues = {"jump": Cue("jump")}`.
4. Emit the signal where it happens: `self.emit("jump")`.
5. Copy `box_bank.raw`, `box_bank.py` and the game's file to the board.

`Game.die()` emits `die`. A game with no cues is silent, and a game with no `signals` (a test) runs as before.

## A sound that plays on

A cue with `loop=True` is one voice that plays on, as the fire of `Runner`: `"fire": Cue("fire", loop=True)`. Its
signal carries a level from 0 to 256: `self.emit("fire", self.fire_k)`. The level scales the cue's gain, and 0 ends
the voice. Emit 0 where the game ends, because `play` does not run after a death.

`Marshmallow` (P773) does the same with the bank as it is: `serve` plays `pickup`, `burn` plays `land`, and `flame`
is the `fire` loop. Its level is the flame's height, `top_px * LEVELS // FLAME_MAX_PX`, sent when it moved by at
least `FLAME_STEP` (16). The game emits `flame` with 0 before `die()` and at the start of each round.

## The music

`App.switch` calls `cues.music()`. It starts the bank's sound `music` once, as a protected loop in the group
`music`, and the loop plays on over a switch of the game. `mixer.group_gain["music"]` is its gain (Q15), apart from
the game sounds' `mixer.group_gain["sfx"]`. A bank with no `music` gives a box with no music.

The music is a note list in `tools/sound_bank.py`: `THEMES` holds two candidates, and `MUSIC` names the one in the
bank. To change the tune, edit the notes or `MUSIC`, and run the tool.

## The voices

The `Speaker` has 4 voices. The music and a looping cue are protected. A new sound takes a free voice, or else the
oldest voice that is not protected. `sound.VoiceSum` is the plain MicroPython sum and always works.
`sound_viper.ViperVoiceSum` gives the same samples faster, and the `Speaker` uses it when it imports.

## What it costs

See bench.md, P768. The sound with the music costs each of the 14 games at most 1 fps.
