# The tech lead: feasibility and direction

Written 2026-11-05 by the same Fable agent that wrote the other two lenses (no independent review). Lens: Feasibility (FE), and "does it fit the technical direction?" (DI). Paths are relative to the root of the firebeetle-games-p638 worktree. Submodules: engine/ is xmejkal/pixel-engine, engine/driver/ is xmejkal/s3lcd.

## Findings

- FE-1 · How a frame is composed today, in order: TftOut.draw sets tracking off, fills the background and paints the still picture (lcd.py:176-183), sets tracking on, then Game.draw (lcd.py:186) runs paint, fx.draw, hud, draw_over (gfx.py:375-394), then show() (lcd.py:188). The scene's paint is where C and Python draws meet (fire.py:194-200, burning.py:126-128). · E the lines named · supports only: the product.
- FE-2 · The frame is one RGB565 buffer. In "double" mode it lives in PSRAM outside MicroPython's heap (FRAME_PSRAM_CAPS, frame.c:27, :117), and show() copies the marked tiles into an internal buffer and sends them (frame.h:19-24). The driver owns the pixels, the tile marks and the send. · E engine/driver/src/frame.c:27, :117. frame.h:19-24, :38-58 · supports only: the product.
- FE-3 · The C core is driver-free: fx_fire_draw and fx_fire_blend take a uint16_t *panel and a palette (fx_fire.h, the two signatures). The binding is not: it includes s3lcd.h, requires s3lcd_type and reads tft->frame_buffer (binding.c:16-21, :285-289). fx_fire.c includes the driver's blend565.h for the blend (fx_fire.c:3). · E the lines named · supports only: the product.
- FE-4 · A C draw today covers the whole panel and marks all tiles: frame_dirty_all after fx_fire_blend or fx_fire_draw (binding.c:303-307) and after fx_balls_draw (:469-470). frame_dirty(frame, x0, y0, x1, y1) exists for a rect (frame.h:62-72). So a rect-bounded C draw needs a new loop bound in the kernel and one call change in the binding, not a driver change. · E the lines named · supports only: the product. "Not a driver change" is H until written.
- FE-5 · The blend already composes over whatever the frame holds: fx_fire_blend reads out[..] and writes alpha_blend_565(fg, out, a), and skips alpha 0 (fx_fire.c:294-298, :310-312). So a C blend layer drawn after a Python layer stacks correctly today. An opaque C draw (fx_fire_draw, fx_balls_draw with bg) does not: it overwrites. · E the lines named · supports only: the product.
- FE-6 · Cost per layer, from P612. A full-panel blend of a lit fire: 7.78 ms a frame (run110). The arithmetic P612 used: 55 ns a PSRAM write, 34 ns a read, 76,800 px a panel. One opaque full-panel write pass: about 4.2 ms (H). One read-and-write pass: about 6.8 ms (H). A rect of a figure, say 32 x 64 px, is 2,048 px: about 0.2 ms a pass (H, the same arithmetic). · E docs/discovery/2026-11-05-p612-frame-time/README.md:12, :70. bench.md:214 · supports only: a benchmark and arithmetic. Caveat: the fire's blend skips cold cells, so its 7.78 ms is for flappy's trail, not a full fire (bench.md:454 gives 11.5 to 13.3 ms for a full fire in picture mode).
- FE-7 · An off-screen layer buffer (option C in the brief) costs one more full-panel read-and-write pass at composite time, about 6.8 ms (H, FE-6), and 153,600 B of PSRAM a full layer. PSRAM free after deinit: 6,747,500 B (bench.md:212). Memory is not the limit, the pass is. · E bench.md:212. H the arithmetic · supports only: a benchmark and arithmetic.
- FE-8 · The Mac tests of the core call it through ctypes with clang (engine/tests/, engine/README.md:20-24). A rect parameter on fx_fire_blend keeps them: the test passes the full rect. · E engine/README.md:20-24 · supports only: the product.
- DI-1 · Direction: "C steps and paints, Python decides" (engine-walkthrough.md:18). A layer list in Python that calls C and Python draws in order keeps it: Python decides the order, C paints its layer. A compositor in C that holds the list would move a decision into C. · E docs/engine-walkthrough.md:18 · supports only: a document, the stated rule.
- DI-2 · The PO's split (#853 comment): driver, the frame and its pixels. C core, effect layers and compositing kernels. Binding, the Python API. Python, the layer list and Python-drawn layers. Today the kernel and the frame meet in the binding (FE-3), which is this split already, with one leak: fx_fire.c includes the driver's blend565.h. · E engine/core/fx_fire.c:3 · supports only: the product.
- DI-3 · Industry names that fit each part, with their sources: the order model is the painter's algorithm (Wikipedia, read 2026-11-05: "from the farthest to the closest object"). A layer's number is Godot's z_index ("A node with a higher Z index will display in front of others", class_canvasitem.html) or Unity's Order in Layer ("lower values render behind higher values"). The composite step is source-over (W3C compositing-1, "co = αs x Cs + αb x Cb x (1 – αs)"). The render order by stage is Unity's RenderQueue (Background, Geometry, Transparent, Overlay). · E the URLs in po-assistant.md EX-4 to EX-7 · supports only: documents.
- DI-4 · Swaps each part allows: the driver's PSRAM frame for an internal "dma" frame (frame.h:20) with the same C API. The blend kernel for P583's PIE kernel behind the same C name (P612 README:79-80). A Python layer for a C layer with the same draw(cv) call. The Python list for a list sorted by z_index without touching the layers. · E frame.h:20-24. P612 README:79-80 · supports only: the product and a document. The Python swaps are H until written.

## What I could not check, and why

- The ms of a second full-panel blend in the burning scene: needs the board.
- Whether a rect-bounded fx_fire_blend costs less than the full one by the rect's share: the loop walks columns of the field, so a rect in panel space maps to a cell range. Not written.
- Whether the "double" frame's copy into outgoing shrinks with fewer marked tiles: show() returns after the copy (bench.md:186), so fewer tiles should shorten it (H).

## Questions for the decider

- Q3 · Does the layer list belong to pixel-engine's Python side (a module beside plugins.py that the engine ships), or to pixel-games? · decides: which repository holds it and tests it.
- Q5 · Does fx_fire.c keep including the driver's blend565.h, or does the blend move into the core with the driver including it? · decides: the dependency direction between core and driver.

## Searches

none: the six URLs in po-assistant.md were fetched directly.
