"""A package module that imports by __import__, which the walk cannot read."""
gfx = __import__("gfx")
