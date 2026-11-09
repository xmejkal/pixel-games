# P729 sound discovery: refuter

Read 2026-11-09 (Europe/Prague). Paths: `PS` = /Users/petr/Development/pixel-sound, `MPY` = ~/esp/micropython-v1.29.0, `IDF` = ~/esp/esp-idf-v5.5.2/components. Nothing was run on a board. Every "calculated" below comes from source read here or arithmetic done here, and none of it was run. `verification.md` is still the empty template (its fill marker), so part 2 had no verification file to compare.

Verdict counts: 6 holds (★C1, ★C2, ★C6, ★C11, ★C15, ★C18), 12 partly (★C3, ★C4, ★C5, ★C7, ★C8, ★C9, ★C10, ★C12, ★C13, ★C14, ★C16, ★C19). None refuted outright; ★C7's and ★C8's second halves come closest. None could-not-open as a whole, and the unopened sources are named at each claim.

## 1. Claims

### Check first (start: existing product)

Does the change address the observed problem? There is no observed problem in the folder. `council/po-assistant.md:58` RA-1: "Nobody is blocked now. The games run silently at 24 to 25 fps (measured), and no card lists a game waiting on sound." The issue title's problem is its own wording: "the games are silent, and we do not know what sound the S3 can do". The second half is a knowledge gap and the first is a wish. The brief's "What we found" never states RA-1. It appears only in the value row of `risks-and-tests.md:9`. Nothing in the folder disproves a want, and the PO's request is a stated want (n = 1). So the honest frame is "a wish and a showcase", not "a problem the change fixes".

What breaks for current users, read from the source. The brief names frame time as the only "must not get worse" line. Three break paths are missing from the brief.

- **Fire and Burning can lose their internal-RAM field.** `IDF/esp_driver_i2s/i2s_private.h:50`: "#define I2S_DMA_ALLOC_CAPS      (MALLOC_CAP_INTERNAL | MALLOC_CAP_DMA | MALLOC_CAP_8BIT)". `PS/engine/binding.c:160-164` allocates the heat field in internal RAM and falls back to PSRAM: "size_t n = (size_t)w * (size_t)h + FX_FIRE_MAP_W * FX_FIRE_MAP_H;", "heat = heap_caps_malloc(n, MALLOC_CAP_SPIRAM);". `run130-p656-smoke.log:7-8`: "fire internal largest 31744", "fire field internal". For a 160 x 120 field (FEAS-12) n is 19,200 + 256 x 32 = 27,392 B (calculated. The map size is `engine/core/fx_fire.h:15-16`). Largest free block 31,744 B leaves 4,352 B. An `ibuf` of 4096 B takes 8 blocks of 512 B plus descriptors from internal RAM (`i2s_common.c:495,503`). Each block is allocated separately, so other free fragments can serve it, and the opening order matters. How much internal RAM is free beyond that block is —. If I2S is open before the field is made, the field can fall to PSRAM and change Fire's frame time. A1's pass line would then fail for a reason the brief does not name. Nothing in the brief says that `machine.I2S`'s buffers come from the same small pool.
- **A blocking write can spend frame time.** `MPY/ports/esp32/machine_i2s.c:238-242`: "delay = portMAX_DELAY;  // block until supplied buffer is emptied". A buffer kept full enough to cover a stall blocks the write when the queue has no free block. A1's "costs the games no frame time" and "plays with no heard gap through the worst frames" pull against each other. The test text does not name the write mode.
- **Road can not be able to pay at all.** Road's means in run130 are 40.7 and 46.5 ms per frame against the 40 ms slot (part 4), so the game has no free frame time for a Python fill. The brief quotes only Fire's headroom.

Claims follow. Quotes are verbatim, with pointer.

### ★C1 · holds
Read: `run130-p656-smoke.log:170` "time road step 1.0 paint 38.5 send 4.7 gc 2.3 fps 20 worst 105 slowest 103 = step 13 paint 68 send 20 gc 11"; `:119` "time stack step 0.7 paint 13.3 send 3.4 gc 2.0 fps 25 worst 40 slowest 29 = step 0 paint 25 send 3 gc 0"; `:12` fire "worst 48"; `:25` balls "worst 57". `games/app.py:71`: "# the longest gap between two frame starts: a freeze shows here". The grep over `games/*.py` for i2s, audio, sound, speaker, MAX98357, DFR0954, buzz and beep printed nothing, and `games/pins.py:4-15` has no audio pin. 23 `time` lines, 14 games, fps 20 to 25: all reproduced. The correction stands: 105 ms is Road's, the 57 ms is BallPit's. Road's 105 is one window of two. The other reads "worst 66" (`:165`). Caveats the claim needs are in part 2.

### ★C2 · holds
Read: `MPY/ports/esp32/machine_i2s.c:371-372` "i2s_std_slot_config_t slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(get_dma_bits(mode, bits), get_dma_format(mode, format));", "slot_cfg.slot_mask = I2S_STD_SLOT_BOTH;"; `:378` ".mclk = I2S_GPIO_UNUSED,". Only `i2s_channel_init_std_mode` (`:397`), so no PDM and no TDM. One note on "does not ... fade": `MPY/extmod/machine_i2s.c:442` "// shift=1 increases volume by 6dB, shift=-1 decreases volume by 6dB". `I2S.shift()` is a whole-buffer volume in C. It is not a fade, so the claim holds, but FEAS-9's "no volume or panning" is too broad.

### ★C3 · partly
Read: `machine_i2s.c:136-137` "if (format == MONO) {", "return I2S_SLOT_MODE_MONO;"; `:149-150` "uint32_t dma_frame_size_in_bytes =", "(get_dma_bits(mode, bits) / 8) * (get_dma_format(mode, format) == I2S_SLOT_MODE_STEREO ? 2: 1);"; `IDF/esp_driver_i2s/i2s_std.c:117` "handle->active_slot = slot_cfg->slot_mode == I2S_SLOT_MODE_MONO ? 1 : 2;"; `i2s_common.c:419` "uint32_t bytes_per_frame = bytes_per_sample * active_chan;". The correction holds: mono TX has a 2-byte DMA frame, and FEAS-3 misread it. 2048 B is 4 blocks and 4096 B is 8 blocks. The wire does carry two slots (`machine_i2s.c:372`, and `IDF/hal/esp32s3/include/hal/i2s_ll.h:1091-1092` "MONO in hardware means only one channel got data, but another doesn't", "MONO in software means two channel share same data"), so FEAS-3 is wrong about DMA and right about the wire.

The narrowing: 64 ms and 128 ms are capacity, not coverage. `IDF/esp_driver_i2s/i2s_common.c:329`: "new_chan->msg_queue = xQueueCreateWithCaps(desc_num - 1, sizeof(uint8_t *), I2S_MEM_ALLOC_CAPS);". The writer can hold 7 of 8 blocks ahead, the eighth being in play. A stall is covered by 7 blocks (112 ms) plus what is left of the playing block (0 to 16 ms). Writes of 640 samples are 2.5 blocks, so every other write ends mid-block and the half-block tail plays as zeros if the stall lands there (`auto_clear`), about 8 ms less. Calculated coverage at 4096 B is about 104 to 128 ms. Road's 105 ms sits inside that range. Sentence to change: "`ibuf` 2048 B is 4 blocks and 64 ms, and 4096 B is 8 blocks and 128 ms (calculated from 256 frames per block)" → "`ibuf` 2048 B is 4 blocks and 4096 B is 8 blocks, which is 64 ms and 128 ms of capacity (calculated). The driver's queue is one block short of that, and a partly filled last block plays as zeros, so 4096 B covers a stall of about 104 to 128 ms (calculated, not run)."

