# pixel-games

Small arcade games in MicroPython on a DFRobot FireBeetle 2 ESP32-S3 with the DFR0664 display (ST7789, 240 x 320, SPI). A C display driver, a fork of [russhughes/s3lcd](https://github.com/russhughes/s3lcd), sends each frame by DMA, so the Python games can run at about 20 fps.

The repository is also a log of how the games got smooth: every step was measured on the bench and written down.

## What is here

| path | what it holds |
| --- | --- |
| `games/` | the games and their small framework (`app.py` starts them, `lcd.py` and `gfx.py` draw) |
| `art/` | the painted art: one set per game, the brush and the export |
| `tests/` | the tests that run on a computer, with no board |
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

- The rain (P593, `games/rain.py`), first at power-on: 160 boxes fall, stepped by the C engine, and a BOOT tap swaps C
  and Python. On the board, C runs at 24 fps with a 0.17 ms step, and Python at 7 to 8 fps with a 30 ms step
  (bench.md P593). It needs the engine image (`./build.sh engine`). Without it, the rain runs in Python only.
- Ten games. Three are painted: runner, flappy and stack (stack as RENT). The other seven are flat.
- The double buffer: the game paints into PSRAM, and `show()` copies the frame and returns.
- Measured fps per painted game, from `bench.md`: flappy 20 to 22 and runner 21 to 24 at a 40 ms frame pace, with no play; stack 24.

In progress: P582 ([#783](https://github.com/xmejkal/spark/issues/783)), heavy floors for RENT. The work is on the branch `p582-heavy` and is not merged. Nobody has yet said how it feels.

Next: P583 ([#784](https://github.com/xmejkal/spark/issues/784)), effects in C on the S3's PIE (its vector instructions).

The work is planned on the board of the [spark](https://github.com/xmejkal/spark) project.

## Licence

MIT, see `LICENSE`. The files under `s3lcd/` keep their own terms.
