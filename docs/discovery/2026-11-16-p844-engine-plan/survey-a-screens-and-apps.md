# P844 survey A: screens and app frameworks on small devices

A source of P844's [synthesis](synthesis.md) and [plan](plan.md), kept as the survey agent wrote it on 2026-11-16.

Spike P844 (spark #1208), area A. Written 2026-11-16. Every source is the project's own repository, read on the date
and commit below. Licenses are from each LICENSE file. Nothing ran on a board. Where I did not read or measure a
fact, the text says so.

## Short answer

- Two of the six are GPL-3.0 (Flipper Zero, InfiniTime). We take their designs only and copy no code.
- Four are MIT (Tildagon, LVGL and its MicroPython binding, UIFlow 2, Presto). We may copy code from them.
- The best fit for our plan is a small scene and app contract that borrows from three of them: Flipper's scene
  manager, the Tildagon's app class and UIFlow 2's app life cycle.
- LVGL is a real option for widget-heavy apps, but not for the engine. It owns the display, and the MicroPython
  fork ships MicroPython 1.24, not our 1.29.

## Our side, in short (from P838's finding and the cards)

Our plan has `Scene` (name, ART, cues, ACTIONS, needs, plugins, `step`, `draw`), `Lineup` (builds a scene as a
generator of progress), `SceneManager` (`pick`, `settle`, `frame`), `LoadingScreen` as a strategy, and an
`Actions` record per player (press, held, release, knob turn). The app kit (#1207) wants menus, lists, values and a
launcher on that same switch. Input is two buttons and a knob. One process, one fixed-step loop, no threads.

## 1. Flipper Zero firmware

- **What it is.** The firmware of the Flipper Zero handheld, with a GUI service, a scene manager and apps (FAP).
  Repository https://github.com/flipperdevices/flipperzero-firmware, branch `dev`, commit `a8a24de3ff` (pushed
  2026-11-14).
- **License.** GPL-3.0 (LICENSE file). Our repositories are MIT. **Copy no code.** Design only.
- **Screens and apps.**
  - `ViewDispatcher` (`applications/services/gui/view_dispatcher.h`) holds many `View`s by id and shows one at a
    time (`view_dispatcher_add_view`, `switch_to_view`). A dispatcher is fullscreen or windowed (with a status bar).
  - A `View` is a draw callback, an input callback, a "previous" callback (where Back goes), enter and exit
    callbacks and an optional model (`view.h`).
  - `SceneManager` (`scene_manager.h`) holds three arrays of handlers per scene id: `on_enter`, `on_event`,
    `on_exit`. It keeps a stack. `next_scene(id)` pushes, `previous_scene()` pops, and
    `search_and_switch_to_previous_scene(id)` pops down to a named scene. Each scene has one `uint32` state slot that
    survives while the scene is on the stack.
  - Three event kinds reach a scene: Custom (a number a view sent), Back, Tick. A scene returns true when it handled
    the event. If no scene handles Back, the app stops.
  - The pattern: a stock view (a submenu, a list, a text box) sends a custom event number when the user acts, and the
    scene decides what to do. The view knows no logic and the scene knows no pixels.
  - Apps are declared in `application.fam` (`documentation/AppManifests.md`): `appid`, `apptype` (APP, PLUGIN,
    SETTINGS, SYSTEM, EXTERNAL and others), `name`, `entry_point`, `requires`, `conflicts`, `order`, `stack_size`,
    icon. An external app (FAP) is a separate binary the firmware links on load.
- **Input.** `input.h` gives five event types per key: Press, Release, Short (a release inside the long-press time),
  Long, and Repeat (every period after Long). The apps see these types, not raw levels.
- **Event loop.** `furi/core/event_loop.h`: one loop per thread. It subscribes to queues, semaphores, mutexes and
  flags, has a tick callback and a "pend callback" for work run in the loop. The view dispatcher runs on it.
- **Copy as code.** Nothing (GPL).
- **Take as design.**
  - The scene stack with `enter`, `event`, `exit` and a back event, and the "stock view sends a custom event, scene
    decides" split.
  - The `Short` / `Long` / `Repeat` key types. Our action map has press, held and release only. A long press on D14
    or the knob button is the natural second kind for apps (a settings screen needs "long press = back").
  - The app manifest as data (name, type, order, requires), which fits our `catalog.py` rows.
- **Leave, and why.** The C callback tables, the GUI service and view-port layers (we have one screen and one
  process), the dynamic FAP linker, and the event-loop subscription model (our fixed-step loop is simpler, and a
  second loop would break the frame budget).

## 2. EMF Camp Tildagon badge (MicroPython)

- **What it is.** The 2024 badge firmware of Electromagnetic Field, MicroPython on an ESP32-S3 with a round 240x240
  display and six buttons. Repository https://github.com/emfcamp/badge-2024-software, `main`, commit `f10ecb8b18`
  (pushed 2026-10-11).
- **License.** MIT (LICENSE: "Copyright (c) 2025 Electromagnetic Field"). Code may be copied with the notice.
- **App model** (read in `modules/app.py`, `modules/system/scheduler/__init__.py`):
  - An app is a class that extends `App`. Methods: `update(delta_ms)`, `draw(ctx)`, `background_update(delta)`,
    `minimise()`, `terminate()`. Each app also has `run(render_update)` and `background_task()`, which the base class
    supplies.
  - `update` returns `False` when nothing changed, and then the base class sleeps and skips the redraw. Any other
    return means "draw me". This is a dirty flag the app sets.
  - `draw` is separate from `update`. Overlays are a list on the app, drawn on top.
  - Foreground and background: every running app gets a `background_task` (always runs). Only the app on top of a
    foreground stack gets its `update` task and its `draw`. A second stack, `on_top_stack`, holds apps that draw over
    everything (notifications) and never take focus. `minimise()` pops the app from the foreground. It keeps running
    in the background.
  - Crash isolation: the scheduler wraps `update` and `draw` in `try`. A failure stops that app only, prints the
    trace, shows a "has crashed" notice and plays a sound. The badge keeps running.
  - Events: a global `eventbus` (`system/eventbus.py`) with `on(EventType, handler, app)` and `emit(event)`, a queue
    and handlers keyed by app. Buttons are `ButtonDownEvent` and `ButtonUpEvent`. The helper `Buttons(app)` keeps a
    level per button and `pressed(button)` is latched, true once per press.
  - Everything runs on `asyncio` with one task per app.
  - Apps live in a folder with a manifest `tildagon.toml` (metadata, capabilities the app needs or provides). The
    launcher lists the manifests. Requirements are checked before launch (`system/capabilities/utils.py`).
  - App store (`modules/firmware_apps/app_store.py`): the index comes from `https://apps.badge.emfcamp.org/v1/apps`
    as JSON. An install downloads a tarball and unpacks it to the apps folder. A menu offers categories, details,
    install and update.
- **Copy as code (MIT).** The shape of the `App` base class, the crash-isolation `try` around update and draw, and
  `Buttons.pressed` (a latched press, about 15 lines). Our action map already has its own press edge, so the latch
  is a cross-check, not new code.
- **Take as design.**
  - The `update` return value as "no redraw needed". For apps (settings, lists) this saves most frames. Games always
    return True.
  - Crash isolation at the scene boundary: a failing app returns to the launcher with a notice. Our
    `SceneManager.refuse` already refuses a failing build. Extending it to `step` and `draw` is the same idea.
  - A manifest next to the app, with needs checked before launch. Our `needs = ("balls",)` is the same thing.
  - A top overlay stack that never takes focus. We have `overlay.py` for this.
  - The app store as an index plus a tarball. That is far later for us, and the install side is out of scope now.
- **Leave, and why.** `asyncio` with one task per app (more heap, and a fixed-step loop is easier to test and to
  hold at 60 fps), the global event bus (hidden coupling, and it prints on every `on`), the `ctx` vector drawing API
  (round vector display, not our pixel canvas), and the hexpansion and capability system (badge hardware).

## 3. LVGL and lv_micropython

- **What it is.** LVGL is a C widget library for embedded displays. `lv_binding_micropython` generates a MicroPython
  module from LVGL's headers. `lv_micropython` is a fork of MicroPython with the binding built in.
  - LVGL: https://github.com/lvgl/lvgl, release `v9.6.0` (2026-09-16), `master` at `6187fb91fb`.
  - Binding: https://github.com/lvgl/lv_binding_micropython, `master` at `032dda4b7e` (2026-09-06).
  - Fork: https://github.com/lvgl/lv_micropython (last push 2026-09-06). `py/mpconfig.h` there says
    `MICROPY_VERSION_MAJOR 1`, `MINOR 24`. **Our firmware is 1.29.**
- **License.** LVGL: MIT (LICENCE.txt, "Copyright (c) 2025 LVGL Kft"). Binding: MIT (LICENSE). The fork: MicroPython's
  MIT license (GitHub reports "NOASSERTION" because of the mixed tree; its LICENSE is MIT, Damien George).
- **Screen model.**
  - A display owns four permanent layers: bottom, the active screen, top and system
    (`docs/src/main-modules/display/screen_layers.mdx`). The top and system layers are transparent and draw over
    whatever screen is active. That is our overlay.
  - Widgets form a tree under a screen object. You load a screen, with optional animation. When you no longer need a
    screen, you call `screen.delete()` so MicroPython's gc can free it (binding README, "Memory Management").
  - Styles, themes, animations and a timer system come with it.
- **Input model.** Input devices have a type: pointer, keypad, encoder or button. A **group** holds the focusable
  widgets. An encoder works so: turn to move focus, press to click, long press to leave "edit mode"
  (`docs/src/main-modules/indev/encoder.mdx`). This is exactly a knob with a button.
- **Display interface.** You set draw buffers with `lv_display_set_buffers(disp, buf1, buf2, size, render_mode)`.
  Modes: PARTIAL (buffers smaller than the screen, "at least 1/10 display size is recommended"), DIRECT and FULL
  (docs `display/setup.mdx`). You set a flush callback that sends the area to the panel. `lv_task_handler` must run
  periodically. In MicroPython the flush and read callbacks may be pure Python, C, or a mix. The binding says to
  configure pins at run time, not by macros.
- **Cost.** LVGL's README says "a typical UI needs only ~100 kB RAM, ~200-300 kB flash and a buffer of 1/10 of the
  screen", and the bare minimum is 32 kB RAM and 128 kB flash. I did not measure the S3 build. Our own numbers are
  missing.
- **Copy as code (MIT).** Possible, but not useful now. The binding drivers (`driver/esp32/ili9XXX.py`) target the
  ILI9341, not our ST7789 driver `s3lcd`.
- **Take as design.**
  - The encoder-and-group navigation for lists and menus. This is the right model for a two-button-and-knob box.
  - Layers: a screen and a top layer for the overlay (already ours).
  - The display driver as two small callbacks (`flush(area, pixels)` and `read()`), with run-time pins. This matches
    our "drivers behind small interfaces" decision.
  - `screen.delete()` as an explicit free step. Our scenes already have `leave`.
- **Leave, and why (for the engine).** LVGL redraws by invalidated areas and wants to own the flush. Our games draw a
  whole canvas through `s3lcd` and C draws. Two owners of the display on the same panel is a source of tearing and a
  heap fight. The fork is two MicroPython versions behind us. The binding would have to be added as a user C module
  to our own 1.29 build, and I have not tested that it builds. So: **no LVGL in the engine.** Consider it later only
  as an optional "widget strategy" in the app kit, behind a spike that builds it on 1.29 and measures flash and
  heap on the box. A small hand-made list and value widget set in plain Python is likely enough for a settings
  screen and a clock.

## 4. M5Stack UIFlow 2

- **What it is.** M5Stack's MicroPython firmware for ESP32 devices, with a Python API (`M5`, `Widgets`, `BtnA`) and a
  launcher on the device. Repository https://github.com/M5Stack/uiflow-micropython, `master`, commit `54b1d24241`
  (2026-11-13).
- **License.** MIT (LICENSE, "Copyright (c) 2023 M5Stack"). Some bundled third-party parts have their own license
  (its README names Apache 2.0 for the camera part). Check any single file's SPDX line before copying it.
- **App model.**
  - A user app is a plain script in `fs/user/apps/` (`helloworld.py`). It calls `M5.begin()` and runs its own
    `while True: M5.update()` loop.
  - Buttons: `BtnA.setCallback(type=CB_TYPE.WAS_CLICKED, cb=...)`, `WAS_HOLD`, and so on, called from `M5.update()`
    (docs `docs/source/hardware/button.rst`). That doc has a table of which buttons each host board has.
  - The on-device launcher (`m5stack/modules/startup/basic/apps/`) is built from small classes. `AppBase` in
    `app_base.py` has the life cycle: `on_install`, `on_launch`, `on_view`, `on_ready` (starts an asyncio task
    `on_run`), `on_hide` (cancels the task), `on_exit`, `on_uninstall`. Driver methods wrap them: `install`,
    `start` (launch, view, ready), `pause` (hide), `resume` (ready), `stop` (hide, exit), `uninstall`.
    `AppSelector` has `next`, `prev`, `current`, `select`. Launcher pages are `AppBase` subclasses (list, run,
    settings, dev, ezdata).
- **Copy as code (MIT).** `AppBase` and `AppSelector` are about 50 lines. They are a good start for the app kit.
  Keep the SPDX header.
- **Take as design.**
  - Separate "build the screen" (`on_launch`, `on_view`) from "start running" (`on_ready`) and from "stop running"
    (`on_hide`). This is where a loading screen fits. Our `Lineup.build_steps` is `on_launch`, and `settle` is
    `on_ready`.
  - `pause` and `resume` apart from `stop`. A game that goes to the pause menu needs them. It also fits the
    "overlay pane" of multiplayer.
  - A per-board button table in the docs, as a capability fact. Our spark pin records hold this already.
- **Leave, and why.** Per-app asyncio tasks (see Tildagon), the fixed 320x240 launcher art made from images, and the
  callback API on buttons (our action map is polled once per frame, which keeps the frame order testable).

## 5. Pimoroni Presto (and its launcher)

- **What it is.** An RP2350 board with a 480x480 display. MicroPython firmware with a C module and frozen Python.
  Repository https://github.com/pimoroni/presto, `main`, commit `b96a8cbe3f` (2026-08-26).
- **License.** MIT (LICENSE).
- **Model.**
  - Hardware is one frozen class `Presto(full_res, palette, layers, direct_to_fb, ...)` in
    `modules/py_frozen/presto.py`. It wraps the C module `_presto` (with the underscore) and gives a `PicoGraphics`
    display, a touch driver and helpers (`update`, `partial_update`, `clear`). The constructor flags choose the
    memory layout.
  - The launcher is `examples/main.py`. It lists the `.py` files in the folder and draws icons. To start an app it
    writes the app's file name to `/ramfs/launch.txt` (a RAM file system) and calls `machine.reset()`. On the next
    boot, `main.py` reads that file first, deletes it and does `__import__(name)`. So each app starts on a clean
    heap, and the launcher cannot be damaged by an app. Back to the launcher is another reset.
- **Copy as code (MIT).** Little. The launcher uses PicoVector icons.
- **Take as design.**
  - **Reset-to-launch.** One clean heap per app. This fits our known problem: switching games in one process
    leaves heap fragmentation and slow `switch` lines (P822, P837). A variant for us: `machine.soft_reset()` after
    saving the next name where it survives (a file in flash, or RTC memory). I did not check what survives a soft
    reset on ESP32-S3 with MicroPython 1.29, so that needs a test. The cost is a boot time before the next game
    appears, and our loading card hides some of that.
  - The `_presto` plus frozen `presto.py` split is the same as our `_engine` plus `engine` names. This is a small
    outside example for the PO's naming decision.
  - Hardware as one class with constructor flags is close to our `Parts` record and `hardware.py`.
- **Leave, and why.** PicoVector and touch (not on our box), and the full-reset launch as the only mode (a reset
  loses the sound state and the P822 speed we have won).

## 6. PineTime InfiniTime

- **What it is.** Open firmware for the PineTime smartwatch (nRF52, 240x240 ST7789, FreeRTOS, LVGL). Repository
  https://github.com/InfiniTimeOrg/InfiniTime, `main`, commit `9ad16304f5` (pushed 2026-11-03).
- **License.** GPL-3.0 (LICENSE). **Design only.**
- **Model.**
  - One `Screen` base class (`src/displayapp/screens/Screen.h`) with `Refresh()` (called by an LVGL task),
    `OnButtonPushed()` and two `OnTouchEvent` overloads. The three handlers **return a bool: true means "I handled
    it"**. When the app returns false, the system does the default (for the button, go back to the clock).
  - `DisplayApp` (`src/displayapp/DisplayApp.h`) owns exactly one `std::unique_ptr<Screen> currentScreen`, a message
    queue of 10 and an `Apps` enum. `StartApp(app, direction)` and `LoadNewScreen` destroy the old screen and build
    the new one. A transition has a direction (None, Up, Down, Left, Right, and two animated kinds). `returnToApp`
    remembers where to go back to.
- **Take as design.**
  - **"Handled" return value for input.** The app gets first use of a press. If it does not take it, the system uses
    it. For us: the scene gets the action first, and an unused `next` press goes to the pick. This keeps a
    long-press-to-back rule out of every game.
  - One live screen at a time, built on switch and freed on leave. This is our current model. It is a good check that
    the app kit should not keep several screens built.
  - A transition direction as data (for a settings screen that slides in).
- **Leave, and why.** FreeRTOS tasks and queues, LVGL-based widgets, and the touch events (we have none).

## What we copy, learn and leave: one table

| Source | License | Code to copy | Design to take | Leave |
| --- | --- | --- | --- | --- |
| Flipper Zero | GPL-3.0 | none | scene stack with enter/event/exit; view sends event, scene decides; Short/Long/Repeat keys; manifest as data | C callbacks, GUI service, FAP linker, event-loop subscriptions |
| Tildagon | MIT | `App` shape, crash isolation `try`, `Buttons.pressed` latch | `update` returns False for "no redraw"; crash returns to launcher; manifest with needs; top overlay stack; store index plus tarball (later) | asyncio per app, event bus, vector ctx |
| LVGL + binding | MIT (fork: MicroPython MIT) | none now | encoder focus groups; layers; two-callback display driver with run-time pins; explicit screen free | LVGL in the engine; fork on MicroPython 1.24 |
| UIFlow 2 | MIT | `AppBase`, `AppSelector` (about 50 lines) | install/launch/view/ready/hide/exit life cycle; pause and resume apart from stop | asyncio tasks, button callbacks, image launcher |
| Presto | MIT | none | reset-to-launch with a RAM hand-off; `_presto` plus frozen wrapper naming; hardware as one class | PicoVector, touch |
| InfiniTime | GPL-3.0 | none | "handled" bool on input; one live screen; transition direction | FreeRTOS, LVGL widgets |

## Ranked: the three most useful things for our engine and app kit

1. **A scene contract with a life cycle and a "handled" input rule** (design from UIFlow 2's `AppBase`, Flipper's
   scene `enter/event/exit` and back event, and InfiniTime's handled-bool). The contract: `build` (the
   `Lineup` steps, behind the loading card), `enter` (ready), `step(now, actions)` returning "changed or not" (from
   the Tildagon's `update`), `pause` and `resume`, `leave`. An unused `back` or `next` action goes to the
   `SceneManager`. A crashing scene returns to the launcher with a notice (Tildagon).
   **Where:** stage 3b (`SceneManager`, `Scene`, `LoadingScreen`) writes the contract. The app kit (#1207) is its
   second user. Add the `changed` return and `pause/resume` as optional methods so the games change nothing.
   `AppBase` and `AppSelector` from UIFlow 2 (MIT) are the code start for the kit's launcher.
2. **Press kinds for the action map: Press, Release, Short, Long, Repeat** (from Flipper's `input.h`), plus an
   encoder-style navigation rule for lists (turn moves focus, press selects, long press goes back; from LVGL's
   encoder doc). The box has two buttons and a knob, so this is how menus, lists and a settings screen get used
   without more keys.
   **Where:** stage 1 (the action map) adds Long and Repeat as fields of `Actions`, with the characterization tests,
   so multiplayer's remote input fills the same record. The app kit's menu and list widgets read them.
3. **A spike on reset-to-launch against in-process switching** (from Presto). Test on the box whether
   `machine.soft_reset()` with a saved next-app name gives a clean heap and a switch time the PO accepts, compared
   with the P822/P837 `switch` lines. If it does, the app kit's launcher can use it for apps, and games stay in
   process. This one also answers heap leaks between apps from different authors.
   **Where:** the app kit's launcher card, before it is refined. It is a measurement card, not a stage. It does not
   touch stages N to 9.

Not in the top three, and later: LVGL as an optional widget strategy in the app kit (needs a 1.29 build spike and
heap numbers first), and an app store index (Tildagon) once more than one device runs the engine.
