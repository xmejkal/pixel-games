"""P762: the time of one repaint of the volume's picture into its kept strip, by part (us, the least of 5).
No game and no sound run. games/overlay.py, lcd.py, gfx.py and volume.py must be on the board (tools/crackle.sh with
KNOB=1 copies them). Run: mpremote connect <port> run probe762_paint.py. --- MVP (P762) ---"""
import time

import lcd
import overlay
import volume

vol = volume.MasterVolume(16)
pane = overlay.VolumePane(vol)
turned = type("T", (), {"turned": lcd.ORIENTATION == 180})()


def least(rect, paint):
    """The least of 5 runs of paint(canvas) into a kept strip of rect, in us."""
    cv = lcd.TftCanvas(lcd.Strip(*lcd.TftCanvas.panel_rect(turned, *rect)))
    best = 1 << 30
    for _ in range(5):
        t = time.ticks_us()
        paint(cv)
        best = min(best, time.ticks_diff(time.ticks_us(), t))
    return best


print("still part", least(overlay.RECT, pane.paint))
print("level part", least(overlay.LEVEL_RECT, pane.paint_level))
