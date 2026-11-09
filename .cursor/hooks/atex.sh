#!/bin/sh
# Project hook. Runs the tested Python memory layer from this repository.
ROOT=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m atex.cli hook "$@"
