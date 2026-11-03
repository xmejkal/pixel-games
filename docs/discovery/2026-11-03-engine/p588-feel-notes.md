# P588 (spark #789): the PO's feel notes on RENT, sorted under the draft engine

The desk test of A1 (D6, D7 in brief.md). Step 1 fixes the population and its count before any sort. Step 2 sorts each
note. Read 2026-11-03 by the desk-test agent (Opus 5.5). Times are Europe/Prague (CET).

## Step 1. The population

### Inclusion rule

- A feel note is the PO's own words about how RENT moves, feels, looks in motion, or how he wants it to behave physically.
- His words are of two kinds. V: a verbatim quote that a source marks as his. D: a decision recorded as "the PO's
  decisions". He chose it among options in the session, and the wording is the team's record of his choice.
- The GitHub author field does not tell him from the team, because the team posts as the same account (xmejkal). So
  the attribution in the text decides, never the author field.
- The same words quoted in two places count once, at the first dated post.
- One message gives one note per behaviour it states. A later message on the same behaviour is a new dated note.
- The time is the post time of the words on the issue. He said them in the session shortly before.

### Sources read

- spark #774 (body and 3 comments) and spark #783 (body and 7 comments), with timestamps from the GitHub API.
- bench.md on master and on origin/p582-heavy (21c0b09), the P568 and P582 sections.
- docs/discovery/2026-11-02-games-restyle/brief.md, decisions D1 to D15 and the findings that quote him.

### How the messages were split

