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

// The random draws, in this order, so a reference can repeat them byte for byte. Each draw is one xorshift32 call.
// - fx_fire_init: the map's 8192 cells row by row, one draw each, then the FX_FIRE_MAX_SPOTS spots, one draw each.
// - fx_fire_set_look, when the spot count changes: the FX_FIRE_MAX_SPOTS spots again, one draw each.
// - fx_fire_step, per step: with spots 0, the bottom row's cells left to right, one draw each (part 1's row). Else
//   each spot in turn, one draw (its walk or jump), then the bottom row's cells left to right, one draw each (the
//   flicker). Then, with sway 1, the rows from the top down, one draw per 16 cells from x = 0, 16, 32 and so on.
//   With wind not 0, each row takes one draw first, before its sway draws (the wind's).
// A spot's place is r % w. A spot's draw r: when its top 6 bits are 0 (1 in 64) it jumps to (r >> 8) % w, else it
// walks r % 3 - 1 cells, clamped to the field. The flicker keeps heat * (128 + (r >> 25)) >> 8. The sway's draw gives
// 2 bits per cell, the lowest first: 00 is -1, 01 and 10 are 0, 11 is +1. The wind's draw r shifts the row's read one
// column against the wind when r & 255 is under |wind|.

static void place_spots(fx_fire_t *f) {
    for (int32_t i = 0; i < FX_FIRE_MAX_SPOTS; i++) {
        f->spot_x[i] = (int32_t)(xorshift32(&f->rng) % (uint32_t)f->w);
    }
}

// n cells stride apart, each the mean of itself and its two neighbours, in place, wrapping around the ends.
static void blur_ring(uint8_t *p, int32_t n, int32_t stride) {
    uint32_t first = p[0], prev = p[(n - 1) * stride];
    for (int32_t i = 0; i < n; i++) {
        uint32_t cur = p[i * stride];
        uint32_t next = i + 1 < n ? p[(i + 1) * stride] : first;
        p[i * stride] = (uint8_t)((prev + cur + next) / 3);
        prev = cur;
    }
}

// The cooling map: 1 cell in 16 at 255 and the rest 0, two 3 x 3 box blurs that wrap (each a row pass, then a
// column pass), so the tile has no seam, then its min to max stretched onto 0 to 255.
static void make_cooling(fx_fire_t *f) {
    uint8_t *map = f->cooling;
    int32_t n = FX_FIRE_MAP_W * FX_FIRE_MAP_H;
    for (int32_t i = 0; i < n; i++) {
        map[i] = xorshift32(&f->rng) >> 28 == 0 ? 255 : 0;
    }
    for (int32_t pass = 0; pass < 2; pass++) {
        for (int32_t k = 0; k < FX_FIRE_MAP_H; k++) {
            blur_ring(map + k * FX_FIRE_MAP_W, FX_FIRE_MAP_W, 1);
        }
        for (int32_t k = 0; k < FX_FIRE_MAP_W; k++) {
            blur_ring(map + k, FX_FIRE_MAP_H, FX_FIRE_MAP_W);
        }
    }
    uint32_t lo = 255, hi = 0;
    for (int32_t i = 0; i < n; i++) {
        lo = map[i] < lo ? map[i] : lo;
        hi = map[i] > hi ? map[i] : hi;
    }
    for (int32_t i = 0; i < n; i++) {
        map[i] = hi > lo ? (uint8_t)((map[i] - lo) * 255 / (hi - lo)) : 0;
    }
}

void fx_fire_init(fx_fire_t *f, uint8_t *heat, uint8_t *cooling, int32_t w, int32_t h, uint32_t seed) {
    f->w = w;
    f->h = h;
    f->heat = heat;
    f->cooling = cooling;
    f->rng = seed ? seed : 1;
    f->scroll = 0;
    f->fast_scroll = 0;
    f->decay = 31;
    f->cool = 0;
    f->sway = 0;
    f->spots = 0;
    f->spread = 1;
    f->fast = 0;
    memset(heat, 0, (size_t)w * (size_t)h);
    make_cooling(f);
    place_spots(f);
}

void fx_fire_set_look(fx_fire_t *f, int32_t decay, int32_t cool, int32_t sway, int32_t spots, int32_t spread,
                      int32_t fast) {
    f->decay = decay;
    f->cool = cool;
    f->sway = sway;
    f->spread = spread;
    f->fast = fast;
    if (spots != f->spots) {
        f->spots = spots;
        place_spots(f);
    }
}

