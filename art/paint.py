"""Paint the runner's art in a pencil and watercolour style, and write it for the board.

Run from the repository root: python3 art/paint.py. Standard library and PIL only, deterministic (fixed seed).
Writes games/art/<name>.bin (RGB565 big-endian, panel layout), games/art_index.py and art/preview.png.

The background is painted at 4x and shrunk, so washes and pencil grain stay soft. A sprite is painted at 8x as
watercolour parts, shrunk, cut to a hard mask (every pixel fully on or off: the board skips one key colour), and
given a pencil outline outside its shape, tinted by the colour it borders.
"""

import os

from export import check_seams, preview, write_bins, write_index
from sets import ART_SETS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(root=ROOT):
    """Paint every set in ART_SETS on its own seed, then write the board files, the index and the preview under root."""
    paintings = {art_set.name: art_set.paint() for art_set in ART_SETS}
    out_dir = os.path.join(root, "games", "art")
    os.makedirs(out_dir, exist_ok=True)
    total = write_bins(paintings, out_dir)
    check_seams(paintings)
    count = write_index(ART_SETS, paintings, os.path.join(root, "games", "art_index.py"))
    os.makedirs(os.path.join(root, "art"), exist_ok=True)
    preview(paintings, os.path.join(root, "art", "preview.png"))
    print("%d pictures, %d bytes" % (count, total))


if __name__ == "__main__":
    main()
