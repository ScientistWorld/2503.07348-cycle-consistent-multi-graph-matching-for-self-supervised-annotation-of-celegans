#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

mkdir -p outputs/method

OUTPUT="outputs/method/predictions.json"
prev=""
for arg in "$@"; do
  if [ "$prev" = "--output" ]; then
    OUTPUT="$arg"
    break
  fi
  prev="$arg"
done

python -m method.cycle_mgm "$@"
bash scripts/evaluate.sh "$OUTPUT"
