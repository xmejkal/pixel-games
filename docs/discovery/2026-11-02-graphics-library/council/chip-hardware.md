# P539 council: chip hardware for 2D graphics (S3, P4, other ESP32, RP2040/RP2350)

Researcher: chip-hardware seat, 2026-11-02, 12:37 to about 13:25 Europe/Prague. Read only. This file is the only write.
Tags: E = read, with a pointer. H = hypothesis, with its origin. D = decision, with who and when. — = unknown.
"Read 2026-11-02" applies to every URL below unless a different date is given. Speed-ups name their baseline, because
most published numbers compare against a plain C loop, not against newlib `memcpy` or an optimised C loop.

Downloaded and kept in the session scratchpad only (not in the repo):

| document | URL | printed version | sha256 |
|---|---|---|---|
| ESP32-S3 TRM | https://www.espressif.com/sites/default/files/documentation/esp32-s3_technical_reference_manual_en.pdf | Version 1.8 (PDF dated 2026-03-04), 1531 pages | 4484bf8a69035ec42a731c58c64ada6fbd1f1618c5559409f134d9ea083f444f |
| RP2040 datasheet | https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf (redirects to pip.raspberrypi.com RP-008371-DS) | PDF dated 2025-02-20, 642 pages | be56fbb75ba0ae9e26558a73c93ac3e75c2ad4e6878d3b6703de2a76d886ea8c |
| RP2350 datasheet | https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf | build date 01/10/2026, build version 80d627281ed5, 1371 pages | a638d6780da919162660691bfa02c6dcf7c2a0b6e9f18e2d7519c80b664a2e39 |

Page numbers below are the printed page numbers of these files, unless marked "PDF p".

## 1. Findings

### 1.0 The five that matter most

- **HW-1** (E+H). On the PO's S3 today, no special hardware addresses the current limit. The paint is 34 ms a frame for runner at a
  40 ms pace, and it is Python call overhead, not pixel loops (bench.md:116, p537-finding.md:7). The largest published PIE
  gain is the RGB565 copy, 9.8 x against LVGL's ANSI C. On a whole 320 x 240 frame it saves about 1 to 1.5 ms (computed in HW-S3-9). The
  arithmetic is E. "The paint is call overhead" is H, from the P537 finding's phase maxima, which are not averages.
- **HW-2** (E). The cheapest S3 PIE code to reuse is Espressif's own assembly in esp_lvgl_port: RGB565 fill, RGB565 copy
  ("blend normal" with full opacity and no mask) and a memcpy macro file, under Apache-2.0. It is self-contained Xtensa
  windowed-ABI code (`entry a1, 32` … `retw.n`, no includes) that takes a 9-word descriptor struct. Measured on the S3 against
  LVGL's ANSI C, in cycles per pixel: fill 0.196 vs 1.146 (16-byte aligned 128 x 128), 0.497 vs 1.124 (1-byte aligned
  127 x 127). Copy: 0.352 vs 3.437 (aligned) and 0.866 vs 5.978 (unaligned). esp_lvgl_port builds it only for LVGL
  9.1.x and only on ESP32 and S3. LVGL master has no Xtensa or PIE backend.
- **HW-3** (E). Colour-key blit and alpha blend have PIE instructions that fit but no published Espressif number. The TRM has
  `EE.VCMP.EQ.S16`, eight 16-bit equal compares into 0xFFFF/0 masks (TRM §1.8.79 p155). It has `EE.ANDQ`/`EE.ORQ`/`EE.NOTQ`
  (p52) and unaligned loads (`EE.LD.128.USAR.IP` + `EE.SRC.Q`, p47–48). One third-party RGB565 PIE blend exists
  (BitsForPeople `rgb565_s3_simd.hpp`, C++ inline asm). It states "about 90-100 CPU clock cycles" for 16 pixels, "about 5x"
  over scalar. That is stated, not measured by us, and the file is **GPL-3.0**, so it cannot be copied into an MIT library.
- **HW-4** (E). On the ESP32-P4 the special hardware is a driver call, not assembly. PPA (`ppa_do_fill`,
  `ppa_do_blend` with colour key, `ppa_do_scale_rotate_mirror` with byte swap) and 2D-DMA through
  `esp_lcd_dpi_panel_enable_dma2d()` / `esp_lcd_rgb_panel_enable_dma2d()`. LVGL's PPA draw unit hands the PPA only opaque
  fills with no radius and no gradient, plus (behind a Kconfig) unscaled, unrotated, opaque RGB565/RGB888 images. It runs blocking
  (`LV_PPA_NONBLOCKING_OPS 0`). Espressif publishes no PPA timing. It says the time "is proportional to the amount of the data in
  the block" and drops with PSRAM contention.
- **HW-5** (E). On RP2040/RP2350 the graphics hardware is the SIO interpolator (two per core, "single cycle iteration" for
  affine texture mapping, RP2040 datasheet §2.3.1.6.5 p41) and PIO. PicoSystem's PIO program clocks pixels to the ST7789.
  It doubles each pixel and each line on the wire, from a 120 x 120 framebuffer to a 240 x 240 panel. It drops the 4 alpha bits.
  The CPU does no work per pixel for this. MicroPython's rp2 port exposes PIO and DMA (`rp2_pio.c`, `rp2_dma.c`) and enables both inline
  Thumb and inline RV32 assemblers. The esp32 port enables neither inline assembler.

### 1.1 ESP32-S3

