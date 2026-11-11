"""P762: the time of one repaint of the volume's picture into its kept strip, by part (us, the least of 5).
No game and no sound run. games/overlay.py, lcd.py, gfx.py and volume.py must be on the board (tools/crackle.sh with
KNOB=1 copies them). Run: mpremote connect <port> run probe762_paint.py. --- MVP (P762) ---"""
import time
import lcd, overlay, volume
from gfx import DARK, GREY, WHITE
vol = volume.MasterVolume(8)
view = overlay.VolumeView(vol)
x, y, w, h = overlay.RECT
strip = lcd.Strip(*lcd.TftCanvas.panel_rect(type("T", (), {"turned": lcd.ORIENTATION == 180})(), x, y, w, h))
cv = lcd.TftCanvas(strip)
def least(f):
    best = 1 << 30
    for _ in range(5):
        t = time.ticks_us(); f(); best = min(best, time.ticks_diff(time.ticks_us(), t))
    return best
def cells():
    for i in range(16):
        cv.fill(x + 40 + 8 * i, y + 8, 6, 12, WHITE)
print("paint", least(lambda: view.paint(cv)))
print("fill", least(lambda: cv.fill(x, y, w, h, DARK)))
print("box", least(lambda: cv.box(x, y, w, h, GREY)))
print("text vol", least(lambda: cv.text("vol", x + 8, y + 10, WHITE)))
print("cells", least(cells))
print("text 16", least(lambda: cv.text("16", x + 176, y + 10, WHITE)))
print("key", least(lambda: ("volume", vol.step)))
