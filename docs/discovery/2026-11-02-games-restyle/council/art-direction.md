# Art-direction lens: P565 games restyle

Read: games/arcade.py, arcade2.py, space3d.py, world3d.py, gfx.py (Game, Particles), lcd.py (picture), pictures.py,
st7789.py, art/paint.py (Sprite, runner poses, q565), art/PROMPTS.md, art/preview.png (seen as an image), bench.md
(the cost lines), council/user.md (to avoid repeating it). Nothing was run on the board. Six web searches and two page
reads. Tags: E (pointer), H (where it comes from), D (who, when). These are options for the PO, not decisions.

## Findings

### The facts the look must fit

- ART-1 · The game canvas is 320 wide by 240 tall (wide), not 240x320: every layer, sprite and title card is
  composed for a wide frame. · E · games/st7789.py:15 ("landscape: MADCTL below turns the 240x320 panel on its
  side"). art/paint.py:18 (`W, H, GROUND = 320, 240, 192`) · supports: the frame of all art below.
- ART-2 · A painted picture is drawn by one `blit_buffer` at a position, with one clear colour. There is no scale,
  rotation, flip or alpha. So squash and stretch, tilt and every pose must be baked as separate frames in
  art/paint.py. · E · games/lcd.py:78-81. games/pictures.py:60-67 · supports: the animation plan (part 4 below).
- ART-3 · A sprite has a hard mask: each pixel is fully on or off, with a pencil outline outside it. Soft glows,
  smoke, motion blur and semi-transparent water cannot be sprites. They must be baked onto a known background
  (as the sky rows are) or drawn as particles and fills. · E · art/paint.py:1-8 (docstring), :481-504 (`cut`)
  · supports: which effects each direction can afford.
- ART-4 · Frames are cheap in time and memory. A keyed 16x24 sprite blits in 19.8 µs. One 16x24 frame is 768 bytes;
  8.32 MB of PSRAM was free for the pool, and all art today is 1.5 MB. Even 300 extra sprite frames (about 230 KB)
  cost under 1 ms of paint if only a few are drawn per frame. · E · bench.md:169, :172, :176 · caveat: load time at
  boot and the file count were not measured · supports: "well animated" is affordable. The limit is painting time,
  not the board.
- ART-5 · Full-screen motion costs send time. A frame that changes every tile sends in about 31 ms. Partial sends in
  a mostly still game are 4 to 17 ms. A screen shake moves every tile, so in stack, snake, cube, tunnel, starfire and
  gravpong a shake costs about +15 to +25 ms per shaken frame. Runner and flappy already send full frames, so a shake
  there is nearly free. · E · bench.md:115, :162, :173 · H (my reading of those numbers. Not measured with a shake)
  · supports: shake only on death or a big hit, 3 to 5 frames.
- ART-6 · RGB565 keeps 5 bits of red and blue (32 steps); `q565` truncates without dithering. A smooth gradient over
  240 rows bands in steps of several rows. The painted watercolour hides this with grain. A flat-colour direction
  avoids the problem entirely. · E · art/paint.py:1233-1240 (`p[0] & 0xF8`, `p[2] & 0xF8`). art/preview.png (the
  skies show no visible bands because of grain) · supports: direction choice.
- ART-7 · Text costs time (about 2.5 ms per text run. The game-over box painted in 93 to 140 ms at one point). A
  title or game-over "moment" should be a painted picture with lettering baked in, not drawn text. · E ·
  games/arcade.py (Runner.paint comment "no text, which costs ~2.5 ms"). bench.md:77 · supports: title and game-over
  cards below.
- ART-8 · The death moment has a fixed stage: after `die()`, `paint()` still runs every frame while the over box
  shows, and a retry is blocked for 900 ms. The title lasts 1500 ms. So a death animation has about 22 frames before
  a retry is possible, and a title animation about 37. Today both are one shared generic shell for all ten games. ·
  E · games/gfx.py:285-286 (`TITLE_MS = 1500`, `OVER_MS = 900`), :309-314, :365-396 · supports: frame budgets for
  title and game-over per game.
- ART-9 · Particles exist (at most 40, drawn as 2x2 or 3x3 fills, with gravity). Debris, feathers, sparks and dust
  fit them. Anything bigger than 3 px or shaped must be a sprite. · E · games/gfx.py:233-258 · supports: particle
  use per game.
- ART-10 · The working sprite size the PO already approved is 16x24 for a person, with a 6-frame run cycle at 14 fps
  and a 5-pose jump (takeoff, rise, apex, fall, land). Flappy's bird is 18x14 with 2 wings x 3 tilts. Both read on
  the preview at 4x. · E · art/paint.py:520-556 (RUN, JUMP). games/arcade.py (Runner.pose, `int(t * 14) % 6`);
  art_index.py. art/preview.png; D the PO 2026-11-02 ("super cool, I love it", brief.md Frame) · supports: the size
  floor in part 4.

### What other games prove

- ART-11 · Strong limits read well and became a signature: Downwell uses a palette of four colours by default (black
  ground, white outlines, red for gems, enemies and key items, blue for water) and lets the player unlock other
  palettes. · E · https://en.wikipedia.org/wiki/Downwell_(video_game), read 2026-11-02 (citing a Nintendo eShop
  listing and Rock Paper Shotgun 2015) · caveat: a fan page says three colours; Wikipedia says four · supports:
  direction B.
