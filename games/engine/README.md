# The engine package

`games/engine/` is the runtime that the games import (P849, stage 0b-1 of the engine plan,
[plan.md](../../docs/discovery/2026-11-16-p844-engine-plan/plan.md)). It is the folder `:engine/` on the board, and
`python3 tools/box.py deploy` copies it there as `.mpy` files (`--py`: as `.py` files). Stage 9 moves it to the
pixel-engine submodule.

| Module | What it holds |
| --- | --- |
| `signals.py` | `Signals`: a game emits a signal by its name, and each listener of that name is called at once |
| `clock.py` | `since`, `ticks_us` and `ticks_diff`: the board's tick clock, 0 on the Mac |

- `__init__.py` is empty, so each module imports alone: a later board takes only the modules it needs.
- A module imports only the modules of the package that its row of `DIRECTION` names, and MicroPython's built-in
  modules (`tests/test_engine_boundary.py`). It never imports a game's module or `engine_config`. The test fences
  this package only: the games get their own rule in a later stage of the plan.
- The C module of the firmware is `_engine`. The games import it as `import _engine as engine` until stage 5b, so in
  a game's module the name `engine` is the C module, not this package.

## The rule of two versions

Each hot part has one interface and two versions. The reference version is plain Python: it runs anywhere and is the
Mac's test oracle. The fast version is C or viper and gives the reference version's results, faster. `main.py` chooses
once at the start (stage 0b-2), and a setting forces the reference version per part. A test runs both versions on the
same input. The rule is P838's ([finding](../../docs/discovery/2026-11-16-p838-engine-layer/finding.md), section 2).
