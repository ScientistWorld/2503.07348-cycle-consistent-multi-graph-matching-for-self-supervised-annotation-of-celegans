#!/bin/bash
# Score the visible evaluation slice from a method prediction artifact.
#
# Usage mirrors scripts/evaluate.sh:
#   bash scripts/evaluate_train.sh [predictions.json]

set -e

cd /home/user

mkdir -p scoring

PREDICTIONS="${1:-outputs/method/predictions.json}"
python -m eval.train.evaluate_slice "$PREDICTIONS" --output scoring/scores_train.json
