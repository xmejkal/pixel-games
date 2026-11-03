# P594 effects discovery: tech lead (feasibility, vision, lens electronics-firmware:physics)

Opus 5.5, 2026-11-03, read-only on the tree. Tags: E evidence with a pointer, H a hypothesis and its source, D a decision (who, when). An unknown is written as "unknown". Clock 240 MHz, one cycle 4.17 ns (E: p580-finding.md:3, build-s3lcd/sdkconfig:1592). Every number below was computed by `budget.py` in the session scratchpad (not in the tree). Its inputs and their provenance are listed under PHYS-1. "Effect room" means the ms that one effect can use for its step and draw while the scene still holds 24 fps.

## Findings

### Physics lens (PHYS)

- **PHYS-1 · The inputs.**
  - Alpha compose with s3lcd's `alpha_blend_565`: 337.5 ns/px into the PSRAM frame (E: bench.md:205, run46).
  - Extra cost of a PSRAM write: 55.3 ns/px. Calculated from (6.83 − 2.58) ms / 76,800 px (E: bench.md:198).
  - Opaque PSRAM-to-PSRAM blit: 88.9 ns/px. Calculated from 6.83 ms / 76,800 (E: bench.md:198).
  - Copy into the internal frame: 33.6 ns/px. Calculated from 2.58 ms / 76,800.
  - C float step: 0.135 µs per body-step, with no contacts (E: bench.md:238).
  - The rain at N = 160: step 0.16 to 0.17 ms, read 1.06 to 1.14, draw 13.47 to 14.01, HUD 10.6 to 10.9 ms, 24 fps. At N = 192: 23 fps (E: bench.md:268-274).
  - Frame pace: `FRAME_MS = 40` (E: games/app.py:27). That is 25 fps at most, not the brief's "about 41 ms".
  - The cycles per pixel of each kernel are H. Fire 30 cycles and palette 8 come from p580-finding.md:19. Ripple update 15 cycles and render 175 ns/px come from p580-finding.md:21. The rest are my own instruction-count guesses, each marked below. · supports: every cost below.

- **PHYS-2 · The effect room is about 15 ms today and about 26 ms with a cheap HUD.**
  - The rain's game side (step, read, draw and HUD) is 25.3 to 26.2 ms at 24 fps. At N = 192 it is 27.3 to 28.9 ms, which gave 23 fps (calculated from bench.md:268-274).
  - So the fixed rest of a 40 ms frame is about 14 ms: background fill, the `show()` copy, gc and the loop.
  - The 24 fps line sits at about 26 to 27 ms of game-side work. Subtracting the HUD gives an effect room of about 15 ms with today's HUD and about 26 ms with a 0.3 ms HUD.
  - Calculated, from E inputs. The 14 ms rest is inferred, not measured per part. · supports: Q2 and the size of each effect.

- **PHYS-3 · A full-screen change caps the frame at about 30 fps, and 24 fps still fits.**
  - When every tile changes, `show()` costs a 3.4 ms copy plus a send of about 30 ms in the background, 33.4 ms in all (E: bench.md:186). That is 29.9 fps at most (calculated).
  - At the 40 ms pace, a full-screen effect with its paint inside the room of PHYS-2 keeps 24 fps.
  - The rain already changes most tiles, so its 24 fps already includes this send (H: 160 boxes spread over the whole screen. The window count was not logged). · supports: full-screen effects are possible.

- **PHYS-4 · The rain's draw time is Python call overhead, not pixels.**
  - 160 fills of 4 x 4 cost 84 to 88 µs each (calculated from bench.md:270).
  - The pixels themselves are 2,560 x 55.3 ns = 0.14 ms, about 1 % of the draw.
  - The same rain drawn in C costs about 0.19 ms (H: 0.3 µs per call is my guess).
  - Any effect drawn element by element from Python is capped near 150 to 300 elements: 500 particles cost 42 ms and 2,000 cost 169 ms (calculated). So the effects draw in C. · supports: Q3, and D11's "drawing moves to C".

