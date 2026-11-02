# Risks and tests

## Risks
<!-- One row per type; an active extension adds its own rows. evidence now: tag and ids (★C<n>, A<n>).
status: open · retired · n/a because ….
e.g. `| usability | H no test yet (A2) | a five-person prototype test | open |` -->
| risk | evidence now | cheapest way to retire it | status |
| --- | --- | --- | --- |
| value <!-- REQUIRED:risk-value --> | H: the pull is the PO's wish, n = 1 (★C22); his logged verdicts are about smoothness, none calls the flat seven boring (★C14); whether a reflex game can carry a theme is untested (★C19; A1, A2) | slice 0 played blind by the PO (A1, A2), a use log n = 1 | open |
| usability <!-- REQUIRED:risk-usability --> | E ★C11 (shared title and over shell, 900 ms lock), ★C12 (plain motion); H user.md USER-5, USER-6: detail under about 8 px and busier backgrounds at 150 to 520 px/s may not read, not seen on the panel (A9) | the same slice 0 play; the account questions Q10, Q15 | open |
| feasibility <!-- REQUIRED:risk-feasibility --> | E ★C3, ★C4 (no frame-time headroom; full send caps scrolling games near 29 fps), ★C5 (blit costs, internal destination only), ★C6 (PSRAM, calculated), ★C13 (Python body cost, bounded) (A3, A4, A5) | one board probe session (electronics-firmware:R6): PSRAM-destination blits, a partly off-screen blit, the Python cost of a picture draw, `esp32.idf_heap_info` after `pool(5 MB)`, `os.statvfs("/")`, a timed body-update loop | open |
| viability <!-- REQUIRED:risk-viability --> | H: paint.py grows by 1,155 to 2,030 hand-written lines for seven games (★C9); the generated-image route has no importer and an unknown cost (★C10); the licence of generated art in a public MIT repo is — (A6, A7) | hours logged on slice 0; ai-cli's cost read and told before any run; the PO's rule on job-application cost (Q4) | open |
| ethics and safety <!-- REQUIRED:risk-ethics --> | H po-assistant.md PO-30 and art-direction.md ART-19: aim at systems and situations, never at real people, parties or groups; a shock topic may cost the PO in a job application (PO-22) (A7, A8) | Q4 with the PO: his rule and his list of what is off limits; one search per chosen premise (A8) | open |
| power and battery <!-- REQUIRED:electronics-firmware:power --> | — | — | n/a because the board is USB-powered in play and the restyle changes no hardware; a Li-ion is — in the brief's flag and unchanged by this item |
| current and stall <!-- REQUIRED:electronics-firmware:stall --> | — | — | n/a because no motor or actuator is involved |
| thermal <!-- REQUIRED:electronics-firmware:thermal --> | — | — | n/a because no hardware changes and the chip already runs at the frame pace (★C3); no new load is added |
| EMC and ESD <!-- REQUIRED:electronics-firmware:emc-esd --> | — | — | n/a because no hardware changes; the SPI clock stays at the measured 40 MHz (★C4) |
| sensor drift and calibration <!-- REQUIRED:electronics-firmware:sensor-drift --> | — | — | n/a because the games read no sensor |
| brown-out <!-- REQUIRED:electronics-firmware:brown-out --> | — | — | n/a because no new load joins the rail |
| wake and low power <!-- REQUIRED:electronics-firmware:wake --> | — | — | n/a because the restyle does not touch the power-off path (games/app.py:121-124, a long D14 hold) |
| the firmware–hardware contract <!-- REQUIRED:electronics-firmware:contract --> | E ★C4 (the real SPI clock is 40 MHz; 80 MHz gave a dark panel), ★C23 (31,744 B largest internal DMA block after "double"; a kept background must live in PSRAM); the panel DFR0664 has no tearing-effect line (tech-lead.md PHYS-7) | nothing to retire: fixed limits the art plan is sized against; the probe above confirms the PSRAM costs | open, as a constraint |
| supply and documents <!-- REQUIRED:electronics-firmware:supply --> | — | — | n/a because no new part; the board and panel are the ones in hand |
<!-- EXTEND:risk-rows --><!-- EXTEND:pair-rows -->

