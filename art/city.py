"""The sky script (P573): one city seen through one day, a game an hour (D4). HOURS holds each hour's sky as three
colours, from the top, to the middle, to the haze over the roofs; a set reads its hour's and paints the rest itself.
Stack's noon came from art/sets/stack.py unchanged; P576 fills in the hours no game has yet."""

MORNING = ((112, 138, 184), (176, 192, 214), (232, 228, 214))  # snake (FEED): a clear cool sky, a pale warm haze
NOON = ((128, 120, 150), (196, 192, 208), (238, 234, 226))  # stack (RENT): bleached, a grey-violet haze
MIDNIGHT = ((6, 8, 20), (16, 18, 40), (52, 36, 58))  # gravpong (BUBBLE): deep indigo, a mauve haze over the city
HOURS = {10: MORNING, 12: NOON, 24: MIDNIGHT}
SODIUM = (120, 70, 40)  # the street lamps' glow low on the city at night, under the haze


def sky_at(hour, t):
    """The hour's sky at t, 0 at the top and 1 at the haze: the top to the middle over the first half, the middle to
    the haze over the second."""
    top, middle, haze = HOURS[hour]
    t = max(0.0, min(1.0, t))
    a, b, t = (top, middle, t / 0.5) if t < 0.5 else (middle, haze, (t - 0.5) / 0.5)
    return tuple(int(p + (q - p) * t) for p, q in zip(a, b))
