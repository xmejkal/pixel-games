"""
P905 (#1284): the switch prototype. The game box runs a small test game with two of Rescue's figures, the fireman and
the child, and seven ways to switch between them. The game counts each switch, so the log shows for each way whether
the PO met his pass line: 10 switches in a row with no wrong figure (D35). The app, the catalog and the box's lineup
do not change. The probe runs one game, so PICK picks no other game and the game reads it, and the App has no knob,
so the knob's turn steps no volume and the game reads it (games/app.py, App.frame).

Deploy the game code and the rescue pack first (`python3 tools/box.py deploy --all`), then, from the repository root,
on the Mac:

    python3 probe905_switch.py [--dry-run] [--minutes N]

The Mac part:
1. reads `ls :`, then `ls :packs` when the box has that folder, and refuses a box without :packs/rescue.pak.
2. hard-resets the box and waits with `exec pass` until the box answers.
3. runs this file once on the box, from RAM, within N minutes (60 by default). It shows each line on the Mac as it
   comes and writes it at once to the first free log of logs/run-p905-switch.log, logs/run-p905-switch-2.log and on,
   so a log is never overwritten, and a Ctrl-C or a killed Mac session keeps every line that was played
   (tools/box.py, ProbeRun).
4. hard-resets the box in every case, so the box plays its lineup again.
A run that QUIT ended, whose last line is `done`, exits 0. A run that the time limit ended exits 0 when its lines hold a `p905 ways` line, so a
run that hung before the menu does not pass as a play. Any other end is refused with its last line and the log's path.
--dry-run prints each board command and runs none, and writes no log.

The game. FIRE is BOOT or the stick's push-button, which this file calls the click. The menu lists the seven ways,
each with its best streak and PASS once a round of it passed, and QUIT. The stick's up and down move the cursor, and
FIRE starts a round of the row's way. QUIT asks for FIRE a second time. A round starts with READY for 600 ms. Then
each task wants the figure that is not active (the one he holds), with a ring on the street and the wanted figure's
name. He switches, walks the wanted figure to the ring with the stick's x, and presses FIRE there. The fireman sprays
and the child waves for 400 ms. WRONG shows for 400 ms when a task turns wrong. The result card names the way, the
end, the streak and the best streak. After 900 ms FIRE goes back to the menu, and the cursor is on the way he played.

The seven ways (WAYS):
- stick: a new lean of the stick's y. Up picks the fireman, down the child. FIRE acts.
- click: a push of the click takes the other figure. BOOT acts.
- double: a second push of FIRE at most 300 ms (DOUBLE_MS) after the first takes the other figure. A push with no
  second one acts 300 ms later, where the figure then stands.
- hold: FIRE held 400 ms (HOLD_MS) or longer takes the other figure, once for each hold. A release before it acts, and
  so does a tap so short that the box saw no level.
- pick: a push of PICK (D14) takes the other figure. Never hold it: a hold of about 5 s powered an older board off
  (bench.md). FIRE acts.
- knob: a turn. Its positive detents pick the child and the other way the fireman, by the encoder's sign. FIRE acts.
- auto: the control. The game makes the wanted figure active at each task's start. FIRE acts.
The stick and the knob stop at the list's ends, so a step past an end changes nothing (`same`). The four button ways
take the other figure. 300 ms and 400 ms are Android's DOUBLE_TAP_TIMEOUT and DEFAULT_LONG_PRESS_TIMEOUT
(core/java/android/view/ViewConfiguration.java at commit 8b948e5 of the aosp-mirror). His play decides them.

The count (Tally). A switch is each change of the active figure. In a task the first switch gives the wanted figure:
`first`. A switch away from the wanted figure is `extra`, and the switch that brings it back is `back`. An act of the
figure that the task does not want is `other`. An act of the wanted figure away from its ring is `stray`, and at the
ring (REACH_PX) `reached`, which ends the task. A task with an `extra` or an `other` is wrong, once. A task that ends
with neither is clean, and the streak is the clean tasks in a row. In one frame the act comes before the switches. A
round ends with `pass` at a streak of 10, with `fail` at the event that makes its third wrong task, with `idle` after
20 s with no task ended, and the control way with `control` after 10 tasks, never with `pass`.

The lines, from the box. Each line of the game starts with `p905`:
- `p905 ways stick,click,double,hold,pick,knob,auto streak 10 wrong 3 double 300 hold 400`: the ways and the values
- `p905 inputs stick yes knob yes`: whether the box has a stick and a knob
- `p905 round <way> starts`
- `p905 task <n> wants <figure> at <x>`: a task, its wanted figure and its ring's x
- `p905 switch <figure> first|extra|back|same`: the active figure after a step of the way
- `p905 act <figure> reached|other|stray`: the figure that acted
- `p905 task <n> clean|wrong streak <s> wrong <w>`: a task that ended, the round's streak and wrong tasks after it
- `p905 round <way> ends pass|fail|idle|control streak <s> best <b> tasks <t> wrong <w>`
- `done`, after QUIT. A traceback and no `done` when the run failed. A box with no stick is refused with
  `p905 refused` before any `p905 ways` line.
The App's own lines come between them: `game switchtest`, `switch switchtest ...`, and every 5 s `fps`, `time`,
`phases`, `avg` and `heap`. The box is silent.

By hand, when the box does not come back: `mpremote reset`. Nothing is copied to the box, so the reset is the whole
cleanup.
"""

