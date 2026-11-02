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
- About 08:11 erase, then write the stock v1.29 build at 0x0 (921600 baud, hash verified). esptool's reset by RTS left the board in download mode, because it entered by the buttons. One press of RST started it.
- About 08:12 the stock build runs: `MicroPython v1.29.0 on 2026-11-02`, flash 16,777,216 bytes, 8,319,680 bytes free on the heap, the USB REPL answers (303a:4001). Note: MicroPython's USB serial number is made from the chip id, so it is masked like a MAC in every log.
- About 08:13 finding: `machine.bootloader()` on our v1.29 build also leaves the board on MicroPython's USB device (303a:4001). Download mode needs the buttons on this board, with both builds.
- 08:15 to 08:17 the s3lcd build written (hash verified), RST pressed, games copied without main.py, `import app; app.run()` from the REPL for 2 minutes while the PO played (`run1-v129-s3lcd.log`). USB stayed alive the whole run.
  - flappy: 9.5 fps, paint 34.8 ms, send 63.1 ms, gc 0.1 ms per frame.
  - runner: 6.8 fps, paint 72.4 ms, send 63.0 ms, gc 0.4 ms (max 5.2 ms).
  - So the collector does not cause the freezes in this run. The send is the largest cost, and Python waits through it.
- 08:18 `sendtest.py`, show() of a full 320x240 frame, 20 times each (`sendtest.log`): 60 MHz takes 63 ms (from the games), 80 MHz takes 47.2 ms, with 16-row or 48-row strips alike.
  Reading: the wire needs about 15 ms at 80 MHz, so about 32 ms per frame is the CPU copy and byte swap of each strip out of PSRAM, done while the bus waits. At 60 MHz the wire time of about 31 ms fits a real clock of 40 MHz (80 MHz divided by 2).
  Next: 80 MHz in the games if the panel shows clean colors, then slice 5: overlap the copy with the send, and a cheaper copy.
- Note on times: the minutes marked "about" are worked out from the files' times (the backup at 08:10, run1 ended 08:17, sendtest at 08:18), not read from the clock when written.
- 08:22 the PO: run 1 looked "kinda the same, almost fluent, but it froze sometimes". The colors at 80 MHz looked clean. The games now print `worst`, the longest gap between two frame starts, and run at 80 MHz.
- 08:24 run 2 at 80 MHz (`run2-v129-s3lcd-80mhz.log`): flappy 10.9 fps, paint 39.4 ms, send 47.4 ms (was 63.1), gc 0.0. Worst gaps between frames per 5 s: 161 101 392 149 155 155 201 ms. It ended after about 35 s because the PO pressed RST (reset_cause power on, up 22 s): the display looked dark to him at the start, while the log shows the game running. Open: was the display dark at 80 MHz in the games.
- 08:26 correction: at 80 MHz the panel stays dark. Run 3 (60 s, 80 MHz) ran the game with nothing on the display, and the slow color test showed nothing at 80 MHz but six clean colors at 60 MHz (the PO watched both). The earlier "clean" answer was about a 60 MHz picture. So the games go back to 60 MHz (a real 40 MHz), and the send stays at 63 ms until the copy overlaps it.
- 08:29 run 4 at 60 MHz, 2 min (`run4-v129-s3lcd-60mhz.log`), games flappy, runner, snake, stack. New per-interval line: the slowest frame and its split.
  - The send is 63 ms in every slow frame. The paint is the part that jumps: 108 to 631 ms in the slowest frames, against 35 to 70 ms on average. The longest stop was 695 ms in runner (paint 631).
  - The explicit collections, at the game's quiet moments, take 57 to 124 ms (the whole 8 MB PSRAM heap is scanned).
  - Reading, not yet proven: the freezes are automatic collections inside the paint, when the drawing code allocates. They count as paint time. Test: measure the bytes allocated per frame in paint.
  - Learned: `python3 -m py_compile` does not catch MicroPython syntax limits (star unpacking in a tuple). Check game code with `mpy-cross` before a copy.

## Slice 3 continued, 2026-11-02: the freezes and the buttons

