#!/bin/bash
# Run the reproduced method (paper's unsupervised cycle-consistent MGM atlas)
# and score it on the visible slice.
#
# Usage: bash scripts/method.sh [extra args for method/cycle_mgm.py]
# Defaults: seed 7, 8 learning worms, 40/40/12 BO trials, output
# outputs/our_unsupervised_atlas/predictions.json (single CPU: ~1 hour).
set -e
cd /home/user
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python -m method.cycle_mgm "$@"
bash scripts/evaluate_train.sh
