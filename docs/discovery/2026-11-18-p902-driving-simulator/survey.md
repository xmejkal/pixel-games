# P902: how driving simulators and car games are built (a survey)

Basic research before a product discovery, written 2026-11-18 from sources. It holds facts, standard names and options. It holds no design and no decision. Nothing here was run on a board. Each claim carries a tag: `read` (I opened the page and it says so), `snippet` (a search result only) or `own` (my knowledge, no source read). `S12` points to the source list at the end.

The PO asked for a driving simulator feel: car physics, collisions, a drive path from the speed and the wheel angle, AI drivers and multiplayer. He wants a basic strategy first and a good one later, probably in C. He wants industry names. He also asks how much 3D to build, or whether to switch to a top-down camera. His words are on the P902 card.

## Summary

1. Today's Road game is a picture, not a simulation: a lane number, a speed number and a pseudo-3D road. No heading, no mass, no force (section 0).
2. The smallest real car model is the kinematic bicycle (CommonRoad "KS"). Its input is a steering angle and an acceleration. It has two parameters, the distances from the centre of mass to the axles [S3 read].
3. A dynamic bicycle with slip angles adds understeer and oversteer. Its tire model breaks near zero speed, so CommonRoad switches to the kinematic model below 0.1 m/s [S4 read].
4. On a real road the two models predicted a car about equally well. After one 200 ms step the error was 0.08 m and 0.07 m [S3 read]. Slip matters near the grip limit [S4 read].
5. The best code to read is GPL (TORCS, Speed Dreams, VDrift, Stunt Rally, Rigs of Rods). It cannot be copied into an MIT repository. The reusable code is MIT, BSD or zlib: Box2D, CommonRoad's vehicle models, Cyclone, Bullet, Jet [S17, S4, S20, S22, S12 read].
6. The view is a separate choice from the physics. "Pseudo-3D" cannot hold simulation depth by itself: "The depth of physics found in more simulation-like games tends to be lost" [S7 read].
7. A game on the ground plane can have one simulation and several cameras: top-down, chase, pseudo-3D. Fiedler's loop already splits the physics state from the render state [S14 read].
8. AI drivers have standard names: path following, pure pursuit, Stanley, PID for speed. Rubber-banding is a catch-up rule, not a driver model [S24, S25].
9. ESP-NOW carries 250 bytes (v1) or 1470 bytes (v2) per packet. A car state fits many times in one packet. Lockstep needs the same result on every box, which floats make hard [S16, S14 read].
10. The S3 has a single-precision FPU. The P4 has one too, plus a pixel accelerator that rotates only in 90 degree steps [S27 read].

## What a first basic strategy and a later good strategy could be, per part (options, not decisions)

