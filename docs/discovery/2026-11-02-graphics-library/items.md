# Proposed items
<!-- Filing needs the decider's yes to this list: a D in brief.md that names items.md. One block per item; copy the
block for more. needed by: the decider's words, quoted. value proven by: a proof the decider can read.
status: proposed, or filed D<n>.
e.g. `- needed by: "I want to know what we should build next" (Lena, 2026-10-06)` -->
Numbers: P540 onward, the next free after P539 (`gh issue list -R xmejkal/spark --state all --limit 20`, read 2026-11-02: the newest is #743 P539). Spark's issue form (`.github/ISSUE_TEMPLATE/item.yml`) asks for Needed by, Value proven by and Archive. The board's Slice options hold no slice for this library, so each item asks the decider for a new one. The order below is the synthesizer's proposal: the cheap probes first, then the skeleton. D5 (the PO, 2026-11-02): the first release serves his games and is a public showcase, not yet for other people. Items stay small and testable, status proposed.

## One list with P537's slices 0 to 8
P537 (`p537-finding.md:134-143`, closed as Done) has nine slices. Its slices become build cards together with these items. Each slice is covered once, either by an item below or as a P537 slice card still to file. No repeat remains.

| P537 slice | covered by |
| --- | --- |
| 0 measure first, then the step probe | a P537 slice card to file. P550 reads its step one (average per phase) and adds the per-call timing |
| 1 even pace | a P537 slice card to file |
| 2 kept background and score text in C (glyph cache, `keep()` and restore inside `show()`) | a P537 slice card to file. P541 does not replace its text part |
| 3 sprites in C (`sprite()`, `blit()` with key and flips, orientation map in C) | a P537 slice card to file. P541 tests whether `framebuf.blit` can stand in for the blit part, P546 holds the walking skeleton of the same primitives, Q4 settles which one is built |
| 4 overlap (4a `show(wait=False)`, 4b PSRAM back buffer) | a P537 slice card to file. P542 gives its window cost |
| 5 tile layers and software parallax | a P537 slice card to file, later (R2 of the story map) |
| 6 soft edges | a P537 slice card to file, later, optional |
| 7 blend modes | a P537 slice card to file, later, optional |
| 8 PIE fill and copy | P544, the same work, one card |

Items with no slice: P540 (reopens P537's "No library is adopted whole" on the PO's "do not reinvent"), P542, P543, P545, P546, P547, P549, P550. P542 is a P536 follow-up, not P539 work.

## P540 — Spike: nobody measured whether an existing stack is fast enough → the adopt bench: one fixed scene on CircuitPython displayio plus `_stage`, lvgl_micropython and UIFlow2 `User_GFX` on the FireBeetle, ms per frame each
- type: spike <!-- REQUIRED:item-type -->
- needed by: "let's really not reinvent the wheel, we have a lot of inspiration" (the PO, 2026-11-02, #743) <!-- REQUIRED:needed-by -->
- value proven by: one table in bench.md: candidate, builds for this board yes or no, ms per frame for the fixed scene (20 sprites 16 x 16 with a key colour, a score text, a tiled background, 120 frames), against the pass line of A3 (no candidate at or under 33 ms) <!-- REQUIRED:value-proven-by -->
- depends on: Q3 (the PO's yes to benching before building), the PO's bench time <!-- REQUIRED:depends-on -->
- status: proposed <!-- REQUIRED:item-status -->
- label (the repository's type label): spike <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P539 #743 <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one <!-- REQUIRED:spark-process:slice -->
<!-- EXTEND:item-fields -->

## P541 — Spike: `frame.c` hides its pixels from Python → a buffer view of the frame, `framebuf.blit` with a key colour on it, and runner's sprite phase measured
- type: spike
- needed by: "fast sprites, tiles and text that I call from Python" (J2, from the PO's "all fully usable from micropython", #743)
- value proven by: runner's sprite-phase average at FRAME_MS 40 with the sprites drawn by `framebuf.blit`, against A5's line (under 4 ms, P537 slice 3's line), the C change is about 10 lines (an estimate), reversible
- note: text is not tried here. `framebuf.text` has no scale and the hud draws at scale 2 (games/gfx.py:344), so the text stays P537 slice 2's glyph cache in C. `framebuf` knows no orientation map, so the map stays in Python per call and its cost is counted. If A5 passes, slice 3's blit part becomes this adapter
- depends on: Q3, P537 slice 0 (the phase averages)
- status: proposed
- label (the repository's type label): spike
- parent (the epic, as a sub-issue): P536 #740
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P542 — Spike: the window cost is a fit on buggy runs → the send-overhead probe: n windows of equal bytes, n = 1 to 64, ms per show on the board
- type: spike
- needed by: "each frame painted and sent within one frame period" (J1, the PO's "smooth, not stucky", #741)
- value proven by: a table n against ms in bench.md and the fitted fixed cost per window, against A7's line (within 15 % of 0.08 ms + n x 0.128 ms + bytes / 5 MB/s), the default tile size and join rule follow from it
- depends on: the PO's bench time, the probe code lives in the fork behind a flag
- status: proposed
- label (the repository's type label): spike
- parent (the epic, as a sub-issue): P536 #740
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P543 — Spike: nobody knows which C++ flags a MicroPython user C module gets → add MicroPython's `cppexample` to the s3lcd build and read its line in `compile_commands.json`
- type: spike
- needed by: "use C but if possible C++ if not too much slower … the newest C++ standard" (the PO, 2026-11-02, #743)
- value proven by: the quoted compile line of the `.cpp` file (its `-std`, `-fno-exceptions`, `-fno-rtti` present or absent), and the `target_compile_options` line that fixes it, no board needed, minutes
- depends on: —
- status: proposed
- label (the repository's type label): spike
- parent (the epic, as a sub-issue): P539 #743
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P544 — P537 slice 8: the S3's PIE gain for fill and copy is Espressif's number, not ours → esp_lvgl_port's three `.S` files (fill, copy, `lv_macro_memcpy.S`) behind a build flag and `s3lcd.simd_bench(op, w, h, offset, reps)`, cycles per pixel for the C loop, a word loop and the asm
- type: spike
- needed by: "maybe we could even use the AI chip or instructions that the S3 has" (the PO, 2026-11-02, #743)
- value proven by: cycles per pixel at 16 x 16, 32 x 32, 127 x 127, 128 x 128 and 320 x 240, aligned and at a 2-byte offset, internal and PSRAM, within 25 % of Espressif's table at 128 x 128 aligned, and the frame-time gain in ms on one game, `machine.freq()` printed, so the clock is known. Done as P537 slice 8 states it: the files stay if a frame gains 2 ms or more, otherwise they go and the number stays in bench.md
- depends on: Q7 (Apache-2.0 with its notice allowed), P537 slices 2 and 3 (no PIE kernel before the paint is batched in C, ★C3), the PO's bench time
- status: proposed
- label (the repository's type label): spike
- parent (the epic, as a sub-issue): P539 #743
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P545 — Spike: "one core builds under four build systems" is a claim → one header and one fill into a surface, compiled as a MicroPython usermod, an ESP-IDF component, an Arduino-ESP32 sketch and a Pico SDK target, with a port macro per build file
- type: spike
- needed by: "the architecture really allowed for easy swap ins, porting and applying in various situations for various chips and models and firmwares and drivers" (the PO, 2026-11-02, #743)
- value proven by: 4 of 4 compile and link, each build log quoted, or the one that fails named with its error, the Arduino and Pico toolchains are not installed here, so their install cost is named first
- depends on: P543, Q6 (which targets the MVP must build)
- status: proposed
- label (the repository's type label): spike
- parent (the epic, as a sub-issue): P539 #743
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P546 — the drawing primitives live inside `s3lcd_obj_t` and raise Python errors from C → a walking skeleton: a surface type with signed, clipped `fill_rect` and `blit_keyed`, error codes, host golden-hash tests under ASan, bound into the fork so one game paints through it
- type: story
- needed by: "good engineering practices, code design and tests, refactorings, from the beginning" and "the MVP is ok to just be quick and dirty, but always refactor and test" (the PO, 2026-11-02, #743)
- value proven by: `ctest` green on the Mac with the golden hashes, one bench.md run line of a game painting through the new call at no worse frame time than run 22, and the diff that shows no `py/*.h`, esp_lcd or FreeRTOS include under `core/`
- note: P537 places a new `scene.c` beside `frame.c` with `frame_t` as its only dependency (p537-finding.md:108), but `frame_t` lives in `frame.h`, which includes FreeRTOS, esp_lcd and `py/obj.h` (frame.h:13-17). Either P537's layer design or this include rule changes. Q4 settles it: until then slices 2 and 3 keep `frame_t`, and this card waits. It covers the primitives of slice 3 in the core's form
- depends on: Q4 (the layer shape A or B, with or without C, and the `scene.c` dependency), Q5 (the standard), P541's result (adapter or C blit first)
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P539 #743
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P547 — Chore: the fork mixes MIT, public-domain, zlib and ChaN-terms files with no licence table → a COPYRIGHTS table with a row per bundled file (path, licence, copyright, source URL), read from each file's header, before anything is public
- type: chore
- needed by: "in the end make it public" (the PO, 2026-11-02, #743)
- value proven by: the table in the fork, one row per file under `src/`, every row with a permissive licence or the file removed. The lead found that 11 of 14 `pngenc` files name `zlib.h`, whose line 4 carries the Gailly and Adler copyright, and TJpgDec carries ChaN's terms (tjpgd565.c:2-13), so the rows quote those
- depends on: Q7 (which licences may enter)
- status: proposed
- label (the repository's type label): chore
- parent (the epic, as a sub-issue): P539 #743
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P548 — deferred by D5 (A1 rated low) — Spike: nobody besides the PO has asked for fast MicroPython sprites, as far as one search saw → a one-hour desk count of MicroPython and CircuitPython GitHub Discussions, last 12 months, posts asking for faster sprites, tiles or text on ESP32 or RP2 colour displays
- type: spike
- needed by: "make it public … so we can really offer a good thing" (the PO, 2026-11-02, #743)
- value proven by: a list of the posts with URL and date, the count of distinct posters, against A1's line (5 or more), and the search terms used, secondhand accounts, labelled so
- depends on: Q1 (the PO's pass line for the riskiest test)
- status: proposed, deferred by D5 until the PO wants other people as users
- label (the repository's type label): spike
- parent (the epic, as a sub-issue): P539 #743
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P549 — Chore: bench.md contradicts itself on the strip cost and p537-finding.md carries three stale reuse claims → both documents say one thing, with the pointer that settled each
- type: chore
- needed by: "comments throughout that get checked and updated if stale" (the PO, 2026-11-02, #743), applied to the two documents the library stands on
- value proven by: bench.md:77 and bench.md:100 agree (the one-row strip bug held in slices 1 to 3, per s3lcd.c:2809), p537-finding.md's st7789_mpy date, its LVGL "no esp32 path" and its "no published number" lines corrected with PO-7's pointers, the 40 to 55 KB copy line recomputed with the window overhead removed (PHYS-3)
- depends on: P537 #741 leaving Review (or the fix lands on that card)
- status: proposed
- label (the repository's type label): chore
- parent (the epic, as a sub-issue): P536 #740
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P550 — Spike: nobody measured what the 34 ms runner paint is made of → the paint composition probe: calls per frame, cost per call and collection time, in one session on the board
- type: spike
- needed by: "smooth, not stucky" (the PO, 2026-11-02, #741, J1), and the refuter's riskiest assumption under D5 (A2)
- value proven by: three numbers in bench.md: (a) `fill_rect` calls per frame for runner, from a counter in `TftCanvas.fill`, (b) the cost of one 8 x 8 and one 240 x 16 `tft.fill_rect`, 1000 calls each by `time.ticks_cpu()`, (c) the average paint per phase (P537 slice 0) and the collection time inside it (`GC_FRAMES` 0 for one run). Pass line, set 2026-11-02 before any result: calls per frame times the per-call cost accounts for at least 70 % of the 34 ms. Under 40 %: batching alone will not reach 12 ms
- depends on: P537 slice 0 step one (the phase averages), the PO's bench time, Q1 (the PO rates A2)
- status: proposed, the refuter's opinion, pending Q1
- label (the repository's type label): spike
- parent (the epic, as a sub-issue): P539 #743
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## Board actions
<!-- Each action, taken or pending, with its D. e.g. `- move the item to Discovery · pending` -->
- file P540 to P550 as issues, except P548 (deferred by D5), and file the P537 slice cards of the table above with their labels, each a sub-issue of P539 #743 or P536 #740, after the PO's yes to this list · pending <!-- REQUIRED:board-actions -->
- ask the PO for a new Slice option for the library (none of the board's options fits) · pending
- run spark's `tools/check_backlog.py` after filing · pending
- order the Ready column with P543 first (no board, no bench), then P550, P541 and P542 (bench), as a proposal for the PO · pending
