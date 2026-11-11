# P767 A: how engines mix sounds and how a game starts them (finding for spark issue 1057)

Date: 2026-11-11. This is a finding with sources. It is not a design. Tags: [source] says what a page says,
[repo] says what the code shows, [inference] is my own reasoning. "Not confirmed" marks what I did not read.

## Short version

- Q1. Every system has voices, a few groups (buses) with one volume each, one master gain, and a rule for the full
  case. SoLoud kills the oldest voice and can protect some. Godot cuts off the oldest sound at max_polyphony.
  FMOD adds priority and a cap per event. SoLoud mixes in float and clips at the end. Godot says to keep the
  master below 0 dB and offers a hard limiter. Use few voices, one sum, one master and one clip at the end.
- Q2. A direct call is the base: miniaudio `ma_engine_play_sound`, Godot `play()`, SDL_mixer `MIX_PlayTrack`.
  FMOD sends events by name, but I did not read how. Music is a looping sound in its own group, with fades.
  Ducking is a sidechain effect on a bus (Godot, FMOD). Start with a direct call.

## Q1. Voices, groups, master, stealing and clipping

[repo] Today Mixer (games/sound.py, lines 24-54) holds one voice. The last play wins. MasterVolume is applied to
each block in Refill.render_block (line 83). More than one voice is "Later, not MVP" (lines 180-181).

| System | Voice | Group | Master | Full case | Clipping | Source |
|---|---|---|---|---|---|---|
| SoLoud | voice, 16 by default | bus | not read | kills oldest, protect | float, clip at end | [2] |
| Godot | one per play, max_polyphony | audio bus | Master bus | cuts off oldest | below 0 dB, limiter | [4] [5] |
| miniaudio | ma_sound | ma_sound_group | engine volume | not found | engine not confirmed | [3] |
| SDL_mixer 3 | MIX_Track | MIX_Group | mixer gain | not found | not found | [1] |
| FMOD Studio | event instance | bus | not read | priority, stealing mode | not read | [6] |

- [source] SoLoud: "Each of these sound instances is a "voice"." The default is 16 concurrent voices, and it
  "can be adjusted at runtime". Buses "let you mix together groups of audio streams", for example music against
  effects. [2] (sections: Voice, Mixing Bus)
- [source] SoLoud full case: it "finds the oldest voice and kills it". "you can protect channels from being
  killed by using the soloud.setProtect() call." "Protected voices are always played." [2] (section: Voice)
- [source] SoLoud clipping: it mixes in float and clips before output. "The roundoff clipper is used by default."
  A basic clipper exists. Then the page says to lower the global volume. It does not say "limiter". [2]
  (section: Clipping)
- [source] Godot: "Calling play() after this value is reached will cut off the oldest sounds." [4] (property
  max_polyphony)
- [source] Godot buses: any number of buses, each with effects "applied in order". Routing runs right to left, so
  no loop. A player names its bus. A missing name falls back to "Master". [5] (sections: Introduction, Adding
  effects, Playback routing)
- [source] Godot headroom: "0 dB is the maximum amplitude possible in a digital audio system." Signals above it
  clip. Keep the master mix below it. [5] (section: Decibel scale) An AudioEffectHardLimiter on Master is
  "probably better" than a compressor there. [7]
- [source] miniaudio: a group has "its own volume control and effect processing". `ma_engine_set_volume()` is a
  linear scale, 0 is silence and above 1 amplifies. [3] (sections: 1.2, 5)
- [source] miniaudio: its low-level device layer has a "built in clipping function" (noClip). [3] (section: 16.1)
- [source] SDL_mixer 3: a group callback gets "just that group's mixed audio" before the final mix. Gain calls
  exist for the mixer, a track and a tag. "There are no limits to the number of fire-and-forget sounds that can
  mix at once", "short of running out of memory". [1] (pages: MIX_Group, CategoryAPI, MIX_PlayAudio)
- [source] FMOD Studio: max instances caps one event. A stealing setting then picks oldest, quietest, virtualize
  or furthest. "None" means no new instance plays until one stops. A higher priority channel "can never be stolen
  by a lower priority Channel". Studio has five priority levels. [6] (sections: Max Instances, Virtual Voices)
- Not confirmed: SDL_mixer full-pool rule and clipping, miniaudio voice limit and engine clipping (70 000
  characters of its manual were cut off), FMOD clipping and master, Wwise (not searched).