import sys
import time

# --- the rules, in ms, px and small ints ---
LEAN = 40  # engine.actions.LEAN: an axis this far from the middle, of 100, leans
LEAN_REST = 20  # an axis under this far from the middle rests: the next lean is a new one
DOUBLE_MS = 300  # a second push at most this long after the first is a double tap (Android's DOUBLE_TAP_TIMEOUT)
HOLD_MS = 400  # FIRE held this long is a hold (Android's DEFAULT_LONG_PRESS_TIMEOUT)
STREAK_TO_PASS = 10  # clean tasks in a row that pass a round: the PO's line (D35)
WRONG_MAX = 3  # the wrong tasks that end a round with fail
WALK_LEFT, WALK_RIGHT = 96, 304  # px: the hips walk between these, the street that both of Rescue's ranges share
TASK_MIN_PX = 60  # px at least from the wanted figure to its ring
REACH_PX = 8  # px from the hips to the ring's middle that reach it
READY_MS = 600  # a round starts with READY, which reads no input
ACT_MS = 400  # the fireman sprays or the child waves this long after an act
MARK_MS = 400  # WRONG shows this long after a task turns wrong
IDLE_MS = 20000  # a round with no task ended for this long ends: since READY's end or the last task's end
FIREMAN, CHILD = 0, 1  # the list of the figures
NAMES = ("fireman", "child")  # each figure's word in the log
START_X = (140, 260)  # px: each figure's hips at a round's start; the fireman is active first

# How a round ends (Round.end), and its word in the log
PLAYING, PASS, FAIL, IDLE, CONTROL = range(5)
ENDS = ("playing", "pass", "fail", "idle", "control")
TASK_WORDS = ("clean", "wrong")  # a task's word in its line, by whether it is wrong
CARD_WORDS = ("", "PASS", "%d WRONG" % WRONG_MAX, "IDLE", "CONTROL")  # each end's word on the result card

# What a switch or an act counts as (Tally), and its word in the log
FIRST, EXTRA, BACK, SAME, REACHED, OTHER, STRAY = range(7)
WORDS = ("first", "extra", "back", "same", "reached", "other", "stray")


class Quit(Exception):
    """QUIT pressed twice in the menu: the run ends."""


class Seen:
    """A FIRE button wrapped, so the game tells BOOT from the click. It keeps its last update in two attributes:
    pushed, whether that update saw a push, and held, the button's level. engine.actions.fold reads held as an
    attribute, so update() and forget() both refresh it."""

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
    """engine.actions.lean's rule, for the walk: -1, 0 or 1. The board runs this file from RAM, so it keeps its own
    copy, and a Mac test pins the two alike."""
    return 1 if v >= LEAN else -1 if v <= -LEAN else 0


class LeanEdge:
    """The edge of an axis: read(v) answers -1 or 1 once when a new lean starts, else 0. A lean starts at LEAN or more
    from the middle, and the axis rests under LEAN_REST, so a lean that wavers between the two answers once. A lean the
    other way is a new lean at once. v is the stick's x or y, -100 to 100: up and left read negative. It is not
    engine.actions.lean, which answers the level and which the walk uses."""

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


class Way:
    """One way to switch, a strategy. reset(now_ms, actions, boot, click) starts it from the inputs as they are: the
    lean now is no new lean, a FIRE that is down needs a new push, and a push that waits is dropped. read(now_ms,
    actions, boot, click) reads one frame and leaves its answer in steps (along the list of the figures: + toward the
    child, - toward the fireman) and acts (whether FIRE acts), so a frame makes no tuple. actions is the frame's
    engine.actions.Actions, boot and click the two Seen FIRE buttons. name: the log's word; label: the screen's; hint:
    one line of the top bar, 40 characters at most; wraps: whether a step past the list's end comes round (false for
    the stick and the knob, whose list stops at its ends); control: true for the way that is no test."""

    name = label = hint = ""
    wraps, control = True, False

    def __init__(self):
        self.steps, self.acts = 0, False

    def reset(self, now_ms, actions, boot, click):
        self.steps, self.acts = 0, False

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = 0, actions.fire.pressed


class StickWay(Way):
    """A new lean of the stick's y picks by direction: up the fireman, down the child."""

    name, label, hint, wraps = "stick", "STICK UP/DOWN", "up: FIREMAN, down: CHILD  act: FIRE", False

    def __init__(self):
        Way.__init__(self)
        self.edge = LeanEdge()

    def reset(self, now_ms, actions, boot, click):
        Way.reset(self, now_ms, actions, boot, click)
        self.edge.reset(actions.y)

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = self.edge.read(actions.y), actions.fire.pressed


