"""
The display's pins on the FireBeetle 2 ESP32-S3's GDI connector (P2), where DFRobot's GDI cable fixes them.

Walk 4 workaround: spark's pins.py names the pins spark chose for a wired breakout, and requirements.json cannot pin a
part to a connector (walk 4 diary, G27). So these come from parts/dfr0664-tft-2in.json, facts
gdi_on_firebeetle2_s3_gpio (board schematic V1.3 page 1, read off the image, not verified) and
gdi_backlight_gpio_on_firebeetle2_s3 (verified on the bench on 2026-11-01). SPI matches pins.py.
"""

import pins

SCLK = pins.SCLK  # 17, the same in pins.py and on GDI pin 15
MOSI = pins.MOSI  # 15, GDI pin 14
MISO = pins.MISO  # 16, GDI pin 13
DC = 3  # GDI pin 12; GPIO3 is the JTAG source strap (board record), fine once running
RST = 38  # GDI pin 11
CS = 18  # GDI pin 10 (LCS)
SD_CS = 9  # GDI pin 9; held high, so the card stays off the bus
BL = 21  # GDI pin 17; the same pin as pins.ONBOARD_LED, so the board's LED lights with the backlight
