# Proposed items
<!-- Filing needs the decider's yes to this list: a D in brief.md that names items.md. One block per item; copy the
block for more. needed by: the decider's words, quoted. value proven by: a proof the decider can read.
status: proposed, or filed D<n>. -->

## P639 slice 0: the burning scene paints the bodies, then the field blended over them (option A)
- type: story, a feel slice (the existing card #854 takes it as its first slice; no new card) <!-- REQUIRED:item-type -->
- needed by: "when somehthing is on fire, it cannot only be around it" (the PO, 2026-11-05, spark #853) <!-- REQUIRED:needed-by -->
- value proven by: the PO plays it on the board and says it looks on fire; the scene's draw ms at 13.5 or less and the fps at 23 or more (run117: 6.40 to 6.44 ms, 24 to 25 fps, `bench.md:570-571`) <!-- REQUIRED:value-proven-by -->
- depends on: Q4 (A or A then B), Q2 (one field or two) <!-- REQUIRED:depends-on -->
- status: proposed <!-- REQUIRED:item-status -->
<!-- EXTEND:item-fields -->

## A scene lists its layers, and the Render stage draws them in order (option B, slice 1)
- type: story
- needed by: "generalize this to adding layers to the effects so that we can intertwine multiple layers" (the PO, 2026-11-05, spark #853)
- value proven by: fire, burning, balls and rain each list their layers with a `layer` number (Godot's `CanvasLayer.layer`, lower behind); the Mac tests hold; run117's draw ms within 0.1 (`bench.md:562-571`)
- depends on: Q4 = B, slice 0 merged
- status: proposed

## A C layer paints a rect with a blend mode and marks only that rect dirty (option B, slice 2)
- type: story (the C half P628 named, `docs/discovery/2026-11-05-p628-engine-layers/README.md:82-83`; shared with P610 blur and P616 balls on fire)
- needed by: "even a python ldrawn layer in between two C layers" (the PO, 2026-11-05, spark #853)
- value proven by: one scene with balls under a Python layer under fire runs on the board (P616's picture), `fx_balls_draw` without its bg fill, `frame_dirty(rect)` in the binding instead of `frame_dirty_all`
- depends on: slice 1, A5 (a scene that wants it), Q5
- status: proposed

## Each part named and placed: the compositing kernel's home, the API per part, the swap list (slice 3)
- type: chore (documentation and one file move)
- needed by: "split it into what belongs where ... industry standards for naming and such" (the PO, 2026-11-05, spark #853 comment)
- value proven by: lesson D of `docs/engine-deep-dives.md` names driver, core, binding and Python with a source per name and what each swaps for; `blend565.h` lives where Q5 says
- depends on: Q5
- status: proposed

## Fix the card's number: "about 5 ms" per full-panel pass → "4 to 7 ms by what the pass does"
- type: chore (a comment on spark #853)
- needed by: the card's own note, "P612 #817 (each full-panel pass through PSRAM costs about 5 ms)" (spark #853 Notes)
- value proven by: the comment cites `bench.md:429-430`, `:484` and `p580-finding.md:15`
- depends on: —
- status: proposed

## Board actions
- none taken: the PO is not reachable (auto mode, 2026-11-05); filing, commenting and the Miro frame wait for his yes to this list <!-- REQUIRED:board-actions -->
