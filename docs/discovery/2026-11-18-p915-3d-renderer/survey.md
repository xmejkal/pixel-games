# P915: 3D and 2.5D rendering for very small computers, and how it could fit the game box (a survey)

Basic research before a product discovery, written 2026-11-18. It holds facts, standard names and options. It holds no design and no decision. Nothing here was run on a board. Each claim has a tag: `read` (I opened the page and it says so), `snippet` (a search result only) or `own` (my knowledge, no source read). `S12` points to the source list at the end. `repo` means a file of this repository, read in this worktree (pixel-games `aa35f88`, pixel-engine `1005249`). "First survey" is the P902 driving survey on branch `p902-driving-simulator-survey`. I do not repeat it.

The PO asked: are there embedded driving simulators, are there really simple 3D engines to extend or copy ideas from, and what could a 3D or 2.5D renderer be on the S3 and later the P4, as an MVP that moves cube and tunnel onto it. His words are on the P915 card.

## Summary

1. Tiny 3D engines exist and several are free to copy: small3dlib and raycastlib (CC0), Jet (MIT), esp32_3d_engine (MIT), PortableGL (MIT), TinyGL (zlib-like), a3d (Apache-2.0), Pico3D (MIT) [S1-S10 read].
2. a3d is the only one with numbers on an ESP32-S3 with an SPI ST7789 at 240 x 320: 32.2 fps on a 4,672-triangle animated model, two worker tasks, and 19.5 ms for the render alone [S9 read].
3. Games prove the class of chip can draw a full 3D picture: a Wipeout clone at 60 fps on an S3 at 480 x 320 (interlaced, two cores, no source) [S16 read]. Doom at about 20 fps at 320 x 240 on the first ESP32 [S13 read, rate S33 snippet]. Quake at 20 to 25 fps on the P4 at 512 x 300 [S14 read].
4. Today the box draws its four "3D" games with lines, filled rectangles and polygons, projected in Python. Paint takes 15 to 53 ms of a 40 ms frame (section 0).
5. The wire is a hard floor: a full 153,600-byte frame takes 31.0 ms at the box's real 40 MHz SPI clock, so about 32 fps at most. 80 MHz left the panel dark (section 0, section 5).
6. Memory fits only in bands: one 16-bit z-buffer for 320 x 240 is 153,600 bytes, the same as a frame. A 40-row band needs 25,600 bytes for colour and as much for depth (section 3).
7. 2.5D methods are far cheaper than triangles: raycasting, Doom sectors, a voxel height map, Mode 7, scaled sprites. They share projection (`F / z`), sprite scaling and span filling with a true 3D renderer (section 4).
8. The S3 has a single-precision FPU, 128-bit PIE vector instructions and two cores. The P4 adds a pixel accelerator that scales, mirrors, blends, fills and turns in 90 degree steps only (section 5).
9. The repository already has the shape a renderer needs: a plain C99 core with a Python twin (`games/engine/README.md`), and a Mac path through ctypes (`tools/render_scene.py`) (section 6).

## What a first basic strategy and a later good strategy could be, per part (options, not decisions)

| Part | Basic first | Good later |
| --- | --- | --- |
| Primitives | the driver's own line, rectangle and convex polygon calls, as today | one C call that draws a whole list of polygons into the frame or a band |
| Projection | float, one pinhole `F / z`, as in all four games | a full model-view-projection matrix; fixed point where it pays |
| Hidden surfaces | painter's sort by depth (Starfire does it today for its rocks) | 16-bit z-buffer in internal-RAM bands, or span buffer; front-to-back for 2.5D |
| Shading | flat colour with depth fade (`shade`) | Gouraud per vertex |
| Texture | none | affine with subdivision, then perspective-correct every N pixels |
| Frame | the box's whole frame in PSRAM with "double" send | bands of 32 to 40 rows in internal RAM, sent one by one |
| Cores | everything on the MicroPython core | a C worker on the second core, two bands or two interlaced fields |
| Scene | Python hands a list of draw calls | a scene of meshes and a camera, held in C |
| 2.5D | pseudo-3D road and tunnel rings, as today | raycast, sector, voxel and Mode 7 as strategies behind the same camera and sprite interface |
| Display | SPI at the real 40 MHz | a faster clock if the panel allows it, or on the P4 MIPI-DSI plus the pixel accelerator |

## Short answer to the first question

Yes, both exist. Driving: the first survey found esp32s3-arcade-3d (an OutRun-style game on an S3) and the simulators are all GPL. Tiny 3D engines: at least eight below, five of them under licenses an MIT project may copy. Licar (CC0) is a 3D stunt racing game by the author of small3dlib that "runs with less than 1 MB of RAM" and "avoids floating point" [S12 read]. The three most worth a closer look:

1. **small3dlib** (CC0, C99, integer only). It lets you pick the strategy at compile time: no z-buffer, full or reduced z-buffer, or triangle sorting. Perspective correction none, full or every N pixels. That is "a basic one first, a good one later" in one header [S1 read]. Licar and a ported demo run on it.
2. **a3d** (Apache-2.0, C++17 header-only). It renders in horizontal strips into small buffers, so it needs no full frame, and it publishes S3 and P4 frame times [S9 read].
3. **Jet** (MIT, C++17). Painter's sort or z-buffer, affine or perspective-correct texturing, flat, Gouraud, Phong or wireframe per material, and up to 100k triangles a second on an S3 [S7 read]. It leaves the display send to the application, which fits our driver.

