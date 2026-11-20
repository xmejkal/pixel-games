# Risks and tests

## Risks
| risk | evidence now | cheapest way to retire it | status |
| --- | --- | --- | --- |
| value <!-- REQUIRED:risk-value --> | H the PO's "water, or other materials" (spark #871); E P597 and P600 read no velocity field (★C6) | ask Q2: which second material first | open |
| usability <!-- REQUIRED:risk-usability --> | E the PO picks looks on Mac clips (spark #869), but saw the P639 pop only on the panel (bench.md:600-601) | Mac clips, then one board look | open |
| feasibility <!-- REQUIRED:risk-feasibility --> | E a copied second field steps 6.8 ms more and drops to 23 fps (★C3); H a carried quantity costs about the same (★C10) | a Mac spike for bytes and looks, then one board run for ms (A2, A3) | open |
| viability <!-- REQUIRED:risk-viability --> | E a hobby project under MIT; H Stam's code licence is unknown (C8) | write each strategy from its published description and cite it | open |
| ethics and safety <!-- REQUIRED:risk-ethics --> | n/a because a hobby game on one board, no users but the PO, no data | — | n/a because no users or data |

## Assumptions
| id | belief | type | evidence now | importance | cheapest test | pass line, dated | result that would change the decision | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 <!-- REQUIRED:assumptions --> | The second material the PO wants first moves like a gas (smoke, steam), not like liquid water | value | H the lens, RA-1; ★C6 | — (decider) | ask Q2 | proposed: he names smoke or steam, set 2026-11-06 | he names P597's water or P600's cells: the MVP is then not a flow | open |
| A2 | Smoke carried by the fire's flow costs no more than a copied field: +6.8 ms step, 23 fps or more | feasibility | E ★C3 (one probe); H ★C10 | — (decider) | one board run of slice 0, like run120 | proposed: step +7 ms or less, 23 fps or more, set 2026-11-06 | worse than a copy: the layer adds cost, not reuse | open |
| A3 | A legacy flow strategy reproduces today's fire byte for byte | feasibility | E the rng draw order is part of the contract (fx_fire.c:12-30); H that a strategy can keep it (council/light.md FE-10) | — (decider) | Mac: tests/test_fire_core.py with the flow in place | proposed: all fire tests pass unchanged, set 2026-11-06 | bytes differ: the PO judges the look instead (Q4) | open |
| A4 | The renderer moves out of the fire byte for byte | feasibility | E ★C1; byte equality untested | — (decider) | Mac: the fire tests after the move | proposed: all fire tests pass unchanged, set 2026-11-06 | bytes differ: find the cause before slice 0 goes on | open |
| A5 | One renderer gives smoke a look the PO wants, from a palette and an alpha table | usability | H the lens, RA-4 | — (decider) | Mac clips of two or three smoke palettes | proposed: the PO picks one, set 2026-11-06 | none fits: smoke needs its own draw | open |
| A6 | A smoke layer with alpha above 0 at most heats keeps the draw within budget | feasibility | E P646's early-out skips 95 to 97 % of a front pass's cells only when the alpha is clear (council/light.md FE-7, bench.md:637-660) | — (decider) | the same board run as A2 | proposed: draw +3 ms or less, set 2026-11-06 | more: smoke drawn at half resolution or not at all | open |
| A7 | A coarse velocity grid (for example 40 x 30, 2,400 B) is enough for flames that cross and merge | feasibility | H the lens, FE-4 and FE-6; E a per-cell grid is 38,400 B, over the 31,744 B block (★C5) | — (decider) | Mac clip of slice 2 | proposed later, at slice 2 | flames still in columns: a finer grid in PSRAM | open |

## Collection plan
| question | decision it blocks | who can answer | how | when |
| --- | --- | --- | --- | --- |
| Which second material first? <!-- REQUIRED:collection --> | the MVP's proof scene (Q2) | the PO | Q2 in this session | 2026-11-06 |
| What fps and ms line holds for the proof scene? | A2's and A6's pass lines (Q1) | the PO | Q1 in this session | 2026-11-06 |
| Is the byte test a hard gate? | whether a legacy strategy must exist (Q4) | the PO | Q4 in this session | 2026-11-06 |
| What does smoke cost on the board? | A2, A6 | Claude, one board run | the burning scene with smoke, 5 s log lines | after slice 0's Mac work |

## Results
| date | source and pointer | what was seen | pass line met or missed | what it changes |
| --- | --- | --- | --- | --- |
