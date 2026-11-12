#!/bin/bash
# Reproduce the gym's reference end to end (single CPU, ~1 hour):
#   1. the paper's method, seed 7 (pool-only training) ->
#      outputs/our_unsupervised_atlas/{predictions.json,model.json,annotate.sh}
#   2. the unlearned linear baseline -> outputs/_comparators/unlearned_linear_baseline/
#      (and, when the hidden side is present, the supervised comparator; both are
#      frozen into eval/{train,test}/fixed/)
#   3. visible and hidden scoring.
# scripts/run.sh runs the full hardening audit (seeds, variants, shortcuts).
set -e
cd /home/user
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1
python -m method.cycle_mgm --seed 7 --work checkpoints/our_unsupervised_atlas \
  --output outputs/our_unsupervised_atlas/predictions.json
python -m baseline.unlearned_linear --reuse checkpoints/our_unsupervised_atlas \
  --output outputs/_comparators/unlearned_linear_baseline/predictions.json
if [ -f eval/test/keys.json ]; then
  [ -f eval/test/oracle/predictions.json ] || python -m eval.test.supervised_oracle --output eval/test/oracle/predictions.json
  python eval/test/run_annotator.py outputs/_comparators/unlearned_linear_baseline outputs/_comparators/baseline_labelings.json
  python eval/test/install_comparator.py unlearned_linear_baseline outputs/_comparators/baseline_labelings.json
  python eval/test/install_comparator.py supervised_oracle_atlas eval/test/oracle/predictions.json
  bash scripts/evaluate_test.sh
fi
bash scripts/evaluate_train.sh
bash scripts/evaluate.sh
