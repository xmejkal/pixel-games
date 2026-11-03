# P586 engine patterns: how others build a C engine with a script API

Researcher: engine patterns (Opus). Read on 2026-11-03. Every web pointer was read on that date unless the line says
otherwise. Repository commits read: TinyCircuits-Tiny-Game-Engine 64b5f0d (2026-10-14), box2d dd8bd3f (2026-10-29),
Chipmunk2D f2f3d66 (2026-05-05), Physac 587b639 (2024-10-20). Host measurements ran on this Mac (arm64, 64-bit
pointers). Scratch copies sit in the session scratchpad, not in the repository.

Tags: E evidence with a pointer, H hypothesis with its source, D decision. The word "unknown" stands for the brief's unknown tag.

## Findings

### A. The one engine that already gives MicroPython a C core: Thumby Color's Tiny Game Engine (TGE)

- ENG-1 · TGE is licensed GPL-3.0. pixel-games is MIT. Code copied from TGE into pixel-games stays under GPL
  terms. So TGE is reusable as an API shape and a pattern only. · E (licence) H (what the licence means for reuse:
  general licence knowledge, not legal advice) · `gh api repos/TinyCircuits/TinyCircuits-Tiny-Game-Engine` →
  `"license":"GPL-3.0"`, pushed 2026-10-14 · supports: the reuse table row for TGE.
- ENG-2 · TGE is a MicroPython external C module with one folder per engine part. The folders are `nodes/` (2D and
  3D), `physics/`, `draw/` and `display/` (one driver file per port). Then `io/`, `audio/`, `animation/` and
  `resources/`. Then `link/` (two-device link), `save/`, `time/`, `math/`, `debug/` and `fault/`. Its README names RP2350, Unix and WebAssembly as
  targets. ESP32 is not named. · E · `gh api .../git/trees/HEAD?recursive=1` (src listing), README read via WebFetch ·
  supports: a module map for the engine. TGE does not run on an S3 as published.
- ENG-3 · TGE's loop lives in C. `engine_tick()` first runs the link task and the physics step. If the fps
  limit allows, it then reads input, steps animation and calls every node's `tick` callback layer by layer. Next it removes
  deleted nodes, draws every node and the GUI, and sends and clears the whole screen buffer. Last it calls
  `mp_handle_pending()`. Python calls `engine.start()`
  to loop, or `engine.tick()` by hand. · E · `src/engine.c:254-325`, `:341-362` · supports: a C-owned loop with
  Python hooks.
- ENG-4 · TGE's object model is a node tree with inheritance from C node types. A Python class subclasses a C node
  (for example `PhysicsRectangle2DNode`) and passes `self` as the first constructor argument. At construction, C looks
  up four methods once with `mp_load_method_maybe`: `physics_tick`, `tick`, `on_collide` and `on_separate`. It
  stores the bound methods in the C struct. Each frame C calls them with `mp_call_method_n_kw`. C also replaces the Python
  type's attribute slot. Reads and writes of `position`, `velocity` and the like then go straight to the C struct.
  Nodes have parents and children in linked lists and sit on numbered layers. · E ·
  `src/nodes/2D/physics_rectangle_2d_node.c:405-500`, `src/nodes/node_base.h:13-26`, `:73-95`,
  `src/engine_object_layers.c:88-110` · supports: one proven way for C to call back into Python without a lookup
  per frame.
- ENG-5 · TGE allocates on the MicroPython heap at every callback. Each `tick` call builds a new float for `dt`. Each
  collision builds five floats and one `CollisionContact2D` object per side that has `on_collide`. Node structs come
  from `m_malloc` and `mp_obj_malloc_with_finaliser`, so the collector scans them. · E ·
  `src/engine_object_layers.c:108`, `src/physics/engine_physics.c:332-356`,
  `src/nodes/2D/physics_rectangle_2d_node.c:425-431` · supports: the cost side of the callback pattern on a large
  PSRAM heap (see ENG-25).
