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
- status: filed D21 <!-- REQUIRED:item-status -->
- label (the repository's type label): spike <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P900, https://github.com/xmejkal/spark/issues/1279 <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games <!-- REQUIRED:spark-process:slice -->
<!-- EXTEND:item-fields -->

## No game lets the player switch figures → the walking skeleton: two figures on one screen, a switch, and one action of both that ends the mission
- type: story <!-- REQUIRED:item-type -->
- needed by: "one can pick who to control, and there is some collaboration mission always" (the PO, 2026-11-18) <!-- REQUIRED:needed-by -->
- value proven by: he plays it on the board (a feel slice: it stops at ready to play) <!-- REQUIRED:value-proven-by -->
- depends on: the two spikes. Its order against P901 (https://github.com/xmejkal/spark/issues/1280), whose card says "Needed by P900", is Q14 <!-- REQUIRED:depends-on -->
- status: filed D21 <!-- REQUIRED:item-status -->
- label (the repository's type label): story <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P900, https://github.com/xmejkal/spark/issues/1279 <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games <!-- REQUIRED:spark-process:slice -->
<!-- EXTEND:item-fields -->

## Nobody knows which input switches a figure well → a prototype on today's pool: two placeholder figures at today's size and each way to switch, played by him
- type: spike <!-- REQUIRED:item-type -->
- needed by: "one can pick who to control, and there is some collaboration mission always" (the PO, 2026-11-18) <!-- REQUIRED:needed-by -->
- value proven by: he tries each way to switch and names the one he wants (a feel slice) <!-- REQUIRED:value-proven-by -->
- depends on: — for the stick's up and down, FIRE's double tap or hold and the automatic switch. PICK, the knob and the split of FIRE each need an app change first <!-- REQUIRED:depends-on -->
- status: filed D21 <!-- REQUIRED:item-status -->
- label (the repository's type label): spike <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P900, https://github.com/xmejkal/spark/issues/1279 <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games <!-- REQUIRED:spark-process:slice -->
<!-- EXTEND:item-fields -->

## Nobody counted what the first mission's whole pictures weigh → a count on the Mac: each move of each character of the first mission painted, and the bytes summed with the street against the pool size that the board showed
- type: spike <!-- REQUIRED:item-type -->
- needed by: "Q4: whole pictures first, behind one picture source." (the PO, 2026-11-18, D26) <!-- REQUIRED:needed-by -->
- value proven by: a table he can read, one row for each character and move, with the sum against the pass line <!-- REQUIRED:value-proven-by -->
- depends on: the list of the first mission's figures and actions, which is his since 2026-11-19 (D29): the fireman moves to the wall and holds a ladder, and the child climbs. The test and the pass line are his too (D27, D28). His words name no captured motion for an action and no idle cycle. So the count's plan names a stand-in for each such row and marks it (the facilitator's method, no decision of his) <!-- REQUIRED:depends-on -->
- status: filed D27 <!-- REQUIRED:item-status -->
- label (the repository's type label): spike <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P900, https://github.com/xmejkal/spark/issues/1279 <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games <!-- REQUIRED:spark-process:slice -->
<!-- EXTEND:item-fields -->

## Board actions
<!-- Each action, taken or pending, with its D. e.g. `- move the item to Discovery · pending` -->
- file the three items above · taken 2026-11-18 · D21: P904 #1283, P905 #1284 (the switch prototype), P906 #1285 (the walking skeleton) <!-- REQUIRED:board-actions -->
- file the count's item · taken 2026-11-19 · D27: P924 #1308
- order the count's card into Ready · taken 2026-11-19, 10:11 Prague · D30
