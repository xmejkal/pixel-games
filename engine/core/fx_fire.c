// The fire (P595): see fx_fire.h. --- MVP (P595) ---
#include "fx_fire.h"

#include <string.h>

static uint32_t xorshift32(uint32_t *state) {
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return *state = x;
}

void fx_fire_init(fx_fire_t *f, uint8_t *heat, int32_t w, int32_t h, uint32_t seed) {
    f->w = w;
    f->h = h;
    f->heat = heat;
    f->rng = seed ? seed : 1;
    memset(heat, 0, (size_t)w * (size_t)h);
}

void fx_fire_step(fx_fire_t *f, int32_t steps, int32_t decay) {
    int32_t w = f->w, h = f->h;
    uint8_t *bottom = f->heat + (h - 1) * w;
    for (int32_t s = 0; s < steps; s++) {
        for (int32_t x = 0; x < w; x++) {
            bottom[x] = (uint8_t)(xorshift32(&f->rng) >> 24);
        }
        for (int32_t y = 0; y < h - 1; y++) {  // top down, so each row reads rows this step has not changed yet
            uint8_t *row = f->heat + y * w;
            const uint8_t *below = row + w;
            const uint8_t *below2 = y + 2 < h ? below + w : NULL;
            for (int32_t x = 0; x < w; x++) {
                uint32_t sum = below[x];
                if (x > 0) {
                    sum += below[x - 1];
                }
                if (x + 1 < w) {
                    sum += below[x + 1];
                }
                if (below2) {
                    sum += below2[x];
                }
                sum = (sum * (uint32_t)decay) >> 7;
                row[x] = (uint8_t)(sum > 255 ? 255 : sum);
            }
        }
    }
}

void fx_fire_draw(const fx_fire_t *f, uint16_t *panel, const uint16_t *palette) {
    int32_t w = f->w, h = f->h, pw = 2 * h;
    for (int32_t k = 0; k < w; k++) {  // panel rows 2k and 2k + 1 show field column w - 1 - k, top cell first
        const uint8_t *cell = f->heat + (w - 1 - k);
        uint16_t *out = panel + 2 * k * pw;
        for (int32_t y = 0; y < h; y++, cell += w) {
            uint16_t c = palette[*cell];
            out[2 * y] = c;
            out[2 * y + 1] = c;
        }
        memcpy(out + pw, out, (size_t)pw * sizeof(uint16_t));
    }
}
