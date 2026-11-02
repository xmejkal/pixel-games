# P537: smooth motion and a C graphics layer (spike finding, 2026-11-02)

Spark issue [#741](https://github.com/xmejkal/spark/issues/741), epic P536 #740, after P533 #737 (the driver) and before P535 #739 (what moves to C).

## TL;DR

> The steps have two causes, and neither is the moving objects. First, the frames come at uneven intervals of 40 to 80 ms, because no game meets the 40 ms pace. Second, the objects jump 4 to 25 px a frame at 25 fps (the falling bird and the pong ball most). The phase numbers we have are per-interval maxima, not averages, so they say where the slow frames go, not the average split. In those maxima two parts are large. The score bar text, runner hud up to 27 ms, is drawn as fill_rect runs from Python. The game-over box takes 33 to 54 ms. The moving objects are small (5 to 13 ms). The card asked for a bench number per question and for the frame rate where the PO stops seeing steps. Both are deferred to slice 0. It first measures the average per phase, then the PO's threshold. The projection from the maxima: a kept background in C plus the score text blitted in C brings runner's paint from 34 ms to about 8 at most. Then every game in play meets 33 ms (30 fps), with steps of 3 to 14 px (21 for the ball). Sprites in C, and then a PSRAM back buffer painted while the DMA sends, reach 40 fps. A third buffer gains nothing, because the panel has no vsync. The S3 has no graphics accelerator. Its PIE vector unit speeds fills and copies 6 to 10 times, and that is a late slice. The layer is ours: small, MIT, panel-independent, on top of frame.c. It takes ideas from Stage, displayio TileGrid, PicoSystem blend modes and TFT_eSPI soft edges. No library is adopted whole.

## Where it stands (bench.md runs 18 to 22, probe6)

- Pace `FRAME_MS = 40`. Flappy 21 to 24 fps, runner 20 to 21, stack 24. So no game meets the pace: a frame takes 42 to 48 ms on average and up to 70 to 80 ms (worst gap). The loop then restarts the pace from now (`app.py`, `due = time.ticks_ms()`), so the interval varies frame by frame. This is judder: perceived uneven movement caused by irregular picture durations (source: [Emby, Display judder](https://emby.media/learn/articles/display-av/motion/Display-Judder.html)).
- Sends in play: flappy 11.3 ms, runner 7.7 ms, game over about 20 ms, a whole frame 31 ms.
- Paint by phase, from the phases line of runs 18 and 19. These are per-interval MAXIMA. `gfx.PHASES` keeps the slowest of each draw phase (`gfx.py:264`), and `app.py:106` prints it. The runs used a 60 ms pace, BEFORE partial show. Runner: static 22 to 31 ms (up to 54 at game over), hud 18 to 27, paint 5 to 8, fx 3 to 11, over 66. Flappy: static 2 to 4, hud 9 to 20, paint 6 to 13, fx 0 to 4, over 22 to 49. The maxima add up to more than the average paint (runner 31.5 to 33 ms), so they cannot be read as a split. No average per phase exists yet: slice 0 measures it first. Since 49ea8e7 `paint_static` runs in `TftOut.draw`, outside `Game.draw` (`lcd.py:113`). So the static phase now reads about 0, and its cost sits in the paint total. `TftOut.draw` repaints `fill(bg)` and `paint_static` every frame with tracking off. `Game.hud` draws its text every frame as `fill_rect` runs per glyph row (`gfx.py:336-351`). On the TFT canvas `cv.immediate` disables its reuse.
- The game step costs 0.6 to 1.2 ms. `Game.step` uses the real `dt`, clamped at 60 ms (`gfx.py:319`), so a 75 ms frame moves 60 ms worth: a second source of unevenness.

## Question 1: the steps, and what removes them

### Px per frame now, from the speeds in the games

The speeds in px/s come from the code. Flappy: pipes and ground 95 to 155 (`arcade.py:37`), clouds 28 to 46. The bird falls at up to about 564 (free fall over the 194 px from the top to the floor at 820 px/s², flap -270). Runner: obstacles 150 to 310 (`arcade.py:114`), the jump starts at 420 up. Stack: the bar 120 to 330 (`arcade2.py:20,57`). Cave: scroll 120 to 180, climb up to 230. Pong: the paddle 170 to 250, the ball 410 to 635 after a hit (`arcade2.py:178`).

| object, px/s | 110 ms (old) | 50 ms (20 fps) | 40 ms (pace) | 33 ms (30 fps) | 25 ms (40 fps) | 16.7 ms (60 fps) |
| --- | --- | --- | --- | --- | --- | --- |
| flappy pipes 95 to 155 | 10 to 17 | 5 to 8 | 4 to 6 | 3 to 5 | 2 to 4 | 2 to 3 |
| flappy bird falling, up to 564 | 62 | 28 | 23 | 19 | 14 | 9 |
| runner obstacles 150 to 310 | 17 to 34 | 8 to 16 | 6 to 12 | 5 to 10 | 4 to 8 | 3 to 5 |
| runner jump start 420 | 46 | 21 | 17 | 14 | 11 | 7 |
| stack bar 120 to 330 | 13 to 36 | 6 to 17 | 5 to 13 | 4 to 11 | 3 to 8 | 2 to 6 |
| pong ball 410 to 635 | 45 to 70 | 21 to 32 | 16 to 25 | 14 to 21 | 10 to 16 | 7 to 11 |
| clouds 28 to 46 | 3 to 5 | 1 to 2 | 1 to 2 | 1 | 1 | under 1 |

The card's 13 to 20 px for the stack bar was at 110 ms. At the 40 ms pace it is 5 to 13 px, but the interval is not 40 ms, it is 40 to 80.

### What frame rate removes visible steps

The sources give no single number. On a sample-and-hold panel the eye tracks the object, and the step it sees is speed times frame time (the px per frame column above). Blur Busters' forum puts the slideshow threshold near 10 fps. It says stutter is still felt well above that, and more so the faster the object moves in px per frame. Source: the [Blur Busters forum thread on repeated images at low frame rates](https://forums.blurbusters.com/viewtopic.php?p=76800), found by search. It was not read in full, because the site refused the fetch. Judder from uneven intervals is a separate defect, and even playback removes it. Source: [Emby](https://emby.media/learn/articles/display-av/motion/Display-Judder.html). My reading, to be measured: even intervals first. Then steps under about 5 px for the objects the eye follows (pipes, the bar, obstacles). That is 30 fps for the pipes and the bar, and 40 to 60 fps for the fastest obstacles and the jump. The panel scans at about 60 Hz (plan E6). So 60 fps is the ceiling and 30 fps the even divisor. With no TE line, neither locks to the scan.

The bench measurement that settles it is a Python-only probe. It moves a 16 x 16 block at 100, 200 and 300 px/s. The pace is fixed at 16, 20, 25, 33, 40 or 50 ms, in random order, and every interval is met. The PO says "steps" or "smooth" for each. The result is the px per frame his eyes accept, one number in bench.md. Slice 0.

### The options, ranked by gain per line of code

| rank | option | gain | lines | verdict |
| --- | --- | --- | --- | --- |
| 1 | Even pace. Set `FRAME_MS` to what the slowest frame meets (50 for runner), or a pace per game, and log worst gap = pace | removes judder now, costs 5 fps | 1 to 5 | do first, blind A/B 40 vs 50 with the PO |
| 2 | Kept background in C. After `paint_static`, `tft.keep()` copies the frame to a PSRAM copy. `show()` restores the tiles marked "before" (the holes) from it, so nothing repaints the still picture. The score text is blitted from a glyph cache in C. Runner's score changes 7.5 to 15.5 times a second (`score = int(odo / 20)`, `arcade.py:116`), every 2 to 4 frames at 30 fps. So a Python redraw on change saves little | runner paint 34 to about 8 ms at most. That is an upper bound from the maxima, and the average split is unmeasured. Flappy 20 to about 10. Every game in play meets 33 ms | about 60 C for the background, about 80 C for the glyph blit, 15 Python | the big one, slice 2 |
| 3 | Sprites and text in C. A sprite built once as an RGB565 bitmap with a key colour, blitted in one call with the orientation map inside C. Glyphs the same way | paint of the objects 5 to 11 ms to 1 to 3, hud to under 1 ms | about 150 C, 20 Python | slice 3, the start of the layer and of P535 |
| 4 | Paint overlapping the send. `show(wait=False)` queues and returns, `wait()` or the first draw blocks | 1 to 3 ms (the step and the Python overhead overlap) | about 15 C | slice 4a, cheap |
| 5 | PSRAM back buffer, the PO's second buffer. Paint in PSRAM, copy the dirty tiles into the internal frame, send. Paint overlaps the whole send. probe6's 7 to 30 are windows, not tiles. A 7.7 to 11.3 ms send at 40 MHz carries about 75 to 110 tiles of 512 B. So the copy is 40 to 55 KB a frame | 8 to 11 ms in play, 20 at game over. Risk, measured: run 14 (PSRAM framebuffer) against run 15 (internal), bench.md slices 2 and 3. Flappy paint 25.5 against 18.2 ms (+40 %). Static 6 to 8 against 2 to 4. The game-over box 2 to 3 times slower. A whole frame is past the 32 KB cache ([Espressif, external RAM restrictions](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/external-ram.html#restrictions)) | about 80 C | slice 4b. If the PSRAM paint plus the tile copy stays under the send, it pays. Measure first |
| 6 | Soft edges and sub-pixel positions. Blit at 8.8 fixed point, the edge pixel blended by its coverage | smooth for objects under 2 px a frame (clouds, the apex of a jump, a ball at its top). Does nothing for a 10 px step | about 40 C inside the blit | slice 6, after the blit exists |
| 7 | Alpha and blend modes for effects (dim at game over, additive particles) | looks, not smoothness. `fill_rect` already takes alpha in s3lcd | about 60 C | slice 7 |
| 8 | PIE vector fills and copies (the S3's SIMD) | fill 5.8 x and copy 6.9 to 9.8 x on 128 x 128 RGB565, against LVGL's ANSI C loops, not against memcpy. Unaligned small fills gain only 2.3 x. Source: [esp_lvgl_port simd test](https://github.com/espressif/esp-bsp/blob/master/components/esp_lvgl_port/test_apps/simd/README.md). Our fills are already C and small. A frame gains about 1 to 2 ms | 3 .S files ported (fill, copy and lv_macro_memcpy.S) | slice 8. If the tile copy of slice 4b shows in the profile, try it |
| 9 | Fixed timestep with interpolation ([Gaffer on Games, Fix your timestep](https://gafferongames.com/post/fix_your_timestep/)) | none here: the step costs 1 ms and already uses the real dt. Its gain is even motion under varying frame times. Ranks 1 and 2 give that | 30 | idea only. When the pace holds, drop the 60 ms clamp |
| 10 | Viper or native emitters for paint | small: the paint is already a chain of C calls, the per-call overhead stays | 10 | skip, rank 3 removes the calls instead |
| 11 | A third buffer | none: with no vsync the sender is DMA that ends in 8 to 11 ms, a third buffer adds one frame of lag and smooths nothing | | skip, say why to the PO |
| 12 | Panel refresh (FRCTRL2) or hardware scroll | refresh does not change our step. Scroll runs along game x only and fights partial show (E7) | | skip |

Parallax in the panel is impossible (one layer, E7). Parallax in software is slice 5: the kept background becomes two or three tile layers with an x offset each, composed in C only for the dirty tiles.

## Question 2: the C graphics layer

### Similar projects and what we take from each

Three surveys ran on 2026-11-02 (GitHub API for dates and licenses, file heads, not full source reads, "not verified" where so). All MIT or BSD unless flagged. Our repo is MIT, so GPL code is out.

| project | good for us | license | last commit | S3 and MicroPython fit | verdict |
| --- | --- | --- | --- | --- | --- |
| [russhughes s3lcd](https://github.com/russhughes/s3lcd), [st7789_mpy](https://github.com/russhughes/st7789_mpy) | our base: C fill, line, polygon with alpha, blit_buffer with alpha, bitmap and Hershey fonts, jpg, png. Lacks key-colour sprites, tiles, dirty rects (ours now), sub-pixel | MIT | s3lcd Mar 2024, st7789_mpy Oct 2026 | runs here | reuse as is. If a fix is missing, pull it from st7789_mpy |
| [CircuitPython displayio, vectorio, bitmaptools](https://docs.circuitpython.org/en/latest/shared-bindings/displayio/index.html), [source](https://github.com/adafruit/circuitpython/tree/main/shared-module/displayio) | Group with integer x, y, scale. TileGrid: tile maps and sprite sheets, flip, transparent palette index. Per-object dirty areas merged into one region. bitmaptools: blit, rotozoom, alphablend, dither. No sub-pixel, no blending beyond transparency | MIT | Nov 2026 | portable C, tied to the CircuitPython core, a port is heavy | port a piece: TileGrid.c as reading, reimplement the glue |
| [Deshipu Stage / uGame](https://github.com/python-ugame/circuitpython-stage), C in [_stage](https://github.com/adafruit/circuitpython/tree/main/shared-module/_stage) | a 16 x 16 tile Grid plus Sprite and Text layers. C composes them per scanline strip with no framebuffer. Colour 0 is transparent. It renders only the changed rectangle. Small: Layer.c, Text.c, __init__.c | MIT | 2026-02 (Python), 2024-05 (C) | portable, tiny | port a piece: the layer composition loop, the closest match to arcade sprites and tiles |
| [LVGL](https://github.com/lvgl/lvgl), [lvgl_micropython](https://github.com/lvgl-micropython/lvgl_micropython) | v9 software renderer: layers, blending, image transforms, glyph cache text, dirty invalidation, partial flush, double buffering | MIT | Nov 2026, binding Jun 2026 | a custom MicroPython build with its own driver stack, replaces s3lcd | skip as a base: a GUI toolkit with widgets and an event loop |
| [Pimoroni PicoGraphics, PicoVector](https://github.com/pimoroni/pimoroni-pico) | pens RGB565, RGB332, P8, P4. Sprite sheets with scale, alpha, dithering, pretty-poly AA polygons, bitmap and Hershey text, partial update, MicroPython bindings | MIT | Oct 2026 | C++ core separable, display glue is Pico SDK | port a piece: pretty-poly (check its own header), copy the bindings pattern |
| [PicoSystem SDK](https://github.com/pimoroni/picosystem) | the game API shape: sprites, blend modes COPY ALPHA MASK PEN DARKEN LIGHTEN ADD SUBTRACT MULTIPLY as per-pixel functions, target buffers, camera, text | MIT | Aug 2026 | C++, RP2040 glue | take the idea: the blend table and the API shape |
| [32blit SDK](https://github.com/32blit/32blit-sdk) | Surface, SpriteSheet, TileMap with per-tile transforms, blend modes, Pen with alpha, ARM asm blits | MIT | Jul 2026 | C++, ARM asm will not carry | port a piece: the tile map with transforms, as a C rewrite |
| [TFT_eSPI](https://github.com/Bodmer/TFT_eSPI) | TFT_eSprite (1, 4, 8, 16 bit, pushSprite with a transparent colour, DMA pushImage), anti-aliased shapes with alpha at edges (drawWideLine, drawSmoothCircle, fillSmoothRoundRect, alphaBlend) | MIT base plus BSD notices, mixed | Apr 2026 | Arduino bound | port a piece: the soft-edge math |
| [LovyanGFX](https://github.com/lovyan03/LovyanGFX) | LGFX_Sprite, pushRotateZoom, pushImageAffine, DMA, S3 support, pixelcopy (format copy with a key) | BSD style, mixed, re-check each file | Oct 2026 | runs on S3, heavy C++ templates | port a piece: pixelcopy and the affine sampler, later |
| [Adafruit GFX](https://github.com/adafruit/Adafruit-GFX-Library) | GFXcanvas16, GFXfont glyph tables. No sprites, no dirty rects | BSD | Oct 2026 | neutral C++ | idea only, fonts as data after a per-file license check |
| [Arduboy2](https://github.com/MLXXXp/Arduboy2) | sprite plus mask pairs, nextFrame() pacing, everyXFrames | BSD 3 | Aug 2023 | AVR, 1 bit | idea only: the pacing helper |
| [Thumby](https://github.com/TinyCircuits/TinyCircuits-Thumby-Code-Editor) | Python-level 1-bit sprites | GPL-3.0 | Mar 2025 | RP2040 | skip: GPL and 1 bit |
| [esp_lvgl_port](https://github.com/espressif/esp-bsp/tree/master/components/esp_lvgl_port) | double buffering and partial flush on esp_lcd, flush_ready from `on_color_trans_done` (as frame.c does). PIE assembly for RGB565 fill and copy in src/lvgl9/simd | Apache-2.0 (esp-bsp), notice kept, not verified per file | active | S3 | port a piece: the two .S files, slice 8 |

None of them has dirty-tile tracking as frame.c has it. None fits whole: displayio and LVGL bring a runtime, the Arduino ones bring C++ and a bus layer, Stage brings no framebuffer. So the layer is ours, and it is small.

### The mix: each feature, where it comes from, why

| feature of our layer | from | why |
| --- | --- | --- |
| kept background, holes restored per dirty tile | ours (frame.c marks) plus Stage's idea of composing only the changed rectangle | the marks exist, a restore per tile is 20 lines |
| sprite: RGB565 bitmap plus key colour, flip, integer scale | Stage Layer.c, displayio TileGrid transparent index, TFT_eSPI pushSprite | one call per sprite instead of 20 fills, the key colour fits our pre-swapped colours |
| tile map layers with an x offset each (software parallax) | displayio TileGrid, 32blit TileMap, Stage Grid | the only way to parallax on a one-layer panel |
| text from a glyph cache | ours (`gfx.GLYPHS` runs) moved to C bitmaps, Adafruit GFXfont as the data format | the hud is 19 to 25 ms today |
| blend modes: COPY, ALPHA, ADD, DARKEN, MULTIPLY | PicoSystem's per-pixel table, s3lcd's alpha | effects without a second framebuffer |
| soft edges, 8.8 fixed-point positions | TFT_eSPI alphaBlend edge math, LovyanGFX pixelcopy | sub-pixel motion for slow objects |
| rotate and zoom (later) | LovyanGFX pushRotateZoom, bitmaptools rotozoom | the 3D games and effects, not needed for the arcade set |
| dirty tiles and windows | ours | unique among the surveyed set |
| double buffer, flush from the done callback | esp_lvgl_port, frame.c | proven pattern on esp_lcd |
| PIE fill and copy | esp_lvgl_port simd .S | measured 6 to 10 x on the S3 |
| orientation map in C | ours (`TftCanvas.fill`) | every draw takes game coordinates, text stops being rotated |

### Chip-specific acceleration on the ESP32-S3

- PIE, the Processor Instruction Extensions. Eight 128-bit registers q0 to q7, used as 16 x 8-bit or 8 x 16-bit lanes. Saturating add and multiply, fused load and store, 16-byte aligned loads. Sources: [TRM chapter 1](https://documentation.espressif.com/esp32-s3_technical_reference_manual_en.html#page=39) and the [cheat sheet in esp-dl](https://github.com/espressif/esp-dl/blob/master/tools/agents/skills/esp32s3-pie-simd/SKILL.md). GCC does not emit them. Every Espressif use found is hand-written assembly (not verified beyond those examples). esp-dsp uses them ([benchmarks](https://docs.espressif.com/projects/esp-dsp/en/latest/esp32/esp-dsp-benchmarks.html)). For graphics the measured use is esp_lvgl_port's LVGL v9 blend. RGB565 fill: 0.196 cycles a pixel aligned, against 1.146 in C. Copy: 0.352 against 3.437. Source: [README](https://github.com/espressif/esp-bsp/blob/master/components/esp_lvgl_port/test_apps/simd/README.md). LVGL upstream has no esp32 path, only arm2d, helium, neon, riscv_v and sve2. Source: [lvgl/src/draw/sw/blend](https://github.com/lvgl/lvgl/tree/master/src/draw/sw/blend). Colour-key blit and RGB565 alpha blend have no published number. The instructions fit (compare to a mask, and, or, 16-bit multiply with a shift), but the gain is unmeasured. For us it helps the tile copy of slice 4b and large fills. Slice 8 tries it, with the fill_rect and tile copy microseconds before and after.
- GDMA memory to memory, `esp_async_memcpy`. The copy runs beside the CPU, and the callback runs in an ISR. The CPU does the unaligned edges. A cached destination needs at least two cache lines. Source: [async_memcpy](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/async_memcpy.html). Espressif says DMA to PSRAM is very limited, and worse while the CPU reads PSRAM. Source: [external RAM restrictions](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/external-ram.html#restrictions). Short copies are faster on the CPU. If the CPU tile copy of slice 4b shows in the profile, this is the candidate. No S3 MB/s is published. The IDF test app prints it ([test_async_memcpy.c](https://github.com/espressif/esp-idf/blob/master/components/esp_driver_dma/test_apps/dma/main/test_async_memcpy.c)).
- 2D-DMA and PPA (scale, rotate, mirror, blend, colour key, fill). Read from the docs, not tested: they exist on the ESP32-P4 only. Sources: the [P4 datasheet](https://documentation.espressif.com/esp32-p4_datasheet_en.html#page=64) lists them, and the [GMF note](https://docs.espressif.com/projects/esp-gmf/en/latest/gmf-framework/gmf-video.html#hardware-accelerated-ppa) says PPA is supported on ESP32-P4 and ESP32-S31 only. The S3 has none. On the S3 the only helpers are GDMA copies and PIE.
- PSRAM. A frame of 150 KB is past the 32 KB cache. So a whole-frame PSRAM paint runs at raw PSRAM speed. It also evicts cached flash code. Source: [restrictions](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/external-ram.html#restrictions). The front buffer stays internal for a measured reason. In slice 3 the bench cut a full send from 71.3 ms to 31.0 ms by moving the framebuffer into internal DMA RAM. The paint got faster too (run 14 against run 15, above). The PSRAM bandwidth limit in the [spi_master doc](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/spi_master.html#transactions-with-data-on-psram) is not the reason, because our 40 MHz is far below it. If there is a back buffer, it is the PSRAM copy of slice 4b.

### What the layer holds, and where it sits

Panel-independent, in a new `scene.c` beside `frame.c`, with `frame_t` as its only dependency: the pixels pointer, width, height, `frame_dirty`, the marks. It knows no esp_lcd call and no ST7789 command. `s3lcd.c` keeps the bus, init, jpg and png. The orientation map (`TftCanvas.fill`) moves into the layer as four flips. Then every call takes game coordinates, and the two Python classes shrink to pass-through. Phase 1 (slices 2 to 4): kept background, sprite blit with key, glyph text, async show, the back buffer. Phase 2 (slices 5 to 8): tile layers with offsets, soft edges, blend modes, PIE. Everything is a setting or a call, nothing runs unless the game asks, as the driver's `config()` does.

### Python API sketch

```python
tft.orient(0)                                   # 0 or 180: the map, in C now
bg = tft.keep()                                 # the frame now is the still picture: show() restores the holes from it
tft.keep(0, 0, 320, 16)                         # re-keep one band, after the score bar changed
bird = tft.sprite(BIRD, BIRD_COLOURS, scale=2)  # RGB565 bitmap plus key colour, built once
tft.blit(bird, x, y, flip=0)                    # one call, clipped, marks its tiles. x and y may be floats in slice 6
font = tft.glyphs(framebuf_8x8)                 # the glyph cache, one bitmap per character
tft.text(font, "best 12", x, y, YELLOW, scale=2)
far = tft.layer(tiles, columns, rows)           # a tile map, slice 5
far.offset = 0.3 * dist                         # its own scroll: parallax in software
tft.compose((far, near))                        # the kept background becomes the composed layers, per dirty tile
tft.blend(tft.ADD)                              # the mode for the next blits and fills, slice 7
tft.show(wait=False)                            # queue the windows and return
tft.wait()                                      # or the first draw waits
```

What stays in Python: the games, their speeds, their rules. The layer draws, it decides nothing (spark's rule: facts, not behaviour, applies to the games' logic too).

## Question 3: the plan in testable slices

Each slice is one PR in firebeetle-games. The bench measures it before and after, with the same games. It ends with the PO's words in bench.md. Smallest first.

0. **Measure first, then the step probe (Python only).** Step one: the average per draw phase, a sum beside the maximum in `gfx.PHASES`. It is logged per interval for every game, at the 40 ms pace, with partial show on. This is the bench number the card asked for in question 1. Every projection in this file waits for it. Step two: a block moves at 100, 200 and 300 px/s under paces of 16 to 50 ms, in random order. Every interval is met. Measures: the average split of the paint, and the px per frame at which the PO stops seeing steps. Done: the average split and that threshold, with the pace it needs, are in bench.md. The rest of the plan uses them as the target.
1. **Even pace.** `FRAME_MS` 50 against 40, blind, two minutes each, the slowest frame under the pace. Measures: worst gap equals the pace in every interval, fps, the PO's verdict. Done: his pick is the pace until slice 2, and bench.md says whether even 20 fps beat uneven 24.
2. **Kept background and score text in C.** First step: `glyphs()` and `text()`, a glyph cache blitted in C, and `Game.hud` and `Canvas.big` call it. This comes first because runner's score changes every 2 to 4 frames. A redraw on change alone still leaves hud frames of up to 27 ms. Second step: `keep()`, and the restore of the "before" tiles inside `show()`. `TftOut.draw` paints the still picture once per game switch. When the score changes, `Game.hud` draws into the kept band. Measures: the average paint per game and phase, fps at 40 and 33 ms, stale pixels through title, play, game over and three switches. Done: runner and flappy paint under 12 ms in play. Every game in play meets 33 ms with the worst gap equal to the pace. Game-over frames are outside this criterion until slice 3 (the box is 33 to 54 ms of text plus about 20 ms of send). No stale pixel, and the PO's eyes.
3. **Sprites in C.** `sprite()`, `blit()` with the key and the flips, and the orientation map in C. `TftCanvas.sprite` calls it, and the game-over box uses slice 2's text. Measures: the paint and over phases, bytes allocated per frame. Done: the objects paint under 4 ms, the hud under 1 ms, the game-over box under 10 ms, so game over also meets 33 ms. The Mac tests pass with a fake driver.
4. **Overlap.** 4a: `show(wait=False)` and `wait()`, so the step runs during the send. 4b: a PSRAM back buffer and the dirty-tile copy into the internal frame. A probe measures first: a runner frame painted in PSRAM against internal, and the tile copy. Measures: frame time, fps at 25 ms. Done: 4a gains its 1 to 3 ms with no tear report. If a frame gains more than the PSRAM paint costs, 4b stays. Its target is 40 fps in play, judged by the PO's eyes.
5. **Tile layers and software parallax.** `layer()`, `compose()`, flappy's clouds and hills on two layers with their own offsets. Measures: compose time per dirty tile, fps. Done: flappy keeps its slice 4 fps with two layers, and the PO sees the depth.
6. **Soft edges.** `blit()` takes 8.8 fixed-point x and y and blends the edge pixels. Measures: blit microseconds, the PO's eyes on the clouds and on the apex of the runner's jump against slice 3. Done: no fps lost, his verdict logged, kept or switched off by a setting.
7. **Blend modes.** `blend()` with COPY, ALPHA, ADD, DARKEN, MULTIPLY in the fill and blit paths. Measures: the cost per mode per 1000 pixels. Done: the game-over dim and additive particles at no fps lost.
8. **PIE fill and copy.** Port esp_lvgl_port's three .S files (fill, copy and lv_macro_memcpy.S, Apache-2.0 notice kept), behind a build flag. Measures: fill_rect and tile copy microseconds before and after, frame time. Done: if a frame gains 2 ms or more, the files stay. Otherwise the files go, and the number stays in bench.md.

Slices 0 to 2 answer the PO's question. Slices 3 and 4 are the first half of P535 (what moves to C). Slices 5 to 8 are the layer's second phase, each one optional and switchable.

## What does not change

- The panel: one layer, no TE, so a tear line stays possible. Partial windows of 8 to 11 ms make it rare, and no slice here claims to remove it.
- The driver's contract: frame.c keeps its settings, the layer sits above it and never calls esp_lcd.
- The games' speeds. The step probe can show that the PO prefers slower objects at the same fps. That is a game tuning, not a driver change.

## Sources not reached

The Blur Busters site returned 403 to the fetch. So its law (step width equals speed times frame time) is cited from the search summary of its forum, not read. The surveys read license files, dates and file listings, not the code. Code claims beyond those are "not verified". Before a slice ports a piece, it checks that piece's code and license header.
