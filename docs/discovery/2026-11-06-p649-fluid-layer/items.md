# Proposed items
<!-- Filing needs the decider's yes to this list: a D in brief.md that names items.md. -->

## Field renderer: the fire's draw and blend paint any byte field
- type: story, under P609 #812 (the engine) <!-- REQUIRED:item-type -->
- needed by: "for the physicxs to be reusable. or graphics? both?" (the PO, 2026-11-06, spark #871) <!-- REQUIRED:needed-by -->
- value proven by: the fire tests pass unchanged, and a second field is painted by the same call <!-- REQUIRED:value-proven-by -->
- depends on: — <!-- REQUIRED:depends-on -->
- status: proposed <!-- REQUIRED:item-status -->

## Flow: a velocity field the fire reads, with a legacy and a light strategy
- type: story, under P609 #812; replaces P650 #872's prototype path
- needed by: "Wait, so it should probably slso be generalized as fluids right?" (the PO, 2026-11-06, spark #871)
- value proven by: legacy keeps the fire tests byte for byte; light matches P647's picked clip (bend 1, wander 512)
- depends on: the field renderer
- status: proposed

## Smoke: a second quantity on the same flow and renderer
- type: story, under P609 #812
- needed by: "Cause we'll wanmt other effects too, like qter, or other materials" (the PO, 2026-11-06, spark #871)
- value proven by: one Mac clip of fire and smoke from one flow, and one board run with ms and fps against Q1's line
- depends on: the flow
- status: proposed

## Board actions
- post the finding's short version on spark #871 · pending a D <!-- REQUIRED:board-actions -->
- fold P650 #872 into the flow story, or keep it as the first strategy · pending Q3
- file the three stories above as sub-issues of P609 #812 · pending a D that names items.md