## Assumptions
<!-- About ten at most. type: value, usability, feasibility, viability or ethics. importance: "— (decider)" until
the decider rates it, then "high D<n>" or "low D<n>". pass line: written, with its date, before any result.
status: open, or retired with the date of its Results row.
e.g. `| A2 | Assignees never see new tasks | value | H ★C2 | — (decider) | query opened-within-48h | under 50 %, set 2026-10-06 | over 80 % | open |` -->
| id | belief | type | evidence now | importance | cheapest test | pass line, dated | result that would change the decision | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 <!-- REQUIRED:assumptions --> | A one-button reflex game with no text and no sound can carry a social theme that the player reads while playing | value | H ★C19 (no such reference game found in two searches), ★C20 (no speaker); po-assistant.md PO-18 | — (decider) | slice 0: one game, one theme pass, played blind by the PO; a prototype test, n = 1 | proposed 2026-11-02, pending Q1: without being told the theme, he names the system it aims at in his own words, logged in bench.md | he names nothing, or only the picture: the theme moves to the title and over cards, or goes mild | open |
| A2 | "Wild and shocking" and the painted look he loved can come out of one pipeline and still read as beautiful | value | H ★C15 (the approved style sentence is "gentle and charming"); po-assistant.md PO-10 | — (decider) | the same slice 0 play; his verdict | proposed 2026-11-02, pending Q1: his verdict is "exciting" or stronger, in his words | "pretty but flat" or "cheap": a different look (Q3) or a milder take (Q4) | open |
| A3 | The new art keeps fps at or above the P556 numbers in play | feasibility | E ★C3 (no headroom, measured without play), ★C4 (calculated cap near 29 fps for scrolling games) | — (decider) | the `time` log line during the slice 0 play, before and after the pass | proposed 2026-11-02, pending Q1: average fps in play not below the same game's fps before the pass; for flappy, runner, stack not below 20 to 22, 21 to 24, 24 | a drop beyond what Q8 allows: the scrolling games wait for P556 #760, P554 #758, P555 #759 | open |
| A4 | Ten games' art fits the PSRAM pool and the flash file system | feasibility | calculated ★C6 (5.02 MB against 6,813,040 B free; the heap split and the file-system size are —) | — (decider) | `esp32.idf_heap_info` after `pool(5 MB)` plus `gc.mem_free()`; `os.statvfs("/")`; one board session (R6) | proposed 2026-11-02: a 5.5 MB pool allocates with the heap still able to run a game, and the file system has 5 MB free | it does not: a palette-limited look (B or C), fewer frames, shared layers (W), or fewer games | open |
| A5 | Springs, bodies and 40 particles in Python fit in a few ms per frame | feasibility | calculated ★C13 (about 2 us per simple statement; 30 bodies 0.75 to 1.5 ms; statement count and float boxing H) | — (decider) | a timed loop of one body update and one spring on the board | proposed 2026-11-02: 30 bodies plus 40 particles' motion under 3 ms per frame | over 3 ms: a viper fixed-point integrator, or the C-emitter question (Q13) | open |
| A6 | paint.py scales to ten games at an effort the PO accepts | viability | H ★C9 (1,452 lines for three games; main() hard-codes them) | — (decider) | hours logged on slice 0, after the data-table refactor (P572) | proposed 2026-11-02: one game's layers, sprites and cards in one working session | several sessions per game: generated backgrounds (Q7), a cheaper look (B), or fewer games (Q10) | open |
| A7 | A sharp theme costs the PO nothing in a job application | viability, ethics | H po-assistant.md PO-22, PO-30; nobody of the reader group is reachable | — (decider) | Q4: his rule and his list of what is off limits; each theme row checked against it | proposed 2026-11-02: every chosen theme passes his written rule, and none names a real person, party, group or event | he wants mild only: the alt themes (art-direction.md table) replace the sharp ones | open |
| A8 | Each game's theme is original: no known game has the same premise and verb | ethics, viability | H art-direction.md table ("as far as I know; not searched per theme") | — (decider) | one web search per chosen premise (a spike, P577) | proposed 2026-11-02: no released game found with the same premise and the same player verb | a match: the alt theme, or a new one | open |
| A9 | Painted title and over cards carry the theme at no cost to play | usability | E ★C11 (title 1500 ms, over 900 ms; text costs about 2.5 ms per run; the over box paints in 33 to 54 ms) | — (decider) | one card on the board in slice 0, its paint time in the `time` log | proposed 2026-11-02: the card paints in less than today's 33 ms over box, and he reads its lettering at arm's length | slower or unreadable: lettering as sprites, fewer frames | open |
| A10 | Stills of restyled games persuade a hiring manager in 30 seconds | value | H jobs-and-journeys.md job 2; user.md USER-10, USER-11; nobody of this group was asked | — (decider) | none reachable now; P566 #770 owns the page; a secondhand check later | none set, 2026-11-02: no reader is reachable; set when one is | — | open |

