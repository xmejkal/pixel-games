# P755 finding: how to model fire sound on our S3, and what to take from others (spike, #1038)

> 1. Fire sound is noise shaped by the fire's numbers. No tool or paper gives a ready fire synth, but the parts are known and cheap: a roar, a hiss, a whoosh per moving body and a flare thump.
> 2. Take methods, not code: garjan's roar and crackle rates, Farnell's hiss bursts, Plaits Particle (MIT), the puffing law f = 1.5 / sqrt(D). Our own integer C stays the code.
> 3. The S3 is not the limit for P753. SIMD, esp-dsp and core 0 help later, for P749's many voices. First slice: one smooth roar that follows the fire's size and flicker.

All layers together cost an estimated 0.2 to 0.6 ms per 16 ms block, next to today's measured 0.45 ms. So P753 needs no S3 tricks, and it keeps the plain integer C of our engine. With many voices (P749), the S3's SIMD helps. If the render grows or the game's Python delays the callback, core 0 helps. Two council claims were wrong: PIE has a widening multiply-accumulate, and hvcc states its output license. One more was partly wrong: the Mutable Instruments license.

I did not listen. I have no way to. All claims about sound are design, not ear. The PO decides by ear.

## 1. The fire model we take, layer by layer

Drivers from P750 come from scans of the heat array, with no kernel change: total heat, hot area, flame height, heat change. The game gives the rest: wind (`FirePlugin.wind`), and body speed, trail burn and flare radius (`burning.py`).
Cost: one 16 ms block is 256 samples. The S3 runs at 240 MHz (stock SPIRAM_OCT build), so a block is 3.84 M cycles. Today's render is 0.45 ms, about 420 cycles a sample. That is far above a bare cycle count, so each estimate below takes the high end.

| Layer | Driver from the field | Method | Source | Cost per block (estimate) |
|---|---|---|---|---|
| Roar | level: total heat. cutoff: flame height (150 to 600 Hz, our speaker passes little under 200 Hz). flutter: the change of flame height each step, so it moves with the picture | white noise, 2 integer one-pole low-passes, a Q15 gain set once a block. The engine has this roar already (`fx_crackle.c`, `roar1`, `roar2`), but its cutoff is a shift (steps of 2x). Use a Q15 coefficient for a smooth cutoff | garjan roar: brown noise, low-pass 600 Hz, level 0.3 x intensity (read). Farnell lapping (P750). Chadwick and James: low band follows heat release (P750) | 0.03 to 0.1 ms |
| Flicker rate | hot-area width as a size in "virtual metres" (our constant) | the field's own flicker drives the flutter. If its spectrum has no 1 to 5 Hz puff, add a smooth swell at f = 1.5 / sqrt(D) Hz: 4.7 Hz at 0.1 m, 1.5 Hz at 1 m, 0.75 Hz at 4 m | Cetegen and Ahmed 1993, read in Xia and Zhang 2018 (arXiv 1803.10400, p. 10): f = 0.48 sqrt(g/D) = 1.5 sqrt(1/D). Other authors give 1.5 to 1.68 | about 0 (one rate a block) |
| Hiss | level: hot area. burst density: heat change | high-passed noise times (slow noise)^4, soft and dense, so it reads as texture and not as events | Farnell (P750, read) | 0.03 to 0.1 ms |
| Wind on the flames | level and gust: `FirePlugin.wind` and its rise | a gust lifts the roar level a little and the flutter depth, and opens the hiss. Plus a wind bed: noise through one band-pass whose centre (300 to 800 Hz) and level follow the wind, smoothed per block | no source for wind on flame sound (council searched, none found). Wind bed: Farnell's wind (snippet only). This layer is our design | 0.03 to 0.08 ms |
| Whoosh of a moving burning body | relative airspeed s = abs(body velocity minus wind), and the body's own fire size (trail heat) | white noise, one integer state-variable band-pass (Chamberlin form). Centre rises with s (clamp 300 to 2500 Hz). Level rises with s squared times its fire size. Set per block, so no clicks. Into the wind, s is large: louder and brighter. With the wind, s is small: quiet | whoosh recipe (violetrecording, snippet). Dobashi 2003: texture rate follows object or wind speed (snippet). Relative airflow: our design, answers the PO's "against the wind" | 0.03 to 0.06 ms per body, cap at 4 bodies |
| Flare "whoomp" | a flare event in `burning.py` (flare radius), seen on screen | 150 ms noise burst, low-pass swept 400 to 100 Hz, plus an 80 to 120 Hz sine thump. Level from flare radius. A sharp sound is allowed here, because the eye sees the event | explosion recipe (part C, snippet). P750 design | 0.02 ms while it plays |
| Pops (have) | ember births and their rise speed | PSRAM bank grains, approved in sync | P751 | today's 0.45 ms |

Total of the new layers: 0.15 to 0.6 ms a block, estimate. Measure each layer in C against the 0.45 ms baseline before the next one.

