#!/bin/sh
# Prefer the native Helium binary. Python is the fallback when it is absent.
ROOT=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
if [ -n "${ATEX_BIN:-}" ] && [ -x "$ATEX_BIN" ]; then
  exec "$ATEX_BIN" hook cursor
fi
if command -v atex >/dev/null 2>&1 && atex --version 2>/dev/null | grep -q helium-native; then
  exec atex hook cursor
fi
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m atex.cli hook cursor