- ENG-6 · TGE's physics does not turn bodies on contact. The collision response changes linear velocity and position
  only. The calls that add angular impulse at the contact point are commented out (lines 210-211 for the
  normal impulse, 316-317 for friction). The pair test is a plain all-against-all loop with no broad phase, and the
  body limit is 180 (`PHYSICS_ID_MAX`). Colliders are rotated rectangles and circles. The step is a fixed-step
  accumulator clamped at 30 ms. · E · `src/physics/engine_physics.c:210-211`, `:316-317`, `:362-380`, `:418-455`,
  `src/physics/engine_physics_ids.h:10` · supports: TGE physics cannot give RENT's "tip by centre of weight, topple"
  as published.
- ENG-7 · TGE draws in retained mode with no dirty regions. Each node draws itself each frame into a full 128 x 128
  RGB565 buffer of 32,768 bytes (calculated from `SCREEN_BUFFER_SIZE_BYTES`), and the engine swaps two buffers and
  sends the whole frame. · E · `src/display/engine_display_common.h:15-28`, `src/display/engine_display.c:70-89` ·
  supports: a comparison with pixel-games' partial show (`lcd.py` header, PARTIAL tiles).

### B. Small engines with a fixed callback set (the family pixel-games' Game base is already in)

- ENG-8 · Pimoroni PicoSystem (MIT) has a MicroPython binding over its C++ library. `start()` looks up the global
  functions `update` and `draw`, then loops in C: read buttons, call `update(tick)`, wait for the last flip, call
  `draw(tick)`, wait for vsync, flip, run `gc_collect()` every frame, then `mp_event_handle_nowait()`. Drawing is
  immediate (`pen`, `frect`, `text`) into one framebuffer. It targets the RP2040. · E ·
  `micropython/modules/picosystem/picosystem.cpp:86-168`, `libraries/picosystem.hpp:23-25`, `:103-117`, licence via
  `gh api repos/pimoroni/picosystem` → MIT · supports: MIT code for a C loop that calls Python update and draw.
- ENG-9 · 32blit SDK (MIT, C++) uses three function pointers: `init()`, `update(time)` and `render(time)`. `update`
  runs at a fixed 10 ms step, with catch-up while time is pending. `render` runs once per tick. Timers and tweens live
  in the engine. Ports in the tree: STM32, Pico, SDL. No ESP32 port. · E · `32blit/engine/engine.hpp`,
  `32blit/engine/engine.cpp:94`, `:103-146`, repository root listing · supports: fixed-step update with a separate
  draw.
- ENG-10 · 32blit separates firmware and game with a versioned table of function pointers (`APIConst`: `now`,
  `set_screen_mode_format` and others, with `api_version_major` and `minor`). Its multiplayer seam is two calls:
  `send_message(data, len)` and a `message_received(data, len)` callback. · E ·
  `32blit/engine/api_private.hpp:28`, `:71-132`, `32blit/engine/multiplayer.hpp` · supports: a function-table seam
  (D4) and a byte-message seam for later networking (D2).
- ENG-11 · Arduboy2 (BSD-3-Clause) has no callbacks. The sketch's `loop()` polls `nextFrame()` to gate the frame rate,
  uses `everyXFrames()` for timers and `collide(Rect, Rect)` for overlap, and draws into a 1-bit buffer
  `sBuffer[(HEIGHT*WIDTH)/8]`. AVR only. · E · `src/Arduboy2.h:836`, `:884`, `:940`, `:1129-1146`, `:1465`, licence
  file header "BSD 3-clause" · supports: the polling end of the event spectrum.
- ENG-12 · TIC-80 (MIT) gives a cartridge a fixed set of callbacks: `TIC` (every frame, 60 per second, required),
  `BOOT` (once), `BDR(n)` (before each scanline), `OVR` (last, on its own layer), `MENU`. API groups: drawing, input,
  sound, memory, utilities, system. · E · https://github.com/nesbox/TIC-80/wiki/API · supports: API shape. Runs on
  S3: unknown.
- ENG-13 · PICO-8 uses `_init`, `_update` (or `_update60`) and `_draw`. It is proprietary. · H (model knowledge, the
  manual was not read) · supports: API shape only.
- ENG-14 · LÖVE uses `love.load`, `love.update(dt)` and `love.draw`, and its `love.physics` wraps Box2D with
  `World:setCallbacks(beginContact, endContact, preSolve, postSolve)`. · H (model knowledge. love2d.org answered HTTP
  403 to the fetch) · supports: a precedent for physics callbacks in a script API.