class ClickWay(Way):
    """A push of the click (the stick's push-button) takes the other figure, and a push of BOOT acts."""

    name, label, hint = "click", "STICK CLICK", "click: switch  act: BOOT"

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = 1 if click.pushed else 0, boot.pushed


class DoubleWay(Way):
    """A second push of FIRE at most DOUBLE_MS after the first takes the other figure. A push with no second one acts
    DOUBLE_MS later. A frame reads its push before the time, so a second push at exactly DOUBLE_MS switches. After a
    double tap the count starts again, so a third push is a first one. A push past DOUBLE_MS is a new first one, and
    the push before it acts in that frame."""

    name, label, hint = "double", "DOUBLE TAP", "FIRE twice: switch  FIRE once: act"

    def __init__(self):
        Way.__init__(self)
        self.waiting, self.first_ms = False, 0  # a first push that waits for a second, and its frame's clock

    def reset(self, now_ms, actions, boot, click):
        Way.reset(self, now_ms, actions, boot, click)
        self.waiting = False

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = 0, False
        late = self.waiting and time.ticks_diff(now_ms, self.first_ms) > DOUBLE_MS
        if actions.fire.pressed:
            if self.waiting and not late:
                self.steps, self.waiting = 1, False
                return
            self.acts = late
            self.waiting, self.first_ms = True, now_ms
            return
        if self.waiting and time.ticks_diff(now_ms, self.first_ms) >= DOUBLE_MS:
            self.acts, self.waiting = True, False


class HoldWay(Way):
    """FIRE held for HOLD_MS or longer takes the other figure, once for each hold. A hold starts at a push and ends
    when both FIRE buttons are up. A release before HOLD_MS acts, and a release after it does not. A tap so short that
    the box saw no level acts at once. The length is the frame's clock, so a release that a frame sees at HOLD_MS or
    later is a hold."""

    name, label, hint = "hold", "HOLD FIRE", "hold FIRE: switch  tap FIRE: act"

    def __init__(self):
        Way.__init__(self)
        self.down, self.since_ms, self.switched = False, 0, False

    def reset(self, now_ms, actions, boot, click):
        Way.reset(self, now_ms, actions, boot, click)
        self.down = False

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = 0, False
        fire = actions.fire
        if fire.pressed and not self.down:
            if not fire.held:
                self.acts = True
                return
            self.down, self.since_ms, self.switched = True, now_ms, False
            return
        if not self.down:
            return
        long = time.ticks_diff(now_ms, self.since_ms) >= HOLD_MS
        if long and not self.switched:
            self.steps, self.switched = 1, True
        if not fire.held:
            self.down, self.acts = False, not long


class PickWay(Way):
    """A push of PICK (the board's D14 button) takes the other figure, and FIRE acts. Never a hold: a hold of about 5 s
    powered an older board off (bench.md)."""

    name, label, hint = "pick", "PICK (D14)", "press PICK, never hold  act: FIRE"

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = 1 if actions.pick.pressed else 0, actions.fire.pressed


class KnobWay(Way):
    """A turn of the knob picks by direction: its positive detents step toward the child. Which way that is on the box
    follows the encoder's sign, so the hint names no direction."""

    name, label, hint, wraps = "knob", "KNOB", "knob: one way FIREMAN, other way CHILD", False

    def read(self, now_ms, actions, boot, click):
        self.steps, self.acts = actions.turn, actions.fire.pressed


class AutoWay(Way):
    """The control: the game makes the wanted figure active at each task's start (Round), so no input switches."""

    name, label, hint, control = "auto", "AUTO (control)", "the game switches for you  act: FIRE", True


WAYS = (StickWay, ClickWay, DoubleWay, HoldWay, PickWay, KnobWay, AutoWay)  # the menu's order
QUIT = len(WAYS)  # the menu's last row