### ★C4 · partly
Sources read: ★C1, ★C3, FEAS-11, RA-5. The arithmetic (40 + 64 = 104, 40 + 128 = 168) is right. Three faults.
1. "polled once per frame (40 ms)" is the target `games/app.py:31` "FRAME_MS = 40". The game that forces 128 ms is Road, whose frames average 43 to 50 ms (fps 23 and 20) and whose worst is 105 ms. A hit just after the poll, before that frame, waits up to 105 ms. Road's bound is about 233 ms at 128 ms of buffer (calculated), so "up to about 168 ms" is not an upper bound in the game that sets the buffer.
2. "Only the 128 ms buffer covers Road's 105 ms gap" names two depths and picks one. 7 blocks (3584 B, 112 ms capacity) also clears it nominally, and ★C3's reading says 4096 B only covers it depending on phase.
3. The claim needs the correct delay target. The 20 to 30 ms figure is model knowledge (RA-5). It is flagged in the caveat but A3 still sets its pass line from it.
Sentence to change: "so a hit waits up to 40 ms plus the buffer: about 104 ms with 64 ms of buffer and about 168 ms with 128 ms. Only the 128 ms buffer covers Road's 105 ms gap (calculated)" → "so a hit waits up to one frame plus the buffer: about 104 ms with 64 ms of buffer and about 168 ms with 128 ms in a 40 ms frame, and about 233 ms in Road's 105 ms frame (calculated). Of the two depths named, only 128 ms nominally covers Road's 105 ms gap, and the driver's queue makes the coverage about 104 to 128 ms (★C3)".
It also carries through ★C1's rival: the 105 ms frame is a state-change frame (part 3, R1).

### ★C5 · partly
The figures reproduce: 640 samples x 2 µs = 1.28 ms. X 10 µs = 6.4 ms; `run130-p656-smoke.log:12` means 6.9 + 9.2 + 4.3 + 2.0 = 22.4 ms, so 17.6 ms is free; 17.6 ms / 640 = 27.5 µs; 1 s / 16,000 = 62.5 µs. The correction stands in substance: no per-sample cost is measured here, so "impossible" is not shown. Read: `council/po-assistant.md:17` "that a naive Python version of sample generation cannot loop per sample"; `:61` "A per-sample Python loop at 16 kHz is not feasible from the call costs (EX-7)"; `council/tech-lead.md:15` "10 µs (H, derived from the measured 56.8 µs per particle update and 114 µs per spring body update ... as about 6 statements; the statement count is my estimate)".
Faults:
1. The quoted words "cannot loop per sample" are at EX-7 (line 17), not RA-4 (line 61). Attribution error.
2. "one voice fits up to 27.5 µs per sample" is Fire's budget, stated without the word. Free time by game (40 minus step + paint + send + gc, 5 s window means): Burning 9.5 ms, Flappy 9.6, Runner 9.3, Cave 2.5 and 7.1, Road −0.7 and −6.5. At those the per-sample budget is 14.5 to 15.0 µs, 3.9 and 11.1 µs, and none. The brief's own interface is one interface for the games, and its slice 8 is sound in the other games. In Road no live synthesis fits at all.
3. The 10 µs per sample is about one float statement by its own derivation. `probe567.py:58-65` has 7 statements in the particle body (`p[3] += g * dt`, `p[2] *= drag`, `p[3] *= drag`, `p[0] += p[2] * dt`, `p[1] += p[3] * dt`, `p[4] -= dt`, `if p[4] <= 0:`), so 56.8 µs is about 8 µs per float statement (calculated). A sample with noise and a decay (A2's test) is several statements. By the same derivation that is well above 27.5 µs, unless integer statements on an `array('h')` are much cheaper, which is — (no integer cost is measured, FEAS-8). The brief passes 6.4 ms to the PO as "about 6 ms" in Q2 with the word "estimate" and without this.
Sentence to change: "Fire leaves 17.6 ms of the frame, so one voice fits up to 27.5 µs per sample." → "Fire leaves 17.6 ms of the frame, so one voice fits up to 27.5 µs per sample in Fire, as a mean of one 5 s window. Other games leave less (9.3 to 9.6 ms in Burning, Flappy and Runner, 2.5 to 7.1 ms in Cave) and Road leaves none (−0.7 and −6.5 ms). The 10 µs estimate is close to one float statement by its own derivation (56.8 µs over 7 statements in `probe567.py`), and a sample takes several, so 6.4 ms is a low estimate."
N2's "Whether `@viper` is in this image is —": `games/fast.py:1` "@native where MicroPython has it" and `games/gfx.py:240`, `games/motion.py:42`, `games/render.py:17` use it. `@native` is in the code that runs. Only `@viper` stays —.

### ★C6 · holds
Read: `machine_i2s.c:297` ".on_send_q_ovf = NULL,"; `:363` "chan_config.auto_clear = true;"; `IDF/esp_driver_i2s/include/driver/i2s_common.h:51` "i2s_isr_callback_t on_send_q_ovf;       /**< Callback of sending queue overflowed event, only for TX channel". The caveat "only the header's words are read" can be tightened from the driver. `i2s_common.c:642-647`: "if (xQueueIsQueueFullFromISR(handle->msg_queue)) {", "if (handle->callbacks.on_send_q_ovf) {". The queue holds `desc_num − 1` entries (`:329`), and it is full only when no block has data ahead. So the callback fires once per 16 ms block played dry. One gap of N blocks is N events, not one event. It also fires when the game simply writes nothing during silence. Q4's O2 "a real count" counts dry blocks, and it needs a fill that always writes (silence included). Calculated from source, not run.

### ★C7 · partly
Read: `machine_i2s.c:449-456` "if (xTaskCreatePinnedToCore(", "MP_TASK_COREID) != pdPASS) {"; `:274` "mp_sched_schedule(descriptor.callback, MP_OBJ_FROM_PTR(self));"; `mphalport.h:54` "#define MP_TASK_COREID (1)". The first two sentences hold. "A C task on core 0 is the only named path that keeps playing through a garbage collection" does not follow. `machine_i2s.c:40` "// - all sample data transfers use DMA": DMA plays through a collection on the stock path, if the buffer outlasts it. Run130's collections are 1.9 to 3.0 ms on average per frame and 10 to 11 ms in the four slowest frames that include one (`:78`, `:131`, `:170`, `:204`), all under the 64 ms buffer. FEAS-13 only says a core-0 task is not paused (H). It says nothing about being the only path. That DMA plays through a collection is itself not run (USER-9's caveat). Sentence to change: "A C task on core 0 is the only named path that keeps playing through a garbage collection" → "A C task is the only named path that refills while Python stalls longer than the buffer. A collection of the size seen in run130 (10 to 11 ms at most) is shorter than a 64 ms buffer, so the stock DMA should play through it (H, not run)". The core is a choice too: a task of higher priority than the MicroPython task (`ESP_TASK_PRIO_MIN + 1`, FEAS-4) on core 1 preempts the interpreter (H, FreeRTOS). P2's "proves: sound through a garbage collection" proves nothing the stock path cannot.

### ★C8 · partly
Read: `council/po-assistant.md:51` "No project found is both a C sound core and a MicroPython user module for the ESP32-S3. One search ... This is one search, so absence is weak." The sentence about what was found holds as a report of that one search. The following H ("The C part is probably written here from primitives") is contradicted by one search here. `https://github.com/shorepine/amy` README: "We've run AMY on:" ... "ESP32, ESP32S3 (Xtensa)". Licence MIT (`gh api repos/shorepine/amy`, SPDX id MIT). `shorepine/tulipcc` `tulip/esp32s3/esp32_common.cmake:188-196` lists "${TULIP_SHARED_DIR}/amy_connector.c", "${AMY_DIR}/src/amy.c", "${AMY_DIR}/src/delay.c", and more into a MicroPython firmware, with an `N16R8` board at `tulip/esp32s3/boards/N16R8/`, the PO's memory size; `tulip/shared/modtulip.c:2032` "MP_REGISTER_MODULE(MP_QSTR__tulip, tulip_module);". It is not a plain user C module (it is built into a firmware), and I did not read its frame behaviour, its core use or its I2S path. It is a C synth core in MicroPython on the S3, MIT, and it was not found. Sentence to change: "The C part is probably written here from primitives (H)" → remove, or "AMY (MIT, C, runs on the S3) built into MicroPython's Tulip firmware is the nearest project found, and neither its fit nor a smaller alternative was read." P2's caveat "no report names one" should name it. Its size and fit are —.

