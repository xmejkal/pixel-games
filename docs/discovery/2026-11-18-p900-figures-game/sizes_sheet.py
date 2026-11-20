"""The ladder scene of P906 at four figure heights, for the PO's eye (P900, Q20: which height do the figures get?).

Run it with a checkout of pixel-games that holds the places for each height (the branch p906-height, 839cc45 or
later) as the working folder, and the CMU files in mocap.CMU_DIR:
    python3 -B <this file> OUT.png
It changes no file of the repository. This branch's own art/ is older than P906 and cannot paint the scene. Each row is one height: the round's start at the left, and the child at the
climb's end at the right, each as art/mission.py's Storyboard.frame draws it, 320 by 240 px, with the bar's words in
PIL's font and not the box's. The places follow from the height (art/mission.py's places): at 96 px they are the
ones set by eye, and the climb ends higher for a smaller child, so that its head is over the roof.
"""
import argparse
import sys

sys.path.insert(0, "art")

from PIL import Image, ImageDraw  # noqa: E402

import mission  # noqa: E402
from sets.rescue import read_committed  # noqa: E402

HEIGHTS = (48, 64, 80, 96)
MOMENTS = (0, 2)  # Storyboard's frames: a round's start, and the child at the climb's end
LABEL_H = 14
W, H = 320, 240


def main():
    parser = argparse.ArgumentParser(description="The ladder scene of P906 at four figure heights.")
    parser.add_argument("out")
    args = parser.parse_args()
    capture = mission.capture(parser)
    street = read_committed([mission.STREET])[mission.STREET]
    sheet = Image.new("RGB", (W * len(MOMENTS), (H + LABEL_H) * len(HEIGHTS)), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for row, height in enumerate(HEIGHTS):
        painted = mission.painted(capture, height)
        board = mission.Storyboard(painted, street, height)
        top = row * (H + LABEL_H)
        boxes = {figure: painted[figure, "run"].size for figure in ("fireman", "child")}
        tall = {}
        for figure in ("fireman", "child"):  # the standing picture's own rows, top to bottom
            img = painted[figure, "run"].left[mission.STAND[figure]]
            box = img.getchannel("A").getbbox()
            tall[figure] = box[3] - box[1]
        draw.text((4, top + 2), "height %d px: the fireman stands %d px tall, the child %d px"
                  % (height, tall["fireman"], tall["child"]), fill=(255, 255, 255))
        for col, k in enumerate(MOMENTS):
            sheet.paste(board.frame(k).convert("RGB"), (col * W, top + LABEL_H))
        print("height %d: run boxes fireman %s child %s, standing fireman %d px child %d px"
              % (height, boxes["fireman"], boxes["child"], tall["fireman"], tall["child"]))
    sheet.save(args.out)
    print("wrote", args.out, sheet.size)


if __name__ == "__main__":
    main()
