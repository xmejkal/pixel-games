<!-- Resume: invoke product-discovery again; `discovery.py check <this folder>` names the next step. -->
# P649 one fluid layer: discovery brief

> Paused on 2026-11-06 at step 5 of 8, because the PO put spark's refactor first. The work so far: the frame (D1),
> one lens report (council/light.md), jobs, a proposed story map, seven assumptions, three proposed stories and
> four queued questions. To resume: run the refuter on this brief (step 6, the prompt in the skill's
> references/council.md), reproduce ★C2, ★C7 and ★C9, then ask Q1. The main finding so far: the two water cards,
> P597 and P600, read no velocity field (★C6), so a fluid layer serves gases such as smoke or steam, not water.
> `discovery.py check` lists 32 problems on 2026-11-06, mostly keep words missing where a ★ claim is cited.
> Fix them before the refuter runs.

<!-- Readiness, its one home. collecting evidence: anything short of the two below. an experiment: the decider chose
a test (a D) before choosing an option. design: the decider confirmed the frame, the jobs and a direction, and accepted
the remaining risk (D rows). An extension may tighten these. Next: design, or a chosen test of kind spike or prototype
→ the design skill the facts name, with this file; otherwise none, and the collection plan says who runs it.
Stands on: the assumptions not retired in risks-and-tests.md; of which those the decider rated high, or — while any
is unrated. check computes both. -->
**Ready for:** collecting evidence: Q1 to Q4 are open <!-- REQUIRED:ready -->
**Stands on:** 7 H, — of which would change the decision <!-- REQUIRED:debt -->
**Decision needed:** which fluid layer pixel-games builds first as the MVP: the flow (physics), the field renderer (graphics), or both, and with which flow strategy <!-- REQUIRED:decision-needed -->

