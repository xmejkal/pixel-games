# P844: what the engine copies, takes as design, or leaves from 22 frameworks

Spike P844 ([spark #1208](https://github.com/xmejkal/spark/issues/1208)), for the engine epic P841
([spark #1205](https://github.com/xmejkal/spark/issues/1205)). Written on 2026-11-16 from pixel-games master `1d002da`
(engine submodule at `9589dcd`). It sums up three surveys, kept beside it as sources:
[A, screens and apps](survey-a-screens-and-apps.md), [B, small game engines](survey-b-small-game-engines.md) and
[C, architecture, drivers and boards, audio, net](survey-c-architecture-drivers-audio-net.md). The stage numbers are
those of [plan.md](plan.md). Nothing ran on a board for this page. The council's round 1 changed it in four points
(plan.md, Council, changes 15, 16, 40 and 41): no copy, no stage D, the input words and the "handled" rule with P843,
and `gdi.py:16-19`.

> TL;DR
>
> - **We copy no code.** The useful parts are formats and designs. Our MIT repositories can take a design from any
>   license. Our `s3lcd` driver already reads a panel's start-up list, so CircuitPython's table needs no copy.
> - **We reuse MicroPython's own parts as they are.** These are its board folder, `pins.csv`, `espnow`, the encoder,
>   `mpy-cross` and `manifest.py`. All are MIT and already in our toolchain.
> - **Six designs change the plan.** Each lands where it has a reader.
>   - A scene life cycle and a crash rule (UIFlow 2, Flipper Zero, Tildagon), in stage 3b.
>   - Long and repeat presses, knob navigation and a "handled" rule (Flipper Zero, LVGL, Pyxel, InfiniTime), with
>     the app kit P843, their first reader.
>   - A reset-to-launch spike, and a `Switcher` only if it pays (Presto, Thumby Color).
>   - The board as a MicroPython board folder (MicroPython), in stage 7a.
>   - The panel as data with its bus kind and start-up list, and one builder (CircuitPython, esp_lcd), in stage 7b.
>   - The Mac as a named host behind `FrameOutput` (TIC-80, 32blit, Thumby Color), from stage N.
> - **We leave four things.** We leave LVGL inside the engine and asyncio in the frame loop. We also leave node and
>   widget trees and a global event bus. We copy no GPL, LGPL, proprietary or Espressif-only code.
> - **No survey found a plain Python twin of each C part.** So our PEP 399 rule (P838, section 2) stays our own.
>   Godot's servers and Playdate's Lua and C split confirm its shape.

## The words of the table

| Verdict | Means |
| --- | --- |
| **copy** | We copy code or a table into our repository, with its license notice. Only MIT, BSD or Apache-2.0 sources |
| **reuse** | We use a tool, a module or a file format as it is, with no copy into our tree |
| **design** | We write our own code from the idea. Any license allows this, GPL included |
| **leave** | We take nothing, for the reason given |

The rule for a copy: the license must fit our MIT repositories. Never GPL, LGPL, proprietary or Espressif-only code.
A pin number or a register value is a fact, not code: we copy facts freely and cite them (survey C, its rule).

## The table

| Source (license) | Verdict | What we take or leave | Why | Stage |
| --- | --- | --- | --- | --- |
| MicroPython board folder (MIT) | reuse | The file set of `ports/esp32/boards/<BOARD>/`: `board.json`, `mpconfigboard.cmake`, `mpconfigboard.h`, `sdkconfig.board`, `pins.csv`, `manifest.py`, `board.md`. MicroPython 1.29 builds an out-of-tree folder through `BOARD_DIR` (`ports/esp32/Makefile:8-11`) | It is the format our firmware build already reads, so `boards/<board>/` holds a real board definition, not a format of our own. Today `build.sh:15-20` holds these settings | 7a |
| MicroPython `pins.csv` (MIT) | reuse | Rows `NAME,GPIOn`, written by spark beside `pins.py` | An existing format that works with and without spark (P842). Nobody knows yet whether it gives `machine.Pin.board.NAME` on our build (survey C, section 3) | P842 |
| MicroPython `espnow`, `machine.Encoder`, `mpy-cross`, `mpremote` (MIT) | reuse | As they are. `irecv(0)` drained once per frame, no allocation | Built in, free, local | P832, 0b |
| MicroPython `manifest.py` freezing (MIT) | reuse, later | Freeze the `engine` package into the firmware | Saves heap and import time, but each change then needs a flash. Stage 0b's import numbers decide | after 9 |
| CircuitPython board files and ST7789 start-up table (MIT) | design | The start-up table as data: `command, count or DELAY, data...` | Our `s3lcd` already reads a start-up list (`engine/driver/src/s3lcd.c:1389-1410`). A panel's list is a fact from its datasheet, so we copy nothing | 7b |
| CircuitPython board folder and `busdisplay` (MIT) | design | The panel as data (size, offsets, rotation, SPI rate, start-up table) and one shared builder. Bus, panel and scene apart | `gdi.py:16-19` repeats four pins of `pins.py:19-22`, and `lcd.py:33` fixes 240 x 320. A second board becomes a second record | 7b |
| CircuitPython `_stage` (MIT) | design, later | A line compositor of tile layers into a small buffer | A candidate for a fast `paint_static`. The board's RAM or stage 4's paint gate decides | A5 |
| CircuitPython displayio tree | leave | Group, TileGrid, shaders | A call per item in the hot path. Our games paint by hand through fast draws (P838, section 7) | none |
| Pimoroni picographics (MIT) | design | A display chosen by name with default pins and a custom-bus override. `pen_type` changes memory, not the API | Fits the board record. Its 30-case C++ `switch` is the opposite of data, so no code | 7b |
| Pimoroni picovector (no license file) | leave | Nothing | No license means no right to copy | none |
| Pimoroni Presto (MIT) | design | Reset-to-launch: write the next app's name, reset, read it at boot. And `_presto` with a frozen `presto.py`, the same naming as `_engine` and `engine` | A clean heap per app. The naming is an outside example of the PO's decision | S1, 0a |
| TinyCircuits Tiny Game Engine (GPL-3.0) | design | One small display and input header with one file per platform, an SDL build of the same game code, reset-to-switch, docs beside the C | GPL forbids a copy. The shapes fit our hosts and the Switcher | N, 6, S1 |
| Flipper Zero firmware (GPL-3.0) | design | A scene stack with enter, event and exit, and a back event. A stock view sends a number, the scene decides. Press, Release, Short, Long and Repeat per key. An app manifest as data | GPL forbids a copy. Long and Repeat give two buttons and a knob enough words for menus | 3b, P843 |
| InfiniTime (GPL-3.0) | design | An input handler returns "handled". When the screen does not take an event, the system does its default. One live screen at a time | GPL forbids a copy. It keeps the pick and the volume out of every game | P843 |
| UIFlow 2 (MIT) | design | The life cycle `on_launch`, `on_view`, `on_ready`, `on_hide`, `on_exit`, with pause and resume apart from stop. `AppSelector` with next, previous and select | Its `AppBase` (about 50 lines) starts an asyncio task in `on_ready`. Without asyncio little is left to copy, so we write the contract ourselves | 3b, P843 |
| Tildagon badge (MIT) | design | Crash isolation at the scene's edge: a failing app goes back to the launcher with a notice. `update` answers "nothing changed, no redraw". A manifest with needs. An overlay stack that never takes focus | `App.refuse` (`app.py:303-307`) already refuses a failing build: the same rule reaches `step` and `draw`. The redraw answer is for apps only | 3b, P843 |
| LVGL and lv_micropython (MIT) | design, and leave in the engine | Knob navigation: a turn moves the focus, a press selects, a long press goes back. Layers over a screen | LVGL wants to own the display, beside our s3lcd and C draws. Its fork is MicroPython 1.24, ours is 1.29. Later only as an optional widget strategy in the app kit, after a build spike | P843 |
| Pyxel (MIT, Rust) | design | `btnp(key, hold, repeat)`: key repeat lives in the input layer. Hard limits as the game's contract | Rust, so no code. Its MML synth costs CPU our callback lacks (4 Python voices take 9 ms of 16, `bench.md:1397`) | P843, 8 |
| TIC-80 (MIT) | design | A core with no platform: the host passes input in and takes pixels and samples out | One core, many hosts: the board, the Mac stand-in, later the T-Display | N, 6, 9 |
| 32blit SDK (MIT) | design | One game source for three hosts (STM32, SDL, Pico). A profiler as an engine part | Matches `FrameStats` and the Mac host. Its table of function pointers is not needed: our games are Python modules | N, 6 |
| PICO-8 (proprietary) | design | `_init`, `_update`, `_draw` is the whole game contract | Our `setup`, `play`, `paint` already match. Nothing to copy | 8 |
| Playdate SDK (Panic SDK License) | design | Script for the game, C for the hot parts, mixed per function | Confirms our rule. The license forbids a copy | none |
| Arduboy2 (BSD-3-Clause, AVR C++) | design | `nextFrame()` as a one-line pacer. Core, Base and full library as layers | Confirms the hardware, engine and kit layers. AVR code, nothing to copy | 6 |
| Godot servers and MultiplayerPeer (MIT) | design | Servers behind an API under the scene tree. A peer with `poll`, a peer id, three transfer modes, an offline peer. The host holds authority | Confirms the reference and fast rule. Gives the link's `Transport` its shape | P832 |
| Gaffer On Games, and netcode, yojimbo (BSD-3-Clause) | design | The host holds the state, the controller sends inputs. A sequence number and the last few inputs in every packet | UDP and C for many players. We have two boards on ESP-NOW | P832 |
| Espressif esp_lcd (Apache-2.0) | design, already in our driver | A display driver has two parts. The bus moves the bytes and reports the end of a send. The controller knows what the bytes mean | `s3lcd` already splits them: `s3lcd.SPI_BUS` builds the bus (`lcd.py:250-251`, `s3lcd_spi_bus.c`, `s3lcd_i80_bus.c`) and `s3lcd.ESPLCD` the panel. The board's profile names the bus kind | 7b |
| Espressif esp-bsp (Apache-2.0 per board folder) | design, facts | One header of pin names per board, a small API per function. Facts for later boards, cited with file and commit | No LilyGO or T-Display folder exists. Facts go to spark's records, not into our code | 7b, P842 |
| Zephyr devicetree (Apache-2.0) | design | The hardware is data, and a binding says which keys a driver needs. Hardware and software settings in two files | This is P842's split: spark exports the facts, the engine's catalog holds the bindings, a check ties them. No generator of code: spark exports facts, never behaviour | P842 |
| esp-dsp (Apache-2.0) | reuse, later | Filters and FFT as a link in the `_engine` build | A later synth or spectrum can use it (P831's synth.md). Keep Espressif's notice | A later |
| esp_audio_effects (Espressif modified MIT, Espressif chips only) | leave | Nothing in our repositories | Anyone can take a copy from a public MIT repository to a non-Espressif chip. Its license forbids that | none |
| Mozzi (LGPL-2.1) | design | A control rate (per frame) and an audio rate (per block) | Our split already: Python per frame, C per 256-sample block. LGPL forbids a copy | none |
| MicroPython asyncio (MIT) | leave | Not in the frame loop | Task objects and an unknown timer step, for one task. P838 and espnow.md say the same | none |

`S1` is the reset-to-launch spike, and `A1` to `A5` are the acceleration candidates, in plan.md's later stages. The
council's round 1 removed stage D, because `s3lcd` already splits the bus from the panel.

## The notices we keep

No copy is planned. If a later card copies code, this is the rule:

- **CircuitPython's start-up table format** (stage 7b). If we copy a table, or the code that reads it, from
  `ports/espressif/boards/<board>/board.c`, then our file gets the line `SPDX-License-Identifier: MIT` and the source
  file's copyright line. The board's `board.md` names the source URL and commit. A table that we write from the
  panel's datasheet needs no notice, only the citation.

A reuse is not a copy: `espnow`, `machine.Encoder`, `mpy-cross` and the board folder's file names come with the
MicroPython we build. The `BOARD_DIR` folder that we write is our own file in their format. Its `board.md` cites the
format's source: `ports/esp32/boards/ESP32_GENERIC_S3/`, MicroPython v1.29.0, MIT, Damien P. George.

## What the surveys changed in the plan

| Lesson | Its sources | Where in plan.md |
| --- | --- | --- |
| The action map with `pressed`, `held` and the knob's `turn` | Unity, Godot (P838) | Stage 1 |
| Long and repeat presses, the knob as a focus mover, and a "handled" rule for the system actions | Flipper `input.h`, Pyxel `btnp`, LVGL encoder, InfiniTime | P843 |
| The scene life cycle: build, enter, step, leave. Pause and resume with their first caller | UIFlow 2, Flipper | Stage 3b, P843 |
| A failing `step` or `draw` is refused as a failing build is | Tildagon | Stage 3b |
| A `Switcher` strategy, and a spike: reset-to-launch against the switch in one process | Presto, Thumby Color | Spike S1, then a card if it pays |
| The board as a MicroPython board folder | MicroPython | Stage 7a |
| The panel as data with its bus kind and start-up list, and one builder | CircuitPython, picographics, esp_lcd | Stage 7b |
| `FrameOutput` as the host's boundary, with the Mac's stand-in as a named host | TIC-80, 32blit, Thumby Color | Stage N (the host), stage 6 (`FrameOutput`) |
| spark's tool registry chooses the firmware stack. spark's export, the engine's driver catalog, and a contract test between them | Zephyr, esp-bsp, the PO (change 41) | P842 |
| The `Transport` with transfer modes, a peer id and an offline peer. Inputs with a sequence number | Godot, Gaffer, MicroPython `espnow` | P832 |

## What the surveys did not check

- No survey ran code on a board. Every cost number here is from `bench.md` or a source's own README.
- Whether `pins.csv` gives `machine.Pin.board.NAME` on our build (survey C, from memory of the docs).
- What survives `machine.soft_reset()` on the ESP32-S3 with MicroPython 1.29 (survey A). Spike S1 measures it.
- Whether LVGL's binding builds on our 1.29 firmware, and its heap and flash cost on the box (survey A).
- The licenses of esp-bsp folders other than `esp-box-3` (survey C).
- Mozzi's code and Gaffer's later articles were not read (survey C).
