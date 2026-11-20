# Refuter: P900, the figures game (2026-11-18)

Read in ~/Development/pixel-p900 at HEAD 5eebd6e, on 2026-11-18 from 09:27 Prague time, for about 25 minutes. Nothing ran on a board, nothing
was posted, no git command wrote. I wrote this one file. Verdict words: holds · partly · refuted · could not open.

## Check first: existing product

Does the change address the observed problem?

- The observed problem is one sentence of one person, said after he read the engine's README: "ours are tiny and one
  doesn't appreciate the details so much" (#1279 body). No play account and no visitor stands behind it
  (council/user.md USER-10, USER-22: "No visitor's reaction is recorded anywhere I read").
- The problems the PO reported after play are other ones: "I dont get the rescue game, it doesnt work" (PO-21 e, #1124)
  and "No the game is not exciting, its still just not much fun" (USER-6). The brief carries neither. A 96 px figure
  answers neither.
- Possibly the detail is not in the pictures. The painter draws limbs as lines of a constant width
  (`art/sets/rescue.py:197`: "THIGH_W, SHIN_W, FOOT_W, UPPER_W, FORE_W, TORSO_W = 2.8, 2.3, 2.2, 2.3, 2.0, 4.2  # px, at
  the final size") and a head as an ellipse. At 96 px a bigger schematic figure is a possible result. The user lens's question
  AQ-12 ("which details did you mean you could not see?") decides this, and the brief's queue does not hold it.
- No option keeps play small and shows the detail elsewhere (a 96 px figure on the title, the pick card or a
  close-up). It costs no pool, no frame time and no input. The folder does not rule it out.

What breaks for the current user and the fifteen games?

- A pool of about 2 MB is held for every game (TECH-5. The brief carries this in one option's caveat only).
- P822 (#1175) asks "whether a 4 MB picture pool fits beside the heap" for keeping the lineup's sets in memory
  (PO-9). A 2 MB figure pack and P822 want the same PSRAM. The brief lists P822 in C19 as an overlap "by title" and
  does not state the conflict.
- The load: TECH-10 computes 1.6 to 2.2 s for a 1.9 to 2.2 MB pack. The README says "every set loaded in under 0.6 s"
  (`README.md:383`). The frame's "must not get worse" names each set's load time, and the proposed pass line allows
  2.5 s for the new set. The brief does not say that the new game breaks the README's sentence.
- PICK or the knob given to a game changes how he leaves a game and where the volume is, in all games (TECH-13 misfit
  3). A mirror flag is a firmware flash for all games. The golden net runs on the Mac, so it does not cover the flashed
  driver (not checked by me: I did not read the net's scope for C).
- P800's boundary ("The game shows no realistic suffering of people: nobody is drawn burning, and no child or grandma
  screams in pain or cries for help while burning", #1124, read by me) is carried in risks-and-tests.md. Holds.

## 1. The ★ claims, each against its source

- ★C1 · holds. `art/export.py:21`: `"""Game image (w, h) -> panel bytes (h by w after a 90 degree turn), RGB565
  big-endian."""`. `art/sets/rescue.py:172`: `FIG_H = 26  # px from the soles to the helmet's top, standing`. `:181`:
  `SIZES = {"run": (26, 30), "turn": (26, 30), "spray": (40, 30), "carry": (30, 30)}`. `:593`:
  `out.update({"rescue_%s_l%d" % (cycle, i): ImageOps.mirror(img) for i, img in enumerate(right)})`. "No compression"
  is not in the cited lines. A grep for zlib, deflate and compress in `art/*.py` and `games/pictures.py` printed
  nothing, and TECH-1's sum of w x h x 2 matches the pack.
- ★C2 · partly. `games/pictures.py:44-45`: "It is made once, as big as the largest pack, and every set is read into it
  in turn." `ls -l games/packs`: `739216 ... runner.pak`, `660008 ... rescue.pak`. But `:50-52` says: "a pool a soft
  reset kept smaller (ValueError): a bytearray instead". So a bigger pack without a hard reset still loads, into the
  Python heap (where P562 measured "733 KB in the heap made each collection cost about 90 ms", `:44`). Sentence to
  change: "so a bigger pack needs a hard reset" → "so a bigger pack loads into the heap, with a slower collection,
  until a hard reset". Why: a spike that forgets the hard reset passes its load and measures the wrong memory.
- ★C3 · partly. The arithmetic reproduces (part (b) below). The claim is narrower than the brief uses it:
  1. The card records the PO's answer as "about 96 px, four times today's 24 px" (#1279, comment 6972668412). Four
     times is the tech lead's second column: 2,239,488 bytes, 3.03 times the pool (TECH-4). The brief chose 96/26 and
     offers in Q3 only "the figure, the picture". The reading the card's words give is missing.
  2. "2.6 times today's pool" compares figure pictures with a pool that holds a whole pack. With Rescue's street
     (153,600 bytes, TECH-1) the same cut is 2,067,552 bytes, 2.8 times.
  3. The cut is not the mission the PO chose. His example is the fireman who holds a ladder and the grandma who
     climbs (#1279, the same comment). The cut holds the fireman's run and spray and the man's run and wave. It has
     no turn (170,496 bytes, TECH-4), no idle cycle (the brief's own walking skeleton, "stands and breathes"), no
     ladder hold and no climb. USER-17 says "no idle pose set exists".
  4. The man is scaled by the fireman's factor. His look is 25 px tall (`art/sets/rescue.py:397`), so he comes out
     at 92 px. The granny (22 px) at 81 px.
  Sentence to change: "come to 1,913,952 bytes, 2.6 times today's pool" → "come to 1,913,952 bytes at 96/26 or
  2,239,488 at four times (his recorded words), 2.6 to 3.0 times today's pool before the background, and this cut
  holds none of the cycles his example mission or the idle figure needs".
- ★C4 · partly. `bench.md:214`: "Memory after deinit ("double" run; "dma" within 420 B): PSRAM free 6747500.00 B, its
  largest block 6553600.00 B; ... a 4,000,000 B bytearray allocates (the substitute for A4's pool test: a larger pool
  needs a hard reset, so not run). Flash file system 12800000.00 B free of 14680064.00 B; art on the board
  1507152.00 B." The line does not say 8 MB (that is `bench.md:43`, "the whole 8 MB PSRAM heap", and the board
  record in TECH PHYS-1). "Art on the board 1507152 B" is in the sentence about the flash file system. That it was
  loaded comes from `bench.md:212` ("art load at start (pictures.load, 1507152.00 B)"). The brief drops "after
  deinit". Sentence to change: "With a 1,507,152 byte art set loaded" → "After a run that loaded a 1,507,152 byte art
  set, measured after the display's deinit". Why: what deinit frees was not read, so it is possible that the row overstates what is free
  while a game runs.
- ★C5 · partly. `games/app.py:334`: `pressed, switched = actions.fire.pressed, actions.pick.pressed and
  len(self.games) > 1  # one game: no pick`. `:336`: `self.knob.poll(now, actions.turn)  # --- MVP (P764) ---`. The
  lines show that the app acts on PICK and the knob. They do not show that a game cannot read them: `games/app.py:242`
  hands the game the whole record (`game.stick = self.action_map.actions if self.action_map.stick else None`), and
  USER-1 ends "Does not support that they cannot be rebound". Sentence to change: "A game cannot use PICK or the knob
  today" → "A game can read PICK and the knob, but the app acts on both in the same frame (it switches the game and
  moves the volume)". Also dropped: FIRE has two bindings, BOOT and the stick's switch (USER-3), see part (c).
- ★C6 · partly. `games/rescue.py:566`: `events = rules.step(self.ms, held, None if self.stick is None else
  lean(self.stick.x))`. `games/meteors.py:380`: `rules.walk(self.ms, lean(self.stick.x))`. "Free" is narrower than it
  reads: the PO's example mission has a climb, which is the stick's up. USER-3 says a pad with no stick reads "about
  +21 drifting". USER-23 says the genre switches "at the touch of a button". `bench.md:1764-1765`, which the brief
  did not re-read, I read: "In run 1 the push meant as up read `JOY_X` high, against run 2's clear hold; run 2 is
  kept." Sentence to add to the caveat: "the example mission's climb wants the same axis".
- ★C7 · holds. `bench.md:58`: "USB dropped after about 5.5 s of steady hold. The board record says why
  (`hardware_revisions`, V1.1 and earlier): D14 also drives the AXP313A's PWRON through a diode, so a long press powers
  the board off." The date is the heading at `bench.md:47`: "Slice 3 continued, 2026-11-02". One hold, n = 1.
- ★C8 · partly, and its second sentence is not supported by the cited lines. Read: `:84` "switch rescue 1428 ms, load
  638 ms". `:86` "time rescue step 5.9 paint 33.0 send 4.0 gc 7.2 fps 18 worst 150". `:88` "avg rescue static 16.4
  paint 14.5 fx 0.7 hud 1.5 over 0.0 title 18.4". `:91` "time rescue step 8.4 paint 26.8 send 3.7 gc 7.5 fps 19 worst
  84". `:93` "avg rescue static 8.5 paint 16.4 fx 0.9 hud 0.8 over 0.0 title 0.0". And outside the cited range `:95-96`
  "fps rescue 20 ... step 9.4 paint 25.7". Three things:
  1. No line says "game over". The second and third windows average `over 0.0 title 0.0` and a step of 8.4 and 9.4 ms.
     Flappy, which `bench.md:1657` alone calls "idle, on its game-over screen", shows `step 0.8` to `1.7` and `over
     15.4` to `34.7` (`:104-111`). `bench.md:1656` calls Rescue only "idle". The rival that the folder does not rule
     out: Rescue ran its rules untouched (the fireman runs by himself on the button's path, the people run), which is
     play with six small figures and nobody steering. I did not prove it: the over box is cached (`games/gfx.py:441`,
     `cv.keep`), so `over 0.0` alone does not decide.
  2. The range drops the third window: 18 to 20 fps (as `bench.md:1656` and PO-7 say), paint 25.7 to 33.0 ms.
  3. The 18 is the window that holds the title and the build (`title 18.4`, slowest frame 146 ms).
  Sentence to change: "are from its title and game-over screens ... No row has Rescue in play" → "are from an idle
  run that nobody steered: the first 5 s window holds the title (18 fps), the next two show no title and no game-over
  painting (19 and 20 fps); whether the rules ran in them was not checked". Why: the pass line's 18 fps rests on it.
- ★C9 · partly. `games/rescue.py:179`: `return self.ran * RUN_POSES // STRIDE_PX % RUN_POSES`. `:182`, `:212`, `:834`
  the same shape. `games/meteors.py:249`: `return (x if right else -x) * RUN_POSES // STRIDE_PX % RUN_POSES`.
  Meteors takes the pose from the position x with a sign, not from the px run. `:165` and `:220`: `px = self.rest //
  1000`. Sentence to change: "is written four times in Rescue and once in Meteors" → "... and once in Meteors from the
  position x, not from the px run". Why: the facilitator proposes Meteors as the proof (Q8), and a part built on `ran`
  must also give Meteors' pose bit for bit (A6's pass line is 0 changed hashes). Dropped beside it: the cycles that run
  on time and not on distance (`games/rescue.py:215`, `self.wave_ms * WAVE_POSES // WAVE_MS % WAVE_POSES`, and the
  spray).
- ★C10 · holds. `tests/test_engine_boundary.py:23`: "# The modules each package module may import besides BUILT_IN:
  other modules of the package and the C module.". `:27`: `DIRECTION = {"__init__": (), "signals": (), "clock": (),
  "accel": ("_engine",), "actions": (), "subpixel": ()}`.
- ★C11 · holds as arithmetic, partly as a reading. `games/rescue.py:39`: `SPEED_PX_S = 56  # his run: the motion
  capture's 3.6 m/s at 24.07 px a body height`. 56 x 96/26 = 206.8, and 320/206.8 = 1.55 s. But a figure 96 px wide
  that stays on the screen travels 224 px, which is 1.08 s. Rescue's street of 230 px is 1.11 s (USER-13: "about 1.1
  to 1.4 s"). At four times, 224 px a second. Sentence to change: "so it crosses the 320 px screen in about 1.5 s" →
  "so its hips cross 320 px in about 1.5 s, and a figure that stays whole on the screen has about 1.1 s of run".

The pointers of the decisions: D1 to D4, D6 and D7 match the three comments I read (ids 6972668412, 6972734738,
6972767160) and D5 the body. D8's card title matches. D9 to D12 are "in the session": could not open.

## 2. The brief against its detail

Frame
- "Open questions" names "what a mission is, step by step". No question in the queue asks it and no item holds it.
  PO-21 (d) names level design as "the part that cannot be generated".
- The depth line's cost comment says "the P900 rehearsal's council ... (2026-10-06)". The card P900 is from
  2026-11-18. The number's item is misnamed or its date is.
- The outcome's proof command (`grep -l "engine.figure" games/*.py`) passes on a comment or an unused import.

What we found
- Dropped: the send. PO-6 ("What costs is the send: windows past 40 make the driver send the whole frame, 31 ms") and
  TECH-7 (three figures "send about 20 ms". "a figure that moves keeps its old tiles one more frame"). The brief has
  no claim on it, and the pass line has no window count, though PO-20 asks for "fps, the slowest gap and the window
  count".
- Dropped: TECH-6 and TECH-8, which say the figures' blit is 1.2 to 2.8 ms for three and that 20 ms of send "hides
  behind Rescue's paint". The tech lead's own numbers say memory and load are the risk and the frame rate probably is
  not. The brief's A1 joins both into one belief, so one pass line hides which half failed.
- Dropped: TECH-10's load estimate, 1.6 to 2.2 s. It is the only source near the pass line's 2.5 s and it is not a
  claim in the brief.
- Dropped: "ALL of Rescue's figure cycles, scaled: 6,676,896 B ... It cannot be a pack" (TECH-4) and PO-5's 5.2 MB for
  the five people. D3 asks for mixed situations, one per level, so each level is its own pack and its own load.
- Dropped: PO-10's "a new pack format built before stage 4 is rework".
- C12 is stronger than its source. "The survey found no MicroPython binding" holds for ESP-NN and ESP-DL. TOOLS-23
  found one for TensorFlow Lite Micro (`mocleiri/tensorflow-micropython-examples`, MIT, with an ESP32-S3 build
  status and "A breaking change is pending").
- C15 is weaker and wrong in its caveat. PO-13: in Trine "only one body exists in the world at a time ... an idle
  figure does not exist at all". So the caveat "what an idle figure does in each stayed unknown" is false for Trine,
  and the collection plan asks a question PO-13 answers. Dropped: Lemmings (PO-15), the nearest prior art for D4, and
  USER-23 (the genre switches by a button).
- C16 "mostly there" is stronger than TECH-13, which lists three misfits. The brief keeps one. The caveat "Rescue
  only" is narrower than the source, which also read Meteors (`games/meteors.py:139-147`).
- C14 holds against `art/sets/rescue.py:197` (the widths are on line 197. Line 196 is `HIPS`, as the brief says).
- C13 holds: `art/sets/gravpong.py:7-8`, "which at 24 px reads as pointing or aiming, not as holding a net at the
  waist".

Options
- The decision numbers do not match. In Options Q3 is the art, Q4 the switch, Q5 the unheld figure, Q6 the older game.
  In Questions they are Q4, Q5, Q7 and Q8, and Q3 and Q6 are other questions. verification.md's splits use the
  Questions' numbers. A reader who answers "Q4" answers two different things.
- "half a day", "about a day", "two or three days": no source. TECH-19 says the 96 px painter "is a code change, not
  only a number", which speaks against half a day.
- The board spike is described as "load one 96 px cycle". One run cycle in both facings with the street is 665,088
  bytes, under today's pool of 739,216 (my sum, part (b)). So the spike as written needs no bigger pool and no hard
  reset, and cannot test the pass line's first clause ("the pack loads into the pool after a hard reset"). The option
  and the pass line describe two different runs.
- The mirror flag: "the best ratio of gain to change" with "the size of the C change was not estimated" in the same
  line. A ratio with an unknown half. TECH-3 says "not a claim that a C flag is small". Dropped: P555 (#759, "sprites
  in C with flips", PO-9) already exists as a card for it.
- The bigger pool: dropped the load time and the conflict with P822.
- "a state machine with Reynolds's steering · the same formulas for objects and cars": TOOLS-18 "supports only: the
  page". Rescue's figures move on one axis. The folder does not show that a 2-D steering formula does anything there.
  Dropped: Rescue's `Person` rule already is this "simple AI" (PO-15, PO-17), so "reuse Rescue's rule" is an option
  with code today.
- Q8, Meteors "because it is small": ★C9's Meteors formula differs, and Meteors has one cycle, so it proves the least
  about "a figure with several cycles".

Questions
- Dropped from the lenses: PO Q-b (P903 against stages 8c and 8e, the same files), Q-d (may an idle figure fail),
  Q-e (how many kinds in the first mission, which sets the art bytes), Q-g (the lane limit for P901), Q-h (close P635
  and P636). The tech lead's "does the PO accept a hard reset and a bigger pool for every game". The user lens's Q-U4
  (run, slide or scroll), Q-U6 and AQ-12.

Found on the way
- C19 names six cards. PO-9 names ten. Missing: P555 (#759), P843 (#1207), P832 and P841's stages. Its caveat
  "bodies not all read" is weaker than PO's own note: eight bodies were read, #759 and #1218 were not.
- C17: P895 (#1269) not opened by me: could not open. TECH-11 names P885, not P895.
- C18 holds against the two lines I read.

jobs-and-journeys.md
- The second journey's step 1 cites "about three figures fit across the screen (USER-12)". USER-12 assumes a picture
  83 px wide (96 as the picture's height). At ★C3's 96 px it is 3.3, and a spray picture is 148 px wide, so 2.2.
  Two cuts are mixed in one row.
- Job 2's "so I can finish a task that needs more than one figure" is tagged E from an example "which the facilitator
  wrote and the PO chose". That is a chosen option, not an account.

risks-and-tests.md
- A1's "result that would change the decision" is under 15 fps and its pass line is 18. A result of 15 to 18 is
  neither.
- A3's test (he says the detail shows) has the facilitator's painter as its only stimulus. A no can mean the painter
  and not the size.
- The power row is "n/a because the item adds no part". A bigger pool and a longer load do not change power. Holds.

verification.md
- "The tech lead, the PO assistant and the user lens each name the art memory as the first blocker": the three
  computed from the same constants, so it is one calculation three times, not three observations. The user lens's own
  limit: "Does not support what fits in PSRAM beyond the pool".
- Every row's "reproduced" is the facilitator's re-read of his own claim.

## 3. Each interpretation and its strongest rival

- "Bigger figures let him appreciate the detail and sell it more" (job 1, A3). Rival: the detail is not painted. Or
  the complaints on record are goal and fun, and size is the newest thought, not the cause.
- "The motion capture was misread at 24 px" (C13, used for value). Rival: the wrong trial was used (a
  "direct traffic, wave, point" trial for holding a net). Arms straight out read as pointing at any size.
- "A1 is the riskiest". Rival: A4 or A3. PO-18 says nobody is blocked, and the PO's past verdicts fail games on fun.
  Feasibility first is the builders' order. The brief's own cheapest test (the Mac picture) tests value.
- "Rescue's 18 fps is not in play" (★C8). Rival: idle play with the rules running, see part 1.
- "The stick's y is free" (★C6). Rival: the mission needs it for the climb.
- "No free input for the switch" (★C5, verification's Agree). Rival: FIRE's two bindings can be split, see (c).
- "The art does not fit, so the pool grows or C changes" (★C2, ★C3). Rival: a first mission with fewer cycles and one
  stored facing per figure fits today's pool. Nothing computed it.
- "The repeat asks for a Figure part" (★C9). Rival: five one-line formulas ask for one function. PO-21 (f) says a part
  shaped by one game costs the next user more.
- "The steering seam is mostly there" (C16). Rival: the output seam is there and the input seam (the world view) is per
  game, so the reusable part is the small half.
- "'the s3's AI capabilities' is a wish" (D4). Holds as written. No rival needed.
- "'i'm reading, go on' continues this discovery" (D12). Rival in (a).

## 4. Numbers without unit, population, period or provenance

- "about 96 px" (D2, the outcome): of the figure, the picture, or four times 24 (the card's words). Three sizes: 1.43,
  1.91 and 2.24 MB.
- "2.6 times today's pool": figure pictures against whole packs. No background.
- "about 2 MB" (the pool option): decimal or binary, and for which cut.
- "half the bytes" (mirror): of the figure pictures, not of the pack.
- "18 fps" (pass line): a 5 s window's average, in which state, with how many figures moving, with sound or not. Its
  source window holds the title. "15 fps" (risks): no source.
- "4 MB of PSRAM free": 4,000,000 or 4,194,304 bytes. Read by which call (`gc.mem_free` or `esp32.idf_heap_info`).
  At which moment.
- "a load under 2.5 s": of which pack size. The `load` field or the whole `switch` time (Rescue's are 638 and
  1,428 ms).
- "548 ms": no log (the brief says so). "638 ms": one switch, n = 1. "about 5.5 s": one hold.
- "half a day", "about a day", "two or three days": no provenance.
- "10 switches in a row" (A2), "plays the mission twice" (A4): proposed lines with no source for the count.
- "about three figures fit": see part 2.
- "6 agents, 499 calls and about 90M input tokens (2026-10-06)": named for P900, dated six weeks before the card.
- "Discovery 2 of 2, the board 4 of 4 in flight": the board's state, with no pointer and no time of reading.
- "8 MB of PSRAM": 8,388,608 bytes by the board record. The cited line does not hold it.
- "about 207 px a second" and "about 1.5 s": at 96/26 only.

## (a) D12: "i'm reading, go on"

- The words: could not open (the session). I judge the brief's own record of them.
- D11's words are "Before we start with it and refine it, lets first finish the open things, please." and the brief's
  own gloss is "the discovery goes on at his word". D12's words name neither P900 nor the discovery. He said them
  "while he reads the overview of P896", and P896 is one of the open things. The plain rival: "go on" means go on with
  the open things while I read. The brief's template says, three lines above the decisions, "A yes covers only the
  actions and choices it names." By that rule D12 covers nothing.
- His rules file says "Finish before switching ... say so and finish first unless he says otherwise." D11 was the
  "otherwise" in the other direction. An unclear word after a clear stop is not safe to read as a start.
- D12 is recorded as a decision of "the PO" with "options: none offered". It is the facilitator's reading (its own
  second sentence says so). Its tag is H until he answers one question.
- What the work done on it risked. Reversible: all of it is on a branch, no PR, no board move, no filing, no comment.
  Spent: the synthesis (commit 5eebd6e, 09:27, nine minutes after the pause's commit at 09:18) and this refuter on the
  strongest model, against "tokens precious". Bent: the card sits in Idea while Discovery work runs, so the board is
  not the truth and the limit of four in flight is passed by not counting the work. Risked: attention taken from the
  open things he asked for first, and a finished-looking brief that anchors him before he refined the idea, which is
  what D11 asked not to do yet.

## (b) The arithmetic of ★C3 and ★C11, redone

Run in Python from `art/sets/rescue.py:181,530`, `games/rescue.py:39,43,61` (poses 12, 6, 12, 12), k = 96/26, sides
rounded to whole px, 2 bytes a pixel, two facings:

- fireman run 96 x 111: 511,488 · spray 148 x 111, 6 poses: 394,272 · man run 89 x 118: 504,096 · man wave: 504,096 ·
  sum 1,913,952 · divided by 739,216 = 2.589. Reproduced. Unrounded sides give 1,908,203.
- 96 as the picture's height (k = 96/30): 1,431,360, which is 25.2 % less. Reproduced. One facing: 956,976.
  Reproduced. Four times (TECH-4): 2,239,488, not in the brief.
- One run cycle, both facings, plus the 153,600 byte street: 665,088, under the 739,216 byte pool.
- The cut plus the turn and the street: 2,238,048.
- ★C11: 56 x 96/26 = 206.77 px a second. 320/206.77 = 1.548 s. Reproduced. (320 − 96)/206.77 = 1.083 s.
  230/206.77 = 1.112 s.
- Load at Rescue's two rates: 1.59 to 1.85 s for 1,913,952 bytes (TECH-10 says 1.6 to 2.2 s for 1.9 to 2.2 MB).
- Free PSRAM after such a pack by the tech lead's model: 6,747,500 + 1,507,152 − 2,067,552 = 6,187,100 bytes.

## (c) Options that are missing

Q4 in Questions, how the art fits:
- Fewer cycles and poses. TECH-4 has the row: run only, two kinds, both facings, 1,015,584 bytes. One facing, about
  508 KB, which fits today's pool with the street. Six poses a cycle (the spray has six) halves again. Not an option.
- An 8-bit palette. TECH-4: "as an 8-bit palette it would be half (not built; no 8-bit blit exists)". Not an option.
- Key-colour run lengths or a tight crop per pose. A figure fills a small part of its 96 x 111 box. Nobody measured
  the share. Not an option.
- A smaller size for the far or unheld figures, or 48 px, which D2's question offered. Not an option.
- One pack per mission. D3 implies it. Not stated.
- Big figures outside play (title, pick card). See "Check first".

Q5 in Questions, how he switches:
- Split FIRE's two bindings: the stick's switch switches the figure and BOOT acts, or the other way. USER-3 names the
  two bindings. It needs no app change for PICK or the knob. Its known weakness is in USER-4 ("a tap shorter than
  about one frame ... is lost" on the stick's switch). Not an option.
- A double tap or a hold of FIRE (USER-19 b. The tech lead's question names "FIRE tap"). Rescue already tells a tap
  from a hold (`TAP_MS = 180`, `games/rescue.py:37`). Not an option.
- Automatic: the nearest figure, or the one the task needs (USER-19 e, AQ-9). Not an option.
- The Trine way: one body, and the switch swaps who it is (PO-13). It contradicts D4, so it is the rival to name, not
  an option to add.
- The facilitator's "the stick first" runs against USER-23 and against the climb in the PO's example.

## (d) The pass line of A1

- "4 MB of PSRAM free": no source sets it as a need. The nearest are `bench.md:214` ("a 4,000,000 B bytearray
  allocates") and P822's open question about a 4 MB pool. By PHYS-2 a 2 MB pool leaves about 6.2 MB, so the line sits
  2 MB under the expected result and can hardly fail. Invented, and slack.
- "18 fps": from ★C8's first window, which holds the title. The same log gives 19 and 20. It follows from a source,
  from its weakest row. It names no state, no worst gap and no window count.
- "a load under 2.5 s": follows from no source. TECH-10's estimate is 1.6 to 2.2 s, so the line is the estimate plus a
  margin: it is set to pass. What the PO accepts is unknown. PO-21 (a) says P822 "shows he dislikes a stopped screen at
  a switch (up to 0.6 s)", and AQ-10 was not asked.
- The line fits a run that the spike option does not describe (one cycle fits today's pool).
- It is proposed and dated before any result. That part holds.

## (e) The two items against the PO assistant's order

PO-10's order: the engine parts that exist. A board spike of one 96 px figure. P901. The first mission. P903. P902.

- Item 1 is in the order's place, but it joins two runs with different gates: the Mac picture (no bench, tests the
  value A3) and the board run (his bench, a hard reset, a deploy, tests A1). Q2 asks him to order these two while
  items.md has already joined them. As one card it stays in Build until his bench is free, though the picture can
  close in a session. Its "needed by" quote is the value quote. The board half tests something he did not ask.
- Item 2 depends on P901, but story-map.md puts the walking skeleton at slice 0 and the parts at slice 2. The two
  files order the same two things oppositely.
- Missing against the lenses: a card or a question for what the first mission is. A2's test (two placeholder figures
  and a switch), which needs no 96 px art, no bigger pool and no P901, so it can run first and on today's pool. The
  sequencing of P903 with stages 8c and 8e (PO Q-b). The closing of P635 and P636 (Q-h).
- The lane: the slice pixel-games has its own limits in Ready and Build (the rules file, P730). Two new cards, P900
  and P901 in one lane: PO-22 and Q-g raise it, items.md does not.

## Searches

none

## What stayed open

- The session's words for D9 to D12: could not open.
- Whether Rescue's rules ran in the log's second and third windows: not proven either way.
- What `deinit` frees before `bench.md:214`'s reading.
- P895 (#1269), the tools survey beyond the rows the brief cites (TOOLS-1, 13, 15, 18 to 24, 39), the engine plan
  (`plan.md`), the pixel-engine driver source and the thirteen other games: not read.
- The comment ids were matched by their time and order, not each by its text.
- No scratch file was made.

## Second pass

On the diff 9232a27 to 9088322, read on 2026-11-18 from 09:35 Prague time, for about 10 minutes. D13 to D17 are "in the
session": could not open. I judge the brief's record of them.

### A correction to my first pass

- My "Check first" section put two quotes together as "the problems the PO reported after play". The second one is
  not about Rescue. `bench.md:1622-1623`: "No the game is not exciting, its still just  not much fun. But its us
  experimenting and testing spark, so its ok." It stands under the heading at `bench.md:1607`: "## P573 (#778),
  2026-11-16: cube as SMILE, the PO's play test". The first quote I had taken from PO-21 and not from the card. I read
  it now, in #1124's comments: `2026-11-13, the PO played the toy on the board: "I dont get the rescue game, it doesnt
  work. can you fix it and add the victims running around?"`. A fix round followed it (the same card: "made the game
  readable after the PO's 'I dont get the rescue game'").

### Whether each "sentence to change" was applied

- ★C2 · applied as written ("the Python heap" for "the heap").
- ★C3 · applied in part. The street, the missing cycles and the man's 92 px are in. The second size (2,239,488 bytes
  at four times, "2.6 to 3.0 times") is out, on D14. D14 is in the session, and the card's comment still says "four
  times today's 24 px". The claim names D14 and not the card's other words.
- ★C4 · applied as written, with the caveat.
- ★C5 · applied as written. The new second sentence ("FIRE has two bindings") is not in the cited lines
  `games/app.py:242,334,336`. It is at `games/app.py:461` ("FIRE is BOOT, and the joystick's switch when pins names the
  stick") and `games/engine/actions.py:5`.
- ★C6 · applied (the caveat).
- ★C8 · applied as written, with the third window.
- ★C9 · applied as written, with the cycles that run on time.
- ★C11 · applied as written.
- Not applied, from part 2: the Q2 board option still says "load one 96 px cycle" while the Test line and item 1 now
  say a pack of about 2 MB. D13 also says "one 96 px motion loaded". So the PO chose the run that fits today's pool
  (665,088 bytes with the street), and the pass line is written for another run. The mirror flag's "the best ratio
  of gain to change" beside "not estimated". P555 (#759) for the flip. The three time estimates with no source. The
  proof command of the outcome. C12, C15, C16 and C19. Meteors "because it is small", though ★C9 now says its
  formula differs. A1's "under 15 fps" beside a line that is now 19. The send and the window count (PO-6, TECH-7).
  The lane limit for the items. The question of what a mission is.

### Part 2 again: dropped caveats and claims stronger than their source

- C20 · wrong in one half and stronger in the other. "After play, the PO said other things about Rescue": the second
  quote is about CubeTiming as SMILE (above). Its pointer is line 1622, not 1623. Its second sentence ("But its us
  experimenting and testing spark, so its ok") is dropped. The first quote is about "the toy" of 2026-11-13, before
  the people, the carry and the scoring, and it asked for a fix that was made. "council/refuter.md, which read
  #1124" was not true of the first pass for this quote. It is true now.
- C21 · holds against `art/sets/rescue.py:197`. "The head as an ellipse" rests on one line that I saw, `:526`, which
  paints the hair of a `Person`. I did not read the head's own lines.
- C22 · stronger than the frame. The frame's "must not get worse" names "each set's load time" of the fifteen games. A
  new set that loads slower does not make an old set worse. What it breaks is the README's sentence "every set loaded
  in under 0.6 s". The claim joins the two.
- C23 · as PO-9 says it. The card's body was read by neither the facilitator nor me.
- The Test line · "the collection stays near Rescue's 7.5 ms": "near" has no bound, and the log's values are 7.2,
  7.5 and 7.7 ms. "the pack sits in the pool and not in the heap": no log line says where a pack sits, because
  `games/pictures.py:50-52` falls back without a word. The spike needs its own print for it. "19 fps (the rate of
  Rescue's idle windows without the title)": the two windows are 19 and 20. The line still names no worst gap and no
  window count.
- risks-and-tests.md, A1 · the result that changes the decision stays "under 15 fps". With a line of 19, a result of
  15 to 18 is neither. The gap grew by one.
- Q5, FIRE's two bindings split · "no app change" is stronger than the code. The tuple is built in
  `games/app.py:477-482` (`fire = (boot, buttons.Button(Pin(pins.JOY_SW, ...`) and the map has one FIRE action. A split
  needs a new action in `ActionMap` and a change in `app.open_action_map`. "a switch under the thumb that holds the
  stick": no source. USER-7 says where the hands are "is not written anywhere I read".
- Q5, a double tap or a hold of FIRE · "no app change" holds for the app. Rescue's tap rule is on the button's path
  only (`games/rescue.py:93`: "None on the button's path"). With the stick, FIRE held "sprays from its first frame
  (wait_ms 0)" (`:129-130`). So the stick path has no tap window today. The option's "Rescue already tells a tap from a
  hold" is narrower than it reads.
- Q4, fewer cycles · "about 508 KB" is 507,792 bytes without the street, 661,392 with it. The option does not say
  which.
- Q4, an 8-bit palette · "half the bytes" leaves out the palette and says nothing of the key colour.
- verification.md, "Agree: the refuter and the PO assistant both put a test that needs no 96 px art early" · not in
  the PO assistant's report. PO-20: "A2 is the riskiest on use, and its test needs the first mission, so it comes
  second". The PO assistant puts the board spike first. This agreement is mine alone.
- verification.md, "Split: ... the refuter and the user lens point to a button, as the genre does" · USER-23 is from
  two search snippets ("pages not opened"). "As the genre does" drops that.
- verification.md · the ★C5 row keeps the pointer 332-341 while the brief cites 242, 334, 336. The ★C3 row holds no
  line that I quoted.
- items.md, item 1 · still one card with "two steps with their own gates". Its first step is the Mac picture, and D13
  chose the board spike over the picture. The item does not say that the picture is now only the spike's input.
- items.md, item 2 · "P901 follows it, as slice 2". The card P901 says "Needed by P900" (PO-10, from `gh issue view
  1280`). The item and the card now order the two oppositely, where before the item and the story map did.
- items.md, item 3 · "each way to switch" is six ways now. Two of them (PICK, the knob) need an app change and a third
  (the split) needs a new action, so "depends on: —" holds for three of the six. Its proof ("names the one he wants")
  is not A2's pass line ("10 switches in a row with no wrong figure").
- D16 · a home path is in the pushed history: commits 5db7260 (5 added lines) and 7383393 (1 added line) are on
  `origin/p900-figures-discovery`. The files at 9088322 hold none. No question, no board action and no item in the
  brief carries the open rewrite, and the repository is public.

### Part 3 again: the strongest rival for each new interpretation

- "The first yes is for this point" (D17). Rival: one message asked several things, and "yes,yes,ok, lets go on" is a
  loose yes to the bundle. Which yes goes with which question is again the facilitator's reading. If the record is
  true to his words, the discovery's continuation from D17 on is covered.
- "A bigger figure answers neither" (C20). Rival: the 2026-11-13 complaint was about a goal that he could not read,
  and bigger figures are easier to read. With the second quote gone, C20 is one remark about an unfinished toy.
- "Size alone possibly adds no detail" (C21). Rival: at 96 px the motion itself reads better (the stride, the lean,
  the arm swing), and that is the "realistic figures" of his words. Q12 asks it.
- "19 fps is Rescue's rate" (the Test line). Rival: it is the rate of an untouched box in an unknown state, on one
  evening, in two 5 s windows. A steered Rescue is possibly slower, so the spike is held to a line the old game never
  met in play.
- "A prototype at today's size shows which switch is good" (item 3). Rival: with two 96 px figures that fill two
  thirds of the screen the pick is a different act (no doubt about who is near, a mark is easy to see), so a result
  at 24 px does not carry over.
- "The spike first tests A1" (D13). Rival: as D13 words it, the run fits today's pool, so it tests the frame rate and
  not the memory.

### Part 4 again: numbers without unit, population, period or provenance

- "19 fps": two 5 s windows, one run, 2026-11-16, an idle box. No state named for the spike's own measure.
- "near Rescue's 7.5 ms": no bound. One window's `gc` value of three.
- "about 2 MB" (the Test line, item 1): which cycles. ★C3's cut is 1,913,952 bytes of figures or 2,067,552 with the
  street, and it holds none of the mission's cycles.
- "about 508 KB": with or without the street.
- "under 15 fps": no source, unchanged.
- "1.6 to 2.2 s" (C22): calculated from two load rates, one of them with no kept log (548 ms).
- "a 4 MB picture pool" (C23): P822's number, not re-read.
- "Its picture box is about 111 px" (D14): the run's box. The spray's is 148 by 111.
- "half the bytes" (the 8-bit option): of the pictures, before the palette.
- "about a day", "half a day", "two or three days": unchanged, no source.

### Whether D17 answers part (a)

- In part. Going forward, yes, if the session holds the words as recorded: could not open.
- Not for the past: D17 says itself that "the work before it ran on the facilitator's reading alone".
- Still open from part (a): D12 stays in the list as a decision of "the PO", though D17 says it was a reading. The
  card is in Idea while the discovery runs and reads "Ready for: an experiment". The board action "move #1279 to
  Discovery again" is pending behind P892, so the board shows three in flight while four are worked on.
- D17's question was closed ("Whether 'go on' meant this discovery. If not, I stop it"). It was asked after the work
  was written and the refuter had run, so a no cost him more than a yes.

### Searches

none

### What stayed open

- The session's words for D13 to D17. The head's painting lines for C21. P822's body. Whether the rules ran in the
  log's idle windows. The parts of the brief that the diff did not touch were not read again.
- No scratch file was made.

# Third pass, 2026-11-18: the sections changed after the spike's results

The refuter, third pass, 22:55 to 23:07 Prague, on the uncommitted diff of `brief.md` and `risks-and-tests.md` only.
Sources read on disk at `4949c73` (`~/Development/pixel-p904`): `bench.md` lines 1770 to 1954,
`logs/run-p904-2c.log`, `logs/run-p904-2c-2.log`, `logs/run-p846-baseline-a.log:84-96`, `games/pictures.py:40-54`,
`games/gfx.py:383`. The bodies of pixel-games PRs #109, #110 and #111. The comments 6976801110, 6987519468 and
6991338050 on spark #1283, and 6973482873 and 6974532204 on spark #1279. Every cited bench.md anchor points at the
lines the brief says. D25's words have no pointer, so I did not find them.

## 0. First check: the existing product

- The observed problem is the PO's wish for bigger figures (A3, A4). The changed sections answer feasibility only.
  The value row stays open, and C20 (after play he named other problems than size) is not touched. This is
  consistent, not a fault.
- What breaks for current users is not shown either way. The product's pool is made once at a hard reset, "as big
  as the largest pack" in `art_index.PACKS` (`games/pictures.py:42-44`, quoted:
  `largest = max(total for path, total, build_id in art_index.PACKS.values())`). Today that is 739,216 bytes
  (comment 6987519468). If the figures pack joins the product's index, every one of the fifteen games holds a pool of
  2,464,000 bytes. The spike did not run that case. It used a shadow index with one game: log line 9 says
  `lineup 1: figures`, and bench.md says "This shadow index makes the pool as big as this pack."
- After each run the box showed Marshmallow (load 153 and 154 ms, 23 fps after step 2d). No baseline for
  Marshmallow's fps is cited, the other 14 games were not started, and after step 2d "What the box held was not read
  back". So "the box was left as it was" is not shown.
- The frame says the load time must not get worse (C22). D19 accepts about 2 s for the new game "with a loading
  card". The run had no loading card (bench.md: "The load ran with no loading card, because the probe's one game
  builds at once").
- C28's free PSRAM and the largest block were measured with the probe's one game. P822's 4 MB pool (C23) and the
  fifteen games' heaps beside a 2.46 MB pool were not measured.

## 1. The cited claims

- ★C24. Read: log line 13 `switch figures 2211 ms, load 2138 ms, import 0 ms`. Line 14 `pack pool 2464000`. Lines
  73, 78, 83 and 88 `fps figures 24`. Bench.md:1819 "Two moving 96 px figures hold 19 fps: pass." Verdict: holds,
  for the numbers. The caveats it drops are in part 2.
- ★C25. Read: bench.md:1906 "The highest count that holds 19 is 36. Its read lines say 19, 20, 20 and 20 (lines 151,
  156, 161 and 166)."; bench.md:1907 "The first count that does not hold 19 is 40."; log line 151
  `fps figures 19`, line 177 `fps figures 18`, lines 21 to 36 `fps figures 23`. Verdict: partly. Bench.md says "the
  figures start at other places than in step 2c's run", so it is not "the same scene". Change "With more figures the
  same scene held 19 fps up to 36 figures and read 18 with 40" to "Over the same street and set, with start places
  that differ from step 2c's run, each listed count from 16 to 36 held 19 fps and 40 read 18". Add to the caveat:
  at every count of this run a worst gap over 60 ms shows, so the figures moved slower than their speed
  (bench.md step 2d, `games/gfx.py:383`).
- ★C26. Read: PR #109 "fireman (run) at 96 px: 12 poses of 67 by 102 px, 328032 bytes with both facings", "child
  (child) at 96 px: 12 poses of 42 by 72 px, 145152 bytes with both facings", "the cast: 8 characters, 2310384
  bytes"; PR #110 "fireman's jump ... 259584 bytes", "fireman's forward jump ... 309504 bytes", "fireman's climb ...
  254592 bytes". Verdict: holds, for the fireman. Each move is 12 poses. Its reuse in part 2 is stronger.
- C27. Read: PR #111 "cutout, the pixels only: the run uses 86 part pictures, 60226 bytes, for one facing (the board
  mirrors a part for the other); with every step of the six limb kinds, 389 pictures ..., 270848 bytes" and "flat,
  the poses only (no code, no time): ... 1536 bytes". Verdict: holds. Dropped: "The bytes are the pixels only, with
  no header a picture", and the cutout's 1,080 bytes of poses are not in 60,226.
- C28. Read: bench.md:1832 "`psram free 5026784 largest 4980736` at the end". Verdict: partly. Step 2d's run ended
  with `psram free 4764636 largest 4718592` (bench.md, step 2d). Change "After the run with the 2,464,000 byte pool,
  5,026,784 bytes of PSRAM were free, with a largest block of 4,980,736" to "At the end of step 2c's probe, before
  its cleanup, 5,026,784 bytes of PSRAM were free (largest block 4,980,736). Step 2d's run, with 64 figure objects,
  ended with 4,764,636 (largest 4,718,592)".
- C29. Read: comment 6976801110 "The PO's words on the first four characters (2026-11-18, in the session,
  pixel-games PR https://github.com/xmejkal/pixel-games/pull/106)", then "> the characters themselves look ok for
  the first iteration, but we will make them better later". Verdict: partly. His words were about four characters,
  before PR #109 added the officer, the builder, the chef and the acrobat. Change "The PO saw the painted characters
  and said" to "The PO saw the first four painted characters (PR #106) and said".
- D24. Read: comment 6991338050 "to the offer of a second board run with 32 and 64 figures: "yes, run more people"".
  Holds as a record. The comment is the facilitator's post of his words, not his own post. "options: none offered,
  an offer of a run with 32 and 64 figures" contradicts itself. The counts 36 and 40 came from the plan's amendment
  (22:03 Prague), not from his words.
- D25. Could not open: "in the session" has no pointer. See part 2.

## 2. The changed sections against their sources

- "Ready for: an experiment". The rule (brief.md:4-6): "an experiment: the decider chose a test (a D) before choosing
  an option". D13's test has come back. No D chooses P905 as the next test. D21 files it ("file the three items"),
  and D23 put P904 before P905. The header says itself "Its place in Ready is the PO's to give". By the rule the
  state is "collecting evidence". Change to "**Ready for:** collecting evidence (the test of A1, D13, came back on
  2026-11-18, see Results. No D has chosen the next test: P905, filed by D21, waits for the PO's order)".
- "A1 is retired" (A1's status, the Riskiest line, the feasibility row, Results row 1).
  - The three parts of D22 and D19, as read, are met: 24 fps on lines 73 to 88, `pack pool` on line 14, 2,138 ms on
    line 13.
  - Two of the readings are not the PO's words. The 2,500 ms is "my reading of "about 2 s"" (comment 6987519468).
    D19 says "with a loading card", and the run had none. Results row 1 says "read as 2,500 ms or less" and does not
    say whose reading.
  - A1's belief is "two 96 px figures with enough poses". The pack held one run of 12 poses for each of eight
    characters (193 names). The test line before today named "two figures with two cycles each". ★C3 says even that
    cut "holds none of the cycles that his example mission needs". The PO agreed to count a rising number of
    characters (comment 6987519468: "The PO agreed on 2026-11-18 that step 2c counts a rising number of characters
    at once"), but that agreement is no D in the brief.
  - The feasibility row now says "H that a mission's moves fit too". That is the "enough poses" half of A1. So the
    part that came back is narrower than A1 as written. "Retired" claims all of A1. Either restate A1 as tested or
    keep it open with the narrowed half. "Stands on: 8 H" counts A1 as retired. With A1 kept open it is 9.
  - The scene: "Rescue's own play (crowd, fire, dog) is not in it" (comment 6987519468, plan point 2). See part 3.
- Results row 2, "the number of figures on the screen does not limit a mission of two. No option of Q4 moves."
  - The first sentence holds only in the probe's scene. At 16 figures the rate fell from 24 to 23 with 64 objects
    alive, gc 4.0 against 2.5 ms a frame, and the cause "is not proven" (bench.md:1919-1921). Objects alive, not
    figures on screen, are possibly the limit that a game with AI adds.
  - The second sentence is stronger than the source. The run gives a paint cost of about 0.6 ms a whole figure
    (bench.md step 2d, "worked out"). The cutout and the C painter options spend frame time that C27 says is
    unknown. This run is the first number those options are judged against. It moves no option's rank by itself,
    but it does inform two options.
- The Riskiest line (A2). It is the facilitator's opinion, labelled so, with Q1's ratings unasked. The Test line's
  pass line "10 switches in a row" names no proposer. The rival choice is in part 3.
- Q4's first option, rewritten.
  - "each move of a character adds 254,592 to 328,032 bytes" is stronger than ★C26. The range is the fireman's four
    moves. The child's run is 145,152 bytes. No other character's jump or climb was painted.
  - "shown on the board for eight characters with one run each" was shown with a lineup of one game and the shadow
    index (part 0). Not shown: the product pool at 2.46 MB beside the fifteen games.
  - The opinion "the first maker, because it is the only one that ran on the board" is circular. It ran because the
    plan chose it first: "The first maker on the board is "whole" ... this maker needs no new board code"
    (comment 6987519468). The order of the test is not a merit of the option.
- Q4's second option (cutout). "about a fifth of the bytes for a run" holds only for the 86 pictures with a mirror
  on the board: 60,226 of 328,032 bytes is 18 % (calculated here). Without the mirror it is 120,452 (PR #111), 37 %.
  "less for each further move" is the facilitator's reading of "a second move costs its poses and the pictures of
  the steps that it adds". With every limb step the atlas is 270,848 bytes, 83 % of one whole run. No source says
  how many steps a second move adds.
- Q4's third option (one picture source). The PO's quote holds (comment 6974532204). The seam ("the game asks for a
  picture by character, motion, pose and facing") is the facilitator's text in that comment, not his. "that the
  choice of Q4 can change later with no change in a game" is a design claim, not a test result. A change of maker
  changes the frame time (C27) and needs a flash for cutout or flat, so the game's code stays but its frame rate
  possibly changes.
- Q4's line under Questions, "status: asked 2026-11-18, after the spike's result". No pointer says where it was
  asked.
- "Decision needed: Q4 ... now with measured numbers (★C24 to C27)". Only ★C24 and ★C25 are board measurements.
  ★C26 and C27 are byte counts painted on the Mac.
- The collection plan's first row, "Does a 2 MB pool leave the heap enough ... answered". Answered for the probe's
  one game only. The heap of a real game beside the pool is not measured (part 0).
- D25. The words "continue as you advice" do not say what the advice was, and "#1279. and go on" does not name a
  board move. The board action "move #1279 to Discovery again · asked of the spark session · D25" rests on a D whose
  words do not cover it. "Discovery holds one of two" has no time or source.
- The board action "move P904 #1283 to Review ... taken 2026-11-18 by the spark session" names no D. The brief's
  own rule above Board actions says "None is taken without a D". The board itself was not read here.
- The Hand-off line says the refuter ran "a third time on the sections that the return changed". It was written
  before this pass existed. It also drops whether the passes are applied, which the old line said.

## 3. Rival explanations

- ★C24, 24 fps with two figures: a light scene, not headroom that a game has. The probe's frame with two figures
  is step 1.3 to 1.4, paint 10.4 to 11.0, send 3.3 to 5.6 and gc 2.6 ms (bench.md table). Rescue's own frame at
  19 fps is step 8.4, paint 26.8, send 3.7 and gc 7.5 ms (`logs/run-p846-baseline-a.log:90`, 46.4 ms in all).
  Count 2 against count 0 adds about 1.2 to 1.9 ms of paint and 2.5 to 4.8 ms of send. Added to Rescue's 46.4 ms,
  that is about 50 to 53 ms a frame, about 19 to 20 fps: at the pass line, not over it. Calculated here, rough:
  Rescue's own 24 px figures leave that frame. The pass line itself says "as Rescue did". No source rules this
  out.
- ★C24, 24 and not 25: the App caps at 25 fps (`FRAME_MS` 40). With two figures the worst gap reached 60 ms (log
  line 89, `worst 60`), the game clock's cap (`games/gfx.py:383`, `min(..., 60)`). A heavier frame crosses it, and
  then the figures move slower than their speed.
- ★C24, the load of 2,138 ms: one load in a lineup of one, with no loading card. Step 2d's switch took 107 ms more
  with the same load. A switch from another game in the product's lineup was not measured.
- ★C25, 23 against 24 at 16 figures: objects alive and the collector (64 against 16 objects, about 70,000 more
  bytes, gc 4.0 against 2.5 ms), or the other start places. The source names both and proves neither.
- C28: what took 3,227,920 bytes is not said. Step 2d's run took 262,148 bytes more. The free PSRAM depends on what
  the game holds, so a game with rules and AI leaves less.
- C29: his "ok" was for four characters. PR #109 lists faults in the later four ("The officer's cap band is faint",
  "The builder's hard hat reads more like a cap"), which he has not judged.
- The new Riskiest (A2): the rival is the rest of A1. A mission's characters and moves in bytes, in one pool that
  every game holds, and a game's own frame with two 96 px figures, are both untested. A2 has evidence of risk too
  (★C5, ★C6). Without Q1's ratings the folder cannot rank them.

## 4. Numbers without unit, population, period or provenance

- "one move of one character is 254,592 to 328,032 bytes" (feasibility row) and "each move of a character adds
  254,592 to 328,032 bytes" (Q4): the population is the fireman's four 12-pose moves, not every character.
- "about a fifth of the bytes for a run" (Q4, cutout): no provenance. It is calculated from 60,226 and 328,032, one facing,
  pixels only, with a mirror on the board.
- "a load of about 2 s, read as 2,500 ms or less" (Results row 1, Test line): the reading's author is missing (the
  facilitator, amended 20:33 Prague before the result).
- "5,026,784 bytes of PSRAM were free" (C28): the period is the end of step 2c's probe, before its cleanup. It is one of
  two runs.
- "held 19 fps up to 36 figures" (★C25, Results row 2): each count is four 5 s read lines of a 30 s count, with 64
  objects alive. The counts between the listed ones are unknown.
- "24 fps in each read line" (★C24): four 5 s lines of one 30 s count, one run, the App capped at 25.
- "10 switches in a row with no wrong figure" (Test line): no proposer.
- "Discovery holds one of two" (Board actions): no time and no source.
- "8 H" (Stands on): depends on A1 counted as retired (part 2).

## Searches

None on the web. Local reads and `gh` reads only, as listed at the top of this pass. No scratch file was made.

# Fourth pass, 2026-11-18: the sections changed after D26

The refuter, fourth pass, on the uncommitted diff of brief.md, risks-and-tests.md and story-map.md at `91a3555`, in the worktree of the branch `p900-figures-discovery` (the facilitator left the worktree's path out here, because the repository is public). I wrote no file and made no scratch file.

## 1. D26 (brief.md:157)
- "Q4's first option and its third option together": partly. It holds by the Options list (brief.md:80, :82). By the Questions line (brief.md:114, "a bigger pool, a mirror flag in C, or poses painted on the board"), the third option would be the C painter. Change it to: "Q4's option "both facings as pictures and a bigger pool" and its option "one picture source with several makers behind it" together".
- "By the first option's cost cell the art of the first mission then needs no C change, and a hard reset once": partly. Three problems:
  - It drops the cell's third part, "each move of the fireman adds 254,592 to 328,032 bytes".
  - It holds only if the count passes. A10's own cell sends a bigger pack to "another maker of Q4", and the cutout and the C painter need a flash (brief.md:81, :84).
  - "once" holds only while the pack does not grow. `games/pictures.py:43-45` says the pool "is made once, as big as the largest pack".
  Change it to: "By the first option's cost cell, and only if the first mission's pack fits the pool (A10, untested), its art needs no C change and a hard reset each time the largest pack grows. Each move of the fireman adds 254,592 to 328,032 bytes (★C26: painted on the Mac)."
- "the pool holds that PSRAM for every game": partly. "that PSRAM" has no size, because D26 itself says his words name no pool size. Change it to: "the pool, as big as the largest pack, holds its PSRAM for every game (★C2)".
- "names no other maker, no pool size, no interface ... and no card that builds it": holds. P901's body (#1280) names no picture source either.
- The link, "as in D25" and "options, as asked": hold against the comment.
- Rival: his answer repeats the facilitator's opinion on brief.md:114 word for word. The question offered two of the eight Options. So D26 confirms the proposal as it was framed. It is no sign that he weighed the mirror flag, fewer moves, the palette or figures outside play.

## 2. The header lines
- "Ready for: collecting evidence": holds. The rule on brief.md:5 needs a D that chooses a test, and no D after D13 does. Design also needs the jobs and the risk, and no D confirms them.
- "D26 confirms a direction for the art": holds as worded, but it opens a gap in the check. `discovery.py:462` only matches the words "frame", "jobs", "direction" and "risk" anywhere in the D rows.
  - D26 is the first D with "direction". At HEAD, 0 D rows had it.
  - "jobs" is matched only by D3's "everyday jobs".
  - So any later D that contains "risk" passes the design gate on words alone, while the jobs are unconfirmed.
  Keep "for the art" wherever it appears, and file the word match as a finding for the skill.
- "Decision needed" starting with Q15: partly. D26 names no pool size, so the count's pass line, "2,464,000 bytes or less" (brief.md:103), is still only the facilitator's. Q1's status, "the pass line is answered (D20), the importance of A1 to A9", is stale. D20 was A1's pass line, and A10 is new. Change the start of Decision needed to "Q15, with A10's pass line". In Q1, change "A1 to A9" to "A2 to A10".

## 3. Q4, Q14, Q15 and the Riskiest line
- Q4 "answered D26": holds. Its "options: as in Options" is stale, because he was asked two options. Change it to "options: two, as asked in comment 6992953082".
- Q14's added words: hold. None of the three items in items.md names a picture source. The line misses ★C10, though. `tests/test_engine_boundary.py:27` `DIRECTION` lists no `pictures` module. Add: "and ★C10 keeps a source that imports `pictures` out of `games/engine/` until the plan's stages 3c and 4".
- Q15's unblocks cell: partly. The count compares bytes with 2,464,000, which is one run's pool. C28 shows a largest free block of 4,718,592 bytes at the end of step 2d. The frame's half waits for P906. Change the cell to: "the count tells whether the first mission's whole pictures fit 2,464,000 bytes (A10's bytes half)".
- The Riskiest sentence: holds. "are counted" reads as if the count already ran. Change it to "so the count of A10's bytes is for that maker".

## 4. Board actions
- The comment at "23:04 Prague": holds. `created_at` is 2026-11-18T22:04:08Z, which is 23:04:08 CET.
- The waiting line: partly.
  - `board.py status` lists "(#1279) since 2026-11-18, 0 d" under "waits on the PO". That part holds.
  - The project fields set Waiting on "the PO" at 22:04:57Z and Waiting since at 22:04:58Z, so 23:04:57 Prague. "asked the spark session for it at 23:05 Prague" has no pointer.
  - The line names no D, against brief.md:167, "None is taken without a D".
  - "It stays set while Q15 waits for him", but Q15 is "queued" (brief.md:125).
  Change it to: "set 2026-11-18, 23:04 Prague (the fields' times) · his standing rule "It moves as the work moves", as in D9". Then either ask Q15 now and mark it asked with a pointer, or the flag claims a wait he does not have.

## 5. A10's cell (risks-and-tests.md:41)
Partly. Three faults:
- (a) If another maker joins for the first mission, that reverses D26. That is his choice again.
- (b) The cutout and the C painter each bring a firmware flash, and a flash is what Q4 "decides".
- (c) No remedy in the cell answers "under 19 fps". C27 says the other makers' "frame time is unknown", and a bigger pool adds nothing to the frame rate.

Also missing is fewer moves (brief.md:85), which keeps D26. Change the cell to: "the pack is bigger: the PO decides again on D26: fewer moves, another maker behind the picture source (a firmware flash for cutout parts or a C painter), or a test of a bigger pool. The rate is under 19 fps: the frame's cost is the question (P907), since no other maker is shown to paint faster (C27)".

## 6. Slice 0
Holds. A10's test reads "the walking skeleton's log", and A2 is the switch. Two notes. The tag drops A1's caveat "in the probe's scene". And "one action of both" also rests on A7, which the tag did not name before the change either.

## 7. The Hand-off
Partly. "the fourth pass" points at a pass that is not yet in refuter.md, and the line does not say what was applied. It also drops the fact that the frame's decision is still open: the parts and their order are Q8 and Q14. Given point 2, that matters. Change the start to: "not yet: the jobs, the parts and their order (Q8, Q14) and the importance of the assumptions are unconfirmed ... A direction for the art only is confirmed (D26)". End the line with "(the fourth pass, applied: <which>)".

## 8. Stale, and not touched by the diff
- verification.md:27, "· Q4": add "settled for the first mission by D26". verification.md:38, "and Q4 is asked": add "answered D26".
- brief.md:80 and :82: mark both options "chosen D26".
- The Collection plan has no row for the count (Q15, A10). It also has no row for D26's caveat set against the frame's "must not get worse: the fifteen games" (brief.md:21). The spike ran "lineup 1: figures". Add a row: "Do the fifteen games load and hold their rate beside the first mission's pool? | D26, the frame | the board, his bench | start each game once | before the pack joins the product's index".
- risks-and-tests.md:64, "★C3 against ★C4", predates ★C24 and ★C26.
- items.md has no item for the count. Filing needs a D that names items.md (items.md:2). Propose the item before asking Q15.
- jobs-and-journeys.md:47 still asks Q3, which D14 answered. That is not caused by D26.
- The Frame's "Open questions" (brief.md:19): nothing there is stale because of D26.

## 9. Numbers
- "read at 23:15 Prague" (D26): no pointer.
- "23:05 Prague" (the waiting line): the fields read 23:04:57.
- "a hard reset once" (D26): true only while the pack does not grow (point 1).

## Searches
None on the web. I read the diff, every file in the folder and refuter.md's third pass. Also:
- comment 6992953082: its body and `created_at`
- the project fields of #1279, through `gh api graphql`
- `tools/board.py status`
- the body of #1280
- `games/pictures.py:40-52`
- `tests/test_engine_boundary.py:20-31`
- `discovery.py:20,458-464`
- the skill's council.md and SKILL.md

## What stayed open
- D26's time and the words "after a clear": the session cannot be read.
- Who set the board fields: the fields show the time, not who made the change.
- Whether the picture source must import `pictures`: it is not designed.
- The fifteen games beside a 2.46 MB pool: not measured.
- Whether a test chosen after D26 counts as "an experiment". brief.md:5 says "before choosing an option", and Q15 claims it decides "the readiness".

# Fifth pass, 2026-11-19: the sections changed after D27 and D28

The refuter, fifth pass, on `git diff fe00814 c680a93` in the worktree of branch `p900-figures-discovery` (HEAD `c680a93`, the tree is clean). I wrote no file.

## 1. D27 and D28
- D27's option text, its options cell and "This chooses a test": hold. They match the question and the option word for word.
- D27 covers the filing: holds. The option says "Your yes also files the count's card under P900", so rule 8 is met. The D names items.md, which items.md:2 asks for. That name is the facilitator's mapping. His yes named "the count's card", not "this list".
- "names no list of figures and moves (Q16) and no Ready order": holds. The option fixes only "two figures".
- D28's text, "the question named the pack as all moves of both figures, plus the street", and the options cell: hold.
- "set before any result": holds for the count. No row of the first mission existed, because Q16 is still open. One caveat. Q15's question put "about 250 to 330 KB for one move of the fireman" in front of him (★C26), so he set the line with the inputs in view. Add "with the fireman's bytes a move (★C26) in the question".
- Rival: Q15's question said "the board showed room for 2.46 MB". The board showed a pool of that size. C28 shows a largest free block of 4,980,736 bytes after that pool was made. D28's option text ("the only pool size that the board showed, in one run") is accurate. The question that framed it overstated the room.

## 2. "Ready for: an experiment"
Partly. The label holds, but the reason does not match the rule. brief.md:5 says "before choosing an option", and the Options list holds Q4's options, one of which D26 chose. "No option of the frame's decision is chosen" narrows the rule's words. The record has a better reason. D26 holds "only if the first mission's pack fits the pool (A10, untested)". D28's chosen option says "A bigger number means that you decide again". So the test comes before the art's option is final. Words for the line:

"**Ready for:** an experiment (D27 chose the next test, the count of the first mission's bytes on the Mac, P924, with the PO's pass line D28. The test comes before the art's option is final: D26 holds only if the pack fits the pool, and by D28 a bigger pack means he decides again. The frame's decision is open (Q8, Q14). The count waits for Q16. ...)"

The check's gate (`discovery.py:464`, "test" in any D) already passed on D13's words. So the check is no evidence here.

## 3. Q16
- It is a real question. No D fixes the first mission. D1's comment gives an example, and D3 mixes the situations.
- The option text is partly wrong. D1's comment 6972668412 reads "he moves the fireman to the wall, the fireman holds a ladder, then he switches to the grandma and she climbs". Q16 and card #1308 write "a second figure runs and climbs". "runs" adds a move, and the count is about moves. Use D1's words.
- Q7 is just as urgent. It "decides ... the idle poses", and an idle cycle for each figure is a row of the count. Ask Q7 with Q16, or add "and an idle cycle (Q7)" to Q16.

## 4. Test line, A10, Collection plan, items.md
- The Test line: holds.
- A10's pass-line cell: partly. "set by the PO 2026-11-19 (D28)" heads both halves. D22 set 19 fps for the spike's probe, not for the skeleton. Change it to "the bytes half set by the PO 2026-11-19 (D28): ... The frame half, carried by the facilitator from D22's spike line: 19 fps in the skeleton's log". Q1's status already says "A10's bytes" only.
- The Collection plan row: partly. It blocks "Q15", which is answered. Change the cell to "D26 (by D28 a bigger pack means he decides again), A10". "the painters on the Mac" is a tool, not a person. Change it to "the session that builds P924, with the painters".
- The items.md block and its board line: hold. P924's fields read back as Status Idea and Slice pixel-games, both set at 00:18 Prague. Its parent is 1279.

## 5. Card #1308
- "254,592 to 328,032 bytes" and "a pool of 2,464,000 bytes in one run": neither has a pointer. Add PRs #109 and #110 for the first, and bench.md#L1819-L1828 at `4949c73` for the second.
- "a second figure runs and climbs": see point 3.
- The items.md link points at the branch `p900-figures-discovery`, which is deleted when the PR squashes (brief.md, Board actions). Link to the commit `c680a93` instead.
- The rest holds: his quote, "said yes to this card", Done when, and the remedy, which matches D28's option.

## 6. Numbers and times
- "00:18 Prague" (D27, D28, the board action): holds. `createdAt` is 23:18:47Z, which is 00:18:47 CET.
- "Stands on: 9 H": holds (A2 to A10).
- #1279 still has Waiting on "the PO" since 2026-11-18. Q16 is "queued", so the flag claims a wait for a question he has not been asked yet.

## Searches
None on the web. I read:
- the diff
- items.md, lines 36 to 54
- the body, labels, `createdAt` and project fields of #1308
- the project fields of #1279
- the line in comment 6972668412 that holds D1's example

## What stayed open
- The session where the options tool ran cannot be read. So the question and option texts rest on the coordinator's copy.
- Whether the "Needed by" convention means a board field: no such field shows on #1279 or #1308.

# Sixth pass, 2026-11-19: the sections changed after D29 and D30
## 1. D29
- "names two figures and three actions": partly. His words, "The fireman moves to the wall and holds a ladder, then I switch to the child and the child climbs", also give the order and his switch. Change to: "two figures, three of their actions in this order, and his switch from the fireman to the child". With that change, "no design of the mission" holds.
- "no gait ... no end of the mission": holds. None of those things is in the message.
- "repeats a text that the facilitator wrote" (H): I could not check it. It contradicts Q16's line, "opinion (none)", and comment 6994615454, whose only example has the grandma. Either Q16 gets the facilitator's later opinion (the child), or D29's options drop "(the facilitator's opinion)".
- "Both figures are among the eight characters painted at 96 px, and no grandma is": partly. CAST at L443-444 lists 8. PR #109 prints "child (child) at 96 px: 12 poses of 42 by 72 px". But mocap.py L289 captures a granny: `Cycle("granny", "35_01", ...)`. Add: "the child at scale 0.75, 72 px tall (detailed.py L429); a granny's walk is captured (mocap.py L289) but not painted at 96 px".
- "A run of each figure and a climb are captured": holds. L279 `Cycle("run", "09_01"`, L288 `Cycle("child", "09_02"`, L296 `Rising("climb", "13_33"` ("climb ladder", L31).
- "the file lists no hold of a ladder": partly. This is literally true, but it misleads. L280 spray is "both arms held out in front at chest height in a staggered stance" (L15-16), which is the nearest stand-in. Add: "the nearest is the spray's held arms (L280)".
- "The climb's bytes were printed for the fireman only": holds. PR #110: "fireman's climb (13:33 at 120 fps): 12 poses of 52 by 102 px, 254592 bytes".
## 2. D30
- The Ready order is in the pixel-games lane: holds. #1308 has Slice=pixel-games.
- "one place in Ready and one in Build": holds. W6 L85 says "the sound session (the slices "pixel-games" and "graphics library") one in each".
- The quoted rule: holds, word for word, at CLAUDE.local.md L24.
- "options: none offered": open. If the paste text held "P924 to Ready", the facilitator offered it.
- "it waits for a free place": refuted. P921 #1303 went from Review to Done at 10:12:27 Prague, before the commit at 10:14:01. P924 went from Ready to Build at 10:15:50 Prague (GraphQL status events). Change to: "pulled into Build at 10:15 Prague, after P921 went to Done at 10:12".
## 3. Board actions
- "taken 10:11 ... read back: Ready": holds. The status went from Idea to Ready at 09:11:16Z.
- "at 10:11 the board held 4 of 4": holds. P921 was in Review until 10:12:27.
- "Its move to Build waits for a free place": refuted, as above. Add the action "move P924 to Build · taken 10:15 Prague".
- items.md, "order ... into Ready · 10:11": holds.
- Defect, a missing action: P924's body still says "Open before the count: the list of the first mission's figures and moves (Q16) ... grandma ... The PO confirms the list first". #1279 has no comment since 00:24 Prague. The card is now in Build, so whoever builds it reads a stale card. Fix: put D29's and D30's words on P924 and in a comment on #1279.
## 4. The header lines, Q16, items.md, risks-and-tests.md
- The readiness "an experiment" holds by the top comment's rule (D27). "its card P924 is in Ready (D30)": partly. It is in Build now.
- "Decision needed": holds. It matches the queue in the Q16 comment.
- Q16's status "answered D29": holds. Its "opinion (none)" conflicts with D29 (see section 1).
- items.md, "So the count's plan names a stand-in for each such row and marks it": partly. No D holds this. Add "(the facilitator's method)".
- A7's evidence: partly, the same spray point as in section 1.
- The Collection plan's "in Ready since 2026-11-19 (D30)": partly. Change to "in Build since 2026-11-19, 10:15 Prague".
## 5. Stale, and not touched by the diff
- P924's body, as in section 3.
- A10 says "two 96 px figures". The mission's second figure is 72 px tall (PR #109). The frame half is a worst case, so say so.
- council/user.md L29 and verification.md L46 keep the grandma. They are history, so leave them.
## 6. Numbers and times
- "eight", "96 px", "10:11" and "4 of 4" hold, from the sources above.
- "about 00:30 Prague": I could not check it. The comment it follows was posted at 00:24:15 Prague.
- "10:13 by the facilitator's clock": I could not check it. The commit is at 10:14:01 +0100.
- The child's run is printed at 145,152 bytes (PR #109). D29 could name it.
## Searches
- I grepped the folder for Q16, grandma, granny, "waits for", "in Ready" and Idea.
- I read the GraphQL status events of #1308 and #1303.
- `board.py status` at 10:15 CET listed P924 in Ready, behind P923 and P922. A field read at 10:16:26 CET showed P924 in Build.
## What stayed open
- The session, its paste text and the facilitator's clock: I could not read any of them.

2 refuted, 8 partly, 12 hold, and 1 missing action

# Seventh pass, 2026-11-19: the sections changed after the count's result
## 1. ★C31 and the Results row
- The numbers hold. On 85c1d54, `python3 art/mission.py` (28 s) printed 1034920, 717976, 1429080, the street's 153600 and a 16-byte header. They match `tests/test_mission.py` lines 231 to 245. My sum of the six rows is 881,304, plus 153,616, which makes 1,034,920. 2,464,000 minus 1,034,920 is 1,429,080, and 1,429,080 / 153,600 is 9.3, so "9 more pictures" holds.
- REFUTED: "every row with 24 poses in place of 12 (1,916,224 bytes)". 1,916,224 is every row doubled, so the 6-pose rows go to 12 and not to 24. With 24 poses in every row the pack is 2,497,264 bytes, 33,264 over the line. The same error is in PR #115's body ("That is still under the line"), finding 13 of comment 7006108038, and card comment 7006141011. Fix: "every row with twice its poses (1,916,224 bytes, calculated)".
- "met (D28)" holds as counted, at 42 % of the line. The summary lines keep "placeholders" and "painted on the Mac".
- Partly: "the pack ... as D29 names it" and "D29's rows" (in ★C31, Results, the Hand-off, the Collection plan, the feasibility row and A10's evidence). D29 names three actions. The child's run and the two idles are the facilitator's rows. Fix: "the six counted rows, three of them named by D29".
- A note that changes no verdict: rows 2 and 5 are the same picture (the fireman's spray), counted twice. The export's aliases (`art/export.py` lines 191 to 196) would place it once, so a written pack would be 916,192 bytes. The count is conservative.
## 2. D26's condition
- Partly: "So D26's condition holds for this list of rows" says more than the evidence. D26 says "fits the pool". The count is pictures painted on the Mac, under the one pack size that the board loaded (★C24, one run). It was never loaded on the board, and the turn, the ladder and the wall are not counted. Fix: "So D26's condition is met on the Mac for the counted rows. Nothing was loaded on the board."
## 3. The readiness
- Holds. By the rule (brief.md, lines 4 to 9), no D chooses a next test, so the folder is not "an experiment". The third pass set this precedent (verification.md:37). "design" fails, because the jobs and the remaining risk are unconfirmed.
## 4. The Riskiest and Test lines
- Holds: both are marked as proposals, and the pass line is "not his". "The skeleton needs a way to switch" is backed by story-map.md:16 ("switches with one input").
- A stronger candidate, in my opinion: A10's frame half. C30's arithmetic puts it "near 19 fps", which is the pass line itself, and A10's own cell says no remedy is shown (C27, P907). For A2, ★C5 and ★C6 are already known.
## 5. A10
- The status cell "the bytes half met D28's line" holds.
- Partly: the Results row's "holds for the mission as D29 names it". The count tests something narrower than "the moves that the first mission needs fit the pool": the counted pictures, painted on the Mac, against a size from one run. Fix: "met D28's line for the counted rows".
## 6. Board actions and times
- Holds: 7004957790 at 09:20Z is 10:20 Prague, 7004983292 at 09:21Z is 10:21, and 7005344538 at 09:38Z is 10:38. P924 is in Review.
- Partly: these actions are missing. The finding comment 7006141011 (11:13 Prague) is not listed. #1279 has no comment with the result; its last comment is from 10:20.
- Partly: Q1 is now "asked from 2026-11-19". But the row "Waiting on ... cleared ... no question is asked of him now" stands, and the board does not show P900 as waiting on the PO. Either set Waiting on as an action, or write "to be asked".
## 7. Stale, and not touched by the diff
- The Hand-off (edited by the diff) still counts the refuter's runs up to the fourth. The fifth and sixth passes are in verification.md:46 and 50.
- The new verification.md line for ★C31 says "refuter: holds" and cites 34 planted faults. That was the refuter of PR #115, not this folder's refuter. Name it.
- story-map.md:16 tags "H A10". Write "H A10's frame half".
- brief.md:159 ("A10, untested") and risks-and-tests.md:60 are dated records, so they hold.
## Searches
I grepped for "waits for Q16", "in Build", "an experiment", "count the first mission's bytes", "A10", "P924", "untested" and "fit the pool". There is no other stale line.
## What stayed open
I could not check when P924 moved to Review (10:38): the API gives no time for a field change. Nothing ran on the board.

1 refuted, 8 partly, 10 hold

# Eighth pass, 2026-11-19: D31, Q1's opinion and the board's revision
## 1. D31
- "name no rating, no Ready order and no test": holds.
- "do not say that he read the table … stays in Review": partly. A fair reader can take "great" as his word on the result. Add: "'great' may answer the result. The facilitator does not count it as his word that he read the table."
- "reads 'go on' as in D25: the discovery's work that needs no decision of his goes on": partly. D25 (brief.md:158) says only that the discovery goes on and that his words name no board move. The part about "needs no decision" is new. The reading that "go on" accepts the proposed P905 is never named. Add: "A reader could take it as a yes to P905. The facilitator does not, because a Ready order waits on him." Also, "by the clock" should say "by the facilitator's clock", as D28 to D30 do.
- The work it names (one row, a proposal) is no decision: holds. I could not see the report or its three paste lines.
## 2. Q1's opinion
- It is labelled as the facilitator's opinion and not as his rating: holds.
- A2 "the game's one verb, D1": refuted. D1 (brief.md:134) says only that he switches figures, and the request names joystick movements too. Write "the switch is how he collaborates (D1)".
- A2 "no input is free for it": partly. ★C6 says the stick's y is free in both games. Write "no input is free without a change to the app (★C5), and the climb wants the free y (★C6)".
- A3 "good for a first iteration": partly. C29 says "ok", not "good". D18 (the painter must gain detail) points the other way.
- A5 "if the mission comes first, Q14": partly. Q14 orders P906 and P901. Whether A5 is needed turns on Q7, which is open, and on D4.
- A9 "a scroll answers it": partly. A scroll is A9's own fail line, so it is not a fix.
- A4, A6, A7, A8 (README.md:38 quotes the FAQ, "may be copied…") and A10's frame half (C30): hold.
- The split: partly hidden. Riskiest (brief.md:103) names the seventh pass's candidate. Q1 and "Decision needed" do not, so one yes picks A2 without his seeing it. Add "the seventh pass rates the frame half of A10 riskier (Riskiest)".
- Q1's status still says "one assumption at a time, A2 first" only. Add the one-yes offer.
## 3. ★C7's caveat
- "only the board's name, its MAC and its deploys": partly. The keys are board, deploys and mac, but `board` is the type "firebeetle2-esp32s3". Write "the board's type".
- The quote and lines 248 and 255: hold, verbatim.
- "different revisions, or two boards": partly. A third reading fits. The 2026-10-31 note judged only where the buttons sat. Its "read 0 while held" does not separate the revisions, since about 0.7 V reads as 0 (from memory, not re-read). bench.md:58 infers V1.1 from the power-off and read no chip. The record's first deploy is 2026-11-01, so the store cannot tie the 2026-10-31 board to this MAC. The store holds one FireBeetle record.
- `how_to_tell` (line 308): holds. "settles it" settles only the board on his bench.
## 4. The other lines
- The collection row matches `how_to_tell`. Partly: its method cell holds a result. The method is his look.
- "Decision needed" matches D31: holds.
## What stayed open
I did not check: DFRobot's overview pictures, P924's column on the board, the session's report.

1 refuted, 12 partly, 9 hold

# Ninth pass, 2026-11-19: D32 to D34, the readiness, the ratings and the board moves

**The verdict:** one claim is refuted. The pass line of P905 (the switch prototype) is written as "asked", but it was never put to him before the commit. There are 11 partly and 11 hold, and 3 board actions are missing. Nothing was written in the tree. My scratch folder is removed.

## 1. The readiness
- "an experiment (the PO chose the next test on 2026-11-19 …": holds. By the rule, a test was chosen by a D before an option, and Q8 and Q14 are open. The precedent for D26 is the fifth pass. The weakest link is not the words but where they come from. The facilitator's reply of 11:38 Prague offered item 3: "If you want the switch's test next: your Ready order for P905". The folder never cites this, so on the page "With D33 it chooses the next test" reads as an inference.
- "It is asked, and it is set before any result": **refuted**. Before 11:45:44 no text names "10 switches": no reply in the five sessions that hold it, no question in the options tool, and no comment on #1279 (the last is 7006678229, 11:37). The 11:38 reply asks five things, and the pass line is not one of them. The same claim is in the Decision needed line ("It is asked on 2026-11-19"), Q1's status ("is asked 2026-11-19"), A2's cell ("Asked of the PO 2026-11-19"), the Test line and D33 ("it is asked"). Fix, in each place: "to be asked in the next reply (not asked at the commit, 11:45 Prague)".

## 2. Stands on
- "9 H, 3 of which would change the decision": holds. A2 to A10 are open, and the three high cells are A2, A4 and A10. `check` printed "stands on 9 H, 3 would change the decision", and its output check passes. It also warns "brief.md: 220 lines; the guide is 150".
- "high D33 for the frame half. The bytes half was not among the nine ratings": holds. The comment's row reads "A10, the frame half | … | high".

## 3. D32
- "His whole message repeats, unchanged …": holds. His message at 11:39:50 Prague, his first after the clear at 11:39:30, is the same string as the paste line. The reply's stamp of 10:38:30Z holds. "paste this line, changed where you disagree" holds, word for word.
- He read the corrected table: holds. Comment 7006141011 says "Corrected at 11:19 Prague", which is before his message.
- "So they accept the count as the result of the test": partly. The "So" follows from "no judgment of a row", which does not support it. Write: "His 'Done' closes the card. The facilitator reads it as his acceptance of the count as the test's result. His words confirm no row as the mission's design." The closing comment 7006863759 repeats the sentence.

## 4. D33
- The high and low sets match the comment, row by row: holds. "So one yes to this table also puts the switch's test first" is in the comment, word for word: holds. The definition of high holds too.
- "(a game's own frame holds 19 fps)": partly. The comment's belief reads "a game's own frame with two 96 px figures holds 19 fps".
- Q1 (brief.md:112), "riskier than A2 …, so one yes … puts A2's test first": partly. The "so" turns the reason around. The real reason is only in the 11:38 reply: "because its test is cheap and the skeleton needs a switch anyway". Write: "…riskier than A2. One yes still puts A2's test first, because its test is cheap and the skeleton needs a switch."

## 5. D34
- The Ready order holds: Status Ready at 11:43:38 Prague, Slice pixel-games. The feel-slice sentence is in #1284, word for word. "you pull the top card of your lane without asking" is in CLAUDE.local.md:24.
- "in the pixel-games lane": partly. W6 (WORKING_AGREEMENTS.md, line 85) reads: "the sound session (the slices "pixel-games" and "graphics library") one in each". Write "in the sound session's lane".
- "The session is past 100k of context": partly. It is true by the transcript's token counts: about 114k at 11:42 and 139k at 11:44 Prague. But the folder holds no evidence for it. The rule says "restart near 100k", not "restarts there". Tag it "(H the facilitator's note of its own session)", or drop it.
- "options: none offered as a question": partly. Write "options: item 3 of the 11:38 reply, 'If you want the switch's test next: your Ready order for P905'".

## 6. The changed header lines
- Riskiest, "· D33: he rated A2 high": partly. The line says itself that D33 "does not say which of the two is riskier". Write "· proposed: the facilitator's pick among the three that D33 rates high. D34 tests it first".
- Test line: the "Done when" quote "He tried each way and named the one he wants" matches #1284: holds. "two placeholder figures at today's size": partly. The card reads "on today's art and today's pool: two figures at today's size".
- Decision needed, "which is Q1's open half for A2": partly. This is circular, because Q1 asks the pass line of "the riskiest test". Write "the pass line of the next test, P905 (D34)". The line also leaves out Q6, which is queued: "decides: the switch's binding · unblocks: Q5". Write "Then Q6 and Q5, which the switch prototype needs, then Q7, Q8, Q10 and Q14".
- The chip and PICK: holds. PICK is D14 (games/engine/actions.py:6).
- Hand-off, "a fifth, a sixth and a seventh time": partly. The eighth pass was applied in 62a76af (verification.md:58-59). Add "and an eighth, on D31 and Q1's proposal".

## 7. Stale lines that the commit did not touch
- verification.md:56, "· Q1, whose ratings decide between them": partly. D33 did not decide between them. Write "· D33 rates both high and does not decide. D34 tests A2 first".
- brief.md:207, Waiting on the PO "Q1's first importance question is asked of him": partly. That question is answered, but the field is still set (since 11:21), and no new question has been posted.
- The searches for "pending Q1", "unrated", "waits for the PO's order" and "No D chooses" find only the rule's comment and the dated Results row: holds.

## 8. Missing actions
- **Missing:** #1308 was closed at 11:46:28 Prague with comment 7006863759, after the commit. No Board actions row records it. The folder does not claim that the card is open.
- **Missing:** a comment on #1279 with D32 to D34 and the pass-line question.
- **Missing:** P905 #1284 has no comment, and its body still dates from 2026-11-18. It lacks D33 and D34, the proposed pass line and the gate of the chip look on a hold of PICK. The fresh session will pull this card, which is the same defect as the sixth pass found on P924.
- The board moves of 11:43 hold: P924 is Done with no waiting field, and P905 is Ready. `check_backlog.py` printed "the limits hold". items.md's new row holds.

## Searches
- I read the diff, the comment, #1284, the closing comment and the GraphQL fields of #1308, #1284 and #1279.
- I read both session transcripts with a small Python script.
- I ran `check`, `check_backlog.py` and `board.py status`.

## What stayed open
- Whether the next reply asks the pass line: it comes after my run.
- A GraphQL read of the whole board did not finish within 120 s and was moved to the background. It is read-only. I used `board.py status` instead.

1 refuted, 11 partly, 11 hold, and 3 missing actions

# Tenth pass, 2026-11-19: D35, the pass line of the switch's test and the pull of P905

The refuter read the commit e30d857 against 8e172f2. The facilitator records its report here, because the refuter writes nothing in the tree.

## 1. D35's words and readings
- **REFUTED:** D35's evidence time "about 12:25 Prague" is wrong. The branch and PR search in the session's transcript ran at 11:21:14Z and printed at 11:21:17Z, which is 12:21 Prague. The commit that records it was made at 11:22:43Z. A run at about 12:25 would come after the text that reports it.
- **Holds:** the quote is exact. His message at 11:18:03Z matches the paste line in the reply of 10:59:07Z word for word.
- **Holds:** "his first message after a clear". The session opens with `/clear` at 11:17:41Z, and "12:18" matches the message's time.
- **Holds:** "does not show that he weighed the other answers", the three answers, and the proposal's date of 2026-11-18 (`git log -S` finds commit 5eebd6e, 2026-11-18 09:27).
- **Holds:** "pull it and plan it" is no yes to a plan.
- **Partly:** the example drops "in a row". The comment 7007110325 says "switch ten times in a row".
- **Partly:** "a wrong figure can only be a press" is too strong. The card #1284 lists ways to switch with no press: the stick's up and down, and the automatic switch to the nearest figure.
- **Partly:** the rule's wording. The rules file says "plan mode, then the plan council ..., then build".
- **Partly:** "the reply asked him to add what he saw". The reply said "If you looked at the chip, add what you saw".
- **Partly:** "the prototype offers no hold of PICK" sits in a D row whose who cell is "the PO", but it is not his word. It comes from the Collection plan (risks-and-tests.md, "before the switch prototype offers a hold of PICK").

## 2. "Set before any result"
- **Holds.** The card was in Ready until 11:19:33Z, and nobody played it.
- Neither the local refs nor origin has a branch of P905. `gh pr list --search P905` finds only #104.
- The branches `p818-pick` and `p819-switch-options` are from 2026-11-15 and concern the app's lineup of games, not this test.

## 3. The summary lines
- **Partly, Ready for:** it lacks D35's caveat "his line does not say how a switch or a wrong figure is counted".
- **Partly, Decision needed:** "no decision ... blocks the plan" leaves out what D35 says. The count of a switch, of a wrong figure and of a switch by mistake is open, and the plan decides it.
- **Partly, the Test line and A2's row:** both drop the second half of the caveat: the line counts no switch by mistake while he moves a figure. A2's belief is "never switches by mistake".
- **Partly, Q1:** Q1 asks only for "the riskiest test", and D33 with D35 now answers it, yet its status stays "asked". Also, the line of A10's frame half is "carried by the facilitator from D22's line", not "proposed".
- **Holds:** the hand-off and the row of items.md.

## 4. The Board actions row
- **Holds:** P905 is in Build since 11:19:33Z, read back as "Build". The output of `board.py status` at 11:19:18Z shows only P918 in Build.
- **Partly:** "the limits hold" was printed at 11:21:34Z, and the refuter reproduced it. It is the gate of the branch `p918-lane-flight`, not main's gate.

## 5. Stale lines and the planned actions
- **Holds:** no line in the folder still calls A2's pass line proposed or asked. D34's line reads as dated history.
- **Holds:** neither planned action is claimed as done. The body of #1284 still says "The pass line is not set".

## 6. Missing actions
- **Missing:** on #1279, Waiting on the PO is still set. The reason in its last row, the pass-line question, is answered. Keep the field with a new reason (the look at the chip) or clear it, and add a row.
- **Missing:** the title of PR #104, "...collecting evidence", is out of date. Only the title was read.
- **Missing:** the sound session's lane has no card in Ready now (Ready holds P927, P923 and P922, all spark cards). That needs his Ready order, so it belongs in the reply's list of what waits on him.

## What stayed open
- Main's gate was not run, because that needs a worktree.
- The refuter ran `git fetch --all` in the main clone of pixel-games. It moved that clone's remote-tracking refs, and no file of a working tree changed.

1 refuted, 11 partly, 14 hold, and 3 missing actions

# Eleventh pass, 2026-11-19: D36, his yes to the plan of the switch prototype

The refuter read the commit 344a10a. The facilitator records its report here, because the refuter writes nothing in the tree.

## 1. D36
- **Holds:** "approved ... with no words of his". In the session's transcript the tool result of 12:05:47Z holds no feedback, and the approved plan's text is identical to the plan file.
- **Holds:** D36's three decided items. Each one is in the plan's section "What the PO decides with his yes".
- **Partly:** "nothing more" and "he gave none". "He gave none" is fair, because the plan said that the stricter reading is "his to say with his yes". Two things are missing: the section's fourth point, "Nothing about the board yet", and the caveat that D33 and D35 carry: a yes given in the dialog does not show that he read or weighed the count.
- **Partly:** "The first is a switch by mistake while he moves a figure". The plan's `extra` is "a switch by mistake while he walks, a double push, or a lean or a turn back". Two mistakes are not wrong under the count: a switch by mistake before the task's first switch is counted `first` and is clean, and a lean or a turn toward the active figure is `same`.
- **Partly:** "The plan's own values". The plan lists more start values, among them `TASK_MIN_PX` and `REACH_PX`, which decide whether an act counts as `reached` or `stray`. "His yes carries them as start values" is the facilitator's reading.
- **Partly:** "The automatic way is a control: its rounds say nothing about A2". The plan says only that it is a control and never ends with `pass`. One case is not checked: if he names the automatic way, D36's reading can never be met.
- **Holds in substance, partly in its evidence:** "The count stands before any result". The reflog of pixel-p905 shows the branch made at 13:06:23 +0100, after the yes at 13:05:47. There is no `logs/run-p905*` file, and the card's only comment is the plan. The branch is from `origin/master` 85c1d54, and the local `master` is another commit. Unlike D35, the claim has no E tag with a time.
- **Holds:** D36's time, as worded. The yes itself is stamped 13:05 Prague.

## 2. The Board actions row
- **Holds.** The URL is right, the comment was made at 12:06:39Z (13:06 Prague) and changed at 12:06:54Z.

## 3. The summary lines
- **REFUTED:** Decision needed, "no decision blocks the switch's test". The plan says that his yes for the board is asked when the probe is merged, and its step 9 runs the smoke run only "With his yes for the board". The same line is stale twice: the look at the chip "decides whether the prototype offers a hold of PICK", and the approved plan offers none. "Q6, an account that the prototype's plan can use": the plan leaves Q6 out, "his play shows it". The Collection plan's row of Q6 is stale for the same reason.
- **Partly, Ready for:** "The count is his since D36" lacks that the count's values are the plan's start values.
- **Partly, the Test line and A2's row:** "a switch by mistake while he moves a figure makes its task wrong". The rule is "a switch that takes the active figure away from the wanted one". Neither line says that a press the box never saw goes uncounted.
- **Holds:** the hand-off.
- **Not reproduced:** "Two council rounds". It is the plan's own claim, cited as such.

## 4. Missing actions
- **Missing:** a comment on #1279 with D36. Its last comment is D35's.
- **Missing:** the draft PR #104. Its title still says "set by D35", and its body says "D1 to D35".

1 refuted, 7 partly, 5 hold, 2 missing actions

# Twelfth pass (2026-11-19, after the play of the switch prototype and D37 to D41)

The refuter read the commit ef22773, the play's log at 8024613, `bench.md` at c7d88ea, the card #1284 with its comments, the probe's classes Tally and Round, `games/pins.py` at 72f0772, the knob's record and the session's transcript. It recounted every round of the log with `python3 -I`. It wrote nothing else in the tree.

## 1. The claims

- **Partly, ★C32.** Every number holds. The lines read: line 901 `p905 task 1 clean streak 1 wrong 0`, line 918 `p905 task 2 wrong streak 0 wrong 1`, line 947 `p905 task 3 wrong streak 0 wrong 2`, line 962 `p905 task 4 clean streak 1 wrong 2`, line 1051 `p905 task 13 clean streak 10 wrong 2`, line 1052 `p905 round stick ends pass streak 10 best 10 tasks 13 wrong 2`, line 225 `p905 round stick ends idle streak 0 best 0 tasks 0 wrong 1`. Round 4 holds 18 switch lines (lines 187 to 219). The caveat is narrower than the log in three ways:
  - Round 4 counts one wrong task (line 225). The claim says only "no finished task".
  - Tasks 4 to 13 hold four `same` lines (954, 991, 1016, 1017). Lines 954 and 991 (`p905 switch child same`) are leans toward the child while the task wants the fireman: a lean toward the figure that the task does not want, which the count leaves out (D36).
  - The stick and the knob stop at their ends (`wraps = False`), so a lean toward the active figure costs nothing. The click, the hold, PICK and the double tap wrap, so every extra press there is `extra`, and that task is wrong. The ways were not counted on equal terms.
  - Fix: add to the caveat "round 4 counted one wrong task; four `same` lines in tasks 4 to 13, two of them a lean toward the unwanted figure, are not counted; the stick and the knob stop at their ends, so the count forgives them more than the ways that wrap".
- **Partly, C33.** The counts hold. "20 s after their last finished task" is false for 7 of the 9 idle rounds, because they have no finished task, and the idle then runs from READY's end (`IDLE_MS`, the comment at line 93 of the probe). "They say nothing against the pass line" drops that five idle rounds each count one wrong task (lines 174, 225, 373, 576, 835). The automatic rounds 1 and 2, which have no task, are left out. Fix: "nine of the eleven rounds ended with idle, 20 s with no task ended; five of them count one wrong task each".
- **Holds, C34.** 16 switch lines in round 8, 6 in round 9, and 8 `act fireman other` lines with no switch in round 7. Caveat to add: 10 of the knob's 16 lines are `same`, so 6 changed the figure.
- **Holds, C35.** The quote is verbatim (13:49:39Z). The read of 14:49:39 Prague is confirmed. Round 5 idles at least 20 s after it, so round 6 comes after the session's text of 14:50:01 Prague. "After" holds, and "because" is not shown.
- **Partly, C36.** Each number holds: fps 16 to 19, paint 32.1 to 40.1, slowest 41 to 437. Two caveats are dropped:
  - The phases lines put the HUD at 184 to 393 ms in 13 of 18 windows of round 10 (for example line 1047, `hud 338`). So the slowest-frame figure is mostly the HUD, and "the cause was not looked for" ignores what the log names. Windows with `hud 1` still read 17 to 19 (lines 920, 940, 949, 956, 1036).
  - The finding's own caveat, "A line can hold frames from before the round's start", is missing.
- **Holds, C37.** `games/pins.py` holds JOY_SW, ENC_A and ENC_B, and no knob switch. The record says "The person's unit has not been seen." Caveat to add: the record also says that Leybold lists 5 pins with SW.

## 2. The sections against their sources

- **REFUTED, A2's status:** "a question, and no demand". At 14:15:44Z (15:15:44 Prague), 16 s before the commit, he wrote "hmm, alright, so lets do a short update and add the knob button using the system when youre done". A2's own change trigger is "he asks for a button the box does not have", and by C37 the knob's button reaches nothing. Fix: record his order, and check A2's retirement against its trigger. His words do not say what the button does, so whether the trigger fired is open.
- **Partly, A2, "retired as tested".** The evidence cell drops round 4's wrong task. The round that passed holds three `extra` lines (909, 936, 938), which are switches away from the wanted figure, and the belief says "never".
- **Partly, D39.** The quotes are verbatim. "With his reason: the knob is the volume" drops that the facilitator's reply 1.5 minutes before said "The knob would have to stop being the volume knob." D39 lists the reply's reasons without this one. The marker "The last two sentences" fits "P905: Done. Go on." literally, so it is unclear whether the switch sentence was a marked recommendation. "It orders no card" is true of that message, but his next message ordered one.
- **Partly, D38.** The quotes are verbatim. It drops the offer's own terms: "If you say "enough" instead, I record it as it is: your words name the stick and the knob, and the pass line was not tested."
- **Partly, D37.** "The option's text" is cut without a mark. It drops "If the suite fails, I tell you, and the play's log still counts unless the fix changes the probe." The times hold: 13:37:29Z, 13:46:10Z, 13:49:26Z.
- **Partly, Riskiest.** "The switch prototype's own rounds … read 16 to 19": only round 10 reads 16 to 19. Round 11 reads 15 to 19, and all rounds read 11 to 21 (the finding). Fix: "the round that passed".
- **Partly, Ready for, and A11.** "A climb wants the stick's up and down too" is written as fact and cited to D29. D29's words name no axis. Fix: mark it H (the facilitator's).
- **Partly, Q14's opinion.** "The skeleton has its switch (D39)" is stronger than the source while A11 is open.
- **Partly, the chip row.** The quote is cut. The full message is "I wont be able to read the chip, any other photo you could use to tell ?".
- **Partly, the Results row.** "An earlier round with no finished task" drops that round's wrong task.
- **Partly, Decision needed.** It is stale since 15:17 Prague. P932 #1320 is in Ready in the pixel-games lane (Status=Ready, Slice=pixel-games, read by GraphQL), so a Ready order for P906 now meets the lane's one place.
- **Holds:** the Test line, Q5, Q6, Q17, D40, D41, the hand-off, the Q6 collection row, and every new Board actions row. GitHub's times: 12:48:56Z, 12:47:27Z, 13:07:31Z, 13:39:26Z, 13:40:59Z, 13:46:10Z, 14:03:10Z, 13:49:26Z, 14:04:51Z and 14:04:00Z.

## 3. Rival explanations

- **A2 retired:** the stick passed partly because its count forgives a lean toward the active figure (section 1). The three `extra` lines in the passing round speak against "never".
- **A11:** the climb may be an act by FIRE at the ladder, the probe's own model ("walk to a ring and press FIRE"). Then nothing collides, so A11 rests on a design that the facilitator assumes. Against that rival, the four `same` leans in the streak would be climb inputs on a shared axis. That is evidence for A11 that the row does not cite.
- **"His own choice" (D39):** he echoes the facilitator's volume argument, and he still wants the knob in play (P932).
- **"Enough" (D38):** he declines the knob's round, or he is done after a round that he saw pass.
- **"Done" (D40):** he pasted the block without reading it. The same reply asked for a clear and `/model` first, and the facilitator noted "You pasted the text into the same session, with no clear before it".
- **"Collecting evidence":** it holds by the template, because no D chose a test. No collection runs.
- **The frame half (C36):** the HUD repaints of an untuned probe, not the figures, make the slow frames.

## 4. Numbers that lack a unit, a population or a provenance

- The length of an `fps` window and of a `time` window is unstated (C36, the Results row).
- "18 switch lines": 4 of them are `same`, and the session told him "17 switches".
- "16 switch lines from the knob": 10 of them are `same`.
- "20 s after their last finished task" names the wrong population (C33, and the finding).
- "Rounds … 16 to 19" covers one round (Riskiest).

## 5. bench.md's section

The table's 11 rows match my recount in every column. These sentences say more than the log holds:
- "with nobody at the buttons" (line 1962): the log cannot show it.
- "he did not press QUIT" (line 1965): the log shows only that no `done` line exists.
- "because the screen does not say the task" (line 2013) is H.
- "The cause of the slow frames was not looked for" (line 2014): the phases lines name the HUD.
- "round 4, with 18 switch lines and no finished task" (line 1998) drops its wrong task and its 4 `same` lines.
- "Not shown" lacks the uncounted leans of lines 954 and 991.

## 6. Missing actions

- **Missing:** a D row for his order of 15:15:44 Prague ("hmm, alright, so lets do a short update and add the knob button using the system when youre done").
- **Missing:** a Board actions row for P932 #1320, filed 14:17:24Z in Ready, slice pixel-games, under #1279.
- **Missing:** the Ready order between P932 and P906 in the lane's one Ready place is not asked.
- **Missing:** his question "would the knob buttton work too?" got no answer in the session before his order. Between 14:08:11Z and 14:15:44Z the only text to him is "The section on your play is written into `bench.md`…". P932's body ("When he heard that nothing is wired for it") is not in the transcript.
- **Owed, as the commit says:** verification.md's row for ★C32.

## Searches: none

Not checked: the figures' act sizes, because I did not trace which act poses the probe uses.

1 refuted, 13 partly, 12 hold, 4 missing actions

# Thirteenth pass (2026-11-19, after D42 to D44)

The refuter read `git diff ef22773..f064717` for brief.md, risks-and-tests.md, verification.md, story-map.md and items.md. It also read the session's transcript, the photo of his knob's module, the comments on #1320, #1284 and #1279, the board fields of the four cards by GraphQL, and `bench.md` at a089674. It wrote nothing else in the tree.

## 1. D42, D43 and D44 against his words

- **Holds:** his own words in all three rows are exact. "hmm, alright, so lets do a short update and add the knob button using the system when youre done" (14:15:44Z). "OK, maybe the encoder doesn't have a button, even though it feels like it does, I can press it down. But I see no other pin to connect" (14:24:43Z). "Park it" (14:31:30Z). "sounds good, do it" (14:35:45Z).
- **REFUTED, D42's quote of the facilitator:** "If you want that looked at, say so, and I file it as an idea card with your words." The transcript holds this sentence only in the facilitator's own script that wrote D42, at 14:28:27Z. The words to him before his order are a narration at 14:10:05Z: "The knob's button can't be used as things stand: the board exposes only GA, GB, VCC and GND, and the pin map has no wire for the push switch. Shop photos suggest the knob has one, but nobody has verified your unit, so I'll file it as an idea card if you want that checked." Fix: quote these words, or mark the quote as the facilitator's reconstruction. The substance holds: the offer named an idea card, and his words ordered the work.
- **REFUTED, D43's quote of the facilitator:** "are you fine with soldering one wire onto that little blue board? If yes, I plan it as P932 after I close today's record. If no, I park the card." The transcript holds it only in the script that wrote D43, at 14:33:02Z. The words before "Park it" are the narration at 14:30:30Z: "The photo shows the four pads read GND, VCC, GB and GA, and the two solder points beside the knob are very likely the push switch's legs, though that's only a guess from one photo. Do you want to solder one wire onto that blue board so I can plan P932, or should I park the card? I'm finishing the P905 close now." "After I close today's record" is not in them. The card's comment 7012074663 ends "Asked of him: whether he is fine with solder on the module. If not, the card is parked." Fix: quote the narration.
- **Partly, D43's time:** "15:32 Prague, the time of the card's comment". His word is of 14:31:30Z, which is 15:31 Prague.
- **Holds, D44's quote of the question.** It is verbatim in the text of 14:33:35Z.
- **Partly, D44:** "So Q14 is answered: the mission first, and the reusable figure is separated out of it after." The options that he saw were "the walking skeleton P906 first …" and "the reusable figure P901 first, and the mission on it after". No option said that the figure is separated out after. That half is Q14's wording in the brief, not his answer.
- **Rival reading of "sounds good, do it":** the same message ends its state with "When it passes, I merge that PR and write the closing report", and says that the twelfth pass is applied. "Do it" can answer that, or take the advice and leave the Ready order that "then … follows" as a later act. D44 tags its reading of the Ready order H, and "his words take the advice and order it" says more than that.

## 2. "Ready for: an experiment"

- **Holds by the letter.** The rule at the top is "the decider chose a test (a D) before choosing an option". It does not ask for his pass line. The Test line has dated lines: the frame half's line of 2026-11-18 (the facilitator's, from D22) and A4's proposed line. D34 set the precedent: a Ready order counted as the choice of a test before D35 set its line.
- **Partly:** "the PO chose the next test … for A4 and the frame half of A10". He answered "what is built next?". His words and the question name no test, no A4 and no A10. The mapping is the facilitator's, so tag it H. A2's open part, the climb, has no pass line at all, and the Decision-needed line leaves it to P906's plan.

## 3. The photo of his knob's module

- **Holds:**
  - The labels read GND, VCC, GB and GA, top to bottom, which is the record's `pin_order`.
  - Two silver solder points sit at the board's left edge, one above the other, on the side away from the labels.
  - Six small parts stand in a column: one above GND, four beside the labels and one below GA.
- **Partly:** "very likely the push legs". From the top only one solder point shows on the labels' side of the encoder, so the "three turn legs on one side" that the reading leans on cannot be seen. The H tag is right, and the photo itself does not support "very likely".
- **Partly:** "no pad for the push". The photo shows no fifth label. The four pads are hidden under the jumper wires, and the bottom side is not seen. Fix: "the top shows no fifth label".
- **Not noted:** the record says four resistors and one capacitor, five parts. The photo shows six. The folder and the card do not say that the photo and the record disagree.

## 4. The twelfth pass's fixes

- **Holds, applied as given:** ★C32's caveat, C33, D37, D38, D39, the chip row, A2's row, the Results row, and C36's `hud` counts. My recount gives 13 windows at 184 to 393, and 5 windows at 1 (lines 922, 942, 951, 958 and 1038).
- **Partly, C36 and bench.md:** "the `time` lines are in ms". The log's `time` lines carry no unit, like the `phases` lines. Fix: cite the code that sets the unit, or drop "in ms".
- **REJECTED, my own twelfth-pass point:** "his question got no answer in the session before his order". The narration of 14:10:05Z (quoted in section 1) answered it. The transcript does not show whether a narration reaches his screen. The correction of P932's body ("heard" removed) and verification.md's line on it rest on my error. Fix: restore or qualify "heard" on P932, and correct that line.

## 5. The new Board actions rows

- **Holds:** every time and state that I read back:
  - comments: 14:25:10Z, 14:30:36Z, 14:31:02Z, 14:31:33Z (updated 14:32:04Z), 14:32:01Z and 14:36:45Z
  - #1284 CLOSED at 14:31:08Z, with Status Done and no waiting field
  - #1320 in Idea, slice pixel-games
  - #1285 in Ready, slice pixel-games
  - #1279 in Discovery, with no Waiting fields
- **Stale since the commit:** "the draft PR #117 merged · pending". It merged at 14:40:35Z, which is 15:40 Prague, at merge commit 014fcfd. HEAD f064717 is of 15:37:53.

## 6. Missing actions

- **Missing:** a Board actions row for PR #117's merge (15:40 Prague, 014fcfd).
- **Missing:** the title of the draft PR #104 still ends "collecting evidence", and the brief now says "an experiment".
- **Missing:** the correction of P932's body and of verification.md's line that rest on my withdrawn point (section 4).
- **Missing:** a note that the photo's six small parts disagree with the record's five. The record is in spark's store, so this is a found item for its card, not a change here.

## Searches: none

Not checked: whether a narration block reaches the PO's screen, and the code that gives the `time` lines their unit.

2 refuted, 6 partly, 16 hold, 4 missing actions; 1 of my own twelfth-pass points withdrawn

# Fourteenth pass (2026-11-19, after D45 to D47)

The refuter read the diff from bb4e2cf to 28b2c31 in full, the approved plan, the card's comment, the three session transcripts, the board fields, the build worktree, the play log of P905 and the entry of bench.md for it. It wrote nothing in the tree.

1. **REFUTED.** D46, third point: "the prototype's mapping the other way round, which he played for 15 minutes on the same day". The sitting ran from 14:46:14 to 15:02:34 Prague (bench.md:1964) and had 11 rounds across seven ways. The stick, with up for the fireman, ran in only 2 of those rounds: log lines 185 to 225 and 891 to 1052, which hold 22 of the log's 192 `time` lines. Fix: say that the 16-minute sitting played this mapping in 2 of its 11 rounds.

2. **Partly.** D46 says "the yes holds what the plan's section ... lists, and nothing more". It then says "the facilitator reads his yes as carrying all of them as start values (H)". But the plan calls only the speeds and the places start values (plan:486-489). The lean's 40 and 20 and READY define what counts as a pick, so they are part of the pick line. Fix: hold those values fixed with the pass lines, and keep only the speeds and places as start values.

3. **Partly.** Q7 and Q10 both read "answered D46 for the walking skeleton". The discovery check now prints "15 asked, 2 queued", so what stays open beyond the skeleton has left the queue. The Appetite slot still reads "—: —". D46's fifth point and Q10 also drop the plan's stop rule: "If the time ends before "ready to play", I stop and report what is missing". Fix: keep a queued remainder for each question, and quote the stop rule.

4. **Partly.** The Hand-off says "approved it in plan mode (D46)" but leaves out "with no words of his" and the caveat that a yes does not show he weighed each line. It also keeps "(Q8, Q14) are unconfirmed", while this commit's items.md says "D44 answered it". Fix: carry the caveat over, and make the Q14 wording the same in both files.

5. **Partly.** Lines the commit left stale:
   - story-map slice 0's tag ("H A10's frame half, A2, A7") lacks A4.
   - risks-and-tests' P905 Results row says "possibly wants the same axis (H, the facilitator's)".
   - jobs-and-journeys:51 still asks "What does it do? (Q7)".
   - The revision row says "The way that he chose uses no PICK", yet Decision needed cites it for the skeleton's PICK.

   Fix: add A4 to the tag, and a "D46 then ..." note on each of the other three.

6. **Partly.**
   - D45 says the message "ends with three lessons ... and "Go on."". The sentence "The state is in the memory note ... and on the card." stands between them.
   - D47 quotes "(16:41 Prague". The approval's stamp is 16:40:14, and 16:41:03 is the facilitator's clock read after it.
   - The plan file is 35,396 characters with its last newline. It matches the other two texts once the ends are stripped.

   Fix: one clause for each.

7. **Holds**, 11 checks:
   - D45's and D47's texts match the replies' code blocks (924 and 549 characters).
   - The plan was submitted at 15:29:27Z and is the same as the approved text, so "he changed nothing" holds.
   - The approval is 16:40 Prague; the comment was created 15:41:13Z.
   - Status Build was set at 14:50:32Z, with Slice pixel-games and "the limits hold".
   - The branch was made at 16:41:17. ls-remote prints nothing, and none of the 24 worktrees has a p906 log, still true at 16:58.
   - The seven points cover the plan's eight bullets.
   - The pass lines, the tally, when a line is not read, and the verdict are restated correctly.
   - The PICK claim matches plan:192-193.
   - Waiting on is empty on both cards.

8. **Missing.** The body of #1285 still says "Open for this card's plan: how the child's climb is steered ..." and "A fresh session pulls the card and plans it". Fix: add a line with D45 to D47.

## Searches: none

Not checked: what he read while the dialog was open for 11 minutes, the plan's other code citations, and whether `time` lines are evenly spaced.

1 refuted, 5 partly, 11 hold, 1 missing action

# Fifteenth pass (2026-11-19, after the play of the walking skeleton, D48 to D51)

I read the diff from 8a65cdb to 1b18b43, all 194 lines of the play log, both smoke logs, bench.md lines 2025 to 2090, the probe and `art/mission.py` at 71333b2, the plan, the transcript from 16:08Z to 22:38Z, the four card comments, the board fields and the store's record for the box.

1. **REFUTED.** D50 says his words came "between two commands that the session's clock puts at 23:26 and 23:27 Prague".
   - The transcript holds them as a queue record (`enqueue`) stamped 2026-11-19T22:25:58.207Z, which is 23:25:58 Prague.
   - A `queued_command` attachment with a human origin carries the same stamp.
   - At 22:26:35Z they were handed to the running turn as a system note ("absorbed_mid_turn").
   - That is 35 s after the sitting ended, between the session's clock reads of 23:25:31 and 23:26:32.
   - Fix: write "23:25:58 Prague by the queue's stamp".

2. **REFUTED.** bench.md's frame bullet is wrong on two numbers.
   - It says "a send of 3.3 to 10.5 ms", but line 25 reads `send 2.6`.
   - It says the heap is "236,960 bytes in round 1 and 278,480 from the first result screen on". Line 100 reads 237664, and lines 116 to 150 read 278656 to 279264.
   - Fix: write "2.6 to 10.5", and give the heap as ranges.

3. **Partly.** Lines the play made stale:
   - The Ready-for line and the Hand-off both still say "which no play tested".
   - The Hand-off still says "his play is asked: the card says ready to play" and "Its frame half is untested".
   - The P905 Results row also says "which no play tested".
   - The feasibility risk row still names "the walking skeleton's log" as the next test.
   - Fix: rewrite each line to match the play's result.

4. **Partly.** The Riskiest line says "so the frame half of A10 has its first evidence", and the new riskiest pick is marked as a proposal. But it rests on rates that the plan does not read.
   - The plan says "The first round of a sitting is left out".
   - Round 1 holds every slow gap in the sitting: `slow 5` against `slow 0`.
   - The slot's head still names A10 as the riskiest.
   - Fix: say this in C39's caveat and in the slot.

5. **Partly.** Five of the eight wrong picks changed nothing: lines 80, 118, 172, 173 and 179 are `same`.
   - Round 1 is wrong only by D46's stricter rule. By D36's count it would be clean.
   - After D46, the build changed two tally rules ("Each lean of the stick during READY counts as a pick", and one detector for the whole sitting). He was told this at 20:18.
   - bench.md says "The reading was fixed before any run". No line of the log has ms 0, so the READY change touched no pick.
   - Fix: add both facts to C38 and to bench.md.

6. **Partly.**
   - D48 says "It ended:", but the reply goes on with the P828 bullet.
   - D50 calls his words "a signal against A3", but A3 compares 96 px with 24 px, and "too big" names neither size.
   - Fix: one clause for each.

7. **Partly.** bench.md says "no deploy since".
   - The store's record of the box (firebeetle2-esp32s3, 34:85:18:xx:xx:xx, the last three bytes masked in this copy) has its last deploy at 2026-11-19T10:11:37+01:00, made by `box.py`, and none after it.
   - Fix: cite that record, and add that a copy made outside `box.py` is not recorded.

8. **Holds** (11 checks).
   - The quotes in D48, D49 and D51 are exact. D51's question is in the turn's last reply (22:28:13Z), so it is stored as written.
   - D49's "about three hours later" holds: the report is stamped 20:18 and his yes 23:18.
   - The gaps recount: 600, 440, 640, 1,400, 1,083 and 79 ms.
   - The rates recount: 24.92 and 24.90.
   - Every cell of bench.md's table recounts.
   - Both smoke logs hold: 68 and 63 lines, eight `fps ladder 24` lines each, and no pick.
   - C41 holds against the code: `PACE = 2` at line 117, and 282 − 117 = 165 px.
   - The three readings match plan lines 101, 106 and 113.
   - The 11 Board-actions times read back.
   - The fields read back: #1285 is in Review, waiting on the PO since 2026-11-19. #1279 is in Discovery.

For verification.md:
- ★C38, line 145: `p906 round 2 ends wrong ms 16949 gaps 422 worst 46 slow 0 streak 0`. A search for `streak 5 met` printed 0.
- ★C39, line 105: `p906 round 1 ends wrong ms 68821 gaps 1715 worst 65 slow 5 streak 0`.

**Missing.**
- His `/clear`, queued at 23:32:47 Prague, still waits while the session works on.
- The body of #1285 has no line on the play, and its "Done when" is now met.
- #1279 has no Waiting on, although the Decision-needed line lists three decisions of his.

## Searches

None.

Not checked: the captured speeds 199 and 108 (they need a paint with the CMU files), and what the box held, because I did not touch it.

2 refuted, 5 partly, 11 hold, 3 missing actions.

# Sixteenth pass (2026-11-20, after the sheet of sizes, D52)

I read both diffs, the picture, sizes_sheet.py, art/mission.py and moves.Ladder at 92569c5, probe906_ladder.py, log lines 60 to 194, D36, the transcripts (spark 90ee8eec, pixel-games 87e18361 and ad4bec61) and the store's morning note. I ran the script once and measured each height with three more scripts in scratch.

1. **Holds.** C42's numbers match my printed lines: fireman 50/66/81/97 and child 34/46/57/68. My picture is `(640, 1016)`, and its sha256 813f418c… matches the committed file. ad4bec61 shows two earlier runs, at 00:21 and 00:24, with "same picture: cmp exit 0".

2. **REFUTED: "so a smaller fireman does not reach the rail".** The picture and my measurement say otherwise. At 48 px his glove (row 172, column 98) touches the rail, which is in columns 96 and 97. At 64, 80 and 96 px his hands reach 5, 8 and 9 columns past it. The small rows go wrong in a different place, the child's climb. END_UP is 54 px, so the child's top row is 29, 19 and 6 px under the roof's row 96 at 48, 64 and 80 px. Only at 96 px is it over the roof. Fix: write the child's shortfall instead. The morning note's line 19 needs the same fix: "a smaller fireman stands a little off the ladder".

3. **Missing caveats.**
   - The ladder's slant follows each height's climb, at (3,9), (3,12), (4,16) and (5,19). So the ladder's top is at column 72 at 48 px and at 80 to 82 at the other heights.
   - The child's height is not chosen on its own: it is about 0.7 of the fireman's.
   - The bar uses PIL's font, not the box's 8x8 font (Storyboard's docstring). Yet sizes_sheet.py says "each as the box shows it".

   Fix: add these to the caveat in one sentence.

4. **Holds.** Both quotes in D52 match the transcript character for character (checked as substrings). The 00:18 and 00:20 times are right. The spark session passed the words on with SendMessage at 23:18:23Z and 23:20:28Z.

5. **Missing.** His second message says: "when you need my input, use fable and the council … to decide for me". The record still asks Q20 of him and calls each part "his", and no (H) gives the reason. Nor does D52 say how "prioriittize spark" was applied. This session offered to take a spark card, and the spark session declined at 00:23. Fix: add one (H) sentence on each.

6. **Partly.** "under his words of D52" (in the Decision-needed line and in Q20) reads as if his words covered the sheet, and D52 says they do not. "status: asked 2026-11-20" was committed at 00:24:45. The morning note was written "from 00:27 Prague on", and Q20 names no place where it was asked (compare Q16). The rule: "If the decider cannot be asked, the queue stays here". Fix: "on the facilitator's reading of D52 (H)", and "asked 2026-11-20, 00:27, in the store's morning note". The collection row and the value row hold.

7. **Missing.** The Hand-off still ends at the fifteenth pass and names neither D52 nor the sheet. The Files line lists neither new file. Fix: add them.

8. **Holds.** D50's times match the enqueue at 22:25:58Z and the remove at 22:26:35Z. The Riskiest line and the sentences of C38 and C39 hold: 17 picks, 8 wrong, and lines 80, 118, 172, 173 and 179 are `same`. "slow 5" and "slow 0" are in lines 105 and 145. So do both rows in verification.md. The facilitator is right to reject the fifteenth pass's sentence. Line 79, `act none click 52099`, comes before line 80, `pick child wrong same`, so the child was active in task 1. D36 counts "an act of the figure that the task does not want". The probe leaves `act none` out of its tally, so ★C38's wording holds.

## Searches

"with no answer yet": 0 hits. "no D chooses": only the Ready-for line, still true. "offer": Q20's offer is real (reply at 22:28:13Z). "collecting evidence": consistent.

The check printed: "Questions: 16 asked, 6 queued", "Output check: pass", "Ready for: collecting evidence · stands on 9 H, 3 would change the decision".

Not checked: how big the box's screen looks against a monitor (no bench); the council brief this session wrote at 00:26, after the commit.

3 hold, 1 refuted, 1 partly, 3 missing.

# Seventeenth pass (2026-11-20, after the night's council and build, D53 and C43)

I read the diff 3953c33..19537cf, the council and plan comments, the PO's two messages in the transcript, PRs 120 and 121 with their reviews, both sheets, the plan file and the board.

1. **Partly.** D53 against the reports: the votes are right (FIRE first is 2 of 3, and the architect wants the stick's left). But the PO assistant never says "percent" or "places following". Those come from 2 of 3, and they read as if they sit under "All three say". D53 also leaves out the PO assistant's "Do not write a council answer as a D row" and "Do not add pictures or a long record with many refuter passes". Since then the night added a repaint and this pass, and the check says "brief.md: 323 lines; the guide is 150". Fix: name the percent and the places as 2 of 3, and say in one sentence that the D row and the repaint go against the PO assistant (H).
2. **REFUTED.** "an experiment, by delegation". The folder's rule says "an experiment: the decider chose a test (a D)". D53 says "not his word". Q22 is still "queued". The third pass refuted the same reading (verification.md:40). The check also drops the qualifier: "Ready for: an experiment". Its Next changed from "none — … the PO" (on a scratch copy of 3953c33) to "superpowers:brainstorming". Fix: keep "collecting evidence" and put the delegated second sitting in the parentheses.
3. **Missing.** His words, "use fable and the council … to decide for me", hold as a premise. Four steps rest on readings with no (H) tag: starting new work on that message, building pixel-games work under "prioriittize spark", building a plan with no yes of his, and moving P906 back to Build. Only the no-merge reading is tagged. Fix: one (H) sentence in D53 that names these four.
4. **Partly.** These numbers in C43 hold: 1621 and 1292.429 s on f61fd1a, run by the builder. 1637 and 1016.670 s on 44d249f. 10 plus 2 sessions, three ways, 108/90/71/54, 3.3/4.6/7.0/10.9 s (the plan's table, lines 443 to 446), 2 px, 25 rows, Python 3.10.0. Both PRs are OPEN, not drafts and not merged. But the twelve sessions ran on PR 120's branch only, not on p906-height. C43 also leaves out that 89 older rows of PR 120 did not run. Fix: name the branch and those 89 rows.
5. **Holds.** C42: by my eye, the child is at the ladder's top at every height. The 3953c33 sheet ends the child mid-ladder at 48 to 80 px. The figures 6/4/2/2 are in PR 121's body, not in its review comment. From 839cc45 to the head, art/mission.py renames things only.
6. **Holds.** Board times, in Prague: the comment 00:35, the move Review→Build 00:35, the plan 01:21. PR 120 was opened at 01:33 and marked ready at 03:23. PR 121 was opened at 02:55 and marked ready at 04:56. Card #1285 is Build with no Waiting on. The spark session declined at 00:23.
7. **Partly.** D51 still says "A change of it is not built". PR 120 builds the pace. Fix: add "built in PR 120, not merged (C43)".

## Searches

None of these is stale outside D51: "no D chooses", "collecting evidence", "with no answer yet", "not built", "no second sitting", "waits for his play".

Check output, as printed: "Questions: 16 asked, 6 queued" · "Output check: pass" · "Ready for: an experiment · stands on 9 H, 3 would change the decision".

Not checked: when the morning note asked Q20 (the file was last changed at 05:00). The fault-handler run. Who ran the 1637-test suite: the line appears first in this session's own transcript, so the session most likely ran it.

2 hold, 3 partly, 1 refuted, 1 missing.

# Eighteenth pass (2026-11-20, after the second sitting, D54 to D56)

I read PR 122 at caf2d31 (both logs, bench.md lines 2101 to 2156), the brief's diff 7cd05c9..768f8f8, the four card comments, the transcript, both plans, `probe906_ladder.py` on master, and log 3. Nothing in any tree was changed.

1. **Holds**: the log counts, in all three places. Round 1 is lines 24 to 70, with 713 × 1,000 / 28,610 = 24.92. Round 2 is lines 76 to 138, with 24.67. The picks are 5 right and 4 wrong (3 same, 1 switch), then 6 right and 6 wrong (2 same, 4 switch). The gaps are 2,135, 2,519, 686 and 1,982 ms. The climb took 7,020 ms. The ranges of the `time` lines, the heap values (they change at line 75), the eight lines of 24 fps in the smoke run, the line counts 64 and 237, and the pack and load lines all check out. Every act is a `click`. "5 of the 10 wrong picks changed no figure" holds. They are lines 35, 45, 59, 99 and 111, and code line 90 says a `same` pick is a lean that picks the active figure. ★C44's line, verbatim: `p906 round 2 ends wrong ms 32383 gaps 799 worst 64 slow 1 streak 0` (line 138), with no `streak 5 met` in the 237 lines.

2. **Holds** (the brief, the comments):
   - **His words:** all four quotes are exact. The stamps are 08:02:27Z, 08:11:53Z in the queue, 08:14:12Z in the queue and 08:15:14Z, which is 09:02, 09:11, 09:14 and 09:15 Prague.
   - **The session's quoted sentences:** the ones in D55 and D56 are exact (08:13:03Z and 08:14:41Z). D56's "as its reply had said" holds: "With "drop", the merges ... follow at once."
   - **The pass lines:** "not read", "not met" and "not read" hold by the probe's docstring (lines 12 to 20) and council comment 7025261567.
   - **The merges:** they happened at 09:15:54 and 09:16:09 Prague. Master's tree equals 71d4f97's tree (f710084). Both branches are deleted.
   - **The status lines:** "collecting evidence" and the statuses of Q20 and Q22 are fair.

3. **Partly**, D54 (the brief): he sent the whole line as the example gave it, not only the height. The message he answered (07:56:10Z) named trial 2 as "your sitting with the FIRE way ... at pace 100". Fix: say both facts.

4. **Missing**, D55 (the brief): the question was first put before he played, at 08:07:14Z: "was the climb too slow at your height?" Fix: add that he played already knowing this question would come (H).

5. **Partly**, "while he runs" (bench.md, the brief, comment 7034185099):
   - bench.md's lead-in "The wrong picks while he ran:" states his account as the log's.
   - The comment's "So the picks go wrong while he runs" and "the climb's place ... was not the only cause in the first sitting" are not tagged, and the mapping flipped between the sittings.
   - The Riskiest line's "no longer the climb beside it" is not tagged either, while every FIRE was the stick's click.
   - Unused support for his account: line 91 is a FIRE 1,339 ms after the unwanted switch of line 90, and it held nothing. No switch followed a click within 1 s.

   Fix: tie each sentence to D56 or tag it (H), and add line 91.

6. **REFUTED**, comment 7034185099: "Round 2, task 1, lasted 17 s" is wrong. The hold is at 19,578 ms (line 108). 17.2 s is the time from the first fireman pick (line 82). Fix: post a corrected comment.

7. **Partly**, C46, Q24 and the Decision-needed line (the brief):
   - **The 3.3 s:** it is not only calculated. Log 3, lines 102 and 103, measures 3,322 ms at 96 px.
   - **The cause:** that log's climb ended at 57 px, and this sitting's at 76 px. So the longer distance explains part of the 7.0 s, not only the pace.
   - **Round 2:** its three goes add up to 7,021 ms. Its "stops 32" after "starts 33" (lines 127 and 128) is a pose value from the code's pose table, not a slide down.

   Fix: add these four facts.

8. **REFUTED**, stale lines (the brief):
   - The Ready-for line's "(the start of this line)", which appears twice, now points at ★C44, not ★C38.
   - Line 84 says "not merged and never ran on the box".
   - Line 208 says "which is not merged".
   - Line 321 says "The merge waits for a smoke run".
   - risks-and-tests.md line 65 says "No D orders that sitting".
   - C44's "third mapping" is wrong: there are two mappings, and this was the second change (code lines 6 and 7).

   Fix: correct each line.

## Searches

- "not merged": brief lines 84, 208 and 321.
- "waits for a smoke run": line 321.
- "No D orders that sitting": risks-and-tests.md line 65.
- "never ran on the box": line 84.
- "his pick is asked": no hit.
- "no D of his orders that sitting": no hit.

The discovery check gives "Output check: 1 problems", and the one problem is "verification.md: ★C44 needs its row, ending in keep". It also prints "brief.md: 338 lines; the guide is 150".

Not checked:
- The 132 and 71 px a second. 108 × 64 / 96 = 72, and I did not run `art/mission.py` to see where 71 comes from.
- The store's deploy record and the box itself, which was off limits.
- The Mac-clock start times.

Counts: 2 Holds, 3 Partly, 1 Missing, 2 REFUTED.
