# P539 council: PO assistant (lenses: Existing first, Risks and assumptions)

Run 2026-11-02, model Opus. Read-only on every repository. All GitHub facts were read on 2026-11-02 through `gh api`
(repo metadata, `releases/latest`, `commits`, `contents`), unless a line says otherwise. GitHub gives its dates in UTC.
Only dates are given here, no clock times. "Stars" means the GitHub stargazer count read on 2026-11-02. It is a
popularity signal, not a count of users.

## Findings

Format: PO-n · claim · tag · pointer · supports only.

### A. What matters most

- PO-1 · Only one person is blocked today, and the P537 plan already unblocks him without a public library. The PO's games
  run at 21 to 24 fps at a 40 ms pace, and paint is now the limit. P537 projects this for a kept background plus glyph text in
  C, about 140 C lines inside the s3lcd fork: runner's paint goes from 34 ms to about 8 ms at most. Then every game in play
  is under 33 ms · E bench.md run 22 (measured, 3 games, 2026-11-02), E p537-finding.md "options" table, rank 2
  (projection from per-interval maxima, so H until slice 0 measures the averages) · supports only: J1 (smooth games) does
  not need a multi-chip public library. It needs P537 slices 0 to 3. The public library is a separate bet, on other
  people.
- PO-2 · A public C++ core that serves both MicroPython and a C++ SDK, and uses chip hardware, already exists for one chip:
  Pimoroni PicoSystem. It has a C++ library (`libraries/blend.cpp`, `primitives.cpp`, `text.cpp`, `screen.pio`,
  `screen_double.pio`) and a MicroPython binding over the same code (`micropython/modules/picosystem/picosystem.c` plus
  `.cpp` files). MIT. Release v2.0.0, 2026-08-27. RP2040 only · E gh api repos/pimoroni/picosystem (contents, licence,
  releases/latest) · supports only: the architecture the PO asks for is proven feasible at small scale. It does not show
  that such a library gets users outside its own console.
- PO-3 · LovyanGFX is already usable from MicroPython, through M5Stack's UIFlow2 firmware. `m5stack/components/M5Unified/mpy_m5gfx.cpp`
  (MIT, 1522 lines) wraps M5GFX (a LovyanGFX derivative), and `mpy_user_lcd.txt` defines a `User_GFX` with ST7789,
  ST7735, GC9A01, ILI9342 and SSD1306 panels on SPI. The binding is thin. Its canvas has `newCanvas` and
  `push(x, y)` = `pushSprite(x, y)`. Among its functions I found no transparent-colour push. I found no rotate or zoom, and no dirty-region send
  · E gh api m5stack/uiflow-micropython, function list grepped from mpy_m5gfx.cpp (read 2026-11-02).
  MIT, last push 2026-11-02, 214 stars, boards folder lists only M5Stack boards plus Nesso_N1 · supports only: "adopt
  LovyanGFX from MicroPython" is a real option. Today it means M5's firmware or a fork of its binding, and the sprite
  features the games need are missing from that binding. Not tested on the FireBeetle.
- PO-4 · CircuitPython supports the PO's exact board: `ports/espressif/boards/firebeetle2_esp32s3` (16 MB flash, 8 MB octal
  PSRAM, AXP313A frozen module). It brings displayio (TileGrid, Group, Palette, dirty areas in `area.c`, last TileGrid commit
  2026-10-19) and `_stage` (tiles and sprites in C). The board file sets up no display. The user's code builds the ST7789
  · E gh api adafruit/circuitpython contents of the board folder and of shared-module/displayio, MIT (LICENSE read).
  release 10.3.1, 2026-09-14 · supports only: an adopt path that needs no new C code exists on this board. Its frame rate
  on this board and panel is unknown (see PO-27). Taking it means a firmware switch and a port of the games.
- PO-5 · Every MicroPython C graphics project I surveyed ships as custom firmware, one image per board. Examples:
  s3lcd and st7789_mpy (user C modules, a `firmware` folder in st7789_mpy), lvgl_micropython (builds MicroPython with its
  own `make.py`), UIFlow2 (its own board list), Pimoroni (11 `.uf2` images in release v1.29.0-2, one per board), and the
  Thumby Color engine (a MicroPython fork) · E gh api contents and releases of each repo (2026-11-02), research.md §2
  (the s3lcd build command) · supports only: a MicroPython user of the new library must flash our image for their board.
  The reach is the set of boards we build images for. A dynamic native module (`.mpy`) is the only route around this.
  MicroPython ships a `framebuf` natmod example (`examples/natmod/framebuf`). I did not check whether a natmod can
  call esp_lcd (see "What I was not able to check").
