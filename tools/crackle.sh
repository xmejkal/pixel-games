#!/bin/bash
# The crackle's try loop (P747): one command from a saved engine/core/fx_crackle.c to the sound on the board.
# It builds crackle_c.mpy, copies it with games/crackle.py, games/fire.py and games/sound.py, and runs
# probe733_games.py on Fire with CallbackRefill for SECONDS (10 by default). The board needs firmware with
# HeatField.take_births (P747; P751: with rises and engine.SoundBank, else GrainCrackle falls back to a bytearray), and
# the amplifier wired as in P733. Its last line gives the seconds from the start of
# this script to the first pop.
#
#     tools/crackle.sh [seconds] [voice] [look]   # voice: NativeCrackle (default), SampledCrackle or GrainCrackle
#
# A look, such as "6, 24, 6000, 12000, 28400, 31600, 3, 4000, 224", replaces CRACKLE_LOOK in the crackle.py that this
# run copies. That copy stays on the board until the next copy.
# GrainCrackle (P751) also needs the bank on the board: games/fire_bank.raw (about 250 KB, about 60 s to copy) goes
# only when `mpremote fs sha256sum` shows the board's copy differs.
# --- MVP (P747, P751) ---
set -eo pipefail
START=$(date +%s)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SECONDS_RUN=${1:-10}
VOICE=${2:-NativeCrackle}
LOOK=${3:-}
TOOLS=$(ls -d "$HOME"/.espressif/tools/xtensa-esp-elf/*/xtensa-esp-elf/bin | tail -1)
IDF_PYTHON=$HOME/.espressif/python_env/idf5.5_py3.10_env/bin/python
PROBE_DIR=$(mktemp -d)
trap 'rm -rf "$PROBE_DIR"' EXIT
PROBE=$PROBE_DIR/probe747.py
CRACKLE_PY=$PROBE_DIR/crackle.py

PATH=$TOOLS:$PATH make -s -C "$ROOT/engine/natmod/crackle" ARCH=xtensawin CROSS=xtensa-esp32s3-elf- PYTHON="$IDF_PYTHON"
sed -e 's/^GAME = .*/GAME = "Fire"/' -e 's/^REFILL = .*/REFILL = "CallbackRefill"/' -e 's/^IBUF = .*/IBUF = 2048/' \
    -e "s/^VOICE = .*/VOICE = \"$VOICE\"/" -e "s/^SECONDS = .*/SECONDS = $SECONDS_RUN/" \
    "$ROOT/probe733_games.py" > "$PROBE"
if [ -n "$LOOK" ]; then
    sed "s|^CRACKLE_LOOK = .*|CRACKLE_LOOK = ($LOOK)|" "$ROOT/games/crackle.py" > "$CRACKLE_PY"
else
    cp "$ROOT/games/crackle.py" "$CRACKLE_PY"
fi
mpremote cp "$ROOT/engine/natmod/crackle/crackle_c.mpy" :crackle_c.mpy + cp "$CRACKLE_PY" :crackle.py \
    + cp "$ROOT/games/fire.py" :fire.py + cp "$ROOT/games/sound.py" :sound.py
if [ "$VOICE" = GrainCrackle ]; then
    mpremote cp "$ROOT/games/fire_bank.py" :fire_bank.py
    HERE_SUM=$(shasum -a 256 "$ROOT/games/fire_bank.raw" | cut -d' ' -f1)
    BOARD_SUM=$(mpremote fs sha256sum :fire_bank.raw 2>/dev/null | tr -d '[:space:]' || true)
    case $BOARD_SUM in *"$HERE_SUM"*) echo "fire_bank.raw is on the board" ;; *) mpremote cp "$ROOT/games/fire_bank.raw" :fire_bank.raw ;; esac
fi
mpremote run "$PROBE" | while IFS= read -r line; do
    echo "$line"
    case $line in "first pop "*) echo "loop $(( $(date +%s) - START )) s from the script's start to the first pop" ;; esac
done
