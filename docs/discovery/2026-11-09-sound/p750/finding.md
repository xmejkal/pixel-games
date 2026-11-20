# P750 finding: fire sound layers that follow the heat field (spike, #1032)

> Published fire sound has 3 layers: a low lapping roar, bursty hiss, and crackles. Chadwick and James drive the low band from heat release.
> Our field gives total heat, hot area, flame height and heat change for about 20k cheap adds per step. Only ember size needs a small kernel change.
> First slice: replace the steady roar with a flickering lapping bed that follows flame height, then size the pops by ember rise speed.

I could not listen. All claims about sound are from the design and the numbers, not from the ear. The PO decides by ear.

## Sources (one or two reads each)
- Farnell, Designing Sound, ch. "Fire" (sample PDF, read in full for the three layers): https://aspress.co.uk/ds/pdf/ds_sample_02.pdf
- Chadwick and James, Animating Fire with Sound, SIGGRAPH 2011: project page https://www.cs.cornell.edu/projects/Sound/fire/ and paper https://www.cs.cornell.edu/projects/Sound/fire/FireSound2011.pdf
- Burning wood: only weak sources. A sound-design guide (https://sfxengine.com/blog/fire-crackling-sound-effect) and two firelog patents (https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6017373). They agree on a low bed plus irregular cracks, and that cracks are strongest early in a burn and weaken. No synthesis code.

## What the sources say
- Farnell: lapping is flame roar, crackling is small explosions in the fuel, hissing is outgassing. He makes all three from one noise source, so they move together ("causal linkage").
- Lapping: noise through a band-pass near 30 Hz, Q 5, then high-pass 25 Hz and a clip. At 16 kHz on a small speaker this is mostly inaudible, so we must raise the pitch (my choice: low-pass 90 to 350 Hz).
- Hiss: high-passed noise times a slow random signal, squared twice (4th power). The result is short loud bursts with silence between. This is what stops a hiss sounding like steady wind.
- Crackle: noise burst with a 20 ms square-law decay, random decay up to 30 ms, a random resonant band-pass 1.5 to 16.5 kHz. The trigger rate comes from a slow random signal crossing a window.
- Chadwick and James: the low band comes from the heat release rate, taken as the fuel flux through the flame front, from the visual simulation at a low rate. The high band is added by noise with a power-law spectrum f^-alpha (alpha 2.2 to 3.4, theory about 5/2), or by texture synthesis from recordings. They do not treat crackle or pops.
- Both say the same thing: the low band follows how much fire burns; the high band is only shaped noise.

## Layers and the heat-field number each could follow
Costs are my estimates for the S3 at one 256-sample block, not measured. Today's crackle is 0.41 ms.

| Layer | What it is | Driver (per step) | Est. C cost per block | Source |
|---|---|---|---|---|
| Lapping bed | low-passed noise, 3 poles, cutoff 90 to 350 Hz, times a squared 0 to 6 Hz flutter | level: total heat; cutoff: flame height; wind adds flutter | 0.15 to 0.25 ms | Farnell, Chadwick |
| Hiss | high-passed noise times (slow noise)^4, soft | level: hot area; bursts: heat change | 0.10 to 0.15 ms | Farnell |
| Pops (ember) | noise burst; loudness, length and brightness by size | ember rise speed vy at birth | about 0 extra (set at birth) | PO, Farnell |
| Crackle (fuel) | today's C crackle, roar off | ember births (as today) | 0.41 ms less its roar, about 0.3 ms | today |
| Burning object | sparser woody crackle, rate follows the trail burn and decays with age | trail burn count, heat change | 0.05 to 0.1 ms | patents, guide |
| Flare thump | 55 to 115 Hz sine sweep plus noise, 0.15 s | hit speed (flare radius) | about 0.05 ms while it plays | my design, no source |

Total of lapping, hiss and crackle: about 0.6 to 0.7 ms a block, 4 percent of the 16 ms block.

## What the kernel gives, and at what cost
Read from engine/core/fx_fire.c. The caller owns the heat array, so a caller can scan it with no kernel change.

| Number | Cost | Kernel change? |
|---|---|---|
| Total heat | 19,200 adds a step, about 10 to 20 us as a word-wise scan | No: scan heat |
| Hot area (cells over T) | 19,200 compares | No: scan, or count in the step's x loop |
| Flame height (top row over T) | a row scan from the top, stops at the first hit | No: scan |
| Heat change | needs the old value: one extra 19.2 KB copy, or one subtract in the step loop where row[x] is overwritten | Small, optional: sum in the loop |
| Wind | already in the caller (FirePlugin.wind) | No |
| Ember size | born only counts. fx_fire_take_births returns a number, not which ember | Yes: keep the vy of each new ember (a 4 slot array next to born) |
| Burn count, flare radius | known in Python (burning.py) | No |

Ember size: every ember starts at heat 255 and loses 12 a step, so all live about 18 steps. They differ only in rise speed vy (2 to 5 rows a step, so 36 to 90 rows of climb) and sideways speed. So the "bigger and brighter" ember on screen is the fast one with the long streak. Rise speed vy is the only size proxy the kernel has. If the PO wants a real size, the kernel needs a size field, which is a visual change too.

## Demo run (the real kernel, 15 s, after 2 s warm-up, seed 595, LOOK of games/fire.py, wind gusts like FirePlugin)
- The steady fire barely moves its numbers: total heat, hot area, flame height and heat change each vary only 8 to 11 percent (std over mean). So "level follows total heat" is a gentle swell. Flame height and wind move more with gusts (height 3 to 94 rows at the start, then steady near 70). The flutter and the hiss bursts do most of the work against the "river" sound.
- Births in this run: 42 in 15 s (2.8 a second, not 3.9). Embers seen with vy 2, 3, 4, 5.
- The bed levels are set by hand to mix well. In C they need fixed constants for the 98th percentile I used (total about 7.8e5, area about 1,800, change about 1.6e5).

## Ranked first slice (what the PO should hear first)
1. Lapping bed with flutter, replacing the steady roar. It answers "wind or river". Drive: total heat for level, flame height for cutoff. No kernel change.
2. Sized pops. Add the vy of each birth to the kernel (about 5 lines) and set pop gain, length and brightness from it. It answers "not synchronized with their size". Cost near zero.
3. Hiss bursts, soft. Drive: hot area. No kernel change.
4. Burning-object layer (woody crackle plus thump). Needs a hook from burning.py: pass burn count and flare radius to the sound. Later.

Keep the naive path: plain Python and the sampled crackle stay as the fallback behind one interface.

## Open questions for the PO
1. Do the pops sound right when loud means fast? Or should size mean something else (longer life)? Compare c and c0.
2. Is the bed too soft or too hissy? The mix is my guess. Which of the 3 layers do you want louder?
3. Is a kernel change for ember vy acceptable (a new field in fx_fire_t, test mirror and the Mac twin)?
4. For burning bodies: should a body's crackle fade with its age (the patents say crackle weakens as the log burns)? And do you want a thump on every flare, or only the big ones?
5. Speaker: does the board's speaker pass 55 Hz thumps? If not, raise the thump pitch.

## Demos (16 kHz mono, 15 s)
Made by /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750/demo.py, driving fx_fire.c through ctypes. Per step numbers are in steps.json and steps_burning.json.

| File | What | RMS | Peak |
|---|---|---|---|
| /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750/p750-a-today.wav | today's crackle, roar and pops from births | 1998 | 29490 (90%) |
| /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750/p750-b-layers.wav | lapping bed + soft hiss + C crackle (roar off, pops from births) | 2000 | 21219 (65%) |
| /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750/p750-c-sized-pops.wav | lapping + hiss + pops sized by ember vy (loud, long, bright for fast) | 2000 | 21694 (66%) |
| /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750/p750-c0-unsized-pops.wav | same, but pop size random (control for c) | 2000 | 19939 (61%) |
| /private/tmp/claude-501/-Users-petr-Development-firebeetle-games/42053813-a780-4e73-8e84-3f6b69758cd3/scratchpad/p750/p750-d-burning-object.wav | 4 falling burning bodies, base off; bed + woody crackle + thump on 27 flares | 2000 | 15155 (46%) |

a is also soft-limited (tanh above 45 percent) to reach the RMS target, so its pops are flatter than the board's. The demo for d uses my own body model (fall time 0.3 to 0.7 s, trail radius 3 at heat 200, flare radius v/150 at 255), not games/burning.py itself.
