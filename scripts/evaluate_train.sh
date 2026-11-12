#!/bin/bash
# Score the visible dev slice (4 held-out worms, labels in eval/train/) for every
# method directory under outputs/ plus the fixed comparators in eval/train/fixed/.
#
# Usage (no arguments): bash scripts/evaluate_train.sh
# Each method writes outputs/<method_name>/predictions.json; the ranked entry is
# outputs/our_unsupervised_atlas/predictions.json. See briefing/evaluation.md.
set -e
cd /home/user
mkdir -p scoring
python eval/train/evaluate_slice.py --output scoring/scores_train.json