- **PHYS-5 · Cost per frame of each candidate, plain C, best layout.** Compose: write-only 55.3 ns/px, or s3lcd alpha 337.5 ns/px. All values calculated.

  | effect | method | working memory, where | ms per frame (formula) | fits 15 ms (today's HUD) · 26 ms (cheap HUD) |
  | --- | --- | --- | --- | --- |
  | fire, full resolution | Lode heat kernel, palette, opaque write | 76,800 B u8, PSRAM (over the internal block) | 76,800 x (30 + 8 cycles x 4.17 + 55.3 ns) = 16.4 | no · yes |
  | fire, half resolution, 2 x 2 output | same | 19,200 B u8. Internal RAM, space permitting (PHYS-8) | 19,200 x 38 cycles + 76,800 x 55.3 ns = 7.3 | yes · yes |
  | fire, 320 x 80 strip | same | 25,600 B | 25,600 x (158 + 55.3 ns) = 5.5 | yes · yes |
  | smoke, half-res kernel, full screen through s3lcd alpha | same kernel, alpha over the background | 19,200 B | 19,200 x 158 ns + 76,800 x 337.5 ns = 29.0 | no · no |
  | smoke, the same with a SWAR blend (PHYS-6) | about 15 cycles a pixel plus PSRAM read 34 and write 55 ns (H) | 19,200 B | 14.7 | yes, at the limit · yes |
  | smoke, 160 x 120 window, s3lcd alpha | | 19,200 B | 19,200 x (158 + 337.5) ns = 9.5 | yes · yes |
  | particles 500 / 2,000 (sparks, dust, embers, rain) | SoA, 4 steps a frame, 2 x 2 dots, drawn in C | 500 x 10 B = 5 KB / 20 KB | n x 4 x 0.135 µs + n x (4 x 55.3 ns + 50 cycles) = 0.48 / 1.94 | yes · yes |
  | colliding circles 300 / 1,000 | uniform grid, 2 iterations, 4 steps, about 6 candidates of 25 cycles each (H), r = 4 discs of about 50 px | 300: about 8 KB. 1,000: 20 B a body + grid 2,400 B + next 2,000 B = 24.4 KB | collide + integrate + draw: 300 = 1.50 + 0.16 + 0.90 = 2.6. 1,000 = 5.0 + 0.54 + 3.0 = 8.6. Substeps for PHYS-9 add about 50 % to the collide part | yes · yes |
  | bodies on fire (300 circles, each body puts heat into the half-res fire field) | the two above, composed | about 27 KB | 2.6 + 7.3 = 9.9 | yes · yes |
  | water: ripple, half-res field, full-screen render | Elias two-buffer, displaced lookup | 2 x 19,200 x 2 B = 76.8 KB, PSRAM | 19,200 x 15 cycles + 76,800 x 175 ns = 14.6 | at the limit · yes |
  | water: ripple, 128 x 128 window | same | 64 KB int16 (PSRAM) or 32 KB int8 | 16,384 x (62.6 + 175) ns = 3.9 | yes · yes |
  | water: a surface of 320 spring columns over a 320 x 100 body | 1D springs, column fills | 320 x 8 B | about 0.01 + 32,000 x 55.3 ns = 1.9 | yes · yes |
  | water or sand: cellular grid 160 x 120 | falling-sand rules, 2 x 2 output | 19,200 B u8 | 19,200 x 15 cycles + 76,800 x 55.3 ns = 5.5. Writing only the changed cells costs less | yes · yes |
  | water: a particle liquid (SPH or PBF), 500 particles | about 20 neighbours, 2 passes, 40 cycles each (H), 4 steps | about 15 KB | 4 x 500 x 20 x 2 x 40 cycles = 13.3, plus draw about 1.5 = about 15 | no · yes |
  | metaballs, half-res, 8 balls | field sum through a lookup table | 1/r² table | 19,200 x 80 cycles + 76,800 x 55.3 ns = 10.7 | yes · yes |
  | plasma, full resolution | 3 sine lookups | 1 KB tables | 76,800 x (15 cycles + 55.3 ns) = 9.1 | yes · yes |
  | cloth or rope, 300 points | Verlet, 600 constraints, 4 iterations x 4 steps, sqrt 91 cycles (search 3, a preprint) | about 7 KB | 600 x 16 x 121 cycles + lines = 5.0 | yes · yes |
  | glow, dissolve, shake, noise smoke, shatter | as p580-finding.md:22-26 | as there | 0.25 to 2.9 at 64 x 64. Shake: a full copy and send | yes · yes |

  · supports: Q1 and Q2. Every row with H cycles can be 2 x off. The ranking survives that error. The fits columns near the line ("at the limit") do not.

- **PHYS-6 · The 337.5 ns/px is s3lcd's naive blend, not a floor for plain C.**
  - `alpha_blend_565` unpacks three channels and multiplies each twice, with two branches per pixel (E: s3lcd/src/s3lcd.c:186-199). Its blit path adds a bounds check per pixel (E: s3lcd.c:630-641).
  - A SWAR blend packs red and blue in one 32-bit word and green in another, with one multiply each (E: [VirtualDub, entry 117](https://virtualdub.org/blog2/entry_117.html), [embedded-3dgfx blend.rs](https://docs.rs/crate/embedded-3dgfx/latest/source/src/pipeline/rasterize/draw/blend.rs), read as search summaries 2026-11-03).
  - My guess is 10 to 15 cycles a pixel on the S3 (H: instruction count), so about 150 ns/px into PSRAM with the read and the write.
  - So the cheapest rung on the compose is C, not PIE. P580 aimed PIE at the compose, and a C blend 2 to 3 x faster comes first. · supports: Q5, and where PIE pays.

- **PHYS-7 · Panel order decides the write cost.**
  - Game x runs along the panel's y (E: games/lcd.py:18-21, 59-88). So a game row is a panel column, and writing it costs 2-byte strided writes into PSRAM (E: p580-refuter.md:15, bench.md:77 as cited there).
  - Keep effect grids in panel order, so each output row is a sequential write (H, as p580-finding.md:46 proposes). Every cost in PHYS-5 assumes this. · supports: Q3, and the shape of the pixel view.

- **PHYS-8 · The 31,744 B free internal block was measured on the s3lcd image, not on the engine image.**
  - The 31,744 B is from run41, P556 (E: bench.md:186).
  - The engine image adds 12,320 B of static RAM for the two worlds (E: engine/core/world.h:11. My sum is 6,160 x 2). P593 did not measure free internal RAM (E: bench.md:279).
  - So the internal scratch that an effect gets on today's image is unknown. When `.bss` comes out of the same region, it is possibly under 20 KB (H). · supports: where each buffer lives. Only half-res fields of 19,200 B or smaller are candidates for internal RAM.

- **PHYS-9 · Colliding circles tunnel at the engine's 10 ms step under stack's gravity.**
  - A fall of 240 px at g = 2,000 px/s² (E: games/rain.py:31) gives v = sqrt(2 x 2000 x 240) = 979.8 px/s. That is 9.8 px a step at 10 ms (D18), more than the 8 px diameter of r = 4 circles.
  - At 5 ms a step it moves 4.9 px, and at 3.33 ms it moves 3.27 px.
  - So equal circles of r = 4 need 3 substeps, or a radius of about 10 px or more, or a lower g (calculated).
  - The fixed step holds (D18). Substeps change only the count of inner steps. · supports: Q4, the size of the smallest addition.

- **PHYS-10 · World.c collides each body with its own plane only. No body touches another today.**
  - The step tests `y >= rest_y` per body (E: engine/core/world.c:77-90, 111-124). The body arrays hold x, y, vx, vy and rest_y. There is no radius, size or contact (E: world.h:29-40).
  - The events are HIT and SLEEP only (E: world.h:14), with at most 64 per step call (E: world.h:12). · supports: Q4.

### Tech lead (TL)

- **TL-1 · The smallest addition for body-body collision.**
  - A radius array, one value per body.
  - A uniform grid with a cell size equal to the diameter: a head index per cell and a next index per body.
  - Position-based separation of overlapping pairs, 2 iterations a substep.
  - Optional: Verlet integration, which keeps the velocity implicit.
  - About 120 to 200 lines of C in core/ (H: the size of the PHYS-5 kernel).
  - Cost: 2.6 ms for 300 bodies and 8.6 ms for 1,000. Inputs: 0.135 µs a body-step for the integration (E), and about 150 cycles a body-iteration for the pairs (H).
  - The square root is paid only for overlapping pairs. Every test compares squared distances. A native sqrt costs about 91 cycles (search 3, a preprint: H-grade).
  - Memory: 1,000 bodies take 24.4 KB, too much for the internal block (PHYS-8), so they go to PSRAM. 13.4 KB for 500 is cache-sized (H). · supports: Q4.

- **TL-2 · It fits D16 as a broadphase, and only partly as a solver for P592.**
  - D16 asks for an own small solver behind a swappable interface: step, bodies by id, the event buffer (E: engine brief.md:292).
  - The grid broadphase and the contact pairs are what Box2D-Lite's arbiter and P592's tip and topple need too, so that part is shared (H: the Box2D-Lite structure, from model knowledge, not read this session).
  - P592 needs boxes with an angle, angular speed, a box-box narrowphase and impulses accumulated over iterations. Circle position-correction does not give that.
  - So: the grid in core/ as a shared module, the circle solver as an effects mode, the rigid solver later on the same grid. A circle-only solver shown as the engine's rigid solver is a wrong promise (H). · supports: Q4, and the order against P592.

- **TL-3 · Two ways to the screen, and one core either way.**
  - The core kernel writes into a plain pixel view (`uint16_t *px, stride, w, h`) in panel order. It knows neither s3lcd nor MicroPython. That keeps D15's Mac build of the same C. Pixel-exact tests run by ctypes, the way tests/test_engine_core.py builds world.c. Only the binding chooses what the view points at.
  - **A, a Python-owned buffer that Python blits.**
    - Touches only engine/ (binding.c and core).
    - It doubles the pixel traffic: a full screen costs 76,800 x (55.3 + 88.9) ns = 11.1 ms, against 4.25 ms for B.
    - A full-screen RGB565 buffer is 153,600 B, so it lives in PSRAM. A 160 x 120 window of 38,400 B also exceeds the internal block.
    - The opaque and keyed paths of `blit_buffer` are row copies (E: s3lcd.c:611-627), and it marks the tiles itself (E: s3lcd.c:604). Its alpha path is the slow per-pixel blend (E: s3lcd.c:630-641).
    - Python must map game coordinates to the panel, as `TftCanvas.picture` does (E: lcd.py:90-93).
  - **B, the engine writes into the s3lcd frame.**
    - The binding takes the `tft` object and checks it with `mp_obj_is_type(obj, &s3lcd_type)`. `s3lcd_type` is a non-static global (E: s3lcd.c:2782-2799). s3lcd.h does not declare it, so it needs one `extern` line (E: s3lcd.h:86-123 declares only `s3lcd_make_new`, `draw_pixel`, `fast_hline`).
    - It reads `frame_buffer`, `width` and `height` from `s3lcd_obj_t` (E: s3lcd.h:86-114) and marks the drawn rectangle with `frame_dirty()`, a static inline in frame.h:62.
    - frame.h includes FreeRTOS, esp_lcd and `py/obj.h` (E: frame.h:13-17), so this code lives in binding.c or port/s3/, never in core/.
    - The include path is already shared. MicroPython gathers every user module's include directories into one list for the main component, so engine sources already see s3lcd/src (E: ~/esp/micropython-v1.29.0/py/usermod.cmake:19-21, ports/esp32/esp32_common.cmake:236).
    - The cost is one write a pixel. The risk is ABI coupling to the `s3lcd_obj_t` layout. The risk is low, because both modules build in one image (E: micropython.cmake:2-3).
  - B is what D17 names ("reaches the screen only through s3lcd.h") and what D11 points to (drawing moves to C). A is the cheaper first slice only for small keyed windows. · supports: Q3.

- **TL-4 · Today's HUD is the largest single cost that a cheaper version can cut.**
  - The HUD draws an 8 x 8 font as one `TftCanvas.fill` per glyph run through Python (E: lcd.py:104-105, gfx.py:107-135). That costs 10.6 to 10.9 ms a frame in the rain (E: bench.md:274) and 8.2 to 10.96 ms in runner (E: bench.md:158, 162).
  - The label changes only every 500 ms (E: rain.py:34). The frame is refilled every frame, untracked (E: lcd.py:142-143).
  - Smallest cheaper HUD: when the label changes, Python renders it once into a panel-order RGB565 buffer of 320 x 14. Each frame, one `blit_buffer` on the memcpy path costs 4,480 x 88.9 ns = 0.40 ms (calculated).
  - That gains about 10.5 ms a frame and roughly doubles the effect room (PHYS-2). It decides whether full-res fire, full-screen ripple and a particle liquid fit. It helps the ten games too, so it is a "found on the way" item, not part of this scope (H). · supports: Q2.

- **TL-5 · A `.S` file can very likely sit in the user module. Unproven until one build.**
  - The usermod sources are compiled in the main IDF component (E: esp32_common.cmake:224-245, 297), and the IDF project enables ASM (E: ~/esp/esp-idf-v5.5.2/tools/cmake/project.cmake:589 `__project(${project_name} C CXX ASM)`).
  - The QSTR scan keeps only `.c` and C++ files, so a `.S` in `target_sources` is skipped there and does not break it (E: py/makeqstrdefs.py:34-38, 50-54).
  - The IDF compile options are applied to the usermod target (E: esp32_common.cmake:284-285).
  - The build uses MicroPython v1.29.0 with IDF 5.5.2 (E: build-engine-p593.log:1-2, 32, 51).
  - The MicroPython docs name an ASM list only for the Make build (`SRC_USERMOD_LIB_ASM`), and say nothing about CMake (search 1).
  - So: H, with strong code evidence. `engine/port/` does not exist yet (E: `ls engine` lists binding.c, core, micropython.cmake). · supports: Q5.

- **TL-6 · esp-dsp has no pixel kernel. Copying one or two `.S` files is lighter than adding the component.**
  - esp-dsp's PIE files (`*_aes3.S`) hold these kernels (E: `gh api repos/espressif/esp-dsp/git/trees/master?recursive=1`, 2026-11-03):
    - dot products, and 2D dot products in u8, s8, u16 and s16.
    - FIR, FFT sc16 and biquad.
    - s8 and s16 vector add, sub and mul, and matrix multiply.
    - memcpy and memset.
  - There is no blend, palette map, blur or stencil.
  - A ripple update built from the s16 vector adds needs 4 or 5 passes over the buffer. With the buffer in PSRAM, one fused C loop is better (H).
  - To add the component, change ports/esp32/main/idf_component.yml in the cloned MicroPython tree (E: that file lists mdns and tinyusb). build.sh clones a fresh v1.29.0 (E: build.sh:8-9), so build.sh then needs a patch step. The lockfile change gives a warning only, unless MICROPY_MAINTAINER_BUILD is set (E: ports/esp32/CMakeLists.txt:72-83).
  - Flash cost: unknown (H: only the functions used are linked). The app partition has 222,576 B left (E: bench.md:264), so a few KB is not a limit.
  - Copying one Apache-2.0 `.S` file with its header into engine/port/s3/ avoids the build change (E for the licence: p580-refuter.md:55-56). · supports: Q5.

- **TL-7 · Where PIE pays, at the sizes that fit.**
  - PIE pays on compute per pixel without a gather:
    - the fire and smoke diffusion kernel: 2.4 of the 7.3 ms of half-res fire.
    - the alpha or additive compose: 26 of the 29 ms of full-screen smoke.
    - the glow blur, the ripple's field update (0.3 ms) and the dissolve compare.
  - Gains nothing: particles, circle collisions, cellular sand and SPH (scalar, branchy, neighbour lists), the ripple render (a gather, E: p580-finding.md:35), and any write-bound part (55 ns/px into PSRAM is the floor for every full-screen effect: 4.25 ms).
  - Only smoke or alpha at full screen needs a faster compose to fit. The SWAR C blend of PHYS-6 is the rung before PIE.
  - With a cheap HUD, no effect needs PIE to be "tried alone" at the sizes in PHYS-5 (calculated). Then whether PIE is worth it is a PO choice, D2 of the restyle (E: p580-finding.md:3), not a feasibility need. · supports: Q5.

- **TL-8 · The C keeps state across a soft reset, and the effect state will too.**
  - The world is a static in binding.c (E: binding.c:11-12), and a soft reset left 192 bodies that broke the run at 160 (E: bench.md:276).
  - Effect state in static memory repeats this, and it keeps internal RAM for good (PHYS-8).
  - Smallest safe shape: `start` allocates the effect's scratch (`heap_caps_malloc`, internal first, else PSRAM) and returns its size and its memory kind. `stop` frees it. The scene calls `start` in `setup()`.
  - The core takes caller-owned buffers, so it stays Mac-testable (D15). · supports: Q3 and Q6.

- **TL-9 · The smallest shared scene: one generic Python scene and one table, not ten scene files.**
  - Today's pattern is one Game subclass with a C/Python BOOT swap and a HUD with step ms and fps (E: rain.py:93-164).
  - Proposed: `effects.py` with one `Effect(Game)` scene and a table of rows: name, engine kind, the feel numbers (D12: from Python), size. A BOOT tap goes to the next row, or swaps a variant such as C and PIE, or the size. The scene prints the rain's report line with the effect's step and draw ms for bench.md.
  - On the C side: one `engine.fx_start(kind, ...)`, `fx_step(steps)`, `fx_draw(tft)` and `fx_stop()` in binding.c over core/fx_<name>.c files. That keeps "one thin binding" (D17) and stops the binding growing by ten functions.
  - Ten separate entries in `GAMES` add ten presses to the one-way game cycle (E: app.py:40, engine brief F4).
  - "Each tried alone like the rain" is met either way. The single scene is smaller (H). · supports: Q6.

- **TL-10 · The plan fits the direction, with the pixel view as the seam.**
  - One engine module (D17). Effects later used in the games, through Q13's "draws, decides nothing the game reads" (E: brief.md:16). The public graphics library P539 #743 later.
  - These hold on one condition: every kernel writes a neutral pixel view, and only binding.c or port/s3/ knows s3lcd (TL-3, TL-8). That is p580-finding.md:79's "platform-neutral edge", moved from s3lcd to engine.
  - Tension: p580-finding.md:75 put `fx.c` beside `frame.c` inside s3lcd, while D17 (later, 2026-11-03) puts engine C in its own module. D17 is the newer decision, so P580's placement is stale (E: both pointers). · supports: Q6.

- **TL-11 · "Bodies on fire" is two effects composed, and it needs no new kernel.**
  - The circles' C step adds heat at each burning body's position into the fire field. The fire kernel carries it up, so flames trail the bodies.
  - Which body burns, and when, is a feel number or a rule from Python (D12). For an effect the game reads nothing back (Q13).
  - Cost: 9.9 ms (PHYS-5). It reuses TL-1 and the fire kernel, so the ten scenes share about four kernels: heat diffusion, particles, the circle grid, and a water field. · supports: Q1 and Q6.

- **TL-12 · The PIE register state across tasks: unknown.**
  - MicroPython's task, the LCD done-interrupt (E: frame.c:154) and FreeRTOS share the core. Not checked: does ESP-IDF 5.5.2 save the Q registers and ACCX on a task switch? Can an interrupt or a library such as memcpy use PIE without our knowledge?
  - It matters only for a `.S` kernel that runs while another task uses PIE. · supports: Q5's run rung.

## What I did not check, and why

- Whether a `.S` builds and runs in the engine module. That needs an IDF build and a flash. I read the cmake chain only (TL-5).
- The free internal RAM on the engine image. It needs the board, and P593 did not log it (PHYS-8).
- The cycles per pixel of the fire, palette, ripple, SWAR blend, collision and SPH kernels. All are H from instruction counts or P580. Only the compose costs and the C step are measured.
- The background fill and `show()` shares inside the 14 ms rest (PHYS-2). The `time` and `phases` lines of run55 were not parsed. I derived the rest from the `rain` lines only.
- esp-dsp's flash size in the linked image. That needs a build. Its README and the docs were not read (only the file list).
- The windows count of the rain's sends, so whether the rain already pays the full background send (PHYS-3).
- Box2D-Lite's and Chipmunk2D's sources (TL-2 is model knowledge, H).
- The PIE context switch in ESP-IDF 5.5.2 (TL-12). I left one search for it unspent to stay under budget.
- The sqrt cost: a preprint via a search summary, not read (search 3).

## Questions for the decider

- Q-TL1 · Before the effect scenes, does the HUD become one cached blit (about 0.4 ms instead of about 11 ms)? Example: full-resolution fire costs 16.4 ms. It does not fit in today's 15 ms room. It fits in 26 ms. · decides: the size of every effect, and a card "found on the way" for all ten games.
- Q-TL2 · Do effects reach the screen through the s3lcd frame (B: one write a pixel, D17's route) or through a buffer Python blits (A: double the traffic, s3lcd untouched)? · decides: binding.c's shape, and whether the scenes can run full screen.
- Q-TL3 · Is PIE in this card at all? The other option: plain C first, and PIE (after the SWAR C blend) as a later rung, only for an effect that misses its line. Example: only full-screen smoke needs a faster compose. Every other row fits in C. · decides: whether slice 0 holds a `.S` probe, and D2's place in this card.
- Q-TL4 · Colliding bodies: circles only as an effect, with the grid shared with P592 later, or boxes now? Example: 300 circles cost 2.6 ms, but they need 3 substeps at stack's g = 2,000. Boxes with tipping are P592's solver. · decides: the scope of the collision scene and its overlap with P592.
- Q-TL5 · One generic effects scene with a BOOT tap through a table, or one `GAMES` entry per effect? · decides: the shared scene, the Python file count and the length of the game cycle.
- Q-TL6 · esp-dsp as a managed component (a patch to MicroPython's tree, flash cost unknown), one copied `.S` file, or none? · decides: build.sh and the licence notice.

## Searches

- "MicroPython USER_C_MODULES esp32 assembly .S file target_sources user module" · served: Q5, whether a `.S` builds in the user module · used (TL-5: the docs name only `SRC_USERMOD_LIB_ASM` for Make, nothing for CMake). Results: [cmodules v1.29.0](https://docs.micropython.org/en/v1.29.0/develop/cmodules.html), [cmodules latest](https://docs.micropython.org/en/latest/develop/cmodules.html).
- "RGB565 alpha blend 0x07E0F81F single multiply 32-bit trick" · served: whether plain C can beat s3lcd's 337.5 ns/px blend before PIE · used (PHYS-6). Results: [VirtualDub entry 117](https://virtualdub.org/blog2/entry_117.html), [embedded-3dgfx blend.rs](https://docs.rs/crate/embedded-3dgfx/latest/source/src/pipeline/rasterize/draw/blend.rs).
- "ESP32-S3 float sqrtf cycles FPU division performance benchmark" · served: the cost of the collision and cloth constraints (Q4) · used, as H-grade (sqrt 91 cycles, divide 62, from an unreviewed preprint: [researchsquare rs-10413137](https://www.researchsquare.com/article/rs-10413137)). Also returned: [Espressif blog, cores with FPU](https://developer.espressif.com/blog/2025/10/cores_with_fpu/) (not read).
- Not a web search, listed for completeness: `gh api repos/espressif/esp-dsp/git/trees/master?recursive=1` and `gh api repos/espressif/esp-dsp/contents/idf_component.yml` · served: Q5, which PIE kernels esp-dsp offers · used (TL-6).
- The Espressif docs MCP was not used. 3 of 8 web searches were spent.
