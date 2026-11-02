# Proposed items
<!-- Filing needs the decider's yes to this list: a D in brief.md that names items.md. One block per item; copy the
block for more. needed by: the decider's words, quoted. value proven by: a proof the decider can read.
status: proposed, or filed D<n>.
e.g. `- needed by: "I want to know what we should build next" (Lena, 2026-10-06)` -->

Nothing is filed. Numbers P567 upward are the next free ones in xmejkal/spark (the newest issue is P566 #770; read with `gh issue list -R xmejkal/spark --state all --limit 6` on 2026-11-02). The pixel-games repository holds no issues and no issue form; the cards live in xmejkal/spark, whose labels are epic, story, task, chore, spike. Titles follow the PO's card style "P<n>: <problem> → <outcome>". The Slice field of the sibling cards (#766, #769) did not come back from `gh issue view --json projectItems`, so every item asks the decider for its slice. Dependencies are the tech lead's reading of the code (council/tech-lead.md TL-16), proposed. The order below is the facilitator's proposal; the PO orders Ready.

## P567: nobody has measured what the new art costs on the board → one probe session: PSRAM-destination blits, a partly off-screen blit, a picture draw through Python, the pool against the heap, the file system, one body update in Python; a table in bench.md
- type: spike <!-- REQUIRED:item-type -->
- needed by: "great physics like movement and well animated sprites" (the PO, 2026-11-02, #769); the tech lead's Q-g: size the per-game budget from measurement or leave the calculated bounds <!-- REQUIRED:needed-by -->
- value proven by: a bench.md table with the six numbers (★C5, ★C6, ★C13 gaps), each measured, replacing "—" in risks-and-tests.md Budgets <!-- REQUIRED:value-proven-by -->
- depends on: — (the board on USB; no driver card) <!-- REQUIRED:depends-on -->
- status: proposed <!-- REQUIRED:item-status -->
- label (the repository's type label): spike <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P565 #769 <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one (the pixel-games slice was not read) <!-- REQUIRED:spark-process:slice -->

## P568: a theme is a belief until one game carries it → one game, one theme pass (a palette, a backdrop, one sprite with 3 to 4 frames, one death cue, a painted title and over card), played blind by the PO, fps logged before and after
- type: story (slice 0; the test of A1, A2, A3, A9)
- needed by: "I want it to be shoking and cool and beautiful" (the PO, 2026-11-02, #769)
- value proven by: his words in bench.md naming what the game is about without being told, and the `time` line's fps not below the same game's fps before the pass (the proposed pass lines of A1 to A3, pending Q1)
- depends on: P567 for sizing (optional); Q6 names the game; a static-backdrop game needs no driver card, a scrolling game waits for P556 #760
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P565 #769
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P569: ten games share one generic title and game-over shell → a painted title and over card per game, lettering baked, 3 to 6 frames inside the 1.5 s title and 4 to 6 inside the 900 ms over window
- type: story
- needed by: "each one is a wild, beautiful indie game with its own theme" (#769 title, the PO's card)
- value proven by: ten cards on the board, and the over-screen paint time in the `time` log below today's 33 to 54 ms box (bench.md:163)
- depends on: — (no driver card; ★C11)
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P565 #769
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P570: movement is plain Euler with no feel → a game-feel pack in Python: coyote time and jump buffer, hitstop of 2 to 3 frames, a 3 to 5 frame death shake, squash and stretch by frame choice, damped springs for secondary parts
- type: story
- needed by: "great physics like movement" (the PO, 2026-11-02, #769)
- value proven by: his verdict per game in bench.md; the body-update loop time from P567 under the A5 pass line
- depends on: — (tech-lead.md PHYS-5: no driver card); sub-pixel motion later with P558 #762
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P565 #769
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P571: the picture pool is sized by its first call and grows only by a hard reset → one oversize reserve in pictures.py, so adding a game's art needs no reset
- type: chore
- needed by: the tech lead's Q-f (TL-9); every restyle step adds art
- value proven by: copy a new .bin, soft reset, the game draws it, no "the pool is smaller: reset the board" (s3lcd.c:2927-2949)
- depends on: —
- status: proposed
- label (the repository's type label): chore
- parent (the epic, as a sub-issue): P565 #769
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P572: art/paint.py's main() hard-codes three games in 1,452 lines → a data table per game (an index), so a fourth game is a row, not an edit of main()
- type: chore (a refactor before the per-game art)
- needed by: "prettyfy all the games" (the PO, 2026-11-02): ten games through one pipeline (★C9, TL-12)
- value proven by: the same 56 .bin files byte for byte after the refactor (seed 562), and a fourth game added as one table entry
- depends on: —; before P573 and P574
- status: proposed
- label (the repository's type label): chore
- parent (the epic, as a sub-issue): P565 #769
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P573: the four static-backdrop games (snake, stack, gravpong, cube) are flat or without a theme → each in the chosen look with its own theme
- type: story (one card per game may follow, as #769 says "cards for each game come from that plan")
- needed by: "each one is a wild, beautiful indie game with its own theme" (#769)
- value proven by: his verdict per game; fps per game not below its own pre-slice fps in the `time` log
- depends on: P568's verdict and Q2 to Q4; P572; P554 #758 helps (a kept background) but is not required (TL-16a)
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P565 #769
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P574: the six scrolling games (flappy, runner, cave, road, tunnel, starfire) are capped by the full send → each in the chosen look with its own theme, within the P556 fps
- type: story (one card per game may follow)
- needed by: "each one is a wild, beautiful indie game with its own theme" (#769); "flappy is a bit stucky" (the PO, P564)
- value proven by: fps per game not below the P556 numbers (flappy 20 to 22, runner 21 to 24) or its own pre-slice fps; his verdict
- depends on: P556 #760 merged (the overlap; #769 says "starts after P556"); P572; parallax depth wants P557 #761; sprite counts want P555 #759 and P554 #758 (TL-16)
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P565 #769
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P575: art/PROMPTS.md describes a converter and an art/source/ folder that do not exist → either the importer (if Q7 opens the generated route) or the page rewritten to the pipeline that runs
- type: chore
- needed by: the brief's open question "art method"; ★C10 (PO-3, TL-13)
- value proven by: PROMPTS.md names only code that exists, or `art/source/` plus an importer that writes a .bin the board draws
- depends on: Q7 (the art method), and the PO's yes to any paid run (D1)
- status: proposed
- label (the repository's type label): chore
- parent (the epic, as a sub-issue): P565 #769
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P576: the ten games have no shared world → one city, one day: a sky colour script across the D14 cycle and one skyline layer reused by flappy, runner, stack and road (only if Q2 picks option W)
- type: story
- needed by: "it can even be about some controversial political or social topic" (the PO, 2026-11-02); the art-direction lens's opinion for W (H)
- value proven by: the ten title cards in cycle order as stills, dawn to night; the shared layer's bytes counted once in the pool
- depends on: Q2 = W; P569; P572
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P565 #769
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

## P577: no chosen theme has been checked for originality → one search per chosen premise, a finding with sources
- type: spike
- needed by: #769's note "each game gets an original theme, so none stays a copy of a known game"; A8
- value proven by: a table of premise, verb, search query, result, with URLs and dates; each theme passes or gets its alt
- depends on: Q2 to Q4 (the chosen themes)
- status: proposed
- label (the repository's type label): spike
- parent (the epic, as a sub-issue): P565 #769
- slice (one Slice option of the board, or "ask the decider for a new one"): ask the decider for a new one

Found on the way, outside this epic (proposed as separate cards, parent to be named by the decider):
- P578: a tap inside the 900 ms game-over lock is silently ignored → the press is kept and fires when the lock ends, or the lock shows (user.md USER-4) · label: story · parent: — (ask the decider) · depends on: —
- P579: snake turns right only, so a left turn is three taps and up to about 0.5 s → a second control or a tap-and-hold turn (user.md USER-12) · label: story · parent: — (ask the decider) · depends on: Q5 (may a rule change) · caveat: the PO's account (Q15) first; this may be the game's intended rule

## Board actions
<!-- Each action, taken or pending, with its D. e.g. `- move the item to Discovery · pending` -->
- move #769 to Discovery · taken under D1 (its Status read Discovery on 2026-11-02, `gh issue view 769 --json projectItems`) <!-- REQUIRED:board-actions -->
- file P567 to P577 as sub-issues of #769, and P578, P579 with the parent he names · pending (a D that names items.md)
- comment on #769 with the brief's path and the Q1 question · pending
- set "Waiting on" the PO and "Waiting since" the day Q1 is asked · pending
- a Miro frame for this discovery, linked from #769 · pending
