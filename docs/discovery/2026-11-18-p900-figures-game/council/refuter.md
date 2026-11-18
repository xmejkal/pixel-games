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
