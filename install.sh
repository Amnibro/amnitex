#!/bin/sh
set -eu
DEST="${ATEX_BIN_DIR:-$HOME/.local/bin}"
KB="${ATEX_DIR:-$HOME/.atex}"
REPO="${ATEX_REPO:-Amnibro/amnitex}"
URL="https://github.com/$REPO/releases/latest/download/amnitex-helium.tar.gz"
mkdir -p "$DEST" "$KB"
OS="$(uname -s)"
ARCH="$(uname -m)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/atex-install.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT INT TERM
if [ -f "./atex_serve_bin" ] && [ "$OS" = "Linux" ] && [ "$ARCH" = "x86_64" ]; then
  cp "./atex_serve_bin" "$DEST/atex.new"
elif [ -f "./dist/amnitex-helium/bin/atex-linux-x64" ] && [ "$OS" = "Linux" ] && [ "$ARCH" = "x86_64" ]; then
  cp "./dist/amnitex-helium/bin/atex-linux-x64" "$DEST/atex.new"
elif [ -f "./dist/amnitex-helium/src/atex.c" ]; then
  cc -O3 -I"./dist/amnitex-helium/src" "./dist/amnitex-helium/src/atex.c" -lm -lpthread -o "$DEST/atex.new"
else
  printf "[amnitex] downloading Helium bundle from %s ...\n" "$URL"
  curl -fsSL "$URL" | tar -xz -C "$TMP"
  if [ "$OS" = "Linux" ] && [ "$ARCH" = "x86_64" ] && [ -f "$TMP/amnitex-helium/bin/atex-linux-x64" ]; then
    cp "$TMP/amnitex-helium/bin/atex-linux-x64" "$DEST/atex.new"
  else
    printf "[amnitex] compiling native Helium binary for %s/%s ...\n" "$OS" "$ARCH"
    cc -O3 -I"$TMP/amnitex-helium/src" "$TMP/amnitex-helium/src/atex.c" -lm -lpthread -o "$DEST/atex.new"
  fi
fi
chmod 755 "$DEST/atex.new"
mv -f "$DEST/atex.new" "$DEST/atex"
"$DEST/atex" --version
"$DEST/atex" --selftest
"$DEST/atex" init . --atex-dir "$KB"
"$DEST/atex" install --atex-dir "$KB"
printf "[amnitex] installed native Helium binary at %s/atex (kb=%s)\n" "$DEST" "$KB"
