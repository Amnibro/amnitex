#!/bin/bash
# atex update end to end, offline (release folder over file://): Ed25519 against RFC 8032, key handling, refusal of a
# tampered binary, a forged signature or an edited SHA256SUMS, --check, the update itself, the once-a-day background
# update from atex serve, and turning it off.
# Usage: tests/update_test.sh <hc> <helium lib>      (Linux x86-64: it installs the atex-linux-x64 asset)
set -u
HC=$(realpath "${1:?usage: update_test.sh <hc> <helium lib>}"); LIB=$(realpath "${2:?}")
R=$(cd "$(dirname "$0")/.." && pwd)
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
pass=0; fail=0; ok() { if [ "$1" = 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL $2"; fi; }
CUR=$(sed -n 's/.*fn atex_version() const byte\[:\] { "\(.*\)" }.*/\1/p' "$R/atex_serve.amni"); CRE=$(printf '%s' "$CUR" | sed 's/\./\\./g')
build() { sed "s/fn release_pub() const byte\[:\] { \"[0-9a-f]*\" }/fn release_pub() const byte[:] { \"$2\" }/" "$R/atex_serve.amni" | sed "s/$CRE/$3/g" > "$W/$1.amni" && HC_LIB="$LIB" "$HC" build "$W/$1.amni" -o "$W/$1" > /dev/null 2>&1; }
ver() { "$1" --version | cut -d' ' -f2; }

# RFC 8032 section 7.1, test 1: this key signs the empty message to this signature
printf '9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60\n' > "$W/rfc.key"; : > "$W/empty"
build rfc d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a "$CUR"; ok $? "build with the RFC 8032 key"
"$W/rfc" release-sign "$W/rfc.key" "$W/empty" > /dev/null
[ "$(cat "$W/empty.sig")" = e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b ]; ok $? "Ed25519 signature matches RFC 8032 test 1"

# the repository's own build: makes a key, never overwrites one, and without a built-in key never updates
HC_LIB="$LIB" "$HC" build "$R/atex_serve.amni" -o "$W/repo" > /dev/null 2>&1; ok $? "build the repository's atex"
"$W/repo" release-key "$W/key" > "$W/k.out"; ok $? "atex release-key makes a key"
PUB=$(sed -n 's/^public key: //p' "$W/k.out"); [ ${#PUB} = 64 ] && [ "$(stat -c %a "$W/key")" = 600 ]; ok $? "the key is private and its public half is 64 hex digits"
"$W/repo" release-key "$W/key" > /dev/null 2>&1; [ $? = 1 ]; ok $? "release-key refuses to overwrite a key"
"$W/repo" release-sign "$W/key" "$W/empty" > /dev/null 2>&1; [ $? = 1 ]; ok $? "release-sign refuses a key the build does not carry"
ATEX_DIR="$W/kb0" "$W/repo" update > "$W/u0" 2>&1; [ $? = 1 ] && grep -q "no release key" "$W/u0"; ok $? "a build without a release key does not update"

# installed (the current version) and released 9.9.9, both carrying the test key; a signed release folder
build old "$PUB" "$CUR" && build new "$PUB" 9.9.9; ok $? "build the old and the new atex"
mkdir -p "$W/rel" "$W/bin" && cp "$W/new" "$W/rel/atex-linux-x64" && echo 9.9.9 > "$W/rel/VERSION"
(cd "$W/rel" && sha256sum atex-linux-x64 VERSION > SHA256SUMS) && "$W/old" release-sign "$W/key" "$W/rel/SHA256SUMS" > /dev/null; ok $? "sign the release"
export HOME="$W/home" ATEX_DIR="$W/kb"; mkdir -p "$HOME"
inst() { cp "$W/old" "$W/bin/atex-helium"; }
upd() { ATEX_UPDATE_URL="file://$1" "$W/bin/atex-helium" update ${2:-} > "$W/out" 2>&1; }

inst; cp -r "$W/rel" "$W/bad1" && printf x >> "$W/bad1/atex-linux-x64"
upd "$W/bad1"; [ $? = 1 ] && grep -q "does not match its signed SHA-256" "$W/out" && [ "$(ver "$W/bin/atex-helium")" = "$CUR" ] && [ ! -e "$W/bin/atex-helium.new" ]; ok $? "a tampered binary is refused and removed: $(cat "$W/out")"
cp -r "$W/rel" "$W/bad2" && cut -c1-100 "$W/rel/SHA256SUMS.sig" > "$W/bad2/SHA256SUMS.sig"
upd "$W/bad2"; [ $? = 1 ] && grep -q "not signed with this atex's release key" "$W/out"; ok $? "a malformed signature is refused: $(cat "$W/out")"
cp -r "$W/rel" "$W/bad3" && s=$(cat "$W/rel/SHA256SUMS.sig") && if [ "${s:8:1}" = 0 ]; then d=1; else d=0; fi && printf '%s%s%s\n' "${s:0:8}" "$d" "${s:9}" > "$W/bad3/SHA256SUMS.sig"
upd "$W/bad3"; [ $? = 1 ] && grep -q "not signed" "$W/out"; ok $? "a forged signature is refused: $(cat "$W/out")"
cp -r "$W/rel" "$W/bad4" && printf x >> "$W/bad4/atex-linux-x64" && (cd "$W/bad4" && sha256sum atex-linux-x64 VERSION > SHA256SUMS)
upd "$W/bad4"; [ $? = 1 ] && grep -q "not signed" "$W/out" && [ "$(ver "$W/bin/atex-helium")" = "$CUR" ]; ok $? "a SHA256SUMS edited after signing is refused: $(cat "$W/out")"

upd "$W/rel" --check; [ $? = 0 ] && grep -q "atex 9.9.9 is available" "$W/out" && [ "$(ver "$W/bin/atex-helium")" = "$CUR" ]; ok $? "--check reports the new release and changes nothing: $(cat "$W/out")"
upd "$W/rel"; [ $? = 0 ] && grep -q "to 9.9.9" "$W/out" && [ "$(ver "$W/bin/atex-helium")" = 9.9.9 ] && [ ! -e "$W/bin/atex-helium.new" ]; ok $? "atex update installs the signed release: $(cat "$W/out")"
upd "$W/rel"; [ $? = 0 ] && grep -q "9.9.9 is up to date" "$W/out"; ok $? "the new atex is up to date: $(cat "$W/out")"

# atex serve starts the update in the background once a day
inst; rm -rf "$ATEX_DIR/update"
wait_ver() { for _ in $(seq 1 100); do [ "$(ver "$W/bin/atex-helium")" = "$1" ] && return 0; sleep 0.2; done; return 1; }
ATEX_UPDATE_URL="file://$W/rel" "$W/bin/atex-helium" serve < /dev/null > "$W/so" 2>&1; ok $? "atex serve starts and stops"
wait_ver 9.9.9; ok $? "atex serve updated itself in the background"
grep -q "to 9.9.9; it runs from the next start" "$ATEX_DIR/update/log"; ok $? "the background update is logged: $(cat "$ATEX_DIR/update/log" 2>&1)"
[ ! -s "$W/so" ]; ok $? "the background update writes nothing on the server's streams: $(cat "$W/so")"
inst; ATEX_UPDATE_URL="file://$W/rel" "$W/bin/atex-helium" serve < /dev/null > /dev/null 2>&1; sleep 3; [ "$(ver "$W/bin/atex-helium")" = "$CUR" ]; ok $? "a second start the same day does not check again"
rm -f "$ATEX_DIR/update/checked"; ATEX_NO_UPDATE=1 ATEX_UPDATE_URL="file://$W/rel" "$W/bin/atex-helium" serve < /dev/null > /dev/null 2>&1; sleep 3; [ "$(ver "$W/bin/atex-helium")" = "$CUR" ]; ok $? "ATEX_NO_UPDATE=1 turns it off"
"$W/bin/atex-helium" update --off > /dev/null; ATEX_UPDATE_URL="file://$W/rel" "$W/bin/atex-helium" serve < /dev/null > /dev/null 2>&1; sleep 3; [ "$(ver "$W/bin/atex-helium")" = "$CUR" ] && [ ! -e "$ATEX_DIR/update/checked" ]; ok $? "atex update --off turns it off"
"$W/bin/atex-helium" update --on > /dev/null; ATEX_UPDATE_URL="file://$W/rel" "$W/bin/atex-helium" serve < /dev/null > /dev/null 2>&1; wait_ver 9.9.9; ok $? "atex update --on turns it back on"

echo "update_test: $pass pass, $fail fail"; [ $fail = 0 ]