- ENG-15 · Pygame Zero is LGPL-3.0. Its API shape is module-level `draw()` and `update(dt)` plus handlers found by
  name, such as `on_key_down`. · E (licence, `gh api repos/lordmauve/pgzero` → LGPL-3.0) H (API shape: model
  knowledge, docs not read) · supports: handler discovery by name, like TGE's method lookup in ENG-4.

### C. How events reach the script in larger engines

- ENG-16 · MakeCode Arcade (MIT) registers handlers by sprite kind pair: `sprites.onOverlap(kind, otherKind,
  handler)`. A sprite with the `ghost` flag set raises no overlap. Its physics engine is a swappable class,
  `PhysicsEngine`, with `ArcadePhysicsEngine` as the default. It uses Fx8 fixed point and a maximum time step of
  100 ms. · E · https://arcade.makecode.com/reference/sprites/on-overlap, `pxt-common-packages
  libs/game/physics.ts:1-114`, licence MIT via `gh api` · supports: dispatch by kind pair, and physics as a
  strategy. Runs on S3: unknown.
- ENG-17 · Defold queues messages from `msg.post()`. "Each frame, the engine runs through the queue and delivers each
  message to its target address." A delivery that adds messages starts another pass. A hard limit caps the passes. Physics
  collisions arrive as the system message `collision_response` in the script's `on_message()`. · E ·
  https://defold.com/manuals/message-passing/ · supports: a queue drained at one known point in the frame.
- ENG-18 · Godot signals: a node emits a signal, and other nodes connect a function to it. The docs call this
  delegation that lets "one game object … react to a change in another without them referencing one another". · E ·
  https://docs.godotengine.org/en/stable/getting_started/step_by_step/signals.html · supports: a pattern only. Godot
  is far too large for an S3 (H, model knowledge).
- ENG-19 · Box2D v3 does not call user code during the step for contacts. "Contact events are available after each
  world step." The game reads begin-touch, end-touch and hit events as arrays with `b2World_GetContactEvents`.
  It reads sensor events with `b2World_GetSensorEvents`. Body move events also say whether a body fell asleep. The docs
  say the contiguous data "is cache friendly". Bodies are handled by opaque ids, not pointers. · E ·
  https://box2d.org/documentation/md_simulation.html (first 100,000 of 166,148 characters read) · supports: a "poll
  after step" event path, where C fills an array and Python reads it once per frame.

### D. Small 2D rigid physics in C

- ENG-20 · The S3's FPU is single precision only. Double math runs in software. Espressif's measured cycles per
  operation on the S3: add 25 (float) against 70 (double), divide 69 against 75, cosine 121 against 1619, a mixed
  calculation 312 against 3886. · E (stated) · https://developer.espressif.com/blog/2025/10/cores_with_fpu/ ·
  supports: any physics library must be built for `float`.
- ENG-21 · Box2D v3 is MIT and written in C. Its `src/` holds 1,366,152 bytes of source text (measured, sum of `gh
  api` tree sizes) and 35,474 lines of `.c` (measured, `wc -l`). It uses `float` by default, with double only for
  large worlds (`BOX2D_DOUBLE_PRECISION`, off). SIMD paths are SSE2, AVX2 and NEON, with a scalar fallback
  (`B2_SIMD_NONE`) on other CPUs such as Xtensa. It takes a task system from the host through `workerCount` and an
  `enqueueTask` callback, up to 32 workers. · E · `CMakeLists.txt:64-66`, `src/core.h:52-70`,
  `include/box2d/types.h:24-169`, `include/box2d/constants.h:26` · supports: a full-featured MIT option. Flash size
  on Xtensa: unknown. Runs on an S3: unknown (search 1 found no ESP32 port or benchmark).
- ENG-22 · Box2D v3 struct sizes on the 64-bit host: `b2Body` 104 B, `b2BodySim` 96 B, `b2BodyState` 32 B, `b2Shape`
  280 B, `b2Contact` 64 B, `b2ContactSim` 200 B (measured, `cc` sizeof probe). One box body with one shape is about
  512 B, and each touching pair about 264 B (calculated from those). On the 32-bit S3 pointer fields shrink, so these
  are upper bounds. · E (host) H (S3 size: pointer width) · scratchpad `tools/sz_box2d.c` → `b2Body 104 b2BodySim 96
  b2BodyState 32 b2Shape 280 b2Contact 64 b2ContactSim 200` · supports: memory per body. A 20-body tower is about
  10 KB plus contacts (calculated).
- ENG-23 · Chipmunk2D is MIT. Its `src/` holds 10,656 lines of `.c` (measured). `cpFloat` defaults to `double` on any
  target that does not define `CP_USE_DOUBLES` (the 32-bit branch exists only under `__APPLE__`). An S3 build must
  set `CP_USE_DOUBLES=0`, or every step pays software double (ENG-20). Host sizes with doubles and 8-byte pointers:
  `cpBody` 272 B, `cpPolyShape` 600 B, `cpArbiter` 176 B, `cpSpace` 568 B (measured, upper bounds). · E ·
  `include/chipmunk/chipmunk_types.h:44-58`, scratchpad `tools/sz_chip.c` output · supports: a smaller MIT option
  with a known float trap.
- ENG-24 · Physac is MIT, one header of 2,134 lines. It caps bodies at 64, manifolds at 4,096, polygon vertices at 24,
  and runs 20 collision iterations. It starts its own pthread unless `PHYSAC_NO_THREADS` is set. Host sizes:
  `PhysicsBodyData` 512 B (fixed 24-vertex arrays), `PhysicsManifoldData` 72 B (measured). Last push 2024-10-20. · E ·
  `src/physac.h:23-27`, `:101-114`, scratchpad `tools/sz_physac.c` output, `gh api` pushed_at · supports: a tiny
  option that needs its thread removed and its arrays trimmed.
- ENG-25 · RENT's need (boxes land, tip by centre of weight, topple, slide) requires three things: angular response
  to contact impulses, friction, and a contact manifold of up to two points so a box rests flat on a box. TGE has none
  of the first (ENG-6). Box2D v3 and Chipmunk2D have all three. · H (rigid-body physics knowledge. ENG-6 is E) ·
  supports: the subset question. A hand-written subset in the "Box2D Lite" style (oriented boxes, separating-axis
  test, two-point manifold, sequential impulses) is the usual small path. · H (model knowledge of Erin Catto's
  Box2D-Lite, MIT, about a thousand lines, not read).

### E. Object model on a small chip, mapped onto pixel-games

- ENG-26 · What the read engines choose. TGE: node tree with inheritance from C node types (ENG-4). PicoSystem,
  32blit, TIC-80, Arduboy2: no object model, two or three global callbacks, and the game keeps its own state
  (ENG-8, ENG-9, ENG-11, ENG-12). MakeCode: sprites with kinds plus a handler registry (ENG-16). Defold: game objects
  with script components and messages (ENG-17). Godot: node tree plus signals (ENG-18). Box2D: data-oriented arrays
  addressed by ids (ENG-19). None of the small engines read uses an entity-component-system. · E (for the engines
  read) H (that this holds for small engines in general) · pointers as listed · supports: Q4's options.
- ENG-27 · pixel-games today sits in the callback family with a state machine in the base class. `Game` owns TITLE,
  PLAY and OVER, the timing (`dt` capped at 60 ms), particles and the score bar. A game writes `setup()`,
  `play(pressed, held)` and `paint(cv)`. `App.frame()` reads two buttons, steps the game, draws, and paces frames to
  40 ms. With PSRAM, the collector is off in the loop and a timed collection runs every 5 frames. Particles are Python
  lists stepped by a `@native` function. · E · `games/gfx.py:277-339`, `:225-258`, `games/app.py:26-29`, `:75-97`,
  `:164-175` · supports: the starting point of every option.
- ENG-28 · A Python-to-C call in pixel-games costs far more on the Python side than in C: about 98 µs per call all in,
  of which about 8 µs is C (measured). `TftCanvas.fill` allocates 32 bytes per call (measured). · E · `bench.md:155`,
  `:160` · supports: an API that hands C a batch (a node set, a particle pool, a body list) instead of one call per
  primitive. TGE's retained nodes (ENG-4, ENG-7) are one such batch.
- ENG-29 · Collector cost in pixel-games grows with what lives on the MicroPython heap: explicit collections over the
  8 MB PSRAM heap took 57 to 124 ms. With pictures on the heap, gc took 17.5 to 18.8 ms per frame at 1.37 MB. A frame
  buffer in the heap raised gc from 1.3 to 3.1 ms. All three are measured. · E · `bench.md:41`, `:171`, `:184` · supports:
  engine objects (bodies, contacts, particles) kept in C memory outside the MicroPython heap, or in fixed pools, keep
  the collector short. TGE (ENG-5) does the opposite. PicoSystem collects every frame (ENG-8), which suits the
  RP2040's small heap, not an 8 MB one (H, from the measured scaling above).
- ENG-30 · Fixed pools and up-front allocation are the common advice for MicroPython game loops: the collector does
  not compact, so a fragmented heap can fail a large allocation while enough total memory is free. · E (secondary) ·
  https://docs.openmv.io/openmvcam/tutorial/python/micropython/memory-and-gc.html, search 4 · supports: pools over
  per-frame objects.

### F. Per-chip fast paths and the second core (D4)

- ENG-31 · esp-dsp picks a per-chip variant at compile time. Each function exists as `_ansi`, `_ae32` (ESP32),
  `_aes3` (S3) and `_arp4` (P4). A platform header sets `..._enabled` flags from the Xtensa ISA macros
  (`XCHAL_HAVE_FP`, `XCHAL_HAVE_LOOPS`, `XCHAL_HAVE_MAC16`) and from `CONFIG_IDF_TARGET_*`. With `CONFIG_DSP_OPTIMIZED` set, the public name is a
  `#define` to the best variant. Without it, the name maps to `_ansi`. Licence Apache-2.0. · E ·
  `modules/dotprod/include/dsps_dotprod_platform.h:1-40`, `modules/dotprod/include/dsps_dotprod.h:120-155`, README
  via WebFetch · supports: the compile-time port pattern, with a plain C reference beside each fast version.
