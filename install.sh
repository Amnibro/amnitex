#!/bin/sh
# Install the native Helium atex binary and wire it for every Cursor session
# on this machine. Linux and macOS. Windows: see install.ps1.
set -eu
DEST="${ATEX_BIN_DIR:-$HOME/.local/bin}"
KB="${ATEX_DIR:-$HOME/.atex}"
ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
mkdir -p "$DEST" "$KB"
OS="$(uname -s)"
ARCH="$(uname -m)"
REAL="$DEST/atex-helium"
if [ -f "$ROOT/atex_serve.amni" ]; then
  printf "[amnitex] building native Helium binary (%s/%s) ...\n" "$OS" "$ARCH"
  HELIUM="${HELIUM:-$ROOT/.helium}" sh "$ROOT/scripts/build-native.sh" "$REAL.new"
else
  printf "[amnitex] this installer needs the repository checkout (atex_serve.amni).\n" >&2
  exit 1
fi
chmod 755 "$REAL.new"
mv -f "$REAL.new" "$REAL"
cat > "$DEST/atex" <<EOF
#!/bin/sh
REAL="$REAL"
case "\${1:-}" in
  install|uninstall|doctor|bench-cursor)
    if PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 -c 'import atex.cli' >/dev/null 2>&1; then
      export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
      exec python3 -m atex.cli "\$@"
    fi
    ;;
esac
exec "\$REAL" "\$@"
EOF
chmod 755 "$DEST/atex"
"$REAL" --version
"$REAL" --selftest
"$REAL" init . --atex-dir "$KB"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
if python3 -c 'import atex.cli' >/dev/null 2>&1; then
  ATEX_BIN="$REAL" python3 -m atex.cli install --atex-dir "$KB"
else
  printf "[amnitex] python3 atex package not importable; native MCP wiring only.\n"
fi
"$REAL" install --atex-dir "$KB"
printf "[amnitex] installed %s (wrapper %s/atex, kb=%s)\n" "$REAL" "$DEST" "$KB"
printf "[amnitex] check: atex doctor\n"
