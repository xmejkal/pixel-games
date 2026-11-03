# Risks and tests

## Risks
<!-- One row per type; an active extension adds its own rows. evidence now: tag and ids (★C<n>, A<n>).
status: open · retired · n/a because ….
e.g. `| usability | H no test yet (A2) | a five-person prototype test | open |` -->
| risk | evidence now | cheapest way to retire it | status |
| --- | --- | --- | --- |
| value <!-- REQUIRED:risk-value --> | H: the look on this panel (A1, the proposed riskiest) and ten looks from six kernels (A5). His one verdict is on the rain (★C24 (n = 1)) | his play of the walking skeleton with A1's fixed question and its pass line, which a result can miss. Then his words on the first group (A5) | open |
| usability <!-- REQUIRED:risk-usability --> | E: a ring of 21 with no name on screen and a step bar at 0 px in C (★C21, ★C22). H: whether he reads the cost at all (A6) | the harness question Q6, the account question Q12, and his play of P595 | open |
| feasibility <!-- REQUIRED:risk-feasibility --> | H: the C pixel path (A2, ★C6), colliding circles (A7, ★C12, ★C13). E: the room is bracketed by run55 and run54 (A4, ★C4). Unmeasured: the cost of a computed write into the PSRAM frame (★C3). Every kernel cost is H (★C11, ★C14) | the walking skeleton on the board (P595), a Mac test of the circle grid (D15). Levers if a scene misses: `covers` (F6), path B instead of A, a strip or a window, the cached HUD (F1) | open |
| viability <!-- REQUIRED:risk-viability --> | E: three homes claim the kernels (★C19). H: costs alone do not carry into a game (A3, ★C15) | the PO's answers to Q5 and Q9, then the card edits in items.md | open |
| value: his words on method <!-- the PO assistant's pre-mortem cause 3 --> | H: he asked for "special assembler methods or through ESP-IDF" (E #795), and options g1 and g2 may show none (PO-26). A scene alone writes opaque pixels, where PIE gains least (★C15 (black understates a game's cost)) | his answer to Q8 | open |
| ethics and safety <!-- REQUIRED:risk-ethics --> | E: EUPL, GPL and all-rights-reserved sources sit beside MIT ones (★C18). The repository is public and MIT | the proposed no-go, Q11, and a notice file for any copied code (A11) | open |
| power and battery <!-- REQUIRED:electronics-firmware:power --> | n/a: no battery. The board runs on USB, and an effect adds no part | — | n/a because no battery or new load |
| current and stall <!-- REQUIRED:electronics-firmware:stall --> | n/a: no motor | — | n/a because no motor |
| thermal <!-- REQUIRED:electronics-firmware:thermal --> | n/a: no new part. The CPU already runs at 240 MHz in every game (p580-finding.md:3) | — | n/a because no new part |
| EMC and ESD <!-- REQUIRED:electronics-firmware:emc-esd --> | n/a: no new part, no radio, no fast switching beyond today's panel bus | — | n/a because no new part |
| sensor drift and calibration <!-- REQUIRED:electronics-firmware:sensor-drift --> | n/a: no sensor | — | n/a because no sensor |
| brown-out <!-- REQUIRED:electronics-firmware:brown-out --> | n/a: no new load on the rail | — | n/a because no new load |
| wake and low power <!-- REQUIRED:electronics-firmware:wake --> | n/a: the scenes never sleep | — | n/a because nothing sleeps |
| the firmware–hardware contract <!-- REQUIRED:electronics-firmware:contract --> | E: internal RAM left on the engine image is unmeasured (★C8, A9). H: whether ESP-IDF 5.5.2 saves the PIE registers on a task switch, and whether a `.S` builds in the module (★C17, A10). E: C state outlives a soft reset (★C7) | R6: print the largest free internal block at each scene's start. R0: read ESP-IDF 5.5.2's coprocessor save code before any `.S`. R3 is no help: a simulator does not model PIE or PSRAM timing (H) | open |
| supply and documents <!-- REQUIRED:electronics-firmware:supply --> | E: the PIE facts come from TRM v1.8 (sha256 4484bf8a…, p580-finding.md:32), and esp-dsp's file list from master 3c8ac0fd, tag v1.8.2 (FX-37). B couples to the fork's `s3lcd_obj_t` (★C6) | R0: cite the TRM page and the esp-dsp tag in any `.S` card | open |
<!-- EXTEND:risk-rows --><!-- EXTEND:pair-rows -->

