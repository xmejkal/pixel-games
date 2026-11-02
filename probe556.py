"""
P556 slice 1a: the "double" framebuffer on the board, before any game uses it.

    mpremote exec "import probe556; probe556.check()"

It prints the config, round-trips it, times a full and a partial show(), and prints free memory, so two runs after
soft resets show the same numbers. The screen shows red, then a white square in its middle on green.
"""

import esp32
import time

import lcd


def free():
    """Free bytes of PSRAM, and the largest free internal block, from the IDF heap (regions over 1 MB are PSRAM)."""
    heaps = esp32.idf_heap_info(esp32.HEAP_DATA)
    return sum(h[1] for h in heaps if h[0] > 1_000_000), max(h[2] for h in heaps if h[0] <= 1_000_000)


def check():
    print("before", free())
    lcd.FRAMEBUFFER = "double"
    out = lcd.open_tft(60_000_000)
    tft = out.tft
    c = tft.config()
    print("config", c, "round trip", tft.config(**c) == c)
    print("after init", free())
    tft.fill(0xF800 >> 8 | (0xF800 & 0xFF) << 8)
    t = time.ticks_us()
    n = tft.show()
    queued = time.ticks_diff(time.ticks_us(), t)
    t = time.ticks_us()
    tft.show()  # nothing drawn since: it waits for the full frame, then sends the "before" tiles (open_tft sets partial)
    waited = time.ticks_diff(time.ticks_us(), t)
    print("full show windows %d returned after %d us, next show %d us" % (n, queued, waited))
    time.sleep_ms(100)
    tft.fill(0x07E0 >> 8 | (0x07E0 & 0xFF) << 8)
    tft.show()
    time.sleep_ms(100)
    tft.show()  # the "before" marks of the green fill
    tft.fill_rect(100, 140, 40, 40, 0xFFFF)
    t = time.ticks_us()
    n = tft.show()
    print("partial show windows %d returned after %d us" % (n, time.ticks_diff(time.ticks_us(), t)))
    time.sleep_ms(200)
    tft.deinit()
    print("after deinit", free())
