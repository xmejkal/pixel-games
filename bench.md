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
- 10:41 the PO: the white square sits top right, as it should, but the background was "purple/violet", not green. Cause: `probe3.py` filled with `s3lcd.GREEN` (0x07E0) as it is, and the games' colours are pre-swapped (`gfx.py:10`), because since slice 1 nothing swaps on the way. The panel read 0xE007, mostly red with some blue. White is the same in both byte orders. The probe now swaps its colours like the games; the driver did not change.
- 10:44 to 10:46 run 15, 150 s on the new driver (`run15-frame-dma.log`), flappy, runner, snake, stack, frames paced at 110 ms. The send is 31.3 ms in every interval (71.3 in run 14). Flappy: paint 18 to 42 ms, worst gap 110 to 112 ms (the pace), the game-over box 35 to 49 ms (93 to 140 in run 14), so internal RAM also removes the cost of column writes.
- Runner gets slower as it runs: paint 39 to 122 ms in about a minute, static 29 to 88 ms, hud 20 to 71 ms, gc 1.1 to 6.0 ms, fps 9 to 5. Stack, after the switch, starts high (static 33, hud 64). Run 4 had runner at 42 to 72 ms with no climb. Reading, not proven: something keeps live objects on the heap during play, so every allocation and collection gets slower. Test: the live heap after a collection, once per interval.
- 10:54 to 10:57 run 16 (`run16-heap-60ms.log`), `FRAME_MS = 60` and a heap line per interval. Flappy: 14 to 16 fps (9 at 110 ms), send 31.3 ms. Runner: the bytes in use climb from 137 KB to 582 KB, paint from 44 to 362 ms, fps from 12 to 2; the glyph cache stays at 32. Cause: `TftCanvas.sprite` (and `Canvas.sprite`) cached by `id(rows)`, and runner passes `RUN_TOP + leg`, a new tuple each frame, so the cache gained one entry per frame and never hit. An id key could also hit a freed object's old entry and draw the wrong sprite. Fix: key by the rows themselves.
- 10:58 to 11:01 run 17 (`run17-sprite-key.log`): stack at 16 fps, paint 19 to 21 ms while playing, hud 13 to 16 ms (64 ms in run 15, the heap runner left behind), heap 69 to 129 KB and flat. Runner was passed in seconds, so it was not measured. The PO: "Its good to aknowledge that also the whole game is faster now, the pipes and other things still appear a bit stepped, but overall way better."
- 11:01 to 11:04 run 18, runner alone (`run(games=(app.Runner,))`, `run18-runner.log`): 14 fps, paint 32 ms, heap 68 to 145 KB and flat for 80 s of play. Then the game-over box at 7 fps (over 66 ms, static 50 ms). The leak is fixed. The PO: "even better, I think at least the runner s almost fully playable, I like it. Maybe we can somehow even lower the steppness?"
- 11:04 to 11:07 run 19, flappy alone (`run19-flappy.log`): 16 fps while playing, paint 18 to 20 ms, send 31.3 ms, worst gap 61 to 71 ms; the game-over box 33 to 49 ms. Paint plus send is about 50 ms, so the 60 ms pace sets the rate. A shorter pace gains little until the send shrinks: slice 5 (partial sends) is the next step toward smaller steps.

## P533 slice 5: partial show

- What changed: the driver marks the 16 px tiles each draw touches (`_setpixel`, `_fill_rect`, `blit_buffer`; `fill` and the other direct writers mark all). `show()` sends the tiles drawn in this frame or the one before, as windows: runs along each tile row, joined down when the columns match. Whole rows go straight from the internal framebuffer, the rest through the two strips. Past `windows` (40) it sends the whole frame. `TftOut.draw` paints the background and the still picture with `tft.track(False)`. A game switch sends one whole frame. `show()` returns the count of windows it sent.
- 11:20 run 20, flappy with `config(partial=True)` (`run20` log in the scratchpad): send 38 ms, worse than 31. The probe counted about 200 windows a frame.
- 11:30 cause, an upstream bug: the constructor's index list lacks `ARG_idle_mode`, so `dma_rows` read `idle_mode` (true, 1) and `options` read `dma_rows` (16, no wrap bits, harmless). Every strip held one row of 320 pixels. Slice 3's "strips 71.9 ms, overlap gains nothing" was measured with one-row strips, so it says nothing about real strips. Fixed: strips of 16 rows.
- 11:35 probe7, one rectangle per frame: an unchanged frame 0.08 ms; one 16 px tile 0.35 ms; a 240x16 band 1.78 ms; a 16x240 column through a strip 1.85 ms; a full frame 31.0 ms.
- 11:40 probe6, 120 frames per game played by a fixed tap pattern, 40 ms pause per frame, avg per state:

| game | tile | play: windows, send | game over: windows, send |
| --- | --- | --- | --- |
| flappy | 8 | 21, 10.1 ms | 31, 21.4 ms |
| flappy | 16 | 14, 11.3 ms | 25, 21.3 ms |
| flappy | 32 | 11, 15.0 ms | 16, 26.5 ms |
| runner | 8 | 16, 7.1 ms | 27, 17.9 ms |
| runner | 16 | 7, 7.7 ms | 18, 18.3 ms |
| runner | 32 | 8, 13.0 ms | 13, 25.1 ms |

- Tile 16 stays the default: tile 8 saves about 1 ms with twice the windows. The plan's pass number (flappy send under 15 ms) holds while playing. Still owed: the PO's eyes on a 2-minute run through title, play, game over and three switches, for stale pixels, and the `PARTIAL = False` comparison.
- Left: the score bar redraws its same pixels every frame, so its tiles go out every frame. Drawing it untracked while the score stays the same would save more. Not done here.
- 11:29 to 11:31 run 21, all games at the 60 ms pace with partial show: 16 fps everywhere (the pace). Send: flappy 14 to 17 ms, runner about 8, snake about 4. No errors. The PO: "Nice, really nice!"
- 11:36 to 11:38 run 22, `FRAME_MS = 40`: flappy 21 to 24 fps, runner 20 to 21, stack 24. Runner's paint is 34 ms a frame, and the slowest frame of each interval has a paint of about 60 ms (worst gap 70 to 80 ms). Paint now sets the rate, not the send: the C drawing in P537 is the next lever.
- 11:40 the PO on run 22: "I saw it, looks great." No stale pixels reported through title, play, game over and switches. Slice 5 passes.

## P533 slice 4: every setting

`tft.config(**kw)` applies all or none and returns every setting. `tft.config()` only reads.

| key | default | effect | slice |
| --- | --- | --- | --- |
| `timeout` | 100 | the longest time one `show()` may take, 1 to 60000 ms; past it `OSError(ETIMEDOUT)` | 3 |
| `framebuffer` | "dma" | "dma": internal RAM, sent with no copy; "strips": PSRAM, copied through two internal strips. Before `init()` only | 3 |
| `partial` | False | send only the tiles drawn in this frame or the one before | 5 |
| `tile` | 16 | the tile's side: 8, 16 or 32 px | 5 |
| `windows` | 40 | past this many rectangles, send the whole frame; 1 to 64 | 5 |
| `swap` | the bus's `swap_color_bytes` | swap the bytes of each pixel on send; needs "strips" | 4 |
| `defaults` | (none) | True restores every setting first, then applies the others given | 4 |

- 11:55 probe8 at the REPL, every line as expected. Before `init()`: `config(swap=True, framebuffer="strips")`, then `init()` keeps both, and `show()` sends 16 strips of 21 rows. After `init()` in "strips", `swap=False` applies. With "dma": `bogus=1` raises `TypeError: config() has no setting 'bogus'`; `tile=12`, `tile="16"`, `timeout="x"`, `timeout=0`, `windows=65`, `partial=1`, `framebuffer=3` and `defaults=1` each raise ValueError naming the key and what it allows; `swap=True` and `framebuffer="strips"` after `init()` raise ValueError saying to set them before `init()`. `config(timeout=50, tile=12)` raises and changes nothing. A call with every key, `config(**config())`, `defaults=True` and `defaults=True, partial=True` all return the expected dict.
- Slices 6 (TE sync) and 7 (scroll) stay out: this module has no TE line (plan E5), and scroll does not fit the games (E7).

## P533 review

A reviewer (Sonnet) and a refuter (Opus) read the driver diff since slice 3 (9ff1d42 to e99de50). Both found strip reuse, the window count, the timeout drain, the tile marks and the windows right. Fixed after the review:

- MUST (both): `deinit()` after a timed-out `show()` deleted the semaphore and freed the memory while the frame was still on the wire; the bus interrupt then gave a NULL handle and FreeRTOS aborted. Now `deinit()` deletes the panel and the bus first (that waits for the windows on the wire), then frees the frame. The interrupt skips a NULL handle, and `frame_free` clears it before the delete.
- `config(defaults=True)` could bring a swap back onto an internal framebuffer, which sends whole rows raw and other windows swapped. The swap check now runs on the result.
- A second `init()` leaked the frame's memory. It now raises `OSError: init() again: call deinit() first`.
- A 1 ms timeout could end before any time passed (the start is read part way through a tick). The wait has one tick of slack now.
- The range messages repeated the limits as bare numbers. They are built from the `#define`s and name the key (`timeout must be 1 to 60000`).
- `png()` draws through `_fill_rect`, so with tracking off it marked nothing, unlike the `track()` docstring. It marks the whole frame now. `png_write` only reads, so its mark is gone.
- Docs: the timeout is checked at each wait, to within one tick, and esp_lcd's own waits have no limit, so a dead bus still hangs. After a fallback, `framebuffer="dma"` is still accepted. esp_lcd waits for the last window before it starts the next, so the strip wait is a guard. A game switch sends two whole frames (the "before" marks), not one.
- 12:20 probe9 on the board: the refuter's crash steps (`timeout=1`, `show()` raises, `deinit()`) pass; a timed-out frame left for a soft reset, then `soft-reset`, passes; a second `init()` raises; `defaults=True` on a swapping bus with "dma" raises and changes nothing; the messages name the key. probe6 after the soft reset: flappy 11.2 ms in play, runner 7.7 ms, as before.

- 12:31 the board was dark after a power-off (no Espressif device on USB, replug did not help). The schematic (V1.0, AXP313A) has no power LED: D3 is the charger STAT LED, LED1 sits on GPIO21 with the backlight. Holding D14 (K1, PWRON) for 1 to 2 s switched the power chip on (a few red blinks), and the port came back. Redeployed: the 11:51 image (current, make rebuilt nothing), all game files and main.py, so the games start at power-on. Serial after reset: flappy 17 fps, then runner, snake, stack.

## P550 (#754), 2026-11-02: what runner's paint is made of

