# The user: the scene author's journey

Written 2026-11-05 by the same Fable agent that wrote the other two lenses (no independent review). The user is the PO (n = 1), who writes scenes with an agent and plays them on the board. Paths are relative to the root of the firebeetle-games-p638 worktree.

## Findings

- US-1 · Today a scene author who wants flames in front writes the draw calls in paint in that order, by hand. BurningBodies.paint calls super().paint (the field) and then physics_plugin.draw (the boxes). Swapping the two lines puts the field over the boxes. · E games/burning.py:126-128 · supports only: the product.
- US-2 · The swap alone gives "hot flames cover the body": alpha_blend_565 returns fg at alpha 255, and ALPHA is a ramp over heat. Whether a covered body reads as "on fire" or as "gone" is the PO's call. · E engine/driver/src/blend565.h:23-25, games/fire.py:68-79 (the ALPHA ramp) · supports only: the product's formula. The look is H.
- US-3 · The PO's second wish is "a python ldrawn layer in between two C layers". Today a Python draw goes through TftCanvas.fill into tft.fill_rect, which writes the frame and marks its tiles. A C blend after it composes over it, because fx_fire_blend reads the frame's pixel before it writes. So the stacking works today with no new code, as long as the author writes the calls in order. · E games/lcd.py:77-98, engine/core/fx_fire.c:294-298 · supports only: the product.
- US-4 · What the author cannot do today: turn a draw layer on or off by a list, as plugins do for the stages (Game.plugins, "in their stage order"). The draw order has no such list. · E games/gfx.py:302, games/plugins.py:9-10 · supports only: the product.
- US-5 · The author sees the cost in the scene's own log line, "burning <mode> fps <fps> step <ms> draw <ms>". A second field draw shows up as draw ms. · E games/burning.py:13 · supports only: the product.
- US-6 · Harm today: every C draw marks all tiles (frame_dirty_all), so a scene with a C layer sends the whole frame each show(), and the partial send of P533 slice 5 gains nothing. The author cannot change this from Python. · E engine/binding.c:307, :470. engine/driver/src/frame.h:62-72 · supports only: the product.
- US-7 · The PO judged P602's fire by eye: "it looks good, I'm glad we have this effect, but it doesn't really fit the flappy". He judges looks on the board, not from numbers. So the first proof for P639 is a run he plays. · E bench.md:457 · supports only: an account, n = 1.
- US-8 · For P635 the author draws silhouette figures in Python (open in #850). A sprite drawn through Python costs 69 to 71 µs, so a handful of figures is under 1 ms. A full-panel C layer costs 4 to 8 ms. The Python layer is not the cost. · E bench.md:215. docs/discovery/2026-11-05-p612-frame-time/README.md:12 · supports only: a benchmark of sprites and of the fire.

## What I could not check, and why

- How the PO reads a body under hot flames: he has not seen it (Q2).
- Whether the author wants the list on Game (beside plugins) or on a Scene object: no words from him.

## Questions for the decider

- Q2 · Should the body show through the flames in front? · decides: whether the front layer blends at full heat or at a capped alpha, and so one pass or two.
- Q4 · Do you want the layer list beside Game.plugins, one tuple per scene? · decides: the Python API's shape.

## Searches

none.
