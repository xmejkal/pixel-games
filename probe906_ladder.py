"""
P906 (#1285): the walking skeleton, a ladder mission on the game box with the fireman and the child at 96 px over
Rescue's night street (slice 0 of P900). He picks the fireman with the stick down, runs him to the ladder at the fire
station and holds it with FIRE. Then he picks the child with the stick up, runs it to the ladder's foot and climbs to
the roof's edge while the stick leans up. The app, the catalog, the lineup and the pool of the fifteen games do not
change: the probe lends the box a pack of its own for one sitting, and the box runs this game in a lineup of one, so
PICK reaches the game (games/app.py, App.frame).

This is the thin version (step 3 of the plan): the intro, the street, the ladder, the bar, the two figures, the pick
and a round that starts. The round's tasks, the climb, the tally, the result screen and the way out (PICK twice) come
with the whole round (step 5).

From the repository root, on the Mac, with the game code deployed (`python3 tools/box.py deploy <the lineup>`):

    python3 probe906_ladder.py [--dry-run] [--minutes N]

The Mac part:
1. paints the set mission (art/mission.py, about 25 s) from the CMU files in mocap.CMU_DIR, and writes its pack, an
   index of that pack alone and a copy of this file whose NUMBERS holds mission.numbers' answer into a temporary
   folder. It refuses with the capture's message (exit 2) when a file is missing, before any board command.
2. refuses a box that has an :art_index.py: its real index (a deploy with --py) or one that a failed removal left.
3. copies the pack to :packs/mission.pak, then the index to :art_index.py, the shadow index, so the pool is as big as
   this pack alone (tools/box.py, LentPack).
4. hard-resets the box, waits with `exec pass` until it answers, and runs the copy once from RAM within N minutes (60
   by default). Each line shows on the Mac as it comes and goes at once to the first free log of
   logs/run-p906-ladder.log, logs/run-p906-ladder-2.log and on (tools/box.py, ProbeRun).
5. in every case once the copies began: removes both copies where the box holds them. Then, in every case after the
   first board command, it hard-resets the box, so the box plays its lineup again. A Ctrl-C, a SIGTERM and a SIGHUP
   end the Mac part the same way.
A run that ended with `done` exits 0. A run that the time limit ended exits 0 when its lines hold a `p906 round` line.
Any other end is refused with its last line and the log's path. A failed removal is refused with what may be left
on the box and the way out by hand: `mpremote rm :art_index.py :packs/mission.pak`, then `mpremote reset`.
--dry-run paints and writes the set, prints each board command (the removal as for a box that holds both copies),
runs none and writes no log.

The game. FIRE is BOOT or the stick's push-button, which this file calls the click. The intro shows once in a
sitting, for 15 s (TITLE_MS) or until FIRE: the two tasks, the buttons and the way out. A round starts with READY for
600 ms, both figures standing at their start places and the child active. A new lean of the stick's y picks a figure:
up (UP) the child, down the fireman. The active figure runs with the stick's x and the other stands. A white arrow
is over the active figure. The bar at the top holds the two tasks and the way out in three rows of 8 px and is drawn
once. A yellow block beside a row marks the task of the moment.

The lines, from the box. Each line of the game starts with `p906`:
- `p906 rules lean 40 rest 20 ready 600 intro 15000 hold 24 pace 2`: the values
- `pack pool <B>` or `pack heap <B>`: whether s3lcd's pool holds the pack (P904's line)
- `p906 intro ends fire|time`
- `p906 round <n> starts after <ms>`: ms since the last round's end, 0 in round 1
- `done`, at the end. A box with no stick is refused: the traceback ends with `RuntimeError: p906 refused: no stick
  in the pin map ...`.
The App's own lines come between them: `game ladder`, and every 5 s `fps`, `time`, `phases`, `avg` and `heap`.
"""

import sys
import time

