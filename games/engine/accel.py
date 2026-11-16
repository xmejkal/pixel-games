"""The choice of each part's version (P850, stage 0b-2 of the engine plan): a hot part has a reference version in plain
Python and a fast one in viper or C, and the Chooser takes one of them once, at boot, and remembers why. main.py, the
composition root, asks it for every part and prints its line, such as
`engine sum=viper volume=reference(forced) native=_engine,_crackle.mpy`. A setting forces the reference version per
part: main.py reads it from the board's engine_config.py (tools/box.py deploy --engine writes it) and hands it in, so
this module reads no file but the crackle's. It never imports _crackle: native code takes executable memory that stays
taken until the next soft reset, so the crackle loads when Fire builds, and the boot only looks for its file.
--- MVP (P850) ---"""

import os

CRACKLE = "/_crackle.mpy"  # the crackle's native module at the board's root (tools/box.py deploy copies it)
FALLBACK = (ImportError, AttributeError, SyntaxError)  # a fast version this Python cannot load (D26)


class Chooser:
    """Chooses each part's version once and remembers why, for the boot line. reference: "all" forces every part's
    reference version, a tuple of part names forces those, () forces none."""

    def __init__(self, reference=()):
        self.reference = (reference,) if isinstance(reference, str) and reference != "all" else reference
        self.chosen = []  # (part, what was chosen), in the order of the choose calls

    def choose(self, part, fast, reference, label):
        """The fast class (fast() imports and answers it), named label in the line, or the reference class when the
        part is forced or fast() raises ImportError, AttributeError or SyntaxError."""
        if self.reference == "all" or part in self.reference:
            self.chosen.append((part, "reference(forced)"))
            return reference
        try:
            chosen = fast()
        except FALLBACK as e:
            self.chosen.append((part, "reference(%s)" % type(e).__name__))
            return reference
        self.chosen.append((part, label))
        return chosen

    def line(self):
        """`engine <part>=<version>... native=<what is there>`, then `unused=<names>` for each forced name that no
        choose call used."""
        words = ["engine"] + ["%s=%s" % pair for pair in self.chosen]
        words.append("native=" + (",".join(native()) or "none"))
        if self.reference != "all":
            used = [part for part, _ in self.chosen]
            unused = [name for name in self.reference if name not in used]
            if unused:
                words.append("unused=" + ",".join(unused))
        return " ".join(words)


def native():
    """The native code this board has: the firmware's C module _engine, and the crackle's file."""
    found = []
    try:
        import _engine  # noqa: F401  a built-in module: its import takes no executable memory
        found.append("_engine")
    except ImportError:
        pass
    try:
        os.stat(CRACKLE)
        found.append("_crackle.mpy")
    except OSError:
        pass
    return found
