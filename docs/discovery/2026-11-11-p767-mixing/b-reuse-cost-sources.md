# P767 part B: what to reuse, what mixing costs, where sounds come from (spark issue 1057)

Date: 2026-11-11. A finding with sources, not a design. Tags: [source] is what a page says, [repo] is what a file
or run shows, [inference] is my reasoning. "Not confirmed" marks what I did not read or no run measured.

## Short version

- Q3. Reuse no mixer code. Reuse the design of CircuitPython `audiomixer` and Espressif `esp_audio_render`. SoLoud,
  miniaudio and SDL_mixer are free to use, but their size and bare-metal fit are not confirmed.
- Q4. A C voice costs at most 413 to 979 us a block (runs 145b to 149d). A Python voice took 20.9 to 22.7 ms. No
  run summed N sampled voices.
- Q5. The repo has a CC0 fire recording and a bank loader. Kenney packs are CC0. jsfxr is Unlicense. Freesound
  needs a per-sound check.

## Q3. What can we reuse or extend

[repo] Our contract today: `Mixer.play(sound, loop)` and `render(buf)` (games/sound.py lines 24 to 54): "One voice:
the last play wins". It lists "more than one voice summed" as Later (lines 180 to 181). Drivers
`FrameRefill` (line 112) and `CallbackRefill` (line 149) call `render`.

| Option | Licence | Needs | Fit | Source |
|---|---|---|---|---|
| SoLoud | zlib/libpng | Backends, floats not stated | Design only | [1] [2] |
| miniaudio | public domain or MIT-0 | One C file. Bare-metal not stated | Not a fit | [3] |
| SDL_mixer | zlib | "requires SDL 3.4.0 or later" | Not a fit | [4] |
| esp_audio_render, esp_audio_effects | Not confirmed | ESP-IDF, ESP-GMF, tasks | Design only | [5] to [8] |
| CircuitPython audiomixer | MIT (CircuitPython repo, Not read) | CircuitPython core | Design only | [9] |
| micropython-i2s-examples | MIT | Plain MicroPython | Not a fit | [10] |

- [source] SoLoud: "8, 16, and 32-bit WAVs, floating-point WAVs, Ogg, and MP3". "New backends are easy to write".
  Code size, float use and a no-OS build are not stated on the page. [2] (home page).
- [source] SoLoud licence: "extremely liberal, no attribution in binary form is required". [1] (LICENSE).
- [source] miniaudio: "public domain or MIT No Attribution". One C file, "no dependencies
  except the standard library". On unlisted platforms "it will not include any support for playback or capture by
  default". A custom backend exists. Float use and size: Not confirmed, the page is silent. [3] (README).
- [source] SDL_mixer: zlib. Can mix "into a memory buffer", but needs SDL 3.4.0 or later. [4] (README).
- [source] `esp_audio_render` mixes "one or more PCM inputs" into a writer callback. It has stream gain and fade,
  a post-mix ALC or limiter, and "a mixer thread". It needs ESP-GMF and an ESP-IDF build. [5], [6] (Key Features).
- [source] `esp_audio_effects` Mixer: "independently configurable weights and smooth fade transitions", s16. "Most
  modules use less than 1% CPU" on an S3 at 240 MHz (not stated for the mixer). Licence: Not confirmed. [7] [8].
- [source] CircuitPython `audiomixer.Mixer(voice_count, buffer_size, channel_count, bits_per_sample,
  samples_signed, sample_rate)`. `play(sample, *, voice=0, loop=False)` does not block.
  `MixerVoice` has `level` (0 to 1), `loop`, `end()`, `stop()`, `playing`. [9].
- [source] micropython-i2s-examples lists a WAV player, a tone and a PWM master clock. No mixing example. [10].
- [inference] Our `Mixer` has the CircuitPython shape for one voice. The cheapest extension is `voice_count`
  voices with `play(sound, voice=0, loop=False)`, a per-voice level, and a master volume that already exists
  (games/volume.py). Keep `render(buf)` unchanged, so a C version can swap in behind it (naive path rule).
- Recommendation Q3 [inference]: reuse design and names only. Take `Mixer.voice[i].play/level/loop/end/stop` from
  CircuitPython and the "per-stream gain, post-mix limiter" split from esp_audio_render. Write the sum in our own
  small C function next to `fx_noise_mix`. Do not port a library.

## Q4. What mixing costs here

[repo] Numbers only from `bench.md` and the code. Block is 256 samples, 16 ms. Late means a refill over 48 ms.

| What | Result | Run |
|---|---|---|
| Plain Python `Crackle`, one voice | 20.9 to 22.7 ms a block, Fire never finished a frame | run145b, 5c |
| `SampledCrackle` (Mixer, FrameRefill 4096 B) | 24.15 fps, worst 70 ms, late 0, render at most 2.3 ms | run145e |
| Python volume scale, bytecode | 1220 us steady, 1644 us ramp, a block | run152 |
| Same, viper | 116 us a block | run155 |
| C `NativeCrackle` (one voice) | render at most 413 us, 24.00 fps, late 0 | run145b 5b |
| C `GrainCrackle` again | render at most 465 us, worst 74 ms, late 1 | run149a |
| C `FireSound` (pops + 8 noise voices) | render at most 693 us, 24 fps, late 0 | run149b |
| Same on BurningBodies | render at most 979 us, 23.05 fps, worst 89 ms | run149d |
| No sound control, Road | 18.7 fps, worst frame 134 ms | run144 entry 1 |
| `CallbackRefill` 2048 B in Road, tone | 18.9 fps, worst 126 ms, 0 gaps, wait at most 27 ms | run144 3d |