## Assumptions
<!-- About ten at most. type: value, usability, feasibility, viability or ethics. importance: "— (decider)" until
the decider rates it, then "high D<n>" or "low D<n>". pass line: written, with its date, before any result.
status: open, or retired with the date of its Results row.
e.g. `| A2 | Assignees never see new tasks | value | H ★C2 | — (decider) | query opened-within-48h | under 50 %, set 2026-10-06 | over 80 % | open |` -->
| id | belief | type | evidence now | importance | cheapest test | pass line, dated | result that would change the decision | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 <!-- REQUIRED:assumptions --> | the effects read as "cool" on the 2.0 in 240 x 320 RGB565 panel at 24 fps, so he keeps a scene as it looks (the riskiest, D2) | value | H ★C24 (n = 1), PO-27 (32 levels of red and blue may band soft smoke), PO-31 cause 2 (small windows on black may look like a 1990s demo) | high (D2) | his play of the walking skeleton, his words written down first, then one fixed question: "Keep the fire as it looks now, or change its look before the next scenes?" | proposed 2026-11-03, before any result: he keeps it as it looks, with no change asked to its palette, size or banding. A change asked, or a word such as "flat" or "banded", is a miss | a miss: the palette or the size changes before the next scene is built | open |
| A2 | plain C in the engine module writes an effect's pixels to the screen cheaply enough that a full-screen fire fits the room with today's HUD | feasibility | H ★C5, ★C6, ★C11 (no path exists, the kernel cycles are H). On the folder's numbers it is expected to pass: about 7.3 to 9.9 ms against 15.3 to 18.2 (★C4) | — (decider) | the walking skeleton P595 on the board | proposed 2026-11-03: the fire's step plus draw, read from app.py's `time` and `avg` lines (the `time` step plus the `avg` paint minus static, fx and hud), is at most 15.3 ms in each of three 5 s intervals, on the path Q4 picks. Under AB each path is read on its own, and the result names the path. The fps is recorded, not judged: under about 37 ms of logged work it prints 24 whatever the effect costs | over 15.3 ms: `covers` (F6), path B instead of A, a strip or a window, or the cached HUD first | open |
| A3 | the cost measured alone tells P583 what the effect costs in a game | viability | H ★C15 (about 6 times more through `blit_buffer`'s alpha path, maybe 1.5 to 3 times in a kernel's own loop) | — (decider) | the same fire over a painted background at alpha 128, timed in P595 | proposed 2026-11-03: the blended fire's step plus draw is at most 15.3 ms, the room with today's fill and HUD | over 15.3 ms: P583 needs a window, the SWAR blend or PIE first | open |
| A4 | the room for an effect's step plus draw is what run55 and run54 bracket: 15.3 to 18.2 ms with today's fill and HUD, about 19.9 to 22.9 ms with `covers` | feasibility | E ★C4 (run55-p593-rain-c160.log:10, :12, run54, games/lcd.py:142). Calculated by the synthesis. The 3.5 to 5.7 ms of loop and sleep is not split in the log | — (decider) | P595's `time` and `avg` lines | proposed 2026-11-03: every P595 interval whose step plus draw is at most 15.3 ms prints 24 or 25, and none at 18.9 ms or more prints 24 | either fails: the bracket is wrong, so every size in ★C11 and ★C14 moves | open |
| A5 | six kernels give ten looks he counts as ten | value | H PO-18, PO-31 cause 1 | — (decider) | his words after the first K1 group (fire, smoke, bodies on fire) | proposed 2026-11-03: he names the three as different effects | he calls them one effect in three colours, so the list moves to a2 or a3 | open |
| A6 | he can reach, name and read each scene: its name on screen and a cost he understands | usability | E ★C21, ★C22. H USER-11 (he does not read the log) | — (decider) | the account question Q12, then one play session of the harness | proposed 2026-11-03: he finds a named scene without going round the ring twice | he asks which scene it is, or goes past it | open |
| A7 | 300 colliding circles cost about 3.4 ms and do not pass through each other with 3 substeps at 2,000 px/s² | feasibility | H ★C12, ★C13. Rival: 3 to 10 ms if they pile (the refuter) | — (decider) | a Mac test of the grid (D15), then the board | proposed 2026-11-03: no circle passes through another in a 60 s Mac run, and the board step is at most 5 ms. Both bars are the team's: his only word on bodies is "colliding" | tunnelling or over 5 ms: fewer or larger circles, or c2 | open |
| A8 | the kernels built here are the ones P583 and P592 use, in one home, with no second build or move | viability | E ★C19, H ★C20 | — (decider) | the PO's answers to Q3 and Q5, then the card edits | none set, 2026-11-03: a decision, no test | he picks d2 or d3, so the kernels move or are built twice | open |
| A9 | the engine image leaves enough internal RAM for a 19,200 B effect field | feasibility | E ★C8 (unmeasured on this image, no estimate) | — (decider) | print the largest free internal block at the scene's start, R6 | proposed 2026-11-03: at least 19,200 B free in one block | less: every field goes to PSRAM, at its read and write cost | open |
| A10 | a `.S` kernel builds in the engine module and runs safely beside MicroPython's task and the LCD interrupt | feasibility | H ★C17 (strong code evidence for the build, nothing for the PIE registers) | — (decider) | R0: read ESP-IDF 5.5.2's coprocessor save code. Then one 10-line `.S` build, only if Q8 picks g2 or g3 | none set, 2026-11-03: asked only if Q8 brings PIE in | the registers are not saved: a PIE kernel must run with a lock, or not at all | open |
| A11 | no code under EUPL, GPL or all rights reserved lands in the public MIT repository | ethics | E ★C18 | — (decider) | a review of each slice's sources and a notice file, from Q11 | proposed 2026-11-03: every copied file names its source and licence, and none is from the no-go list | a slip: the file comes out before the PR merges | open |