### ★C9 · partly
Read: `council/po-assistant.md:3` "Licences read from each repository's own LICENSE file or the GitHub API on 2026-11-09"; `:42` "MIT (README, API)" (ZzFX); `:41` "jsfxr: Unlicense (API; 2026-05-05)"; `LICENSE:1` "MIT License"; `engine/LICENSE:1` "MIT License". The brief's "Licences read from each project's own file" is stronger than the source. `gh api repos/<r>` here gives esp-dsp Apache-2.0, SDL_mixer Zlib, jsfxr Unlicense, ZzFX MIT, TIC-80 MIT, Soundpipe MIT, arduino-audio-tools GPL-3.0, ESP8266Audio GPL-3.0, Mozzi LGPL-2.1. For CircuitPython, MicroPython, SoLoud, miniaudio and stmlib the API returns NOASSERTION, and those rest on the council's reading of their files, not re-read here. Sentence to change: "Licences read from each project's own file" → "Licences read from each project's own file or the GitHub API (ZzFX and jsfxr from the API or a README)".

### ★C10 · partly
Read: `gh api repos/adafruit/circuitpython/contents/shared-module/audiomixer`: "Mixer.c Mixer.h MixerVoice.c MixerVoice.h __init__.c __init__.h". `engine/binding.c:130` "MP_QSTR_Bodies,", `:347` "MP_QSTR_HeatField,", `:530` "MP_QSTR_Balls,"; `:334-341` for `set_*` and `step`; `engine/core/events.h:41` `events_drain`. The CircuitPython and engine names reproduce. The narrowing: the rest is H from model knowledge (EX-12: "the rest is model knowledge"). The sentence presents it as "Names the projects use", which reads as read. It is tagged H and the caveat says so. Keep, but "Names the projects use:" → "Names the projects use (only CircuitPython's are read; the rest are model knowledge):".

### ★C11 · holds
Read: `engine/core/events.h:3` "Plain C99 with no MicroPython or IDF header."; `engine/micropython.cmake:6-12` lists sources one per line. Across `engine/core/` the includes are `<stdint.h>`, `<stddef.h>`, `<string.h>`, its own headers and `blend565.h` ("driver/src: the blend s3lcd uses, plain C"). The rule holds. One narrowing the brief does not need to change: `core/` already depends on a header in `driver/src/`, so "no driver dependency" would be wrong, but the claim does not say it.

### ★C12 · partly
Read: `events.h:10` "#define EVENTS_MAX 64"; `:15` "int32_t id, kind, speed;  // speed: the impact in px/s, truncated toward 0; 0 for a sleep"; `:30-31` "if (b->n == EVENTS_MAX) {", "b->dropped++;"; `bench.md:244` "| drain of 16 events into an `array('i')`, read in Python | 162.5 | µs | | |"; `games/effects.py:97` "handler(self.bodies[events[j]], events[j + 2])". The first sentence and the 162.5 µs hold. "An event carries no position, material or ball size" is true of `event_t` but says less than the source: the event carries an `id`, and `effects.py:97` hands the handler the body by that id, so Python can read position and material at a Python cost. Sentence to change: "An event carries no position, material or ball size" → "An event carries an id, a kind and a speed. Position, material and size are read from the body by id at a Python cost, not from the event (games/effects.py:97; checked for Bodies, not for Balls)".

### ★C13 · partly
Read: `engine/binding.c:333-342` (set_look, step, set_base, set_filter, burn, scroll, draw, __del__); `engine/core/fx_fire.h:26` "uint8_t *heat;", `:31` "int32_t decay, cool, sway, spots, spread, fast, embers, fade;", `:35` "int32_t ember_heat[FX_FIRE_MAX_EMBERS];  // 0 is a free slot". No read-back holds, and a C core can read the struct. "the Python version cannot" holds for the heat field only. Python holds the gust: `games/fire.py:114` "self.wind, self.target, self.gust = 0, 0, 0  # the gust model: the wind now, where it goes, ms to the next", `:131` "self.field.step(steps, self.wind)". So both versions can share an input Python already holds. "so both versions need one small statistic if they are to share one interface" is the synthesis's H. A6's fallback "read gusts and embers from Python" has a different problem: gusts are Python's, and individual ember births are C-side. Sentence to change: "and the Python version cannot, so both versions need one small statistic" → "and the Python version cannot read the heat field, though it holds the wind gust. So both versions need one small statistic, or the shared input is a Python-side one such as the gust".

### ★C14 · partly
Read: `council/po-assistant.md:53` EX-13 "...(all as shown in the search result, 2026-11-09, pages not opened)". Fetched here: `https://docs.rs/crate/garjan/1.0.0/source/src/fire.rs`, through WebFetch's summarising model, so the page is second-hand: "//! Fire sound synthesis: crackle, roar, hiss.". The summary says the code makes roar (brown noise through a 600 Hz low-pass biquad, Q 0.7, scaled by `intensity * 0.3`), crackle (a Poisson count per 10 ms block, 5 + 30 x intensity events per second, decays over 5 to 30 samples, white noise through a 2000 Hz high-pass), a DC blocker, and that "The code has no separate hiss generator". The brief's recipe (noise bed, sparse decaying impulses, high-pass) has no roar and no low-pass. The roar is half of the source it cites. The Cornell, HAL and patent pages were not opened. The sentence "H for every parameter" can be narrowed: garjan's page gives parameters, though only as this one crate's choice. Sentence to change: "a noise bed, sparse decaying impulses and a high-pass" → "a low roar (low-passed noise), sparse decaying impulses through a high-pass, and a hiss that garjan's docs name and its code does not make". A 16 kHz sample rate has an 8 kHz band. Whether a fire's hiss fits it is —.

### ★C15 · holds
Read: `bench.md:699` ""iterate until realistic"" and "Seven sheets of Mac frames of the C kernel over the Runner's sky"; `:713` "the PO picked E, 2026-11-06: "still not great, but we can tune it later""; `docs/discovery/2026-11-06-p647-flame-motion/README.md:30-31` "Round 1 bent every column with one wave". Round 7 itself reads "Not yet measured on the board". That is a caveat on what "accepted" means here (part 2).

### ★C16 · partly
Read: `bench.md:303` "The PO saw the first fire and said it "looks a bit uniform" (#796)... hot spots at the base, a rising cooling map that cuts the flames into tongues, and a random sideways shift"; `:317` "a cooling map 256 x 32 that never repeats across the field (the three columns)"; `:713` "five versions A to E". "looks a bit uniform" is not "a repeat": the complaint was a sameness across the picture, and the fix is spatial. The word "repeat" comes in later and is spatial too. Reading it as a rejection of a temporal loop is the brief's own H, and N3 builds on it ("A fire from a table repeats, which the PO rejected first in pictures"). "A to E" is one case; USER-18's other picks are four curves, five layers and four columns. Sentence to change: "The PO rejected a repeat first ("looks a bit uniform") and picks from options shown on the Mac, A to E" → "The PO first called the fire "a bit uniform", a sameness across the picture, and picks from options shown on the Mac (round 7: A to E; other times four or five options)". N3's "which the PO rejected first in pictures" needs "H" added.

### ★C18 · holds
Read: `~/Development/spark/parts/max98357a-dfr0954.json` unsupported rates [11025, 12000, 22050, 24000], quoting "LRCLK ONLY supports 8kHz, 16kHz, 32kHz, 44.1kHz, 48kHz, 88.2kHz and 96kHz". A later copy than the record's 2014 mirror (`19-6779; Rev 7; 2/16`, community.nxp.com copy, read by pdftotext): "LRCLK ONLY supports 8kHz, 16kHz, 32kHz, 44.1kHz," "48kHz, 88.2kHz, and 96kHz frequencies. LRCLK clocks" "at 11.025kHz, 12kHz, 22.05kHz and 24kHz are NOT" "supported." ADI's own Rev 16 could not open (two fetch timeouts). The 2016 revision is newer than the mirror and says the same. The diff against Rev 16 stays open.

