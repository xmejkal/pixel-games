# P533 slice 3: the frame in C. The send time, the timeout and its recovery, the config() errors,
# and the "dma" fallback for a second display object. MODE picks the framebuffer: "dma" or "strips".
import time, s3lcd, gdi
from machine import Pin

MODE = globals().get("MODE", "dma")

Pin(gdi.SD_CS, Pin.OUT, value=1)
Pin(gdi.BL, Pin.OUT, value=1)
bus = s3lcd.SPI_BUS(1, mosi=gdi.MOSI, sck=gdi.SCLK, dc=gdi.DC, cs=gdi.CS, pclk=60_000_000, swap_color_bytes=False)
tft = s3lcd.ESPLCD(bus, 240, 320, inversion_mode=True, color_space=s3lcd.RGB, reset=gdi.RST, rotation=0)
print("before init", tft.config(framebuffer=MODE))
tft.init()
print("after init", tft.config())


def timed(n):
    best, total = 10**9, 0
    for i in range(n):
        tft.fill(s3lcd.RED if i % 2 else s3lcd.BLUE)
        t = time.ticks_us()
        tft.show()
        d = time.ticks_diff(time.ticks_us(), t)
        best, total = min(best, d), total + d
    return total / n / 1000, best / 1000


print("send %s: avg %.1f ms, best %.1f ms" % ((MODE,) + timed(20)))

tft.config(timeout=1)
try:
    tft.show()
    print("timeout=1: no error (FAIL)")
except OSError as e:
    print("timeout=1: OSError", e.errno)
tft.config(timeout=100)
tft.fill(s3lcd.GREEN)
tft.fill_rect(0, 0, 40, 40, s3lcd.WHITE)
tft.show()
print("after the timeout: show() ran; the screen is green with a white square at panel (0, 0)")

for kw in ({"timeout": 0}, {"framebuffer": "psram"}, {"framebuffer": "strips" if MODE == "dma" else "dma"}, {"speed": 1}):
    try:
        tft.config(**kw)
        print(kw, "accepted (FAIL)")
    except (ValueError, TypeError) as e:
        print(kw, type(e).__name__, e)
print("round trip", tft.config(**tft.config()))

# A second object on SPI3, on header pins with nothing wired, asks for "dma" too.
bus2 = s3lcd.SPI_BUS(2, mosi=5, sck=4, dc=6, cs=8, pclk=10_000_000, swap_color_bytes=False)
tft2 = s3lcd.ESPLCD(bus2, 240, 320, reset=-1)
tft2.init()
print("second object", tft2.config())
tft2.deinit()
