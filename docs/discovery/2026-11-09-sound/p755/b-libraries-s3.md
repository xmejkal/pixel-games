# P755 part B: ready code, libraries and ESP32-S3 shortcuts

Marks: "read" = I opened the page. "snippet" = a search result only. "memory" = my own knowledge, not checked. 14 of 15 lookups used.

- No library gives a ready fire patch in integer C. DaisySP Particle (MIT) is the best idea to copy: random bursts into a band-pass. Port the method with integer xorshift and an integer filter.
- The S3 gives little for our small blocks. Its float biquad costs the same as on the old ESP32. Its 16-bit SIMD helps only in big loops, and the sources are thin.
- MicroPython runs on core 1. The idle core is core 0, so the audio task pins to core 0 (it shares it with Wi-Fi and IDF tasks).

## Libraries

| Name | What it gives us | License | Fits | URL | Status |
|---|---|---|---|---|---|
| DaisySP | Particle (random bursts into a band-pass: crackle), Dust, ClockedNoise, WhiteNoise, FractalNoise, one-pole LP/HP, SVF | MIT (read) | Copy the method. Code is C++ with float and libm (powf, sqrtf, rand), so it needs the firmware build or a rewrite to integer | https://github.com/electro-smith/DaisySP | repo page read, particle.cpp read |
| Mutable Instruments (eurorack, stmlib) | Fixed-point filters (SVF), noise, random-grain ideas | MIT for most code, with the hardware under CC (memory) | Code is integer-friendly C++. Copy single functions | https://github.com/pichenettes/eurorack | memory, not opened |
| STK | PhISEM shakers (particle collisions, decaying noise), Noise, OnePole, BiQuad | Free for use, credit asked, text is not a standard license (read: "made publicly available for free"), the file LICENSE is a MIT-style text (memory) | C++ with float or double. Take the PhISEM idea only | https://github.com/thestk/stk | repo page read, classes not listed there |
| Faust (libraries and compiler) | noise.lib, filters.lib, a C backend and ESP32 targets (faust2esp32) | Compiler GPL, with an exception for generated code, libraries mostly LGPL or MIT-style (memory, unchecked) | Generated C is float. It needs the firmware build | https://github.com/grame-cncm/faust | page read: it did not state licenses or faust2esp32 |
| hvcc (Heavy compiler) | Pd patch to C. A Farnell fire patch can become C | hvcc is GPL-3.0 (read). Generated code license: not stated, check before use | Output is float C with its own runtime. Firmware build, not natmod | https://github.com/Wasted-Audio/hvcc | repo page read, object support not seen |
| Mozzi | Arduino synth, fixed-point oscillators, filters, rand | LGPL (snippet-free, memory) | Arduino-bound. Take ideas only | https://github.com/sensorium/Mozzi | memory, not opened |
| Teensy Audio Library | Noise, filters, biquad in fixed point | MIT-style (memory) | Fixed-point int16 code is good to read for our integer filters, ARM DSP intrinsics do not port | https://github.com/PaulStoffregen/Audio | memory, not opened |
| SuperCollider UGens | Dust, Dust2, Crackle (chaotic noise), LPF, BPF | GPL v3 | Method only. Write our own code | https://github.com/supercollider/supercollider | memory, not opened |
| esp-dsp | Assembly dot product, FIR, FFT, biquad for ESP32-S3 | Apache-2.0 (read) | Firmware build only (an IDF component). A natmod cannot call it | https://github.com/espressif/esp-dsp | repo page read |

Rule from the project notes: the licenses marked memory need a check before any code is copied. Copy only MIT, BSD or Apache code. For GPL and LGPL code, copy the method and write our own code.

## ESP32-S3 DSP (esp-dsp and PIE)

- esp-dsp has float and int16 versions. The page says "many functions are written in assembly" (read). It does not list which are S3-only.
- Numbers, ESP32-S3, O2 (read, benchmarks page for the esp32 chip target):
  - dot product f32, 256 values: 432 cycles (old ESP32: 1047).
  - dot product s16, 256 values: 307 cycles (old ESP32: 437).
  - biquad f32, 1024 samples: 17552 cycles, about 17 per sample. Same as the old ESP32 (17442). The S3 has no gain here.
  - FIR f32, 1024 samples with 256 taps: 443671 cycles (old ESP32: 1078691).
  - FFT sc16 (int16), 256 points: 3412 cycles (old ESP32: 45746). This is the big S3 win, from SIMD.
  - The page has no rows for an int16 biquad, int16 FIR, or add and multiply.
