# P831: the next engine capability, the options

Card: P831 (spark #1192), under P652 (#875). Written on 2026-11-16. Three notes beside this page hold the detail and
the sources. They are [espnow.md](espnow.md) (in depth), [synth.md](synth.md) and [camera.md](camera.md) (preliminary).
Nothing ran on a board for this page.

> TL;DR: Start with the joystick, then ESP-NOW. Both feed one new engine part, an input layer that turns any control
> into the actions a game reads. A remote board then works in every game with no change to the game. The synthesizer
> comes third, and the camera comes last because it needs a new firmware and takes the joystick's pins.

The PO asked what each new capability means for the box. The PO then picks what the engine gets first and how it
serves the games, as multiplayer does. The five options differ most in two costs: a firmware rebuild and a clash of pins.
The joystick and ESP-NOW need neither, and the box's firmware already has `espnow`. The synthesizer needs a new C part
in the firmware. The camera needs a firmware rebuild and five of the box's pins.

## The PO's words

- 2026-11-16: "I think we should probably now test some adding hardware, the joystick for example. Or some other
  effects in C, or even best would be experimenting with using esp-now for two board communication. What would it
  meana ctually, can you analyze and present how it would have to be done?"
- 2026-11-16, later: "Or another idea is a synthesizer, like a one handed musical instrument using the esp's built in
  optimized effects library for dsp or so, and tyet another would be to capture image using a camera, some edge si
  implementation, maybe some edge model from hugging face, etc. These you can also do some preliminary analysis, just
  to se what it would mean and then we can decide what we want to do to add more capabilities to the engine, so we
  could then generalize it for the games, like the multiplayer"

## The five options side by side

| Option | What the engine gets | New firmware? | Hardware | First step, and what it measures | Main risk |
|---|---|---|---|---|---|
| Joystick | A direction and a strength, not only one button | No | In the drawer, with its pads A0, A1 and D5 set aside | A stick class: two ADC reads a frame, a dead zone, its button | Each game that uses it is its own feel slice |
| ESP-NOW | Two boards that talk: a remote control, then two-player games | No (`espnow` is in the build) | The free LilyGO T-Display as the second board | A 60 s ping-pong at 25 Hz: loss, round trip, the cost of a send and a poll | Internal RAM: the display's DMA buffer and Wi-Fi share it |
| Effects in C | One more visual effect in the pixel engine | Yes, per effect | None | One `fx_<name>.c` with its Mac tests, a build and a flash | The rebuild and the flash each time |
| Synthesizer | A playable voice: oscillator, envelope, filter, echo | Yes (a C voice; esp-dsp optional) | The joystick; the speaker is there | A C voice per 256-sample block: microseconds per block, press-to-sound delay | esp-dsp has filters and FFT, not a synth, so the voice is ours |
| Camera and edge AI | A camera image, motion, later a face or a person | Yes (a camera driver, later an inference engine) | The OV2640 on the FireBeetle 2 (check which boards have it fitted) | Grey frames beside a game; a frame difference moves a paddle | Its connector uses GPIO 4, 5 and 7 (the joystick), GPIO 6 (the amplifier) and GPIO 8 (the microphone) |

## What generalizes for the games

The games read one button today. The joystick, a remote board and a camera paddle are all new ways to make the same
few actions: press, hold, a direction, a strength. One small engine part can carry all of them: an input layer, where
each source (the BOOT button, the stick, the link to a second board, the camera) feeds the actions that a game reads.
Its industry name is an action map (Unity's Input System, "Actions", https://docs.unity3d.com/Packages/com.unity.inputsystem@1.7/manual/Actions.html).
With it, a game written for one button plays from the remote board at once, which is espnow.md's step 3.

Two-player games need one more part: the box decides the game state and sends it to the other board (a
host-authoritative model, Gaffer On Games, cited in espnow.md section 3). The synthesizer adds a second shared part, a
C voice that the games can also use for their sounds. The camera adds a background task whose newest result a game
reads, the same shape as the link to a second board.

## The order recommended

1. **The joystick:** cheapest and surest, and the synthesizer and a remote board both want it.
2. **ESP-NOW, step 1 (the ping-pong)**, then the input layer with a remote button (a feel slice).
3. **The synthesizer:** a C voice first, esp-dsp's filter after.
4. **More effects in C:** when a game needs one.
5. **The camera:** last, after a firmware rebuild plan that frees its pins from the joystick.

## Open decisions for the PO

1. Which capability goes first? Recommended: the joystick, then ESP-NOW.
2. May the T-Display be erased and flashed with MicroPython 1.29.0? The erase removes its factory demo for good.
   Recommended: yes, when ESP-NOW starts, because it is the only free board with a screen.
3. Does the camera stay on the list, given that it takes the joystick's pins? Recommended: yes, but last. A camera
   box can be a second board without the joystick.
4. The other open questions are in each note's last section, each with a recommended answer.
