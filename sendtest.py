# Time s3lcd's show() for one SPI clock and one DMA strip height. Run once per combination, with a reset between.
import time, s3lcd, gdi
from machine import Pin
PCLK, ROWS = PARAMS
Pin(gdi.SD_CS, Pin.OUT, value=1)
Pin(gdi.BL, Pin.OUT, value=1)
bus = s3lcd.SPI_BUS(1, mosi=gdi.MOSI, sck=gdi.SCLK, dc=gdi.DC, cs=gdi.CS, pclk=PCLK, swap_color_bytes=True)
tft = s3lcd.ESPLCD(bus, 240, 320, inversion_mode=True, color_space=s3lcd.RGB, reset=gdi.RST, rotation=1, dma_rows=ROWS)
tft.init()
best, total = 10**9, 0
for i in range(20):
    tft.fill(s3lcd.RED if i % 2 else s3lcd.BLUE)
    t = time.ticks_us()
    tft.show()
    d = time.ticks_diff(time.ticks_us(), t)
    best, total = min(best, d), total + d
print("pclk %d rows %d show avg %.1f ms best %.1f ms" % (PCLK, ROWS, total / 20000, best / 1000))
tft.deinit()
