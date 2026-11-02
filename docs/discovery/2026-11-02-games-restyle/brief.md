<!-- Resume: invoke product-discovery again; `discovery.py check <this folder>` names the next step. -->
# P565 games restyle: discovery brief

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
- Request, verbatim (corrections marked): "please prettyfy all the games, really try to mke them exciting and indie like artistic. Feel free to create a card for it and do all the planning and councils etc. And be really wild, I want it to be shoking and cool and beautiful with great physics like movement and well animated sprites. it can even be about some controversial political or social topic" (the PO, 2026-11-02, this session; card P565 #769) <!-- REQUIRED:request -->
- Decision · decider: which direction the restyle takes (one shared world or a theme per game, which theme or topic, which games first, how the art is made, which physics and animation each game gets) · the PO <!-- REQUIRED:decision -->
- Outcome and how it is observed (a metric with unit and source, a proof command, or a log): the PO plays each restyled game on the board and says it is exciting (his words, logged in bench.md); fps per game from the `time` log line does not fall below the P556 numbers (flappy 20 to 22, runner 21 to 24, stack 24, bench.md P556) <!-- REQUIRED:outcome -->
- Already decided (D · who · when · where; include the product's stated non-goals and earlier decisions the request names): first release = his games + a public showcase repo for job applications, not yet for other people (P539 D5, the PO, 2026-11-02, docs/discovery/2026-11-02-graphics-library/brief.md); the painted pencil-and-watercolour look of runner, stack and flappy, which he liked ("super cool, I love it", 2026-11-02, P562 #766); free tools, and a paid tool only after he hears its cost (rules.md, "Free, few and local"); docs come after, in P566 #770 <!-- REQUIRED:decided -->
- Open questions: one shared world across the games or a theme per game; which social or political topic, and how sharp; keep all ten games or drop or merge some; the art method (art/paint.py procedural painting, generated images, or both); sound (the board has no speaker today: —) <!-- REQUIRED:open -->
- Scope · out of scope (proposed): in: the look, theme, motion physics and sprite animation of the ten games in games/, and the art pipeline in art/. Out: driver speed work (P554 #758 and the P537 slices stay their own cards), new hardware, the GitHub docs (P566 #770), new game rules beyond what a theme needs <!-- REQUIRED:scope -->
- Start and reach (proposed until Q0): start existing product (ten games on the FireBeetle 2 with the GDI display) · decider reachable yes · users the PO, who plays on the board; viewers of the future showcase repo, none reachable · data and connectors: the board on USB with its time logs, the art pipeline art/paint.py, web search, Miro; image generation (ai-cli) available but its cost is not known, so not used without his yes · decider as a user n = 1 · must not get worse: fps and smoothness per game (P556 numbers), the PSRAM picture pool (1.6 MB art now) <!-- REQUIRED:start-reach -->
- Flags (yes · no · —; asked only when it changes a decision; never legal advice; any date or threshold is read at its source at run time and cited):
  - sold or given away, or personal use: personal use, and a public showcase repo under MIT later (P539 D5) <!-- REQUIRED:flag-sold -->
  - connects to a network or runs software (for example the EU's Cyber Resilience Act): runs software, no network use; not sold, so no decision rests on it <!-- REQUIRED:flag-network -->
  - children or food contact: no <!-- REQUIRED:flag-children -->
  - market: none (personal, showcase) <!-- REQUIRED:flag-market -->
  - radio (unlicensed-device rules; read at their source when it decides): no (the games use no radio) <!-- REQUIRED:electronics-firmware:flag-radio -->
  - a Li-ion cell (charging, transport, battery rules): — (the board can take one; the restyle changes nothing there) <!-- REQUIRED:electronics-firmware:flag-li-ion -->
  - mains: no (USB power) <!-- REQUIRED:electronics-firmware:flag-mains -->
  <!-- EXTEND:flags -->
- Extensions (each active id · the fact that activated it; when none matched, only "none matched: core only · the fact that decided it", naming no extension; list any directive skipped under rule 9): electronics-firmware · the games run on a board with fixed frame time and memory ("great physics like movement and well animated sprites" costs paint time); spark-process · "create a card for it and do all the planning and councils" <!-- REQUIRED:extensions -->
- The item (its issue, or the proposal in the decider's words) · what is still open elsewhere · the repository's push check, or "no push check here": P565 #769 (epic, Idea); open elsewhere: P556 PR pixel-games#1 waits on his play and merge, P564 #768 waits on his close verdict, P469 and P511 in Build; no push check in pixel-games <!-- REQUIRED:spark-process:item -->
<!-- EXTEND:frame -->
- Depth: TRIO (PO assistant, user, tech lead), plus one art-direction researcher, because the request is about look and feel (proposed) <!-- REQUIRED:depth -->
  <!-- Cost, measured once: the P900 rehearsal's council took 6 agents, 499 calls and about 90M input tokens (2026-10-06). -->
- Search budget: 12 web searches in all, for indie games with a social theme on small screens, and for physics and animation methods that fit a 40 ms frame <!-- REQUIRED:budget -->
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
- D1 · confirms the frame as written (scope all ten games, TRIO plus an art-direction researcher, 12 searches, no paid image tool without his yes) and yes to moving #769 to Discovery and running the council · the PO · 2026-11-02 · AskUserQuestion in the session · options: as written, TRIO only, narrow the scope

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
