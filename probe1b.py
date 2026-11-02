# P533 slice 1: one picture that settles which way game x runs at rotation 1. The games' own canvas draws six bands,
# red to magenta from game x 0, and the word LEFT at game x 4, y 4. Run: mpremote run probe1b.py
import lcd
from gfx import c565

out = lcd.open_tft(60_000_000)
cv = out.canvas
cv.start()
for i, rgb in enumerate(((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255))):
    cv.fill(i * 54, 0, 54, 240, c565(*rgb))
cv.big("LEFT", 4, 4, c565(0, 0, 0), 3)
out.tft.show()