## Frame
- Request, verbatim (corrections marked): "Wait, so it should probably slso be generalized as fluids right?", then "for the physicxs to be reusable. or graphics? both?", then "Cause we'll wanmt other effects too, like qter, or other materials" (the PO, 2026-11-06, during P647 #869's plan, quoted in spark #871). Then: "Let's do the discovery and some MVP as soon as possible" (the PO, 2026-11-06, spark #871 comment) <!-- REQUIRED:request -->
- Decision · decider: which fluid layer pixel-games builds first as the MVP, and in which stages · Petr, the PO <!-- REQUIRED:decision -->
- Outcome and how it is observed (a metric with unit and source, a proof command, or a log): one flow moves two different materials in two scenes and one field renderer paints both, with no copy of the step or the draw (the card's "Value proven by", spark #871), judged by the PO on the board; the fire keeps its fps (P646: linear 13.21 to 13.78 ms, 24 fps, E bench.md P646 section, runs 128 and 129) <!-- REQUIRED:outcome -->
- Already decided (D · who · when · where; include the product's stated non-goals and earlier decisions the request names): D-P647 · the PO · 2026-11-06 · the light flow, bend 1 and wander 512, every number a setting (docs/discovery/2026-11-06-p647-flame-motion/README.md, short version item 3); P650 #872 is refined after this discovery, and this MVP can replace it. D-P628 · the PO · 2026-11-05 · plugins in the loop first, then the C split (docs/discovery/2026-11-05-p628-engine-layers/README.md). D12 · "C steps and paints, Python decides" (docs/engine-walkthrough.md). D-reuse · the PO · 2026-11-06 · reuse before inventing, license-compatible copy only. D-no-paid · the PO · 2026-10-31 · no paid Wokwi runs. Order · the PO · 2026-11-06 · P649 before P648 #870 and P601 #802 (spark #871 comment) <!-- REQUIRED:decided -->
- Open questions: Q1 and the queue below <!-- REQUIRED:open -->
- Scope · out of scope (proposed): in: a flow in the C core (a velocity field plus the quantities it carries: heat, water, smoke), one field renderer (palette, alpha, filter), the flow strategies (row flows, curl noise, Stam's stable fluids), their board cost, and how P597 #798, P600 #801 and P647 #869 use it. Out: P628's on/off engine layers, P638's layer order, P601's 16-byte vectors, new effects past one proof scene (D1) <!-- REQUIRED:scope -->
- Start and reach (proposed until Q0): start existing product (pixel-games with the pixel-engine submodule), the PO's own idea · decider reachable yes · users the PO himself, on the board · data and connectors: the repositories and bench.md on disk, GitHub through gh; no analytics, none needed · decider as a user n = 1 · must not get worse: the fire's fps on the board (bench.md, P646) and the Mac tests of the C core <!-- REQUIRED:start-reach -->
- Flags (yes · no · —; asked only when it changes a decision; never legal advice; any date or threshold is read at its source at run time and cited):
  - sold or given away, or personal use: personal use, and public code under MIT (engine/LICENSE) <!-- REQUIRED:flag-sold -->
  - connects to a network or runs software (for example the EU's Cyber Resilience Act): runs software on one board, no network in this change · — for the Act, not needed for this decision <!-- REQUIRED:flag-network -->
  - children or food contact: no <!-- REQUIRED:flag-children -->
  - market: none, a hobby project <!-- REQUIRED:flag-market -->
  <!-- EXTEND:flags -->
- Extensions (each active id · the fact that activated it; when none matched, only "none matched: core only · the fact that decided it", naming no extension; list any directive skipped under rule 9): none matched: core only · the item is a software design question in pixel-games and its engine, with no hardware, part or electrical change (the probe found no extension fact in pixel-games, 2026-11-06) <!-- REQUIRED:extensions -->
<!-- EXTEND:frame -->
- Depth: TRIO (default: PO assistant, user, tech lead) | FULL or LIGHT (who asked, when); add "no independent review" if subagents could not start: LIGHT, one Sonnet agent for all four core lenses (the PO, 2026-11-06, D1); the refuter (step 6, Fable) is the second pair of eyes <!-- REQUIRED:depth -->
  <!-- Cost, measured once: the P900 rehearsal's council took 6 agents, 499 calls and about 90M input tokens (2026-10-06). -->
- Search budget: 6 web searches, all given to the LIGHT agent; used: see council/light.md, Searches <!-- REQUIRED:budget -->
- Appetite (the decider's, asked only when heading for design) | —: — <!-- REQUIRED:appetite -->

## What we found <!-- CLAIMS -->
<!-- One claim per line: `- [★C<n>] claim · E pointer | H source | D who date · caveat: qualifier | none`.
★ marks a claim that a decision, an option or the riskiest assumption rests on. A quote is verbatim, with its pointer.
Say what the evidence can support: an account (what happened to one person), data (how often, in its population and
period), a document (what was specified), the product (what exists, not whether anyone needs it), a benchmark (a
comparison). Model knowledge is H until a source is read. Elsewhere cite a ★ claim as ★C<n>, with its keep: words.
e.g. `- [★C2] 13 of 526 tickets ask for recurring tasks · E tickets.csv:2-14 · caveat: picked by Lena; shows that, not how often` -->
- [★C1] The fire's draw and blend read only the heat, the width, the height and the filter of the fire, plus the palette and the alpha passed in: `fx_fire_draw(const fx_fire_t *f, uint16_t *panel, const uint16_t *palette)` and `fx_fire_blend(..., const uint8_t *alpha)`, whose bodies start with `int32_t w = f->w, h = f->h` and branch on `f->filter` · E `engine/core/fx_fire.h:68`, `:74`; `engine/core/fx_fire.c:253-254`, `:284-285`; council/light.md EX-1 · caveat: that the output stays byte for byte after a move is untested <!-- REQUIRED:findings -->
- [★C2] The fire's step is already a pull advection: a cell reads the cells below it at a column moved by the wind and a random sway, and the fast patches read two rows down; the decay, the cooling map and the fade act on top · E `engine/core/fx_fire.c`, `fx_fire_step`'s row loop; council/light.md EX-2 · caveat: the lens's reading of the code; the order of the random draws is part of the byte contract (`fx_fire.c:12-30`)
- [★C3] Today a second effect is a copy, and a copied second field steps about 6.8 ms more: the step went from 7.92 to 8.08 ms (run119) to 14.51 to 14.84 ms (run120), and the scene from 23 to 24 fps to 23 fps · E `bench.md:593-594`, `:608` · caveat: one scratch probe with its own burns, linear mode
- [★C4] The fire as it is now (P646, linear) runs at 24 fps, step 7.91 to 8.06 ms, draw 13.21 to 13.78 ms, and its draw misses the P646 pass line by 0.28 ms · E `bench.md:647`, `:655` · caveat: two runs, run128 and run129
- [★C5] Internal RAM is the limit: the largest free internal block at the scene's start is 31,744 B, and a second 19,200 B field left 18,432 B; a velocity of two int8 per fire cell (160 x 120) is 38,400 B, more than the block · E `bench.md:294`, `:608`; H the 38,400 B by arithmetic · caveat: one firmware image
- [★C6] The two water cards name no velocity field: P597 asks for "a K4 spring surface that bodies drop into, with K2 splash droplets", and P600 for "the sand and water cells on K6" · E spark #798 and #801 bodies, read 2026-11-06 · caveat: K6 is not built, so whether it could read a flow is H
- [★C7] P647's prototype flow is a per-cell displacement inside the fire (`fx_fire_set_flow`, bend and wander), analytic, and marks itself as one "which a fluid layer can replace later (P649)" · E branch p647-motion in pixel-engine, `engine/core/fx_fire.c` and `.h`; council/light.md EX-3 · caveat: a prototype, its cost not measured (P647 finding, "Cost")
- [C8] Stam's "Real-Time Fluid Dynamics for Games" (GDC 2003) is a published solver of diffuse, project and advect steps; no licence statement for its code was found, and the repository writes methods again from their description · E council/light.md EX-10 (a mirror, read 2026-11-06); `engine/core/fx_fire.h:1-4` · caveat: the licence was not read at its source
- [★C9] Curl noise (Bridson, Hourihan and Nordenstam, ACM TOG 26(3), 2007) gives a flow without divergence from the curl of a smooth potential, with no solver · H council/light.md EX-11, the paper found by search and not read · caveat: not read
- [★C10] Cost estimates: one more carried quantity at 160 x 120 costs about a second field's step, +5 to 7 ms; Stam's solver on a 40 x 30 grid about 1.8 ms · H council/light.md FE-3, FE-4, derived from ★C3 (one probe) and about 370 ns a cell · caveat: no velocity read or solver step was ever timed on the board
- [C11] "Material" already names the contact material of the balls: `fx_balls_set_material(b, friction, restitution, restitution_threshold)` · E `engine/core/fx_balls.h:46`, `:73` · caveat: none
- [C12] P650 waits for this discovery: "do not spend long on code that P649 will redo. Refine this card after P649's discovery" · D the PO, 2026-11-06, spark #872 notes (council/light.md UJ-4) · caveat: none
- [C13] The PO judges a look on Mac clips (P647's three rounds), but the P639 flames that popped on and off showed only on the panel · E spark #869; `bench.md:600-601` (council/light.md RA-8) · caveat: n = 1

## Options <!-- CLAIMS -->
<!-- Two or three per open decision: decision · option · cost · what it would prove · opinion (whose), then the tag
and caveat cells. e.g. `- Q2 what first · fix delivery · two weeks · whether seen tasks get done · opinion (the facilitator's) · H ★C2 · caveat: none` -->
- Q2 the second material · A. a gas (smoke or steam) on the fire's flow · cost: the MVP below · proves: one flow and one renderer serve two materials (the card's proof) · opinion (Claude's) · E ★C2, ★C6 · caveat: the lens narrows "any material" to quantities a flow carries <!-- REQUIRED:options -->
- Q2 the second material · B. liquid water from P597 or P600 · cost: a spring surface or a cell automaton, a different model, P597 or P600 itself · proves: nothing about a shared flow · opinion (Claude's) · E ★C6 · caveat: K6 is not built
- Q3 what to build first · A. the field renderer alone (slice 0, first row) · cost: about a day, no new behaviour (H) · proves: the graphics half reuses, byte for byte · opinion: the safe first PR · E ★C1 · caveat: no physics reuse yet
- Q3 what to build first · B. the walking skeleton, all three rows of slice 0 in stages: renderer, flow with legacy and light strategies (P650's look), smoke · cost: about three days on the Mac and one board run (H) · proves: the card's "Value proven by" end to end, and A2's cost · opinion (Claude's): recommended, each stage a PR that keeps the fire byte for byte until the light strategy · E ★C1, ★C2, ★C7 · H ★C10 · caveat: cost untimed
- Q3 what to build first · C. P650 first as it is, then P649 · cost: P650's card, then a rework · proves: the light flow on the board soon · opinion: against the PO's "do not spend long on code that P649 will redo" · D C12 · caveat: none
- Q4 the byte test · A. a hard gate: a legacy strategy keeps every fire test · cost: one strategy more · proves: the refactor changes nothing until the light strategy · opinion (Claude's) · E `fx_fire.c:12-30` · caveat: A3 is untested
- Q4 the byte test · B. the look is the judge: tests are rewritten when the flow lands · cost: less code · proves: less; the tuned look can drift (council/light.md RA-7 item 3) · opinion: — · H · caveat: none
- Proposed no-gos and rabbit holes (proposals until the decider confirms): no-go: liquid water in this card (P597, P600 keep it); no-go: a velocity per fire cell (38,400 B, ★C5); no-go: a float solver (the bytes differ between Mac and board, council/light.md RA-5); rabbit hole: Stam's solver before the walking skeleton runs; rabbit hole: the word "material" for the carried quantity (C11), so "quantity" or "scalar field" instead, checked against the names table <!-- REQUIRED:nogos -->

## Riskiest assumption and its test
- Riskiest: A2, smoke carried by the fire's flow costs no more than a copied field (+6.8 ms step, 23 fps) · proposed — Claude's opinion, pending Q1 | D<n> <!-- REQUIRED:riskiest -->
- Test · kind · pass line, dated before any result · proposed | D<n>: one board run of the burning scene with smoke after slice 0's Mac work, 5 s log lines · a prototype on the board · step +7 ms or less and 23 fps or more, set 2026-11-06 · proposed <!-- REQUIRED:test -->

## Questions
<!-- A queue; the first open question is asked alone. Each: Q<n> · question · decides: … · options · unblocks ·
opinion (whose) · kind: decision | account (a past-tense question about the decider's own use; the answer is E,
account, n = 1) · status: queued | asked <date> | answered D<n>.
If the decider cannot be asked, the queue stays here, and whatever rests on it stays H. -->
- Q0 · Is this frame right: the decision, the start and reach, the extensions and the depth? · decides: the frame · status: answered D1 <!-- REQUIRED:q0 -->
- Q1 · How important is each assumption, and what pass line must the riskiest test meet? · decides: importance and pass lines · status: queued
- Q2 · Which second material comes first: a gas such as smoke or steam, or liquid water? · decides: the proof scene, and whether the MVP is a flow at all · options: A gas, B water · unblocks: items.md · opinion (Claude's): A · kind: decision · status: queued
- Q3 · What comes first: the renderer alone, the walking skeleton in stages, or P650 as it is? · decides: the first PR · options: A, B, C above · unblocks: items.md, P650 · opinion (Claude's): B · kind: decision · status: queued
- Q4 · Is the fire's byte test a hard gate until the light strategy? · decides: whether a legacy strategy exists · options: A gate, B the look judges · opinion (Claude's): A · kind: decision · status: queued <!-- REQUIRED:q1 -->

## Decisions
<!-- D<n> · what · who · when · where recorded · options considered.
A yes covers only the actions and choices it names. A standing yes names its kind of action and its source.
Name what a D confirms in its words: the frame, the jobs, a direction, the remaining risk, a test, items.md. -->
- D1 · the frame (decision, start and reach, no extension, scope) is right, depth LIGHT · Petr, the PO · 2026-11-06 · this session, Q0 · options considered: LIGHT, TRIO, change the frame

## Found on the way <!-- CLAIMS -->
<!-- Outside this item's scope. Each is a separate proposal, never folded in. Same line format as What we found. -->
- [C14] The panel is 240 x 320 and the fire field 160 x 120 (README.md:3, games/fire.py); the lens brief said "320x170-ish", a slip in Claude's prompt, not in the code · E council/light.md FE-1 · caveat: none <!-- REQUIRED:found -->

<!-- EXTEND:brief-sections -->

## Hand-off
<!-- Written only after the decider confirms the understanding (a D); copies only confirmed constraints. Holds: outcome ·
who · success and its proof · constraints (appetite, confirmed no-gos, rabbit holes) · what they said (D) against what
we assume (H) · links to the journeys and the map · riskiest assumptions and their tests · options considered. -->
not yet: Q1 to Q4 are open, and the PO has not confirmed the jobs or a direction <!-- REQUIRED:handoff -->

## Files
[Jobs and journeys](jobs-and-journeys.md) · [Story map](story-map.md) · [Risks and tests](risks-and-tests.md) · [Verification](verification.md) · [Items](items.md) · council/
