"""The games the box can hold (P817): one row each, (name, module, class name, art sets), in the order the box plays
them. The name is the class's `name`, the word a lineup uses. The sets are the art sets (art_index.PACKS) the game's
setup loads, so a deploy copies only their packs. It imports nothing: tools/box.py reads it on the Mac, and app.py
imports a game's module only when the box builds that game. --- MVP (P817) ---"""

CATALOG = (
    ("marshmallow", "marshmallow", "Marshmallow", ("runner",)),  # Fire's ART: the runner set's sky
    ("balls", "balls", "BallPit", ()),
    ("meteors", "meteors", "Meteors", ("meteors",)),
    ("bucket", "bucket", "Bucket", ("bucket",)),
    ("rescue", "rescue", "Rescue", ("rescue",)),
    ("flappy", "arcade", "Flappy", ("flappy",)),
    ("runner", "arcade", "Runner", ("runner",)),
    ("snake", "arcade", "Snake", ("snake",)),
    ("stack", "arcade2", "Stack", ("stack",)),
    ("cave", "arcade2", "Cave", ()),
    ("tunnel", "world3d", "Tunnel", ()),
    ("road", "world3d", "Road", ()),
    ("starfire", "space3d", "Starfire", ()),
    ("cube", "space3d", "CubeTiming", ("cube",)),
    ("gravpong", "arcade2", "GravityPong", ("gravpong",)),
)
NAMES = tuple(row[0] for row in CATALOG)
ROWS = {row[0]: row for row in CATALOG}  # name: its row


def lineup_fault(names):
    """Why names cannot be a lineup, or None when they can: a lineup is a tuple of one or more names of the catalog,
    each once. app.read_lineup and tools/box.py ask the same question."""
    if not isinstance(names, tuple) or not all(isinstance(name, str) for name in names):
        return "LINEUP is not a tuple of names"
    if not names:
        return "LINEUP is empty"
    for name in names:
        if name not in NAMES:
            return "no game %s in the catalog" % name
        if names.count(name) > 1:
            return "%s is in LINEUP twice" % name
    return None