# --- the rules, in ms, px and small ints ---
LEAN = 40  # engine.actions.LEAN: an axis this far from the middle, of 100, leans
LEAN_REST = 20  # an axis under this far from the middle rests: the next lean is a new one
UP = -1  # the stick's y reads negative up (drivers/stick.py): a lean up picks the child, and it climbs while up leans
READY_MS = 600  # a round starts with READY: a lean that starts in it is the round's first pick, at its end
TITLE_MS = 15000  # the intro shows this long, or until FIRE
HOLD_PX = 24  # FIRE within this many px of his place makes the fireman hold the ladder
PACE = 2  # the figures run at their captured speed divided by this: half, a start value
WIDTH = 320  # the screen's width (gfx.WIDTH)
FEET = 214  # the row the soles stand on (games/rescue.py's FEET, art/mission.py's FEET)
FIREMAN, CHILD = 0, 1  # the list of the figures: the fireman is drawn first, the child in front of him
FIGURES = ("fireman", "child")  # each figure's word in the set's names and in the log
SET = "mission"  # the set the game loads: the pack that the Mac part lends the box (art/mission.py)
MOTIONS = (("fireman", "run"), ("fireman", "hold"), ("child", "run"), ("child", "climb"))  # the set's (figure, motion)
NUMBERS = None  # the Mac part sends a copy with art/mission.py's numbers here: the places, the gaits, the pivots

# --- what the screen shows, in px ---
BAR = ("1 FIREMAN: stick DOWN to ladder, FIRE", "2 CHILD: stick UP to ladder, UP climbs", "PICK twice: quit")
BAR_RECT = (0, 0, WIDTH, 24)  # the bar: three rows of 8 px, kept with a constant key, so it is drawn once
BAR_KEY = ("p906 bar",)
BAR_X = 10  # each row's words start here and end by x 314, the base bar's edge (gfx.Game.draw_hud)
BLOCK_X, BLOCK_W = 2, 6  # the task block: its left and its size, beside the task's row
ARROW_GAP = 6  # from the arrow's tip, and the mark's lowest row, to the top of the picture under it
# each shape's rows, from the top, each over a dark rim of 1 px all round (art/mission.py's Storyboard draws the same)
ARROW = (7, 5, 3, 1)  # the white arrow over the active figure: its tip lowest
MARK = (1, 3, 5, 7, 9, 7, 5, 3, 1)  # the yellow mark, the next thing to do: a diamond (drawn from step 5)
READY_AT = (100, 56)  # READY's top left: 5 letters of 24 px, under the bar and over the figures
INTRO = ("THE LADDER MISSION", "", "1 FIREMAN: stick DOWN picks him,", "  run to the ladder, FIRE: hold it",
         "2 CHILD: stick UP picks it,", "  run to the ladder, UP: climb", "",
         "FIRE = BOOT or the stick's click", "PICK twice: quit", "", "FIRE: start")
INTRO_RECT = (16, 40, 288, 152)  # the intro's dark panel, kept; a line every 12 px from 10 px under its top
INTRO_KEY = ("p906 intro",)


class Quit(Exception):
    """PICK twice: the sitting ends (the way out comes with step 5's Exit)."""


class Seen:
    """A FIRE button wrapped, so the game tells BOOT from the click (P905's). It keeps its last update in two
    attributes: pushed, whether that update saw a push, and held, the button's level. engine.actions.fold reads held as
    an attribute, so update() and forget() both refresh it."""

    def __init__(self, button):
        self.button, self.pushed, self.held = button, False, button.held

    def update(self, now_ms):
        self.pushed = self.button.update(now_ms)
        self.held = self.button.held
        return self.pushed

    def forget(self):
        """The button drops its pushes (the box was busy), so no push waits here either."""
        self.button.forget()
        self.pushed, self.held = False, self.button.held


def lean(v):
    """engine.actions.lean's rule, for the run: -1, 0 or 1. The file keeps its own copy because at its top it imports
    only sys and time, so the Mac part and the tests load it with no game code. A Mac test pins the two alike."""
    return 1 if v >= LEAN else -1 if v <= -LEAN else 0


