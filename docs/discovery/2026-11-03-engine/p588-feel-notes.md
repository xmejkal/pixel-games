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
