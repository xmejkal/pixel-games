# P586 council: Python and C events, binding patterns, the later networking seam

Researcher: Python and C events, with the networking seam (Opus). Read 2026-11-03. Read only. This file is the one write.
Local primary source: MicroPython v1.29.0 at `~/esp/micropython-v1.29.0` (the tree `build.sh` builds), and its built
sdkconfig at `ports/esp32/build-s3lcd/sdkconfig`. Pixel-games paths are relative to the repository root.
"p582-heavy:" means `git show origin/p582-heavy:<path>`.

## Findings

### The event mechanisms at a glance

Costs are per event unless the row says otherwise. "Py call" is one call into a Python function with a small body. The
repo measured a Python-to-C call with no work at 5.5 µs and a small Python wrapper at 40 to 87 µs (bench.md:156, :161,
measured). No source gives the time of one C-to-Python call on an ESP32-class chip, so the C-to-Python figures are
calculated from those measurements (H).

| Mechanism | Allocation per event | Cost | Safety | Fits a 40 ms frame |
|---|---|---|---|---|
| A. C ring buffer, Python drains into a preallocated `array('i')` (C writes ints, returns a count) | 0 B (calculated: small ints are not boxed in REPR_A, `py/mpconfig.h:129`) | one Python-to-C call per frame (about 5.5 µs, measured) plus the Python loop over n events | C never touches a Python object, so the C side can run in a task or an ISR. An exception in game code is raised in game code, after the C step ended cleanly | yes (calculated: 20 events at about 50 µs of Python each are about 1 ms) |
| B. C ring buffer, Python drains one tuple per event | 32 B per 4-int tuple (calculated: 24 B rounded up to two 16 B blocks. The repo's 4-tuple measured 32 B, bench.md:155) | as A, plus one tuple allocation | as A | yes, but garbage grows with gc off in play (app.py:159) |
| C. Direct callback from inside the C update (`mp_call_function_n_kw` or `mp_call_method_n_kw`) | 0 B for small-int args. 16 B per float arg. A callback with more than 44 B of locals and stack gets its frame on the heap (`py/objfun.c:201`, `:273-286`). The frame is freed at once (`:342-345`) | calculated about 20 to 60 µs per event (H, from the repo's Python call costs) | runs on the MicroPython thread inside the C call. If the C code does not wrap the call in `nlr_push`, an uncaught exception jumps out of the C update. The update is then left half done (H, from the `py/runtime_utils.c` protected-call pattern). The callback can call back into the engine while C is mid-loop (re-entry) | yes for a few events. A storm (every resting contact, every step) does not |
| D. `mp_sched_schedule` from C (the `micropython.schedule` path) | 0 B in the queue (fixed 8 slots, `ports/esp32/mpconfigport.h:73`). Args must be existing objects | one Py call. Runs only between bytecodes or in `sleep_ms`, never inside native code or a C call (`docs/library/micropython.rst:205-217`) | ISR-safe to enqueue (atomic section, `py/scheduler.c:163-181`). Queue full returns false and the event is lost (`:176`). An exception prints and is swallowed (`mp_call_function_1_protected`, `py/runtime_utils.c`). Runs at most one Python callback per pending check (`py/scheduler.c:108-117`) | yes as a wake-up. No as the event channel: 8 slots, one callback per check, order relative to the frame not fixed |
| E. Python subclass of a C type, C calls the override | as C, plus one bound-method object cached per entity at creation | as C | the C object is a separate allocation that does not know its Python wrapper (`py/objtype.c:93`, `:373`), so C needs a stored back-reference. Thumby Color stores it and calls without `nlr_push` (below) | yes for a few events |
| F. Shared buffer, no queue (C writes per-body flags, Python reads after step: today's `Bodies.hit`) | 0 B for int flags. 16 B for each float read (calculated) | one Python read per body per frame | as A | yes. It is what p582-heavy does now |

### Events and binding (EVT)

- **EVT-1** · The repo already uses mechanism F in Python. `Bodies.step()` clears `hit[i]` and writes the impact speed of
  a bounce. A body at rest fires nothing. The game reads `hit[]` right after `step()` and calls named hooks:
  `landing`, `slab_hit`, `collapse_start`, `collapse_hit` · E · p582-heavy:games/motion.py:36-63, :66-69,
  p582-heavy:games/arcade2.py:234-236, :282-283, :327-331, :289 ("The four moments P583 hangs its effects on") · supports:
  the event contract (once per event, none at rest, read after step) exists and can move to C unchanged.
- **EVT-2** · Today's Python physics costs real frame time. The slowest frames of run 51 took up to 60 ms, 15 ms of it
  the physics step. `Bodies.step` allocates 544 B per call and `Spring.step` 112 B, because each written float is boxed
  · E · p582-heavy:bench.md:232, :235 (measured) · supports: moving bodies to C removes both costs. It says nothing on
  the event path.
- **EVT-3** · Floats are boxed in this build. `MICROPY_OBJ_REPR_A` and single-precision floats. A float object is a base
  word plus the value, one 16 B GC block · E · `ports/esp32/mpconfigport.h:18`, `:69`, `py/objfloat.c:55-58`,
  `py/mpconfig.h:251` · supports: any event or attribute that hands a float to Python allocates 16 B. Ints in the
  31-bit small-int range allocate nothing (`py/mpconfig.h:129`).
- **EVT-4** · `micropython.schedule` cannot deliver an event during a C update. Scheduled functions run between
  opcodes, not inside native code, and the scheduler is not run during `@native` code · E ·
  `docs/library/micropython.rst:204-217`, `docs/reference/speed_python.rst` "The Native code emitter" · supports: a
  scheduled callback arrives after `engine.update()` returns. The repo saw this with the button IRQ ("a soft interrupt,
  run after the current C call", games/buttons.py:39).
- **EVT-5** · The scheduler queue holds 8 Python callbacks on this port, and a full queue drops the new one. Each pending
  check runs at most one Python callback. An exception in it is printed and swallowed · E ·
  `ports/esp32/mpconfigport.h:73`, `py/scheduler.c:108-117`, `:163-181`, `py/runtime_utils.c`
  (`mp_call_function_1_protected`) · supports: schedule fits a wake-up, not a burst of game events.
- **EVT-6** · C code can also schedule a static node (`mp_sched_schedule_node`): a C callback with no allocation, run on
  the MicroPython thread, all pending nodes per check. It is on in this port · E · `py/scheduler.c:184-207`, `:88-104`,
  `ports/esp32/mpconfigport.h:74` · supports: a C task on core 0 can hand work to the MicroPython thread without
  touching Python objects.
- **EVT-7** · Calling Python from a FreeRTOS task that MicroPython did not create is unsafe. The VM finds its thread state
  through the task's thread-local slot, so a foreign task has none. MicroPython runs pinned to core 1, Wi-Fi on core 0
  · E · `ports/esp32/mpthreadport.c:97-103`, `ports/esp32/mphalport.h:51-55`, built sdkconfig
  `CONFIG_ESP_WIFI_TASK_PINNED_TO_CORE_0=y`, `# CONFIG_FREERTOS_UNICORE is not set` · supports: if physics ever runs
  in its own task or core, it can safely write only a C ring buffer (mechanism A). The ISR rule is the same:
  no heap allocation in a hard ISR (`docs/reference/isr_rules.rst:103-109`).
- **EVT-8** · The ESP32 port runs every `Pin.irq` handler through `mp_sched_schedule` from the ISR. It keeps the handler
  alive as a root pointer · E · `ports/esp32/machine_pin.c:91-95` · supports: the port's own pattern for "C event,
  Python reacts" is enqueue in C, run later on the Python thread.
- **EVT-9** · The repo's driver already shows the safe ISR-to-task path in C. The bus interrupt only counts down and
  gives a semaphore. It touches no Python object · E · s3lcd/src/frame.c:153-160 · supports: a C engine event raised
  in an ISR or a DMA callback follows the same rule.
- **EVT-10** · The repo's driver already calls Python from C synchronously: `mpfile.c` calls a Python file's
  `readinto`, `write`, `seek` with `mp_call_function_1/2` for jpg and png · E · s3lcd/src/mpfile.c:65, :75, :83 ·
  supports: mechanism C has a precedent in this C module. It was never measured here.
- **EVT-11** · Thumby Color's engine (TinyCircuits, GPL-3.0) calls Python directly from its C physics step. On each
  contact it boxes five floats (`mp_obj_new_float`), builds a contact object, and calls `on_collide` for each side with
  `mp_call_method_n_kw`. No `nlr_push` guards the call in `engine_physics.c`. It also calls `physics_tick` and
  `on_separate` the same way · E · github.com/TinyCircuits/TinyCircuits-Tiny-Game-Engine `src/physics/engine_physics.c`
  :82, :332-357, :402-406, commit 64b5f0dc (2026-10-14), read 2026-11-03 · supports: mechanism C costs at least six
  allocations per contact per side. An exception in `on_collide` unwinds out of the physics loop. Licence: GPL-3.0, so
  pixel-games (MIT) can take the pattern, not the code.
- **EVT-12** · Thumby Color lets a game subclass a C node in Python. The subclass passes `self` as the first argument
  (`super().__init__(self, ...)`). At creation C looks up `tick`, `physics_tick`, `on_collide`, `on_separate` on the
  instance with `mp_load_method_maybe` and caches the bound methods in the node. It also swaps the attr slot of the
  subclass type at run time · E · same repo `src/nodes/2D/physics_rectangle_2d_node.c`:405-421, :435, :473-505,
  `src/nodes/node_base.c`:426-438 · supports: subclass-and-override works for C callbacks, at the cost of an unusual
  constructor and a patched type.
- **EVT-13** · Thumby Color steps physics on a fixed timestep with an accumulator and a clamp, separate from the render
  tick · E · same repo `src/physics/engine_physics.c`:421-446, `src/engine.c`:263-274 · supports: a small MicroPython
  engine already separates a fixed-step simulation from the frame (also the networking seam, NET-9).
- **EVT-14** · LVGL's MicroPython binding calls a Python callback synchronously from C. The generated C stub builds the
  args, looks the callable up in a dict kept in the C struct's `user_data`, and calls `mp_call_function_n_kw`. No
  `nlr_push` in the stub. LVGL and MicroPython must share one thread, and LVGL's own periodic work is driven through
  `mp_sched_schedule` · E · github.com/lvgl/lv_binding_micropython `gen/gen_mpy.py`:2926-2935, :1756-1795, README
  "Concurrency" and "Callbacks", commit 032dda4b (2026-09-06), read 2026-11-03 · supports: the two large bindings both
  pick mechanism C on one thread. Neither guards the callback against an exception.
- **EVT-15** · A Python subclass of a C type holds the C object as a separate object in `subobj[0]`. The C object is made
  by the native `make_new` with the native type, so it has no pointer to its Python wrapper · E · `py/objtype.c:89-96`,
  `:372-373` · supports: for C to call an override, the C struct needs a stored back-reference (as Thumby does) or the
  event carries an id that Python maps to its object.
- **EVT-16** · A C struct outside the GC heap (PSRAM by `heap_caps_malloc`, the `s3lcd.pool` block) is not scanned. A
  Python object referenced only from there can be collected. The repo keeps the frame there on purpose for this reason
  · E · s3lcd/src/frame.c:27 ("outside MicroPython's heap: gc never scans it"), s3lcd/src/s3lcd.c:2925-2952 · supports:
  an entity pool in PSRAM must not hold `mp_obj_t` callbacks. Callbacks belong in a GC-heap object or a root pointer
  (`MP_REGISTER_ROOT_POINTER`, as `py/scheduler.c:210` and `machine_pin.c:93` do). An id-based event (mechanism A)
  needs neither.
- **EVT-17** · Python-to-C calls are cheap. The C part is small. An empty call stayed at 5.5 µs. A raw `fill_rect` 8 x 8
  costs 5.61 µs. "Per call, all in: 98 µs, of which about 8 µs is C." A loop iteration alone is 2.10 µs · E ·
  bench.md:154, :156, :160 (measured) · supports: a binding with few, coarse calls (one `update()`, one `drain()` per
  frame) costs microseconds. A binding that crosses per entity per frame costs what the Python side costs.
- **EVT-18** · The current boundary is one user C module with one Python type. `ESPLCD`'s locals table maps methods to
  C wrappers. Constants are `MP_ROM_INT` in the module table. The type has `print`, `make_new` and `locals_dict` only:
  no buffer protocol, no `attr` slot, no subclass flags · E · s3lcd/src/s3lcd.c:2735-2777, :2782-2788, :2956-2978 ·
  supports: today Python cannot get a buffer view of the frame from the type itself, and a Python subclass of
  `ESPLCD` has never been tried.
- **EVT-19** · `frame.c` is a C part with its own state struct (`frame_t` inside the `ESPLCD` object) and thin method
  rows in `s3lcd.c` (`show`, `config`, `track`). `config(**kw)` checks every key and value, then applies all or none,
  names the bad key, and returns a dict. `show()` returns a small int · E · s3lcd/src/frame.c:461-592,
  s3lcd/src/s3lcd.c:2648-2651, :2715-2733 · supports: the house pattern for a readable binding already exists. Caveat:
  `frame.c` includes `py/runtime.h` and raises MicroPython errors, so the part is not plain C, and `config()` allocates
  a dict per call (fine at setup, not per frame).
- **EVT-20** · The place for an event queue today: the game's `step()`, right after the C step call, before draw.
  `App.frame` reads the buttons, calls `game.step(now, pressed, held)`, then `out.draw` and `show()`. The game already
  reads `hit[]` at that point · E · games/app.py:78-91, p582-heavy:games/arcade2.py:222-236 · supports: a C `update()`
  that fills a queue, followed by a drain in the same `step()`, changes no loop order.
- **EVT-21** · Dynamic native modules (`.mpy` natmod) build for `xtensawin` (ESP32-S3). They link only against
  `mp_fun_table`, not the firmware's symbols, so a natmod cannot call s3lcd's C functions or ESP-IDF directly. No
  initialised data and no static BSS. libm and libgcc only with `LINK_RUNTIME = 1` · E · `docs/develop/natmod.rst:27-110`
  · supports: to land a new effect or body type without a firmware rebuild, the part must work on buffers passed in from
  Python (buffer protocol) and returns ints. It cannot reach into the engine's C structs.
- **EVT-22** · Native code (natmod, `@native`, `@viper`) is placed in executable internal RAM (`MALLOC_CAP_EXEC`) and
  freed at soft reset · E · `ports/esp32/main.c:301-312`, `:293-299` · supports: natmods and viper compete for
  internal RAM with the "double" frame's `outgoing` buffer (NET-7). How much exec RAM is free in play: —.
- **EVT-23** · `@native` is "roughly twice as fast as bytecode" and still boxes floats. `@viper` uses machine ints and
  raw pointers (`ptr8/16/32`) over buffers. "Floating point may be used but is not optimised." Neither runs the
  scheduler while it runs · E · `docs/reference/speed_python.rst` sections "The Native code emitter" and "The Viper code
  emitter" · supports: viper over an `array('i')` in fixed point is a no-rebuild middle step for a new effect.
  `fall_bodies` is `@native` today and still allocates 544 B per step (EVT-2).
- **EVT-24** · An id-based event record keeps C free of Python objects. C emits (kind, id, a, b) as ints. Python maps id
  to its own object (a list index), and kind is a module constant (`MP_ROM_INT`, as `s3lcd.WRAP` is) · H (design
  reasoning from EVT-3, EVT-7, EVT-15, EVT-16, EVT-18) · supports: mechanism A with no back-references and no magic
  strings. It costs Python one lookup per event.
- **EVT-25** · Extending a C entity from Python, three shapes. Subclass with overrides (Thumby, EVT-12). Callback slots
  set as attributes (`body.on_land = fn`, LVGL-style, EVT-14). Component: a plain Python object that holds a C handle
  (an int) and reacts to drained events (EVT-24). Only the component shape needs no C change to add a new behaviour
  · H (comparison from EVT-12, EVT-14, EVT-24) · supports: the decider's "nicely extendable" wish. A new reaction to
  an existing event needs no rebuild in any shape. A new body type or effect computed in C needs a rebuild unless
  written as viper or a natmod over a buffer (EVT-21, EVT-23).
- **EVT-26** · A user C module joins the firmware through one cmake source list. Each new `.c` part is one line in
  `micropython.cmake` and a full firmware build · E · s3lcd/src/micropython.cmake:5-19, build.sh:13-17 · supports:
  the cost of "a new C part" is a rebuild and reflash, not a binding framework.

### Networking (NET)

- **NET-1** · MicroPython's `espnow` module is on in this port. Packets are up to 250 B (v1) or 1470 B (v2, since
  ESP-IDF 5.4). Up to 20 peers. A WLAN interface must be active, not connected · E · `ports/esp32/mpconfigport.h:93-94`,
  `docs/library/espnow.rst:30-67`, :211-213 · supports: an input packet for these games (a frame number and a button
  byte) is a few bytes, far under either limit. Whether this build reports 1470: — (not run on the board).
- **NET-2** · `ESPNow.irecv()` reuses its buffers. `recv()` allocates per message. `irq(callback)` goes through the
  scheduler and "can overflow and callbacks will be missed" at high rates · E · `docs/library/espnow.rst:308-334`,
  :566-592 · supports: a per-frame `irecv(0)` poll in the game loop fits the gc-off loop. The irq path has EVT-5's
  limits.
- **NET-3** · Espressif's own ESP-NOW test (ESP32 and ESP32-C3, ESP-IDF v4.4.1, office, 0.5 m, oscilloscope, 10
  packets): one-way 10 B avg 2.43 ms, max 3.06 ms. 230 B avg 5.37 ms, max 15.66 ms. Round trip, unicast, 3 m, 10,000
  packets: 10 B avg 4.56 ms, max 75 ms, loss 0.11 %. 230 B avg 11.45 ms, max 94 ms · E (measured by Espressif, not on
  an S3, not in MicroPython) · github.com/espressif/esp-now/files/14846115/ESP-NOW.Test.Report.pdf, sha256
  0ad90d0c8acc36b009da3f509069dd1b48d9a307247ab4a7f73a2e6c25a0f3ac, read 2026-11-03, tables "单程延时" and "往返延时"
  · supports: average latency is a small part of a 40 ms frame. The worst case (75 to 94 ms) is two frames.
- **NET-4** · Electric UI's benchmark (ESP32 boards, one-way, input pin to output pin): ESP-NOW 12 B 5.6 ms, 128 B 5.8
  ms, 1 kB about 24 ms. ESP32 Wi-Fi UDP and TCP with default ESP-IDF config: medians 74 to 84 ms. Tuned (power save
  off, IRAM, Nagle off): TCP medians about 6 ms, UDP about 9 ms, outliers to 25 ms · E (field, third party, statistic
  not named) · electricui.com/blog/latency-comparison, read 2026-11-03 (about February 2024, per
  hackaday.com/2024/02/11) · supports: plain UDP through an access point needs power save off to be playable.
- **NET-5** · Wi-Fi power save turns the radio off "typically for hundreds of milliseconds" and is switched on when the
  station connects to an access point. The fix is `sta.config(pm=sta.PM_NONE)` or an active AP interface · E ·
  `docs/library/espnow.rst:825-846`, `docs/library/network.WLAN.rst:256-266` · supports: any transport seam must set
  `pm` explicitly. It is not a per-frame cost.
- **NET-6** · This firmware's Wi-Fi uses 10 static RX buffers (about 1.6 KB each, DMA internal RAM, allocated at
  `esp_wifi_init`) and 32 dynamic TX buffers. It does not let Wi-Fi or lwIP allocate in PSRAM · E · built sdkconfig
  lines 1561-1562, 1714-1719, docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/wifi-driver/overview.html
  "Wi-Fi Buffer Configure", read 2026-11-03 · supports: about 16 KB of internal DMA RAM at radio start, plus dynamic
  buffers in play (calculated).
- **NET-7** · With `framebuffer="double"` the largest free internal block is 31,744 B while the game runs (188,416 B
  before init). The `outgoing` buffer takes 153,600 B of internal DMA RAM · E · bench.md:186 (measured),
  s3lcd/src/frame.c:111 · supports: the radio and the frame compete for internal RAM. Whether Wi-Fi starts beside
  "double", and what it does to the frame: — (not measured).
- **NET-8** · Today's games are not deterministic across two boards. `dt` is the wall-clock gap between frames,
  clamped to 60 ms. Effects call `random.random()` unseeded. A slow frame restarts the pace from now · E ·
  games/gfx.py:326, games/gfx.py:244-245, games/app.py:165-171 · supports: lockstep or rollback needs a fixed
  step and an engine-owned seeded random, at least for anything that changes game state.
- **NET-9** · The input already reaches a game as a per-frame record. `App.frame` hands `game.step` the time, `pressed`
  and `held`. Only `now` makes it wall-clock dependent · E · games/app.py:78-84 · supports: the seam is small. Replace
  `now` with a frame number and a fixed `dt`, and make (frame, buttons) the only input to the simulation. Then a local
  button, a recorded replay, or a remote packet can feed the same `step()` (H, design reasoning).
- **NET-10** · GGPO's rollback asks the game for three things: a fully deterministic simulation, save and load of the
  whole state, and an advance-one-frame call that takes all players' inputs for that frame. GGPO itself owns input
  delay and prediction. Re-simulated frames are not drawn · E · github.com/pond3r/ggpo/blob/master/doc/README.md, read
  2026-11-03 · supports: lockstep needs determinism and per-frame inputs. Rollback adds snapshot and restore. A flat C
  pool (arrays of numbers, no pointers to Python) makes a snapshot one `memcpy` (H).
- **NET-11** · Thumby Color ships networking as a separate byte-transport module (`engine_link`: `start`, `send`,
  `read_into`, `available`, a 511 B ring buffer, connect and disconnect callbacks). The engine has no sync model. The
  game writes its own protocol · E · github.com/TinyCircuits/TinyCircuits-Tiny-Game-Engine `src/link/engine_link_module.c`
  :68-406, commit 64b5f0dc, read 2026-11-03 · supports: the PO's "first as a separate MVP" matches what one small engine
  did. Its transport is a USB cable, not radio.
- **NET-12** · Floats on two identical boards running the same image: the same IEEE single-precision instructions on the
  same inputs give the same bits. The risks are elsewhere: two different builds (a compiler can fuse `a*b+c` into one
  `madd.s` on the S3 with different rounding), libm, uninitialised memory, iteration in address order, wall-clock dt,
  unseeded random · H (model knowledge. The `madd.s` emission is from an esp32.com thread snippet seen in a search, not
  read). The build compiles with `-O2` and no FP-contract flag · E · `build-s3lcd/compile_commands.json`, frame.c flags
  `['-mlongcalls', ..., '-O2', ...]` · supports: float lockstep between two boards with one firmware image is plausible
  but untested. A Mac peer does not match: the repo runs motion code under CPython on the Mac, which uses doubles · E ·
  p582-heavy:games/motion.py:4-7 · supports: a cross-platform peer or a Mac replay check needs fixed point, or a check
  run on the board.
- **NET-13** · The networking seam costs nothing now if the engine keeps four rules: (a) a fixed-step `update(frame,
  inputs)` with constant `dt`, (b) all game-state randomness from an engine-owned seeded generator, (c) inputs as a
  per-frame command record, never read inside the simulation, (d) simulation state in flat C pools that a snapshot can
  copy. If presentation (particles, shake, sound) never feeds back into state, it can stay non-deterministic · H
  (synthesis of NET-8 to NET-10 and EVT-13) · supports: both transports (ESP-NOW, UDP) and both sync models (delay
  lockstep, rollback) stay open without building either.
- **NET-14** · Calculated budget for delay lockstep at 25 fps (40 ms): one input packet per frame per player is a few
  bytes. With NET-3's round-trip averages of about 5 to 11 ms, one frame of input delay covers the average. The 75 to
  94 ms maxima stall about two frames · H (calculated from NET-3) · supports: delay lockstep is a viable first
  model for one-button games. Rollback is needed only if those stalls show in play.

## What you could not check, and why

- The time of one C-to-Python call (`mp_call_function_n_kw`) on the ESP32-S3. One search found no published number.
  The repo measured only the Python-to-C direction. A probe on the board can settle it in minutes.
- Whether Wi-Fi or ESP-NOW starts and stays stable beside `framebuffer="double"` (NET-7). Not run on the board: this
  task reads and changes nothing.
- Whether this build reports `espnow.MAX_DATA_LEN` 1470 (v2). Not run on the board.
- Free executable internal RAM in play, for natmods and viper (EVT-22). Not measured.
- ESP-NOW latency on an S3 under MicroPython. Both sources are C firmware on the ESP32 or C3 (NET-3, NET-4).
- Whether the Xtensa GCC in ESP-IDF 5.5.2 fuses multiply-add in this build (NET-12). The GCC page fetched has no
  `-mfused-madd` text. A disassembly of one function of the built firmware answers it.
- Whether a Python subclass of a type in this firmware behaves as `py/objtype.c` reads (EVT-15). Not tried on the board.
- The Thumby Color `engine_physics.c` line numbers are from the file at commit 64b5f0dc. The file was fetched by the
  GitHub contents API on the default branch (blob sha 50e74def).

## Questions for the decider

| Question | What it decides |
|---|---|
| Should C ever call Python during `engine.update()`, or only queue events that Python drains after it? | Mechanism A against C and E. Whether the engine must guard callbacks with `nlr_push` and handle re-entry. |
| Do event payloads go to Python as ints (pixels, px/s) or as floats? | Allocation per event: 0 B against 16 B per value (EVT-3). |
| Should a game extend an entity by subclassing a C type, by setting callback slots, or by a Python component that holds an id? | The binding's shape and whether C holds Python references at all (EVT-15, EVT-16, EVT-25). |
| Must a new effect or body type land without reflashing, or is a firmware rebuild per new C part acceptable? | Whether the engine exposes buffer views for viper or natmod parts (EVT-21, EVT-23, EVT-26). |
| Should the engine step on a fixed `dt` now, even with no network? | The networking seam and replayable bot runs (NET-8, NET-9, NET-13). It changes how today's games feel on a slow frame. |
| Must lockstep be possible against a non-S3 peer (a Mac, a PC, another chip)? | Floats against fixed point in the C physics (NET-12). |
| Should the first network MVP be a separate transport module, as Thumby Color's `engine_link`? | Whether the engine API carries any networking now beyond the input record (NET-11). |

## Searches

Web searches: 4 of 12. One Espressif docs search through the plugin tool, listed for completeness. Page fetches and
`gh api` file reads are not counted.

| Query, verbatim | Decision it served | Used |
|---|---|---|
| `ESP-NOW latency measured milliseconds ESP32 round trip` | which transport fits a 40 ms frame | yes: led to the Electric UI benchmark (NET-4) |
| `ESP32-S3 Xtensa FPU madd.s fused multiply add gcc -ffp-contract single precision` | whether float physics can run in lockstep | partly: only a snippet on `madd.s`, kept as H (NET-12) |
| `micropython function call overhead microseconds ESP32 benchmark method call` | the cost per event of a C-to-Python callback | no: no number found |
| `micropython espnow latency ms irecv measured game` | ESP-NOW latency under MicroPython | yes: led to Espressif's test report (NET-3). No MicroPython number |
| Espressif docs tool: `ESP32-S3 Wi-Fi internal RAM memory consumption static and dynamic buffers kilobytes` | whether the radio fits beside the "double" frame | yes (NET-6) |
