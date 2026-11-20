# Verification
<!-- One line per ★ claim in brief.md; rejected claims stay. refuter: holds · partly · refuted · could not open, with
the line it read, verbatim. result: reproduced · not reproduced · rejected. keep: the words any summary of the claim
must carry (phrases separated by ;), or none; keep comes last on the line. -->
- ★C1 · engine/core/fx_fire.h:68, :74; fx_fire.c:253-254, :284-285 · refuter: not run yet (paused 2026-11-06) · reproduced how: Claude re-read the signatures and the first lines of both bodies, 2026-11-06 · result: reproduced · keep: byte for byte after a move is untested <!-- REQUIRED:claims -->
- ★C2 · engine/core/fx_fire.c, fx_fire_step · refuter: not run yet · reproduced how: not yet, the lens's reading only · result: not reproduced · keep: the lens's reading; the random draw order is part of the contract
- ★C3 · bench.md:593-594, :608 · refuter: not run yet · reproduced how: Claude re-read run119 (step 7.92 to 8.08 ms, 23 to 24 fps) and run120 (14.51 to 14.84 ms, 23 fps), 2026-11-06 · result: reproduced · keep: one scratch probe; linear mode
- ★C4 · bench.md:647, :655 · refuter: not run yet · reproduced how: Claude re-read both lines, 2026-11-06 · result: reproduced · keep: two runs
- ★C5 · bench.md:294, :608 · refuter: not run yet · reproduced how: Claude re-read 31,744 B and 18,432 B, 2026-11-06; 160 x 120 x 2 = 38,400 by arithmetic · result: reproduced · keep: one firmware image; 38,400 B by arithmetic
- ★C6 · spark #798, #801 · refuter: not run yet · reproduced how: Claude read both bodies with gh, 2026-11-06 · result: reproduced · keep: K6 is not built
- ★C7 · branch p647-motion, engine/core/fx_fire.c and .h · refuter: not run yet · reproduced how: not yet · result: not reproduced · keep: a prototype; cost not measured
- ★C9 · Bridson et al. 2007 · refuter: not run yet · reproduced how: not yet, the paper was not read · result: not reproduced · keep: not read
- ★C10 · council/light.md FE-3, FE-4 · refuter: not run yet · reproduced how: an estimate, nothing to re-run · result: not reproduced · keep: H; never timed on the board

## Agree / split
- Not yet: the refuter has not run, so there is no second view to agree or split with. The lens and Claude agree on ★C1, ★C3 to ★C6 <!-- REQUIRED:agree-split -->
