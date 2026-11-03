# Proposed items
<!-- Filing needs the decider's yes to this list: a D in brief.md that names items.md. One block per item. Copy the
block for more. needed by: the decider's words, quoted. value proven by: a proof the decider can read.
status: proposed, or filed D<n>. -->

Everything here is proposed, filed only on the PO's yes to this list. Nothing is filed. P595 is the next free number in xmejkal/spark (the newest issue is P594 #795, read with `gh issue list --repo xmejkal/spark --state all --limit 5` on 2026-11-03, E). P595 to P599 were named in this folder before, so the new cards take P600 and P601. Each card follows spark's issue form (.github/ISSUE_TEMPLATE/item.yml: Needed by, Value proven by). Each card is a sub-issue of P594 #795, which sits under the epic P586 #787, Slice pixel-games. One card is one play turn (D10): fire alone, then smoke and bodies on fire, then water and sparks, then colliding bodies, then the rest. Each effect is its own `GAMES` entry, like the rain (D9), and shows its name and its cost in ms on screen (D3, D15). Its kernel sits in engine/core/fx_<name>.c, with fast paths in port/s3/ and one thin binding (D8). Code under MIT, BSD or Apache-2.0 can be ported with its notice in a notices file. EUPL, GPL and code with no licence are ideas only (D14). Each feel card stops at "ready to play" until he played it (engine D21). Sizes are the team's estimate (H), in pull requests: S is one PR, M is two. "Engine D<n>" names a line of docs/discovery/2026-11-03-engine/brief.md, and a bare D<n> a line of this folder's brief.md.

## P595: no effect scene exists and the engine draws no pixel → a fire scene on the board, its heat kernel in plain C in the engine module, drawn by both screen paths and timed, with its cost in ms on screen
- type: story (slice 0, the walking skeleton, a feel slice). It tests A1, the riskiest (D2), with A2 and A9 in the same run, and records A3's blended number <!-- REQUIRED:item-type -->
- needed by: "let's try to make 10 more effects, something including fire and smoke" (the PO, 2026-11-03, #795). "just like with the rain, let's just try the effects themselves" (the PO, 2026-11-03, #795). His choices in this session: A1's test (D2), both paths timed (D7) <!-- REQUIRED:needed-by -->
- value proven by: he plays the fire. His words are written down first and sorted into look, variety or HUD (D5). Then the fixed question, as written: "Keep the fire as it looks now, or change its look before the next scenes?" (D2). Only look words, or a change asked to the look, count as a miss of A1. bench.md gets one row per path (D7) from three 5 s intervals of app.py's `time` and `avg` lines. Each row holds the fps and the step plus draw (brief.md's one formula, games/app.py:104-106, :109). The field is 160 x 120, drawn at 2 x 2 to the full screen, opaque on black. The row also holds the largest free internal block at the scene's start (A9). It also holds the blended step plus draw of the picture variant (A3, D12) <!-- REQUIRED:value-proven-by -->
- done when: a fire entry in `GAMES` like the rain (D9). engine/core/fx_fire.c in plain C passes a Mac test (engine D15). Path A is a C buffer that Python blits. On path B the engine writes into the s3lcd frame through s3lcd.h. Both are built and timed on the same field. Each is read on its own against A2's line, 15.3 ms, which the team keeps (D15). The number picks one path, and the other is dropped (D7). The scene shows its name and its cost in ms (D3, D15). A variant over a painted background exists (D12). Its control is open for the plan, because BOOT swaps two ways of computing (D3, D12). If the scene paints every pixel each frame, it sets `covers` (F6). When the scene is left, its C state is freed (the brief's no-go on static state). Ready to play, then played
- depends on: the PO's yes to this list. The board on USB. Size M (H) <!-- REQUIRED:depends-on -->
- status: proposed <!-- REQUIRED:item-status -->
- label (the repository's type label): story <!-- REQUIRED:spark-process:label -->
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787) <!-- REQUIRED:spark-process:parent -->
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games <!-- REQUIRED:spark-process:slice -->

