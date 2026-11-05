# The tech lead: feasibility, and the fit with the engine's direction

Written 2026-11-05 by the one discovery agent (Fable 5.1), as one of three reports. Paths are relative to the root of
pixel-games, worktree `firebeetle-games-p638` at `4751ca9`. Every line number comes from a per-file read of that file.

## Findings

- TL-1 · Today one C call paints the whole panel into the driver's frame and marks every tile dirty. `heat_field_draw`
  checks for an `s3lcd` object, demands the panel be `2h x 2w`, then runs `fx_fire_blend` or `fx_fire_draw` and
  `frame_dirty_all(&tft->frame)` · E `engine/binding.c:282-308` · supports only: the product as it is.
- TL-2 · The ball pit's C draw does the same and fills the background first, so it cannot sit over anything · E
  `engine/binding.c:469-470`, `engine/core/fx_balls.c:332-337` (`panel[k] = bg` over every pixel) · supports only: why
  two C layers cannot stack today.
- TL-3 · The order of the layers is the call order inside `Game.draw` and the game's `paint`: `paint`, then the
  particles `fx.draw`, then `hud`, then `draw_over` · E `games/gfx.py:385-394` · and in the burning scene `paint` is the
  fire first, then one `fill` per body · E `games/burning.py:126-128` · supports only: why flames are behind a body.
- TL-4 · P633 left the render open on purpose: "The render stays the game's: its paint calls each plugin's draw where it
  wants it, so the order of the layers is open (P638)" · E `games/plugins.py:9-10` · supports only: that the Render stage
  has no list of its own yet.
- TL-5 · The fire kernels already stack when blended: `fx_fire_blend` reads what the frame holds and skips a pixel whose
  alpha is 0 ("a pixel of alpha 0 keeps what it holds, and skips the blend's cost") · E `engine/core/fx_fire.c:294-299`,
  `:310-313` · supports only: a blended C layer can be drawn after a Python layer with no other change.
- TL-6 · The blend is Porter and Duff's "over" with straight alpha and an opaque frame: `fg * alpha + bg * (255 - alpha)`
  per channel, after a byte swap in and out · E `engine/driver/src/blend565.h:17-32` · and it lives in the driver's fork,
  not in the engine's core · E same file, header comment `:1-8` · supports only: where the compositing kernel sits.
- TL-7 · The frame: PSRAM in "double" mode, copied into an internal `outgoing` buffer at `show()`. the dirty marks are one
  byte per 16 px tile, set by `frame_dirty(x0, y0, x1, y1)`, which every driver draw calls with its rect · E
  `engine/driver/src/frame.h:20-24`, `:40-58`, `:62-73`. `games/lcd.py:38`, `:43` · supports only: that a C kernel could
  mark a rect instead of the whole frame with the function that exists.
- TL-8 · A Python off-screen layer already exists: `Strip` is a panel rectangle with its own pixels, drawn once when its
  key changes and blitted every frame by `blit_buffer`'s memcpy path · E `games/lcd.py:47-62`, `:107-118`;
  `engine/driver/src/s3lcd.c:573-600` (the alpha 255, in-bounds memcpy path) · supports only: a cached layer surface is a
  pattern the code has, not a new idea.
- TL-9 · Cost of one full-panel pass, measured: the opaque nearest draw 4.26 to 4.27 ms, linear 6.41 ms (burning,
  run89) · E `bench.md:429-430` · the linear blend over the sky 11.51 to 13.32 ms (fire picture, run90) · E
  `bench.md:433` · the sky picture's blit 7.3 ms a frame (flappy, run109) · E `bench.md:484` · supports only: these
  scenes, this image, one run each.
- TL-10 · Per-pixel costs behind those: PSRAM write 55 ns/px, read 34 ns/px, alpha compose in C 337.5 ns/px into the
  PSRAM frame (run46) · E `p580-finding.md:15` · so a full-panel write is about 4.2 ms and a read-plus-write pass about
  6.8 ms, before any arithmetic · H arithmetic over 76,800 px · supports only: an estimate.
- TL-11 · The card's "each full-panel pass through PSRAM costs about 5 ms" (P638 notes) is not a sentence in P612's
  finding. the nearest sources are TL-9's 4.26 ms (one opaque write) and TL-10's 55 ns/px · E
  `docs/discovery/2026-11-05-p612-frame-time/README.md:70` (the arithmetic, 92 ns/px for the four-pass background) ·
  supports only: the number is 4 to 7 ms, by what the pass does.
- TL-12 · A second buffer costs a second pass: P603 part 1 drew the fire into a 153,600 B picture buffer and blitted
  it. part 2 blended straight into the frame and the paint fell about 16 ms, "because the frame no longer gets a second
  full-panel pass" · E `bench.md:366`, `:371`, `:373` · supports only: an off-screen layer per effect is the expensive
  design on this board.