Raycastlib (CC0) is the fourth to read, for the tunnel and any corridor game [S2 read].

## 0. What the box draws today

Answer first. All four games make the 3D look in Python: they project points with a pinhole formula and call the display driver's C routines one primitive at a time. The repository's C engine has no drawing code for them: `engine/core/world.c` only steps falling bodies and `fx_fire.c` and `fx_balls.c` draw effects (repo). The driver (`engine/driver/src/s3lcd.c`) offers `line` (Bresenham-style, `fast_hline` and `fast_vline`), `fill_rect`, `fill_polygon` (called from `games/lcd.py:153`), `blit_buffer` with a colour key and an alpha blend (`blend565.h`) (repo). The Python canvas turns game coordinates (320 x 240) into panel coordinates (240 x 320) per call (`games/lcd.py:79-100, 155-184`).

| Game | How the picture is made | Cost on the board | What limits it |
| --- | --- | --- | --- |
| Tunnel (`games/world3d.py:15-106`) | Wireframe. A ring is 4 corners projected by `F / z` (F = 150) and 4 `cv.line` calls. About 9 dim rings, 2 gap rings (thick near), 3 ship lines: about 45 to 65 lines a frame (my count). The 4 edges are drawn once. No fill, no hidden-surface step, rings are in depth order. | fps 22 to 23, paint 27.7 to 39.6 ms, step 0.5 to 1.3 ms (`bench.md:1305`, run of 2026-11-11). Older: 13 to 17 fps while it sent many windows (`bench.md:189-190`) | Python calls to `line`, and lines mark many 16 px tiles, so `windows_max` is 4 and a whole frame goes out |
| Road (`games/world3d.py:109-226`) | Pseudo-3D, Lou Gorenfeld's method [first survey S7]. 36 bands of 4 px from row 88: stripe parity from `int(K / t + odo) % 2`, half-width `t * 0.8 + 3`, a bend by a quadratic. Each band is 3 to 5 `fill` calls. Trees (10 pairs) and cars are scaled rectangles. About 200 fill calls a frame (my count). No lines, no polygons. | fps 21 and 12 (second interval, cause unknown), paint 34.4 to 53.0 ms (`bench.md:1306-1315`); frames of 116 to 127 ms in P733 (`bench.md:744`) | Python-side fill calls; the slowest game |
| Starfire (`games/space3d.py:29-149`) | Flat 3D. 40 stars, each two projections and one line (a streak from `z` to `z + 0.25`). Up to 4 rocks, each a hexagon turned in 2D, 12 lines, sorted far first (a painter's sort, `space3d.py:128`). No matrix, no z-buffer. | fps 24, paint 21.3 to 27.0 ms (`bench.md:1307`) | up to about 90 lines a frame from Python |
| CubeTiming as SMILE (`games/space3d.py:168-220, 263-552`) | A true 8-corner cube: yaw, then a fixed tilt (0.6 rad), then `F / (z + D)` (F = 200, D = 5). `Housing.update` projects 10 points into lists made once. A face is visible when its turned normal is toward the eye, so back-face culling replaces a z-buffer. Visible faces are `cv.poly` quads in 3 ink shades, edges `cv.line`. Painted pictures (lens, walkers, light) are blitted with a colour key. | About 27 lines a frame (`games/lcd.py:156-157`). Old wire cube, before SMILE: fps 24, paint 15.7 to 20.5 ms (`bench.md:1308`, table dated 2026-11-11). SMILE itself: 22 fps in the PO's play, paint "not measured" (`bench.md:1617-1618`) | Python projection and per-primitive calls; the art blits |

What limits the frame rate (repo):
- The pace is `FRAME_MS = 40`, so 25 fps at most (`games/app.py:67`). The box shows 21 to 24 fps (`docs/overview.md:102-103`).
- The wire: a full frame is 31.0 ms at "the real 40 MHz" (`bench.md:86`). The code sets 60 MHz, which the driver divides to a real 40 MHz (`bench.md:35`). At 80 MHz the panel stayed dark (`bench.md:40`).
- With the "double" frame, `show()` copies the changed windows in about 3.4 ms and returns, so the send runs under the next paint (`bench.md:188`, `games/lcd.py:10-11`). Past 4 windows a whole frame is sent (`games/lcd.py:39-43`). The frame is then paint plus 3.4 ms, with a 31 ms send behind it, so a paint over about 37 ms makes the frame late.
- The Python paint is the other limit: the games call C once per primitive. Tunnel and Road paint 28 to 53 ms. Other C parts show the pattern that works: one call per frame (Rain at 0.22 ms in C against 28 ms in Python, `README.md` via `docs/overview.md:251`).
- Memory: a frame in PSRAM costs 4.25 ms more to blit than in internal RAM (`bench.md:216`). The largest internal DMA block is 188,416 bytes, and 31,744 bytes while "double" runs (`bench.md:63, 188`).

Primitives a shared renderer would have to offer so cube and tunnel move onto it (my list from the code above):
- A pinhole projection of 3D points to screen with a centre and `F`, and the near-plane guard (Tunnel `NEAR = 1`, Starfire drops `z < 0.2`).
- A world turn: yaw and a fixed tilt for the cube. Tunnel and Starfire need none.
- A clipped line with a colour, and a depth fade of the colour (`gfx.shade`).
- A filled convex polygon with a flat colour and an optional alpha (the cube's faces and the lens light).
- A face visibility test (the cube) and a far-to-near draw order (Starfire's rocks, SMILE's walkers).
- A clip rectangle (`AREA`), kept as a state of the canvas.
- Rectangle fills, scaled with depth, for Road's bands, trees and cars, and the colour-key blit for pictures. These already exist in the canvas.

## 1. Existing software renderers small enough for a microcontroller

Answer first. Eight candidates are small and open. Only a3d gives S3 numbers. None of small3dlib, raycastlib, TinyGL, PortableGL or micro-gl states a speed on a named microcontroller on the pages I read.

| Project | What | Language | License, quoted | May an MIT project copy it? | Number format and features | Memory | Measured speed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| small3dlib [S1 read] | "single header" rasteriser by drummyfish; ports for Pokitto, Gamebuino META, ESPboy demos | C99 | "Everything in this repository is CC0 1.0" plus "a waiver of all other IP rights" | yes | "only 32bit integer math", fixed point; perspective none, full or per N pixels; z-buffer none, full or reduced, or triangle sorting; near-plane cull, push or clip; per-pixel callback | no heap; sizes not stated | none stated; lists Pokitto 48 MHz with 36 kB RAM |
| raycastlib [S2 read] | raycaster for floor and ceiling of variable height, textures, shearing to look up and down | C99 | "Everything is CC0 1.0 (public domain ...)" plus a waiver "including patents" | yes | "only integer math (32bit)"; fixed point | no heap; no figure | none stated |
| TinyGL [S3 read] | "a Small, Free and Fast Subset of OpenGL" by Fabrice Bellard | C | "Zlib-like licence for easy integration in commercial designs (read the LICENCE file)" | yes with its notice (LICENCE file not opened) | "32 bit float only arithmetic"; 16-bit z-buffer, 16-bit RGB output; textures with perspective correction; Gouraud; "about 40 kB" of code on x86 | no RAM figure | none; "a lot faster than Mesa" |
| PortableGL [S4 read] | OpenGL 3.x-ish in one header | C99 | "PortableGL is licensed under the MIT License (MIT)"; its clipping code is TinyGL's, "also under the MIT License" | yes | shaders are C functions; no z-buffer statement on the page | not stated | none; not aimed at microcontrollers on the page |
| tinyrenderer [S5 read] | a course, "Software rendering in 500 lines of bare C++" | C++ | LICENSE.txt: "This software is provided 'as-is' ...", "Copyright Dmitry V. Sokolov" (it reads as zlib; the file names no license) | yes with the notice, my reading | line drawing to shadow mapping; float | n/a | none |
| micro-gl [S6 read] | "Headers Only C++11 CPU Vector Graphics. no std-lib, no FPU" | C++11 | "custom open source semi-permissive license": derivative work and usage "should be credited to the project and the author" | unclear: not a standard license, so no | fixed (`Q` numbers) or float; triangles, 2D sampling; "can render 3d geometries" | zero heap allocations | none |
| Jet [S7 read, first survey S12] | "tiny, dependency-free, fixed-function 3D rasteriser" | C++17 | "Jet is distributed under the MIT License." | yes | integer in the hot path; optional z-buffer or painter's sort (per object or per triangle); affine and perspective-correct; flat, Gouraud, Phong, wireframe per material; half-width and interlaced field buffers; sprites composited at scan-out | no RAM figure; example colour buffer 320 x 240 RGB565 = 153,600 B (derived) | "up to 100k tris/sec" on an ESP32-S3, rasterised triangles over render time, scan-out left out |
| esp32_3d_engine [S8 read] | scene graph, camera, lighting; ST7789 over SPI on an S3, EK79007 MIPI-DSI on a P4 | C++ (ESP-IDF 5.4.1 or later) | "MIT" | yes | float (`glm`); painter's algorithm, no z-buffer; Sutherland-Hodgman clipping; per-face directional light | PSRAM allocator, double frame buffer; no figures | none on the page |
| a3d [S9 read] | header-only low-poly renderer with skeletal animation, a tile binner and a software rasteriser | C++17 | "Apache-2.0" | yes with its license and notices kept; the copied files stay Apache-2.0 (own, not legal advice) | float; Gouraud; optional z-buffer; RGB565 textures; clipped, binned, filled | strips of `tileHeight` 40 into small per-worker buffers, no full frame; FOX model decode buffer 18,888 B internal plus 41,992 B PSRAM | S3 ST7789, 240 x 320, 2 workers: FOX (1,728 vertices) 19.5 ms render, 32.2 fps on the panel; CESIUMMAN (4,672 triangles in the benchmark) 41.8 ms, 19.2 fps on the panel. P4 at 360 MHz, 2 workers: FOX 7.6 ms. C6 (no FPU) FOX 265.6 ms |
| Pico3D [S10 read] | open-world 3D game engine for the PicoSystem (RP2040), a master's thesis | not stated (C++ file names) | "MIT license" | yes | the second RP2040 core is the rasteriser; distance and frustum culling; fixed or float not stated | world of 12 x 12 chunks, 50 NPCs and 50 zombies | none |
| Thumby Color engine (repo `docs/discovery/2026-11-16-p844-engine-plan/survey-b-small-game-engines.md`) | 2D and 3D engine for MicroPython on an RP2350, mesh nodes in C | C | GPL-3.0 | no | node tree drawn by C into double-buffered 16-bit buffers | 128 x 128 screen | not read |

Notes:
- The a3d rows: FOX and CESIUMMAN are a3d's two test models. The page's table says 4,672 triangles for the benchmark model [S9 read]. The off-screen render time (19.5 ms) and the on-panel total (31.1 ms, from 32.2 fps) differ by about 11.6 ms. That gap is the send and its wait (my inference. The two numbers are measured in different modes).
- Not found on pages I read: any RP2040 or ESP32 speed for small3dlib or raycastlib. LovyanGFX or TFT_eSPI 3D parts (not searched). Arduboy and PicoSystem 3D demos beyond small3dlib's "experimental" Arduboy support [S1] and Pico3D [S10].
- First survey: esp32s3-arcade-3d (no license shown) and Jet. Not repeated.

## 2. Existing 3D and driving games on such hardware

Answer first. A true 3D racer at 60 fps on an S3 exists but has no source. The open ones use raycasting or a small integer 3D library, and run at 18 to 35 fps on 48 to 160 MHz chips at low resolution.

| Game | Method | License | Hardware and rate, as the source states |
| --- | --- | --- | --- |
| Licar [S12 read] | true 3D, small3dlib and tinyphysicsengine, "avoids floating point" | "CC0" code and media | Linux; "runs with less than 1 MB of RAM"; designed for embedded devices without a GPU; no frame rate on the page |
| Anarch [S11 read] | raycasting on a grid (raycastlib), several floor and ceiling levels, "not a BSP engine" | "CC0 1.0 ... + a waiver of all other IP rights (including patents)" | Pokitto 48 MHz, 110 x 88: target 35 (overclocked) or 22 fps; Gamebuino Meta 48 MHz, 80 x 64: 18 fps; ESPboy 160 MHz, 128 x 128: 22 fps; binary 180 to 416 KB. These are "target FPS", not measured results |
| esp32-doom [S13 read] | PrBoom port, software renderer | Doom "released by iD software in 1999 under the Gnu GPL"; Espressif's changes "Apache license, version 2.0" | ESP32 with 4 MiB PSRAM; frame rate not on the page; a forum post says about 20 fps at 320 x 240 [S33 snippet] |
| Doom in Retro-Go on an Arduino Nano ESP32 (S3) [S18 read, rate snippet] | PrBoom build | not stated | 320 x 240; the article gives no number; a search result says about 34 fps [S33 snippet] |
| Doom on the P4 [S15 read] | Doom at 320 x 200 scaled by the PPA to a 1024 x 600 MIPI-DSI panel | not stated | CPU scale-and-blit "about 24 ms per frame" capped it near 20 fps; PPA scale plus flip about 9 ms, a steady 30 fps; Doom's own 35 Hz tick is the ceiling |
| esp32-quake [S14 read] | Quake 1 on quake-generic | no license file; "based on the Quake sources released by Id Software" (GPL, own knowledge) | ESP32-P4-Function-EV-Board; 512 x 300 upscaled to 1024 x 600 at 20 to 25 fps |
| Wipeout clone [S16 read] | custom polygon engine, interlaced fields, two cores each doing one half | none; the author "is considering" an open license | ESP32-S3, 8 MB PSRAM, 480 x 320, "60 frames per second" |
| Jet megatextures demo [S17 read] | Jet with 5.01 MB of 8-bit textures in a 16 MB PSRAM | not stated | ESP32-S3; no frame rate on the page |
| Pico3D [S10 read] | open world, second core is the rasteriser | MIT | RP2040 PicoSystem; no frame rate |
| esp32s3-arcade-3d | first survey | no license | first survey |

Notes: Tomb Raider (OpenLara, BSD-2-Clause) is said to run at about 30 fps on a P4 with PPA upscaling [S33 snippet]. The OpenLara page I opened names no platform and no rate [S34 read]. I found no Playdate or Game Boy Advance racing game with open source in this pass (not searched). Quake on an S3: not found.

## 3. Architectures of a renderer for 320 x 240 on this class of chip

Answer first. The standard pipeline is the same everywhere. The choices that matter here are the hidden-surface method (memory) and whether the frame is built whole or in bands (memory and the send).

**The pipeline** (`own`, since Khronos's "Rendering Pipeline Overview" returned HTTP 403 and was not read [S35]): model transform, view transform, projection, clipping, perspective divide, viewport transform, rasterisation, per-pixel steps (depth test, blend). PortableGL calls itself "OpenGL 3.x-ish", with C functions as shaders [S4 read], and small3dlib offers a pixel callback [S1 read]. The tinyrenderer course goes "from line drawing to shadow mapping" [S5 read].

| Choice | Standard name and source | Memory and cost here | Fit |
| --- | --- | --- | --- |
| Painter's sort | painter's algorithm: sort, paint far to near. It "prioritizes the efficient use of memory but at the expense of higher processing power"; cannot resolve cyclic overlap or piercing polygons [S24 read] | no extra buffer; every polygon is fully filled, overdraw included | Starfire, Tunnel and the cube today; esp32_3d_engine; Jet and small3dlib offer it |
| Z-buffer | z-buffer or depth buffer; the "traditional 16-bit buffer" can z-fight; precision is not linear after the perspective divide [S23 read] | 320 x 240 x 2 B = 153,600 B, the size of the frame (my arithmetic); 40-row band 25,600 B | small3dlib (full or reduced), Jet, a3d, TinyGL (16-bit) |
| Scanline and span buffer | scanline rendering, span buffering; "the first Quake engine" used it for the world, with moving objects z-buffered over it [S27 read]. Its intermediate tables "can exceed the size of a Z-buffer for a complex scene" [S27 read] | row-sized tables; more code | none of the small engines; Doom's visplanes are the 2.5D form |
| BSP, front to back | Doom: `R_RenderBSPNode` sorts subsectors front to back; walls as columns, floors as visplane spans; fixed 16.16; visplanes capped at 128 [S19 read] | the tree is data made offline | levels; see section 4 |
| Portals | rooms joined by openings; no page read (`own`) | per room | not covered |
| Fixed against float | S3 has a "single-precision floating-point unit (FPU)" [S28 read]. small3dlib is integer only [S1 read], TinyGL float only [S3 read], Jet integer in the hot path [S7 read]. a3d notes a chip with no FPU turns each float into a library call (C6: 265.6 ms against 19.5 ms on an S3, different clocks) [S9 read] | on S3 and P4 floats are fine for transforms; integer loops are the common choice for the inner loop (my reading of S1, S7) | float first, fixed later where a profile says so |
| Shading | flat, Gouraud (a3d, Jet, TinyGL), Phong (Jet) [S3, S7, S9 read] | Gouraud adds colour interpolation per pixel | flat first |
| Texturing | affine is fastest and distorts; perspective-correct "more expensive"; the PlayStation split triangles; Quake corrected "only every 16 pixels" [S25 read]. small3dlib: none, full or per N pixels [S1 read] | a per-pixel divide, or one per N pixels | none first |
| Tiles or bands | tiled rendering: "subdividing a computer graphics image by a regular grid", 16 x 16 and 32 x 32 popular, "the modest amount of on-chip memory" [S26 read]. a3d: strips of 40 rows into small buffers, then `sendTile` [S9 read]. Jet: "parallel rendering bands" [S7 read] | 40 rows x 320 x 2 B = 25,600 B colour (+25,600 B depth); fits internal RAM | the way to get a z-buffer without PSRAM |
| Double buffer and dirty rectangles | the box has both: "double" frame (`games/lcd.py:36-38`) and 16 px dirty tiles with at most 4 windows (`games/lcd.py:5-7, 43`) (repo) | in 3D almost every tile changes, so a whole frame goes out (`bench.md:1305-1308`, `windows_max` 4) | keep "double"; dirty tiles buy little here |

Where the time goes on a microcontroller (my reading of the numbers above, not a profile): fill rate (pixels written, with overdraw) against transform (vertices) against the send. On the box today the Python call cost per primitive and the 31 ms wire are the two limits (section 0). a3d shows a case where the render is 19.5 ms and the panel total is 31.1 ms [S9 read].

## 4. 2.5D methods as cheaper strategies

Answer first. Each trades camera freedom for cost. All are column or span loops, so they share the loops with a polygon renderer more than the maths.

| Method (standard name) | What the camera can do | Classic game | Source |
| --- | --- | --- | --- |
| Raycasting (grid, DDA) | turn and move on a plane; floor, ceiling and walls of one height in the basic form. raycastlib adds floors and ceilings of other heights and "shearing for looking up and down" | Wolfenstein 3D (`own`); Anarch is a modern one | first survey S10; [S2 read] |
| Sector and BSP engine | walk through rooms of any height with a BSP front-to-back order; walls as columns, floors and ceilings as visplane spans; sprites last, far to near; no room over room (`own`) | Doom | [S19 read] |
| Voxel height map ("Voxel Space") | fly with position, angle, height and horizon; one height per map position, so no overhangs; draws vertical lines column by column; "might be still patented in some countries"; the maps are 1024 x 1024 one-byte | Comanche | [S20 read]; MIT code, maps excluded |
| Mode 7 | a flat floor with a perspective step: a matrix per scanline, `lambda = a_y / h`; move and turn only; horizon fixed in the first lesson. SNES has hardware; the GBA does it with a per-line register write | F-Zero and Super Mario Kart (`own`) | [S21 read] |
| Scaled sprites ("Super Scaler") | the game is a list of sprites scaled by distance | Hang-On, Space Harrier, OutRun | [S22 read] |
| Pseudo-3D road | the camera follows a road; curves by accumulated shift per line; sprites scaled by `1 / z` | OutRun | first survey S7 |

What could share code with a true 3D renderer (my inference from the code in section 0 and the sources):
- Projection: `k = F / z` appears in Starfire (`project`), Tunnel (`corners`), the cube and Road (`K / t`). One function serves all.
- Sprite and rectangle scaling by depth: Road's trees and cars, Starfire's rocks, Doom's things [S19], OutRun's scaled sprites [S22].
- Span filling: Road's bands, Doom's `R_DrawSpan` [S19], Mode 7's per-line transform [S21], a polygon rasteriser's rows. A fast horizontal fill is the shared inner loop.
- A far-to-near or near-to-far order: Starfire, Doom's things, the voxel y-buffer [S20].
- Not shared: the raycaster's DDA grid walk and the voxel loop's height-map lookups are their own loops.

## 5. What the chips offer

Answer first. The S3 can do float transforms and, on two cores, a few tens of thousands of triangles a second. The wire at the box's 40 MHz clock caps the picture at about 32 fps. The P4 is about 2.3 to 2.6 times faster on a3d's two models and adds 2D blits, but no triangle hardware and no free arbitrary rotation.

**ESP32-S3** (Espressif datasheet and technical reference manual [S28 read], via Espressif's documentation search):
- Two Xtensa LX7 cores up to 240 MHz, five-stage pipeline, a 128-bit data bus, a "single precision floating point unit (FPU)", CoreMark 1329.92 for two cores at 240 MHz.
- PIE vector instructions: 128-bit registers; 8, 16 and 32-bit vector operations (add, subtract, multiply, accumulate, shift, compare). Loads that move data while they compute; "non-aligned 128-bit vector data". Saturation.
- Memory: 512 KB SRAM, 384 KB ROM. Data cache 32 or 64 KB. PSRAM maximum clock 80 MHz in the datasheet table, and octal PSRAM at 120 MHz is "an experimental feature" with a crash risk on temperature change [S29 read].
- GP-SPI2 and 3 as master: "clock frequency up to 80 MHz". One DMA transfer of 1 to 32 KB, longer by segments. A GP-SPI DMA transfer from PSRAM shares bandwidth with the PSRAM bus [S29 read].
- Repo: PIE fills 5.8 times and copies 9.8 times faster than LVGL's plain C, "measured by Espressif" (`docs/discovery/2026-11-03-engine/brief.md:72`, not re-opened by me). The second core is free of MicroPython if the task touches no Python object (same file).

SPI send time for one frame, 153,600 bytes = 1,228,800 bits on one data line (my arithmetic, and the box measured 31.0 ms):

| SPI clock | Time | Frame rate by the send alone |
| --- | --- | --- |
| 20 MHz | 61.4 ms | 16 fps |
| 40 MHz (the box's real clock, `bench.md:86`) | 30.7 ms | 32 fps |
| 60 MHz | 20.5 ms | 49 fps |
| 80 MHz (the S3 maximum; the box's panel went dark, `bench.md:40`) | 15.4 ms | 65 fps |

A band send is the same bytes with a start cost per window: about 1.9 ms per strip beyond its bytes in an early version (`bench.md:79`). The driver also has an 8-bit parallel (i80) bus file (`engine/driver/src/s3lcd_i80_bus.c`). The box's panel is SPI. A parallel panel is not measured.

**ESP32-P4**:
- First survey S27 (read): dual-core RISC-V up to 400 MHz (360 MHz default on v1.3), a single-precision FPU, 768 KB L2. No 3D hardware.
- Pixel-processing accelerator (PPA) [S30 read]: scale, rotate, mirror (SRM) and blend (BLEND). Rotation "0°, 90°, 180°, 270°" only. Scaling: v1.3's manual says a 4-bit integer and 8-bit fraction, the current manual says 8-bit integer and 4-bit fraction. ESP-IDF truncates to steps of 1/16 and says the scaler is bilinear. Blend mixes two same-size layers by alpha, fills, and has colour-key ranges. Formats include RGB565 and RGB888. Blocks move through 2D-DMA.
- MIPI-DSI output at 24-bit RGB888; 768 KB on-chip SRAM. External PSRAM as cache [S30 read]. PSRAM "HEX 200MHz" appears in an Espressif benchmark config [S30 read].
- Numbers: Doom scale plus flip 9 ms against 24 ms on the CPU [S15 read]. Quake 512 x 300 at 20 to 25 fps [S14 read]. A3d FOX 7.6 ms against 19.5 ms on the S3 [S9 read].

What each feature buys a renderer (all my inference):
- FPU: the model-view-projection in float, no fixed-point code in the first version.
- PIE: fast flat span fills and sprite copies (the repo's 5.8 and 9.8 times). Less so a per-pixel z-test, which I have not seen a number for.
- Two cores: one core for Python and the next frame's logic, one for a C render task. Or two bands or two interlaced fields as in the Wipeout clone [S16] and a3d's workers [S9].
- PSRAM: room for a whole frame and a z-buffer, but slower per access than internal RAM (repo `bench.md:216`), so a z-buffer in 32-to-40-row bands in internal RAM is the safer fit.
- PPA: render at 160 x 120 or 320 x 200 and scale up (Doom, Quake). Blend a sprite layer. Fill. It cannot turn a sprite by any angle (first survey, S30). It helps the P4's own frame, not the SPI wire of a 320 x 240 SPI panel.

## 6. How a renderer could fit this repository's engine (options, not a design)

Answer first. The repository already asks for the shape: a plain C99 core with no MicroPython header, a binding, and a Python reference twin that the Mac tests compare. The Mac path exists too.

What is in place (repo):
- The rule of two versions: a reference in plain Python and a fast C or viper twin behind one interface, chosen once at boot by `accel.Chooser`; `tests/test_twins.py` runs both on the same input (`games/engine/README.md:25-36`).
- The core is plain C99 so clang builds it on the Mac and the board build compiles the same files. The binding `engine/binding.c` checks arguments; "C steps and paints, Python decides" (`docs/overview.md:83-85`, `docs/engine-walkthrough.md` section 0).
- Precedent for C drawing into the frame: `fx_fire_blend` blends the heat field straight into the s3lcd frame (`bench.md:368`).
- `tools/render_scene.py` runs `lcd.TftOut.draw` on `tests/drawing_tft.DrawingTft`, a stand-in for the driver's `fill`, `line`, `fill_polygon` and `blit_buffer`, with the C engines through ctypes. The golden net pins each game's frames by hashes (`docs/overview.md:215-217`).

Options for what the game hands the renderer each frame:

| Option | The game gives | The renderer does | Fits |
| --- | --- | --- | --- |
| A. Draw-call list | a flat array of points and primitive records (line, polygon, rect, sprite), already projected or not | clip, sort, draw in one call | smallest step; Python keeps the projection or hands points |
| B. Scene and camera | meshes with transforms, a camera, lights | transform, cull, sort or z-test, draw; keeps state in C | what Jet, esp32_3d_engine and a3d offer; larger |
| C. Strategies behind a camera | a camera and a list of sprites; the strategy is pseudo-3D road, raycast or polygons | the strategy draws | fits section 4's shared parts |

Where the 2D pictures and effects sit: the order in `lcd.TftOut.draw` is background (`paint_static`), the game's `paint`, then the overlay (`games/lcd.py:221-238`). A 3D layer would sit in the game's `paint`. Sprites (`pictures.draw`, a colour-key blit) and particles come after it, so a z-sort between a sprite and a mesh is a new need. The HUD is a kept strip (`Canvas.keep`). The heat field and particles blend into the frame afterwards.

A smallest first step that shows a result on the Mac before any board (one option):
- Move Tunnel's ring (4 corners and 4 lines, section 0) into a C function with the same inputs and the same pixel result, called through ctypes by `tools/render_scene.py`, with the Python version as the reference twin. Success would be an unchanged golden hash for tunnel, since the frame is the same picture.
- Next option: the cube's `Housing.update` (10 projections and a visibility test) in C, handing the quads to `fill_polygon`.
- Open: whether `DrawingTft.line` reproduces the driver's line pixel for pixel (not checked), so a C twin that calls its own line routine could differ on the Mac or on the board.

## Not found, not read

- Khronos's pipeline page (HTTP 403). A Pokitto forum post on small3dlib (certificate error). The `LICENCE` file of TinyGL and the full micro-gl terms.
- Speeds on a named chip for small3dlib, raycastlib, PortableGL, micro-gl and esp32_3d_engine. Jet's RAM use. Any P4 PSRAM bandwidth number. Any z-test timing with PIE.
- LovyanGFX and TFT_eSPI 3D examples. Arduboy and PicoSystem 3D demos other than the ones named. Playdate or Game Boy Advance racing sources. Quake on an S3.
- Portal rendering has no source. The Wolfenstein 3D, F-Zero and Super Mario Kart rows are `own`.
- Two searches' snippets (Doom at 20 and 34 fps) are not opened pages.

## Sources

Searches used: 4 web searches (Licar, Quake on S3 or P4, Pico3D, Doom on an S3) and 4 queries to Espressif's documentation search. `S1` to `S35`:

| Id | Page and URL | Tag |
| --- | --- | --- |
| S1 | small3dlib README, drummyfish: https://gitlab.com/drummyfish/small3dlib/-/raw/master/README.md (project page "Miloslav Číž / small3dlib · GitLab") | read |
| S2 | raycastlib README: https://gitlab.com/drummyfish/raycastlib/-/raw/master/README.md | read |
| S3 | "TinyGL : a Small, Free and Fast Subset of OpenGL": https://bellard.org/TinyGL/ | read |
| S4 | "GitHub - rswinkle/PortableGL": https://github.com/rswinkle/PortableGL | read |
| S5 | "GitHub - ssloy/tinyrenderer": https://github.com/ssloy/tinyrenderer and https://raw.githubusercontent.com/ssloy/tinyrenderer/master/LICENSE.txt | read |
| S6 | "GitHub - micro-gl/micro-gl": https://github.com/micro-gl/micro-gl and https://raw.githubusercontent.com/micro-gl/micro-gl/master/LICENSE.MD | read |
| S7 | "GitHub - CubeCoders/Jet": https://github.com/CubeCoders/Jet | read |
| S8 | "andresragot/esp32_3d_engine v1.0.1 - ESP Component Registry": https://components.espressif.com/components/andresragot/esp32_3d_engine/versions/1.0.1/readme | read |
| S9 | "0015/a3d v0.9.4 - ESP Component Registry": https://components.espressif.com/components/0015/a3d/versions/0.9.4/readme | read |
| S10 | "GitHub - bernhardstrobl/Pico3D": https://github.com/bernhardstrobl/Pico3D | read |
| S11 | Anarch README: https://gitlab.com/drummyfish/Anarch/-/raw/master/README.md | read |
| S12 | "Licar", Libregamewiki: https://libregamewiki.org/Licar | read |
| S13 | "GitHub - espressif/esp32-doom": https://github.com/espressif/esp32-doom | read |
| S14 | "GitHub - espressif/esp32-quake": https://github.com/espressif/esp32-quake | read |
| S15 | "DOOM at 30 FPS - letting the hardware scaler do the work", Hackaday.io: https://hackaday.io/project/206493-claude-sonnet-plays-doom-on-scintix-p4/log/250260-doom-at-30-fps-letting-the-hardware-scaler-do-the-work | read |
| S16 | "Wipeout Clone Runs Native On ESP32-S3", Hackaday, 2026-04-29: https://hackaday.com/2026/04/29/wipeout-clone-runs-native-on-esp32-s3/ | read |
| S17 | "Jet Megatextures Demo For ESP32-S3", Hackaday, 2026-09-28: https://hackaday.com/2026/09/28/jet-megatextures-demo-for-esp32-s3/ | read |
| S18 | "Your Arduino Nano ESP32 can run Doom", Arduino Blog: https://blog.arduino.cc/2023/09/12/your-arduino-nano-es32-can-run-doom/ | read |
| S19 | "Doom engine code review", Fabien Sanglard: https://fabiensanglard.net/doomIphone/doomClassicRenderer.php | read |
| S20 | "VoxelSpace", s-macke: https://github.com/s-macke/VoxelSpace | read |
| S21 | "Tonc: Mode 7 Part 1": https://www.coranac.com/tonc/text/mode7.htm | read |
| S22 | "List of Sega arcade system boards" (the "Sega Super Scaler" page redirects to it): https://en.wikipedia.org/wiki/Sega_Super_Scaler | read (first 100,000 characters) |
| S23 | "Z-buffering": https://en.wikipedia.org/wiki/Z-buffering | read |
| S24 | "Painter's algorithm": https://en.wikipedia.org/wiki/Painter%27s_algorithm | read |
| S25 | "Texture mapping": https://en.wikipedia.org/wiki/Texture_mapping | read |
| S26 | "Tiled rendering": https://en.wikipedia.org/wiki/Tiled_rendering | read |
| S27 | "Scanline rendering": https://en.wikipedia.org/wiki/Scanline_rendering | read |
| S28 | ESP32-S3 datasheet https://documentation.espressif.com/esp32-s3_datasheet_en.html and technical reference manual https://documentation.espressif.com/esp32-s3_technical_reference_manual_en.html (PIE, SPI, memory) | read through the documentation search |
| S29 | ESP-IDF "SPI Flash and External SPI RAM Configuration": https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/flash_psram_config.html and "SPI Master Driver": https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/spi_master.html | read through the documentation search |
| S30 | ESP32-P4 technical reference manual chapter "Pixel-Processing Accelerator (PPA)" https://documentation.espressif.com/esp32-p4_technical_reference_manual_en.html, datasheet https://documentation.espressif.com/esp32-p4_datasheet_en.html, ESP-IDF PPA API https://docs.espressif.com/projects/esp-idf/en/latest/esp32p4/api-reference/peripherals/ppa.html, "Espressif's HMI Smart Displays" https://www.espressif.com/en/solutions/hmi/smart-displays, esp-nn https://components.espressif.com/components/espressif/esp-nn | read through the documentation search |
| S33 | Search "Doom ESP32-S3 port fps 320x240": https://esp32.com/viewtopic.php?p=10985 ("ESP32-Doom available") and Retro-Go results; search "Quake port ESP32-P4": OpenLara result https://www.remio.ai/ko/post/esp32-p4-tomb-raider-port-runs-playably-without-a-gpu-ko | snippet |
| S34 | "GitHub - XProger/OpenLara": https://github.com/XProger/OpenLara | read (no platform or rate on the page) |
| S35 | Khronos "Rendering Pipeline Overview": https://wikis.khronos.org/opengl/Rendering_Pipeline_Overview | not read (HTTP 403) |
