# pixel-games

Small arcade games in MicroPython on a DFRobot FireBeetle 2 ESP32-S3 with the DFR0664 display (ST7789, 240 x 320, SPI). A C display driver, a fork of [russhughes/s3lcd](https://github.com/russhughes/s3lcd), sends each frame by DMA, so the Python games can run at about 20 fps.

The repository is also a log of how the games got smooth: every step was measured on the bench and written down.

## What is here

| path | what it holds |
| --- | --- |
| `games/` | the games and their small framework (`app.py` starts them, `lcd.py` and `gfx.py` draw) |
| `s3lcd/` | the C driver: the fork with `frame.c`, a DMA send of one frame and partial updates |
| `build.sh` | builds the MicroPython firmware, with or without the driver |
| `bench.md` | the bench log: each run, its numbers and what it taught |
| `p537-finding.md` | the options for smooth motion, ranked, with a plan in slices |
| `docs/discovery/` | the discovery for a public graphics library for small chips (P539) |

## Build and run

You need ESP-IDF v5.5.2 in `~/esp/esp-idf-v5.5.2`. The script clones MicroPython v1.29.0 into `~/esp` if it is not there.

1. Build the firmware with the driver: `./build.sh s3lcd`.
2. Put the board in download mode: `mpremote bootloader`.
3. Write the image: `esptool --before no_reset --after watchdog_reset write_flash 0x10000 micropython.bin`.
4. Copy the games: `mpremote cp games/*.py :`.
5. Reset the board. `main.py` starts the games.

If the board stays dark after a long press of its D14 button, hold D14 for 1 to 2 seconds. That button also switches the board's power off.

## Status

The games run at 20 to 24 fps (flappy and runner at a 40 ms frame pace). Painting in Python is now the limit. The next step is a measurement of what that paint time is made of (spark issue [P550 #754](https://github.com/xmejkal/spark/issues/754)). The work is planned on the board of the [spark](https://github.com/xmejkal/spark) project.

## Licence

MIT, see `LICENSE`. The files under `s3lcd/` keep their own terms.
