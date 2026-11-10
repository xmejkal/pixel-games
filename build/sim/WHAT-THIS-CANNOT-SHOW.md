# What this simulation cannot show

Generated beside the diagram by spark. Most lines come from a part record's own words, or from
the board's Wokwi definition: the JSON file of the Wokwi part type that spark keeps in its store.
The rest say what spark did not check or leaves out of the diagram.
A scenario passing over any of these proves what the FIRMWARE did, and nothing about
the hardware the stand-in replaced or the board's part that Wokwi lacks.

- **Cjmcu111RotaryEncoder** — Wokwi's KY-040: it adds an SW pin this board does not bring out, and its CLK and DT carry pull-ups to VCC that this board may not have. A pass here does not prove the lines idle high on the bench
- **JoystickModuleMh** — Wokwi's analog joystick. VRX mapped to HORZ and VRY to VERT by name only; the real board's axis directions are unmeasured.
- **Max98357aDfr0954** — not simulated at all: no Wokwi part for the I2S amplifier; cues are visible in the serial log
- **SpeakerTerminal** — not simulated at all: a terminal is wiring, not a part to simulate; the amplifier it hangs off has no Wokwi part either, and no sound reaches the simulation
- **ONBOARD_LED (GPIO21)** — the Wokwi part of firebeetle2-esp32s3 is a stand-in, where GPIO21 is a bare header pin with no onboard LED or button, so spark knows no way for a scenario to read it. Test it on the board.
- **ONBOARD_BUTTON (GPIO47)** — the Wokwi part of firebeetle2-esp32s3 is a stand-in, where GPIO47 is a bare header pin with no onboard LED or button, so spark knows no way for a scenario to press it. Test it on the board.