class Tally:
    """The count of one round, in whole numbers. A task wants the figure that is not active at its start, so its first
    switch gives the wanted figure: FIRST. Then a switch away from the wanted figure is EXTRA, and the switch that
    brings it back is BACK, neither wrong nor clean. An act of the figure that the task does not want is OTHER, an act
    of the wanted figure away from the ring STRAY (not wrong), and at the ring REACHED, which ends the task. A task is
    wrong at its first EXTRA or OTHER, once however many it had, and the streak goes to 0 at once. A task that ends
    with no EXTRA and no OTHER had one switch: it is clean, and the streak grows. streak: the clean tasks in a row;
    best: the round's longest streak; wrong: its wrong tasks; tasks: its tasks that ended."""

    def __init__(self):
        self.streak = self.best = self.wrong = self.tasks = 0
        self.switches, self.marked = 0, False  # the task's switches, and whether it is wrong

    def start(self):
        """A new task."""
        self.switches, self.marked = 0, False

    def switch(self, to_wanted):
        """A change of the active figure: to_wanted, whether it now is the wanted one. Answers FIRST, EXTRA or BACK."""
        self.switches += 1
        if self.switches == 1:
            return FIRST
        if to_wanted:
            return BACK
        self.mark()
        return EXTRA

    def act(self, wanted, at_ring):
        """An act of the active figure: wanted, whether it is the wanted one; at_ring, whether it is in reach of the
        ring. Answers OTHER, STRAY or REACHED."""
        if not wanted:
            self.mark()
            return OTHER
        if not at_ring:
            return STRAY
        self.tasks += 1
        if not self.marked:
            self.streak += 1
            self.best = max(self.best, self.streak)
        return REACHED

    def mark(self):
        """The task is wrong, once."""
        if not self.marked:
            self.marked, self.streak = True, 0
            self.wrong += 1

    def passed(self):
        return self.streak >= STREAK_TO_PASS

    def failed(self):
        return self.wrong >= WRONG_MAX


def ring_x(dice, x):
    """The next ring's x for the wanted figure at x: one draw of dice (a gfx.Dice) over the places of the walk that are
    TASK_MIN_PX or more from x, left of it first."""
    left = max(0, x - TASK_MIN_PX - WALK_LEFT + 1)  # WALK_LEFT to x - TASK_MIN_PX
    right = max(0, WALK_RIGHT - (x + TASK_MIN_PX) + 1)  # x + TASK_MIN_PX to WALK_RIGHT
    k = dice.below(left + right)
    return WALK_LEFT + k if k < left else x + TASK_MIN_PX + k - left


def reaches(x, ring):
    """Whether hips at x reach the ring: within REACH_PX of its middle."""
    return abs(x - ring) <= REACH_PX