- PO-6 · The projects we build on show the maintenance risk. s3lcd's last commit was 2024-03-20 ("Fix for
  micropython decf8e6a"), and it has 11 open issues. P511 had to patch it to build on MicroPython v1.29 and IDF 5. TFT_eSPI's
  last release is V2.5.43 of 2024-03-06. It has 278 open issues, and its S3 DMA was fixed for Arduino-ESP32 core 3.x only
  on 2026-02-15 (commit c00d8f4e). Issue #3667 "Example Rotate_Sprite_3 doesn't compile in ESP32 core 3.x.y" is open since
  2025-02-18 · E gh api russhughes/s3lcd commits and search/issues, Bodmer/TFT_eSPI releases/latest, commits, search/issues
  (2026-11-02), E firebeetle-games commit 568af6b ("s3lcd builds on MicroPython v1.29") · supports only: single-maintainer
  display libraries stall when the IDF, MicroPython or the Arduino core moves. Two upstreams per binding (MicroPython plus
  IDF, Arduino core plus IDF) double that exposure.
- PO-7 · The P537 survey has three stale or wrong claims. (a) "st7789_mpy … last commit Oct 2026": that commit is a
  dependabot pip merge. The last human commit is f629308d of 2024-06-09, and the C sources last changed before that.
  (b) "LVGL upstream has no esp32 path": true for `src/draw/sw/blend`, but LVGL now has `src/draw/espressif/ppa`
  (`lv_draw_ppa*.c`, a P4 PPA draw unit, last commit 2026-10-27). (c) "Colour-key blit and RGB565 alpha blend have no
  published number" on PIE: Jet (MIT) has S3 PIE inline assembly for RGB565 blending (`src/BlendSpans.cpp`, `ee.vld.128`,
  `ee.vmul.u16`, under `CONFIG_IDF_TARGET_ESP32S3`). BitsForPeople wrote a post on 2026-10-15. It says "16+16 RGB565 source pixels
  into 16 RGB565 destination pixels takes about 90-100 CPU clock cycles", "~5x" against scalar · E gh api
  russhughes/st7789_mpy commits (non-bot filter), E gh api lvgl/lvgl contents of src/draw and commits on
  src/draw/espressif, E gh api CubeCoders/Jet contents and code search "ee.vld",. The 90-100 cycles is stated by the
  author (E github.com/CubeCoders/Jet/discussions/10, fetched 2026-11-02), not measured by us · supports only: the
  P537 reuse table must be corrected before the brief cites it. The blend number is the author's own claim.
- PO-8 · GPL code sits close to the useful pieces, and our repo is MIT. GPL-3.0: TinyCircuits Tiny Game Engine (the
  MicroPython 2D and 3D engine of Thumby Color), BitsForPeople/esp-bits-and-pieces (the S3 SIMD RGB565 helpers that the
  Jet post links), and the Thumby code editor. u8g2's code is BSD-2, but its fonts "are licensed under different
  conditions" · E LICENSE files read through gh api (2026-11-02) · supports only: we can read these but not copy them.
  Per-file licence checks are needed before any port, fonts included.

### B. The survey table

Verdict words: reuse = take as a dependency. Port = copy code under its licence, notice kept. Idea = learn, write our own.
skip. "Split" = how the panel driver, the bus and the drawing are separated in the code. Every licence was read in the
LICENSE file itself on 2026-11-02 (GitHub shows "NOASSERTION" for several, the file decides). Activity = last release
(tag, date) and last push or commit, read the same day.

