# Jobs and journeys
<!-- Tags as in the brief: E with a pointer, H with its source, D with who and when; an unknown is —. -->

## Who
<!-- One line per persona: who · evidence status (E pointer | H source). -->
- Petr, the PO, who builds scenes for the board with Claude and judges each look on Mac clips, then on the panel · E spark #869 and #872 (his look notes on P647's clips), bench.md:600-601 (the P639 flames he saw only on the panel) <!-- REQUIRED:who -->
- Claude, who writes the scene's code from his words and must not copy the fire's step for each new effect · E council/light.md UJ-1

## Jobs
<!-- One job story per line, each clause tagged: When …, I want to …, so I can …. -->
- Job 1 · When I want a second effect that moves like fire, for example smoke or steam [E spark #871, "other effects too, like qter, or other materials"], I want to give it its own look numbers and colours on the same flow [H the lens, UJ-2], so I can add it without a second copy of the fire's step and its 7 ms [E bench.md:594, :608] <!-- REQUIRED:jobs -->
- Job 2 · When I tune how the flames move [E spark #869], I want every flow number as a setting and Mac clips to pick from [E spark #872, "Needed by"], so I can say "less bend" and see it the next round [E spark #869, P647 rounds 1 to 3]
- Job 3 · When I add water from the side or sand and water cells [E spark #798, #801], I want them to reuse what the fire has [H the PO's "or other materials", spark #871], so I can keep the engine small · caveat: the lens reads both cards as a spring surface and a cell automaton, which read no velocity field (council/light.md RA-1, UJ-2)

## Today they…
<!-- Per job: what they do instead today (a competitor, a workaround or nothing), tagged. -->
- Job 1 · copy `fx_fire.[ch]` (389 + 101 lines), the `HeatField` binding and `FirePlugin` into a new effect, whose look numbers mean fire only · E `wc` of engine/core/fx_fire.c and .h; council/light.md UJ-1. A copy steps about 6.8 ms more (run120, one scratch probe) · E bench.md:608
- Job 2 · the P647 prototype on branch p647-motion: `fx_fire_set_flow(bend, rows, steps, width, wander)` inside the fire, not reusable · E council/light.md EX-3; docs/discovery/2026-11-06-p647-flame-motion/README.md
- Job 3 · nothing yet: P597 and P600 are open cards · E spark #798, #801

## Journeys
### The PO with Claude — add smoke over the burning scene <!-- REQUIRED:journey -->
| step | what they do | evidence | friction or harm | today | open question |
| --- | --- | --- | --- | --- | --- |
| 1 | asks for smoke that rises with the flames | H the PO's words, spark #871 | — | works | Is smoke the second material he wants first, or water? (Q2) |
| 2 | Claude copies the fire into a smoke effect | E council/light.md UJ-1 | about 600 lines copied, and eight look numbers that mean fire only | partly | — |
| 3 | the smoke moves on its own random sway, apart from the flames | E fx_fire.c, each field draws its own random numbers (council/light.md UJ-2 b) | the smoke does not follow the flames | not yet | — |
| 4 | Mac clips, the PO picks a look | E spark #869, P647 rounds 1 to 3 | — | works | — |
| 5 | one board run reads the ms and fps | E bench.md:594 (run120) | a second field costs about 6.8 ms and 1 fps | partly | What fps line holds for the proof scene? (Q1) |

```mermaid
flowchart LR
  s1["asks for smoke"] --> s2["Claude copies the fire"] --> s3["smoke sways on its own"] --> s4["Mac clips, he picks"] --> s5["board run: +6.8 ms, 23 fps"]
```
