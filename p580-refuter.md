# P580: refuter of the PIE effects finding (2026-11-02)

Read-only check of p580-finding.md at 8984b52 (Opus 5.5). Every line below was opened and read. TRM = ESP32-S3 Technical Reference Manual v1.8, espressif.com PDF, sha256 4484bf8a69035ec42a731c58c64ada6fbd1f1618c5559409f134d9ea083f444f, 1,531 pages.

## Verdicts in short

MUST
1. "No 16-bit compare, EE.VCMP in S8 only" is refuted. TRM 1.8.79 `EE.VCMP.EQ.S16`, 1.8.82 `EE.VCMP.GT.S16`, syntax line `EE.VCMP.LT.S16 qa, qx, qy`, and S32 forms. The esp-dl cheat sheet lists only S8 (its lines 741, 759), so the finding copied the sheet's gap. Fix summary 1 and Q1. A 16-bit key compare exists, so a keyed RGB565 compose is cheaper in PIE than the finding says.
2. Rank 1 leaves out the compose. Soft smoke (ART-3) and "additive" read the frame, blend and write back. The table counts a plain write only. The measured C blend is 337.52 ns/px into the PSRAM frame and 323.43 into the internal one (run46-p567-double.log, run46-p567-dma.log), so a 320 x 40 alpha strip costs about 4.2 ms in C, not 1.1 or 2.6 ms. PIE pays on this blend, not on the heat kernel. Slice 0 should time the heat-to-alpha compose and name the compose mode in its pass line.
3. Slice 0 times a warm cache. 200 reps on one 64 x 64 window keep its frame lines in the 32 KB data cache (sdkconfig: `CONFIG_ESP32S3_DATA_CACHE_SIZE=0x8000`, line 32 B). run46 shows how far off that is: the same sprite costs 23.76 µs warm and 67.80 µs interleaved. The 64 x 64 alpha blend costs 1382 µs into PSRAM and 1325 µs into internal RAM, so a warm window shows only 14 ns/px of PSRAM cost. Fix: put a full-frame blit or a cache write-back between reps, as probe567 did.
4. The pass line leaves a gap. Pass is at least 3 x and kill is under 1.5 x, so 1.5 to 3 x has no verdict. A strip over 1.5 ms has no consequence. Add one line for each.

SHOULD
5. The inputs the finding cites are not on its branch. bench.md's P567 section and probe567.py are on p567-to-master (a29c851), and `git merge-base --is-ancestor a29c851 8984b52` fails. Cite that branch, or merge it first.
6. The PSRAM split is partly wrong. The full-frame copy takes 2.58 ms in "dma" and 6.83 ms in "double", so a PSRAM write costs about 55 ns/px and a read about 34, not 45 each. The claim "the blend spends 90 ns on PSRAM and 250 computing" is refuted, because into internal RAM the blend still costs 323 ns/px. The lesson that compute dominates still holds, and more strongly.
7. The clock is H, but the evidence exists, and it is the strip that turns the plan. Clock: build-s3lcd/sdkconfig:1592 has `CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ=240`, games/ never sets a frequency, and the build uses `CONFIG_COMPILER_OPTIMIZATION_PERF` (-O2), which is the C baseline's flag. Strip: game x runs along panel y (games/lcd.py:59). So a 320 x 40 game strip is 320 panel rows of 40 px. The finding does not say how the heat scratch is laid out. A scratch in game order turns the palette write into 2-byte column writes, whose cost bench.md:77 shows.
8. The arena is too small. A 64 x 64 ripple takes 24,576 B, the whole "about 24 KB" arena, so no smoke puff can run beside it. The arena also holds 24 of the 31,744 B that TL-10 gives to P554, P537 and P557.
9. "This kernel is the only way to soft smoke" is refuted by ART-3 itself (art-direction.md:18-20): "baked onto a known background (as the sky rows are) or drawn as particles and fills".
10. Screen shake does not cost 0. Every tile changes, so each shaken frame costs a full copy (3.4 ms, run41) and a full send (about 33 ms, in the background).
11. TL-15 names "particles' motion" as physics, so the bend redefines physics. Q13 is still queued, although its tech-lead opinion says D2 answers the emitter half for effects. Make the PO's yes on the bend a gate before slice 1, and pass gravity and drag from Python.
12. The summary gives fire "about 1.2 ms" and the table gives 1.1 ms.

