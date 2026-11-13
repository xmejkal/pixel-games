"""
Rescue (P800): a night street under a meteor shower. Carry the people who run about in panic to the fire station,
under the green SAFE sign.

How to play: the fireman runs along the street and never stops on his own. Tap BOOT and he turns round. Hold it and
he stops and sprays the hose ahead of him: a fire within REACH_PX goes down and is out after about a second of water.
People come out of the houses and run about in panic: a man, a woman, a child (small and fast), a grandma (slow, with
a cane) and a man with his dog. Each wears a bright shirt, so they show on the dark street. A fire stops everyone. A
person turns back from it. A person with a fire on one side and a fire or the street's end close on the other is
trapped: they stop, wave and shout for help, under a pale arrow and a blinking "help!". The fireman stops at a fire
too, until the hose puts it out. Run into a person and he picks them up. He is slower then and cannot spray, and he
runs through the flames with the person sheltered in his arms. At the station's door he sets them down: a point, two
for a child, and "+1" rises over the door. A meteor's shadow grows on the street for FALL_MS before it lands, in a
blinking target ring. Where it lands a crater opens and burns for FIRE_MS. A person it lands on is gone, in a puff of
smoke (nobody is drawn burning). Three people lost end the round. Every SAVES_A_STEP people saved, the meteors come
faster and more people are out at once.

Every figure is motion capture (art/mocap.py, art/sets/rescue.py), painted facing right and facing left: the
fireman's run, spray, turn and carry, each person's run (granny's is a walk) and wave. The dog is hand-keyed. A pose
follows the distance its figure ran, so the feet do not slide. The fire is the heat field (fire.FireLayer), burned at
each burning crater above the street lane and stepped every FIRE_STEP_MS, as the Runner's.
--- MVP (P800) ---
"""

import random

import pictures
from cues import LEVELS, Cue
from fire import ALPHA, PALETTE, FireLayer
from gfx import DARK, GREY, ORANGE, RED, WHITE, WIDTH, YELLOW, Game, Particles, c565
from meteors import SMOKE_ALPHAS, SMOKE_H, SMOKE_MS, SMOKE_W

# --- MVP (P800) --- the rules, in px, ms and ints
TAP_MS = 180  # a press released before this is a tap, and turns him; held this long, he sprays
FLASH_MS = 120  # the nozzle flashes from here until the spray starts
SPEED_PX_S = 56  # his run: the motion capture's 3.6 m/s at 24.07 px a body height (art/mocap.py prints the stride)
STRIDE_PX = 41  # px he runs in one run cycle: the capture's stride, 1.698 body heights, at 24.07 px a body height
CARRY_PX_S = 38  # carrying, he jogs: about the jog's own speed, 1.75 body heights a second
CARRY_STRIDE_PX = 32  # the jog's stride, 1.333 body heights (mocap's carry cycle), at 24.07 px a body height
RUN_POSES, SPRAY_POSES, TURN_POSES, CARRY_POSES = 12, 6, 4, 12  # art/mocap.py's CYCLES
SPRAY_POSE_MS = 83  # the spray cycle's loop is 0.5 s of capture, over its six poses
TURN_MS = 160  # the turn's four poses, after a turn: he turns on the spot, and cannot spray
LEFT_X, RIGHT_X = 74, 304  # px: his hips, from the station's door to the street's end, where he turns by himself
REACH_PX = 40  # px ahead of his hips that the hose reaches
HEAT_MAX = 255
DOUSE_MS = 1000  # ms of water that put out a full fire
FIRE_MS = 6000  # a fire left alone burns this long
TURNED, OUT, BURNT = 1, 2, 4  # what Rules.step answers, as bits: a tap turned him, the hose put a fire out, it burnt out
LANDED, PICKED, SAVED, LOST, TRAPPED, CAME, FELL, OVER = 8, 16, 32, 64, 128, 256, 512, 1024  # and the rest of a frame

# The people: each kind's picture name, speed, the stride of its cycle (its capture's stride at its size, as
# art/sets/rescue.py paints it) and its points
KINDS = ("man", "woman", "child", "granny", "dogman")
MAN, WOMAN, CHILD, GRANNY, DOGMAN = range(5)
PERSON_PX_S = (42, 42, 48, 18, 46)
PERSON_STRIDE_PX = (34, 33, 25, 19, 39)  # 1.438, 1.474, 1.656, 0.899, 1.636 body heights at 23.6, 22.6, 15.1, 20.8, 23.6 px
POINTS = (1, 1, 2, 1, 1)  # a child counts double
PERSON_POSES, WAVE_POSES = 12, 12
WAVE_MS = 1120  # the wave's loop: 1.12 s of capture
RUN, WAVING, CARRIED = 0, 1, 2  # a person's state
STREET_LEFT, STREET_RIGHT = 96, 308  # px: the people's hips stay between these; they never go into the station
BLOCK_PX = 18  # px from a burning crater's middle: nobody comes closer from the side they are on
TRAP_PX = 80  # px: a person who meets a fire with another fire this close behind is trapped, and waves
WALL_PX = 30  # px: so is one who meets a fire with the street's end this close behind
TOUCH_PX = 9  # px between his hips and a person's: he picks them up
DODGE_PX = 24  # px: a running person turns away from a meteor's shadow this close ahead
GRACE_MS = 500  # ms after a pickup when a meteor on him does not take the person
PANIC_MS = (1500, 4500)  # ms a person runs one way at most, before turning round in panic
COME_MS = 3000  # ms from one person coming out to the next, while fewer are out than the tier allows: a street
# he has emptied stays emptier for a while, so carrying fast keeps people out of the meteors' way
COME_FIRST_MS = 600  # ms to the first person of a round
COME_GAP_PX = 30  # px at least between a person who comes out and a burning crater, or the fireman
# The meteors: a shadow grows FALL_MS before one lands; it takes the people within HIT_PX
FALL_MS = 800
HIT_PX = 8
FIRST_MS = 1500  # ms to the first meteor of a round
METEOR_LEFT, METEOR_RIGHT = 100, 312  # px: where a meteor lands
AIM, AIM_PX = 3, 16  # one meteor in AIM lands within AIM_PX of a person who runs
HOLES = 6  # craters kept on the street; the oldest that no longer burns goes first
LOST_MAX = 3  # people lost that end the round
# The ramp: a step of difficulty each SAVES_A_STEP people saved (people, not points), up to the last tier
SAVES_A_STEP = 3
METEOR_MS = (2400, 2100, 1800, 1500, 1200, 900)  # ms between two meteors at each tier
CROWD = (2, 3, 3, 4, 4, 5)  # people out at once at each tier