## Collection plan
<!-- One row per gap. e.g. `| Do assignees open new tasks? | Q2 | Lena, from analytics | one query | this week |` -->
| question | decision it blocks | who can answer | how | when |
| --- | --- | --- | --- | --- |
| How important is each assumption, and what pass line must A2 meet? <!-- REQUIRED:collection --> | all, Q1 | the PO | AskUserQuestion, Q1 | first |
| Did he read the rain's HUD or tap BOOT? | A6, A1, Q12 | the PO | account question Q12 (Q-U1, Q-U2 in council/user.md) | second, after Q1 |
| What do the fire kernel and the pixel path cost on the board, what does a computed write into the PSRAM frame cost (55.3 to 88.9 ns/px, ★C3), and how much internal RAM is free? | A2, A3, A4, A9, Q4 | the AI team, on the board | the walking skeleton P595, with app.py's `time` and `avg` lines and one heap print | after Q1 to Q6 |
| Do 300 circles in a pile cost about 3.4 ms, or 3 to 10 ms? | A7, Q3 | the AI team | a Mac test (D15), then the board | only if Q3 picks c1 or c3 |
| What does "cheap enough" mean to him, and what does "being on fire" mean? | Q13, Q14 | the PO | AskUserQuestion | after Q12 |
| Does the fire look cool on the panel? | A1 | the PO | his play of P595 (D21) | after P595 is ready to play |
| Does ESP-IDF 5.5.2 save the PIE registers on a task switch? | A10, Q8 | the tech lead | R0: read the IDF source | only if Q8 brings PIE in |
| Is Adafruit_PixelDust's BSD licence 2-clause or 3-clause? | A11 | the AI team | read its LICENSE file | only if K6 copies from it |

## Results
<!-- Filled on a return; may stay empty until then. One row per result: what was tested, what was seen (verbatim,
with its pointer), the pass line met or missed, what it changes. -->
| date | source and pointer | what was seen | pass line met or missed | what it changes |
| --- | --- | --- | --- | --- |

## Budgets <!-- REQUIRED:electronics-firmware:budgets -->
<!-- Energy per mode · peaks per rail against the source · dissipation per part, each number with its provenance and
the rung that would settle it (electronics-firmware:R<n>). "n/a — no battery, motor, radio or regulator" is allowed. -->
Energy, rails and dissipation: n/a — no battery, motor, radio or regulator. The board is USB-powered in play. The budgets this item spends are frame time and memory:
- frame: pace 40 ms, so 25 fps at most (stated, games/app.py:27). The rain at N 160 in C: step 0.16 to 0.17, read 1.06 to 1.14, draw 13.47 to 14.01, HUD 10.6 to 10.9 ms, 24 fps (measured, bench.md:268-274, run55). The rest of the rain's frame (measured, run55-p593-rain-c160.log:10, :12, 5 intervals): background fill 4.6 to 4.7, fx 0.1, HUD 10.6 to 10.9, copy 3.2 to 3.3, gc 1.6 to 1.7 ms, and 3.5 to 5.7 ms of loop and sleep (inferred from the fps floor). Effect room for step plus draw: 15.3 to 18.2 ms with today's fill and HUD (measured bracket: N 160 prints 24, N 192 prints 23, run54), about 19.9 to 22.9 ms with `covers` (games/lcd.py:142), about 25.5 to 28.7 ms with a cached HUD, about 30 to 33 ms with both (calculated by the synthesis, the HUD at 0.40 ms calculated). Settles: R6.
- per pixel into the PSRAM frame: a memcpy's PSRAM penalty over internal 55.3 ns, an opaque blit 88.9 ns in all (calculated from bench.md:198, measured run46), `blit_buffer`'s alpha path 337.5 ns with its per-pixel checks (measured, bench.md:205). A computed write from a C loop: unmeasured, between about 55.3 and 88.9 ns (H, the refuter's bound). Kernel cycles per pixel: H (P580 and the tech lead). Settles: R6.
- full-screen send: a full `show()` is a 3.4 ms copy plus a send of about 30 ms in the background, 33.4 ms in all, so about 30 fps at most when every tile changes (measured, bench.md:186, run41; fps calculated). Settles: R6.
- internal RAM: largest free block 31,744 B on the s3lcd image while the games run (measured, bench.md:186). The engine image adds 12,320 B of static RAM (stated, engine/core/world.h:11). Free internal RAM on the engine image: — (not measured, bench.md:279). Settles: R6, one print.
- flash: 222,576 B left in the app partition on the engine image (measured, bench.md:264). Settles: R6 per build.
<!-- EXTEND:risks-sections -->