### ★C19 · partly
Read: `games/gdi.py:15-19` "DC = 3 ...", "RST = 38 ...", "CS = 18 ...", "SD_CS = 9 ...", "BL = 21 ..."; `games/pins.py:8-11` "TFT_CS = 11", "TFT_DC = 12", "TFT_RST = 13", "SD_CS = 14"; `~/Development/spark-walks/p581-sound-joystick/firmware/pins.py:13` "TFT_DC = 11", `:14-17` "I2S_BCLK = 12", "I2S_LRC = 13", "I2S_DIN = 14", "AUDIO_SHUTDOWN = 6". The correction holds: the amplifier pins are free in `gdi.py`, which the code runs. Narrowings:
1. The pointer `games/app.py:130` is in `open_st7789`, the fallback. Run130 ran `backend s3lcd` (`run130-p656-smoke.log:3`), and the running path is `games/lcd.py:201-204` ("bus = s3lcd.SPI_BUS(1, mosi=gdi.MOSI, sck=gdi.SCLK, dc=gdi.DC, cs=gdi.CS, pclk=spi_hz, swap_color_bytes=False)"). The claim is right and its pointer is the wrong branch.
2. "12, 13, 14 and 6 ... collide only with `pins.py`": 6 is in no line of `games/pins.py`. Only 12, 13 and 14 collide.
3. Those collisions are on paper: nothing reads `pins.TFT_*` or `pins.SD_CS` (grep over `games/` and `tools/` shows only `import pins` at `games/app.py:18` and `games/gdi.py:10`). What the running code reads from `pins.py` is SCLK, MOSI, MISO and the two onboard pins.
4. The risk the caveat leaves soft is a real one. Walk row 1 (`p581-rows.md:7`): "Unpinned, assign_pins put I2S_BCLK on GPIO18 and JOY_SW on GPIO9, the GDI's CS and SD_CS". Regeneration has already placed I2S on a pin `gdi.py` runs.
Module side: the shelf record `dfr0664-tft-2in.json` `gdi_used_signals` says FPC pins 11 to 18 "have no net on this module" (`verified: false`), so the GDI cable is not known to reach 12, 13, 14 or 6.
Sentence to change: "The walk's amplifier pins 12, 13, 14 and 6 are free in `gdi.py` and collide only with `pins.py`" → "The walk's amplifier pins 12, 13, 14 and 6 are free in `gdi.py`. 12, 13 and 14 clash only with names in `pins.py` that nothing reads, and 6 clashes with nothing. `games/lcd.py:201-204` is the running path."

## 2. Brief against its detail

### Caveats dropped
- **No observed problem** (RA-1, line 58). Absent from "What we found". See part 1, Check first. For an existing-product start this is the first thing the brief should say.
- **Road's 105 ms has a mechanism in the log** that no report read: see part 3, R1.
- **The evidence period.** ★C1 says "one smoke run". `games/app.py:30`: "FPS_EVERY_MS = 5000". Each `time` line is one 5 s window, with 1 or 2 per game: 23 windows, about 115 s in all. Road's two windows are 66 and 105 ms, and 23 and 20 fps.
- **Internal RAM** (FEAS-5, "internal DMA largest free block 31,744 B"), and the fact that the heat field lives there. The brief says nothing, and FEAS-5's own "one 1 KB audio descriptor chain fits (calculated: 4 descriptors x 256 frames x 4 B = 4 KB)" is self-contradictory (1 KB against 4 KB) and uses a stereo frame that ★C3 has now corrected. Not fixed anywhere.
- **"Two voices do not fit"** (FEAS-7: "a naive bytecode mixer at 16 kHz mono with one voice costs 6.4 ms of the 10.8 ms headroom; two voices do not fit"). The brief quietly swaps Stack's 10.8 ms (run52) for Fire's 17.6 ms (run130) and drops the conclusion. No sentence says the headroom source changed.
- **FEAS-7's 32 kHz cost** (12.8 ms at 10 µs). ★C18 says "16 or 32 kHz". Nothing tells the PO that 32 kHz halves the per-sample budget to 13.75 µs in Fire.
- **FEAS-13's flash stall:** "any filesystem write while sound plays risks a gap". Absent from P2.
- **FEAS-9's "no volume"** is wrong, and ★C2's narrower wording hides that the report is wrong (`I2S.shift`).
- **PHYS-13 clock-stop hazard** ("NEVER stop LRCLK while BCLK is running") is a safety item. It is in `risks-and-tests.md:13` and not in the brief's P1, Short version or hardware section. Note `machine_i2s.c:418-427` deinit. The hazard applies to the stock path too. Datasheet Rev 7 (`pdftotext` output, at the LRCLK section): "Do not remove LRCLK while BLCK is pres-".
- **PHYS-5** ("the speaker's rating is not reachable"): the 3 W, 8 ohm label cannot be driven by the amplifier at either rail. Not stated in C17 or C20.
- **EX-9** (a uasyncio I2S freeze report on an ESP32-S3, H) is absent. It bears on which `machine.I2S` mode A1 uses.
- **EX-9/EX-3 scheduler depth** ("queue is 8 deep on the ESP32") is absent from ★C7.
- **RA-3's test** had `gc.collect()` forced and a scope or recording. A1 dropped the forced collection, though it sets ★C1's headroom against gc.
- **RA-7's overlap:** #160 round 3 is the same work with a different Done-when. The brief does not name it; `items.md:63` only proposes a link.
- **RA-8's WIP question** (branch `p581-spark-walk`, finish before switching) is absent. The brief's D5 reuses the walk's amplifier, and the walk stays open.
- **★C15's** "accepted" has a condition: `bench.md:713` round 7 ends "Not yet measured on the board". An acceptance of a sheet, on a surface other than the board.
- **The open question "which S3 abilities are worth using for sound"** (Frame, line 21) has no Q, no option and no item. FEAS-6 and EX-10 mark most of it H, and the collection plan's row sits "before Q3's own-task option". The brief does not say this question stays unanswered, and items.md has no spike for it.
- **Mono channel test:** `risks-and-tests.md:50` "a listen with a mono signal on left only". Stock `format=MONO` sends both slots (`machine_i2s.c:372`, `i2s_ll.h:1091-1094`), so MONO cannot produce that signal, and R1's channel select does not change what stock mono plays. The row needs STEREO with one side silent, or goes away for the sound path. PHYS-11's "supports: the choice of MONO and the channel" is overtaken by the source.