- Plan: `~/.claude/plans/enchanted-marinating-falcon.md`, checked by one refuter. Code 9ec66df: `gfx.PHASE_SUM` and an `avg` line per interval (P537 slice 0 step one), the still picture timed as "static" in `TftOut.draw`, `probe550.py`.
- Per-call costs, no play (`run25-p550-bench.log`, three runs, equal to 0.01 µs): empty loop 2.10 µs, `fill_rect` 8 x 8 5.61 µs, 16 x 240 52.33 µs, `TftCanvas.fill` 8 x 8 113.5 µs, 240 x 16 325.3 µs, full-screen `tft.fill` 2885.4 µs. Tiles tracked as in the games, gc on.
- `TftCanvas.fill` allocates 32 bytes per call, `fill_rect` none (`run27-p550-alloc.log`, and `probe550.bench()` since). A call clipped away, so no C call at all, still costs 155.3 µs and 32 bytes, against 15.5 µs for the raw 8 x 8 `fill_rect` in the same loop. Reading, not measured: the 32 bytes are the 4-tuple that `lcd.py:51` builds (`x0, y0, x1, y1 = max(...), ...`).
- Costs rise as garbage builds up: with gc off, the Python-only call went from 161 to 605 µs between two passes, while an empty call stayed at 5.5 µs (`run26-p550-split.log`). A first split that passed `*args` allocated in the harness itself and is void.
- So the Python wrapper, not the C call, is most of a canvas call's cost. The count per play frame (R2) and the baseline paint (R1) still wait on the PO's play.
- 14:19 to 14:24, R1 and R2 with the PO playing runner, 2 minutes each (`run23-p550-baseline.log`, `run24-p550-count.log`). Pure-play intervals (over and title 0): 18 of 24. Paint 32.61 ms per frame (31.6 to 33.2): static 16.97 (background fill and still picture), game 3.39, fx 1.19, hud 10.96. Fps 21.7.
- Calls per play frame (11 reports of 125 play frames): still picture 42 small and 127 large, game 160.7 small and 3.0 large, 333 in all, 92,297 px. No line calls.
- D7 verdict: calls priced at the raw `fill_rect` cost by class, plus the screen fill, are 10.82 ms, 33 % of the paint. Area-scaled: 5.63 ms, 17 %. Both are under 40 %, so the Python side is cut first and measured again. Priced at the bench's `TftCanvas.fill` cost the share is 209 %, impossible, so that price is too high for game conditions (gc on and garbage in the bench) and the share is not used. Per call, all in: 98 µs, of which about 8 µs is C.
- The cut (11e5841): `TftCanvas.fill` without the four-name tuple. Bench (`run28-p550-lean.log`): 8 x 8 169 to 87 µs, clipped away 161 to 80 µs, 0 bytes per call. `probe550.bench()` after it: canvas.fill 8 x 8 40.3 µs, 240 x 16 86.8 µs.
- 14:25 to 14:28, R4 with the cut, the PO playing (`run29-p550-lean-play.log`): pure-play intervals only 6 of 24. Paint 24.40 ms (static 13.25, game 2.22, fx 0.60, hud 8.20), send 7.98, fps 24.0, worst gap 52 ms. So the paint fell by 8.2 ms (25 %), on fewer pure-play intervals than R1.
- What is left: about 80 µs of Python per call even with the cut, and the still picture is repainted every frame. Both are what a batch in C or a kept background (P537 slice 2, P554 #758) removes.

## P562 (#766), 2026-11-02: painted art, the blit cost

- Before (`run34-blit-cost.log`): `blit_buffer` of a full 240 x 320 picture from PSRAM 9.65 ms, a 100 x 320 band 4.07 ms, the screen fill 2.90 ms. It blended every pixel through `alpha_blend_565` with a bounds check.
- d4e4996: `blit_buffer` takes a key colour, and a picture wholly on screen at alpha 255 is copied by rows (memcpy, or every pixel but the key). Refuter: two overflows fixed before the flash. Flashed without buttons (`mpremote bootloader`, esptool write-flash 0x10000, hash verified).
- After (`run35-p562-blit-fast.log`): full frame from PSRAM 2.65 ms, a keyed 16 x 24 sprite 19.8 µs.
- 6968b70: the art from `art/paint.py` (24 pictures, 733,056 bytes; preview `art/preview.png`). a2940e1, a9a9ba3: `pictures.py` draws the sky still and four layers scrolling (clouds 0.08, far 0.2, hills 0.45, ground 1.0) and the sprites, keyed. `art.py` was renamed `pictures.py`: on the board `import art` found the `/art` folder first.
- `run36-p562-art.log`, pictures in the heap: static 3.1 ms (13 to 17 before), send 31 ms (every layer moves, so every frame is a full send), gc 17.5 to 18.8 ms per frame (heap 1.37 MB: each collection scanned the pictures), 12 to 14 fps.
- a9a9ba3: `s3lcd.pool(size)`, one PSRAM block outside MicroPython's heap (8.32 MB free there, `esp32.idf_heap_info`), kept across soft resets. Refuter: no MUST; each layer file now loads once (pool 733,056 bytes, not 1.29 MB).
- `run37-p562-pool.log`, no play: gc 1.2 to 1.4 ms, heap 77 to 86 KB, static 3.0 ms, paint 15.6 to 19.7 ms, send 31 ms, 17 to 19 fps. The full send is now the limit; overlapping it with the paint (P556 #760, slice 4a) is the next lever.
- 686fd6c, 1b9a35f: cacti with an outline and a lit stripe, a 6-frame run cycle and a 5-frame jump, the stack art (973,440 bytes in all). The pool grew, so the board was hard-reset after the copy (a soft reset keeps the first, smaller pool).
- `run38-p563-Runner.log`, `run38-p563-Stack.log`, no play: no errors; runner 18 fps (paint 18.6, send 31.4, gc 1.4 ms, heap 96 KB); stack 23 fps (paint 15.4, send 9.7, gc 1.4 ms, heap 81 KB).
- 88f8b10, 67145d2: flappy painted (P564): a morning sky, clouds 0.15, a hill town 0.3, bushes 0.6, ground 1.0, sandstone pillars with caps at the gap (placed 240 px long, the driver clips them), a bird with 2 wings x 3 tilts. Art 1,506,384 bytes in the pool. The first copy failed when the port dropped ("Device not configured"): the runs after it used the old files and are void. Copied again and checked (55 files), hard reset.
- `run39-p564-Flappy.log`, `run39-p564-Runner.log`, no play, mostly on the game-over screen: no errors, heap 80 to 88 KB; flappy 14 fps (paint 32.5, send 31.4 ms), runner 15 fps (paint 30.0, send 31.4 ms). Fps in play waits on the PO's play.

## P556 (#760), 2026-11-02: overlap the paint with the send, slice 0 probe

- Plan: a "double" framebuffer, the frame in PSRAM, an internal buffer for the send. A frame costs copy + max(step + paint, send). The probe asks what painting into PSRAM costs, with no firmware change: `framebuffer="strips"` keeps the frame in PSRAM.
- `run40-p556-{dma,strips}-{Flappy,Runner}.log`, no play, about 14 s each; the second interval is steady (game-over screen).
- Flappy: paint 32.9 ms internal, 41.3 ms PSRAM (+8.4, +26 %). Runner: 30.1 against 39.8 (+9.7, +32 %). Step 0.3 in both.
- The strips send of a full frame is 33.5 ms (the old 71.9 ms number was void). gc 3.1 ms with the frame in MicroPython's heap against 1.3 ms: the collector scans it. So the "double" frame goes outside that heap.
- Gate: step + paint in PSRAM is 40 to 42 ms, over the 31 ms send, so the overlap is not full. Expected frame: 3 + 41 = about 44 ms, against 64 ms now (14 to 15 fps to about 22). The card's rule holds: the frame gains about 28 ms, more than the 9 ms the PSRAM paint costs. So slice 1 goes on. The 40 ms pace needs a smaller paint as well (kept background, P554 #758).
- Slice 1a, "double" in C: the frame in PSRAM outside MicroPython's heap, `outgoing` in internal DMA RAM, `show()` copies the windows there, queues them and returns. Built (no warning), flashed, hash verified. `probe556.check()` twice with a soft reset between (`run41-p556-check.log`): `config(**config())` round-trips with `framebuffer='double'`; a full `show()` returns after 3.4 ms (the copy), the next one waits for the send (33.4 ms in all); free memory is the same before init and after deinit (PSRAM 6,813,040, largest internal block 188,416; 31,744 while it runs).
- Slice 1b, lcd.py `FRAMEBUFFER = "double"` (`run42-p556-double-*.log`, no play, steady interval, against "dma" in run40/run42): flappy 14 to 20 fps (paint 42.7, send 3.2 ms), runner 15 to 21 (40.7, 3.2), stack 23 (run38) to 24 (15.7, 4.1). Tunnel 14 in "dma" (44.7, 20.8) and 13 in "double" (49.9, 19.3): it sends many windows, and esp_lcd starts each one only when the last ended, so `show()` waits for all but the last.
- Windows (`run43-p556-w*.log`): past 4 windows a whole frame goes out in the background, so tunnel is 17 fps at 4 windows and 16 at 1; stack 24 at 1, 4 and 40. lcd.py sets 4 for "double": one run per value, so a first pick within noise of 1.
- Pace (`run44-p556-pace*.log`, windows 4): at 40 ms flappy 20 to 22 fps, runner 21 to 24, worst gap 63 to 69 ms. At 50 ms 19 to 20 fps, worst gap still 62 to 73, because the slowest frames paint in 48 to 52 ms (frames of 52 to 64 ms). So 50 ms buys no even pace here, and `FRAME_MS` stays 40. The limit is now the paint, about 39 to 43 ms in PSRAM (8 to 10 ms of it the PSRAM cost, slice 0); the next lever is a smaller paint (P554 #758, the kept background). Done criterion "40 ms pace held" is not met; the PO's play judges what it feels like.
- Review (Sonnet reviewer, Fable refuter): no MUST in the code; the refuter's MUST was a wrong number here (the pace bullet), fixed. Renames `frame_queue_copy`, `packed_pixels`; the mode names by designated initializer; stale docs of `swap` and `.show()` fixed. Rebuilt and flashed (hash verified). `run45-p556-*.log`: flappy 20 to 22 fps as before; tunnel 18 fps at 2 windows and 14 at 8 (16 at 1, 17 at 4), so 2 to 4 is the best range and 4 stays. Three soft resets with flappy sending, then `probe556.check()`: free memory the same as before (PSRAM 6,813,040, internal block 188,416), and init works again each time.

## P567 (#772), 2026-11-02: what the new art costs, per primitive

`probe567.py`, the real pictures in s3lcd.pool, drawn in TftCanvas.picture's panel shape; `run46-p567-double.log` (the frame in PSRAM, as the games run since P556) and `run46-p567-dma.log` (the internal frame). Per call over n calls, a loop of empty calls taken off. Written before the run: a full-frame blit about 2 ms more in "double".

| what | "double" | "dma" | unit |
| --- | --- | --- | --- |
| full-frame blit, opaque (sky 320x240) | 6.83 | 2.58 | ms |
| full-frame blit, keyed | 6.86 | 3.56 | ms |
| sprite 16x24, keyed, warm (1000 at one spot) | 23.76 | 23.10 | µs |
| sprite 16x24 right after a full-frame blit (50) | 67.80 | 52.32 | µs |
| largest sprite (cactus64, 20x64), warm | 47.23 | 53.83 | µs |
| sprite 16x24 half off screen (clip path, through Python) | 59.52 | 69.08 | µs |
| 64x64 at alpha 128 | 1382.49 | 1324.77 | µs |
| the same, per pixel | 337.52 | 323.43 | ns |
| TftCanvas.picture, 16x24 (Python + blit) | 33.29 | 42.45 | µs |
| pictures.draw, 16x24 (as the games call it) | 69.43 | 71.43 | µs |
| Python physics: 30 spring bodies + 40 particles, one update | 5.69 | 5.71 | ms |
| Python physics: 40 particles alone, one update | 2.27 | 2.28 | ms |
| art load at start (pictures.load, 1507152.00 B) | 2154.00 | 2152.00 | ms |

Memory after deinit ("double" run; "dma" within 420 B): PSRAM free 6747500.00 B, its largest block 6553600.00 B; internal largest block 188416.00 B; gc free 6603376.00 B, gc alloc 78304.00 B; a 4,000,000 B bytearray allocates (the substitute for A4's pool test: a larger pool needs a hard reset, so not run). Flash file system 12800000.00 B free of 14680064.00 B; art on the board 1507152.00 B.

- The full-frame blit costs 4.25 ms more into PSRAM (opaque) and 3.30 ms more (keyed), about twice the 2 ms written before the run. One opaque and four keyed full-frame layers would pay about 17 ms more than in the old frame (4.25 + 4 × 3.30); the P556 slice 0 paint difference was 8.4 to 9.7 ms. Why they differ is not checked: slice 0 ran "strips", and its layers are not all full frames.
- Small sprites cost the same in both frames when warm (23 µs); right after a full-frame blit the 16x24 sprite takes 67.8 µs in PSRAM against 52.3 µs (a raw timer bracket, so it holds the timer's own cost, which the warm rows have taken off). Through Python a sprite costs 69 to 71 µs warm (pictures.draw), so 30 sprites cost at least 2 ms.
- Python physics costs more than the tech lead's bound of 1.75 to 3.5 ms for 30 bodies and 40 particles (council/tech-lead.md PHYS-3, calculated): 57 µs per particle and 114 µs per spring body per update. 40 particles alone are 2.3 ms, 30 bodies and 40 particles 5.7 ms. So A5's pass line (under 3 ms) fails for the full set and holds for 40 particles alone. The ways out are fewer bodies, viper or fixed point in Python (A5's fallback), or effects in C (P580 #771, the PO's D2); the tech lead notes that a C emitter reopens the rule that the C layer draws and decides nothing (TL-15).
- Translucency costs about 330 ns per pixel: a full-screen fade would be about 25 ms, so a fade fits a title or game-over moment, not play.
- Flash is not a limit (12.8 MB free); PSRAM is the shared limit of the pool, the frame and MicroPython's heap.

## P568 (#774), 2026-11-02: stack as RENT, the PO's play test

- Written before the play (A1, the P565 discovery): the system the theme aims at is "speculative housing: flats as investments, nobody lives there". The PO is not told this; his own words are matched against it afterwards.
- Pass line (D3): his verdict "exciting" or stronger, and the average fps in pure-play intervals (title 0 and over 0 in the `phases` line) at most 2 below the same average before; at least 6 pure-play intervals in each run.
- Before (`run47-p568-before.log`, the P572 state on the board, the PO playing stack 3 minutes): 23 pure-play intervals; averages fps 24.09, paint 21.41 ms, send 3.53 ms, worst gap 48.39 ms (computed by a parser over the `time` and `phases` lines; the first interval after the switch dropped). The after run must hold at least 22.09 fps.
- After (`run48-p568-after.log`, RENT on the board after a hard reset, the PO playing 3 minutes): 9 pure-play intervals (at least 6 needed); averages fps 24.00, paint 19.89 ms, send 3.20 ms, worst gap 50.67 ms. Against before: fps -0.09 (the line allows -2), paint -1.52 ms (only the visible floors are drawn now). Fewer pure-play intervals than before (9 against 23); shorter rounds under the swing are a likely cause, not checked.
- The PO's words, verbatim: "yeah, its good. I don't like how it moves unpredictibly, we could change that back to the original linear motion".
- Against D3: the fps half passes; the verdict "good" is below "exciting", so slice 0 does not pass yet. A1: he did not name the system the theme aims at, so "the theme reads while playing" is not shown.
- 1f55f98: the hanging floor slides straight again, as he asked; the tower's settling sway stays.

## P589 (#790), 2026-11-03: what a C step costs

`probe589.py` (removed in P590; its last version is at c325d40) on the engine image (`./build.sh engine`: s3lcd plus the probe module `engine`, sha256 1dd3f2cb714a563b before the A8 edit, not rebuilt since, `-O2` from `CONFIG_COMPILER_OPTIMIZATION_PERF`, 223,120 B left in the app partition). The baseline is `fall_bodies` from p582-heavy 21c0b09 (`games/motion.py`, `@native`). Three runs in one boot at 11:17 CET, `run53-p589.log` (git-ignored, kept on the Mac). Each value is the median of the three runs. The timings of the three runs differ by 0.01 µs at most. The alloc lines differ by up to 128 B. The scene: g 2000 px/s², a 10 ms step, restitution 0.35, friction 0.6, 12 bodies, 6 blocks of one load and 100 steps. A frame is 6 steps. The pass lines were written before the run, in risks-and-tests.md.

| what | value | unit | pass line | verdict |
| --- | --- | --- | --- | --- |
| today's `fall_bodies`, per body-step (fall scene) | 36.95 | µs | baseline | |
| today's `fall_bodies`, one frame of 12 bodies and 6 steps | 2.66 | ms | baseline | |
| C float step, per body-step (fall scene) | 0.135 | µs | | |
| C float step, one frame (0.135 × 72) | 9.7 | µs | A3: under 2 ms | lower bound only |
| C fixed-point (Q16.16) step, per body-step | 0.211 | µs | D16: a number only | |
| C fixed-point step, one frame (0.211 × 72) | 15.2 | µs | | |
| C step, one frame through one Python call (both modes; 16 calls of 6 steps) | about 0.02 | ms | | |
| bounce scene, per awake body-step: Python, float, fixed | 37.60, 0.142, 0.211 | µs | | |
| drain of 16 events into an `array('i')`, read in Python | 162.5 | µs | | |
| step plus drain, per frame | about 0.18 | ms | A2: under 0.5 ms | passes |
| one C-to-Python call (1,000 timed) | 5.34 | µs | A2: over 60 µs fails | passes |
| 12 Python list reads of `bodies.y[i]` | 32.35 | µs | | |
| `engine.read_y` plus 12 reads of its `array('f')` | 60.03 | µs | | |
| one Python-to-C call of `engine.nothing()`, loop included | 2.60 | µs | | |
| one edit-to-import cycle: build 32 s, flash 12 s, first import 4 s (timed by `date` in the shell, no log file) | 48 | s | A8: under 5 minutes from edit to play | passes; play adds the game's start |

- The C float step is about 274 times faster than today's `fall_bodies` per body-step. The sanity lines compare y only, in the bounce scene: after 6 and after 100 steps, C (both modes) and `fall_bodies` differ by 0.0001 px at most. The fixed step rounds `v / rate` toward zero, so its work is close to the float step's, not the same.
- The Python bracket leaves gc on, so a collection inside it counts in the baseline, as it does in a game. `fall_bodies` allocates 127,600 B in 600 calls, so 213 B per call, or about 31 kB/s at 6 steps a frame and 24 fps. The C step allocates 0 B.
- Fixed-point is about 1.56 times slower than float in scalar C. The S3 has a hardware float unit, and the fixed step pays for int64 products. PIE SIMD was not measured. A PIE path works on integer lanes, so this row is the base it would start from, not its speed.
- A3 has a lower bound only: this step has no contacts and no rotation, and a rigid step costs more. A3 stays open.
- The step and the calls are small next to the drain: 162.5 µs for one C call and a Python loop over 48 ints. That the loop costs most of it is calculated from the 2.60 µs call, not measured. Reading 12 values back from C costs more than 12 Python list reads (60.03 against 32.35 µs). So a design that sends every body back to Python each frame pays for the read, not for the step. B draws in C and avoids that read.
- The 5.34 µs C-to-Python call settles the PO-29 disagreement: the 5.5 µs stand-in in TL-14 held, and the 20 to 60 µs estimate was high.
- Builds: the first `./build.sh engine` took 1 min 34 s (cold build directory). An incremental `./build.sh s3lcd` took 36.9 s. It gave sha256 9c22d6b6f3951c99, not the sha of the image built on 2026-11-02 in the same folder, with the same size (1,806,224 B). The cause was not looked for.
- The A8 edit was `1.5f` to `1.6f` in `engine/core/world.c:66` (the rest speed), reverted after. The flash was without buttons, as in line 83 above, with the hash verified.
- Restore: `build-s3lcd/micropython.bin` (9c22d6b6f3951c99) flashed back, hash verified. After the reset, the games started on their own: flappy at 21 fps (`restore-p589.log`).

## P593 (#794), 2026-11-03: the rain, the C engine on screen

The engine image (`./build.sh engine`, sha256 2a519b269b3bb482, 222,576 B left in the app partition) with `games/rain.py` first in `GAMES`. Each mode ran through `mpremote run` with `app.run()`. The Python mode ran with `rain.engine = None`: the same `PythonStepper` a BOOT tap reaches, but its HUD label "python, no C" is 6 glyphs longer, so its fps is slightly low. Logs (git-ignored, kept on the Mac): `run54-p593-rain-c.log` and `run54-p593-rain-py.log` at N = 192, `run55-p593-rain-c160.log` and `run55-p593-rain-py160.log` at N = 160, `run56-p593-smoke.log` for the games. The values are per frame, from the `rain` lines (5 s intervals).

| N | stepper | fps | step | read | draw | unit |
| --- | --- | --- | --- | --- | --- | --- |
| 192 | C | 23 | 0.18 to 0.19 | 1.28 to 1.34 | 16.11 to 16.68 | ms |
| 192 | Python | 6 to 7 | 34.39 to 35.64 | 7.28 to 9.44 | 29.92 to 56.41 | ms |
| 160 | C | 24 | 0.16 to 0.17 | 1.06 to 1.14 | 13.47 to 14.01 | ms |
| 160 | Python | 7 to 8 | 28.89 to 29.83 | 5.78 to 6.86 | 25.04 to 44.83 | ms |

- N is 160: the most of the two tried that keeps C at 24 fps. At 192, C ran at 23 fps.
- The HUD text costs 10.6 to 10.9 ms a frame in C mode at 160 (9.7 to 10.7 at 192) (`avg rain ... hud`), more than the plan's guess of 3 to 8 ms. That is why 192 missed 24 fps.
- At 160 boxes, the C step is about 175 times shorter than the Python step (0.17 against 29.8 ms). The fps differs about 3 times. Python mode also draws 2 to 4 times slower (draw 25 to 45 ms against 14, HUD 43 to 47 ms against 11), and its draw grows during the first 20 s. Its heap allocation is 200 to 487 kB against 99 kB, which points at gc, but the cause was not looked for.
- Defect found on the board: the C world outlives a soft reset, so a run at 192 left 192 bodies, and the run at 160 raised `ValueError: an array('h') of 3n ints is needed`. Fixed in 5b72b20 (the rain loads exactly N bodies first), with a Mac test.
- Smoke test on the engine image: all ten games start and print fps lines, with no error (snake 24, cave 22, tunnel 22, road 21, starfire 24, cube 24, gravpong 24, runner 20 to 23, stack 25, flappy 21 then 18, on its game-over screen). Three needed 16 s instead of 9 s to print their first fps line.
- The first `mpremote run` after an `mpremote cp`, and a `cat` of the port after a reset, printed nothing, as on 2026-11-01 (line 54). A second run works.
- Free internal RAM at start was not measured: the logs hold only `mem 8029760`, the total with PSRAM. The plan asked for it.
- The board keeps the engine image. The rain starts at power-on.

## P595 (#796), 2026-11-03: the fire, the first native effect

The engine image (`./build.sh engine`, sha256 389c0020b31b0f86, 220,768 B left in the app partition) with `games/fire.py` first in `GAMES`. The field is 160 x 120 cells, drawn at 2 x 2 px over the whole screen, one kernel step per 40 ms (`DECAY` 31). Each mode ran alone through `mpremote run` for about 40 s, started by a small script in that mode, because a BOOT tap needs a hand. Logs (git-ignored, kept on the Mac): `run57-p595-fire-B.log`, `run57-p595-fire-A.log`, `run57-p595-fire-picture.log`, and `run58-p595-smoke.log` for the games. Step plus draw is brief.md's one formula: the `time` line's step plus the same interval's `avg` paint. A2's line is 15.3 ms (risks-and-tests.md), and each row holds every 5 s interval of its run.

| mode | intervals | fps | step | paint | step + draw | static | hud | unit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B: C writes the s3lcd frame | 7 | 24 to 25 | 3.1 to 3.2 | 4.6 | 7.7 to 7.8 | 0.1 | 11.3 to 12.6 | ms |
| A: C fills a buffer, Python blits it opaque | 7 | 23 to 24 | 3.3 | 11.7 | 15.0 | 0.1 | 11.0 to 11.5 | ms |
| picture: the buffer at alpha 128 over the sky | 7 | 15 to 17 | 4.2 to 4.5 | 22.5 to 25.5 | 26.7 to 30.0 | 7.1 | 14.8 to 17.0 | ms |

- A2 passes on both paths, B with room (7.7 to 7.8 ms) and A by 0.3 ms (15.0). B is about half of A's cost, so B stays and A's opaque mode is dropped (D7, commit e968acd). The fire swaps B and the sky variant on a BOOT tap.
- The fire's own lines split B's cost: the kernel step 2.67 to 2.73 ms and the draw into the frame 4.31 to 4.34 ms. The discovery's estimate was 7.6 to 7.7 ms (★C11, H), and the run gives 7.7 to 7.8 ms.
- A9 passes: the largest free internal block at the scene's start is 31,744 B in every run, and the 19,200 B field went to internal RAM (`fire field internal`).
- A3, with no pass line: the blended step plus draw is 26.7 to 30.0 ms, 3.5 to 3.9 times B's and 1.8 to 2.0 times A's, plus 7.1 ms of `static` for the sky's keyed blit, which a game pays too. The discovery expected about 33.6 ms (H).
- The fps print is 24 or 25 in B. A2's room is not the fps limit: the HUD text still costs 11 to 13 ms a frame (P599 #800).
- Smoke test after the drop: all eleven other entries start and print fps lines, with no error (rain 24, flappy 19 to 22, runner 20 to 23, snake 24, stack 24 to 25, cave 20 to 22, tunnel 19 to 22, road 13 to 21, starfire 20 to 24, cube 22 to 23, gravpong 24). Road's 13 is one interval. P593's smoke run printed 21 for it.
- The two-mode cycle after the drop was not timed on the board. Its picture path is the one timed above, and a Mac test covers the tap.
- The board keeps the engine image. The fire starts at power-on, with the rain second.

### P595 part 2, 2026-11-03: the fire's look (the PO's "Both")

The PO saw the first fire and said it "looks a bit uniform" (#796). He chose hot spots at the base, a rising cooling map that cuts the flames into tongues, and a random sideways shift. The numbers were set by eye on Mac renders of the C kernel (decay 33, cool 24, sway 1, 12 spots, spread 16): decay 34 ran away to white columns, cool 64 kept the flames low, and the look stayed stable over 2,000 steps. The engine image (`./build.sh engine`, sha256 2009d38f7e67b498, 219,728 B left in the app partition by its size line). Logs: `run59-p595-look-B.log`, `run59-p595-look-picture.log`, `run60-p595-look-smoke.log`.

| mode | intervals | fps | step | paint | step + draw | static | hud | unit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B, the new look | 6 | 24 | 5.6 to 5.7 | 4.5 to 4.6 | 10.1 to 10.3 | 0.1 | 10.1 to 12.2 | ms |
| picture, the new look | 6 | 15 to 17 | 7.4 to 8.0 | 20.6 to 23.3 | 28.0 to 31.3 | 7.1 | 14.5 to 16.9 | ms |

- A2 still passes on B: 10.1 to 10.3 ms against 15.3. The look costs about 2.5 ms a frame: the kernel step grew from 2.67 to 2.73 ms to 5.07 to 5.19 ms (the fire's own lines), and the draw stayed at 4.30 to 4.32 ms. The lead's guess was 1 to 1.5 ms.
- In the picture mode the same kernel step takes 6.96 to 7.53 ms, about 2.3 ms more than in B. The cause was not looked for. The blend's reads of PSRAM may slow it.
- A9: the field and its map, 23,296 B in one block, went to internal RAM. The largest free internal block at the start was 31,744 B, as before.
- Smoke test: all eleven other entries start, with no error. Road printed 21, 13 and 11. Road was also low in the part 1 run (13), and P593 printed 21 for it.

### P595 part 3, 2026-11-03: different rise speeds, wind and embers

The PO saw part 2 and said all the heat rises "at the same speed", and later that "three columns" rise together (#796). Part 3: no cell gets hotter than the hottest cell it reads (a bound: no cell outgrows its source), a cooling map 256 x 32 that never repeats across the field (the three columns), fast patches whose heat jumps two rows a step (fast 128), wind gusts from Python (up to 60, a new gust every 1.5 to 3 s), up to 24 embers (embers 40), and a fade of 4 sixteenths a row. The Mac stability test (seeds 1 to 5, 7 and 595, 5,000 steps) keeps every top-10-row mean under 48, the highest 40.2 (seed 4). The line holds for those seven seeds, not for every seed: the refuter found seed 31 at 49.1, still bounded (its hottest cell 182). The engine image: sha256 900f13c4a626027f, 218,960 B left in the app partition (build output). Logs: `run61-p595-rise-B.log`, `run61-p595-rise-picture.log`, `run62-p595-rise-smoke.log`.

| mode | intervals | fps | step | paint | step + draw | static | hud | unit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B, part 3 | 6 | 24 | 7.0 to 7.2 | 4.5 to 4.6 | 11.5 to 11.8 | 0.1 | 11.9 to 13.1 | ms |
| picture, part 3 | 6 | 15 to 16 | 9.3 to 10.0 | 21.4 to 24.1 | 30.7 to 34.1 | 7.0 to 7.1 | 13.9 to 15.7 | ms |

- A2 still passes on B: 11.5 to 11.8 ms against 15.3. Part 3 costs about 1.5 ms a frame over part 2: the kernel step grew from 5.07 to 5.19 ms to 6.53 to 6.69 ms (the fire's own lines). The draw stayed at 4.29 ms.
- A9: the field and its wider map, 27,392 B in one block, went to internal RAM. The largest free internal block at the start was 31,744 B.
- Smoke test: all eleven other entries start, with no error. Road printed 21, 12 and 12, as low as in the part 1 and part 2 runs.

## P599 (#800), 2026-11-03: the HUD drawn once into a strip

The engine image 900f13c4a626027f, unchanged: P599 changes Python only. Each HUD is drawn into a panel-order strip when its text changes (`cv.keep`), and the strip is blitted every frame. Each game ran alone through `mpremote run` for about 40 s, first with master's `games/*.py`, then with the branch's. Logs: `run63-p599-before-<game>.log`, `run64-p599-after-<game>.log`, `run65-p599-smoke.log`, and the probes `run66` to `run72`. Hands-off flappy and runner die in seconds, so their rows hold the intervals after the first, all in the game-over state, which draws the HUD too. The values are per frame, from the `time`, `avg` and `phases` lines (5 s intervals).

| game | run | intervals | fps | paint (`time`) | hud (`avg`) | hud slowest | game draw | over | unit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rain | before | 8 | 23 | 32.1 to 34.1 | 11.1 to 12.8 | 15 to 17 | 16.0 to 16.4 | 0 | ms |
| rain | after | 8 | 23 to 24 | 25.5 to 29.1 | 1.7 to 2.5 | 24 to 28 | 18.6 to 22.0 | 0 | ms |
| flappy | before | 6 | 18 | 45.7 to 46.3 | 9.1 | 11 | 12.3 | 16.5 to 17.2 | ms |
| flappy | after | 6 | 20 | 41.7 to 41.9 | 0.8 | 0 | 12.6 | 20.6 to 20.8 | ms |
| runner | before | 6 | 20 | 42.1 to 42.4 | 8.7 to 8.8 | 12 | 10.1 | 15.6 to 16.0 | ms |
| runner | after | 6 | 21 | 37.7 to 38.1 | 0.9 | 0 | 9.9 | 19.2 to 19.6 | ms |

- The HUD drops to 0.8 to 0.9 ms in flappy and runner, under the card's 1 ms, and their fps rises by 1 to 2. The refuter expected 0.5 to 0.7 ms. Their `hud slowest` is 0 because the score did not change in these intervals, so no redraw ran (the field prints whole ms).
- The rain misses the 1 ms line: its HUD averages 1.7 to 2.5 ms, because its label changes every 500 ms and each redraw costs 24 to 28 ms in one frame. With the strip drawn once and never again (probe E10, `run70`), the rain's HUD is 0.9 ms. A redraw through a FrameBuffer with no Python wrapper costs 16 ms (probe E12, `run71`). The redraw makes the rain's worst frame worse: its slowest frame grew from 45 to 46 ms to 57 to 64 ms, a hitch twice a second where the old HUD never took more than 17 ms.
- The whole paint still drops by about 4 to 8 ms a frame in each game. It drops less than the HUD alone, because other draws got slower: the rain's own draw by 2.5 to 6 ms, and the game-over box by about 4 ms.
- Why those draws got slower is not known. Found: on the branch, the rain's draw per frame repeats with a period of 5 frames, the same as the timed collection (`GC_FRAMES`), for example 13.1, 16.0, 23.0, 22.5, 19.7 ms (probe E13, `run72`). E13 marks label changes, not collections, so the phase against a collection is inferred, and master's draw was not traced, so the period is not yet tied to the slowdown. Ruled out, one run each: the blit (E1 without it is slow, E4 master with an extra blit is fast), the frame pace (E5 with no sleep is slow, E6 master at 50 ms is fast), an allocation per frame in `keep` (E7 without it is slow), and the new attribute and buffer alone (E8 is fast). The strip's redraw every 500 ms is the trigger (E10 without it is fast). Not excluded: where the strip buffers landed (PSRAM or internal RAM). The `heap` line spreads by about 1 KB within a run (97.6 to 98.6 KB before, 107.3 to 108.7 KB after), so the garbage per frame is small, under about 0.5 KB. Proposed card: find why a redraw into the strip slows the draws of the frames after it.
- Smoke test: all twelve entries start and print fps lines, with no error. After the first interval, the HUD field is 0.7 to 1.4 ms in the ten games and 2.3 in the fire and the rain (their labels change every 500 ms). Road printed 23 and 15.
- The Mac tests (`tests/test_hud.py`) compare the kept HUD with the drawn one pixel by pixel, at both orientations. Nobody looked at the panel in this run.

## P603 (#804), 2026-11-03: the blend in the panel's byte order

The games keep colours in the panel's byte order (`gfx.c565`, `swap_color_bytes=False`). s3lcd's `alpha_blend_565` cut red, green and blue as if the colours were in normal order, so a blend mixed bits across channels: the fire over the sky showed wrong colours. The blend now lives in `s3lcd/src/blend565.h`. It swaps the bytes of both colours in, blends, and swaps the result back. `tests/test_blend.py` checks it on the Mac against a Python reference. With the old body put back, 3 of its 4 tests fail (refuter).

The fire in picture mode alone (the fire blitted at alpha 128 over the sky), about 40 s each, started by a small script that sets the mode, because a BOOT tap needs a hand. Before: image 900f13c4a626027f, `run73-p603-before-picture.log`. After: the engine image sha256 46d79a3385701c35 (218,208 B left in the app partition), built from bbf7121, `run74-p603-after-picture.log`. The later commits on the branch add parentheses to the swap macro and a comment, with the same compiled code for today's callers. Both runs have the P599 HUD. Each row holds the 7 intervals of 5 s.

| run | fps | paint (`avg`) | paint (`time`) | worst frame |
| --- | --- | --- | --- | --- |
| before | 18 (20 in the first) | 23.3 to 23.9 ms | 32.8 to 36.1 ms | 80 to 94 ms |
| after | 18 to 19 | 22.3 to 25.2 ms | 33.6 to 36.2 ms | 81 to 132 ms |

- The swap costs less than the spread between intervals: the paint did not move by more than about 1 ms either way.
- Three worst frames of the after run were longer (106, 108 and 132 ms). The cause was not looked for. One run each, so this can be noise.
- Smoke (`run75-p603-smoke.log`): all twelve entries start and report fps (22 to 25), with no error.
- Not changed: the indexed `bitmap` path, the PNG loader and the font draws in s3lcd.c build or pass colours in normal order. No game calls them. `bitmap` carries a "Later, not MVP" comment.

### Part 2, 2026-11-04: the alpha follows the heat

The PO saw dark flame sides in part 1: the cool, dark edge cells were blended at the same alpha 128 as the core. Now each heat has its own alpha (`ALPHA` in `games/fire.py`, `heat * 128 // 255`), and a C kernel, `fx_fire_blend`, blends each cell straight into the s3lcd frame. The 153,600 B picture buffer and its blit are gone. Image sha256 cee7185f07870860 (217,728 B left in the app partition), built from the same tree as 78674c4. The run, `run76-p603-alpha-picture.log`, is the same picture script as part 1, 7 intervals of 5 s.

| run | fps | paint (`avg`) | paint (`time`) | worst frame |
| --- | --- | --- | --- | --- |
| part 1 | 18 to 19 | 22.3 to 25.2 ms | 33.6 to 36.2 ms | 81 to 132 ms |
| part 2 | 23 to 24 | 6.9 to 8.5 ms | 17.6 to 19.4 ms | 68 to 84 ms |

- The paint is about 16 ms shorter, because the frame no longer gets a second full-panel pass: the buffer fill and the blit become one blend that skips the clear cells.
- The binding's argument checks have no Mac test (the binding is not built on the Mac). `run76b-p603-args-probe.log` calls `draw` with five bad arguments, a field of the wrong size and three good forms: all nine give the expected result.
- Smoke (`run77-p603-alpha-smoke.log`): all twelve entries start and report fps (20 to 25), with no error.
- The look (2026-11-04): the PO found the half alpha too pale over the light sky. On the panel and on a Mac render of four curves, he picked full alpha from heat 96 up, climbing evenly from clear at heat 0 (`ALPHA_FULL = 96`). The kernel still skips only alpha 0, so the paint cost does not change.

## P596 (#797), 2026-11-04: bodies on fire, the fire on objects

The PO cut the card to the fire on objects (2026-11-04): "Now do the fire and use it on objects, that's a good proof of concept." Eight of the rain's falling bodies each burn heat into one screen-wide fire field (`HeatField.burn`, `fx_fire_burn`), half a frame of their motion behind them, along the path since the last frame. The field's base is off (`fx_fire_set_base`), so only the bodies burn. A sleeping body rests 1.5 s and burns straight up, then falls again. The look (decay 32, cool 40, fade 16, heat 200) was set from Mac frames with `tools/render_scene.py`: the fire's own look climbed to the top of the screen.

Image sha256 9dcce36eb60720d4 (217,120 B left in the app partition), built from 4d466cf. `run78-p596-burning.log`, the scene alone, 7 intervals of 5 s.

| scene | fps | step (bodies, burns, field) | draw | worst frame |
| --- | --- | --- | --- | --- |
| burning B | 24 to 25 | 7.24 to 7.36 ms | 4.26 to 4.27 ms | 42 to 58 ms |

- The draw is the opaque path B (P595: 7.8 ms of step + draw for the fire). The step holds the bodies' 10 ms steps in C, the read-back and 8 burns from Python, and the field's step.
- The binding's new checks have no Mac test. `run78b-p596-args-probe.log` calls `burn` with two good argument sets and eight bad ones, and `set_base` both ways: all as expected.
- Smoke (`run79-p596-smoke.log`): all thirteen entries start, with no error.

## P590 (#791), 2026-11-04: the bodies' step in C behind one API, with events back to Python

`engine.Bodies(n)` replaces the P589 probe's two global worlds: one float `world_t` per object, in its own GC block (in PSRAM), stepped by today's `fall_bodies` maths. Its twin `motion.Bodies(n)` takes the same calls. A step writes each hit (with its speed in px/s) and each new rest as an int event, and the game drains them once per frame. The burning scene flares on a hit at 600 px/s or faster. Image sha256 56f2051a13aa9eed (218,448 B left in the app partition), built from ed75e25 (`build-engine-p590.log`). Logs (git-ignored, kept on the Mac): `run80-p590-rain-c.log`, `run80-p590-rain-py.log`, `run81-p590-burning.log`, `run82-p590-alloc.log`, `run83-p590-smoke.log`. Each scene ran alone through `mpremote run` with `app.run(games=(...))` for 42 s.

| scene | fps | step | read | draw | before |
| --- | --- | --- | --- | --- | --- |
| rain C, N 160 | 24 to 25 | 0.21 to 0.23 ms | 1.05 to 1.11 ms | 9.86 to 10.21 ms | P593: 24 fps, step 0.16 to 0.17 ms |
| rain Python, N 160 | 8 to 9 | 27.69 to 28.51 ms | 7.82 to 9.31 ms | 42.78 to 45.55 ms | P593: 7 to 8 fps |
| burning B | 24 to 25 | 7.48 to 7.60 ms (bodies, flares, field) | | 4.26 to 4.27 ms | P596: 24 to 25 fps, step 7.24 to 7.36 ms |

- Allocation (`run82-p590-alloc.log`): 100 calls each of `step` (4 steps of 160 bodies), `read` and `drain`, in a `gc.mem_alloc()` bracket with gc off: 0 B each, and 0 B for the empty loop. The gate passes.
- Events on the board (same log): three bodies hit at 900, 1,000 and 1,100 px/s, bounce at about 0.35 of that, and each reports `SLEEP` once at rest.
- The rain's C step rose by about 0.05 ms. The world moved from static internal RAM (the probe) into the GC heap in PSRAM. The cause is calculated from that move, not measured apart.
- The draw of the rain fell from 13.5 to 14.0 ms (P593) to 9.9 to 10.2 ms. P599's HUD strip came in between, so this row does not measure P590.
- The burning step rose by 0.2 to 0.3 ms: the drain and the flares from Python.
- Smoke (`run83-p590-smoke.log`): all thirteen entries start, with no error. Road dipped to 14 fps in its second interval, as in earlier smoke runs.

## P607 (#809), 2026-11-04: a body carries an effect, and an event can start one

The engine image 063448a95d2c8b92, unchanged: P607 changes Python only. `games/effects.py` gives each body of a `rain.Stepper` an `effect` slot, and the burning scene runs on it: each body carries a `FireTrail`, and its flare is the reaction to a `HIT`. Each run went through `mpremote run` with `app.run((BurningBodies,))`, after one warm-up run (line 54). The values are per frame, from three 5 s `burning` lines.

| run | code | fps | step | draw |
| --- | --- | --- | --- | --- |
| `run85-p607-before-burning.log` | master's `burning.py` | 24 to 25 | 7.48 to 7.56 ms | 4.26 to 4.27 ms |
| `run86-p607-after-burning.log` | branch a1b9cd2, `*body.place()` | 24 to 25 | 7.64 to 7.75 ms | 4.25 to 4.26 ms |
| `run86b-p607-after-burning.log` | branch, place unpacked first | 24 to 25 | 7.60 to 7.68 ms | 4.25 to 4.26 ms |

- The step rose by about 0.12 ms: one Python call per body more (`Body.place`, then `Effect.update`). The plan's line was 0.3 ms.
- The look on the Mac: `tools/render_scene.py burning` at frames 30, 60 and 120 gives byte-identical PNGs on master and on the branch. The refuter replayed 1,500 frames on both: the same 10,749 `HeatField.burn` calls, in the same order.
- Smoke (`run87-p607-smoke.log`): all thirteen entries start, with no error.

## P608 (#810), 2026-11-04: the smooth fire, bilinear filtering of the heat field

The engine image 167304489f3dbb6a (217,600 B left in the app partition), built from cbbd865 (`build-engine-p608b.log`). `HeatField.set_filter(engine.LINEAR)` draws each cell's 2 x 2 px at centre-sampled bilinear weights (OpenGL's `GL_LINEAR` at 2x), `engine.NEAREST` as the 2 x 2 blocks before. Each mode ran alone through `mpremote run` for 42 s, first in its scene's `MODES`, after one warm-up run. The values are per frame, from seven 5 s lines each. The nearest lines are the before, in the same image.

| run | scene and mode | fps | step | draw |
| --- | --- | --- | --- | --- |
| `run89-p608-burning-linear.log` | burning, linear | 24 to 25 | 7.60 to 7.78 ms | 6.41 ms |
| `run89-p608-burning-nearest.log` | burning, nearest | 24 to 25 | 7.60 to 7.73 ms | 4.26 to 4.27 ms |
| `run90-p608-fire-linear.log` | fire, linear | 24 to 25 | 6.39 to 6.49 ms | 6.42 to 6.43 ms |
| `run90-p608-fire-nearest.log` | fire, nearest | 24 to 25 | 6.40 to 6.49 ms | 4.26 to 4.27 ms |
| `run90-p608-fire-picture.log` | fire, picture (linear blend over the sky) | 23 to 24 | 6.55 to 6.76 ms | 11.51 to 13.32 ms |

- Linear costs about 2.15 ms more a frame to draw than nearest, and the fps holds. The fps cannot show the cost, because FRAME_MS 40 caps it at 25.
- The first image (36f0629's loop, image c923e0de98a9d90a) worked out each pixel's neighbours, clamps and half its sum again for all 76,800 pixels: 12.69 to 12.70 ms of draw, and the picture mode fell to 21 to 22 fps at 18.7 to 20.4 ms. The Fable refuter found the cause. cbbd865 picks each panel row's two cell columns once and slides down them, with the same bytes (the Mac tests).
- The picture mode was not timed with nearest in this image. P603 measured it at 23 to 24 fps, the same as linear's now.
- Args probe (`run90b-p608-args-probe.log`, first image, same binding): `set_filter` takes 0, 1 and True, raises ValueError for 2 and -1 and TypeError for "1" and None, and `engine.NEAREST` is 0, `engine.LINEAR` 1.
- Smoke (`run91-p608-smoke.log`): all thirteen entries start, with no error.

## P602 (#803), 2026-11-04: the flappy bird trails fire

The engine image 5206b1c9bed42b4d (217,312 B left in the app partition), built from the tree at 8fc5d44 (`build-engine-p602.log`, which holds no commit). It adds `HeatField.scroll(dx)` (`fx_fire_scroll`), which moves the field with the world. Flappy ran alone through `mpremote run` for about 45 s with the title (40 s of play measured) under one probe (an autopilot flaps and `die` is off), first with master's `games/*.py` on image 167304489f3dbb6a, then with the branch's on the new image. The values are per frame, from eight 5 s lines each. The probe prints the frames at the 60 ms dt cap and times `FireLayer.update` (the scroll and the field's step) and `FireLayer.draw` (the blend over the picture).

| run | fps | step | paint | send | gc | static | game paint | layer update | layer draw | frames at the cap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `run92-p602-before-flappy.log` | 24 to 25 | 0.7 to 1.0 ms | 20.7 to 22.0 ms | 3.3 to 3.7 ms | 1.9 to 2.0 ms | 7.2 ms | 8.4 to 13.0 ms | none | none | 0 to 1 of about 125 |
| `run93-p602-after-flappy.log` | 21 to 23 | 6.4 to 9.9 ms | 27.4 to 29.8 ms | 3.3 to 3.7 ms | 1.9 ms | 7.2 ms | 13.5 to 20.7 ms | 8.19 to 8.51 ms | 7.58 to 7.72 ms | 1 to 5 of about 108 |

- The fire costs about 16 ms a frame: 8.4 ms to scroll and step the field, and 7.6 ms to blend it. Flappy falls from 24 to 21 fps. The plan's estimate was 16 to 17 fps, from P608's picture mode, which blends a full fire (11.5 to 13.3 ms). The trail leaves most cells at heat 0, which the blend skips.
- The first line of each run holds the title, so it differs from the rest.
- Flappy's 24 fps before is higher than the P599 rows above (20 fps), which were measured in the game-over state.
- The step and the blend are the PO's speed spike's first numbers (P612 #817).
- Allocation (`run95-p602-alloc.log`, after the review fixes): `gc.mem_alloc()` read around every 50th call shows 0 B for `FireLayer.update` (9 samples) and `FireLayer.draw` (10 samples). The heap line of run 93 rises from 124,192 to 131,888 B over its intervals, while run 92's stays at 120.8 to 121.9 kB. The `FireTrail` lag and Flappy's float physics make floats a frame, as on master, so the rise is likely the gc's timing under longer frames.
- Smoke (`run94-p602-smoke.log`): all thirteen entries start, with no error. Burning runs at 25 fps.
- The PO played it (2026-11-04): "it looks good, I'm glad we have this effect, but it doesn't really fit the flappy, so we should remove it, this was just a test, but we could definitely use it in other games." The merged branch keeps the scroll and `FireLayer` with no game on them. Flappy is as on master.

## P598 (#799), 2026-11-04: the ball pit

The board runs `engine.Balls` (`fx_balls.c` on the uniform grid of `grid.c`). The last image is 481959b8587c1502, built from 862e32e (`build-engine-p598h.log`, which holds no commit), with `games/*.py` at 862e32e. Runs 104 to 107 ran on image 74f1d9d27d6003c6 (211,312 B left in the app partition), built from the C at c952675, with `games/*.py` at 9cb3cba. Run 108 repeats run 106 on the last image with the same numbers, and the pit starts at 24 fps (`run108b-p598-smoke-balls.log`). A step is 4 substeps of 2.5 ms and 2 relaxation passes.

| run | what | result |
| --- | --- | --- |
| `run96-p598-balls-s4.log` | 300 balls, the first build | 5 fps, step 165 ms a frame |
| `run97-p598-substep-probe.log` to `run97d` | one substep, 300 balls of r 2 packed | 7.0 ms, then 4.6 (`view_t`: the arrays once a substep), 4.1 (an int cell division), 4.3 (the contact with no `sqrtf` or division) |
| `run98-p598-base-scaling.log` | one substep, spread balls, no contact | 42 µs at 0 balls, 2.1 ms at 300: about 7 µs a ball |
| `run99d-p598-balls-max100.log` | the pit at 100 balls | 23 fps, step 17.9 ms a frame |
| `run100-p598-stream.log` | the PO pours | 95 balls 24 fps, 185 balls 20, 275 balls 11, 320 balls 8 |
| `run106-p598-material-cost.log` | one step of a settled pile, material 0 against the game's (friction 0.5, restitution 0.7) | 100 balls 4.02 against 4.21 ms, 300 balls 13.01 against 13.76 ms: the material adds about 5 % |

- The S3 calls a library routine for each float division and `sqrtf`, so the first build paid one `sqrtf` and four divisions per touching pair in each pass. The contact now uses a fast inverse square root (Lomont 2003) and a table of mass shares.
- The HUD's text rebuild costs about 50 ms twice a second in every scene, which caps a scene near 23 to 24 fps.
- The pit's own log (`run104-p598-pit-material.log`) showed 6 fps and 124 ms a frame at 320 balls, against 8 fps and about 97 ms in run 100 (90 ms in its first sample). The two runs hold different piles at different frame rates, so they do not compare. Run 106 measures the same pile with both materials.
- Allocation (`run106`): 20 calls of step, read and drain allocate 0 B.
- Smoke (`run107-p598-smoke.log`, `games/*.py` at 9cb3cba): all fourteen entries start, with no error, at 22 to 25 fps. The pit runs at 24 fps with its first pour.
- The PO played it (2026-11-04): "Yeah, better. I like it. The bounce could be a bit stronger [...] Let's make it stronger here." Restitution went from 0.5 to 0.7. On the cost: "its ok for a few balls". P614 (#820) makes the solver faster.

## P612 (#817), 2026-11-05: where flappy's frame time goes, and P604's HUD hitch

The image 481959b8587c1502 and `games/*.py` at 184fa2e: the board's 23 game files match master by sha256. Each probe ran through `mpremote run` for about 47 s. In flappy, an autopilot flaps and `die` is off, as P602's probe did. A `part` line is the average over the play frames, timed around each call in `paint_art`. The finding is `docs/discovery/2026-11-05-p612-frame-time/README.md`. The pace is `FRAME_MS`, and the dt cap is the 60 ms limit on a step's time (`gfx.py:341`).

| run | what | fps | step | paint | send | gc | parts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `run109-p612-r1-flappy-nocap.log` | flappy, no pace (`FRAME_MS` 0, a late frame still sleeps 1 ms) | 28 | 1.1 | 22.2 to 22.6 | 7.9 to 8.3 | 2.0 | static 7.3, clouds 2.43, far 2.68, near 2.06, pipes 4.85, ground 1.04, bird 0.27, play 0.44 ms |
| `run110-p612-r2-flappy-fire-nocap.log` | the same with P602's `FireLayer` and `FireTrail` (from 324c23d) | 21 | 10.1 | 30.1 to 30.4 | 3.3 | 2.1 | the fire's step 8.85, the fire's paint 7.78 ms, 32 of 907 play frames at the 60 ms dt cap |
| `run111-p612-r4-flappy-cap33.log` | flappy, a 33 ms pace | 28 | 1.2 | 22.3 to 22.5 | 6.2 to 6.6 | 2.0 | 1 of 1,212 play frames at the dt cap |
| `run112-p612-r3a-rain-redraw.log` | rain, the label redrawn every 500 ms | | | | | | rain paint 12.7 ms over 150 traced frames, strip at 0x3c1dfae0 |
| `run112-p612-r3b-rain-noredraw.log` | rain, the label drawn once | | | | | | rain paint 9.1 ms, strip at 0x3c1dfae0 |
| `run112-p612-r3c-rain-format-only.log` | rain, the label formatted every 500 ms, the strip never redrawn | | | | | | rain paint 9.8 ms, strip at 0x3c1dfb00 |
| `run113-p612-r3d-rain-glyphs-warm.log` | rain, no redraw, the glyph cache filled once at the start (24 glyphs) | | | | | | rain paint 14.4 ms, 18.0 ms right after a gc, strip at 0x3c1dfb70 |

- With no pace, the send grows from 3.3 to 3.7 ms (run92) to 7.9 to 8.3 ms. Its cause is not split.
- In all three rain runs, the paint after a timed gc is the slowest of the 5-frame period: 15.5, 13.9, 12.4, 11.5, 9.9 ms with the redraw, and 11.2, 9.3, 8.7, 8.2, 8.0 ms without it.
- With the redraw, the glyph cache holds 13 glyphs, against 1 without it. R3d, with 24 glyphs and no redraw, paints slowest of all, so the redraw path is not P604's cause (the finding's P604 section).

## P632 (#846), 2026-11-05: the engine and the driver in their own repositories

The engine moved to `xmejkal/pixel-engine` (submodule `engine/`) and the driver fork to `xmejkal/s3lcd` (submodule
`engine/driver/`). No C line changed. The image grew by 32 bytes (1,820,320 to 1,820,352), because `ESP_ERROR_CHECK`
in `s3lcd.c` stores the longer source path. `objdump -d` of all 19 engine and driver objects is the same before and
after. The P612 probes ran unchanged on the new image:

| run | what | fps | paint ms | send ms | against (the same columns) |
| --- | --- | --- | --- | --- | --- |
| `run114-p632-flappy-nocap.log` | flappy, no pace, as run109 | 28 | 21.5 to 22.6 | 7.9 to 9.1 | run109: 28, 21.5 to 22.6, 7.9 to 9.1 |
| `run114-p632-rain-redraw.log` | rain, the label redrawn every 500 ms, as run112a | 24 to 25 | 18.4 to 20.1 | 3.6 to 4.1 | run112a: 24 to 25, 17.5 to 19.8, 3.7 to 4.2 |

## P635 (#850) slice 0, 2026-11-05: what jointed silhouette figures cost in the burning scene

`tools/probe635.py` (run with `mpremote run`, nothing copied) plays `BurningBodies` with figures of 10 bones and a
head disc (a sine walk of 16 baked poses), drawn after the scene's own paint. Each run is 60 s on the image of P632,
at ORIENTATION 0. The go limit is the plan's: 12 figures add at most 8 ms a frame and the scene keeps 23 fps or more
([P635 #850](https://github.com/xmejkal/spark/issues/850), the plan comment).

Per call, 500 calls each, and 200 draws of one pose per figure way (`run116-p635-n0.log`):

| call | us |
| --- | --- |
| `tft.line` 12 px | 17.7 |
| `tft.line` 12 px twice (2 px) | 30.0 |
| `cv.line` 12 px (the canvas wrapper) | 144.4 |
| `fill_circle` r 3 | 20.6 |
| `polygon` 5 points | 79.2 |
| `fill_polygon` 4 points | 18.9 |
| one figure through `cv.line`, 2 px | 2,860 |
| one figure through `tft.line`, 2 px | 348 |
| one figure as 3 open `polygon` chains, 1 px | 119 |
| one figure as one `fill_polygon` band per bone, 2 to 3 px | 231 |

The scene with figures drawn as `fill_polygon` bands (the App's `time` lines, the first line of each run left out,
because it holds the per-call bench):

| run | figures | step ms | paint ms | send ms | gc ms | sum ms | fps | worst ms | figures ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `run116-p635-n0.log` | none | 8.6 to 8.7 | 9.5 to 9.9 | 3.8 to 4.3 | 3.6 to 3.8 | 25.6 to 26.4 | 24 | 54 to 70 | |
| `run116-p635-n6-way3-burn0.log` | 6 walking | 8.7 to 8.8 | 11.0 to 11.7 | 3.6 to 4.2 | 3.6 to 3.7 | 27.0 to 28.3 | 24 | 55 to 63 | 1.78 |
| `run116-p635-n12-way3-burn0.log` | 12 walking | 8.8 to 8.9 | 13.1 to 13.5 | 3.7 to 4.3 | 3.7 | 29.4 to 30.3 | 24 | 55 to 76 | 3.40 |
| `run116-p635-n24-way3-burn0.log` | 24 walking | 9.0 to 9.2 | 16.0 to 16.4 | 3.8 to 3.9 | 3.6 to 3.8 | 32.5 to 33.1 | 23 | 57 to 92 | 6.47 |
| `run116-p635-n12-way3-burn1.log` | 12 burning (a `FireTrail` each) | 10.0 | 12.8 to 13.1 | 3.7 to 4.3 | 3.8 | 30.4 to 31.0 | 23 to 24 | 55 to 89 | 3.29 |

- Decision: go. 12 figures add about 3.8 ms walking and about 4.7 ms burning, and the scene keeps 23 to 24 fps. The
  figures stay in Python, drawn as one `fill_polygon` band per bone plus a `fill_circle` head, with the poses baked
  once as panel offsets. No C painter is needed for the MVP.
- `fill_polygon` fills only the rows strictly between a polygon's top and bottom (`s3lcd.c:2391-2397`). The probe's
  band spans -1 to +2 across rows (2 px for a flat bone, 3 px for a slanted one) and 0 to +1 across columns, so the
  cost errs high. Slice 1's painter uses -1 to +2 only for a flat bone and 0 to +2 otherwise. The first runs (`run115-p635-*`)
  used 1 px offsets, which drew flat bones not at all, so they are left out.
- The canvas wrapper costs 8 times the driver's call (144 against 18 us), so the figure painter calls the driver.
- `polygon` draws an open chain at 119 us a figure, the cheapest, but 1 px only.
- gc is 3.6 ms here against 2.0 ms in run89, because the probe's own code and baked poses add about 54 KB to the
  heap (alloc 177,792 bytes). The baseline run shares it, so the differences hold, but the free time in this scene
  is about 14 ms, not 16 ms. Slice 1 keeps its baked tables small.
- Not checked: the look. Nobody saw the figures on the panel yet. Slice 1's Mac PNG and board run show them.

## P633 (#847), 2026-11-05: the scenes on plugins

Python only, so the image is the one flashed in P632 (`flash-p632.log`). Each scene ran alone through `mpremote run`
with `app.run(games=(X,))` for 42 s, after one warm-up run, first with master's `games/*.py` (1de2019), then with the
branch's (143c879). Rain ran a second pair (`run118`) to see whether its draw gap holds. The values are per frame,
from the scene's 5 s lines (seven each), and paint from the App's `time` lines.

| run | scene | fps | step ms | draw ms | paint ms |
| --- | --- | --- | --- | --- | --- |
| `run117-p633-master-rain.log` | rain, C | 24 to 25 | 0.21 | 9.80 to 11.02 | 16.4 to 17.9 |
| `run117-p633-branch-rain.log` | rain, C | 24 to 25 | 0.26 to 0.27 | 12.00 to 12.36 | 18.3 to 19.3 |
| `run118-p633-master-rain.log` | rain, C | 24 to 25 | 0.21 | 9.80 to 11.54 | 16.4 to 18.0 |
| `run118-p633-branch-rain.log` | rain, C | 24 to 25 | 0.26 to 0.27 | 11.03 to 12.08 | 17.5 to 18.9 |
| `run117-p633-master-fire.log` | fire, linear | 24 to 25 | 6.39 to 6.49 | 6.41 to 6.42 | 9.0 to 9.2 |
| `run117-p633-branch-fire.log` | fire, linear | 24 to 25 | 6.35 to 6.45 | 6.44 to 6.45 | 8.7 to 9.4 |
| `run117-p633-master-burning.log` | burning, linear | 24 to 25 | 7.66 to 7.83 | 6.40 to 6.41 | 9.4 to 9.8 |
| `run117-p633-branch-burning.log` | burning, linear | 24 to 25 | 7.67 to 7.83 | 6.43 to 6.44 | 9.3 to 10.0 |

- The fps is the same in all three scenes. Fire and burning keep their step and draw within 0.05 ms.
- Rain's mean step is 0.05 to 0.06 ms higher: `fixed_update` adds a `StepClock.take`, two tick reads and one call a
  frame.
- Rain's mean draw is 1.0 to 1.7 ms higher (run118 10.55 to 11.52 ms, run117 10.50 to 12.18 ms). The cause is not
  found. run118's master run is a second run: its first five lines equal run117's, and its later
  lines differ. The draw loop is the same loop, and the
  boxes are in the same places (the refuter's 300 frames on the Mac). A row in P633's rows file holds it.
- The review fixes after 143c879 (`take_step_us`, and the burning scene takes a tap before it counts) were not run
  on the board. They add one call a frame and move no work.

## P639 (#854), 2026-11-06: flames in front of the burning bodies

Python only, so the image is the one flashed in P632 (`flash-p632.log`). Each run went through `mpremote run` with
`app.run(games=(B,))`, where `B` starts `BurningBodies` in one mode, for 42 s after one 30 s warm-up. The values are
per frame, from seven 5 s lines each. The draw now times the whole `draw_layers`: the field behind, the eight body
fills (about 0.7 ms, P550's 87 µs a fill) and the field in front. Before, it timed the opaque field alone: 6.40 to
6.44 ms (run117, `bench.md:570-571`).

| run | front layer | mode | fps | step ms | draw ms |
| --- | --- | --- | --- | --- | --- |
| `run119-p639-burning-linear.log` | the same field, at most half opaque | linear | 23 to 24 | 7.92 to 8.08 | 17.30 to 18.04 |
| `run119-p639-burning-picture.log` | the same field, at most half opaque | picture | 20 to 21 | 8.85 to 9.12 | 20.21 to 21.36 |
| `run120-p639-front5b-probe.log` | a second field with its own burns, alpha test at heat 110 | linear | 23 | 14.51 to 14.84 | 14.30 to 14.39 |
| `run121-p639-cutout-linear.log` | the same field, cut out: clear below heat 120, solid from 180 | linear | 24 | 7.85 to 8.10 | 14.80 to 15.03 |
| `run121-p639-cutout-picture.log` | the same field, cut out: clear below heat 120, solid from 180 | picture | 21 to 22 | 8.46 to 8.71 | 17.91 to 18.54 |
| `run123-p639-ramp-linear.log` | the same field, cut out wider: clear below heat 100, solid from 230 | linear | 24 | 7.88 to 8.11 | 15.11 to 15.46 |
| `run122-p639-edge-picture.log` | the cutout, and `BLEND_PALETTE` for every blend | picture | 21 to 22 | 8.39 to 8.77 | 17.88 to 18.56 |

- The PO picked the soft cutout from Mac frames of five front layers (2026-11-06). On the panel its hot flames popped
  on and off over the bodies, so the built ramp is the wider 100 to 230 (run123, the PO's ok): 0.3 to 0.4 ms more draw.
- D5's line (draw 13.5 ms or less, 23 fps or more) does not hold: the built ramp draws 1.6 to 2.0 ms over it in linear (run123),
  of which about 0.7 ms is the body fills the old draw never timed, and the picture mode falls to 21 to 22 fps. The PO judges the look on the panel.
- A front blend that is half opaque everywhere costs about 3 ms more than the cutout: cells of alpha 0 are skipped
  and cells of alpha 255 need no blend math (`fx_fire.c:294`, `engine/driver/src/blend565.h:22-24`).
- `BLEND_PALETTE` (run122) removes the dark borders over the sky at no cost: the same table lookup, another table.
- The second field (run120, a scratch probe) fits in internal RAM (18,432 B left after it) and steps 6.8 ms more.

## P601 (#802), 2026-11-06: the bound probe, before any SWAR blend

Python only, on the P632 image (`flash-p632.log`). A scratch probe ran `BurningBodies` in one mode, started through
`setup` and `set_mode`, for 42 s after a 30 s warm-up, with a hard `mpremote reset` before each run. "a" keeps
today's alpha tables. "bound" sets each alpha of `burning.FRONT_ALPHA` and `fire.ALPHA` to 0 where the SWAR blend
skips (alpha 0 to 3) and to 255 elsewhere. Then no pixel is mixed, each pixel is skipped or stored, and the draw is
the best that any blend rewrite can reach. The values are per frame, from seven 5 s lines each.

| run | tables | mode | fps | step ms | draw ms |
| --- | --- | --- | --- | --- | --- |
| `run124-p601-a-linear.log`, `run125-p601-a-linear.log` and their `-linear2` repeats | a | linear | 24 | 7.96 to 8.10 | 15.03 to 15.52 |
| `run126-p601-bound-linear.log`, `run127-p601-bound-linear.log` and their `-linear2` repeats | bound | linear | 24 | 7.96 to 8.06 | 14.50 to 14.62 |
| `run124-p601-a-picture.log`, `run125-p601-a-picture.log` | a | picture | 21 | 8.63 to 8.93 | 18.26 to 19.29 |
| `run126-p601-bound-picture.log`, `run127-p601-bound-picture.log` | bound | picture | 22 to 23 | 8.31 to 8.45 | 15.85 to 16.18 |

- The plan set the pass line before the runs: D5 (draw 13.5 ms or less, 23 fps or more) in every 5 s line. A pass
  needs more than 0.5 ms to spare.
- The bound misses the line in both modes: by 1.0 to 1.1 ms in linear and by 2.4 to 2.7 ms in picture. So no blend
  rewrite, neither the SWAR blend nor PIE on the blend, can make either mode pass.
- All the blend math costs about 0.75 ms in linear (one blended pass) and 2.6 to 2.8 ms in picture (two). The rest of
  each pass is the bilinear interpolation. Every pixel pays it, also a pixel that the blend then skips.
- The bound is optimistic: a store of 255 reads no background, and a real blend does.
- The `-linear2` logs were meant as picture runs, but they are four more linear runs (P639's row 14 again).
  `Game.__init__` calls `reset`, `restart` and `setup` (`games/gfx.py:306-316`), and `Fire.setup` calls
  `set_mode(self.mode)` with the 0 of `Fire.__init__` (`games/fire.py:156, 168`). The probe set `self.mode` only
  after that. The number alone changes no filter, blend or name.

## P646 (#865), 2026-11-06: the early-out in the LINEAR blend

The image of `build-engine-p646.log` (`flash-p646.log`), with engine 2a5ffdd: `fx_fire_blend`'s LINEAR path skips the
two heats of a cell whose three mixes are at most 4T - 3, with T the first heat whose alpha is not 0. The output stays
byte for byte the same (`tests/test_fire_core.py`). A scratch probe ran `BurningBodies` as P601's did, but it set the
mode with `set_mode` after `setup`. Each run lasted 72 s after a hard `mpremote reset`. The values are per frame, from
the last seven 5 s lines of each run, after the 30 s warm-up.

| run | mode | fps | step ms | draw ms |
| --- | --- | --- | --- | --- |
| `run128-p646-linear.log`, `run129-p646-linear.log` | linear | 24 | 7.91 to 8.06 | 13.21 to 13.78 |
| `run128-p646-picture.log`, `run129-p646-picture.log` | picture | 22 to 23 | 8.34 to 8.53 | 14.78 to 16.48 |

- Against P601's runs 124 and 125, with today's tables: linear draws 1.7 to 1.8 ms less (15.03 to 15.52 before), and
  picture 2.8 to 3.5 ms less (18.26 to 19.29 before). Linear is below P601's bound, which kept the interpolation
  (14.50 to 14.62 ms). Picture's slowest line, 16.48 ms, is 0.3 ms above the bound's 15.85 to 16.18 ms.
- The pass line was set before the runs: D5 (draw 13.5 ms or less, 23 fps or more) in every 5 s line, with more than
  0.5 ms to spare. Both modes miss it.
- Linear misses by 0.28 ms at its slowest line (13.78 ms), and by 0.78 ms against the pass line with its spare. Its
  fps stays 24.
- Picture misses by up to 2.98 ms (16.48 ms), by 3.48 ms against the pass line, and runs at 22 fps in most lines.
- The Mac count of the plan: the check skips at least 95 to 97% of the front pass's cells and 81 to 89% of the picture
  field pass's (burning scene, frames 200 to 1000). The count used the limit 4T - 4, so it is a lower bound.

## P656 (#881), 2026-11-06: smoke run of all 14 games on today's image

The image is the one of `build-engine-p646.log` (`flash-p646.log`). The local `build-engine/micropython.bin` has sha256 4c680c72a2957e39 and leaves 211,200 B in the app partition (build output). The board reports `v1.29.0 on 2026-11-06`. The flashed image was not read back, so the hash is the build's, not the board's. The engine pin on master (a10a4c7) did not change since P646. `games/*.py` and `games/art/*` at c9e1045: all 104 files match master by sha256 through mpremote. The board also holds files that master does not have: `boot.py`, `bench582.py`, `probe550.py`, `probe556.py`, `probe567.py`, `probe582.py` and `art/runner_jump.bin`. None collides with a game name. These facts come from the build log, the flash log and mpremote's output, which are git-ignored and kept on the Mac. Each entry ran alone for about 13 s, as `app.run(games=(G,))` through `mpremote run`. The log `run130-p656-smoke.log` starts each entry with a `=== entry N` header.

| entry | started | fps lines |
| --- | --- | --- |
| 0 fire | yes | 25 |
| 1 balls | yes | 24, 24 |
| 2 burning | yes | 24 |
| 3 rain | yes | 25, 24 |
| 4 flappy | yes | 24 |
| 5 runner | yes | 24 |
| 6 snake | yes | 25, 24 |
| 7 stack | yes | 25 |
| 8 cave | yes | 23, 24 |
| 9 tunnel | yes | 25, 24 |
| 10 road | yes | 23, 20 |
| 11 starfire | yes | 25, 24 |
| 12 cube | yes | 25, 24 |
| 13 gravpong | yes | 24, 24 |

- Smoke (`run130-p656-smoke.log`): all fourteen entries start and print fps lines, with no error or traceback in the log, at 20 to 25 fps. Road is lowest (20 in its second interval), as in earlier smoke runs.

## P651 (#874), 2026-11-06: the Runner's runner on fire

Python only, on the P646 image (`flash-p646.log`; `HeatField.scroll` is in it since P602). The Runner carries a `FireTrail` on a `FireLayer` (the P602 flappy's shape): the layer scrolls with the world, one blend pass is drawn behind the runner. Each run went through `mpremote run probe651.py` (scratch): the Runner alone under an autopilot (a tap every 1.6 s, `die` off), after a hard `mpremote reset`, for 75 s. The probe times `FireLayer.update` (scroll and step) and `FireLayer.draw`. The values are per frame, from the last seven 5 s lines of each run. The pass line was set before the runs: fps 22 or more in every line, update plus draw 12 ms or less, 0 B allocated a frame. That last line was never measured for the fire alone.

| run | fire | fps | paint | update | of it step | draw |
| --- | --- | --- | --- | --- | --- | --- |
| `run131-p651-before-runner.log` | master's `arcade.py` | 22 to 24 | 30.2 to 35.3 ms | none | none | none |
| `run132-p651-after-runner.log` | heat step every 40 ms | 16 to 18 | 36.5 to 40.9 ms | 9.75 to 10.16 ms | not timed | 5.36 to 5.45 ms |
| `run133-p651-after-step80-runner.log` | heat step every 80 ms (`FIRE_STEP_MS`, built) | 18 to 19 | 36.4 to 38.7 ms | 5.08 to 5.32 ms | 4.00 to 4.22 ms | 5.39 to 5.43 ms |

- The pass line: update plus draw holds at 80 ms (10.5 to 10.8 ms, 12 or less) and misses at 40 ms (15.1 to 15.6 ms). The fps misses in both. The Runner is at the 40 ms frame edge with its painted layers and a HUD that redraws each frame under this autopilot (22 to 24 fps, paint 30 to 35 ms, more than run130's 22.9 ms), so any 10 ms more costs 4 to 5 fps.
- The best setting found is the 80 ms heat step: it saves 4.8 ms of update (the step is 4.0 to 4.2 ms of the 5.2, the scroll about 1.1 ms) for 2 fps. The flames rise at half the burning scene's pace in time: the PO judges the look.
- The blend draw is 5.4 ms, under P602's 7.6 ms (P646's early-out), and the field's 160 x 120 size is fixed by the C draw (it writes the whole panel).
- Not tried: a heat step every 120 ms (about 2.6 ms of step, a slower, coarser flame), `RADIUS` 2, the fire only while a bonus runs.

The PO's looks (2026-11-06: "shorter", "even shorter", "grow with speed", "looks bad: flat yellow or orange, not see-through", "falling apart and fading", "iterate until realistic") led to a longer change. The flame follows the base speed (none below `FIRE_START_SPEED` 300 px/s, full from `FIRE_FULL_SPEED` 560), and the speed curve rises more (`SPEED_SLOPE`, `SPEED_ROOT`, `SPEED_KNEE` 6, 8, 620 against 4, 6, 520; the top 700 against 600; the jump's reach and the obstacle gaps both scale with sqrt(base), so the ratio holds, the reaction time at 700 px/s from the right edge to the runner is 0.38 s against 0.52 s at 520). Seven sheets of Mac frames of the C kernel over the Runner's sky (kept outside the repository, `p651-sheets/round1.png` to `round7.png`) set the look:
- Round 1 (decay, cool, fade, embers): a flat bar smeared behind the runner. Round 2 (heat field drag at 6 to 30% of the world speed): tongues rise and break into wisps, but thin and hidden behind the sprite, with a bright blob in front. Round 3 (burn at the runner's back, bigger heat and radius): it looks like fire, but too tall and the core is a white blob. Round 4 (smaller, heat 225): short, white-yellow core, orange tongues, red wisps that detach and fade; the variants differ little, so the sweep stops.
- Rounds 5 and 6 (after the lead's critique: a flat pale wedge, a flame that lies down like a comet tail, orange that vanishes on the peach sky): round 5 swept wide (decay 20 to 40, cool 120 to 255, fade 24 to 80, heat 200 to 255, radius 2 to 4, drag 0 to 0.3, a random heat and radius each frame, a deep-red palette); the best has tongues that rise and break into separate flickering bits (decay 36, drag 0.04). Round 6 narrowed around it: its eight variants differ little, so the sweep stops there.
- Chosen (round 7, version E; the code): `FIRE_DECAY` 36, `FIRE_COOL` 255, `FIRE_FADE` 56 (burning's: 32, 40, 16), the burn at the runner's back with `FIRE_HEAT` 255 and `FIRE_RADIUS` 2, each frame up to `FIRE_HEAT_JIT` 80 cooler and `FIRE_RADIUS_JIT` 1 smaller at random (the flicker), the heat field scrolling at `FIRE_DRAG_PCT` 5% of the world speed (100% leaves a flat bar), the heat step every 80 ms, alpha by heat as a ramp 30 to 150 up to 235 (`FIRE_ALPHA`; fire.ALPHA is opaque from heat 96), and its own palette `FIRE_STOPS` (orange-red low end, orange, yellow, a small pale core only at the top) through `fire.ramp`, passed to `FireLayer(..., alpha, palette)`.

| run | flame | fps | paint | update | of it step | draw |
| --- | --- | --- | --- | --- | --- | --- |
| `run135-p651-alpha-speed-full-runner.log` | speed-driven, squared alpha, drag 100% | 16 to 18 | 40.2 to 43.3 ms | 5.37 to 5.59 ms | 4.29 to 4.54 ms | 5.44 to 5.48 ms |
| `run136-p651-ragged-flame-full-runner.log` | decay 24, cool 160, fade 40, ramp alpha, drag 20% | 17 to 18 | 39.9 to 42.0 ms | 5.33 to 5.57 ms | 4.19 to 4.43 ms | 5.48 to 5.51 ms |
| `run137-p651-realistic-flame-full-runner.log` | decay 28, cool 220, fade 56, heat 225, drag 8%, burning's palette | 17 to 18 | 39.2 to 41.4 ms | 5.30 to 5.50 ms | 4.17 to 4.36 ms | 5.49 to 5.51 ms |
| `run138-p651-rising-flame-full-runner.log` (built) | decay 36, cool 255, fade 48, heat 255 with jitter, drag 5%, own palette | 17 to 18 | 40.3 to 41.2 ms | 5.21 to 5.39 ms | 4.26 to 4.33 ms | 5.69 to 5.75 ms |

- Run 131 (no fire) was 22 to 24 fps with paint 30 to 35 ms. Runs 135 to 138 start with the run far on (`far` 40,000 px, base speed 697 px/s), so the flame is full and the world scrolls the most cells: the worst case. Their paint is also higher (the faster world, more things). The cost of the fire in the built version is the update (5.2 to 5.4 ms) plus the draw (5.7 ms), 10.9 to 11.1 ms, under the 12 ms line; the 22 fps line is missed (17 to 18).
- Run 134 (`run134-p651-decay20-runner.log`, decay 20 at the old speed, flame full from the start): 18 to 19 fps, update 5.2 to 5.3 ms, draw 5.4 ms.
- Round 7 (`p651-sheets/round7.png`, five versions A to E; the PO picked E, 2026-11-06: "still not great, but we can tune it later"): the burn narrower at the runner (`FIRE_RADIUS` 2, `FIRE_RADIUS_JIT` 1, was 4 and 2), more broken (`FIRE_FADE` 56, sway 1 (sway 2 crashed the board's binding; fx_fire.c reads sway as on or off, so the picture is the same), fast 200, embers 30, was 48, 1, 128, 0), no dark rim (alpha ramp `FIRE_CLEAR` 30 to `FIRE_SOLID` 150, was 10 to 150; the palette's low end orange-red 200, 60, 10, was dark red 90, 15, 10). Not yet measured on the board.
- The PO plays it (feel slice, not yet). The Runner runs on the board after the last measurement.
- Set `OBSTACLE_GAP` in `games/arcade.py` back to 1 before the merge (it is 1 at the merge, and 3 while the flame is tuned, so the PO jumps less).

## P733 (#1003), 2026-11-10: a 440 Hz tone beside the games, through stock `machine.I2S`

The spike tests A1 of the sound discovery (`docs/discovery/2026-11-09-sound/` on the branch `p729-sound-discovery`):
stock `machine.I2S`, refilled once per frame by Python, plays with no gap and costs the games no frame time. The
DFR0954 amplifier is on D12, D11, D10 and A2. The INMP441-type microphone is on A3, A5 and A4, L/R on GND. The
probes are `probe733.py` (step 1) and `probe733_games.py` (steps 2 and 3). Each run is 120 s with a game restart every
30 s (the PO shortened the plan's 300 s). 16 kHz mono, `ibuf=4096` (8 DMA buffers of 256 samples, a ring of 128 ms),
the tone at 10000 of 32767.

| run | game | tone | fps (mean of 20) | worst frame, median and max | late refills | breaks in the tone |
| --- | --- | --- | --- | --- | --- | --- |
| `run140-p733-games.log` entry 10 | Fire | yes | 24.05 | 50, 56 ms | 0 | none inferred (`short` within 300) |
| entry 11 | Fire | no | 24.05 | 53, 56 ms | | |
| entry 12 | BallPit | yes | 24.05 | 60, 73 ms | 0 | none inferred (`short` within 300) |
| entry 13 | BallPit | no | 24.00 | 60, 77 ms | | |
| entry 14 | Road | yes | 20.70 | 103, 116 ms | 4 | about 3 inferred (`short` rose about 700 samples) |
| entry 15 | Road | no | 20.55 | 107, 127 ms | | |
| `run141-p733-mic.log` entry 16 | Fire | yes, microphone | 24.00 | 56, 62 ms | 0 | 0 heard |
| entry 17 | BallPit | yes, microphone | 24.00 | 63, 81 ms | 0 | 0 heard |
| entry 18 | Road | yes, microphone | 19.60 | 105, 122 ms | 7 | 3 heard, 12 ms each, at 4.9, 10.3 and 67.1 s |

- Step 1 (`run139-p733-tone.log`): the PO heard the tone. 160,000 B for the 5 s of tone, in a run of 6.0 s. Beep, silence, beep with SD
  (A2) low in the middle: the PO heard the middle silent, so A2 shuts the amplifier down while the clocks run.
- The frame-time line of D23 passes in all three games: the worst frame with the tone is within 5 ms of the control
  run, or lower, and the mean fps is within 1 fps. Each write took under 1 ms.
- The "no gaps at all" line of D9 fails in Road. Its own slow frames, 116 to 127 ms, are longer than the 112 ms that
  the ring holds after a refill. A game restart costs 11 to 20 ms in the hook, so it is not the cause. The microphone's
  3 breaks and the rise of `short` (about 3 buffers of 256 samples) agree. `late` (7) counts more than the breaks
  heard (3), because a refill 112 to 128 ms late can still come in time. `short` moves by up to about 300 samples
  between reports with no break, and its last value, after the close, ends 500 to 600 higher. The phone recording of
  D18 did not run.
- The first refill waited for room (blocking writes and a lead of 96 ms): each refill waited 26 to 43 ms, and Fire fell
  to 16 to 22 fps (`run140` entry 2). A `select.poll()` switch makes the writes return at once with what fits.
- The microphone heard the tone at 3000 no louder than the quiet room (1 to 5 units), and at 10000 at 16 to 21. It
  settles for about 1.3 s after it opens, and its constant offset counted as noise until the block mean left it out.
  Voice and claps read up to 154 (`run141`, the diagnosis runs 141b to 141d). The room floor with the game running is
  0 to 5, so BallPit passed the check (tone at least 4 times the floor) by 21 against 20: the margin is thin.
- Open for the design: a larger ring (8192 B, 256 ms, over D9's limit, and a sound effect up to 256 ms late), a refill
  from C outside the game loop, or Road frames under 112 ms.

## P746 (#1025), 2026-11-10: Road at 8192 B, and the delay from a hit to its sound

The spike follows P733 and D24 (the PO: "Deeper buffer first"). `probe733_games.py` gains `IBUF` (the TX ring in
bytes), `HITS` (`"auto"`: a beep every 2 s, `"press"`: a beep at each BOOT press) and a `Beeper`: silence between
beeps of 60 ms at 20000. The microphone measures the delay from the start of the frame that sees the hit to the
beep, in its own sample clock. Road, 16 kHz mono, no game restarts in the hit runs.

| run | ring | hits | delay, median and max | the PO |
| --- | --- | --- | --- | --- |
| `run143-p746-delay.log` entry 2 | 4096 B (8 x 16 ms) | 21 auto | 117, 125 ms (two early onsets, 23 and 96 ms) | |
| entry 3 | 8192 B (16 x 16 ms) | 21 auto | 243, 251 ms (one early onset at 44 ms) | |
| entry 5 | 4096 B | 10 presses | 112, 125 ms | "they came with the press" |
| entry 8 | 8192 B | 28 hits (31 presses), 19 heard | 245 ms median (first hit 383 ms) | "there is a delay" |

- A3's line (median under 130 ms, and the PO's ear, confirmed 2026-11-10) passes at 4096 B and fails at 8192 B. Most
  delays fall in 107 to 125 ms and 236 to 251 ms, close to the prediction of (buffers - 1) x 16 ms plus 0 to 16 ms
  (112 to 128 and 240 to 256 ms). Outliers: 23, 44, 96, 266, 282 and 383 ms. The ring is always full of silence, so a
  beep waits behind all of it.
- So a refill once per frame cannot pass both lines in Road: 4096 B has Road's gaps (P733), and 8192 B is too late.
  The cause is the refill rate, not the ring size. The next step is a refill that does not wait for a frame.
- The run of Road with the tone at 8192 B did not run (`run142-p746-road.log`): the microphone heard the tone at 9,
  under the probe's minimum of 10 (`TONE_MIN`), also at 4096 B, where it heard 20 to 21 at 12:47 (`run141` entries 16
  to 18). The microphone or the speaker probably
  moved. After the PO heard the delay at 8192 B, this run could change nothing, so it was skipped.
- In the press runs at 8192 B, entries 6 and 7 saw no press at all, and entry 8 saw 31. The cause is not known. The
  probe now prints each press before any check. In entry 8, 9 of 28 hits found no beep within the probe's 400 ms,
  4 of them in the first 5 hits, with presses over 1 s apart. The cause is not known.
- Limits of the measure (the refuter, 2026-11-10), fixed in the next spike, which reruns it:
  - The delay counts from the frame that reads the press, not from the push. Road's frames add up to 50 to 120 ms
    before that, so the PO heard press-to-sound times longer than the table's, and A3's 130 ms line compares two
    different spans. The next probe stamps the hit in the button's interrupt (`Button.edge`).
  - One 4 ms block over the threshold counts as an onset, with a thin margin (threshold 10, the beep about 18). That
    explains the misses and the early onsets better than the press timing does. Next: two or three blocks in a row,
    a rising edge, the loudest block printed per hit, and the 400 ms window set from the ring size.
  - The probe dropped 3 of the 31 presses in entry 8 without a print, because a hit waited for its beep.
  - `between` in a hit line is the previous frame's refill gap, not the one that wrote the beep.
- The microphone's clock is right: alone, it lags 0 to 192 samples (`run143d`). The first smoke printed negative
  `lost` in the hit line, because inside a read it counted a block twice, so the hit line no longer prints it.
- The microphone's receive ring holds about 240 ms (16 buffers of 16 ms): a read every 500 ms lost half of the
  samples (`run143c`).

## P748 (#1028), 2026-11-10: one Mixer, a per-frame and a callback refill, measured in Road

`games/sound.py` gives the games one `Mixer` (`play(sound)`, `render(buf)`) and two drivers that feed the I2S ring.
`FrameRefill` refills once per frame (the naive path, D26). `CallbackRefill` refills from the stock `I2S.irq` callback,
about every 16 ms (D25). `probe733_games.py` uses the module, and `REFILL` picks the driver. The log is
`run144-p748-mixer.log`. Road and Fire, 16 kHz mono, 120 s per entry, the microphone on in every entry.

| entry | driver, ring | sound | result |
| --- | --- | --- | --- |
| 1 | none | none | 18.7 fps, worst frame 134 ms: the cost control |
| 2 | `FrameRefill`, 4096 B | 58 auto hits | delay median 134 ms, max 143 ms, 0 missed, 9 late refills |
| 3d | `CallbackRefill`, 2048 B | tone at 6000 | 18.9 fps, worst 126 ms, 0 gaps, handler wait at most 27 ms, 0 late |
| 4 | `CallbackRefill`, 2048 B | 58 auto hits | delay median 70 ms, max 78 ms, 0 missed, handler wait at most 22 ms |
| 5b | `CallbackRefill`, 2048 B | 72 presses, beep at 6000 | 20 heard: delay median 76 ms, push to beep median 101 ms. The PO: "With the press" |
| 6d | `CallbackRefill`, 2048 B | tone at 6000, Fire | 24.0 fps, worst 62 ms, 0 gaps, handler wait at most 29 ms, 0 late |

- The callback passes all four lines that the plan set before the runs. Gaps (D9): none in Road or Fire (3d, 6d),
  no open gap, and each 5 s line sent 314 of 315 expected blocks or more. Delay (A3): 70 ms in entry 4, under the
  90 ms goal, and the PO's ear in entry 5b. Cost (D23), from entry 3d: Road within 1 fps and 5 ms of the control.
  Handler wait: at most 29 ms, under the ring minus two blocks (32 ms). No `stall` line came in any entry.
- The cost line is close in the other callback runs. Entry 4 had a worst frame of 140 ms (6 ms over the control),
  and entry 5b ran at 17.7 fps (1.0 fps under). In 6d, `between_max` reached 46 to 47 ms, 1 to 2 ms under a late
  refill (48 ms).
- The per-frame driver's delay rose from P746's 117 ms to 134 ms. A probable cause, not checked: `FrameRefill` keeps
  the unwritten rest of a block, so a new sound can wait up to 16 ms more.
- The microphone read 32-bit words from entry 3b on. The 16-bit read kept the top 16 of its 24 bits, so every level
  was divided by 256, and the tone at 10000 read 4 to 17 against a room of 0. With 24 bits it read 1985 to 4630
  against about 200 (`run144i`, `run144j`). The level at the microphone varies a lot between runs: the tone at 3000
  read 351 against 268 (entry 3c), so the gap runs used 6000.
- Entries 3b and 6b heard gaps at 113 to 119 s and at 40 to 54 s, and 6b lost USB at 15:08:38. The PO reports
  touching the speaker, the microphone and the cable then, because the tone at 10000 was "really annoying". No log
  line marks a touch. The log rules out the driver: `late` stayed 0 and `lag_max` at most 31 ms. An empty ring plays
  silence (`auto_clear` is on), so a gap from the driver would also count as late.
- In entry 5b, 52 of 72 hits found no beep. Most missed hits read 568 to 1158, under the onset threshold of 1200.
  Three read 1225, 1243 and 3268, and why they missed is not known. The 20 heard hits read 1301 to 7048, above the
  soft beep's usual level, so some onsets can be another sound, such as the button's click. So 5b's delay (median 76
  ms) is weak evidence, and A3 rests on entry 4 and the PO's ear. Push to frame (`seen`) was 1 to 52 ms, median about
  25 ms. The probe's `BEEP_MIN` is now 700, not tested on the bench.
- Later, not MVP (the "Later" marker in `games/sound.py`): more than one voice summed, a volume, a C mixer with the
  same `render(buf)` (P747), and a C task on the second core (D27).
- `align 0` in all 18 entries that opened the sound: the refill block is aligned to 16 bytes (D27).

## P747 (#1027), 2026-11-10: the fire's crackle in C, with one pop per ember

`games/crackle.py` gives Fire a crackle: a deep, quiet roar and one pop per ember that the kernel births
(`HeatField.take_births()`, new in this image). `NativeCrackle` renders it in C (`engine/core/fx_crackle.c`) from
`crackle_c.mpy`, a native module that loads with no firmware rebuild. The plain Python `Crackle` is the same integer
math and equals the C sample for sample on the Mac. `SampledCrackle` is the naive path on the board. The probe's
`VOICE` picks the sound. Fire, 16 kHz mono, 120 s per entry with a new game every 30 s, no microphone.

| entry | log | driver, ring | voice | result |
| --- | --- | --- | --- | --- |
| loop | run145a | `CallbackRefill`, 2048 B | `NativeCrackle`, 10 s | 12 s from a saved C file to the first pop, 24 fps, late 0 |
| 5a | run145b | `CallbackRefill`, 2048 B | silent `Mixer` | 24.00 fps, worst 77 ms, 1 late: the control |
| 5b | run145b | `CallbackRefill`, 2048 B | `NativeCrackle` | 24.00 fps, worst 77 ms, 0 late, render at most 413 us, pop wait median 11 ms, max 27 ms, 0 dropped |
| 5c | run145b | `FrameRefill`, 4096 B | `Crackle` (Python) | hung: no frame after `align 0`, stopped by hand |
| roar A, B | run145c, d | `CallbackRefill`, 2048 B | `NativeCrackle`, 20 s each | A no roar, B roar at about 40 Hz, a quarter of the level. The PO chose B |
| 5c | run145e | `FrameRefill`, 4096 B | `SampledCrackle` | 24.15 fps, worst 70 ms, 0 late, render at most 2.3 ms, pop wait median 12 ms, max 42 ms, 3 dropped |

- 5b passes every line that the plan set before the runs: fps and worst frame equal to the control, no more late
  refills than the control, a render under 1 ms, no dropped pop, and a pop wait (from `add_pops` to the render that
  starts it) of median 11 ms and max 27 ms against 20 and 48 ms. The ring then holds a pop up to 64 ms more. These
  runs had the old roar. The roar's numbers change no work per sample, and run145d (the deep roar, 20 s) rendered in
  at most 408 us. The probe then took one wait per `add_pops` call, not per pop (the refuter), so the logs hold no
  pop count. It now takes one per pop.
- The PO's ear: the pops come with the sparks "kinda, its not synchronized with their size", because "some are
  brighter and bigger". Every ember is born the same in the kernel today, and each pop's loudness is random. The old
  roar (`roar_shift` 4, `roar_gain` 48) sounded like "background noise like wind or river". On the Mac, the roar
  alone measured RMS 1637 and the whole 15 s WAV 1620, with other seeds, so the roar was most of the sound.
- The Python `Crackle` takes 20.9 to 22.7 ms for 256 samples (16 ms of sound) on the board (the last line of
  run145b), about 50 times the C's slowest render. The first
  5c hung because `FrameRefill` rendered until the ring was full, and a renderer slower than real time never fills
  it. A `FrameRefill` write now renders at most one ring. The PO chose pre-rendered pops as the naive path, and on
  `SampledCrackle`: "sounds weird, but never mind lets leave the simple one like that, advanced versions will be cool".
- 5a, the control, counted 1 late refill, and 5b none (the probe prints a running total). Both sit near the line: `lag_max` reached 32 ms in 5a and
  29 ms in 5b, and a refill whose wait passes 32 ms (the ring minus two blocks) counts as late. The game switches every 30 s cause the worst frames.
- Later, not MVP: a pop whose loudness follows its spark's size (the kernel gives each ember a size), the flames in C,
  and the S3's vector instructions where a measurement shows the need (D27).

## P751 (#1033), 2026-11-10: the fire sound of P750's demo g, from a sample bank

`tools/fire_bank.py` renders P750 round 2's demo g on the Mac into a bank of 247 KB (246960 bytes): a 6 s bed and 12 woody pops. At
first the bed held grains of a CC0 fire recording, sparse small crackles and a low fluttering roar (entries 5d to 5d2).
After the PO's ear, it holds only the roar (run146e). On the board, `GrainCrackle` mixes grains
of the bed and one pop per ember birth in C (`engine/core/fx_grains.c`, in `crackle_c.mpy`). A fast ember (rise 4 or
5) gets a larger pop. The bank lives in `engine.SoundBank`, outside the GC heap. Fire, `CallbackRefill` 2048 B, 120 s.

| entry | log | bank | result |
| --- | --- | --- | --- |
| loop | run146a | bytearray in the GC heap | plays, but fps 23, gc 5.3 ms a frame, late 4 |
| gc | run146a, run146b | 247 KB | `gc.collect()`: run146a 93 us with no bank, 7657 us with a bytearray; run146b 96 us with no bank, 102 us with a `SoundBank` |
| 5d | run146b | `SoundBank` (PSRAM) | 24 fps, worst 85 ms, gc 2.4 ms, late 0, render at most 464 us, pop delay (to the render that starts it) median 9 ms, max 27 ms, 0 dropped |
| 5d2 | run146c | `SoundBank` (PSRAM) | 24 fps, worst 81 ms, late 1, render at most 463 us, pop delay max 27 ms, 0 dropped |

- Against P747's control (run145b 5a: 24.00 fps, worst 77 ms, late 1), 5d2 passes every line. 5d misses the worst
  frame line by 3 ms in one 5 s window (85 ms, with the frame's own phases at 50 ms, so the time went between frames).
  The other worst frames are 51 to 74 ms in the two runs, as in the control (52 to 77 ms).
- A bytearray bank cost 7.6 ms at each collection, and the game collects every 5 frames. Memory from
  `heap_caps_malloc` is not in the GC heap, so the collector skips it (the plan's refuter found no flag for this in
  v1.29.0's `py/gc.c`). The bank loads in 179 to 226 ms.
- The flash needed no buttons this time: `mpremote bootloader` reached download mode (USB 0x1001).
- The PO's ear on the board's speaker (run146e, 2026-11-10 19:25 to 20:20): "No, not yet", with the pops "out of sync"
  and the bed "still water or wind". Embers show from their first kernel step, so the delay was not the cause. The bed's
  own crackles (3 to 15 a second, against 2 to 4 births a second) came with no spark on screen. With the bed off
  (`GRAIN_LOOK = (0, 32768)`), the PO: "Yes, in sync now", "The cracks are good already, snynced". The PO then chose a
  bed of the roar alone. The roar does not follow the video ("That doesnt seem to be synced with the video"), which is
  P753's first slice. Render at most 467 us, 0 dropped in all runs of run146e.


## P753 (#1036), 2026-11-10: the fire's bed and the bodies' whooshes

`FireSound` (`games/crackle.py`) plays P751's pops and adds noise in integer C (`engine/core/fx_noise.c`): a noise bed
that follows the heat field, and 8 whoosh voices, one per burning body, that follow its airspeed. Python sets targets and C
glides to them in about 32 ms. Each run is 120 s with `CallbackRefill` 2048 B. The control is `GrainCrackle` on the same game.

| entry | log | game and voice | result |
| --- | --- | --- | --- |
| 1 | run147a | Fire, GrainCrackle | 24 fps, worst 86 ms, late 2, render at most 456 us, 0 dropped |
| 2 | run147b | Fire, FireSound at -Os, bed off | 24 fps, worst 75 ms, late 1, render at most 514 us, 0 dropped |
| 3 | run147c | Fire, FireSound at -O2, bed off | 24 fps, worst 68 ms, late 1, render at most 623 us, 0 dropped |
| 4 | run148a | BurningBodies, GrainCrackle | 23.25 fps, worst 82 ms, late 0, render at most 445 us |
| 5 | run148b | BurningBodies, FireSound at -Os | 23 fps, worst 81 ms, late 0, render 948 to 1054 us (fails the 1000 us line) |
| 6 | run148c | BurningBodies, FireSound at -O2 | 23.1 fps, worst 82 ms, late 0, render at most 891 us |

- The fps is the mean of the 5 s lines, the worst frame is the largest `worst`, `late` is the largest of the 5 s lines, and the render time is the largest `render_max`. BurningBodies has embers off, so it has no pops and no dropped line.
- Entries 2 and 3 ran with the bed off (`BED = False`, so `follow_field` is 0 in their lines). The PO's ear test of the bed is run147d-p753-bed-ear.log.
- `HeatField.stats(threshold=48)` returns `(total, height)`. At first it took 1.5 ms a call on the board, because `memcpy` ran as a call per word. Reading whole words and a loop of 4 words a turn brought it to 393 to 498 us a call (board, 2026-11-10, logged in run147e).
- Entries 3 and 6 built the whole natmod at -O2. At -Os the 8 voices made render 948 to 1054 us a block, over the 1000 us line. At -O2 it is at most 891 us. But -O2 on the whole module added about 100 us to a Fire block where nothing whooshes (entry 3 against entry 2). So the build now gives -O2 to `fx_noise_mix` alone, and the rest stays at -Os. Its numbers come in run149.
- The PO's ear on the board: the noise bed on Fire "sounds like a lot of wind in the background". A quiet bed that flaps with the flame height was "Still wind". So `BED = False`: Fire plays the pops alone, and the bed code stays, marked Later, not MVP. The whooshes on BurningBodies: "Cool, keep it".
- Pass lines against the control on the same game:
  - Mean fps within 1: entries 2, 3, 5, 6 pass.
  - Worst frame within 5 ms: entries 2, 3, 5, 6 pass.
  - `late` no more than the control's: pass.
  - Render at most 1000 us: entries 2, 3, 6 pass, entry 5 fails.
  - 0 dropped pops on Fire: pass.
  - Under 0.1 % of samples at the clamp: the Mac test `test_fire_like_stats_with_pops_stay_loud_and_clamp_under_a_tenth_of_a_percent` asserts it. No 15 s WAV share is measured yet.
  - The probe counts `follow_*` calls above 0: on Fire `follow_field` and `follow_bodies` show 0, because the bed is off. On BurningBodies `follow_bodies` shows about 119 a window.
- On the Mac, wind -60 against +60 changes a whoosh level 3.4 times. The test asserts at least 1.41 times, and its sign: a body with dx above 0 is louder at wind -60.
- Before fix C, `BurningBodies.follow_bodies` cost about 0.8 ms a frame (step 8.30 to 9.1 ms, run148). It now reads the physics `out` array in place. New numbers come in run149.

After the review (engine 1c15d73, `crackle_c.mpy` sha256 90d7503d, `-O2` on `fx_noise_mix` only, the stuck-whoosh fix
and the `out` read), 120 s each. `HeatField.stats()` timing is in run147e: 392 to 497 us a call.

| entry | log | game, voice | result |
| --- | --- | --- | --- |
| 7 | run149a | Fire, GrainCrackle | 24 fps, worst 74 ms, step 7.0 ms, late 1, render at most 465 us, 0 dropped |
| 8 | run149b | Fire, FireSound | 24 fps, worst 70 ms, step 7.1 ms, late 0, render at most 693 us, 0 dropped |
| 9 | run149c | BurningBodies, GrainCrackle | 23.4 fps, worst 84 ms, step 9.5 ms, late 0, render at most 443 us |
| 10 | run149d | BurningBodies, FireSound | 23.05 fps, worst 89 ms, step 11.7 ms, late 0, render at most 979 us, 119 follow_bodies calls a window |

- Entries 8 and 10 pass every line against 7 and 9, with thin margins on BurningBodies: render 979 us against 1000,
  and worst 89 ms against 84 + 5.
- `-O2` on the one function renders slower than the whole module at `-O2` (entry 6: at most 891 us; Fire 623 us). The
  refuter's per-path cost is real, but this fix did not lower it. A faster mix (voices in an outer loop, state in
  locals) is a later row.
- The step on BurningBodies grows from 9.5 to 11.7 ms with the whooshes, against about 0.8 ms in run148. Both runs pass
  the fps line. The cost of `follow_bodies` in Python is a later row too.

## P758 (#1041), 2026-11-10: the rotary encoder on the pulse counter

The PO's CJMCU-111 knob sits on 3V3 and GND, with GA on SDA (GPIO1, `pins.ENC_A`) and GB on SCL (GPIO2, `pins.ENC_B`).
spark's `requirements.json` chose both pins. `games/encoder.py` reads the knob with `machine.Encoder`, the ESP32-S3's
pulse counter, with the internal pull-ups and the 12 us glitch filter. `probe758.py` prints one line per change of
the raw edge count for 180 s. The PO turned the knob by hand and counted the clicks.

This section describes the place of 2026-11-10. On 2026-11-11 the encoder moved to the pads RX and TX, so
`pins.ENC_A` is 44 and `pins.ENC_B` is 43 now (P757, entries 20 to 24).

| entry | log | what the PO did | result |
| --- | --- | --- | --- |
| 1 | run150-p758-encoder.log, 0 to 16 s | a free try, both ways | the count goes up to 9 and down to -16, so the sign follows the direction |
| 2 | 16 to 30 s | the way up | the count stops at 85, and the start of the count is unclear |
| 3 | 35 to 55 s | 20 clicks back | 85 to 5: 80 edges, 4 edges per click |
| 4 | 55 to 180 s | hands off | no change for 125 s, the run ends at 5 |

- `EDGES_PER_DETENT = 4` in `games/encoder.py` comes from entry 3. The part record `cjmcu-111-rotary-encoder` now holds
  it as a bench fact. The shops publish 20 clicks per turn and no edge count.
- Inside a turn the count steps back by 1 edge six times (17.5 s, 17.9 s, 26.4 s, 35.8 s, 38.9 s, 49.2 s). The log
  cannot tell a contact bounce from the PO's hand.
- The knob does not rest on a multiple of 4 edges. The run starts at 0, and the rests are at 9, 85 and 5, each 1 above
  a multiple of 4. `detents()` gives each click 4 edges (2 to 5 is click 1), so at such a rest 1 more edge changes
  the click count. A use that must not flicker, such as P757's volume, needs a dead band.
- ENC_A and ENC_B are the board's SDA and SCL pads. spark's board record says that a FireBeetle 2 ESP32-S3 of V1.1 or
  earlier has its power chip (AXP313A) and 5.1 kΩ pull-ups on these lines, so the knob's contacts would toggle that
  chip's bus. The revision of the PO's board is not recorded. Nothing else in the repository uses I2C.
- No frame loop ran beside the probe. The count under a game's load is P757's bench.
- Not measured: the module's own pull-ups (an ohmmeter from VCC to GA and to GB, power off, with the GA and GB wires
  out of the board). The record keeps that fact unverified.

## P757 (#1040), 2026-11-11: the master volume

`MasterVolume` (`games/volume.py`) scales each block of 256 samples by a Q15 gain, just before the I2S. It has 17
steps of 3 dB, and step 0 is silent. `ViperMasterVolume` (`games/volume_viper.py`) is the same scale as viper code.
`probe733_games.py` runs them with `VOLUME` and `LEVEL`. Nobody flashed the board for this card, and these runs did
not read its image. `crackle_c.mpy` is 90d7503d74fe (engine 1c15d73). Logs (git-ignored, kept on the Mac): `run151`
to `run175`.

### Slices 1 and 2: the gain and its cost

The scale gives the same samples on the Mac and on the board, as bytecode and as viper code.

| entry | log | what ran | result |
| --- | --- | --- | --- |
| 1 | run152-p757-scale-mac.log, run152-p757-scale-board.log | the naive scale on 10 named cases of a scratch script (not the 8 `CASES` of `volume_viper`), the same script on both | the same `GAINS` table and the same 10 sums |
| 2 | run152-p757-scale-board.log | the naive scale alone, 20 blocks each | a steady gain 1220 us a block (median), a ramp 1644 us |
| 3 | run154-p757-emitters.log | the steady loop as bytecode and under `@micropython.native` | 1204 us and 681 us |
| 4 | run155-p757-viper-board.log | `volume_viper.scale_match()`, then the viper scale alone | `scale match 1`, and 116 us a block, steady and ramp |

Fire with `FireSound`, `CallbackRefill` 2048 B, 30 s each (`tools/crackle.sh 30 FireSound`), from five 5 s lines:

| log | volume | fps | late | step ms | apply_max us | render_max us |
| --- | --- | --- | --- | --- | --- | --- |
| run153a-p757-fire-off.log | none | 24, 24, 24, 24, 24 | 0 | 7.3 to 7.5 | | 593 to 664 |
| run153b-p757-fire-l8.log | `MasterVolume`, step 8 | 24, 24, 23, 23, 24 | 0 | 7.6 to 8.1 | 1366 to 1909 | 604 to 685 |
| run156-p757-fire-viper-l8.log | `ViperMasterVolume`, step 8 | 24, 24, 24, 24, 24 | 0 | 7.4 to 7.6 | 249 to 334 | 615 to 700 |

The tone through the microphone (`MIC = 1`, `FrameRefill` 4096 B), `tone_mean` and `floor` of each run:

| log | volume | tone_mean | floor |
| --- | --- | --- | --- |
| run151b-p757-tone-off.log | none | 616 | 207 |
| run151a, run151c, run151d-p757-tone-l16.log | step 16 | 616, 855, 561 | 1036, 634, 209 |
| run151d-p757-tone-l15.log | step 15 | 337 | 204 |
| run151d-p757-tone-l14.log | step 14 | 245 | 206 |
| run151d-p757-tone-l13.log | step 13 | 217 | 203 |
| run151d-p757-tone-l12.log | step 12 | 218 | 217 |
| run151d-p757-tone-l8.log | step 8 | 200 | 203 |
| run151d-p757-tone-l1.log | step 1 | 202 | 204 |
| run151d-p757-tone-l0.log | step 0 | 197 | 202 |

- The naive scale costs about 1.2 ms of each 16 ms block as bytecode, twice the `FireSound` render itself. Fire lost
  one frame per second in two of five lines. The viper scale costs 116 us alone and at most 334 us in the game, with
  the probe's timer around it. The naive class stays: it is the path that always works (D26).
- `fast.native` does nothing on the board (entry 3 and `print(fast.native)`: `<function native>`, the fallback of
  `games/fast.py`). The `micropython` module has no `native` name to import: the compiler knows only the written
  decorator `@micropython.native`. So the `@native` code of `gfx.py`, `motion.py` and `render.py` runs as bytecode.
  `volume.py` does not use it. The fix is not in this card.
- The microphone does not prove the levels. Every tone run ended with `mic slot empty`, also the run with no volume:
  the tone read 561 to 855, under 3 times the room in each run, where P733 read 901 to 976. The cause is not measured.
  The room moved between 202 and 1036. The numbers fall with the step and meet the room at about step 13.
  They cannot tell step 12 from step 0, and they cannot tell 3 dB a step from another slope.
- Nobody listened to these runs. The PO's ear is the test of slice 3.

### Slice 3: the knob

`VolumeKnob` reads `Encoder.take_detents()` once per frame and turns the step, 1 step per detent. The dead band is
2 edges, and the rest point follows the count after 500 ms with no change, at most 1 edge from a whole detent. The
three numbers are not tuned on the bench.

| entry | log | what ran | result |
| --- | --- | --- | --- |
| 5 | run157-p757-fire-knob-rest.log | Fire with `FireSound`, `ViperMasterVolume` at step 8, `KNOB = 1`, 30 s, hands off | `edges 0` and step 8 in all five lines, no `level` line, fps 24, 24, 23, 23, 23, late 0, step 7.4 to 7.7 ms, apply_max 270 to 308 us |

| 10 | run161-p757-fire-knob-review.log | the same as entry 5, after the review's changes (the bounded rest point, the `finally` in `render_block`) | `scale match 1`, `edges 0` and step 8 in all five lines, no `level` line, fps 24, 24, 24, 23, 24, late 0, step 7.4 to 7.6 ms, apply_max 247 to 387 us |

- Entry 5 is the pulse counter beside a game's load at rest: it counted no edge in 30 s. Entry 10 is the same.
- Entries 5 and 10 pass for a knob that works and for one that does not: nobody turned it.

The PO's turn, 2026-11-11: "I played it and heard fire dounds, but the rotary did nothing". The runs that followed,
each with the PO's hand on the knob (entries 13 and 14 with no hand). Entries 12 to 17 are scratch scripts, not in
the repository: they set up the encoder as `Encoder.on_board` does and print once a second or once a phase.

| entry | log | what ran | result |
| --- | --- | --- | --- |
| 11 | run162-p757-fire-knob-po.log | entry 5 again, the PO turns | step 8 in all five lines, no `level` line, edges 0, 0, 1, 0, 1 |
| 12 | run163-p757-encoder-raw.log | the encoder alone: both pins read raw beside the pulse counter, 45 s | both pins change, the counter reads 240 edges after about 22 s of turning |
| 13 | run165-p757-encoder-i2s.log | no hand: the pins' GPIO registers and raw rising edges in 1 s, before, with and after an open I2S | GPIO1 and GPIO2: output off, `out_sel` 256 and the same IO_MUX word in all three states. 0 edges, level 1 |
| 14 | run166-p757-encoder-display-i2s.log | no hand: the same with the display opened first | the same: 0 edges, level 1 |
| 15 | run164-p757-encoder-phases.log | the count alone (25 s), after the display's setup (15 s), after the I2S opens (15 s) | alone and with the display the count follows the hand. With the I2S open it stands at -3 for the 15 s, pin A changes as before (168 polled changes in 15 s), pin B 2403 |
| 16 | run167-p757-encoder-alternate.log | the display open, the I2S closed and open in turns of 4 s, raw rising edges per second on each pin with no filter | I2S closed: 2 to 22 edges a second on B, the count goes from 20 to 172. I2S open, the 16 seconds with a turn: 26052 to 300347 edges a second on B, 10 to 1377 on A, and the count changes in 6 of 28 seconds, by 2 at most. At rest: 0 edges, also with the I2S open |
| 17 | run168-p757-encoder-adc.log | the voltage on both pins by the ADC (11 dB, bins of 200 mV), five turns of 12 s by the script (the log has no times): the I2S closed, open, closed, open, closed. The first two turns show no closed contact | open contact: 3.0 to 3.2 V, and with the I2S open up to 133 of 85466 samples in 2.8 to 3.0 V. Closed contact, I2S closed: 1.2 to 1.4 V, with 13 of 31002 low samples outside that bin on A and 3 of 14667 on B in the last turn. I2S open: the low samples spread over 0.8 to 2.0 V, with 315 of 39064 outside the bin on A and 1598 of 16257 on B |
| 18 | run169-p757-pads-unplugged.log | the PO wrote "unplugged": GA and GB are off the pads SDA and SCL. Each pad: 200 digital reads with no pull, with the chip's pull-down and with its pull-up, then 200 ADC reads by the script (the log has no count) | both pads read 1 in all 200 reads under each pull, also under the pull-down. The ADC reads 3071 mV in every sample on both pads |
| 19 | run170-p757-pads-i2c-scan.log | an I2C scan on the two pads, at 100 kHz by the script, right after entry 18 | 1 device answers, at 0x36 |

- The knob does not turn the volume while the sound plays. The encoder, its wires and the pulse counter work when
  the I2S is closed (entries 12, 15, 16). `volume.py` and `take_detents` are not the cause: the count that they
  read stands still.
- Measured: a closed contact reads 1.2 to 1.4 V, not 0 V, and an open one 3.0 to 3.2 V (entry 17). Read, not
  measured: the ADC's setup switches the pin's own pull-up off (ESP-IDF v5.5.2, `gpio_config_as_analog`). If that
  holds on this image, a pull-up outside the chip holds the open level, and the closed contact is one half of a
  divider. Which resistors these are is not measured.
- Measured: with the I2S closed the count follows the hand at this level (entries 15 and 16), and P758's bench ran
  with the I2S closed (run150). With the I2S open, B shows 26052 to 300347 raw edges a second while the knob turns,
  and the count changes by 2 at most in a second (entries 15 and 16).
- Inferred, and tested by no run: the level sits near the input's threshold, so the I2S's noise flips the input.
  The pulse counter's filter (`FILTER_NS`, 12 us) drops these pulses, so the counter sees B as constant, and each
  edge of A counts once up and once back. The source is the bit clock on GPIO12: 512000 edges a second by the I2S's
  settings (16 kHz, 16 bits, 2 slots), which no run measured.
- The chip does not drive GPIO1 or GPIO2 (entry 13). How the clock's noise reaches the pins is not measured.
- With the encoder off, the pads SDA and SCL read high under the chip's pull-down (entry 18). The reading of
  that: a pull-up outside the chip, stronger than the pull-down. A device answers on them at 0x36 (entry 19). The
  board record says that V1.1 and earlier carry an AXP313A power chip on this bus, with 5.1 kOhm pull-ups to 3V3.
  That 0x36 is that chip's address is from
  memory, not from a document read here, and no run measured the pull-ups' value. The record's line for V1.2 and
  later ("NONE anywhere on the board") does not fit this board.
- Measured: a device at 0x36 shares the two pads with the encoder. Likely, not proven: it is the board's power
  chip, and this board is V1.1 or earlier. Nobody read the chip's marking or the back silkscreen, which is how the
  record tells the versions apart. The encoder's contacts made edges on that device's SDA and SCL. What it does
  with such edges is not measured. The encoder's wires stay off these two pads.
- The fix is the move to the pads RX and TX, below. The PO's turn in Fire is entry 27. Not done: his turn in
  BurningBodies.

The move to the pads RX and TX, 2026-11-11 (the PO: "lets go with TX and RX though"). `requirements.json` puts GA on
RX (GPIO44) and GB on TX (GPIO43). Entries 20 to 24 have no wire on the pads they test, and nobody turned a knob
there. Entries 25 to 27 have the encoder on RX and TX, and 26 and 27 have the PO's hand. Entries 20 to 26 are
scratch scripts, not in the repository.

| entry | log | what ran | result |
| --- | --- | --- | --- |
| 20 | run171-p757-pads-txrx.log | RX and TX: the pads' registers as the script finds them and after `Pin(n, Pin.IN, Pin.PULL_UP)`. Then 5 detents made with the chip's pulls, counted by `machine.Encoder`, with the I2S closed and open | as found: IO_MUX 0xb00 on both pads. After `Pin()`: 0x1b00, output off. 20 edges for 5 detents with the I2S closed and with it open, and the count stays at 20 for 1 s at rest with the I2S open. The script also set the console's input to a constant 1 (`in_sel` 0xb8) and left it so |
| 21 | run172-p757-pads-txrx-control.log | 20 low pulses of 2 ms on RX by the chip's pull-down, bytes counted at the REPL's input, with the pad as function 0 and as function 1 | 0 bytes in both. Not valid as a control: entry 20 left `in_sel` at 0xb8, so the console's input was a constant 1 in both stages |
| 22 | run173-p757-pads-joystick.log | A0, A1 and D5, the joystick's reserved pads: 200 digital reads under each pull, and 200 ADC reads under each pull | each pad follows the chip's pulls: 1 in 0 of 200 reads under the pull-down and in 200 of 200 under the pull-up. ADC 0 mV under the pull-down and 3071 mV under the pull-up |
| 23 | run174-p757-pads-console.log | after `machine.deepsleep(300)`, so the registers are the image's. The UART's own input bit (UART_STATUS_REG, bit 15) under the chip's pull-down and pull-up on RX, 200 reads each, and its break bit after 20 low pulses of 2 ms. Stage 1: the pad as the image has it. Stage 2: after `Pin(44, Pin.IN, Pin.PULL_UP)`. Stage 3: also with `in_sel` 0xb8 | stage 1: IO_MUX 0xb00, the bit reads 1 in 0 of 200 under the pull-down and 200 of 200 under the pull-up, break 1 (`int_raw` 0x82). Stage 2: IO_MUX 0x1b00, 200 of 200 under both pulls, break 0 (`int_raw` 0x2). Stage 3: the same as stage 2 |
| 24 | run175a-p757-app-takes-pads-control.log, run175-p757-app-takes-pads.log | the board restarts through `machine.deepsleep(300)`, `main.py` starts `app.run`, and about 6 s after the USB port is back mpremote stops it. A script then reads the IO_MUX word of both pads and calls no `Pin()`. First with the board's `app.py` from before this change, then with the `app.py` of commit 9ec1212 | before: 0xb00 on both pads. With `encoder.take_pads` in `app.run`: 0x1b00 on both |
| 25 | run176a-p757-txrx-rest.log | the encoder on RX and TX, no hand. `take_pads`, `Encoder.on_board`, and one counter of rising edges on each pad. 2 s with no sound, then 2 s with the I2S open and a tone of 437.5 Hz. The caller set the 2 s, and the log does not print it | IO_MUX 0x1b00 on both pads as found and at the end. GA 1 and GB 1 at rest. 0 edges in both windows, so the tone made no edge. No break and no frame error |
| 26 | run176-p757-txrx-hand.log | the same script with the PO's hand: 10 s with no sound from his first edge, then 10 s with the tone. The ask was about ten clicks one way and about ten back, in each window | no sound: the count went to -28 edges (7 detents) and back to +1. Rising edges: GA 17, GB 15. GA read low in 61219 of 154433 loop reads, and the UART's input read low in 0 of them. With the tone: the count went to +18, then down to -25. Rising edges: GA 22, GB 17. GA read low in 177 of 626 loop reads, and the UART's input in 0. No break, no frame error and no KeyboardInterrupt in both windows |
| 27 | run176c-p757-txrx-fire.log | `VOLUME=ViperMasterVolume KNOB=1 tools/crackle.sh 45 FireSound`. The ask: down to silent, then up to full | the step went from 8 to 0 (edges 0 to -31). The count went on to -40 at step 0. The step then went from 0 to 16 (edges -36 to 23) and stayed at 16 while the count ran to 177. Then it went down to 7 and back up to 16. 8 sound lines, each with `late 0` and `pushes 0`. 8 crackle lines, each with `dropped 0`. `apply_max` at most 360 us. `written 720384 short 0` |

- Measured, with no wire: the pulse counter counts on RX and TX, with the I2S open too (entry 20).
  `Pin(n, Pin.IN, Pin.PULL_UP)` alone cuts the console's input from the RX pad (entry 23), so `take_pads` writes no
  register. After a game started, both pads are plain inputs (entry 24).
- What entries 20 to 24 do not show. The edges of entry 20 came from the chip's own pulls, which swing the full
  range, and its I2S was mono. So they do not show that a real contact counts on these pads with the sound on.
  Entries 26 and 27 show that. Entry 24 is one
  read after mpremote stopped the game: that `take_pads` is the first statement of `app.run` is read from
  `games/app.py`. Entry 23 rests on the image's route: the console's input comes straight from the IO_MUX
  (`in_sel` 0x3c as found). A `machine.UART(0, ...)` call can route it through the GPIO matrix, and then `Pin()`
  does not cut it. No game makes a UART. Stage 2 of entry 23 did not read the pad's own level under the pull-down.
- The register names, the restart through `machine.deepsleep(300)` and the wait of 6 s in entries 21, 23 and 24
  come from the scripts. The logs do not print them.
- Read from the source, not measured: until `take_pads`, the console holds TX high and each `print` toggles it. A
  byte on RX goes to the console, and the byte 0x03 stops the program (MicroPython v1.29, `ports/esp32/uart.c`).
- A limit that stays: from the reset until `app.run` starts, the console owns both pads. A turn of the knob in that
  time can type into the console. The time is not measured, and it has no fixed end. The console keeps both pads
  when the start stops before `take_pads`: a Ctrl-C from mpremote, an import that fails, a byte 0x03 on RX, or a
  probe that does not call it. The full fix is an image with no serial console on these pads.
- The meter rule (under 1 kΩ from GB to GND means stop) does not depend on that time. The limit is a choice, not
  a datasheet fact: at 1 kΩ, a pad at 3.3 V drives 3.3 mA. Not checked: parts of the board's own on the RX and TX
  pads. Entry 20 shows that both pads follow the chip's pulls with no wire.
- `app.py` now needs this change's `encoder.py` and `pins.py` on the board. With `KNOB=1`, `tools/crackle.sh`
  copies all three.
- A control starts from a known state (entries 20 and 21). `mpremote reset` did not put `in_sel` back, and a restart
  through deep sleep did (entry 23, "as found"). Three failed tries of entry 23 are kept: `run174a` (no restart
  before it), `run174b` (the USB port was not back yet) and `run174c` (after a soft restart).
- The pads A0, A1 and D5 have no wire and follow the chip's pulls (entry 22). They are a second place for an
  encoder. No run tested an encoder there.
- spark's build writes the pin map, the sheet and the board for the new pads, and its simulation stage fails:
  `"44" is not a pin of board-esp32-s3-devkitc-1`. So `build/sim/` is from before the move. That is not a pass.
- Open before the plug, and answered in the three bullets below: the PO's meter reading from GB to GND with the
  power off, and his turn with the wires on RX and TX.
- The PO's meter, 2026-11-11, with the USB and the battery unplugged and the encoder's VCC and GND on the rails:
  "its about 180 kOhm and goes low when turned, from GB to VCC its around 6,6 kOhm". So GB to GND reads about
  180 kΩ at rest, and GB to VCC about 6.6 kΩ. Both are readings in the circuit, not on a bare module.
  Two web searches found no schematic of the CJMCU-111, as the part record says.
- The PO's next reading, the same day, from GB to GND with the contact closed: "I think it's 3,3 kOhm". That is
  above the limit of 1 kΩ, so the rule lets GB go on TX. The console's high level then drives about 1 mA into a
  closed contact (3.3 V across 3.3 kΩ). His "I think" stays in the record: it is one reading, and run176 reads
  the closed level on the pad as a second look. VCC to GA is not read yet.
- Measured with the PO's hand, the same day (entries 25 to 27). The pulse counter counted on RX and TX while he
  turned the knob: with no sound, with a tone, and with Fire's sound. Both pads read 0 and 1 in entry 26. In
  Fire the step went from 0 to 16 over the edges -36 to 23, which is 59 edges for 16 steps. In entry 26, while
  GA was low on RX, the UART's input read high in every read. Entry 27 did not read the UART.
  The PO after the Fire run: "yeah, seems to be working."
- What entries 25 to 27 do not show. The board cannot say what the PO's hand did or what his ear heard. So
  "the count follows his hand" rests on the shape of the count and on his word above, which does not name the
  16 steps. Entry 26 has more rising edges than
  one for each detent on each pad. With no sound: 17 and 15 for about 14 detents. With the tone: 22 and 17 for
  about 15. Bounce longer than the filter's 12 us can explain it, and that is inferred, not measured. The count itself came back
  to +1. Not known: if GA or GB rests low in some places of the knob. Two state lines of entry 26 read GA 0
  between the turns, but the PO's hand was on the knob then. No run starts the board with a contact closed on
  RX, where the console holds the pad until `take_pads`.

### Slice 4: the save

`VolumeStore` keeps the step in `volume.txt` on the board (littlefs2, 3584 blocks of 4096 B, 2231 free). `VolumeKnob`
saves the step 3 s after its last change. The stress run saves each second, whatever the knob does
(`SAVE=1 SAVE_EVERY_MS=1000`). It ran as two runs of 30 s, not one of 60 s, because the probe leaves Fire after 30 s.

| entry | log | what ran | result |
| --- | --- | --- | --- |
| 6 | run158a-p757-fire-save-stress.log | Fire with `FireSound`, `ViperMasterVolume`, `KNOB = 1`, a save each second, 30 s, hands off | `stored level None`, 24 saves, save_max 14 to 19 ms, save_errors 0, late 0, fps 24, 24, 24, 23, 23 |
| 7 | run158b-p757-fire-save-stress.log | the same again | `stored level 8`, 22 saves, save_errors 0. One save took 2600 ms: in its 5 s line sent 155 of 313, between_max 2601 ms, late 1, short 40464 samples, fps 11, worst frame 2622 ms. The other lines: save_max 13 to 19 ms, fps 24, 23, 23, 24 |
| 8 | run159-p757-save-times.log | 200 saves of `volume.txt` in a loop, no sound, no game | saves 14, 51, 88, 125, 162 and 199 took 2407 to 2417 ms each: each 37th save. The other 194 took 5.2 ms each (mean) |
| 9 | run160-p757-nvs-times.log | 200 saves into the board's NVS (`esp32.NVS`: `set_i32`, `commit`), no sound, no game | 0.8 ms each (mean), the worst 10.6 ms, five saves over 5 ms (each 34th or 35th). The read gave the last value. The probe's key is erased again |

- The save into a file breaks the sound. Each 37th save stops the game loop for 2.4 s. The sound's ring holds 64 ms,
  so the speaker is silent for 2.5 s and the picture stands still. The other saves (13 to 19 ms beside the game)
  made no `late` count.
- The cause of the 2.4 s is not measured. The period of 37 saves is a fact of run159, on this board's file system
  as it is filled now.
- By the plan, the save stays behind `SAVE` (default 0), and the fix is a later card. Entry 9 is one candidate:
  a store in the NVS. Its worst save is under one block of 16 ms, but it is not measured beside the sound.
- The step survives a restart of the probe: entry 7 read the 8 that entry 6 saved. Not done yet: the knob's own save
  on the board (turn, wait 3 s, reset the board, the same level). Nobody turned the knob in these runs.

## P762 (#1049), 2026-11-11: the system overlay shows the volume

The overlay (`games/overlay.py`) shows the volume's picture for 1 s after each change of the step. Entries 1, 2 and 6
ran `VOLUME=ViperMasterVolume KNOB=1 tools/crackle.sh 45 FireSound`, with nobody at the board.

| # | log | what ran | result |
|---|-----|----------|--------|
| 1 | run177a-p762-nohand.log | no hand: the step stays at 8, and the overlay never shows | 8 sound lines, each with `late 0` and `pushes 0`. `between_max` 39 to 47 ms. Frame `worst` 56 to 69 ms, `slowest` 52 to 54 ms, mean paint 10.1 to 10.7 ms. `apply_max` at most 306 us. `windows_max 1` in each line. `written 720896 short -48` |
| 2 | run177b-p762-spin.log | `SPIN_EVERY_MS=3000`: the probe turns the step to an end, 1 step per frame, 12 times. The first spin starts at the step of the start, each later one at the other end | 8 sound lines, each with `pushes 0`. `late` is a running count: 0, 0, 1, 3, 4, 4, 4, 4. `between_max` 44 to 49 ms. Frame `worst` 61 to 83 ms, `slowest` 54 to 70 ms, mean paint 11.4 to 14.3 ms. `apply_max` at most 385 us. `windows_max 1` in each line. `written 720128 short 96` |
| 3 | run177c-p762-paint-time.log | `probe762_paint.py`: one repaint of the picture into its kept strip, the least of 5, no game, no sound | 3765 us. Its parts: the fill 217, the border 305, the text `vol` 1654, the 16 cells 1086, the text `16` 1120 |
| 4 | run178-p762-hand.log | the same command for 120 s, with the PO's hand on the knob and his eye on the screen. The picture was still one kept picture | the PO: "nice". 123 changes of the step, between 0 and 16, some by 2 steps in one frame. 23 sound lines. `late` is a running count and ended at 5. `between_max` 38 to 49 ms. 22 to 24 frames per second, `worst` 59 to 93 ms, `slowest` 54 to 79 ms. `apply_max` at most 347 us. `windows_max 1` in each line. `written 1920256 short 256` |
| 5 | run179a-p762-paint-time.log | `probe762_paint.py` after the split of the picture into a still part and a level part, at step 16 | the still part 2229 us, painted once. The level part (the cells and the number) 2204 us, painted at each new step |
| 6 | run179b-p762-spin.log | entry 2 again with the split picture: `SPIN_EVERY_MS=3000`, 12 spins | 8 sound lines. `late` 1 in the first line and no more after it. `between_max` 39 to 48 ms. 23 to 24 frames per second, `worst` 59 to 109 ms, `slowest` 52 to 65 ms, mean paint 10.9 to 13.1 ms. `windows_max 1` in each line. `written 720384 short 128` |
| 7 | run180-p762-spin-alpha.log | entry 6 again with the still part at alpha 192, so the game shows through it. The cells and the number stay solid | 8 sound lines. `late` 0 in the first two lines, then 2 to the end. `between_max` 35 to 49 ms. 23 to 24 frames per second, `worst` 65 to 77 ms, `slowest` 62 to 68 ms, mean paint 12.0 to 14.7 ms. `written 720128 short 80` |

- Entry 1 is the control run. The overlay's code in the frame adds no `late` count while nothing shows.
- The sound's margin in Fire is small. The longest gap between two refills was 47 ms in entry 1, and a gap over
  48 ms is a `late` count (`games/sound.py`, `late_us`). With the picture on the screen the longest gap reached
  49 ms (entries 2, 4 and 7). So the 1 ms of margin is the state without the overlay only.
- Entry 2 is the costly case: each frame of a spin paints the picture again. It made 4 late refills in 45 s.
  Nobody listened, so no run shows that a late refill is heard.
- A repaint of the whole picture took 3.8 ms, and the two texts took 2.8 ms of it (entry 3, at step 8).
- With the PO's hand the whole picture made 5 late refills in 120 s (entry 4). His word on the picture is "nice".
  He said nothing about a gap in the sound, so no run shows that a late refill is heard.
- `pushes` is the count of raw BOOT interrupts, not a fault of the sound. In entry 4 it rose to 3: the button was
  pressed. The lines with `pushes 0` in the other entries say only that nobody pressed it.
- After entry 4 the picture became two kept pictures. A new step paints only the cells and the number again:
  2.2 ms against 3.8 ms (entry 5). Entry 5 ran at step 16 and entry 3 at step 8, so its number has 2 characters
  against 1. The first show paints both parts, 4.4 ms against 3.8 ms.
  The same stress then made 1 late refill against 4 (entries 6 and 2).
  That is one run on each side, so it is a first sign and not a proof.
- The one late refill of entry 6 is in the 5 s of the first show, where both parts are painted in one frame.
  The cause is not shown by the run.
- `windows_max` is 1 in each line, and that shows nothing about the overlay. Fire marks the whole frame at each
  frame, so its frame is always one window (read in the driver by the review's refuter). A game with partial sends
  is the test, and none ran.
- Read, not measured: on `lcd.py` the hidden picture leaves the screen through the driver's tiles (`frame.c`).
  The PO saw the picture on the board. He named no time for its end.
- The see-through picture ran (entry 7): 2 late refills against 1 for the solid picture (entry 6), one run on each side.
  The mean paint was about 1 ms longer per frame. The driver blends each of the still part's 5600 pixels.
- The plan's rule was: if a sound line is late with the blend, the picture stays solid. So `VolumeView.alpha` is 255.
  `ALPHA=192` on the command shows the see-through picture. Nobody looked at it yet.
- The rule assumed that the solid picture gives `late 0`. Entries 2, 4 and 6 show that it does not.
  So the rule does not separate the two pictures, and the choice is the PO's.
- Not shown by any run: the split picture under the PO's hand, and the picture in any game but Fire.

## P764 (#1051), 2026-11-11: the overlay holds panes (PR A)

The overlay holds a list of panes, and `VolumePane` shows itself at each change of the volume's step. It is
see-through: alpha 192 in entries 1 to 7, and 128 after the PO's pick (entry 9). Each run is
`VOLUME=ViperMasterVolume KNOB=1 tools/crackle.sh <seconds> FireSound`, in Fire, with `pushes 0` and 23 or 24 frames
per second. Entries 1 to 6 ran for 45 s each, between 12:17 and 12:24 CET, with 8 sound lines each.

| # | log | what ran | result |
|---|-----|----------|--------|
| 1 | run181a-p764-nohand.log | this PR's code, no hand, no spin: the pane never shows | `late 1` from the first line on, and no more after it. `between_max` 36 to 48 ms. Frame `worst` 56 to 99 ms, `slowest` 51 to 54 ms, mean paint 10.1 to 10.8 ms. `written 720384 short 176` |
| 2 | run181b-p764-spin.log | `SPIN_EVERY_MS=3000`, the pane's own alpha (192). The knob turned during the run: `edges 15` at the second volume line and `edges 164` at the fourth, with 37 `level` lines between them. The PO turned it: "i did turn it" | `late 0` in each line. `between_max` 41 to 47 ms. `worst` 60 to 82 ms, `slowest` 57 to 64 ms, mean paint 11.8 to 14.5 ms. `written 720128 short 80` |
| 3 | run181c-p764-spin-solid.log | `ALPHA=255 SPIN_EVERY_MS=3000`: 12 spins, the solid picture, edges 0 | `late` is a running count: 0, 0, 1, 1, 1, 2, 2, 2. `between_max` 40 to 49 ms. `worst` 58 to 94 ms, `slowest` 52 to 62 ms, mean paint 11.0 to 13.0 ms. `written 720640 short 16` |
| 4 | run182a-p764-master-nohand.log | the control: `master`'s code (4a7bb01's files, worktree `pixel-p762`), `ALPHA=255`, no hand, no spin | `late 0` in the first line, then 1 to the end. `between_max` 44 to 48 ms. `worst` 54 to 75 ms, `slowest` 52 to 56 ms, mean paint 10.3 to 11.2 ms. `written 720384 short 224` |
| 5 | run182b-p764-nohand.log | entry 1 again | `late 0` in each line. `between_max` 40 to 46 ms. `worst` 54 to 70 ms, `slowest` 51 to 53 ms, mean paint 10.0 to 10.7 ms. `written 720384 short 112` |
| 6 | run182c-p764-spin.log | `SPIN_EVERY_MS=3000`, the pane's own alpha (192): 12 spins, edges 0 | `late 0` in the first line, then 1 to the end. `between_max` 39 to 48 ms. `worst` 60 to 88 ms, `slowest` 53 to 63 ms, mean paint 11.7 to 14.0 ms. `written 719872 short 224` |
| 7 | run183-p764-hand.log | 90 s with the PO's hand and eye, the pane at alpha 192 | the PO: "yeah, it could be more see through". 78 changes of the step, between 0 and 16. 17 sound lines, `late` a running count that ended at 3. `between_max` 34 to 49 ms. `worst` 59 to 91 ms, `slowest` 53 to 61 ms, mean paint 10.2 to 14.5 ms. `written 1440768 short 96` |
| 8 | run184-p764-hand-alpha128.log | `ALPHA=128`, 45 s. It started 9 s after entry 7 ended, and the knob did not turn: no pane showed | 8 sound lines, `late 0` in seven and 1 in the last. `between_max` 44 to 48 ms. `worst` 53 to 99 ms, `slowest` 49 to 54 ms, mean paint 10.1 to 10.7 ms. `written 720640 short 192` |
| 9 | run185-p764-hand-alpha128.log | `ALPHA=128`, 60 s with the PO's hand and eye | the PO: "yes, nice". 51 changes of the step, between 4 and 16. 11 sound lines, `late` 0 in five lines, then 1 to the end. `between_max` 35 to 49 ms. `worst` 57 to 83 ms, `slowest` 52 to 64 ms, mean paint 10.4 to 13.8 ms. `written 961024 short 16` |

- The plan's pass rule has two parts. The first is `late 0` in each sound line of the run with no hand and no spin,
  as in run177a. Entry 5 meets it. Entry 1 does not: it has 1 late refill. The second part is the PO's read of the
  see-through picture with his hand on the knob: entries 7 and 9. He chose alpha 128, so `VolumePane.alpha` is 128.
  Entry 8 is one more run with no pane on the screen and 1 late refill, on this PR's code.
- The plan named runs on this PR's code only. Entry 4, the control on `master`'s code, is an addition, made after
  entry 1 was late. It has no hand and no spin, so no pane shows in it: it is no control for the spin runs or for
  `ALPHA`.
- What differs from `master` while the picture shows: the pane's 1 s starts at the next frame's `update`, so the
  picture can stay one frame longer. Any change of the step shows it, not only the knob and the spin. And
  `VolumePane.update` runs in each frame, also while hidden. Its time is not measured.
- The control on `master`'s code (entry 4) also has 1 late refill. So a run with no hand gives 0 or 1 late refill
  in 45 s on both codes, and these runs show no difference between them. The sound's margin in Fire is 1 ms
  (P762), and a run with nothing on the screen can cross it.
- The spin runs are a record only, as the plan says: 1 late refill see-through (entry 6) against 2 solid (entry 3),
  one run each. That is the other order than in P762 (2 against 1), so no rule rests on it.
- Entry 2 is no clean spin run, because the PO turned the knob in it. It is the only run of this PR with a turned
  knob, and it has no late refill. He did not say what he saw on the screen.
- In the spin runs the pane shows with no `show` call from the probe: the mean paint rose by 1 to 4 ms against the
  runs with no spin, as in P762. Nobody looked at the screen in the spin runs. The PO looked in entries 7 and 9.
- With his hand the runs had 3 late refills in 90 s (entry 7) and 1 in 60 s (entry 9). He named no gap in the sound.
- Entries 7 to 9 ran from 12:31 to 12:36 CET, on c3d0ee0. No run is on the code with the default 128: entries 8
  and 9 set 128 with `ALPHA`.
- Not run: any game but Fire.

## P764 (#1051), 2026-11-11: the knob in the game box (PR B)

The game box opens the rotary encoder as the volume's knob, polls it in each frame and adds the volume pane
(alpha 128). `probe764_box.py` runs the box over all 14 games, 12 s each, and prints one `box` line per game. Each
run is `mpremote run probe764_box.py` with no hand on the board: 12:40 to 12:43 CET (`run186-p764-box-master.log`),
12:44 to 12:46 (`run187-p764-box-knob.log`) and 12:46 to 12:49 (`run188-p764-box-spin.log`, with
`SPIN_EVERY_MS = 3000`). Run 0 has `master`'s `app.py` and `overlay.py` on the board. Runs 1 and 2 have this PR's
`app.py`, `overlay.py`, `volume.py`, `encoder.py` and `pins.py`. Each cell holds the two `time` lines of a game,
first and second. Nobody pressed a button, so a game with a title screen stayed there or played its own demo.

| game | run 0: `master` (0b79320), no knob | run 1: this code, no spin | run 2: this code, the spin | windows_max |
| --- | --- | --- | --- | --- |
| fire | fps 24, 24; worst 50, 53 ms; step 7.0, 7.0 ms; paint 9.6, 9.4 ms | fps 24, 24; worst 60, 60 ms; step 7.4, 7.5 ms; paint 10.5, 10.3 ms | fps 24, 24; worst 66, 59 ms; step 7.4, 7.4 ms; paint 11.6, 11.5 ms | 1, 1, 1 |
| balls | fps 24, 24; worst 54, 53 ms; step 2.6, 2.6 ms; paint 7.7, 7.3 ms | fps 24, 24; worst 57, 61 ms; step 2.8, 2.9 ms; paint 7.9, 8.2 ms | fps 24, 24; worst 61, 58 ms; step 2.9, 2.9 ms; paint 9.3, 9.0 ms | 1, 1, 1 |
| burning | fps 24, 24; worst 54, 61 ms; step 8.7, 8.9 ms; paint 16.0, 16.8 ms | fps 24, 24; worst 57, 69 ms; step 9.0, 9.1 ms; paint 16.3, 17.0 ms | fps 24, 24; worst 57, 62 ms; step 8.8, 9.1 ms; paint 17.4, 17.8 ms | 1, 1, 1 |
| rain | fps 24, 23; worst 62, 65 ms; step 2.3, 2.5 ms; paint 27.0, 26.7 ms | fps 24, 23; worst 70, 71 ms; step 2.7, 2.8 ms; paint 28.5, 28.3 ms | fps 23, 23; worst 80, 76 ms; step 2.6, 2.7 ms; paint 29.1, 28.8 ms | 1, 1, 2 |
| flappy | fps 22, 20; worst 79, 63 ms; step 0.8, 0.5 ms; paint 33.1, 41.0 ms | fps 22, 20; worst 85, 67 ms; step 1.1, 0.7 ms; paint 32.3, 39.8 ms | fps 22, 20; worst 84, 70 ms; step 1.0, 0.6 ms; paint 32.2, 38.9 ms | 4, 4, 4 |
| runner | fps 22, 19; worst 111, 69 ms; step 3.7, 0.4 ms; paint 31.0, 43.6 ms | fps 22, 20; worst 117, 68 ms; step 4.1, 0.8 ms; paint 30.1, 41.7 ms | fps 22, 19; worst 76, 115 ms; step 4.2, 1.0 ms; paint 30.0, 41.5 ms | 4, 4, 4 |
| snake | fps 24, 25; worst 66, 40 ms; step 0.7, 0.7 ms; paint 18.5, 11.8 ms | fps 24, 24; worst 70, 41 ms; step 1.0, 0.9 ms; paint 17.7, 11.6 ms | fps 24, 24; worst 78, 42 ms; step 0.9, 0.9 ms; paint 18.0, 12.5 ms | 4, 4, 4 |
| stack | fps 25, 25; worst 42, 40 ms; step 0.7, 0.7 ms; paint 13.3, 11.2 ms | fps 25, 25; worst 41, 41 ms; step 1.0, 1.0 ms; paint 13.0, 11.0 ms | fps 25, 25; worst 43, 43 ms; step 1.0, 1.0 ms; paint 14.2, 12.3 ms | 1, 1, 1 |
| cave | fps 22, 21; worst 80, 62 ms; step 0.9, 0.4 ms; paint 34.5, 39.5 ms | fps 22, 20; worst 86, 66 ms; step 1.1, 0.7 ms; paint 33.9, 39.6 ms | fps 21, 20; worst 72, 72 ms; step 1.1, 0.6 ms; paint 34.1, 40.2 ms | 1, 4, 4 |
| tunnel | fps 23, 21; worst 79, 76 ms; step 1.0, 0.5 ms; paint 28.9, 39.0 ms | fps 23, 21; worst 68, 65 ms; step 1.3, 0.8 ms; paint 27.7, 38.6 ms | fps 22, 20; worst 77, 62 ms; step 1.2, 0.7 ms; paint 29.6, 39.6 ms | 4, 4, 4 |
| road | fps 21, 12; worst 120, 93 ms; step 0.9, 0.6 ms; paint 36.7, 51.4 ms | fps 22, 21; worst 69, 129 ms; step 1.0, 1.2 ms; paint 34.4, 36.8 ms | fps 21, 12; worst 113, 96 ms; step 1.2, 0.8 ms; paint 36.5, 53.0 ms | 4, 4, 4 |
| starfire | fps 24, 24; worst 66, 54 ms; step 1.2, 1.4 ms; paint 21.3, 25.5 ms | fps 24, 24; worst 67, 54 ms; step 1.4, 1.6 ms; paint 21.4, 25.5 ms | fps 24, 24; worst 66, 52 ms; step 1.4, 1.6 ms; paint 22.4, 27.0 ms | 4, 4, 4 |
| cube | fps 24, 24; worst 66, 68 ms; step 0.8, 0.9 ms; paint 20.2, 15.7 ms | fps 24, 24; worst 79, 67 ms; step 1.0, 1.2 ms; paint 19.0, 15.8 ms | fps 24, 24; worst 74, 67 ms; step 1.0, 1.2 ms; paint 20.5, 17.1 ms | 4, 4, 4 |
| gravpong | fps 23, 22; worst 64, 54 ms; step 0.9, 0.5 ms; paint 29.7, 33.6 ms | fps 24, 23; worst 59, 63 ms; step 1.1, 0.7 ms; paint 27.7, 30.8 ms | fps 23, 23; worst 58, 65 ms; step 1.1, 0.7 ms; paint 28.4, 30.7 ms | 4, 4, 4 |

- Each log has 188 lines, 14 `box` lines and `done`, with no error and no traceback. Run 0 prints `knob 0`, and
  runs 1 and 2 print `knob 1`.
- Run 0 against run 1, the cost of the open knob and its poll: the mean step rose by 0.1 to 0.5 ms in each game
  (Road's second line by 0.6 ms). The frames per second are the same or differ by 1, but for Road's second line.
- Road's second line is 12 frames per second in runs 0 and 2 and 21 in run 1. Runs 0 and 2 have different code and
  agree, so the knob does not explain it. The cause is not known, and this line compares nothing.
- Run 1 against run 2, the cost of the picture: Road apart, the mean paint changed by -0.9 to +1.9 ms. In Fire, Balls,
  Burning, Stack, Starfire and Cube it rose in both lines, by 0.8 to 1.5 ms. Rain, Snake, Cave and Tunnel also rose in both lines (0.2 to 1.9 ms).
  Flappy and Runner fell in both lines, and Gravpong's two lines do not agree. Each game had 3 spins but Road, which had 2. The frames per second are the same or 1 lower,
  but for Road's second line.
- `windows_max` is the same in the three runs but in Rain (1, 1, 2) and Cave (1, 4, 4). Cave's 4 came with no
  picture on the screen (run 1), so the picture did not cause it.
- In run 1 the step stayed 8 in each game: the knob did not turn.
- `worst` moves between the runs in both directions (Runner 111, 117, 76 ms in the first line), so one run per
  code gives no verdict on it.
- Every caller of `app.run()` now gets the knob: `probe550.py`, `tools/probe635.py`, the p612 probes and each sound
  run with `KNOB=0`. A run before this PR is no control for a run after it. `overlay.py` imported `volume.py` before this PR, and
  `app.py` now also needs `encoder.py`'s `Encoder` and `pins.py`'s encoder pins on the board.
- The sound with the box's knob (`run189-p764-box-sound-spin.log`, 12:52 CET, 45 s, no hand:
  `VOLUME=ViperMasterVolume KNOB=1 SPIN_EVERY_MS=3000 tools/crackle.sh 45 FireSound`): 8 sound lines, `late 0` in
  the first two, then a running count that ended at 3. `between_max` 43 to 50 ms, `edges 0`, `windows_max 1`,
  23 or 24 frames per second, `written 720640 short 272`. PR A's same run had 0 late refills (run181b, with the
  PO's turns) and 1 (run182c). One run each gives no verdict on the difference.
- The tool with its new copy list and `KNOB=0`, so the box opens its own knob
  (`run190-p764-box-sound-knob0.log`, 12:54 CET, 30 s, no hand: `VOLUME=ViperMasterVolume KNOB=0 tools/crackle.sh
  30 FireSound`): 5 sound lines, `late 0` in each, `between_max` 40 to 47 ms, the step stayed 8, `done`.
- Not tested and not run: `run()` with a caller's knob has no Mac test (the Mac has no `machine`). Runs 189 and
  190 cover its two paths on the board. An error from `Encoder.on_board` in `open_knob()` stops `run()`.
- Not run: a game in play, the PO's hand and eye in the games.

## P768 (#1058), 2026-11-11: the game box plays a sound (PR 1)

The box (`app.run`) now takes a `Speaker`. `Runner` emits `jump` and `die`, and each plays its sound from
`games/box_bank.raw` through one voice. `probe768_box.py` ran `Runner` for 120 s with no hand: a press every 900 ms
while the game plays. The image and the board are those of P764. Each run has 22 `time` lines and 22 `sound` lines after the first, and the table reads those 22.

| Run | Log | Speaker | Mean fps | Worst frame, per 5 s | Late refills | `between_max` | `render_max` | Plays |
|---|---|---|---|---|---|---|---|---|
| 191 | `run191-p768-runner-silent.log` | none (the control) | 22.0 | 70 to 95 ms | - | - | - | - |
| 192 | `run192-p768-runner-sound.log` | opened before the first game's setup | not read | not read | 14, all in the first 5 s | 163 ms, then 34 to 38 ms | 2370 us, then 297 to 400 us | not summed |
| 193 | `run193-p768-runner-sound.log` | opened after the setup, no volume | 21.1 | 73 to 107 ms | 0 | 33 to 42 ms | 2353 us, then 319 to 492 us | 99 |
| 194 | `run194-p768-runner-sound-knob.log` | as 193, with the knob's `ViperMasterVolume` and the soft sounds | 21.0 | 74 to 101 ms, and one of 135 ms | 0 | 34 to 39 ms | 2376 us, then at most 456 us | 98 |

- Run 192 found a fault: the first refills waited behind the first game's setup, so 14 were late. `run()` now opens
  the `Speaker` after `app.start()`. Runs 193 and 194 have 0 late refills.
- The sound costs about 1 frame per second in `Runner` (22.0 against 21.1 and 21.0). The worst frame of a 5 s line
  is about 5 to 10 ms longer with the sound. One run per case gives no verdict on the line of 135 ms.
- The first render of each run takes about 2.4 ms. The likely cause is the `Mixer`'s block of zeros, which the
  first render makes. No run tested that cause. Later renders take at
  most 0.5 ms. `render_max` includes the probe's own timer.
- Free flash with the bank on the board: 9084928 of 14680064 bytes, read with `os.statvfs` before run 191 (not in
  a log). The bank is 23040 bytes.
- `main.py` now opens the `Speaker` for all 14 games, so each game pays the refill 62 times a second, also a
  game with no cue. Only `Runner` ran. PR 3's run measures the other 13 games.
- One voice plays, so a `die` within 120 ms of a `jump` cuts the jump, and a switch cuts a sound. A cut can click.
  PR 2's voices end the first case.
- Not run: a switch of the game (D14) with the `Speaker` open. Each run held one game. A switch collects the
  heap and sets up a game, so its refills can be late. PR 3's run of all 14 games measures it.
- Not run: the amplifier's tone check of the plan's step 1 (the PO dislikes tones). The runs with the sound are
  the amplifier's check. No microphone ran, so no run measured the delay from a press to its sound.
- The PO, during run 193: "I wasn't able to lower the volumr now, btw. And the sounds should be nice and not
  aggressive". The probe gave the `Speaker` no volume in runs 192 and 193. From run 194 it passes the knob's
  volume, as `main.py` does. The sounds of runs 192 and 193 were a sweep to 990 Hz at peak 9000 and a noise burst at
  peak 11000. These are the tool's values at commit 07d6917. From run 194 they are pure sine notes with a 10 ms rise. The
  tool's peaks are 3000 and 3200, and the largest samples in the bank are 2519 and 2993.
- After the review, `run195-p768-runner-sound-20s.log` (20 s, the fixed code): 3 sound lines, `late 0`, `done`.
- The PO after run 194: "yeah, ok, go on automatically, add all the sounds and overlays". His hand on the knob
  with the box's sound is not confirmed in words.

## P768 (#1058), 2026-11-11: the voices, the fire and Runner's sounds (PR 2)

`Mixer(voices, voice_sum)` sums its voices. `VoiceSum` is the plain Python reference, and `ViperVoiceSum`
(`games/sound_viper.py`) is the fast one. `probe768_sum.py` measured one render of 256 samples, 100 times, with
looping voices at gain 20000 and no game beside it (`run197-p768-sum.log`, and `run196-p768-sum.log` before the bank
moved):

| Voices | `VoiceSum` mean / max | `ViperVoiceSum` mean / max |
|---|---|---|
| 0 (silent) | 2017 / 2134 us | 129 / 228 us |
| 1 | 3777 / 3940 us | 261 / 396 us |
| 2 | 5543 / 5709 us | 396 / 549 us |
| 4 | 9080 / 9242 us | 664 / 821 us |
| 8 | 16150 / 16297 us | 1200 / 1391 us |

- `sum match 1`: the viper sum gave the plain sum's samples on the board, from an array and from a bank's bytes.
- The pass line was a render of at most 1000 us. The viper sum passes with 4 voices and fails with 8, so the
  `Speaker` has 4 voices. The plain sum is the reference: with 4 voices it takes 9 ms of each 16 ms block.
- `gc.collect()` with nothing else on the heap: 548 to 611 us. With a 300000-byte `array("h")` on the heap: 9915 to
  19206 us. With the same bytes in an `engine.SoundBank`: 548 to 801 us. So `Bank` keeps the file in a `SoundBank`.

`Runner`, 120 s, no hand, a press every 900 ms (`probe768_box.py`), with `jump`, `land`, `pickup`, `footstep`, `die`
and the fire loop. The 22 lines after the first:

| Run | Log | Mean fps | Worst frame, per 5 s | Late refills | `between_max` | `render_max` | Plays |
|---|---|---|---|---|---|---|---|
| 198 | `run198-p768-runner-silent.log` | 21.1 | 72 to 115 ms | - | - | - | - |
| 199 | `run199-p768-runner-voices.log` | 20.9 | 77 to 112 ms | 0 | at most 38 ms | 847 us in the first line, then at most 862 us | 410 |

- The four pass lines hold: the render is under 1000 us, 0 late refills, the mean fps differs by 0.28 (21.14 and
  20.86), and the longest frame is 112 ms against 115 ms (the shortest worst frame is 77 ms against 72 ms). The first render is no longer slow (PR 1: 2.4 ms).
- The silent run is 0.9 fps under PR 1's silent run (run191, 22.0). One run each gives no verdict on the cause.
- Not known from the log: if the fire loop played. The log counts plays and does not name them. The Mac test
  covers the cue, and the PO's ear is the check.
- Not run: a switch of the game with the sound on, and the other 13 games (PR 3).
- Open: the PO's ear on all sounds together and his hand on the knob.
- After the review (PR 67): `Mixer.slot()` keeps what it read, a looping cue plays again when a render ended its
  voice, and `Bank` refuses an index that starts below 0. `run200-p768-runner-fixes.log`, 30 s with all sounds: 0
  late refills, a render of at most 880 us, 91 plays, no error.

## P768 (#1058), 2026-11-11: the music in every game (PR 3)

The bank now holds `music`: theme `a` of `tools/sound_bank.py`, a loop of 92160 samples (5.76 s) with a peak of 1600
of 32767. The bank is 295040 bytes. `App.switch` starts the loop once. `probe768_box.py` with `GAME = ""` and
`SWITCH_S = 12` goes through all 14 games, 12 s each, no hand, a press every 900 ms.

| Run | Log | What | Result |
|---|---|---|---|
| 201 | `run201-p768-all-silent.log` | all games, no speaker | the control |
| 202 | `run202-p768-all-music.log` | all games, the music and `Runner`'s sounds | no error, 1 late refill in 170 s (in the first window of `burning`, `between_max` 49 ms) |
| 203 | `run203-p768-rain-silent.log` | `Rain`, 60 s, no speaker | 11 lines: 18 or 19 fps, worst frame 130 to 244 ms |
| 204 | `run204-p768-rain-music.log` | `Rain`, 60 s, the music | 15 to 17 fps, worst frame 158 to 258 ms, 0 late, render mean 587 to 650 us, max 1322 to 1624 us |
| 205 | `run205-p768-rain-nomusic.log` | `Rain`, 60 s, the speaker open and no music voice | 16 to 19 fps, worst frame 110 to 343 ms, render mean 273 to 333 us |

- Run201 against run202, the mean fps of each game's two lines (whole numbers, so 1 fps is one line's rounding): 13 games differ by at most 1 fps
  (`runner` 21.5 and 20.5, `cave` 21.5 and 20.5, `cube` 23.5 and 22.5, the others by 0.5 or less). `rain` went from
  19.0 to 16.5.
- `Rain` fails the fps line: about 18.4 fps silent and 16.2 fps with the music (run203, run204). With the speaker
  open and no music voice it is 17.6 fps (run205). So the open speaker costs about 0.7 fps there and the music
  voice about 1.5. One run each, so the sizes are not exact. Run201 has no speaker, so run201 against run202 holds
  both costs in every game.
- The render line of PR 2 (at most 1000 us) does not hold as a maximum beside a game. In run202 the longest render
  of a window is 700 to 1322 us with one or two voices, and over 1000 us in windows of 7 games. Alone, one voice
  took at most 396 us (run197). The cause is not known. No late refill came from it.
- The switches make no error. The log does not say if the one late refill came at a switch. The music plays on over it by the code
  and its Mac test. No log shows that the ear hears no gap.
- Open: the PO's ear on the tune (theme `a` or `b`), its loudness against the game sounds, and the choice for
  `Rain`: accept the 2 fps, or a later card for a faster sum (the C sum of P767).

### After the PO's decision on `Rain` (2026-11-11)

The probe's presses swapped `Rain` between C and Python: run203 and run204 each print `stepper c` 33 times and
`stepper python` 33 times. So their 18 and 16 fps are a mix of both steppers, and a case that nobody plays. The PO:
"Let's get rid of the slow verson, leave only the fast version." A tap in `Rain` now starts the rain again and swaps
nothing. The Python twin stays for the places with no engine module (the Mac's tests, a stock image).

| Run | Log | What | Result |
|---|---|---|---|
| 206 | `run206-p768-rain-c-silent.log` | `Rain`, 60 s, no speaker | 66 times `stepper c`, 24 fps in all 11 lines, worst frame 52 to 55 ms |
| 207 | `run207-p768-rain-c-music.log` | `Rain`, 60 s, the music | 66 times `stepper c`, 24 or 25 fps, worst frame 51 to 67 ms, 0 late, render mean 510 to 531 us, max 705 to 799 us |

- `Rain` on the C stepper passes the fps line with the music. The worst frame is 12 ms longer in one line (67
  against 55), over the 5 ms line, and within it (at most 60 ms) in 9 of 11 lines.
- The rows of run201 to run205 for `rain` describe the mixed case and no longer the game.
- The probe still presses every 900 ms, so each run starts the rain 66 times.

## P773 (#1065), 2026-11-11: Marshmallow, the game on the fire's field

`Marshmallow` took `Fire`'s place in `app.GAMES`. Each run is 60 s with the sound and the music, and no hand. The
probe is a scratch copy of `probe768_box.py`, not in the repository. It differs in four things: `SECONDS = 60`,
`PRESS_EVERY_MS = 0`, `Fire` as the game where `GAME` is not in `app`, and a hold hook. The hook sets
`box.fire.held` for `HOLD_MS` of each 3000 ms, taps at the start of each 3000 ms, and taps on the game-over screen.
From run210 its last line prints the score and the frames with the button held.

The plan's pass lines: at least 24 fps, the worst frame at most the control's plus 5 ms, and no more late refills
than the control.

| Run | Log | What | fps | Worst frame, ms | Paint mean, ms | Late | Render mean, us |
|---|---|---|---|---|---|---|---|
| 208a | `run208a-p773-fire-control.log` | `Fire`, the control | 24 | 46 to 70 | 9.4 to 10.1 | 0 | 498 to 511 |
| 208b | `run208b-p773-marshmallow-nohand.log` | `Marshmallow`, no hold, `covers` False | 24 | 44 to 80 | 13.7 to 14.0 | 0 | 630 to 690 |
| 208c | `run208c-p773-marshmallow-hold.log` | `Marshmallow`, hold 1300 of 3000 ms, `covers` False | 24 or 25 | 43 to 88 | 13.7 to 14.2 | 0 | 675 to 695 |
| 209a | `run209a-p773-marshmallow-nohand.log` | `Marshmallow`, after the fix, see below | 24 | 45 to 75 | 8.5 to 9.8 | 0 | 631 to 700 |
| 209b | `run209b-p773-marshmallow-hold.log` | `Marshmallow`, hold 1300 of 3000 ms, after the fix | 24 or 25 | 41 to 81 | 8.5 to 9.7 | 0 | 641 to 704 |
| 209c | `run209c-p773-fire-control.log` | `Fire`, the second control | 24 | 49 to 81 | 9.6 to 11.1 | 0 | 500 to 515 |
| 210a | `run210a-p773-marshmallow-nohand.log` | `Marshmallow`, no hold, after the fix | 24 or 25 | 49 to 74 | 8.5 to 9.4 | 0 | 637 to 694 |

The paint mean leaves out each run's first line, which holds the title (up to 17.2 ms in `Marshmallow`).

- Run208 failed the worst-frame line: 80 and 88 ms against the control's 70 ms. `covers` was False, so the display
  filled the background under the field in each frame. The paint took about 14 ms against the control's 10 ms.
- The fix: `covers` is False in the title and True in play, where the field paints every pixel. The paint then took
  8.5 to 9.8 ms, a little under the control's.
- After the fix the worst frame is 74 ms with no hold (run210a) and 81 ms with the hold (run209b). The two controls
  differ by 11 ms (70 and 81 ms). So run210a passes against both controls. Run209b passes against the second
  control and is 6 ms over the line against the first. The 5 ms line is narrower than the spread of the control.
- The fps line and the late-refill line pass in every run.
- Run209a is not a clean run. Its header says no hold, but the HUD's glyph count rose from 13 to 20 and the cues
  started a sound in most windows, as in the hold runs. So the score rose. The cause is not known: a hand on BOOT, or a
  wrong header. Run210a repeats it: score 0, 0 frames held, 13 glyphs in every line.
- The flame loop is a second voice beside the music: the render mean is 630 to 704 us against the control's 498 to
  515 us. The longest render of a window was 1122 us (run209a), and no late refill came from it.

### After the review: new rules (2026-11-11)

The refuter proved on the Mac that the first rules were no game: a fixed rhythm of hold and release scored with no
end, and a player who did nothing never lost. Run209b agrees: the probe's blind hold raised the score. The rules now
have a time for each marshmallow (8 s, less 0.4 s for each point, down to 3.2 s), a black that comes nearer to
golden with each point, and a white marshmallow at once after a lost one. The high heat at 5 points went from 250 to
220, so the flame stays under the marshmallow at the top (Mac, 5,900 steps: at most 198 px of 200).

Mac trials with the C field (scratch scripts, 10 minutes of play at most): nothing done loses in 24 s, a hold with
no end in 12 s. Of 175 fixed rhythms none played on. The best reached 27 points in my trial and 19 in the refuter's
trial of 176. Seeing players that go at most 60 to 120 px under the flame's top reached 12 to 176 points (my trial
and the refuter's, 4 or 5 rounds each), and every round ended within 10 minutes. The wind's seed was not fixed, so
these numbers move from run to run, and no script of them is in the repository. With the plain flame, a few of
the fixed rhythms played on for 10 minutes (4 of 175, and 1 of 176 with 192 points). The rules stop getting harder
at 16 points: the campfire at 5, the time at 12 and the black limit at 16.

| Run | Log | What | fps | Worst frame, ms | Late | Last line |
|---|---|---|---|---|---|---|
| 211a | `run211a-p773-marshmallow-nohand.log` | no hold | 23 or 24 | 59 to 95 | 0 | `score 0 held_frames 0` |
| 211b | `run211b-p773-marshmallow-hold.log` | hold 1300 of 3000 ms | 24 or 25 | 42 to 88 | 0 | `score 2 held_frames 646` |

- Run211a: the round ended after 24 s, as on the Mac, and the game-over screen stayed for the rest of the run,
  because this probe presses nothing with no hold. The window with the death has 23 fps and the worst frame, 95 ms.
- Run211b: the blind hold scored 2 points in 60 s. Its worst frame, 88 ms, is in a window with a death too.
- In both runs every window of play with no death has a worst frame of at most 75 ms, inside the controls' 70 and
  81 ms. The windows on the game-over screen of run211a have 69 to 78 ms.
- The frame of a death holds the HUD's new strip (22 to 26 ms) and the first game-over box (26 to 29 ms). Both are
  `Game`'s code, shared by every game. `Fire` never dies, so the controls hold no such frame, and no run here
  measures a death in another game. On the game-over screen the box takes 19.5 ms in each frame, at 24 fps.
- Open: the PO's hand, eye and ear. No run shows how the game looks or plays, or how loud the flame is
  (`FLAME_GAIN`). The numbers of the rules come from Mac trials with simple players, not from a person.


## P773 (#1065), 2026-11-12: Bucket, the game on the rain's physics

`Bucket` took `Rain`'s place in `app.GAMES`. Each run is 60 s with the sound and the music. The probe is a scratch
copy of the Marshmallow probe, not in the repository. In the `Bucket` run a bot in the probe holds BOOT while the
bucket's middle is left of the lowest falling box, so the whole run is play. The board held b3518d6's `bucket.py`
and `app.py`.

The plan's pass lines: at least 24 fps, the worst frame at most the control's plus 5 ms, and no more late refills
than the control.

| Run | Log | What | fps | Worst frame, ms | Paint mean, ms | Late | Last line |
|---|---|---|---|---|---|---|---|
| 212a | `run212a-p773-rain-control.log` | `Rain`, the control, no hand | 23 or 24 | 55 to 91 | 19.8 to 26.7 | 0 | `score 0 held_frames 40` |
| 212b | `run212b-p773-bucket-bot.log` | `Bucket`, the steering bot | 24 or 25 | 40 to 64 | 8.0 to 12.8 | 0 | `score 54 held_frames 710` |

- Run212b passes every line. Its worst frame (64 ms) is under the control's (91 ms), because `Bucket` draws at most
  8 boxes and the pile, against the rain's 160 boxes.
- The control's fps line is 23 in 4 of its 12 windows, so the control itself is under the 24 fps line.
- The bot scored 54 and did not lose in 60 s. The first window holds the title, so its paint mean is the highest.
- Open: the PO's hand, eye and ear. No run shows how the game looks or plays.
