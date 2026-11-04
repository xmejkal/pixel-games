# pixel-games

Small arcade games in MicroPython on a DFRobot FireBeetle 2 ESP32-S3 with the DFR0664 display (ST7789, 240 x 320, SPI). A C display driver, a fork of [russhughes/s3lcd](https://github.com/russhughes/s3lcd), sends each frame by DMA, so the Python games can run at about 20 fps.

The repository is also a log of how the games got smooth: every step was measured on the bench and written down.

## What is here

| path | what it holds |
| --- | --- |
| `games/` | the games and their small framework (`app.py` starts them, `lcd.py` and `gfx.py` draw) |
| `art/` | the painted art: one set per game, the brush and the export |
| `tests/` | the tests that run on a computer, with no board: `python3 -B -m unittest discover tests` from the repository root (the C ones need clang) |
| `tools/` | `render_scene.py`: `python3 -B tools/render_scene.py burning out.png [frames ...]` draws a heat-field scene on the Mac to a PNG (needs clang and Pillow) |
| `s3lcd/` | the C driver: the fork with `frame.c`, a DMA send of one frame and partial updates |
| `build.sh` | builds the MicroPython firmware, with or without the driver |
| `bench.md` | the bench log: each run, its numbers and what it taught |
| `p537-finding.md` | the options for smooth motion, ranked, with a plan in slices |
| `docs/` | the discoveries: a public graphics library (P539) and the restyle of the games (P565) |

## Build and run

You need ESP-IDF v5.5.2 in `~/esp/esp-idf-v5.5.2`. The script clones MicroPython v1.29.0 into `~/esp` if it is not there.

1. Build the firmware with the driver: `./build.sh s3lcd`.
2. Put the board in download mode: `mpremote bootloader`.
3. Write the image: `esptool --before no_reset --after watchdog_reset write_flash 0x10000 micropython.bin`.
4. Copy the games: `mpremote cp games/*.py :`.
5. Reset the board. `main.py` starts the games.

If the board stays dark after a long press of its D14 button, hold D14 for 1 to 2 seconds. That button also switches the board's power off.

## Status

Runs now:

- The fire (P595, `games/fire.py`), first at power-on: a heat field in C (`engine.HeatField`) burns over the whole
  screen, and a BOOT tap swaps B (C writes the screen's frame) and the fire over the painted sky. It needs the engine
  image. The flames rise from wandering hot spots, break into tongues, rise at two speeds, lean in gusts of wind and
  throw embers. On the board, B runs at 24 fps with 11.5 to 11.8 ms of step + draw, and the sky variant at 15 to
  16 fps (bench.md, P595). In the picture mode C blends the fire in C at an alpha that follows the heat, full from heat 96
  (P603). The blend swaps the bytes of each colour in and out (`s3lcd/src/blend565.h`), so the colours are right.
- The bodies on fire (P596, P607, `games/burning.py`), second: eight falling bodies from the rain's stepper each carry
  an `effects.FireTrail`, which burns heat into the fire's field behind them (`HeatField.burn`), and the field's own base is off (`HeatField.set_base`), so only the bodies
  burn. A hit at 600 px/s or faster flares up at the body's plane: C reports the hit with its speed as an event, and
  Python decides the flare (P590). `tools/render_scene.py` draws it on the Mac. Smoke is later (cut by the PO,
  2026-11-04).
- The rain (P593, `games/rain.py`), third: 160 boxes fall, stepped by the C engine, and a BOOT tap swaps C
  and Python. On the board, C runs at 24 to 25 fps with a 0.22 ms step, and Python at 8 to 9 fps with a 28 ms step
  (bench.md P590). It needs the engine image (`./build.sh engine`). Without it, the rain runs in Python only.
- The bodies' API (P590): `engine.Bodies(n)` in C and its twin `motion.Bodies(n)` in Python take the same calls:
  `spawn`, `step`, `read` into an `array('h')` and `drain` into an `array('i')`. A step reports each hit with its
  speed (`HIT`) and each body that comes to rest (`SLEEP`) as an event, and the game drains them once per frame.
  `rain.Stepper` holds either one, and `motion.StepClock` turns a frame's ms into 10 ms steps.
- Effects on bodies (P607, `games/effects.py`): a body of a `rain.Stepper` carries an effect, and an event can start
  one. A scene makes `BodyEffects(stepper)` once and calls `react` and `apply` each frame, after the step and the read:

  ```python
  effects = BodyEffects(stepper)
  effects.bodies[0].effect = FireTrail(field, 8, 3, 200, 0.5)  # size px, radius cells, heat, lag frames
  reactions = {HIT: lambda body, speed: ...}  # Python decides what a hit causes; it can set body.effect
  effects.react(reactions)
  effects.apply()
  ```

  A new effect is one more subclass of `effects.Effect` (`apply(x, y)`, `forget()`), and its callers do not change.
- The HUD is drawn once into a strip and blitted each frame (P599).
- Ten games. Three are painted: runner, flappy and stack (stack as RENT). The other seven are flat.
- The double buffer: the game paints into PSRAM, and `show()` copies the frame and returns.
- Measured fps per painted game, from `bench.md`: flappy 20 to 22 and runner 21 to 24 at a 40 ms frame pace, with no play; stack 24.

In progress: P607 ([#809](https://github.com/xmejkal/spark/issues/809)), effects on bodies. The PO chose "Full MVP, 4 slices" on 2026-11-04 to close the effects epic P594 ([#795](https://github.com/xmejkal/spark/issues/795)). Paused: P582 ([#783](https://github.com/xmejkal/spark/issues/783)), heavy floors for RENT, on the branch `p582-heavy`, not merged.

Next: P608 ([#810](https://github.com/xmejkal/spark/issues/810)), a slight blur, the second effect. Then P602 ([#803](https://github.com/xmejkal/spark/issues/803)), the flappy bird trails fire, the first effect inside a game, and P598 ([#799](https://github.com/xmejkal/spark/issues/799)), colliding bodies. Later: P583 ([#784](https://github.com/xmejkal/spark/issues/784)), effects in C on the S3's PIE (its vector instructions).

The work is planned on the board of the [spark](https://github.com/xmejkal/spark) project.

## Licence

MIT, see `LICENSE`. The files under `s3lcd/` keep their own terms.
