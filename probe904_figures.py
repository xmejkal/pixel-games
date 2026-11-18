"""
P904 step 2c (#1283): how many 96 px figures the game box moves at once. Rescue's still street, and over it 0, 1, 2,
4, 8 and 16 figures (COUNTS), each count for SECONDS on the board's wall clock, in one board run. Figure i is
character i modulo 8 of art/detailed.py's CAST, so count 2 is the fireman and the paramedic. 96 px is
detailed.TALL, an adult's standing height from the soles to the top of the fireman's helmet. The pictures are 72 to
111 px tall and 42 to 67 px wide: the child is smaller, the chef's toque is taller, and a pose in flight adds. The
pictures are the set figures (art/figures.py), painted whole on the Mac: its pack is 2,464,000 bytes, in no
ART_SETS.

Each figure runs at its captured speed, rounded to a whole px a second (the gait rows keep the captured value), and
steps in whole px with a carry in thousandths of a px, as games/rescue.py's fireman does. At an edge of the screen it
turns at once (the fireman plays his turn poses), so its picture stays whole on the screen. Its pose follows the px it
ran. Figure i starts at (i * 5 mod 16) / 15 of its way between its two edges, facing right when i is even, so the 16
start places differ and a figure that starts at an edge faces away from it.

Deploy the branch's game code first (`python3 tools/box.py deploy <the lineup>`), close any log, then, from the
repository root, on the Mac:

    python3 probe904_figures.py [--dry-run] [--cmu DIR]

The Mac part:
1. reads `ls :` and refuses when the box has an :art_index.py. It is the box's real index (a deploy with --py:
   deploy without --py first) or a shadow index that a failed cleanup left (remove it as below);
2. checks the CMU files in DIR (mocap.CMU_DIR by default) and refuses with the capture's own message when they are
   missing;
3. paints the set (about a minute) and writes its pack and an index of it alone into a temporary folder, with a copy
   of this file whose GAITS holds each character's gait row (name, pivot x, stride, speed);
4. copies the pack to :packs/figures.pak, then the index to :art_index.py (the shadow index: the board imports a .py
   before the .mpy of the same name, so the pool is made as big as this pack alone; meanwhile the lineup's games find
   no art and draw their plain shapes);
5. hard-resets the board, waits with `exec pass` until the board answers, then runs the copy once: the board run,
   within the counts times SECONDS plus 120 s (LIMIT_S);
6. prints each line of the board run and writes them to the first free log of logs/run-p904-2c.log,
   logs/run-p904-2c-2.log, -3 and on, so a log is never overwritten, also after a failed or a timed-out board run. It
   refuses a board run that did not end with a `done` line, and at its end prints the log's path;
7. in every case, once the copies began: reads `ls :`, and `ls :packs` when the box has that folder, removes
   :art_index.py and :packs/figures.pak where they are, and hard-resets the board, so the box plays its lineup with its
   own index again. Each of these commands is tried again while the probe still runs and keeps mpremote out. When the
   cleanup itself fails, its message holds the first error too, and says that both files may still be on the box.
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
- `count <N> starts` at each count; the App's `fps`, `time`, `phases`, `avg` and `heap` lines every 5 s
  (app.FPS_EVERY_MS) between them: 6 a count on an even 40 ms clock, 5 or 6 on the board. Every `fps figures` line
  between two count lines is that count's, because the count starts the App's interval (new_interval), which clears
  the counters of the `fps` and `time` lines. It does not clear gfx's phase sums (PHASES, PHASE_SUM), which only the
  frame of an `fps` line clears, so a count's first `phases` and `avg` lines can hold frames of the count before. The
  first set of lines of each count is left out. In this scene `avg`'s paint is the figures'
- `done`, after the last count. `game figures refused: ...` and no `done` when the box cannot make the pool, and a
  traceback when a picture does not draw.
The box's music plays, as for every game.

By hand, when the cleanup itself fails: `mpremote rm :art_index.py :packs/figures.pak`, then `mpremote reset`. The
next `python3 tools/box.py deploy` also removes an :art_index.py.
"""

import sys

