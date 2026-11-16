#!/bin/bash
# Build MicroPython v1.29.0 for the FireBeetle 2 ESP32-S3 (N16R8), with ESP-IDF v5.5.2.
# Usage: ./build.sh            the stock image
#        ./build.sh s3lcd      the image with the s3lcd C module
#        ./build.sh engine     s3lcd and the engine module (P590 bodies, P595 fire), in build-engine, built clean (P848)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MPY="$HOME/esp/micropython-v1.29.0"
# The engine and its driver are submodules (P632): fetch them if this clone was made without --recurse-submodules
[ -f "$HERE/engine/driver/src/micropython.cmake" ] || git -C "$HERE" submodule update --init --recursive
[ -d "$MPY" ] || git clone -q -b v1.29.0 --depth 1 https://github.com/micropython/micropython.git "$MPY"
source "$HOME/esp/esp-idf-v5.5.2/export.sh" > /dev/null
make -C "$MPY/mpy-cross" -j8 > /dev/null
cd "$MPY/ports/esp32"
ARGS=(BOARD=ESP32_GENERIC_S3 BOARD_VARIANT=SPIRAM_OCT)
if [ "${1:-}" = s3lcd ]; then
  ARGS+=(USER_C_MODULES="$HERE/engine/driver/src/micropython.cmake" BUILD=build-s3lcd)
elif [ "${1:-}" = engine ]; then
  ARGS+=(USER_C_MODULES="$HERE/micropython.cmake" BUILD=build-engine)
  # Clean (P848): every worktree builds into this one folder, and genhdr/module keeps each tree's binding.c.module, so
  # an incremental build registered another tree's engine beside this tree's _engine
  rm -rf "$MPY/ports/esp32/build-engine"
fi
make "${ARGS[@]}" submodules > /dev/null
make "${ARGS[@]}" -j8
if [ "${1:-}" = engine ]; then
  # The image registers the C module as _engine and not as engine (P848)
  DEFS="$MPY/ports/esp32/build-engine/genhdr/moduledefs.h"
  if ! grep -q 'MP_QSTR__engine)' "$DEFS" || grep -q 'MP_QSTR_engine)' "$DEFS"; then
    echo "build.sh: $DEFS does not register _engine alone:" >&2
    grep -n 'engine' "$DEFS" >&2
    exit 1
  fi
  IMAGE="$MPY/ports/esp32/build-engine/micropython.bin"
  echo "$IMAGE: $(wc -c < "$IMAGE" | tr -d ' ') B, sha256 $(shasum -a 256 "$IMAGE" | cut -d' ' -f1), engine $(git -C "$HERE/engine" rev-parse --short HEAD)"
fi
