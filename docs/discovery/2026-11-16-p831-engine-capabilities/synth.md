# P831: a one-handed synthesizer on the game box (preliminary note)

Date: 2026-11-16. A preliminary note for spike P831 (spark issue 1192), not a design and with no code. The PO's words:
"a synthesizer, like a one handed musical instrument using the esp's built in optimized effects library for dsp".
Tags: [source] says what a page says, [repo] what the code or a run shows, [inference] is reasoning. "Not confirmed"
marks what nobody read or ran.

## TL;DR

> The box can be a one-handed instrument: the joystick sets pitch and filter, the button plays, the knob picks the
> sound. The CPU is not the problem: one note with an envelope and a filter costs a few percent of one core
> [inference]. Two things need care: the press-to-sound delay (the sound ring is 64 ms today) and linking esp-dsp into
> the firmware (not tried). esp-dsp is filters, transforms and vector math, not a synth and not an effects pack.

Summary. A monophonic subtractive synth (one oscillator, an ADSR envelope, a low-pass filter, an echo) fits the existing
16 kHz mixer path and is best written as one small C voice in the engine, as the crackle and the noise already are.
esp-dsp adds a tested biquad filter with its coefficient maker, and a very fast 16-bit FFT for a spectrum on the
screen. Its filters are not faster than plain C on the S3, so the library is a convenience here, not a speed-up. The
smallest first step is one probe that renders one voice into the I2S and measures the time per block and the delay.

## The instrument with the box's controls

