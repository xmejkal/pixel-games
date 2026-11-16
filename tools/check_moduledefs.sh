#!/bin/bash
# The engine image's module list (P848): build.sh engine runs it on build-engine/genhdr/moduledefs.h after the build.
# It exits 1 unless the image registers the C module as _engine and not as engine (a stale build-engine once
# registered both). Usage: tools/check_moduledefs.sh MODULEDEFS_H
DEFS=${1:?usage: tools/check_moduledefs.sh MODULEDEFS_H}
if [ ! -f "$DEFS" ]; then
  echo "check_moduledefs.sh: no $DEFS" >&2
  exit 1
fi
if ! grep -q 'MP_QSTR__engine)' "$DEFS" || grep -q 'MP_QSTR_engine)' "$DEFS"; then
  echo "check_moduledefs.sh: $DEFS does not register _engine alone:" >&2
  grep -n 'engine' "$DEFS" >&2
  exit 1
fi
