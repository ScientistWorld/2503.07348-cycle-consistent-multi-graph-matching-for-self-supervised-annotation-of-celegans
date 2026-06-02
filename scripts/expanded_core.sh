#!/bin/bash
# Expanded scaled reproduction for probing core_claim_plus.
#
# This keeps the paper's cycle-consistent graph matching procedure and uses the
# same tracked sample, but increases the number of training worms and cells.
# Scores are written outside scoring/scores.json so the validated default
# benchmark remains intact unless this expanded setting is reviewed separately.

set -e

cd /home/user

mkdir -p outputs/expanded

python -m method.cycle_mgm \
  --output outputs/expanded/predictions.json \
  --train-worms 16 \
  --learn-worms 6 \
  --test-worms 6 \
  --cells 220 \
  --trials 6 \
  --seed 13

python -m eval.evaluate_outputs outputs/expanded/predictions.json \
  --output outputs/expanded/scores.json
