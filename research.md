# Research: a self-built MicroPython display driver (spike, 2026-11-02)

Summary. A self-build needs ESP-IDF 5.x. The newest MicroPython (v1.29.0) wants v5.5.2, so the local IDF v4.4.8 and MicroPython v1.18 are too old. s3lcd is MIT and unmaintained since March 2024. It already wraps esp_lcd, has a transfer-done callback and has VSCRDEF/VSCSAD scrolling. Its show() path busy-waits, which is a likely cause of the freezes. The USB loss is not a pin clash, because the games use neither GPIO19 nor GPIO20. Look for a crash or reset first. Build the prototype by forking s3lcd's SPI path.

## 1. ESP-IDF for the newest MicroPython
- Newest release: v1.29.0 (published 2026-08-24). Source: https://api.github.com/repos/micropython/micropython/releases/latest
- Its ports/esp32/README.md at tag v1.29.0 says recommended ESP-IDF v5.5.2. It also supports v5.3, v5.4, v5.4.1, v5.4.2, v5.5.1 and v5.5.4.
  https://raw.githubusercontent.com/micropython/micropython/v1.29.0/ports/esp32/README.md
- Master already moved on: it says "requires ESP-IDF version 5", recommended v5.5.5.
  https://raw.githubusercontent.com/micropython/micropython/master/ports/esp32/README.md
- Pick v1.29.0 with IDF v5.5.2 (a matched pair). Do not use the local v4.4.8.

## 2. State of s3lcd
- Source: https://github.com/russhughes/s3lcd (48 commits, 16 forks, 11 open issues).
- Last commit: f254daf5 on 2024-03-20 ("Fix for micropython decf8e6a..."). Nothing since.
  https://api.github.com/repos/russhughes/s3lcd/commits
- Builds with: the prebuilt image is MicroPython v1.20.0 on IDF v4.4.4. README has build steps for 1.14-1.19 and 1.20+.
- USER_C_MODULE: yes in form. The README command is
  `make BOARD=ESP32_GENERIC BOARD_VARIANT=SPIRAM USER_C_MODULES=.../s3lcd/src/micropython.cmake FROZEN_MANIFEST=.../s3lcd/manifest.py`.
  I did not build it. Against MicroPython 1.29 and IDF 5.5 it is untested by its author. Expect small API fixes
  (esp_lcd and SPI headers moved between IDF 4.4 and 5.x). The author's own last fix tracks a MicroPython change.
- License: MIT, Copyright Russ Hughes (LICENSE file; GitHub shows "Other"/NOASSERTION only because of a header).
  https://raw.githubusercontent.com/russhughes/s3lcd/main/LICENSE
- Forks: I did not find a named active fork with IDF 5 fixes in the searches I ran. Not verified. Check the fork list by hand.
- What I read in src/s3lcd.c (main branch):
  - SPI path: `spi_bus_initialize(..., SPI_DMA_CH_AUTO)`, `.on_color_trans_done = lcd_panel_done`, DMA buffer from
    `heap_caps_malloc(size, MALLOC_CAP_DMA)`.
  - `s3lcd_dma_display()` copies a strip into the DMA buffer, sets `lcd_panel_active = true`, calls
    `esp_lcd_panel_draw_bitmap`, then spins in `while (lcd_panel_active) {}` (lines ~2620-2628).
    This is a busy wait with no timeout. If the callback never fires, MicroPython hangs. It also blocks all
    Python while DMA runs, so there is no overlap of drawing and sending.
  - Already has `vscrdef` and `vscsad` methods (lines ~1253-1284), which send 0x33 and 0x37.

## 3. Why the USB port can vanish
- On ESP32-S3, GPIO19 is USB D- and GPIO20 is USB D+. They are shared by the native USB-OTG block (TinyUSB CDC)
  and the USB-Serial-JTAG block.
- MicroPython master (ports/esp32/mpconfigport.h): on S3 the default is native USB CDC through TinyUSB.
  USB-Serial-JTAG is enabled only when native USB is off or the chip has a second USB block.
  https://raw.githubusercontent.com/micropython/micropython/master/ports/esp32/mpconfigport.h
  So the REPL port is TinyUSB, which needs its task and interrupts serviced. I did not check what the v1.22.2 image used.
- The games' pin map (games/gdi.py): SCLK 17, MOSI 15, MISO 16, DC 3, RST 38, CS 18, SD_CS 9, BL 21.
  No pin is 19 or 20. Bus is SPI host 1, 60 MHz. So a pin clash is unlikely. i80 is not used (SPI only).
- Likely causes, in order:
  1. The chip crashes or resets in the driver (`ESP_ERROR_CHECK` aborts on any esp_lcd error), so USB re-enumerates
     and the port disappears. A reboot looks like "port gone, then back".
  2. The busy-wait loop (above) starves the TinyUSB task, so the host drops the device.
  3. PSRAM mode mismatch. A T-Display-S3 thread reports "PSRAM configuration was wrong (octal), crashes disabling
     the USB port" (found via search, not read in full: https://github.com/orgs/micropython/discussions/9329).
     The N16R8 needs the octal image, which the user has.
- How to test: (a) read UART0 (GPIO43 TX / GPIO44 RX) with a USB-UART adapter while the driver starts. A panic
  backtrace or "rst:" line settles case 1. (b) After the port comes back, run `machine.reset_cause()`.
  (c) Replace the spin loop with a timeout and a FreeRTOS semaphore or `vTaskDelay(1)`. (d) Init the driver with
  no drawing; if USB still dies, the bug is in init.