| project | does | does not | licence (file, read 2026-11-02) | activity | split | MicroPython / Arduino reach | verdict | tag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LovyanGFX (lovyan03) | sprites (LGFX_Sprite), rotate and zoom, affine push, DMA, many panels and buses, platforms esp32, esp32s3 (Bus_Parallel8/16, Bus_RGB), esp32p4 (Bus_DSI), rp2040, sdl, framebuffer | no dirty-tile send that I saw, no MicroPython binding of its own | FreeBSD (BSD-2), Copyright 2020 lovyan03, plus Adafruit BSD and MIT notices in `license.txt` | 1.2.36, 2026-10-30, last commit 2026-10-30, 1797 stars | `src/lgfx/v1/` Bus.hpp, Panel.hpp, platforms/<chip>/, panel/ | Arduino, ESP-IDF, Pico SDK (examples_for_picosdk), PC (examples_for_PC). MicroPython only through M5's binding (PO-3) | port pieces (panel init tables, affine sampler) with the BSD notice, reuse as a dependency only for an Arduino build | E gh api, license.txt, contents |
| TFT_eSPI (Bodmer) incl. TFT_eSprite ("Bodmer's sprites") | sprites 1/4/8/16 bit, pushSprite with a transparent colour, smooth AA fonts and shapes, per-chip `Processors/` incl. ESP32_S3 and RP2040 with PIO programs | release stalled since 2024-03, a setup file per board (User_Setups) | FreeBSD (Copyright 2026 Bodmer) for his code, BSD for the Adafruit parts, MIT for the ILI9341 start | V2.5.43, 2024-03-06, last commit 2026-04-03 (README), 278 open issues, 4967 stars | TFT_eSPI.cpp + Processors/<chip> + TFT_Drivers/ + Extensions/Sprite.cpp | Arduino (and IDF as a component), no MicroPython | idea (soft-edge math, sprite API), port single functions after a per-file check | E gh api, license.txt |
| Adafruit GFX | GFXcanvas16, the GFXfont glyph format, shape primitives | no sprites with a key colour, no DMA, no dirty regions | BSD (Copyright 2012 Adafruit) | 1.13.0, 2026-10-20, push 2026-10-30, 2865 stars | GFX base class, panel drivers in separate libraries | Arduino only | idea, take the GFXfont format as data (LovyanGFX, TFT_eSPI and Arduino_GFX all read it, H from their file names `gfxfont.h`) | E gh api, license.txt |
| Arduino_GFX (moononournation) | the widest bus list: `src/databus/` has ESP32 SPI, SPIDMA, QSPI, LCD8/16, RGB panel, DSI panel, RPi Pico SPI and PAR8/16, AVR, STM32, nRF, canvases RGB565, 3-bit, indexed, mono | no sprites with a key colour as such (—), no MicroPython | `license.txt` is the Adafruit BSD text only (24 lines) | v1.6.9, 2026-10-07, last commit 2026-10-28, 1156 stars | clean three-way split: `databus/`, `display/`, `canvas/` | Arduino only | idea: the databus/display/canvas split as the port interface model | E gh api, contents |
| LVGL (draw layer and drivers, not widgets) | software renderer with layers, blending, transforms, glyph cache, draw units for P4 PPA (`src/draw/espressif/ppa`), STM32 DMA2D, NXP, VG-Lite, blend paths arm2d, helium, neon, riscv_v, sve2, display drivers lv_st7789, lv_st7735, lv_ili9341, generic MIPI, and wrappers for tft_espi and lovyan_gfx | no S3 PIE path upstream, the draw layer is run through its own task pipeline, and calling it outside that is not a documented path (search summary of docs.lvgl.io 9.x, H) | MIT | v9.6.0, 2026-09-16, push 2026-11-02, 25074 stars | `src/draw/<unit>/`, `src/drivers/display/<panel>` | MicroPython via lv_binding_micropython (MIT, push 2026-09-06) and lvgl_micropython (MIT, no release, push 2026-06-23), Arduino yes | idea: the draw-unit interface is the model for "one call, many accelerators", port the PPA unit's use of esp_driver_ppa as the P4 reference. Skip as the base (PO-23) | E gh api, H for the standalone-draw point |
| u8g2 / ucglib (olikraus) | u8g2: monochrome displays, large font collection, ucglib: colour displays | ucglib dormant | BSD-2 code, u8g2 fonts per font group | u8g2 no GitHub release, push 2026-09-14, 6741 stars, ucglib push 2021-04-08 | — (not read) | Arduino, C | u8g2 fonts: port per font after its licence, ucglib skip | E gh api, LICENSE files |
| Pimoroni PicoGraphics / PicoVector (pimoroni-pico) | pens as classes per colour format (`pico_graphics_pen_rgb565.cpp`, rgb332, p4, p8, 1-bit, rgb888, inky7), sprites, text, pretty-poly AA vectors, ST7789 parallel by PIO (`drivers/st7789/st7789_parallel.pio`) | RP2040/RP2350 only | MIT | v1.29.0-2, 2026-08-31, push 2026-10-27, 1566 stars | libraries/pico_graphics (drawing), drivers/<panel> (bus+panel), micropython/modules/picographics (binding) | MicroPython (per-board `.uf2`) and C++ Pico SDK, no Arduino | port: the pen-per-format pattern and the C-over-C++ binding pattern (`picographics.c` + `.cpp`), idea for the PIO bus | E gh api contents, releases |
| Pimoroni PicoSystem | game API: sprites, blend modes, text, PIO screen with pixel doubling | one console only | MIT | v2.0.0, 2026-08-27, 177 stars | libraries/ core + micropython/modules binding over the same core | MicroPython and C++ SDK | port the blend table (`blend.cpp`), idea: the whole shape (PO-2) | E gh api |
| CircuitPython displayio, bitmaptools, `_stage` | Group, TileGrid (sprite sheets, flips, transparent index), Palette, ColorConverter, dirty areas (`area.c`), `_stage` composes 16 x 16 tile layers and text per pixel while streaming to the bus, no framebuffer (Layer.c 2200 B, Text.c 1244 B, __init__.c 2710 B) | tied to the CircuitPython core and its display bus, `_stage` has 4-bit tiles, 16 px fixed | MIT (LICENSE and SPDX headers of Layer.c, TileGrid.c read) | 10.3.1, 2026-09-14, TileGrid.c commit 2026-10-19, `_stage` commit 2024-05-20 | shared-module (C) + shared-bindings (Python API) | CircuitPython only (supports the FireBeetle 2 S3, PO-4), MicroPython port of Stage: python-ugame/micropython-stage, MIT, push 2021-09-02 | port: `_stage` render loop and the 8-way orientation switch (read in full, PO-14), idea: displayio's Group/TileGrid API | E gh api, files read |
| russhughes s3lcd (and our fork) | esp_lcd SPI and i80 buses, fill, line, polygon, alpha `blit_buffer`, bitmap and Hershey fonts, jpg, png, our `frame.c`: internal DMA frame, partial send by 16 px tiles, timeout, `config()` | no key-colour sprite (lcd.py: "blit_buffer has none"), no tiles, upstream dormant | MIT (Russ Hughes 2020-2022, Ivan Belokobylskiy 2019) | last commit 2024-03-20, 11 open issues, newest fork kankungyip/s3lcd (push 2025-09-24, "add transform for blit_buffer" 2025-02-19) | s3lcd_spi_bus.c / s3lcd_i80_bus.c, s3lcd.c (2927 lines: panel + drawing + Python), frame.c / frame.h (528 + 83 lines: memory + send) | MicroPython on ESP32-S3 only | reuse frame.c (ours), port drawing out of s3lcd.c into the core, the upstream bug P533 found has no upstream issue (search "dma_rows" gives 2 unrelated issues) | E gh api, files in s3lcd/src |
| russhughes st7789_mpy | the same drawing family for ST7789 on ESP32, Pico and others | no esp_lcd, no DMA queue (research.md §7, devbis copy) | MIT | no release, last human commit 2024-06-09 (PO-7), 730 stars | single C module | MicroPython, prebuilt images | idea, fixes only | E gh api |
| MicroPython framebuf (core) | RGB565 and other formats, fill, line, ellipse, poly, `blit(src, x, y, key, palette)` with a key colour and a palette, `text` 8 x 8 | per-pixel `getpixel`/`setpixel` in blit (modframebuf.c:730-780), so generic, not fast paths, no dirty marks | MIT | in every MicroPython, file last changed 2025-08-14 | one file | every MicroPython build, also a natmod example | reuse now as the baseline for sprites, if frame.c exposed its pixels as a buffer (it does not today: no buffer-protocol getter among s3lcd's methods, grepped) | E modframebuf.c read, s3lcd.c grep |
| Espressif esp_lcd (in ESP-IDF) | panel IO (SPI, i80, QSPI, RGB, DSI), panel ops, color-done callback | no drawing | Apache-2.0 | IDF push 2026-11-02 | panel_io / panel | under MicroPython user modules (frame.c uses it) and Arduino-ESP32 | reuse as the ESP bus/panel layer (frame.c already does) | E gh api, frame.h |
| esp-bsp / esp_lvgl_port | LVGL on esp_lcd, double buffer, flush from the done callback, S3 PIE `.S` for RGB565 fill and RGB565 blend-normal, and `lv_macro_memcpy.S` (`src/lvgl9/simd/`, 11 files) | tied to LVGL's blend API | Apache-2.0 (`license.txt`, SPDX header in `lv_color_blend_to_rgb565_esp32s3.S`, 404 lines) | component 2.9.0, repo push 2026-10-30 | — | IDF only | port the `.S` files with the Apache notice (as P537 slice 8 plans) | E gh api, files |
| esp-dsp | S3 PIE assembly: `support/mem/esp32s3/dsps_memcpy_aes3.S`, `dsps_memset_aes3.S`, s16 add/sub/mul, image dot products, one P4 file (`dsps_biquad_f32_arp4.S`) | no graphics | Apache-2.0 | no GitHub release, push 2026-05-11 | per module, per chip suffix (`_aes3`, `_arp4`) | IDF, and the Arduino-ESP32 core (H) | port memcpy/memset as the PIE copy and fill candidates, idea: the per-chip file suffix as the dispatch pattern | E gh api code search "aes3 extension:S" (32 hits) |
| Pico SDK examples (pico-examples, pico-playground) | `pio/st7789_lcd` example, pico-playground `scanvideo/sprite/sprite.S` (ARM assembly sprites) | not a library | BSD-3-Clause | pico-examples push 2026-10-12, pico-playground push 2026-09-04 | — | C SDK | idea / port of the PIO program for a Pico bus | E gh api |
| Jet (CubeCoders) | 3D rasteriser in C++17, Sprite2D, RGB565 S3 PIE blend in inline assembly (PO-7), ships `library.properties`, `library.json`, `idf_component.yml`, `CMakeLists.txt`, Doxyfile, tests | 3D focus (out of scope) | MIT (Copyright 2026 CubeCoders Limited) | created 2026-05-05, last commit 2026-09-25, 548 stars | — | Arduino, PlatformIO, IDF, no MicroPython | port the S3 blend kernel (MIT), idea: one repo shipped as Arduino library and IDF component, C++17 on the S3 | E gh api contents, LICENSE, code search |
| TinyCircuits Tiny Game Engine (Thumby Color) | MicroPython 2D/3D game engine in C: nodes, sprites, text, shaders, physics, audio, drivers rp2 GC9107, unix SDL, also WebAssembly | ESP32 not ported | GPL-3.0 (LICENSE.txt read) | push 2026-10-14, 34 stars | src/display/engine_display_driver_<chip>_<panel>.c, src/draw/ | MicroPython (its own fork) | idea only (GPL): the driver-per-chip-and-panel file naming and the desktop SDL target | E gh api |
| Thumby code editor | 1-bit Python sprites | colour | GPL-3.0 | push 2025-03-19 | — | — | skip | E gh api |
| ODROID-GO MicroPython games (cheungbx) | games on ODROID-GO | maintained | none stated | push 2019-11-16 | — | — | skip (dormant) | E gh api |
| python-ugame/micropython-stage | Stage for MicroPython (C `_stage` + Python) | updates since 2021 | MIT | push 2021-09-02, 45 stars | — | MicroPython | idea, the CircuitPython copy is newer | E gh api |
| peterhinch micropython-nano-gui | GUI on framebuf in Python | C speed | MIT | push 2026-06-13, 668 stars | — | MicroPython | skip for drawing | E gh api |
| bitbank2 bb_spi_lcd | display library with ESP32 support | — (not read) | Apache-2.0 (GitHub field) | 2.9.10, 2026-10-30 | — | Arduino | — (not read beyond metadata) | E gh api metadata only |

Kitronik ZIP96 MicroPython code: the repo name I tried returned 404. Not surveyed.

### C. Where each library part comes from (the mix table)

Every row is a proposal for the decider, from the survey above. "Ours" = code in the s3lcd fork today.

| part | take from | how | licence effect | tag |
| --- | --- | --- | --- | --- |
| panel driver (init, orientation) | esp_lcd's ST7789 panel (ESP), LVGL `lv_st7789.c` / `lv_lcd_generic_mipi.c` (non-ESP), PicoGraphics `drivers/st7789` (Pico) | reuse esp_lcd as a dependency, port the LVGL generic MIPI driver for other chips | Apache-2.0 notice in images, MIT | E file listings |
| bus and DMA | ours (`frame.c` on esp_lcd: internal frame, done semaphore, timeout), Pico: PicoGraphics `st7789_parallel.pio`, pico-examples `pio/st7789_lcd`, TFT_eSPI `pio_SPI.pio.h`, P4: esp_lcd DSI | reuse frame.c, port one PIO program | MIT / BSD-3 / FreeBSD notice | E |
| framebuffer and dirty regions | ours (16 px tile marks, windows, measured: flappy send 11.3 ms in play, bench.md slice 5), displayio `area.c` (area union) as a second strategy | reuse ours, idea from displayio | — | E bench.md, gh api |
| blit and sprites | MicroPython `framebuf.blit` (key + palette) as the zero-code baseline, `_stage` Layer.c (16 x 16, 8 orientations, palette), TFT_eSprite transparent push, LovyanGFX affine and rotate-zoom later | port Layer.c logic, idea from the others | MIT, FreeBSD for LovyanGFX pieces | E files read |
| fonts and text | framebuf 8 x 8 (in core, used by the games now), Adafruit GFXfont format as data, s3lcd bitmap and Hershey fonts (in the fork), TFT_eSPI smooth fonts later, u8g2 fonts per font | glyph cache in C (P537 slice 2) reading GFXfont tables | BSD / MIT, per-font check | E |
| tiles and layers | `_stage` (tile grid composed per pixel, colour 0 transparent), displayio TileGrid (flips, transparent index), 32blit TileMap (MIT, from P537, not re-read) | port `_stage` loop into a per-dirty-tile compose | MIT | E (stage, displayio), H (32blit, P537 survey) |
| colour formats | PicoGraphics pens (one class per format) | idea: a pen/format strategy class, RGB565 first | MIT | E file list |
| blending | s3lcd `alpha_blend_565` (ours, s3lcd.c:185), PicoSystem `blend.cpp` (mode table), S3: esp_lvgl_port `.S` (fill, blend), Jet `BlendSpans.cpp` (PIE blend, MIT), esp-dsp `dsps_memcpy_aes3.S` / `dsps_memset_aes3.S` | port, each behind a build flag and a scalar fallback | MIT / Apache-2.0 | E |
| chip dispatch | LVGL draw units (one interface, many accelerators: PPA, DMA2D, VG-Lite), esp-dsp file suffixes `_aes3`, `_arp4` | idea | — | E |
| MicroPython binding | MicroPython `examples/usercmodule/cppexample` (C++ in a user module), PicoGraphics / PicoSystem C-over-C++ binding, M5's `mpy_m5gfx.cpp` (LovyanGFX in MicroPython) | port the pattern | MIT | E file listings |
| Arduino binding | LovyanGFX, Arduino_GFX and Jet ship `library.properties`, Jet and LovyanGFX also `library.json` and an IDF component | idea | — | E |
| build, CI, releases | Pimoroni (a `.uf2` per board on each release), LovyanGFX `examples_for_PC` and `platforms/sdl`, Tiny Game Engine unix SDL driver (desktop tests) | idea | — | E |

What none of the surveyed projects offers, by my reading (H, surveyed set only, not a market scan): one MIT C/C++ core that
is (a) a MicroPython module and (b) an Arduino library, (c) on the ESP32-S3 with an esp_lcd partial send by dirty tiles,
and (d) with S3 PIE blits behind the same calls. The closest are PicoSystem (a+SDK, RP2040, PIO), M5GFX in UIFlow2 (a+b
through LovyanGFX, M5 boards plus a User LCD, thin binding) and LVGL (a+b, a widget runtime).

### D. Risks and assumptions

- PO-9 · Who is blocked without this now: the PO, n = 1, for J1, and P537 slices 0 to 3 address it inside the fork
  (PO-1). For the three other personas in jobs-and-journeys.md (Arduino makers, MicroPython users on other boards,
  contributors) the evidence is H (the PO's words). My one search for 2025 forum posts about slow MicroPython sprites on
  an S3 found none that matched. It found drivers whose READMEs say "use a framebuffer" · E jobs-and-journeys.md "Who",
  search 4 below (summary, not read in full) · supports only: I saw no outside user ask for this. Absence in
  one search is weak evidence.
- PO-10 · Popularity of the incumbents, as a ceiling and a competition signal (stars, 2026-11-02): LVGL 25074,
  TFT_eSPI 4967, Adafruit GFX 2865, LovyanGFX 1797, pimoroni-pico 1566, Arduino_GFX 1156, st7789_mpy 730,
  micropython-nano-gui 668, s3lcd 112, micropython-stage 45, Tiny Game Engine 34 · E gh api · supports only: Arduino users
  have mature choices. MicroPython C graphics modules draw two orders of magnitude fewer stars than Arduino libraries.
  Stars are not users.
- PO-11 · What must be true for building to beat adopting (each H, mine, from the findings):
  1. LovyanGFX from MicroPython (through M5's binding or a fork) cannot reach the games' needs at less cost than a new core.
     PO-3 shows the binding lacks a key-colour push and a dirty-region send. Adding them to a fork is possibly cheaper than a new
     core. Unmeasured.
  2. LVGL's draw layer cannot be used without its runtime at an acceptable cost and size. Not shown either way (H, search 5
     summary).
  3. CircuitPython displayio plus `_stage` on the FireBeetle is too slow or too limiting for the games. Unmeasured
     (PO-27).
  4. At least one user besides the PO will flash a custom image to get the speed (PO-5, PO-9).
  5. The PO, with AI, can keep two bindings and more than one chip building against moving IDF, MicroPython and Arduino
     cores (PO-6).
  6. A C++ core costs no measurable frame time against C on the S3. Jet runs C++17 on the S3 at 21.6 to 23.6 ms per
     480 x 320 frame (author's measurement, docs/ESP32Performance.md, 2026-09-24). That is a different workload, so it
     only shows the toolchain copes.
- PO-12 · The riskiest belief, my opinion: belief 4 together with 5. A library built to make one person's S3 games smooth
  becomes a public multi-chip, two-binding project that others adopt and that one maintainer keeps alive. Every surveyed
  dormant project (s3lcd, st7789_mpy C code, micropython-stage, ucglib) died on this, not on speed · H (mine), from
  PO-5, PO-6, PO-10 · supports only: the bet is about value and viability more than feasibility. PO-2 and PO-3 show
  feasibility.
- PO-13 · Cheapest tests, each with a pass line written today, 2026-11-02, before any result (proposals, the decider
  sets the real lines):
  - T1 value, desk, about 1 hour: read MicroPython and CircuitPython GitHub Discussions of the last 12 months for posts
    asking for faster sprites, tiles or text on ESP32 or RP2 colour displays. Proposed pass: 5 or more distinct posters.
    Fewer than 2 means the public part waits until the PO's own games are done.
  - T2 adopt bench, half a day per candidate: run one fixed scene (20 sprites of 16 x 16 with a key colour, a score text
    and a tiled background, moving 120 frames) on the FireBeetle with (a) s3lcd + frame.c + Python today, (b) CircuitPython
    displayio + `_stage`, (c) lvgl_micropython or UIFlow2's User_GFX if it builds for this board. Proposed pass for
    "build": no candidate reaches 33 ms per frame for the scene without new C code.
  - T3 reuse in core, about 10 C lines (H estimate) plus a bench run: let frame.c hand its pixels to Python as a buffer,
    wrap it in `framebuf.FrameBuffer(..., RGB565)`, draw the sprites with `framebuf.blit(..., key)` and the text with
    `framebuf.text`, and mark the frame dirty. Proposed pass: runner paint under 12 ms (P537 slice 2's line). If it
    passes, the first C slice is a small adapter, not a new blit.
  - T4 viability, after P538: publish the one S3 image and README, then count outside issues, forks and stars in 8 weeks.
    Proposed pass: at least 1 outside issue or pull request.
- PO-14 · `_stage` was read in full (render_stage and get_layer_pixel): per output pixel it walks the layers until one is
  not transparent, with 4-bit palette tiles of 16 x 16 and an 8-way orientation switch, and streams into a small buffer
  sent over the bus. It has no framebuffer and composes only the region it is given · E adafruit/circuitpython
  shared-module/_stage/__init__.c and Layer.c, read 2026-11-02 · supports only: the compose loop fits frame.c's dirty
  tiles: compose only the dirty tiles into the internal frame. Speed on the S3 is not measured.

### E. Pre-mortem: "It is six months after the first public release, and it failed. Why?"

Each cause is H (mine) unless its pointer is E. Ordered by how likely I judge it.

- PO-15 · Scope ran ahead of the game. Multi-chip, Arduino, PIE, P4 and Pico work started before the S3 games met 33 ms.
  The MVP slipped. The games stayed at 21 to 24 fps · H. The six wishes on #743 widen the scope (E #743), today's
  rate E bench.md run 22.
- PO-16 · Nobody was able to try it. One image for one board and one panel (P538's done line) meant every other MicroPython user
  had to build firmware (PO-5). Arduino users had LovyanGFX and TFT_eSPI with more panels (PO-10) · E #742 "Done when",
  E PO-5.
- PO-17 · Upstream churn broke the builds. IDF 5.x and MicroPython 1.3x moved headers and APIs. The Arduino-ESP32 core
  changed DMA (TFT_eSPI needed a fix on 2026-02-15). CI built nothing that ran on hardware. So breaks reached users first
  · E PO-6, E research.md §1 (MicroPython master already recommends IDF v5.5.5, v1.29.0 v5.5.2).
- PO-18 · Issues for hardware the maintainer does not own piled up, as in TFT_eSPI (278 open) and s3lcd (11 open, two
  are board requests: #24 "SUNTON 1732S019 …", #25 "Generic ILI9341") · E gh api search/issues.
- PO-19 · The S3-specific gains were small for the cost. P537 projects PIE at 1 to 2 ms per frame. Hand-written `.S`
  per chip became the hardest code to keep, with the fewest testers · E p537-finding.md rank 8 (projection, H).
- PO-20 · The public API changed under its first users. P538 already says "Publishing before that API settles means
  changing it in public" · E #742.
- PO-21 · A licence slip: a GPL piece (Tiny Game Engine, esp-bits-and-pieces) or a font under its own terms was copied,
  and the MIT claim was withdrawn · E PO-8.
- PO-22 · The library stayed welded to the s3lcd fork. s3lcd.c (2927 lines) mixes panel, drawing and Python glue, and
  frame.h includes `py/obj.h` and raises Python errors from C (`frame_config` returns `mp_obj_t`). So the core was not able to
  serve Arduino without a rewrite · E s3lcd/src/frame.h:17 and :82, `wc -l` of s3lcd.c.
- PO-23 · It reimplemented LVGL's draw layer badly. LVGL already had the layers, blending, glyph cache, a P4 PPA unit and
  ST7789 drivers. A plain-C game layer on top of LVGL or LovyanGFX reaches users through their existing
  bindings · H, from E PO-7(b) and the LVGL row.

## What I was not able to check, and why

- Whether a MicroPython dynamic native module (`.mpy`) can call esp_lcd or other ESP-IDF functions. If it can, that removes the
  custom-firmware barrier (PO-5). The natmod docs were not read (search 3 returned only third-party pages). —
- Whether LVGL's software draw functions run usefully without `lv_init` and a display, and at what flash and RAM cost.
  Only the API listing was seen (search 5 summary). —
- displayio, lvgl_micropython or UIFlow2 frame rates on the FireBeetle 2 with the DFR0664. No benchmark found (search 6
  found an older 10 to 14 fps report on another chip, joshondesign.com 2023, not read). Needs a bench (T2). —
- Whether UIFlow2 builds for a non-M5 S3 board with `User_GFX` on custom pins. The board list is M5-only, the build was not
  tried. —
- LovyanGFX internals: whether it has a dirty-region or partial-send mechanism. Only the file list was read. —
- Arduino_GFX's sprite and transparency support, bb_spi_lcd beyond its metadata, 32blit beyond P537's survey. —
- The Jet blend kernel's speed: the 90-100 cycles per 16 pixels is the post author's statement, not read from a
  benchmark file. The linked helper is GPL-3.0, Jet's own kernel is MIT, and their relationship is not known. —
- Kitronik ZIP96: the repository name I tried does not exist, not searched further (budget). —
- Real usage numbers (downloads, forum counts) for any library: no analytics, only stars. —
- Whether the Arduino-ESP32 core and MicroPython can share one C++ core built with the same standard (C++17/20/23 flags in
  each build): not read. —

## Questions for the decider

| question | what it decides |
| --- | --- |
| Who is the first release for: your games on the FireBeetle only, or other people too? | the MVP's scope: P537 slices inside the fork, or a public core with bindings first (PO-1, PO-12) |
| Do you accept that MicroPython users must flash our firmware image for their board, with images only for boards we build? | reach and CI cost, whether a natmod spike comes first (PO-5) |
| Do you want the Arduino binding in the MVP, or after the MicroPython games run smoothly? | whether the core must be free of MicroPython types from day one (PO-22), and a second build in CI |
| Shall an adopt bench (T2: CircuitPython displayio + Stage, LVGL or UIFlow2 on the FireBeetle) run before any new C? | build versus adopt, with a measured line (PO-11, PO-13) |
| Do you want the library extracted from working code (P537 slices 0 to 3 first, then a repo), or designed as a repo first? | order of P537 and P539, and when P538 publishes (PO-15, PO-20) |
| Which licences are allowed: MIT only, or also BSD-2/3 and Apache-2.0 with their notices? GPL stays out? | which pieces in the mix table can be ported (PO-8) |
| Which other chips and panels do you own to test on (P4, Pico, other S3 boards)? | which targets can be tested at all, and so which can be promised (PO-18) |
| How many hours a week will you give the project after the public release? | how many targets and bindings to promise (PO-6, PO-12) |
| Does a 1-hour desk count of forum demand (T1) change your plan if it finds few posters? | whether the public part is gated on evidence of other users (PO-9) |

## Searches

| query, verbatim | decision it served | used or not |
| --- | --- | --- |
| MicroPython C module sprite tilemap game engine ESP32-S3 display fast blit | existing first: is there a MicroPython game graphics module we missed | used: led to python-ugame/micropython-stage (then read through gh api) |
| LovyanGFX MicroPython binding generic board ST7789 sprite | adopt LovyanGFX from MicroPython | not used: no LovyanGFX result, the binding was found by reading m5stack/uiflow-micropython instead |
| MicroPython dynamic native module natmod xtensawin graphics framebuffer esp32 .mpy | distribution: can we avoid custom firmware | partly: showed that a framebuf natmod example exists (then read in the micropython repo), the esp_lcd question stays open |
| micropython esp32-s3 st7789 game slow sprites fps "framebuf" forum 2025 | value: is anyone outside blocked | used as weak negative evidence (PO-9) |
| LVGL use draw layer without widgets lv_draw_sw standalone canvas game sprites | adopt LVGL's draw layer | used as H only (PO-11, LVGL row) |
| CircuitPython displayio ESP32-S3 frame rate sprites TileGrid performance slow | adopt CircuitPython on the same board | not used for a number (other chips, not read), kept as a pointer for T2 |
| ESP32-S3 PIE SIMD RGB565 alpha blend sprite blit assembly graphics library | J4: does PIE graphics code exist beyond esp_lvgl_port | used: led to Jet (MIT) and esp-bits-and-pieces (GPL), both then read through gh api (PO-7, PO-8) |
| graphics library same C core Arduino and MicroPython bindings display driver ESP32 RP2040 | is the "both bindings, one core" shape new | not used: no match, PicoSystem and M5GFX were found by reading repos |
| RP2040 RP2350 MicroPython ST7789 PIO DMA C module driver framebuffer | existing for a later Pico target | not used: PicoGraphics' PIO driver was found by reading pimoroni-pico |

9 of 12 searches used. Fetches (not searches): github.com/CubeCoders/Jet/discussions/10, and the GitHub API reads listed in
the pointers.
