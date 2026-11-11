# P767 part C: reuse, round 2 (spark issue 1057, question 3)

Date: 2026-11-11. Closes the gaps of b-reuse-cost-sources.md. Tags: [source] is what a page says, [repo] is what a
file shows, [inference] is my reasoning. "Not confirmed" marks what I did not read. No build was run.

Columns: a pull sum into our buffer. b gain, fades, loops. c clip or limiter. d links into the MicroPython build.
e integer or S3 float. f licence fits an open repo. g PIE use. h plain Python twin, sample for sample.

| Candidate | a | b | c | d | e | f | g | h |
|---|---|---|---|---|---|---|---|---|
| 1 esp-dsp | part [1,3] | gain only [3] | aes3 add only [4] | Not conf. | yes [1] | yes [5] | yes [3] | no [3] |
| 2 esp_audio_effects | yes [8] | yes [8] | ALC, Not conf. | Not conf. | Not conf. | no [6] | Not conf. | no [7] |
| 3 render, GMF, ADF | no [10] | yes [10] | yes [10] | Not conf. | Not conf. | Not conf. | Not conf. | Not conf. |
| 4 miniaudio | yes [11] | part [11] | Not conf. | Not conf. | no, f32 [11] | yes [R1] | no | Not conf. |
| 5 CP audiomixer | part [12] | yes [12] | yes [12] | no [12] | yes [12] | yes [12] | no [12] | yes [12] |
| 6 SoLoud | yes [13] | Not conf. | yes [13] | Not conf. | no, float [13] | yes [R1] | no | Not conf. |

R1 is the round-1 file, sources 1 to 4 there. Row 3 is mostly from one page, see its notes.

## Notes

### 1 esp-dsp
- [repo] Int16 functions exist: `dsps_add_s16` (ansi, ae32, aes3 files), `dsps_sub_s16` (same three),
  `dsps_mul_s16` (ansi, ae32, aes3), `dsps_mulc_s16` (ansi, ae32 only), `dsps_dotprod_s16` (ansi, ae32, arp4,
  no aes3 file). Paths are under modules/math and modules/dotprod/fixed in espressif/esp-dsp. [3]
- [repo] `dsps_add_s16_ansi.c` computes `acc = a + b` then `acc >> shift`. It has no clamp. `dsps_mulc_s16_ansi.c`
  computes `acc >> 15` with no clamp. `dsps_add_s16_aes3.S` uses `ee.vadds.s16`, which saturates. [3] [4]
- [inference] So ansi and aes3 add can differ on overflow. A Python twin must pick one. Whether the aes3 add keeps
  the `shift` argument: Not confirmed, I did not read the whole .S file.
- [source] Names: `_ansi` "a universal function", `_aes3` "written on ESP32S3 assembler". Types: "int16 for fixed
  point arithmetic and float". [1] Licence: Apache License 2.0, first lines of LICENSE. [5]
- No fades, loops or limiter. No call into it from MicroPython was tried: Not confirmed.

### 2 esp_audio_effects
- [repo] Binary only. CMakeLists uses `add_prebuilt_library(... libesp_audio_effects.a)`. A `lib/esp32s3/` folder
  holds `libesp_audio_effects.a`. No .c source is in the component. [7]
- [source] `esp_ae_mixer.h`: `esp_ae_mixer_open`, `esp_ae_mixer_set_mode`, `esp_ae_mixer_process(handle,
  sample_num, ...)`. Weights, `transit_time`, 16, 24, 32 bit. No task appears in the header lines I read. [8]
- [source] Licence "Espressif Modified MIT License". Rule 1: "MUST BE USED IN CONJUNCTION WITH ESPRESSIF SYSTEMS
  PRODUCTS". Rule 3: "Redistribution ... FOR USE WITH NON-ESPRESSIF PRODUCTS is strictly prohibited". [6]
- [source] Registry: v1.4.5, "Supports all targets", S3 listed (for v1.4.0). Tags include mixer, fade, drc. [9]
- [inference] Legal on an S3, but a binary cannot sit in an open repo as a twin base, and its rounding is unseen.

### 3 esp_audio_render, ESP-GMF, ESP-ADF
- [source] esp_audio_render: mixing, then "deliver final PCM to the application via a writer callback". I2S is a
  sink "such as I2S, Bluetooth sink, or network streaming" that you connect. So I2S can stay with machine.I2S [10]
- [source] The page does not say whether it makes its own tasks, and states no licence. Built from "ESP-GMF
  elements". [10] Round 1 read "a mixer thread" on another page (R1 source 5).
- ESP-ADF and ESP-GMF core: I read no page this round. Tasks, I2S ownership and licence: Not confirmed.
- [inference] It is a pipeline framework with a push writer, not a call that fills our buffer.

### 4 miniaudio
- [repo] miniaudio.h: `MA_NO_DEVICE_IO` "Disables playback and recording. This will disable `ma_context` and
  `ma_device` APIs." `noDevice` config: "ma_engine_read_pcm_frames() can be called manually to read data". [11]
