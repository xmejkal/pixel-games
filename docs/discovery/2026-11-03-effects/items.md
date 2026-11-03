# Proposed items
<!-- Filing needs the decider's yes to this list: a D in brief.md that names items.md. One block per item; copy the
block for more. needed by: the decider's words, quoted. value proven by: a proof the decider can read.
status: proposed, or filed D<n>.
e.g. `- needed by: "I want to know what we should build next" (Lena, 2026-10-06)` -->

Nothing is filed. P595 is the next free number in xmejkal/spark (the newest issue is P594 #795, read with `gh issue list --repo xmejkal/spark --state all --limit 3` on 2026-11-03). Each card's form follows spark's issue form (.github/ISSUE_TEMPLATE/item.yml: Needed by, Value proven by). Every card is a sub-issue of P594 #795, which sits under the epic P586 #787. The list holds the walking skeleton, the next two groups and the colliding bodies. P599, the cached HUD, is the team's proposal found on the way, outside P594's scope. Later slices stay in story-map.md until the PO orders them. Sizes are the synthesis's estimate (H), in working sessions of the AI team: XS is under one session, S is one session, M is more than one. Each feel card stops at "ready to play" until he played it (D21). The cards follow option a1's order and the team's readings of his words as an example: Q2 to Q14 can change them.

## P595: the engine draws no pixel and no effect scene exists → one effects scene shows fire from a heat kernel in plain C, drawn by the engine module, with its name and its cost on screen
- type: story (slice 0, the walking skeleton). It tests A1, the proposed riskiest, with A2, A3, A4 and A9 in the same run <!-- REQUIRED:item-type -->
- needed by: "let's try to make 10 more effects, something including fire and smoke" and "just like with the rain, let's just try the effects themselves" (the PO, 2026-11-03, #795) <!-- REQUIRED:needed-by -->
- value proven by: he plays the fire on the board, gives his words, and answers A1's fixed question (keep its look, or change it). bench.md gets a row from three 5 s intervals of app.py's `time` and `avg` lines: fps, step plus draw of a 160 x 120 field drawn at 2 x 2 to the full screen, opaque, plus the largest free internal block at the scene's start and the same fire at alpha 128 over a painted background. Read against the proposed lines of A1, A2 (at most 15.3 ms), A3 and A4 <!-- REQUIRED:value-proven-by -->
- depends on: Q1 (the pass line), Q4 (the path), Q5 (the home), Q6 (the harness), Q9 (black or a picture). The board on USB. Also done when: a Mac test of the kernel passes (D15). Size S to M <!-- REQUIRED:depends-on -->
- status: proposed <!-- REQUIRED:item-status -->
- label (the repository's type label): story <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787) <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games <!-- REQUIRED:spark-process:slice -->

## P596: only fire uses the heat kernel → smoke and bodies on fire from the same kernel, each a row in the effects scene
- type: story (the K1 group)
- needed by: "something including fire and smoke, and maybe some bodies colliding, being on fire" (the PO, 2026-11-03, #795)
- value proven by: he plays both and says whether they look like different effects from fire (A5). One bench.md row per effect from three 5 s report lines
- depends on: P595 played (D21), Q2 (the list), Q7 (one turn or two). Q14 (what "being on fire" means: this card reads it as bodies that trail flames in one heat field, the team's reading). Bodies on fire use the rain's falling bodies until P598 exists. Size S
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787)
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P597: no water and only 40 Python particles → water seen from the side, a spring surface that bodies drop into with splash droplets, on a C particle kernel
- type: story (K4 with K2)
- needed by: "and maybe water" (the PO, 2026-11-03, #795)
- value proven by: he plays it and gives his words. One bench.md row: fps, step ms and draw ms, and the particle count the scene holds at 24 fps against today's 40 particles at 2.27 ms
- depends on: P595 played (D21), Q2 (which water), Q11 (formulas or copied code: the spring method has no licence, so formulas only). Size S
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787)
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P598: no two bodies in the engine touch → bodies that collide (the team's reading, if Q3 says round bodies: a few hundred circles in a box, on a uniform grid with substeps), and the burning bodies of P596 on them
- type: story (K5)
- needed by: "maybe some bodies colliding, being on fire" (the PO, 2026-11-03, #795)
- value proven by: he plays it and gives his words. One bench.md row with the step ms for 300 circles. A Mac test shows no circle passes through another in a 60 s run at 2,000 px/s² (A7, a bar the team sets: his only word on bodies is "colliding")
- depends on: Q3 (what "bodies colliding" means, then c1, c2 or c3, and so its overlap with P592 and D16), Q11 (port with notice or write from the method). P595 played (D21). Size S to M
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787)
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P599: the HUD's text costs about 11 ms a frame in every game → the text drawn once into a buffer when it changes and blitted each frame, at about 0.4 ms
- type: story (found on the way, F1: the team's proposal, outside P594's scope, filed only on the PO's yes to Q10)
- needed by: no words of the PO. The team's proposal (the tech lead, TL-4, F1): a cached HUD grows an effect's room from about 15.3 to 18.2 ms to about 25.5 to 28.7 ms (★C4 (the room depends on covers and the HUD)) and cuts every game's HUD cost. His words go here only after his yes to Q10
- value proven by: bench.md rows of the rain and two games before and after: the HUD ms in the report line drops from 10.6 to 10.9 ms to under 1 ms, fps the same or higher, and he sees the same text
- depends on: Q10 (before P595, after it, or not now). Size S
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): ask the decider. It is outside P594's scope, so not a sub-issue of #795 by default
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## Changes to existing cards (proposals, none applied)
- P583 #784: if Q5 picks d1, "The first effects ... exist in the s3lcd fork" becomes "in the engine module (D17), from P594's kernels", and its slice 0 `.S` probe moves to engine/port/s3/. Its done-when (RENT uses them, fps at most 2 below) stays. If Q9 picks h2 or h3, it reads P594's blended numbers first.
- P587 #788: if Q5 picks d1, its files become "the frame and its DMA send, drawing and blits", without "effects", and its "Needed by" drops P583.
- P593 #794 is Done. No change.
- P592 #793: if Q3 picks c1, a note: P598's uniform grid in engine/core/ is the broad phase the rigid solver can reuse, and the circle solver stays an effects mode (TL-2). If Q3 picks c2, P598 depends on P592.
- P594 #795: its "Done when" names the ten effects once Q2 is answered.

## Board actions
<!-- Each action, taken or pending, with its D. e.g. `- move the item to Discovery · pending` -->
- file P595 to P599 as sub-issues of #795, Slice pixel-games, stage Idea · pending, needs a D that names items.md <!-- REQUIRED:board-actions -->
- apply the changes to #784, #788, #793 and #795 above · pending, needs a D
- comment on #795 with the brief's link and set Waiting on the PO (Q1) · pending