## 1. Claims against their sources

| claim | source read | verdict |
| --- | --- | --- |
| 8 QR registers, 128-bit, 16 x 8-bit multipliers, 8 x 16-bit | TRM p. 39-41: "Bank of eight 128-bit vector QR registers", "eight 16-bit multipliers", "8-bit multiplication ALU contains 16 multipliers" | holds |
| loads and stores force 16-byte alignment | TRM 1.3.5: "the data should be 128-bit aligned, and the lower 4 bits of address will be ignored". SAR_BYTE: "forced to be 16-byte aligned" | holds |
| unaligned data uses USAR plus SRC.Q | TRM SAR_BYTE: EE.SRC.Q* "read two 16-byte data from two aligned addresses ... shift it by the byte size of SAR_BYTE" | holds |
| EE.VLD.128.IP step is -2048..2032 in the TRM, -512..496 in the sheet | TRM p. 164: "EE.VLD.128.IP qu, as, -2048..2032". pie_instruction_set.md:122: "-512..496" | holds |
| VCMP in S8 only, no 16-bit compare | TRM 1.8.79, 1.8.80, 1.8.82, 1.8.86 (S16, S32) | refuted (MUST 1) |
| VADDS saturating, signed only. VMUL U8/U16/S8/S16. VSR.32. VZIP, VUNZIP | TRM instruction headings (grep of 1.8.x) | holds |
| lvgl fill 0.196 against 1.146, copy 0.352 against 3.437, unaligned fill 2.3 x | esp-bsp simd README: "128x128 / 16 byte / 0.196 / 1.146", "0.352 / 3.437", "127x127 / 1 byte / 0.497 / 1.124". Clock and memory not stated | holds (5.8 x, 9.8 x, 2.26 x) |
| esp-dsp dotprod_s16_aes3: `#if dspi_dotprod_aes3_enabled`, ansi fallback, usar loads | file line 16 `#if (dspi_dotprod_aes3_enabled == 1)`, line 70 `call8 dspi_dotprod_s16_ansi`, line 137 `ee.ld.128.usar.ip` | holds |
| full copy 6.83 ms, 89 ns/px | run46-p567-double.log `blit_full_opaque 6.83 ms` (the sky picture from the pool to the frame, PSRAM to PSRAM) | holds. 6.83/76,800 = 88.9 ns |
| blend 337.5 ns/px | `blit_alpha128_per_px 337.52 ns` | holds. The split is wrong (SHOULD 6) |
| 40 particles 2.27 ms in Python | `physics_0_bodies_40_particles 2.27 ms`. probe567 `physics()`: update only, no draw | holds. The comparison is conservative |
| 16x24 sprite 23.76 µs | `sprite_16x24_warm 23.76 us`, warm. Interleaved 67.80 | partly: rank 8 uses the warm figure, so ×2.9 in play |
| 31,744 B largest block while it runs | bench.md:186 (run41). TL-10: largest DMA block | holds. run46's 188,416 was read after deinit |
| clock 240 MHz (H) | sdkconfig:1592 | holds, upgrade to E |
| D2 at brief.md:124, TL-15 at tech-lead.md:60, ART-3 at art-direction.md:18 | lines read | hold. "Only way to soft smoke" refuted (SHOULD 9) |
| Lode's formula `*32)/129` | lodev.org/cgtutor/fire.html, read | holds |
| s3lcd.c:186 alpha_blend_565, :607 keyed rows, gfx.py:233 Particles, micropython.cmake target_sources | read | holds |

## 2. Arithmetic, and what a 2x error does

Every product was recomputed, and each holds to rounding: 8,000 cyc = 0.033 ms. 102,400 cyc = 0.43 ms. 12,800 x 45 ns = 0.58 ms. C 384,000 cyc = 1.6 ms. Ripple 6,144 cyc = 26 µs. 4,096 x 175 ns = 0.72 ms. C 61,440 cyc = 0.26 ms. Buffers 2 x 8,192 + 8,192 = 24,576 B. 48 x 48: 13,824 B. Glow 68 µs, 43 µs, 0.37 ms. Rank 7: 77 µs and 1.54 ms. Rank 8: 24 x 23.76 = 0.57 ms.

