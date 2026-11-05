#!/bin/bash
# Build MicroPython v1.29.0 for the FireBeetle 2 ESP32-S3 (N16R8), with ESP-IDF v5.5.2.
# Usage: ./build.sh            the stock image
#        ./build.sh s3lcd      the image with the s3lcd C module
#        ./build.sh engine     s3lcd and the engine module (P590 bodies, P595 fire), in build-engine
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
fi
make "${ARGS[@]}" submodules > /dev/null
make "${ARGS[@]}" -j8
