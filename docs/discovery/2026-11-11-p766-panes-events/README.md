# P766: panes, events and listeners (finding for spark issue 1055)

Date: 2026-11-11. This is a finding with sources. It is not a design. Tags: [source] says what a page says,
[repo] says what the code shows, [inference] is my own reasoning. "Not confirmed" marks what I could not check.

## Short version

- Q1. Standard systems keep a tree of objects, send events to listeners, and redraw only marked areas. LVGL's events page,
  Godot and Game Programming Patterns are read. LVGL's display and input-device pages are not. Use direct listeners for state
  changes, and a small queue only where the sender must not wait (interrupts, radio).
- Q2. The official rule for interrupts is: short code, no heap allocation, use micropython.schedule. No timing numbers
  for a Python call or a callback were found. Measure them on the board.
- Q3. S3 has a second core, LCD_CAM and PIE. P4 adds the PPA (scale, rotate, mirror, blend), MIPI-DSI and 2D-DMA.
  Keep the blit, the blend and the fill behind swappable parts. MicroPython has an ESP32-P4 port (stable v1.29.0). A binding for the PPA is not confirmed.
- Q4. One system can hold buttons, knob, values, game state, timers, sound level and radio messages. ESP-NOW works in
  MicroPython on ESP32 with both polling and a callback.
- Gaps: LVGL's display and encoder pages, MicroPython call costs, a PPA binding, input events in Godot or Unity.

## 1. How the standard systems do it

[repo] Today a pane compares a value in each frame. VolumePane.update (games/overlay.py) tests `volume.step !=
self.seen`. The game box polls the knob in each frame (games/app.py, lines 96-97). The title and the game over are
drawn by each game: Game.draw_title and draw_over in games/gfx.py (about line 397). Canvas.keep (games/gfx.py,
line 87) redraws a kept strip only when its key changes. App.frame names its stages after Unity (app.py line 89).

| Option | What it is | Cost or risk | Fit here | Source |
|---|---|---|---|---|
| Object tree, dirty areas | Parent and child objects. Change marks area | Cost not on the page | Like render.Dirty | [1] |
| Signals (observer) | Object emits. Listeners connect | Sender waits for listeners | Good for values | [2], [3] |
| Event queue | Events wait in a ring buffer. A loop reads them | Stale data, hidden loops | Good for interrupts | [3] |
| Poll in each frame | The frame reads each source | Work each frame. A tap can fall between | Works now | [repo] |

- [source] Godot: "signals are Godot's version of the observer pattern". Signals let one node react to another
  without a reference to it. Connect with `connect()`, send with `emit()`. [2] (sections: See also, Connecting a
  signal via code, Custom signals).
- [source] Event queue chapter: "You only need a queue when you want to decouple something in time." Queues are "a
  poor fit when the sender needs a response". A central queue is a global variable. Receivers must not assume the
  world is unchanged. Queues hide feedback loops. A ring buffer avoids allocation. [3] (sections: When to Use It,
  Keep in Mind, A Ring Buffer).
- [source] LVGL 9.5, events page, read after the first pass. A callback joins a widget with
  `lv_obj_add_event_cb(btn, my_event_cb, LV_EVENT_CLICKED, user_data)`: one object, one event code as a filter, and
  the caller's data. A widget takes several callbacks: "The events will be called in the order as they were added."
  [1] (section: Adding Events to a Widget)
- [source] LVGL: an event goes to the parent only by choice: "If lv_obj_add_flag(widget, LV_OBJ_FLAG_EVENT_BUBBLE)
  is enabled all events will be sent to a Widget's parent as well." A changed value has its own code,
  `LV_EVENT_VALUE_CHANGED` ("Widget's value has changed (i.e. slider moved)"). [1]
