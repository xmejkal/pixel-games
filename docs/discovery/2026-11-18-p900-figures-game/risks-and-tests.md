# Risks and tests

## Risks
<!-- One row per type; an active extension adds its own rows. evidence now: tag and ids (★C<n>, A<n>).
status: open · retired · n/a because ….
e.g. `| usability | H no test yet (A2) | a five-person prototype test | open |` -->
| risk | evidence now | cheapest way to retire it | status |
| --- | --- | --- | --- |
| value <!-- REQUIRED:risk-value --> | H the PO's belief that bigger figures "sell it more" (A3, A4). C13 is one case where a small figure was misread. C20: after play he named other problems than size, in two other cases | the Mac picture, shown to him | open |
| usability <!-- REQUIRED:risk-usability --> | E ★C5, ★C6: no free button for the switch. H that the stick's up and down is enough (A2) | a prototype on the board with two placeholder figures | open |
| feasibility <!-- REQUIRED:risk-feasibility --> | E ★C2, ★C3, ★C4: the art is 2.6 times the pool. H that it fits after a hard reset (A1) | the board spike | open |
| viability <!-- REQUIRED:risk-viability --> | E `README.md:38`: CMU's page forbids resale "even in converted form" (A8) | re-read CMU's terms at their source if the game is ever sold | open |
| ethics and safety <!-- REQUIRED:risk-ethics --> | E https://github.com/xmejkal/spark/issues/1124: "The game shows no realistic suffering of people". Bigger, more real figures in rescue scenes come closer to that line | the design keeps P800's boundary as a no-go, on the PO's word | open |
| power and battery <!-- REQUIRED:electronics-firmware:power --> | — | n/a because the item adds no part, load or radio to the box | n/a because the item adds no part, load or radio to the box |
| current and stall <!-- REQUIRED:electronics-firmware:stall --> | — | — | n/a because the box has no motor |
| thermal <!-- REQUIRED:electronics-firmware:thermal --> | — | — | n/a because the item adds no part, load or radio to the box |
| EMC and ESD <!-- REQUIRED:electronics-firmware:emc-esd --> | — | — | n/a because the item adds no part, load or radio to the box |
| sensor drift and calibration <!-- REQUIRED:electronics-firmware:sensor-drift --> | H the user lens, USER-5: one inconsistent reading of the stick's "up" (`bench.md:1762-1765`, not re-read here) | ten deliberate up and down pushes logged on the board | open |
| brown-out <!-- REQUIRED:electronics-firmware:brown-out --> | — | — | n/a because the item adds no part, load or radio to the box |
| wake and low power <!-- REQUIRED:electronics-firmware:wake --> | E ★C7: a 5.5 s hold of D14 powered the board off (measured) | read the board's hardware revision, and keep a hold off PICK | open |
| the firmware–hardware contract <!-- REQUIRED:electronics-firmware:contract --> | E ★C5, ★C7: PICK and the knob belong to the app, and D14 also drives the power chip | the design names which input the game owns | open |
| supply and documents <!-- REQUIRED:electronics-firmware:supply --> | H tools-survey TOOLS-1: CMU's site gave a certificate error on 2026-11-18, and the files are only in a cache folder on this Mac | keep a list of the trials with their sha256 beside the painter | open |
<!-- EXTEND:risk-rows --><!-- EXTEND:pair-rows -->