- TL-13 · The burning scene's free time is about 14 ms a frame at the 40 ms pace (P635 slice 0, run116) · E
  `bench.md:535`, `:552` · and 12 Python-drawn figures cost about 3.4 ms · E `bench.md:537` · supports only: one more
  blended pass (TL-9's 5 to 7 ms over opaque) fits, two do not.
- TL-14 · Blended fire at the same pace holds the fps: fire picture 23 to 24 fps against 24 to 25 opaque · E
  `bench.md:433`, `:431-432` · supports only: P639's "within 2 fps" is reachable with the blend alone, in the fire
  scene. the burning scene was not run blended.
- TL-15 · Which parts a C kernel touches: `fx_fire_draw` and `fx_fire_blend` take a bare `uint16_t *panel` and know
  nothing of the driver · E `engine/core/fx_fire.h:66-73`. only the binding knows `s3lcd_type` and `frame_dirty_all` ·
  E `engine/binding.c:16`, `:21`, `:285`, `:307` · supports only: the "rect and blend mode" change (P628's own later
  stage, `docs/discovery/2026-11-05-p628-engine-layers/README.md:82-83`) is a binding change plus a rect argument in C.
- TL-16 · The Mac stand-in for the frame is `render.StOut`, and the figures' probe showed a Python painter should call
  the driver, not the canvas wrapper (144 against 18 us a 12 px line) · E `games/render.py:120`, `:133`;
  `bench.md:521`, `:548` · supports only: a Python layer's `draw(cv)` must take whatever `cv` the out gives it.
- TL-17 · Industry names, read today: Godot `CanvasLayer.layer`, "Layer index for draw order. Lower values are drawn
  behind higher values", and the layer "will hold regardless of the CanvasItem.z_index" · E
  https://docs.godotengine.org/en/stable/classes/class_canvaslayer.html, read 2026-11-05 · Godot `z_index`: "A node with
  a higher Z index will display in front of others", items "drawn in tree order on their canvas layer" · E
  https://docs.godotengine.org/en/stable/classes/class_canvasitem.html, read 2026-11-05 · Unity Sorting Layers: "Defines
  the overlay order of Sprites in the 2D system" · E
  https://docs.unity.com/en-us/engine/current/manual/unity-editor/editor-settings-reference/comp-manager-group/class-tag-manager,
  read 2026-11-05 · Bevy `SortedPhaseItem::SortKey`: "The smallest values are drawn first" · E
  https://docs.rs/bevy/latest/bevy/core_pipeline/core_2d/struct.Transparent2d.html, read 2026-11-05 · the painter's
  algorithm: "placing each polygon in order from the farthest to the closest object", "at the cost of having painted
  invisible areas of distant objects" · E https://en.wikipedia.org/wiki/Painter%27s_algorithm, read 2026-11-05 ·
  Porter and Duff 1984, "A over B", premultiplied `C_o = C_a + C_b(1 − α_a)` · E
  https://en.wikipedia.org/wiki/Alpha_compositing, read 2026-11-05 · supports only: the names. none of these pages says
  how its engine stores a layer in memory.
- TL-18 · Direction fit. The engine's rule since P628 and the deep dives: "C steps and paints, Python decides", and the
  effects combine as numbers in the heat field, "the engine blends once, at the end" · E `docs/engine-deep-dives.md:93-94`,
  `:240` · An ordered list that calls kernels in place keeps that rule. per-effect surfaces composited by C would make
  the compositor the place where effects combine instead · H my reading · supports only: the fit, not the value.

## What I could not check

- The burning scene blended (base off, bodies first, fire over them) was never run on the board. TL-14's number is the
  fire scene with its base on, so it has more lit pixels than the burning scene would. the cost is then lower, H (H).
- Whether one field blended over a body reads as "on fire" or as "a body behind flames" is the PO's eye (the user's
  report, U-5), not a measurement.
- SDL's blend-mode page is cited from the deep dives (`docs/engine-deep-dives.md:90-92`), not re-read today.
- The off-screen surface names (render target, `SDL_SetRenderTarget`, Skia `saveLayer`) are model knowledge, H, not read.

## Questions for the decider

- Q4 · Does the compositing kernel (`blend565.h`, the "over") stay in the s3lcd fork or move to pixel-engine's core? ·
  decides: which repository the kernel lives in after P632's split, and who tests it on the Mac.
- Q3 · Flames in front: one field blended over the bodies, or two fields (behind and front)? · decides: zero C work
  against a second `HeatField` and its step cost (TL-9: a second step is about 6 to 8 ms, `bench.md:429`).

## Searches

none (eight page reads, each listed in TL-17 with its date. two misses: Unity's old URL redirected, and
`docs.rs/bevy/latest/bevy/sprite` holds no ordering text).
