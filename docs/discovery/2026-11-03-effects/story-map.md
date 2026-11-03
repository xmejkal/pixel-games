# Story map
<!-- Proposed, not applied: this map stays here until the decider confirms it; nothing changes the product's own
map file. -->
**Status:** proposed, not applied <!-- REQUIRED:map-status -->

## Backbone
<!-- The activities, left to right, as the user does them. e.g. `Assign → Notice → Act → Close` -->
Pick a scene → Watch the effect → Change it (BOOT) → Read its cost → Judge it (his words) → Keep it for later (bench.md row, a kernel the games can call)

The kernels the slices share (the PO assistant's K1 to K6, PO-18, and the tech lead's TL-11, H): K1 a heat field, K2 particles, K3 a 2D wave seen from above, K4 a 1D spring surface, K5 circles on a uniform grid, K6 a grain grid. Which ten effects ride on them is Q2, the path to the screen Q4 and the harness Q6. The rows below follow the PO assistant's ten (option a1 in the brief) as one example of the order, not a choice. <!-- REQUIRED:backbone -->

## Slices
<!-- Walking skeleton first: the thinnest slice that runs end to end. One row per story. job: a job in
jobs-and-journeys.md. tag: as in the brief. proof: something the decider can read.
e.g. `| 0 | Notice | the assignee gets one daily digest | job 1 | H ★C2 | the digest log for one team |` -->
| slice | activity | story | job | tag | proof |
| --- | --- | --- | --- | --- | --- |
| 0 walking skeleton <!-- REQUIRED:slices --> | Pick, Watch, Read its cost, Judge | one effects scene (its name on screen, one row in a table) shows fire from the K1 heat kernel in plain C, drawn by the engine module (the path is Q4), with its step and draw ms on screen and in a report line | jobs 1, 2 | H ★C4, ★C5, ★C6 | the PO plays fire on the board and says his words. A bench.md row with fps, step ms and draw ms from three 5 s report lines |
| 0 | Change it | a BOOT tap in the scene changes one feel number or the size (half-res field against a strip), all numbers from Python (D12) | job 3 | E ★C25 | the report line shows both sizes. He says whether the tap helps |
| 1 | Watch | smoke: the same K1 kernel with a grey palette, slower cooling and a sideways drift | job 1 | H ★C11 | he plays it, and says whether it looks different from fire |
| 1 | Watch | bodies on fire: falling bodies seed heat into the K1 field, so flames trail them (the rain's world, or K5 circles once slice 3 exists) | job 1 | H ★C11, ★C12 | he plays it. bench.md row |
| 2 | Watch | sparks or fireworks from the K2 particle kernel, hundreds of particles drawn in C | jobs 1, 3 | H ★C10 | he plays it. bench.md row against today's 40 Python particles at 2.27 ms |
| 2 | Watch | water seen from the side: a K4 spring surface that bodies drop into, with K2 splash droplets | job 1 | H ★C14 | he plays it. bench.md row |
| 3 | Watch | colliding bodies: a few hundred circles in a box on a K5 uniform grid, with substeps (Q3 decides its home and its overlap with P592) | job 1 | H ★C12, ★C13, ★C20 | he plays it. A Mac test shows no tunnelling at g 2,000 px/s². bench.md row |
| 4 | Watch | ripple seen from above, and a shockwave ring (K3) | job 1 | H ★C14 | he plays it. bench.md row |
| 4 | Watch | falling sand and water as cells (K6) | job 1 | H ★C14 | he plays it. bench.md row |
| 5 | Watch | the tenth, his pick after playing the others: plasma, lightning, metaballs, cloth or a particle liquid | job 1 | H ★C14 | he names it, then plays it |
| later | Read its cost | the same effect drawn over a painted background, so its cost carries into a game (Q9) | job 3 | E ★C15 | bench.md row with both costs |
| later | Change it | a SWAR blend in C, then a PIE `.S` probe for the one effect that misses its line (Q8) | job 2 | H ★C16, ★C17 | bench.md row, C against PIE |

## Delta to the product's map <!-- REQUIRED:spark-process:map-delta -->
<!-- The rows to add or change in the repository's own story map file, in that file's table shape, with its journey
step numbers; proposed, not applied. "n/a — no map file" is allowed. -->
n/a — no map file: pixel-games has no story map file (docs/ holds only discovery/). Its cards sit on spark's board (project 2) under the Slice "pixel-games". items.md names the Slice per card.
<!-- EXTEND:map -->
