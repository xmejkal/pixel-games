# Proposed items
<!-- Filing needs the decider's yes to this list: a D in brief.md that names items.md. One block per item; copy the
block for more. needed by: the decider's words, quoted. value proven by: a proof the decider can read.
status: proposed, or filed D<n>.
e.g. `- needed by: "I want to know what we should build next" (Lena, 2026-10-06)` -->

## A 96 px figure is only arithmetic → two steps with their own gates: a painted figure on the Mac (no bench), then a 2 MB pack on the board with the memory and the frame rate (his bench)
- type: spike <!-- REQUIRED:item-type -->
- needed by: "we should sell it more and make bigger figures, ours are tiny and one doesn't appreciate the details so much" (the PO, 2026-11-18) <!-- REQUIRED:needed-by -->
- value proven by: a GIF he can look at, and a board log with the pool, the free PSRAM, the fps and the load time against the pass line <!-- REQUIRED:value-proven-by -->
- depends on: — <!-- REQUIRED:depends-on -->
- status: proposed <!-- REQUIRED:item-status -->
- label (the repository's type label): spike <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P900, https://github.com/xmejkal/spark/issues/1279 <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games <!-- REQUIRED:spark-process:slice -->
<!-- EXTEND:item-fields -->

## No game lets the player switch figures → the walking skeleton: two figures on one screen, a switch, and one action of both that ends the mission
- type: story <!-- REQUIRED:item-type -->
- needed by: "one can pick who to control, and there is some collaboration mission always" (the PO, 2026-11-18) <!-- REQUIRED:needed-by -->
- value proven by: he plays it on the board (a feel slice: it stops at ready to play) <!-- REQUIRED:value-proven-by -->
- depends on: the spike. P901 (https://github.com/xmejkal/spark/issues/1280) follows it, as slice 2 of the story map <!-- REQUIRED:depends-on -->
- status: proposed <!-- REQUIRED:item-status -->
- label (the repository's type label): story <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P900, https://github.com/xmejkal/spark/issues/1279 <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games <!-- REQUIRED:spark-process:slice -->
<!-- EXTEND:item-fields -->

## Nobody knows which input switches a figure well → a prototype on today's pool: two placeholder figures at today's size and each way to switch, played by him
- type: spike <!-- REQUIRED:item-type -->
- needed by: "one can pick who to control, and there is some collaboration mission always" (the PO, 2026-11-18) <!-- REQUIRED:needed-by -->
- value proven by: he tries each way to switch and names the one he wants (a feel slice) <!-- REQUIRED:value-proven-by -->
- depends on: — (no 96 px art, no bigger pool and no P901 are needed, council/refuter.md part e) <!-- REQUIRED:depends-on -->
- status: proposed <!-- REQUIRED:item-status -->
- label (the repository's type label): spike <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P900, https://github.com/xmejkal/spark/issues/1279 <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games <!-- REQUIRED:spark-process:slice -->
<!-- EXTEND:item-fields -->

## Board actions
<!-- Each action, taken or pending, with its D. e.g. `- move the item to Discovery · pending` -->
- file the two items above · pending, Q11 <!-- REQUIRED:board-actions -->
