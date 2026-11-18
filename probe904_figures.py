"""
P904 step 2c (#1283): how many 96 px figures the game box moves at once. Rescue's still street, and over it 0, 1, 2,
4, 8 and 16 figures (COUNTS), each count for SECONDS on the board's wall clock, in one run. Figure i is character
i modulo 8 of art/detailed.py's CAST, so count 2 is the fireman and the paramedic. Each figure runs at its captured
speed, turns at the screen's edges so that its picture stays whole on it, and its pose follows the px it ran. The
pictures are the set figures (art/figures.py), painted whole on the Mac: its pack is 2,464,000 bytes, in no ART_SETS.

Deploy the branch's game code first (`python3 tools/box.py deploy <the lineup>`), close any log, then, from the
repository root, on the Mac:

    python3 probe904_figures.py [--dry-run] [--cmu DIR]

The Mac part:
1. reads `ls :` and refuses when the box has an :art_index.py: that is the box's real index (deploy --py), and the
   cleanup would delete it;
2. paints the set from the CMU files in DIR (mocap.CMU_DIR by default; about a minute), and refuses with the capture's
   own message when they are missing;
3. writes the pack and an index of it alone into a temporary folder, with a copy of this file whose GAITS holds each
   character's gait (name, pivot x, stride, speed);
4. copies the pack to :packs/figures.pak, then the index to :art_index.py (the shadow index: the board imports a .py
   before the .mpy of the same name, so the pool is made as big as this pack alone; meanwhile the lineup's games find
   no art and draw their plain shapes);
5. hard-resets the board, waits with `exec pass` until the board answers, then runs the copy once, within the counts
   times SECONDS plus 120 s (LIMIT_S);
6. prints each line of the run and writes them to logs/run-p904-2c.log, also after a failed or a timed-out run, and
   refuses a run that did not end with `done`;
7. in every case, once the copies began: reads `ls :` and `ls :packs`, removes :art_index.py and :packs/figures.pak
   where they are, and hard-resets the board, so the box plays its lineup with its own index again. Each of these
   commands is tried again while the probe still runs and keeps mpremote out.
--dry-run prints each board command and runs none: the cleanup as for a board that holds both copies, no `done` test
and no log. It still paints and writes the set in the temporary folder.

The lines, from the board:
- `probe p904 counts 0,1,2,4,8,16 seconds 30`
- `psram free <B> largest <B>` and `gc free <B> alloc <B>`, at the start and at the end: PSRAM's free bytes and its
  largest free block (esp32.idf_heap_info), and the heap after a collection
- the App's `game figures` and `switch figures <ms> ms, load <ms> ms, import <ms> ms`: the load is the pack's read
  (the probe's one game builds at once, with no loading card)
- `pack pool <B>` or `pack heap <B>`, after the load: whether s3lcd's pool holds the pack's size (the size the loader
  asked it for), or the pool was smaller and the pack went into the heap
- `count <N> starts` at each count; the App's `fps`, `time`, `phases`, `avg` and `heap` lines every 5 s between them.
  In this scene `avg`'s paint is the figures'. The App starts its interval at each count, but not its `avg` sums, so
  the first lines of each count are left out
- `done`, after the last count. `game figures refused: ...` and no `done` when the box cannot make the pool, and a
  traceback when a picture does not draw.
The box's music plays, as for every game.

By hand, when the cleanup itself fails: `mpremote rm :art_index.py :packs/figures.pak`, then `mpremote reset`. The
next `python3 tools/box.py deploy` also removes an :art_index.py.
"""

import sys

COUNTS = (0, 1, 2, 4, 8, 16)  # figures at once, one count after the other
SECONDS = 30  # each count's, on the wall clock
GAITS = None  # the Mac part sends a copy with each character's (name, pivot x, stride, speed) here (figures.gaits)
WIDTH, FEET = 320, 214  # the screen's width (gfx.WIDTH) and the row the soles stand on (games/rescue.py's FEET)
POSES = 12  # a run's poses
NIGHT = "figures_night"  # the still street
LIMIT_S = len(COUNTS) * SECONDS + 120  # the run's time limit: the counts, the boot, the load and the lines
PACK, INDEX = "packs/figures.pak", "art_index.py"  # where the copies go on the board
WAIT = ["exec", "pass"]  # a cheap command: the board answers it once it is back from the hard reset


class Done(Exception):
    pass


