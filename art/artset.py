"""An art set: one game's pictures, painted on its own seed, and what the preview sheets need to show them."""

from dataclasses import dataclass, field

from brush import rnd
from looks import Watercolour


@dataclass
class Painting:
    """What one art set paints. pictures: name to (image, keyed), in the order their files are written; layers: the
    parallax layers back to front, as (name, image, top, speed, keyed), each one also among the pictures."""

    pictures: dict
    layers: list = field(default_factory=list)

    def images(self):
        return {name: img for name, (img, _) in self.pictures.items()}

    def through(self, look):
        """The same painting seen through a look: every picture, and the layers among them, in the same order."""
        pictures = {name: (look.apply(img), keyed) for name, (img, keyed) in self.pictures.items()}
        layers = [(name, pictures[name][0], top, speed, keyed) for name, _, top, speed, keyed in self.layers]
        return Painting(pictures, layers)


@dataclass
class ArtSet:
    """One game's art: its module in art/sets/ makes one, and one row in ART_SETS lists it. Its paint_fn starts on
    the set's own seed, so a change to one game moves no other game's art. The functions after look draw the set on
    the preview sheets; a set without them is left off."""

    name: str
    seed: int
    paint_fn: object  # () -> Painting
    aliases: dict = field(default_factory=dict)  # an old name the game may still ask for: the picture it now shows
    look: object = field(default_factory=Watercolour)  # how the pictures are seen; Watercolour leaves them as painted
    index_layers: bool = False  # its layers are art_index.LAYERS, the name the runner's game code reads
    sheet_fn: object = None  # (painting, sheet, y) -> the next y: its rows on preview.png
    tail_fn: object = None  # (painting, sheet, y) -> the bottom y: rows drawn after every set's sheet_fn
    scene_fn: object = None  # (painting) -> one composed frame (RGB), for preview-ink.png
    ink_accent: tuple = None  # the hue NightInk keeps on preview-ink.png; None leaves the set off that sheet

    def paint(self):
        rnd.seed(self.seed)
        return self.paint_fn().through(self.look)
