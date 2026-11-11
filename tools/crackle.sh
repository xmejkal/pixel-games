#!/bin/bash
# The crackle's try loop (P747): one command from a saved engine/core/fx_crackle.c to the sound on the board.
# It builds crackle_c.mpy, copies it with games/crackle.py, games/fire.py and games/sound.py, and runs
# probe733_games.py on Fire with CallbackRefill for SECONDS (10 by default). The board needs firmware with
# HeatField.take_births (P747; P751: with rises and engine.SoundBank, else GrainCrackle falls back to a bytearray;
# P753: with HeatField.stats, else FireSound is a GrainCrackle), and the amplifier wired as in P733. Its last line
# gives the seconds from the start of this script to the first pop.
#
#     tools/crackle.sh [seconds] [voice] [look]
#         voice: NativeCrackle (default), SampledCrackle, GrainCrackle or FireSound (P753)
#     GAME=BurningBodies tools/crackle.sh 30 FireSound   # the game: Fire (default) or BurningBodies (P753)
#     VOLUME=MasterVolume LEVEL=8 tools/crackle.sh 30 FireSound   # with the master volume at step 8 (P757)
#     VOLUME=ViperMasterVolume KNOB=1 SAVE=1 tools/crackle.sh 60 FireSound   # the knob turns the step and saves it
#
# The environment also sets the probe's VOLUME (default "": the mix as it is), LEVEL (default None), KNOB (default 0),
# SAVE (default 0), SAVE_EVERY_MS (default 0) and MIC (default 0). With a VOLUME, games/volume.py and
# games/volume_viper.py go to the board too, and with KNOB=1 games/encoder.py and games/pins.py (P757).
# With KNOB=1 each change of the step also shows the volume on the screen for 1 s (P762): games/overlay.py goes to
# the board with app.py, lcd.py, render.py and gfx.py. SPIN_EVERY_MS (default 0) is the overlay's run with no hand: the probe
# spins the step to an end at this period. ALPHA (default 255, solid) under 255 lets the game show through the picture.
#
# A look, such as "6, 24, 6000, 12000, 28400, 31600, 3, 4000, 224", replaces CRACKLE_LOOK in the crackle.py that this
# run copies (GRAIN_LOOK for GrainCrackle and FireSound, such as "0, 32768": bed gain, pop gain).
# That copy stays on the board until the next copy.
# GAME=BurningBodies also copies burning.py and plugins.py, which the bodies' whooshes hook into (P753).
# GrainCrackle and FireSound (P751, P753) also need the bank on the board: games/fire_bank.raw (about 250 KB, about
# 60 s to copy) goes only when `mpremote fs sha256sum` shows the board's copy differs.
# --- MVP (P747, P751, P753, P757, P762) ---
set -eo pipefail
START=$(date +%s)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SECONDS_RUN=${1:-10}
VOICE=${2:-NativeCrackle}
LOOK=${3:-}
GAME=${GAME:-Fire}
VOLUME=${VOLUME:-}
LEVEL=${LEVEL:-None}
MIC=${MIC:-0}
KNOB=${KNOB:-0}
SAVE=${SAVE:-0}
SAVE_EVERY_MS=${SAVE_EVERY_MS:-0}
SPIN_EVERY_MS=${SPIN_EVERY_MS:-0}
ALPHA=${ALPHA:-255}
TOOLS=$(ls -d "$HOME"/.espressif/tools/xtensa-esp-elf/*/xtensa-esp-elf/bin | tail -1)
IDF_PYTHON=$HOME/.espressif/python_env/idf5.5_py3.10_env/bin/python
PROBE_DIR=$(mktemp -d)
trap 'rm -rf "$PROBE_DIR"' EXIT
PROBE=$PROBE_DIR/probe747.py
CRACKLE_PY=$PROBE_DIR/crackle.py

PATH=$TOOLS:$PATH make -s -C "$ROOT/engine/natmod/crackle" ARCH=xtensawin CROSS=xtensa-esp32s3-elf- PYTHON="$IDF_PYTHON"
sed -e "s/^GAME = .*/GAME = \"$GAME\"/" -e 's/^REFILL = .*/REFILL = "CallbackRefill"/' -e 's/^IBUF = .*/IBUF = 2048/' \
    -e "s/^VOICE = .*/VOICE = \"$VOICE\"/" -e "s/^SECONDS = .*/SECONDS = $SECONDS_RUN/" \
    -e "s/^VOLUME = .*/VOLUME = \"$VOLUME\"/" -e "s/^LEVEL = .*/LEVEL = $LEVEL/" -e "s/^MIC = .*/MIC = $MIC/" \
    -e "s/^KNOB = .*/KNOB = $KNOB/" -e "s/^SAVE = .*/SAVE = $SAVE/" \
    -e "s/^SAVE_EVERY_MS = .*/SAVE_EVERY_MS = $SAVE_EVERY_MS/" \
    -e "s/^SPIN_EVERY_MS = .*/SPIN_EVERY_MS = $SPIN_EVERY_MS/" -e "s/^ALPHA = .*/ALPHA = $ALPHA/" \
    "$ROOT/probe733_games.py" > "$PROBE"
LOOK_NAME=CRACKLE_LOOK
case $VOICE in GrainCrackle | FireSound) LOOK_NAME=GRAIN_LOOK ;; esac
if [ -n "$LOOK" ]; then
    sed "s|^$LOOK_NAME = .*|$LOOK_NAME = ($LOOK)|" "$ROOT/games/crackle.py" > "$CRACKLE_PY"
