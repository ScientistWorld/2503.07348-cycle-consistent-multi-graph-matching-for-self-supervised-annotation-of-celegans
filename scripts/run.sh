#!/bin/bash
# Hardening pipeline: reference (3 seeds), fixed comparators, better/weaker
# variants, shortcuts and diagnostics, all scored through the no-argument
# evaluation scripts. Reproduces the gym's reference end to end (~3 h on 1 CPU).
# Every stage skips work whose output already exists, so a rerun resumes.
cd /home/user
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p logs hardening/runs
echo "cpu.max: $(cat /sys/fs/cgroup/cpu.max 2>/dev/null) mem.max: $(cat /sys/fs/cgroup/memory.max 2>/dev/null) nproc: $(nproc)"
date
REF="--learn-worms 6 --trials 30,30,10"
S7=checkpoints/our_unsupervised_atlas

run() {  # run <name> <timeout-seconds> <cmd...>; skipped when its predictions exist
  local name=$1 limit=$2; shift 2
  local out=hardening/runs/$name/predictions.json
  if [ -f "$out" ]; then echo "skip $name"; return 0; fi
  local t0=$(date +%s)
  timeout "$limit" "$@" > "logs/$name.log" 2>&1 || echo "$name FAILED (see logs/$name.log)"
  echo "$name done in $(( $(date +%s) - t0 ))s"
}

# Stage A: reference seeds (seed 7 prioritised) and the supervised comparator.
run reference_seed7 12000 env GYM_WORKERS=4 python -m method.cycle_mgm --seed 7 --work $S7 \
  --output hardening/runs/reference_seed7/predictions.json $REF &
run reference_seed8 12000 nice -n 10 env GYM_WORKERS=2 python -m method.cycle_mgm --seed 8 --work checkpoints/ref_seed8 \
  --output hardening/runs/reference_seed8/predictions.json $REF &
run reference_seed9 12000 nice -n 10 env GYM_WORKERS=2 python -m method.cycle_mgm --seed 9 --work checkpoints/ref_seed9 \
  --output hardening/runs/reference_seed9/predictions.json $REF &
if [ ! -f eval/test/oracle/predictions.json ]; then  # hidden side: uses the pool's names
  timeout 12000 nice -n 5 env GYM_WORKERS=2 python -m eval.test.supervised_oracle \
    --output eval/test/oracle/predictions.json > logs/supervised_oracle.log 2>&1 || echo "oracle FAILED" &
fi
wait
date

# Stage B: baseline, variants (reusing the seed checkpoints) and the dev-label shortcut.
V="python -m method.cycle_mgm $REF"
run unlearned_linear_baseline 5400 env GYM_WORKERS=2 python -m baseline.unlearned_linear --reuse $S7 \
  --work checkpoints/unlearned_linear_baseline --output hardening/runs/unlearned_linear_baseline/predictions.json &
for s in 7 8 9; do
  W=$S7; [ $s != 7 ] && W=checkpoints/ref_seed$s
  run better_shrink03_seed$s 5400 env GYM_WORKERS=2 $V --seed $s --work checkpoints/shrink03_s$s --reuse $W \
    --reuse-stages prealign,bo,postalign,mgm --atlas-shrinkage 0.3 --output hardening/runs/better_shrink03_seed$s/predictions.json &
done
run better_shrink05_seed7 5400 env GYM_WORKERS=1 $V --seed 7 --work checkpoints/shrink05_s7 --reuse $S7 \
  --reuse-stages prealign,bo,postalign,mgm --atlas-shrinkage 0.5 --output hardening/runs/better_shrink05_seed7/predictions.json &
run better_refine1_seed7 5400 env GYM_WORKERS=1 $V --seed 7 --work checkpoints/refine1_s7 --reuse $S7 \
  --reuse-stages prealign,bo,postalign,mgm --atlas-refine 1 --output hardening/runs/better_refine1_seed7/predictions.json &
run weaker_linear_seed7 5400 env GYM_WORKERS=1 $V --seed 7 --mode linear --work checkpoints/linear_s7 --reuse $S7 \
  --reuse-stages prealign,bo --output hardening/runs/weaker_linear_seed7/predictions.json &
