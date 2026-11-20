# Story map
<!-- Proposed, not applied: this map stays here until the decider confirms it; nothing changes the product's own
map file. -->
**Status:** proposed, not applied <!-- REQUIRED:map-status -->

## Backbone
<!-- The activities, left to right, as the user does them. -->
Paint a field → Move it with a flow → Carry a second quantity → Tune it on clips → Read it on the board <!-- REQUIRED:backbone -->

## Slices
<!-- Walking skeleton first: the thinnest slice that runs end to end. One row per story. -->
| slice | activity | story | job | tag | proof |
| --- | --- | --- | --- | --- | --- |
| 0 walking skeleton <!-- REQUIRED:slices --> | Paint a field | the field renderer: `fx_fire_draw` and `fx_fire_blend` move out as a renderer of any byte field (cells, w, h, palette, alpha, filter), byte for byte | 1 | E ★C1 | tests/test_fire_core.py passes unchanged; the Mac clip is the same bytes |
| 0 walking skeleton | Move it with a flow | the flow: a velocity field the fire's step reads, with a legacy strategy that gives today's bytes and P647's light flow (bend 1, wander 512) as a second strategy | 2 | E ★C2, ★C7 | the byte test holds with legacy; Mac clips of light match P647's page |
| 0 walking skeleton | Carry a second quantity | smoke: a second byte field carried by the same flow, with its own sources and sinks, painted by the same renderer | 1 | H ★C10 | a Mac clip of fire and smoke from one flow; one board run gives ms and fps |
| 1 | Tune it on clips | every flow and smoke number a setting, three clips per round | 2 | E spark #872 | the PO's pick on an artifact page |
| 2 | Move it with a flow | a coarse velocity grid with curl noise or Stam's solver behind the same interface, so flames cross and merge | 1 | H ★C9, ★C10 | a Mac clip, then board ms against the pass line set at Q1 |