## Assumptions
<!-- About ten at most. type: value, usability, feasibility, viability or ethics. importance: "— (decider)" until
the decider rates it, then "high D<n>" or "low D<n>". pass line: written, with its date, before any result.
status: open, or retired with the date of its Results row.
e.g. `| A2 | Assignees never see new tasks | value | H ★C2 | — (decider) | query opened-within-48h | under 50 %, set 2026-10-06 | over 80 % | open |` -->
| id | belief | type | evidence now | importance | cheapest test | pass line, dated | result that would change the decision | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 <!-- REQUIRED:assumptions --> | Two 96 px figures with enough poses fit the art memory and the frame time on the board, beside a background | feasibility | calculated ★C3, measured ★C4 and ★C8 for other loads | — (decider) | the board spike | set by the PO 2026-11-18 (D20, D19): 25 fps with two moving figures, the 2 MB pack in the pool, a load of about 2 s | the pool cannot grow, or the rate is under 25 fps: then the art shrinks or the drawing changes (Q4) | open |
| A2 | He can pick and switch a figure with the box's inputs and never switches by mistake | usability | E ★C5, ★C6; H the rest | — (decider) | a prototype with two placeholder figures, played by him | proposed 2026-11-18: 10 switches in a row with no wrong figure | he asks for a button the box does not have | open |
| A3 | At 96 px the motion capture's detail shows, and he likes it more than at 24 px | value | H his words; C13 one case; C21: the painter's lines have one width; D18: he wants faces, hands, clothes and gear too, so the painter must gain detail | — (decider) | the Mac picture and GIF, shown to him | proposed 2026-11-18: he says the detail shows | he sees no gain over 24 px | open |
| A4 | A mission where he switches between figures is fun for him on this box | value | H; C15 for other games | — (decider) | the first mission, played by him | proposed 2026-11-18: he plays the mission twice without being asked | he says it is not fun after two tries | open |
| A5 | A rule-based life (a state machine and steering) is enough for "their own lives" | feasibility | H tools-survey TOOLS-18; C12 | — (decider) | the second slice, seen by him | proposed 2026-11-18: he names nothing that looks dead or silly | he asks for behaviour that a rule cannot give | open |
| A6 | A figure part of pure logic fits the engine's boundary and leaves the old game's golden hashes unchanged | feasibility | E ★C9, ★C10; H the rest | — (decider) | move Meteors' walker onto it and run the golden net | proposed 2026-11-18: 0 changed hashes | a hash changes, or the game needs the figure to draw | open |
| A7 | The poses a mission needs (hold a ladder, climb, lift together) exist in CMU or can be posed by hand | feasibility | E `art/mocap.py:19-20`: the carry's arms were posed by hand | — (decider) | search CMU's index for the trials of the first mission | proposed 2026-11-18: a trial or a hand pose for each action of the first mission | no trial and no readable hand pose | open |
| A8 | The pictures painted from CMU's data may stay in a public repository | viability | E `README.md:38` | — (decider) | re-read the terms at CMU's site | proposed 2026-11-18: the terms allow the pictures in public | the terms forbid it | open |
| A9 | A figure that crosses the screen in about 1.5 s still leaves room for a mission on one screen | usability | calculated ★C11 | — (decider) | the Mac GIF with the real speed | proposed 2026-11-18: he does not ask for a scroll | he wants a scene that scrolls | open |

## Collection plan
<!-- One row per gap. e.g. `| Do assignees open new tasks? | Q2 | Lena, from analytics | one query | this week |` -->
| question | decision it blocks | who can answer | how | when |
| --- | --- | --- | --- | --- |
| Does a 2 MB pool leave the heap enough, and what is the frame rate with two 96 px figures? <!-- REQUIRED:collection --> | Q2, Q4 | the board, on the PO's bench | the spike's log | after his yes to Q2 |
| Which hand is free while he holds the stick? | Q5 | the PO | Q6, an account | when asked |
| Which hardware revision is his board? | Q5 (PICK) | the board record in spark's store | read the record | before the design |
| What do idle figures do in The Lost Vikings and Trine? | Q7 | a play video or a manual | one search with the page opened | before the design |
| Do CMU's terms today allow the painted pictures in public? | A8 | CMU's site | open the page in a browser, because the fetch failed | before any sale |

## Results
<!-- Filled on a return; may stay empty until then. One row per result: what was tested, what was seen (verbatim,
with its pointer), the pass line met or missed, what it changes. -->
| date | source and pointer | what was seen | pass line met or missed | what it changes |
| --- | --- | --- | --- | --- |

## Budgets <!-- REQUIRED:electronics-firmware:budgets -->
<!-- Energy per mode · peaks per rail against the source · dissipation per part, each number with its provenance and
the rung that would settle it (electronics-firmware:R<n>). "n/a — no battery, motor, radio or regulator" is allowed. -->
n/a — no battery, motor, radio or regulator is added or changed. The memory budget is ★C3 against ★C4 in brief.md.
<!-- EXTEND:risks-sections -->
