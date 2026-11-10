# P750 round 2: why the fire does not sound like fire, and what to try

I did not hear any sound. I have no way to listen. All claims about how a demo sounds are expected, not heard. The PO decides by ear.

> 1. Round 1 sounded like clicks and noise because every crackle was one short noise burst with one shape, and the bed was filtered noise.
> 2. Real crackle is a resonant, woody ring with many sizes, in clusters, at a changing rate. Real fire texture is a recording.
> 3. Best route to try: grains cut from a CC0 recording for the bed and the crackles (demo f), with Farnell-style woody snaps on top (demo g).

## Why round 1 failed
- Round 1's pop was low-passed white noise with an exponential tail. It has no pitch. The ear hears a click.
- A wood crack rings. The wood splits and the piece resonates for 5 to 30 ms at some pitch. Fracture-sound work models this as a rigid body hit at one point, so the sound is a short sum of decaying modes (Zheng and James, https://www.cs.cornell.edu/projects/FractureSound/). My reading, not measured: several inharmonic modes with random pitch per event make "wood". One mode with high Q makes "electric ping".
- Farnell's crackle (round 1 read https://aspress.co.uk/ds/pdf/ds_sample_02.pdf): random impulses from a slow random signal, each excites a band-pass with a random centre, with a square-law decay. I did not re-read the full chapter. The sample PDF shows only part. Demo e follows my reading of it, so it can differ from his patch.
- All round 1 pops were alike in rate and shape. Real crackle has a power-law mix: many tiny, few large, and clusters.
- The bed was 3-pole low-passed noise times a flutter. A smooth low-passed noise is exactly "wind or river". Real fire hiss is itself made of thousands of tiny crackles, not Gaussian noise.
- It was "too even, too thin": no density changes, no low body from the larger snaps, level held near flat (heat moves only 8 to 11 %).

## What I found on fire statistics
- No source gave a crackle rate or a spectrum of real fire. I searched once for each. The only measurements found are lab studies that tell burning materials apart by spectrum (Mikedi et al. 2013, https://gnosis.library.ucy.ac.cy/handle/7/55853). They give no numbers I can use.
- Mechanism claims (steam and gas in the cells burst the fibres) come from low-quality web pages. I treat them as unverified.
- Chadwick and James 2011 (https://www.cs.cornell.edu/projects/Sound/fire/FireSound2011.pdf): low band from the simulation, high band by texture synthesis from recordings. So the published answer for "full" is data-driven. Not real time on their side, but grain playback is cheap.
- Open implementations model crackle as random impulses at an events-per-second rate through a high-pass (garjan, https://docs.rs/crate/garjan/1.0.0/source/src/fire.rs). That is Round 1 again.
- The rates in my demos (25 to 250 small crackles a second, clusters of 1 to 4) are my guesses. They are not measured.

## Approaches
| Approach | Realism expected | Cost on S3 in C (estimate, not measured) | Memory | License |
|---|---|---|---|---|
| Round 1 noise pops + filtered bed | low (heard: clicks, wind) | 0.6 to 0.7 ms a block | none | own |
| Farnell-style resonant snaps, dense stream, clusters (demo e) | medium. woody if modes and sizes vary | about 2 biquad per live event, 20 to 40 events live: 1 to 2 ms a block | none | own |
| Grains from a recording: bed + crackle grains (demo f) | high for texture. limited by source length and repeats | a few ms at most: copy, window, add. no filters | 2.9 s at 16 kHz int16 is 92 KB. a 20 s bank is 640 KB (needs PSRAM or flash) | CC0 for the file I used |
| Hybrid: grain bed + Farnell snaps sized by ember speed (demo g) | highest expected. snaps follow the heat field, bed has real texture | about 2 to 4 ms a block | 100 to 300 KB | CC0 + own code |
| Offline-made sample bank, board plays grains (as f/g) | depends on the bank | same as f | same as f | see below |

## Recommended route
1. Keep the naive path (plain MicroPython) as the fallback behind one interface, as the PO's rule says.
2. Try g first, then f and e by ear. If the PO hears f or g as fire, build a grain player in C: Hann-windowed grains from a flash bank, 50 to 300 ms, 50 % overlap, speed 0.85 to 1.15, level from heat and a slow random signal.
3. Drive loud crackle grains from ember births: pick the grain by rise speed (vy), as in f. This keeps what the PO liked in round 1 (pops sized by speed).
4. Keep synthetic woody snaps (e) only if the bank's crackles are too few or too repeating. They need no memory.
5. A longer, cleaner source is the main need. The one I found is only 2.9 s and has 12 crackles. Grains repeat audibly.

## Offline generation (not run, only named)
- Stable Audio Open 1.0 (https://huggingface.co/stabilityai/stable-audio-open-1.0): text to sound effects, up to 47 s. Sources disagree on the license: a non-commercial community license at launch, later listed as the Stability AI Community License with a revenue limit. I did not read the LICENSE file. Check it before any release.
- Pure Data or SuperCollider (both open source, GPL) can render a Farnell-style patch to a WAV once. Output of your own patch is yours. I did not check versions.
- Also: record real fire and cut it yourself. That avoids all license questions.

## Open questions for the PO
1. Is e, f or g closest to fire? Which part is wrong: crackle shape, density, or bed?
2. Is flash or PSRAM space of 100 to 600 KB for a sample bank acceptable on the S3?
3. Is a longer source worth recording (a real fire, 20 to 60 s), or do we search freesound for a CC0 one? It needs a login to download.
4. Can crackle grains be chosen by ember speed, as pops were in round 1?
5. Should heat change the bed level strongly (a clear swell) or stay gentle?

## Recording (data only, never run)
- Fire Crackling by AntumDeluge, OpenGameArt, 2013-05-10. License: CC0 (public domain). Page: https://opengameart.org/content/fire-crackling
- File: https://opengameart.org/sites/default/files/fire-1.wav (44.1 kHz mono, 2.87 s).
- Saved: /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750r2/source/fire-1.wav
- Converted with afconvert to 16 kHz mono: /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750r2/source/fire16k.wav
- My onset detector found 12 crackles in it. Wikimedia Commons gave no hit. Freesound needs a login.

## Demos (15 s, 16 kHz mono, same kernel run as round 1, seed 595)
Script: /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750r2/gen.py

| File | What | RMS | Peak |
|---|---|---|---|
| /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750r2/p750r2-e-farnell.wav | resonant snaps, random centre, dense stream, clusters, ember snaps by vy, flutter bed + sizzle | 2000 | 29479 (90 %) |
| /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750r2/p750r2-f-grains.wav | grain bed, one crackle grain per birth sized by vy | 2000 | 28046 (86 %) |
| /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750r2/p750r2-g-hybrid.wav | f's grains + e's crackles and snaps, little synthetic bed | 2000 | 29461 (90 %) |

Play with `afplay` and the full path. Peaks sit at the 90 % limit because crackle is spiky (a soft limiter clips them).
