# Risks and tests

## Risks
<!-- One row per type; an active extension adds its own rows. evidence now: tag and ids (★C<n>, A<n>).
status: open · retired · n/a because ….
e.g. `| usability | H no test yet (A2) | a five-person prototype test | open |` -->
| risk | evidence now | cheapest way to retire it | status |
| --- | --- | --- | --- |
| value <!-- REQUIRED:risk-value --> | H: only the PO is blocked, and whether his J1 needs no public library is the PO assistant's opinion (★C4), outside demand unseen (★C26) (A1, A2) | P550, the paint composition probe (A2), P537 slices 0 to 3 measured, T1, the forum desk count, is deferred by D5 | open |
| usability <!-- REQUIRED:risk-usability --> | H: a MicroPython user must flash a custom image (★C24), silent faults (wrong colours, dark screen) give no message (USER-10) (A9) | T4 after P538: count outside issues in 8 weeks, init-time checks that name the fault | open |
| feasibility <!-- REQUIRED:risk-feasibility --> | H mostly: one core for two bindings is shown on RP2040 only, one vendor and one toolchain family (★C20), frame.c cuts along three layers (★C10), no build outside MicroPython exists (TL-9) (A3, A4, A5, A6, A7) | the compile spike in four build systems (P545), the framebuf trial (P541), the send probe (P542), the C++ flags probe (P543) | open |
| viability <!-- REQUIRED:risk-viability --> | H: single-maintainer display libraries stall when IDF, MicroPython or the Arduino core moves (★C25) (A8) | a CI matrix kept green for 8 weeks after the public release, the PO's hours-per-week answer | open |
| ethics and safety <!-- REQUIRED:risk-ethics --> | E: GPL-3.0 code sits next to the useful pieces and the fork mixes licences (★C33) (A10) | a COPYRIGHTS table with a row per bundled file before the first public commit (P547) | open |
| power and battery <!-- REQUIRED:electronics-firmware:power --> | — | — | n/a because the library draws no power of its own: it runs on a board whose supply P536 and P534 own |
| current and stall <!-- REQUIRED:electronics-firmware:stall --> | — | — | n/a because the library drives no motor or load |
| thermal <!-- REQUIRED:electronics-firmware:thermal --> | — | — | n/a because the library adds no dissipating part, CPU load at 240 MHz is the board's existing case |
| EMC and ESD <!-- REQUIRED:electronics-firmware:emc-esd --> | — | — | n/a because the library changes no wiring or switching edge, the SPI clock stays at the panel's measured 40 MHz (★C5) |
| sensor drift and calibration <!-- REQUIRED:electronics-firmware:sensor-drift --> | — | — | n/a because the library reads no sensor |
| brown-out <!-- REQUIRED:electronics-firmware:brown-out --> | — | — | n/a because the library changes no rail or peak, the D14 power-off (USER-8) is a board fact noted on P534 #738 |
| wake and low power <!-- REQUIRED:electronics-firmware:wake --> | — | — | n/a because the library has no sleep or wake path |
| the firmware–hardware contract <!-- REQUIRED:electronics-firmware:contract --> | E: the DFR0664 has no TE line, so a tear line stays possible (USER-3), the panel takes 40 MHz at most (★C5), PIE needs 16-byte alignment and task context (★C29), IDF v5.5.2 SPI DMA cannot read PSRAM (★C9), negative coordinates wrap in today's primitives (★C12) | R0 contract checks written into the core's tests (clipping, alignment), the send probe (R6) for the window model, a TE-synced show only on a panel with TE | open |
| supply and documents <!-- REQUIRED:electronics-firmware:supply --> | E: s3lcd upstream dormant since 2024-03-20 (★C25), MicroPython v1.29.0 pairs with IDF v5.5.2 and master already recommends v5.5.5 (PO-17), Arduino-ESP32 and arduino-pico move their C++ flags (★C16), bench.md contradicts itself on the strip cost (Found on the way) | R0: pin the MicroPython and IDF pair in `build.sh` and CI, read the toolchain flags at each bump, fix the two documents (P549) | open |
<!-- EXTEND:risk-rows --><!-- EXTEND:pair-rows -->

