# P755 researcher A: fire sound models, tools, motion, wind

> No model after 2011 gives a ready fire synth. The usable facts are small. Puffing frequency falls with fire width. Tools expose one "intensity" for roar level and crackle rate. A whoosh is band-passed noise driven by speed.
> Wind on a flame has almost no direct sound research. Treat wind as a flutter and noise-level control (a design choice, not a sourced law).
> I read 1 page fully (garjan source). All else is "snippet" (search result text). Both pages from Nemisindo and Wwise gave 404 and 403.

Marks: read = I opened it. snippet = search result text only. Costs are rough, not measured. "Our numbers" = total heat, hot area, flame height, heat change, wind, ember rise speed, trail and flare radius.

## 1. Models after 2011, and how size changes the sound

1. Puffing frequency of a pool fire falls with diameter: f = 1.5 / sqrt(D) (D in metres, f in Hz). Source: Cetegen and Ahmed 1993, quoted in a 2022 Cambridge paper. snippet. https://www.cambridge.org/core/services/aop-cambridge-core/content/view/E9A7FF517322D98E9ECBB01169C8F710/S2633425922000265a_hi.pdf/a-computational-examination-of-large-scale-pool-fires-variations-in-crosswind-velocity-and-pool-shape.pdf
   - Same square-root trend seen in a 2014 ethanol study. snippet. Moreno-Boza 2018 ties onset to the Rayleigh number (grows with D cubed). snippet. https://e-archivo.uc3m.es/entities/publication/2613ed72-8032-4a3b-8b16-695d50b6183a
   - Inputs: fire width. Our driver: hot area, taken as width = sqrt(area). Use it as the flutter rate of the lapping bed: a 0.1 m fire gives about 4.7 Hz, a 1 m fire 1.5 Hz, a 4 m fire 0.75 Hz. Cost: cheap (one LFO rate).
2. Turbulent flame noise is broadband with one peak. A review puts the peak at a wavelength near 50 times the burner diameter, 200 to 800 Hz in practice. snippet. https://www.ioa.org.uk/system/files/publications/HG%20LEVENTHALL%20CG%20PALMER%20JP%20ROBERTS%20NOISE%20SOURCES%20IN%20OIL%20AND%20GAS%20COMBUSTION%20PROCESSES.pdf
   - A premixed study says the peak frequency depends on flame height above the port, not on flame speed. snippet. https://www.ioa.org.uk/system/files/publications/JP%20ROBERTS%20GAS%20COMBUSTION%20NOISE%20PRODUCED%20BY%20FLOW%20TURBULENCE%20IN%20OPEN%20PRE-MIXED%20FLAMES.pdf
   - One fit gives f_peak proportional to U^0.18 D^0.08 (weak size effect). snippet. https://core.ac.uk/download/4736053.pdf
   - Non-premixed (candle-like, wood) flames peak lower, under 100 Hz, with a steeper fall at high frequency. snippet. https://openresearch.surrey.ac.uk/esploro/outputs/conferencePresentation/Modelling-of-combustion-noise-spectrum-using/99512455602346
   - Meaning for us: real peaks sit under 100 Hz to 800 Hz. Our speaker is weak below about 200 Hz, so the cutoff is our choice (P750: 90 to 350 Hz). Driver: flame height sets the cutoff (taller flame, lower peak, per the premixed finding, not confirmed for open fires). Cost: cheap (one filter cutoff).
3. Data-driven and neural: MTCRNN (Huzaifah and Wyse 2020) is a GRU texture model that lists crackling fire. snippet. https://arxiv.org/pdf/2011.12596.pdf
   - Inputs: a conditioning vector from training audio. Size on the S3 at 300 to 800 hidden units per layer: heavy. Reject for the board. It can only make a bank of samples offline.
4. Texture synthesis follow-ups: Jo 2016 extends Chadwick and James with bandwidth extension. snippet. https://sonicfield.org/library/sound-synthesis-methods-of-fire-flame-sound-for-predicting-hidden-images  . A Cornell demo page for fire texture synthesis exists. snippet. https://dougjam.github.io/demos/fire-texture-synthesis/
   - Inputs: a low band from a heat-release signal, a high band from recorded grains. Our heat change can drive the low band. Cost: medium (grain lookup, plus a crossfade). Fits our sample-bank style.
5. DDSP for fire: my search found no paper. Not found, not a "no".

## 2. How tools model fire

1. garjan (open Rust crate, procedural fire). read. https://docs.rs/crate/garjan/1.0.0/source/src/fire.rs
   - One input: intensity 0 to 1 (embers to inferno).
   - Roar: brown noise, low-pass 600 Hz, Q 0.7, level = intensity x 0.3.
   - Crackle: Poisson events in 10 ms blocks. Rate = 5 + 30 x intensity per second. Peak = intensity x uniform(0.1, 0.6).
   - Each crackle lasts 5 to 30 samples with linear decay. The noise is high-passed at 2 kHz.
   - Hiss is in the doc but not in the code. A DC blocker ends the chain.
   - Our map: intensity from total heat. Cost: cheap (two filters, a Poisson draw).
