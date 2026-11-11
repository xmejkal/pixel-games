# pixel-games

Small arcade games in MicroPython on a DFRobot FireBeetle 2 ESP32-S3 with the DFR0664 display (ST7789, 240 x 320, SPI). A C display driver, a fork of [russhughes/s3lcd](https://github.com/russhughes/s3lcd), sends each frame by DMA, so the Python games can run at about 20 fps.

The repository is also a log of how the games got smooth: every step was measured on the bench and written down.

## What is here

| path | what it holds |
| --- | --- |
| `games/` | the games and their small framework (`app.py` starts them, `lcd.py` and `gfx.py` draw) |
| `art/` | the painted art: one set per game, the brush and the export |
| `engine/` | a git submodule: [pixel-engine](https://github.com/xmejkal/pixel-engine), the C engine (bodies, balls, the heat field) with its Mac tests. Its own submodule `engine/driver/` is the [s3lcd fork](https://github.com/xmejkal/s3lcd), the C display driver with `frame.c`, a DMA send of one frame and partial updates |
| `tests/` | the tests that run on a computer, with no board: `python3 -B -m unittest discover tests` from the repository root (the C ones need clang). The engine's own tests run with the same command in `engine/` |
| `tools/` | `render_scene.py`: `python3 -B tools/render_scene.py burning out.png [frames ...]` draws a heat-field scene on the Mac to a PNG (needs clang and Pillow). `crackle_wav.py out.wav [seconds]` renders the fire's crackle to a WAV on the Mac (needs clang). `crackle.sh [seconds] [voice] [look]` builds the C crackle as `crackle_c.mpy`, copies it to the board and plays it on Fire |
| `build.sh` | builds the MicroPython firmware, with or without the driver |
| `bench.md` | the bench log: each run, its numbers and what it taught |
| `p537-finding.md` | the options for smooth motion, ranked, with a plan in slices |
| `docs/` | the discoveries: a public graphics library (P539) and the restyle of the games (P565). Also the wiring guides: `wiring.html` (every wire, with pictures) and `p758-encoder-steps.html` (the encoder, one wire per step) |

## Build and run

You need ESP-IDF v5.5.2 in `~/esp/esp-idf-v5.5.2`. The script clones MicroPython v1.29.0 into `~/esp` if it is not there.

1. Clone with the submodules: `git clone --recurse-submodules https://github.com/xmejkal/pixel-games.git`. If you cloned
   without them, `build.sh` fetches them.
2. Build the firmware with the driver and the engine: `./build.sh engine`.
3. Put the board in download mode: `mpremote bootloader`.
4. Write the image: `esptool --before no_reset --after watchdog_reset write_flash 0x10000 micropython.bin`.
5. Copy the games: `mpremote cp games/*.py :`.
6. Reset the board. `main.py` starts the games.

If the board stays dark after a long press of its D14 button, hold D14 for 1 to 2 seconds. That button also switches the board's power off.

## Status

Runs now:

- The fire (P595, `games/fire.py`), first at power-on: a heat field in C (`engine.HeatField`) burns over the whole
  screen. A BOOT tap moves through three modes: linear (C writes the screen's frame), picture (the fire over the painted
  sky) and nearest. It needs the engine image. The flames rise from wandering hot spots, break into tongues, rise at two speeds, lean in gusts of wind and
  throw embers. On the board, B runs at 24 fps with 11.5 to 11.8 ms of step + draw, and the sky variant at 15 to
  16 fps (bench.md, P595). In the picture mode C blends the fire in C at an alpha that follows the heat, full from heat 96
  (P603). The blend swaps the bytes of each colour in and out (`engine/driver/src/blend565.h`), so the colours are right.
  Since P608 the fire draws with bilinear filtering (`HeatField.set_filter(engine.LINEAR)`, OpenGL's `GL_LINEAR`): each
  cell's 2 x 2 px mix its heat with its neighbours', so no blocks show. The nearest mode draws the blocks as before.
  Linear costs 6.4 ms a frame to draw against 4.3 ms for nearest, at the same 24 to 25 fps (bench.md, P608).
- The ball pit (P598, `games/balls.py`), second: round balls of radius 2 to 5 px fall, knock, bounce and pile in the
  screen's box. The solver is C (`engine.Balls`): position Verlet with relaxation passes on a uniform grid
  (`engine/core/grid.c`). A BOOT tap pours 10 balls in the next colour, up to 2,000. A hold of 0.3 s or more shakes the
  pit when you let go, more strongly the longer you held it. `set_material(friction, restitution,
  restitution_threshold)` takes Box2D v3's names, and the pit uses 0.5, 0.7 and 100 px/s. Each hit is an event with
  its speed, and the HUD counts the hits a second. On the board, about 100 balls keep 23 to 24 fps (run99d, run100), and 320 run at 6 to 8 fps (run104, run100).
  A settled pile's step takes 4.2 ms at 100 balls and 13.8 ms at 300 (bench.md, P598). It needs the engine image.
- The bodies on fire (P596, P607, `games/burning.py`), third: eight falling bodies on the rain's physics each carry
  an `effects.FireTrail`, which burns heat into the fire's field behind them (`HeatField.burn`), and the field's own base is off (`HeatField.set_base`), so only the bodies
  burn. A hit at 600 px/s or faster flares up at the body's plane: C reports the hit with its speed as an event, and
  Python decides the flare (P590). The flames show behind and in front of a body: the scene draws the field, the
  bodies, then the field's hot part again, cut out with a soft edge (P639). A BOOT tap walks three modes: linear,
  picture (over the sky) and nearest. `tools/render_scene.py` draws it on the Mac. Smoke is later (cut by the PO,
  2026-11-04).
- The rain (P593, `games/rain.py`), fourth: 160 boxes fall, stepped by the C engine, and a BOOT tap swaps C
  and Python. On the board, C runs at 24 to 25 fps with a 0.22 ms step, and Python at 8 to 9 fps with a 28 ms step
  (bench.md P590). It needs the engine image (`./build.sh engine`). Without it, the rain runs in Python only.
- The bodies' API (P590): `engine.Bodies(n)` in C and its twin `motion.Bodies(n)` in Python take the same calls:
  `spawn`, `step`, `read` into an `array('h')` and `drain` into an `array('i')`. A step reports each hit with its
  speed (`HIT`) and each body that comes to rest (`SLEEP`) as an event, and the game drains them once per frame.
  `plugins.PhysicsPlugin` holds either one, and its `motion.StepClock` turns a frame's ms into 10 ms steps.
- Plugins (P633, `games/plugins.py`): a scene turns on an engine layer by listing it in one line, and leaves a layer
  off by not making it. The rain lists `(physics_plugin,)`, the fire `(fire_plugin,)` and the bodies on fire both:

  ```python
  self.plugins = (self.physics_plugin, self.fire_plugin)  # in BurningBodies.setup
  ```

  While the game plays, `Game.step` runs each plugin's `fixed_update(ms)` (the bodies step by their clock), then the
  game's `play` (reads, events, burns), then each plugin's `late_update(ms)` (the field takes the burns, blows and
  steps), in Unity's order. The game's `paint` calls each plugin's `draw` where it wants that layer.
- Effects on bodies (P607, `games/effects.py`): a body of a `PhysicsPlugin` carries an effect, and an event can start
  one. A scene makes `EffectSystem(physics_plugin)` once and calls `dispatch` and `update` each frame, after the read:

  ```python
  effects = EffectSystem(physics_plugin)
  effects.bodies[0].effect = FireTrail(field, 8, 3, 200, 0.5)  # size px, radius cells, heat, lag frames
  handlers = {HIT: lambda body, speed: ...}  # Python decides what a hit causes; it can set body.effect
  effects.dispatch(handlers)
  effects.update()
  ```

  A new effect is one more subclass of `effects.Effect` (`update(x, y)`, `reset()`), and its callers do not change.
- Sound (P748, P747, `games/sound.py`, `games/crackle.py`): a `Mixer` renders 16 kHz mono samples, and a driver
  feeds them to the amplifier through stock `machine.I2S`: `FrameRefill` once per frame, or `CallbackRefill` from the
  I2S callback. The fire's crackle is a soft, deep roar and one pop per ember birth (`HeatField.take_births()`), so
  the pops come with the sparks. `NativeCrackle` renders it in C (`engine/core/fx_crackle.c`), loaded from
  `crackle_c.mpy` with no firmware rebuild: at most 0.41 ms per 16 ms block, and Fire keeps 24 fps (bench.md, P747).
  `SampledCrackle` is the plain Python path: four pre-rendered pops through the `Mixer`. Since P751, `GrainCrackle` plays
  one woody pop per ember, in sync with the sparks, over a low flame roar, from a bank rendered on the Mac
  (`tools/fire_bank.py`), kept in `engine.SoundBank` outside the GC heap. The fastest embers (rise 4 and 5) get larger pops. Only the bench probe
  (`probe733_games.py`) turns the sound on today. Try a change to the C crackle with `tools/crackle.sh`. Since P753, `FireSound` adds integer noise in C (`engine/core/fx_noise.c`): each falling burning body of `BurningBodies` whooshes by its airspeed, and Fire plays the pops alone, because the PO heard the noise bed as wind. Try it with `GAME=BurningBodies tools/crackle.sh 30 FireSound`.
- The rotary encoder (P758, `games/encoder.py`): `Encoder.on_board(pins.ENC_A, pins.ENC_B, EDGES_PER_DETENT)` reads
  the knob through `machine.Encoder`, the ESP32-S3's pulse counter, so no interrupt runs. `detents()` gives the clicks,
  + one way and - the other. The bench measured 4 edges per click (bench.md, P758). The knob can rest 1 edge from a
  click's border, so a use that must not flicker calls `take_detents(now_ms)`: it has a dead band of 2 edges, and
  its rest point follows the knob. No game uses the knob yet: only the probe does. The encoder sits on the pads RX
  and TX (`docs/wiring.html`), which the image gives to its serial console at each reset. So `app.py`, `encoder.py`
  and `pins.py` go on the board together.
  `encoder.take_pads(pins.ENC_A, pins.ENC_B)` takes them, and `app.run` calls it first.
- The master volume (P757, `games/volume.py`): `MasterVolume` is one gain on the whole mix, the last step before
  the I2S. It has 16 steps of 3 dB, and step 0 is silent. A change of step ramps across one block, so it does not
  click. Give it to a driver: `CallbackRefill(mixer, i2s, sd, ring_samples, volume)`. `MasterVolume` is plain
  MicroPython (1.2 ms a block). `ViperMasterVolume` (`games/volume_viper.py`) gives the same samples in 0.1 ms.
  `VolumeKnob(encoder, volume, store)` turns the step, 1 step per click, from `poll(now_ms)` once per frame.
  `VolumeStore` keeps the step in `volume.txt`, and the knob saves it 3 s after the last turn. The save is off in the
  probe by default: each 37th save takes 2.4 s and stops the sound (bench.md, P757). The fix is a later card.
  Status: the gain works, and the knob turns it on the pads RX (GA, GPIO44) and TX (GB, GPIO43). On the first
  pads, SDA and SCL, the step did not move in Fire. A closed contact read 1.2 to 1.4 V there, not 0 V. A
  device at 0x36 also answers on those pads (bench.md, P757, entries 11 to 19). So the encoder moved on
  2026-11-11. The games take both pads from the console at their start (entry 24). While the PO turned the knob,
  the counter counted with no sound and with a tone (entry 26). In Fire the step went from 0 up to 16 (entry
  27). The PO: "yeah, seems to be working." From a reset until a game starts, a turn of the knob can
  type into the console. That time is not measured. If the start stops before `take_pads`, the console keeps
  both pads. No run starts the board with a contact closed on RX. Set the step with `LEVEL`:
  `VOLUME=ViperMasterVolume LEVEL=4 tools/crackle.sh 30 FireSound`. `KNOB=1` adds the knob, and `SAVE=1` the save.
- The system overlay (P762, `games/overlay.py`): one small picture over the running game, for system information.
  `Overlay` holds one view and hides it 1 s after the last `show(view, now_ms)`. A view is any object with
  `draw(cv)`, so a new kind of information is a new class. `VolumeView` is the first view: the volume's step as 16
  cells and a number. The app owns the overlay (`App.overlay`), and each output draws it after the game.
  Status: with `KNOB=1` the probe shows the volume at each turn of the knob, in Fire. The PO turned the knob and saw
  it: "nice". That was the first form of the picture, painted whole at each step. No game shows it yet, because only
  the probe has the knob. Now the first show paints both parts (4.4 ms), and a new step paints the cells and the
  number again (2.2 ms). Without the overlay the fire's sound has 1 ms of margin in Fire: the longest gap between
  two refills is 47 ms, and the limit is 48 ms. With the overlay and fast turns the gap reached 49 ms. The PO's
  turns made 5 late refills in 120 s, with the first form of the picture (bench.md, P762). Nobody reported a gap in
  the sound. The picture is solid. `ALPHA=192` on the command lets the game show through it, for about 1 ms more per frame:
  `ALPHA=192 VOLUME=ViperMasterVolume KNOB=1 tools/crackle.sh 60 FireSound`. Nobody looked at that picture yet.
- The wiring comes from spark (P758): `requirements.json` names the board, the parts and the PO's wired pads. After a
  change, run `python3 ~/Development/spark/scripts/check_spine.py requirements.json --keep build --json` and copy
  `build/firmware/pins.py` to `games/pins.py`. The run ends in `problems` today, only because the reserved display pins
  connect to no part. The microphone's record, `parts/inmp441-i2s-mic-round.json`, comes from one photo through
  `/spark:identify`: list its open facts with `parts.py --unverified inmp441-i2s-mic-round --project .`. The wiring
  guide with pictures is `docs/wiring.html`, also at https://claude.ai/artifact/Xyppus2vF8xmC3Etc9Rbm4.
- The HUD is drawn once into a strip and blitted each frame (P599).
- Fourteen games. Four are effect scenes: fire, the ball pit, bodies on fire and rain. Three are painted: runner, flappy and stack (stack as RENT). The other seven are flat.
- The double buffer: the game paints into PSRAM, and `show()` copies the frame and returns.
- Measured fps per painted game, from `bench.md`: flappy 24 under an autopilot (run92, the P602 run before the fire went on), runner 21 to 24 with no play, both at a 40 ms frame pace; stack 24.

Done last: P598 ([#799](https://github.com/xmejkal/spark/issues/799)), the ball pit, merged 2026-11-05. Before it, P602 ([#803](https://github.com/xmejkal/spark/issues/803)), fire that drifts with a scrolling world (`HeatField.scroll`, `FireLayer`), merged with no game on it: the PO tried it behind flappy's bird and kept it for other games. The PO chose "Full MVP, 4 slices" on 2026-11-04 to close the effects epic P594 ([#795](https://github.com/xmejkal/spark/issues/795)). Paused: P582 ([#783](https://github.com/xmejkal/spark/issues/783)), heavy floors for RENT, on the branch `p582-heavy`, not merged.

In Idea, after the pit: P614 ([#820](https://github.com/xmejkal/spark/issues/820)), a faster ball solver, and P618 ([#824](https://github.com/xmejkal/spark/issues/824)), a soft contact with a damping ratio, P619 ([#825](https://github.com/xmejkal/spark/issues/825)), balls drawn from small pictures, and P616 ([#822](https://github.com/xmejkal/spark/issues/822)), balls on fire. Also in Idea: P610 ([#814](https://github.com/xmejkal/spark/issues/814)), a Blur effect on a screen region, and P611 ([#815](https://github.com/xmejkal/spark/issues/815)), a motion blur behind a fast body, combined with its FireTrail. Later: P612 ([#817](https://github.com/xmejkal/spark/issues/817)), a spike on where a game's frame time goes and how to reach 25 fps or more, and P583 ([#784](https://github.com/xmejkal/spark/issues/784)), effects in C on the S3's PIE (its vector instructions).

The work is planned on the board of the [spark](https://github.com/xmejkal/spark) project.

## Licence

MIT, see `LICENSE`. The files under `engine/driver/` keep their own terms.