## P599: the HUD's text costs about 11 ms a frame in every game → the text drawn once into a buffer when it changes and blitted each frame, at about 0.4 ms
- type: story (found on the way, F1, the team's proposal, outside P594's scope)
- needed by: no words of the PO on the problem. He said yes to filing it, to be built after P595 and before the bigger effects need the room (D13). The team's words (the tech lead, TL-4, F1): a cached HUD grows the rain's room for step plus draw from about 15.3 to 18.2 ms to about 25.5 to 28.7 ms (calculated, H for an effect). It also cuts every game's HUD cost
- value proven by: bench.md rows of the rain and two games, before and after. The HUD ms in the report line drops from 10.6 to 10.9 ms to under 1 ms. The fps is the same or higher, and he sees the same text
- done when: each time the HUD text changes, it is drawn into a buffer in panel order. Each frame blits that buffer. The rows above are in bench.md
- depends on: P595 played (D13). Size S (H)
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787). The team's proposal: D13 orders it among P594's turns, though its gain reaches every game
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P596: only fire uses the heat kernel → smoke, and bodies on fire that trail flames, from the same kernel, each its own scene
- type: story (the K1 group, one play turn, D10)
- needed by: "something including fire and smoke, and maybe some bodies colliding, being on fire" (the PO, 2026-11-03, #795). Being on fire means trail: heat seeded into one screen-wide fire field at each burning body (D16)
- value proven by: he plays both, and his words are sorted as in P595 (D5). He says whether they read as effects different from fire (A5). One bench.md row per effect from three 5 s intervals, and the blended row of smoke's picture variant (D12)
- done when: a smoke entry and a bodies-on-fire entry in `GAMES` (D9), both on engine/core/fx_fire.c. Bodies on fire seed heat into one screen-wide field at each body (D16). Until P598 exists, the bodies are the rain's falling bodies (H, the team's reading). Smoke has a variant over a picture (D12). Cost in ms on screen (D15). Ready to play, then played
- depends on: P595 played. Size S to M (H)
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787)
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P597: no water and only 40 Python particles → water seen from the side with splashes, and sparks or fireworks, on a C spring surface and a C particle kernel
- type: story (K4 with K2, one play turn, D10)
- needed by: "and maybe water" and "let's try to make 10 more effects" (the PO, 2026-11-03, #795). His list holds water from the side with splashes, and sparks or fireworks (D4)
- value proven by: he plays both, his words sorted as in P595 (D5). One bench.md row per effect: fps, step and draw ms, and the particle count the sparks scene holds at 24 fps against today's 40 particles at 2.27 ms. The blended row of the sparks' picture variant (D12)
- done when: two entries in `GAMES` (D9): a K4 spring surface that bodies drop into, with K2 splash droplets, and sparks or fireworks on K2. The spring method's tutorial states no licence, so it is written from its formulas (D14). The sparks have a variant over a picture (D12). Cost in ms on screen (D15). Ready to play, then played
- depends on: P596 played. Size M (H)
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787)
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P598: no two bodies in the engine touch → a few hundred round bodies that fall, knock and pile in a box, on a uniform grid in engine/core/ that P592 can reuse
- type: story (K5, one play turn, D10)
- needed by: "maybe some bodies colliding" (the PO, 2026-11-03, #795) and "especially the colisions, but all of it really" (the PO, 2026-11-03, this session). Round bodies in a box: circles with Verlet steps on a uniform grid in core/, the grid shared with P592, each hit a fact in the event buffer (D6)
- value proven by: he plays it, his words sorted as in P595 (D5). One bench.md row with the step ms for 300 circles. A Mac test shows no circle passes through another in a 60 s run at 2,000 px/s² (A7, the team's bar: his only word on bodies is "colliding")
- done when: a colliding-bodies entry in `GAMES` (D9). The grid is its own module in engine/core/, and the circle solver is an effects mode (D6). Each hit is written as a fact into the event buffer, and Python decides what follows (D6, engine D12). Code ported from an MIT source keeps its notice (D14). Cost in ms on screen (D15). Ready to play, then played
- depends on: P597 played. Size M (H)
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787)
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P600: four effects of the ten have no kernel yet → ripple seen from above, falling sand and water cells, a shockwave or glow, and plasma or dissolve, each its own scene
- type: story (K3, K6 and the rest, one play turn, D10)
- needed by: "let's try to make 10 more effects" (the PO, 2026-11-03, #795). His list holds these four (D4)
- value proven by: he plays the four, his words sorted as in P595 (D5). One bench.md row per effect from three 5 s intervals
- done when: four entries in `GAMES` (D9): the ripple on K3, the sand and water cells on K6, a shockwave or glow, and plasma or dissolve. D4 names both of each pair, so the PO picks which one is built. Cost in ms on screen (D15). Ready to play, then played
- depends on: P598 played. P599 built, if a scene needs its room (D13). Size M (H)
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787)
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## P601: an effect in plain C misses its line, and his "special assembler methods" are not shown → for that effect, a SWAR blend in C, then one PIE `.S` probe, each timed against plain C
- type: story (the late rungs of D11). The team's proposal for where the probe sits: its own small card after the groups, not inside an effect card. Why: the miss is known only from a bench row, so no effect card can hold the probe before its run. A card of its own keeps each effect card one play turn (D10) and keeps the rungs in D11's order
- needed by: "or even by trying to call the special assembler methods or through ESP-IDF" (the PO, 2026-11-03, #795). Plain C first, then a SWAR blend in C, then one PIE probe for the effect that misses its line (D11)
- value proven by: one bench.md row per rung for the effect that missed: plain C, the SWAR blend and PIE, each against the same line
- done when: the SWAR rung is timed. If the effect still misses, ESP-IDF 5.5.2's coprocessor save code is read first (A10, R0), then one `.S` in engine/port/s3/ is built and timed. If no effect misses its line after P600, the card closes as not needed, and no PIE shows in P594 (D11)
- depends on: a bench row that misses its line, in P595 to P600. Size S (H)
- status: proposed
- label (the repository's type label): story
- parent (the epic, as a sub-issue): P594 #795 (under P586 #787)
- slice (one Slice option of the board, or "ask the decider for a new one"): pixel-games

## Changes to existing cards (proposed, applied only on the PO's yes to this list)
- P583 #784: "The first effects ... exist in the s3lcd fork" becomes "in the engine module, from P594's kernels. P583 places them in RENT" (D8). Its slice 0 `.S` probe moves to engine/port/s3/ and reads P601's result first, if P601 ran (H, the team's). It reads P594's blended numbers first (D12). Its done-when (RENT uses them, fps at most 2 below) stays.
- P587 #788: its files become "the frame and its DMA send, drawing and blits", without "effects", and its "Needed by" drops P583 (D8).
- P592 #793: a note: P598's uniform grid in engine/core/ is the broad phase its rigid solver reuses later. The circle solver stays an effects mode (D6).
- P594 #795: its "Done when" names the ten of D4: fire, smoke, bodies on fire, water from the side with splashes, sparks or fireworks, colliding bodies, ripple from above, falling sand and water cells, a shockwave or glow, and plasma or dissolve. Its sub-issues are the cards above.

## Board actions
<!-- Each action, taken or pending, with its D. -->
- file P595 to P601 as sub-issues of #795, Slice pixel-games, stage Idea · pending, needs a D that names items.md <!-- REQUIRED:board-actions -->
- apply the changes to #784, #788, #793 and #795 above · pending, needs the same D
- comment on #795 with the brief's link, and set Waiting on the PO (the confirmation and the yes to this list) · pending
