# User lens report: P539 graphics library (2026-11-02)

Lens: the user's journey. Primary persona: the PO (n = 1). Secondary personas: H only. Read and changed nothing but this file. Paths: bench.md = firebeetle-games/bench.md; finding = firebeetle-games/p537-finding.md; the 5 issues are xmejkal/spark #743, #741, #740, #742, #737 (read 2026-11-02 via gh).

## Findings

Tags: E pointer, H source, D who when. Every time in a log is a CET clock time of 2026-11-02 as the log wrote it; the logs do not name the zone (—).

### The PO, scenario (a): write or change a game and see it run smoothly

- USER-1 · The PO's own verdicts moved from "not playable" to "looks great" over one day, and the metric he quotes is feel, not fps. 08:05 "kinda smooth, not smooth enough ... not playable really"; 11:40 "I saw it, looks great"; also "pipes still half rendered" at 09:10 · E · bench.md:17-18 area (08:05 baseline), bench.md:56-58 (run 13), bench.md:117 (run 22) · supports only: an account of one person on one day, n = 1; it does not say how often he stops seeing steps.
- USER-2 · After partial show the speed limit is Python paint, not the send. Flappy 21-24 fps, runner 20-21 fps at a 40 ms pace; runner paint 34 ms a frame; worst gap 70-80 ms. Measured by firmware probes on one board, one session · E · bench.md:117 (run 22), p537-finding.md "Where it stands" · supports only: a benchmark on the PO's board; the per-phase numbers are maxima per 5 s interval, not averages (p537-finding.md, same section).
- USER-3 · The defect he names unprompted is tearing and "steps", not low fps. "pipes are still half rendered, I mean the breaking in the middle" (09:10); after native order "the whole pipe, not broken in the middle" (10:23); at 11:00 "still appear a bit stepped"; "lower the steppness?" · E+D · bench.md:76, #737 comment (PO quotes), bench.md run 17/18 lines · supports only: what he sees on a 2.0 inch-class DFR0664 in his playing hold; DFR0664 has no TE line (E in #737 comment, DFRobot schematic V0.1), so a tear line stays possible; whether he accepts it at 7-11 ms windows is — .
- USER-4 · He cannot supply the threshold at which steps vanish. The finding's step probe (16x16 block at 100/200/300 px/s, paces 16-50 ms, blind) is unrun; the PO has not answered "px per frame I accept" · E · p537-finding.md Question 1 and slice 0; jobs-and-journeys.md J1 says "smooth, not stucky" with no number · supports only: the number is — .
- USER-5 · A change to a game's look in Python is easy; a C change is not. To change the C driver he rebuilds MicroPython: `./build.sh s3lcd` against ESP-IDF v5.5.2 (checkout 647 MB; ~/.espressif 7.6 GB) then flashes at 0x10000. Build time and flash time per iteration are — . · E · firebeetle-games/build.sh:1-17; bench.md:8-9 (install cost); bench.md "slice 3" flash line (`esptool ... write_flash 0x10000`) · supports only: the setup of one Mac. The build-time number is not logged anywhere I read.
- USER-6 · Flashing needs hands. `machine.bootloader()` did not reach download mode on v1.22.2 or on v1.29 (board stays 303a:4001); BOOT held plus RST worked at once. Later a no-button path is logged: `mpremote bootloader`, wait for the port, `esptool --before no_reset --after watchdog_reset` — it worked at slice 3 (the log's own words: "The RTS reset left the chip in download mode (USB 0x1001)") but 08:13 said buttons are needed for both builds. The two entries disagree; which one holds on a fresh board is — · E · bench.md:22, 27 against the slice 3 "Flash with no button" line · supports only: two dated logs that conflict.
- USER-7 · USB drops at driver start. "Every other run" lost USB (slices 0-2); after `mpremote cp` the first run lost USB each try; the slice 3 cause given is an unclaimed SPI bus after a soft reset (`deinit()` finalizer). It is a reading, "likely cause", not proven. Whether it is gone: runs 15-22 report none, no statement that it was checked · E · bench.md:54, 64, 76, slice 3 notes · supports only: a likely cause for one board; recurrence rate after the fix is — .
- USER-8 · Board power-off harm. A long hold of D14 powers the board off through the AXP313A PWRON diode (V1.1 and earlier). Run 11: display dark and USB gone while he held jump. And at 12:31 the board was dark again after a power-off, no device on USB, replug did not help, no power LED on the schematic; recovery was a 1-2 s D14 hold. The game button was moved to BOOT, D14 to a short "next game" press · E · bench.md:56 (run 11), bench.md:149 (12:31) · supports only: one board. A library cannot cause or cure this; a user of another board has no warning (H).
- USER-9 · Stale pixels: only a look can find them, and the PO is the only detector. Slice 5 passed on "no stale pixels reported" after a 2-minute look through title, play, game over and three switches; no automatic check exists. A game switch sends two whole frames (review note) · E · bench.md:117, review section · supports only: a human check, n = 1; "no report" is not a measurement of none.
- USER-10 · He gets wrong colours without an error. Colours are pre-swapped at gfx.c565; a probe that used the library's own GREEN showed purple. 80 MHz SPI gave a dark screen with the game "running" in the log. A MicroPython syntax limit passed `py_compile` and failed on the board. These are cases where the board gives no message and he guessed from the picture · E · bench.md:88 (colours), bench.md:38 (80 MHz), bench.md:43 (py_compile) · supports only: three incidents on one day.
- USER-11 · Silent-slow harm. Runner slowed from 14 fps to 2 fps over about a minute through a cache keyed by `id(rows)` (heap 137 to 582 KB). Found only by adding a heap line to the log. A user without the log would see "it gets laggy" · E · bench.md run 16 line · supports only: one cause in one cache; the class "slow with play time" has no automatic test.
- USER-12 · Settings he can use without a rebuild: `tft.config(...)` all-or-none, readable back, typed errors naming the key (timeout, framebuffer, partial, tile, windows, swap, defaults). He asked for exactly this ("config reachable from python") · E+D · bench.md slice 4 table; #737 comment (PO) · supports only: that the config API exists and was requested; no log says he used it to compare on and off himself.
- USER-13 · What the PO can supply: his eyes on a verdict (smooth, steps, tear, stale, colour), his hold (rotation), bench time with the board, a yes on cost. What he cannot supply: a number for steps, a second panel or board to test on (only the FireBeetle 2 ESP32-S3 and DFR0664 appear anywhere), and any panel with a TE line. Repo evidence for a second board or panel: — · E (absence) · grep of bench.md, research.md, games/ shows only DFR0664/GDI pins (games/gdi.py:1-19) plus `st7789.py` fallback · supports only: absence in what I read.
- USER-14 · Workflow facts that shape what the library must keep: a Mac stand-in loop runs the games without hardware (lcd.py header says `import s3lcd` is inside `open_tft()` for the Mac), and a Python fallback `st7789` driver is used when the image has no s3lcd · E · games/lcd.py:1-12, games/app.py:36-38 · supports only: that a no-C path exists today; its speed relative to the C path: bench.md says 1-13 fps for pure MicroPython (research.md "Alternatives").

#### Journey table (a): write or change a game and see it run smoothly on the board

| step | what they do | evidence | friction or harm | today | open question |
| --- | --- | --- | --- | --- | --- |
| 1 | Edits a game's paint in Python on the Mac | E games/lcd.py:1-12 (Mac stand-ins) | Syntax limits of MicroPython pass `py_compile` and fail on the board (bench.md:43); needs `mpy-cross` | works | Does the Mac loop also catch a draw that is wrong in panel coordinates (orientation map)? — |
| 2 | Copies files to the board (`mpremote cp`) | E bench.md:54 | First run after the copy lost USB each try on one day | partly | Is that gone after the finalizer fix? — |
| 3 | Starts `import app; app.run()` or resets; sees picture | E bench.md:41-42, 149 | Board may be dark after a power-off with no LED, recovered by a 1-2 s D14 hold; a long D14 hold during play powers it off | partly | How often did he lose the board in a week? — account |
| 4 | Plays, judges smooth or steps with eyes | E bench.md:117 (run 22) | No threshold number; steps from 3-25 px/frame and uneven 40-80 ms frames; vertical tear stays (no TE) | partly | At which px per frame does he stop seeing steps? — account |
| 5 | Reads the serial log to see why it is slow | E bench.md runs 5, 8 | Counting costs time itself (114 ms/frame when counting allocations); phases are maxima; heap leak found only after adding a heap line | partly | Which numbers did he read, and which did he ignore? — account |
| 6 | Wants a faster draw (score text, sprites) | E finding "ranked options" | A C change means rebuilding MicroPython (647 MB IDF) and flashing; no-button flash and download mode conflict in the log | not yet | How long did one rebuild and flash take him? — account |
| 7 | Checks stale pixels, colours, orientation by eye | E bench.md:88, 117 | Wrong colours and stale pixels give no error | partly | Which of the last 5 wrong pictures did he find by eye, which by log? — account |
| 8 | Tunes with `tft.config()` and compares on/off | E bench.md slice 4 | He asked for it; no log shows him doing the comparison | partly | Did he change a setting himself, and which? — account |

### The PO, scenario (b): move a game to another board or panel

No log shows a move. The nearest cases are: the Python fallback driver (`st7789.py`), a re-orientation of the same panel, and a different SPI clock. I treat them as the evidence for what a move costs today.

- USER-15 · Moving to another panel is not logged, so everything in scenario (b) is H except the points below. The jobs file J3 says "each chip and panel gets its own driver fork (s3lcd for the S3, st7789_mpy elsewhere)" · E jobs-and-journeys.md J3 · supports only: that this is the plan's description of today; the PO's account of an actual move is — .
- USER-16 · Panel geometry is baked into three places: `PANEL_W, PANEL_H = 240, 320` (lcd.py:28), the orientation formulae in `TftCanvas.fill`/`line` (lcd.py:50-70), and `WIDTH, HEIGHT = 320, 240` in `st7789.py:15` imported by `gfx.py`. A panel of other size or order means editing these and re-deriving the map by eye (the PO had to look at a corner picture to find where pixel (0,0) is: bench.md slice 0, 10:00) · E games/lcd.py:28,50-70; games/st7789.py:15; bench.md "slice 0" · supports only: that the map is hand-derived and has no table for other panels.
- USER-17 · Orientation: he said "offer all orientations and make it fast to transform"; today only 0 and 180 exist, 90/270 are refused (lcd.py ValueError) · E+D · bench.md slice 1 note; games/lcd.py:38-39 · supports only: 90/270 not built.
- USER-18 · Pins are a "walk 4 workaround": games/gdi.py reads GDI pins by hand because spark's pin map cannot pin a part to a connector; the comment says the schematic page was "read off the image, not verified" for the GDI pins · E games/gdi.py header · supports only: that moving to another board means a new hand-made pin file, and the check on those pins is partial.
- USER-19 · Board-specific harm does not travel with the code: the D14/PWRON power-off exists only on FireBeetle 2 V1.1 and earlier (board record `hardware_revisions`, cited in bench.md:56) and the BOOT/D14 game-button choice follows from it. A second board has its own — · E bench.md:56 · supports only: that it is one board's fact; others are — .
- USER-20 · SPI clock limit is panel-specific: 80 MHz gives a dark screen, 60 MHz (real 40 MHz) works; the datasheet limit quoted in app.py is 16 ns write cycle (62.5 MHz) · E games/app.py:28-31; bench.md:38 · supports only: the DFR0664 panel. TE is absent here and "slice 6 TE sync only on another display" (#737 comment), so a panel with TE is untested.
- USER-21 · Firmware port: a new chip means a new MicroPython build with the C module, a different ESP-IDF pairing (research.md: MicroPython v1.29.0 with IDF v5.5.2 matched pair), and the S3-only memory trick (188,416-byte internal DMA block; one frame 153,600 bytes) may not fit another chip; another panel size needs a new fit calculation · E bench.md slice 0 (10:00 area), research.md §1 · supports only: S3 N16R8 memory. A smaller chip fit is — .

#### Journey table (b): move a game to another board or panel

| step | what they do | evidence | friction or harm | today | open question |
| --- | --- | --- | --- | --- | --- |
| 1 | Picks the other board or panel | H no log | He owns which others? — | — | Which board or panel would he move to first? — account |
| 2 | Finds the pins | E games/gdi.py header | Hand-read from a schematic image, "not verified" | partly | Did he ever re-wire a game to different pins? — account |
| 3 | Gets a firmware with the C driver | E build.sh; bench.md:8-9 | Needs ESP-IDF match for the chip; 647 MB; no prebuilt image yet (#742) | not yet | Would he build, or want a downloaded image? — |
| 4 | Sets geometry and orientation | E games/lcd.py:28, 38-39 | Constants in three files; the map found by a corner picture and by asking him which corner; only 0 and 180 | partly | Which orientations did he need on a real move? — account |
| 5 | Sets SPI clock and colours | E games/app.py:28-32; bench.md:38, 88 | Dark screen at too high a clock; wrong colours without an error; byte order pre-swapped in game colours | partly | How many tries did the clock and the colours take? — account |
| 6 | Plays; judges tear | E #737 comment (TE absent) | TE only exists on some panels and is not tested | not yet | Does the other panel have a TE pin? — |
| 7 | Falls back if the image has no s3lcd | E games/app.py:36-38 | Fallback is the old driver and slow (research.md: 1-13 fps pure MicroPython) | works | Is a slower but working fallback acceptable to him, or must a move not lose speed? — |
| 8 | Checks that nothing harmed the board | E bench.md:56, 149 | Power-off behaviour and USB are board facts that the code cannot carry | — | What warnings would he want printed at first run? — |

### Secondary persona 1: an Arduino maker who wants the library from C++ (H only)

- USER-22 · Install: the likely path is the Arduino Library Manager or PlatformIO. Arduino's library spec needs `library.properties` in the repo root, a unique version per release, name not starting with "Arduino", `architectures` default `*`, and `arduino-lint` for checks · E for the spec, URL https://docs.arduino.cc/arduino-cli/library-specification and https://www.github.com/arduino/library-registry/blob/main/FAQ.md, read 2026-11-02 via search summaries (not full pages) · supports only: the registry's rules; that a maker uses it is H (the PO's "usable from c, so in arduino", #743).
- USER-23 · First sprite: the Arduino maker has no MicroPython bindings and wants a bus layer for his own panel (TFT_eSPI, LovyanGFX, Adafruit GFX are what the jobs file says he picks today: jobs-and-journeys.md J5, H the lead's model knowledge). He needs: a one-line panel setup (pins, size, driver chip), one sprite format (the finding's API sketch has `tft.sprite(BIRD, BIRD_COLOURS)` for Python only; the C++ form is — ), and a picture on the first upload · H, no interview.
- USER-24 · First game: needs a frame loop with a pace, buttons, and a way to see why it is slow. The Arduino side has no equivalent of the serial phase log the PO used. The finding says "what stays in Python: the games, their speeds, their rules" — an Arduino game has no Python to hold them, so game helpers are a gap or not in scope · H; E p537-finding.md "What the layer holds".
- USER-25 · Porting: Arduino users on a Pico or an ESP32 board need that panel's bus layer. The library's J3 says "swap one port layer"; no port layer exists yet, and S3 GDMA/PIE code would be inactive on the Pico · H; E jobs-and-journeys.md J3, J4.
- USER-26 · Harm to expect: wrong colour order, wrong rotation and a dark screen at a high SPI clock are the same silent faults the PO met (USER-10); an Arduino maker with no log will lose time unless the library names them · H from USER-10.

#### Journey table: Arduino maker (H only)

| step | what they do | evidence | friction or harm | today | open question |
| --- | --- | --- | --- | --- | --- |
| install | Adds the library via Library Manager or PlatformIO | H spec URL above | Needs library.properties, a version per release, ESP32 architecture naming (not checked) | — | Which of Library Manager and PlatformIO first? — |
| first sprite | Sets a panel and draws one sprite | H | No C++ API exists yet; no panel presets | — | What panel config would he write, and in what? — |
| first game | Writes a loop with pace and buttons | H | No timing/pace helper and no phase log in C++ | — | Does he expect game helpers? — |
| porting | Moves to another chip or panel | H | No port layer yet; chip-specific code inactive off S3 | — | Which chips matter first? — |

### Secondary persona 2: a MicroPython user on a different board (H only)

- USER-27 · Install: a C module in MicroPython means a custom firmware build. Prebuilt images are the route #742 plans ("one released image for the FireBeetle 2 ESP32-S3 with the GDI display") — for one board only, so a user on another board cannot install without building · E #742 "Done when" · supports only: the stated plan; other boards — .
- USER-28 · A dynamic native `.mpy` module avoids a rebuild for pure C code, targeted at `xtensawin` for ESP32/S3, but it can only call functions the firmware already exports through `mp_fun_table`/`mp_port_fun_table`; new IDF functions (esp_lcd, DMA, semaphores as frame.c uses them) need a firmware rebuild · E https://docs.micropython.org/en/latest/develop/natmod.html (read 2026-11-02 via search summary) · supports only: the doc's description. Whether frame.c can fit that is — and I did not test.
- USER-29 · First sprite: the user needs a driver for his panel. s3lcd supports ST7789 and a few; st7789_mpy is the fork for other chips (finding table; J3). The 8x8 font of `framebuf` is the only text without a font module (lcd.py header) · E games/lcd.py:12-14 · supports only: this image; other panels — .
- USER-30 · First game: the games use a recorded-canvas class and a "Game base class" in the repo (gfx.py); a new user has none unless these ship with the library; today `gfx.py` imports `st7789.WIDTH/HEIGHT` (games/gfx.py:21), tying the games to a 320x240 landscape · E games/gfx.py:21; games/st7789.py:15 · supports only: current code.
- USER-31 · Porting: the user's chip may lack internal DMA RAM of 188,416 bytes or PSRAM; the "dma" framebuffer path needs 153,600 bytes for a 320x240 panel and a fallback "strips" mode runs at 71.9 ms (with the idle_mode bug, so that number is void, see bench.md:100) · E bench.md slice 0, slice 3, line 100 · supports only: the S3 N16R8 board; others —.
- USER-32 · Harm: a firmware flash is a destructive step. The PO made a full 16 MB backup (59.7 s) before his first flash and wrote the restore command; another user is not told to · E bench.md:23-24 · supports only: that the PO did it; no guidance for a public user exists.

#### Journey table: MicroPython user on a different board (H only)

| step | what they do | evidence | friction or harm | today | open question |
| --- | --- | --- | --- | --- | --- |
| install | Downloads an image or builds MicroPython with the module | E #742; build.sh | One image for one board; building needs IDF 647 MB | not yet | Prebuilt for which boards? — |
| first sprite | Imports the module, inits a panel, draws | E games/lcd.py | Panel presets and fonts: only ST7789 on one board proven | — | Which panels at first? — |
| first game | Copies a game from the repo | E games/gfx.py:21 | Games tied to 320x240 and the fallback driver | partly | Do games ship in the library repo? — |
| porting | Changes pins, size, orientation, SPI clock | E games/gdi.py; app.py:28-32 | Hand-edited constants; silent faults | — | A config file or a call? — |

## What you could not check, and why

- Whether the PO ever moved a game to another board or panel: no log, issue or file I read shows one. The (b) walk is built from the nearest cases and marked.
- How long a rebuild plus flash cycle takes him: build time and flash time per iteration are not logged in what I read (build-s3lcd.log and build-stock.log exist, not opened; the timestamps there may answer).
- How often the board lost USB or power since the finalizer fix: runs 15-22 do not say; I did not read all run*.log files (read only bench.md's summary of them).
- The step threshold in px per frame: unmeasured (slice 0 is not run).
- Blur Busters and Emby sources cited in the finding: not opened by me; relied on the finding's own note that the Blur Busters fetch failed.
- Whether the s3lcd fork or frame.c compile as an Arduino C++ library: the fork's source was not read (cwd is spark; s3lcd/ folder not opened).
- Arduino ESP32-specific library rules and naming (`architectures=esp32`): the search did not answer it.
- The council folder is empty besides this file; I did not read other lenses.
- Issue #743 has no comments (gh shows 0), so its D rows come from the body only.
- Timezone of the clock times in bench.md: the logs name none; #741's comments use CET.

## Questions for the decider

1. Account: at which speed of a moving block (px per frame, at what fps) did you last say "smooth" and "steps" on the DFR0664? · decides the target of J1 and the pass line of slice 0 (account, n = 1).
2. Account: in the last two weeks, how many times did you lose the board (dark, no USB, needing D14 or BOOT+RST), and what were you doing? · decides whether safety guards (a first-run warning, a safe-start call) are in the MVP (account).
3. Account: how long did your last C change take from edit to seeing it run (build, flash, copy, start), and which step did you dislike most? · decides whether a no-rebuild path (native module, prebuilt image, hot config) is MVP or later (account).
4. Account: when did you last judge a picture wrong (colour, orientation, stale pixel, dark), and how did you find the cause? · decides whether the library ships self-tests or probes as a first feature (account).
5. Account: have you tried a game on another board or panel, or do you own one? Which? · decides whether scenario (b) has any E and what the second port target is (account).
6. Account: when you compared a setting on/off, did you use `tft.config()` yourself? · decides if config is exposed as a call, a file or both (account).
7. Is a tear line that stays (no TE on DFR0664) acceptable for the MVP, or must a panel with TE be bought? · decides TE slice order and whether to buy a panel (needs a cost line, ask first).
8. Which orientations are required for the MVP (0, 90, 180, 270)? · decides the port-layer interface and the map in C.
9. Must the first public release run on boards other than the FireBeetle 2 ESP32-S3, and must the C++ side (Arduino) be in the MVP or after it? · decides what the first image, the first binding and the first docs are.
10. Does the MVP include a no-C fallback (pure MicroPython path) for users who cannot flash firmware? · decides whether `st7789.py`-style fallback stays a supported layer.

## Searches

| query, verbatim | decision it served | used or not |
| --- | --- | --- |
| MicroPython native modules .mpy dynamic native module esp32 xtensawin install without rebuilding firmware | whether a MicroPython user can install the C layer without a firmware rebuild | used (USER-28) |
| Arduino library specification library.properties architectures ESP32 Library Manager requirements | what an Arduino maker needs at install | used (USER-22) |
