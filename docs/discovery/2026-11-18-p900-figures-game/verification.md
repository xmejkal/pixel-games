# Verification
<!-- One line per ★ claim in brief.md; rejected claims stay. refuter: holds · partly · refuted · could not open, with
the line it read, verbatim. result: reproduced · not reproduced · rejected. keep: the words any summary of the claim
must carry (phrases separated by ;), or none; keep comes last on the line.
e.g. `- ★C3 · STATUS.md:84 · refuter: partly — "Shown on the C6, assumed for the S3" · reproduced how: re-read STATUS.md:84 · result: reproduced · keep: assumed for the S3` -->
- ★C1 · art/export.py:20-27, art/sets/rescue.py:172,181,591-593 · refuter: holds — "FIG_H = 26  # px from the soles to the helmet's top, standing" · reproduced how: re-read the lines: `FIG_H = 26`, `SIZES = {"run": (26, 30), ...}`, `ImageOps.mirror(img)` · result: reproduced · keep: read in the painter <!-- REQUIRED:claims -->
- ★C2 · games/pictures.py:42-52 · refuter: partly — "a pool a soft reset kept smaller (ValueError): a bytearray instead"; the sentence is changed · reproduced how: re-read `block`, and `ls -l games/packs` printed runner.pak 739216 · result: reproduced · keep: none
- ★C3 · calculated from ★C1 · refuter: partly — the arithmetic reproduces; the cut holds none of the cycles of his example mission; the sentence is changed · reproduced how: re-ran the arithmetic in Python: 511488 + 394272 + 504096 + 504096 = 1913952 · result: reproduced · keep: calculated
- ★C4 · bench.md:214 · refuter: partly — "Memory after deinit"; the 8 MB is at bench.md:43; the sentence is changed · reproduced how: re-read the row: "PSRAM free 6747500.00 B", "a 4,000,000 B bytearray allocates" · result: reproduced · keep: an older build
- ★C5 · games/app.py:332-341 · refuter: partly — "game.stick = self.action_map.actions if self.action_map.stick else None": a game can read them; the sentence is changed · reproduced how: re-read: `switched = actions.pick.pressed and len(self.games) > 1`, `self.knob.poll(now, actions.turn)` · result: reproduced · keep: none
- ★C6 · games/rescue.py:566, games/meteors.py:380 · refuter: partly — "In run 1 the push meant as up read `JOY_X` high, against run 2's clear hold"; the caveat is changed · reproduced how: grep for `stick.x` and `stick.y` in both files: two hits, both x · result: reproduced · keep: two games read
- ★C7 · bench.md:58 · refuter: holds — "USB dropped after about 5.5 s of steady hold" · reproduced how: re-read: "USB dropped after about 5.5 s of steady hold", "V1.1 and earlier" · result: reproduced · keep: V1.1 and earlier
- ★C8 · logs/run-p846-baseline-a.log:84-96 · refuter: partly — no line says game over: "avg rescue static 8.5 paint 16.4 fx 0.9 hud 0.8 over 0.0 title 0.0"; the sentence is changed · reproduced how: re-read: "load 638 ms", "paint 33.0 ... fps 18", "paint 26.8 ... fps 19", "title 133" · result: reproduced · keep: nobody steered
- ★C9 · games/rescue.py:179,182,212,834, games/meteors.py:249 · refuter: partly — "return (x if right else -x) * RUN_POSES // STRIDE_PX % RUN_POSES": Meteors takes x; the sentence is changed · reproduced how: re-read lines 179, 212 and 834 of rescue.py and 249 of meteors.py; line 182 read earlier in the session · result: reproduced · keep: two of fifteen games read
- ★C10 · tests/test_engine_boundary.py:24-31 · refuter: holds — "DIRECTION = {"__init__": (), "signals": (), ..." · reproduced how: re-read `DIRECTION` and `BUILT_IN` · result: reproduced · keep: until the plan's stages 3c and 4
- ★C11 · calculated from games/rescue.py:39 · refuter: holds as arithmetic — a figure that stays whole on the screen has about 1.1 s; the sentence is changed · reproduced how: re-ran: 56 * 96 / 26 = 206.8 px a second, 320 / 206.8 = 1.55 s · result: reproduced · keep: calculated

## Agree / split
<!-- Where the lenses and the refuter agree, and where they split; each split becomes a question.
e.g. `- Split: Feasibility says a day, Risks says a week · Q4` -->
- Agree: the tech lead, the PO assistant and the user lens each name the art memory as the first blocker, with 1.9 MB, 1.95 MB and 1.08 MB for different cuts. The brief uses the tech lead's cut, which was recomputed here <!-- REQUIRED:agree-split -->
- Agree: the tech lead and the user lens both find no free input for the switch (★C5)
- Split: the PO assistant says the board spike comes before any design, and the facilitator puts a Mac picture before it · Q2
- Split: the tools survey offers poses painted on the board in C, and the tech lead finds no measured hot spot that asks for C · Q4
- Split: the user lens computes about 220 px a second for the run, and the brief computes 207, from 96/26 and not from a factor of 4 · Q3

- Split: the refuter finds the pass line of A1 invented in two of its three parts, and the facilitator had proposed it · Q1, with a new line that names its source for each part
- Split: the refuter doubts that size answers what he said after play (C20, C21), and the brief's jobs rest on his words about size · Q12
- Split: the facilitator proposed the stick's up and down first, and the refuter and the user lens point to a button, as the genre does, and to the climb in his example · Q5, with three more options
- The refuter alone puts A2's test early, because it needs no 96 px art. The PO assistant puts it second, after the first mission (PO-20) · the third item in items.md, P905
- Second pass: the refuter corrected its own grouping of two quotes in C20, and the brief now names each quote's game and date
- Split: D13's words describe one motion, which fits today's pool, and the test needs a pack bigger than the pool · settled by D21, whose question named the 2 MB pack