class LeanEdge:
    """The edge of an axis (P905's): read(v) answers -1 or 1 once when a new lean starts, else 0. A lean starts at LEAN
    or more from the middle, and the axis rests under LEAN_REST, so a lean that wavers between the two answers once. A
    lean the other way is a new lean at once. v is the stick's x or y, -100 to 100: up and left read negative."""

    def __init__(self):
        self.on = 0  # the lean that answered and has not rested since: -1, 0 or 1

    def reset(self, v):
        """Starts from the axis as it is: a lean now is no new lean."""
        self.on = lean(v)

    def read(self, v):
        side = lean(v)
        if side and side != self.on:
            self.on = side
            return side
        if -LEAN_REST < v < LEAN_REST:
            self.on = 0
        return 0


class PackSource:
    """The one picture source of D26: a picture by figure, motion, pose and facing, from the set's pack. Each picture
    is made once, here: (name, dx, dy), its name and its top left dx px right and dy px down from the figure's place,
    its pivot's column on the soles' row, so a frame makes no name and no tuple. art: the index's ART (name: w, h, set,
    offset), whose sizes it reads; pivots: NUMBERS' pivot column of each motion facing right. The left picture is the
    right one mirrored, so its pivot is w - 1 - pivot. Another maker of pictures can stand behind the same four words.
    An index without a motion of MOTIONS is refused, naming its first picture."""

    def __init__(self, art, pivots):
        self.made = {}
        for figure, motion in MOTIONS:
            pivot, sides = pivots[figure, motion], []
            for side in "rl":
                poses = []
                while True:
                    name = "%s_%s_%s_%s%d" % (SET, figure, motion, side, len(poses))
                    if name not in art:
                        break
                    w, h = art[name][0], art[name][1]
                    poses.append((name, -pivot if side == "r" else pivot + 1 - w, 1 - h))
                if not poses:
                    raise RuntimeError("%s_%s_%s_%s0 is not in the index" % (SET, figure, motion, side))
                sides.append(tuple(poses))
            self.made.setdefault(figure, {})[motion] = tuple(sides)

    def poses(self, figure, motion):
        """(right, left): each a tuple of the motion's pictures, a pose each."""
        return self.made[figure][motion]

    def picture(self, figure, motion, pose, facing):
        """The picture of the pose facing right (facing 1) or left (-1)."""
        return self.made[figure][motion][0 if facing > 0 else 1][pose]