class SteeredFigure:
    """One figure that the stick's x walks: its hips' x, its facing (1 right, -1 left), the px it ran, the thousandths
    of a px carried to its next step (rest) and the lean of its last walk, all whole numbers, as games/rescue.py's
    Fireman.run. speed in px a second, stride the px of one run cycle, h its pictures' height. runs and acts are
    (right, left), each a tuple of (name, width) pairs made once, so a frame makes no name: its run cycle, and the act's
    cycle at act_pose_ms a pose. stands: (right, left), one pair each, for the picture it stands in, or None to stand
    in the run's pose where it stopped. Its hips are at its picture's middle."""

    def __init__(self, x, facing, speed, stride, h, runs, acts, act_pose_ms, stands=None):
        self.x, self.facing, self.ran, self.rest, self.lean = x, facing, 0, 0, 0
        self.speed, self.stride, self.h = speed, stride, h
        self.runs, self.acts, self.act_pose_ms, self.stands = runs, acts, act_pose_ms, stands

    def walk(self, ms, lean):
        """ms of a frame with the stick's lean (-1, 0 or 1): 0 stands, else it faces the lean and walks, in whole px
        with the carry. At an end of the walk it stops, and the carry goes."""
        self.lean = lean
        if not lean:
            return
        self.facing = lean
        self.rest += lean * self.speed * ms
        px = self.rest // 1000
        self.rest -= px * 1000
        x = self.x + px
        if x < WALK_LEFT or x > WALK_RIGHT:
            x, self.rest = WALK_LEFT if x < WALK_LEFT else WALK_RIGHT, 0
        self.ran += abs(x - self.x)
        self.x = x

    def picture(self, act_ms):
        """Its (name, width) now: the act's pose act_ms after its act started (act_ms -1: no act), else standing its
        stand picture, else the run's pose for the px it ran."""
        side = 0 if self.facing > 0 else 1
        if act_ms >= 0:
            names = self.acts[side]
            return names[act_ms // self.act_pose_ms % len(names)]
        if not self.lean and self.stands:
            return self.stands[side]
        names = self.runs[side]
        return names[self.ran * len(names) // self.stride % len(names)]


class Round:
    """One round of one way, with no drawing. way: a Way; figures: the two SteeredFigures, the fireman first; dice: a
    gfx.Dice for the rings; emit: where each `p905` line goes (print on the box, a list's append in a test); now_ms:
    the round's start on the frame's clock. step(now_ms, ms, actions, boot, click) runs one frame in this order: READY,
    the way's read, the act, the switches, the walk, the round's end. During READY every frame resets the way and reads
    nothing, so the way starts from the inputs of READY's last frame and that frame's pushes are dropped. The first task
    starts in READY's first frame after it. An act comes before the switches: a REACHED ends the task and starts the
    next one at once, so a switch in its frame is the next task's. A PASS, a CONTROL or a FAIL ends the round at its
    event and the rest of the frame does not run; IDLE is the frame's last check. The game draws from its state:
    figures, active, wanted, ring, tally, ready, act_ms(i), marking() and end (PLAYING until it ends)."""

    def __init__(self, way, figures, dice, emit, now_ms):
        self.way, self.figures, self.dice, self.emit = way, figures, dice, emit
        self.start_ms = self.now = self.since_ms = now_ms  # since_ms: the idle's start
        self.ready, self.end, self.tally = True, PLAYING, Tally()
        self.active, self.wanted, self.ring = FIREMAN, CHILD, -1  # no ring until the first task
        self.act_at, self.act_figure, self.mark_at = now_ms, -1, None
        emit("p905 round %s starts" % way.name)

    def step(self, now_ms, ms, actions, boot, click):
        self.now = now_ms
        if self.end != PLAYING:
            return
        way = self.way
        if self.ready:
            if time.ticks_diff(now_ms, self.start_ms) < READY_MS:
                way.reset(now_ms, actions, boot, click)
                return
            self.ready, self.since_ms = False, time.ticks_add(self.start_ms, READY_MS)
            self.next_task()
        way.read(now_ms, actions, boot, click)
        if way.acts:
            self.act(now_ms)
            if self.end != PLAYING:
                return
        if way.steps:
            self.switch(now_ms, way.steps)
            if self.end != PLAYING:
                return
        walk = lean(actions.x)
        for i in range(len(self.figures)):
            self.figures[i].walk(ms, walk if i == self.active else 0)
        if time.ticks_diff(now_ms, self.since_ms) >= IDLE_MS:
            self.finish(IDLE)

    def next_task(self):
        """A task: it wants the figure that is not active, at a ring TASK_MIN_PX or more from it. The control way makes
        the wanted figure active at once, and that switch is the task's first."""
        self.wanted = CHILD if self.active == FIREMAN else FIREMAN
        self.ring = ring_x(self.dice, self.figures[self.wanted].x)
        self.tally.start()
        self.emit("p905 task %d wants %s at %d" % (self.tally.tasks + 1, NAMES[self.wanted], self.ring))
        if self.way.control:
            self.active = self.wanted
            self.emit("p905 switch %s %s" % (NAMES[self.active], WORDS[self.tally.switch(True)]))

    def act(self, now_ms):
        tally, a = self.tally, self.active
        wrong = tally.wrong
        said = tally.act(a == self.wanted, reaches(self.figures[a].x, self.ring))
        self.emit("p905 act %s %s" % (NAMES[a], WORDS[said]))
        self.act_at, self.act_figure = now_ms, a
        if tally.wrong != wrong:
            self.mark_at = now_ms
        if said != REACHED:
            if tally.failed():
                self.finish(FAIL)
            return
        self.emit("p905 task %d %s streak %d wrong %d" % (tally.tasks, TASK_WORDS[tally.marked], tally.streak,
                                                          tally.wrong))
        self.since_ms = now_ms
        if self.way.control:
            if tally.tasks >= STREAK_TO_PASS:
                self.finish(CONTROL)
                return
        elif tally.passed():
            self.finish(PASS)
            return
        self.next_task()

    def switch(self, now_ms, steps):
        """steps along the list of the figures: round it when the way wraps, else stopped at its ends. A step that
        changes nothing is SAME."""
        n = len(self.figures)
        to = (self.active + steps) % n if self.way.wraps else max(0, min(n - 1, self.active + steps))
        if to == self.active:
            self.emit("p905 switch %s %s" % (NAMES[to], WORDS[SAME]))
            return
        tally, wrong = self.tally, self.tally.wrong
        self.active = to
        self.emit("p905 switch %s %s" % (NAMES[to], WORDS[tally.switch(to == self.wanted)]))
        if tally.wrong != wrong:
            self.mark_at = now_ms
        if tally.failed():
            self.finish(FAIL)

    def finish(self, end):
        self.end, tally = end, self.tally
        self.emit("p905 round %s ends %s streak %d best %d tasks %d wrong %d" % (
            self.way.name, ENDS[end], tally.streak, tally.best, tally.tasks, tally.wrong))

    def act_ms(self, i):
        """ms since figure i's act, while its act shows (ACT_MS), else -1."""
        if i != self.act_figure:
            return -1
        ms = time.ticks_diff(self.now, self.act_at)
        return ms if ms < ACT_MS else -1

    def marking(self):
        """Whether WRONG shows: MARK_MS from the moment a task turned wrong."""
        return self.mark_at is not None and time.ticks_diff(self.now, self.mark_at) < MARK_MS


class Menu:
    """The menu, with no drawing: a row for each way and QUIT last. The cursor moves one row for each new lean of the
    stick's y and stops at both ends. FIRE starts the row's way. QUIT asks for FIRE a second time, and a move of the
    cursor takes the first press back. best and marked: each way's best streak, and whether a round of it passed (or,
    for the control way, ended with CONTROL). changes counts each change, so the drawing knows when to draw again.
    reset(actions) runs each time the menu comes back, in place of a step: the lean now is no new lean, and the
    frame's push starts nothing."""

    def __init__(self):
        self.cursor, self.armed, self.changes, self.edge = 0, False, 0, LeanEdge()
        self.best, self.marked = [0] * len(WAYS), [False] * len(WAYS)

    def reset(self, actions):
        self.edge.reset(actions.y)
        self.armed, self.changes = False, self.changes + 1

    def step(self, actions):
        """One frame: the row whose way FIRE starts, QUIT at its second press, or None."""
        to = max(0, min(QUIT, self.cursor + self.edge.read(actions.y)))
        if to != self.cursor:
            self.cursor, self.armed, self.changes = to, False, self.changes + 1
        if not actions.fire.pressed:
            return None
        if self.cursor < QUIT:
            return self.cursor
        if self.armed:
            return QUIT
        self.armed, self.changes = True, self.changes + 1
        return None

    def record(self, row, end, best):
        """A round of the row's way ended with end, its best streak best."""
        self.best[row] = max(self.best[row], best)
        if end == PASS or end == CONTROL:
            self.marked[row] = True
        self.changes += 1


def game_class(boot, click):
    """The probe's game, a gfx.Game named switchtest on Rescue's art set: the menu, then a round of the way it picks,
    then the result card, then the menu again. boot and click are the two Seen FIRE buttons of the action map. It starts
    in play (TITLE_MS 0). The base game runs setup() in its constructor and again after each card, so the menu, the dice
    and the seven ways are built once in __init__, before the base's, and setup() makes only the round's figures anew.
    play() hands each frame to the menu or the round with the frame's clock (self.last). The top bar (hud, draw_hud)
    and the card (draw_over) are its own: the base card says "game over" and is kept by the score, which stays 0 here.
    It imports gfx, pictures and rescue here, as the board part and a Mac test call it: rescue needs framebuf."""
    import gfx
    import pictures
    import rescue

    feet, lane, mark = rescue.FEET, rescue.LANE, rescue.MARK
    spray, run_w = rescue.SIZES["spray"], rescue.SIZES["run"]
    child_w, child_h = rescue.PEOPLE_SIZES[rescue.CHILD]
    # each picture a (name, width) pair, made once: a frame makes no name
    fireman_runs = tuple(tuple((n, run_w) for n in rescue.POSES["run", side]) for side in "rl")
    fireman_acts = tuple(tuple((n, spray) for n in rescue.POSES["spray", side]) for side in "rl")
    fireman_stands = tuple((rescue.POSES["spray", side][0], spray) for side in "rl")  # the hose ready, as Rescue's
    child_runs = tuple(tuple((n, child_w) for n in rescue.PEOPLE_POSES[rescue.CHILD, "run", side]) for side in "rl")
    child_acts = tuple(tuple((n, child_w) for n in rescue.PEOPLE_POSES[rescue.CHILD, "wave", side]) for side in "rl")
    wave_pose_ms = rescue.WAVE_MS // rescue.WAVE_POSES
    big_names = ("FIREMAN", "CHILD")  # the task's wanted figure, big
    menu_rect = (24, 32, 272, 8 + 16 * (QUIT + 1))  # the menu's panel, kept like the score bar
    ready_y, task_y, arrow_y = 90, lane - 40, lane - 8  # READY and WRONG, the task's name, the arrow's tip row - 3

    def drawn(cv, name, x, y):
        if not pictures.draw(cv, name, x, y):
            raise RuntimeError("%s did not draw: no art" % name)

    class Switchtest(gfx.Game):
        name = "switchtest"
        hint = "switch between two figures"
        ART = ("rescue", None)
        TITLE_MS = 0
        bg = rescue.Rescue.bg
        accent = gfx.ORANGE

        def __init__(self):
            self.menu, self.dice = Menu(), gfx.Dice(905)
            self.ways = tuple(way() for way in WAYS)
            self.row = 0
            gfx.Game.__init__(self)

        def setup(self):
            self.covers = pictures.load(*self.ART)  # the street covers the screen, so no fill goes under it
            self.figures = [
                SteeredFigure(START_X[FIREMAN], 1, rescue.SPEED_PX_S, rescue.STRIDE_PX, rescue.PICTURE_H,
                              fireman_runs, fireman_acts, rescue.SPRAY_POSE_MS, fireman_stands),
                SteeredFigure(START_X[CHILD], -1, rescue.PERSON_PX_S[rescue.CHILD],
                              rescue.PERSON_STRIDE_PX[rescue.CHILD], child_h, child_runs, child_acts, wave_pose_ms)]
            self.round, self.fresh = None, True  # fresh: the menu's next frame is its reset

        def play(self, pressed, held):
            actions, r = self.stick, self.round
            if r is None:
                if self.fresh:
                    self.fresh = False
                    self.menu.reset(actions)
                    return
                row = self.menu.step(actions)
                if row == QUIT:
                    raise Quit
                if row is not None:
                    self.row, self.round = row, Round(self.ways[row], self.figures, self.dice, print, self.last)
                return
            r.step(self.last, self.ms, actions, boot, click)
            if r.end != PLAYING:
                self.menu.record(self.row, r.end, r.tally.best)
                self.die()

        def paint_static(self, cv):
            drawn(cv, "rescue_night", 0, 0)

        def paint(self, cv):
            r = self.round
            if r is None:
                cv.keep(("switchtest menu", self.menu.changes), menu_rect, self.draw_menu)
                return
            if not r.ready:
                rescue.Rescue.draw_ring(cv, r.ring, REACH_PX, gfx.YELLOW)
            for i in range(len(r.figures)):
                f = r.figures[i]
                name, w = f.picture(r.act_ms(i))
                drawn(cv, name, f.x - w // 2, feet - f.h + 1)
            x = r.figures[r.active].x  # the arrow over the active figure: four fills, as Rescue's draw_help
            cv.fill(x - 3, arrow_y, 7, 1, mark)
            cv.fill(x - 2, arrow_y + 1, 5, 1, mark)
            cv.fill(x - 1, arrow_y + 2, 3, 1, mark)
            cv.fill(x, arrow_y + 3, 1, 1, mark)
            if r.ready:
                cv.big("READY", gfx.WIDTH // 2 - 60, ready_y, gfx.WHITE, 3)
                return
            word = big_names[r.wanted]
            w = 16 * len(word)
            cv.big(word, max(0, min(gfx.WIDTH - w, r.ring - w // 2)), task_y, gfx.WHITE, 2)
            if r.marking():
                cv.big("WRONG", gfx.WIDTH // 2 - 60, ready_y, gfx.RED, 3)

        def draw_menu(self, cv):
            x, y, w, h = menu_rect
            cv.fill(x, y, w, h, gfx.BLACK)
            cv.box(x, y, w, h, gfx.GREY)
            m = self.menu
            for i in range(QUIT):
                way = WAYS[i]
                cv.text("%s %-14s best %2d %s" % ("> " if i == m.cursor else "  ", way.label, m.best[i],
                                                  ("control" if way.control else "PASS") if m.marked[i] else ""),
                        x + 4, y + 6 + 16 * i, gfx.YELLOW if m.marked[i] else gfx.WHITE)
            quit_row = "QUIT: FIRE again" if m.armed else "QUIT"
            cv.text(("> " if m.cursor == QUIT else "  ") + quit_row, x + 4, y + 6 + 16 * QUIT,
                    gfx.RED if m.armed else gfx.GREY)

        def hud(self, cv):
            """The top bar, two lines of 8 px, drawn again only when the screen, the way, the streak or the wrong
            tasks change."""
            r = self.round
            if r is None:
                cv.keep((self.name, 0, 0, 0, 0), gfx.HUD_RECT, self.draw_hud)
            else:
                cv.keep((self.name, 1, self.row, r.tally.streak, r.tally.wrong), gfx.HUD_RECT, self.draw_hud)

        def draw_hud(self, cv):
            cv.fill(0, 0, gfx.WIDTH, gfx.HUD_RECT[3], gfx.DARK)
            r = self.round
            if r is None:
                cv.text("P905 SWITCH TEST: pick a way", 0, 0, gfx.WHITE)
                cv.text("stick up/down: row  FIRE: start", 0, 8, gfx.GREY)
                return
            cv.text(r.way.label, 0, 0, gfx.WHITE)
            cv.text("streak %d/%d" % (r.tally.streak, STREAK_TO_PASS), 120, 0, gfx.YELLOW)
            wrong = "wrong %d" % r.tally.wrong
            cv.text(wrong, gfx.WIDTH - 8 * len(wrong), 0, gfx.RED if r.tally.wrong else gfx.GREY)
            cv.text(r.way.hint, 0, 8, gfx.GREY)

        def draw_over(self, cv):
            """The result card: the way, the end, the streak and the best streak, kept like the bar. Its timing is the
            base game's: FIRE goes back to the menu OVER_MS after the end, and only then the card says so."""
            r = self.round
            cv.keep((self.name, self.row, r.end, r.tally.streak, r.tally.best), gfx.OVER_RECT, self.draw_card)
            if self.age >= self.OVER_MS:
                x, y, w, h = gfx.OVER_RECT
                cv.text("FIRE: menu", x + w // 2 - 40, y + h - 20, gfx.YELLOW)

        def draw_card(self, cv):
            x, y, w, h = gfx.OVER_RECT
            r = self.round
            cv.fill(x, y, w, h, gfx.BLACK)
            cv.box(x, y, w, h, self.accent)
            cv.box(x + 3, y + 3, w - 6, h - 6, gfx.GREY)
            label, word = r.way.label, CARD_WORDS[r.end]
            cv.text(label, x + w // 2 - 4 * len(label), y + 10, gfx.WHITE)
            colour = (gfx.WHITE, gfx.GREEN, gfx.RED, gfx.GREY, gfx.CYAN)[r.end]
            cv.big(word, x + w // 2 - 8 * len(word), y + 26, colour, 2)
            line = "streak %d  best %d" % (r.tally.streak, r.tally.best)
            cv.text(line, x + w // 2 - 4 * len(line), y + 52, gfx.WHITE)

    return Switchtest


def board():
    """The board part: the knob's pads first, as main.py takes them at boot, then the box's action map with both FIRE
    buttons wrapped (Seen), then the App with the probe's game alone, silent and with no knob, so PICK and the knob's
    turn reach the game. It refuses a pin map with no stick. QUIT ends the run with `done`."""
    import pins
    from drivers import encoder

    encoder.take_pads(pins.ENC_A, pins.ENC_B)  # first: until here a turn of the knob types into the console (P757)
    import app
    from engine.actions import ActionMap

    found = app.open_action_map()
    if found.stick is None or len(found.fire_bindings) < 2:
        raise RuntimeError("p905 refused: no stick in the pin map (pins.JOY_X): the probe needs the stick")
    boot, click = Seen(found.fire_bindings[0]), Seen(found.fire_bindings[1])
    action_map = ActionMap((boot, click), found.pick_bindings, found.encoder, found.stick)
    print("p905 ways %s streak %d wrong %d double %d hold %d" % (
        ",".join([way.name for way in WAYS]), STREAK_TO_PASS, WRONG_MAX, DOUBLE_MS, HOLD_MS))
    print("p905 inputs stick yes knob %s" % ("yes" if found.encoder else "no"))
    try:
        app.run(games=(game_class(boot, click),), knob=None, speaker=None, action_map=action_map)
    except Quit:
        pass
    print("done")


# --- the Mac part ---

LOG = "logs/run-p905-switch.log"  # from the repository root: the first log's path (box.ProbeRun.free_log)
MINUTES = 60  # the run's time limit; QUIT ends it sooner
PACK = "rescue.pak"  # the art the game needs, in :packs
WAIT = ["exec", "pass"]  # a cheap command: the box answers it once it is back from the hard reset
DEPLOY = "python3 tools/box.py deploy --all"


def check(box, runner, sleep):
    """Refuses a box without :packs/rescue.pak. It reads `ls :`, then `ls :packs` when the box has that folder (a dry
    run reads both and refuses nothing), each tried again while a running game keeps mpremote out."""
    root = box.board_names(box.retried(runner, ["ls", ":"], box.PROBE_TRIES, box.RESET_PAUSE_S, sleep))
    if runner.dry_run or "packs/" in root:
        packs = box.board_names(box.retried(runner, ["ls", ":packs"], box.PROBE_TRIES, box.RESET_PAUSE_S, sleep))
    else:
        packs = set()
    if not runner.dry_run and PACK not in packs:
        raise SystemExit("refused: the box has no :packs/%s: deploy first: %s" % (PACK, DEPLOY))


def minutes_arg(text):
    """--minutes' value: a whole number of 1 or more."""
    import argparse

    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError("not a whole number of 1 or more: %r" % text)
    return int(text)


def mac(argv, runner=None, sleep=None):
    """The Mac part from the command line: runner and sleep stand in for box.Mpremote and time.sleep in a test."""
    import argparse
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.join(here, "tools") not in sys.path:
        sys.path.insert(0, os.path.join(here, "tools"))
    import box

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print each board command, run none")
    parser.add_argument("--minutes", type=minutes_arg, default=MINUTES, metavar="N",
                        help="the run's time limit in minutes (%(default)s)")
    args = parser.parse_args(argv)
    runner, sleep = runner or box.Mpremote(args.dry_run), sleep or time.sleep
    run = box.ProbeRun(runner, os.path.join(here, LOG))
    try:
        try:
            check(box, runner, sleep)
            box.reset(runner, sleep=sleep)
            box.retried(runner, WAIT, box.RESET_TRIES, box.RESET_PAUSE_S, sleep)
            end = run.run(os.path.relpath(os.path.abspath(__file__), box.ROOT), args.minutes * 60)
        finally:
            box.reset(runner, sleep=sleep)  # in every case: the box plays its lineup again
    except (box.subprocess.CalledProcessError, FileNotFoundError) as e:
        raise SystemExit(box.failure(e))
    if end == run.LIMIT and [line for line in run.lines if line.startswith("p905 ways ")]:
        print("the time limit of %d minutes ended the run" % args.minutes)
    elif not runner.dry_run and (end != run.DONE or run.lines[-1:] != ["done"]):  # P904's probe also needs done
        raise SystemExit("refused: %s: %s; the log is %s" % (
            run.why or "the run ended with no done line", run.lines[-1] if run.lines else "no output", run.logged))
    if run.logged:
        print("the log is %s" % run.logged)


if sys.implementation.name == "micropython":
    board()
elif __name__ == "__main__":
    mac(sys.argv[1:])
