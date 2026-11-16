#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
H="${HELIUM:-$HOME/ai/amni-lang/helium-gold}"
HC="${HC_BIN:-$H/build/hc}"
HCLIB="${HC_LIB:-$H/hc/lib}"
O="${OUT:-dist}"
X="${MCPB:-npx -y @anthropic-ai/mcpb}"
# zig cross-compiles the generated C for macOS and Windows: pip install ziglang, or set ZIG.
if [ -z "${ZIG:-}" ]; then
  if command -v zig > /dev/null 2>&1; then ZIG=zig
  elif python3 -c 'import ziglang' 2> /dev/null; then ZIG="python3 -m ziglang"
  else echo "build.sh needs zig for the macOS and Windows binaries: pip install ziglang, or set ZIG" >&2; exit 1; fi
fi
P="$O/pkg/amnitex-helium"
rm -rf "$O" hclib
mkdir -p "$P/bin" "$P/src"
ln -s "$HCLIB" hclib
trap 'rm -f hclib' EXIT
HC_LIB=hclib "$HC" build atex_serve.amni -o "$P/bin/atex-linux-x64"
HC_LIB=hclib "$HC" build atex_serve.amni -o "$P/src/atex.c"
cp "$H/hc/hrt.h" "$P/src/hrt.h"
cp -R win "$P/src/win"
CF="-O2 -fwrapv -w -s -I$P/src"
$ZIG cc -target aarch64-macos.11.0 $CF "$P/src/atex.c" -o "$P/bin/atex-macos-arm64" -lm -lpthread
$ZIG cc -target x86_64-macos.10.15 $CF "$P/src/atex.c" -o "$P/bin/atex-macos-x64" -lm -lpthread
$ZIG cc -target x86_64-windows-gnu $CF -include win/compat.h -Iwin/include "$P/src/atex.c" -o "$P/bin/atex-windows-x64.exe" -lpthread
rm -f "$P"/bin/*.pdb
if grep -q "$HOME" "$P/src/atex.c" "$P"/bin/*; then echo "build embeds \$HOME path" >&2; exit 1; fi
cp atex_serve.gold atex_serve.amni "$P/src/"
cp install.sh install.ps1 README.md LICENSE manifest.json mcpb-entry.mjs "$P/"
chmod 755 "$P"/bin/* "$P/install.sh"
tar -C "$O/pkg" -czf "$O/amnitex-helium.tar.gz" amnitex-helium
cp "$O/amnitex-helium.tar.gz" "$O/amnitex-linux-x64.tar.gz"
cp "$P/bin/atex-windows-x64.exe" "$O/atex-windows-x64.exe"
cp install.sh install.ps1 "$O/"
chmod 755 "$O/install.sh"
$X validate "$P/manifest.json"
$X pack "$P" "$O/amnitex.mcpb"
rm -rf "$O/pkg"
(cd "$O" && sha256sum amnitex-helium.tar.gz amnitex-linux-x64.tar.gz atex-windows-x64.exe amnitex.mcpb install.sh install.ps1 > SHA256SUMS)
ls -la "$O"