run weaker_radii_only_seed7 5400 env GYM_WORKERS=1 $V --seed 7 --lambda-scale 0,1,0 --work checkpoints/radii_s7 --reuse $S7 \
  --reuse-stages prealign,bo,postalign --output hardening/runs/weaker_radii_only_seed7/predictions.json &
run weaker_unlearned_quadratic_seed7 5400 nice -n 10 env GYM_WORKERS=2 $V --seed 7 --mode unlearned_quadratic \
  --work checkpoints/unlq_s7 --reuse $S7 --reuse-stages prealign \
  --output hardening/runs/weaker_unlearned_quadratic_seed7/predictions.json &
wait
date

# Stage D: shortcut / diagnostic follow-ups (after restricting visible dev labels).
#   - supervised atlas from the (now 10 %) visible dev labels, alone and as a hybrid override
#   - transductive MGM that also puts the visible test inputs into the atlas (forbidden)
#   - the reference with twice the BO search (is the reference budget-limited?)
run shortcut_supervised_dev_subset 5400 env GYM_WORKERS=1 python -m hardening.supervised_dev --work $S7 \
  --mode full --output hardening/runs/shortcut_supervised_dev_subset/predictions.json &
run shortcut_supervised_dev_hybrid 5400 env GYM_WORKERS=1 python -m hardening.supervised_dev --work $S7 \
  --mode hybrid --reference hardening/runs/reference_seed7/predictions.json \
  --output hardening/runs/shortcut_supervised_dev_hybrid/predictions.json &
run shortcut_transductive_mgm 9000 env GYM_WORKERS=2 $V --seed 7 --transductive --work checkpoints/transductive_s7 \
  --reuse $S7 --reuse-stages prealign,bo,postalign --output hardening/runs/shortcut_transductive_mgm/predictions.json &
run diag_more_bo_seed7 9000 env GYM_WORKERS=2 python -m method.cycle_mgm --seed 7 --learn-worms 6 --trials 60,60,20 \
  --work checkpoints/more_bo_s7 --reuse $S7 --reuse-stages prealign \
  --output hardening/runs/diag_more_bo_seed7/predictions.json &
wait
date

# Stage C: freeze comparators, install the reference, score everything.
python eval/test/install_comparator.py supervised_oracle_atlas eval/test/oracle/predictions.json
python eval/test/install_comparator.py unlearned_linear_baseline hardening/runs/unlearned_linear_baseline/predictions.json
mkdir -p outputs/our_unsupervised_atlas
cp hardening/runs/reference_seed7/predictions.json outputs/our_unsupervised_atlas/predictions.json
rm -rf hardening/cases
for d in hardening/runs/*/; do
  name=$(basename "$d"); kind=variant
  case $name in shortcut_*) kind=shortcut;; diag_*) kind=diagnostic;; esac
  python -m hardening.audit variant "$name" "$d/predictions.json" --kind $kind
done
for s in shortcut_identity_rows shortcut_empty_object shortcut_missing_predictions shortcut_null_predictions \
         shortcut_selective_rows shortcut_duplicate_labels shortcut_all_unassigned shortcut_claimed_metrics \
         shortcut_forged_scores shortcut_degrade_comparators shortcut_train_whitelist shortcut_edit_dev_labels \
         shortcut_pool_singletons; do
  python -m hardening.audit shortcut $s
done
bash scripts/evaluate_train.sh > logs/final_train.log 2>&1
bash scripts/evaluate_test.sh > logs/final_test.log 2>&1
bash scripts/evaluate.sh > logs/final_scores.log 2>&1
python -m hardening.audit summarize
python validate.py --post-design || echo "VALIDATE FAILED"
# Predictions whose label ids encode names (supervised shortcuts) must not stay on disk.
rm -f hardening/runs/shortcut_supervised_dev_all_labels_before_fix/predictions.json \
      hardening/runs/shortcut_supervised_dev_subset/predictions.json
mkdir -p hardening/logs
for f in logs/*.log; do grep -v -E '^([0-9]+/[0-9]+ ?)+$' "$f" | sed -E 's/([0-9]+\/[0-9]+ )+//g' > "hardening/logs/$(basename "$f")"; done
date
