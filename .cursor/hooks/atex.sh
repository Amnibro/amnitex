#!/bin/sh
if [ -n "${ATEX_BIN:-}" ] && [ -x "$ATEX_BIN" ]; then
  exec "$ATEX_BIN" hook cursor
fi
exec atex hook cursor
