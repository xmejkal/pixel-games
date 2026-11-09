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
| 18 | I recorded D5 from "alright, lets go on with the sound project now". That is a general go-ahead, and it covers the amplifier question only by inference. | this session | raised | I told the PO in the same turn. The bench work waits for the PO anyway. | Yes: a D needs the decider's words on that point. |
| 19 | I set the appetite to 3 days from a general OK on my proposal. The user lens warns that 3 days can be too short for the fire rounds. | this session, USER-17 to 20 | raised | Brief question Q4 asks how many rounds fit. | No |
| 20 | A worktree of pixel-games has no engine code until `git submodule update --init --recursive` runs. | this session | acted | I ran it before the lenses started. | No |

## Time

All times are Europe/Prague (+0100), from the commits of 2026-11-09.

| step | finished | what |
|---|---|---|
| 1 frame | 11:02:00 +0100 | the folder and the frame |
| Q0 | 11:18:33 +0100 | the PO's answer recorded |
| 3 lenses | 11:23:24 +0100 | three reports committed |
| 4, 5 synthesis | 11:34:57 +0100 | jobs, map, options, risks, items |

## Agents

The figures come from each agent's completion notice. The first three ran in parallel.

| agent | model | seconds | tool calls | tokens |
|---|---|---|---|---|
| user lens | Sonnet | 90 | 11 | 75,860 |
| PO assistant lens | Sonnet | 218 | 19 | 86,081 |
| tech lead lens | Sonnet | 243 | 25 | 125,415 |
| synthesis | Opus | 644 | 41 | 194,531 |
| total so far | | | 96 | 481,887 |
