# Story map
<!-- Proposed, not applied: this map stays here until the decider confirms it; nothing changes the product's own
map file. -->
**Status:** proposed, not applied <!-- REQUIRED:map-status -->

## Backbone
<!-- The activities, left to right, as the user does them. e.g. `Assign → Notice → Act → Close` -->
Pick a scene → Watch the effect → Change it (BOOT) → Read its cost → Judge it (his words) → Keep it for later (bench.md row, a kernel the games can call)

The kernels the slices share (the PO assistant's K1 to K6, PO-18, and the tech lead's TL-11, H): K1 a heat field, K2 particles, K3 a 2D wave seen from above, K4 a 1D spring surface, K5 circles on a uniform grid, K6 a grain grid. The ten effects ride on them (D4). Each effect is its own `GAMES` entry (D9), shows its name and its cost in ms (D3, D15), and keeps its kernel in the engine module (D8). The slices follow D10: the fire alone, then smoke and bodies on fire, then water and sparks, then colliding bodies, then the rest. Each slice is one play turn and one card in items.md. <!-- REQUIRED:backbone -->

## Slices
<!-- Walking skeleton first: the thinnest slice that runs end to end. One row per story. job: a job in
jobs-and-journeys.md. tag: as in the brief. proof: something the decider can read. -->
| slice | activity | story | job | tag | proof |
| --- | --- | --- | --- | --- | --- |
| 0 walking skeleton, P595 <!-- REQUIRED:slices --> | Pick, Watch, Read its cost, Judge | fire from the K1 heat kernel in plain C, drawn by both screen paths and timed on the same field (D7), its name and its cost in ms on screen (D3, D15) | jobs 1, 2 | D2, D7. H ★C4, ★C5, ★C6 | he plays the fire. His words are sorted into look, variety or HUD (D5), then A1's fixed question (D2). One bench.md row per path |
| 0, P595 | Read its cost | the same fire over a painted picture (D12). Its control is open for the plan, because BOOT swaps two ways of computing (D3) | job 3 | D12. E ★C15 | the blended number in bench.md (A3) |
| after 0, P599 | Read its cost | the HUD text drawn once into a buffer when it changes (F1). Outside P594's scope, built after P595 (D13) | job 2 | D13. H TL-4 | bench.md rows before and after: HUD under 1 ms |
| 1, P596 | Watch | smoke: the same K1 kernel with a grey palette, slower cooling and a drift, with a picture variant (D12) | job 1 | D4, D12. H ★C11 | he plays it and says whether it differs from fire (A5). bench.md row |
| 1, P596 | Watch | bodies on fire: heat seeded into one screen-wide field at each body, so flames trail them (D16). The rain's bodies until P598 exists (H) | job 1 | D16. H ★C11 | he plays it. bench.md row |
| 2, P597 | Watch | water seen from the side: a K4 spring surface that bodies drop into, with K2 splash droplets | job 1 | D4. H ★C14 | he plays it. bench.md row |
| 2, P597 | Watch | sparks or fireworks from the K2 particle kernel, with a picture variant (D12) | jobs 1, 3 | D4, D12. H ★C10 | he plays it. bench.md row against today's 40 Python particles at 2.27 ms |
| 3, P598 | Watch | colliding bodies: a few hundred circles in a box, Verlet steps on a K5 uniform grid in core/, each hit a fact in the event buffer, the grid shared with P592 (D6) | job 1 | D6. H ★C12, ★C13 | he plays it. A Mac test shows no tunnelling at 2,000 px/s². bench.md row |
| 4, P600 | Watch | ripple seen from above (K3), falling sand and water cells (K6), a shockwave or glow, plasma or dissolve | job 1 | D4. H ★C14 | he plays the four. bench.md rows |
| 5, P601 | Read its cost | for the effect that misses its line: a SWAR blend in C, then one PIE `.S` probe (D11). Closed if nothing misses | job 2 | D11. H ★C16, ★C17 | bench.md rows: C, SWAR and PIE against the same line |

## Delta to the product's map <!-- REQUIRED:spark-process:map-delta -->
<!-- The rows to add or change in the repository's own story map file, in that file's table shape, with its journey
step numbers; proposed, not applied. "n/a — no map file" is allowed. -->
n/a — no map file: pixel-games has no story map file (docs/ holds only discovery/). Its cards sit on spark's board (project 2) under the Slice "pixel-games". items.md names the Slice per card.
<!-- EXTEND:map -->
