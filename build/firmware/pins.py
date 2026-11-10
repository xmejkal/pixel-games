# The pin map: written by spark's assign_pins.py from requirements.json
# for the DFRobot FireBeetle 2 ESP32-S3. Regenerate it; do not edit it.

AUDIO_SHUTDOWN = 6  # pad A2; asked for by name — dedicated hardware, not a choice
JOY_X = 4  # pad A0; asked for by name — dedicated hardware, not a choice
JOY_Y = 5  # pad A1; asked for by name — dedicated hardware, not a choice
JOY_SW = 7  # pad D5; asked for by name — dedicated hardware, not a choice
JOY_SW_PULL = "up"  # no resistor: Pin(JOY_SW, Pin.IN, Pin.PULL_UP) uses the board's internal one
MIC_SCK = 8  # pad A3; asked for by name — dedicated hardware, not a choice
MIC_WS = 11  # pad A5; asked for by name — dedicated hardware, not a choice; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio
MIC_SD = 10  # pad A4; asked for by name — dedicated hardware, not a choice; spi: MOSI, MISO, SCK and SS: the hardware SPI bus, silkscreened MO, MI, SCK and A4
SCLK = 17  # pad SCK; asked for by name — dedicated hardware, not a choice; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio; spi: MOSI, MISO, SCK and SS: the hardware SPI bus, silkscreened MO, MI, SCK and A4
MOSI = 15  # pad MO; asked for by name — dedicated hardware, not a choice; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio; spi: MOSI, MISO, SCK and SS: the hardware SPI bus, silkscreened MO, MI, SCK and A4
MISO = 16  # pad MI; asked for by name — dedicated hardware, not a choice; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio; spi: MOSI, MISO, SCK and SS: the hardware SPI bus, silkscreened MO, MI, SCK and A4
GDI_RST = 38  # pad D3; asked for by name — dedicated hardware, not a choice; not_wake_capable: outside the RTC domain, so these cannot wake the chip however they are configured
GDI_CS = 18  # pad D6; asked for by name — dedicated hardware, not a choice; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio
GDI_SD_CS = 9  # pad D7; asked for by name — dedicated hardware, not a choice
GDI_BL = 21  # pad D13; asked for by name — dedicated hardware, not a choice; onboard_led: the on-board user LED, silkscreened D13, lit by a 1: measured on the PO's own DFR0975 on 2026-10-31 (walk 3 rehearsal, P470 #639; revision not recorded, its buttons sat where DFRobot's V1.2 overview shows them), the LED lit while the firmware wrote 1
SWITCH_BUTTON = 47  # pad D14; asked for by name — dedicated hardware, not a choice; not_wake_capable: outside the RTC domain, so these cannot wake the chip however they are configured; onboard_button: the on-board user button, silkscreened D14, reads 0 when pressed: measured on the PO's own DFR0975 on 2026-10-31 (walk 3 rehearsal, P470 #639; revision not recorded, its buttons sat where DFRobot's V1.2 overview shows them), it idled at 1 and read 0 while held, with the internal pull-up
I2S_BCLK = 12  # pad D12; on the I2S bus, which this board routes through its GPIO matrix rather than to labelled pins, so any pin serves; needs nothing special; the cheapest pin left could still pwm and wake, which is spent here; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio
I2S_LRC = 13  # pad D11; on the I2S bus, which this board routes through its GPIO matrix rather than to labelled pins, so any pin serves; needs nothing special; the cheapest pin left could still pwm and wake, which is spent here; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio
I2S_DIN = 14  # pad D10; on the I2S bus, which this board routes through its GPIO matrix rather than to labelled pins, so any pin serves; needs nothing special; the cheapest pin left could still pwm and wake, which is spent here; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio
ENC_A = 1  # pad SDA; needs nothing special; the cheapest pin left could still adc and pwm and wake, which is spent here; i2c: SDA and SCL: the hardware I2C bus
ENC_A_PULL = "up"  # no resistor: Pin(ENC_A, Pin.IN, Pin.PULL_UP) uses the board's internal one
ENC_B = 2  # pad SCL; needs nothing special; the cheapest pin left could still adc and pwm and wake, which is spent here; i2c: SDA and SCL: the hardware I2C bus
ENC_B_PULL = "up"  # no resistor: Pin(ENC_B, Pin.IN, Pin.PULL_UP) uses the board's internal one
ONBOARD_LED = 21  # onboard_led: the on-board user LED, silkscreened D13, lit by a 1: measured on the PO's own DFR0975 on 2026-10-31 (walk 3 rehearsal, P470 #639; revision not recorded, its buttons sat where DFRobot's V1.2 overview shows them), the LED lit while the firmware wrote 1. Usable, but it will blink whatever you put on it
ONBOARD_LED_ON = 1  # the active level in the board record, the source is on the line above
ONBOARD_BUTTON = 47  # onboard_button: the on-board user button, silkscreened D14, reads 0 when pressed: measured on the PO's own DFR0975 on 2026-10-31 (walk 3 rehearsal, P470 #639; revision not recorded, its buttons sat where DFRobot's V1.2 overview shows them), it idled at 1 and read 0 while held, with the internal pull-up. The older revision in hardware_revisions reads about 0.7 V pressed, not 0 V. Already has a button on it, and cannot wake the chip from deep sleep
ONBOARD_BUTTON_ON = 0  # the active level in the board record, the source is on the line above
