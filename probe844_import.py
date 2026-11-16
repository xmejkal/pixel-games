"""
P849 (stage 0b-1 of the engine plan, P844): what a package costs on the board against flat files, and the heap and
the executable memory beside it. --- MVP (P849) ---

Deploy the branch first (`python3 tools/box.py deploy --all`: its pictures.py imports engine.clock), close any log,
then, from the repository root, on the Mac:

    python3 probe844_import.py [--rounds 3]

It compiles the same ten modules of games/ (MODULES) with mpy-cross twice and copies them to the board: flat as
:p844_<module>.mpy, and in a folder :p844/ with an empty __init__.mpy. Each round hard-resets the board and imports the
flat set cold, then hard-resets it and imports the folder's set cold (mpremote's own soft reset follows each hard
one, so each run starts from a clean heap). Before the timed imports a run imports the board's own copies of the ten
modules, so each copy's imports find their modules loaded and its time is its own: the lookup, the load and its body.
The folder's first line is the package's __init__.mpy. After the rounds one more reset and the heap's run, then it
removes every file it copied, also when a step fails.

Lines, from the board: `import <flat|package> <module|__init__> <us>` per module and run; `heap <stage> free <B>
gc_idle_us <us> exec_free <B> exec_largest <B>` at boot, after `import engine.signals, engine.clock` (`heap package
none` on a board without the package), after every game module of the catalog, and after sound_viper and
volume_viper: gc.mem_free() after a gc.collect(), the time of a second, idle gc.collect(), and
esp32.idf_heap_info(esp32.HEAP_EXEC) summed (free) and its largest free block. Then, from the Mac:
`median <module> flat <us> package <us>` per module, and `median total flat <us> package <us> (<+-n> %)`. bench.md gets
the medians and the heap lines; the plan's gate is a package within 10 % of flat files.
"""

import sys

SET = None  # the Mac part sends a copy with "flat", "package" or "heap" here
MODULES = ("catalog", "fast", "volume", "sound", "cues", "gfx", "motion", "pictures", "track", "overlay")
FOLDER = "p844"


def board():
    import gc
    import time

    def heap(stage):
        import esp32
        gc.collect()
        free = gc.mem_free()
        t = time.ticks_us()
        gc.collect()
        idle = time.ticks_diff(time.ticks_us(), t)
        regions = esp32.idf_heap_info(esp32.HEAP_EXEC)
        print("heap %s free %d gc_idle_us %d exec_free %d exec_largest %d" % (
            stage, free, idle, sum(r[1] for r in regions), max(r[2] for r in regions)))

    def timed(kind, label, name):
        t = time.ticks_us()
        __import__(name)
        print("import %s %s %d" % (kind, label, time.ticks_diff(time.ticks_us(), t)))

    if SET == "heap":
        heap("boot")
        try:
            import engine.signals  # noqa: F401
            import engine.clock  # noqa: F401
            heap("package")
        except ImportError:
            print("heap package none")
        import catalog
        for row in catalog.CATALOG:
            __import__(row[1])
        heap("games")
        import sound_viper  # noqa: F401
        import volume_viper  # noqa: F401
        heap("viper")
    else:
        for name in MODULES:
            __import__(name)  # the board's own copies: each timed copy's imports find them loaded
        gc.collect()
        if SET == "package":
            timed(SET, "__init__", FOLDER)
        for name in MODULES:
            timed(SET, name, ("%s_%s" if SET == "flat" else "%s.%s") % (FOLDER, name))
    print("done")


def mac(argv):
    import argparse
    import os
    import re
    import statistics
    import tempfile
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, "tools"))
    import box

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args(argv)
    runner, mpy_cross = box.Mpremote(), box.MpyCross()
    box.Compiler(mpy_cross).check()
    with open(__file__) as f:
        source = f.read()
    times = {"flat": {}, "package": {}}
    with tempfile.TemporaryDirectory() as tmp:
        flat = []
        for name in MODULES:
            flat.append(os.path.join(tmp, "%s_%s.mpy" % (FOLDER, name)))
            mpy_cross.run(["-march=xtensawin", "-s", "%s_%s.py" % (FOLDER, name), "-o", flat[-1], "games/%s.py" % name])
        os.mkdir(os.path.join(tmp, FOLDER))
        folder = []
        for name, path in [("__init__", "games/engine/__init__.py")] + [(m, "games/%s.py" % m) for m in MODULES]:
            folder.append(os.path.join(tmp, FOLDER, name + ".mpy"))
            mpy_cross.run(["-march=xtensawin", "-s", "%s/%s.py" % (FOLDER, name), "-o", folder[-1], path])
        runs = {}
        for kind in ("flat", "package", "heap"):
            runs[kind] = os.path.join(tmp, "run_%s.py" % kind)
            with open(runs[kind], "w") as f:
                f.write(source.replace("\nSET = None ", '\nSET = "%s" ' % kind, 1))
        box.retried(runner, ["cp"] + flat + [":"], box.PROBE_TRIES, box.RESET_PAUSE_S, box.time.sleep)
        try:
            if FOLDER + "/" not in box.board_names(runner.run(["ls", ":"])):
                runner.run(["mkdir", ":" + FOLDER])
            runner.run(["cp"] + folder + [":%s/" % FOLDER])
            for _ in range(args.rounds):
                for kind in ("flat", "package"):
                    for line in board_run(box, runner, runs[kind]):
                        found = re.match(r"import (\w+) (\w+) (\d+)$", line)
                        if found:
                            times[found.group(1)].setdefault(found.group(2), []).append(int(found.group(3)))
            for line in board_run(box, runner, runs["heap"]):
                pass
        finally:  # what is there of the copies, also after a failed step
            there = box.board_names(runner.run(["ls", ":"]))
            box.Deploy(runner).remove([":" + n for n in sorted(there) if n.startswith(FOLDER + "_")])
            if FOLDER + "/" in there:
                box.Deploy(runner).remove(sorted(":%s/%s" % (FOLDER, n)
                                                 for n in box.board_names(runner.run(["ls", ":" + FOLDER]))))
                runner.run(["rmdir", ":" + FOLDER])
    total = {}
    for name in ("__init__",) + MODULES:
        med = {kind: statistics.median(times[kind][name]) if name in times[kind] else 0 for kind in times}
        for kind in med:
            total[kind] = total.get(kind, 0) + med[kind]
        print("median %s flat %d package %d" % (name, med["flat"], med["package"]))
    print("median total flat %d package %d (%+.1f %%)" % (
        total["flat"], total["package"], 100.0 * (total["package"] - total["flat"]) / max(total["flat"], 1)))


def board_run(box, runner, path):
    """A hard reset, then the probe's copy at path on the board; prints and answers its lines."""
    box.reset(runner)
    said = box.retried(runner, ["run", path], box.PROBE_TRIES, box.RESET_PAUSE_S, box.time.sleep)
    lines = [line.strip() for line in said.splitlines() if line.strip()]
    for line in lines:
        print(line)
    if "done" not in lines:
        raise SystemExit("the board's run did not end: " + (lines[-1] if lines else "no output"))
    return lines


if sys.implementation.name == "micropython":
    board()
elif __name__ == "__main__":
    mac(sys.argv[1:])
