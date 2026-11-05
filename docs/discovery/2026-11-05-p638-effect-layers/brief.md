<!-- Resume: invoke product-discovery again; `discovery.py check <this folder>` names the next step. -->
# P638 ordered effect layers: discovery brief

<!-- Readiness, its one home. collecting evidence: anything short of the two below. an experiment: the decider chose
a test (a D) before choosing an option. design: the decider confirmed the frame, the jobs and a direction, and accepted
the remaining risk (D rows). An extension may tighten these. Next: design, or a chosen test of kind spike or prototype
→ the design skill the facts name, with this file; otherwise none, and the collection plan says who runs it.
Stands on: the assumptions not retired in risks-and-tests.md; of which those the decider rated high, or — while any
is unrated. check computes both. -->
**Ready for:** collecting evidence <!-- REQUIRED:ready -->
**Stands on:** 8 H, — of which would change the decision <!-- REQUIRED:debt -->
**Decision needed:** which layer design pixel-games builds first, and in which stages <!-- REQUIRED:decision-needed -->

## Frame
- Request, verbatim (corrections marked): "Remember that we'll also need to add fron layer effects, so like when things are on fire, i can only see the flames as if from behind it, but when somehthing is on fire, it cannot only be around it. And probably ew'll want to generalize this to adding layers to the effects so that we can intertwine multiple layers and even a python ldrawn layer in between two C layers etc, we'll dop ome good analysis and research and get inspired and design and plan this and add it to our low level pixel pack" (the PO, 2026-11-05, spark #853). Follow-up: "well, not necessarily the engine, split it into what belongs where, you know like something goes to the graphycs , some maybe to the driver or the binding, the python parts,,, lets stick to good reusable and changable architecture and industry standards for naming and such" (the PO, 2026-11-05, #853 comment). <!-- REQUIRED:request -->
- Decision · decider: which of the layer designs below pixel-games builds, and in what order of stages · Petr, the PO <!-- REQUIRED:decision -->
- Outcome and how it is observed (a metric with unit and source, a proof command, or a log): a burning body shows flames in front of it as well as behind it, judged by the PO on the board (P639 #854), and the burning scene keeps its fps within 2 of 24 to 25 (E bench.md:565-572, run117), read from the scene's 5 s log lines <!-- REQUIRED:outcome -->
- Already decided (D · who · when · where; include the product's stated non-goals and earlier decisions the request names): D-P628 · the PO · 2026-11-05 · plugins in the loop first (option C), then option A's C split (docs/discovery/2026-11-05-p628-engine-layers/README.md:185-187). D-P633 · the PO · 2026-11-05 · the stages FixedUpdate, Update, LateUpdate run in Game.step, and the render stays the game's (games/plugins.py:5-10). D12 · "C steps and paints, Python decides" (docs/engine-walkthrough.md:18). D-no-paid · the PO · 2026-10-31 · no paid Wokwi runs. No-goal: spark exports facts, never behaviour (AGENTS.md). <!-- REQUIRED:decided -->
- Open questions: Q0, Q1 below. Q2: must the body stay visible through the front flames (two passes), or may hot flames cover it (one pass)? Q3: is "our low level pixel pack" pixel-engine, with the split of the follow-up? <!-- REQUIRED:open -->
- Scope · out of scope (proposed): in: the order of draw layers in one frame, C and Python mixed, where each part lives (driver, C core, binding, Python), its board cost, prior art and a staged plan. Out: new effects, the figures of P635 themselves, PIE kernels (P583 #784), sound, a scene graph. <!-- REQUIRED:scope -->
- Start and reach (proposed until Q0): start existing product (pixel-games plus the pixel-engine and s3lcd submodules) · decider reachable yes · users the PO himself, on the board · data and connectors: the repositories and bench.md on disk, GitHub through gh; no analytics, none needed · decider as a user n = 1 · must not get worse: the three scenes' fps (bench.md:565-572), partial send (P533 slice 5), the Mac tests of the C core <!-- REQUIRED:start-reach -->
- Flags (yes · no · —; asked only when it changes a decision; never legal advice; any date or threshold is read at its source at run time and cited):
  - sold or given away, or personal use: personal use, and public code under MIT (engine/LICENSE, engine/driver/LICENSE) <!-- REQUIRED:flag-sold -->
  - connects to a network or runs software (for example the EU's Cyber Resilience Act): runs software on one board, no network in this change · — for the Act, not needed for this decision <!-- REQUIRED:flag-network -->
  - children or food contact: no <!-- REQUIRED:flag-children -->
  - market: none, a hobby project <!-- REQUIRED:flag-market -->
  <!-- EXTEND:flags -->
- Extensions (each active id · the fact that activated it; when none matched, only "none matched: core only · the fact that decided it", naming no extension; list any directive skipped under rule 9): none matched: core only · the item is a software design question inside one repository, with no hardware, part or electrical change, so no extension's trigger fact is present <!-- REQUIRED:extensions -->
<!-- EXTEND:frame -->
- Depth: TRIO (default: PO assistant, user, tech lead), but one agent (Fable, 2026-11-05) wrote all three lens reports in council/, so no independent review; the refuter (step 6) is the first second pair of eyes <!-- REQUIRED:depth -->
  <!-- Cost, measured once: the P900 rehearsal's council took 6 agents, 499 calls and about 90M input tokens (2026-10-06). -->
- Search budget: 8 web searches in total; used: 6 sources read through 9 fetch calls (3 were redirects), no search query <!-- REQUIRED:budget -->
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
- Q0 · Is this frame right: the decision, the start and reach, the extensions and the depth? · decides: the frame · status: queued <!-- REQUIRED:q0 -->
- Q1 · How important is each assumption, and what pass line must the riskiest test meet? · decides: importance and pass lines · status: queued <!-- REQUIRED:q1 -->
- Q2 · When a body burns, must it stay visible through the front flames, or may the hottest flames cover it? · decides: one draw pass or two (option A's cost) · options: cover · stay visible · unblocks: P639's slice 0 · opinion (the writer's): cover first, it costs nothing · kind: decision · status: queued
- Q3 · Is "our low level pixel pack" pixel-engine with the follow-up's split (driver, C core, binding, Python)? · decides: where the layer list lives · options: yes · a new package · unblocks: items.md · opinion (the writer's): yes, the follow-up says so · kind: decision · status: queued

## Decisions
<!-- D<n> · what · who · when · where recorded · options considered.
A yes covers only the actions and choices it names. A standing yes names its kind of action and its source.
Name what a D confirms in its words: the frame, the jobs, a direction, the remaining risk, a test, items.md. -->

## Found on the way <!-- CLAIMS -->
<!-- Outside this item's scope. Each is a separate proposal, never folded in. Same line format as What we found. -->
- ⟨fill⟩ | none <!-- REQUIRED:found -->

<!-- EXTEND:brief-sections -->

## Hand-off
<!-- Written only after the decider confirms the understanding (a D); copies only confirmed constraints. Holds: outcome ·
who · success and its proof · constraints (appetite, confirmed no-gos, rabbit holes) · what they said (D) against what
we assume (H) · links to the journeys and the map · riskiest assumptions and their tests · options considered. -->
not yet: Q0 (the frame), Q1 (the pass lines), Q2 and Q3 are unconfirmed, and the refuter has not run <!-- REQUIRED:handoff -->

## Files
[Jobs and journeys](jobs-and-journeys.md) · [Story map](story-map.md) · [Risks and tests](risks-and-tests.md) · [Verification](verification.md) · [Items](items.md) · council/