## 4. A C module with two buffers and async push
- Plan: allocate two frame buffers with `heap_caps_malloc(w*h*2, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)`. Do not hand
  PSRAM straight to SPI DMA unless the bus config allows it. On S3 with `SPI_DMA_CH_AUTO`, the driver bounces PSRAM
  data through internal DMA RAM in chunks. Set `max_transfer_sz` to a few strips (for example 20 lines) and
  size `trans_queue_depth` for them. Keep the front/back index in the module. Register `on_color_trans_done`
  to set a flag or give a semaphore (ISR-safe: `xSemaphoreGiveFromISR`). `show()` swaps buffers and calls
  `esp_lcd_panel_draw_bitmap` for the whole screen, then returns at once. The next `show()` first waits on the semaphore with a timeout.
  The draw API does not copy the pixels: the buffer must stay valid until the callback.
- Example 1: lvgl_micropython (org lvgl-micropython, MIT-style, last push 2026-06-23). Its lcd_bus SPI bus sets
  `.on_color_trans_done = &bus_trans_done_cb` and its view1/view2 buffers show two-buffer use.
  https://github.com/lvgl-micropython/lvgl_micropython (file ext_mod/lcd_bus/esp32_src/spi_bus.c)
- Example 2: s3lcd itself (callback + DMA buffer, but synchronous): https://github.com/russhughes/s3lcd/blob/main/src/s3lcd.c
- Espressif's LVGL port (esp_lvgl_port, in esp-bsp) does double buffering with esp_lcd on S3; I did not open it.
- No small standalone "two-buffer esp_lcd MicroPython module" exists that I found. Start from s3lcd's SPI path.

## 5. Tearing sync with the TE pin
- ST7789 command 0x35 (TEON, param 0 = V-blank only) turns the TE output on; 0x44 sets the TE line position.
  Espressif says TE anti-tearing applies to SPI, I80 and QSPI panels with internal GRAM, and names 35h and 44h.
  https://docs.espressif.com/projects/esp-iot-solution/en/latest/display/lcd/lcd_screen_tearing.html
- Espressif's sample is `examples/display/lcd/lcd_with_te` in esp-iot-solution. The README shows an i80 panel
  (AXS15231B), not an ST7789, and I could not see the TE code. So there is no ST7789 + esp_lcd example I verified.
- Pattern (from the Linux fbtft TE patch and Espressif's text): configure TE GPIO (IO14) as input with a rising-edge
  interrupt (`gpio_install_isr_service`, `gpio_isr_handler_add`). The ISR gives a semaphore. `show()` waits for
  that semaphore, then calls `draw_bitmap`. Keep the SPI send faster than the panel refresh scan. At 60 MHz a
  320x240x2 frame takes about 20 ms, near the 60 Hz scan, so expect to need a faster clock or a partial region.
  Send the 0x35 command through `esp_lcd_panel_io_tx_param(io, 0x35, &zero, 1)`.

## 6. ST7789 vertical scroll
- VSCRDEF is 0x33 with 6 bytes: TFA, VSA, BFA (16 bits each). VSCSAD is 0x37 with 2 bytes: the start line.
  Opcodes confirmed in ST7789 driver headers (https://docs.rs/crate/st7789v2/latest/source/src/commands.rs
  cites ST7789V2 datasheet V1.0 2016/11, pages 210 and 220).
- Rule from the datasheet, not verified here: TFA + VSA + BFA = 320. Scroll always runs along the controller's
  320-line axis (its native portrait height), not along the screen axis you see in landscape.
- With the panel rotated by MADCTL (0x36) bit MV (0x20) for landscape, that 320 axis becomes the screen's long
  X axis. So a "vertical" scroll moves content sideways in landscape. For vertical scrolling in landscape, you cannot
  use hardware scroll. Choose the game's scroll axis to be the long 320 side, or keep the panel portrait and rotate in software.
  Test MADCTL combos on the bench; the MX/MY bits flip the scroll direction.
- s3lcd already exposes vscrdef and vscsad, so no new code is needed for the first test.

## 7. Alternatives
- lvgl_micropython (kdschlosser, now https://github.com/lvgl-micropython/lvgl_micropython): active, ESP32-S3
  and ST7789 supported, esp_lcd based, double full-frame buffers in SPIRAM, builds MicroPython itself with `make.py`.
  Fit: best maintained base, but it brings all of LVGL and a different drawing API. The games would need a port. Heavy.
- russhughes/s3lcd: what you run now. Same esp_lcd base, simplest to patch, but unmaintained.
- devbis/st7789_mpy (local copy): plain SPI, no esp_lcd, no async. I grepped it: no scroll or TE code. Not a fit.
- Pure MicroPython with machine.SPI: 1-13 fps measured. Not a fit.

## Recommended first prototype (smallest proof of double buffering)
1. Install ESP-IDF v5.5.2 and take MicroPython v1.29.0 (new folders; leave v4.4.8 alone). Build the stock
   GENERIC_S3 octal board once and flash it, to prove the toolchain and that USB survives.
2. Copy s3lcd into a new folder as the USER_C_MODULE. Build it against 1.29/IDF 5.5. Fix compile errors only.
3. On the bench, flash it and read UART0 while the driver starts. Record whether USB dies and any panic text (question 3).
4. Add a timeout and a semaphore instead of the spin loop in `s3lcd_dma_display`. Re-test the games. This alone may cure the freezes.
5. Add `show_async()`: two PSRAM buffers, front/back swap, `on_color_trans_done` gives a semaphore, return immediately.
   Add `wait()` that takes the semaphore with a timeout.
6. Prove it with a test script: draw frame N+1 in Python while frame N is sending. Print ticks per frame with and
   without `show_async()`. Success is a higher fps and no blinking.
7. Then add TE: send 0x35, GPIO14 interrupt gives a semaphore, `show_async()` waits for it. Compare tearing on a moving bar.
8. Last, test vscrdef/vscsad with the game's MADCTL setting for a scroll along the long axis.
