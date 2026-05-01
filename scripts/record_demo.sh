#!/usr/bin/env bash
set -euo pipefail
export PYTHONIOENCODING=utf-8
ATEX_DIR="$HOME/.atex-demo-record"
rm -rf "$ATEX_DIR"
echo
echo "  $ atex demo --model qwen2.5:0.5b-instruct"
echo
sleep 0.8
atex demo --atex-dir "$ATEX_DIR/.atex" --model qwen2.5:0.5b-instruct --no-consent
echo
echo "  $ atex stats --atex-dir $ATEX_DIR/.atex"
echo
sleep 0.6
atex stats --atex-dir "$ATEX_DIR/.atex"
echo
echo "  Done."
echo