| Part | Basic first | Good later |
| --- | --- | --- |
| Vehicle model | kinematic bicycle (KS) | dynamic bicycle (ST) below the grip limit, KS below a small speed |
| Tire | clamped linear lateral force | Pacejka Magic Formula or a brush model |
| Grip limit | friction circle (Kamm's circle) on the total force | load transfer feeds the circle per axle |
| Drivetrain | speed from throttle with a top speed | torque curve, gear ratios, differential |
| Drag and brakes | quadratic drag, constant brake force | downforce, brake balance, ABS |
| Collision | circles, walls as segments | oriented boxes, SAT, impulse response with friction and restitution |
| Surfaces | a grip factor per tile | a grip factor per tire, with the best touching area |
| View | pseudo-3D road as today | top-down camera, then a chase camera on the same simulation |
| AI | waypoints, speed from curvature | racing line, pure pursuit or Stanley, PID for speed |
| Multiplayer | a second input source on the box | ESP-NOW with state sync. Lockstep needs identical builds |
| Controls | stick x as steering, y as throttle and brake | dead zone, speed-sensitive steering, steering rate, assists |
| Step | fixed step with an accumulator | semi-implicit Euler at a higher rate. RK4 only after a test shows a need |

## 0. What the box has today

The box is an ESP32-S3 on a 320 by 240 display. It runs at about 22 to 24 fps, one frame every 40 ms (`games/app.py:67`, `FRAME_MS = 40`). A frame's step is at most 60 ms (`games/gfx.py:383-384`). The engine folder `engine/` is a git submodule that is empty in this worktree (`.gitmodules` names pixel-engine, and `git submodule status` shows it not initialised). So I read the engine only through `docs/engine-walkthrough.md`. The Python side of the engine is in `games/engine/` (`accel.py`, `actions.py`, `clock.py`, `signals.py`, `subpixel.py`). The README rows for Tunnel and Road are `README.md:84-85`. The stick is described at `README.md:196-197`.

How Road moves the car (`games/world3d.py:109-226`, class `Road`):

- The car has no heading. It has a lane number 0 to 2 (`lane`). It has a drawn lane `lx` that eases toward it. It has an odometer `odo` (`:118-120`).
- A button tap changes the lane. The stick picks the lane through `lean()` (`:122-129`, `:153-156`, and `lean` is in `games/engine/actions.py:18-21`). `lx` follows the lane at a rate of 12 per second (`:130`).
- Speed is a number: `6.5 + min(score, 40) * 0.08`, times 1.7 while FIRE is held (`:131-133`). It is not a force or a torque.
- The road's bend is a sine of the odometer (`:182`). It moves the drawn road only, not the car (`:164-168`).
- Collision is one test: an obstacle's depth crosses the player's depth while it is in the player's lane (`:139-143`).

How Road draws the road (`:180-212`): one band every 4 px (`SEG = 4`, `:115`) from the horizon row 88 down to row 232, so 36 bands. Each band gets a stripe parity from `int(K / t + odo) % 2` (`:184-194`), grass, rumble strips, asphalt and lane dashes. Trees and obstacles are scaled by `K / depth` (`:195-208`). The car is a few rectangles (`:217-226`). Tunnel (`:15-107`) projects four ring corners with a focal length `F = 150` (`:21`, `:69-71`). Both are views with no world behind them.

What is physics and what is not: Road has none. The engine has some, but not for cars. Its point bodies fall to a plane (`world_t`). Its balls are discs with a radius and no angle. They use a grid broad phase with 10 px cells and position relaxation after Jakobsen. They have Coulomb friction. Restitution works at the velocity level, with Box2D v3 names. They cost 4.2 ms at 100 settled balls and 13.8 ms at 300 (`docs/engine-walkthrough.md`, Lesson E). A fixed-step clock exists: `StepClock` (`games/motion.py:132-145`). The rule "C steps and paints, Python decides" is in section 0 of the walkthrough. The repository's own ESP-NOW spike is `docs/discovery/2026-11-16-p831-engine-capabilities/espnow.md`. The cost of one Road frame: not found in the files I read.

## 1. Vehicle models, from the simplest to the real ones

Answer first. Real simulators stack the same few parts. They are a bicycle model for the body and a tire model for the force at each wheel. They add a limit on total grip, a drivetrain and drag. For arcade cost, the sources point to a bicycle model with a saturating lateral tire force. Add a friction limit, a drivetrain with torque and gears, and drag. Full suspension and a four-wheel model are the expensive end [S1, S3, S4].

| Model, standard name | In, out | Cost per step (operation counts, my hand count, not measured) | Source |
| --- | --- | --- | --- |
| Point mass, "PM" | acceleration in. Position out | a few multiplies. Not a car, no turning circle | S4 read |
| Kinematic single-track (bicycle), "KS" | steering angle and acceleration in. Position, heading, speed out | 3 trig, 1 tan, 1 atan, about 15 multiplies | S3, S4 read |
| Dynamic single-track (bicycle), "ST", linear tire | the same in. Adds slip angle and yaw rate | about 3 trig and 40 multiplies, with one divide by speed per axle | S3, S4 read |
| Single-track drift, "STD" | ST with Pacejka tire forces | ST plus 2 atan and 1 sin per axle | S4 read |
| Multi-body, "MB" | full 3D car with suspension | far above the budget | S4 read |
| Ray-cast vehicle (Bullet, Godot) | engine force, brake, steering in. A rigid body with spring wheels out | a ray per wheel plus a rigid body | S22 read |

- Kinematic bicycle: each wheel pair is lumped into one wheel. There is no tire slip, so the speed vector lies along the link between the wheels [S4 read]. Its only parameters are the two distances from the centre of mass to the axles [S3 read]. CommonRoad's KS uses the rear axle as its reference point [S4 read, figure 1 caption]. It has the minimum turning radius for free, which a point mass has not [S4 read].
- Ackermann steering geometry: the front wheels turn by different angles so that all wheel axes meet on a line from the rear axle. On the page, "the inner wheel turns farther than the outer wheel" [S5 read]. The page calls it sound for low-speed manoeuvres and says pure Ackermann "ignores important dynamic and compliant effects" [S5 read]. With one lumped front wheel it is not needed.
- Dynamic bicycle: the lateral force of each axle is `F = -C * alpha` for the linear tire, with `C` the cornering stiffness and `alpha` the slip angle [S3 read]. Marco Monster writes the same: "Flateral = Ca * alpha", and "As the slip angle grows, so does the cornering force" [S1 read].
- Low speed: "any tire model becomes singular at low vehicle speeds", because the slip angle has the speed in the denominator [S3 read]. CommonRoad's ST "becomes singular for small velocities", so it switches to a kinematic model below 0.1 m/s [S4 read].
- When slip matters: "when the vehicle is not driving close to its physical capabilities, those effects are not dominant" [S4 read]. The test car drove a winding road at 13.8 m/s on average. The kinematic model (Euler, 100 ms) had a mean error of 0.08 m after one 200 ms step. The linear tire model had 0.07 m. After four steps it was 0.40 m against 0.27 m [S3 read]. A larger step helped the kinematic model because Euler truncation makes wider turns, like understeer [S3 read].

Tire models, in order of cost [S6 read unless marked]:

| Name | What it is | Source |
| --- | --- | --- |
| Linear | force proportional to slip angle, valid below the peak | S1, S3 read |
| Clamped linear | the same, capped at `mu * load` | S1 read (longitudinal case) |
| Brush models | simple physical models, popular in the 1960s and 1970s (Dugoff, Fancher and Segel, 1970) | S6 read |
| Fiala | the "stretched string tire model (Fiala 1954)" | S6 read |
| Pacejka "Magic Formula" | empirical: a sine of an arctangent of a slip term, with fitting constants B, C, D, E. "no particular physical basis" | S6 read |
| Physical, such as FTire and RMOD-K | far more detailed | S6 read |

The Magic Formula is in Pacejka's book "Tire and Vehicle Dynamics" (Butterworth-Heinemann, 3rd edition 2012) [S6 read]. One evaluation is 2 atan and 1 sin by its structure [S6 read]. Cheap on the S3 per wheel. The cost is in finding the constants for a car feel, not in the maths [own].

Other parts, each with its name and source:

- Friction circle, also traction circle or Kamm's circle: total acceleration is limited by `mu * g`. CommonRoad writes it as "the friction circle (aka Kamm's circle) limiting absolute acceleration" [S4 read]. Beckman's traction budget: the circle's boundary marks the limit, a point inside shows how the budget is spent. Weight transfer is factored out of the circle [S2 snippet].
- Load transfer: longitudinal acceleration moves load between the axles, "neglecting suspension dynamics" [S4 read]. The page of Marco Monster has a section "Weight Transfer": under acceleration the car "leans back" [S1 read]. Without springs the transfer is instant and can make a car unstable [S2 snippet, a forum post].
- Drivetrain: an engine torque curve (Monster's example peaks near 4400 rpm at about 475 N.m). Gear ratios (first 2.66 to sixth 0.50, reverse 2.90). A differential ratio (3.42). "What you gain in torque, you have to pay back in angular velocity" [S1 read]. Monster's sections: Engine Force, Gear Ratios, Drive wheel acceleration, Slip ratio and traction force [S1 read].
- Brakes: a constant force against the motion. When the speed reaches zero, stop the brake force [S1 read].
- Drag and rolling resistance: drag grows with the square of speed. Rolling resistance is linear [S1 read]. Downforce: not in the sources I read. The usual form is a lift coefficient, an area and speed squared [own].
- Suspension: a spring and a damper per wheel in ray-cast vehicles. Godot's VehicleBody3D is "based on the raycast vehicle system commonly found in physics engines" [S22 read]. Its inputs are `engine_force`, `brake` and `steering` [S22 read].
- Beckman's "The Physics of Racing": the pages returned HTTP 403, so I have search snippets only [S2 snippet]. Milliken and Gillespie: not opened.
- Marco Monster's article is copyrighted: "Copyright 2000-2003 Marco Monster. All rights reserved. This tutorial may not be copied or redistributed without permission." [S1 read]. Read it for ideas. Do not copy its text or tables.

## 2. Open-source simulators and car-physics code

Answer first. The simulators are GPL and large. Read them for structure. The reusable parts are small and permissive: CommonRoad's vehicle models (BSD 3-Clause), Box2D (MIT) and Cyclone (MIT). A GPL source file cannot be copied into an MIT project [own, not legal advice]. A paper's equations can be re-implemented from the published description [own].

| Project | What | Language | License, quoted | Copy into MIT? | Size and fit | Small idea |
| --- | --- | --- | --- | --- | --- | --- |
| TORCS [S23 read] | racing simulator for AI drivers | not stated on the page | "Open source under GPLv2 - the full source ships with every release." | no | whole game. Too big | plug-in modules: "The Robot Module Interface gives an AI driver access to simulation state". The simulation is replaceable |
| Speed Dreams [S23 read] | fork of TORCS | C and C++ | the page lists "GNU General Public License version 2.0 (GPLv2) and version 3.0 (GPLv3)" | no | too big | a motorsport sim on the TORCS plug-ins |
| VDrift [S23 read] | "cross-platform, open source driving simulation made with drift racing in mind" | not shown | "It is released under the GNU General Public License (GPL) v3." | no | 2,230 commits. Too big | docs pages "Car parameters" and "Numerical Integration" are worth reading |
| Stunt Rally [S23 read] | 3D racing game on VDrift and OGRE | C++ (tags) | "The license GNU GPL 3.0 applies only to code written by us." | no | too big | a game built on VDrift's car |
| Rigs of Rods [S23 read] | soft-body physics simulator | not shown | "Rigs of Rods is now licensed under GPLv3 or later:" | no | too big | soft-body vehicles |
| Box2D [S17 read] | 2D physics engine | portable C17 | "MIT license" (file `LICENSE`) | yes | the manual calls the solver "a high performance sequential solver that operates in order N time". The repo's engine already uses its v3 names | the car as a body with no gravity (see iforce2d) |
| iforce2d top-down car [S21 read] | Box2D tutorial, last edited 2014-03-19 | C++ | no license stated for the code | no | tiny | cancel the sideways velocity by an impulse, cap the impulse so the tire skids, a grip factor per ground area |
| Bullet [S22 read] | physics SDK, 14.9k stars | C++ | "All source code files are licensed under the permissive zlib license" | yes | big. The page names no vehicle class | ray-cast vehicle (class name `btRaycastVehicle`, own) |
| CommonRoad vehicle models [S4 read] | PM, KS, KST, ST, STD, MB with a 30-page PDF | Python and MATLAB | "BSD 3-Clause License, Copyright 2020 Technical University of Munich, Professorship of Cyber-Physical Systems." | yes, keep the notice | a few equations each. Fits | the model ladder, and the switch from ST to KS at low speed |
| F1TENTH gym [S23 read] | simulator for 1/10 scale race cars | not stated | "MIT license" | yes | not found what its models are | not read in depth |
| Cyclone [S20 read] | the engine of Millington's physics book (the page names it "Game Physics Engine Design") | not stated | "MIT license", "Copyright (c) 2003-2009 Ian Millington." | yes | small | rigid-body structure and contact resolution |
| Jet [S12 read] | 3D rasteriser for ESP32 | C++17 | "Jet is distributed under the **MIT License**." | yes | 563 stars, 51 commits. See section 3 | see section 3 |

Fit for a single-precision FPU at 240 MHz after a port to C [own, from the sizes above]: the equations of KS, ST and the Magic Formula (a few dozen float operations, trig and one divide). Probably Box2D's ideas, not its whole library. Far too big: TORCS, Speed Dreams, VDrift, Stunt Rally and Rigs of Rods, because they are whole games with their own renderers.

## 3. The view, and how much 3D

Answer first. Five ways to get a picture from the same world, from cheap to dear. The Road game is already the second one. The physics works on the ground plane, so a top-down view and a pseudo-3D view can both read the same state [own].

| View | Standard name | What the camera can do | Cost per frame (rough, own) | On a microcontroller |
| --- | --- | --- | --- | --- |
| Top-down 2D | tile map plus sprites. The car picture is pre-turned to N angles | scroll and follow. Zoom needs scaled tiles | one blit per visible tile and car. 20 by 15 tiles of 16 px is 300 blits | the box's engine blits already [own] |
| Pseudo-3D road | "pseudo 3D" or segment-based road, as in OutRun | follow, lean in curves, hills. No sideways camera, no real depth | one polygon or band per visible segment. The box draws 36 bands | esp32s3-arcade-3d [S11 read] |
| Mode 7 | an affine floor, F-Zero, Super Mario Kart | rotate and scale one plane. "trades height for depth" | a texture lookup per floor pixel, a matrix per scanline | none found |
| Raycasting | one ray per screen column over a grid | turn only. Walls of one height | 320 rays per frame | not searched |
| 3D polygons | software rasteriser | any camera | triangles per frame, plus fill | Jet, esp32_3d_engine [S12 read, S13 snippet] |

- Lou's Pseudo 3D Page (Louis Gorenfeld): the road is read scanline by scanline from a buffer of distances. The projection is a perspective divide. Curves come from an accumulating shift (a `dx` and a `ddx` per line). Hills from the number of lines per road-map entry. Sprites are drawn back to front and scaled by 1/Z [S7 read]. Accurate 3D geometry is impossible with this method, and "The depth of physics found in more simulation-like games tends to be lost" [S7 read]. The page gives no per-frame cost [S7 read].
- Jake Gordon's JavaScript racer: about 500 segments, each with two points. Each frame it projects a fixed number of segments from the camera. It skips hidden ones. It draws grass, road, rumble strips and lane marks as polygons. The car is a scaled sprite [S8 read]. The code is on GitHub. The article page states no license [S8 read].
- esp32s3-arcade-3d: an "OutRun-style pseudo-3D racing game for the ESP32-S3 microcontroller with an ILI9341 320×240 SPI display". It runs on an ESP32-S3 with 8 MB PSRAM, in RGB565, with a double buffer in PSRAM. The car is a 3D mesh with scanline affine texture mapping. Its list of physics is acceleration, friction coast-down, centrifugal drift, hill gravity, collision with recovery and lap timing. The page shows no license and no frame rate [S11 read]. A write-up is said to quote about 30 fps [S13 snippet]. No license means the code cannot be copied [own].
- Mode 7 is "a graphics mode that allows a background layer to be rotated and scaled". The matrix is often set "for each scanline" [S9 read]. A single plane: the sprites need another method [S9 read]. A Mode 7 floor on a microcontroller: not found.
- Raycasting (Lode Vandevenne): one ray per stripe, a grid walk (DDA), wall height inversely proportional to distance. The basic engine has no height changes or slopes [S10 read]. Its page is "All rights reserved". It fits a tunnel better than a road [own].
- 3D polygons: Jet is "A tiny, dependency-free, fixed-function 3D rasteriser" claiming "up to 100k tris/sec" on an ESP32-S3. The page says this counts rasterised triangles over render time and leaves out display scanout [S12 read]. The Espressif component `esp32_3d_engine` lists ST7789 over SPI and a Waveshare ST7789 example at 240 by 320 [S13 snippet]. `a3d` is a header-only rasteriser that draws horizontal strips into a small buffer [S13 snippet]. Licenses of both: not found.
- The ESP32-P4's pixel accelerator rotates in steps of 0, 90, 180 and 270 degrees only. It scales with 4-bit integer and 8-bit fraction factors [S27 read]. So it cannot turn a car sprite to any angle (my inference).

The pattern that separates simulation from view. Fiedler's "Fix Your Timestep!" keeps a physics state and renders between the previous and the current state with `alpha = accumulator / dt` [S14 read]. That is the "simulation and presentation" split [own]. Game Programming Patterns' "Game Loop" chapter names the loop that decouples game time from the frame [own. Page not opened]. Then a camera is a function from the world state to a picture: top-down, chase, pseudo-3D [own]. Today's Road has no such split: `lane`, `lx` and `odo` are both state and view (section 0).

## 4. Collisions for cars

Answer first. Cars are boxes. A simple version uses 1 to 3 circles per car. The sequence is the same in every engine: a broad phase finds near pairs, a narrow phase makes contact points and a normal, then an impulse solver fixes the speeds.

| Step | Standard name | Source |
| --- | --- | --- |
| Shapes | circle, oriented box (OBB), polygon, segment for walls | S19 read, own |
| Broad phase | AABB overlap. A dynamic tree (bounding volume hierarchy). The repo's grid | S17 read. S0 repo |
| Narrow phase | separating axis theorem (SAT) | S19 read |
| Contact | a manifold: contact points and a normal | S17 read |
| Response | sequential impulses, accumulated impulses, warm starting | S18 read |
| Friction | Coulomb friction. The cone `\|Pt\| <= mu * Pn` | S18 read |
| Restitution | bounce at the velocity level, with a threshold | S0 repo, S17 |

- Box2D manual: a contact needs overlapping shape bounding boxes. A contact manifold "holds the contact points and normal vector between colliding shapes". Friction is "the Coulomb (dry) friction coefficient, usually in the range [0,1]" [S17 read].
- SAT: "If two convex objects are not penetrating, there exists an axis for which the projection of the objects will not overlap". A rectangle needs only two axes. Two circles need one (the line between the centres). The smallest overlap gives the "minimum translation vector", which is the normal and the depth [S19 read].
- Erin Catto, "Fast and Simple Physics using Sequential Impulses" (GDC 2006): normal impulses prevent penetration. Tangent impulses impose friction. Clamp the accumulated impulse, not the single step's. Friction is clamped to `mu` times the normal impulse. Warm starting applies the old accumulated impulses at the start of the step, giving "less iterations and greater stability" [S18 read].
- Millington's Cyclone is the small MIT reference for the book's contact code [S20 read]. The repo's balls already run this chain in C, with a grid broad phase and position relaxation (`docs/engine-walkthrough.md`, Lesson E). They are discs without an angle, so a car with a heading is new.
- Track limits: walls as segments or as solid tiles [own]. Surfaces with other grip: iforce2d marks ground areas as sensor fixtures with a friction modifier. Each tire uses the best-grip area it touches, and that value scales friction, drag and drive [S21 read].
- A first collision for a pseudo-3D game: the test the Road game has today, depth and lane (`games/world3d.py:139-143`).

## 5. AI drivers

Answer first. The standard chain is a path made of waypoints, a steering law that follows it, and a speed law. The names:

| Part | Standard name | What it does | Source |
| --- | --- | --- | --- |
| Path | waypoints, racing line | the line to follow. The racing line is also a player assist | S26 snippet |
| Path following | "Path Following" steering behavior (Reynolds, GDC 1999) | stay near a path | S24 read (listed only) |
| Steering | pure pursuit | the curvature that takes the car to a goal point some distance ahead on the path | S24 snippet |
| Steering | Stanley controller | a steering law on a simple kinematic model. The car that won the DARPA Grand Challenge | S24 snippet |
| Speed | PID for speed | throttle and brake from the speed error | own |
| Pace | rubber-banding, catch-up | a speed bonus for AI cars behind the player and a speed cut for AI cars ahead | S25 read |

- Craig Reynolds, "Steering Behaviors For Autonomous Characters" (GDC 1999) lists Seek, Pursue, Obstacle Avoidance, Path Following and more. OpenSteer is its C++ library, license not stated on the page [S24 read].
- Pure pursuit: R. Craig Coulter, "Implementation of the Pure Pursuit Path Tracking Algorithm", CMU-RI-TR-92-01, January 1992. It was used on the Terragator, NavLab and NavLab II [S24 snippet]. It needs the kinematic bicycle's wheelbase [own].
- Stanley: Jarrod M. Snider, "Automatic Steering Methods for Autonomous Automobile Path Tracking", CMU-RI-TR-09-08, February 2009, compares selected tracking methods. It finds that "none of the approaches work well in all applications" [S24 read]. The page I read does not name pure pursuit or Stanley. The table of contents does, per a mirror [S24 snippet]. The original Stanley paper is Thrun et al., Journal of Field Robotics 2006 [own. Not opened].
- Rubber-banding: it "dynamically adjusts AI players to the player's skill and performance level" [S25 read, Dave Mark, 2010]. Mario Kart pairs it with items weighted by position. Nintendo's algorithm is in US Patent 7278913 [S25 snippet]. Critics say it makes wins feel unearned [S25 snippet]. What simulators do instead: not found. From my own knowledge: skill levels that scale the AI's pace, its braking margin and its mistakes, not its physics [own].
- The kinematic bicycle (section 1) is also the model for the AI's planning [S3 read].

## 6. Multiplayer on small devices

Answer first. Two families. Lockstep sends only inputs, and every box runs the same simulation. State synchronization sends the objects' state, and each box predicts and corrects.

| | Deterministic lockstep | State synchronization with prediction |
| --- | --- | --- |
| Sends | inputs only. "bandwidth is proportional to the size of the input, not the number of objects" | the state of the objects, by priority |
| Needs | the same result on every machine, bit for bit | a correction that blends an error away |
| Fails when | one input is late: the step waits | packets are lost: extrapolate on the last input |
| Source | S14 read | S14 read, S15 read |

- Fiedler, "Deterministic Lockstep" (2014-11-29): "Floating point determinism is a complicated subject and there's no silver bullet". Results can differ across compilers, operating systems and architectures. A playout buffer smooths jitter at a price in latency. Send every unacknowledged input in each UDP packet. The input in his example is about 6 bits. He reports smooth play at 2 seconds of latency and 25 % loss [S14 read]. A later board with another CPU (ESP32-P4 is RISC-V) makes bit-equal floats harder [own].
- Fiedler, "State Synchronization" (2015-01-05): a packet holds a sequence number, up to 32 redundant inputs and up to 64 state updates. A priority accumulator picks which objects to send. Both sides quantise the state. Corrections decay as an error offset (a blend of 0.95 for small errors). The target is 256 kbit/s [S14 read].
- Gambetta, "Client-Side Prediction and Server Reconciliation": the client applies its own input at once. The server stays authoritative. The client drops acknowledged inputs and replays the rest. Entity interpolation for other players is the next part, which I did not read [S15 read].
- ESP-NOW [S16 read]: 250 bytes per packet on v1.0 and 1470 bytes on v2.0. A default rate of 1 Mbps. Up to 20 peers. "If the channel is set to 0, data will be sent on the current channel". The send callback returns success "if the data is received successfully on the MAC layer". The page adds: "It is not guaranteed that application layer can receive the data". The page suggests a sequence number to drop duplicates and application-level acknowledgments. Broadcast works. The repo's spike measured nothing. It quotes another source for 5.6 ms one way at 12 bytes. It counts 25 messages a second at a 40 ms frame (`espnow.md`, sections 1 and 2).
- Arithmetic (own): a car's x, y, heading, speed and steering as float32 is 20 bytes. Eight cars is 160 bytes, within 250. One packet per frame is enough.
- A second player on the same box (own): a second input source, because the box has one stick, one button and one knob. The repo's action map (`README.md:190-197`) already turns several inputs into one action. The P831 spike's "remote BOOT button" idea carries two stick axes in 8 bytes. A second car state in the simulation. A camera for two cars (a shared top-down view, or two 160 px halves, which costs the same pixels in total). Its AI option is a car with a driver from section 5.

## 7. Controls

Answer first. The stick gives two axes from -100 to 100. The box already reads them (`games/engine/actions.py`, `lean` at `:18-21`, `rate` at `:24`). The sources give names for what a driving game does with them.

- Steering from a stick: the steering angle is moved toward the wanted angle at a limited rate, not set at once. iforce2d does it with joint limits "moving toward a desired steering angle at a limited rate" [S21 read]. CommonRoad limits steering angle, steering angle velocity and speed [S4 read]. Names: steering angle limit (steering lock), steering rate limit [S4 read].
- Dead zone and speed-sensitive steering (less lock at speed): standard in console racing games. I opened no source [own].
- Throttle and brake on one axis: forward is throttle, back is brake and then reverse [own]. Monster: at zero speed, stop the brake force [S1 read].
- Assists, as named in console racing games [S26 snippet from guides to Forza, F1 and Gran Turismo]. ABS stops the wheels from locking. Traction control limits wheelspin. Stability management brakes single wheels against rotation. Steering assist and braking assist let the game steer or brake. The racing line is shown on the road. The Forza page itself returned HTTP 403.
- A friction-circle limit on the commanded acceleration is a simple stability assist [S4 read for the constraint. The use is own].

## 8. The step

Answer first. Use a fixed step with an accumulator, and semi-implicit Euler unless a test shows a need for more.

- Fixed step: Fiedler's "Fix Your Timestep!" (2004-06-10) gives a fixed delta time. An accumulator "produces time" for the simulation to "consume". Leftover time carries over. The rendered state is interpolated. A cap on steps per frame guards against the "spiral of death" [S14 read]. The repo's `StepClock` is this pattern with a cap: "steps past cap in one frame are dropped, so a long frame slows the world instead of stepping it in a burst" (`games/motion.py:132-145`).
- Integrators, from "Integration Basics" (Fiedler, 2004-06-01): explicit Euler is first order and gains energy on a spring. Semi-implicit Euler is first order and symplectic, and "most commercial game physics engines use this integrator". RK4 is fourth order with four evaluations per step and "extra runtime cost" [S14 read]. Vehicle papers use Euler at 100 to 200 ms [S3 read].
- Float or fixed point: the S3 has a single-precision FPU, and "all currently available FPUs support single-precision only", so a `double` is done in software [S27 read]. The repo notes that "a float division and `sqrtf` are library calls" on the S3. It fixed that with a fast inverse square root (`docs/engine-walkthrough.md`, Lesson F). The repo's Python helpers use small ints to allocate nothing per frame (`games/engine/actions.py:19-20`). Fixed point for a car: not found in the sources. Not needed for range, since a car's numbers are small [own].
- The ESP32-P4 [S27 read, Espressif product page and datasheets via the Espressif documentation search]: a dual-core RISC-V up to 400 MHz. It has "single-precision FPU and AI extensions" and 768 KB of L2 memory. It has a pixel-processing accelerator (PPA) for scaling, rotation in 90 degree steps, mirroring and blending. Chip revision v1.3 defaults to 360 MHz and v3.x reaches 400 MHz. The pre-release datasheet v0.7 lists 16 MB or 32 MB of PSRAM in the package. It adds no 3D hardware: the PPA is 2D only.

## Not found or not read

- Marco Monster's original site (the asawicki.info mirror gave a bot check, so I read the rsms.me mirror) and Beckman's pages (HTTP 403, snippets only).
- Not opened: Milliken, Gillespie, Pacejka's book, Thrun's Stanley paper, Millington's book, Fiedler's snapshot interpolation page, Gambetta's entity interpolation part, Catto's later GDC talks.
- Not searched: Rocket League's networked car physics. Not found: a Mode 7 floor on a microcontroller, and the license of Godot on the page I read. Also not found: the vehicle models of F1TENTH gym, where VDrift keeps its car dynamics, and the licenses of Jake Gordon's code, `esp32_3d_engine` and `a3d`.
- Nothing measured: the cost of a Road frame on the board, the time of any model on the S3, the frame rate of esp32s3-arcade-3d beyond a snippet. No P4 board was checked.

## Sources

Tags: read means the page was opened. A PDF was read as text. S0 is this repository (`docs/engine-walkthrough.md` and the files named in section 0).

| Id | Title and URL | Status |
| --- | --- | --- |
| S1 | Marco Monster, "Car Physics for Games", v1.9, Nov 2003, mirror: https://rsms.me/etc/car-physics/ | read |
| S2 | Brian Beckman, "The Physics of Racing", part 7 "The Traction Budget": https://www.pelicanparts.com/techarticles/physics_racing/part7.htm and https://gamedev.net/tutorials/programming/math-and-physics/the-physics-of-racing-part-7-the-traction-bu-r1616 | snippet (403) |
| S3 | Kong, Pfeiffer, Schildbach, Borrelli, "Kinematic and Dynamic Vehicle Models for Autonomous Driving Control Design", IEEE IV 2015, DOI 10.1109/ivs.2015.7225830, copy: https://nuhuo08.github.io/control/IV_KinematicMPC_jason.pdf | read |
| S4 | Althoff and Würsching, "CommonRoad: Vehicle Models (Version 2020a)": https://gitlab.lrz.de/tum-cps/commonroad-vehicle-models/-/raw/master/vehicleModels_commonRoad.pdf and its README and `LICENSE.txt` in the same repository | read |
| S5 | "Ackermann steering geometry", Wikipedia: https://en.wikipedia.org/wiki/Ackermann_steering_geometry | read |
| S6 | "Hans B. Pacejka" and "Tire model", Wikipedia: https://en.wikipedia.org/wiki/Hans_B._Pacejka , https://en.wikipedia.org/wiki/Tire_model | read |
| S7 | Louis Gorenfeld, "Lou's Pseudo 3D Page": http://www.extentofthejam.com/pseudo/ | read |
| S8 | Jake Gordon, "How to build a racing game - straight roads": https://jakesgordon.com/writing/javascript-racer-v1-straight/ | read |
| S9 | "Mode 7", Wikipedia: https://en.wikipedia.org/wiki/Mode_7 | read |
| S10 | Lode Vandevenne, "Raycasting", Lode's Computer Graphics Tutorial: https://lodev.org/cgtutor/raycasting.html | read |
| S11 | davidmonterocrespo24/esp32s3-arcade-3d: https://github.com/davidmonterocrespo24/esp32s3-arcade-3d | read |
| S12 | CubeCoders/Jet: https://github.com/CubeCoders/Jet | read |
| S13 | Search results: "The ESP32 Goes 3D: Retro Racing on a Chip" https://www.hackster.io/news/the-esp32-goes-3d-retro-racing-on-a-chip-ba2abada65ab and "esp32 3d engine" https://components.espressif.com/components/andresragot/esp32_3d_engine and "a3d" https://components.espressif.com/components/0015/a3d/versions/0.9.4/examples/ESP-IDF/Waveshare_ESP32-S3-Touch-LCD-2 | snippet |
| S14 | Glenn Fiedler, Gaffer On Games: "Fix Your Timestep!" https://gafferongames.com/post/fix_your_timestep/ and "Integration Basics" https://gafferongames.com/post/integration_basics/ and "Deterministic Lockstep" https://gafferongames.com/post/deterministic_lockstep/ and "State Synchronization" https://gafferongames.com/post/state_synchronization/ | read |
| S15 | Gabriel Gambetta, "Fast-Paced Multiplayer (Part II): Client-Side Prediction and Server Reconciliation": https://www.gabrielgambetta.com/client-side-prediction-server-reconciliation.html | read |
| S16 | "ESP-NOW - ESP32-S3 - ESP-IDF Programming Guide": https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_now.html | read |
| S17 | Box2D: https://github.com/erincatto/box2d and "Box2D: Overview": https://box2d.org/documentation/ | read |
| S18 | Erin Catto, "Fast and Simple Physics using Sequential Impulses", GDC 2006: https://box2d.org/files/ErinCatto_SequentialImpulses_GDC2006.pdf | read |
| S19 | dyn4j, "SAT (Separating Axis Theorem)", 2010-01-01: https://dyn4j.org/2010/01/sat/ | read |
| S20 | idmillington/cyclone-physics: https://github.com/idmillington/cyclone-physics | read |
| S21 | iforce2d, "Top-down car physics" (Box2D C++ tutorials): https://www.iforce2d.net/b2dtut/top-down-car | read |
| S22 | Bullet: https://github.com/bulletphysics/bullet3 and Godot, "VehicleBody3D": https://docs.godotengine.org/en/stable/classes/class_vehiclebody3d.html | read |
| S23 | TORCS https://torcs.sourceforge.net/ and Speed Dreams https://sourceforge.net/projects/speed-dreams/ and VDrift https://github.com/VDrift/vdrift and Stunt Rally https://github.com/stuntrally/stuntrally and Rigs of Rods https://github.com/RigsOfRods/rigs-of-rods and F1TENTH gym https://github.com/f1tenth/f1tenth_gym | read (project pages) |
| S24 | Craig Reynolds, "Steering Behaviors For Autonomous Characters" https://www.red3d.com/cwr/steer/ (read). Snider, CMU-RI-TR-09-08 https://publications.ri.cmu.edu/automatic-steering-methods-for-autonomous-automobile-path-tracking (read, names not on the page). Coulter, CMU-RI-TR-92-01 https://www.ri.cmu.edu/publications/implementation-of-the-pure-pursuit-path-tracking-algorithm/ | read / snippet |
| S25 | Dave Mark, "Rubber-Banding as a Design Requirement", 2010-06-02: https://gamedeveloper.com/design/rubber-banding-as-a-design-requirement (read). Patent and Mario Kart: search results of the query on rubber band AI | read / snippet |
| S26 | Search results on driving assists: https://simracingsetup.com/forza/forza-motorsport-assists-settings/ , https://simracingsetup.com/ea-sports-f1/f1-25-assists-guide/ | snippet |
| S27 | Espressif: ESP32-P4 product page https://www.espressif.com/en/products/socs/esp32-p4#features and datasheet https://documentation.espressif.com/esp32-p4_datasheet_en.html and chip revision v3.x user guide https://documentation.espressif.com/esp32-p4-chip-revision-v3.x_user_guide_en.html and "Floating-Point Units on Espressif SoCs: Why (and when) they matter" https://developer.espressif.com/blog/2025/10/cores_with_fpu/ | read (through Espressif's documentation search) |