| Option | What it is | Cost or risk | Fit here | Source |
|---|---|---|---|---|
| Fixed N voices, steal oldest | Take a free slot, else the oldest | Cuts a long sound | Simple | [2] [4] |
| Priority or protect | Each voice has a rank or a flag | One more field | Keeps the music | [2] [6] |
| Headroom, limiter | Lower each gain, limit the master | More code | C part later | [5] [7] |

- Recommendation: [inference] Take SoLoud's shape. Mixer holds a small fixed number of voices. A voice has a sound,
  a position, a loop flag, a gain and a group. A new play takes a free voice. If none is free, it steals the oldest
  voice that is not protected. The music voice is protected. Sum into a wide integer. Apply the group gain and
  then the master gain (MasterVolume). Clip to int16 once at the end. Keep one voice working in plain
  MicroPython (D26). The voice count is for the owner to test, and no source gave a value for this board.
- Names to take over: voice (SoLoud, FMOD), group (SDL_mixer, miniaudio, the owner's word) for the loudness group,
  master (Godot, MasterVolume), protect (SoLoud), polyphony (Godot), gain (SDL_mixer, miniaudio).
## Q2. Direct call or event, and background against event sounds

[repo] Today a game calls `mixer.play(sound, loop=False)` (games/sound.py, line 35). No game imports sound.py yet.

| Option | What it is | Cost or risk | Fit here | Source |
|---|---|---|---|---|
| Direct call | `play("jump")`, with or without a handle | Game knows the sound | Works now | [1] [3] [4] |
| Named event, table | The game sends a name. A table maps it | A table to keep | Later, with [8] | [6] |

- [source] miniaudio: `ma_engine_play_sound()` is "fire and forget", with a group parameter. [3] (sections: 1.2, 5)
- [source] SDL_mixer 3: fire and forget gives no handle, so you cannot stop it early. [1] (page: MIX_PlayAudio)
- [source] Godot: `play()` "Plays a sound from the beginning". Its `finished` signal says a sound ended. [4]
- [source] Fades: miniaudio has `ma_sound_set_fade_in_milliseconds()` [3] (section 5). SDL_mixer 3 has a fade-in
  property and lists no fade-out entry. [1] (page: CategoryAPI)
- [source] Godot ducking: the compressor's sidechain is the "Audio bus to use for the volume threshold
  detection". It is "common in video game mixing to decrease the volume of music and SFX while voices are being
  heard", "also known as "ducking"". [7] (section: Description)
- [source] FMOD: its sidechain modulator, for dB properties, "will only lower" a value. [6] (modulator reference)
- [inference] One music channel against many effect channels is the group split: music is one looped, protected
  voice, and effects are short, stealable voices. SoLoud names this as its bus example. [2]
- Not confirmed: how FMOD or Wwise start an event in code (the FMOD page fetched came back empty, Wwise not
  searched). Godot signals as a start method. SoLoud fade and loop. The cost of a level detector here.
- Recommendation: [inference] Use direct calls now. `play(name)` starts a short effect in the effects group with
  no handle. `music(name)` starts a looped, protected voice and returns a handle for fades. Fades are a linear
  gain ramp per block. Ducking is a plain rule, not a sidechain detector: while an effect voice plays, the music
  group gain falls to a set share, then a fade brings it back. A named event table can sit in front of `play`
  later, so the listeners in [8] call it with no change to Mixer. The share and the fade time are for the owner
  to set by ear. No source gave a value.
- Names to take over: play (miniaudio, Godot), stop (Godot), loop (SDL_mixer, Godot), fade (miniaudio,
  SDL_mixer), duck (Godot, FMOD), music (no system, my word), event (FMOD, only for the later table).
## Sources

1. SDL3_mixer wiki: https://wiki.libsdl.org/SDL3_mixer/CategoryAPI, .../MIX_Group, .../MIX_PlayAudio
2. SoLoud concepts: https://solhsa.com/soloud/concepts.html
3. miniaudio manual: https://miniaud.io/docs/manual/index.html
4. Godot AudioStreamPlayer: https://docs.godotengine.org/en/stable/classes/class_audiostreamplayer.html
5. Godot audio buses: https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html
6. FMOD, search results only: https://documentation.help/fmod-studio-api/virtualvoices.html,
   https://d1s9dnlmdewoh1.cloudfront.net/2.02/studio/modulator-reference.html
7. Godot AudioEffectCompressor: https://docs.godotengine.org/en/stable/classes/class_audioeffectcompressor.html
8. Sister finding: docs/discovery/2026-11-11-p766-panes-events/README.md