class Walker:
    """One figure that the stick's x runs (P905's SteeredFigure, changed for the mission): its place x, the column of
    its pivot, its facing (1 right, -1 left), the px it ran and the lean of its last run, all small ints. sub: a
    SubPixel (games/engine/subpixel.py) that keeps the part of a px carried to the next step. speed: px a second;
    stride: px of one run cycle; lo and hi: its run's ends, its place at the ladder and the last place where its
    pictures stay whole on the screen. run: (right, left), each a tuple of its run's pictures (PackSource's); stand:
    (right, left), its standing picture; hold_poses: (right, left), the picture it holds the ladder in, or None. holds:
    whether it holds the ladder: then it does not move. up: px its soles are over the soles' row, 0 on the street (the
    climb sets it, step 5)."""

    def __init__(self, sub, speed, stride, lo, hi, run, stand, hold_poses=None):
        self.sub, self.speed, self.stride, self.lo, self.hi = sub, speed, stride, lo, hi
        self.run, self.stand, self.hold_poses = run, stand, hold_poses
        self.put(lo, -1)

    def put(self, x, facing):
        """At x facing facing, standing on the street with no carry and no hold: a round's start."""
        self.x, self.facing, self.ran, self.lean, self.holds, self.up = x, facing, 0, 0, False, 0
        self.sub.reset()

    def walk(self, ms, lean):
        """ms of a frame with the stick's lean (-1, 0 or 1): 0 stands, else it faces the lean and runs in whole px with
        the carry. At an end of its run it stops, and the carry goes. While it holds it does not move."""
        self.lean = lean
        if not lean or self.holds:
            return
        self.facing = lean
        x = self.x + self.sub.step(lean * self.speed, ms)
        if x < self.lo or x > self.hi:
            x = self.lo if x < self.lo else self.hi
            self.sub.reset()
        self.ran += abs(x - self.x)
        self.x = x

    def hold(self, place):
        """FIRE: within HOLD_PX of place it holds the ladder there, until put() again. Answers whether it holds."""
        if not self.holds and -HOLD_PX <= self.x - place <= HOLD_PX:
            self.x, self.holds = place, True
        return self.holds

    def picture(self):
        """Its picture now: the hold while it holds, the standing picture at rest or leaning into the end of its run
        that it stands at, else the run's pose for the px it ran."""
        side = 0 if self.facing > 0 else 1
        if self.holds:
            return self.hold_poses[side]
        if not self.lean or self.x == (self.lo if self.lean < 0 else self.hi):
            return self.stand[side]
        poses = self.run[side]
        return poses[self.ran * len(poses) // self.stride % len(poses)]


class Round:
    """One round, with no drawing. In the thin version it starts, runs READY and the pick, and the active figure runs;
    its tasks, the climb, the tally and its end come with step 5. number: the round's number in the sitting; ended_ms:
    the last round's end on the frame's clock, None in round 1; figures: the two Walkers, the fireman first, at their
    start places; emit: where each `p906` line goes (print on the box, a list's append in a test). step(now_ms, ms,
    actions, boot, click) runs one frame. Its first frame starts the round: its line, and READY from that frame's clock,
    where the stick's lean is no pick (LeanEdge.reset). In READY the stick is read and its answer waits: a lean that
    starts in READY is the round's first pick, at READY's end. Then each new lean of the stick's y picks a figure, and
    the active figure runs with the stick's x while the other stands. The child is active at the start. The game draws
    from its state: figures, active, task (the task of the moment, 1 or 2) and ready."""

    def __init__(self, number, ended_ms, figures, emit):
        self.number, self.ended_ms, self.figures, self.emit = number, ended_ms, figures, emit
        self.start_ms, self.ready, self.active, self.task = None, True, CHILD, 1
        self.edge, self.waiting = LeanEdge(), 0  # waiting: a lean that started in READY

    def step(self, now_ms, ms, actions, boot, click):
        if self.start_ms is None:
            self.start(now_ms, actions)
        side = self.edge.read(actions.y)
        if self.ready:
            if side:
                self.waiting = side
            if time.ticks_diff(now_ms, self.start_ms) < READY_MS:
                return
            self.ready, side = False, self.waiting
        if side:
            self.pick(side)
        walk = lean(actions.x)
        for i in range(len(self.figures)):
            self.figures[i].walk(ms, walk if i == self.active else 0)

    def start(self, now_ms, actions):
        """The round's first frame of play."""
        self.start_ms = now_ms
        self.edge.reset(actions.y)
        self.emit("p906 round %d starts after %d" % (
            self.number, 0 if self.ended_ms is None else time.ticks_diff(now_ms, self.ended_ms)))

    def pick(self, side):
        """A new lean of the stick's y: UP picks the child, the other way the fireman. Step 5 scores it and logs it."""
        self.active = CHILD if side == UP else FIREMAN


def pack_line(pool, size):
    """Where the pack sits (P904's): pool (s3lcd.pool) answers size, the size the loader asked it for, when the pool
    holds it, and raises ValueError when the pool was made smaller, so the loader put the pack in the heap."""
    try:
        pool(size)
    except ValueError:
        return "pack heap %d" % size
    return "pack pool %d" % size


def game_class(boot, click, numbers, pool=None):
    """The probe's game, a gfx.Game named ladder on the set mission. boot and click: the two Seen FIRE buttons of the
    action map; numbers: NUMBERS; pool: s3lcd.pool on the box, for the pack line after the first load, or None. The
    base game runs setup() in its constructor and again after each result screen, so the picture source and the two
    walkers are made once in __init__, before the base's, and setup() only puts both figures at their start places and
    makes a new Round. step() notes the intro's end (step 5 reads Exit there first, on the frame's clock). play() hands
    each frame to the round with the frame's clock (self.last). The intro (draw_title), the bar (hud) and the result
    screen (draw_over, step 5) are its own. It imports gfx, pictures and engine.subpixel here, as the board part and a
    Mac test call it."""
    import gfx
    import pictures
    from engine.subpixel import SubPixel

    night, ladder = SET + "_night", SET + "_ladder"
    ladder_x, ladder_y = numbers["ladder"]
    starts = numbers["start"]

    def drawn(cv, name, x, y):
        if not pictures.draw(cv, name, x, y):
            raise RuntimeError("%s did not draw: no art" % name)

    def shape(cv, x, y, rows, colour):
        """Rows of widths from row y down, each centred on column x, over a dark rim of 1 px all round: first, for
        each row, a black rect 1 px wider on both sides and 1 px higher and lower. Plain fills, no text."""
        for k in range(len(rows)):
            w = rows[k]
            cv.fill(x - w // 2 - 1, y + k - 1, w + 2, 3, gfx.BLACK)
        for k in range(len(rows)):
            w = rows[k]
            cv.fill(x - w // 2, y + k, w, 1, colour)

    def walker(source, i):
        figure = FIGURES[i]
        run = source.poses(figure, "run")
        stand = numbers["stand"][figure]
        art = pictures.art_index.ART
        reach = max(dx + art[poses[0][0]][0] - 1 for poses in run for _, dx, _ in poses[:1])
        hold = None
        if figure == "fireman":
            right, left = source.poses(figure, "hold")
            hold = (right[0], left[0])
        return Walker(SubPixel(), numbers["speed"][figure] // PACE, numbers["stride"][figure], numbers["place"][i],
                      WIDTH - 1 - reach, run, (run[0][stand], run[1][stand]), hold)

    class Ladder(gfx.Game):
        name = "ladder"
        ART = (SET, None)
        TITLE_MS = TITLE_MS
        bg = gfx.BLACK
        accent = gfx.YELLOW

        def __init__(self):
            source = PackSource(pictures.art_index.ART, numbers["pivot"])
            self.figures = [walker(source, i) for i in range(len(FIGURES))]
            self.number, self.ended_ms, self.round = 0, None, None
            self.bar_draw, self.intro_draw = self.draw_bar, self.draw_intro  # bound once: a frame binds no method
            gfx.Game.__init__(self)

        def setup(self):
            self.covers = pictures.load(*self.ART)  # the street covers the screen, so no fill goes under it
            if pool is not None and self.number == 0:  # the first load made the pool
                print(pack_line(pool, pictures.art_index.PACKS[SET][1]))
            self.number += 1
            for i in range(len(self.figures)):
                self.figures[i].put(starts[i], -1)
            self.round = Round(self.number, self.ended_ms, self.figures, print)

        def step(self, now_ms, pressed, held):
            intro = self.state == gfx.TITLE
            gfx.Game.step(self, now_ms, pressed, held)
            if intro and self.state == gfx.PLAY:
                print("p906 intro ends %s" % ("fire" if pressed else "time"))

        def play(self, pressed, held):
            self.round.step(self.last, self.ms, self.stick, boot, click)

        def paint_static(self, cv):
            drawn(cv, night, 0, 0)
            drawn(cv, ladder, ladder_x, ladder_y)

        def paint(self, cv):
            r = self.round
            for i in range(len(r.figures)):  # the fireman first, the child in front of him
                f = r.figures[i]
                name, dx, dy = f.picture()
                drawn(cv, name, f.x + dx, FEET - f.up + dy)
            f = r.figures[r.active]
            top = FEET - f.up + f.picture()[2]
            shape(cv, f.x, top - ARROW_GAP - len(ARROW) + 1, ARROW, gfx.WHITE)
            if r.ready:
                cv.big("READY", READY_AT[0], READY_AT[1], gfx.WHITE, 3)

        def hud(self, cv):
            """The bar, drawn once with its constant key and copied in each frame after, then the task block over the
            copy, which covers what paint drew there."""
            cv.keep(BAR_KEY, BAR_RECT, self.bar_draw)
            cv.fill(BLOCK_X, 8 * (self.round.task - 1) + 1, BLOCK_W, BLOCK_W, gfx.YELLOW)

        def draw_bar(self, cv):
            """All 24 rows, as a new strip is black: the dark, then the three rows, white."""
            cv.fill(BAR_RECT[0], BAR_RECT[1], BAR_RECT[2], BAR_RECT[3], gfx.DARK)
            for k in range(len(BAR)):
                cv.text(BAR[k], BAR_X, 8 * k, gfx.WHITE)

        def draw_title(self, cv):
            """The intro: its panel, kept, over the street and the ladder."""
            cv.keep(INTRO_KEY, INTRO_RECT, self.intro_draw)

        def draw_intro(self, cv):
            x, y, w, h = INTRO_RECT
            cv.fill(x, y, w, h, gfx.DARK)
            cv.box(x, y, w, h, gfx.YELLOW)
            for k in range(len(INTRO)):
                cv.text(INTRO[k], x + 8, y + 10 + 12 * k, gfx.YELLOW if k == 0 else gfx.WHITE)

    return Ladder


def board():
    """The board part: the knob's pads first, as main.py takes them at boot, then the box's action map with both FIRE
    buttons wrapped (Seen), then the App with the probe's game alone, silent and with no knob, so PICK reaches the
    game. It refuses a pin map with no stick. PICK twice (Quit) ends the run with `done`."""
    import pins
    from drivers import encoder

    encoder.take_pads(pins.ENC_A, pins.ENC_B)  # first: until here a turn of the knob types into the console (P757)
    import app
    from engine.actions import ActionMap

    found = app.open_action_map()  # a map with a stick has two FIRE buttons: BOOT and the stick's switch
    if found.stick is None:
        raise RuntimeError("p906 refused: no stick in the pin map (pins.JOY_X): the probe needs the stick")
    boot, click = Seen(found.fire_bindings[0]), Seen(found.fire_bindings[1])
    action_map = ActionMap((boot, click), found.pick_bindings, found.encoder, found.stick)
    print("p906 rules lean %d rest %d ready %d intro %d hold %d pace %d" % (LEAN, LEAN_REST, READY_MS, TITLE_MS,
                                                                           HOLD_PX, PACE))
    try:
        import s3lcd
        pool = s3lcd.pool
    except (ImportError, AttributeError):  # no s3lcd, or an older image without the pool: no pack line
        pool = None
    try:
        app.run(games=(game_class(boot, click, NUMBERS, pool),), knob=None, speaker=None, action_map=action_map)
    except Quit:
        pass
    print("done")


# --- the Mac part ---

LOG = "logs/run-p906-ladder.log"  # from the repository root: the first log's path (box.ProbeRun.free_log)
MINUTES = 60  # the run's time limit; PICK twice ends it sooner
WAIT = ["exec", "pass"]  # a cheap command: the box answers it once it is back from the hard reset


def filled(source, numbers):
    """This file's source with NUMBERS filled in, for the box (as P904's probe fills GAITS). The line's start is
    replaced, so its comment stays."""
    old = "\nNUMBERS = None"
    if source.count(old) != 1:
        raise ValueError("not one NUMBERS = None line in the probe")
    return source.replace(old, "\nNUMBERS = %r" % (numbers,))


def minutes_arg(text):
    """--minutes' value: a whole number of 1 or more."""
    import argparse

    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError("not a whole number of 1 or more: %r" % text)
    return int(text)


def said(box, e):
    """An error's line: a failed or missing tool as box.main says it, any other error as itself."""
    if isinstance(e, (box.subprocess.CalledProcessError, FileNotFoundError)):
        return box.failure(e)
    return repr(e)


def sitting(box, lent, run, files, limit_s, sleep):
    """Steps 3 and 4: the copies, the reset and the run, and the removal in every case once the copies began. files:
    the pack's, the index's and the copy's paths. Answers how the run ended (ProbeRun's DONE, LIMIT or FAILED)."""
    pack, index, copy = files
    runner, first = lent.runner, None
    try:
        lent.lend(pack, index)
        box.reset(runner, sleep=sleep)
        box.retried(runner, WAIT, box.RESET_TRIES, box.RESET_PAUSE_S, sleep)
        return run.run(copy, limit_s)
    except BaseException as e:
        first = said(box, e)
        raise
    finally:
        try:
            lent.remove()
        except Exception as e:  # noqa: BLE001  said with what may be left
            before = first or run.why
            raise SystemExit("refused: the removal failed: %s%s; :%s and :%s may still be on the box: run %s%s" % (
                said(box, e), "; before it: " + before if before else "", lent.INDEX, lent.pack, lent.recovery(),
                "; the log is %s" % run.logged if run.logged else ""))


def mac(argv, runner=None, sleep=None, art=None):
    """The Mac part from the command line: runner, sleep and art stand in for box.Mpremote, time.sleep and
    art/mission.py in a test."""
    import argparse
    import os
    import tempfile

    here = os.path.dirname(os.path.abspath(__file__))
    for folder in ("art", "tools"):
        if os.path.join(here, folder) not in sys.path:
            sys.path.insert(0, os.path.join(here, folder))
    import box

    if art is None:
        import mission as art
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print each board command, run none")
    parser.add_argument("--minutes", type=minutes_arg, default=MINUTES, metavar="N",
                        help="the run's time limit in minutes (%(default)s)")
    args = parser.parse_args(argv)
    capture = art.capture(parser)  # before any board command: the box plays on while the set is painted
    runner, sleep = runner or box.Mpremote(args.dry_run), sleep or time.sleep
    lent, run = box.LentPack(runner, art.SET, sleep), box.ProbeRun(runner, os.path.join(here, LOG))
    with tempfile.TemporaryDirectory() as tmp:
        painted = art.painted(capture)
        pack, index = art.write(tmp, painted)
        copy = os.path.join(tmp, os.path.basename(__file__))
        with open(os.path.abspath(__file__)) as f:
            source = f.read()
        with open(copy, "w") as f:
            f.write(filled(source, art.numbers(painted)))
        try:
            try:
                lent.check()
                end = sitting(box, lent, run, (pack, index, copy), args.minutes * 60, sleep)
            finally:
                box.reset(runner, sleep=sleep)  # also after a Ctrl-C, a SIGTERM or a SIGHUP (main): the lineup again
        except box.Refused as e:
            raise SystemExit("refused: %s" % e)
        except (box.subprocess.CalledProcessError, FileNotFoundError) as e:
            raise SystemExit(box.failure(e))
    if end == run.LIMIT and [line for line in run.lines if line.startswith("p906 round ")]:
        print("the time limit of %d minutes ended the sitting" % args.minutes)
    elif not runner.dry_run and (end != run.DONE or run.lines[-1:] != ["done"]):
        raise SystemExit("refused: %s: %s; the log is %s" % (
            run.why or "the run ended with no done line", run.lines[-1] if run.lines else "no output", run.logged))
    if run.logged:
        print("the log is %s" % run.logged)


def main(argv):
    """The Mac part from the command line. A SIGTERM or a SIGHUP (a closed terminal, a session that ends) ends it as a
    Ctrl-C does: the handler raises SystemExit, so stream kills the board run's mpremote, and the removal and the
    reset run."""
    import signal

    def stop(signum, frame):
        raise SystemExit("stopped by signal %d: the box is reset" % signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)
    mac(argv)


if sys.implementation.name == "micropython":
    board()
elif __name__ == "__main__":
    main(sys.argv[1:])
