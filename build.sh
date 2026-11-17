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
$ZIG cc -target aarch64-macos.11.0 $CF "$P/src/atex.c" -o "$O/atex-macos-arm64" -lm -lpthread
$ZIG cc -target x86_64-macos.10.15 $CF "$P/src/atex.c" -o "$O/atex-macos-x64" -lm -lpthread
# One universal macOS binary, as lipo writes it: a fat header, the x86_64 slice
# at 4 KiB and the arm64 slice at the next 16 KiB boundary.
be32() { printf "$(printf '\\%03o' $(($1 >> 24 & 255)) $(($1 >> 16 & 255)) $(($1 >> 8 & 255)) $(($1 & 255)))"; }
XS=$(wc -c < "$O/atex-macos-x64"); AS=$(wc -c < "$O/atex-macos-arm64"); AO=$(( (4096 + XS + 16383) / 16384 * 16384 ))
{ be32 $((0xcafebabe)); be32 2
  be32 $((0x01000007)); be32 3; be32 4096; be32 "$XS"; be32 12
  be32 $((0x0100000c)); be32 0; be32 "$AO"; be32 "$AS"; be32 14
  head -c $((4096 - 48)) /dev/zero; cat "$O/atex-macos-x64"
  head -c $((AO - 4096 - XS)) /dev/zero; cat "$O/atex-macos-arm64"; } > "$P/bin/atex-macos"
rm -f "$O/atex-macos-x64" "$O/atex-macos-arm64"
$ZIG cc -target x86_64-windows-gnu $CF -include win/compat.h -Iwin/include "$P/src/atex.c" -o "$P/bin/atex-windows-x64.exe" -lpthread
rm -f "$P"/bin/*.pdb
if grep -q "$HOME" "$P/src/atex.c" "$P"/bin/*; then echo "build embeds \$HOME path" >&2; exit 1; fi
cp atex_serve.gold atex_serve.amni "$P/src/"
cp install.sh install.ps1 README.md LICENSE manifest.json "$P/"
chmod 755 "$P"/bin/* "$P/install.sh"
tar -C "$O/pkg" -czf "$O/amnitex-helium.tar.gz" amnitex-helium
cp "$O/amnitex-helium.tar.gz" "$O/amnitex-linux-x64.tar.gz"
cp "$P/bin/atex-windows-x64.exe" "$O/atex-windows-x64.exe"
cp install.sh install.ps1 "$O/"
chmod 755 "$O/install.sh"
$X validate "$P/manifest.json"
$X pack "$P" "$O/amnitex.mcpb"
# atex update downloads the bare binary for its platform and VERSION, checked against the signed SHA256SUMS
cp "$P/bin/atex-linux-x64" "$P/bin/atex-macos" "$O/"
"$O/atex-linux-x64" --version | cut -d' ' -f2 > "$O/VERSION"
rm -rf "$O/pkg"
(cd "$O" && sha256sum amnitex-helium.tar.gz amnitex-linux-x64.tar.gz atex-windows-x64.exe atex-linux-x64 atex-macos VERSION amnitex.mcpb install.sh install.ps1 > SHA256SUMS)
KEY="${ATEX_RELEASE_KEY:-$HOME/.config/amnitex/release.key}"
if [ -f "$KEY" ]; then "$O/atex-linux-x64" release-sign "$KEY" "$O/SHA256SUMS"
else echo "build.sh: no release key at $KEY: SHA256SUMS is unsigned, so installed atex will not update to this release (see RELEASE.md)" >&2; fi
ls -la "$O"
