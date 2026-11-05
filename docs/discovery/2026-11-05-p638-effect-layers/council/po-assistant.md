# The PO assistant: existing first, risks and assumptions

Written 2026-11-05 by the same Fable agent that wrote the other two lenses (no independent review). Lenses: Existing first (EX) and Risks and assumptions (RA). Paths are relative to the root of the firebeetle-games-p638 worktree, branch p638-effect-layers.

## Findings

- EX-1 · In the product, the only draw order is the one each scene writes by hand in its paint. BurningBodies draws the field first and the bodies after it. · E games/burning.py:126-128, games/fire.py:194-200 · supports only: the product, what exists.
- EX-2 · plugins.py names the gap: "The render stays the game's: its paint calls each plugin's draw where it wants it, so the order of the layers is open (P638)." · E games/plugins.py:9-10 · supports only: the product's own statement.
- EX-3 · P628's option A already foresaw the C side of this: "Later each painter takes a rect and a blend mode instead of frame_dirty_all (binding.c:307, :470), so two C painters stack." The PO picked C first, then A. · E docs/discovery/2026-11-05-p628-engine-layers/README.md:82-83, :185-187 · supports only: a document, an earlier proposal.
- EX-4 · Outside: Unity orders 2D renderers by "Sorting Layer and Order in Layer" and "renders sublayers in numerical order, so lower values render behind higher values". Its render queue runs Background 1000, then Geometry, AlphaTest 2450, GeometryLast 2500, Transparent 3000 "in back-to-front order", Overlay 4000 "rendered last". · E https://docs.unity.com/en-us/engine/current/manual/unity2d/sprite/sort-sprites/2d-renderer-sorting and https://docs.unity.com/en-us/engine/current/script-reference/unityengine/rendering/renderqueue, both read 2026-11-05 · supports only: a document, what Unity specifies.
- EX-5 · Outside: Godot draws "Canvas items ... in tree order on their canvas layer", with "CanvasItem.z_index" ("A node with a higher Z index will display in front of others") and CanvasLayer, where "Layers with a greater number will be drawn above those with a smaller number" and "CanvasLayers are independent of tree order". · E https://docs.godotengine.org/en/stable/classes/class_canvasitem.html and https://docs.godotengine.org/en/stable/tutorials/2d/canvas_layers.html, read 2026-11-05 · supports only: a document.
- EX-6 · Outside: the W3C compositing spec separates two steps, "Porter-Duff compositing and blending", and defines source-over as "co = αs x Cs + αb x Cb x (1 – αs)". The engine's alpha_blend_565 is this formula with integer alpha and no destination alpha. · E https://www.w3.org/TR/compositing-1/ (Candidate Recommendation Draft, 21 March 2024), read 2026-11-05. engine/driver/src/blend565.h:17-32 · supports only: a document, and the code's formula.
- EX-7 · Outside: the painter's algorithm paints "from the farthest to the closest object" and pays "the cost of having painted invisible areas of distant objects". Our frame already does this: every layer paints over the last. · E https://en.wikipedia.org/wiki/Painter%27s_algorithm, read 2026-11-05 · supports only: a document, a name for what the code does.
- EX-8 · Licences: the s3lcd fork is MIT (engine/driver/LICENSE), pixel-engine is MIT (engine/LICENSE). No option copies code from outside. · E the two files · supports only: the product.
- RA-1 · Blocked now: P639 #854 "Waits for P638's design", and P635 #850 lists "whether it is built on P633's plugins" as open. · E spark #854, #850, read with gh 2026-11-05 · supports only: the backlog.
- RA-2 · Overlap: P583 #784 holds the fire's PIE kernels (fx_fire_step, fx_fire_blend). A layer design that changes fx_fire_blend's signature touches P583's kernel. · E docs/discovery/2026-11-05-p612-frame-time/README.md:80 · supports only: the backlog.
- RA-3 · The belief with the least evidence: that drawing the field after the bodies, with no new C, is what the PO means by "on fire". He has not seen it. The one-pass version hides the body under hot cells (alpha 255 returns fg, blend565.h:23). · H the writer, from the PO's words and blend565.h · supports only: a hypothesis.
- RA-4 · Cost belief: a full-panel blend costs 7.78 ms a frame (run110). A full-panel opaque C write is about 4.2 ms (H: 76,800 px x 55 ns). A read-and-write pass is about 6.8 ms (H: plus 34 ns a read). The card's "about 5 ms a pass" sits between them. · E docs/discovery/2026-11-05-p612-frame-time/README.md:12, :70. bench.md:214 (a full-frame blit costs 4.25 ms more into PSRAM) · supports only: a benchmark of flappy's fire and the arithmetic.
- RA-5 · Pre-mortem (after Klein): six months on, the layer list exists, but every scene still has one full-panel fire draw, because no C draw takes a rect, and the partial send gains nothing in a still scene. A second way to fail: ten layers in a list cost ten calls at 2.60 µs each (negligible, bench.md P589) but ten whole-panel passes (not negligible). · H the writer · supports only: a hypothesis.

## What I could not check, and why

- Unity's "2D rendering order" page with the full priority list: not fetched, budget.
- Whether a second full-panel blend keeps the burning scene within 2 fps: no board run in a discovery.
- What the PO sees as "on fire": only he can say (Q2).

## Questions for the decider

- Q2 · Must the body stay visible through the front flames? · decides: one pass or two, and so A2's cost.
- Q8 · Is the layer list part of pixel-engine's Python side, or of pixel-games? · decides: where the list lives and who tests it.

## Searches

none: six pages fetched by URL (EX-4 to EX-7), each named above with its date. Three fetches were redirects of the Unity URLs.
