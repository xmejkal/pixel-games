# P533 slice 0: three probes, no C. Internal DMA memory, the panel's own (rotation 0) corners, and a scroll trial.
# Run: mpremote run probe0.py (memory and corners), or mpremote exec "SCROLL=1" run probe0.py (all three).
import time, esp32, s3lcd, gdi
from machine import Pin

DMA_INTERNAL = (1 << 3) | (1 << 11)  # MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL, esp_heap_caps.h
FRAME = 320 * 240 * 2  # the bytes of one framebuffer, and of one internal "dma" framebuffer


def memory(when):
    heaps = esp32.idf_heap_info(DMA_INTERNAL)
    free = sum(h[1] for h in heaps)
    largest = max(h[2] for h in heaps)
    print("%-12s internal DMA: free %d, largest block %d, per heap (total, free, largest) %s, a frame fits: %s"
          % (when, free, largest, [h[:3] for h in heaps], largest >= FRAME))


memory("boot")
Pin(gdi.SD_CS, Pin.OUT, value=1)
Pin(gdi.BL, Pin.OUT, value=1)
bus = s3lcd.SPI_BUS(1, mosi=gdi.MOSI, sck=gdi.SCLK, dc=gdi.DC, cs=gdi.CS, pclk=60_000_000, swap_color_bytes=True)
tft = s3lcd.ESPLCD(bus, 240, 320, inversion_mode=True, color_space=s3lcd.RGB, reset=gdi.RST, rotation=0)
tft.init()
memory("after init")
W, H = tft.width(), tft.height()
print("rotation 0 size", W, H)

# The corner picture: red at the panel's first pixel (0, 0), green at the end of row 0, blue at the start of the
# last row, white at the last pixel. A yellow bar marks row 0 and a cyan bar marks column 0.
tft.fill(s3lcd.BLACK)
tft.fill_rect(0, 0, W, 6, s3lcd.YELLOW)
tft.fill_rect(0, 0, 6, H, s3lcd.CYAN)
for x, y, c in ((0, 0, s3lcd.RED), (W - 40, 0, s3lcd.GREEN), (0, H - 40, s3lcd.BLUE), (W - 40, H - 40, s3lcd.WHITE)):
    tft.fill_rect(x, y, 40, 40, c)
tft.show()
memory("after show")
if not globals().get("SCROLL"):  # the picture stays on the panel until the next run
    raise SystemExit

# The scroll trial: eight colour bands across the native 320 axis, rolled by the panel itself (VSCRDEF, VSCSAD).
for i, c in enumerate((s3lcd.RED, s3lcd.GREEN, s3lcd.BLUE, s3lcd.YELLOW, s3lcd.CYAN, s3lcd.MAGENTA, s3lcd.WHITE, s3lcd.BLACK)):
    tft.fill_rect(0, i * 40, W, 40, c)
tft.show()
tft.vscrdef(0, 320, 0)
print("scroll trial for about %d s" % (int(SCROLL) * 5))
for _ in range(int(SCROLL) * 2):
    for line in range(0, 320, 2):
        tft.vscsad(line)
        time.sleep_ms(15)
tft.vscsad(0)
memory("end")
tft.deinit()
