"""Paint every game's art in a pencil and watercolour style, and write it for the board.

Run from the repository root: python3 art/paint.py. Standard library and PIL only, deterministic: each art set paints
on its own seed. Writes games/art/<name>.bin (RGB565 big-endian, panel layout), games/art_index.py, art/preview.png,
and art/preview-ink.png (the night-ink look, on a sheet only).

A new game touches two places: its module in art/sets/ (its painters, its ArtSet with a seed, and the functions that
draw it on the preview sheets) and one row in ART_SETS in art/sets/__init__.py. Shared brushes it needs go to
brush.py. The art set is in artset.py, the looks in looks.py, the board's format, the index and the sheets in export.py.
"""

import os

from export import check_seams, preview, preview_ink, write_bins, write_index
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
    preview(ART_SETS, paintings, os.path.join(root, "art", "preview.png"))
    preview_ink(ART_SETS, paintings, os.path.join(root, "art", "preview-ink.png"))
    print("%d pictures, %d bytes" % (count, total))


if __name__ == "__main__":
    main()
