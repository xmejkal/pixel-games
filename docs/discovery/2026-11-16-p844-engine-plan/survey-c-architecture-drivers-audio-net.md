# Survey C: engine architecture, drivers and boards, audio, multiplayer

A source of P844's [synthesis](synthesis.md) and [plan](plan.md), kept as the survey agent wrote it on 2026-11-16.

Spike P844 (spark #1208), part C. Written 2026-11-16. Read first: the card, #1205 (engine epic), #1206 (P842), and
P838's finding (`docs/discovery/2026-11-16-p838-engine-layer/finding.md`, TL;DR and sections 2 to 6), plus the P831
synth note. Licenses come from each repository's LICENSE file (read through `gh api`, 2026-11-16). "Read" means I
read the page or file. "Not read" means I name it from the card or from memory and say so.

Our repositories are MIT. Rule used here: copy code only from MIT, BSD or Apache-2.0 sources, with the notice kept.
A pin number or a register value is a fact, not code. Copy facts freely, and cite them.

## 1. Godot (design only)

- What: a 2D/3D game engine. License: MIT (`LICENSE.txt`; master `4d0d43b77`, 2026-11-14).
- Servers. Low-level APIs for rendering, physics and sound. The scene tree sits on top of them and calls them. They
  use opaque RID handles ([Using servers](https://docs.godotengine.org/en/stable/tutorials/performance/using_servers.html), stable docs, read).
  Take: this is the same shape as our rule "a reference and a fast version behind one interface". The server is the
  interface. The nodes are the convenience layer. It confirms that games should never hold the fast object's
  internals, only an interface plus a handle.
- Scenes and nodes. Not our case. We have 15 small games, not a node tree. P838's `Scene`/`SceneManager` already
  matches Godot's `SceneTree.change_scene` idea. Leave nodes: a node tree costs RAM on a 320 KB-heap-class board
  (inference, not measured).
- MultiplayerPeer. An abstract transport with `poll()`, `set_target_peer`, `get_packet_peer`, a unique id, and three
  transfer modes: unreliable, unreliable ordered, reliable. Implementations: ENet, WebSocket, WebRTC, offline. A
  custom peer plugs in by assigning it to the API
  ([High-level multiplayer](https://docs.godotengine.org/en/stable/tutorials/networking/high_level_multiplayer.html), read;
  [MultiplayerPeer.xml](https://github.com/godotengine/godot/blob/master/doc/classes/MultiplayerPeer.xml), read).
  By default the server (peer id 1) holds authority over a node. RPC modes are "authority" and "any_peer".
  Take as design: our `Transport` interface (stage "link") offers the same three modes, a poll call, a peer id, and
  an offline/loopback peer for tests. Take "the host has authority; a client only sends input". Leave RPC,
  spawner and synchronizer: they need reflection we do not have.
- Copy as code: nothing. C++ in a different shape. (MIT would allow it, but there is nothing to copy.)

## 2. Espressif esp-bsp and esp_lcd

esp-bsp (https://github.com/espressif/esp-bsp, master, pushed 2026-11-13).
- What: one folder per board under `bsp/` (about 25: esp-box-3, esp-box-lite, esp32_s3_eye, esp32_s3_korvo_2,
  m5stack_core_s3, m5dial, m5_atom_s3, esp_bsp_devkit, esp_bsp_generic, and more). No LilyGO or Waveshare T-Display
  board is in the list, so none of our two boards has a ready BSP.
- What a board holds (read: `bsp/esp-box-3/include/bsp/esp-box-3.h`, `esp-box-3.c`, `idf_component.yml` v3.2.1):
  - A header of `#define BSP_LCD_*`, `BSP_I2S_*`, `BSP_SD_SPI_*`, `BSP_POWER_AMP_IO` pin names with GPIO numbers.
  - A small API per function: `bsp_display_new()`, `bsp_audio_init()`, `bsp_audio_codec_speaker_init()`, SPIFFS
    mount, buttons, LED.
  - `Kconfig` options per board, `idf_component.yml` for dependencies and chip target, and a `LICENSE` file.
  - The display code builds an `esp_lcd` panel io, then a panel by controller (`esp_lcd_new_panel_st7789` or
    ili9341), with a vendor init command table for the ones that need it.
  - The audio code builds an I2S bus and an ES8311 codec through `esp_codec_dev`. Our box has no codec: it is a
    MAX98357 amplifier on plain I2S, so that part does not apply.
- License: no root LICENSE (GitHub says NOASSERTION). Each BSP folder has its own LICENSE: `bsp/esp-box-3/LICENSE` is
  Apache-2.0 and the source files carry `SPDX-License-Identifier: Apache-2.0`. Apache-2.0 is fine for an MIT repo if
  we keep the notice and mark changes. Check each folder before copying from it.
- Copy as code: no. It is ESP-IDF C on top of esp_lcd, and our display goes through s3lcd. We could copy a vendor
  init command table (an array of bytes) with the notice, but our s3lcd driver already has its own.
- Facts to feed our `boards/` folders: only for boards that appear there. For our own two boards: none. For
  later boards (an ESP-BOX-3, an M5 board): the header gives pins, panel controller, I2S pins, and the amp enable
  pin, each citable with the file and commit. Use as a source for spark's part and board records, not as a
  runtime dependency.
- Take as design: (1) one header per board with names, never numbers, in game code; (2) a small API per function
  (display, audio, input) that main.py calls once; (3) per-board option file. This is the same as our `boards/<board>/`.
- Leave: LVGL port, codec dev, the touch and camera parts (not our hardware).

esp_lcd (ESP-IDF, Apache-2.0, https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/lcd/index.html, read).
- Two layers. A panel IO is the transport (SPI, I2C, i80, RGB, MIPI DSI) that sends commands and pixel data and
  reports completion by callback. A panel is the controller (ST7789 is built in) with reset, init, draw, mirror,
  swap axes, gap, invert, on/off. Vendor init commands are sent through the IO handle between init and display-on.
- Take as design: our `drivers/display/` interface splits the same way: a bus (what moves bytes, with a done
  callback) and a controller (what the bytes mean), plus the panel's init table as data in `boards/<board>/`.
  Today `s3lcd` does both in one C file (`engine/driver/src/s3lcd.c`), so the split is a design target for a second
  display, not a thing to do now.
- Leave: the C API itself. We are MicroPython and use s3lcd.

## 3. MicroPython boards, pins.csv, machine

MicroPython (https://github.com/micropython/micropython, MIT, `LICENSE`, "Copyright (c) 2013-2026 Damien P. George";
master `350908ad3`, 2026-11-16).
- Board folder (read): `ports/esp32/boards/<BOARD>/` holds `board.json` (name, mcu, vendor, features list, images,
  variants, deploy offset), `mpconfigboard.h` (board name, default I2C/SPI/SD pins as `MICROPY_HW_*`, UART REPL
  switch), `mpconfigboard.cmake` (sdkconfig fragments, variants), optional `sdkconfig.board`, `manifest.py`
  (frozen modules), `modules/` (board-specific Python), `pins.csv` (names to GPIO), and `board.md` (docs).
  Example: `LILYGO_T3_S3` has all of these. A shared `mpconfigboard_esp32s3_common.cmake` holds what all S3 boards share.
- `pins.csv`: lines `NAME,GPIOn`, for example `I2C_SCL,GPIO8`, `SPI_MOSI,GPIO35` (`UM_TINYS3/pins.csv`, read). The build
  turns it into `machine.Pin.board.NAME`, so game code says `Pin(Pin.board.I2C_SCL)` and never a number.
  (Pin.board is from memory of the docs, not read here. Check before relying on it.)
- Comments in `mpconfigboard.h` of LILYGO_T3_S3 cite the schematic ("Verified: schematic T3S3_V1.2"). That is the
  same habit as spark's cited facts.
- machine driver model: one class per bus (`Pin`, `I2S`, `SPI`, `Pin` with `irq`, `Counter`/`Encoder` for the
  pulse counter), constructed with pins by the caller. There is no registry and no device description. Take: our
  drivers take pins as constructor arguments (P838 already says this). Leave: nothing to add, it is the plain model.
- Copy as code: MIT allows it. The directory layout and file names are the thing to copy, and a `board.json`-style
  file with `features`. Copy the format, not their pins.
- asyncio in MicroPython: see section 8.

## 4. Zephyr devicetree and drivers (design only)

Zephyr (https://github.com/zephyrproject-rtos/zephyr, Apache-2.0, `LICENSE`; main, pushed 2026-11-14).
- Devicetree says what hardware exists and its initial configuration. Bindings describe what a node may contain,
  with data types. The build makes a C header from them, and drivers read it through `DT_` macros
  ([intro](https://docs.zephyrproject.org/latest/build/dts/intro-scope-purpose.html), read, short). Kconfig is the
  separate way to choose software features.
- Take as design: the split "hardware description is data, drivers read it" and "a binding is a schema for a node".
  This is exactly P842's division. Spark exports the node (pins, panel, I2S rate). The engine's catalog holds the
  binding (which driver accepts which part, and which keys it needs). A check compares the two.
  Also take: hardware (devicetree) and software features (Kconfig) are two separate files. For us:
  `boards/<board>/` data versus `engine_config.py` (REFERENCE set).
- Leave: the DTS syntax, the C macros, the overlay system, and any generator that makes code. Spark exports facts,
  never behaviour. A JSON or `pins.py`-style data file is enough.
- Copy as code: nothing. Apache-2.0 would allow it, but there is nothing small to copy.

## 5. Espressif audio: esp_audio_effects, esp-dsp

esp-dsp (https://github.com/espressif/esp-dsp, Apache-2.0, `LICENSE` read; pushed 2026-05-11).
- Filters, FFT and vector math as an ESP-IDF component. Already assessed in P831's `synth.md` (biquad 17552 cycles per
  1024 samples on S3, FFT fast). Fit: usable as a build-time link in the firmware, not copied into our tree. A
  biquad coefficient maker is small enough to write from the textbook (RBJ cookbook) in our own C instead.
- Verdict: keep as an optional dependency of the C `_engine`, for a spectrum bar or a filter, later. Not for the
  engine's first stages. If used, we keep Espressif's notice.

esp_audio_effects (https://components.espressif.com/components/espressif/esp_audio_effects, v1.4.5, read).
- ALC, sample-rate and bit-depth conversion, EQ, mixing, fading, DRC, multiband compressor, reverb, delay. Supports
  S3. The registry page links a repository, and the download is a 3.81 MB archive (source or binary not stated).
- License (read, the registry's license page for v1.4.5): "Espressif Modified MIT License", with these conditions:
  "Permission is hereby granted for use EXCLUSIVELY with Espressif Systems products" and redistribution "FOR USE
  WITH NON-ESPRESSIF PRODUCTS is strictly prohibited". Same text in `espressif/esp-gmf` `LICENSE`.
- Meaning for us: it is not MIT and it is not open in the usual sense. Using it on an ESP32-S3 is allowed. Committing
  it, or a copy of its code, into our public MIT repositories is not safe, because anyone could use our copy on a non-Espressif chip.
  We could only add it as a build-time fetch (like a registry dependency), never as a file in the repository,
  and the engine must work without it.
- Leave for the first versions. P831's synth works with a small C voice and our own echo (a ring buffer). This also
  fits "free, few and local": one more component with a special license is a cost to name.

Mozzi (https://github.com/sensorium/Mozzi, LGPL-2.1 or later per `LICENSE.TXT`; v2.0.4, 2026-04-14).
- Synthesis library for Arduino. The README lists ESP32 and ESP32-S/C/H/P boards, with I2S out. Read from the
  README: "You may distribute *your own* source code which merely *uses* the Mozzi-API under any licence".
- License fit: LGPL-2.1 is not MIT. Copying its code into an MIT repo would put that code under LGPL. It is also
  an Arduino C++ library, and our engine is MicroPython with a C module. Do not copy.
- Take as design (from its README and general knowledge, the code not read): the split into a control rate (a slow
  function that reads inputs and sets parameters) and an audio rate (a fast function that makes one sample), with
  fixed-point oscillators, wavetables, ADSR and filters as small objects. Our split is the same: Python once per
  frame passes numbers, C renders a 256-sample block. It supports P831's chosen shape. Leave: the library itself.

## 6. Networking for two boards

Gaffer On Games, "What Every Programmer Needs To Know About Game Networking" (Glenn Fiedler, 2010-02-24,
https://gafferongames.com/post/what_every_programmer_needs_to_know_about_game_networking/, read).
- Three models: deterministic lockstep (all machines run the same simulation, only commands are sent), client/server
  with interpolation (the server holds the state and sends updates), and client-side prediction with correction.
- Content license: the articles are not a code license. Fiedler's code is in `mas-bandwidth/netcode`,
  `yojimbo` and `reliable`, all BSD-3-Clause (`netcode` LICENCE read, pushed 2026-11-12). They are C and UDP-over-IP,
  built for internet games with many players. We have two boards on ESP-NOW. Copy nothing. Design only.
- For our case (a second board with buttons and a knob, the host runs the game): the second board is a controller.
  This is the simplest model: the host holds all state, the controller sends inputs, nothing predicts. If the
  second board also shows the game, the host sends the screen state or a small snapshot and the second board only
  draws. Lockstep is the wrong fit: it needs determinism on both boards, and our games use time and a random draw.
  (Inference. The PO decides "controller or also screen", open in #1205.)
- The one detail to take (inference, standard practice, not read on his pages): put a sequence number in each packet
  and repeat the last few inputs in every packet. Then one lost packet loses nothing and no resend code is needed.

MicroPython ESP-NOW (https://docs.micropython.org/en/latest/library/espnow.html, latest docs, read).
- Built into MicroPython as `espnow`, MIT (it is part of the MicroPython tree). No outside library is needed.
- Facts: payload 250 bytes (ESP-NOW v1) or 1470 (v2), `espnow.MAX_DATA_LEN` at run time. Up to 20 peers, 6 encrypted.
  Peers must be added with `add_peer()` before `send()`. `send(mac, msg, sync=True)`, `recv(timeout_ms)`,
  `irecv()` (reuses buffers, no allocation), `recvinto`, `any()`, an `irq` callback. Wi-Fi power saving makes receive
  unreliable (`sta.config(pm=sta.PM_NONE)`). Both peers must share a channel. A full buffer drops packets, and the
  sender still gets an ack, so an ack is not proof of use. `recv()` allocation can fragment memory.
- asyncio: `aioespnow.AIOESPNow` with `arecv`, `airecv`, `asend`, `async for`.
- The docs name ESP32 in general, not S3 in particular. Not run by me on an S3.
- Take: our `Transport` interface wraps `espnow` with `irecv(0)` drained once per frame (no allocation, no asyncio
  needed) and a sequence number. A fake transport (two queues) for the Mac tests. Copy as code: nothing needed.

## 7. Where each one lands in our plan

| Source | Our stage or layout | What we take |
| --- | --- | --- |
| MicroPython board folder, pins.csv | `boards/<board>/` and P842 | the file set and `NAME,GPIOn` rows |
| esp_lcd | `drivers/display/` | bus and controller split, init table as data |
| esp-bsp | `boards/` and spark board records | per-board header names and facts to cite for later boards |
| Zephyr devicetree | P842 | hardware as data, a binding schema, a check that ties them |
| Godot servers | the reference/fast rule (P838 section 2) | confirms it |
| Godot MultiplayerPeer | stage "link" (P832) | transfer modes, authority, an offline peer |
| MicroPython espnow | stage "link" | the real limits above, `irecv(0)` once per frame |
| Gaffer | P832 | controller-only first, sequence number and repeated inputs |
| esp-dsp | later, `_engine` optional | biquad and FFT, as a build link |
| esp_audio_effects | leave | license is Espressif-only |
| Mozzi | design only | control rate and audio rate, matches P831 |

## 8. asyncio as the frame loop

- What: MicroPython's `asyncio` is `extmod/asyncio` (MIT, same repo). Its core is pure Python: a task heap queue, a
  poller, and `ticks_ms` time (`extmod/asyncio/core.py`, read: `run_until_complete` picks the head of
  `_task_queue`, computes `dt` from `ticks_diff`, and polls).
- Cost on ESP32-S3: I found no measurement for the S3 on 1.29. Old reports (search results, not primary): a task
  switch near 200 microseconds on a pyboard-era uasyncio, and on ESP32 sleep times of 30 and 50 ms for a 20 and
  40 ms request, caused by a 10 ms tick. Those reports may be out of date. I did not confirm them. Treat both as unknown.
- Why it does not fit the frame loop: our frame is one fixed step with a measured budget (about 40 ms, a frame
  stage list, a gc policy). Every frame allocates nothing by design. A scheduler adds heap work (task objects, queue
  pushes) and an unknown timer granularity, for no gain, because the game logic has one task. Leave it.
- Where it can fit: the `link` receive path if the PO wants it (`aioespnow`), run beside the frame loop. But
  draining `irecv(0)` once per frame is simpler and costs nothing extra. Recommendation: no asyncio in the engine's
  first versions. If someone wants it, one probe measures `ticks_us` around a yielding loop on the S3 (about 10
  lines), as the spark rule says: write a count only after you saw the output.

## 9. Ranked: the three most useful for our engine

1. MicroPython's board folder and `pins.csv` (MIT; copy the shape, and the `NAME,GPIOn` rows).
   Fits: the drivers-and-boards layout, and P842's spark division. Make `boards/<board>/` hold `board.json`
   (mcu, features), a pins file, the sdkconfig fragment and `board.md`. Have spark export its pin facts as
   `pins.csv` rows next to `pins.py`, with the schematic note as a comment. The same file then works with or
   without spark, and a MicroPython firmware build can read it as `Pin.board`. It is a format that already exists,
   which is the "reuse before inventing" rule.
2. esp_lcd's two layers, with Zephyr's "hardware is data, a binding says what a driver accepts".
   Fits: stage 7 (the hardware description) and `drivers/`, plus P842's check. A display driver is a bus plus a
   controller, and the panel's init table is data in `boards/<board>/`. The engine's catalog holds one binding per
   driver (keys it needs). The spark check says "the board has a part the catalog has no driver for". Apache-2.0
   sources, design only, so no license cost.
3. A small `Transport` interface after Godot's MultiplayerPeer, over MicroPython's built-in `espnow`.
   Fits: the `link` stage of P832 (multiplayer built inside the engine). Three transfer modes, a poll, a peer id,
   an offline or fake peer for Mac tests. The host holds authority, the second board is a controller first (sends
   inputs with a sequence number and the last few inputs repeated), and it drains `irecv(0)` once per frame. Real
   limits to design for: 250 bytes (v1) or 1470 (v2), 20 peers, no radio power saving, a shared channel, and an ack
   that does not prove use.

Not in the top three, but noted: do not adopt Mozzi (LGPL) or esp_audio_effects (Espressif-only license) into the
repositories. Keep asyncio out of the frame loop until a probe shows a gain.

## 10. What I did not do

- No code ran on a board. No S3 timing for asyncio or ESP-NOW was measured.
- I did not read Mozzi's source, Gaffer's later articles, or the `Pin.board` docs. I flagged each such claim.
- I read the license of esp-bsp's esp-box-3 folder only. Other BSP folders may differ.
