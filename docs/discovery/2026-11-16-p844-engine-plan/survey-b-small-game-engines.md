# Survey B: small game engines and consoles (spike P844)

A source of P844's [synthesis](synthesis.md) and [plan](plan.md), kept as the survey agent wrote it on 2026-11-16.

Written 2026-11-16 for spark #1208. Sources are GitHub repositories read through `gh api` on 2026-11-16 (latest commit
dates given), plus the named docs. I checked each LICENSE file. Nothing here ran on a board. Where I only read a file
name or a header and not the whole code, I say so.

## Licenses at a glance

| Project | License (file checked) | Can we copy code into our MIT repos? |
| --- | --- | --- |
| TinyCircuits Tiny Game Engine | GPL-3.0 (`LICENSE.txt`) | No. Design only. A copy forces GPL on pixel-games. |
| Pimoroni pimoroni-pico (picographics) | MIT (`LICENSE`, 2021 Pimoroni) | Yes, with the notice kept. |
| Pimoroni picovector | No LICENSE file in the repository root | No. No license means no right to copy. Design only. |
| CircuitPython (core, `_stage`, displayio, board files) | MIT (`LICENSE`, Damien P. George and each file has an SPDX MIT line) | Yes, with the notice kept. |
| Adafruit_CircuitPython_ST7789 and Display_Text | MIT (GitHub license field) | Yes, with the notice kept. |
| Pyxel 3.0.1 (2026-11-10) | MIT (`LICENSE`, Takashi Kitao) | Yes. Rust, so only design or tables. |
| TIC-80 v1.4.1 | MIT (`LICENSE`, Vadim Grigoruk) | Yes. C, so design or small tables. |
| 32blit SDK | MIT (`LICENSE`, Pimoroni) | Yes. C++, so design or small tables. |
| Arduboy2 (MLXXXp, last push 2023-08-14) | BSD 3-clause (text inside `LICENSE.txt`) | Yes with the notice, but the code is AVR C++. Nothing to copy. |
| PICO-8 | Proprietary, paid. The manual states no license for the runtime | No. Design from the manual only. |
| Playdate SDK | Panic SDK License 1.0, "non-exclusive, non-transferable, revocable" | No. Design from the public docs only. |

## 1. TinyCircuits Thumby Color: Tiny Game Engine

Source: https://github.com/TinyCircuits/TinyCircuits-Tiny-Game-Engine (last commit 2026-10-14, `64b5f0dc`). GPL-3.0.

- **What it is.** A 2D/3D engine for MicroPython. The README says "Core engine features are written in C and integrated
  into MicroPython as external C modules. The engine API is exposed through Python modules." Target: RP2350 (128x128
  screen). Also builds for Linux (SDL) and WebAssembly.
