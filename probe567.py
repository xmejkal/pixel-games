"""
P567: what the new art costs on the board, with the frame where the games paint it (P556 "double": PSRAM) or the old
internal frame ("dma"), for the P565 restyle's budgets.

    mpremote run probe567.py            # "double", as the games run
    (with lcd.FRAMEBUFFER = "dma" set first, the old baseline)

One line per number: `name value unit`. Each timing is per call over n calls, the empty loop's share taken off, as in
probe550.bench(). Sprite timings at one spot are cache-warm lower bounds; the `interleaved` line times the sprite after
a full-frame blit, as in play. The sources are the real pictures in s3lcd.pool, drawn in the panel shape
TftCanvas.picture uses (lcd.py). It ends with tft.deinit().
"""

import gc
import os
import time

import esp32

import app
import lcd
import pictures

PANEL_H = lcd.PANEL_H


def per_call(n, body):
    """Microseconds per call of body(), a loop calling an empty function taken off (body is a lambda too)."""
    nothing = lambda: None
    t = time.ticks_us()
    for _ in range(n):
        nothing()
    empty = time.ticks_diff(time.ticks_us(), t) / n
    t = time.ticks_us()
    for _ in range(n):
        body()
    return time.ticks_diff(time.ticks_us(), t) / n - empty


def say(name, value, unit):
    print("%s %.2f %s" % (name, value, unit))


def physics(n_bodies, n_particles, updates):
    """Milliseconds per update: bodies under gravity on a damped spring, particles under gravity and drag with a life."""
    bodies = [[160.0 + i, 120.0, 0.0, 0.0, 160.0 + i, 120.0] for i in range(n_bodies)]  # x, y, vx, vy, rest x, rest y
    parts = [[160.0, 120.0, (i % 7) * 20.0 - 60.0, -(i % 5) * 30.0, 1.0] for i in range(n_particles)]  # x, y, vx, vy, life
    dt, g, k, c, drag = 0.04, 820.0, 60.0, 8.0, 0.98
    t = time.ticks_us()
    for _ in range(updates):
        for b in bodies:
            ax = -k * (b[0] - b[4]) - c * b[2]
            ay = g - k * (b[1] - b[5]) - c * b[3]
            b[2] += ax * dt
            b[3] += ay * dt
            b[0] += b[2] * dt
            b[1] += b[3] * dt
        for p in parts:
            p[3] += g * dt
            p[2] *= drag
            p[3] *= drag
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            if p[4] <= 0:
                p[0], p[1], p[4] = 160.0, 120.0, 1.0
    return time.ticks_diff(time.ticks_us(), t) / updates / 1000


def memory():
    heaps = esp32.idf_heap_info(esp32.HEAP_DATA)  # (total, free, largest free block, min free) per region
    say("psram_free", sum(h[1] for h in heaps if h[0] > 1_000_000), "B")
    say("psram_largest_block", max(h[2] for h in heaps if h[0] > 1_000_000), "B")
    say("internal_largest_block", max(h[2] for h in heaps if h[0] <= 1_000_000), "B")
    gc.collect()
    say("gc_free", gc.mem_free(), "B")
    say("gc_alloc", gc.mem_alloc(), "B")
    try:
        big = bytearray(4_000_000)  # the substitute for A4's pool test: can 4 MB more be had at all?
        say("alloc_4mb", 1, "ok")
        del big
    except MemoryError:
        say("alloc_4mb", 0, "ok")
    gc.collect()
    st = os.statvfs("/")
    say("flash_free", st[0] * st[3], "B")
    say("flash_total", st[0] * st[2], "B")
    say("art_on_board", sum(os.stat("/packs/" + f)[6] for f in os.listdir("/packs")), "B")


def bench():
    t = time.ticks_ms()
    ok = pictures.load()
    say("art_load", time.ticks_diff(time.ticks_ms(), t), "ms")
    if not ok:
        print("no art on the board")
        return
    say("art_loaded", sum(len(p[2]) for p in pictures.PICS.values()), "B")
    out = lcd.open_tft(app.SPI_HZ)
    tft, cv = out.tft, out.canvas
    say("framebuffer_double", 1 if tft.config()["framebuffer"] == "double" else 0, "")
    tft.track(True)
    cv.start()
    key = pictures.art_index.KEY_C565
    blit = tft.blit_buffer
    w, h, sky = pictures.PICS["sky"]  # 320 x 240, opaque
    say("blit_full_opaque", per_call(20, lambda: blit(sky, 0, 0, h, w, 255, -1)) / 1000, "ms")
    say("blit_full_keyed", per_call(20, lambda: blit(sky, 0, 0, h, w, 255, key)) / 1000, "ms")
    sw, sh, small = pictures.PICS["runner_run0"]  # 16 x 24
    say("sprite_16x24_warm", per_call(1000, lambda: blit(small, 100, PANEL_H - 100 - sw, sh, sw, 255, key)), "us")
    big = max((p for p in pictures.PICS.items() if p[1][0] <= 100 and p[1][1] <= 100), key=lambda p: p[1][0] * p[1][1])
    bname, (bw, bh, bbuf) = big
    print("largest_sprite %s %dx%d" % (bname, bw, bh))
    say("sprite_largest_warm", per_call(1000, lambda: blit(bbuf, 60, PANEL_H - 100 - bw, bh, bw, 255, key)), "us")
    say("sprite_16x24_offscreen", per_call(1000, lambda: cv.picture(small, -8, 100, sw, sh, key)), "us")  # half past the left edge
    n, spent = 50, 0
    for _ in range(n):  # the sprite right after a full frame, as in play
        blit(sky, 0, 0, h, w, 255, -1)
        t = time.ticks_us()
        blit(small, 100, PANEL_H - 100 - sw, sh, sw, 255, key)
        spent += time.ticks_diff(time.ticks_us(), t)
    say("sprite_16x24_interleaved", spent / n, "us")
    patch = sky[:64 * 64 * 2]  # 64 x 64 pixels of the sky, as a picture
    us = per_call(200, lambda: blit(patch, 80, 80, 64, 64, 128, -1))
    say("blit_64x64_alpha128", us, "us")
    say("blit_alpha128_per_px", us * 1000 / (64 * 64), "ns")
    say("picture_16x24_python", per_call(1000, lambda: cv.picture(small, 100, 100, sw, sh, key)), "us")
    say("pictures_draw_16x24", per_call(1000, lambda: pictures.draw(cv, "runner_run0", 100, 100)), "us")
    say("physics_30_bodies_40_particles", physics(30, 40, 200), "ms")
    say("physics_0_bodies_40_particles", physics(0, 40, 200), "ms")
    tft.show()
    time.sleep_ms(100)
    tft.deinit()
    memory()


bench()
