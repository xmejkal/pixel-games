<!-- Resume: invoke product-discovery again; `discovery.py check <this folder>` names the next step. -->
# P586 a small game engine every game shares: discovery brief

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
- Request, verbatim (corrections marked): the PO's words of 2026-11-03, verbatim on [#787](https://github.com/xmejkal/spark/issues/787) (E). In short: refactor out the graphics and the physics, at least the C files; a simple game engine the games reuse, that grows with effects, tools and models as needed; an area-capture game built on it (original, not a copy of Xonix, P585 #786) and all games ported to it; map what we need, what exists to reuse, how others do it, the engine's architecture, full collaboration between Python and C, "be able to react both ways"; later physics and joystick control. On the order: "now, be able to react on physical events from python maybe, etc. I'd like the best council to research and analyse and propose and plan with me". Added during the frame (D2, 2026-11-03): "Later we might also add networking and multiplayer rsupport to the engine, or possibly  just first as an mvp separately but then integrate into the engine, also we can offer multiple methods, like ESP-NOW, or some other wayss, pure UDP, we'd see" <!-- REQUIRED:request -->
- Decision · decider: the engine's shape (its modules and their seams, what lives in Python and what in C, how C events reach Python), what its first slice holds, and the order of P584 #785, P587 #788, RENT P582 #783 and P585 #786 on it · the PO <!-- REQUIRED:decision -->
- Outcome and how it is observed (a metric with unit and source, a proof command, or a log): the PO confirms a brief with a needs map, a reuse map, two or three architecture options with a class and a sequence diagram, and proposed cards. Later the engine proves itself when RENT's rigid physics runs on it and Python code reacts to a C event (a landing, a tip-off), at no lower fps than today: stack 24.00 fps in bot run 52 (pixel-games bench.md, P582 section, measured), flappy 20 to 22 fps with framebuffer "double" (bench.md, P556 section, measured) <!-- REQUIRED:outcome -->
- Already decided (D · who · when · where; include the product's stated non-goals and earlier decisions the request names): the scope on #787 · the PO · 2026-11-03 · #787. The engine comes now, RENT's rigid physics (#783 decisions: overhang whole, tip by centre of weight, rigid thud, 3 lives, topple of rigid pieces) is its first user · the PO · 2026-11-03 · #787 comment. Effects move in C (Q13 yes) · the PO · 2026-11-02 · #771, pixel-games p580-finding.md. A piece enters the engine when a game needs it, never ahead · #787 "Done when". The C layer is where the public graphics library P539 #743 grows, one design · #787 Notes. The games keep their genre's mechanic but are original in name, art and levels · #769, #786. D1 frame (Q0 yes) and D2 networking later, below. <!-- REQUIRED:decided -->
- Open questions: which modules the engine has and which game needs each first; Python or C per module; the event path from C to Python (callback, queue, poll) and its cost per frame; what to reuse (MicroPython game libraries, small C engines) and under which licence; how the C split P587 meets the graphics library P539; where input (buttons, joystick) and sound (P581 #782) plug in; where networking (ESP-NOW, UDP) would plug in later. <!-- REQUIRED:open -->
- Scope · out of scope (proposed): in: the game loop and states, scenes and entities, graphics, effects, rigid 2D physics and collision, input (buttons now, a joystick later), a sound hook, Python and C events both ways, the seams for later networking; the ten games and the area-capture game as its users · out: a spark change, 3D beyond what space3d.py and world3d.py already do, building networking now (D2: later), a copy of any existing game. <!-- REQUIRED:scope -->
- Start and reach (proposed until Q0): start own idea (the PO's) · decider reachable yes · users the PO as player and game writer, and his sister as a player of the area-capture game (#786), n = 1 reachable · data and connectors: the pixel-games repository (code, tests, bench.md, run logs), the s3lcd fork in it, the web (search and fetch), GitHub (gh), Miro; no analytics or forum data connected · decider as a user n = 1 · must not get worse: today's games and their fps (stack 24, flappy 20 to 22, the games as they play now) <!-- REQUIRED:start-reach -->
- Flags (yes · no · —; asked only when it changes a decision; never legal advice; any date or threshold is read at its source at run time and cited):
  - sold or given away, or personal use: given away as open source (pixel-games is public, MIT) <!-- REQUIRED:flag-sold -->
  - connects to a network or runs software (for example the EU's Cyber Resilience Act): software; no network now, networking later (D2), read at its source only if it decides <!-- REQUIRED:flag-network -->
  - children or food contact: no food contact; a child may play (the sister's game), no decision rests on it now <!-- REQUIRED:flag-children -->
  - market: public on GitHub, worldwide <!-- REQUIRED:flag-market -->
  - radio (unlicensed-device rules; read at their source when it decides): no now; later ESP-NOW or Wi-Fi through the board's own module (D2), read at its source when that card starts <!-- REQUIRED:electronics-firmware:flag-radio -->
  - a Li-ion cell (charging, transport, battery rules): no <!-- REQUIRED:electronics-firmware:flag-li-ion -->
  - mains: no <!-- REQUIRED:electronics-firmware:flag-mains -->
  <!-- EXTEND:flags -->
- Extensions (each active id · the fact that activated it; when none matched, only "none matched: core only · the fact that decided it", naming no extension; list any directive skipped under rule 9): electronics-firmware · "at least the C files", "joystick controll support", "ESP-NOW" (firmware on the ESP32-S3, the C driver, input hardware, radio later); spark-process · "make an epic or update an epic", the item is on spark's board (project 2) <!-- REQUIRED:extensions -->
- The item (its issue, or the proposal in the decider's words) · what is still open elsewhere · the repository's push check, or "no push check here": [P586 #787](https://github.com/xmejkal/spark/issues/787), an epic in Discovery on spark project 2, under #769, slice pixel-games · still open elsewhere: P582 #783 in Build with draft pixel-games PR #10, P469 #637 and P511 #706 in Build, P565 games restyle and P539 graphics library discoveries in pixel-games · pixel-games has no push check: the folder lands by PR <!-- REQUIRED:spark-process:item -->
<!-- EXTEND:frame -->
- Depth: TRIO (default: PO assistant, user, tech lead) | FULL or LIGHT (who asked, when); add "no independent review" if subagents could not start: TRIO plus two researchers (D1, the PO asked for "the best council"): the PO assistant (Opus), the user (Sonnet), the tech lead with the physics lens (Opus), an engine-patterns researcher (Opus), a Python and C events researcher with the later networking seam (Opus); the refuter on Fable 5.1; 6 agents <!-- REQUIRED:depth -->
  <!-- Cost, measured once: the P900 rehearsal's council took 6 agents, 499 calls and about 90M input tokens (2026-10-06). -->
- Search budget: web searches: PO assistant 10, tech lead 8, engine patterns 14, events and networking 12, user 2, refuter 6 <!-- REQUIRED:budget -->
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

- D1 · the frame confirmed (Q0 yes): scope, start and reach, extensions, 6-agent council · the PO · 2026-11-03 · this session, AskUserQuestion · options: as written, FULL, change scope
- D2 · networking and multiplayer later (ESP-NOW, plain UDP, others), possibly first as a separate MVP that the engine absorbs; the architecture leaves a seam for it, nothing is built now · the PO · 2026-11-03 · this session, his message during the frame
- D3 · direction wish: the engine's core and its parts in C, highly optimized, with a MicroPython binding that lets the games use it easily, clearly and readably, and that is easy to extend; the PO's words: "Actually, it might make sense for the core of the engine and the various parts of it to be in C and higly optimised but the micropython have great binding and access to it, so the games really can interact with it easily and clearly and readably and its nicely extendable, etc" · the PO · 2026-11-03 · this session · the council tests it as the leading option beside others; it is not yet a chosen design

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