- ART-12 · Lucas Pope on Return of the Obra Dinn's 1-bit look: "I decided to prioritise legibility above all else"
  and "the most important part of using dithering was to use it as little as possible". The low resolution
  (640x360) conflicted with dithering when stretched. · E ·
  https://blog.playstation.com/archive/2019/10/17/lucas-pope-on-return-of-the-obra-dinns-art-style, PlayStation
  Blog 2019-10-17, read 2026-11-02 · supports: direction B (use little dither on a small panel).
- ART-13 · Silhouette style: Limbo (2010) set the trend, and Badland (mobile) looked very similar while playing very
  differently; Limbo has no HUD and shows only silhouettes of the character, enemies and surroundings. · E · search
  results (paleocave.sciencesortof.com "Demo Sunday – Limbo". Experimentalgamedesign.sites.northeastern.edu
  2018-12-07), read 2026-11-02 · caveat: snippets only. Nothing found on small-screen readability · supports:
  direction C.
- ART-14 · Game feel by added feedback: Jan Willem Nijman's "The Art of Screenshake" (reported as INDIGO 2013) adds
  feedback step by step to a simple shooter, each step making it feel better. · E · search results (infovore.org
  "Making Game Feel". Kenney.nl "must see videos"), read 2026-11-02 · caveat: venue and date not confirmed at the
  video's own page · supports: part 4 (shake, hitstop, particles).
- ART-15 · Politics through mechanics, not lectures: Papers, Please makes border bureaucracy feel absurd and inhuman
  through repetitive paperwork; Pope said the rigid structure of an oppressive bureaucracy suits how he designs
  mechanics. Beholder (a landlord spying on tenants) and Orwell (a surveillance official) take surveillance. ·
  E · https://reason.com/2013/09/26/papers-please-politics-in-games-and-the/ (Pope quote, snippet);
  rawg.io Papers, Please reviews. nodal.gg Beholder listing, read 2026-11-02 · caveat: secondary summaries ·
  supports: the per-game takes. Also what NOT to copy (a desk inspection game, a landlord-spy game).