- 08:35 run 5 counted the bytes each draw allocates: 8 to 14 KB per frame, at most 18.9 KB, and no collection inside a draw. The count itself cost about 114 ms per frame, because `gc.mem_alloc()` and `gc.mem_free()` take about 20 ms for each MB allocated (measured at the REPL: 14 ms at 0.8 MB, 55 ms at 2.5 MB). The old floor check called `gc.mem_free()` every 30 frames, so it stalled up to about 150 ms on a full heap.
- 08:37 run 6, `gc.threshold(64_000)`: the 300 to 700 ms pauses went away, but the collections hid inside the paint (paint 35 to 73 ms).
- 08:39 run 7, gc off and a timed `gc.collect()` every 5 frames: 15 to 20 ms per collection, 3 to 6 ms per frame. The paint still jumped to 108 to 200 ms in frames with no collection. So the collector does not cause the freezes. The reading from run 4 was wrong.
- 08:41 run 8 timed each draw phase. The game-over box took 46 to 127 ms and the score bar up to 58 ms, the game paint only 9 to 17 ms. Cause: `Canvas.big` cached whole strings, the cache stopped at 60 entries, and each new string read the font pixel by pixel.
- 08:43 run 9, text cached per character (`gfx.GLYPHS`): the game-over box 36 to 60 ms, the score bar 14 ms, worst gap 140 to 155 ms.
- 08:44 the PO: "the speed is kind of okay now already. It's almost playable", but presses get lost. Cause: `Button.update` read the pin once per frame (about 140 ms) and needed two reads in a row, so a tap shorter than about two frames was lost.
- 08:46 run 10, each button counts its edges in a pin interrupt (`Button.watch`). This build refuses `Pin.irq(hard=True)`, so the soft interrupt only counts, and `update()` drops an edge that is the bounce of a release. Tested on the Mac with a fake pin.
- Learned: the first run after an `mpremote cp` lost USB at start in each try today. The second run works.
- Next: the PO's verdict on the buttons; the game-over box still costs 36 ms per frame (many small `fill_rect` calls from Python).
- 08:52 run 11: the display went dark and USB went away while the PO held the jump button in runner. 09:00 an edge-count script with no display: taps gave 26 edges, a steady hold gave none (no storm), and USB dropped after about 5.5 s of steady hold. The board record says why (`hardware_revisions`, V1.1 and earlier): D14 also drives the AXP313A's PWRON through a diode, so a long press powers the board off. So BOOT is now the game button and D14 the short "next game" press.
- 09:10 run 13, frames paced at 110 ms (`FRAME_MS`). The PO: "pipes are still half rendered, I mean the breaking in the middle sort of". So the defect he sees most is tearing: the panel shows the top of a new frame over the bottom of the old one. Pacing evens the steps but cannot fix it. The driver work moved to P533 (spark #737).

## P533 slice 0, 2026-11-02: the probes before any C (`probe0.py`)

- 09:58 internal DMA memory (`MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL`), from `esp32.idf_heap_info`: free 264,347 bytes at boot, 261,651 after `init()`. The largest block is 188,416 bytes at boot, after `init()` and after a send. One frame needs 153,600 bytes, so the internal "dma" framebuffer fits, with about 35 KB left in that heap. A send holds no extra memory, because s3lcd copies each strip into its own internal buffer, so the SPI driver never bounces. Slice 3 uses `framebuffer="dma"`.
- 10:00 the corner picture at rotation 0 (driver native, 240 x 320). The PO, holding the board to play: red, the panel's pixel (0, 0), is top right, and the yellow bar of row 0 runs down the right edge. So panel x runs down the screen and panel y runs from right to left: panel x = game y, panel y = 319 - game x. The panel scans row by row from the right edge to the left, so in native order a tear is one vertical line.
- 10:02 the scroll trial (`SCROLL=6`, `vscrdef(0, 320, 0)`, `vscsad` in steps of 2 lines): the PO saw the bands move from left to right. The panel scrolls along game x, as E7 said, so the fixed areas are left and right bands, never the top score bar. Slice 7 (scroll) is dropped.
- USB dropped at driver start in every other run, with no file copy before it. The run after a drop works.

## P533 slice 1, 2026-11-02: no byte swap (`probe1.py`, `probe1b.py`)

- About 10:05 `lcd.py` sends the framebuffer as it is (`swap_color_bytes=False`), and `TftCanvas` passes the games' colours on unchanged. Send of a full frame, 20 times: 61.8 ms (was 63.1). The swap cost about 1 ms. The plan's pass "below 50 ms" fails, and its inference "about 32 ms is the swap" is rejected. The other 30 ms are the strip copy and wait structure or the real SPI clock: slice 3 measures them.
- About 10:06 colours right: the six bands showed red to magenta, no red and blue exchange.
- 10:08 the bands and the word LEFT, drawn through `TftCanvas` at rotation 1: in the hold the PO used for the test pictures, LEFT was upside down. The PO: "it's not [my playing position], I'd have to rotate it, but if it would mean some extra work that the game must do to turn it upside down, I don't mind turning the display itself, so it can stay like that, in general, however it would be good to offer all orientations and make it fast to transform". Slice 2 offers the orientations through a map in `TftCanvas`.

## P533 slice 2, 2026-11-02: native order

- The driver stays at rotation 0, and `TftCanvas.fill` and `line` turn game coordinates into panel coordinates (`ORIENTATION` 0 or 180 in `lcd.py`). The map is written out in `fill`, because a helper that returns a tuple would allocate on every fill. `box` draws its edges through `fill`. Tested on the Mac with a fake driver (both orientations, clipping, a line, and 90 refused).
- The first map put LEFT upside down in the playing hold. The slice 0 corner answers were given in the playing hold, and the slice 1 note that blamed a different hold was wrong. With the branches swapped, the PO: LEFT reads normally at the top left, red the leftmost band. So in the playing hold, panel x = game y and panel y = 319 - game x, as slice 0 said. Rotation 1 drew the games upside down in this hold.
- 10:20 to 10:23 run 14, 150 s in native order (`run14-native.log`; the run before it lost USB at driver start). The PO: "the pipes still break but I think now the whole pipe, not broken in the middle". So the tear line is vertical, as E4 said: a pipe is either all old or all new. The tear stays, because DFR0664 has no TE (E5).
- Two costs in run 14. The send is 71.3 ms (61.8 at rotation 1). s3lcd sends 16-row strips, 15 at rotation 1 and 20 at rotation 0, with the same bytes, so each strip costs about 1.9 ms beyond its bytes. That fixed cost explains the 30 ms over the wire time. The game-over box paints in 93 to 140 ms (36 to 60 before): a text run along game x is now a panel column, and each of its pixel rows is 480 bytes from the next in the PSRAM framebuffer. Reading, to measure in slice 3: one `draw_bitmap` of an internal framebuffer removes both.

## P533 slice 3, 2026-11-02: the frame in C (`probe3.py`)

- `s3lcd/src/frame.c` owns the framebuffer memory, two internal strips, the count of windows in flight and the done semaphore. `show()` sends the whole frame as one `draw_bitmap` from internal DMA RAM when `framebuffer="dma"`, and waits on the semaphore instead of a spin loop. `config(timeout=, framebuffer=)` checks all values, then applies all. `deinit()` is also the finalizer.
- Build notes: FreeRTOS.h gives `traceISR_EXIT_TO_SCHEDULER` its empty default only under `ESP_PLATFORM`, which MicroPython's user C modules lack, so frame.c defines it. The tick is 100 Hz and esp_lcd drops the callback's return value, so the callback yields itself.
- Flash with no button: `mpremote bootloader`, wait for the port, `esptool --before no_reset --after watchdog_reset write_flash 0x10000 micropython.bin`. The RTS reset left the chip in download mode (USB 0x1001). The watchdog reset starts MicroPython.
- 10:34 to 10:38, `config(framebuffer="dma")`: a full frame takes 31.0 ms, avg and best of 20 (71.3 ms in slice 2). That is the wire time at the real 40 MHz. `config(timeout=1)` makes `show()` raise OSError 116 (ETIMEDOUT), and the next `show()` at `timeout=100` runs. Errors: `timeout=0` and `framebuffer="psram"` raise ValueError, `framebuffer="strips"` after init raises ValueError ("set framebuffer before init()"), an unknown key raises TypeError (this build's text does not name the key: slice 4). `config(**config())` round-trips. A second object on SPI3 asking for "dma" prints `frame: no free internal block of 153600 bytes, so framebuffer="strips"` and runs.
- `config(framebuffer="strips")`: 71.9 ms. The overlap of copy and send gains nothing, so the cost per strip is not the copy. Not measured further, because "dma" removes it.
- The first strips run did not raise at `timeout=1`: each strip wait had its own timeout. Fixed: one deadline per `show()`, as the docstring says.
- Each run here followed the last with a soft reset and no reboot. Before the finalizer, `init()` after a soft reset found the SPI bus still claimed, and `ESP_ERROR_CHECK` aborted. That reading explains the USB drop "in every other run" of slices 0 to 2.
