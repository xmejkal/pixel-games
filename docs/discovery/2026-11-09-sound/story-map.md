# Story map
<!-- Proposed, not applied: this map stays here until the decider confirms it; nothing changes the product's own
map file. -->
**Status:** proposed, not applied <!-- REQUIRED:map-status -->

## Backbone
<!-- The activities, left to right, as the user does them. e.g. `Assign → Notice → Act → Close` -->
Wire and start → Hear a moment → Follow the fire → Swap the version → Compare and judge <!-- REQUIRED:backbone -->

The activities follow the two journeys in jobs-and-journeys.md.

## Slices
<!-- Walking skeleton first: the thinnest slice that runs end to end. One row per story. job: a job in
jobs-and-journeys.md. tag: as in the brief. proof: something the decider can read.
e.g. `| 0 | Notice | the assignee gets one daily digest | job 1 | H ★C2 | the digest log for one team |` -->
Slice 0 is the thinnest thing that runs end to end on the board, and each later slice adds one thing. The probe of the riskiest assumption (A1, items.md) comes before slice 0, because slice 0's buffer size rests on it. Every slice is a proposal. Q2 to Q5 are answered (D10 to D14). The order after slice 1 waits on the queue (Q7, Q6 and Q9 to Q15). If no measured result asks for slice 7, it does not exist.

| slice | activity | story | job | tag | proof |
| --- | --- | --- | --- | --- | --- |
| 0 walking skeleton <!-- REQUIRED:slices --> | Wire and start → Hear a moment | One game (BallPit) plays one fixed sound on a physics hit: the DFR0954 on the amplifier pins, stock `machine.I2S`, 16 kHz mono, one table of samples, a volume from the hit's speed. No mixing and no C | job 1 | H ★C2, ★C12, ★C18, ★C19 | the PO hears a hit on the board, and one row in `bench.md` holds the frame time beside `run130-p656-smoke.log` |
| 1 | Hear a moment | The naive Python version as Q2 defines it plays the same sound behind the interface Q5 picks | jobs 1, 3 | H ★C5 | one `bench.md` row for the Python version, with the same event script |
| 2 | Swap the version | The C version in `engine/core/` with `binding.c` and a Mac test, swapped in with one import | jobs 3, 4 | E ★C11, H ★C5 | a second `bench.md` row, and the game's code unchanged in the diff |
| 3 | Compare and judge | The bench row gains its gap source and its latency, as Q4 decides. Chosen (D6, D12): a microphone beside the speaker, a round module that matches the INMP441, on the second I2S controller gives the gap count that the stock class lacks. Q9 asks which instrument the A1 test uses | job 4 | E ★C6 (dry blocks), ★C26 (marking is unread) | the two rows, each with the columns Q4 names |
| 4 | Hear a moment | A cap on sounds at once, and bursts of hits, as Q5 picks | job 1 | E ★C12 | the PO's words on a ball pit pour, and the row's CPU at the cap |
| 5 | Follow the fire | Fire sound as wav files on the Mac, A to E, with no board and no engine change | job 2 | H ★C14, ★C16, E ★C15 | the PO's pick, in the PO's words |
| 6 | Follow the fire | The picked fire sound runs on the board and reads a few numbers from the fire | job 2 | E ★C13 | the PO's verdict on the board, and the frame time against run130 |
| 7 | Swap the version | If a measured result fails A1 or Q4's line, an own I2S task, and a driver repository when D1's condition holds | jobs 3, 4 | E ★C7, H ★C4 | a `bench.md` row that shows the gain on the same script |
| 8 | Hear a moment | Sound in the other games, one by one. If Q-U6 asks for a mute, the mute too | job 1 | H USER-2, USER-8 | the PO plays each game |

<!-- EXTEND:map -->
