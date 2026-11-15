# P819: what else makes the game switch smooth, and at what cost

Spike P819 ([spark #1172](https://github.com/xmejkal/spark/issues/1172)), for the epic P652. On 2026-11-15 the PO
asked for plans against the stutter when he switches games. His words are on the card.

## The short answer

The many picture files were the main cause, and P814 removed it. A switch now freezes the screen for 0.15 to 0.6 s
while the game's pack loads, and the music stays fed. Two changes in build take most of what is left. P817 puts only
the chosen games on the board. P818 loads a game only after you stop pressing. Then skipping costs nothing. After them,
the best next step is to load the pack behind a moving card, so the screen never stops. Precompiled modules make the
boot 5 s shorter for little work.

## What a switch costs now (measured on the board, 2026-11-15)

The board ran pixel-games master 6912986 with BUBBLE and FEED (MicroPython 1.29.0, FireBeetle 2 ESP32-S3). A probe
built each game twice, after `pictures.free()` and `gc.collect()`. The two tries agreed within 4 ms.

| game | setup | of it, the pack load |
| --- | --- | --- |
| runner | 609 ms | 603 ms |
| rescue | 572 ms | 567 ms |
| gravpong (BUBBLE) | 544 ms | 543 ms |
| flappy | 430 ms | 428 ms |
| stack | 415 ms | 413 ms |
| snake (FEED) | 371 ms | 369 ms |
| meteors | 275 ms | 262 ms |
| bucket | 161 ms | 158 ms |
| marshmallow | 155 ms | 147 ms |
| balls | 35 ms | 0 ms |
| cave, tunnel, road, starfire, cube | 0 to 2 ms | 0 ms |

The setup is the pack load plus at most 35 ms. The board reads a pack at about 1.2 MB/s (runner: 739,216 B in
603 ms).

The boot has a second cost. `import app` takes 9,941 ms, because app.py imports every game module at the start.

| boot import of app | time |
| --- | --- |
| from .py files (today) | 9,941 ms, twice |
| from .mpy files (mpy-cross 1.29.0) | 5,031 and 5,029 ms |

From .mpy files, the game modules take about 2.8 s of the 5 s: meteors 539 ms, arcade 512, fire 503, arcade2 255,
balls 256, rescue 223, bucket 202, space3d 126, world3d 118, marshmallow 62. The shared modules take the rest.

## The options

Each option says what it changes, what it costs and how sure the number is.

1. Only the chosen games on the board (P817, in build). The box imports and cycles only the lineup's games. It saves
   up to 2.8 s of the boot import and every load of a game you do not play. Cost: a deploy tool and a lazy import in
   app.py. A game's first switch then adds its import, 60 to 540 ms from .mpy (measured above), about twice that from
   .py (not measured per module).
2. Load after the pick settles (P818, next). A press shows the next game's name, and the game loads after a
   short pause with no press, or at once on BOOT. Skipping four games to the fifth loads one game, not five. Cost: a
   name card and a settle timer in App. The landing game still freezes the screen for its load.
3. Load behind a moving card. The loader reads a few 8 KB chunks each frame while a card with a progress bar
   animates. The screen never stops. The wait stays about as long as the load, plus the frames' own time. Cost: the
   loader becomes a step-wise loader, and App waits for it before the game starts. The frame rate during the load is
   not measured.
4. Keep the lineup's sets in memory. Read every set of the lineup once, behind the first game, with option 3's
   loader. After that, a switch costs about 0 ms. With BUBBLE and FEED, the eight packs are 3,955,632 B (master
   alone has six packs, 2,903,080 B). The heap had 6,500,704 B free after the import. Nobody measured whether a 4 MB
   picture pool fits beside the heap that the games need. Cost: option 3
   first, then a pool sized from the lineup and a test of the frame rate with less heap.
5. Precompiled modules (.mpy). mpy-cross turns each module into bytecode on the Mac, so the board does not compile
   it. Measured above: the boot import halves, 9.9 s to 5.0 s. Cost: the deploy compiles with the mpy-cross that
   matches the firmware (1.29.0), and two viper modules need `-march=xtensawin`. An .mpy built for another version
   does not load. Source: MicroPython's page on .mpy files,
   https://docs.micropython.org/en/v1.29.0/reference/mpyfiles.html.
6. Smaller packs. Fewer animation frames or a simple compression of the keyed sprites make the packs smaller. A
   decode costs time on each load. It pays only when the read is the bound. Nothing is measured, and the pictures
   change, so the PO's eye decides.

## The recommendation

1. Finish P817 and P818 (in build).
2. Next, one card for option 5 in the deploy tool of P817: it is small and the gain is measured.
3. Then one card for options 3 and 4 together: a step-wise loader behind a card, then, if the frame rate holds, the
   lineup's sets kept in memory.
4. Leave option 6 until a load is still too slow after option 4.

## How the numbers were taken

The probes ran through `mpremote run` from the Mac. The .mpy files went into a separate folder, `/mpytest`, first on
`sys.path`, and the folder was removed after the runs. The probe scripts are not kept in the repository.