Rule kept from the board: only a seen event makes a sharp sound (pops, flare). Every other layer is smooth and follows its number. This rules out two shortcuts as they stand. garjan's crackle (Poisson clicks, 5 + 30 x intensity a second) and Plaits Particle make random clicks with no event on screen. Use them only as the sound of an event we trigger, or so dense that they become hiss. The same holds for a grain bed cut from a crackling recording: cut the bed grains from parts with no crackle.

## 2. Shortcuts to take, with licenses

| Shortcut | What we take | License | Take |
|---|---|---|---|
| garjan fire.rs | roar recipe, crackle rate law 5 + 30 x intensity per second, 5 to 30 sample linear decay, high-pass 2 kHz | crate license not read | method only |
| Farnell, Designing Sound | hiss as noise x (slow noise)^4, lapping, causal linkage of layers | book. Patch files not opened | method only |
| Plaits / DaisySP Particle | random impulses (probability per sample) into a resonant band-pass whose centre jumps on a sample-and-hold | MIT (read: DaisySP LICENSE and the Plaits header, Emilie Gillet 2016) | method. Code is float with powf, sqrtf and rand, so we write it in integer. Copy is allowed with the notice |
| Mutable Instruments stmlib, Plaits SVF | reference for the state-variable filter | MIT for the STM32 projects, GPL-3.0 for the AVR projects (README read) | method, from STM32 code only |
| STK PhISEM shakers | random events, decaying energy, resonators: rain, sparks (later) | MIT-style (LICENSE read) | method, or code with the notice |
| esp-dsp | FFT sc16, dot product s16, and its `.S` files as PIE examples | Apache-2.0 (read) | later, linked into the firmware C module. Not in a natmod |
| hvcc (Pd to C) | render a Farnell Pd patch to C to prototype on the Mac | compiler GPL-3.0. Its static runtime is ISC. Generated files carry a header you set with `--copyright` (docs read) | later, Mac only. Its output is float with its own runtime, too heavy for our block |
| Chadwick and James 2011 | high band as noise with spectrum f^-alpha, alpha 2.2 to 3.4 | paper | method, later with the S3 FFT |

## 3. How to use the S3

| Feature | Where it helps | Where not | Verdict |
|---|---|---|---|
| Integer per-sample loop (xorshift, one-pole, Q15 gain) | every layer. Same style as `fx_grains.c`. Also builds as a natmod (no libgcc) | none | use now |
| Float | coefficient maps once a block, in the firmware C module only | per-sample loops. esp-dsp's float biquad costs about 17 cycles a sample on the S3. The old ESP32 costs the same (17,552 vs 17,442 cycles for 1024 samples, read) | later, block rate only |
| PSRAM | sample banks (pops today, bed grains, other sounds) | hot filter state: keep it in internal RAM | use now |
| PIE SIMD (128-bit, 8 x int16) | mixing many voices and Q15 gain on 8 samples at once: `EE.VMUL.S16` forms the 32-bit product and shifts it by SAR, `EE.VADDS.S16` adds with saturation, `EE.VMULAS.S16.QACC` accumulates into eight 40-bit lanes (TRM read) | one recursive filter (each sample needs the last one). A few layers: mixing 256 samples is a few hundred cycles, nothing to save | later, for P749 (8 to 16 voices in lanes). Needs a `.S` file in the firmware module |
| esp-dsp FFT sc16 | 256 points in 3,412 cycles on the S3 vs 45,746 on the ESP32 (read), about 14 us at 240 MHz. Shaped f^-alpha noise, one inverse FFT a block | P753's layers need no FFT | later |
| Core 0 | moves the render off the game's core, and the audio no longer waits for bytecodes or GC | P753 alone: 0.45 to 1 ms of 16 ms fits on core 1 | later. Trigger: P749's render passes about 2 ms, or underruns are heard |

What core 0 takes (read in MicroPython v1.29.0): the MicroPython task runs on core 1 (`mphalport.h` line 54, `MP_TASK_COREID` 1 on a dual-core build, used in `main.c` line 285). machine.I2S's own write task also runs on core 1 (`machine_i2s.c` lines 449 to 456). That task calls the Python callback through `mp_sched_schedule` (lines 261 to 275). machine.I2S keeps its channel handle inside its Python object, and it has no C call for another task. So a core 0 task can not feed machine.I2S. It needs its own IDF channel (`i2s_new_channel`, `i2s_channel_init_std_mode`, `i2s_channel_write`) on a port that machine.I2S does not open. The GIL is on (`MICROPY_PY_THREAD_GIL` 1), so the task touches no Python object: Python writes numbers into a plain C struct, and births go through a lock-free ring. machine.I2S with the scheduled callback stays as the naive path behind the same interface.

## 4. Other sounds for later

| Sound | Model | Driver | Cost (estimate) | Ready method |
|---|---|---|---|---|
| Wind | noise, 1 to 3 band-passes, slow moving centre | wind speed | cheap | Farnell (snippet) |
| Rain, sparks | random events into resonators, decaying energy (PhISEM) | drops a second | cheap | STK, MIT-style |
| Water drop | decaying sine at the bubble's frequency, pitch rises a little | splash size | cheap per drop | van den Doel 2005 (snippet) |
| Impact | 4 to 12 decaying modes, struck by collision speed | each seen collision | medium, cap 8 to 16 voices, SIMD later | modal (van den Doel, Kry, Pai 2001, snippet). DaisySP, MIT |
| Explosion | noise burst, falling low-pass, low thump, tail | blast size | cheap | recipe only |
| Engine | harmonics of the firing rate, or a PSRAM grain loop | speed, throttle | cheap to medium | ghurni is GPL-3.0: method only |
| Whoosh | band-pass sweep by speed | speed of a seen pass | cheap | as the body whoosh above |

