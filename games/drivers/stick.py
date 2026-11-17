"""
The joystick (P851): its two axes on the ESP32-S3's ADC, each read as -FULL to FULL around a fixed center.
--- MVP (P851) ---

The module is the PO's joystick-module-mh (spark's requirements.json): two potentiometers and a push switch. The axes
are pins.JOY_X and pins.JOY_Y (pads A0 and A1). The switch is pins.JOY_SW (pad D5), a plain button that drivers.buttons
reads, with the chip's pull-up (pins.JOY_SW_PULL is "up"), so it reads SWITCH_ON when pressed. With ATTN_11DB,
read_u16 reads the whole swing. The numbers here are the bench readings of 2026-11-17 on the PO's box, kept in P851's
plan; no log was kept (bench.md, P851): each axis went from 0 to 65535 and rested about 33000.

The center is fixed at CENTER, never sampled at boot, so a stick tilted at the boot cannot skew a session. DEAD_ZONE
covers the rest: in those readings the rest moved between 32391 and 33688, at most 920 from CENTER, so DEAD_ZONE (1024)
leaves 104 counts over one sample of the rest, not a margin measured over many. A pad with no stick on it floats: one
swept 0 to 40000 in those readings, so no read says whether a stick is there; the pin map names it or not.

The switch is polled once a frame with the 20 ms debounce (app.open_action_map), not counted in a pin interrupt as
BOOT is. So a tap shorter than about one frame (FRAME_MS, 40 ms, or a longer frame) can fall between two reads and is
lost, and a press is seen one frame after the same press of BOOT would be, at the frame after it has read pressed
for 20 ms. The bench step taps it quickly on purpose.
"""

CENTER = 32768  # read_u16's middle (0 to 65535): fixed, never sampled
TOP = 65535  # read_u16's largest value
DEAD_ZONE = 1024  # read_u16 counts on each side of CENTER that read 0: over the bench's rest, 920 from CENTER at most
FULL = 100  # an axis reads -FULL to FULL
SWAP_AXES = True  # the PO's module sits turned 90 degrees on the breadboard: up and down move pins.JOY_X, left and right
# pins.JOY_Y (logs/p851-stick-directions.log, run 2: up read JOY_X low for 7 s; left read JOY_Y high, right low)
X_SIGN = -1  # so left reads negative: left reads its pad high (the log above)
Y_SIGN = 1  # so up reads negative: up reads its pad low (the log above)
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
    """read_x() and read_y(): the stick's axes now, -FULL to FULL, left and up negative (X_SIGN, Y_SIGN). adc_x and adc_y answer read_u16(), as machine.ADC does."""

    def __init__(self, adc_x, adc_y):
        self.adc_x, self.adc_y = adc_x, adc_y

    @classmethod
    def on_board(cls, pin_x, pin_y):
        """pin_x and pin_y: the module's own X and Y pads, as the pin map names them; SWAP_AXES says which moves with
        left and right on this box."""
        from machine import ADC, Pin

        if SWAP_AXES:
            pin_x, pin_y = pin_y, pin_x
        return cls(ADC(Pin(pin_x), atten=ADC.ATTN_11DB), ADC(Pin(pin_y), atten=ADC.ATTN_11DB))

    def read_x(self):
        return axis(self.adc_x.read_u16(), X_SIGN)

    def read_y(self):
        return axis(self.adc_y.read_u16(), Y_SIGN)