## Assumptions
<!-- About ten at most. type: value, usability, feasibility, viability or ethics. importance: "— (decider)" until
the decider rates it, then "high D<n>" or "low D<n>". pass line: written, with its date, before any result.
status: open, or retired with the date of its Results row.
e.g. `| A2 | Assignees never see new tasks | value | H ★C2 | — (decider) | query opened-within-48h | under 50 %, set 2026-10-06 | over 80 % | open |` -->
| id | belief | type | evidence now | importance | cheapest test | pass line, dated | result that would change the decision | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 <!-- REQUIRED:assumptions --> | At least one person besides the PO wants fast sprites, tiles and text from MicroPython on an ESP32 or RP2 colour panel, enough to flash a custom image | value | H ★C26 (one search found none), the three personas are the PO's words | low D5 | T1: read the MicroPython and CircuitPython GitHub Discussions of the last 12 months for such posts, about one hour (P548) | 5 or more distinct posters (no denominator or base rate, so a weak line), set 2026-11-02 | fewer than 2 posters: the public part waits until the PO's games are done, and R1 moves after R0 | open |
| A2 | The 34 ms runner paint is made of C-call count and repeated work, so batching the draws into C brings runner under 12 ms and J1 is met by P537 slices 0 to 3 inside the fork, with no public library | feasibility | H ★C3, ★C4 (a projection from maxima that predate partial show), E ★C1 for the 34 ms and 60 ms figures | high D6 | P550, one session on the board: count `fill_rect` calls per frame for runner, time one 8 x 8 and one 240 x 16 `fill_rect` 1000 times each with `time.ticks_cpu()`, read the average paint per phase (P537 slice 0) and the collection time inside it (`GC_FRAMES` a very large value for one run, never 0) | the calls per frame by size class times the measured 8 x 8 or 240 x 16 cost, summed, account for at least 70 % of the average paint re-measured in the same session, set 2026-11-02 before any result (D7), the old line stays as the second check: runner paint under 12 ms after P537 slice 2 | under 40 %: batching alone will not reach 12 ms, the first slice becomes a Python-side cut (one call per sprite, the map in C) measured again before the layer design, paint over 25 ms after slice 2 means the core needs more than batching. Proposed by the refuter, rated high by D6 | open |
| A3 | No existing adopt path (CircuitPython displayio plus `_stage`, lvgl_micropython, UIFlow2 `User_GFX`) reaches 33 ms a frame on the fixed scene without new C | feasibility | H PO-11 points 1 to 3, ★C22 ★C23 | — (decider) | T2, the adopt bench (P540): one fixed scene (20 sprites 16 x 16 with a key, score text, tiled background, 120 frames) per candidate on the FireBeetle | no candidate at or under 33 ms a frame, set 2026-11-02 | one candidate at or under 33 ms: adopt it (or its binding) instead of building a core | open |
| A4 | One core serves the MicroPython binding and an Arduino class without a frame-time cost on the S3 | feasibility | H ★C20 (RP2040 precedent only, one toolchain family), E ★C18 (compile measurement, in kind), H for the S3 | low D6 | the walking skeleton (P546): the same `fill_rect` and `blit_keyed` called from Python and from a C test, cycles counted | the C-called path within 5 % of the Python-called path's inner loop cycles, set 2026-11-02 | more than 20 % apart: the bindings need separate fast paths, and "one core" is weaker than claimed | open |
| A5 | `framebuf.blit` with a key over a buffer view of `frame.c`'s pixels brings the average sprite part of runner's paint (not the maximum) under 4 ms (P537 slice 3's line), so slice 3 is an adapter, not a new C blit | feasibility | H the PO assistant's T3 (about 10 C lines, an estimate), ★C11 (no buffer getter today) | — (decider) | T3, the framebuf trial (P541): expose the frame as a buffer, wrap in `framebuf.FrameBuffer(RGB565)`, draw the sprites, mark dirty, bench one game, with the orientation map still in Python per call | average sprite phase under 4 ms, set 2026-11-02, between 4 and 8 ms is unsettled and asked (today's maximum is 5 to 8 ms, p537-finding.md:13) | average sprite phase over 8 ms: the per-pixel loop is too slow and a C blit is slice 3 | open |
| A6 | One source tree compiles under the four build systems (MicroPython usermod, ESP-IDF component, Arduino-ESP32 sketch, Pico SDK) with a port macro set per build file (the refuter's second pick, rated low by D6) | feasibility | H the tech lead's TL-9 and layout sketch, E ★C15 (ESP_PLATFORM absent in a usermod), ★C16 | low D6 | the compile spike (P545): one header and one fill into a surface, built in each system, the C++ flags probe first (P543) | 4 of 4 build systems compile and link, set 2026-11-02 | Arduino or Pico fails on the layout: the R2 binding and the R3 ports move later, and the layout changes before any code | open |
| A7 | The present layer's cost is a fixed cost per window (about 128 µs) plus bytes at 5 MB/s, so tile 16 and window joining are the right defaults | feasibility | E ★C6 (a fit on three sends carrying the one-row strip bug) | — (decider) | the send-overhead probe (P542): n windows of equal bytes, n = 1 to 64, ms per show on the board | the fit holds within 15 % for every n, set 2026-11-02 | the overhead grows with n or with position: the tile size and the join rule are redesigned, and the frame budget (★C8) is recomputed | open |
| A8 | The fork's S3 image and its one host-test workflow still build when MicroPython or the IDF moves, at a cost in the PO's and the AI's time small enough that the showcase stays current (D5: a showcase the PO keeps building, not a supported library) | viability | H ★C25 (every surveyed single-maintainer library stalled), the PO's hours per week — | high D6 | P551: one ESP-IDF or MicroPython version bump on a branch of the fork (MicroPython master recommends IDF v5.5.5 against v1.29.0's v5.5.2), the PO's and the AI's time logged | image builds and host tests pass within 4 hours of logged time in total, set 2026-11-02, proposed, pending the PO | over 4 hours, or red: the showcase pins one MicroPython and IDF pair and says so in the README | open |
| A9 | A MicroPython user on another board accepts flashing a custom image for the speed | usability | H ★C24 (every surveyed project ships custom firmware), USER-27 | — (decider) | T4 after P538: count outside issues, pull requests and forks in 8 weeks | at least 1 outside issue or pull request (no base rate), set 2026-11-02 | 0 after 8 weeks: reach comes by the Arduino library or a natmod spike, not more images | open |
| A10 | Every piece ported into the library is MIT, BSD or Apache-2.0 with its notice kept, and no GPL-3.0 code or font with its own terms enters | ethics | E ★C33 (GPL next to the useful pieces, the fork's mix) | low D6 | a COPYRIGHTS table with a row per bundled file, checked before the first public commit (P547), and a per-file header read before each port | every bundled file has a row with a permissive licence, set 2026-11-02 | a GPL or unlicensed file found: it is removed or rewritten clean-room before R1 | open |

## Collection plan
<!-- One row per gap. e.g. `| Do assignees open new tasks? | Q2 | Lena, from analytics | one query | this week |` -->
| question | decision it blocks | who can answer | how | when |
| --- | --- | --- | --- | --- |
| Rate A3, A5, A7 and A9 (D6 did not show them) <!-- REQUIRED:collection --> | Q5 | the PO | Q5, asked alone | before P540 to P542 are ordered |
| Which licences may enter, and which hours per week for the showcase? | Q7, A8 | the PO | Q7 from the queue, P551 logs the hours of one bump | after Q5 |
| At which px per frame does he see steps, has he moved a game, which boards does he own? | slice 0's step threshold, Q6, scenario (b) | the PO | Q9, an account (user lens questions 1 and 5), plus P537 slice 0's blind step probe | after Q1 |
| What is the 34 ms paint made of: call count, Python-side work or collection? | A2 | the lead with the PO's bench | P550, one session, before any C | after Q3 |
| Does anyone else ask for fast MicroPython sprites? | A1 | the lead, from GitHub Discussions | T1 desk count (P548), one hour, deferred by D5 | not before the public release is for others |
| Does any adopt path reach 33 ms a frame? | A3, Q3 | the lead with the PO's bench | T2 adopt bench (P540), half a day per candidate | after Q3 |
| Does framebuf.blit over a frame view reach 12 ms? | A5 | the lead with the PO's bench | T3 trial (P541) | after Q3 |
| What C++ flags does a MicroPython usermod get? | A6, Q4 | the lead, no board | add cppexample to the s3lcd build and read compile_commands (P543), minutes | any time |
| Does one tree compile in four build systems? | A6, Q6 | the lead, the Arduino and Pico toolchains are not installed (a cost to name) | compile spike (P545) | after Q6 |
| What does a window cost on the board? | A7 | the lead with the PO's bench | send-overhead probe (P542) | with P537 slice 0 |
| Do the PIE kernels reach Espressif's numbers here? | R1's PIE row | the lead with the PO's bench | the `simd_bench` probe (P544) | after R0 |
| Does one version bump of the fork's image stay inside 4 hours? | A8 | the lead with the PO's time log | P551, one bump on a branch | before R1 |
| Which pieces of the fork carry which licence? | A10 | the lead | read each file header (P547) | before R1 |

## Results
<!-- Filled on a return; may stay empty until then. One row per result: what was tested, what was seen (verbatim,
with its pointer), the pass line met or missed, what it changes. -->
| date | source and pointer | what was seen | pass line met or missed | what it changes |
| --- | --- | --- | --- | --- |

## Budgets <!-- REQUIRED:electronics-firmware:budgets -->
<!-- Energy per mode · peaks per rail against the source · dissipation per part, each number with its provenance and
the rung that would settle it (electronics-firmware:R<n>). "n/a — no battery, motor, radio or regulator" is allowed. -->
No energy, rail or dissipation budget: the library adds no battery, motor, radio or regulator. Its budget is time and memory per frame, on the FireBeetle 2 ESP32-S3 with the DFR0664 (240 x 320, RGB565), from `council/tech-lead.md` PHYS-1 to PHYS-9:

| budget | number | provenance | rung that settles it |
| --- | --- | --- | --- |
| frame period | 40 ms today (FRAME_MS), 33.3 ms the target, 16.7 ms out of reach for more than half a screen (★C8) | games/app.py, bench.md:116, calculated | electronics-firmware:R1, then R6 (a game run) |
| full-frame wire time | 30.72 ms calculated, 31.0 ms measured at 40 MHz (★C5) | 153,600 B x 8 / 40e6, bench.md:84 | R1 done, R6 confirmed |
| partial send in play | flappy 11.3 ms (14 windows), runner 7.7 ms (7 windows), 22 to 31 % of a frame (★C8) | bench.md probe6, tile 16 | R6 done |
| fixed cost per window | about 128 µs (★C6), so 5.1 ms at windows=40 only if the "dma" window costs the same as a strip (untested) | a fit on three sends from two code paths carrying the strip bug | R6: the send probe (P542) |
| paint budget at 40 ms, synchronous show | flappy 27.5 ms, runner 31.1 ms (FRAME_MS − send − step), runner paints 34 ms a frame today (run 22, one board, 2026-11-02, log not kept) | PHYS-5, calculated, bench.md:116 | R6: P537 slice 0 averages |
| pixel work in C per full frame | fill 0.37 ms, copy 1.10 ms at 240 MHz, with PIE 0.06 and 0.11 ms (★C3, ★C27) | Espressif's cycles per pixel, arithmetic | R1 done, R6: the simd_bench probe (P544) |
| internal DMA RAM | largest block 188,416 B, one frame 153,600 B, 34,816 B left in the block (★C7) | bench.md 09:58 | R6: `heap_caps_get_largest_free_block` after `init()` |
| PSRAM copy per frame | 34 to 55 KB a frame at about 50 MB/s is 0.7 to 1.1 ms, plus a paint penalty of about 40 % into PSRAM, confounded (★C9) | forum bandwidths (field, search summary, H), bench.md run 14 against 15, which also differ in driver, orientation handling and the game-over path | R6: P537 slice 4b |
| flash | s3lcd.c 21,773 B text linked, frame.c 3,383 B, jpg and png code about 51 KB, 229,776 B free (★C13) | `xtensa-esp32s3-elf-size` text column, 2026-11-02, bench.md:6 | R0 done |
<!-- EXTEND:risks-sections -->