- ENG-32 · Espressif already wrote S3 SIMD assembly for RGB565 fills and blends, for LVGL: files such as
  `lv_color_blend_to_rgb565_esp32s3.S` and `lv_rgb565_blend_normal_to_rgb565_esp32s3.S`. CMake globs `*_esp32s3.S` or
  `*_esp32.S` by `IDF_TARGET`. A header maps LVGL's hook macros (`LV_DRAW_SW_COLOR_BLEND_TO_RGB565`) to the assembly.
  LVGL's default for each hook returns `LV_RESULT_INVALID`. With no hook set, the C path runs. The CMake gate
  limits this to LVGL 9.1.x. Files carry SPDX Apache-2.0. · E · esp-bsp
  `components/esp_lvgl_port/CMakeLists.txt:110-133`, `include/esp_lvgl_port_lv_blend.h:17-47`,
  `src/lvgl9/simd/lv_color_blend_to_rgb565_esp32s3.S:2-4`, lvgl `src/draw/sw/blend/lv_draw_sw_blend_to_rgb565.c:81-89`
  · supports: a ready S3 fill and blend for RGB565 with a hook-and-fallback shape. Whether it beats s3lcd's own
  fill: unknown.
- ENG-33 · LVGL also dispatches at run time. Each draw task is offered to every draw unit's `evaluate_cb`, which
  compares its speed with the best score so far. A faster unit writes its own preference score. The best unit's `dispatch_cb` then runs the task. Units in the tree
  include `sw`, `espressif/ppa` (the P4's pixel processing accelerator), `nxp`, `vg_lite`, `sdl` and others. The
  software unit can run `LV_DRAW_SW_DRAW_UNIT_CNT` threads. Licence MIT. · E · lvgl
  `docs/src/main-modules/draw/draw_pipeline.mdx:15-30`, `:120-152`, `src/draw/sw/lv_draw_sw.c:29`, `:105-118`, tree
  listing of `src/draw/` · supports: a run-time function-table pattern that fits a P4 with a pixel accelerator later.
- ENG-34 · Other engines pick their port at compile time by file: TGE has one display, input and fault file per port
  (`engine_display_driver_rp2_gc9107.c` beside `engine_display_driver_unix_sdl.c`, `engine_io_rp3.c` beside
  `engine_io_sdl.c`). 32blit uses a versioned run-time function table between firmware and game (ENG-10). · E · TGE
  src listing, `32blit/engine/api_private.hpp:71-132` · supports: the three choices (compile-time file per port,
  compile-time `#define` per function, run-time table).
- ENG-35 · MicroPython on a dual-core ESP32 pins its task to core 1, or core 0 on a single-core build. · E ·
  micropython `ports/esp32/mphalport.h:50-55`, `ports/esp32/main.c:291` · supports: core 0 is the free core for an engine
  task. What else runs on core 0 in pixel-games' image (Wi-Fi is off): unknown.
- ENG-36 · retro-go (GPL-2.0) runs its display on its own task, pinned to core 1 at priority 6. The emulator posts a
  frame pointer to that task's queue and carries on. `rg_display_sync()` waits until the queue is empty. · E ·
  ducalex/retro-go `components/retro-go/rg_display.c:495-516`, `:649`, `components/retro-go/rg_system.c:566-590` ·
  supports: a pattern only (GPL). The shape is a producer posts a finished frame, a consumer on the other core sends
  it.
- ENG-37 · s3lcd starts no task of its own and calls Python only for file reads, writes, seeks and closes. Its
  "double" framebuffer already lets `show()` return once the DMA send starts (about 3.4 ms copy for a full frame,
  stated in `lcd.py`). So the second core is unused today. · E · `grep xTaskCreate|PinnedToCore|mp_call_function
  s3lcd/src/*.c` → only `mpfile.c:65-99`, `games/lcd.py:10-11` · supports: the second core is free capacity. Box2D v3's
  `enqueueTask` hook (ENG-21) is one way to use it for physics. · H (that it pays off at this body count: not tried).

### Reuse table

| Project | What it is | Licence | Runs on S3 | Reuse as |
|---|---|---|---|---|
| Thumby Color TGE | MicroPython engine, C nodes, physics, audio, link | GPL-3.0 (E) | no as published, RP2350 and Unix (E) | API shape and pattern: C nodes subclassed in Python, method lookup once, attribute slot override (ENG-4) |
| PicoSystem MicroPython | C loop calling Python `update` and `draw` | MIT (E) | no, RP2040 (E) | code for the loop shape (ENG-8), and API shape |
| 32blit SDK | C++ handheld SDK | MIT (E) | no port (E) | API shape (init, update at 10 ms, render), function table, multiplayer seam (ENG-9, ENG-10) |
| Arduboy2 | AVR game library | BSD-3-Clause (E) | no (E) | pattern: polling and frame gate (ENG-11) |
| MakeCode Arcade | TypeScript game engine and editor | MIT (E) | unknown | API shape: overlap by kind pair. Pattern: swappable physics class (ENG-16) |
| TIC-80 | fantasy console | MIT (E) | unknown | API shape: TIC, BOOT, OVR (ENG-12) |
| PICO-8 | fantasy console | proprietary (H) | no (H) | API shape only (ENG-13) |
| LÖVE | Lua 2D framework | zlib (H) | no (H) | API shape: load, update, draw, physics callbacks (ENG-14) |
| Pygame Zero | Python on pygame | LGPL-3.0 (E) | no (H) | API shape: handlers found by name (ENG-15) |
| Godot | full engine | MIT (H) | no (H) | pattern: signals (ENG-18) |
| Defold | full engine | unknown | no (H) | pattern: message queue drained once a frame (ENG-17) |
| Box2D v3 | 2D rigid physics in C | MIT (E) | unknown (scalar SIMD path exists, E) | code, whole or trimmed (ENG-21, ENG-22) |
| Chipmunk2D | 2D rigid physics in C | MIT (E) | unknown | code, with `CP_USE_DOUBLES=0` (ENG-23) |
| Physac | one-header 2D physics | MIT (E) | unknown | code, thread removed and arrays trimmed (ENG-24) |
| esp-dsp | per-chip DSP kernels | Apache-2.0 (E) | yes, `_aes3` (E) | pattern: suffix variants and `#define` pick (ENG-31) |
| esp_lvgl_port SIMD | S3 RGB565 fill and blend assembly | Apache-2.0 per file (E) | yes (E) | code for fills and blends, hook with C fallback (ENG-32) |
| LVGL draw units | run-time draw dispatch | MIT (E) | yes (H, LVGL ships on S3) | pattern: evaluate and dispatch (ENG-33) |
| retro-go | ESP32 emulator launcher | GPL-2.0 (E) | yes (H) | pattern: display task on the other core, frame by queue (ENG-36) |

## What I could not check, and why

- Whether Box2D v3, Chipmunk2D or Physac builds for the S3 in pixel-games' MicroPython image, its flash size and its
  step time for a 20-box tower at 25 fps. No toolchain run was in scope, and search 1 found no ESP32 port or benchmark.
- Struct sizes on 32-bit Xtensa. The probes ran on a 64-bit host, so they are upper bounds.
- The cost of `mp_call_method_n_kw` from C into a Python method on the S3, and the cost of one boxed float. No board
  run was in scope. The events researcher covers the event path.
- LÖVE's `World:setCallbacks` page (HTTP 403), the PICO-8 manual and Pygame Zero's docs. Their lines stay H.
- Whether MakeCode Arcade or TIC-80 run on an ESP32-S3. Not searched, because no decision rests on it.
- Defold's licence and core language. The page read did not say.
- Whether the esp_lvgl_port S3 assembly is faster than s3lcd's `fill_rect` on this board, and whether it works
  outside LVGL 9.1.x.
- Which ESP-IDF system tasks occupy core 0 in pixel-games' image.
- Box2D's simulation page beyond its first 100,000 characters.

## Questions for the decider

- Q-ENG-1 · Do the games subclass engine objects (TGE's way: a Python `Box(Body)` with `on_collide`), or do
  they keep the Game base and read events the engine collects (Box2D v3's way)? · decides: the object model and the
  event path from C to Python.
- Q-ENG-2 · Do engine objects live in C memory outside the MicroPython heap, at the price of explicit lifetimes
  (create and destroy calls)? · decides: collector cost against a simpler Python API (ENG-5, ENG-29).
- Q-ENG-3 · For RENT's physics: take Box2D v3 or Chipmunk2D whole, trim one, or write a Box2D-Lite-sized subset? ·
  decides: flash, memory per body, and the work before RENT runs on the engine.
- Q-ENG-4 · Is a GPL-3.0 dependency acceptable anywhere (TGE code), or does every engine file stay MIT-compatible? ·
  decides: whether TGE is code or only a pattern.
- Q-ENG-5 · For per-chip speed: one `#define` per function picked at build time (esp-dsp), or a run-time table of
  draw units (LVGL)? · decides: how the S3 path and a later P4 path plug in (D4).
- Q-ENG-6 · Does the second core run the physics step or the frame send, with Python on core 1? · decides: the
  threading model and what a frame waits for.

## Searches

| # | Query, verbatim | Decision it served | Used |
|---|---|---|---|
| 1 | Box2D ESP32 port performance bodies fps | Q-ENG-3: does Box2D fit an S3 | not used: no ESP32 result |
| 2 | MicroPython game engine C module ESP32-S3 sprites physics | the reuse map: an existing MicroPython C engine on the S3 | not used: only Stage, a Python sprite library, no C engine or physics |
| 3 | Chipmunk2D ESP32 microcontroller float | Q-ENG-3: Chipmunk's float cost on the S3 | used: led to the Espressif FPU blog (ENG-20) |
| 4 | MicroPython game loop avoid allocation garbage collector object pool entity component system microcontroller | Q-ENG-2: object model and the collector | used: ENG-30 |
| 5 | esp_lvgl_port SIMD ESP32-S3 assembly blend LV_DRAW_SW_ASM_CUSTOM | Q-ENG-5 (D4): an existing S3 fast path | used as a lead: the files were then read in esp-bsp (ENG-32) |
| 6 | ESP32 emulator game display task pinned other core xTaskCreatePinnedToCore render while emulating retro-go | Q-ENG-6 (D4): how engines split work across two cores | not used: generic results. retro-go was read from its repository instead (ENG-36) |

Six searches of the 17 allowed (14 plus 3 for D4). Repository pages, files and docs fetched directly are not counted.
