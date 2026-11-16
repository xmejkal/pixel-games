# P844: what the engine copies, takes as design, or leaves from 22 frameworks

Spike P844 ([spark #1208](https://github.com/xmejkal/spark/issues/1208)), for the engine epic P841
([spark #1205](https://github.com/xmejkal/spark/issues/1205)). Written on 2026-11-16 from pixel-games master `1d002da`
(engine submodule at `9589dcd`). It sums up three surveys, kept beside it as sources:
[A, screens and apps](survey-a-screens-and-apps.md), [B, small game engines](survey-b-small-game-engines.md) and
[C, architecture, drivers and boards, audio, net](survey-c-architecture-drivers-audio-net.md). The stage numbers are
those of [plan.md](plan.md). Nothing ran on a board for this page.

> TL;DR
>
> - **We copy almost no code.** The useful parts are formats and designs. Our MIT repositories can take a design
>   from any license. The one planned copy is small: CircuitPython's start-up table format, for a second panel.
> - **We reuse MicroPython's own parts as they are.** These are its board folder, `pins.csv`, `espnow`, the encoder,
>   `mpy-cross` and `manifest.py`. All are MIT and already in our toolchain.
> - **Six designs change the plan.**
>   - A scene life cycle with pause, resume and a "handled" rule (Flipper Zero, UIFlow 2, InfiniTime).
>   - Long and repeat presses and knob navigation in the action map (Flipper Zero, LVGL, Pyxel).
>   - A `Switcher` strategy, with a reset-to-launch spike (Presto, Thumby Color).
>   - The board and the panel as data, with one builder (CircuitPython, MicroPython).
>   - A display driver split into a bus and a controller (esp_lcd).
>   - The Mac as a named host behind `FrameOutput` (TIC-80, 32blit, Thumby Color).
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
| MicroPython board folder (MIT) | reuse | The file set of `ports/esp32/boards/<BOARD>/`: `board.json`, `mpconfigboard.cmake`, `mpconfigboard.h`, `sdkconfig.board`, `pins.csv`, `manifest.py`, `board.md`. MicroPython 1.29 builds an out-of-tree folder through `BOARD_DIR` (`ports/esp32/Makefile:8-11`) | It is the format our firmware build already reads, so `boards/<board>/` holds a real board definition, not a format of our own. Today `build.sh:15-20` holds these settings | 7 |
| MicroPython `pins.csv` (MIT) | reuse | Rows `NAME,GPIOn`, written by spark beside `pins.py` | An existing format that works with and without spark (P842). Nobody knows yet whether it gives `machine.Pin.board.NAME` on our build (survey C, section 3) | P842 |
| MicroPython `espnow`, `machine.Encoder`, `mpy-cross`, `mpremote` (MIT) | reuse | As they are. `irecv(0)` drained once per frame, no allocation | Built in, free, local | P832, 0b |
| MicroPython `manifest.py` freezing (MIT) | reuse, later | Freeze the `engine` package into the firmware | Saves heap and import time, but each change then needs a flash. Stage 0b's import numbers decide | after 9 |
| CircuitPython board files and ST7789 start-up table (MIT) | copy, later | The table format `command, count or DELAY, data...` for a panel's start-up bytes, with CircuitPython's MIT notice and the file's SPDX line | Our s3lcd driver has its own start-up today. The copy waits for a second panel | 7, D |
| CircuitPython board folder and `busdisplay` (MIT) | design | The panel as data (size, offsets, rotation, SPI rate, start-up table) and one shared builder. Bus, panel and scene apart | `gdi.py:15-19` repeats four pins of `pins.py:19-22`, and `lcd.py:33` fixes 240 x 320. A second board becomes a second record | 7 |
| CircuitPython `_stage` (MIT) | design, later | A line compositor of tile layers into a small buffer | A candidate for a fast `paint_static`. The board's RAM or stage 4's paint gate decides | A5 |
| CircuitPython displayio tree | leave | Group, TileGrid, shaders | A call per item in the hot path. Our games paint by hand through fast draws (P838, section 7) | none |
| Pimoroni picographics (MIT) | design | A display chosen by name with default pins and a custom-bus override. `pen_type` changes memory, not the API | Fits the board record. Its 30-case C++ `switch` is the opposite of data, so no code | 7 |
| Pimoroni picovector (no license file) | leave | Nothing | No license means no right to copy | none |
| Pimoroni Presto (MIT) | design | Reset-to-launch: write the next app's name, reset, read it at boot. And `_presto` with a frozen `presto.py`, the same naming as `_engine` and `engine` | A clean heap per app. The naming is an outside example of the PO's decision | 3b spike, 0a |
| TinyCircuits Tiny Game Engine (GPL-3.0) | design | One small display and input header with one file per platform, an SDL build of the same game code, reset-to-switch, docs beside the C | GPL forbids a copy. The shapes fit our hosts and the Switcher | 6, 3b spike |
| Flipper Zero firmware (GPL-3.0) | design | A scene stack with enter, event and exit, and a back event. A stock view sends a number, the scene decides. Press, Release, Short, Long and Repeat per key. An app manifest as data | GPL forbids a copy. Long and Repeat give two buttons and a knob enough words for menus | 1, 3b, P843 |
| InfiniTime (GPL-3.0) | design | An input handler returns "handled". When the screen does not take an event, the system does its default. One live screen at a time | GPL forbids a copy. It keeps the pick and the volume out of every game | 3b |
| UIFlow 2 (MIT) | design | The life cycle `on_launch`, `on_view`, `on_ready`, `on_hide`, `on_exit`, with pause and resume apart from stop. `AppSelector` with next, previous and select | Its `AppBase` (about 50 lines) starts an asyncio task in `on_ready`. Without asyncio little is left to copy, so we write the contract ourselves | 3b, P843 |
| Tildagon badge (MIT) | design | Crash isolation at the scene's edge: a failing app goes back to the launcher with a notice. `update` answers "nothing changed, no redraw". A manifest with needs. An overlay stack that never takes focus | `App.refuse` (`app.py:303-307`) already refuses a failing build: the same rule reaches `step` and `draw`. The redraw answer is for apps only | 3b, P843 |
| LVGL and lv_micropython (MIT) | design, and leave in the engine | Knob navigation: a turn moves the focus, a press selects, a long press goes back. Layers over a screen | LVGL wants to own the display, beside our s3lcd and C draws. Its fork is MicroPython 1.24, ours is 1.29. Later only as an optional widget strategy in the app kit, after a build spike | 1, P843 |
| Pyxel (MIT, Rust) | design | `btnp(key, hold, repeat)`: key repeat lives in the input layer. A design policy with decision records. Hard limits as the game's contract | Rust, so no code. Its MML synth costs CPU our callback lacks (4 Python voices take 9 ms of 16, `bench.md:1397`) | 1, 0b, 8 |
| TIC-80 (MIT) | design | A core with no platform: the host passes input in and takes pixels and samples out | One core, many hosts: the board, the Mac stand-in, later the T-Display | 6, 9 |
| 32blit SDK (MIT) | design | One game source for three hosts (STM32, SDL, Pico). A profiler as an engine part | Matches `FrameStats` and the Mac host. Its table of function pointers is not needed: our games are Python modules | 6 |
| PICO-8 (proprietary) | design | `_init`, `_update`, `_draw` is the whole game contract | Our `setup`, `play`, `paint` already match. Nothing to copy | 8 |
| Playdate SDK (Panic SDK License) | design | Script for the game, C for the hot parts, mixed per function | Confirms our rule. The license forbids a copy | none |
| Arduboy2 (BSD-3-Clause, AVR C++) | design | `nextFrame()` as a one-line pacer. Core, Base and full library as layers | Confirms the hardware, engine and kit layers. AVR code, nothing to copy | 6 |
| Godot servers and MultiplayerPeer (MIT) | design | Servers behind an API under the scene tree. A peer with `poll`, a peer id, three transfer modes, an offline peer. The host holds authority | Confirms the reference and fast rule. Gives the link's `Transport` its shape | P832 |
| Gaffer On Games, and netcode, yojimbo (BSD-3-Clause) | design | The host holds the state, the controller sends inputs. A sequence number and the last few inputs in every packet | UDP and C for many players. We have two boards on ESP-NOW | P832 |
| Espressif esp_lcd (Apache-2.0) | design | A display driver has two parts. The bus moves the bytes and reports the end of a send. The controller knows what the bytes mean. The start-up table is data | Today `s3lcd` does both in one C file (`engine/driver/src/s3lcd.c`). The split is for a second display, not now | D |
| Espressif esp-bsp (Apache-2.0 per board folder) | design, facts | One header of pin names per board, a small API per function. Facts for later boards, cited with file and commit | No LilyGO or T-Display folder exists. Facts go to spark's records, not into our code | 7, P842 |
| Zephyr devicetree (Apache-2.0) | design | The hardware is data, and a binding says which keys a driver needs. Hardware and software settings in two files | This is P842's split: spark exports the facts, the engine's catalog holds the bindings, a check ties them. No generator of code: spark exports facts, never behaviour | P842 |
| esp-dsp (Apache-2.0) | reuse, later | Filters and FFT as a link in the `_engine` build | A later synth or spectrum can use it (P831's synth.md). Keep Espressif's notice | A later |
| esp_audio_effects (Espressif modified MIT, Espressif chips only) | leave | Nothing in our repositories | Anyone can take a copy from a public MIT repository to a non-Espressif chip. Its license forbids that | none |
| Mozzi (LGPL-2.1) | design | A control rate (per frame) and an audio rate (per block) | Our split already: Python per frame, C per 256-sample block. LGPL forbids a copy | none |
| MicroPython asyncio (MIT) | leave | Not in the frame loop | Task objects and an unknown timer step, for one task. P838 and espnow.md say the same | none |

`D` is the display drivers stage, after the second display is chosen, and `A1` to `A5` are the acceleration
candidates, in plan.md's later stages.

## The notices we keep

Only one copy is planned, and it waits for a second panel:

- **CircuitPython's start-up table format** (stage 7 or D). If we copy a table, or the code that reads it, from
  `ports/espressif/boards/<board>/board.c`, then our file gets the line `SPDX-License-Identifier: MIT` and the source
  file's copyright line. The board's `board.md` names the source URL and commit. A table that we write from the
  panel's datasheet needs no notice, only the citation.

A reuse is not a copy: `espnow`, `machine.Encoder`, `mpy-cross` and the board folder's file names come with the
MicroPython we build. The `BOARD_DIR` folder that we write is our own file in their format. Its `board.md` cites the
format's source: `ports/esp32/boards/ESP32_GENERIC_S3/`, MicroPython v1.29.0, MIT, Damien P. George.

## What the surveys changed in the plan

| Lesson | Its sources | Where in plan.md |
| --- | --- | --- |
| Long and repeat presses, and the knob as a focus mover, in `Actions` | Flipper `input.h`, Pyxel `btnp`, LVGL encoder | Stage 1 |
| The scene life cycle: build, enter, step, pause, resume, leave, with a "handled" rule for the system actions | UIFlow 2, Flipper, InfiniTime | Stage 3b |
| A failing `step` or `draw` is refused as a failing build is | Tildagon | Stage 3b |
| A `Switcher` strategy, and a spike: reset-to-launch against the switch in one process | Presto, Thumby Color | Stage 3b, spike S1 |
| The board as a MicroPython board folder, and the panel as data with one builder | MicroPython, CircuitPython, picographics | Stage 7 |
| `FrameOutput` as the host's boundary, with the Mac's stand-in as a named host | TIC-80, 32blit, Thumby Color | Stage 6 |
| A display driver split into bus and controller | esp_lcd | Stage D |
| spark's export, the engine's driver catalog, and a check between them | Zephyr, esp-bsp | P842 |
| The `Transport` with transfer modes, a peer id and an offline peer. Inputs with a sequence number | Godot, Gaffer, MicroPython `espnow` | P832 |
| A design-decisions folder beside the package's README | Pyxel | Stage 0b |

## What the surveys did not check

- No survey ran code on a board. Every cost number here is from `bench.md` or a source's own README.
- Whether `pins.csv` gives `machine.Pin.board.NAME` on our build (survey C, from memory of the docs).
- What survives `machine.soft_reset()` on the ESP32-S3 with MicroPython 1.29 (survey A). Spike S1 measures it.
- Whether LVGL's binding builds on our 1.29 firmware, and its heap and flash cost on the box (survey A).
- The licenses of esp-bsp folders other than `esp-box-3` (survey C).
- Mozzi's code and Gaffer's later articles were not read (survey C).
