# Risks and tests

## Risks
| risk | evidence now | cheapest way to retire it | status |
| --- | --- | --- | --- |
| value <!-- REQUIRED:risk-value --> | H the PO's words only; nobody saw a front blend (A1, A2) | P639 as option A on the board, the PO plays it | open |
| usability <!-- REQUIRED:risk-usability --> | H a layer list is one more class a scene writer adopts (A3) | write the four scenes' lists in a branch and count the lines lost against `paint` (A3) | open |
| feasibility <!-- REQUIRED:risk-feasibility --> | E ★C3 the blend stacks; E ★C4, ★C5 a blended pass fits the 14 ms; the burning scene never ran blended (A4) | one board run of option A with the fps line | open |
| viability <!-- REQUIRED:risk-viability --> | E one user story waits (P639, spark #854); H no scene needs two C layers yet (A5) | build slice 0 only until a second user exists | open |
| ethics and safety <!-- REQUIRED:risk-ethics --> | n/a because the change is a drawing order on the PO's own board | — | n/a because no person, data or network is touched |
<!-- EXTEND:risk-rows --><!-- EXTEND:pair-rows -->

## Assumptions
| id | belief | type | evidence now | importance | cheapest test | pass line, dated | result that would change the decision | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 <!-- REQUIRED:assumptions --> | One field blended over the body, after the body, reads as "on fire" to the PO | value | H his words, spark #853; U-5 names the harm | — (decider) | option A on the board, a Mac PNG first (prototype, n = 1) | the PO says it looks on fire, in his words, set 2026-11-05 | "the body is gone" or "still only around it" → Q2's two fields or a second alpha curve | open |
| A2 | The fps stays within 2 with the blend in the burning scene | feasibility | E C12 the fire scene 23 to 24 blended against 24 to 25; the burning scene not run | — (decider) | the same run's `burning linear fps` line | draw ms 13.5 or less and 23 fps or more over seven 5 s lines, set 2026-11-05 (the fps alone cannot fail: FRAME_MS 40 caps it at 25, `bench.md:435`) | 22 or less → option A needs the rect kernel (slice 2) before P639 ships | open |
| A3 | A layer list with an int `layer` is simpler for a scene writer than calls in `paint` | usability | H the agent's; P633's plugin list cost about 30 lines a game (`docs/discovery/2026-11-05-p628-engine-layers/README.md:170-171`, H there) | — (decider) | a branch with the four scenes' lists; count lines | each scene's `paint` shrinks or stays, set 2026-11-05 | a scene grows → option A stays the design | open |
| A4 | A C kernel that paints a rect and marks `frame_dirty(rect)` costs no more than today's whole-panel draw | feasibility | E C9, C10 the functions exist; H no measurement | — (decider) | the Mac test for the rect and one board run of the fire with a full rect | draw ms within 0.1 of run117 (`bench.md:568-571`), set 2026-11-05 | slower → keep `frame_dirty_all` for a full-panel layer | open |
| A5 | A second scene will want two C layers with a Python layer between | value | H no card names one; P616 is Idea (`docs/engine-deep-dives.md:256`) | — (decider) | ask the PO (Q9) and wait for a card | a card exists before slice 2 starts, set 2026-11-05 | none appears → slice 2 waits | open |
| A6 | Surfaces per layer are too costly for per-frame effects on this board | feasibility | E ★C6 16 ms once; H C7 6.8 ms by arithmetic | — (decider) | none needed now; a later card measures one surface composited | a composite under 3 ms would retire it, set 2026-11-05 | under 3 ms → option C comes back for live layers | open |

## Collection plan
| question | decision it blocks | who can answer | how | when |
| --- | --- | --- | --- | --- |
| How does a front blend look on a body? (A1) <!-- REQUIRED:collection --> | Q4, Q2 | the PO, on the board | P639 slice 0 (option A), a Mac PNG through `tools/render_scene.py` first | his next bench time |
| Does the burning scene hold 23 fps blended? (A2) | Q4 | the agent, with the board | the same run's fps line, seven 5 s lines | the same bench time |
| Which scene needs two C layers next? (A5) | slice 2 | the PO | Q9 | his next reply |
| Where does the blend kernel live? (Q5) | slice 3 | the PO | Q5 | his next reply |

## Results
<!-- Filled on a return; may stay empty until then. -->
| date | source and pointer | what was seen | pass line met or missed | what it changes |
| --- | --- | --- | --- | --- |

<!-- EXTEND:risks-sections -->
