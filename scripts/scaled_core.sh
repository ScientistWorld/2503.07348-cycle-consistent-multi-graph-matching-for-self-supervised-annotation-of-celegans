#!/bin/bash
# Medium-sized scaled reproduction for the core claim.
#
# This keeps the same cycle-consistent multi-graph matching pipeline as the
# smoke run, but increases worms, cells, and parameter-search trials to make the
# result less dependent on a tiny diagnostic subset.

set -e

cd /home/user

python -m method.cycle_mgm \
  --output outputs/method/predictions.json \
  --train-worms 8 \
  --learn-worms 4 \
  --test-worms 4 \
  --cells 96 \
  --trials 2 \
  --seed 11

bash scripts/evaluate.sh outputs/method/predictions.json
