#!/bin/bash
# Score the held-out evaluation slice from the same prediction artifact.
#
# Usage mirrors scripts/evaluate.sh:
#   bash scripts/evaluate_test.sh [predictions.json]

set -e

cd /home/user

mkdir -p scoring

PREDICTIONS="${1:-outputs/method/predictions.json}"
MATCH_ARGS=()
if [ -f scoring/scores_train.json ]; then
  MATCH_ARGS=(--match-methods-from scoring/scores_train.json)
fi

python -m eval.test.evaluate_slice "$PREDICTIONS" --output scoring/scores_test.json "${MATCH_ARGS[@]}"