COUNTS = (0, 1, 2, 4, 8, 16)  # figures at once, one count after the other
SECONDS = 30  # each count's, on the wall clock
GAITS = None  # the Mac part sends a copy with each character's gait row (name, pivot x, stride, speed) here
WIDTH, FEET = 320, 214  # the screen's width (gfx.WIDTH) and the row the soles stand on (games/rescue.py's FEET)
POSES = 12  # a run's poses
NIGHT = "figures_night"  # the still street
SPARE_S = 120  # the board run's time beside its counts: the boot, the load and the lines
LIMIT_S = len(COUNTS) * SECONDS + SPARE_S  # the board run's time limit with COUNTS (Bench.limit_s with others)
PACK, INDEX = "packs/figures.pak", "art_index.py"  # where the copies go on the board
WAIT = ["exec", "pass"]  # a cheap command: the board answers it once it is back from the hard reset
RECOVERY = "`mpremote rm :%s :%s`, then `mpremote reset`" % (INDEX, PACK)


class Done(Exception):
    pass


class Figure:
    """One moving figure: a character's gait row (name, pivot x, stride, speed) and its pictures' size (w, h). It holds
    the column of its hips (x), the way it faces (facing: 1 right, -1 left), the px it ran and the thousandths of a px
    carried to its next step (rest), all whole numbers, so a step makes no float (games/rescue.py's Fireman.run). Its
    hips stay between lo and hi, where both facings' pictures are whole on the screen: the left picture is the right
    one mirrored, so its pivot is w - 1 - pivot from its left. share: how far from lo to hi it starts."""

    def __init__(self, row, size, share, facing):
        self.name, self.pivot, self.stride, speed = row
        self.speed = round(speed)  # whole px a second
        self.w, self.h = size
        margin = max(self.pivot, self.w - 1 - self.pivot)  # the hips to the far side of either facing's picture
        self.lo, self.hi = margin, WIDTH - 1 - margin
        self.x, self.facing, self.ran, self.rest = int(self.lo + (self.hi - self.lo) * share), facing, 0, 0
        # its 24 pictures' names, made once (games/rescue.py's POSES): a frame formats no name
        self.right = ["figures_%s_r%d" % (self.name, i) for i in range(POSES)]
        self.left = ["figures_%s_l%d" % (self.name, i) for i in range(POSES)]

    def step(self, ms):
        """ms of running at its speed, in whole px with the carry. Past an edge it stands at the edge and turns at
        once, and the carry goes."""
        self.rest += self.facing * self.speed * ms
        px = self.rest // 1000
        self.rest -= px * 1000
        self.x += px
        self.ran += abs(px)
        if self.x < self.lo or self.x > self.hi:
            self.facing = 1 if self.x < self.lo else -1
            self.x = self.lo if self.x < self.lo else self.hi
            self.rest = 0

    def picture(self):
        """Its pose's picture: the pose follows the px it ran (games/rescue.py's run_pose), its side its facing."""
        return (self.right if self.facing > 0 else self.left)[self.ran * POSES // self.stride % POSES]

    def corner(self):
        """The picture's top left: its pivot (the hips' column on its last row) on (x, FEET)."""
        pivot = self.pivot if self.facing > 0 else self.w - 1 - self.pivot
        return self.x - pivot, FEET - self.h + 1


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


class CountClock:
    """The clock that steps through the counts, after each frame of the App (board()), on the wall clock from the first
    frame of the probe's game, after its load: that frame prints the pack line (pack answers it). At each change of
    count_at it prints `count N starts`, gives the game the count and starts the App's interval, so no fps line mixes
    two counts. After the last count it raises Done. ticks_ms and ticks_diff are time's."""

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


def game_class(rows):
    """The probe's game, a gfx.Game: Rescue's still street, and over it the first count of its 16 figures, figure i
    on rows[i % len(rows)] (gait rows), starting as the docstring says. It starts in play (TITLE_MS 0, as rain.py), and
    sets covers as Rescue does. A picture that does not draw raises, so an empty scene cannot pass. The count is set
    from outside (CountClock). play and paint loop by index, so a frame makes no list. The board part calls it, and a
    Mac test with games/ on the path."""
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
                row = rows[i % len(rows)]
                size = art["figures_%s_r0" % row[0]][:2]
                self.figures.append(Figure(row, size, i * 5 % n / (n - 1), 1 if i % 2 == 0 else -1))

        def play(self, pressed, held):
            for i in range(self.count):
                self.figures[i].step(self.ms)

        def paint_static(self, cv):
            drawn(cv, NIGHT, 0, 0)

        def paint(self, cv):
            for i in range(self.count):
                figure = self.figures[i]
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
    clock = CountClock(time.ticks_ms, time.ticks_diff, lambda: pack_line(s3lcd.pool, size))
    _frame = app.App.frame

    def frame(self):
        _frame(self)
        if isinstance(self.game, Probe):
            clock.after_frame(self)

    app.App.frame = frame
    try:
        app.run(games=(Probe,), knob=knob, speaker=speaker)
    except Done:
        pass
    memory()
    print("done")


# --- the Mac part ---

def text(out):
    """A board run's output as text: a timed-out one's is bytes (subprocess.run decodes only a finished command's), or
    None."""
    return out.decode("utf-8", "replace") if isinstance(out, bytes) else out or ""


def free_log(path):
    """path, or the first of its -2, -3, ... that no file has: a later board run never overwrites a log."""
    import os

    stem, ext = os.path.splitext(path)
    k = 1
    while os.path.exists(path):
        k += 1
        path = "%s-%d%s" % (stem, k, ext)
    return path


class Bench:
    """The Mac part's work on the box, through runner (a box.Mpremote, or a test's): check() is step 1; run() has
    art (art/figures.py, or a test's) paint and write the set (step 3), then steps 4 to 7. log: the first log's path
    (free_log picks the one written); sleep: the pause between two tries; counts: the copy's COUNTS, which set the
    board run's time limit."""

    def __init__(self, runner, art, log, sleep=None, counts=COUNTS):
        import time

        import box

        self.runner, self.art, self.log, self.box = runner, art, log, box
        self.sleep, self.logged = sleep or time.sleep, None
        self.counts, self.limit_s = counts, len(counts) * SECONDS + SPARE_S

    def tried(self, args, tries=None):
        """The runner's answer to args, tried again while mpremote cannot reach the board."""
        box = self.box
        return box.retried(self.runner, args, tries or box.PROBE_TRIES, box.RESET_PAUSE_S, self.sleep)

    def check(self):
        """Refuses a box that has an :art_index.py, before any copy: the cleanup would delete it."""
        if INDEX in self.box.board_names(self.tried(["ls", ":"])):
            raise SystemExit("refused: the box has an :%s. It is its real index (a deploy with --py: deploy without "
                             "--py first) or a shadow index that a failed cleanup left (remove it: %s)"
                             % (INDEX, RECOVERY))

    def run(self, capture):
        """Steps 3 to 7 with the CMU files of capture: the set painted and written, the copies, the board run, its
        lines and log, the cleanup. Answers the board run's lines."""
        import os
        import tempfile

        first, lines = None, []  # first: why a step or the board run failed
        with tempfile.TemporaryDirectory() as tmp:
            pack, index = self.art.write(tmp, capture)
            copy = os.path.join(tmp, "probe904_figures.py")
            with open(__file__) as f:
                source = f.read()
            with open(copy, "w") as f:
                f.write(filled(source, self.art.gaits(capture), self.counts))
            try:
                self.runner.run(["cp", pack, ":" + PACK])  # the pack first: a failed copy leaves no index naming it
                self.runner.run(["cp", index, ":" + INDEX])
                self.box.reset(self.runner, sleep=self.sleep)
                self.tried(WAIT, self.box.RESET_TRIES)
                said, first = self.board_run(copy)
                lines = self.keep(said)
            except Exception as e:
                first = self.failure(e)
                raise
            finally:
                self.clean(first)
        if first:
            raise SystemExit("refused: %s; the log is %s" % (first, self.logged))
        if not self.runner.dry_run and "done" not in lines:
            raise SystemExit("refused: the board run did not end with done: %s; the log is %s" % (
                lines[-1] if lines else "no output", self.logged))
        if self.logged:
            print("the log is %s" % self.logged)
        return lines

    def failure(self, e):
        """An error's line: a failed or missing tool as box.main says it, any other error as itself."""
        import subprocess

        if isinstance(e, (subprocess.CalledProcessError, FileNotFoundError)):
            return self.box.failure(e)
        return repr(e)

    def board_run(self, copy):
        """The copy run on the board once, within limit_s: its output, and why it failed or None."""
        import subprocess

        try:
            return self.runner.run(["run", copy], timeout=self.limit_s), None
        except subprocess.TimeoutExpired as e:
            return text(e.stdout) + text(e.stderr), "the board run took over %d s" % e.timeout
        except subprocess.CalledProcessError as e:
            return text(e.stdout) + text(e.stderr), "the board run failed with exit %d" % e.returncode

    def keep(self, said):
        """The board run's lines, printed and written to the first free log (a dry run's are none, and it writes no
        log)."""
        lines = [line.strip() for line in said.splitlines() if line.strip()]
        for line in lines:
            print(line)
        if not self.runner.dry_run:
            self.logged = free_log(self.log)
            with open(self.logged, "w") as f:
                f.write("".join(line + "\n" for line in lines))
        return lines

    def clean(self, first=None):
        """The copies that the board holds go, then a hard reset, so the box plays its lineup with its own index. A
        dry run's board holds both. When a command of it fails, it refuses with its error, first (the error before
        it, or None), what may be left, and the log when one was written."""
        box, dry = self.box, self.runner.dry_run
        try:
            root = box.board_names(self.tried(["ls", ":"]))
            folder = PACK.split("/")[0]
            packs = box.board_names(self.tried(["ls", ":" + folder])) if dry or folder + "/" in root else set()
            there = [":" + path for path, names in ((INDEX, root), (PACK, packs))
                     if dry or path.split("/")[-1] in names]
            if there:
                self.tried(["rm"] + there)
            box.reset(self.runner, sleep=self.sleep)
        except Exception as e:
            raise SystemExit("refused: the cleanup failed: %s%s; :%s and :%s may still be on the box: run %s%s" % (
                self.failure(e), "; before it: " + first if first else "", INDEX, PACK, RECOVERY,
                "; the log is %s" % self.logged if self.logged else ""))


def filled(source, rows, counts):
    """This file's source with GAITS filled in with the gait rows and COUNTS with counts, for the board (as
    probe844_import.py fills SET). Each line's start is replaced, so its comment stays. The default counts give the same
    COUNTS line, so the guard counts the lines and does not compare the copy with the source."""
    for old, new in (("\nGAITS = None", "\nGAITS = %r" % (tuple(rows),)),
                     ("\nCOUNTS = %r" % (COUNTS,), "\nCOUNTS = %r" % (tuple(counts),))):
        if source.count(old) != 1:
            raise ValueError("not one %s line in the probe" % old.strip())
        source = source.replace(old, new)
    return source


def counts_arg(text):
    """--counts' value as a tuple: whole numbers of 0 or more by commas, at least one, no repeat, in the order given.
    The start rule (game_class) needs a largest count n of 2 or more (it divides by n - 1) and not a multiple of 5 (then
    i * 5 mod n repeats start places)."""
    import argparse
    import re

    if not re.fullmatch(r"[0-9]+(,[0-9]+)*", text):
        raise argparse.ArgumentTypeError("not whole numbers of 0 or more by commas: %r" % text)
    counts = tuple(int(n) for n in text.split(","))
    if len(set(counts)) < len(counts):
        raise argparse.ArgumentTypeError("a count repeats: %s" % text)
    if max(counts) < 2 or max(counts) % 5 == 0:
        raise argparse.ArgumentTypeError("the largest count, %d, is under 2 or a multiple of 5: the start places "
                                         "(i * 5 mod n) / (n - 1) need neither" % max(counts))
    return counts


LOG = "logs/run-p904-2c.log"  # from the repository root: the first log's path (free_log)


def mac(argv, runner=None, art=None):
    """The Mac part from the command line: runner and art stand in for box.Mpremote and art/figures.py in a test."""
    import argparse
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    for folder in ("art", "tools"):
        if os.path.join(here, folder) not in sys.path:
            sys.path.insert(0, os.path.join(here, folder))
    import box
    import mocap

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print each board command, run none")
    parser.add_argument("--cmu", default=mocap.CMU_DIR, metavar="DIR", help="the CMU .asf and .amc files (%(default)s)")
    parser.add_argument("--counts", type=counts_arg, default=COUNTS, metavar="A,B,...",
                        help="the counts of figures, in this order (%s)" % ",".join("%d" % n for n in COUNTS))
    args = parser.parse_args(argv)
    if art is None:
        import figures as art
    bench = Bench(runner or box.Mpremote(args.dry_run), art, os.path.join(here, LOG), counts=args.counts)
    try:
        bench.check()
        bench.run(mocap.open_capture(parser, args.cmu))
    except (box.subprocess.CalledProcessError, FileNotFoundError) as e:
        raise SystemExit(box.failure(e))


if sys.implementation.name == "micropython":
    board()
elif __name__ == "__main__":
    mac(sys.argv[1:])
