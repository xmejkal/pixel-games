# Story map
<!-- Proposed, not applied: this map stays here until the decider confirms it; nothing changes the product's own
map file. -->
**Status:** proposed, not applied <!-- REQUIRED:map-status -->

## Backbone
List the layers → Render draws them in order → a C layer paints its rect, opaque or over → Present (show) → the PO judges the look and the fps <!-- REQUIRED:backbone -->

## Slices
| slice | activity | story | job | tag | proof |
| --- | --- | --- | --- | --- | --- |
| 0 walking skeleton <!-- REQUIRED:slices --> | Render draws in order | P639: the burning scene paints the bodies, then the field blended over them (option A) | job 1 | H ★C2, ★C3; A1 | the PO's words on the board and the `burning linear fps` line at 23 or more |
| 1 | List the layers | `Game.layers`, each with `layer` and `draw(cv)`; the Render stage sorts and draws them; fire, burning, balls and rain list theirs | job 2 | H C11, C13 | the Mac tests hold, run117's draw ms within 0.1 (`bench.md:562-571`) |
| 2 | A C layer paints its rect | `HeatField.draw(tft, palette, alpha, rect)` marks `frame_dirty(rect)`, not all; `fx_balls_draw` loses its bg fill (P628's `fx_discs.c`) | job 2, job 3 | H C9, C10, C11 | two C layers stack in one scene (balls under fire, P616) with a Python layer between |
| 3 | Name and place each part | the compositing kernel in the core (Q4), the API doc per part, the swap list | job 3 | H Q4 | `docs/engine-deep-dives.md` lesson D updated, each name with its source |
| later | Cached surfaces | a static layer drawn once into a surface and blitted (option C for a still sky or HUD) | job 2 | H ★C4, ★C6 | the sky's 7.3 ms pass drops (`bench.md:484`) |

<!-- EXTEND:map -->