- [source] LVGL: "Besides Widgets, events can be registered for displays and input devices as well"
  (`lv_display_add_event_cb`, `lv_indev_add_event_cb`). The display sends `LV_EVENT_INVALIDATE_AREA` ("An area is
  invalidated (marked for redraw)") and `LV_EVENT_REFR_REQUEST`. During a draw, a change to a widget is forbidden. [1]
- [inference] LVGL matches the split below: the same callback form for widgets, the display and the inputs, a filter
  by event code, a redraw that follows marked areas, and no state change in the draw stage.
- Not confirmed: LVGL's display page (how areas join and flush) and its input-device page (the encoder). Not read.
  The first pass's fetches of docs.lvgl.io failed: the pages moved to lvgl.io/docs/open.
- Not confirmed: Unity's event system. I used Godot only, as the task allows one engine.
- Recommendation: [inference] split by timing. A state change (volume step, game state) fits a direct listener that
  runs in the frame, with the value captured in the event. An interrupt or radio source fits a ring buffer that the
  frame drains. This follows [3] and keeps feedback loops visible.

## 2. What fits MicroPython at 40 ms with the sound at its limit

[repo] The refill callback is at its time limit (task text, gap over 48 ms is late). MasterVolume says set() and
apply() each store one int, so a callback between two bytecodes sees a whole value (games/volume.py docstring).
[repo] Button.watch counts edges in a pin interrupt, and update() reads the counter in the frame (games/buttons.py,
lines 29-43). The comment there says the interrupt is a soft interrupt, run after the current C call.

| Option | What it is | Cost or risk | Fit here | Source |
|---|---|---|---|---|
| Plain call to listeners | Frame calls each bound method | Call cost not confirmed | Fine if short | none |
| Allocation in a callback | New object in a handler | Heap allocation not re-entrant | Never in interrupts | [4] |
| micropython.schedule | Runs a function when heap is free | Queue size not confirmed | Exit from an interrupt | [4] |
| Ring buffer of ints | Fixed storage, no growth | Needs a size and a full rule | Interrupts, refill | [3], [4] |

- [source] Interrupt rules: "Keep the code as short and simple as possible." "Avoid memory allocation: no appending
  to lists or insertion into dictionaries, no floating point." Allocate an emergency buffer with
  `micropython.alloc_emergency_exception_buf(100)`. Scheduled callbacks are queued "at a time when the heap is not
  locked". "Altering the contents of an array or bytearray is safe", but adding keys to a dict can rehash. Disabling
  interrupts is "the usual and simplest way" for a critical section. [4] (sections: tips, creation of Python objects,
  use of Python objects, critical sections, using micropython.schedule).
- [source] The page gives no time limit for an interrupt handler. It says only to return in "a short, predictable
  period of time". [4]
- [repo] A cost the repo measured: gc.mem_free() "costs about 20 ms per MB allocated" (games/app.py, line 114). The
  loop turns the gc off with PSRAM and collects every 5 frames (GC_FRAMES).
- Not confirmed: the cost of a Python call, of a bound method, and of an allocation. I did not search for them
  (limit reached). Also not confirmed: the size of the schedule queue. Measure on the board with time.ticks_us.
- Recommendation: [inference] the refill callback and interrupts never call listeners. They write ints into
  preallocated storage. The frame reads that storage and then calls listeners. This is the pattern the repo already
  uses in MasterVolume and Button. Keep the listener lists short and fixed after start.

## 3. Hardware

| Option | What it is | Cost or risk | Fit here | Source |
|---|---|---|---|---|
| S3 pulse counter | Counts encoder edges in hardware | None new | Already used | [5] |
| S3 LCD_CAM | 8 or 16 bit parallel LCD bus, GDMA, 40 MHz or less | New wiring or C driver | Later | [5] |
| S3 PIE (SIMD) | 128 bit vector instructions | Needs C or assembly | Fill, blend, volume in C | [5] |
| S3 second core | Dual-core LX7, up to 240 MHz | Use from MicroPython not confirmed | Not confirmed | [5] |
| S3 GDMA | 5 send and 5 receive channels, shared | Shared channels | SPI and I2S use it | [5] |
| P4 PPA | Scale, rotate, mirror, blend, fill (2D-DMA) | New C API. Bilinear scale | Pane blend, rotation | [6], [7] |
| P4 MIPI-DSI | 2 data lanes, up to 1.5 Gbps each | Needs a DSI panel | Bigger display later | [8] |
| P4 cores | Dual RISC-V, up to 400 MHz (360 in rev 1.3) | Not Xtensa | Native code rebuilt | [8], [9] |

- [source] The S3 datasheet lists LCD_CAM, 128-bit SIMD and a dual-core CPU. The PIE section lists 128-bit vector
  operations and saturation. [5] (sections: 4.1.1.1 CPU, 4.1.1.2 PIE, 4.1.1.4 GDMA, 4.2.1.4 LCD and Camera).
- [source] The P4 PPA has two parts: SRM (scale, rotate, mirror) and BLEND (alpha blend of two layers of the same
  size, plus fill). Formats include RGB565. Scale factors are truncated to a step of 1/16 in the ESP-IDF driver. [6]
  (sections: 35.1, 35.3 and Perform PPA Operations), [7].
- [source] The P4 datasheet lists the PPA, 2D-DMA, MIPI-DSI and an LCD interface. It does not list a separate 2D
  graphics accelerator beyond the PPA. A comparison table in [9] says "2D accelerator (PPA): Yes" for P4. [8], [9]
- [source] [9] says the P4 has no Bluetooth and gets Wi-Fi 6 "via co-processor". [inference] ESP-NOW on a P4 needs the
  companion chip, so a radio source must stay behind an interface.
- [source] MicroPython has a download page for the board `ESP32_GENERIC_P4`: "applicable to most development boards
  based on ESP32-P4", with at least 16 MiB of flash. Its latest stable release there is v1.29.0 (2026-08-24). Its
  variants are Generic (chip revision 3.x or later, or no co-processor in use), PRE REV3 (revisions 0.x and 1.x), and
  C5 or C6 WiFi/BLE "for boards with an external ESP32-C5 coprocessor". [11] A search summary says that v1.27.0
  (December 2025) added the port. I did not read the release notes.
- Not confirmed: a MicroPython binding for the PPA, the DSI display or the P4's other graphics parts. Not searched.
  Also not confirmed: whether MicroPython can start a task on the second core of the S3.
- Recommendation: [inference] keep four things swappable: the blit to the display (SPI now, LCD_CAM or DSI later),
  the blend and fill of a pane (Python now, C with PIE, PPA on P4), the volume scaling, and the radio. Each is one
  interface with the plain MicroPython version always working, as the PO's rule says (memory: naive path stays).

## 4. Event sources in one system

| Source | Standard model | Fit here | Ref |
|---|---|---|---|
| Button | Press and release events, debounced | Button counts edges in an interrupt | [repo], [4] |
| Rotary knob | A counter that gives steps (LVGL not confirmed) | Detents in the frame | [repo] |
| Changed value | A signal from the value's owner | Replaces the per-pane compare | [2] |
| Game state | A custom signal | Title, play, over as signals | [2] |
| Microphone level | A sampled value. Emit on a threshold | Sound writes an int | [inference] |
| Timer | Fires after a delay | Pane hold_ms is a manual timer | [repo] |
| Joystick | Axis values and buttons | Same shape as the knob | [inference] |
| Other board | ESP-NOW packets, polled or by callback | See below | [10] |

- [source] Godot: custom signals can announce a game event such as "health depleted" that opens a game-over screen.
  Signal names are past-tense verbs. [2] (section: Custom signals)
- [source] MicroPython ESP-NOW: the page covers ESP32 and ESP8266. It does not name the S3, but it is an ESP32 family
  chip, so I count it as likely. [10] (Introduction). Messages arrive by `recv()` (allocates), `irecv()` (reuses
  buffers), `recvinto()`, `any()` for polling, `irq()` for a callback (ESP32 only), or `aioespnow` for asyncio. The page
  warns that the scheduler stack can overflow and callbacks can be missed under heavy traffic. The default receive
  buffer is 528 or 2972 bytes. A message holds 250 bytes in V1 and 1470 bytes in V2 (V2 needs ESP-IDF 5.4). Check
  `espnow.MAX_DATA_LEN`. [10] (sections: Sending and Receiving Data, Callback Methods, Constants)
- Not confirmed: that ESP-NOW runs on the S3 build the project uses. Test it on the board.
- [source] LVGL's input events include `LV_EVENT_PRESSED`, `LV_EVENT_RELEASED`, `LV_EVENT_CLICKED`,
  `LV_EVENT_LONG_PRESSED`, `LV_EVENT_LONG_PRESSED_REPEAT` and `LV_EVENT_KEY`. [1] [inference] These are kinds of one
  event shape, which fits "a source id, a kind and ints" below.
- Not confirmed: how LVGL models an encoder or a joystick (its input-device page), and Unity's model.
- Recommendation: [inference] one event shape for all sources: a source id, a kind and ints. Sources that change
  slowly (state, value) use listeners. Sources that arrive in bursts (buttons, radio, level) fill a ring buffer that
  the frame drains once. For ESP-NOW prefer `irecv(0)` in the frame over `irq()`, so no callback runs between frames.

## What stays unknown

- LVGL: how the display joins and flushes invalidated areas, and how an encoder becomes events. Pages not read.
- Unity's event system and any input-event model from a game engine. Not searched.
- The cost in microseconds of a Python call, a bound-method call, an allocation and a schedule call on this board.
- The length of the micropython.schedule queue.
- Any MicroPython binding for the P4's PPA or DSI, and the s3lcd driver's state on the P4.
- Whether MicroPython can run work on the S3 second core.
- Whether the project's S3 image has ESP-NOW enabled.
- Real P4 numbers for PPA speed. The sources give features, not times.

## Sources

1. LVGL 9.5, Events: https://lvgl.io/docs/open/9.5/common-widget-features/events (read 2026-11-11, all but the
   last 1,200 characters). The display and input-device pages are not read.
