"""@native where MicroPython has it, and nothing on the Mac, so the same code runs in the test."""

try:
    from micropython import native
except (ImportError, AttributeError):
    def native(function):
        return function
