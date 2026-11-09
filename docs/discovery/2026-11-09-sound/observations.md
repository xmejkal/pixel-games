# P729 sound for the games: rows

These rows record the gaps, bugs, work and time of the sound epic, as the work happens. The PO will analyze them
later and update spark from them (the PO, 2026-11-09). Card: [P729 #997](https://github.com/xmejkal/spark/issues/997).

This file stays in pixel-games while the other session refactors spark. When that work ends, the rows move to spark's
`docs/observations/rows/p729-sound.md`. The status column uses raised, verified, acted, rejected or closed.

## Rows

| # | claim | source | status | evidence / where it went | for spark |
|---|---|---|---|---|---|
| 1 | `gh project item-list --limit 600` did not show the new card, and gave no error. The board holds 610 items. | this session | verified | A direct GraphQL read of the item showed its fields. | Yes: find each board reader with a fixed limit. |
| 2 | The REST call that creates a view returned 404 with the numeric user id. The same call worked with the login. | this session | verified | Views 4 and 5 exist. The call used `/users/xmejkal/projectsV2/2/views`. | Yes: note it for any tool that writes views. |
| 3 | pixel-games has no push hook. `.git/hooks` holds only samples, and `core.hooksPath` is empty. The merge rule asks for "The push hook passed". | this session | verified | The push of 2026-11-09 printed no hook output. | Yes: decide what the gate is in a project repository. |
| 4 | The limits count the whole board, so two sessions can take each other's places. | the PO | acted | The PO split them into two lanes. P730 #998 holds the card. | Yes: P730. |
| 5 | Two sessions take card numbers from one sequence. | this session | acted | I read the highest number just before I filed P729. P730 followed it. | Yes: a tool can give out the number. |
| 6 | The frame named "underruns per minute", but `machine.I2S` has no underrun counter. The PO confirmed the frame before the lenses ran. | tech lead FEAS-1 to 4, 9 | raised | Brief question Q4 proposes a change. | Yes: a frame metric needs a named source. |
| 7 | The frame lacks a latency figure and a listening test. | PO assistant, user | raised | Brief question Q4. | No |
| 8 | The tech lead wrote that mono expands to stereo on transmit. The synthesis found this wrong. | synthesis, ★C3 | raised | The refuter tests it. | Yes: a lens error passed until a later step. |
| 9 | The PO assistant used a worst frame of 57 ms. The synthesis read 105 ms in Road in run130. | synthesis, ★C1 | raised | The refuter tests it. | No |
| 10 | The PO assistant wrote that Python cannot loop per sample. The synthesis calculated 27.5 µs per sample of room for one voice in Fire. | synthesis, ★C5 | raised | The refuter tests it. Brief question Q2 defines "naive". | No |
| 11 | `games/pins.py` and `games/gdi.py` disagree on the display pins. The header of `pins.py` says spark generated it. The code runs `gdi.py`. | tech lead PHYS-10 to 12, synthesis ★C19 | raised | The refuter tests it. | Yes: a generated pin map went stale beside the real one. |
| 12 | The MAX98357 does not support 22.05 kHz. | tech lead PHYS-2 | raised | The reading stays unproven until someone re-reads the current datasheet. | Maybe: the part record can hold sample rates. |
| 13 | The speaker FIT0502 has no part record, and the revision of the PO's board is not recorded. | tech lead PHYS-4 to 8 | raised | A look at the bench can settle the revision. | Yes: drawer items without a part record. |
| 14 | The drawer assigns both amplifiers to other projects. | drawer record `dfrobot-dfr0954.json` | acted | D5 uses the one assigned to p581-sound-joystick. | Maybe: reassigning a part has no command that I used. |
| 15 | The tech lead used 1 of 5 searches. It did not settle whether the S3 has a DAC, or how many I2S controllers it has. | tech lead report | raised | I settle this with one read at the reproduction step. | No |
| 16 | The synthesis agent added a `## Searches` part to the user lens report, to clear a line that `discovery.py check` printed. A lens report belongs to its lens. | synthesis agent | raised | The added part says "none" and holds no finding. | Maybe: the lens prompt asks for that part, and the user lens left it out. |
| 17 | The simple-english hook counts verbatim quotes and the required unknown marker as faults. It reported 13 hits on the card, 138 on the user report and 233 on the tech lead report. | hook output | verified | I kept the quotes and the markers unchanged. | No: this is the plugin's rule. |
| 18 | I recorded D5 from "alright, lets go on with the sound project now". That is a general go-ahead, and it covers the amplifier question only by inference. | this session | acted | The PO's photo of the amplifier, with "the modules I want to use", now gives the PO's own words. | Yes: a D needs the decider's words on that point. |
| 19 | I set the appetite to 3 days from a general OK on my proposal. The user lens warns that 3 days can be too short for the fire rounds. | this session, USER-17 to 20 | raised | Brief question Q4 asks how many rounds fit. | No |
| 20 | A worktree of pixel-games has no engine code until `git submodule update --init --recursive` runs. | this session | acted | I ran it before the lenses started. | No |
| 21 | The PO's photos show the display on a flat cable to the board's GDI connector. This supports `gdi.py` as the real pin map, and not `pins.py`. | photos, 2026-11-09 | raised | It adds to row 11. `gdi.py` lines 15 to 19 name pins 3, 38, 18, 9 and 21. | Yes: same as row 11. |
| 22 | The PO wants to use an I2S microphone, but the frame lists microphone input as out of scope. | photos, "the modules I want to use" | acted | The PO, 2026-11-09: a game input comes later, and the test instrument is worth a try. The brief changes after the refuter ends. | Yes: a frame written before a look at the bench missed a part. |
| 23 | The photos show no model name on the microphone. Its pads read SD, VDD, GND, L/R, WS and SCK. The drawer holds 3 of `dfrobot-sen0526`, an I2S microphone, with no part record link. | photos, drawer | raised | Rows 35 and 36 settle the identity by a match, and the chip's own marking is unread. | Yes: a drawer item without a part record. |
| 24 | The photos show no jumper wires to the amplifier or the microphone. The speaker plugs into the amplifier. | photos | raised | The pin list comes before the wiring. | No |
| 25 | The PO's idea: a microphone and a camera as test instruments on the bench, and perhaps later part of spark. | the PO, 2026-11-09 | acted | Card P731 #1000 holds the PO's words. It joined the board at 12:21 +0100, after the wait in row 26. | Yes: P731. |
| 26 | GitHub refused GraphQL calls with "API rate limit already exceeded for user ID 631808." at 11:48 +0100. The limit is shared with the other session. | this session | raised | `rate_limit` printed a reset at 12:19:16 +0100. I wait for the reset. My 2,000-item board listing used several pages. The share of each session is unknown. | Yes: board readers need a cost limit. |
| 27 | All three lenses missed AMY, an MIT synthesizer in C that runs on the S3. Only the refuter found it. | refuter ★C8 | acted | Brief question Q3 now holds it as option P4. | Yes: a fresh adversary found what the reuse search did not. |
| 28 | My brief to the agent named the repository `shortwave/amy`. The real one is `shorepine/amy`. | correction agent | verified | The agent found and used the right repository. | No |
| 29 | Road's 105 ms frame holds a state change. Frames during play reach 69 ms. | refuter ★C1 | acted | Brief question Q7 asks which of these the buffer covers. | No |
| 30 | `discovery.py check` read a quoted fill marker in the refuter's report as an unfilled slot. The agent changed that quoted token. | correction agent | raised | `council/refuter.md:3` | Maybe: the skill's tool. |
| 31 | `discovery.py check` wants each keep phrase on every line that cites a claim, so citing lines carry extra words in brackets. | correction agent | raised | `brief.md` | Maybe: the skill's tool. |
| 32 | A fresh agent reproduced the starred claims, and I did not. The skill says "yourself". 22 of 22 reproduced, and 3 of them have limits. I read only the pin path myself. | this session | raised | `verification.md`, `games/lcd.py:199-206`, `games/gdi.py:15-19` | Yes: the rule can say who reproduces the claims. |
| 33 | The microphone's pads read SD, VDD, GND, L/R, WS and SCK. The SEN0526 page reads 3V3, GND, SCK, SEL, WS and DO. DFRobot's photo shows a rectangular board, and the PO's module is round. It is another part. | correction agent, then this session | verified | https://wiki.dfrobot.com/sen0526/ read 2026-11-09. The orders list no other microphone, and a search of AliExpress orders found no order (row 37), so where the module came from is unknown. Its chip marking is unread (row 35). | Yes: a drawer match by function is not an identity. The drawer lacks this part. |
| 35 | The PO's round microphone matches the module sold as INMP441. A seller's photos show the same shape, notches, ring, sound hole and pad order. The chip's own marking is unread. | this session | verified | https://www.universal-solder.ca/product/inmp441-digital-mems-microphone-omnidirectional-i2s/ read 2026-11-09, and the PO's photos. | Yes: a comparison with a seller's photo identified a part with no chip marking. |
| 36 | The INMP441 datasheet gives VDD 1.62 V to 3.63 V, and 3.63 V is the absolute maximum, so 5 V is out. It needs 64 SCK cycles per WS frame, so `machine.I2S` receives 32-bit words. | DS-INMP441 rev 1.1, CERN copy | verified | `pdftotext` of the copy. The datasheet asks for a 100 kΩ pulldown on SD, and the module's resistor value is unread. | Yes: these facts belong in a part record. |
| 37 | AliExpress redirected to its sign-in page in Chrome, so the search of the PO's orders did not run. | this session | acted | The PO then signed in. A search for INMP441 over the last year, and for microphone over the last 2 years, found no order. The page offers no longer range, so the seller and the count stay unknown. | Yes: the drawer import needs a signed-in browser, and old orders fall outside AliExpress search. |
| 38 | The `identify` steps 3 and 4 did not run: no part record and no drawer entry exist yet. | this session | raised | Owed in the next session. | Yes: the part is still missing from the drawer. |
| 39 | The microphone can miss the gaps it measures. A stall that starves the output also delays the input on the same loop. | refuter, second pass | raised | The next correction round adds an assumption row. | Yes: an instrument needs its own test. |
| 40 | GPIO12, 13 and 4 or 14 also reach the GDI connector. Only an unproven record says that this display leaves them unused. DFRobot's page and the board record disagree on D5, D6 and D10. | refuter, second pass | raised | The tone test settles the pads. | Yes: the board record and the maker's page disagree. |
| 41 | `~/.local/share/spark/boards` holds no pin data for the FireBeetle, and the pins are in the spark repository's `boards/`. My first read failed on this. | this session | verified | `boards/firebeetle2-esp32s3.json` in `~/Development/spark`. | Yes: name one home for board records. |
| 42 | A board listing of 900 items failed with a rate limit error while `rate_limit` still showed 3,765 points left. This is a second limit that the counter does not show. | this session | verified | Card P733 #1003 was already filed. I stopped calling the API. | Yes: list the board less often, and filter on the server. |
| 43 | The PO asked to see the findings with diagrams. The discovery's files are too long to read for that. | the PO, 2026-11-09 | acted | https://claude.ai/artifact/E7Po7kRqDyCkAxj4GLRpCg, private to the PO. | Yes: a discovery can end with a one-page summary. |
| 34 | The second pass of the refuter waits until after Q1, so that one pass covers all changed sections. | this session | acted | Step 8 of the discovery. | No |

## Time

All times are Europe/Prague (+0100), from the commits of 2026-11-09.

| step | finished | what |
|---|---|---|
| 1 frame | 11:02:00 +0100 | the folder and the frame |
| Q0 | 11:18:33 +0100 | the PO's answer recorded |
| 3 lenses | 11:23:24 +0100 | three reports committed |
| 4, 5 synthesis | 11:34:57 +0100 | jobs, map, options, risks, items |
| 6 refuter | 11:52:37 +0100 | the report committed |
| 6 corrections | 12:06 +0100 | corrections, AMY, pin proposal, reproduced claims |

## Agents

The figures come from each agent's completion notice. The first three ran in parallel.

| agent | model | seconds | tool calls | tokens |
|---|---|---|---|---|
| user lens | Sonnet | 90 | 11 | 75,860 |
| PO assistant lens | Sonnet | 218 | 19 | 86,081 |
| tech lead lens | Sonnet | 243 | 25 | 125,415 |
| synthesis | Opus | 644 | 41 | 194,531 |
| refuter | Opus | 1,022 | 38 | 236,861 |
| corrections and reproduction | Opus | 810 | 31 | 225,071 |
| refuter, second pass | Opus | 431 | 20 | 153,754 |
| corrections after the second pass | Sonnet | 272 | 15 | 119,366 |
| total so far | | | 200 | 1,216,939 |
