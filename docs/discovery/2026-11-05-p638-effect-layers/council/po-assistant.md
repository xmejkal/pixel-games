# The PO assistant: existing first, and risks and assumptions

Written 2026-11-05 by the one discovery agent (Fable 5.1), as one of three reports. Paths are relative to the root of
pixel-games at `4751ca9`. line numbers from per-file reads.

## Findings

- PA-1 · The PO's ask, verbatim: "we'll also need to add fron layer effects, so like when things are on fire, i can
  only see the flames as if from behind it, but when somehthing is on fire, it cannot only be around it. And probably
  ew'll want to generalize this to adding layers to the effects so that we can intertwine multiple layers and even a
  python ldrawn layer in between two C layers etc" · E spark #853 body, read 2026-11-05 with `gh issue view 853` ·
  supports only: his words.
- PA-2 · The PO's placement rule, verbatim: "well, not necessarily the engine, split it into what belongs where, you
  know like something goes to the graphycs , some maybe to the driver or the binding, the python parts,,, lets stick to
  good reusable and changable architecture and industry standards for naming and such" · E spark #853, comment of
  2026-11-05 15:06 UTC · supports only: the Done-when's part-by-job rule.
- PA-3 · The first user is one story, P639: "A burning body or figure shows flames in front of it as well as behind
  it ... The scene keeps its fps within 2" · E spark #854, read 2026-11-05 · and P635's figures that "catch fire" are
  its next · E spark #850 · supports only: two users, both his own scenes. no scene needs "a Python layer between two
  C layers" yet (H: no card names one. P616 balls on fire is Idea, `docs/engine-deep-dives.md:256`).
- PA-4 · Existing in the product: the order already exists as call order (`gfx.py:385-394`, `burning.py:126-128`). a
  blended C layer already composites over what the frame holds (`fx_fire.c:294-299`). a cached Python surface exists
  (`lcd.py:107-118`). What does not exist: a list a scene writes to say the order, a C kernel that paints a rect
  instead of the whole panel, and any C layer that can go over another C layer (`binding.c:307`, `:470`) · E the
  tech lead's TL-1 to TL-8 · supports only: the gap is small for P639 and real for "any order".
- PA-5 · Existing outside, by name only (read today, the tech lead's TL-17): Godot's `CanvasLayer.layer` and
  `z_index`, Unity's Sorting Layers, Bevy's sorted phase items, the painter's algorithm and Porter-Duff's "over".
  All order whole items by one integer or float key and draw back to front. None of them is a library the board can
  run. they lend names and the model, not code · E TL-17 · supports only: naming.
- PA-6 · P628 already proposed the C half of this: "Later each painter takes a rect and a blend mode instead of
  `frame_dirty_all` (`binding.c:307`, `:470`), so two C painters stack" · E
  `docs/discovery/2026-11-05-p628-engine-layers/README.md:82-83` · and the PO picked C then A there · E the parent's
  brief to this agent (the PO's choice is recorded in P628, not re-read here) · supports only: this card continues a
  chosen path.
- PA-7 · Is anyone blocked now? P639 is "Waits for P638's design" · E spark #854 · P635 slices 1 to 3 do not wait on it
  (its figures burn through the field, `bench.md:539`) · supports only: one story waits.
- PA-8 · Overlaps in the backlog: P610 "blur on a region" wants "a new draw on `tft->frame_buffer` with a rect, not
  whole-panel" · E `docs/engine-deep-dives.md:251` · P616 wants "a blend after `fx_balls_draw`" · E `:256` · P629
  wants one C pass over four pictures · E `docs/discovery/2026-11-05-p612-frame-time/README.md:109` · supports only:
  three Idea cards share the "rect and blend mode per kernel" piece.
- PA-9 · Pre-mortem (after Klein), six months on, it failed. Why: (a) every layer became a surface and the frame budget
  went to copying (TL-12's 16 ms lesson). (b) the layer list grew a z number, a sort and a Layer class that one scene
  uses, while the other scenes keep calling draws by hand, so two orders exist. (c) the fire in front hid the body and
  the PO stopped using it, so the feature had one user who left · H my reasoning · supports only: what to guard.

## Riskiest belief, my proposal

A1 (value): "one heat field blended over the body, after the body is painted, reads as 'on fire' to the PO". Least
evidence: nobody has seen it. the PO's own words say the flames must not be "only around it", which a front blend
satisfies in geometry but maybe not in look (the coal body is darker than the flames, `burning.py:35`). Cheapest
test: P639 as a call-order swap with the blend, a Mac PNG through `tools/render_scene.py` first, then the board.

## What I could not check

- The PO's pick in P628 (C then A) is relayed by the parent agent, not re-read in an issue comment.
- Whether a user beyond the PO exists: pixel-games has one player, so every value claim is n = 1.

## Questions for the decider

- Q2 · Which design: the call order alone (A), a layer list that draws in place (B), or surfaces with a compositor
  (C)? · decides: the plan's stages and the C work.
- Q6 · Appetite for the first slice: P639 alone (a day, Python only, H), or the layer list with it? · decides: the
  size of the next card.

## Searches

none.
