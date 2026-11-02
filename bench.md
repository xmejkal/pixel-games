# Bench log (P511 #706)

## Builds (no board)

- 2026-11-02 07:16: stock MicroPython v1.29.0, ESP32_GENERIC_S3 SPIRAM_OCT, ESP-IDF v5.5.2. firmware.bin 1,786,704 bytes, app partition 310,448 bytes free.
- 2026-11-02 07:3x: the same with s3lcd f254daf5 plus two compile fixes. firmware.bin 1,867,376 bytes, sha256 starts 78df6fbe8479f0c6, app partition 229,776 bytes free. `genhdr/moduledefs.h` registers `s3lcd`.
- Install cost for P530: ESP-IDF v5.5.2 checkout 647 MB. The shared tools folder ~/.espressif holds 7.6 GB with the old v4.4 tools in it.

## Slice 3, at the bench (waits on the PO)

1. Baseline on the image now on the board: its file name, fps per game, blinks, freezes, USB.
2. Backup: `esptool read-flash 0 0x1000000 backup.bin` and `mpremote cp -r :/ backup/`.
   Restore: `esptool write-flash 0 backup.bin`.
3. Stock v1.29 image, REPL over USB. Then the s3lcd image, games without main.py, started by hand.