2. Nemisindo (browser, QMUL, Reiss). Fire is in the Action Pack and the Nature Pack. Parameters can change at runtime. snippet. https://docs.unrealengine.com/marketplace/ja/product/nemisindo-action-pack
   - A 2024 AES paper lists its fire as "Burning Embers": additive, physically informed and subtractive. snippet. https://www.aes.org/e-lib/download.cfm/22409.pdf?ID=22409
   - Parameter names: not found. Docs URL gave 404. Do not guess them.
3. Wwise SoundSeed Air: Woosh and Wind. Speed and distance link to its parameters. You set the object's shape, path and speed. No source audio. Wind uses time-varying parameter sets. snippet. https://www.audiokinetic.com/en/wwise/plugins/soundseed-air/ (the page gave 403, text from search results) Parameter names: not found.
4. Unreal MetaSounds: Nemisindo 2.0 ships its models as MetaSounds nodes. snippet (same Epic page as above). No separate fire patch found. Not searched further.
5. Pattern across tools: one intensity control, crackle rate rising with it, a low bed that gets louder. This matches the P750 plan. Wind is not a named control in any fire tool I found.

## 3. Moving flames (torch, fireball, burning object)

1. Whoosh recipe: noise through a band-pass or low-pass, cutoff swept up and down about 1 s, with a swell-and-fade level. A fixed noise burst with a fade is not a whoosh. Pitch moves for approach and pass-by (Doppler feel). snippet. https://violetrecording.com/how-to-make-whoosh-sounds/
2. Speed as driver: a procedural-audio article drives envelope, filter, gain and noise mix from vehicle speed. snippet (same search, no URL kept). Our driver: body speed. Cost: cheap (one band-pass with cutoff and gain set from speed).
3. Physics: vortices shed behind a thin object give a tone whose pitch rises with speed (Aeolian tone). The CEDEC 2010 talk (Heavenly Sword whoosh) says subtractive synthesis is cheaper than full aerodynamics. snippet. https://cedec.cesa.or.jp/2010/archive/files/C10_P0051/C10_P0051.pdf
   - Rule of thumb from my own memory, not sourced here: f = St x v / d with St near 0.2. A burning body is a poor thin rod, so use it as a pitch slope only.
4. Dobashi, Yamamoto, Nishita 2003: sound textures from fluid simulation, played back at a rate set by object motion or wind speed. snippet. https://history.siggraph.org/?p=115926 . Survey https://arxiv.org/pdf/2011.05538
   - Cost: medium (a texture bank plus a playback-rate change). We can do the cheap version: one noise with a speed-driven band-pass.
5. A moving flame is two sources: the flame's own roar (follows size) and the air whoosh (follows speed relative to the air). No paper found that joins them for flames. Gap.
6. "Kinda against the wind" (PO): use relative speed = body velocity minus wind velocity. Moving into the wind gives a large relative speed, so a louder, brighter whoosh. Moving with the wind gives a small one. This is my design from the physics of relative airflow, not a sourced result.
   - Inputs: body vx, vy, wind. Our drivers: speed, wind, flare radius. Cost: cheap.

## 4. Wind on a flame

1. Direct research on sound against crosswind speed: not found. A search for it returned only indirect work. snippet. https://prism.ucalgary.ca/items/eb2b2ec2-e12d-40b3-b1ed-41e2993cfed9
2. Non-burning jets in a crossflow get a higher noise power level (NASA VTOL study). snippet. https://ntrs.nasa.gov/api/citations/19730013202/downloads/19730013202.pdf Plume sound in crossflow concentrates downwind (snippet: https://sonicfield.org/library/sound-propagation-through-elevated-heated-jets-in-cooler-cross-flow-an-experimen). Hot jet only, not flame.
3. Crosswind and pool fires: a Cambridge paper simulates crosswind and pool shape. It is about shape and burn rate, not sound. snippet. Same URL as in section 1, item 1.
4. Design choices that fit the evidence (mine, to test by ear):
   - Wind raises the level of the noise bed a little, and shortens the flame (visible on screen already).
   - Wind raises flutter depth and adds irregular gusts in the bed. Driver: wind gust number. Cost: cheap.
   - Wind past the listener is a separate wind layer (band-passed noise, level from wind). Cost: cheap.

## What this means for P753 (one line each)

- Size layer: total heat sets bed level, hot area sets flutter rate (1.5 / sqrt(D) shape), flame height sets cutoff. Cheap.
- Wind layer: wind sets noise level and flutter depth. Cheap.
- Moving burning object: relative speed (body minus wind) sets whoosh band and level. Cheap. Crackle rate follows trail burn (garjan: 5 to 35 per second by intensity). Cheap.
- Heavy options (neural texture, CFD textures) do not fit the "naive path stays working" rule and have no field driver we lack.

## Gaps

- Nemisindo and Wwise parameter names: not found (404, 403).
- No source joins fire size to roar spectrum for open fires in a clean law.
- No source for wind against flame sound.
- Unreal MetaSounds: no fire patch found.
- Searches used: 11 searches, 3 fetches (one of them read: garjan).