### Claims stronger than the source
- **Short version:** "delays every new sound by up to about 168 ms": see ★C4 (Road 233 ms, and the figure is for a 40 ms frame only).
- **Frame D1:** "a driver repository beside it". Issue #997: "a new submodule, only if the discovery shows the need". D1's condition is dropped in the Frame line and returns only in P2 and Q3.
- **Frame Outcome:** "a game plays sound on the board". Issue #997: "The games play sound". Narrowed to one game, with no decision (D) on the narrowing.
- **D5:** "alright, lets go on with the sound project now", read as yes to Q0. Q0 is the frame, start, extensions, depth; D5 also takes the amplifier from p581. The quoted words confirm none of that. The session could not be opened, so this reading is unverifiable from the folder. Line 23 still says "proposed until Q0" although Q0 is "answered D5".
- **D4** ("the PO's OK on a proposal") is cited as a decision and has no line in `## Decisions`, and no quote.
- **N1** "the words the PO used". The issue says "some simple python version" and "a naive micropython implementation". Neither says live per-sample synthesis. That reading is the facilitator's, as the row's opinion field half admits.
- **N3** "the shape that does not underrun" (opinion, RA-4). Mixing two tables in plain Python is per-sample work too, unless a block primitive does it. RA-4 said "a Python mixer over precomputed sample tables, no live synthesis" and gave the test, not the claim. The row's cost ("tables in flash or PSRAM") omits the mix's CPU.
- **P1** "one cmake line": true only with a C fill. A Python fill needs no cmake line, and the option's name includes both.
- **O2** "proves: a real count": it counts 16 ms dry blocks and idle silence (★C6).
- **A1's pass line** "each game's `worst` within 5 ms and its fps equal to run130 (48, 57, 105 ms and 25, 24, 20)". Run130's own second windows differ more than that: Road 66 and 105, Cube 46 and 72, Starfire 69 and 48, GravityPong 66 and 43, Cave 79 and 54. Fps moves by 1 to 3 within one game. A 5-minute maximum against a 5 to 10 s maximum is not the same statistic. The line fails on noise.
- **A1's method** "Write a 440 Hz table ... once per frame": a frame at 20 fps needs 800 samples, not 640. The text does not say the write follows elapsed time. A fixed-length write would underrun by design in Road.
- **A3's pass line** "median delay under 130 ms" against the depth A1 demands: at a kept-full 128 ms buffer the median is about 112 to 128 ms of buffer plus a mean 20 ms poll wait, so 132 to 148 ms. A1 and A3 are nearly unsatisfiable together, and neither row says so.
- **`items.md:9`** "The games stall for 40 to 105 ms": 40 to 105 ms is the span of each game's worst single gap, not a stall the games do.
- **★C14, ★C8 tagged E.** Both rest on search-result summaries, and the source report says "pages not opened". `story-map.md:25` tags slice 5 "E ★C14, ★C15, ★C16", though ★C14 is summary-only and ★C16's reading is H.
- **"H for every parameter" (★C14) and "Faust... —"** (★C9) are fine. The "Fire sound is known as a recipe" lead is stronger than one crate's code and one search.
- **★C13's "both versions need"** is flagged H and still stated as the conclusion in Q5 and A6.
- **[C23]** pointer `MPY/ports/esp32/machine_i2s.c:356` is `} else { // rx`. FEAS-15's "line 356" refers to `extmod/machine_i2s.c:356` (`MP_QSTR_ibuf`), and `sd=` is `extmod/machine_i2s.c:348`. Wrong file in the brief.
- **Jobs and journeys, journey step 3** repeats 104 to 168 ms with no Road case. The same fix as ★C4 applies.

## 3. Rival explanations