## 5. First slice for P753, ranked

1. **Roar that follows the fire's size and flicker.** Add the smooth roar under the approved pops. Level from total heat, cutoff from flame height, flutter from the step-to-step change of flame height. No kernel change. The PO hears a bigger fire get louder and darker, and the roar breathe with the flames. One layer, one measurement against 0.45 ms.
2. Wind on the flames: gusts lift the roar and open a soft wind bed.
3. Whoosh of a moving burning body, from relative airspeed. Needs the body's speed from `burning.py` into the sound.
4. Flare whoomp on the seen flare.
5. Hiss, last, because its bursts risk sounding like random events.

Before slice 1 is built: measure the flicker spectrum of flame height in the Mac twin (one script, no board). If it has no 1 to 5 Hz puff, the roar's flutter needs the 1.5 / sqrt(D) swell.

## 6. Open questions for the PO

1. "Against the wind": we propose louder and brighter into the wind, quieter with it. Agreed?
2. "How big the burning fire is": the whole fire drives the roar, and each body's own fire drives its whoosh. Agreed?
3. Order: roar, then wind, then the moving bodies, then the flare. Agreed?
4. A synthetic roar first, or a grain bed cut from a recording with no crackles in it? The synthetic one has no random sharp sounds.
5. Core 0 and SIMD wait for P749. Agreed, or do you want one S3 feature in P753 itself?

## 7. Refuter table

| Claim | Source read | Verdict |
|---|---|---|
| Puffing f = 1.5 / sqrt(D), D in m, f in Hz (Cetegen and Ahmed 1993) | arXiv 1803.10400 p. 10 (read): f = 0.48 sqrt(g/D), g = 9.8 m/s^2, "equivalent to f = 1.5 sqrt(1/D)" | confirmed. It is a visual flicker law for pool fires. Using it for sound is our choice. Other fits give 1.5 to 1.68 (search result) |
| garjan: brown noise, LP 600 Hz Q 0.7, level 0.3 x intensity. Crackle 5 + 30 x intensity per s, 10 ms blocks, 5 to 30 samples, linear decay, HP 2 kHz. Hiss missing, DC blocker | docs.rs fire.rs (read) | confirmed, all numbers. Fix: the crackle HP has Q 1.0. Crate license not read |
| DaisySP Particle: random bursts into a band-pass, MIT | particle.cpp, particle.h, LICENSE (read) | confirmed. Fix: it is Emilie Gillet's Plaits code (MIT). Density is a trigger chance per sample, the centre jumps on a sample-and-hold, default resonance 0.9 |
| esp-dsp S3 cycles: dotprod f32 432, s16 307, biquad f32 17,552, FIR f32 443,671, FFT sc16 3,412 | esp-dsp benchmarks page (read) | confirmed. Fix: the page has columns for ESP32, ESP32-S3 and ESP32-P4. It is not "for the esp32 target" only |
| PIE has no 16-bit shift | ESP32-S3 TRM via Espressif docs (read): shifts are `EE.VSL.32`, `EE.VSR.32` | confirmed |
| PIE has no widening multiply, no narrowing shift (bitbank) | TRM: `EE.VMULAS.S16.QACC` into 40-bit lanes, `EE.VMUL.S16` shifts the 32-bit product by SAR, `EE.SRCMB.S16.QACC` narrows with shift and saturation | wrong for audio. No widening into a Q register, but Q15 gain and wide accumulate exist |
| MicroPython's task runs on core 1, core 0 is free | local `mphalport.h` 51 to 55, `main.c` 285 | confirmed. With Wi-Fi on, its tasks share core 0 |
| A C task on core 0 can write I2S with the IDF driver, and machine.I2S must not own the port | local `machine_i2s.c` | confirmed by reading. It can not feed machine.I2S itself. No running example exists |
| `xTaskCreatePinnedToCore` not declared in a newer IDF | local `main.c` 285 builds on IDF v5.5.2 | does not apply to our build |
| hvcc: generated code license not stated | hvcc docs, Licensing (read) | wrong. Static runtime ISC, generated files carry your own `--copyright` header |
| Mutable Instruments: MIT for most code | eurorack README (read) | partly wrong. MIT for STM32 projects, GPL-3.0 for AVR projects |
| STK is MIT-style | STK LICENSE (read) | confirmed |
| Flame noise peaks 200 to 800 Hz, wood flames under 100 Hz | snippets only | unverified. No decision rests on it: our speaker sets the band |
| Aeolian tone f = St x v / d, St near 0.2 | researcher's memory | unverified. We use "centre rises with speed" only |
| Nemisindo and Wwise parameter names | pages gave 404 and 403 | unverified |
