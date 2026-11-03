"""Average fps and paint over pure-play intervals (phases title 0 and over 0) of one game in a board log."""
import re, sys
path, game = sys.argv[1], sys.argv[2]
times, rows = None, []
first = True
for line in open(path, errors="replace"):
    m = re.match(r"time %s step [\d.]+ paint ([\d.]+) send ([\d.]+) gc [\d.]+ fps (\d+) worst (\d+)" % game, line)
    if m:
        times = tuple(float(x) for x in m.groups())
        continue
    m = re.match(r"phases %s static \d+ paint \d+ fx \d+ hud \d+ over (\d+) title (\d+)" % game, line)
    if m and times:
        if first:  # the first interval after the switch is dropped (the plan)
            first = False
        elif m.group(1) == "0" and m.group(2) == "0":
            rows.append(times)
        times = None
n = len(rows)
print("pure-play intervals", n)
if n:
    for i, name in enumerate(("paint ms", "send ms", "fps", "worst ms")):
        print("%s %.2f" % (name, sum(r[i] for r in rows) / n))