- [repo] Other cut options: `MA_NO_RESOURCE_MANAGER`, `MA_NO_NODE_GRAPH`, `MA_NO_ENGINE`, `MA_NO_GENERATION`,
  `MA_NO_DECODING`. `MA_NO_THREADING` "cannot be used without MA_NO_DEVICE_IO". [11]
- [repo] The engine is float: `ma_engine_process_proc` takes `float* pFramesOut`, and the fader uses
  `ma_format_f32`. Whether `read_pcm_frames` accepts s16 output: Not confirmed. A size figure: none seen. [11]

### 5 CircuitPython audiomixer
- [repo] shared-module/audiomixer/Mixer.c: "SPDX-License-Identifier: MIT", copyright Adafruit. Gain is 16 bit with
  1.0 as `1 << 15`, sample times gain, shift right 15. Float only in the synthio path. [12]
- [repo] Clip: `add16signed` clamps to `SHRT_MAX` and `SHRT_MIN` (ARM DSP uses `__QADD16`). `mult16signed` clamps
  the same way. The fallback is plain C. [12]
- [repo] Ties: `audiomixer_mixer_get_buffer()` follows the sample get-buffer protocol, calls
  `audiosample_get_buffer()` on each voice, uses `m_malloc_without_collect()`. Port work: replace those. [12]

### 6 SoLoud
- [repo] C++ (repo says "portable c/c++ audio engine"). `Soloud::mix(float *aBuffer, unsigned int aSamples)` and
  `mixSigned16(short *aBuffer, ...)` are public in include/soloud.h. `clip_internal` works on float buffers. [13]
- [repo] A null backend exists: src/backend/null/soloud_null.cpp, `null_init` ends with `postinit_internal(...)`.
  So a backend needs an init that sets rate, buffer and channels, then something that calls `mix`. [13]
- Voice gain, fade, loop, code size, C++ runtime need on the S3: Not confirmed, not read.

## Recommendation [inference]

- Reuse as code: esp-dsp `dsps_add_s16_aes3` and `dsps_mul_s16_aes3` as an optional fast path. Apache-2.0, S3
  assembly, int16. Keep our own `ansi`-style C sum as the default. Match the twin to one saturation rule.
- Reuse as design: CircuitPython gain `1 << 15`, multiply then `>> 15`, clamp after each add, voice and level API.
  MIT, so the C idea can be copied with the header kept. Also the render gain, fade, limiter split.
- Leave: esp_audio_effects (binary, Espressif-only), esp_audio_render and GMF (framework), miniaudio and SoLoud
  (float, large engines, C++ for SoLoud), ADF.
- Honest limit: esp-dsp has no fade, loop, limiter or voice list. We write those, about 50 lines of C.

## Only a build trial can answer

1. Does esp-dsp link as an ESP-IDF 5.5 component inside `build.sh` with the MicroPython S3 image, and its size?
2. us per 256-sample block for `dsps_add_s16_aes3` against our C loop, for N = 2, 4, 8 voices.
3. Does `aes3` add match the `ansi` add and a Python twin on overflow inputs, and with which `shift`?
4. Does `ee.vadds.s16` need 16-byte aligned buffers, and are our bufs aligned?
5. Does miniaudio with `MA_NO_DEVICE_IO` and `noDevice` compile for xtensa, with what size and s16 output?
6. Does SoLoud compile as a user C module with C++ enabled in this build, and what size?
7. Is float in the render path fast enough on the S3, and does a Python twin match it sample for sample?

## Sources

1. https://docs.espressif.com/projects/esp-dsp/en/latest/esp32/esp-dsp-library.html (Function Naming)
2. https://docs.espressif.com/projects/esp-dsp/en/latest/esp32/esp-dsp-apis.html#basic-math
3. https://github.com/espressif/esp-dsp (modules/math/{add,sub,mul,mulc}/fixed, modules/dotprod/fixed)
4. https://documentation.espressif.com/esp32-s3_technical_reference_manual_en.html (1.5.4, EE.VADDS.S16)
5. https://raw.githubusercontent.com/espressif/esp-dsp/master/LICENSE
6. https://raw.githubusercontent.com/espressif/esp-adf-libs/master/esp_audio_effects/LICENSE
7. https://github.com/espressif/esp-adf-libs/tree/master/esp_audio_effects (CMakeLists.txt, lib/esp32s3)
8. https://raw.githubusercontent.com/espressif/esp-adf-libs/master/esp_audio_effects/include/esp_ae_mixer.h
9. https://components.espressif.com/components/espressif/esp_audio_effects
10. https://docs.espressif.com/projects/esp-gmf/en/latest/gmf-framework/gmf-package/esp-audio-render.html
11. https://github.com/mackron/miniaudio (miniaudio.h, build options table, engine section)
12. https://github.com/adafruit/circuitpython/blob/main/shared-module/audiomixer/Mixer.c
13. https://github.com/jarikomppa/soloud (include/soloud.h, src/core/soloud.cpp, src/backend/null/soloud_null.cpp)