- PIE is the S3 128-bit SIMD (eight int16 per register). A reader of the bitbank blog (read) found it "very minimal": 128-bit load and store, saturating add, multiply with accumulate. It has no 16-bit shift, no widening multiply, and no narrowing shift. Loads need 16-byte alignment for best speed. A 14 ms to 10 ms gain was seen in a JPEG loop. No cycle table exists in what I read.
- The Espressif PIE blog I read (developer.espressif.com/blog/2024/12/pie-introduction/) shows the P4 version (esp. names, RISC-V). Do not copy its code to the S3. The S3 names start with ee. (snippet).
- Calling PIE from C: use a separate .S file per function (bitbank, read) or inline asm. The sample file to copy is esp-dsp dsps_fft2r_sc16_aes3.S (bitbank, read). The assembler is in the IDF toolchain, so it fits the firmware build and the C user module. A natmod cannot use it.
- My view: a 256-sample block is small. A loop that mixes eight samples per instruction saves cycles in mixing and gain only. A recursive filter (one-pole, biquad) has a sample-to-sample dependency, so SIMD does not help one filter. When many voices or filters run side by side across lanes, SIMD helps. That is an inference, not a measurement.

## Core 1 (the second core)

- MicroPython pins its main task to core 1 on a dual-core build (snippet: MP_TASK_COREID is 1, or 0 on unicore, in ports/esp32/mphalport.h). The old reason: Wi-Fi and BLE run on core 0. So the free core is core 0, and the task pinned there shares it with Wi-Fi.
- Call xTaskCreatePinnedToCore(..., 0) from the C module (read in main.c: the port itself uses this call).
- The interpreter uses a GIL (snippet). Rule: the audio task runs pure C and never touches Python objects, never allocates from the MicroPython heap, never raises. Python writes parameters to a plain C struct. Use a small lock-free handoff (a sequence counter or a double buffer).
- Then no GIL is needed. The I2S write can use the IDF driver directly from the task. This replaces the scheduled callback and removes the 0.45 ms from the game core. (Inference.) Check that machine.I2S does not own the same port.
- Caveats found (snippet): a crash at task end when the task was not on the Python core. Never end the task by return. Loop forever, or delete it with a stop flag. One 2025 issue says xTaskCreatePinnedToCore was not declared in a newer IDF build (include freertos/FreeRTOS.h and task.h). Our IDF v5.5.2 needs a check.
- A task on core 0 touches PSRAM, which both cores share. Cache and bus contention are possible. Measure.
- I found no example of a MicroPython C module with its own pinned audio task. This design has no read example.

## Floats

- The S3 has a single-precision FPU (memory, ESP32-S3 TRM). One float multiply-add is a few cycles. Division, sqrt, pow, exp go to libm and cost tens to hundreds of cycles (memory).
- Read data: biquad f32 costs about 17 cycles per sample (read). An integer one-pole is about 3 to 6 cycles by my estimate, not measured here. So integer is cheaper per filter on tight loops. Float is simpler to write and tune.
- Natmods cannot call libgcc or libc and float is untested there (project note). In the C user module float works.
- Advice: keep the per-sample loop in integer (xorshift, one-pole, Q15 gain). Compute filter coefficients and gains per block (every 16 ms) in float or lookup tables. Floats at block rate cost almost nothing.
- Float helps where tuning matters: SVF coefficients (tan, exp) and heat-field mapping. Do these once per block.

## Sources

- https://github.com/espressif/esp-dsp (read)
- https://docs.espressif.com/projects/esp-dsp/en/latest/esp32/esp-dsp-benchmarks.html (read)
- https://github.com/electro-smith/DaisySP and /Source/Noise/particle.cpp (read)
- https://bitbanksoftware.blogspot.com/2024/01/surprise-esp32-s3-has-few-simd.html (read)
- https://developer.espressif.com/blog/2024/12/pie-introduction/ (read. P4 code)
- https://github.com/Wasted-Audio/hvcc , https://github.com/grame-cncm/faust , https://github.com/thestk/stk (read, thin)
- https://github.com/micropython/micropython/blob/master/ports/esp32/main.c (read). mphalport.h, mpthreadport.c and forum threads (snippet)
