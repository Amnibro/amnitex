#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
H="${HELIUM:-$HOME/ai/amni-lang/helium-gold}"
HC="${HC_BIN:-$H/build/hc}"
HCLIB="${HC_LIB:-$H/hc/lib}"
O="${OUT:-dist}"
X="${MCPB:-npx -y @anthropic-ai/mcpb}"
rm -rf "$O" hclib
mkdir -p "$O/pkg/amnitex-helium/bin" "$O/pkg/amnitex-helium/src"
ln -s "$HCLIB" hclib
trap 'rm -f hclib' EXIT
HC_LIB=hclib "$HC" build atex_serve.amni -o "$O/pkg/amnitex-helium/bin/atex-linux-x64"
HC_LIB=hclib "$HC" build atex_serve.amni -o "$O/pkg/amnitex-helium/src/atex.c"
if grep -q "$HOME" "$O/pkg/amnitex-helium/src/atex.c" "$O/pkg/amnitex-helium/bin/atex-linux-x64"; then echo "build embeds \$HOME path" >&2; exit 1; fi
cp "$H/hc/hrt.h" "$O/pkg/amnitex-helium/src/hrt.h"
cp atex_serve.gold atex_serve.amni "$O/pkg/amnitex-helium/src/"
cp install.sh README.md LICENSE manifest.json mcpb-entry.mjs "$O/pkg/amnitex-helium/"
chmod 755 "$O/pkg/amnitex-helium/bin/atex-linux-x64" "$O/pkg/amnitex-helium/install.sh"
tar -C "$O/pkg" -czf "$O/amnitex-helium.tar.gz" amnitex-helium
cp "$O/amnitex-helium.tar.gz" "$O/amnitex-linux-x64.tar.gz"
cp install.sh "$O/install.sh"
chmod 755 "$O/install.sh"
$X validate "$O/pkg/amnitex-helium/manifest.json"
$X pack "$O/pkg/amnitex-helium" "$O/amnitex.mcpb"
rm -rf "$O/pkg"
(cd "$O" && sha256sum amnitex-helium.tar.gz amnitex-linux-x64.tar.gz amnitex.mcpb install.sh > SHA256SUMS)
ls -la "$O"
