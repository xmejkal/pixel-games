<!-- Resume: invoke product-discovery again; `discovery.py check <this folder>` names the next step. -->
# P594 ten native effects tried alone on the board: discovery brief

<!-- Readiness, its one home. collecting evidence: anything short of the two below. an experiment: the decider chose
a test (a D) before choosing an option. design: the decider confirmed the frame, the jobs and a direction, and accepted
the remaining risk (D rows). An extension may tighten these. Next: design, or a chosen test of kind spike or prototype
→ the design skill the facts name, with this file; otherwise none, and the collection plan says who runs it.
Stands on: the assumptions not retired in risks-and-tests.md; of which those the decider rated high, or — while any
is unrated. check computes both. -->
**Ready for:** ⟨fill⟩ <!-- REQUIRED:ready -->
**Stands on:** ⟨fill⟩ H, ⟨fill⟩ of which would change the decision <!-- REQUIRED:debt -->
**Decision needed:** ⟨fill⟩ <!-- REQUIRED:decision-needed -->

## Frame
- Request, verbatim (corrections marked): the PO's words of 2026-11-03, after he played the rain (P593 #794), verbatim on [#795](https://github.com/xmejkal/spark/issues/795) (E): "nice. Alright, I really like it, before we move on, Let's now create other cool effects that might be really doable in C, or even by trying to call the special assembler methods or through ESP-IDF. I don't know, but let's try to make 10 more effects, something including fire and smoke, and maybe some bodies colliding, being on fire, and maybe water. Think of some research. Feel free to get inspired by other code, and let's just make more native effects that we can then later use in the engine. But now, just like with the rain, let's just try the effects themselves." On the way of working: "the usual research refinement, the cards, the councils, all of that" <!-- REQUIRED:request -->
- Decision · decider: which ten effects, how each is computed (plain C, a PIE `.S` kernel, or an ESP-IDF component such as esp-dsp), where their code lives in the engine module, what one effect scene shows (the effect, its cost on screen, a BOOT tap like the rain), which code is learned from under which licence, and the order of the slice cards · the PO <!-- REQUIRED:decision -->
- Outcome and how it is observed (a metric with unit and source, a proof command, or a log): the PO confirms a brief with a ranked list of ten effects (each with its look, its method, its cost per frame and its provenance) and proposed slice cards. Later, done on #795: ten effect scenes run on the board, each alone as the rain does, with the cost on screen and in bench.md, and the PO played them. Today's rain as the reference: N 160, C step 0.16 to 0.17 ms, draw 13.5 to 14.0 ms, HUD text 10.6 to 10.9 ms a frame, 24 fps (pixel-games bench.md P593, measured) <!-- REQUIRED:outcome -->
- Already decided (D · who · when · where; include the product's stated non-goals and earlier decisions the request names): effects move to C and the C layer may own an effect's state if the game reads nothing back (Q13 yes) · the PO · 2026-11-02 · #771, p580-finding.md question 4. C computes facts, Python decides consequences, every feel number comes from Python (D12) · the PO · 2026-11-03 · engine brief. The engine C lives in an own `engine` module beside s3lcd: core/ plain C for the Mac and the board, port/s3/ for fast paths, one thin binding (D17). A Mac build of the same C (D15). Own small solver with chip fast paths, ideas from Box2D-Lite, Box2D v3 and Chipmunk2D (D16). Fixed 10 ms step (D18). A feel slice stops at "ready to play" until the PO played it (D21) · all the PO · 2026-11-03 · docs/discovery/2026-11-03-engine/brief.md. Each effect is tried alone first, the way the rain was; use in the engine and the games comes later · the PO · 2026-11-03 · #795. The games are original in name, art and levels (#769). P583 #784 puts effects into RENT; this card does not <!-- REQUIRED:decided -->
- Open questions: which ten (P580 ranks eight: fire and smoke, particles, ripple, glow, dissolve, shake, noise smoke, shatter); what "bodies colliding" and "bodies on fire" mean on screen and whether they use the engine's world.c; what "water" is (a ripple window, a falling liquid of particles, a filled level with waves); where PIE or esp-dsp pays and where plain C is enough; code to learn from and its licence; the frame budget of one scene, given the HUD text at about 11 ms; how the effects reach the screen (a C buffer that Python blits, or C drawing into the s3lcd frame through s3lcd.h) <!-- REQUIRED:open -->
- Scope · out of scope (proposed): in: ten effect scenes, each alone, its method, its cost on screen and in bench.md, the C home of the kernels inside the engine module, the research gaps P580 left (colliding and burning bodies, water, licences, esp-dsp and PIE kernels) · out: effects inside a game (P583 #784), the engine's rigid tip and topple (P592), sound, a spark change, a copy of any existing game or demo <!-- REQUIRED:scope -->
- Start and reach (proposed until Q0): start own idea (the PO's) · decider reachable yes · users the PO as player and game writer, n = 1 reachable · data and connectors: the pixel-games repository (code, tests, bench.md, run logs, p580-finding.md), the board on USB, the web (search and fetch), GitHub (gh), the Espressif docs MCP, Miro; no analytics connected · decider as a user n = 1 · must not get worse: the ten games and the rain as they play now (rain 24 fps at N 160, bench.md P593) <!-- REQUIRED:start-reach -->
- Flags (yes · no · —; asked only when it changes a decision; never legal advice; any date or threshold is read at its source at run time and cited):
  - sold or given away, or personal use: given away as open source (pixel-games is public, MIT) <!-- REQUIRED:flag-sold -->
  - connects to a network or runs software (for example the EU's Cyber Resilience Act): software; no network <!-- REQUIRED:flag-network -->
  - children or food contact: no <!-- REQUIRED:flag-children -->
  - market: public on GitHub, worldwide <!-- REQUIRED:flag-market -->
  - radio (unlicensed-device rules; read at their source when it decides): no <!-- REQUIRED:electronics-firmware:flag-radio -->
  - a Li-ion cell (charging, transport, battery rules): no <!-- REQUIRED:electronics-firmware:flag-li-ion -->
  - mains: no <!-- REQUIRED:electronics-firmware:flag-mains -->
  <!-- EXTEND:flags -->
- Extensions (each active id · the fact that activated it; when none matched, only "none matched: core only · the fact that decided it", naming no extension; list any directive skipped under rule 9): electronics-firmware · ⟨fill: the request words that activated it⟩; spark-process · electronics-firmware · "doable in C", "special assembler methods", "ESP-IDF" (firmware on the ESP32-S3 and its PIE unit); spark-process · "the cards, the councils", the item is on spark's board (project 2) <!-- REQUIRED:extensions -->
- The item (its issue, or the proposal in the decider's words) · what is still open elsewhere · the repository's push check, or "no push check here": [P594 #795](https://github.com/xmejkal/spark/issues/795), in Discovery on spark project 2, under the engine epic P586 #787, slice pixel-games · still open elsewhere: P469 #637 and P511 #706 in Build, Ready holds 6 of 5 (#783 waits on P592), the engine discovery P586 is Ready for an experiment (P589 done, P590 #791 next) · pixel-games has no push check: the folder lands by PR <!-- REQUIRED:spark-process:item -->
<!-- EXTEND:frame -->
- Depth: TRIO (default: PO assistant, user, tech lead) | FULL or LIGHT (who asked, when); add "no independent review" if subagents could not start: proposed until Q0: TRIO plus one researcher for the gaps: the PO assistant (Opus), the user (Sonnet), the tech lead with the C and PIE lens (Opus), an effects researcher for colliding and burning bodies, water, esp-dsp and licences (Opus); the refuter on Fable 5.1; 5 agents <!-- REQUIRED:depth -->
  <!-- Cost, measured once: the P900 rehearsal's council took 6 agents, 499 calls and about 90M input tokens (2026-10-06). -->
- Search budget: web searches: PO assistant 6, tech lead 8, effects researcher 14, user 0, refuter 6 <!-- REQUIRED:budget -->
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
- Q0 · Is this frame right: the decision, the start and reach, the extensions and the depth? · decides: the frame · status: ⟨fill⟩ <!-- REQUIRED:q0 -->
- Q1 · How important is each assumption, and what pass line must the riskiest test meet? · decides: importance and pass lines · status: ⟨fill⟩ <!-- REQUIRED:q1 -->

## Decisions
<!-- D<n> · what · who · when · where recorded · options considered.
A yes covers only the actions and choices it names. A standing yes names its kind of action and its source.
Name what a D confirms in its words: the frame, the jobs, a direction, the remaining risk, a test, items.md. -->

## Found on the way <!-- CLAIMS -->
<!-- Outside this item's scope. Each is a separate proposal, never folded in. Same line format as What we found. -->
- ⟨fill⟩ | none <!-- REQUIRED:found -->

## Board actions <!-- REQUIRED:spark-process:board-actions -->
<!-- Each action on the board or the issue (stage, waiting flag, comment, filing): taken, with its D, or pending.
None is taken without a D. e.g. `- move #16 to Discovery · pending` -->
⟨fill⟩
<!-- EXTEND:brief-sections -->

## Hand-off
<!-- Written only after the decider confirms the understanding (a D); copies only confirmed constraints. Holds: outcome ·
who · success and its proof · constraints (appetite, confirmed no-gos, rabbit holes) · what they said (D) against what
we assume (H) · links to the journeys and the map · riskiest assumptions and their tests · options considered. -->
⟨the hand-off | not yet: what is unconfirmed⟩ <!-- REQUIRED:handoff -->

## Files
[Jobs and journeys](jobs-and-journeys.md) · [Story map](story-map.md) · [Risks and tests](risks-and-tests.md) · [Verification](verification.md) · [Items](items.md) · council/
