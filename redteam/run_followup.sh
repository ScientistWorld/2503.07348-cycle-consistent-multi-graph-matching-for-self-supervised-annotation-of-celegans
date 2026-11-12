#!/bin/bash
set -euo pipefail
cd /home/user
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
for name in better_alignment_train6 better_alignment_train24 better_statistical_atlas weaker_radii_only shortcut_stale_scores; do
  echo "Running $name"
  bash "redteam/$name/run.sh" > "redteam/$name/run.log" 2>&1
  cat "redteam/$name/evidence.json"
done
python -m redteam.summarize