- **Split of C and Python.** Python modules are named by job: `engine`, `engine_nodes`, `engine_draw`,
  `engine_resources`, `engine_io`, `engine_audio`, `engine_physics`, `engine_math`, `engine_save`, `engine_time`,
  `engine_link` (from https://color.thumby.us/doc/landing.html). In `src/`, each module is a folder of C files with a
  `*_module.c` that binds it. The game is Python that subclasses nodes. The C loop owns time: `engine.fps_limit(30)`
  is set in `filesystem/main.py`, and the C code keeps the frame period (`src/engine.c`).
- **Rendering.** A node tree (rectangle, circle, line, text, sprite, mesh) drawn by C into double-buffered 16-bit
  frame buffers (`src/display/engine_display_common.h`). The screen size is a `#define` (128x128).
- **Display and input per board.** One small header, `engine_display.h`, has `init`, `clear`, `send`,
  `apply_brightness`. One C file per platform sits behind it: `engine_display_driver_rp2_gc9107.c` and
  `engine_display_driver_unix_sdl.c`. Input does the same: `engine_io_rp3.c` and `engine_io_sdl.c`. So a new board
  is one new file per concern, and the Mac/Linux build runs the same game code on SDL.
- **Audio.** 4 channels playing .wav, RTTTL ringtones or tones (README).
- **Physics.** Rotated rectangle and circle colliders as nodes.
- **Link.** A Link API connects two devices for local multiplayer (`src/link/`), with `rp3` and `unix` backends. This
  is the closest match to our P832. I did not read it deeply.
- **Launcher.** `filesystem/system/run_on_boot.py` writes the next game's path to a file and resets the machine.
  `main.py` reads it at boot. A comment says it is done "so that device can hard reset to clear memory".
- **Docs.** The API docs are comments inside the C files (NAME, ID, DESC, PARAM blocks), collected by
  `doc/generate.py` into markdown (`doc/format_documentation.md`). Docs live beside the code that they describe.
- **Tests.** `performance_samples.txt` logs average FPS per commit hash for node tests. No unit tests that I saw.
- **Copy?** No. GPL.
- **Take as design:** (a) the display and input split into one tiny header and one file per platform, (b) the
  reset-to-switch launcher as an optional way to defeat heap fragmentation, (c) docs written in the C source.
- **Leave:** the node tree. We have a recording canvas and 15 games that paint by hand, and a tree adds calls in the
  hot path (finding section 7 already says no scene tree). 128x128 constants in C headers. No reference Python
  version of each C part: there the C is the only version, so it does not give us PEP 399 twins.

## 2. Pimoroni MicroPython builds: picographics and picovector

Sources: https://github.com/pimoroni/pimoroni-pico (last commit 2026-10-27, `5ed5cb4a`, MIT) and
https://github.com/pimoroni/picovector (last commit 2026-05-05, no license file).

- **What it is.** Per-board MicroPython firmware (`micropython/modules/micropython-tufty2040.cmake`,
  `-pico2.cmake`, `-tiny2350.cmake`, and so on) with a C++ graphics module over a plain Python call.
- **API.** `display = PicoGraphics(display=DISPLAY_PICO_DISPLAY_2, pen_type=PEN_RGB565)`, then `set_pen`, shape and
  text calls, `update()`. Source: `micropython/modules/picographics/README.md`.
- **Display per board.** One enum value per display (about 30: LCDs, OLED, e-ink, LED matrices). The C++ file
  `picographics.cpp` has a `switch` on the enum that builds the right driver class with default pins. A caller can
  pass its own bus for "Custom Pins" (README, section "Custom Pins").
- **Pen types.** `PEN_1BIT`, `PEN_P4`, `PEN_P8`, `PEN_RGB332`, `PEN_RGB565`, `PEN_RGB888` choose the frame buffer
  format. Same drawing API for each.
- **picovector.** Anti-aliased vector shapes and fonts in C++ for RP2350. README: "An embedded vector graphics
  library for the Raspberry Pi Pico 2." Its text fonts moved out of the firmware to a separate fonts release.
- **Copy?** picographics: allowed (MIT), but it is C++ for the RP2 and the Pimoroni bus classes. Nothing small and
  portable to take. picovector: not allowed.
- **Take as design:** (a) the display as one enum plus default pins plus an override, (b) `pen_type` as a constructor
  choice that changes memory, not the API, (c) removing big optional assets (fonts) out of the firmware image.
- **Leave:** 30 displays. We have one panel. A giant `switch` in C++ is the opposite of a hardware description as
  data.

## 3. CircuitPython: displayio, `_stage`, board folders

Source: https://github.com/adafruit/circuitpython (last commit 2026-11-15, `8373f3be`, MIT). Docs:
https://docs.circuitpython.org/en/latest/shared-bindings/displayio/index.html

- **displayio.** A scene model in C: `Group` (container with x, y, scale, hidden), `TileGrid` (tiles from one
  `Bitmap`, coloured by a `Palette` and a one-tile grid is a sprite). Rendering is lazy: pixels are computed only for
  dirty regions. The bus that carries pixels is a separate module (`fourwire`, `paralleldisplaybus`), and
  `busdisplay` joins a bus to a panel (`shared-module/` folder list).
- **A board is a folder of five files.** Example `ports/espressif/boards/adafruit_feather_esp32s3_tft/`:
  `board.c`, `mpconfigboard.h`, `mpconfigboard.mk`, `pins.c`, `sdkconfig`. `board.c` holds the ST7789 start-up as a
  byte table (`command, count | DELAY, data...`), the SPI pins, the baud rate (40 MHz), the size (240x135) and the
  column and row offsets (40, 53). `pins.c` names the pins. The panel is data. The code that builds it is shared.
- **`_stage`.** A C module by Radomir Dopieralski (MIT) for PyBadge and PyGamer. `render_stage` in
  `shared-module/_stage/__init__.c` builds each screen line from a list of tile layers and text layers, a few
  lines at a time into a small buffer, and sends it to the bus. No full frame buffer. `Layer` holds a tile map, a
  graphic, a palette, x, y, width, height, frame and rotation (`Layer.h`). Transparent colour falls through to the
  next layer, and a background colour fills the rest. Python describes the layers. C paints.
- **Audio.** `audiomixer`, `audiocore`, `audiopwmio`, `audioio`: a mixer is a separate module from the output.
- **Copy?** Yes, MIT: the ST7789 init table pattern and the `_stage` line compositor are copyable with the notice.
  We already have our own s3lcd driver and our own init, so we will copy only the idea of the table.
- **Take as design:** (a) the hardware description as a data table beside a pin list, with shared code that reads it,
  (b) bus separate from panel separate from scene, (c) line-by-line compositing for RAM-poor screens.
- **Leave:** the whole displayio object tree (Group, TileGrid, shaders). It is a generic UI model with call overhead
  per item, and our games paint fast C-backed draws. Also the CircuitPython "board.DISPLAY" magic, because our
  composition root passes objects in and does not use globals.

## 4. Pyxel

Source: https://github.com/kitao/pyxel (v3.0.1, 2026-11-10, MIT). API: `docs/api-reference.md`, `docs/mml-commands.md`.

- **What it is.** A retro game engine for Python. The core is Rust (`crates/pyxel-core`, with `platform/`, `audio.rs`,
  `canvas.rs`, `sound.rs`, `tilemap.rs`, `mml_parser.rs`) and a thin binding (`crates/pyxel-binding`). The same core
  runs on desktop and in the browser (`wasm/`).
- **Model.** `pyxel.init(width, height, fps=30, ...)`, then `pyxel.run(update, draw)`. Input by `btn`, `btnp(key,
  hold, repeat)`, `btnr`. Fixed limits: 16 colours, 3 image banks, 8 tilemaps, 4 audio channels, 64 sounds.
- **Sound.** A sound is data: notes plus tone, volume and effect lists, or a text MML string
  (`T120 @1 V100 ...`, with envelope, vibrato and glide slots). Four tones: triangle, square, pulse, noise.
- **Resources.** One `.pyxres` file holds images, tilemaps, sounds and music (`docs/pyxres-format.md`).
- **Project process.** `AGENTS.md` sends every agent to `docs/design/design-policy.md`, `design-audit.md` and
  `design-decisions/`. The policy sets clarity, consistency and "demonstrated hot-path cost" as the only reason to leave
  idiom. This is the same idea as our principles and our finding's decision log.
- **Copy?** MIT, but it is Rust. We can copy the MML command table as a spec (a plain table of commands).
- **Take as design:** the hard limits as the contract (a game cannot ask for a fifth channel), `btnp(hold, repeat)`
  as the one place that does key repeat (our `Actions` can do the same), one resource file per game.
- **Leave:** MML and the tone synth. Our sounds are recorded samples in a bank, and a synth in the callback will
  cost CPU we do not have (the finding says 4 voices already cost 9 ms of 16 ms in Python).

## 5. PICO-8 and TIC-80

- **PICO-8.** Source: https://www.lexaloffle.com/dl/docs/pico-8_manual.html (read 2026-11-16; proprietary and paid).
  128x128, fixed 16-colour palette. Code is Lua, max 8192 tokens. A cartridge is 32 KB, and code must compress to under
  15360 bytes. 4 sound channels, 64 SFX, music patterns 0 to 63. Callbacks `_init`, `_update`, `_draw`
  (`_update60` for 60 fps). Lesson: limits are the cartridge model, and the three callbacks are the whole game
  contract. It matches our `setup`, `play`, `paint`. No code to copy.
- **TIC-80.** Source: https://github.com/nesbox/TIC-80 (v1.4.1, last commit 2026-11-15 `9f9a2f2c`, MIT). 240x136,
  16 colours, 256 sprites and 256 tiles of 8x8, 4 sound channels (wiki Specifications and README). The notable part is
  `include/tic80.h`: the public core is a few C structs. The host fills in gamepad and mouse state, the core is
  ticked, and the host reads back a frame buffer and 44.1 kHz stereo samples. The constants are in the header
  (`TIC80_WIDTH 240`, `TIC80_FRAMERATE 60`, `TIC80_SAMPLERATE 44100`). The language is a plug-in: `src/api/` has one
  file per language (lua, js, python, wasm, and more). So one core drives many front ends.
- **Copy?** TIC-80 is MIT. Nothing to copy as code. Take the shape: a core with no platform headers, whose host
  passes input in and takes pixels and samples out.
- **Leave:** the in-device editors, carts as a file format and the many script languages. We build firmware, not a
  fantasy computer.

## 6. Arduboy2

Source: https://github.com/MLXXXp/Arduboy2 (last push 2023-08-14; BSD 3-clause). A C++ library for a 128x64 mono
console on an AVR chip with 2.5 KB RAM. `Arduboy2Core` (hardware: LCD, buttons, sound pin) is a base of `Arduboy2Base`
and `Arduboy2` (game helpers). Games call `setFrameRate(60)` and then `if (!arduboy.nextFrame()) return;` at the top
of `loop()`. Buttons: `pollButtons()`, `pressed()`, `justPressed()`. Sprites are bit-packed bitmaps. Take as design:
a one-line frame pacer (`nextFrame()`) and the Core/Base/Full class layers, which match our hardware / engine / kit
layers. Nothing to copy: AVR specific. Leave the rest.

## 7. 32blit SDK and Playdate

- **32blit.** https://github.com/32blit/32blit-sdk (last commit 2026-07-27 `db99cb7f`, MIT). Games write
  `init()`, `update(time)`, `render(time)`. One game source builds for three hosts: `32blit-stm32` (the console),
  `32blit-sdl` (a desktop window) and `32blit-pico`. The firmware hands the game an API table of function pointers
  and data (`32blit/engine/api_private.hpp`, `APIConst`, with an `api_version`), so games load as separate files.
  `Surface` carries pixel format, palette and function pointers for blending (`SurfaceTemplate`). Audio is channels
  with waveform bits, ADSR and a callback for a custom wave (`audio.hpp`, 22050 Hz, 64-sample wave buffer).
  `engine/` also has `multiplayer`, `profiler`, `tweening`, `particle`, `save`. Take as design: three hosts from one
  game source, a version number on the engine API, and a profiler as an engine part. Leave: the table of pointers
  (our games are Python modules, so an import does the job).
- **Playdate.** Public docs only: https://sdk.play.date/3.1.1/Inside%20Playdate%20with%20C.html. Lua `playdate.update()`
  runs before every frame. The C API is a `PlaydateAPI*` struct of function pointers, and a game may replace the
  update callback with a C function, or mix C and Lua. Take as design: the same split we use, scripting for the
  game, C for hot parts, with Python chosen by default. The license forbids copying. Leave the rest.

## 8. What this means for our plan

Our finding's rule (reference plus fast version, chosen once, DI by constructor) is the usual shape for these systems
too. None of them has a plain-Python twin for each C part, so none can serve as a model for our twin tests. The
sources that help are about the other layers: how a board is described, how a game is switched in, how the display
is split from the scene.

Per stage in the finding's table (N, 0, 1, 2, 3a, 3b, 3c, 4, 7, 5a, 5b, 6, 8, 9):

- Stage 0 (the home): Pyxel's design policy and decision records are a model for the package README and a
  `docs/design-decisions` folder. Thumby's docs-from-comments is an option for the C module `engine`. Small gain.
- Stage 1 (input): Pyxel's `btnp(key, hold, repeat)` places repeat in the input layer.
- Stage 3b (scene manager): Thumby switches games by reset.
- Stage 6 (loop, display): Thumby's `display.h` shape, Arduboy's `nextFrame()`.
- Stage 7 (hardware): CircuitPython's board folder and Pimoroni's display enum.
- Stage 9 (second board): TIC-80 and 32blit show one core with several hosts.

## 9. Ranked: the three most useful things for our engine

1. **The board and panel as data, handed to one shared builder** (CircuitPython's `board.c` and `pins.c`, MIT; Pimoroni's
   `display=` argument with a custom-bus override, MIT). Fits **stage 7** (the hardware). Concretely: `hardware.py`
   holds a panel record (size, column and row offsets, orientation, SPI rate, the ST7789 start-up bytes as a table,
   DC/CS/RST/BL pins read from `pins.py`) and one `open_display(record)` in `main.py` builds `TftOut` or `StOut` from
   it. This removes `gdi.py`'s repeated pins and the 240x320 constants in `lcd.py:33`, and a second board becomes
   a second record. Copy rule: the byte-table idea only. Our own init stays our code.
2. **The game switch as a strategy, with Thumby's reset-to-switch as the second version** (GPL, so design only).
   Fits **stage 3b** (the scene manager): `SceneManager` takes a `Switcher`. Version one is today's in-process
   switch behind the loading card. Version two writes the next game's name to a file and calls `machine.reset()`,
   so every game starts with a clean heap. Reasoning: the finding measures a 58 ms longest frame at the switch (P837)
   and a `gc` policy per frame. A reset boot costs seconds but needs no gc work. Cost and value are not measured, so
   make it a card in stage 3b's tail, not a default. The Mac test can drive it with a fake `reset`.
3. **A core with no platform in it, driven by a host that gives input and takes frame and samples** (TIC-80's
   `include/tic80.h`, MIT; 32blit's one source for stm32, SDL and Pico, MIT; Thumby's one file per platform behind
   a four-function display header, GPL, design only). Fits **stage 6** (loop, `FrameOutput`) and **stage 9** (the second board and the
   Mac host). Concretely: write the `FrameOutput` interface as `clear`, `draw` (or `send`), `brightness`, and make
   the Mac frame-hash stand-in (`tests/drawing_tft.py`) a first-class second host of it, as Thumby's SDL
   driver and 32blit's SDL host are. This keeps the net of stage N alive after the move. A smaller idea of
   the same row: CircuitPython `_stage` (MIT) composites tile layers a line at a time into a small buffer. It is worth
   a measured spike as a fast `paint_static`, but only if the board's RAM or the paint time (stage 4's 0.5 ms
   gate) demands it. I did not measure anything.

Not ranked but cheap: Pyxel's design-policy plus decision-record layout (stage 0), the hard limits as a contract
(stage 8's new-game checklist), and putting API docs beside the C (stage 0 or 9).