class Figure:
    """One moving figure: a character's gait (name, pivot x, stride, speed) and its pictures' size (w, h). It holds
    the column of its hips (x, a float), the way it faces (facing: 1 right, -1 left) and the px it ran. Its hips stay
    between lo and hi, where both facings' pictures are whole on the screen: the left picture is the right one
    mirrored, so its pivot is w - 1 - pivot from its left. share: how far from lo to hi it starts."""

    def __init__(self, gait, size, share, facing):
        self.name, self.pivot, self.stride, self.speed = gait
        self.w, self.h = size
        margin = max(self.pivot, self.w - 1 - self.pivot)  # the hips to the far side of either facing's picture
        self.lo, self.hi = margin, WIDTH - 1 - margin
        self.x, self.facing, self.ran = self.lo + (self.hi - self.lo) * share, facing, 0.0

    def step(self, ms):
        """ms of running at its speed; at an edge it stops there and turns, as Rescue's fireman does."""
        px = self.speed * ms / 1000
        self.x += px * self.facing
        self.ran += px
        if self.x < self.lo or self.x > self.hi:
            self.facing = 1 if self.x < self.lo else -1
            self.x = self.lo if self.x < self.lo else self.hi

    def picture(self):
        """Its pose's picture: the pose follows the px it ran (games/rescue.py's run_pose), its side its facing."""
        return "figures_%s_%s%d" % (self.name, "r" if self.facing > 0 else "l",
                                    int(self.ran) * POSES // self.stride % POSES)

    def corner(self):
        """The picture's top left: its pivot (the hips' column on its last row) on (x, FEET)."""
        pivot = self.pivot if self.facing > 0 else self.w - 1 - self.pivot
        return int(self.x) - pivot, FEET - self.h + 1


def count_at(ms):
    """The count ms after the first frame, or None after the last count."""
    k = ms // (SECONDS * 1000)
    return COUNTS[k] if k < len(COUNTS) else None


def pack_line(pool, size):
    """Where the pack sits: pool (s3lcd.pool) answers size, the size the loader asked it for, when the pool holds it,
    and raises ValueError when the pool was made smaller, so the loader put the pack in the heap."""
    try:
        pool(size)
    except ValueError:
        return "pack heap %d" % size
    return "pack pool %d" % size


class Counts:
    """The frame wrapper's work (board()), on the wall clock from the first frame of the probe's game, after its load:
    that frame prints the pack line (pack answers it). At each change of count_at it prints `count N starts`, gives the
    game the count and starts the App's interval, so no fps line mixes two counts. After the last count it raises Done.
    ticks_ms and ticks_diff are time's."""

    def __init__(self, ticks_ms, ticks_diff, pack):
        self.ticks_ms, self.ticks_diff, self.pack = ticks_ms, ticks_diff, pack
        self.start, self.count = None, None

    def after_frame(self, app):
        now = self.ticks_ms()
        if self.start is None:
            self.start = now
            print(self.pack())
        count = count_at(self.ticks_diff(now, self.start))
        if count is None:
            raise Done
        if count != self.count:
            self.count = app.game.count = count
            print("count %d starts" % count)
            app.new_interval()


def game_class(gaits):
    """The probe's game, a gfx.Game: Rescue's still street, and over it the first count of its 16 figures, figure i
    on gaits[i % len(gaits)]. It starts in play (TITLE_MS 0, as rain.py), and sets covers as Rescue does. A picture
    that does not draw raises, so an empty scene cannot pass. The count is set from outside (Counts). The board part
    calls it, and a Mac test with games/ on the path."""
    import gfx
    import pictures

    def drawn(cv, name, x, y):
        if not pictures.draw(cv, name, x, y):
            raise RuntimeError("%s did not draw: no art" % name)

    class Probe(gfx.Game):
        name = "figures"
        hint = "the figures run"
        ART = ("figures", None)
        TITLE_MS = 0
        count = 0

        def setup(self):
            self.covers = pictures.load(*self.ART)  # the street covers the screen, so no fill goes under it
            art, n = pictures.art_index.ART, max(COUNTS)
            self.figures = []
            for i in range(n):
                gait = gaits[i % len(gaits)]
                size = art["figures_%s_r0" % gait[0]][:2]
                self.figures.append(Figure(gait, size, i * 5 % n / (n - 1), 1 if i % 2 == 0 else -1))

        def play(self, pressed, held):
            for figure in self.figures[:self.count]:
                figure.step(self.ms)

        def paint_static(self, cv):
            drawn(cv, NIGHT, 0, 0)

        def paint(self, cv):
            for figure in self.figures[:self.count]:
                x, y = figure.corner()
                drawn(cv, figure.picture(), x, y)

    return Probe


def memory():
    """PSRAM's free bytes and its largest free block, then the heap's after a collection (probe567.py's)."""
    import esp32
    import gc

    heaps = [h for h in esp32.idf_heap_info(esp32.HEAP_DATA) if h[0] > 1_000_000]  # (total, free, largest, min)
    print("psram free %d largest %d" % (sum(h[1] for h in heaps), max(h[2] for h in heaps)))
    gc.collect()
    print("gc free %d alloc %d" % (gc.mem_free(), gc.mem_alloc()))


def board():
    import time

    import app
    import main
    import pictures
    import s3lcd

    Probe = game_class(GAITS)
    knob, speaker = main.compose()  # the box's knob and speaker, as main.py builds them (P850)
    print("probe p904 counts %s seconds %d" % (",".join("%d" % n for n in COUNTS), SECONDS))
    memory()
    size = max(row[1] for row in pictures.art_index.PACKS.values())  # the largest pack: the pool's size
    counts = Counts(time.ticks_ms, time.ticks_diff, lambda: pack_line(s3lcd.pool, size))
    _frame = app.App.frame

    def frame(self):
        _frame(self)
        if isinstance(self.game, Probe):
            counts.after_frame(self)

    app.App.frame = frame
    try:
        app.run(games=(Probe,), knob=knob, speaker=speaker)
    except Done:
        pass
    memory()
    print("done")


# --- the Mac part ---

def text(out):
    """A run's output as text: a timed-out run's is bytes (subprocess.run decodes only a finished run's), or None."""
    return out.decode("utf-8", "replace") if isinstance(out, bytes) else out or ""


class Bench:
    """The Mac part's run on the box (steps 1 and 3 to 7 of the docstring) through runner (a box.Mpremote, or a
    test's), with art (art/figures.py, or a test's) writing the set; log: the log's path; sleep: the pause between two
    tries."""

    def __init__(self, runner, art, log, sleep=None):
        import time

        import box

        self.runner, self.art, self.log, self.box = runner, art, log, box
        self.sleep = sleep or time.sleep

    def tried(self, args, tries=None):
        """The runner's answer to args, tried again while mpremote cannot reach the board."""
        box = self.box
        return box.retried(self.runner, args, tries or box.PROBE_TRIES, box.RESET_PAUSE_S, self.sleep)

    def check(self):
        """Refuses a box that has an :art_index.py, before any copy: it is the box's real index."""
        if INDEX in self.box.board_names(self.tried(["ls", ":"])):
            raise SystemExit("refused: the box has an :%s, its real index (deploy --py), which the cleanup would "
                             "delete: deploy without --py first" % INDEX)

    def run(self, capture):
        """Steps 3 to 7 with the CMU files of capture: the copies, the run, its lines and log, the cleanup."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            pack, index = self.art.write(tmp, capture)
            copy = os.path.join(tmp, "probe904_figures.py")
            with open(__file__) as f:
                source = f.read()
            with open(copy, "w") as f:
                f.write(filled(source, self.art.gaits(capture)))
            try:
                self.runner.run(["cp", pack, ":" + PACK])  # the pack first: a failed copy leaves no index naming it
                self.runner.run(["cp", index, ":" + INDEX])
                self.box.reset(self.runner, sleep=self.sleep)
                self.tried(WAIT, self.box.RESET_TRIES)
                said, why = self.board_run(copy)
                lines = self.keep(said)
            finally:
                self.clean()
        if why:
            raise SystemExit("refused: %s; the log is %s" % (why, self.log))
        if not self.runner.dry_run and "done" not in lines:
            raise SystemExit("refused: the board's run did not end with done: " + (lines[-1] if lines else "no output"))
        return lines

    def board_run(self, copy):
        """The copy run on the board once, within LIMIT_S: its output, and why it failed or None."""
        import subprocess

        try:
            return self.runner.run(["run", copy], timeout=LIMIT_S), None
        except subprocess.TimeoutExpired as e:
            return text(e.stdout) + text(e.stderr), "the run took over %d s" % e.timeout
        except subprocess.CalledProcessError as e:
            return text(e.stdout) + text(e.stderr), "the run failed with exit %d" % e.returncode

    def keep(self, said):
        """The run's lines, printed and written to the log (a dry run's are none, and it writes no log)."""
        lines = [line.strip() for line in said.splitlines() if line.strip()]
        for line in lines:
            print(line)
        if not self.runner.dry_run:
            with open(self.log, "w") as f:
                f.write("".join(line + "\n" for line in lines))
        return lines

    def clean(self):
        """The copies that the board holds go, then a hard reset, so the box plays its lineup with its own index. A
        dry run's board holds both."""
        box, dry = self.box, self.runner.dry_run
        root = box.board_names(self.tried(["ls", ":"]))
        packs = box.board_names(self.tried(["ls", ":packs"]))
        there = [":" + path for path, names in ((INDEX, root), (PACK, packs))
                 if dry or path.split("/")[-1] in names]
        if there:
            self.tried(["rm"] + there)
        box.reset(self.runner, sleep=self.sleep)


def filled(source, gaits):
    """This file's source with GAITS filled in, for the board (as probe844_import.py fills SET)."""
    copy = source.replace("\nGAITS = None", "\nGAITS = %r" % (tuple(gaits),), 1)
    if copy == source:
        raise ValueError("no GAITS = None line in the probe")
    return copy


LOG = "logs/run-p904-2c.log"  # from the repository root


def mac(argv, runner=None):
    import argparse
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    for folder in ("art", "tools"):
        if os.path.join(here, folder) not in sys.path:
            sys.path.insert(0, os.path.join(here, folder))
    import box
    import figures
    import mocap

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print each board command, run none")
    parser.add_argument("--cmu", default=mocap.CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    args = parser.parse_args(argv)
    bench = Bench(runner or box.Mpremote(args.dry_run), figures, os.path.join(here, LOG))
    try:
        bench.check()
        bench.run(mocap.open_capture(parser, args.cmu))
    except box.subprocess.CalledProcessError as e:
        raise SystemExit("%s failed: %s" % (" ".join(e.cmd), (e.stderr or "").strip() or "exit %d" % e.returncode))


if sys.implementation.name == "micropython":
    board()
elif __name__ == "__main__":
    mac(sys.argv[1:])