| Control | Does | Why |
|---|---|---|
| Joystick up/down | Pitch, snapped to a scale (for example a pentatonic scale, so no note sounds wrong) | One hand can hit notes with a stick only if the steps are wide [inference] |
| Joystick left/right | Filter cutoff (the "wah"), and the knob-picked patch fixes how far it goes | The classic one-hand gesture |
| Button D14 | The gate: down = note on, up = note off (the envelope's release) | One bit, no timing skill needed |
| Knob | The patch: waveform, envelope, echo on or off. The volume pane shows its name | The PO's "knob for the sound" |
| Screen | A spectrum or the note and cutoff as a bar | Cheap, see "what esp-dsp gives" |

[repo] The joystick pads A0, A1 and D5 (GPIO 4, 5, 7) are kept free in `docs/wiring.html`; the drawer holds two
PS2-style analog sticks, one in the box project. The knob is the volume today (P764), so the instrument mode must take
it over or leave the volume where it is (decision 3). BOOT stays untouched.

## The signal chain (industry names)

Subtractive synthesis, the common design [source: any synth text; no single page cited]:

```
MIDI-style note number -> oscillator (VCO) -> filter (VCF) -> amp (VCA) -> effect -> master gain -> I2S
   joystick Y            saw/square/tri      low-pass, cutoff   ADSR       echo        the knob's
                                             (joystick X), Q    envelope   (delay)     MasterVolume
```

- Oscillator: a phase accumulator (a counter that adds a step per sample) and a table lookup. Pitch = step size.
  At 16 kHz the top is 8 kHz; a naive saw aliases (folds high notes back as noise), so use a wavetable per octave or
  PolyBLEP (a small correction at each jump) [inference].
- Envelope: ADSR (attack, decay, sustain, release), a gain that moves per block or per sample, fixed-point.
- Filter: a biquad low-pass (two poles) with a cutoff and Q (resonance). A state-variable filter is the other
  common choice and is simpler to sweep.
- Effect: an echo is a ring buffer of past samples mixed back; a tremolo is a slow LFO on the gain. Neither is in esp-dsp.
- The sum and the master gain exist: `games/sound.py`, `games/volume_viper.py`. The synth is one more voice.

## What runs in C and what in Python

- [repo] Today: 16 kHz mono, a 256-sample block (16 ms), the I2S ring of 2048 bytes (64 ms), refilled from the I2S
  callback, which runs at a bytecode boundary and never inside a C call such as the display send (`games/sound.py`).
  The frame is about 40 ms (24 fps) and the screen send is long, so sound must not wait for the frame.
- [repo] Costs measured in P767: one C voice at most 413 us per 16 ms block; a sampled voice in the Python `Mixer`
  2.3 ms; a Python generator 21 to 23 ms (too slow). So per-sample work belongs in C (or viper at the least).
- Recommended split [inference]: Python once per frame (or per block) reads the joystick, button and knob, and passes
  numbers (note, cutoff, gate, patch) to the C voice. C renders each 256-sample block: oscillator, envelope, filter,
  echo. Python never touches a sample. This is the shape of `engine.SoundBank` and the C crackle.
- Why not pure viper: viper can do the oscillator and envelope, but a filter and an echo need floats or careful
  fixed-point, and the C path is already proven in the engine. Not measured for a synth.
- Why not ulab: [source] ulab (MIT, v6.12.1) has `scipy.signal.sosfilt`, but it works on whole arrays and allocates,
  and the filter state is the caller's problem. It adds a module for one function. Not confirmed on this build.

## What esp-dsp gives and what it does not

[source] esp-dsp (Apache-2.0, tags up to v1.8.2, an ESP-IDF component; github.com/espressif/esp-dsp,
docs/en/esp-dsp-benchmarks.rst on master, read 2026-11-16) lists these on ESP32-S3, in CPU cycles, optimized (O2):

| Function | Cycles | Reading at 240 MHz [inference] |
|---|---|---|
| `dsps_biquad_f32`, 1024 samples | 17552 (ESP32: 17442; plain C: 26651) | 17 per sample; 256 samples = 18 us |
| `dsps_fir_f32`, 1024 samples, 256 taps | 443671 (plain C: 1353122) | 433 per sample, 3x faster than C |
| `dsps_fft2r_sc16`, 256 complex points | 3412 (plain C: 46164) | 14 us, 13x faster |
| `dsps_fft2r_fc32`, 256 complex points | 20139 (plain C: 36066) | 84 us |
| `dsps_dotprod_s16`, 256 points | 307 (plain C: 3635) | 1.3 us |

- Gives: biquad IIR in float with ten coefficient makers (low-pass, high-pass, band-pass, notch, peaking EQ, shelves,
  all-pass: `dsps_biquad_gen_*_f32`); FIR; FFT, with a real S3 speed-up only in the 16-bit version; vector add, multiply
  and dot product in 16-bit (P767 already looked at these); windows; a tone generator (`dsps_tone_gen`, a sine test
  tone, not an instrument oscillator). [source: the same repository, `modules/`.]
- Does not give: an oscillator bank, an envelope, a synth voice, a delay or reverb, a mixer. "Effects library" in the PO's
  words is a fair guess at the idea, but the library holds no effects [source: its API list].
- The honest surprise: the biquad is not faster on the S3 than on the original ESP32 (17552 against 17442 cycles). It
  is a chain where each sample needs the last, so SIMD does not help [inference]. A 20-line fixed-point biquad in C
  would cost about the same. The S3's SIMD pays off in the FFT, the FIR and the vector math. So the first real use for
  the instrument is the filter's tested coefficients (cutoff and Q to numbers) and a spectrum on the screen.
- [source] The biquad is float only (`f32`), so the C voice converts int16 to float and back, which adds a little [inference].

## How it gets into the firmware

[repo] `build.sh engine` builds MicroPython v1.29.0 with ESP-IDF v5.5.2 and `USER_C_MODULES` pointing at
`micropython.cmake`, which includes `engine/micropython.cmake`. The engine is a user C module. [source] esp-dsp is an
IDF component, normally added with `idf.py add-dependency "espressif/esp-dsp"`; MicroPython's port lists its own
components in `ports/esp32/main/idf_component.yml` (mdns, tinyusb, v1.29.0, read on this Mac).
Two ways, both not tried:
1. Add `espressif/esp-dsp` to that file (a change to the MicroPython tree, not to spark) and call it from the engine.
   The cost is the image size and the build time; the component manager would fetch it at build time, so no vendor
   file enters the repository (AGENTS.md).
2. Copy the few source files the engine needs into the engine. Apache-2.0 allows it with the notice, but spark's rule
   is to commit no vendor file, so this is the second choice.
Not confirmed: that esp-dsp builds under IDF 5.5.2 inside the MicroPython build, its size, and whether it needs
`-DCONFIG_DSP_OPTIMIZED` or a similar setting.

## Existing projects (design only, none read in full)

| Project | License [source: GitHub API] | Use |
|---|---|---|
| Mozzi (sensorium/Mozzi, v2.0.4) | LGPL-2.1 | Arduino synth library; good for names and ideas. LGPL on a flashed binary is a burden; do not copy |
| marcel-licence/esp32_basic_synth | GPL-3.0 | ESP32 with I2S and MIDI; GPL does not fit MIT spark; read for the design only |
| marcel-licence/ML_SynthTools | GPL-3.0 | Same |
| roolin/micropython-microsynth | GPL-3.0 | A MicroPython synth; 0 stars, not read |
Recommendation: reuse none as code. Write the voice from the textbook design (above), as the P767 note did for the mixer.

## The smallest first experiment (call it P831-S)

1. A probe on the box, no game: a C function `render(buf, note, cutoff_q, gate)` with a saw oscillator, an ADSR and a
   one-pole low-pass (own code, no esp-dsp yet). The `CallbackRefill` calls it per 256-sample block.
2. Joystick on A0 and A1 through `machine.ADC`, the button D14. Hear it: this is the PO's ear test.
3. Measure: us per block for the voice, with and without the screen running (the PSRAM copy for the display competes
   for the bus [repo, bench.md: about 32 ms of CPU copy per frame]); late refills (P767 counts them).
4. Measure the delay from the button press to the first non-zero sample queued, and add the ring's queued samples
   (64 ms ring = at most 64 ms). Test a ring of two buffers (32 ms) too. The true press-to-ear delay needs a phone
   recording or the microphone, which is not wired yet (pads A3, A5, A4 are "later"); say so in the result.
5. Then step two: link esp-dsp, swap in `dsps_biquad_f32` with `dsps_biquad_gen_lpf_f32`, and put a `dsps_fft2r_sc16`
   spectrum on the screen. Compare the biquad cost with step one's filter; measure the image size.
Pass (an inference to confirm): block time under 2 ms with the screen on, no late refill, press-to-sound under about 50 ms.

## What it would add to the engine for the games

- Filtered sound effects: a low-pass on every sound when the game pauses or the player is hit; a ducking pad.
- Pitch from one sample: step the playing position by a ratio, so one jump sound gives a rising scale.
- A music sequencer: a list of (note, length) per voice, a tempo, a voice per track; chiptune music without a recording.
  The same C voice, driven by a list instead of the joystick.
- The joystick as an engine input (a card of its own, named in the engine's risks list), and the spectrum as a visual.
- Generalizing: the engine gets a `Voice` kind "synth" beside "sampled" in the existing `Mixer`, so games call
  `play_note(n, patch)`.

## Risks

- Delay: the 64 ms ring plus a 40 ms input poll could make the instrument feel late. Poll the button in the refill
  callback, not the frame; shorten the ring for the instrument only.
- The callback cannot run during a C call such as `show()` (P767), so a long screen send eats the ring.
- Aliasing and a tinny 16 kHz sound; the small speaker hides some. A higher rate costs CPU in the mixer.
- Joystick: the ADC is noisy, the centre drifts; the engine's risk list already asks for a centre and dead-zone
  measurement in place (R6).
- Linking esp-dsp: build, size and the licence notice. GPL projects must not be copied into MIT spark.
- The knob's pads RX and TX are taken from the console at game start; the instrument must do the same (P758).

## Open decisions for the PO

1. Does the synth go first, after ESP-NOW or after the joystick card? Recommended: after the joystick card, since the
   stick is its main input and serves the games too; the synth is a small probe and the joystick is its prerequisite.
2. Use esp-dsp or our own C filter? Recommended: our own one-pole filter for experiment 1, esp-dsp in step two, and
   keep it only if the link is cheap; its win is the FFT and the coefficient makers, not speed.
3. What does the knob do in instrument mode? Recommended: the patch, with the volume fixed at the saved step, and a
   long press (not needed for the probe) back to volume later.
4. Sample rate: stay at 16 kHz? Recommended: yes for the probe, try 22.05 or 32 kHz only if the PO hears the aliasing.
5. Monophonic or poly? Recommended: mono (one hand), but the voice is a class, so the sequencer can run several.
6. Is the delay target of 50 ms right? Recommended: yes as the first bar, then the PO's feel judges it (a feel slice).

## Not sourced

Nothing measured on the box for the synth; the cycle counts are Espressif's, taken on its test, and the clock of 240 MHz
is assumed. The size and the build of esp-dsp inside MicroPython, ulab on this build, and the contents of the GitHub
projects are not confirmed. The textbook synth design is general knowledge, with no page cited.