else
    cp "$ROOT/games/crackle.py" "$CRACKLE_PY"
fi
echo "crackle_c.mpy sha256 $(shasum -a 256 "$ROOT/engine/natmod/crackle/crackle_c.mpy" | cut -d' ' -f1), engine $(git -C "$ROOT/engine" rev-parse --short HEAD)"
mpremote cp "$ROOT/engine/natmod/crackle/crackle_c.mpy" :crackle_c.mpy + cp "$CRACKLE_PY" :crackle.py \
    + cp "$ROOT/games/fire.py" :fire.py + cp "$ROOT/games/sound.py" :sound.py
if [ -n "$VOLUME" ]; then
    mpremote cp "$ROOT/games/volume.py" :volume.py + cp "$ROOT/games/volume_viper.py" :volume_viper.py
fi
if [ "$KNOB" = 1 ]; then
    mpremote cp "$ROOT/games/encoder.py" :encoder.py + cp "$ROOT/games/pins.py" :pins.py \
        + cp "$ROOT/games/app.py" :app.py  # app.run takes the encoder's pads, so the three stay in step (P757)
    mpremote cp "$ROOT/games/overlay.py" :overlay.py + cp "$ROOT/games/lcd.py" :lcd.py \
        + cp "$ROOT/games/render.py" :render.py + cp "$ROOT/games/gfx.py" :gfx.py  # app.py passes the overlay to the
    # outputs, and both canvases' keep takes its alpha (P762)
fi
if [ "$GAME" = BurningBodies ]; then
    mpremote cp "$ROOT/games/burning.py" :burning.py + cp "$ROOT/games/plugins.py" :plugins.py
fi
case $VOICE in GrainCrackle | FireSound) WITH_BANK=1 ;; *) WITH_BANK= ;; esac
if [ -n "$WITH_BANK" ]; then
    mpremote cp "$ROOT/games/fire_bank.py" :fire_bank.py
    HERE_SUM=$(shasum -a 256 "$ROOT/games/fire_bank.raw" | cut -d' ' -f1)
    BOARD_SUM=$(mpremote fs sha256sum :fire_bank.raw 2>/dev/null | tr -d '[:space:]' || true)
    case $BOARD_SUM in *"$HERE_SUM"*) echo "fire_bank.raw is on the board" ;; *) mpremote cp "$ROOT/games/fire_bank.raw" :fire_bank.raw ;; esac
fi
mpremote run "$PROBE" | while IFS= read -r line; do
    echo "$line"
    case $line in "first pop "*) echo "loop $(( $(date +%s) - START )) s from the script's start to the first pop" ;; esac
done