E inputs: 89 ns/px, 337.5 ns/px, 2.27 ms, 23.76 µs, 31,744 B and the lvgl ratios. H inputs: every PIE instruction count, the C cycles per pixel (30, 15 and 60), the 8 cycles per pixel of the palette, and 45 ns per write (55 measured, see SHOULD 6).

If every number is off by 2 x, the ranking survives. Ranks 1 to 3 still cost about 2.1, 0.2 and 1.5 ms against stack's room of about 20 ms. The pass lines do not survive: the strip would be about 2.1 ms against 1.5. One number moves rank 1 by 4 x, and it is not an estimate error: the measured C compose (MUST 2).

## 3. Licences

- esp_lvgl_port `.S`: the file header reads `SPDX-License-Identifier: Apache-2.0`, although GitHub reports the esp-bsp repository as NOASSERTION. Our repo is MIT, and porting is fine if we keep the header and add a NOTICE line. Holds.
- esp-dsp: Apache-2.0 (gh api). Holds.
- esp-dl: MIT (gh api). Holds.
- esp_simd: GitHub finds no licence file, but the README says "licensed under the **MIT License**". Holds, and it is used as an idea only.
- lodev.org says "Copyright (c) 2004-2007 by Lode Vandevenne. All rights reserved." That is not "no licence given". Reimplementing from the formula is fine, and copying the code is not.

## 4. Slice 0 and its pass line

Is the pass line observable? Partly. Cycles per pixel can be read. The strip line needs `fx_bench` run at 320 x 40, with the panel layout and the compose mode named, and timed with a cold cache (MUSTs 2 to 4).

Is slice 0 the cheapest test that would change the plan? No. By the finding's own C numbers (2.6, 0.1 and 1.0 ms), all three effects fit stack in plain C, so PIE changes no go or no-go for stack. Two cheaper tests would change the plan:

- a 10-line `.S` with one `ee.*` instruction, listed in micropython.cmake, to answer whether it assembles;
- `blit_buffer` of a 40 x 320 window at alpha 128 through the existing path, which prices the compose today with no new code.

Run both before the 150-line kernel. D2 asks for PIE, so it stays, but aim it at the compose.

## 5. The API against TL-15 and D2

TL-15: "Physics (integration, springs, particles' motion) in Python fits it. A particle or physics engine in C does not fit the stated rule and would need the decider to reopen it." So "decides nothing the game reads" redefines the rule rather than bending it. The finding does mark it as a proposal for the PO. Q13 is "status: queued", but its tech-lead opinion says "the emitter half is answered for effects". Record the PO's yes as Q13's answer, and gate slice 1 on it.

D2 holds on its other points: "as part of the driver or the P539 library" matches fx.c beside frame.c, "started by the game when something hits..." matches `tft.fx(...)`, and "S3 only" holds, because the C twin is only the baseline. The game does read a little back (a handle, or None when the table is full), which is harmless. Gravity and drag constants in C would be speeds in C, so pass them in from Python.

## Searches

- The TRM PDF (downloaded, pdftotext pages 38 to 330).
- gh api: the licences of esp-bsp, esp-dsp, esp-dl and esp_simd; the esp_lvgl_port simd listing and its rgb565 blend header; esp-dsp dspi_dotprod_s16_aes3.S; esp-dl pie_instruction_set.md; the esp_simd README.
- WebFetch: the esp-bsp simd README and lodev fire.html.
- Local: bench.md, the run46 logs, p567-to-master's bench.md and probe567.py, lcd.py, s3lcd.c, micropython.cmake, the build-s3lcd sdkconfig, brief.md and the council files.

Not checked, for lack of time:
- the Microsoft ripple archive, ivank and the Perlin pages (the algorithms are not in dispute);
- the esp32.com threads (the finding marks them as behind a bot check);
- the esp-dl SKILL.md version date;
- whether a `.S` assembles in the user C module (a build is needed).
