# P533 slice 1: the send with no byte swap. Times 20 full-frame sends, then leaves six colour bands on the panel.
# Run: mpremote run probe1.py. From left to right as played, the bands must be red, green, blue, yellow, cyan, magenta.
import time, s3lcd, gdi
from machine import Pin
from gfx import c565

Pin(gdi.SD_CS, Pin.OUT, value=1)
Pin(gdi.BL, Pin.OUT, value=1)
bus = s3lcd.SPI_BUS(1, mosi=gdi.MOSI, sck=gdi.SCLK, dc=gdi.DC, cs=gdi.CS, pclk=60_000_000, swap_color_bytes=False)
tft = s3lcd.ESPLCD(bus, 240, 320, inversion_mode=True, color_space=s3lcd.RGB, reset=gdi.RST, rotation=1)
tft.init()
best, total = 10**9, 0
for i in range(20):
    tft.fill(c565(255, 0, 0) if i % 2 else c565(0, 0, 255))
    t = time.ticks_us()
    tft.show()
    d = time.ticks_diff(time.ticks_us(), t)
    best, total = min(best, d), total + d
print("swap off: show avg %.1f ms best %.1f ms" % (total / 20000, best / 1000))
colours = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255))
for i, rgb in enumerate(colours):
    tft.fill_rect(i * 54, 0, 54, 240, c565(*rgb))
tft.show()
