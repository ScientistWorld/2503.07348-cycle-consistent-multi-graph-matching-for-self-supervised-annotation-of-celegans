#!/bin/bash
# Hidden-test scoring: every method directory under outputs/ plus the fixed
# comparators in eval/test/fixed/, scored on the 10 hidden test worms.
#
# Usage (no arguments): bash scripts/evaluate_test.sh
set -e
cd /home/user
mkdir -p scoring
python eval/test/evaluate_slice.py --output scoring/scores_test.json
