"""A package module that imports through builtins.__import__, which the walk cannot read."""
import builtins

gfx = builtins.__import__("gfx")