- M1 (#774, 21:02): one behaviour, the slide. "yeah, its good" is a verdict on the game, not a behaviour, so it is
  excluded (see below).
- M2 (#783 body, 21:39): three behaviours. Bigger effects, heavy and natural movement, and bounces.
- M3 (#783, 08:30): two behaviours. The rods break off, and the whole pile shakes. The closing clause ("it just doesn't
  really seem like the real physics for the weight and material it would be") is the reason for both, not a third
  behaviour, so it stays inside notes 5 and 6.
- M4 (#783, 08:35): nine behaviours. Overhang: the floor stays whole, and it tips at the centre of weight. Landing:
  rigid, a thud, dust, a clang. Collapse: the lean from the weakest floor, the pivot as rigid pieces, the slide on the
  street.
- M5 (#783, 08:36): two physical behaviours. The tipped floor falls with a clang, and a lean of the floors above starts
  the topple. The rest of M5 is a game rule (see below).

### The notes

| # | his words | kind | source | time (Prague) |
| --- | --- | --- | --- | --- |
| 1 | "I don't like how it moves unpredictibly, we could change that back to the original linear motion" | V | #774 comment 6587153768. The same words in bench.md P568 (master and p582-heavy) and in the #783 body ("Earlier the same evening") | 2026-11-02 21:02 |
| 2 | "yeah bigger effects would be good" | V | #783 body, "The PO's words (2026-11-02, after playing RENT)" | 2026-11-02 21:39 |
| 3 | "also a really realistic movement. I woud like you to make it really natural moving, like it really is heavy" | V | #783 body, same quote | 2026-11-02 21:39 |
| 4 | "and bounces etc" | V | #783 body, same quote | 2026-11-02 21:39 |
| 5 | "with RENT, I feel like now it doesn't make sense that its'metal rods falling down but then they just break off" | V | #783 comment 6597958872 | 2026-11-03 08:30 |
| 6 | "or the whole pule shaes , it just doesn't really seem like the real physics for the weight and material it would be." | V | #783 comment 6597958872 | 2026-11-03 08:30 |
| 7 | "Overhang: steel does not snap. A floor stays whole and sticks out." | D | #783 comment 6598036562 | 2026-11-03 08:35 |
| 8 | "When its centre of weight passes the edge of what holds it, it tips over the edge and falls off as one piece (real stacking physics)." | D | #783 comment 6598036562 | 2026-11-03 08:35 |
| 9 | "Landing and collapse (asked twice, same answer): rigid. No spring and no wobble" | D | #783 comment 6598036562 | 2026-11-03 08:35 |
| 10 | "one short thud (the screen drops 1 or 2 px)" | D | #783 comment 6598036562 | 2026-11-03 08:35 |
| 11 | "a puff of dust" | D | #783 comment 6598036562 | 2026-11-03 08:35 |
| 12 | "a clang" | D | #783 comment 6598036562 | 2026-11-03 08:35 |
| 13 | "Collapse: the tower leans from its weakest floor" | D | #783 comment 6598036562 | 2026-11-03 08:35 |
| 14 | "and topples as rigid pieces that pivot on their edges" | D | #783 comment 6598036562 | 2026-11-03 08:35 |
| 15 | "then hit the street and slide to a stop" | D | #783 comment 6598036562 | 2026-11-03 08:35 |
| 16 | "the tipped floor falls with a clang" | D | #783 comment 6598053499 | 2026-11-03 08:36 |
| 17 | "The topple comes only when ... the floors above lean too far." | D | #783 comment 6598053499 | 2026-11-03 08:36 |

**The count is fixed: n = 17.** 6 notes are verbatim (V), 11 are his recorded decisions (D).

### Excluded, with the reason

- "yeah, its good" (#774, 21:02): a verdict on the whole game, not a behaviour.
- "Play goes on, a life lost: ... the player loses one of three lives, and the next floor hangs" and "The topple comes
  only when the lives run out" (#783, 08:36): game rules about lives and turns, not physical behaviour. Note 17 keeps
  the physical half of the last sentence.
- "go on Automatically until you're done with this ... have the PO assistant and the tech lead together decide for me"
  (#783, 2026-11-03 00:11): about the process, not about how RENT moves.
- "His next words asked for heavy, natural movement and bigger effects" (#774, 22:17) and the #783 "Done when" text:
  the team's restatements of notes 2 to 4, not his words.
- bench.md P568 quote: the same words as note 1, counted once. bench.md P582 holds no words of his ("He gave no words
  on the feel").
- Restyle brief D2 ("they would get added when something hits something or falls or shakes, is on fire, gets broken"):
  his words on effects for all the games, before RENT existed as a take. Not about RENT.
- Restyle brief "super cool, I love it" (P562): the still painted look of three games, not motion, and before RENT.
- "I want it to be shoking and cool and beautiful" (#774 body, from #769): the goal for the whole restyle, not RENT.
- Restyle brief D7 ("stack (RENT) is slice 0") and D9 (small rule changes): choices of scope, not feel.

## Step 2. The sort

### What the sort assumes

- The engine's rigid C mechanism exists (D7): rigid boxes, contacts, and the tip at the centre of weight.
- C reports four facts (tech lead TL-23, PHYS-3): contact (body and x, y), impact speed (px/s as an int), rest, and
  tip. Python reads the bodies' x and y to draw them (Option A's World_C, council/tech-lead.md part 1b).
- Python passes the numbers in, as `fall_bodies(bodies, dt, gravity, restitution, friction)` does today
  (origin/p582-heavy games/motion.py). PO-6: numbers from Python, never constants in C.
- A note is "new C" when it needs a mechanism or a fact that the draft lacks. When in doubt, it is new C.

### The table

| # | note (short) | sort | reason | C fact or Python hook | fact outside the four? | PO's mark |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | the slide moves linear, not unpredictable | Python number or reaction | The hanging floor's slide is the crane's sideways motion, not a body in the world. Its speed is a Python number. | the slide speed in Stack's play() | no | |
| 2 | bigger effects | Python number or reaction | "Bigger" is the size of the effect at a landing. Size and count are numbers that Python passes to the effect call. | on contact: fx(DUST, x, y, n, speed), P583 | no. New kinds of effect belong to P583's fx module, not to the rigid mechanism | |
| 3 | heavy, natural movement | Python number or reaction | Weight shows through gravity, restitution and the landing reactions (notes 9 to 12). All are numbers or reactions on facts. "Natural" in full is notes 7 to 15. | gravity and restitution passed to step() | no | |
| 4 | bounces | Python number or reaction | A bounce is restitution above 0. Note 9 later sets it to 0. That change is a number, which is what A1 claims. | restitution passed to step() | no | |
| 5 | the rods do not break off | Python number or reaction | The cut is Python game logic today. With rigid boxes the game stops cutting, and the floor stays one box. | Stack's landing code, no cut | no | |
| 6 | the whole pile does not shake | Python number or reaction | The shake is the Python Spring press and sway. Rigid boxes do not wobble, so the game removes the Spring. | remove motion.Spring from the landing | no | |
| 7 | a floor stays whole and sticks out | Python number or reaction | A box that rests on part of its support is plain rigid contact. No overhang fact is needed, because the tip (note 8) says when it falls. | contact, rest | no | |
| 8 | it tips at the centre of weight and falls off as one piece | Python number or reaction | This is the draft's tip, as named in D7. Python reacts to the tip and to the landing after it. | tip, then contact and impact speed | no | |
| 9 | rigid, no spring and no wobble | Python number or reaction | Restitution 0 and no Spring. Both are numbers or the removal of a Python reaction. | restitution 0 | no | |
| 10 | one short thud, the screen drops 1 or 2 px | Python number or reaction | Python moves the screen by 1 or 2 px for a short time when a landing is fast enough. The threshold and the offset are Python numbers. | contact, impact speed | no | |
| 11 | a puff of dust | Python number or reaction | Python starts the dust at the contact point. | contact x, y, then fx(DUST, ...) | no | |
| 12 | a clang | Python number or reaction | Python plays a sound, with the volume from the impact speed. The board has no speaker yet (restyle F7, D13). That is a hardware card, not an engine mechanism. | contact, impact speed, sound hook | no | |
| 13 | the tower leans from its weakest floor | new C mechanism | "Weakest floor" and "leans" need a fact about the whole stack above a floor: where the floors above hold their joint centre of weight against that floor's support. They also need a slow lean of many stacked bodies as one group. The draft's tip is one body, at rest or tipping. D7 names a lean fact as new C. Python can find the floor from x positions (PHYS-4), but it cannot make the group lean. | a lean fact or a group tip, and a way to start it on a chosen floor | yes, lean | |
| 14 | the tower topples as rigid pieces that pivot on their edges | new C mechanism | Many pieces turn and hit each other while they turn. That needs turned boxes in contact with turned boxes, an angle per body, and substeps (PHYS-1). The draft's tip is one box over one support edge. It is in doubt whether "rigid boxes, contacts" covers turned boxes against turned boxes, so it is new C. Drawing is not the issue: painted turned frames or fill_polygon with an angle exist (TL-24). | contact between turned boxes, body angle | yes, the angle and contacts between turned boxes | |
| 15 | the pieces hit the street and slide to a stop | new C mechanism | The hit is contact and impact speed. The slide is the doubt. Today a body that lands slowly stops dead (`fall_bodies` sets vx to 0 at rest), and friction acts only once per bounce. A slide along the street needs friction during a lasting contact. The draft names no friction, so it is new C. This is the closest call: if the draft's contact holds sliding friction, the note is a Python number. | sliding friction in a lasting contact, then rest | yes, sliding friction | |
| 16 | the tipped floor falls with a clang | Python number or reaction | Tip, then contact and impact speed, then the sound hook, as in notes 8 and 12. | tip, contact, impact speed | no | |
| 17 | the topple comes when the floors above lean too far | new C mechanism | "Lean too far" needs a lean of the floors above, which rigid boxes at rest do not have, and a measure of how far. D7 names a lean fact as new C. | a lean fact | yes, lean | |

### The result

- **k = 4 of n = 17 notes need a new C mechanism:** notes 13, 14, 15 and 17.
- The line is "at most 1 in 4". n / 4 = 17 / 4 = 4.25. k = 4, and 4 <= 4.25, so **the first clause holds on the team's
  sort.** The share is 4 / 17 = 23.5 %.
- The second clause, "he disagrees with at most 1 sort", is his to mark in the column "PO's mark".
- The margin is 0.25 of a note. One more note sorted as new C (k = 5) breaks the line.

### What the sort shows

- All 4 new C notes are about the collapse: the lean, the pivot of many pieces, and the slide. Every landing note
  (thud, dust, clang, rigid, bounce) is a Python number or reaction on contact and impact speed.
- Notes 4 and 9 contradict each other (bounces, then no bounce). The change between them is one number, restitution.
- All 4 new C notes are of kind D, his recorded decisions. None of his 6 verbatim notes needs new C.

### Rivals: what the result cannot show

- n = 1 person. The PO is the only source, so the result says nothing about another player's notes.
- One game. All notes are on RENT, a stacking game. Another game's feel notes may need other facts.
- The draft API is the team's. The tech lead wrote the four facts, and the same team sorted the notes. A sorter who did
  not write the API may sort differently.
- 11 of 17 notes are worded by the team. The D notes are the team's record of his choices among options that the team
  wrote. Words such as "centre of weight" and "pivot on their edges" may come from those options, not from him.
- The split rule moves the verdict. The rule counts one note per behaviour per message. If repeats across messages
  merge instead (note 5 into 7, note 6 into 9, note 16 into 8 and 12), n = 14 and n / 4 = 3.5. Then k = 4 fails the
  line, and k = 3 (note 15 as Python) holds it. The rule was fixed in step 1, before the sort (commit 227a591).
- Past notes may not predict later ones. A1 is about his later notes, once the engine exists. All 17 notes come from
  one evening and one morning, after one round of slices.
- The four facts are not the engine's full surface. Positions, and the angle for drawing, are state that Python reads
  beside the four facts. The sort treats reading x and y as given.