class Fireman:
    """Where he is, the way he faces (1 right, -1 left), the press he is in, the px he ran (the run's pose), the
    person he carries (or None) and the ms since he picked them up, and whether a fire stopped him."""

    def __init__(self, x):
        self.x, self.facing, self.rest = x, 1, 0  # rest: px times ms short of the next whole px
        self.down_ms = -1  # ms the button has been held, the first frame's ms included; -1 when it is up
        self.ran, self.turned_ms, self.spray_ms = 0, TURN_MS, 0
        self.carrying, self.carried_ms, self.blocked = None, 0, False

    def spraying(self):
        """Held TAP_MS or longer, not in a turn and not carrying."""
        return self.down_ms >= TAP_MS and not self.turning() and self.carrying is None

    def turning(self):
        return self.turned_ms < TURN_MS

    def flashing(self):
        return FLASH_MS <= self.down_ms < TAP_MS and self.carrying is None

    def press(self, ms, held):
        """ms of a frame with the button held or not. A press released before TAP_MS turns him, at the release.
        Answers whether he turned."""
        self.turned_ms += ms
        self.carried_ms += ms
        if held:
            self.down_ms = ms if self.down_ms < 0 else self.down_ms + ms  # it went down during this frame
            return False
        tap = 0 <= self.down_ms < TAP_MS
        self.down_ms = -1
        if tap:
            self.turn()
        return tap

    def turn(self):
        """He turns on the spot. The turn's poses are the run's at phases 0, 3, 6 and 9 of 12, so the run goes on
        after it from phase 0: ran moves on to the next whole stride. Carrying, he turns at once, as the turn's poses
        have nobody in his arms."""
        self.facing, self.blocked = -self.facing, False
        if self.carrying is None:
            self.turned_ms = 0
            self.ran += -self.ran % STRIDE_PX

    def run(self, ms, stop=None):
        """ms of running the way he faces; at an end of the street he turns by himself. Spraying or turning, he
        stands. stop: an x ahead that he does not pass (a fire's edge), or None."""
        if self.spraying():
            self.spray_ms += ms
            return
        if self.turning():
            return
        self.rest += self.facing * (SPEED_PX_S if self.carrying is None else CARRY_PX_S) * ms
        px = self.rest // 1000
        self.rest -= px * 1000
        self.blocked = stop is not None and (self.x + px - stop) * self.facing >= 0
        if self.blocked:
            px, self.rest = stop - self.x if (stop - self.x) * self.facing > 0 else 0, 0
        self.x += px
        self.ran += abs(px)
        if self.x <= LEFT_X or self.x >= RIGHT_X:
            self.x = LEFT_X if self.x <= LEFT_X else RIGHT_X
            self.rest = 0
            if (self.x == LEFT_X) == (self.facing < 0):
                self.turn()

    def run_pose(self):
        return self.ran * RUN_POSES // STRIDE_PX % RUN_POSES

    def carry_pose(self):
        return self.ran * CARRY_POSES // CARRY_STRIDE_PX % CARRY_POSES

    def ahead(self, x):
        """px from his hips to x, the way he faces: negative when x is behind him."""
        return (x - self.x) * self.facing


class Crater:
    """A crater and its fire: x, the ms of water it took, the ms it burns on."""

    def __init__(self, x):
        self.x, self.wet_ms, self.left_ms = x, 0, FIRE_MS

    def burning(self):
        return self.wet_ms < DOUSE_MS and self.left_ms > 0

    def heat(self):
        """0 to HEAT_MAX: down with the water, 0 once it is out."""
        return HEAT_MAX * (DOUSE_MS - self.wet_ms) // DOUSE_MS if self.burning() else 0


class Person:
    """One person on the street: the kind (an index of KINDS), x of the hips, the way they face, the state (RUN,
    WAVING, CARRIED), the px they ran (the run's pose), the ms they waved and the ms before they turn in panic."""

    def __init__(self, kind, x, facing, panic_ms):
        self.kind, self.x, self.facing, self.state = kind, x, facing, RUN
        self.rest, self.ran, self.wave_ms, self.panic_ms = 0, 0, 0, panic_ms

    def pose(self):
        return self.ran * PERSON_POSES // PERSON_STRIDE_PX[self.kind] % PERSON_POSES

    def wave_pose(self):
        return self.wave_ms * WAVE_POSES // WAVE_MS % WAVE_POSES

    def run(self, ms):
        """ms of running the way they face, in whole px; at an end of the street they turn."""
        self.rest += self.facing * PERSON_PX_S[self.kind] * ms
        px = self.rest // 1000
        self.rest -= px * 1000
        self.x += px
        self.ran += abs(px)
        if self.x <= STREET_LEFT or self.x >= STREET_RIGHT:
            self.x = STREET_LEFT if self.x <= STREET_LEFT else STREET_RIGHT
            self.rest = 0
            if (self.x == STREET_LEFT) == (self.facing < 0):
                self.facing = -self.facing


