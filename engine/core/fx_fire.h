// The fire (P595): a field of heat that rises and cools, drawn through a palette of 256 colours onto the whole panel.
// The method is Lode Vandevenne's heat fire (lodev.org/cgtutor/fire.html), written again from its formula only, with
// no code copied (D14). Plain C99 with no MicroPython or IDF header, so the Mac test builds it with clang and the board
// build with ESP-IDF.
// --- MVP (P595) ---
#ifndef FX_FIRE_H
#define FX_FIRE_H

#include <stdint.h>

// The caller owns heat: w x h bytes, row-major in game orientation, row h - 1 at the bottom. No static state.
typedef struct {
    int32_t w, h;
    uint8_t *heat;
    uint32_t rng;  // xorshift32 state, never 0
} fx_fire_t;

// Zero the field and seed the random numbers (a seed of 0 becomes 1).
void fx_fire_init(fx_fire_t *f, uint8_t *heat, int32_t w, int32_t h, uint32_t seed);

// steps steps. Each one gives the bottom row a random heat per cell, then each cell above, from the top row down,
// becomes (the three cells below it + the cell two below) * decay >> 7, at most 255. A cell outside the field counts 0.
// decay 32 keeps the heat, less cools it. decay is 0 to 255.
void fx_fire_step(fx_fire_t *f, int32_t steps, int32_t decay);

// The whole panel, 2h px wide and 2w px high, as palette[heat], in the panel order of lcd.py's TftCanvas.fill at
// ORIENTATION 0: panel (px, py) shows cell ((2w - 1 - py) / 2, px / 2). The palette is already in the panel's byte order.
void fx_fire_draw(const fx_fire_t *f, uint16_t *panel, const uint16_t *palette);

#endif