| ID | claim | tag | pointer | supports only |
|---|---|---|---|---|
| HW-S3-1 | PIE has eight 128-bit QR registers (16 x 8, 8 x 16 or 4 x 32 bit lanes). It has sixteen 8-bit and eight 16-bit multipliers. It has two 160-bit accumulators QACC_H/QACC_L and one 40-bit ACCX | E | S3 TRM v1.8 §1.2–1.3.1 p39–40 | what the unit holds |
| HW-S3-2 | PIE memory access forces alignment: the low 4 address bits of a 128-bit access are replaced by 0, so an unaligned pointer reads the wrong data silently. Use `aligned(16)` or `heap_caps_aligned_alloc`. Unaligned data goes through `EE.LD.128.USAR.IP` (sets SAR_BYTE) + `EE.VLD.128.IP` + `EE.SRC.Q` | E | TRM §1.5 p47–48. esp-dl cheat sheet https://github.com/espressif/esp-dl/blob/master/tools/agents/skills/esp32s3-pie-simd/SKILL.md | alignment rule and the unaligned pattern |
| HW-S3-3 | `EE.VCMP.EQ.S16 qa, qx, qy` writes 0xFFFF per equal 16-bit lane, else 0. The instruction word is 24 bits | E | TRM §1.8.79 p155 | the colour-key compare exists (the esp-dl cheat sheet lists only S8 compares. The TRM has S16 and S32 EQ) |
| HW-S3-4 | Vector shifts `EE.VSL.32`/`EE.VSR.32` work on 32-bit lanes only, by the low 5 bits of SAR. `EE.VSR.32` is arithmetic. `EE.VMUL.S16`/`.U16` shift the product right by SAR and truncate | E | TRM p47 (SAR text), §EE.VSL.32 p53, EE.VMUL.S16 p198, EE.VMUL.U16 p204. Cheat sheet | RGB565 channel split needs a 32-bit shift plus a mask. No 16-bit shift |
| HW-S3-5 | `EE.VZIP.8/16/32` and `EE.VUNZIP.8/16/32` interleave and de-interleave two QR registers in place | E | TRM EE.VUNZIP.8 p292, EE.VZIP.8 p295 | — |
| HW-S3-6 | A possible RGB565 byte swap in PIE: `EE.VUNZIP.8` (split low and high bytes) then `EE.VZIP.8` with the operands swapped, 16 pixels per pair | H | derived from HW-S3-5 semantics, not run, no published code found | an idea to bench, not a fact |
| HW-S3-7 | Author's limits list for S3 SIMD: no logical right shift, no 8/16-bit shifts, no widening add/multiply, no narrowing shift, no non-saturating add/sub, no unaligned access. Each function in its own `.S` file. 14 ms to 10 ms for JPEGDEC's YCbCr-to-RGB (1.4 x throughput, data size not stated) | E (stated by the author) | Larry Bank, 2024-01-22, https://bitbanksoftware.blogspot.com/2024/01/surprise-esp32-s3-has-few-simd.html | the instruction set is narrow. One field speed-up on colour conversion |
| HW-S3-8 | esp_lvgl_port SIMD test, ESP32-S3, cycles per sample, PIE asm vs LVGL ANSI C. Fill RGB565: 0.196 vs 1.146 (128 x 128, 16-byte aligned) = 5.8 x, and 0.497 vs 1.124 (127 x 127, 1-byte) = 2.3 x. Fill ARGB8888: 0.327 vs 1.600 and 0.488 vs 1.597. Copy RGB565: 0.352 vs 3.437 (aligned) = 9.8 x, and 0.866 vs 5.978 (127 x 128, 1-byte) = 6.9 x. Copy RGB888: 0.744 vs 4.002. LVGL version, CPU clock, run count and compiler flags are not stated | E (measured by Espressif, one table) | https://github.com/espressif/esp-bsp/blob/master/components/esp_lvgl_port/test_apps/simd/README.md | the speed-up of the primitive over ANSI C, not over newlib memcpy |
| HW-S3-9 | Frame-sized effect: 320 x 240 = 76,800 px. Fill: 88,013 cycles (C) vs 15,053 (PIE) = 0.37 vs 0.06 ms at 240 MHz, or 0.55 vs 0.09 ms at 160 MHz. Copy: 263,962 vs 27,034 cycles = 1.10 vs 0.11 ms at 240 MHz, or 1.65 vs 0.17 ms at 160 MHz | E for the arithmetic from HW-S3-8. H for the clock (the build's CPU MHz not read) and for internal SRAM | computed here | the ceiling of what PIE fill/copy saves per full frame |
| HW-S3-10 | esp_lvgl_port SIMD files: `lv_color_blend_to_{rgb565,rgb888,argb8888}_esp32s3.S`, `lv_rgb565_blend_normal_to_rgb565_esp32s3.S`, `lv_rgb888_blend_normal_to_rgb888_esp32s3.S`, `lv_macro_memcpy.S`, plus `_esp32.S` twins for the classic ESP32. The build includes them only for 9.1.0 ≤ LVGL < 9.2.0 and the targets ESP32 and ESP32-S3. SPDX Apache-2.0 | E | `gh api repos/espressif/esp-bsp/contents/components/esp_lvgl_port/src/lvgl9/simd`. CMakeLists.txt lines 110–122 at commit 058d2aaa1a (2026-08-03) | what exists to port, and its licence |
| HW-S3-11 | The RGB565 fill asm reads `dst_buf, dst_w, dst_h, dst_stride, src_buf(colour)` from a struct at offsets 4–20, uses `entry a1,32`/`retw.n` and has no includes. Its aligned inner loop is `loopnez a9, …; ee.vst.128.ip q0, a3, 16` (8 px per store). It falls back to 4-byte and 1-byte paths | E | `lv_color_blend_to_rgb565_esp32s3.S` lines 11–113 (fetched via gh api) | it can be called from plain C with our own struct, no LVGL headers |
| HW-S3-12 | The RGB565 copy asm handles opa and mask fields as unused. The C shim passes only dst/src/w/h/strides. The unaligned path uses `ee.ld.128.usar.ip` + `ee.src.q.ld.ip`, three registers rotating | E | `lv_rgb565_blend_normal_to_rgb565_esp32s3.S` lines 23–31, 95–178. `esp_lvgl_port_lv_blend.h` lines 118–131 | it is a plain rectangle copy, no key, no alpha |
| HW-S3-13 | GCC accepts PIE mnemonics in C/C++ inline asm (`asm("EE.VLD.128.IP q0, %[src1], 16" …)`), and ESP-IDF says "PIE instructions set is currently only supported in GCC compiler". No intrinsics or auto-vectorisation are documented | E | BitsForPeople `rgb565_s3_simd.hpp` lines 196–230 (GPL-3.0, read only). esp-idf `components/freertos/test_apps/freertos/port/test_pie_in_task.c` header comment. PIE blog https://developer.espressif.com/blog/2024/12/pie-introduction/ | inline asm and `.S` are both possible. Clang is not |
| HW-S3-14 | Third-party RGB565 PIE helpers (from565, blend with alphaQ8, to565 with optional BYTESWAP) exist in C++ templates with inline asm. Stated cost: 16 px blend in about 90–100 cycles, about 5 x scalar | E (stated, field) | https://github.com/CubeCoders/Jet/discussions/10 (post dated 2026-10-15). File https://github.com/BitsForPeople/esp-bits-and-pieces/blob/master/esp32-s3/rgb565/rgb565_s3_simd.hpp, licence GPL-3.0 (`gh api repos/BitsForPeople/esp-bits-and-pieces --jq .license.spdx_id`), pushed 2026-10-17 | a blend in PIE is feasible. The code is not reusable under MIT |
| HW-S3-15 | `MALLOC_CAP_SIMD` returns memory accessible by SIMD instructions, aligned to 16 bytes | E | https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/mem_alloc.html#special-capabilities | how to allocate PIE buffers |
| HW-S3-16 | PIE context on the S3 is saved by the Xtensa coprocessor macros: `xchal_cp_cop_ai_store` saves ACCX, QACC, SAR_BYTE, UA_STATE and q0–q7 (208 bytes). Whether the S3 switch is lazy and pins the task, as documented for P4 and S31, is not stated on the S3 FreeRTOS page | E for the macro. H for the lazy, pinning behaviour on S3 | esp-idf `components/xtensa/esp32s3/include/xtensa/config/tie-asm.h` L275–343. S3 FreeRTOS page shows only "Floating Point Usage" | PIE use from a task is supported. PIE in an ISR is not to be assumed |
| HW-S3-17 | With dual-core FreeRTOS, MicroPython's esp32 task is pinned to core 1. Core 0 holds Wi-Fi/BLE and system tasks | E | micropython `ports/esp32/mphalport.h` lines 46–55. `main.c:291` | H, not tried: a C worker task pinned to core 0 renders or converts while Python runs on core 1 |
| HW-S3-18 | GDMA memory-to-memory `esp_async_memcpy` runs beside the CPU. Its callback is in an ISR, and the CPU does the unaligned edges. Espressif calls DMA to PSRAM very limited | E | P537 finding p537-finding.md:102, which cites https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/async_memcpy.html | — |
| HW-S3-19 | Forum benchmarks: async_memcpy IRAM to IRAM about 57 MB/s vs memcpy about 364 MB/s. PSRAM to IRAM async about 52 vs memcpy about 39 MB/s. A tuned SIMD loop is claimed at about 1.41–1.9 GB/s internal | H (field, from the search summary. The forum page returned a bot check and was not read) | esp32.com thread "ESP32-S3 - esp_async_memcpy not working with PSRAM using GDMA", https://esp32.com/viewtopic.php?p=123534 | GDMA is no win for internal copies. Maybe a small one for PSRAM to internal |
| HW-S3-20 | The S3 has no 2D or strided DMA and no pixel accelerator. PPA and 2D-DMA are P4 (and S31) only | E | p537-finding.md:103 (P4 datasheet p64, GMF note). LVGL espressif draw unit is PPA only (HW-P4-5) | — |
| HW-S3-21 | ESP-IDF v5.5.2 SPI master has no `SPI_TRANS_DMA_USE_PSRAM`. A PSRAM tx buffer is re-allocated in internal DMA memory and copied by the driver. IDF master adds `SPI_TRANS_DMA_USE_PSRAM (1<<12)` for direct EDMA from PSRAM, bandwidth shared with the MSPI bus, "otherwise transmission data may be lost" | E | `gh api …/esp_driver_spi/include/driver/spi_master.h?ref=v5.5.2` (line 119 only) vs `ref=master` line 120. https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/spi_master.html#transactions-with-data-on-psram. `spi_common.c` L442–507 `spicommon_dma_setup_priv_buffer` | on today's build a PSRAM framebuffer always costs a CPU copy into internal RAM. A later IDF can skip it |
| HW-S3-22 | Espressif's LCD FAQ says "SPI DMA can't directly transfer PSRAM data" and recommends a PSRAM framebuffer copied in batches through a small SRAM buffer | E | https://docs.espressif.com/projects/esp-faq/en/latest/software-framework/peripherals/lcd.html | conflicts with HW-S3-21 for IDF master. True for v5.5.2 |
| HW-S3-23 | Bench: in "strips" mode about 32 ms per frame went to the CPU copy and byte swap of each strip out of PSRAM. The real SPI clock is 40 MHz (80 MHz set as 60 MHz), and the panel stays dark at 80 MHz. A full frame is 31.0 ms of wire time | E | bench.md:32–38, 84 | the wire, not the paint, bounds full-frame sends. PIE cannot shorten wire time |
| HW-S3-24 | esp_lcd i80 has `swap_color_bytes` ("Swap adjacent two color bytes") in hardware, on i80 buses only (ESP32, P4, S2, S3, S31) | E | `esp_lcd_io_i80.h` L64–123. I80 test app supported targets https://github.com/espressif/esp-idf/blob/master/components/esp_lcd/test_apps/i80_lcd/README.md | no hardware swap on the SPI bus the PO's panel uses |
| HW-S3-25 | ST7789 RAMCTRL (0xB0) second byte, bit 3 = little-endian pixel data. ESP-IDF's ST7789 driver writes 0xF0 (big endian) and ORs bit 3 for `LCD_RGB_DATA_ENDIAN_LITTLE` | E for the driver code. H that the bit works over 4-wire SPI (lvgl_micropython applies it only on 8-lane i80, per the search summary) | esp-idf v5.5.2 `components/esp_lcd/src/esp_lcd_panel_st7789.c` lines 29–30, 112–115, 194 | a panel-side way to drop the software byte swap, to bench |
| HW-S3-26 | LCD_CAM RGB panels have "bounce buffer only" mode: a callback `on_bounce_empty` fills each few-line buffer, "procedurally generated frame-buffer-less graphics" | E | https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/lcd/rgb_lcd.html#bounce-buffer-only | a scanline renderer fits RGB panels. Not the PO's SPI panel |
| HW-S3-27 | MicroPython esp32 port enables the native/viper emitter (`MICROPY_EMIT_XTENSAWIN 1`) but not `MICROPY_EMIT_INLINE_XTENSA` (default 0). With XTENSAWIN set, v1.29.0's inline Xtensa emitter already emits windowed entry/exit. Its opcode table has no `ee.*` PIE instructions. The generic inline-asm `data(size, …)` directive in compile.c can emit raw 24-bit PIE words (H) | E for the config and source. H that a custom build with inline Xtensa runs on the S3 and that raw PIE words via `data()` work | micropython `ports/esp32/mpconfigport.h` lines 40–53. `py/mpconfig.h:499–510`. `py/emitinlinextensa.c` v1.29.0 lines 40–49, 88–97. `py/compile.c` v1.29.0 lines 3335–3347. #739 (asm_xtensa "invalid micropython decorator" on the board) | a Python-only asm path needs a custom build and hand-encoded PIE words. A C module is simpler |
| HW-S3-28 | `@micropython.viper` works on the board | E | spark #739 comment (2026-11-02) | — |

**ESP32-S3 table**

| hardware feature | graphics op it speeds up | how to call it | published speed-up (provenance) | cost or risk | example |
|---|---|---|---|---|---|
| PIE 128-bit store (`EE.VST.128.IP`) | solid fill, clear | `.S` (esp_lvgl_port) or inline asm | RGB565 fill 5.8 x aligned, 2.3 x unaligned vs LVGL ANSI C (measured, Espressif, HW-S3-8) | 16-byte alignment, Apache-2.0 notice, Xtensa-only | `loopnez a9, 1f` / `ee.vst.128.ip q0, a3, 16` / `1:` (HW-S3-11) |
| PIE load/store + `EE.SRC.Q` | rectangle copy, tile restore, kept background | `.S` (esp_lvgl_port copy) | RGB565 copy 9.8 x aligned, 6.9 x unaligned vs LVGL ANSI C (measured, Espressif) | same. Baseline is not newlib memcpy | `ee.ld.128.usar.ip q2,a7,16` / `ee.src.q.ld.ip q4,a7,16,q2,q3` / `ee.vst.128.ip q2,a3,16` |
| `EE.VCMP.EQ.S16` + `EE.ANDQ`/`EE.NOTQ`/`EE.ORQ` | colour-key sprite blit | new `.S` or inline asm | — (none published) | to write and test. Key must be one 16-bit value | H sketch: `ee.vldbc.16 q7,key` / `ee.vld.128.ip q0,src` / `ee.vld.128.ip q1,dst` / `ee.vcmp.eq.s16 q2,q0,q7` / `ee.andq q1,q1,q2` / `ee.notq q2,q2` / `ee.andq q0,q0,q2` / `ee.orq q1,q1,q0` / store q1 |
| `EE.VMUL.U16` or `EE.VMULAS.U8.QACC` | alpha blend RGB565 | inline asm (BitsForPeople pattern) | about 5 x scalar, 16 px in 90–100 cycles (stated, field, GPL-3.0) | GPL code not reusable. Channel unpack needs 32-bit shifts and masks | HW-S3-14, file lines 184–232 (read only) |
| `EE.VZIP.8`/`EE.VUNZIP.8` | RGB565 byte swap on copy | new `.S` | — | H only (HW-S3-6) | — |
| GDMA `esp_async_memcpy` | copy beside the CPU (PSRAM to internal) | ESP-IDF API | IRAM-IRAM about 57 MB/s vs memcpy 364 MB/s (field, unread) | callback in ISR, PSRAM limits | async_memcpy docs |
| SPI master + GDMA (esp_lcd) | send overlapped with paint | `esp_lcd_panel_draw_bitmap` + `on_color_trans_done` | wire 31.0 ms a full frame at 40 MHz (measured, bench.md:84) | internal DMA RAM only on IDF v5.5.2 | frame.c (already done) |
| second core (core 0) | render, convert or copy while Python runs | `xTaskCreatePinnedToCore(…, 0)` from the C module | — | Wi-Fi shares core 0. Cache/PSRAM bandwidth shared | — |
| ST7789 RAMCTRL ENDIAN | removes the software byte swap | panel init command 0xB0 `0x00, 0xE8` | — | possibly no effect over SPI (H) | esp_lcd_panel_st7789.c:112–115 |

### 1.2 ESP32-P4

| ID | claim | tag | pointer | supports only |
|---|---|---|---|---|
| HW-P4-1 | P4 has PIE too, on RISC-V (RV32IMAFCZc + custom `Xhwlp` hardware loops). Mnemonics start `esp.`, eight 128-bit QR, QACC 256 bits each. Stated: memcpy 74.3 % faster than the C library, int16 vector add 93.8 % faster than ANSI C (P4 360 MHz, 2040 B x 100 rounds) | E (stated, Espressif blog) | https://developer.espressif.com/blog/2024/12/pie-introduction/ | P4 has its own SIMD. S3 `.S` files do not carry over |
| HW-P4-2 | Espressif ships P4 PIE assembly in esp-dsp (`*_arp4.S`: dotprod, FIR, FFT). GCC inline asm with `esp.vst.128.ip` is used in ESP-IDF itself | E | gh code search `esp.vld.128.ip repo:espressif/esp-dsp` (11 hits, for example `modules/dotprod/fixed/dsps_dotprod_s16_arp4.S`). esp-idf `components/esp_gdbstub/src/port/riscv/gdbstub_riscv.c` L76–158 | the toolchain path exists. No graphics `.S` found for P4 |
| HW-P4-3 | FreeRTOS on P4 switches PIE lazily and pins the first-using task to its core. PIE in an ISR or critical section aborts. HWLP registers are saved eagerly on every switch once used | E | https://docs.espressif.com/projects/esp-idf/en/latest/esp32p4/api-reference/system/freertos_idf.html#misc | PIE only in task context |
| HW-P4-4 | PPA has three operations. SRM: rotate 0/90/180/270, scale in 1/16 steps (bilinear), mirror X/Y, `byte_swap` and `rgb_swap` for RGB565/ARGB8888 input. Blend: alpha "Ab + Af − Ab×Af", colour key `bg_ck_en`/`fg_ck_en` with RGB888 low/high thresholds, FG A8/A4/L8/L4 with CLUT. Fill. Blocking or non-blocking, with `on_trans_done` in ISR context. Output buffer and size must be cache-line aligned (L1 internal, L1+L2 PSRAM). No timing published | E | https://docs.espressif.com/projects/esp-idf/en/latest/esp32p4/api-reference/peripherals/ppa.html | PPA covers fill, keyed blit, alpha blend, rotation, scaling. The per-call overhead is — |
| HW-P4-5 | LVGL's PPA draw unit (lvgl master 1918a999d7, 2026-11-02) accepts only fills with no radius and no gradient and opa > LV_OPA_MAX. With `LV_USE_PPA_IMG`, it also takes images that are unscaled, unrotated, opaque, unmasked, RGB565/RGB888. `LV_PPA_NONBLOCKING_OPS 0` | E | lvgl `src/draw/espressif/ppa/lv_draw_ppa.c` lines 89–135. `lv_draw_ppa_private.h:24`. Kconfig | LVGL itself uses PPA conservatively. Blends and transforms stay on the CPU there |
| HW-P4-6 | esp_lvgl_port on P4 builds `src/common/ppa/lcd_ppa.c`, a PPA SRM client used for display rotation, buffers aligned to the L2 cache line | E | esp-bsp `components/esp_lvgl_port/CMakeLists.txt` lines 18–22. `lcd_ppa.c` lines 17–77 | — |
| HW-P4-7 | 2D-DMA is a private ESP-IDF driver (`esp_private/dma2d.h`), used by PPA, JPEG and `async_color_convert_dma2d.c`. The public route is `esp_lcd_dpi_panel_enable_dma2d()` (DSI) or `esp_lcd_rgb_panel_enable_dma2d()` (RGB): window copy into the frame buffer by DMA2D with 128-byte bursts. Custom `draw_bitmap_hook` lets PPA rotate or scale on the way | E | gh code search `dma2d_acquire_pool repo:espressif/esp-idf`. https://docs.espressif.com/projects/esp-idf/en/latest/esp32p4/api-reference/peripherals/lcd/dsi_lcd.html. `esp_lcd_panel_dpi.c` L489–524, L536–565 | 2D-DMA is reachable through esp_lcd for DSI/RGB panels, not as a general blit API |
| HW-P4-8 | JPEG codec decode at 360 MHz CPU, 200 MHz PSRAM, 50-run average: 480 x 320 YUV422 to RGB565/888 at 571 fps, 480 x 640 at 307 fps, 720 x 1280 at 109 fps | E (stated, Espressif docs) | https://docs.espressif.com/projects/esp-idf/en/latest/esp32p4/api-reference/peripherals/jpeg.html | backgrounds or cut-scenes as JPEG cost almost no CPU on P4 |
| HW-P4-9 | MicroPython's esp32 port on P4 enables the RV32 native emitter with Zcmp. Inline RV32 asm is not enabled there | E | micropython `ports/esp32/mpconfigport.h` lines 40–49 | viper works on P4. Inline asm needs a custom build |
| HW-P4-10 | ESP32-S31: PIE only on core 1 (FreeRTOS migrates a PIE task there), PPA present, i80 supported | E | S31 FreeRTOS page (Espressif docs MCP result). P537-finding.md:103 (GMF note). I80 test app README | a newer target with both PIE and PPA |

**ESP32-P4 table**

| hardware feature | graphics op it speeds up | how to call it | published speed-up (provenance) | cost or risk | example |
|---|---|---|---|---|---|
| PPA fill | rect fill, clear | `ppa_do_fill(client, &cfg)` | — (no timing published) | cache-line aligned output. Per-call overhead unknown | `ppa_fill_oper_config_t{ .out = …, .fill_block_w, .fill_block_h, .fill_argb_color, .mode = PPA_TRANS_MODE_BLOCKING }` |
| PPA blend + colour key | sprite blit with key, alpha blend | `ppa_do_blend` | — | FG/BG block sizes must match. Key thresholds are RGB888 | IDF example `peripherals/ppa/ppa_color_key` (named on the PPA page, not read) |
| PPA SRM | rotate 90/180/270, mirror, scale, byte swap | `ppa_do_scale_rotate_mirror` | — | input ≠ output buffer. Bilinear blur | esp_lvgl_port `lcd_ppa.c` |
| 2D-DMA | window copy into the frame buffer | `esp_lcd_dpi_panel_enable_dma2d(panel)` | — | DSI/RGB panels only. 16-byte alignment with encryption | `ESP_ERROR_CHECK(esp_lcd_dpi_panel_enable_dma2d(mipi_dpi_panel));` |
| JPEG codec | decode images to RGB565 | `jpeg_decoder_process` | 571 fps at 480 x 320 (stated) | padding to 16 px. Buffers from `jpeg_alloc_decoder_mem` | IDF JPEG page |
| PIE (`esp.*`) | fill, copy, key, blend in software | `.S` or inline asm | memcpy 74 % faster than libc (stated, P4 blog) | separate code from S3. No graphics asm exists | `esp.vst.128.ip q0, a5, 16` (gdbstub_riscv.c) |
| MIPI-DSI, RGB, i80 | bus to panel | esp_lcd | — | panel-specific | IDF `examples/peripherals/lcd/mipi_dsi` |

### 1.3 Other ESP32 parts (brief)

| ID | claim | tag | pointer | supports only |
|---|---|---|---|---|
| HW-ESP-1 | Classic ESP32 drives i80 parallel LCDs through esp_lcd (the I2S peripheral in LCD mode) | E for i80 support. H for "I2S" (from model knowledge) | i80 test app README supported targets: ESP32, P4, S2, S3, S31 | — |
| HW-ESP-2 | Classic ESP32 has no PIE. esp_lvgl_port still ships `_esp32.S` fill/copy routines in plain Xtensa asm. No published numbers for them | E for the files. — for the speed-up | HW-S3-10 listing. The README lists only S3 numbers | a non-PIE asm path exists for ESP32 |
| HW-ESP-3 | ESP32-C3/C6 are RISC-V with no PIE (`SOC_CPU_HAS_PIE` only on S3/P4/S31), no i80 (SPI panels only), and no PPA | E for i80 and PIE lists. H for "no PPA" beyond the GMF note | i80 README. PIE blog lists S3 and P4. P537-finding.md:103 | plain C is the only path on C3/C6 |
| HW-ESP-4 | With `CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT` set, MicroPython disables its RV32 native emitter | E | micropython `ports/esp32/mpconfigport.h` lines 41–44 | viper is possibly absent on C3/C6 builds (H: which builds set it is not checked) |

### 1.4 Raspberry Pi RP2040 / RP2350

| ID | claim | tag | pointer | supports only |
|---|---|---|---|---|
| HW-RP-1 | Each core has two interpolators (INTERP0, INTERP1). They combine "pre-configured operations into a single processor cycle", including "affine texture mapping", "table lookup address generation", "dithering" | E (datasheet) | RP2040 datasheet §2.3.1.6 p32 (PDF p33). RP2350 datasheet §3.1.10 p40 (PDF p41) | both chips have them |
| HW-RP-2 | Affine texture mapping: two lanes, all three bases and `ADD_RAW` reduce the per-pixel step "to a single cycle iteration". Example: `output[i] = *(uint8_t *) interp0->pop[2];` after the setup | E (datasheet-typ claim. Example code BSD-3) | RP2040 datasheet §2.3.1.6.5 p40–41. https://github.com/raspberrypi/pico-examples/blob/master/interp/hello_interp/hello_interp.c lines 214–250 | address generation for rotozoom, Mode-7 floors, scaled sprites |
| HW-RP-3 | Blend mode on INTERP0 (`CTRL_LANE0_BLEND`) does linear interpolation between BASE0 and BASE1. Clamp mode on INTERP1 | E | RP2040 datasheet §2.3.1.6 p36–37 (text lines 2469–2604) | per-channel lerp for alpha. Clamp for saturation |
| HW-RP-4 | Raspberry Pi's scanvideo sprite demo sets up interpolators for affine sprites (`_setup_interp_affine`, `_setup_interp_pix_coordgen`) with asm blitters (`sprite.S`) | E | https://github.com/raspberrypi/pico-playground/blob/master/scanvideo/sprite/sprite.c lines 99–141 | a reference implementation for affine sprite blits |
| HW-RP-5 | Pimoroni pretty-poly uses `interp1` in clamp+signed mode and saves/restores the interpolator around its use (`interp_save`/`interp_restore`) | E | pimoroni-pico `libraries/pico_vector/pretty-poly.h` lines 20, 52–53, 684–739 (MIT) | the interpolator is shared state. A library must save and restore it |
| HW-RP-6 | PicoSystem: a PIO program clocks pixels to the ST7789. `screen_double.pio` sends each pixel twice and DMA sends each scanline twice (120 x 120 to 240 x 240). It discards 4 alpha bits on the fly, and frames sync to the panel's TE/VSYNC pin | E | pimoroni/picosystem `libraries/screen_double.pio` lines 1–40. `libraries/hardware.cpp` lines 109–153 (MIT) | PIO does format conversion and 2 x scaling at no per-pixel CPU cost |
| HW-RP-7 | PicoGraphics' ST7789 driver has a PIO parallel bus (`st7789_parallel.pio`) fed by DMA | E | pimoroni-pico `drivers/st7789/st7789.cpp` lines 128–137, 250–262 | — |
| HW-RP-8 | RP2350 DMA: 16 channels, one read and one write up to 32 bits per clock. `CHAIN_TO` reconfiguration. Completion actions now strictly ordered | E | RP2350 datasheet §12.6 (text lines 65741–65803), p1010 | DMA chains for scanline or tile sends |
| HW-RP-9 | RP2350 has 3 PIO blocks of 4 state machines (12 SMs) | E | RP2350 datasheet §11 (text line 50665–50670) | — |
| HW-RP-10 | RP2350 HSTX: output-only, up to 8 GPIOs (12–19), DDR, fed from DMA through a 32-bit FIFO, with a command expander. SIO has a TMDS encoder (§3.1.9) | E | RP2350 datasheet §12.11 p1113. Contents line 115 | a DVI/fast-parallel output path. Not needed for SPI panels |
| HW-RP-11 | RP2350 Cortex-M33 is configured with single-precision FPU and the DSP extension | E | RP2350 datasheet §3.7.2 p116 | packed 8/16-bit SIMD (UADD16, SEL, …) is available on the Arm cores (instruction names H, from the Armv8-M architecture, not read) |
| HW-RP-12 | No published RP2350 DSP-SIMD blit or RGB565 speed-up found | — | search 4 | — |
| HW-RP-13 | Hazard3: RV32IMAC + Zba, Zbb, Zbs, Zbkb, Zcb, Zcmp, Xh3bextm. `rev8` and `brev8` exist. No packed SIMD | E | RP2350 datasheet §3.8 p226 (text lines 14890–14972, 16727, 16982) | byte reversal is cheap on Hazard3. No vector unit |
| HW-RP-14 | CoreMark/MHz: Cortex-M33 4.09, Hazard3 3.81, M0+ (RP2040) about 2.0 | H (field, from forum and Reddit summaries, not read) | search 5 results (Tom's Hardware forum, r/RISCV) | the Arm cluster is the faster choice for graphics |
| HW-RP-15 | The double-precision coprocessor (DCP) is irrelevant to RGB565 2D graphics | H (model knowledge. DCP is §3.6.2 p99) | RP2350 datasheet contents line 144 | — |
| HW-RP-16 | MicroPython rp2 port: native Thumb emitter, inline Thumb asm (`MICROPY_EMIT_INLINE_THUMB 1`), RV32 native + inline RV32 asm for Hazard3 builds, and `rp2_pio.c`, `rp2_dma.c` modules. The interpolator has no MicroPython module | E for the config and files. H for "no interp module" (no file named for it in ports/rp2) | micropython `ports/rp2/mpconfigport.h` lines 109–115. `gh api repos/micropython/micropython/contents/ports/rp2` | PIO and DMA are reachable from Python. Interp needs C |
| HW-RP-17 | Inline Thumb asm accepts ARMv7-M instructions only through its own table. DSP instructions are not in it, but compile.c's generic `data(size, …)` can emit raw instruction halfwords | E for `data()` in compile.c and the ARMV7M gate. H for DSP via `data()` | `py/emitinlinethumb.c` lines 429–723. `py/compile.c` v1.29.0 lines 3335–3347 | — |

**RP2040 / RP2350 table**

| hardware feature | graphics op it speeds up | how to call it | published speed-up (provenance) | cost or risk | example |
|---|---|---|---|---|---|
| SIO interpolator, ADD_RAW + shift/mask | affine sprite, rotozoom, Mode-7 floor, tile map lookup | pico-sdk `hardware/interp.h` | "single cycle iteration" for the address step (datasheet-typ, RP2040 §2.3.1.6.5) | per-core state. Save/restore around use. C only from MicroPython | `interp0->accum[0]=u; interp0->base[0]=du; … out[i]=*(uint8_t*)interp0->pop[2];` |
| interpolator blend/clamp | alpha lerp, saturating colour add | `interp_config_set_blend`, `_set_clamp` | — | INTERP0 blend only | RP2040 datasheet §2.3.1.6 p36–40 |
| PIO | SPI/parallel panel bus, 2 x pixel doubling, format conversion on the wire | pico-sdk `pio_*`. MicroPython `rp2.PIO`/`rp2.StateMachine` | — | PIO program per panel. GPIO choice fixed by the board | picosystem `screen_double.pio` |
| DMA chaining | scanline/tile sends, ring buffers | pico-sdk `dma_*`. MicroPython `rp2.DMA` | 1 read + 1 write per clock (datasheet) | channel claim conflicts | RP2350 §12.6 |
| HSTX (RP2350) | DVI or fast parallel out | pico-sdk `hardware/structs/hstx_*` (H) | — | GPIO 12–19 only | RP2350 §12.11 |
| M33 DSP SIMD (RP2350) | 2 x RGB565 per word add/select (colour key via SEL) | ACLE intrinsics (H) or asm | — | Arm cluster only. Unmeasured | — |
| Hazard3 Zbb/Zbkb (RP2350) | byte swap (`rev8`), bit tricks | compiler `-march=…_zbb_zbkb` | — | RISC-V cluster only | RP2350 §3.8.1.16 |

### 1.5 Options, ranked by gain for 2D games per unit of work (options, not a decision)

Ranking basis: published or derived gain on a hot game loop, then the work to adopt it, then the risk. Every gain is
against plain C unless said otherwise.

1. **S3: port esp_lvgl_port's PIE fill and copy (`.S`, Apache-2.0).** Work: 3 files, a 9-word struct, a build flag.
   Gain: per HW-S3-9, 0.3 ms (fill) to 1 ms (copy) per full frame at 240 MHz. For a library that does whole-frame restores
   (kept background, tile layers), the gain is larger. Risk: alignment fallbacks are already in the asm. Licence notice
   needed. Xtensa only.
2. **S3: a PIE colour-keyed blit (new `.S`, VCMP.EQ.S16 + AND/NOT/OR), on the copy routine's skeleton.** Work: one new
   routine plus tests against a C reference. Gain: — (none published). If sprites grow, it is the sprite loop that stays hot
   after the C step. Risk: written by us. Must be clean-room (HW-S3-14 is GPL).
3. **RP2040/RP2350: interpolator for affine and tile-map address generation.** Work: C with pico-sdk, an existing example
   (BSD-3). Gain: datasheet "single cycle iteration" for the address step. Risk: shared per-core state. Not the PO's
   hardware today.
4. **P4: PPA fill/blend/SRM and `enable_dma2d`.** Work: small (driver calls). Gain: — (no timings). LVGL hands the PPA
   only large opaque fills and plain image copies, which suggests per-call overhead matters for small sprites (H).
   Risk: no P4 board on the bench.
5. **RP: PIO panel bus with on-the-fly pixel doubling or format conversion (PicoSystem pattern, MIT).** Work: medium.
   Gain: a quarter of the framebuffer and render work at 2 x scale. Risk: panel- and pin-specific.
6. **S3: a C worker task on core 0** for convert/copy/render while Python runs on core 1. Work: medium to high. Gain: —.
   Risk: Wi-Fi on core 0, shared PSRAM bandwidth, cross-core sync.
7. **Panel ENDIAN bit (ST7789 RAMCTRL) to drop software byte swaps.** Work: one init byte. Gain: removes the swap in
   "strips" sends. Risk: possibly no effect on SPI (H). Not a chip feature, but cheaper than a PIE byte swap.
8. **S3 GDMA async memcpy.** Low value: the field numbers show it slower than the CPU for internal copies.
9. **MicroPython inline asm (asm_xtensa) for PIE.** Needs a custom build, hand-encoded 24-bit PIE words via `data()`, and is
   untested on the windowed ABI. A C module gives the same reach with a normal toolchain.
10. **RP2350 M33 DSP SIMD.** No published numbers. Worth a probe only after options 3 and 5.

### 1.6 Cheapest bench test on the PO's S3 (FireBeetle 2, DFR0664 ST7789 over SPI) for option 1

- What: copy `lv_color_blend_to_rgb565_esp32s3.S` (and, for the copy, `lv_rgb565_blend_normal_to_rgb565_esp32s3.S` +
  `lv_macro_memcpy.S`) into the s3lcd C module behind a build flag. Declare the 9-word struct
  `{opa, dst_buf, dst_w, dst_h, dst_stride, src_buf, src_stride, mask_buf, mask_stride}` in C. Add one function,
  `s3lcd.simd_bench(op, w, h, offset, reps)`, that returns the minimum `esp_cpu_get_cycle_count()` delta over `reps` for
  three versions: the module's present C loop, a 32-bit-word C loop, and the asm.
- Where: on the internal DMA framebuffer (16-byte aligned via `MALLOC_CAP_SIMD` or `heap_caps_aligned_alloc`) and on a
  PSRAM buffer, at 16 x 16, 32 x 32, 127 x 127, 128 x 128 and 320 x 240, with `offset` 0 and 2 bytes.
- Pass line: asm cycles/pixel within about ±25 % of HW-S3-8 for 128 x 128 aligned. Then one game run with the paint
  phase average before and after (p537-finding.md:142 already names "fill_rect and tile copy microseconds before and after").
- Cost: no new hardware, no change to the games, reversible by the flag. It also prints `machine.freq()`, so HW-S3-9's
  clock assumption is settled. H: about one session of work, judged from the file sizes (404 lines of asm for the fill).

## 2. What I did not check, and why

- PPA per-call overhead and throughput on the P4: no published number (search 1), no P4 board. The IDF `ppa_*` examples
  were named but not read.
- Any PIE colour-key or alpha-blend number from Espressif: none exists in esp_lvgl_port, LVGL master or the PIE blog. The
  only stated number is third-party GPL code (HW-S3-14), not run.
- Whether S3 FreeRTOS switches PIE lazily and pins the task, as documented for P4/S31: the S3 page shows only the FPU text.
  The tie-asm macro shows the save exists, not its policy.
- esp32.com async_memcpy figures: the forum served a bot check, so HW-S3-19 rests on a search summary.
- Whether ST7789's RAMCTRL ENDIAN bit applies over 4-wire SPI: the ST7789V datasheet was not read. The DFR0664 TE pin
  availability: not checked.
- The CPU clock of the PO's build (160 or 240 MHz): not read. HW-S3-9 gives both.
- With inline Xtensa enabled, does MicroPython's emitter run on the S3, and can `data()` emit PIE words? Not built or
  run.
- RP2350 DSP-SIMD instruction semantics (Armv8-M ARM) and ACLE intrinsics: not read. Hazard3 vs M33 CoreMark/MHz: forum
  numbers only.
- The S3 TRM's PIE cycle counts or pipeline latencies: not searched for in the 1531 pages beyond the chapter intro. The
  TRM describes no per-instruction timing in the parts read.
- LCD_CAM's YUV-RGB conversion and its use for an SPI panel: not applicable to the PO's SPI wiring, not pursued.
- GitHub code search hit its rate limit at 11:41 UTC (12:41 Prague), so the PicoGraphics/picosystem searches for `interp`
  used repository listings instead. A zero hit for `interp0` in pimoroni-pico, picosystem, 32blit, TFT_eSPI and LovyanGFX
  covers only that exact token.

## 3. Questions for the decider

| question | what it decides |
|---|---|
| Is the MVP S3-and-SPI only, or must its interface already have a slot for an accelerator (P4 PPA, RP interpolator, PIE kernels)? | whether a "backend" interface for fill/copy/key/blend exists from slice 1 or is extracted later |
| Is Apache-2.0 code (esp_lvgl_port `.S`, with its NOTICE) acceptable inside the MIT library? And is GPL-3.0 code (BitsForPeople) off limits even as reading? | port vs clean-room rewrite of PIE kernels. Review rules for contributors |
| Is a custom MicroPython build with the C module the only delivery, or must stock firmware work too (native `.mpy`, viper)? | whether any asm path must avoid a firmware rebuild. Rules out or keeps HW-S3-27 |
| Does the PO buy an ESP32-P4 board and a Pico 2 (RP2350) for bench tests, and when? | whether P4 and RP findings stay paper-only or get measured |
| With Wi-Fi off, is the library allowed to start a FreeRTOS task on core 0? | whether option 6 (second-core worker) is in scope |
| Is byte order fixed at the panel (RAMCTRL) before any PIE byte-swap work? | whether a swap kernel is needed at all |
| What counts as "worth keeping" for a hardware kernel: a frame-time gain in ms, or a primitive speed-up? | the done-line for slice 8 (p537-finding.md:142 says 2 ms a frame) |

## 4. Searches

Web searches (7 of 12):

| # | query, verbatim | decision it served | used |
|---|---|---|---|
| 1 | `ESP32-P4 PPA performance benchmark blend fill scale time per frame` | is PPA worth using per sprite vs the CPU | not used: no timing found, only the docs (HW-P4-4) |
| 2 | `ESP32-S3 PIE SIMD alpha blend RGB565 assembly ee.vmul LVGL 9.2 esp32s3 blend` | prior art for PIE colour key and blend | used: bitbank post (HW-S3-7), CubeCoders/BitsForPeople (HW-S3-14) |
| 3 | `esp_async_memcpy ESP32-S3 GDMA throughput MB/s measured vs memcpy` | GDMA copies vs CPU copies | used as H (HW-S3-19). The forum page did not load |
| 4 | `RP2350 Cortex-M33 DSP SIMD instructions UADD8 SEL graphics blit RGB565 speedup` | is an M33 DSP path worth a slice | not used: no numbers (HW-RP-12) |
| 5 | `RP2350 Hazard3 RISC-V vs Cortex-M33 CoreMark per MHz performance comparison` | which RP2350 cluster to target | used as H (HW-RP-14) |
| 6 | `ST7789 RAMCTRL B0h ENDIAN bit little endian RGB565 SPI byte swap` | can the panel remove the byte swap | used: led to the ESP-IDF driver source (HW-S3-25) |
| 7 | `MicroPython asm_xtensa ESP32-S3 MICROPY_EMIT_INLINE_XTENSA esp32 port windowed enable` | is inline asm from Python viable on S3 | not used: answered from MicroPython source instead (HW-S3-27) |

Espressif docs MCP queries (3):

| # | query, verbatim | decision it served | used |
|---|---|---|---|
| E1 | `ESP32-S3 SPI master DMA transmit buffer in PSRAM external memory alignment esp_lcd draw_bitmap` | can the SPI send read a PSRAM framebuffer directly | used (HW-S3-21, HW-S3-22) |
| E2 | `ESP32-S3 PIE TIE coprocessor registers saved on FreeRTOS context switch, using PIE in ISR or multiple tasks` | PIE safety in tasks and ISRs | used (HW-S3-16, HW-P4-3, HW-P4-10) |
| E3 | `esp_lcd I80 interface supported chips ESP32 I2S LCD mode ESP32-S3 LCD_CAM swap_color_bytes RGB panel bounce buffer PSRAM` | which chips have a parallel bus and hardware swap | used (HW-S3-24, HW-S3-26, HW-ESP-1) |
| E4 | `ESP32-P4 MIPI DSI esp_lcd_dpi_panel_enable_dma2d draw_bitmap 2D-DMA copy frame buffer` | how 2D-DMA is reached on P4 | used (HW-P4-7) |

GitHub API reads (contents and code search) and documents fetched by URL are not counted as searches. They are named at
each finding.
