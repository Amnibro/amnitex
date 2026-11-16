#!/bin/sh
# Installs atex on Linux and macOS: puts the native binary in ~/.local/bin,
# runs the self-test, indexes this folder and wires your AI apps.
#   curl -fsSL https://github.com/Amnibro/amnitex/releases/latest/download/install.sh | sh
# On Windows, use install.ps1 instead.
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
case "$OS/$ARCH" in
  Linux/x86_64) PREBUILT=atex-linux-x64 ;;
  Darwin/arm64 | Darwin/aarch64 | Darwin/x86_64) PREBUILT=atex-macos ;;
  *) PREBUILT= ;;
esac
if [ -f "$ROOT/atex_serve.amni" ]; then
  printf "[amnitex] building native Helium binary (%s/%s) ...\n" "$OS" "$ARCH"
  HELIUM="${HELIUM:-$ROOT/.helium}" sh "$ROOT/scripts/build-native.sh" "$REAL.new"
else
  if [ -n "$PREBUILT" ] && [ -f "$ROOT/bin/$PREBUILT" ]; then
    SRC="$ROOT"
  else
    printf "[amnitex] downloading %s ...\n" "$URL"
    curl -fsSL "$URL" | tar -xz -C "$TMP"
    SRC="$TMP/amnitex-helium"
  fi
  if [ -n "$PREBUILT" ] && [ -f "$SRC/bin/$PREBUILT" ]; then
    cp "$SRC/bin/$PREBUILT" "$REAL.new"
  else
    printf "[amnitex] no prebuilt binary for %s/%s; compiling with cc ...\n" "$OS" "$ARCH"
    cc -O3 -fwrapv -w -I"$SRC/src" "$SRC/src/atex.c" -lm -lpthread -o "$REAL.new"
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
case ":$PATH:" in
  *":$DEST:"*) ;;
  *)
    if [ "${ATEX_NO_MODIFY_PATH:-0}" = 1 ]; then
      printf "[amnitex] %s is not on your PATH. Add it to run atex by name.\n" "$DEST"
    else
      case "${SHELL:-}" in
        */zsh) RC="$HOME/.zshrc" ;;
        */bash) if [ "$OS" = Darwin ]; then RC="$HOME/.bash_profile"; else RC="$HOME/.bashrc"; fi ;;
        *) RC="$HOME/.profile" ;;
      esac
      if grep -qs 'added by the amnitex installer' "$RC"; then
        printf "[amnitex] %s already puts %s on PATH. Open a new terminal to run atex by name.\n" "$RC" "$DEST"
      else
        printf '\n# added by the amnitex installer\nexport PATH="%s:$PATH"\n' "$DEST" >> "$RC"
        printf "[amnitex] added %s to PATH in %s. Open a new terminal to run atex by name.\n" "$DEST" "$RC"
      fi
    fi
    ;;
esac
printf "[amnitex] check: atex doctor\n"
