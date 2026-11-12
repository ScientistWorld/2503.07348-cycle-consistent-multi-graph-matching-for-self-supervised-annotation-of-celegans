#!/bin/bash
# Smoke test of the hardened gym (1-hour test node): timings + tiny end-to-end run.
cd /home/user
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p logs hardening/runs/smoke
python -c "import numpy, scipy, optuna, pylibmgm; print('versions', numpy.__version__, scipy.__version__, optuna.__version__)"
timeout 900 python -m hardening.bench || echo "BENCH FAILED"
timeout 1500 python -m method.cycle_mgm --work checkpoints/smoke --output hardening/runs/smoke/predictions.json \
  --trials 3,3,2 --learn-worms 4 --realign-iterations 1 || echo "METHOD FAILED"
timeout 600 python -m baseline.unlearned_linear --reuse checkpoints/smoke --work checkpoints/smoke_baseline \
  --output outputs/_comparators/unlearned_linear_baseline/predictions.json || echo "BASELINE FAILED"
timeout 900 python -m eval.test.supervised_oracle --iterations 1 \
  --output outputs/_comparators/supervised_oracle_atlas/predictions.json || echo "ORACLE FAILED"
python eval/test/install_comparator.py unlearned_linear_baseline outputs/_comparators/unlearned_linear_baseline/predictions.json
python eval/test/install_comparator.py supervised_oracle_atlas outputs/_comparators/supervised_oracle_atlas/predictions.json
mkdir -p outputs/our_unsupervised_atlas && cp hardening/runs/smoke/predictions.json outputs/our_unsupervised_atlas/predictions.json
bash scripts/evaluate_train.sh > logs/smoke_train.log 2>&1 || echo "EVAL TRAIN FAILED"
bash scripts/evaluate_test.sh > logs/smoke_test.log 2>&1 || echo "EVAL TEST FAILED"
tail -40 logs/smoke_test.log
cp hardening/runs/smoke/predictions.json hardening/runs/smoke_ref.json
for v in "smoke_shrink --atlas-shrinkage 0.3" "smoke_refine --atlas-refine 1" "smoke_radii --lambda-scale 0,1,0" "smoke_linear --mode linear"; do
  set -- $v; name=$1; shift
  timeout 600 python -m method.cycle_mgm --work checkpoints/$name --reuse checkpoints/smoke \
    --reuse-stages prealign,bo,postalign,mgm --output hardening/runs/$name/predictions.json \
    --trials 3,3,2 --learn-worms 4 --realign-iterations 1 "$@" || echo "VARIANT $name FAILED"
  python -m hardening.audit variant $name hardening/runs/$name/predictions.json || echo "AUDIT $name FAILED"
done
python -m hardening.audit variant reference_seed7 hardening/runs/smoke/predictions.json
for s in shortcut_identity_rows shortcut_selective_rows shortcut_forged_scores shortcut_degrade_comparators shortcut_train_whitelist shortcut_edit_dev_labels shortcut_pool_singletons; do
  python -m hardening.audit shortcut $s --reference hardening/runs/smoke/predictions.json || echo "AUDIT $s FAILED"
done
python -m hardening.audit summarize || echo "SUMMARY FAILED"
python validate.py || echo "VALIDATE FAILED"
