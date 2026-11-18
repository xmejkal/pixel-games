<!-- Resume: invoke product-discovery again; `discovery.py check <this folder>` names the next step. -->
# P900, a game with bigger figures on reusable parts: discovery brief

<!-- Readiness, its one home. collecting evidence: anything short of the two below. an experiment: the decider chose
a test (a D) before choosing an option. design: the decider confirmed the frame, the jobs and a direction, and accepted
the remaining risk (D rows). An extension may tighten these. Next: design, or a chosen test of kind spike or prototype
→ the design skill the facts name, with this file; otherwise none, and the collection plan says who runs it.
Stands on: the assumptions not retired in risks-and-tests.md; of which those the decider rated high, or — while any
is unrated. check computes both. -->
**Ready for:** collecting evidence <!-- REQUIRED:ready -->
**Stands on:** 9 H, — of which would change the decision <!-- REQUIRED:debt -->
**Decision needed:** Q1: how important is each assumption, and which pass line must the spike meet? <!-- REQUIRED:decision-needed -->

## Frame
- Request, verbatim (corrections marked): "Let's make  a new game with the game box, so controllable with joystick movements and bigger figures of various kinds and situations and one can pick who to control, and there is some collaboration mission always." Then: "lets create a card for the new game including refactoring and separating out some reusable elemnts other games could use". Then, to start this discovery: "so let's do it, lets refine and plan it, offer cool other available tools that I might like to use in the engine too, offer options" (the PO, 2026-11-18, in the session. His full words are on the card, https://github.com/xmejkal/spark/issues/1279) <!-- REQUIRED:request -->
- Decision · decider: which game and which reusable engine parts go to design, in which order, and which tools they use · the PO (Petr Smejkal) <!-- REQUIRED:decision -->
- Outcome and how it is observed (a metric with unit and source, a proof command, or a log): the PO plays one mission on the board in which he switches between two figures of about 96 px to finish it, and the reusable parts are in `games/engine/`, imported by this game and by one older game. It is observed at his bench (his words after play) and by `/usr/bin/grep -l "engine.figure" games/*.py` (the module name is a placeholder) · confirmed, D10 <!-- REQUIRED:outcome -->
- Already decided (D · who · when · where; include the product's stated non-goals and earlier decisions the request names): D1 to D9 below. Earlier, by reference: the engine's rule of two versions, a plain Python reference and a fast twin (E `games/engine/README.md:27-37`). The boundary of P800: "The game shows no realistic suffering of people" (E https://github.com/xmejkal/spark/issues/1124, read 2026-11-18). The CMU data stays out of the repository (E `README.md:38`). A feel slice stops at "ready to play" until the PO played it (D the PO, 2026-11-03, his rules file) <!-- REQUIRED:decided -->
- Open questions: how much art memory and frame time a 96 px figure takes on the board · what a mission is, step by step · how the player picks and switches a figure with one stick, one button and one knob · what the AI of an unheld figure does, and with which technique · which parts need a C twin · which tools from the survey the PO wants · the order of the parts and the game <!-- REQUIRED:open -->
- Scope · out of scope (proposed): in: the game's first mission, the figure, its poses, the steering part with a player and an AI · out (proposed): the remote player (P832, the link), the car simulator (P902, https://github.com/xmejkal/spark/issues/1281), the move of the old games (P903, https://github.com/xmejkal/spark/issues/1282) beyond the one game that proves the parts, new hardware <!-- REQUIRED:scope -->
- Start and reach (proposed until Q0): start existing product · decider reachable yes · users: the PO, who plays the box and shows it with his CV. No other player is reachable · data and connectors: the two repositories, GitHub through `gh`, web search, the Espressif documentation search, Miro. A board on USB was not looked for · decider as a user n = 1 · must not get worse: the fifteen games and their golden net, each set's load time (Rescue's is 548 ms, measured on the board on 2026-11-14, E `README.md:383`), and the engine plan's stages (P841) <!-- REQUIRED:start-reach -->
- Flags (yes · no · —; asked only when it changes a decision; never legal advice; any date or threshold is read at its source at run time and cited):
  - sold or given away, or personal use: — · the repository is public. CMU's home page says "you may not resell this data directly, even in converted form" (E `README.md:38`), which matters only if the game is ever sold <!-- REQUIRED:flag-sold -->
  - connects to a network or runs software (for example the EU's Cyber Resilience Act): yes, it runs software on an ESP32-S3 · no network in this item's scope <!-- REQUIRED:flag-network -->
  - children or food contact: — <!-- REQUIRED:flag-children -->
  - market: — <!-- REQUIRED:flag-market -->
  - radio (unlicensed-device rules; read at their source when it decides): no in this scope · the remote player (out of scope) would use a radio <!-- REQUIRED:electronics-firmware:flag-radio -->
  - a Li-ion cell (charging, transport, battery rules): — <!-- REQUIRED:electronics-firmware:flag-li-ion -->
  - mains: — <!-- REQUIRED:electronics-firmware:flag-mains -->
  <!-- EXTEND:flags -->
- Extensions (each active id · the fact that activated it; when none matched, only "none matched: core only · the fact that decided it", naming no extension; list any directive skipped under rule 9): electronics-firmware · repo-has .spark/project.json; spark-process · "lets create a card", and the item is a card on spark's board <!-- REQUIRED:extensions -->
- The item (its issue, or the proposal in the decider's words) · what is still open elsewhere · the repository's push check, or "no push check here": https://github.com/xmejkal/spark/issues/1279 (P900), with P901 (https://github.com/xmejkal/spark/issues/1280, the reusable figure) under it · still open elsewhere: the discovery of P820 (https://github.com/xmejkal/spark/issues/1173, the artifact interface), which collects evidence and waits for P829 · no push check here (E `git config core.hooksPath` prints nothing and the hooks folder holds only samples, 2026-11-18) <!-- REQUIRED:spark-process:item -->
<!-- EXTEND:frame -->
- Depth: TRIO (default: PO assistant, user, tech lead) | FULL or LIGHT (who asked, when); add "no independent review" if subagents could not start: TRIO (D10): three lens agents on the everyday model and the refuter on the strongest. One more agent, the tools survey, runs since the frame because the PO asked for tool options (D9) <!-- REQUIRED:depth -->
  <!-- Cost, measured once: the P900 rehearsal's council took 6 agents, 499 calls and about 90M input tokens (2026-10-06). -->
- Search budget: 15 web searches for the tools survey · proposed: 4 for each lens <!-- REQUIRED:budget -->
- Appetite (the decider's, asked only when heading for design) | —: — <!-- REQUIRED:appetite -->

## What we found <!-- CLAIMS -->
<!-- One claim per line: `- [★C<n>] claim · E pointer | H source | D who date · caveat: qualifier | none`.
★ marks a claim that a decision, an option or the riskiest assumption rests on. A quote is verbatim, with its pointer.
Say what the evidence can support: an account (what happened to one person), data (how often, in its population and
period), a document (what was specified), the product (what exists, not whether anyone needs it), a benchmark (a
comparison). Model knowledge is H until a source is read. Elsewhere cite a ★ claim as ★C<n>, with its keep: words.
e.g. `- [★C2] 13 of 526 tickets ask for recurring tasks · E tickets.csv:2-14 · caveat: picked by Lena; shows that, not how often` -->
- [★C1] A figure's picture is raw RGB565, 2 bytes a pixel, with no compression. The fireman's run picture is 26 by 30 px, his figure is 26 px tall (`FIG_H`), and each left-facing pose is a second, mirrored picture · E `art/export.py:20-27`, `art/sets/rescue.py:172,181,591-593` · caveat: read in the painter, the pack file itself not decoded
- [★C2] The picture pool is made once, as big as the largest pack, which is the runner's 739,216 bytes. A soft reset keeps a smaller pool, so a bigger pack needs a hard reset · E `games/pictures.py:42-52`, `ls -l games/packs` (runner.pak 739216, rescue.pak 660008) · caveat: none
- [★C3] Two figures at 96 px with two cycles each and both facings (the fireman's run and spray, the man's run and wave) come to 1,913,952 bytes, 2.6 times today's pool · E `art/sets/rescue.py:181,530` (the sizes), scaled here by 96/26 with 2 bytes a pixel: 511,488 + 394,272 + 504,096 + 504,096 · caveat: calculated, not painted and not loaded; with 96 px as the picture's height and not the figure's, about a quarter less; with one facing stored, half · ★C1: read in the painter
- [★C4] The board has 8 MB of PSRAM. With a 1,507,152 byte art set loaded, 6,747,500 bytes of it were free and a 4,000,000 byte block could be allocated · E `bench.md:214` (measured on the board, the P567 run) · caveat: an older build; no row measures a 2 MB pool, because "a larger pool needs a hard reset, so not run"
- [★C5] A game cannot use PICK or the knob today. The app reads PICK to switch the game and hands the knob's turn to the volume. A game gets FIRE and the stick · E `games/app.py:332-341` · caveat: none
- [★C6] Rescue and Meteors read only the stick's x. The stick's y is free in both · E `games/rescue.py:566`, `games/meteors.py:380` · caveat: two games read. The user lens reports one inconsistent reading of "up" on the PO's breadboard (`bench.md:1762-1765`, its USER-5, not re-read here)
- [★C7] A long hold of D14, the PICK button, powered the board off after about 5.5 s on 2026-11-02 · E `bench.md:58` (measured, an edge-count script) · caveat: the row says hardware V1.1 and earlier; the revision of the PO's board today was not read
- [★C8] Rescue's only frame times on the board are from its title and game-over screens: paint 26.8 to 33.0 ms, 18 to 19 fps, load 638 ms. No row has Rescue in play · E `logs/run-p846-baseline-a.log:79-90` (measured, 2026-11-16) · caveat: not in play; the README's 548 ms has no kept log
- [★C9] The pose formula `ran * POSES // STRIDE % POSES` is written four times in Rescue and once in Meteors, and Rescue's two classes step their px by hand though `SubPixel` exists · E `games/rescue.py:179,182,212,834`, `games/meteors.py:249`, `games/rescue.py:165,220` · caveat: two of fifteen games read
- [★C10] A module in `games/engine/` may import only MicroPython's built-in modules, `_engine` and the package modules its `DIRECTION` row names. So a figure there cannot import `pictures` or `gfx`: it holds names and numbers, and the game draws · E `tests/test_engine_boundary.py:24-31` · caveat: until the plan's stages 3c and 4 move the canvas and the pictures into the package (tech lead, TECH-15, TECH-16)
- [★C11] At the captured run speed a 96 px figure moves about 207 px a second, so it crosses the 320 px screen in about 1.5 s · E `games/rescue.py:39` (`SPEED_PX_S` 56), scaled here by 96/26, and 320 / 206.8 · caveat: calculated; a scene that scrolls or a slower gait changes it
- [C12] The ESP32-S3's "AI" is its vector instructions, used through the C libraries ESP-NN and ESP-DL. The survey found no MicroPython binding. `emlearn-micropython` (MIT) gives trees and nearest neighbours as a native module · H council/tools-survey.md TOOLS-20 to TOOLS-24, pages read by the agent on 2026-11-18 and not re-read here · caveat: its match with the box's firmware 1.29 was not checked
- [C13] At 24 px the motion capture's spray stance was misread, so the bubble game's workers are posed by hand · E `art/sets/gravpong.py:7-8` · caveat: one case
- [C14] The painter's limb widths are px constants at the final size, so a 96 px painter is a code change and not one number · H council/tech-lead.md TECH-19 (`art/sets/rescue.py:196` and the lines after it, of which line 196 was re-read here and is another constant) · caveat: the painter was not run at 96 px
- [C15] Games where one player switches between figures exist: The Lost Vikings and Trine. Brothers steers two figures at once with two sticks, which the box does not have · H council/po-assistant.md PO-12 to PO-17, from search snippets · caveat: no primary source read; what an idle figure does in each stayed unknown
- [C16] The steering seam is mostly there: the games already take the stick as a direction and a held button (`Rules.step(ms, held, way)`), and `actions.py` says a remote board gets a second map. An AI needs a read-only view of the game's world, which is per game · H council/tech-lead.md TECH-13 · caveat: Rescue only <!-- REQUIRED:findings -->

## Options <!-- CLAIMS -->
<!-- Two or three per open decision: decision · option · cost · what it would prove · opinion (whose), then the tag
and caveat cells. e.g. `- Q2 what first · fix delivery · two weeks · whether seen tasks get done · opinion (the facilitator's) · H ★C2 · caveat: none` -->
- Q2 what first · a picture on the Mac: paint the fireman at 96 px and show one run as a GIF on a 320 by 240 frame · half a day, no bench · whether the detail shows (A3) and the true bytes · opinion (the facilitator's): first · H ★C1, C14 · caveat: proves no board time · ★C1: read in the painter
- Q2 what first · a spike on the board: load one 96 px cycle, move two figures over Rescue's street, log the pool, the free PSRAM and the fps · about a day and the PO's bench · whether the art and the frame fit (A1) · opinion (the PO assistant's, PO-20): the first gate before design · H ★C3, ★C4, ★C8 · caveat: needs a hard reset and a deploy, which are his · ★C3: calculated · ★C4: an older build · ★C8: not in play
- Q2 what first · the parts first, on Rescue at 24 px · two or three days, no bench · whether the figure and the steering split hold with Rescue's hashes unchanged (A6) · opinion (the facilitator's): after the spike, because the size decides the art · H ★C9, ★C10 · caveat: lands on the engine plan's stage 8e · ★C9: two of fifteen games read · ★C10: until the plan's stages 3c and 4
- Q3 how the art fits · both facings as pictures and a bigger pool of about 2 MB · no C change; a hard reset once · that the pool can grow · opinion (the tech lead's listing, no choice) · H ★C2, ★C3 · caveat: the pool holds that PSRAM for every game · ★C3: calculated
- Q3 how the art fits · a mirror flag in the C blit, one facing stored · a pixel-engine PR and a firmware flash · half the bytes · opinion (the facilitator's): the best ratio of gain to change · H council/tech-lead.md TECH-3 · caveat: the size of the C change was not estimated
- Q3 how the art fits · poses as numbers, the figure painted on the board by a C painter · the largest change: today's painter is Python on the Mac · no pictures to store, turns and blends for free · opinion (the tools survey's "might like") · H tools-survey TOOLS-13, TOOLS-39 · caveat: unmeasured
- Q4 how he switches · the stick's up and down · no app change · whether up and down read cleanly while he runs · opinion (the facilitator's): try first · H ★C6 · caveat: one inconsistent "up" reading in the bench log · ★C6: two games read
- Q4 how he switches · PICK, given to the game while a mission runs · an app change, and a way out of the game is still needed · a counted press that is never lost · opinion (none) · H ★C5, ★C7 · caveat: a long hold can power an older board off · ★C7: V1.1 and earlier
- Q4 how he switches · the knob, one detent a figure · an app change; the volume moves elsewhere during a mission · a pick among many figures · opinion (none) · H ★C5 · caveat: none
- Q5 the unheld figure · it stands and breathes at its place · one idle cycle to paint, no AI · the smallest thing that is not dead · opinion (the facilitator's): the walking skeleton · H · caveat: none
- Q5 the unheld figure · it does its own job by a rule: a state machine with Reynolds's steering · plain Python, the same formulas for objects and cars (D6) · "their own lives" (D4) · opinion (the facilitator's): the second slice · H tools-survey TOOLS-18, TOOLS-19 · caveat: no library read
- Q5 the unheld figure · a learned model on the board · a spike on emlearn-micropython first · whether "the s3's AI capabilities" add anything (D4) · opinion (the facilitator's): later, if at all · H C12 · caveat: none
- Q6 which older game proves the parts · Rescue · two classes and the dog, the plan's stage 8e · the parts carry a figure with several cycles · opinion (none) · H ★C9 · caveat: none · ★C9: two of fifteen games read
- Q6 which older game proves the parts · Meteors · one walker, the plan's stage 8c · the smallest proof · opinion (the facilitator's): first, because it is small · H ★C9 · caveat: none · ★C9: two of fifteen games read <!-- REQUIRED:options -->
- Proposed no-gos and rabbit holes (proposals until the decider confirms): no neural net in the first mission · no paid tool (Spine costs money, tools-survey TOOLS-15) · no C twin before a board row shows a hot spot (tech lead, TECH-18) · no CMU file in the repository · no scrolling scene in the first mission (a rabbit hole: it touches the dirty-rectangle send) · no new hardware · H the facilitator's proposals · caveat: none of them is confirmed <!-- REQUIRED:nogos -->

## Riskiest assumption and its test
- Riskiest: A1: two 96 px figures with enough poses fit the art memory and the frame time on the board, beside a background · proposed — the PO assistant's and the facilitator's opinion, pending Q1 <!-- REQUIRED:riskiest -->
- Test · kind · pass line, dated before any result · proposed | D<n>: the board spike of Q2 · spike · proposed pass line, written 2026-11-18 before any result: the pack loads into the pool after a hard reset, the PSRAM keeps 4 MB free, two moving figures hold 18 fps (Rescue's rate today, ★C8), and the load stays under 2.5 s · proposed — the facilitator's opinion, pending Q1 · ★C8: not in play <!-- REQUIRED:test -->

## Questions
<!-- A queue; the first open question is asked alone. Each: Q<n> · question · decides: … · options · unblocks ·
opinion (whose) · kind: decision | account (a past-tense question about the decider's own use; the answer is E,
account, n = 1) · status: queued | asked <date> | answered D<n>.
If the decider cannot be asked, the queue stays here, and whatever rests on it stays H. -->
- Q0 · Is this frame right: the decision, the start and reach, the extensions and the depth? · decides: the frame · status: answered D10 <!-- REQUIRED:q0 -->
- Q1 · How important is each assumption, and what pass line must the riskiest test meet? · decides: importance and pass lines · status: queued <!-- REQUIRED:q1 -->
- Q2 · What comes first: a picture on the Mac, a spike on the board, or the parts on an old game? · decides: the first card · options: as in Options · unblocks: everything · opinion (the facilitator's): the picture, then the spike · kind: decision · status: queued
- Q3 · Is "96 px" the figure from sole to head, or the height of its picture? · decides: the art bytes, by about a quarter · options: the figure, the picture · unblocks: the spike's sizes · opinion (none) · kind: decision · status: queued
- Q4 · How does the art fit: a bigger pool, a mirror flag in C, or poses painted on the board? · decides: whether a firmware flash is in the plan · options: as in Options · unblocks: the design of the figure's drawing · opinion (the facilitator's): decide after the spike · kind: decision · status: queued
- Q5 · How do you switch figures: the stick's up and down, PICK or the knob? · decides: whether the app changes before the game · options: as in Options · unblocks: A2's test · opinion (the facilitator's): the stick first · kind: decision · status: queued
- Q6 · When you held the stick in Rescue, which hand was free, and for which button? · decides: the switch's binding · unblocks: Q5 · kind: account · status: queued
- Q7 · What does a figure do when you do not hold it: stand and breathe, or do its own job by a rule? · decides: the AI's first behaviour and the idle poses · options: as in Options · unblocks: the first mission · opinion (the facilitator's): stand first · kind: decision · status: queued
- Q8 · Which older game proves the parts: Rescue or Meteors? · decides: which stage of the engine plan P900 sits beside · options: as in Options · unblocks: P901's plan · opinion (the facilitator's): Meteors · kind: decision · status: queued
- Q9 · Which tools from the survey do you want looked at more closely: your own capture with MediaPipe, the 100STYLE set, Box2D for the car, a phone as a remote controller? · decides: which spikes are added later · options: each, or none · unblocks: nothing in the first mission · opinion (none) · kind: decision · status: queued
- Q10 · How much time is the first mission worth to you? · decides: the appetite · unblocks: design · kind: decision · status: queued
- Q11 · Do I file the items in items.md? · decides: the filing · unblocks: the first card · kind: decision · status: queued

## Decisions
<!-- D<n> · what · who · when · where recorded · options considered.
A yes covers only the actions and choices it names. A standing yes names its kind of action and its source.
Name what a D confirms in its words: the frame, the jobs, a direction, the remaining risk, a test, items.md. -->

- D1 · collaboration means that he plays alone and switches between figures · the PO · 2026-11-18 · https://github.com/xmejkal/spark/issues/1279#issuecomment-6972668412 · options: I switch figures, the box helps me, both, two players
- D2 · a figure is about 96 px tall · the PO · 2026-11-18 · the same comment · options: 48 px, 96 px, 160 px, the discovery decides
- D3 · the situations are rescue missions, everyday jobs, circus and sport, mixed with one per level · the PO · 2026-11-18 · the same comment · options: each alone, or mixed
- D4 · a figure that he does not hold has its own life through a simple AI. His wish to use "the s3's AI capabilities" is a wish, not a checked fact · the PO · 2026-11-18 · the same comment · options: none offered, his own words
- D5 · one card holds the game and the reusable parts that other games can use: the figure, the poses, player or AI control · the PO · 2026-11-18 · https://github.com/xmejkal/spark/issues/1279 (the body) · options: none offered
- D6 · the AI also steers what is not a character: objects, obstacles, cars · the PO · 2026-11-18 · https://github.com/xmejkal/spark/issues/1279#issuecomment-6972734738 · options: none offered
- D7 · later a remote player steers too, and C versions stand beside the plain MicroPython ones · the PO · 2026-11-18 · https://github.com/xmejkal/spark/issues/1279#issuecomment-6972767160 · options: none offered
- D8 · after the new game succeeded, the old games move onto the parts (P903) · the PO · 2026-11-18 · https://github.com/xmejkal/spark/issues/1282 · options: none offered
- D9 · start this discovery and offer tool options: "so let's do it, lets refine and plan it, offer cool other available tools that I might like to use in the engine too, offer options". This yes covers the discovery, the tools survey and its 15 web searches. The card's move to Discovery rests on his standing rule "It moves as the work moves" (his rules file, the section "Start of a session") · the PO · 2026-11-18 · in the session · options: P878 first, the game first, the game stays an idea (he chose P878 first, and P878 merged as PR #1278)
- D10 · the frame is right: the scope, the out-of-scope list (the remote player, the car simulator P902, the old games P903 beyond one game that proves the parts) and the outcome sentence. The depth is TRIO: three lenses, then the refuter · the PO · 2026-11-18 · in the session, Q0 · options for the frame: yes, add the car, parts first, game first · options for the depth: three lenses, one lens, full council
- D11 · the open things are finished first: P900 goes back to Idea, the agents that run finish and their reports stay on the branch, and the discovery goes on at his word. "Before we start with it and refine it, lets first finish the open things, please." · the PO · 2026-11-18 · in the session · options: back to Idea, stop the agents too, keep it in Discovery
- D12 · the discovery goes on while he reads the overview of P896: "i'm reading, go on". The facilitator read this as the word D11 waits for. The card stays in Idea until the board has a free place, because P892 takes the fourth place in flight · the PO · 2026-11-18 · in the session · options: none offered

## Found on the way <!-- CLAIMS -->
<!-- Outside this item's scope. Each is a separate proposal, never folded in. Same line format as What we found. -->
- [C17] Rescue's own px step is written by hand twice though `SubPixel` exists, and P895 (https://github.com/xmejkal/spark/issues/1269) already holds that fix · E `games/rescue.py:165,220` · caveat: none
- [C18] The README says Rescue's set loads in 548 ms, and the only kept log says 638 ms · E `README.md:383`, `logs/run-p846-baseline-a.log:79` · caveat: the loader changed between the two dates (tech lead, PHYS-6)
- [C19] Six open cards overlap this item by their titles: P635, P636, P637, P654, P765 and P822 · H council/po-assistant.md PO-9 · caveat: titles read by the agent, bodies not all read <!-- REQUIRED:found -->

## Board actions <!-- REQUIRED:spark-process:board-actions -->
<!-- Each action on the board or the issue (stage, waiting flag, comment, filing): taken, with its D, or pending.
None is taken without a D. e.g. `- move #16 to Discovery · pending` -->
- move #1279 to Discovery · taken 2026-11-18 · D9. Discovery then holds 2 of 2 and the board 4 of 4 in flight
- move #1279 back to Idea · taken 2026-11-18 · D11. The board then holds 3 of 4 in flight
- move #1279 to Discovery again · pending: the board has one free place and the other session's P892 takes it
- a comment on #1279 that links this brief · pending, after the folder's PR exists
- Waiting on the PO and Waiting since on #1279 · pending, set only if Q0 waits past this session
<!-- EXTEND:brief-sections -->

## Hand-off
<!-- Written only after the decider confirms the understanding (a D); copies only confirmed constraints. Holds: outcome ·
who · success and its proof · constraints (appetite, confirmed no-gos, rabbit holes) · what they said (D) against what
we assume (H) · links to the journeys and the map · riskiest assumptions and their tests · options considered. -->
not yet: the jobs, a direction, the importance of the assumptions and the pass line are unconfirmed, and the refuter did not run <!-- REQUIRED:handoff -->

## Files
[Jobs and journeys](jobs-and-journeys.md) · [Story map](story-map.md) · [Risks and tests](risks-and-tests.md) · [Verification](verification.md) · [Items](items.md) · council/
