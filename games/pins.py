# The pin map: written by spark's assign_pins.py from requirements.json
# for the DFRobot FireBeetle 2 ESP32-S3. Regenerate it; do not edit it.

SCLK = 17  # pad SCK; on the board's own SPI pin — dedicated hardware, not a choice; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio; spi: MOSI, MISO, SCK and SS: the hardware SPI bus, silkscreened MO, MI, SCK and A4
MOSI = 15  # pad MO; on the board's own SPI pin — dedicated hardware, not a choice; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio; spi: MOSI, MISO, SCK and SS: the hardware SPI bus, silkscreened MO, MI, SCK and A4
MISO = 16  # pad MI; on the board's own SPI pin — dedicated hardware, not a choice; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio; spi: MOSI, MISO, SCK and SS: the hardware SPI bus, silkscreened MO, MI, SCK and A4
TFT_BL = 38  # pad D3; needs pwm, and this pin does exactly that and no more; not_wake_capable: outside the RTC domain, so these cannot wake the chip however they are configured
TFT_CS = 11  # pad A5; needs nothing special; the cheapest pin left could still pwm and wake, which is spent here; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio
TFT_DC = 12  # pad D12; needs nothing special; the cheapest pin left could still pwm and wake, which is spent here; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio
TFT_RST = 13  # pad D11; needs nothing special; the cheapest pin left could still pwm and wake, which is spent here; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio
SD_CS = 14  # pad D10; needs nothing special; the cheapest pin left could still pwm and wake, which is spent here; adc2_unusable_with_wifi: on ADC2, which shares hardware with the radio
ONBOARD_LED = 21  # onboard_led: the on-board user LED, silkscreened D13, lit by a 1: measured on the PO's own DFR0975 on 2026-10-31 (walk 3 rehearsal, P470 #639; revision not recorded, its buttons sat where DFRobot's V1.2 overview shows them), the LED lit while the firmware wrote 1. Usable, but it will blink whatever you put on it
ONBOARD_LED_ON = 1  # the active level in the board record, the source is on the line above
ONBOARD_BUTTON = 47  # onboard_button: the on-board user button, silkscreened D14, reads 0 when pressed: measured on the PO's own DFR0975 on 2026-10-31 (walk 3 rehearsal, P470 #639; revision not recorded, its buttons sat where DFRobot's V1.2 overview shows them), it idled at 1 and read 0 while held, with the internal pull-up. The older revision in hardware_revisions reads about 0.7 V pressed, not 0 V. Already has a button on it, and cannot wake the chip from deep sleep
ONBOARD_BUTTON_ON = 0  # the active level in the board record, the source is on the line above