- ART-16 · Pixel run cycles are built from key poses (contact, down, passing, up); Pedro Medeiros (saint11) has short
  tutorials for a simple run and for animation easing. · E · search results (ui.lemm.ee list of saint11
  tutorials. Superposition-art walk-cycle guide), read 2026-11-02 · caveat: no frame counts or sprite sizes found
  for Celeste · supports: part 4 (runner's existing 6-frame cycle already follows this).

### My readings (H)

- ART-17 · In a one-button reflex game, anticipation must never delay the player's response: the tap frame shows
  the action at once (a stretch frame), and the anticipation goes into the THREATS (an obstacle that winds up,
  flashes or creaks before it strikes). Follow-through and squash go after the action. · H · animation practice
  (the 12 principles, applied to response time); ART-14 · supports: part 4.
- ART-18 · Seven of ten games are flat fills and 1-px lines today (council/user.md USER-2), and three of them
  (tunnel, starfire, cube) are wireframe 3D whose look comes from code, not pictures. A direction that only paints
  sprites leaves those three behind. A direction built from flat colour and lines (B or C) carries them for free. ·
  E · council/user.md USER-2, USER-12 table. games/space3d.py, world3d.py · H (the reading) · supports: direction
  choice.
- ART-19 · A shocking take reads best when the player is the victim of a system or its small, tired operator, never
  its target audience's enemy. The joke is on the machine. That is the line between "shocking" and "cruel". · H ·
  the PO's request plus the brief's rule (systems, never people, parties or groups) · supports: the takes table.
- ART-20 · The current painter already makes everything direction A needs, and most of C (flat layers, keyed
  sprites, strips); B needs a new small palette mode in paint.py (posterise to 2 to 4 colours, no grain). · E ·
  art/paint.py:74 (Strip), :416 (Sprite), :1252 (frame) · H (cost guess) · supports: the cost column.

### The art directions

Each direction is one look for all ten games. Costs are rough, for one person with Claude writing paint.py code.

**A. Watercolour noir (keep the painter, turn the mood).** The pencil and watercolour the PO loved, but at dusk and
night: desaturated washes (slate, ash, rust, bruise violet), heavy graphite hatching in shadows, and ONE saturated
accent per game for what matters (the threat, the goal). Light comes from inside the scene: windows, lamps, fire.

- Why it reads: the hard-masked, outlined sprites already read at 16x24 (ART-10). A muted ground plus one accent
  gives the eye one place to go. Grain hides RGB565 banding (ART-6).
- Cost: lowest per game. Reuse Sprite, Strip and the layer system. New palettes and new subjects. About one
  paint.py session per game for layers and sprites. The three wireframe games need painted backdrops behind their
  lines (ART-18).
- Proof: the PO's own verdict on runner, stack, flappy (ART-10, D). Watercolour indie games (Gris, Old Man's
  Journey) are H, not searched.
- Risk: the set looks "pretty" more than "shocking". The edge must come from subject and death moments.

**B. Night ink, one wound (1-bit plus one accent).** Black ground, bone-white ink line art, and one blood-red or
signal-orange accent for danger and score. Optional one extra cold colour per game (Downwell's blue, ART-11). No
gradients, almost no dither (ART-12).

- Why it reads: maximum contrast on a small TFT. Silhouettes and outlines read at 12 to 16 px. No banding. The
  wireframe games already look like this (ART-18). Still black backgrounds keep partial sends small (ART-5).
- Cost: low for the art (a posterise mode in paint.py. Most shapes can stay procedural), medium for the
  animation, because flat art lives on motion: more frames, more particles, more shake. Loses the watercolour the
  PO loved.
- Proof: Downwell (ART-11), Return of the Obra Dinn (ART-12).
- Risk: it can look austere or "retro tech demo". The accent rule must be strict to stay a style.

**C. Silhouette poster (two-ink print).** Each game is a two- or three-ink print: a strong flat sky of one hue
(fluorescent pink, acid yellow, deep teal), black silhouettes for the world and the player, and print texture
(halftone dots, a 1 px misregistration of the second ink) baked into the still layers. Big shapes, big type on the
title cards.

- Why it reads: silhouettes are the strongest shape cue at small size (ART-13). Flat skies band less than soft
  ones. The colour of each game's sky becomes its identity in the D14 cycle.
- Cost: medium. Layers are simple to paint procedurally. The player silhouette must carry all the acting by
  pose alone, so pose design takes care (no face to show feeling). Halftone texture on moving layers needs testing
  for shimmer at 25 fps.
- Proof: Limbo, Badland (ART-13). A risograph game by name: — (not searched).
- Risk: a silhouette player is hard to see against a silhouette obstacle. An accent rim (1 px light outline on the
  player) is needed.

A mix the PO may like: A for the side-on games (flappy, runner, stack, cave, snake, gravpong), with B's "one
accent" rule, and B's ink on black for the three space games (starfire, tunnel, cube), tied by one shared accent
colour. (H.)

### Per game: an original theme each

Notes: "take" is the social or political edge, marked mild, sharp or shocking (ART-19). Rules stay as they are. The
theme reskins them. Each title and game-over is a painted card (ART-7) with an animation inside the 1.5 s title and
the 900 ms over window (ART-8). Sizes are game px. None of these copies a known game's premise as far as I know (H;
not searched per theme).

