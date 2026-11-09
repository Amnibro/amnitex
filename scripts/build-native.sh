#!/bin/sh
# Build the native Helium atex binary. Requires git, gcc, and a network
# connection the first time so github.com/Amnibro/helium can be cloned.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
HELIUM=${HELIUM:-"$ROOT/.helium"}
OUT=${1:-"$ROOT/dist/atex-linux-x64"}
if [ ! -x "$HELIUM/build/hc" ]; then
  rm -rf "$HELIUM"
  git clone --depth 1 https://github.com/Amnibro/helium.git "$HELIUM"
  (cd "$HELIUM" && CC=${CC:-gcc} sh hc/bootstrap.sh)
fi
mkdir -p "$(dirname "$OUT")"
ln -sfn "$HELIUM/hc/lib" "$ROOT/.hclib"
HC_LIB="$ROOT/.hclib" "$HELIUM/build/hc" build "$ROOT/atex_serve.amni" -o "$OUT"
chmod 755 "$OUT"
"$OUT" --version
"$OUT" --selftest
