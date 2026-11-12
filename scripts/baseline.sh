#!/bin/bash
# Run the unlearned linear baseline. Its predictions are written under
# outputs/_comparators/ (ignored by the evaluators); the gym's scored copy is the
# fixed comparator frozen in eval/{train,test}/fixed/unlearned_linear_baseline.json.
#
# Usage: bash scripts/baseline.sh [--reuse checkpoints/our_unsupervised_atlas]
set -e
cd /home/user
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python -m baseline.unlearned_linear "$@"