- **R1. Road's 105 ms is not a stall during play.** It is a state-change frame. `games/app.py:93-96` runs a collection when the game's state changes ("# the title and the game over are quiet: collect there"), and `:74-75` "Called at quiet moments, so a pause lands where nobody is playing". The `slowest` numbers are computed at `:101-102`, before the periodic collection at `:103`, so a nonzero `gc` in the `slowest` breakdown can only be that state-change collection. The four worst frames with a gc figure are exactly that: Road `gc 11` (`:170`, phases `over 20`, `:171`), Cave `gc 10` (`:131`, `over 25`, `:132`), Cube `gc 10` (`:204`, `over 23`, `:205`), Flappy `gc 10` (`:78`, `over 19`, `:79`). In those windows the worst gap is the title or game-over transition, not gameplay. The windows without one top out at 69 ms (Starfire, `:182`), so 5 blocks (2560 B, 80 ms, calculated) would cover the play, against 128 ms for the game-over frame. A hit's delay then is 40 + 80 = 120 ms, not 168. Whether the game-over frame needs covering at all is the PO's question: it is the moment a crash sound plays. Not ruled out. The folder has not read the `slowest` breakdown.
- **R2. The buffer-versus-delay trade is specific to P1.** ★C4 reads as a law. An own ring that keeps audio ahead and re-mixes a new sound close to the read head hides stalls and adds little delay, as ★C4's P2 option could. The folder does not raise it.
- **R3. The perceived delay limit is not 20 to 30 ms.** RA-5's figure is model knowledge. Broadcast tolerances for late audio are wider than that (I recall ITU-R BT.1359 as about 125 ms late detectable; H, not opened here). Late audio can be the lesser fault against the picture. A hit's delay is also measured against a picture that itself arrives a frame later.
- **R4. Per-sample Python cost is decided by what the loop body is, not by a global cost.** ★C5 treats one figure as the cost. Integer-only loops on `array('h')` (FEAS-8) are a different cost from float statements. Only A2's probe settles it, and the probe's own loop body (noise plus decay) can be a worse case than a phase-accumulator table lookup. Neither A2 nor N1 fixes the body.
- **R5. "Python's GC is the problem" is the wrong culprit.** ★C7 and P2 target GC. Run130's slowest frames are `paint` 34 to 68 ms and `send` 20 to 26 ms, not GC. Road's paint averages 34.4 to 38.5 ms. A C task on core 0 fixes refill only if the stall is what starves it. The fix might be a slower-frame-tolerant fill, or lower paint cost.
- **R6. The riskiest assumption is not A1.** A1 is proposed by RA-3 and the facilitator, with A4 named as rival. Unrun: nothing in the folder has ever made sound on this board. A8, A9 (wiring, level, brown-out) and the pin question (the collection plan's "before A1" rows) are gating, so A1 cannot run until they pass. If the amplifier or its wiring fails, A1's test returns nothing about stock I2S. Equally, RA-1 says the value is a wish: the riskiest could be that the PO does not want sound enough to pay the 3 days and the frame cost once they hear it. The brief puts the ear as rival and leaves that out.
- **R7. Internal-RAM contention, not stock I2S, can fail A1.** Part 1's check. If the field falls to PSRAM, A1's frame-time line fails with the blame on stock I2S.
- **R8. The Fire-first interest comes from Fire being tuned, not sound.** ★C15 and ★C16 infer the PO's ear from their eye. Rival: the PO's seven rounds on the Runner fire reflect a hard visual effect in one card (P651), and "still not great, but we can tune it later" reflects a session's end, so the rounds predict nothing about sound. The folder names Q-U4 and Q-U5 but treats the seven rounds as a predictor.
- **R9. "Naive" means something simpler than N1.** The PO's words "some simple python version" and "naive micropython implementation" can mean Python driving `machine.I2S` with a table. The brief's ordering of N1 as "the words the PO used" pre-commits Q2's reading.
- **R10. A count of dry blocks is not gaps heard.** ★C6's unknown: a partly filled last block plays as a short run of zeros, heard as a click with no event. And an event per 16 ms block overcounts one gap as several. The outcome line's "underruns per minute (an underrun is a gap in the sound)" hides both.
- **R11. 16 kHz is not a free choice for fire.** The brief picks 16 kHz for CPU. Fire's hiss can be above an 8 kHz band. If realistic fire needs 32 kHz, N1 doubles to 12.8 ms and the per-sample budget halves.

## 4. Numbers without unit, population, period or provenance

- **40 to 105 ms worst gap (★C1, A1, `items.md:9`):** per-game maxima over 5 to 10 s, and A1 calls them "the games' worst frames". Period missing. Unit present.
- **Fps 20 to 25:** mean per 5 s window, in one run, in 14 games. The period is not in the brief.
- **17.6 ms and 27.5 µs per sample (★C5):** Fire, mean of one 5 s window (`:12`). The brief writes "the means of one run". Population (Fire only) missing from the budget sentence.
- **1.28 ms and 6.4 ms:** 2 µs per sample is a guess with no source; 10 µs is derived from a float-statement cost and the statement count is an estimate. Provenance of the derivation is in FEAS-7, not the brief.
- **57 µs per particle, about 80 µs per canvas call (★C5):** no run or image is named in the brief. 56.8 µs is run46 per TL-8. "Measured on other code" does not say which build or body. 80 µs traces to the engine council's PO-11, not re-read here.
- **162.5 µs (★C12, `bench.md:244`):** 16 events, one row, no run name in the row. The cost of each sound call per event is not included.
- **40 ms poll (★C4):** a target, not the frame in Road.
- **104 ms, 168 ms:** calculated with the 40 ms target. Whether it is the mean or the maximum hit delay is not stated ("up to" says maximum, but it is not the maximum in Road).
- **64 ms and 128 ms:** capacity at 16 kHz, 256 frames per block, and not coverage.
- **A1's 5 ms and 5 minutes; A2's 10 ms; A3's 130 ms; A5's caps 4 and 8; A6's 0.5 ms and 2 ms; A7's "a third":** proposed pass lines with no stated basis. "Proposed" is their only provenance.
- **A9's 10 minutes, A3's 20 hits:** no basis stated.
- **3 working days (D4):** date only, no quote and no Decisions entry.
- **"0.58 A" in `risks-and-tests.md:14` and `:68`:** carries the efficiency guess 0.8 and WiFi-on peak 0.355 A, though WiFi is off in the games. Noted there and not in the brief's hardware line.
- **★C15's seven rounds and three rounds:** counts of Mac sheets in one effect each (P651 and P647). Neither is board rounds.
- **"The drawer holds 2 ... 2":** count unit present, date of the drawer read not stated.
- **4 (TIC-80, PICO-8) and 12 (synthio) voices:** H, model knowledge, with no version or page.
- **16 kHz:** chosen, with no source for why not 32 kHz other than CPU. The sound-quality cost is not stated anywhere.

## Searches

1. `AMY audio synthesizer library C MicroPython ESP32-S3 Tulip user module` (web, for ★C8) · used: found AMY and Tulip. The claim-level reading was done on GitHub (AMY README, tulipcc tree, `esp32_common.cmake`, `modtulip.c`).
2. `Andy Farnell procedural fire sound hissing crackling lapping synthesis Designing Sound` (web, for ★C14) · nothing usable: book listings only, no fire chapter text.
3. `MAX98357A datasheet LRCLK "only supports" 8kHz 16kHz 32kHz 44.1kHz 48kHz 88.2kHz 96kHz 22.05kHz not supported` (web, for ★C18) · the summary misread and gave a continuous-range answer. Its link to a datasheet copy was used instead (the NXP-hosted PDF, Rev 7 2/16, read with `pdftotext`).

Fetches, not searches: `docs.rs` garjan `fire.rs` (read through a summarising model); `analog.com` MAX98357A datasheet (two timeouts: could not open); `community.nxp.com` datasheet copy (fetched, then `pdftotext`).

## Second pass

Read 2026-11-09 (Europe/Prague), changed sections only, against the working tree at 518b6af. Paths as in the first pass. Nothing was run on a board. `B:n` is a line of `brief.md`, `RT:n` of `risks-and-tests.md`, `OB:n` of `observations.md`.

Could not open:
- **The PO's words for D8 to D15.** The folder keeps words only for D5, D6, D7 and D16. D8 to D15 say "answer to Q<n>" and hold no quote, and the subjects of commits 8a86961, 8565c9a and 518b6af hold none either. So those eight are compared with the option text they answer, and not with what the PO said. `OB:30` already says "a D needs the decider's words on that point".
- **The PO's photos** (D7, ★C26, C30). They are not in the folder.
- **Issue 997.** It was not opened in this pass, so "issue 997's words" (B:19) rests on the first pass's quote.
- **The s3lcd driver's source.** Not read, so whether it claims a pin beyond the arguments at `games/lcd.py:203-204` is —.

### 2

**Decisions written more strongly or more broadly than the record**

- **D6 (B:140).** The words are "we can add it later. the idea with the testing machine is good, I like it, we can try that too." D6 writes "a test instrument in this epic that lets the board hear its own speaker and report gaps". "In this epic", "the board", "its own speaker" and "report gaps" are not in the words, and "we can try that too" is a try. `OB:34` records it more weakly: "the test instrument is worth a try". The Scope line (B:22) lists it as in.
- **D7 (B:141).** The words are "Here's the picture of the modules I want to use". The list is the facilitator's reading of a picture and not the PO's naming. "The MAX98357 amplifier module" and "the enclosed speaker" are then treated as the drawer's DFR0954 and FIT0502 (★C17, B:75; `story-map.md:20`; the rail at RT:21; A8). No line in the folder compares the photographed amplifier or speaker with those records. C30 shows that this same step failed for the microphone, and `OB:45` draws the rule: "a drawer match by function is not an identity". The rule is not applied to the other two parts.
- **D8 (B:142) and Stands on (B:11).** D8 says that importance "does not rank them". The top line turns the same answer into "10 of which would change the decision". A rating of high is not a statement that the result would change the decision.
- **D9 (B:143).** It says "as proposed", and its text differs from the proposal (B:117, RT:32).
  - "No gaps at all" replaces "0 gaps in the recording". The instrument is gone, and with it "A recording cannot show a very short gap".
  - The clause "no refill later than the buffered time in the log" is gone.
  - "This answers Q7: the buffer covers the state-change frames" is a second decision placed inside the answer to Q1. Q7 is a choice between 4096 B and 2560 B and between a delay of 168 ms and 120 ms (B:131). The record does not show that this trade was put to the PO, and "at most 4096 B" does not choose either depth.
  - "Covers" is stronger than ★C3's "about 104 to 128 ms (calculated, not run)", and Road's 105 ms sits inside that range.
  - The record does not show whether the PO saw the refuter's noise reading before confirming.
- **D10 (B:144).** "If A2 fails, N3 replaces it" is the facilitator's opinion at Q2 (B:126), with no words recorded. A2 has two lines: pass under 10 ms, and change over 17.6 ms (RT:33). A result between 10 and 17.6 ms is neither, so "fails" is undefined. Q6 "unblocks: Q2 and A2" stays queued (B:130) while Q2 reads answered.
- **D11 (B:145).**
  - "A driver repository exists only if the A1 test fails" is narrower than D1's "only if the discovery shows the need" (B:20). It copies the facilitator's opinion at Q3 (B:127) into the decision. A need shown any other way is shut out, for example A3's delay (RT:34: "Q3 moves to a shorter buffer or the own task").
  - "AMY is the first candidate to start from" drops Q3's "its fit is not built".
  - P4 is a synth core with AMY's own I2S tasks in a user C module (B:98). The driver repository belongs to P2 (B:96). D11 joins them, and the failure branch of A1 still says "Q3 moves to the own task" (RT:32) and does not name AMY.
- **D12 (B:146).** O4 holds the microphone count and a latency column (B:104). "One listening verdict per version" comes from O2 (B:102). The decision is a merge that the option list did not offer, with no words kept. O4's caveats are dropped from D12 and from the Outcome line (B:19): "nobody ran it", "The shortest gap it can show is —", "the reading costs the run it measures".
- **D13 (B:147).** "A layer for physics events can sit on top later" is not in option A (B:107). Option A's caveat "fire is not a sample, so it needs `set` parameters" is dropped.
- **D14 (B:148).** "The ball pit test" is not defined as Mac or board. A5 (RT:36) still tests "a cap of 4 and of 8" on a Mac render, so V2 and V3 are not in the test that D14 names. Q5's status names only D13 (B:129).
- **D15 (B:149).** It allocates two rounds and does not show that they fit. ★C15's "Whether 3 days (D4) cover the rounds a sound needs is —" stands. D4 has no quote and predates the microphone in Scope, and no D re-confirms the 3 days with it (`OB:31`).
- **D16 (B:150).** Q8 asks whether an earlier sentence confirmed the frame and the reuse, with the options "yes, or restate the frame" (B:132). D16 writes "the frame with the changes of today", and its options are "yes to both, another amplifier, change the frame". "The changes of today" is not in Q8, and the option sets differ, so "Yes to both" cannot be tied to one text. D16 does not touch RA-8's open question on work in progress, or C29's walk.
- **Ready for (B:10).** The comment at B:4-6 defines "an experiment" as "the decider chose a test (a D)". D9 records a pass line. No D records choosing to run A1 next, and the top line stands on D9 for that. Four "before A1" rows stay open (RT:47-49, RT:51), and the microphone's identity is the open "Decision needed" (B:12).

**Places that still treat the microphone as a SEN0526 or as unsettled, against C30**

C30 (B:82) says "is not a SEN0526". ★C26 (B:80) says "not proven", and the two stand side by side with no line that reconciles them.
- B:14, B:104 and B:117 carry "★C26 (not proven)".
- B:80 opens the microphone's claim with "The drawer holds 3 SEN0526 modules".
- RT:18 "H ★C26: the microphone (D6)". RT:32 "Proposal (D6, ★C26)".
- RT:21 "the SEN0526's "DC 3.3V" applies only if it is that module (★C26)" and "the microphone's range is — (★C26)". The rail stays open on a condition that C30 says is false.
- RT:51 "Which microphone is it? ... SEN0526's page reads 3V3, GND, SCK, SEL, WS, DO (★C26)".
- `story-map.md:23` "H ★C26".
- `verification.md:26` keeps "not proven", with no row for C30.
- `OB:35` still reads "The identity stays unproven".
- C30 has no star although Decision needed (B:12) rests on it, and B:41-42 says that ★ marks such a claim.
- "C30" is used twice (B:82, B:155) for two different claims.
- `items.md` does not name the microphone at all, though D6 and D12 put it in scope. The probe item (`items.md:9-14`) lists no microphone wiring and no identification step, and its proof is "the gap count".

**Caveats dropped, and claims stronger than their source**

- **D12 is written as still open.** B:14 says "proposes", B:117 "Proposal, not decided (D6)", RT:32 "Proposal", and `story-map.md:23` "Proposal (D6, Q4's O4)". B:117 also ends "The PO sets it at Q1", and RT:32 says "proposed", after D9.
- **The instrument of A1 is contradictory.** D12 says gaps are counted with the microphone, and the pass line (B:117) says "0 gaps in the recording", a phone. `story-map.md:23` puts the microphone at slice 3, and `story-map.md:16` puts A1 before slice 0.
- **The Outcome's count works only on a tone.** B:19 gives "gaps per minute" from the microphone for "one row per sound version". The method is described only for a known tone (B:117, RT:18 "a known tone"). Nothing says how a gap is told from an intended silence in a version's real sound. The row's population is missing.
- **O4 "proves: a count of gaps in the sound itself, the source ★C6 (dry blocks) says the stock class lacks" (B:104).** ★C6 is about dry blocks. A heard gap is another quantity, and "proves" sits beside "nobody ran it".
- **A1's frame-time line and the microphone.** O4 says the reading costs the run it measures. D9's "within 5 ms" and "same fps" are read against a run130 that had no RX channel. Whether the 5 minutes run with the microphone on is —.
- **D9 is not tested by its own test.** "The buffer covers the state-change frames", and the test text does not require a state change in the 5 minutes. Road's 105 ms window holds one (R1).
- **The first pass's statistic point is half kept.** B:117 keeps "Road 66 and 105, Cave 79 and 54". It drops "A 5-minute maximum against a 5 to 10 s maximum is not the same statistic" and the fps spread of 1 to 3 within one game.
- **D9 makes A1 and A3 pull harder.** At a kept-full 128 ms the median is about 132 to 148 ms against A3's under 130 ms (RT:34). This is in RT:34 and is not in D9, Ready for or the Short version.
- **D10 and D13 do not meet.** D13 picks `Mixer` with `play(sample_id, volume)` (B:107). D10 picks N1, one voice of live synthesis (B:90), with no sample to play and nothing to mix. N3's caveat "it compares a mixer and not a generator" (B:92) applies here, and it is not raised.
- **Pin list sources (RT:21).**
  - "Source the board record's `pins`" for the microphone: that record maps pads to GPIOs and proposes nothing, so no source chose GPIO7, 8 and 4.
  - "Free because they are in no line above" means free in the code. See Pin list.
  - The rail is sourced from `parts/max98357a-dfr0954.json`, which assumes the photographed module is a DFR0954.
- **★C25 (B:79).** It is tagged E with a datasheet read "(Espressif document search)", and `verification.md:25` says "one query". ★C14's caveat holds that "Search results are not read pages". `soc_caps.h:228` "#define SOC_I2S_NUM (2U)" is read here, and the file has no DAC line, so the local half stands. The datasheet quote is second-hand.
- **P4 "with no 16 kHz rate" (B:98).** `src/amy.h:102-108` is a `#define` in a preprocessor branch ("#ifdef AMY_DAISY", "#elif defined __EMSCRIPTEN__", "#else", "#define AMY_SAMPLE_RATE 44100"). It has no 16 kHz branch. Whether the value can be changed and still build and sound right is —. "No 16 kHz rate" reads as an impossibility.
- **★C8 and D11.** "The nearest project found" rests on two searches, and RT:53 says "a smaller one is not" read. "First candidate" is first of one read.
- **C27 (B:49).** It drops RA-1's limit "supports only: that the order is a choice". C27 says "the value is".
- **C30's sources.** "Read 2026-11-09" does not say how the page's board photo was read. ★C26 says its page came "through a summarising fetch", and `OB:45` says "correction agent, then this session".
- **Stale beside the new top lines.** B:23 "proposed". Hand-off (B:165) "not yet: the importance of each assumption and the riskiest test's pass line (Q1) ... a direction (Q2 to Q5)". `story-map.md:16` and `items.md:7` "wait on Q2 to Q5". `items.md:13,35` "depends on: Q1". B:19 has a broken sentence at "DFR0975 D12 changes".

### 3

- **R12. "The testing machine" (D6) can be a separate rig.** The folder records the PO's idea as "a microphone and a camera as test instruments on the bench" (`OB:37`, card P731, B:155). That reading puts the listener outside the game board. D6 and O4 put it on the board's second controller. D12's "answer to Q4" settles O4 only if O4's text was what the PO read, and no words are kept.
- **R13. The microphone can fail with the thing it measures.** It is on the same board and read by the same loop. A Python stall that starves TX also delays the RX read, so an RX overflow drops samples just when the gap happens, and the instrument then shows a jump or nothing. A gap can be hidden, and a clean tone can show a false gap. The folder names the cost ("the reading costs the run it measures") and not this common cause.
- **R14. Gap detection is per-sample work.** At 16 kHz, 640 samples per frame must be looked at somewhere. In Python that is the per-sample cost ★C5 and Q6 call unmeasured, so the instrument may cost as much as N1. Logging raw to analyse on the Mac is 16,000 x 2 x 300 = 9,600,000 B per 5-minute game (calculated, 16-bit mono), more than the board's 8 MB PSRAM, and FEAS-13 says "any filesystem write while sound plays risks a gap".
- **R15. A1 failing does not show that stock is not enough.** RT:32 and D11 read a failure as a need for an own task or a repository. Rivals the folder does not rule out: the pass line fails on noise (first pass, B:117), internal RAM moves Fire's field (★C28), the microphone's own cost (O4), a wiring or brown-out fault (R6). With D11, a noise failure of the 5 ms line would open a driver repository. No line separates the sound clause of the pass line from the frame clause for that branch.
- **R16. The riskiest assumption may now be the instrument.** D12 hangs the gap count on an unidentified part with no rail, no L/R level, no threshold and no shortest detectable gap (B:80, B:82, RT:21, B:104), and nobody ran it. The Riskiest line (B:116) still names A1 and A4, A8 and A9. No assumption row covers the microphone at all, and RT:18 only names a threshold.
- **R17. D9 "answers Q7" can be a yes to the numbers shown.** The PO confirmed a pass line under Q1. The rival reading is that the PO did not weigh state-change frames, and the sentence that says so is the recorder's.
- **R18. D8's ten highs can mean "I won't rank these".** The folder uses it as ten assumptions that each change the decision. It gives no ranking, and Riskiest (B:116) is still "proposed".
- **R19. AMY is first because it is the only one read.** ★C8 is one search. CircuitPython's mixer and "a smaller one" stay unread (RT:53). A smaller core or a plain own mixer in `core/` (★C11) is not ruled out as the better base, and AMY's 44.1 or 48 kHz stereo fill does not match the 16 kHz mono that D9 tests.
- **R20. The round module "came from another seller" (C30).** The rival is that the "order history" is only DFRobot's. The spark drawer's import is described as "your DFRobot order history", and the claim names no population. The history can then say nothing about other sellers or about a gift. The pad set SD, VDD, GND, L/R, WS and SCK is also that of the common round INMP441 breakout (H, model knowledge, not opened). The folder's "—" on the chip can be closed by one look at the part and has not been.
- **R21. The amplifier and speaker in the photos may not be the drawer's parts.** See D7 above. If the module is another MAX98357A board, R1, the rail and the pad names at RT:21 and C20 all move.
- **R22. "Stock class fits two controllers" (★C25, RT:21) is read from source only.** Two `machine.I2S` objects beside s3lcd and the game loop were not run, and the second one's interrupts and DMA share the pool ★C28 names. A failure at the second object would be blamed on A1.

### 4

- **Stands on "10 H, 10" (B:11):** no noun. Several rows carry E (RT:32, 35, 36), so "H" is not their tag. The count comes from a tool.
- **Outcome (B:19):**
  - "CPU time per frame (ms)" has no statistic, game or event script.
  - "Underruns per minute" has no run length.
  - "Heap (kB)" names no pool, and ★C28 shows that internal RAM is the scarce one.
  - "One row per sound version" against three games in A1.
- **D9, and B:117:**
  - "Within 5 ms" of which window. The list uses Road's 105 ms, and the other window is 66 ms.
  - "Same fps" has no tolerance and no direction, and Road's 20 is the state-change window (the other reads 23).
  - "No gaps at all" has no shortest gap and no instrument.
  - "The buffered time" is 128 ms of capacity or 104 to 128 ms of coverage.
  - "At most 4096 B" against RT:32's fail line "at 4096 B".
- **D12:** "The gap threshold is —" has no unit named. "Delay column in ms" has no statistic (A3 uses a median over 20 hits) and no instrument. "One listening verdict" has no listener, level or length.
- **D15:** "two listening rounds" has no duration. A4 implies five wav files.
- **D4 and the 3 working days:** no scope after the microphone was added, and no quote.
- **A2:** "under 10 ms" and "over 17.6 ms" leave 10 to 17.6 ms unassigned, and 17.6 ms is Fire only. BallPit is slice 0's game, and its free time is not stated: 22.1 ms from `run130-p656-smoke.log:25` (40 − 2.4 − 7.3 − 5.2 − 3.0, calculated).
- **★C24 and P4:** "21 `src/*.c` files", "250 oscillators and 64 voices", "6 DMA blocks" are at `main` on one date, and the commit is not recorded. "Stacks of 12 and 16 KiB" does not say which task has which. "5 names tried" does not list them in the brief.
- **★C28:** 31,744 B is one run, at start of one game, and "leaves 4,352 B" holds only if the figure was taken before the field was made. The log order (`:7` then `:8`) suggests it and does not state it. The share of a microphone channel is unquantified.
- **C30, ★C26:** "3 SEN0526" and "no other microphone" have no drawer read date and no population for "the order history".
- **Q7:** 168 ms and 120 ms are for a 40 ms frame only. The buffer the question decides is forced by Road, whose worst frame is 105 ms.
- **The pin list's "not wired or run":** it has a date and no bench state. The board revision is still — (RT:47).

### Pin list

**Answer: no collision with the running code, and no restriction in the board record for digital use.** Two limits on that answer follow the table.

`~/.local/share/spark/boards/34-85-18-42-e4-10.json` is the record of this board, and it holds only `deploys` and line 101 `"board": "firebeetle2-esp32s3"`. It has no pin data. The other two files there printed no FireBeetle match in a grep and were not read further. The restrictions were read in `~/Development/spark/boards/firebeetle2-esp32s3.json` (`BR` below), which that line names.

`games/gdi.py` and `games/buttons.py` were read whole. In `games/lcd.py` a grep for `gdi\.|Pin\(|ADC|machine\.` printed only lines 201 to 204, and all four use names from `gdi`, not numbers. A grep over `games/*.py` for `PWM(`, `UART(`, `SDCard`, `Signal(`, `TouchPad`, `DAC(`, `ADC(` and `SoftSPI` printed nothing. So the code that runs uses:
- `gdi.py:12-14` "SCLK = pins.SCLK  # 17", "MOSI = pins.MOSI  # 15", "MISO = pins.MISO  # 16"
- `gdi.py:15-19` "DC = 3", "RST = 38", "CS = 18", "SD_CS = 9", "BL = 21"
- `buttons.py:13` "BOOT_BUTTON = 0"
- `pins.py:14` "ONBOARD_BUTTON = 47"

None of the seven proposed pins is in those lines.

| pin | proposed role | line in the running code | pad, `BR` `pins` | `BR` `pin_roles` | DFRobot wiki GDI table |
| --- | --- | --- | --- | --- | --- |
| GPIO12 | amplifier BCLK | none. Named only at `games/pins.py:9` "TFT_DC = 12", which nothing reads (first pass, ★C19) | `"D12": 12` | `adc2_unusable_with_wifi`: ADC only | "\| TCS   \| 12/D12  \| Touch chip select  \|" |
| GPIO13 | amplifier LRC | none. `games/pins.py:10` "TFT_RST = 13", unread | `"D11": 13` | `adc2_unusable_with_wifi`: ADC only | "\| INT   \| 13/D11  \| INT  \|" |
| GPIO14 | amplifier DIN | none. `games/pins.py:11` "SD_CS = 14", unread | `"D10": 14` | `adc2_unusable_with_wifi`: ADC only | no row with 14. "\| BUSY \| 4/D10 \| Tearproof pins  \|" names pad D10, which `BR` says is GPIO14 |
| GPIO6 | amplifier SD | none, and no line in `games/pins.py` | `"A2": 6` | in no entry | no row |
| GPIO7 | microphone SCK | none, and no line in `games/pins.py` | `"D5": 7` | in no entry | "\| FCS \|  7/D6 \| Font library chip select   \|" |
| GPIO8 | microphone WS | none, and no line in `games/pins.py` | `"A3": 8` | in no entry | no row |
| GPIO4 | microphone SD | none, and no line in `games/pins.py` | `"A0": 4` | in no entry | "\| BUSY \| 4/D10 \| Tearproof pins  \|" |

`pin_roles` was read whole: strapping 0 and 3, `adc2_unusable_with_wifi` 11 to 20, onboard_led 21, onboard_button 47, not_wake_capable 38, 43, 44 and 47, console_uart 43 and 44, spi 15, 16, 17 and 10, i2c 1 and 2. Its note on the ADC2 list reads "on ADC2, which shares hardware with the radio", so it does not restrict a digital signal.

Limits on the answer:
1. **RT:21 says the other eight GDI lines "have no GPIO in the record: —". DFRobot's wiki gives them** (wiki.dfrobot.com/SKU_DFR0975_FireBeetle_2_Board_ESP32_S3, read by grep over the page text, 2026-11-09). By that table GPIO12, 13, 7 and 4 run to the GDI connector as TCS, INT, FCS and BUSY. The page is not consistent with `BR`: "7/D6" while `BR` has `"D5": 7` and `"D6": 18`, and "4/D10" while `BR` has `"D10": 14`. If the BUSY line is D10 and not GPIO4, then GPIO14 is on it, and that pin is in the proposal too. `~/.local/share/spark/shelf/dfr0664-tft-2in.json` says of the module's FPC pins 11 to 18: "FCS, TCS, SCL, SDA, INT, BUSY/TE, GPIO1, GPIO2 (11-18) have no net on this module", with `"verified": false`, and of the GPIO map "the wiki's GDI table disagrees on FCS/BUSY labels, so confirm on the bench by running the library's test". So this is not a collision on this display, if that unverified line is right. It is a shared line on the board and it is not in the brief. Which schematic revision matches the PO's board is — (RT:47).
2. **Regeneration and the walk.** The list is safe only while `gdi.py` stays the map. `games/pins.py:9-11` names 12, 13 and 14 for the display, and `games/pins.py:2` says "Regenerate it; do not edit it". The walk that shares this amplifier (D16) uses GPIO7 for another part: `~/Development/spark-walks/p581-sound-joystick/firmware/pins.py` "JOY_SW = 7". That only matters if the walk's wiring stays on the board. C29 says the walk stays open.

Walk lines read for the amplifier pins: "I2S_BCLK = 12", "I2S_LRC = 13", "I2S_DIN = 14", "AUDIO_SHUTDOWN = 6". The microphone's three pins have no such source line.

### Searches

None. Fetches, not searches: `curl` of `shorepine/amy` `src/amy.h` and `src/i2s.c` at `main`, and of the DFRobot DFR0975 wiki page, each read through `grep`.
