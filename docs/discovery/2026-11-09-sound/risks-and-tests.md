# Risks and tests

## Risks
<!-- One row per type; an active extension adds its own rows. evidence now: tag and ids (★C<n>, A<n>).
status: open · retired · n/a because ….
e.g. `| usability | H no test yet (A2) | a five-person prototype test | open |` -->
| risk | evidence now | cheapest way to retire it | status |
| --- | --- | --- | --- |
| value <!-- REQUIRED:risk-value --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| usability <!-- REQUIRED:risk-usability --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| feasibility <!-- REQUIRED:risk-feasibility --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| viability <!-- REQUIRED:risk-viability --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| ethics and safety <!-- REQUIRED:risk-ethics --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| power and battery <!-- REQUIRED:electronics-firmware:power --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| current and stall <!-- REQUIRED:electronics-firmware:stall --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| thermal <!-- REQUIRED:electronics-firmware:thermal --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| EMC and ESD <!-- REQUIRED:electronics-firmware:emc-esd --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| sensor drift and calibration <!-- REQUIRED:electronics-firmware:sensor-drift --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| brown-out <!-- REQUIRED:electronics-firmware:brown-out --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| wake and low power <!-- REQUIRED:electronics-firmware:wake --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| the firmware–hardware contract <!-- REQUIRED:electronics-firmware:contract --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
| supply and documents <!-- REQUIRED:electronics-firmware:supply --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |
<!-- EXTEND:risk-rows --><!-- EXTEND:pair-rows -->

## Assumptions
<!-- About ten at most. type: value, usability, feasibility, viability or ethics. importance: "— (decider)" until
the decider rates it, then "high D<n>" or "low D<n>". pass line: written, with its date, before any result.
status: open, or retired with the date of its Results row.
e.g. `| A2 | Assignees never see new tasks | value | H ★C2 | — (decider) | query opened-within-48h | under 50 %, set 2026-10-06 | over 80 % | open |` -->
| id | belief | type | evidence now | importance | cheapest test | pass line, dated | result that would change the decision | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 <!-- REQUIRED:assumptions --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ | — (decider) | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ | open |

## Collection plan
<!-- One row per gap. e.g. `| Do assignees open new tasks? | Q2 | Lena, from analytics | one query | this week |` -->
| question | decision it blocks | who can answer | how | when |
| --- | --- | --- | --- | --- |
| ⟨fill⟩ <!-- REQUIRED:collection --> | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ | ⟨fill⟩ |

## Results
<!-- Filled on a return; may stay empty until then. One row per result: what was tested, what was seen (verbatim,
with its pointer), the pass line met or missed, what it changes. -->
| date | source and pointer | what was seen | pass line met or missed | what it changes |
| --- | --- | --- | --- | --- |

## Budgets <!-- REQUIRED:electronics-firmware:budgets -->
<!-- Energy per mode · peaks per rail against the source · dissipation per part, each number with its provenance and
the rung that would settle it (electronics-firmware:R<n>). "n/a — no battery, motor, radio or regulator" is allowed. -->
⟨fill⟩
<!-- EXTEND:risks-sections -->
