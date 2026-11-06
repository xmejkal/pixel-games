<!-- Resume: invoke product-discovery again; `discovery.py check <this folder>` names the next step. -->
# P649 one fluid layer: discovery brief

<!-- Readiness, its one home. collecting evidence: anything short of the two below. an experiment: the decider chose
a test (a D) before choosing an option. design: the decider confirmed the frame, the jobs and a direction, and accepted
the remaining risk (D rows). An extension may tighten these. Next: design, or a chosen test of kind spike or prototype
→ the design skill the facts name, with this file; otherwise none, and the collection plan says who runs it.
Stands on: the assumptions not retired in risks-and-tests.md; of which those the decider rated high, or — while any
is unrated. check computes both. -->
**Ready for:** ⟨fill⟩ <!-- REQUIRED:ready -->
**Stands on:** ⟨fill⟩ H, ⟨fill⟩ of which would change the decision <!-- REQUIRED:debt -->
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
- Q0 · Is this frame right: the decision, the start and reach, the extensions and the depth? · decides: the frame · status: answered D1 <!-- REQUIRED:q0 -->
- Q1 · How important is each assumption, and what pass line must the riskiest test meet? · decides: importance and pass lines · status: ⟨fill⟩ <!-- REQUIRED:q1 -->

## Decisions
<!-- D<n> · what · who · when · where recorded · options considered.
A yes covers only the actions and choices it names. A standing yes names its kind of action and its source.
Name what a D confirms in its words: the frame, the jobs, a direction, the remaining risk, a test, items.md. -->
- D1 · the frame (decision, start and reach, no extension, scope) is right, depth LIGHT · Petr, the PO · 2026-11-06 · this session, Q0 · options considered: LIGHT, TRIO, change the frame

## Found on the way <!-- CLAIMS -->
<!-- Outside this item's scope. Each is a separate proposal, never folded in. Same line format as What we found. -->
- ⟨fill⟩ | none <!-- REQUIRED:found -->

<!-- EXTEND:brief-sections -->

## Hand-off
<!-- Written only after the decider confirms the understanding (a D); copies only confirmed constraints. Holds: outcome ·
who · success and its proof · constraints (appetite, confirmed no-gos, rabbit holes) · what they said (D) against what
we assume (H) · links to the journeys and the map · riskiest assumptions and their tests · options considered. -->
⟨the hand-off | not yet: what is unconfirmed⟩ <!-- REQUIRED:handoff -->

## Files
[Jobs and journeys](jobs-and-journeys.md) · [Story map](story-map.md) · [Risks and tests](risks-and-tests.md) · [Verification](verification.md) · [Items](items.md) · council/