// The bottom row from the spots: each walks or jumps, each writes a bump (the larger value kept where bumps meet),
// then each cell flickers to 50 to 100 % of its heat.
static void spots_row(fx_fire_t *f, uint8_t *bottom) {
    int32_t w = f->w, spread = f->spread;
    for (int32_t i = 0; i < f->spots; i++) {
        uint32_t r = xorshift32(&f->rng);
        int32_t x = f->spot_x[i];
        if (r >> 26 == 0) {
            x = (int32_t)((r >> 8) % (uint32_t)w);
        } else {
            x += (int32_t)(r % 3) - 1;
            x = x < 0 ? 0 : x >= w ? w - 1 : x;
        }
        f->spot_x[i] = x;
    }
    memset(bottom, 0, (size_t)w);
    for (int32_t i = 0; i < f->spots; i++) {
        for (int32_t dx = -spread; dx <= spread; dx++) {
            int32_t x = f->spot_x[i] + dx;
            if (x >= 0 && x < w) {
                uint8_t v = (uint8_t)(255 - (dx < 0 ? -dx : dx) * 255 / (spread + 1));
                bottom[x] = v > bottom[x] ? v : bottom[x];
            }
        }
    }
    for (int32_t x = 0; x < w; x++) {
        bottom[x] = (uint8_t)((bottom[x] * (128 + (xorshift32(&f->rng) >> 25))) >> 8);
    }
}

static inline uint32_t cell(const uint8_t *row, int32_t x, int32_t w) {  // 0 outside the field
    return (uint32_t)x < (uint32_t)w ? row[x] : 0;
}

void fx_fire_step(fx_fire_t *f, int32_t steps, int32_t wind) {
    int32_t w = f->w, h = f->h;
    uint32_t decay = (uint32_t)f->decay, cool = (uint32_t)f->cool;
    uint32_t fast_at = 256 - (uint32_t)f->fast;  // a map cell at least this makes a fast cell, 256 never
    uint32_t gust = (uint32_t)(wind < 0 ? -wind : wind);
    int32_t against = wind > 0 ? -1 : 1;  // a cell reads upwind, so positive wind carries heat to larger x
    uint8_t *bottom = f->heat + (h - 1) * w;
    for (int32_t s = 0; s < steps; s++) {
        if (f->spots > 0) {
            spots_row(f, bottom);
        } else {
            for (int32_t x = 0; x < w; x++) {
                bottom[x] = (uint8_t)(xorshift32(&f->rng) >> 24);
            }
        }
        for (int32_t y = 0; y < h - 1; y++) {  // top down, so each row reads rows this step has not changed yet
            uint8_t *row = f->heat + y * w;
            const uint8_t *below = row + w;
            const uint8_t *below2 = y + 2 < h ? below + w : NULL;
            const uint8_t *below3 = y + 3 < h ? below2 + w : NULL;
            const uint8_t *cooling = f->cooling + ((y + f->scroll) & (FX_FIRE_MAP_H - 1)) * FX_FIRE_MAP_W;
            const uint8_t *fast = below2 ? f->cooling + ((y + f->fast_scroll) & (FX_FIRE_MAP_H - 1)) * FX_FIRE_MAP_W
                                         : NULL;
            int32_t shift = gust && (xorshift32(&f->rng) & 255) < gust ? against : 0;
            uint32_t bits = 0;
            for (int32_t x = 0; x < w; x++) {
                int32_t c = x + shift;  // the column read below, shifted by the wind and the sway
                if (f->sway) {
                    if ((x & 15) == 0) {
                        bits = xorshift32(&f->rng);
                    }
                    c += (int32_t)((bits >> 1) & 1) + (int32_t)(bits & 1) - 1;
                    bits >>= 2;
                }
                const uint8_t *near = below, *far = below2;  // a fast cell reads one row further down
                if (fast && fast[(x + FX_FIRE_MAP_W / 2) & (FX_FIRE_MAP_W - 1)] >= fast_at) {
                    near = below2;
                    far = below3;
                }
                uint32_t left = cell(near, c - 1, w), mid = cell(near, c, w), right = cell(near, c + 1, w);
                uint32_t two = far ? cell(far, c, w) : 0;
                uint32_t hot = left > mid ? left : mid;  // the hottest cell read
                hot = right > hot ? right : hot;
                hot = two > hot ? two : hot;
                uint32_t sum = ((left + mid + right + two) * decay) >> 7;
                sum = sum > hot ? hot : sum;  // never hotter than its source, so no decay runs away
                uint32_t loss = (cooling[x & (FX_FIRE_MAP_W - 1)] * cool) >> 8;
                row[x] = (uint8_t)(sum > loss ? sum - loss : 0);
            }
        }
        f->scroll = (f->scroll + 1) & (FX_FIRE_MAP_H - 1);
        f->fast_scroll = (f->fast_scroll + 2) & (FX_FIRE_MAP_H - 1);
    }
}

void fx_fire_draw(const fx_fire_t *f, uint16_t *panel, const uint16_t *palette) {
    int32_t w = f->w, h = f->h, pw = 2 * h;
    for (int32_t k = 0; k < w; k++) {  // panel rows 2k and 2k + 1 show field column w - 1 - k, top cell first
        const uint8_t *col = f->heat + (w - 1 - k);
        uint16_t *out = panel + 2 * k * pw;
        for (int32_t y = 0; y < h; y++, col += w) {
            uint16_t c = palette[*col];
            out[2 * y] = c;
            out[2 * y + 1] = c;
        }
        memcpy(out + pw, out, (size_t)pw * sizeof(uint16_t));
    }
}
