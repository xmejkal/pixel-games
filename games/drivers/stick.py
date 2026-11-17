"""
The joystick (P851): its two axes on the ESP32-S3's ADC, each read as -FULL to FULL around a fixed center.
--- MVP (P851) ---

The module is the PO's joystick-module-mh (spark's requirements.json): two potentiometers and a push switch. The axes
are pins.JOY_X and pins.JOY_Y (pads A0 and A1). The switch is pins.JOY_SW (pad D5), a plain button that drivers.buttons
reads, with the chip's pull-up (pins.JOY_SW_PULL is "up"), so it reads SWITCH_ON when pressed. With ATTN_11DB,
read_u16 reads the whole swing: on the PO's box (2026-11-17) each axis went from 0 to 65535 and rested about 33000.

The center is fixed at CENTER, never sampled at boot, so a stick tilted at the boot cannot skew a session. DEAD_ZONE
covers the rest: on the bench the rest moved between 32391 and 33688, at most 920 from CENTER. A pad with no stick on
it floats: one swept 0 to 40000 on the bench, so no read says whether a stick is there; the pin map names it or not.
"""

CENTER = 32768  # read_u16's middle (0 to 65535): fixed, never sampled
TOP = 65535  # read_u16's largest value
DEAD_ZONE = 1024  # read_u16 counts on each side of CENTER that read 0: over the bench's rest, 920 from CENTER at most
FULL = 100  # an axis reads -FULL to FULL
X_SIGN = 1  # 1 or -1, so left reads negative. Not measured yet: P851's bench step pushes the stick left once
Y_SIGN = 1  # 1 or -1, so up reads negative. Not measured yet: P851's bench step pushes the stick up once
SWITCH_ON = 0  # the switch closes to ground against the pull-up (pins.JOY_SW_PULL is "up"), so it reads 0 when pressed


def axis(raw, sign):
    """A read_u16 value as -FULL to FULL: 0 inside DEAD_ZONE of CENTER, then in proportion from the zone's edge to
    the end of its side, clamped, times sign. Small ints only: nothing is allocated."""
    d = raw - CENTER
    far = abs(d) - DEAD_ZONE
    if far <= 0:
        return 0
    v = min(far * FULL // ((TOP - CENTER if d > 0 else CENTER) - DEAD_ZONE), FULL)
    return sign * v if d > 0 else -sign * v


class Stick:
    """read_x() and read_y(): the stick's axes now, -FULL to FULL, left and up negative once X_SIGN and Y_SIGN are
    measured. adc_x and adc_y answer read_u16(), as machine.ADC does."""

    def __init__(self, adc_x, adc_y):
        self.adc_x, self.adc_y = adc_x, adc_y

    @classmethod
    def on_board(cls, pin_x, pin_y):
        from machine import ADC, Pin

        return cls(ADC(Pin(pin_x), atten=ADC.ATTN_11DB), ADC(Pin(pin_y), atten=ADC.ATTN_11DB))

    def read_x(self):
        return axis(self.adc_x.read_u16(), X_SIGN)

    def read_y(self):
        return axis(self.adc_y.read_u16(), Y_SIGN)
