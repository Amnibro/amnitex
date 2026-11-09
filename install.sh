#!/bin/sh
set -eu
DEST="${ATEX_BIN_DIR:-$HOME/.local/bin}"
KB="${ATEX_DIR:-$HOME/.atex}"
REPO="${ATEX_REPO:-Amnibro/amnitex}"
URL="${ATEX_URL:-https://github.com/$REPO/releases/latest/download/amnitex-helium.tar.gz}"
ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
mkdir -p "$DEST" "$KB"
OS="$(uname -s)"
ARCH="$(uname -m)"
REAL="$DEST/atex-helium"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/atex-install.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT INT TERM
if [ -f "$ROOT/atex_serve.amni" ]; then
  printf "[amnitex] building native Helium binary (%s/%s) ...\n" "$OS" "$ARCH"
  HELIUM="${HELIUM:-$ROOT/.helium}" sh "$ROOT/scripts/build-native.sh" "$REAL.new"
else
  printf "[amnitex] downloading Helium bundle from %s ...\n" "$URL"
  curl -fsSL "$URL" | tar -xz -C "$TMP"
  SRC="$TMP/amnitex-helium"
  if [ "$OS" = "Linux" ] && [ "$ARCH" = "x86_64" ] && [ -f "$SRC/bin/atex-linux-x64" ]; then
    cp "$SRC/bin/atex-linux-x64" "$REAL.new"
  else
    printf "[amnitex] compiling native Helium binary for %s/%s ...\n" "$OS" "$ARCH"
    cc -O3 -I"$SRC/src" "$SRC/src/atex.c" -lm -lpthread -o "$REAL.new"
  fi
fi
chmod 755 "$REAL.new"
mv -f "$REAL.new" "$REAL"
printf '#!/bin/sh\nexec "%s" "$@"\n' "$REAL" > "$DEST/atex"
chmod 755 "$DEST/atex"
"$REAL" --version
"$REAL" --selftest
"$REAL" init . --atex-dir "$KB"
"$REAL" install --atex-dir "$KB"
printf "[amnitex] installed %s (wrapper %s/atex, kb=%s)\n" "$REAL" "$DEST" "$KB"
printf "[amnitex] check: atex doctor\n"
