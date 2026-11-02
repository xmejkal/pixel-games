<!-- Resume: invoke product-discovery again; `discovery.py check <this folder>` names the next step. -->
# P539 a public graphics library for small chips: discovery brief

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
- Request, verbatim (corrections marked): the PO's six messages of 2026-11-02, verbatim on [#743](https://github.com/xmejkal/spark/issues/743) (E). In short: research similar projects, decide what to reuse, mix or add; use each chip's special hardware and instructions (S3 AI instructions, later P4 and Pico); C and C++ usable from Arduino, fully usable from MicroPython, configurable; reuse, do not reinvent; good engineering, tests and refactoring from the start; good embedded standards, C++ if not much slower, the newest standard, embedded naming, comments kept current; an architecture that allows swap-ins and ports across chips, boards, firmwares and drivers; a story map with an MVP and later releases, cards, Miro, GitHub automation and released builds. <!-- REQUIRED:request -->
- Decision · decider: which library to build first (reuse, fork, wrap or new; its layers; its first targets and bindings) and what its MVP holds · the PO <!-- REQUIRED:decision -->
- Outcome and how it is observed (a metric with unit and source, a proof command, or a log): the PO confirms a brief with a reuse map, the chip hardware per target, a layer design, a story map with an MVP and later releases, and proposed cards (#743 "Done when"). The library later proves itself when the games run on it at a smooth pace on the FireBeetle 2 ESP32-S3 (P536 #740); the metric there is frame time in ms, measured with the bench probes in firebeetle-games `bench.md`. <!-- REQUIRED:outcome -->
- Already decided (D · who · when · where; include the product's stated non-goals and earlier decisions the request names): D1 the scope and wishes above · the PO · 2026-11-02 · #743. D2 the frame is a discovery (Q0 yes) · the PO · 2026-11-02 12:10 CET · #743. D3 good models, a council, a refuter and specialised agents · the PO · 2026-11-02 · #743. D4 the public driver is a fork of russhughes/s3lcd, and the upstream bug report waits · the PO · 2026-11-02 · #742. Earlier work it stands on: P533 #737 (Done, `frame.c` DMA send 31.0 ms, partial show), P537 #741 (finding `p537-finding.md` ed58361, in Review), P532 #735 (spark's multi-platform architecture page). <!-- REQUIRED:decided -->
- Open questions: what to reuse from which project; which layers and port interfaces; C or C++ and which standard; which chips and bindings come first; what the MVP holds; the repository name, boards and timing of P538 #742. <!-- REQUIRED:open -->
- Scope · out of scope (proposed): in: a 2D drawing library for small colour displays (shapes, sprites, text, tiles, transfer to the panel), its port layers, its MicroPython and Arduino bindings, its engineering practice and release plan · out (proposed): GUI widgets (LVGL's job), 3D, video decoding, sound, input handling beyond what the games need, a spark change. <!-- REQUIRED:scope -->
- Start and reach (proposed until Q0): start ⟨existing product | someone else's idea | own idea⟩ · decider reachable ⟨yes | no⟩ · users ⟨who, how | none reachable⟩ · data and connectors ⟨by category, from your own tool list; "not connected" is a gap; never ask to connect one⟩ · decider as a user ⟨n = 1 | no⟩ · must not get worse ⟨for an existing product⟩: start own idea (the PO's) · decider reachable yes · users the PO as a game writer on his FireBeetle 2 ESP32-S3 with the DFR0664 display, n = 1; no other users reachable · data and connectors: the firebeetle-games repository and its bench logs, the s3lcd fork, the web (search and fetch), GitHub (gh), Miro; no forum or analytics data connected · decider as a user n = 1 · must not get worse: the games as they run now (P533, flappy 21-24 fps at FRAME_MS 40, bench.md slice 4) <!-- REQUIRED:start-reach -->
- Flags (yes · no · —; asked only when it changes a decision; never legal advice; any date or threshold is read at its source at run time and cited):
  - sold or given away, or personal use: given away as open source (D1 "make it public") <!-- REQUIRED:flag-sold -->
  - connects to a network or runs software (for example the EU's Cyber Resilience Act): no network; it is software (whether the Cyber Resilience Act touches free open source is read at its source only if it decides) <!-- REQUIRED:flag-network -->
  - children or food contact: no <!-- REQUIRED:flag-children -->
  - market: public on GitHub, worldwide <!-- REQUIRED:flag-market -->
  - radio (unlicensed-device rules; read at their source when it decides): no (the library uses no radio) <!-- REQUIRED:electronics-firmware:flag-radio -->
  - a Li-ion cell (charging, transport, battery rules): no (the library does not charge or manage a cell) <!-- REQUIRED:electronics-firmware:flag-li-ion -->
  - mains: no <!-- REQUIRED:electronics-firmware:flag-mains -->
  <!-- EXTEND:flags -->
- Extensions (each active id · the fact that activated it; when none matched, only "none matched: core only · the fact that decided it", naming no extension; list any directive skipped under rule 9): electronics-firmware · "special chip specific instructions", "the AI chip or instructions that the S3 has", "P4, even raspberry pi pico" (firmware on hardware, DMA and panel buses); spark-process · "make cards", "story map", "agile"; the item is on spark's board (project 2) <!-- REQUIRED:extensions -->
- The item (its issue, or the proposal in the decider's words) · what is still open elsewhere · the repository's push check, or "no push check here": [P539 #743](https://github.com/xmejkal/spark/issues/743), an epic in Discovery on spark project 2 · still open elsewhere: P537 #741 in Review (waits on the PO's read), P469 #637 and P511 #706 in Build, P538 #742 with open answers; spark discoveries p100 and p218 still read "collecting evidence" · firebeetle-games has no remote and no push check: the folder lands by local commit, and the comment on #743 links it <!-- REQUIRED:spark-process:item -->
<!-- EXTEND:frame -->
- Depth: TRIO (default: PO assistant, user, tech lead) | FULL or LIGHT (who asked, when); add "no independent review" if subagents could not start: TRIO plus two specialised researchers (D3): the PO assistant (Opus), the user (Sonnet), the tech lead with the physics lens (Opus), a chip-hardware researcher (Opus), an open-source practice researcher (Sonnet); the refuter on Fable 5.1; 6 agents <!-- REQUIRED:depth -->
  <!-- Cost, measured once: the P900 rehearsal's council took 6 agents, 499 calls and about 90M input tokens (2026-10-06). -->
- Search budget: web searches: PO assistant 12, tech lead 10, chip hardware 12, practice 8, user 4, refuter 6 <!-- REQUIRED:budget -->
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