2. Godot, Using signals: https://docs.godotengine.org/en/stable/getting_started/step_by_step/signals.html
3. Game Programming Patterns, Event Queue: https://gameprogrammingpatterns.com/event-queue.html
4. MicroPython, Writing interrupt handlers: https://docs.micropython.org/en/latest/reference/isr_rules.html
5. ESP32-S3 datasheet: https://documentation.espressif.com/esp32-s3_datasheet_en.html (4.1.1, 4.2.1.4), and
   the technical reference manual, chapter 29, LCD_CAM:
   https://documentation.espressif.com/esp32-s3_technical_reference_manual_en.html
6. ESP32-P4 technical reference manual, chapter 39, PPA:
   https://documentation.espressif.com/esp32-p4_technical_reference_manual_en.html
7. ESP-IDF, PPA driver:
   https://docs.espressif.com/projects/esp-idf/en/latest/esp32p4/api-reference/peripherals/ppa.html
8. ESP32-P4 datasheet: https://documentation.espressif.com/esp32-p4_datasheet_en.html (4.1.1.1, product overview),
   TRM chapter 43 for MIPI DSI (same TRM link as 6) and the v1.3 datasheet
   https://documentation.espressif.com/esp32-p4-chip-revision-v1.3_datasheet_en.html (360 MHz).
9. Espressif, Edge-AI with ESP32-S3 workshop, SoC table:
   https://developer.espressif.com/workshops/edge-ai-with-esp32-s3/introduction/
10. MicroPython, espnow: https://docs.micropython.org/en/latest/library/espnow.html
11. MicroPython, download page of ESP32_GENERIC_P4: https://micropython.org/download/ESP32_GENERIC_P4/
