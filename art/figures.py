"""The set figures (P904 step 2c): Rescue's still street and the eight characters of art/detailed.py's CAST, each
running facing right and facing left, for probe904_figures.py, which counts how many 96 px figures the game box moves
at once. 96 px is detailed.TALL, an adult's standing height from the soles to the top of the fireman's helmet. The
pictures are 72 to 111 px tall and 42 to 67 px wide: the child is smaller, the chef's toque is taller, and a pose in
flight adds. It is in no ART_SETS: art/paint.py does not write it, no pack of it is committed, and the box's pool
stays as big as its largest committed pack. write(folder) writes its pack and an index of that pack alone; the probe
calls it with a temporary folder, copies the two files to the board and removes them again. It moves to art/sets/ and
joins ART_SETS when a game loads it (P900).

Its pictures, in their order: figures_night (the street, not keyed), then for each character figures_<name>_r0 to
_r11 (its run's poses facing right) and figures_<name>_l0 to _l11 (the same, facing left), each keyed. It needs the
CMU files, in mocap.CMU_DIR or in the folder of the capture it is given: without them the paint raises
FileNotFoundError.
"""

import dataclasses
import functools
import os

import detailed
import mocap
from artset import ArtSet, Painting
from export import Packs, write_index, write_packs
from sets.rescue import read_committed

NAME = "figures"


@functools.lru_cache(maxsize=None)
def cast(capture):
    """Each character of detailed.CAST's run at 96 px (a RunPictures), painted from capture (a mocap.Capture; None:
    the CMU files in mocap.CMU_DIR) once for paint_figures, gaits and write: about 53 s on the Mac."""
    capture = capture or mocap.Capture()
    return tuple(detailed.RunPictures(capture, detailed.TALL, character=c, cycle_name=name)
                 for c, name in detailed.CAST)


def paint_figures(capture=None):
    """The set's Painting: the street, then each character's run facing right and facing left."""
    pictures = {NAME + "_night": (read_committed(["rescue_night"])["rescue_night"], False)}
    for run in cast(capture):
        for side, poses in (("r", run.pictures), ("l", run.left)):
            pictures.update({"%s_%s_%s%d" % (NAME, run.character.name, side, i): (img, True)
                             for i, img in enumerate(poses)})
    return Painting(pictures)


def gaits(capture=None):
    """A gait row per character for the probe's board part: (name, pivot x, stride, speed). A gait is the pivot x in
    its pictures facing right, the stride in px a cycle and the speed in px a second, as captured (the probe rounds the
    speed to a whole px a second)."""
    return tuple((run.character.name, run.pivot[0], run.stride, run.speed) for run in cast(capture))


def write(folder, capture=None):
    """The set's pack as folder/packs/figures.pak and its index as folder/art_index.py, by the product's writers on a
    copy of the set that owns the index's layers (it has none; write_index asks for one owner). The folder is laid out
    as the board's root, so the index's path to the pack holds in both. Answers the two paths."""
    art_set = dataclasses.replace(ART_SET, paint_fn=functools.partial(paint_figures, capture), index_layers=True)
    paintings = {NAME: art_set.paint()}
    packs = Packs([art_set], paintings)
    os.makedirs(os.path.join(folder, "packs"), exist_ok=True)
    write_packs(packs, os.path.join(folder, "packs"))
    index = os.path.join(folder, "art_index.py")
    write_index([art_set], paintings, packs, index)
    return os.path.join(folder, "packs", NAME + ".pak"), index


ART_SET = ArtSet(NAME, detailed.SEED, paint_figures)  # the seed of every P904 picture
