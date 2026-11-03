# Story map
<!-- Proposed, not applied: this map stays here until the decider confirms it; nothing changes the product's own
map file. -->
**Status:** proposed, not applied <!-- REQUIRED:map-status -->

## Backbone
<!-- The activities, left to right, as the user does them. e.g. `Assign → Notice → Act → Close` -->
Ask in words → Build from shared parts → Step the world → React to a moment → Draw and show → Play and report <!-- REQUIRED:backbone -->

The activities follow the game writer's journey in jobs-and-journeys.md (steps 1 to 6) and the frame of `App.frame` (input, step, draw, show, games/app.py:75-91). "React to a moment" is the job the PO named: "be able to react both ways" (#787).

## Slices
<!-- Walking skeleton first: the thinnest slice that runs end to end. One row per story. job: a job in
jobs-and-journeys.md. tag: as in the brief. proof: something the decider can read.
e.g. `| 0 | Notice | the assignee gets one daily digest | job 1 | H ★C2 | the digest log for one team |` -->
Slice 0 is the thinnest slice that crosses Python and C both ways. It changes no drawing, so it has option A's shape and serves every option. Slice 2 is the move to option B, which D11 chose. It moves no rule and designs no rigid solver. It comes from po-assistant.md PO-32 and tech-lead.md TL-13 and TL-14. Every slice is a proposal. The order after slice 1 waits on Q10.

| slice | activity | story | job | tag | proof |
| --- | --- | --- | --- | --- | --- |
| 0 walking skeleton <!-- REQUIRED:slices --> | Step the world → React to a moment | RENT's physics world step (today's `fall_bodies`, about 25 lines) moves into C behind the same `Bodies` API. The C step fills an int event buffer (landed, bounced with its speed in px/s, at rest) that RENT drains once per frame in place of `hit[]`. A Python twin of the step keeps the Mac tests | jobs 1, 2 | H ★C2, ★C5, ★C11, ★C24 (PO-32, TL-13, TL-14, EVT-24) | RENT plays the same in the PO's words, the Mac tests pass on the twin, `Bodies.step` allocates 0 B (544 B today), pure-play fps at or above 22.09 fps (the P568 gate), a landing raised in C starts dust in Python |
| 1 | Step the world → React to a moment | RENT's rigid tip and topple (#783's decisions) on the slice 0 path: the step model Q9 picks, a tip event, feel numbers passed from Python | jobs 1, 3 | H ★C9, ★C14, ★C20 (PHYS-1, PHYS-4, ENG-25) | the PO plays RENT and judges "heavy and natural", the collapse step in the `time` line against today's 14 to 16 ms |
| 2 | Draw and show | bodies drawn in C by sprite id, so a body costs no Python call per frame (option B) | job 3 | H ★C8 (TL-9, TL-13) | bodies per frame at the same fps in the `time` line |
| 3 | React to a moment | more effects in C on the same events: dust, debris, sparks (P583 #784), with Road's read-back kept by a Python flag | jobs 2, 3 | E C4 (PO-5, TL-5) | his words on the effects, fps not below the game's own |
| 4 | Step the world | input as an engine part: buttons now, a joystick later, as a per-frame input record | job 1 | E ★C18 (TL-2, NET-9) | a game reads the record, and a recorded replay feeds the same `step()` |
| 5 | React to a moment | a sound hook on the same events, a name only until the buzzer exists (P581 #782) | job 2 | E (PO-31, USER-22) | a game calls the hook on a landing, and the hook does nothing without hardware |
| 6 | Build from shared parts | the area-capture game (P585 #786) on the engine, its flood fill entering with it | jobs 1, 4 | H (PO-33, PO-34) | his sister plays the simple version (n = 0 today), and the PO plays the cool one |
| 7 | Build from shared parts | the other games ported one by one to the engine, each in its own PR | job 1 | E ★C1 (TL-3, PO-1) | each game plays the same, and its fps is not below today's |
| 8 | Build from shared parts | the C split by job (P587 #788), without physics, because D17 gives the engine its own module | job 1 | E ★C22 (TL-19, TL-21) | the same bytes on the panel |
| 9 | Draw and show | chip fast paths (D4): S3 PIE for fills, copies and compose, picked at compile time with a plain C twin | job 3 | E, H ★C16 (CHIP-1, CHIP-3, ENG-31) | paint ms per game before and after |
| 10 | Step the world | the networking seams (D2): fixed step, seeded random, input record, flat state pools, with nothing sent | — | H ★C18 (NET-13) | two bot runs with one seed and one input log give the same state |
| later | Play and report | the networking MVP: a separate transport module first (ESP-NOW or plain UDP), then absorbed by the engine (D2) | — | H (NET-11, NET-14) | two boards play one game |

## Delta to the product's map <!-- REQUIRED:spark-process:map-delta -->
<!-- The rows to add or change in the repository's own story map file, in that file's table shape, with its journey
step numbers; proposed, not applied. "n/a — no map file" is allowed. -->
n/a — no map file: pixel-games has no story map file (docs/ holds only discovery/). Its cards sit on spark's board (project 2) under the Slice "pixel-games". items.md names the Slice per card.
<!-- EXTEND:map -->
