#!/usr/bin/env bash
# scripts/build.sh - copy extension to a temporary directory, optionally zip it.
set -euo pipefail
SRC="${1:-$HOME/Projects/url-copy-fire}"
OUT="${2:-$HOME/Projects/url-copy-fire/build}"
mkdir -p "$OUT"
cp -r "$SRC"/* "$OUT/"
(cd "$OUT" && zip -r "$OUT/url-route.zip" .)
echo "Built: $OUT/url-route.zip"
