# Bench log (P511 #706)

## Builds (no board)

- 2026-11-02 07:16: stock MicroPython v1.29.0, ESP32_GENERIC_S3 SPIRAM_OCT, ESP-IDF v5.5.2. firmware.bin 1,786,704 bytes, app partition 310,448 bytes free.
- 2026-11-02 07:20: the same with s3lcd f254daf5 plus two compile fixes. firmware.bin 1,867,376 bytes, sha256 starts 78df6fbe8479f0c6, app partition 229,776 bytes free. `genhdr/moduledefs.h` registers `s3lcd`.
- Install cost for P530: ESP-IDF v5.5.2 checkout 647 MB. The shared tools folder ~/.espressif holds 7.6 GB with the old v4.4 tools in it.

## Slice 3, at the bench (waits on the PO)

1. Baseline on the image now on the board: its file name, fps per game, blinks, freezes, USB.
2. Backup: `esptool read-flash 0 0x1000000 backup.bin` and `mpremote cp -r :/ backup/`.
   Restore: `esptool write-flash 0 backup.bin`.
3. Stock v1.29 image, REPL over USB. Then the s3lcd image, games without main.py, started by hand.

## Slice 3 at the bench, 2026-11-02 (with the PO)

- 08:05 baseline, by the PO's eyes, on the image already on the board (replug since last night: unknown). The screen showed "game over", so a game ran. "Kinda smooth, not smooth enough, it still gets stuck and it's not playable really, but it's the best we've achieved so far."
- The image read over USB: `MicroPython v1.22.2-dirty on 2024-02-21`, flash 16,777,216 bytes, 7,432,720 bytes free on the heap, `s3lcd` imports. USB stayed alive while the game ran, so the USB loss at driver start does not happen every time.
- Backup of the files: `mpremote cp -r :/ backup/files/`. They match `games/`, plus a `boot.py` that only the board has.
- Download mode from software: `machine.bootloader()` over mpremote, no buttons.
- 08:08 finding: `machine.bootloader()` on v1.22.2 did not reach download mode. The board stayed on MicroPython's USB device (303a:4001), and esptool got "No serial data received". BOOT held plus RST pressed worked at once: the chip's own port came up (303a:1001).
- 08:10 full flash backup: `esptool -b 921600 read-flash 0 0x1000000 backup/flash-v1.22.2.bin`, 16,777,216 bytes in 59.7 s, sha256 starts 35a5f77fa46999c4. The file holds the board's MAC, so `backup/` stays out of git.
  Restore: put the board in download mode (BOOT held, RST pressed), then `esptool write-flash 0 backup/flash-v1.22.2.bin`, then copy `backup/files/` if needed.
- 08:13 erase, then write the stock v1.29 build at 0x0 (921600 baud, hash verified). esptool's reset by RTS left the board in download mode, because it entered by the buttons. One press of RST started it.
- 08:15 the stock build runs: `MicroPython v1.29.0 on 2026-11-02`, flash 16,777,216 bytes, 8,319,680 bytes free on the heap, the USB REPL answers (303a:4001). Note: MicroPython's USB serial number is made from the chip id, so it is masked like a MAC in every log.
- 08:17 finding: `machine.bootloader()` on our v1.29 build also leaves the board on MicroPython's USB device (303a:4001). Download mode needs the buttons on this board, with both builds.
