<!-- Resume: invoke product-discovery again; `discovery.py check <this folder>` names the next step. -->
# P900, a game with bigger figures on reusable parts: discovery brief

<!-- Readiness, its one home. collecting evidence: anything short of the two below. an experiment: the decider chose
a test (a D) before choosing an option. design: the decider confirmed the frame, the jobs and a direction, and accepted
the remaining risk (D rows). An extension may tighten these. Next: design, or a chosen test of kind spike or prototype
→ the design skill the facts name, with this file; otherwise none, and the collection plan says who runs it.
Stands on: the assumptions not retired in risks-and-tests.md; of which those the decider rated high, or — while any
is unrated. check computes both. -->
**Ready for:** collecting evidence <!-- REQUIRED:ready -->
**Stands on:** ⟨fill⟩ H, ⟨fill⟩ of which would change the decision <!-- REQUIRED:debt -->
**Decision needed:** Q0: is this frame right? <!-- REQUIRED:decision-needed -->

## Frame
- Request, verbatim (corrections marked): "Let's make  a new game with the game box, so controllable with joystick movements and bigger figures of various kinds and situations and one can pick who to control, and there is some collaboration mission always." Then: "lets create a card for the new game including refactoring and separating out some reusable elemnts other games could use". Then, to start this discovery: "so let's do it, lets refine and plan it, offer cool other available tools that I might like to use in the engine too, offer options" (the PO, 2026-11-18, in the session. His full words are on the card, https://github.com/xmejkal/spark/issues/1279) <!-- REQUIRED:request -->
- Decision · decider: which game and which reusable engine parts go to design, in which order, and which tools they use · the PO (Petr Smejkal) <!-- REQUIRED:decision -->
- Outcome and how it is observed (a metric with unit and source, a proof command, or a log): proposed, not confirmed: the PO plays one mission on the board in which he switches between two figures of about 96 px to finish it, and the reusable parts are in `games/engine/`, imported by this game and by one older game. It is observed at his bench (his words after play) and by `/usr/bin/grep -l "engine.figure" games/*.py` (the module name is a placeholder) <!-- REQUIRED:outcome -->
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
- Depth: TRIO (default: PO assistant, user, tech lead) | FULL or LIGHT (who asked, when); add "no independent review" if subagents could not start: TRIO, proposed: three lens agents and the refuter. One more agent, the tools survey, runs since the frame because the PO asked for tool options (D9) <!-- REQUIRED:depth -->
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
- ⟨fill⟩ <!-- REQUIRED:findings -->

## Options <!-- CLAIMS -->
<!-- Two or three per open decision: decision · option · cost · what it would prove · opinion (whose), then the tag
and caveat cells. e.g. `- Q2 what first · fix delivery · two weeks · whether seen tasks get done · opinion (the facilitator's) · H ★C2 · caveat: none` -->
- ⟨fill⟩ <!-- REQUIRED:options -->
- Proposed no-gos and rabbit holes (proposals until the decider confirms): ⟨fill⟩ <!-- REQUIRED:nogos -->

## Riskiest assumption and its test
- Riskiest: ⟨fill⟩ · proposed — ⟨whose opinion⟩, pending Q1 | D<n> <!-- REQUIRED:riskiest -->
- Test · kind · pass line, dated before any result · proposed | D<n>: ⟨fill⟩ <!-- REQUIRED:test -->

## Questions
<!-- A queue; the first open question is asked alone. Each: Q<n> · question · decides: … · options · unblocks ·
opinion (whose) · kind: decision | account (a past-tense question about the decider's own use; the answer is E,
account, n = 1) · status: queued | asked <date> | answered D<n>.
If the decider cannot be asked, the queue stays here, and whatever rests on it stays H. -->
- Q0 · Is this frame right: the decision, the start and reach, the extensions and the depth? · decides: the frame · status: asked 2026-11-18 <!-- REQUIRED:q0 -->
- Q1 · How important is each assumption, and what pass line must the riskiest test meet? · decides: importance and pass lines · status: queued <!-- REQUIRED:q1 -->

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

## Found on the way <!-- CLAIMS -->
<!-- Outside this item's scope. Each is a separate proposal, never folded in. Same line format as What we found. -->
- ⟨fill⟩ | none <!-- REQUIRED:found -->

## Board actions <!-- REQUIRED:spark-process:board-actions -->
<!-- Each action on the board or the issue (stage, waiting flag, comment, filing): taken, with its D, or pending.
None is taken without a D. e.g. `- move #16 to Discovery · pending` -->
- move #1279 to Discovery · taken 2026-11-18 · D9. Discovery then holds 2 of 2 and the board 4 of 4 in flight
- a comment on #1279 that links this brief · pending, after the folder's PR exists
- Waiting on the PO and Waiting since on #1279 · pending, set only if Q0 waits past this session
<!-- EXTEND:brief-sections -->

## Hand-off
<!-- Written only after the decider confirms the understanding (a D); copies only confirmed constraints. Holds: outcome ·
who · success and its proof · constraints (appetite, confirmed no-gos, rabbit holes) · what they said (D) against what
we assume (H) · links to the journeys and the map · riskiest assumptions and their tests · options considered. -->
⟨the hand-off | not yet: what is unconfirmed⟩ <!-- REQUIRED:handoff -->

## Files
[Jobs and journeys](jobs-and-journeys.md) · [Story map](story-map.md) · [Risks and tests](risks-and-tests.md) · [Verification](verification.md) · [Items](items.md) · council/
