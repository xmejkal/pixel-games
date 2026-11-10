#!/bin/sh
# The crackle's try loop (P747): one command from a saved engine/core/fx_crackle.c to the sound on the board.
# It builds crackle_c.mpy, copies it with games/crackle.py and games/fire.py, and runs probe733_games.py on Fire with
# the C crackle for SECONDS (10 by default). The board needs firmware with HeatField.take_births (P747), and the
# amplifier wired as in P733. Its last line gives the seconds from the start of this script to the first pop.
#
#     tools/crackle.sh [seconds] [voice]      # voice: NativeCrackle (default) or Crackle
# --- MVP (P747) ---
set -e
START=$(date +%s)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SECONDS_RUN=${1:-10}
VOICE=${2:-NativeCrackle}
TOOLS=$HOME/.espressif/tools/xtensa-esp-elf/esp-14.2.0_20251107/xtensa-esp-elf/bin
IDF_PYTHON=$HOME/.espressif/python_env/idf5.5_py3.10_env/bin/python
PROBE_DIR=$(mktemp -d)
PROBE=$PROBE_DIR/probe747.py

PATH=$TOOLS:$PATH make -s -C "$ROOT/engine/natmod/crackle" ARCH=xtensawin CROSS=xtensa-esp32s3-elf- PYTHON="$IDF_PYTHON"
sed -e 's/^GAME = .*/GAME = "Fire"/' -e 's/^REFILL = .*/REFILL = "CallbackRefill"/' -e 's/^IBUF = .*/IBUF = 2048/' \
    -e "s/^VOICE = .*/VOICE = \"$VOICE\"/" -e "s/^SECONDS = .*/SECONDS = $SECONDS_RUN/" \
    "$ROOT/probe733_games.py" > "$PROBE"
mpremote cp "$ROOT/engine/natmod/crackle/crackle_c.mpy" :crackle_c.mpy + cp "$ROOT/games/crackle.py" :crackle.py \
    + cp "$ROOT/games/fire.py" :fire.py + cp "$ROOT/games/sound.py" :sound.py
mpremote run "$PROBE" | while IFS= read -r line; do
    echo "$line"
    case $line in "first pop "*) echo "loop $(( $(date +%s) - START )) s from the script's start to the first pop" ;; esac
done
rm -rf "$PROBE_DIR"
