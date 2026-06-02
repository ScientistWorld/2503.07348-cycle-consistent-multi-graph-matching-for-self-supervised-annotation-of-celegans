#!/bin/bash
# Fast diagnostic run for CPU-only test jobs.
#
# This keeps the paper's cycle-consistent multi-graph matching procedure but
# uses fewer worms, cells, and parameter-search trials than reproduce.sh. It is
# intended to catch container and pipeline issues before running the larger
# scaled reproduction.

set -e

cd /home/user

python -m method.cycle_mgm \
  --output outputs/method/predictions.json \
  --train-worms 4 \
  --learn-worms 3 \
  --test-worms 2 \
  --cells 48 \
  --trials 1 \
  --seed 7

bash scripts/evaluate.sh outputs/method/predictions.json
