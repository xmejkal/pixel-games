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
| 5a | run145b | `CallbackRefill`, 2048 B | silent `Mixer` | 24.00 fps, worst 77 ms, 8 late: the control |
| 5b | run145b | `CallbackRefill`, 2048 B | `NativeCrackle` | 24.00 fps, worst 77 ms, 0 late, render at most 413 us, pop wait median 11 ms, max 27 ms, 405 pops, 0 dropped |
| 5c | run145b | `FrameRefill`, 4096 B | `Crackle` (Python) | hung: no frame after `align 0`, stopped by hand |
| roar A, B | run145c, d | `CallbackRefill`, 2048 B | `NativeCrackle`, 20 s each | A no roar, B roar at about 40 Hz, a quarter of the level. The PO chose B |
| 5c | run145e | `FrameRefill`, 4096 B | `SampledCrackle` | 24.15 fps, worst 70 ms, 0 late, render at most 2.3 ms, 425 pops, 3 dropped |

- 5b passes every line that the plan set before the runs: fps and worst frame equal to the control, no more late
  refills than the control, a render under 1 ms, no dropped pop, and a pop wait (from `add_pops` to the render that
  starts it) of median 11 ms and max 27 ms against 20 and 48 ms. The ring then holds a pop up to 64 ms more.
- The PO's ear: the pops come with the sparks "kinda, its not synchronized with their size", because "some are
  brighter and bigger". Every ember is born the same in the kernel today, and each pop's loudness is random. The old
  roar (`roar_shift` 4, `roar_gain` 48) sounded like "background noise like wind or river". It was most of the sound:
  alone it measured RMS 1637, the whole crackle 1620.
- The Python `Crackle` takes 20.9 to 22.7 ms for 256 samples (16 ms of sound) on the board, 54 times the C. The first
  5c hung because `FrameRefill` rendered until the ring was full, and a renderer slower than real time never fills
  it. A `FrameRefill` write now renders at most one ring. The PO chose pre-rendered pops as the naive path, and on
  `SampledCrackle`: "sounds weird, but never mind lets leave the simple one like that, advanced versions will be cool".
- 5a, the control, counted 8 late refills, and 5b none. Both sit near the line: `lag_max` reached 32 ms in 5a and
  29 ms in 5b, against a late refill at 48 ms minus one block. The game switches every 30 s cause the worst frames.
- Later, not MVP: a pop whose loudness follows its spark's size (the kernel gives each ember a size), the flames in C,
  and the S3's vector instructions where a measurement shows the need (D27).

