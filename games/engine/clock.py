"""The board's tick clock, read the same way on the Mac (P849, moved from pictures.py): CPython's time has no ticks,
so each function answers 0 there. --- MVP (P814, P822) ---"""

import time


def since(start):
    """The ms from start (time.ticks_ms()) to now; 0 on the Mac, where CPython's time has no ticks."""
    return time.ticks_diff(time.ticks_ms(), start) if hasattr(time, "ticks_diff") else 0


def ticks_us():
    """time.ticks_us(), or 0 on the Mac, where CPython's time has no ticks."""
    return time.ticks_us() if hasattr(time, "ticks_us") else 0


def ticks_diff(a, b):
    """time.ticks_diff(a, b), or 0 on the Mac."""
    return time.ticks_diff(a, b) if hasattr(time, "ticks_diff") else 0