## Collection plan
<!-- One row per gap. e.g. `| Do assignees open new tasks? | Q2 | Lena, from analytics | one query | this week |` -->
| question | decision it blocks | who can answer | how | when |
| --- | --- | --- | --- | --- |
| What do the blit primitives cost into a PSRAM destination, and a partly off-screen blit, and a picture draw through Python? <!-- REQUIRED:collection --> | the per-game frame budget (Q8, Q9, Q12) | the facilitator, on the board (P567) | a loop of `blit_buffer` calls under `framebuffer="double"`, as run34/run35 did | before slice 0 is sized |
| How much PSRAM does the pool have after the heap, and how big is the file system? | A4; one city vs a theme per game (Q2); keep all ten (Q10) | the facilitator, on the board (P567) | `esp32.idf_heap_info` after `pool(5 MB)`, `gc.mem_free()`, `os.statvfs("/")` | the same session |
| What does one body update and one spring cost in Python on this build? | A5; Q13 | the facilitator, on the board (P567) | a timed loop | the same session |
| What is the fps of flappy and runner in play with the P562/P564 art? | A3's baseline; Q8 | the PO, playing (bench.md:177 "waits on the PO's play") | the `avg ... static paint fx hud` line while he plays | his next bench time |
| Which games did he play longest and leave first; which did he show someone, and what did they say? | Q6 (first game), Q10 (keep all ten) | the PO | the account questions Q15 (user.md 1 to 11) | at Q1 or after |
| What does ai-cli image generation cost per picture? | Q7 (art method) | the facilitator, reading the tool's price page | one read, the figure told before any run (D1) | if Q7 keeps the route open |
| Does any released game share a chosen premise and verb? | A8; the theme rows | the facilitator (P577) | one search per premise | after Q2 to Q4 |

## Results
<!-- Filled on a return; may stay empty until then. One row per result: what was tested, what was seen (verbatim,
with its pointer), the pass line met or missed, what it changes. -->
| date | source and pointer | what was seen | pass line met or missed | what it changes |
| --- | --- | --- | --- | --- |

## Budgets <!-- REQUIRED:electronics-firmware:budgets -->
<!-- Energy per mode · peaks per rail against the source · dissipation per part, each number with its provenance and
the rung that would settle it (electronics-firmware:R<n>). "n/a — no battery, motor, radio or regulator" is allowed. -->
Energy, rails and dissipation: n/a — no battery, motor, radio or regulator changes; the board is USB-powered in play and no hardware changes. The budgets this item spends are frame time and memory, measured by the tech lead (council/tech-lead.md, the budget table):
- frame pace 40 ms (stated, games/app.py:26); step plus paint 39 to 43 ms with no play (measured, origin/p556-double-buffer bench.md); fps 20 to 24 (measured); worst gap 63 to 69 ms (measured); headroom none (calculated);
- full-frame send 30.72 ms calculated at the real 40 MHz, 31.0 to 33.5 ms measured (bench.md:33, :84); copy into the outgoing buffer 3.2 to 3.4 ms (measured);
- blit: opaque 34.5 ns/px, keyed 51.6 ns/px upper bound, translucent 126 ns/px (measured, internal destination, bench.md:167, :170); PSRAM destination +8.4 to +9.7 ms per frame on the same art (measured, P556 slice 0), per primitive — (R6 settles it, P567);
- memory: art 1,506,384 B for three games (measured, bench.md:176); ten games about 5.02 MB (calculated); PSRAM free 6,813,040 B (measured, IDF, heap split —); internal DMA largest block 31,744 B after "double" (calculated from probe0-memory.log:1); file-system size — (R6: `os.statvfs("/")`); firmware image 1,867,376 B with 229,776 B free in the app partition (measured, bench.md:6).
<!-- EXTEND:risks-sections -->
