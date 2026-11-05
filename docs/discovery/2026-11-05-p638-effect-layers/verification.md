# Verification
<!-- One line per ★ claim in brief.md; rejected claims stay. refuter: holds · partly · refuted · could not open, with
the line it read, verbatim. result: reproduced · not reproduced · rejected. keep: the words any summary of the claim
must carry (phrases separated by ;), or none; keep comes last on the line.
e.g. `- ★C3 · STATUS.md:84 · refuter: partly — "Shown on the C6, assumed for the S3" · reproduced how: re-read STATUS.md:84 · result: reproduced · keep: assumed for the S3` -->
- ★C1 · engine/binding.c:282-308, :469-470; engine/core/fx_balls.c:332-337 · refuter: partly — "fx_fire_blend(&self->fire, tft->frame_buffer, palette.buf, alpha.buf); ... frame_dirty_all(&tft->frame);" · reproduced how: the refuter read the three ranges; the caveat "no C layer can go over another" was too strong and is now "an opaque C layer cannot, a blended one can" · result: reproduced · keep: a blended one can <!-- REQUIRED:claims -->
- ★C2 · games/gfx.py:385-394, games/burning.py:126-128, games/plugins.py:9-10 · refuter: holds — "self.paint(cv) ... self.fx.draw(cv) ... self.hud(cv) ... self.draw_over(cv)" · reproduced how: the refuter read the lines · result: reproduced · keep: none
- ★C3 · engine/core/fx_fire.c:294-299, :310-313; engine/driver/src/blend565.h:17-32 · refuter: holds — "if (alpha[h0] != 0) {  // a pixel of alpha 0 keeps what it holds, and skips the blend's cost" · reproduced how: the refuter read the lines · result: reproduced · keep: not zero where nothing burns
- ★C4 · bench.md:429-430, :433, :484 · refuter: partly — "| run90-p608-fire-picture.log | fire, picture (linear blend over the sky) | 23 to 24 | 6.55 to 6.76 ms | 11.51 to 13.32 ms |" · reproduced how: sed -n '429,435p;484p' bench.md, read 2026-11-05; the claim now separates the opaque pass from the lit blend · result: reproduced · keep: one run each
- ★C5 · bench.md:535-537, :552 · refuter: holds — "the free time in this scene is about 14 ms, not 16 ms" · reproduced how: the refuter read the lines · result: reproduced · keep: run116
- ★C6 · bench.md:366, :371, :373, :167 · refuter: holds — "The paint is about 16 ms shorter, because the frame no longer gets a second full-panel pass: the buffer fill and the blit become one blend that skips the clear cells." · reproduced how: the refuter read the lines · result: reproduced · keep: upper bound

## Agree / split
- Agree: all three lenses (one author) say that a swap of two lines in BurningBodies.paint puts flames over bodies today, that a C blend stacks over a Python draw today, and that frame_dirty_all is the harm. <!-- REQUIRED:agree-split -->
- Agree: whether the body stays visible through the flames is the PO's call · Q2
- Split: the tech lead costs a full-panel blend at 7.78 ms (FE-6, the flappy trail), the brief at 11.5 to 13.3 ms (★C4, a lit fire) · Q4
- Split: the PO assistant reads the card's "about 5 ms" as between 4.2 and 6.8 ms (RA-4), the first draft said it was absent from P612; F1 now holds both · no question, a wording fix
- Split, fixed: the lenses' Q3 (where the list lives) and the brief's Q3 (is the pack pixel-engine) were one number for two questions; the list's home is now Q8
