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

## P582 (#783), 2026-11-02 and 2026-11-03: RENT moves heavy, the allocation and the bot run

- Allocation (`run49-p582-alloc.log`, `probe582.py`, `gc.disable()` around 200 calls alone): `Bodies.step` over a full pool allocates 544 B per call, `Spring.step` 112 B per call. Floats are boxed on the board, so each written float allocates.
- Slice 1 (the drop), the PO playing 3 minutes (`run50-p582-s1.log`): 24 fps and about 22 ms of paint, but every 5-second interval held a game over, so no interval was pure play and the gate could not be read. A Mac simulation showed that a retry works, so the game did not stick: the rounds were short. He gave no words on the feel.
- Slices 2 and 3 started without his slice-1 words, by the joint decision D1 of the PO assistant and the tech lead (2026-11-03, the PO away in auto mode). If his words change the drop, the affected slices are redone.
- After (`run51-p582-bot.log`, slices 1 to 3 on the board after a hard reset): a bench bot played, not the PO (D2). `games/bench582.py` taps in play when the hanging floor, after this frame's slide, is within half a slide of the top floor's drawn x, and in the game over once the retry is allowed. 37 pure-play intervals (at least 6 needed); averages fps 24.03, paint 23.18 ms, send 3.21 ms, worst gap 54.89 ms. Against the P568 before run (24.09 fps): -0.06, inside the -2 line. The bot lost 4 rounds; in those intervals the slowest frame took up to 60 ms, 15 ms of it the physics step, and the interval still ran at 24 fps.
- After the review fixes (`run52-p582-bot.log`, f8604c6 to eb0fb60 on the board, 2026-11-03): the topple collapse in which every floor above the street falls, and the bot cuts a slab on every third tap and waits for the SOLD OUT card. 33 pure-play intervals; averages fps 24.00, paint 22.62 ms, send 3.21 ms, worst gap 54.67 ms. Against the P568 before run (24.09 fps): -0.09, inside the -2 line. 8 intervals hold game-over frames, so the collapse ran; it did not raise the worst gap over run 51.
- The bot's run does NOT test feel or fairness: its taps are regular and near perfect, and it does not judge "heavy" or "natural". The PO's 3-minute play still owes the fps cross-check and his words.