- [repo] FireSound's 8 whoosh voices are generated noise, not summed samples. They cost 693 to 979 us at -O2 on
  one function, "over the 1000 us line" at -Os (run148b: 948 to 1054 us). So a sum of 8 noise voices is near the
  budget, and sampled voices are not the same work.
- [repo] The submodule `engine/` is not checked out. Not confirmed: how `fx_noise.c` sums voices and clamps.
- Not measured yet, to make on the board (each with the same Fire and Road games, 120 s, `CallbackRefill` 2048 B):
  1. Plain-Python `Mixer.render` for one sampled voice, alone, in us a block, after `play`.
  2. Python sum of N = 2, 4, 8 sampled voices (a for-loop add and clamp).
  3. Viper and C sums of N = 2, 4, 8 voices, render_max in us, with the viper master volume behind them.
  4. Looping background plus event sounds from the `SoundBank` in PSRAM: render_max when a bank read misses cache.
  5. A play started while 4 voices run: the `pending` delay (play_between) and dropped plays.
  6. Road, the slowest game, with N voices: late refills, gaps heard, and GC time (slices allocate).
- Recommendation Q4 [inference]: run items 1 to 3 first and decide the voice count from them. One C voice fits
  with room, a Python voice did not (run145b). Keep the plain Python path working (D26).

## Q5. Where the sounds come from

[repo] What exists:
- `engine.SoundBank(nbytes)` holds samples in PSRAM, outside the GC heap. A bytearray bank cost 7657 us a
  `gc.collect()`, a `SoundBank` 102 us (run146b). The bank loads in 179 to 226 ms (P751).
- `tools/fire_bank.py` renders `games/fire_bank.raw` on the Mac: 246960 B, "a 6 s bed and 12 woody pops" (P751).
- `games/fire16k.wav` and `games/fire16k.SOURCE.txt`: "Fire Crackling" by AntumDeluge, OpenGameArt, 2013-05-10,
  CC0, converted to 16 kHz mono. Licence page named in the file: https://opengameart.org/content/fire-crackling.

| Source | Licence and where it is stated | Fit |
|---|---|---|
| Kenney audio packs | "Creative Commons CC0" on the pack page [11] | Good for press, hit, UI |
| freesound.org | Per sound. "for the 'zero' license you can do pretty much what you want" [12] | Per-file check |
| jsfxr (sfxr in HTML5) | UNLICENSE file in the repo [13]. Terms not on the page | Make jump, press, fall |
| OpenGameArt fire (in repo) | CC0 per the SOURCE file [repo] | Used now |

- [source] Kenney: the audio category lists "Interface Sounds", "Impact Sounds", "UI Audio", "Digital Audio", "RPG
  Audio" among others. Only Interface Sounds was read: "Creative Commons CC0", "100×" files. Other packs: Not
  confirmed. The footer says "All rights reserved", the pack page says CC0. Keep the pack link per file. [11].
- [source] Freesound FAQ: you "can't claim you are the author". Its filter "Free Cultural Works" returns "sounds
  under CC-BY or CC0", so it is not a CC0-only filter. A CC0-only filter was Not confirmed. [12].
- [source] jsfxr: "Dead easy game sound effects generator", a port of sfxr. The page did not list presets or
  output formats. Who owns generated sounds: Not confirmed. [13].
- Recommendation Q5 [inference]: make a `tools/sound_bank.py` in the style of `fire_bank.py`. It takes CC0 files
  (Kenney) and jsfxr output, resamples to 16 kHz mono, writes one bank file with an index, and adds a SOURCE.txt
  line per file with its licence URL. Load the bank into `SoundBank` once.

## Not confirmed

- Mixer library size, float need and no-OS builds. Espressif licences. Kenney packs but one. A CC0-only Freesound
  filter. jsfxr presets. Plain `Mixer.render` alone. Any sum of N sampled voices. C voice sums in `engine/`.

## Sources

1. https://raw.githubusercontent.com/jarikomppa/soloud/master/LICENSE (licence text)
2. https://solhsa.com/soloud/index.html (formats, backends, licence line)
3. https://github.com/mackron/miniaudio (README: licence, single file, platforms)
4. https://github.com/libsdl-org/SDL_mixer (README: zlib, SDL 3.4.0, memory buffer)
5. https://components.espressif.com/components/espressif/esp_audio_render (Key Features, Configuration)
6. https://docs.espressif.com/projects/esp-gmf/en/latest/gmf-framework/gmf-package/esp-audio-render.html
7. https://docs.espressif.com/projects/esp-adf/en/latest/basic-components/effects/esp-audio-effects.html
8. https://www.espressif.com/en/solutions/audio-solutions/esp-audio-effects (Audio Mixer specifications)
9. https://docs.circuitpython.org/en/latest/shared-bindings/audiomixer/index.html (Mixer, MixerVoice)
10. https://github.com/miketeachman/micropython-i2s-examples (examples list, MIT)
11. https://kenney.nl/assets/interface-sounds and https://kenney.nl/assets/category:Audio (licence line, pack list)
12. https://freesound.org/help/faq/ (CC0 text, licence filter)
13. https://github.com/grumdrig/jsfxr (description, UNLICENSE file)
14. https://creativecommons.org/publicdomain/zero/1.0/ (CC0 deed: "dedicated the work to the public domain")
