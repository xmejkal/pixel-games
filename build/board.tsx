import { FireBeetle2Esp32S3 } from "./FireBeetle2Esp32S3"

/**
 * DFRobot FireBeetle 2 ESP32-S3 — generated from a module list.
 *
 * The CONNECTIONS are derived and checked: every trace comes from a pin assignment
 * validated against this board's own wake, ADC and strapping constraints, and every
 * module pin comes from a part definition whose facts carry sources.
 *
 * The PLACEMENT is a first draft and nothing more. Modules sit in a column because that
 * does not overlap, not because it is right. Nothing here knows which cable should exit
 * where, what a person has to reach with a soldering iron once the tall parts are in, or
 * what a slamming lid does to a hand-made lead. Lay it out properly before ordering.
 *
 * Not decided here, and it must be: mounting holes, connector keying, and trace widths for
 * anything carrying real current.
 */
export default () => (
  <board width="82.6mm" height="103.8mm" autorouter="auto"
      thickness="1.6mm"
      minViaHoleDiameter="0.3mm" minViaPadDiameter="0.6mm"
      automaticPoursEnabled>
    <FireBeetle2Esp32S3 name="Mcu" pcbX={-22.6} pcbY={0} />

    {/* DFRobot DFR0954 MAX98357A I2S amplifier */}
    <chip name="Max98357aDfr0954" footprint="dip12_w15.24mm" pcbX={11.1} pcbY={36.9}
      pinLabels={{ pin1: "SPK_P", pin2: "DIN", pin3: "BCLK", pin4: "LRC", pin5: "GND", pin6: "VCC", pin7: "GAIN", pin8: "SD", pin9: "NC", pin10: "GND", pin11: "VCC", pin12: "SPK_N" }} />
    {/* 2-pin speaker terminal (JST PH) */}
    {/* silkscreen: SPK_N is printed SPK-, SPK_P is printed SPK+ */}
    <chip name="SpeakerTerminal" footprint="jst_ph_2" pcbX={11.1} pcbY={21}
      pinLabels={{ pin1: "SPK_P", pin2: "SPK_N" }} />
    {/* Two-axis thumb joystick module (PS2-style, 5-pin, silkscreen "MH") */}
    {/* silkscreen: VCC is printed +5V */}
    <chip name="JoystickModuleMh" footprint="headermodule5" pcbX={11.1} pcbY={1.1}
      pinLabels={{ pin1: "GND", pin2: "VCC", pin3: "VRX", pin4: "VRY", pin5: "SW" }} />
    {/* CJMCU-111 rotary encoder module (4-pad: GA GB VCC GND, knob fitted) */}
    <chip name="Cjmcu111RotaryEncoder" footprint="pinrow4" pcbX={11.1} pcbY={-19.9}
      pinLabels={{ pin1: "GND", pin2: "VCC", pin3: "GB", pin4: "GA" }} />
    {/* Round INMP441-type I2S MEMS microphone breakout (6 pads: SCK WS L/R / SD VDD GND), chip marking unread */}
    {/* silkscreen: LR is printed L/R */}
    <chip name="Inmp441I2sMicRound" footprint="dip6" pcbX={11.1} pcbY={-34.9}
      pinLabels={{ pin1: "LR", pin2: "WS", pin3: "SCK", pin4: "SD", pin5: "VDD", pin6: "GND" }} />

    {/* What the parts demand of this board as components, from their records' host_parts — done here. */}
    {/* pulldown on Inmp441I2sMicRound.SD: the datasheet asks for it so that SD does not float in the half-frame the chip does not drive; whether the board has its own is unknown (other face unseen). A host that reads only the slot L/R selects may ignore the other, then the pull-down does not matter */}
    <resistor name="Inmp441I2sMicRoundPulldownSD" resistance="100k" footprint="0603" pcbX={33.7} pcbY={45.1} />
    <trace from=".Inmp441I2sMicRoundPulldownSD > .pin1" to=".Inmp441I2sMicRound > .SD" />
    <trace from=".Inmp441I2sMicRoundPulldownSD > .pin2" to="net.GND" />

    {/* Signals, each on the pin assign_pins.py chose and for the reason it gave. */}
    <trace from=".Mcu > .A2" to=".Max98357aDfr0954 > .SD" />  {/* AUDIO_SHUTDOWN: asked for by name — dedicated hardware, not a choice */}
    <trace from=".Mcu > .A0" to=".JoystickModuleMh > .VRX" />  {/* JOY_X: asked for by name — dedicated hardware, not a choice */}
    <trace from=".Mcu > .A1" to=".JoystickModuleMh > .VRY" />  {/* JOY_Y: asked for by name — dedicated hardware, not a choice */}
    <trace from=".Mcu > .D5" to=".JoystickModuleMh > .SW" />  {/* JOY_SW: asked for by name — dedicated hardware, not a choice */}
    <trace from=".Mcu > .RX" to=".Cjmcu111RotaryEncoder > .GA" />  {/* ENC_A: asked for by name — dedicated hardware, not a choice */}
    <trace from=".Mcu > .TX" to=".Cjmcu111RotaryEncoder > .GB" />  {/* ENC_B: asked for by name — dedicated hardware, not a choice */}
    <trace from=".Mcu > .A3" to=".Inmp441I2sMicRound > .SCK" />  {/* MIC_SCK: asked for by name — dedicated hardware, not a choice */}
    <trace from=".Mcu > .A5" to=".Inmp441I2sMicRound > .WS" />  {/* MIC_WS: asked for by name — dedicated hardware, not a choice */}
    <trace from=".Mcu > .A4" to=".Inmp441I2sMicRound > .SD" />  {/* MIC_SD: asked for by name — dedicated hardware, not a choice */}
    <trace from=".Mcu > .D12" to=".Max98357aDfr0954 > .BCLK" />  {/* I2S_BCLK: on the I2S bus, which this board routes through its GPIO matrix rather than to labelled pins, so any pin serves; needs nothing special; the cheapest pin left could still pwm and wake, which is spent here */}
    <trace from=".Mcu > .D11" to=".Max98357aDfr0954 > .LRC" />  {/* I2S_LRC: on the I2S bus, which this board routes through its GPIO matrix rather than to labelled pins, so any pin serves; needs nothing special; the cheapest pin left could still pwm and wake, which is spent here */}
    <trace from=".Mcu > .D10" to=".Max98357aDfr0954 > .DIN" />  {/* I2S_DIN: on the I2S bus, which this board routes through its GPIO matrix rather than to labelled pins, so any pin serves; needs nothing special; the cheapest pin left could still pwm and wake, which is spent here */}

    {/* ASSIGNED, AND CONNECTED TO NOTHING. The pin assigner placed these, and
        no part in the module list claims them, so this file cannot say what
        they reach. They are not optional — the design asked for them:
          - SCLK on SCK (GPIO17): asked for by name — dedicated hardware, not a choice
          - MOSI on MOSI (GPIO15): asked for by name — dedicated hardware, not a choice
          - MISO on MISO (GPIO16): asked for by name — dedicated hardware, not a choice
          - GDI_RST on D3 (GPIO38): asked for by name — dedicated hardware, not a choice
          - GDI_CS on D6 (GPIO18): asked for by name — dedicated hardware, not a choice
          - GDI_SD_CS on D7 (GPIO9): asked for by name — dedicated hardware, not a choice
          - GDI_BL on D13 (GPIO21): asked for by name — dedicated hardware, not a choice
          - SWITCH_BUTTON on D14 (GPIO47): asked for by name — dedicated hardware, not a choice
        Add a part record for whatever each one drives, or wire it by hand.
        A schematic missing half its signals builds and routes cleanly. */}

    {/* Power. Which rail each module pin belongs to comes from its part file. */}
    <trace from=".Mcu > .3V3" to="net.V33" />
    <trace from=".Mcu > .GND1" to="net.GND" />
    <trace from=".Mcu > .GND2" to="net.GND" />
    <trace from=".Mcu > .GND3" to="net.GND" />
    {/* Mcu.VCC receives net.V5V and NOTHING ON THIS BOARD DRIVES that
        rail, so it is left open — on this module that pad is then a
        source, carrying USB power out. Add a regulator or an inlet
        whose record declares an output on that rail to feed it. */}
    <trace from=".Max98357aDfr0954 > .VCC" to="net.V33" />  {/* 3.3-5 V per DFRobot */}
    <trace from=".Max98357aDfr0954 > .GND" to="net.GND" />
    <trace from=".Max98357aDfr0954 > .SPK_P" to="net.SPEAKER_P" />  {/* bridged class-D output. SPK+ is top row rightmost, SPK- is BOTTOM row rightmost — diagonally opposite, not a neighbouring pair */}
    <trace from=".Max98357aDfr0954 > .SPK_N" to="net.SPEAKER_N" />
    <trace from=".SpeakerTerminal > .SPK_P" to="net.SPEAKER_P" />  {/* To the speaker's + wire, from the amplifier's + output. Never to ground. */}
    <trace from=".SpeakerTerminal > .SPK_N" to="net.SPEAKER_N" />  {/* To the speaker's - wire, from the amplifier's - output. Never to ground: it swings, it is not a return. */}
    <trace from=".JoystickModuleMh > .VCC" to="net.V33" />  {/* Labelled +5V, but there is no regulator or chip on the board: it is only the top end of the two pots. Feed it the host's 3.3 V so VRX and VRY never go above what the ESP32's ADC can take (see host_requirements). */}
    <trace from=".JoystickModuleMh > .GND" to="net.GND" />
    <trace from=".Cjmcu111RotaryEncoder > .VCC" to="net.V33" />  {/* feed from the host's 3V3, never from 5 V: if the board's own pull-ups go to VCC (unconfirmed), GA and GB idle at the supply voltage */}
    <trace from=".Cjmcu111RotaryEncoder > .GND" to="net.GND" />
    <trace from=".Inmp441I2sMicRound > .VDD" to="net.V33" />  {/* the host's 3V3. The chip's absolute maximum is 3.63 V: never 5 V */}
    <trace from=".Inmp441I2sMicRound > .GND" to="net.GND" />
    {/* THE WIDTH OF THE TRACES ABOVE ON net.GND, net.SPEAKER_N, net.SPEAKER_P, net.V33 IS UNJUSTIFIED.
        They take the router's default, which is about 0.15 mm and good
        for roughly 0.6 A. Nobody has stated what these rails carry, so
        nothing here could size them. Name each load's figure in its part
        record (`draws` or `can_supply` on the power pin), or state
        `max_current_a` in .spark/rules.json, and regenerate; `check_physics`
        judges the result by the same arithmetic that would have set it. */}

    {/* What these parts require of this board, from their part files.
        Beyond the 1 passive(s) placed above, none of it is done here — each one is a design decision:
          - DFRobot DFR0954 MAX98357A I2S amplifier: NEVER stop LRCLK while BCLK is running. Maxim state twice that this can produce a large DC output voltage, which into an 8 ohm speaker cooks the voice coil. Stop BCLK, not LRCLK.
          - DFRobot DFR0954 MAX98357A I2S amplifier: SD must be DRIVEN LOW to shut the amplifier down, not left floating — an on-board resistor holds it high, and floating selects a channel rather than turning it off. Removing the clock only reaches standby at 340 uA.
          - DFRobot DFR0954 MAX98357A I2S amplifier: Holding SD low draws current through that on-board resistor for as long as it is held: 33 uA at 3.3 V if R1 is 100k, 4.9 uA if it is 680k. The host GPIO sinks it, and it is spent precisely while the amplifier is meant to be off.
          - DFRobot DFR0954 MAX98357A I2S amplifier: SPK+ and SPK- are on OPPOSITE rows, diagonally — top row rightmost and bottom row rightmost. They are not an adjacent pair, and a footprint drawn as if they were will wire the speaker across the wrong two pads.
          - DFRobot DFR0954 MAX98357A I2S amplifier: This module has no mounting holes. Whatever holds it is the host board's problem.
          - DFRobot DFR0954 MAX98357A I2S amplifier: There is NO pad-1 marker — no square pad, no dot: orient the module by its silkscreen labels, never by a pad number, on a breadboard, a perfboard or a footprint.
          - 2-pin speaker terminal (JST PH): NEVER ground either pin. The amplifier's output is bridged: SPK+ and SPK- both swing and the speaker sits across them, so a pin that meets a ground, or another output, shorts the amplifier.
          - 2-pin speaker terminal (JST PH): This connector and any other 2-pin JST PH on the board — the power inlet's above all — can be cross-plugged. Key one of them or use another series: a motor supply into an amplifier output destroys it.
          - 2-pin speaker terminal (JST PH): The speaker's impedance decides the current through this terminal and what the amplifier delivers: check it against the amplifier's record before choosing a speaker.
          - Two-axis thumb joystick module (PS2-style, 5-pin, silkscreen "MH"): Feed the pin labelled +5V from 3.3 V, never from 5 V. The pot wipers swing up to whatever that pin gets, and 5 V on an ESP32-C6 ADC pin is above its absolute maximum.
          - Two-axis thumb joystick module (PS2-style, 5-pin, silkscreen "MH"): Pull SW up, either with the internal pull-up or with a 10k to 3.3 V. R1 on this board is empty, so an unpulled SW floats and the game sees random presses.
          - Two-axis thumb joystick module (PS2-style, 5-pin, silkscreen "MH"): Read VRX and VRY on ADC1 pins with 11 dB attenuation so the full 0 to 3.3 V swing is in range. At rest the stick sits near half scale, not exactly at it, so calibrate the centre at start-up and allow a dead zone.
          - Two-axis thumb joystick module (PS2-style, 5-pin, silkscreen "MH"): Debounce SW in firmware. A stick switch bounces like any tactile switch.
          - CJMCU-111 rotary encoder module (4-pad: GA GB VCC GND, knob fitted): Feed VCC from the FireBeetle's 3V3 and never from 5 V or VBUS: if the board's own pull-ups go to VCC (unconfirmed), GA and GB idle at the supply voltage, which on 5 V is more than the 3.3 V GPIOs of an ESP32-S3 are rated for. Funduino's sheet says 5 V (4.5-5.5 V) and Leybold says 3.3-5 V; neither is a maker, so 3.3 V is unproven until the knob has been turned on a bench.
          - CJMCU-111 rotary encoder module (4-pad: GA GB VCC GND, knob fitted): No pull-ups are confirmed on this board: have the firmware pull GA and GB up internally (spark's pins.py does when the host board states its internal pull-up), and measure the unit - VCC to GA and VCC to GB with power off - to find out. The contacts then pull each line to GND, so both idle HIGH and read 0 while closed.
          - CJMCU-111 rotary encoder module (4-pad: GA GB VCC GND, knob fitted): THE PUSH SWITCH IS NOT ON THE HEADER of the pictured board (4 pads: GA GB VCC GND). A press cannot be read through it. If the unit has a fifth pad or a SW label, this record does not describe it. To use the press, solder wires to the encoder's two switch pins (small pads on the underside) after checking with a meter that they are isolated from the other pads; that switch is then a bare contact: one side to GND, the other to a GPIO with the internal pull-up.
          - CJMCU-111 rotary encoder module (4-pad: GA GB VCC GND, knob fitted): Shop pages for 'CJMCU-111' describe two different boards: Leybold's text and a search summary list 5 pins (GND + SW DT CLK, KY-040 style) while both shops' photos show 4 pads labelled GA GB VCC GND. Wire from the silkscreen on the unit, never from a CLK/DT/SW diagram: reading the row from the wrong end puts GND on GA and VCC on GB.
          - CJMCU-111 rotary encoder module (4-pad: GA GB VCC GND, knob fitted): Debounce in firmware (the contacts are mechanical and an on-board capacitor, if it is a filter, has an unknown value), and decode both channels together: A alone cannot tell the direction. Count per detent on the bench before trusting a figure: shops give 20 detents and 20 pulses per turn, not the edges per detent.
          - CJMCU-111 rotary encoder module (4-pad: GA GB VCC GND, knob fitted): The board ships with the 4-pin header loose in the bag (Funduino: unsoldered). Solder it, shaft side up or down as the enclosure needs, and do not push sideways on the shaft: the sheet warns against lateral force.
          - Round INMP441-type I2S MEMS microphone breakout (6 pads: SCK WS L/R / SD VDD GND), chip marking unread: Feed VDD from the host's 3V3 and never from 5 V or VBUS: the chip's absolute maximum on VDD is 3.63 V and on the digital pins VDD + 0.3 V, and no regulator can be seen on the pad side of this board (the other face was not seen).
          - Round INMP441-type I2S MEMS microphone breakout (6 pads: SCK WS L/R / SD VDD GND), chip marking unread: L/R must be tied: to GND the samples come in the LEFT slot, to VDD in the RIGHT slot. Do not leave it floating; the slot is undefined.
          - Round INMP441-type I2S MEMS microphone breakout (6 pads: SCK WS L/R / SD VDD GND), chip marking unread: The host is the I2S master and must clock SCK at exactly 64 times WS (32-bit slots, both channels), SCK 0.5 to 3.2 MHz, WS 7.8 to 50 kHz. Read 32-bit words: the 24 bits are the top of each word, two's complement.
          - Round INMP441-type I2S MEMS microphone breakout (6 pads: SCK WS L/R / SD VDD GND), chip marking unread: The first 2^18 SCK cycles after power-up (85 ms at 3.072 MHz) read zero; drop those samples.
          - Round INMP441-type I2S MEMS microphone breakout (6 pads: SCK WS L/R / SD VDD GND), chip marking unread: SD floats in the half-frame the chip does not use. Read only the slot that L/R selects, or add the datasheet's 100 kOhm pull-down to GND on SD.
          - Round INMP441-type I2S MEMS microphone breakout (6 pads: SCK WS L/R / SD VDD GND), chip marking unread: Do not leave SCK and WS running while VDD is off: the datasheet warns that it continuously turns on the ESD diodes and may affect the chip's long-term reliability.
          - Round INMP441-type I2S MEMS microphone breakout (6 pads: SCK WS L/R / SD VDD GND), chip marking unread: The sound port is the small plated hole at the centre of the PAD SIDE: keep it clear of dust, tape and a breadboard surface pressed against it, or the sensitivity drops.
          - Round INMP441-type I2S MEMS microphone breakout (6 pads: SCK WS L/R / SD VDD GND), chip marking unread: Pad order and the identity of the chip rest on one photo of one face. Look at the other face before the pad order is trusted for a PCB footprint.
     */}
  </board>
)