| game | title · one-line premise | what the player is | what moves and how it should feel | key animations (frames) | title and game-over moments | take (level) |
| --- | --- | --- | --- | --- | --- | --- |
| flappy | **HIGH WATER** · a city pigeon threads between the tower blocks of a drowning city | a soot-grey pigeon, one bent foot, 20x16 | heavy body, light wings: the tap is an instant upward stretch, then a long squash glide. Tilt follows speed (exists). Water below bobs on a slow sine. Spray when near the surface. Feathers on each flap (particles) | flap 4 (stretch up, mid, down squash, glide), tilt 3 (exists), death 5 (hit flat, spin, fall, splash, one bubble) | title: rain streaks, the pigeon lands on a TV aerial, shakes water off (3 frames). Over: it hits a tower, flat squash, falls, splash rings, one feather floats. Card "THE WATER KEPT RISING" | the lower "pipes" are flooded blocks of flats with windows going dark as the water rises with the score. The upper ones are dry penthouse towers on stilts with "FLOOD-SAFE LIVING" banners · **sharp** (rising seas fall on the poor first) |
| runner | **ETA** · a courier on foot races the delivery timer across a city that never stops ordering | a courier with a huge cube backpack, 16x24 (the current rig, re-dressed) | the backpack lags and bounces on a spring after each landing (2 to 3 frames of follow-through). Landing squash (exists). Dust puffs. At high speed the background smears and speed lines thicken (exists) | run 6 (exists, re-dressed), jump 5 (exists), plus backpack bounce baked into land 2, stumble 3, collapse 4 | title: a phone buzz shakes the screen (3 frames), "NEW ORDER" card. Over: the courier collapses, the bag spills. A phone in the corner: "Rating 4.6. Account paused." Then the same doorway lets out an identical courier | the coins are star ratings, the clock is "+5 min", the speed curve is the quota rising. The replacement courier at game over is the point · **sharp**. The replacement shown as a queue of identical couriers at the door: **shocking** (not cruel: the courier is the hero. The target is the app's logic, no company named) |
| snake | **FEED** · an endless feed that grows by eating red notification dots | a chain of phone-screen tiles with a glowing head, 12 px cells | smooth: the head slides between cells (tween within the step period) and the body follows with a slight lag wave. A gulp bulge travels down the body after each dot (1 cell per step). Dots pulse | head 4 (open, gulp, chew, glow), dot pulse 3, bulge 2, death: tiles flip to grey one by one from head to tail | title: a thumb flicks, the feed scrolls in. Over: every tile turns grey "SEEN", one by one. Card "YOU SAW 41. YOU REMEMBER 0." (41 = the score) | the attention economy. The self-collision is the joke: you were eaten by your own feed · **sharp** |
| stack | **RENT** · stack flats into a tower that nobody can afford to live in | the crane's swinging floor of flats, 14 px tall blocks | the moving floor hangs from a crane cable and swings with a damped pendulum (cosmetic, the hit test stays on x). The tower sways with a spring and settles after each drop. The cut-off part falls and tumbles with gravity (exists) and breaks into furniture particles at the bottom. Perfect drop: a short hitstop and a gold flash | floor block with lit windows 2 (lit, dark), cut piece tumble 4, crane hook 2, tower collapse 6 on game over | title: the crane lowers the first floor, a "SOLD" sign flips. Over: the top floor misses, the tower leans and falls in 6 frames, dust. Card "SOLD OUT · 0 RESIDENTS" | as the tower grows, the lower floors' windows go dark (empty flats bought as investments). The falling cut-offs carry a sofa, a cot, a lamp · **sharp**. The cot: **shocking** (not cruel: no person is shown, the target is speculative housing as a system) |
| cave | **CANARY** · a canary in a cage on a cable flies the old mine where the air is going bad | a yellow canary in a swinging cage, 18x20 | the cage swings like a pendulum behind the canary's thrust (inertia). Coal dust drifts and gets thicker with the score. Lamp light sways with the cage. Rock walls drip | flutter 3 (holding), glide 2, cage swing baked 3 tilts, cough 2, death 4 | title: a lamp clicks on, the canary blinks. Over: the canary stops, the cage swings once more, empty. The mine's sign behind still reads "AIR QUALITY: OK" | the warning nobody listens to (climate and air quality). The green "OK" sign over the dead bird · **shocking** (not cruel: a cartoon bird, no gore, it is the old metaphor for ignored warnings) |
| gravpong | **BUBBLE** · two tired workers hold a net and keep a swelling bubble in the air | the net, held by two small workers, 70 px wide | the bubble grows a little each bounce and wobbles (squash on contact 2 frames, stretch on rebound 2, settle). The net sags with a spring and recoils. The workers lean the way the net moves | bubble squash 3, wobble 2, net sag 3, workers lean 2 + tired 2, pop 5 (burst into paper banknotes as particles) | title: the bubble inflates from a coin. Over: the bubble hits the floor and pops. Notes rain on the workers, who are left holding the empty net. Card "IT WAS NEVER REAL" | the speculative bubble, kept up by the people who gain least from it · **sharp** |
| starfire | **NOISE** · rumours fly at a small town and you can stamp them only where the feed points your eye | a rubber stamp at the end of a crosshair you cannot steer | paper headlines flutter in, folding and unfolding as they come. A hit stamps "CHECKED" with a 2-frame hitstop and a puff of paper scraps. A miss lands on the town and a window lights red | headline flutter 4, stamp 3 (raise, slam, lift), paper burst (particles), town window flick 2 | title: a radio tower blinks, static. Over: the town is covered in paper. Card "EVERYONE HAD HEARD" | fake news and the algorithm: the auto-sweeping aim (already the rule) becomes the message, you never choose where you look · **sharp**. Alt mild theme: **DEBRIS**, dead satellites raining toward Earth (orbital junk) |
| cube | **SMILE** · a city camera turns. When its lens faces you, you must smile on time | the citizen being watched. The cube is a concrete camera block on a pole | the camera spins with a heavy servo feel: cables swing, the pole wobbles after speed-ups (cosmetic, the yaw stays exact for timing). The ring of dots becomes a ring of tiny heads that turn to the camera | lens iris 3, "smile" face 3 (neutral, forced, frozen) shown in a corner box, heads ring 2, flash green "COMPLIANT" / red "FLAGGED" | title: a lens opens, the red light comes on. Over: the camera zooms into the face, which pixelates into a grid. Card "PROFILE COMPLETE" | mass surveillance and scoring as a system. The forced smile is the horror · **shocking** (not cruel: no country, party or people are named. The player is the one wronged) |
| tunnel | **WINDOW 4** · your application, folded into a paper plane, flies through the corridor of a ministry where only one counter is open | a paper plane, 24x16 | the plane banks with a 2-frame roll when it turns (follow-through), flutters in its own draft. Each ring is a row of counters with three shutters down and one open. Shutters slam with a 1-frame anticipation | plane roll 3 per side, flutter 2, shutter slam 3, stamp "NEXT" 2. Death: the plane hits a shutter, crumples 4, a "DENIED" stamp | title: a ticket number rolls on a counter display. Over: crumple, stamp, the plane drops into a tray of others. Card "PLEASE TAKE A NUMBER" | borders and bureaucracy as an endless corridor (not a desk-inspection game: the player is the paper, not the officer, ART-15) · **sharp** |
| road | **EVAC** · drive out of a burning valley while the road fills with everyone else | a small packed car with a mattress on the roof, about 30 px at the front | the car leans into lane changes and its roof load sways (spring). Embers drift up the screen. The sky glows orange and darkens with distance. Boost shakes the camera a little. Trees at the sides are green early and black later | car lean 3 (left, centre, right), roof sway 2, ember particles, smoke layer 2, burning tree 3 | title: radio alert, the car door slams. Over: crash, the mattress flies off and lands in the road, the fire glow closes in. Card "THE ROAD WAS FULL" | climate and wildfire evacuation · **shocking** (not cruel: no victims shown. The fire is the consequence, not anyone's fault named). Alt mild: **AUTOPILOT**, the last human driver among identical robot trucks (automation of work) |

### One shared world, or a theme per game

**Option W: one city, one bad day.** Call it the city of Tide (H, name only). Each game is one citizen at one hour,
in the order of the D14 cycle: 06:00 the pigeon over the flooded harbour (flappy), 07:00 the courier (runner), 08:00
the paper plane in the ministry (tunnel), 09:00 the camera on the square (cube), noon the feed (snake), 14:00 the
crane on the rent tower (stack), 16:00 the bubble in the exchange (gravpong), 18:00 the rumours at dusk (starfire),
20:00 the evacuation (road), 23:00 the canary in the old mine (cave). Sky colour runs from dawn to night across the
cycle (a colour script), so the D14 press itself tells the day.

- For: one message from ten parts (the city fails in ten small ways), stronger than ten jokes. One skyline layer
  reused in flappy, runner, stack, road (less paint work). The showcase gets one image and one story. The title card
  can show the hour, so the generic shell (ART-8) gains a reason to stay shared.
- Against: the three space games need bending (starfire becomes the city's night sky, tunnel the ministry, cube
  the square). Every take must fit one place. One tone for all ten (no light-hearted game as relief).

**Option T: a theme per game.** Ten small indie games, each with its own palette and world (the table above).

- For: the most variety and the most freedom for "wild". Each game can pick its own direction (A, B or C). The
  alt mild themes can replace a sharp one without breaking a whole.
- Against: more art, no reuse. The set reads as a collection, not a work. Ten tones to keep in balance.

Which carries the request better (my opinion, H): W. The request asks for "shocking" and a "controversial social
topic" in one sentence. Ten unconnected takes risk ten one-liners, while one city on one day builds a shock that
grows across the set (the water in flappy at 06:00 could reach the street in road at 20:00). T carries "wild" and
"beautiful" better per game. A middle path: W's city and colour script, with each game free to use its own
direction inside it.

### What "well animated" needs at this size

| need | proposal | why (tag) |
| --- | --- | --- |
| sprite size for a character with poses | 16x24 floor (runner, approved); 12 to 14 px only for a creature read by silhouette and 2 to 3 frames. A face needs a head of 8 px or more | ART-10 (E). Smaller is H |
| run cycle | 6 frames at 12 to 16 fps (exists: 14); 8 only if the sprite grows to 24x32 | ART-10, ART-16 (E) |
| flap or swim | 3 to 4 frames, the downstroke on the tap frame, the glide held | ART-17 (H) |
| jump | 5 poses (exists): takeoff 1 frame (~70 ms), rise, apex, fall, land squash ~120 ms | games/arcade.py Runner.pose (E) |
| squash and stretch | baked frames only, 2 per event: stretch on the action, squash on the contact, 1 to 3 frames each | ART-2 (E) |
| anticipation | on threats only (a 1 to 2 frame wind-up, 40 to 80 ms). Never before the player's own action | ART-17 (H) |
| follow-through | secondary parts on a damped spring (backpack, cage, net, roof load, cable): computed in Python, drawn from 3 baked tilts | ART-2 (E), the spring is H |
| impact | hitstop 2 to 3 frames (80 to 120 ms) on a score or a death, a white 1-frame flash on the hit sprite (baked) | ART-14 (E), numbers H |
| screen shake | 3 to 5 frames, 2 to 4 px, on death and big hits only. Free in runner and flappy, +15 to 25 ms per frame elsewhere | ART-5 (E + H) |
| particles | the 40-particle pool: feathers, dust, sparks, paper. Anything shaped is a sprite | ART-9 (E) |
| death | 4 to 6 frames inside the 900 ms over window, then a still card | ART-8 (E) |
| title | 3 to 6 frames of one action, inside 1.5 s, on a painted card with baked lettering | ART-7, ART-8 (E) |
| fast motion | at 520 px/s a sprite moves 21 px per frame: use speed lines or a 1-frame smear pose above about 300 px/s | games/arcade.py (base_speed, speed lines) (E), smear is H |

## What I could not check

- How any art looks on the real panel: I saw only art/preview.png at 2x and 4x on a Mac. Colour, contrast and
  gamma on the TFT are —.
- Whether halftone or misregistration (direction C) shimmers when it scrolls at 20 to 25 fps: —, needs a board test.
- The fps cost of a shake, of hitstop, or of more sprites per frame: not measured; ART-4 and ART-5 are readings of
  bench numbers.
- Pool load time at boot with 2 to 3 MB of art: —.
- Whether each theme is truly original: I checked only the known political games in ART-15, not each premise.
- Primary sources for Downwell (an interview with the developer), Nijman's talk page, and any risograph-style indie
  game: not found within six searches.
- How the PO reacts to a sharp or shocking take in practice, and whether the showcase repo (job applications)
  changes how sharp it may be: D only he can give.

## Questions for the decider

- Q-A · One city on one day (W), ten separate games (T), or W with free directions per game? · decides: the whole
  art plan and how much art is shared.
- Q-B · Which look: A watercolour noir, B night ink with one accent, C silhouette poster, or A for the side-on games
  and B for the three space games? · decides: paint.py work and which games change the most.
- Q-C · How sharp may it be in a repo that goes with job applications: mild, sharp, or shocking where it fits? ·
  decides: which theme in each row (main or the mild alt).
- Q-D · Runner and flappy: keep the approved kid and bird and only change the world, or re-dress them (the
  courier, the pigeon)? · decides: whether the art he already loves is reused or repainted.
- Q-E · May the themes change small rules where the take needs it (for example the cave's air getting worse with
  score, or the water rising in flappy), or is it look only? · decides: the scope line "no new game rules".
- Q-F · Which game first, as the test of the direction? (Runner or flappy cost least, stack shows the most physics,
  cube or road is the sharpest take.) · decides: the first slice and the riskiest test.

## Searches

| query, verbatim | the decision it served | used |
| --- | --- | --- |
| Downwell three colour palette art style Ojiro Fumoto interview | direction B: does a tiny palette carry a whole game | used (ART-11, then the Wikipedia page read) |
| Vlambeer "art of screenshake" Jan Willem Nijman talk | part 4: feedback and shake as game feel | used (ART-14) |
| Return of the Obra Dinn 1-bit dithering Lucas Pope devlog readability | direction B: legibility and dither on a low resolution | used (ART-12, then the PlayStation Blog page read) |
| Pedro Medeiros saint11 pixel art tutorial run cycle frames squash stretch Celeste Madeline sprite size | part 4: frame counts and sprite size | used, weak (ART-16. No sizes found) |
| indie game silhouette art style Limbo Badland readability small screen | direction C: silhouettes at small size | used, weak (ART-13. Nothing on small screens) |
| Papers Please Orwell Beholder political indie games surveillance borders bureaucracy design | the takes: how political games work, and what not to copy | used (ART-15) |
