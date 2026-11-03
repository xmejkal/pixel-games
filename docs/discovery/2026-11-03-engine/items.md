# Proposed items
<!-- Filing needs the decider's yes to this list: a D in brief.md that names items.md. One block per item; copy the
block for more. needed by: the decider's words, quoted. value proven by: a proof the decider can read.
status: proposed, or filed D<n>.
e.g. `- needed by: "I want to know what we should build next" (Lena, 2026-10-06)` -->

Nothing is filed. P588 was the next free number in xmejkal/spark (the newest issue was P587 #788, read with `gh issue list --repo xmejkal/spark --state all` on 2026-11-03). The list holds the two spikes that test the riskiest assumptions, the walking skeleton, a solver spike and the next slice. Later slices stay in story-map.md until the PO orders them. Sizes are the synthesis's estimate (H), in working sessions of the AI team: XS is under one session, S is one session, M is more than one. No size was measured.

## P588: nobody knows if the PO's material rules fit a C step that only reports facts → a desk table of his rules from #783, each sorted as "C mechanism", "C fact reported to Python" or "Python reaction or number" under a draft API fixed to four facts, read and marked by him
- type: spike (tests A1 as restated after the refuter, the proposed riskiest, pending Q1). It serves every option, because A, B and C all step in C <!-- REQUIRED:item-type -->
- needed by: "be able to react both ways" (the PO, 2026-11-03, #787), and D3's "the games really can interact with it easily and clearly and readably" (the PO, 2026-11-03) <!-- REQUIRED:needed-by -->
- value proven by: a table in the discovery folder with one row per rule in his two decision comments on #783 (2026-11-03, 08:35 and 08:36 Prague time), each with its sort and his mark, read against A1's pass line (no number in his rules has to live in C, no rule needs a fifth fact, and he disagrees with at most 1 sort, proposed 2026-11-03). The four past feel changes are not the population, because three were AI slices built without his words (★C20) <!-- REQUIRED:value-proven-by -->
- depends on: Q1 (the PO picks the riskiest and sets its pass line), and his time to mark the table. Size XS, desk only, no board <!-- REQUIRED:depends-on -->
- status: proposed <!-- REQUIRED:item-status -->
- label (the repository's type label): spike <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P586 #787 <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games <!-- REQUIRED:spark-process:slice -->

## P589: a C step and a C-to-Python call have no measured cost on the board → one probe session: today's `fall_bodies` timed as the baseline, a C step over 12 bodies, a 16-event drain, one C-to-Python call timed 1,000 times, one timed build and flash, a table in bench.md
- type: spike (tests A2, A3, A8). It serves every option, because A, B and C all step in C
- needed by: "the core of the engine and the various parts of it to be in C and higly optimised" (the PO, 2026-11-03, D3)
- value proven by: a bench.md table with the five numbers, each measured on the board in one session, replacing "—" in risks-and-tests.md Budgets. The baseline (today's `@native` `fall_bodies` per body) gives A2's "against today's `Bodies.step`" its number
- depends on: Q1. The board on USB. It puts new probe C into the image before Q8 (where the engine's C lives) is answered, so the probe C is throwaway. Size S, one session
- status: proposed
- label (the repository's type label): spike
- parent (the epic, as a sub-issue): P586 #787
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P590: RENT's bodies step in Python and allocate 544 B per step → today's `fall_bodies` in C behind the same `Bodies` API, an int event buffer that RENT drains once per frame, a Python twin for the Mac tests
- type: story (slice 0, the walking skeleton). It serves every option: Python still draws each body, which is option A's shape, and it is the first rung of B or C, whose C drawing comes in slice 2 (story-map.md). Q2 says so
- needed by: "now, be able to react on physical events from python maybe, etc." (the PO, 2026-11-03, #787)
- value proven by: RENT plays the same in his words. The Mac tests pass on the twin. `Bodies.step` allocates 0 B in a `gc.mem_alloc()` bracket (544 B today). Pure-play fps at or above 22.09 fps in the `time` line. A landing raised in C starts the dust burst in Python, seen on the panel
- depends on: P588 and P589 passing their lines. Q2 (the architecture), Q3 (the rule), Q4 (the event path), Q8 (where the C lives). The motion.py source on origin/p582-heavy (draft PR #10). Size S to M
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P586 #787
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P591: no small rigid solver is proven for RENT's tip and topple → a host spike in plain C: a two-box tip at the centre of weight and an 11-floor topple, own Box2D-Lite-sized code against a Box2D v3 subset
- type: spike (tests A4, informs Q7)
- needed by: "it doesn't really seem like the real physics for the weight and material it would be" (the PO, 2026-11-03, #783)
- value proven by: a short finding with the two runs' results (rests flat, tips at the centre of weight, no tunnelling at 894 px/s), lines of C and the source licence of each, read against A4's pass line
- depends on: Q7 (which sources to try). Mac only, no board. Size S to M: the own solver is about a thousand lines (H) plus a Box2D v3 subset to compare, so it is testable but not small. A4's pass line "inside one working session" restates this size estimate
- status: proposed
- label (the repository's type label): spike
- parent (the epic, as a sub-issue): P586 #787
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P592: RENT's floors tip and topple only as Python guesses → the rigid tip and topple on the engine's C path, with the step model Q9 picks (a fixed internal step with substeps, today's clamped dt, or swept tests), a tip event, and every feel number passed from Python
- type: story (slice 1, the first user's need on the engine)
- needed by: the PO's material decisions on #783 (2026-11-03): floors "topple as rigid pieces that pivot on their edges"
- value proven by: the PO plays RENT and says whether it is "heavy and natural" in his words. The collapse step in the `time` line against today's 14 to 16 ms. Worst gap against today's 70 ms, which may be paint-bound or gc-bound, so it may not move (★C6, A5)
- depends on: P590, P591. Q5 (RENT's material slice in Python first, or on this path) and Q9 (the fixed step). Size M
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P586 #787
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## Changes to existing cards (proposals, none applied)
- P584 #785: shrinks to one file per game, named numbers and dead-code removal, because `gfx.Game` already is the base class (PO-2). It stays the first move of the Game base into the engine package. The order waits on Q10.
- P587 #788: scope unchanged. If Q8 keeps the engine inside the s3lcd fork, physics becomes one more job file in the split. Its place before or after P590 waits on Q10 (TL-19).
- P582 #783: becomes the engine's first user. Its unmerged motion.py is the source of P590. Whether its material slice lands first in Python or on the C path waits on Q5.
- P585 #786: is built on the engine after P590 and P584. Its flood fill enters the engine with it, by the growth rule (PO-33, PO-34).
- P583 #784: its `fx()` module is the engine's effects module, and the landing event is its first caller. Road's read-back of particle state (world3d.py:182-183) needs a Python flag (TL-5).

## Board actions
<!-- Each action, taken or pending, with its D. e.g. `- move the item to Discovery · pending` -->
- file P588 to P592 as sub-issues of #787, Slice "pixel-games" · pending: needs the PO's yes to this list (a D naming items.md) <!-- REQUIRED:board-actions -->
- apply the changes to #785, #788, #783, #786, #784 · pending: needs the PO's yes