class Meteor:
    """A meteor on its way: the x where it lands and the ms before it does."""

    def __init__(self, x):
        self.x, self.left_ms = x, FALL_MS


class Rules:
    """The rules, with no display: the fireman, the people, the meteors, the craters, the people saved and lost and
    the points. rand(a, b) is random.randrange's (the game's random, or a test's own seeded one). Ints only. step()
    answers the bits of what happened; the frame's details are in landed_x, out_x, lost (the (x, kind) of each person
    lost this frame), saved_kind, trapped_kind and came_x."""

    def __init__(self, rand=random.randrange, x=(LEFT_X + RIGHT_X) // 2):
        self.rand = rand
        self.man = Fireman(x)
        self.people, self.meteors, self.craters = [], [], []
        self.saved = self.lost_count = self.points = 0
        self.meteor_ms, self.come_ms = FIRST_MS, COME_FIRST_MS  # ms to the next meteor, and to the next person
        self.landed_x = self.out_x = self.saved_kind = self.trapped_kind = self.came_x = -1
        self.lost = []

    def tier(self):
        return min(self.saved // SAVES_A_STEP, len(METEOR_MS) - 1)

    def burning(self):
        return [c for c in self.craters if c.burning()]

    def fire_ahead(self, x, facing, reach):
        """The x of the nearest burning crater ahead of x (the way facing) within reach px, or None."""
        best = None
        for c in self.craters:
            d = (c.x - x) * facing
            if 0 < d <= reach and c.burning() and (best is None or d < (best - x) * facing):
                best = c.x
        return best

    def step(self, ms, held):
        """One frame of ms with the button held or not. Answers the frame's bits."""
        man, events = self.man, 0
        if self.lost:
            self.lost = []
        if man.press(ms, held):
            events |= TURNED
        fire = None if man.carrying is not None else self.fire_ahead(man.x, man.facing, BLOCK_PX + SPEED_PX_S)
        man.run(ms, None if fire is None else fire - man.facing * BLOCK_PX)  # carrying, he runs through the flames
        events |= self.burn(ms)
        events |= self.move_people(ms)
        events |= self.carry()
        events |= self.fall(ms)
        events |= self.come(ms)
        if self.lost_count >= LOST_MAX:
            events |= OVER
        return events

    def burn(self, ms):
        """The fires burn down, and the hose wets each one within REACH_PX ahead of him."""
        man, events = self.man, 0
        spraying = man.spraying()
        for c in self.craters:
            if c.burning():
                c.left_ms -= ms
                if spraying and 0 <= man.ahead(c.x) <= REACH_PX:
                    c.wet_ms += ms
                if not c.burning():
                    if c.wet_ms >= DOUSE_MS:
                        events |= OUT
                        self.out_x = c.x
                    else:
                        events |= BURNT
        return events

    def move_people(self, ms):
        """Each person runs; turns in panic now and then; turns back from a fire, or, with another behind, is
        trapped and waves until a way opens."""
        events = 0
        for p in self.people:
            if p.state == CARRIED:
                continue
            if p.state == WAVING:
                p.wave_ms += ms
                ahead = self.shut(p.x, p.facing)
                if not ahead or not self.shut(p.x, -p.facing):  # a way out: they run again
                    p.state = RUN
                    if ahead:
                        p.facing = -p.facing
                continue
            p.panic_ms -= ms
            if p.panic_ms <= 0:
                p.facing, p.panic_ms = -p.facing, self.rand(*PANIC_MS)
            if self.shadow_ahead(p):  # away from a meteor's shadow, never into one
                p.facing = -p.facing
                if self.shadow_ahead(p):
                    p.facing = -p.facing
            if self.fire_ahead(p.x, p.facing, BLOCK_PX + PERSON_PX_S[p.kind] * ms // 1000 + 1) is not None:  # a fire:
                # they turn back before this frame's step would bring them within BLOCK_PX, or are trapped
                if self.shut(p.x, -p.facing):
                    p.state, p.wave_ms, self.trapped_kind = WAVING, 0, p.kind
                    events |= TRAPPED
                    continue
                p.facing, p.panic_ms = -p.facing, self.rand(*PANIC_MS)
            p.run(ms)
        return events

    def shut(self, x, facing):
        """Whether the way from x (the way facing) is shut: a fire within TRAP_PX, or the street's end within
        WALL_PX."""
        end = STREET_RIGHT if facing > 0 else STREET_LEFT
        return self.fire_ahead(x, facing, TRAP_PX) is not None or (end - x) * facing <= WALL_PX

    def shadow_ahead(self, p):
        """Whether a meteor will land ahead of p within DODGE_PX, or on them."""
        return any(-HIT_PX <= (m.x - p.x) * p.facing <= DODGE_PX for m in self.meteors)

    def carry(self):
        """He picks up a person he runs into, unless he sprays, and sets them down at the door."""
        man, events = self.man, 0
        if man.carrying is None and not man.spraying():
            for p in self.people:
                if p.state != CARRIED and abs(p.x - man.x) <= TOUCH_PX:
                    p.state, man.carrying, man.carried_ms = CARRIED, p, 0
                    events |= PICKED
                    break
        p = man.carrying
        if p is not None:
            p.x = man.x
            if man.x <= LEFT_X:
                self.people.remove(p)
                man.carrying = None
                self.saved += 1
                self.points += POINTS[p.kind]
                self.saved_kind = p.kind
                events |= SAVED
        return events

    def fall(self, ms):
        """The meteors fall; one that lands opens a burning crater and takes the people under it. A new one comes
        each METEOR_MS of the tier."""
        events = 0
        for m in self.meteors:
            m.left_ms -= ms
        while self.meteors and self.meteors[0].left_ms <= 0:  # they land in the order they came
            self.land(self.meteors.pop(0).x)
            events |= LANDED | (LOST if self.lost else 0)
        self.meteor_ms -= ms
        if self.meteor_ms <= 0:
            self.meteor_ms += METEOR_MS[self.tier()]
            self.meteors.append(Meteor(self.target()))
            events |= FELL
        return events

    def target(self):
        """Where a meteor lands: near a person who runs once in AIM (they may dodge its shadow), else anywhere on the
        street."""
        out = [p for p in self.people if p.state == RUN]
        if out and self.rand(0, AIM) == 0:
            x = out[self.rand(0, len(out))].x + self.rand(-AIM_PX, AIM_PX + 1)
            return max(METEOR_LEFT, min(METEOR_RIGHT, x))
        return self.rand(METEOR_LEFT, METEOR_RIGHT + 1)

    def land(self, x):
        """A crater at x, and every person within HIT_PX lost: the one he carries too, after GRACE_MS."""
        man = self.man
        self.landed_x = x
        self.craters.append(Crater(x))
        while len(self.craters) > HOLES:
            old = [c for c in self.craters if not c.burning()]
            self.craters.remove(old[0] if old else self.craters[0])
        for p in list(self.people):
            if abs(p.x - x) > HIT_PX:
                continue
            if p.state == CARRIED:
                if man.carried_ms < GRACE_MS:
                    continue
                man.carrying = None
            self.people.remove(p)
            self.lost.append((p.x, p.kind))
            self.lost_count += 1

    def come(self, ms):
        """Now and then a person comes out of a house, while fewer are out than the tier allows."""
        if len(self.people) >= CROWD[self.tier()]:
            self.come_ms = COME_MS
            return 0
        self.come_ms -= ms
        if self.come_ms > 0:
            return 0
        x = self.rand(STREET_LEFT + 10, STREET_RIGHT - 9)
        if abs(self.man.x - x) < COME_GAP_PX or any(abs(c.x - x) < COME_GAP_PX for c in self.burning()):
            return 0  # a fire there, or the fireman: they try again next frame
        self.come_ms = COME_MS
        kind = self.rand(0, len(KINDS))
        self.people.append(Person(kind, x, 1 if self.rand(0, 2) else -1, self.rand(*PANIC_MS)))
        self.came_x = x
        return CAME


# --- MVP (P800) --- the game
FEET = 214  # px: the row the soles stand on (art/sets/rescue.py's FEET)
LANE = 180  # px: the street lane's top; the fire burns above it (art/sets/rescue.py's LANE)
SIZES = {"run": 26, "turn": 26, "spray": 40, "carry": 30}  # each cycle's picture width; the hips at its middle
PICTURE_H = 30  # the fireman's pictures' height (art/sets/rescue.py's SIZES)
PEOPLE_SIZES = ((24, 32), (24, 32), (18, 22), (24, 28), (24, 32))  # each kind's pictures, w x h (art/sets/rescue.py)
DOG_W, DOG_H, DOG_POSES = 18, 12, 8  # the dog's pictures (art/sets/rescue.py)
DOG_STRIDE_PX = 22  # px the dog runs in one gallop cycle
DOG_AHEAD_PX = 13  # px from the man's hips to the dog's, the way they run
# px from his hips and soles to the nozzle's tip, facing right: the spray poses hold it 11 to 13 px ahead and 24 up
# (tests/test_rescue_art.py pins it)
NOZZLE_DX, NOZZLE_DY = 12, -24
FIRE_STEP_MS = 80  # ms a heat step, as the Runner's: 40 sank the Runner to 16 fps (bench.md P651)
# fx_fire_set_look's decay, cool, sway, spots, spread, fast, embers, fade: one flame out of the crater that tapers into
# tongues, set by eye on Mac frames of tools/render_scene.py against eight looks (fast patches and more cooling split
# it into blobs with a gap, less fade makes a white column)
FIRE_LOOK = (34, 30, 1, 0, 1, 0, 0, 16)  # no fast patches (they split the flame), no field embers (they rose low)
FIRE_SEED = 800
DECAY_DROP = 3  # the decay falls this much as the fires die down: from 34, which keeps the flames climbing, to 31
BURN_HALF_PX = 12  # px each side of the crater's middle that burn
BURNS = 8  # hot spots burned a frame by a full fire
BURN_HEAT, FOOT_HEAT = 223, 160  # a spot's heat in a full fire, and in a fire nearly out: still bright, never see-through
REGROW = ((0, 4, 210), (4, 9, 170), (9, 14, 120))  # field rows above a fire's foot and their heat: a flame burned back
WATER = (c565(170, 214, 255), c565(230, 244, 255))
STEAM = c565(200, 200, 210)
SMOKE = (c565(120, 116, 124), c565(150, 146, 152), c565(90, 86, 96))
DEBRIS = (c565(255, 170, 70), c565(120, 70, 50))
SPARKLE = (c565(255, 240, 160), WHITE, YELLOW)
CORE, HALO = WHITE, c565(255, 214, 120)
TRAIL = (c565(255, 150, 50), c565(240, 80, 30), c565(255, 210, 120))
SHADOW, TARGET = c565(14, 10, 16), c565(150, 40, 30)
RING = (WHITE, c565(255, 90, 60))  # the landing's target ring round the shadow, blinking white and red
RING_BLINK_MS = 100
MARK = c565(255, 244, 214)  # the pale arrow over a trapped person
PLATE_Y = LANE - 16  # the "help!" plate's top: its 11 rows end above the fire's foot (the bottom 5 rows over LANE)
DOOR_LIT = c565(255, 214, 140)
GLOW_LEVELS = 8  # the fire's light on the kerb and the street, from none to the full fire
SHAKE = (2, -2, 1, -1)  # px the moving things shift, one a frame, after a meteor lands
FLASH = (((18, c565(255, 200, 110)), (11, WHITE)), ((13, c565(255, 150, 60)), (6, c565(255, 236, 170))),
         ((8, c565(230, 90, 40)),))  # the impact's flash, a frame each: discs (radius, colour), outside first
FALL_DX, FALL_TOP = 70, 18  # a meteor comes in from FALL_DX px right of where it lands, from row FALL_TOP
HELP_MS = 2400  # ms between two shouts of one trapped person
CAME_MS = 600  # ms a house's door shows lit after a person came out of it
THANKS_MS = 1200  # ms the points of a person saved rise over the station's door


def glow(base, warm):
    """GLOW_LEVELS colours from base (unlit) toward warm (lit by a full fire)."""
    n = GLOW_LEVELS - 1
    return tuple(c565(*[b + (w - b) * k // n for b, w in zip(base, warm)]) for k in range(GLOW_LEVELS))


KERB_GLOW = glow((84, 76, 86), (240, 116, 48))  # art/sets/rescue.py's kerb, lit
STREET_GLOW = glow((38, 34, 42), (210, 96, 40))  # the tarmac, a wet shine
SPARK = c565(255, 190, 80)
FLAT = (c565(70, 80, 130), c565(170, 70, 120), c565(60, 150, 160), c565(150, 140, 130), c565(110, 130, 60))  # no art

POSES = {(cycle, side): tuple("rescue_%s_%s%d" % (cycle, side, i) for i in range(n))
         for cycle, n in (("run", RUN_POSES), ("spray", SPRAY_POSES), ("turn", TURN_POSES), ("carry", CARRY_POSES),
                          ("carrykid", CARRY_POSES)) for side in "rl"}
PEOPLE_POSES = {(kind, cycle, side): tuple("rescue_%s_%s_%s%d" % (KINDS[kind], cycle, side, i) for i in range(n))
                for kind in range(len(KINDS)) for cycle, n in (("run", PERSON_POSES), ("wave", WAVE_POSES))
                for side in "rl"}
DOG_NAMES = {side: tuple("rescue_dog_%s%d" % (side, i) for i in range(DOG_POSES)) for side in "rl"}
SMOKES = tuple("rescue_smoke%d" % i for i in range(len(SMOKE_ALPHAS)))  # Meteors' see-through smoke, by alias


class Spray(Particles):
    """The hose's water: the game's own pool, so the shared fx pool keeps its room for the steam."""

    MAX = 60

    def draw(self, cv):
        for q in self.p:  # a drop: 2 x 1 px, then 1 px as it thins out
            cv.fill(q[0], q[1], 2 if q[4] > 0.12 else 1, 1, q[5])


class Puffs(Particles):
    """The meteors' trails and the smoke: the game's own pool. A puff grows as it fades."""

    MAX = 70

    def draw(self, cv):
        for q in self.p:
            n = 1 if q[4] > 0.5 else 2 if q[4] > 0.25 else 3
            cv.fill(q[0], q[1], n, n, q[5])


class Rescue(Game):
    name = "rescue"
    hint = "tap turns, hold sprays, carry people to the station"
    bg = c565(14, 12, 26)
    accent = ORANGE
    cues = {"hose": Cue("hose", loop=True), "siren": Cue("siren"), "whoosh": Cue("whoosh"), "boom": Cue("boom"),
            "cheer": Cue("cheer"), "pickup": Cue("pickup"), "help": Cue("help"), "help_child": Cue("help_child")}

    def __init__(self):
        self.layer = FireLayer(FIRE_LOOK, FIRE_SEED, FIRE_STEP_MS, ALPHA, PALETTE)  # made once, as the Runner's
        super().__init__()

    def setup(self):
        self.layer.clear()
        self.decay = FIRE_LOOK[0]  # the look's decay now, set again only when it changes
        self.rules = Rules()
        self.water, self.puffs = Spray(), Puffs()
        self.covers = pictures.load()  # the painted street covers the screen, so no fill goes under it
        self.smokes = []  # [x, ms since] of each puff of smoke where a person was lost
        self.shake_k = len(SHAKE)  # frames into the shake; len(SHAKE) when still
        self.flash_k, self.flash_x = len(FLASH) + 1, 0  # frames into the impact's flash (none past len(FLASH)), x
        self.came = []  # [x, ms left] of each house door lit by a person coming out
        self.thanks = []  # [points, ms shown] of each person just saved, rising over the door
        self.helped = {}  # id of a trapped person: ms to their next shout
        self.hosing, self.started = False, False
        self.emit("hose", 0)

    def play(self, pressed, held):
        rules = self.rules
        if not self.started:  # the round starts with the siren
            self.started = True
            self.emit("siren")
        events = rules.step(self.ms, held)
        man = rules.man
        self.fires(events)
        self.effects(events)
        if man.spraying():
            x, y = man.x + NOZZLE_DX * man.facing, FEET + NOZZLE_DY
            for _ in range(5):
                self.water.add(x, y, man.facing * random.randrange(100, 140), -random.randrange(50, 90),
                               WATER[random.randrange(2)], 0.34, 320.0)
            for c in rules.craters:
                if c.burning() and 0 <= man.ahead(c.x) <= REACH_PX and random.randrange(3) == 0:
                    self.fx.add(c.x + random.randrange(-8, 9), LANE - 4, random.randrange(-12, 13),
                                -random.randrange(20, 50), STEAM, 0.7, -30.0)
        for m in rules.meteors:  # each meteor's trail of embers
            x, y = self.meteor_at(m)
            for _ in range(3):
                self.puffs.add(x + random.randrange(-1, 2), y + random.randrange(-1, 2), random.randrange(10, 40),
                               -random.randrange(20, 70), TRAIL[random.randrange(3)], 0.45, 0.0)
        if man.spraying() != self.hosing:
            self.hosing = man.spraying()
            self.emit("hose", LEVELS if self.hosing else 0)
        self.water.update(self.dt)
        self.puffs.update(self.dt)
        if self.shake_k < len(SHAKE):
            self.shake_k += 1
        if self.flash_k <= len(FLASH):
            self.flash_k += 1
        if events & OVER:
            self.emit("hose", 0)
            self.die()

    def fires(self, events):
        """The heat field: each burning crater burns its foot into it. A fire that ends empties the field (its heat
        would rise on alone as a flame with no crater under it), and the fires still burning are burned back in."""
        rules = self.rules
        self.layer.update(self.ms, 0)
        field = self.layer.field
        if field is None:
            return
        burning = rules.burning()
        heat = max([c.heat() for c in burning] or [0])
        decay = FIRE_LOOK[0] - DECAY_DROP + DECAY_DROP * heat // HEAT_MAX  # the flames climb less high as they die
        if decay != self.decay:
            self.decay = decay
            field.set_look(decay, *FIRE_LOOK[1:])
        if events & (OUT | BURNT):
            self.layer.clear()
            for c in burning:
                x, y = c.x // 2, LANE // 2 - 2
                for lo, hi, top in REGROW:
                    field.burn(x, y - lo, x, y - hi, 3, top * c.heat() // HEAT_MAX)
        for c in burning:  # hot spots at random along the crater, on its two rows: a wide, ragged base. As a fire
            h = c.heat()  # dies down it narrows and has fewer spots, but its foot stays hot: it never lifts off
            half = 3 + (BURN_HALF_PX - 3) * h // HEAT_MAX
            for _ in range(1 + (BURNS - 1) * h // HEAT_MAX):
                x = (c.x + random.randrange(-half, half + 1)) // 2
                y = LANE // 2 - 2 - random.randrange(2)
                field.burn(x, y, x, y, 1, FOOT_HEAT + (BURN_HEAT - FOOT_HEAT) * h // HEAT_MAX - random.randrange(30))
            if random.randrange(HEAT_MAX) < h // 6:  # sparks fly up from the fire, fewer as it dies down
                self.fx.add(c.x + random.randrange(-8, 9), LANE - 6, random.randrange(-20, 21),
                            -random.randrange(40, 90), SPARK, 0.8, 20.0)

    def effects(self, events):
        """What the frame's events look and sound like."""
        rules, man = self.rules, self.rules.man
        if events & FELL:
            self.emit("whoosh")
        if events & LANDED:
            x = rules.landed_x
            self.emit("boom")
            self.shake_k = self.flash_k = 0
            self.flash_x = x
            self.fx.burst(x, LANE - 2, DEBRIS[0], 12, 120.0, 0.6, 260.0)
            self.fx.burst(x, LANE - 2, DEBRIS[1], 8, 90.0, 0.7, 260.0)
            for _ in range(6):
                self.puffs.add(x + random.randrange(-6, 7), LANE - 4, random.randrange(-20, 21),
                               -random.randrange(20, 50), SMOKE[random.randrange(3)], 1.0, -10.0)
        for x, _ in rules.lost:  # a puff of grey smoke where they stood: they are gone
            self.smokes.append([x, 0])
            for _ in range(0 if self.covers else 16):  # the specks only without the painted smoke
                self.puffs.add(x + random.randrange(-5, 6), FEET - random.randrange(4, 22), random.randrange(-30, 31),
                               -random.randrange(10, 40), SMOKE[random.randrange(3)], 1.2, -15.0)
        for smoke in self.smokes:
            smoke[1] += self.ms
        self.smokes = [m for m in self.smokes if m[1] < SMOKE_MS * len(SMOKES)]
        if events & OUT:
            self.fx.burst(rules.out_x, LANE - 6, STEAM, 14, 50.0, 0.9, -60.0)
        if events & PICKED:
            self.emit("pickup")
            self.pop(man.x + 6 * man.facing, FEET - 16, WHITE)
        if events & SAVED:
            self.score = rules.points
            self.emit("cheer")
            self.thanks.append([POINTS[rules.saved_kind], 0])
            for _ in range(3 if rules.saved_kind == CHILD else 2):
                self.fx.burst(LEFT_X - 36 + random.randrange(30), 140 + random.randrange(30),
                              SPARKLE[random.randrange(3)], 7, 60.0, 0.7, 40.0)
        if events & CAME:
            self.came.append([rules.came_x, CAME_MS])
        for door in self.came:
            door[1] -= self.ms
        self.came = [d for d in self.came if d[1] > 0]
        for t in self.thanks:
            t[1] += self.ms
        self.thanks = [t for t in self.thanks if t[1] < THANKS_MS]
        helped = {}
        for p in rules.people:  # a trapped person shouts now and then, and the siren goes once for them
            if p.state == WAVING:
                left = self.helped.get(id(p), 0) - self.ms
                if left <= 0:
                    if id(p) not in self.helped:
                        self.emit("siren")
                    if p.kind != MAN and p.kind != DOGMAN:  # the one shout is a woman's, pitched up for a child
                        self.emit("help_child" if p.kind == CHILD else "help")
                    left = HELP_MS
                helped[id(p)] = left
        self.helped = helped

    def man_picture(self):
        """The painted picture for now and its cycle: the carry while he carries, the turn just after a turn, the
        spray while he sprays (and its first pose, the hose ready, while a fire stops him), else the run's pose for
        the px he ran. The names are made once, in POSES."""
        man = self.rules.man
        side = "r" if man.facing > 0 else "l"
        if man.carrying is not None:
            cycle = "carrykid" if man.carrying.kind == CHILD else "carry"
            return POSES[cycle, side][man.carry_pose()], "carry"
        if man.turned_ms < TURN_MS:  # the turn's poses go from the old facing to the new one
            return POSES["turn", "l" if man.facing > 0 else "r"][man.turned_ms * TURN_POSES // TURN_MS], "turn"
        if man.spraying():
            return POSES["spray", side][man.spray_ms // SPRAY_POSE_MS % SPRAY_POSES], "spray"
        if man.blocked:
            return POSES["spray", side][0], "spray"
        return POSES["run", side][man.run_pose()], "run"

    def paint_static(self, cv):
        if pictures.draw(cv, "rescue_night", 0, 0):
            return
        cv.gradient(16, LANE, (10, 10, 26), (110, 34, 30), 12)
        cv.fill(0, 96, 80, LANE - 96, c565(84, 40, 36))  # the station
        cv.fill(16, 132, 42, LANE - 132, c565(255, 226, 160))  # its lit door
        cv.fill(0, LANE, WIDTH, 60, c565(38, 34, 42))

    def light(self, cv, x, heat):
        """The fire's light round the crater: the kerb lit warm, and two lines of shine on the tarmac below, each
        as bright as the fire is hot. Opaque fills: the canvas has no blend."""
        k = heat * (GLOW_LEVELS - 1) // HEAT_MAX
        if k:
            for half, level in ((40, k // 3), (30, k * 2 // 3), (20, k)):  # brighter toward the crater
                cv.fill(x - half, LANE, 2 * half, 3, KERB_GLOW[level])
            for y, half in ((LANE + 4, 22), (LANE + 6, 16), (LANE + 9, 10)):  # the shine fades down the street
                cv.fill(x - half, y, 2 * half, 1, STREET_GLOW[k * half // 22])

    def paint(self, cv):
        rules = self.rules
        dx = SHAKE[self.shake_k] if self.shake_k < len(SHAKE) else 0
        for x, _ in self.came:  # a lit door in a house: someone came out
            cv.fill(x - 3, LANE - 13, 7, 13, DOOR_LIT)
        burning = rules.burning()
        for c in burning:
            self.light(cv, c.x + dx, c.heat())
        if self.layer.field is None:  # the flat fire, without the heat field
            for c in burning:
                h = c.heat() // 8
                cv.fill(c.x - 6 + dx, LANE - h, 12, h, ORANGE)
                cv.fill(c.x - 3 + dx, LANE - h // 2, 6, h // 2, YELLOW)
        self.layer.draw(cv)
        for c in rules.craters:  # over the flame's foot: it comes out of the crater
            if not pictures.draw(cv, "rescue_crater", c.x - 14 + dx, LANE - 1):
                cv.fill(c.x - 13 + dx, LANE, 26, 6, DARK)
                cv.fill(c.x - 11 + dx, LANE, 22, 1, c565(232, 70, 40) if c.burning() else GREY)
        for m in rules.meteors:  # the landing shadow grows on the street as the meteor comes, in a bright ring
            half = 2 + 12 * (FALL_MS - m.left_ms) // FALL_MS
            cv.fill(m.x - half + dx, LANE + 2, 2 * half, 3, SHADOW)
            cv.fill(m.x - half // 2 + dx, LANE + 1, half, 1, TARGET)
            self.draw_ring(cv, m.x + dx, half + 3, RING[m.left_ms // RING_BLINK_MS % 2])
        for p in rules.people:
            if p.state != CARRIED:
                self.draw_person(cv, p, dx)
        self.draw_dogs(cv, dx)
        self.draw_man(cv, dx)
        self.draw_help(cv, dx)
        self.draw_smokes(cv, dx)
        self.water.draw(cv)
        for m in rules.meteors:
            self.draw_meteor(cv, m)
        self.puffs.draw(cv)
        if 0 < self.flash_k <= len(FLASH):  # the frame after the impact, then two more, smaller and warmer
            for r, c in FLASH[self.flash_k - 1]:
                cv.disc(self.flash_x + dx, LANE - 4, r, c)
        for points, ms in self.thanks:  # "+1", or "+2" for a child, rising over the door
            cv.big("+%d" % points, 24, 66 - 24 * ms // THANKS_MS, YELLOW, 2)
        self.draw_lost(cv)

    def draw_person(self, cv, p, dx):
        side = "r" if p.facing > 0 else "l"
        w, h = PEOPLE_SIZES[p.kind]
        y = FEET - h + 1
        if p.state == WAVING:
            name = PEOPLE_POSES[p.kind, "wave", side][p.wave_pose()]
        else:
            name = PEOPLE_POSES[p.kind, "run", side][p.pose()]
        if not pictures.draw(cv, name, p.x - w // 2 + dx, y):
            tall, c = h - 8, FLAT[p.kind]
            cv.fill(p.x - 2 + dx, FEET - tall, 5, tall - 6, c)
            cv.fill(p.x - 2 + dx, FEET - tall - 4, 4, 4, c)
            step = p.pose() // 3 % 2 * 3 - 1
            cv.fill(p.x - 2 + step + dx, FEET - 6, 2, 6, c)
            cv.fill(p.x + 1 - step + dx, FEET - 6, 2, 6, c)
            if p.state == WAVING:
                cv.fill(p.x - 4 + dx, FEET - tall - 8, 2, 8, c)

    @staticmethod
    def draw_ring(cv, x, half, c):
        """A flat 1 px ring on the street round x, half px each side: the meteor's target."""
        inner = half * 3 // 4
        cv.fill(x - inner, LANE, 2 * inner + 1, 1, c)
        cv.fill(x - inner, LANE + 6, 2 * inner + 1, 1, c)
        for y, h in ((LANE + 1, 1), (LANE + 5, 1)):
            cv.fill(x - half + 1, y, 2, h, c)
            cv.fill(x + half - 2, y, 2, h, c)
        cv.fill(x - half, LANE + 2, 1, 3, c)
        cv.fill(x + half, LANE + 2, 1, 3, c)

    def draw_help(self, cv, dx):
        """Over each trapped person a pale arrow, bobbing, and "help!" on a plate, blinking. Drawn over the flames, so a
        fire beside them hides no letter; the plate ends above the fire's foot (PLATE_Y), so it hides no flame's
        foot either. The person stays under the arrow, never in the flames."""
        for p in self.rules.people:
            if p.state != WAVING:
                continue
            x, y = p.x + dx, PLATE_Y + 12 + p.wave_ms // 250 % 2
            cv.fill(x - 3, y, 7, 1, MARK)
            cv.fill(x - 2, y + 1, 5, 1, MARK)
            cv.fill(x - 1, y + 2, 3, 1, MARK)
            cv.fill(x, y + 3, 1, 1, MARK)
            if p.wave_ms % 1000 < 600:
                cv.fill(x - 21, PLATE_Y, 42, 11, DARK)
                cv.text("help!", x - 20, PLATE_Y + 2, YELLOW)

    def draw_smokes(self, cv, dx):
        """Meteors' see-through smoke where a person was lost, a frame each SMOKE_MS, each thinner."""
        for x, since in self.smokes:
            k = since // SMOKE_MS
            pictures.draw(cv, SMOKES[k], x - SMOKE_W // 2 + dx, FEET - SMOKE_H + 3, SMOKE_ALPHAS[k])

    def draw_dogs(self, cv, dx):
        """The dog of a man with a dog: ahead of him as they run, standing by as he waves, at the fireman's heels
        while the fireman carries him."""
        rules = self.rules
        for p in rules.people:
            if p.kind != DOGMAN:
                continue
            if p.state == CARRIED:
                man = rules.man
                x, facing, ran = man.x - (DOG_AHEAD_PX + 2) * man.facing, man.facing, man.ran
            else:
                x, facing, ran = p.x + DOG_AHEAD_PX * p.facing, p.facing, (p.ran if p.state == RUN else 0)
            name = DOG_NAMES["r" if facing > 0 else "l"][ran * DOG_POSES // DOG_STRIDE_PX % DOG_POSES]
            if not pictures.draw(cv, name, x - DOG_W // 2 + dx, FEET - DOG_H + 1):
                c = FLAT[DOGMAN]
                cv.fill(x - 6 + dx, FEET - 7, 12, 4, c)
                cv.fill(x + 4 * facing - 2 + dx, FEET - 10, 4, 3, c)
                cv.fill(x - 5 + dx, FEET - 3, 2, 3, c)
                cv.fill(x + 3 + dx, FEET - 3, 2, 3, c)

    def draw_man(self, cv, dx):
        man = self.rules.man
        name, cycle = self.man_picture()
        w = SIZES[cycle]
        if not pictures.draw(cv, name, man.x - w // 2 + dx, FEET - PICTURE_H + 1):
            cv.fill(man.x - 2 + dx, FEET - 20, 5, 12, DARK)
            cv.fill(man.x - 3 + dx, FEET - 24, 7, 4, YELLOW)
            step = man.run_pose() // 3 % 2 * 3 - 1
            cv.fill(man.x - 2 + step + dx, FEET - 8, 2, 8, DARK)
            cv.fill(man.x + 1 - step + dx, FEET - 8, 2, 8, DARK)
            if man.carrying is not None:  # the person in his arms, pale
                cv.fill(man.x + (1 if man.facing > 0 else -10) + dx, FEET - 17, 10, 3, WHITE)
        if man.flashing():
            x, y = man.x + 7 * man.facing + dx, FEET - 16
            cv.fill(x - 1, y - 1, 3, 3, WATER[0])
            cv.fill(x, y, 1, 1, WHITE)

    @staticmethod
    def meteor_at(m):
        """Where a meteor is in the sky: it comes down at a slant to where it lands."""
        return m.x + FALL_DX * m.left_ms // FALL_MS, FALL_TOP + (LANE - FALL_TOP) * (FALL_MS - m.left_ms) // FALL_MS

    def draw_meteor(self, cv, m):
        """A hot white core in a warm halo (its trail of embers is in the puffs)."""
        x, y = self.meteor_at(m)
        cv.fill(x - 3, y - 2, 6, 5, HALO)
        cv.fill(x - 2, y - 3, 4, 7, HALO)
        cv.fill(x - 1, y - 1, 3, 3, CORE)

    def draw_lost(self, cv):
        """The people lost: LOST_MAX crosses under the score bar, red for each one lost."""
        for i in range(LOST_MAX):
            x, c = 8 + 12 * i, RED if i < self.rules.lost_count else GREY
            for d in range(7):
                cv.fill(x + d, 22 + d, 2, 1, c)
                cv.fill(x + 6 - d, 22 + d, 2, 1, c)
