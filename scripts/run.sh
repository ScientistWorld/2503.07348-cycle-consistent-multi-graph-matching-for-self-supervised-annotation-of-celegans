#!/bin/bash
# Hardening pipeline (annotator layout). Builds the reference and its variants,
# freezes the comparators, then scores every case through the no-argument
# evaluation scripts. Each stage skips finished work, so a rerun resumes.
#   reference: python -m method.cycle_mgm --seed 7 (pool-only training, ~40 min on 1 CPU)
#   hidden test of one method: 10 annotate.sh calls (~40 s each)
cd /home/user
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p logs hardening/runs
echo "nproc: $(nproc)"; date
REF="--learn-worms 6 --trials 30,30,10"
M="python -m method.cycle_mgm"

run() {  # run <name> <timeout> <cmd...>; skipped when hardening/runs/<name>/annotate.sh exists
  local name=$1 limit=$2; shift 2
  if [ -f "hardening/runs/$name/annotate.sh" ]; then echo "skip $name"; return 0; fi
  local t0=$(date +%s)
  timeout "$limit" "$@" > "logs/$name.log" 2>&1 || echo "$name FAILED (see logs/$name.log)"
  echo "$name done in $(( $(date +%s) - t0 ))s"
}
out() { echo "--output hardening/runs/$1/predictions.json"; }

# Stage A: final reference (fresh training, seed 7), comparators, and methods
# rebuilt from the previous run's pool-side checkpoints (pool-side code unchanged).
run reference_seed7 12000 env GYM_WORKERS=4 $M --seed 7 --work checkpoints/ref7_final $REF $(out reference_seed7) &
if [ ! -f eval/test/oracle/predictions.json ]; then  # hidden side: uses the pool's names
  timeout 9000 nice -n 5 env GYM_WORKERS=2 python -m eval.test.supervised_oracle \
    --output eval/test/oracle/predictions.json > logs/supervised_oracle.log 2>&1 || echo "oracle FAILED" &
fi
run unlearned_linear_baseline 5400 nice -n 5 env GYM_WORKERS=2 python -m baseline.unlearned_linear \
  --work checkpoints/unlearned_linear_baseline $(out unlearned_linear_baseline) &
for s in 8 9; do
  run reference_seed$s 3000 env GYM_WORKERS=1 $M --seed $s --work checkpoints/ref_seed$s $REF $(out reference_seed$s)
  run better_shrink03_seed$s 3000 env GYM_WORKERS=1 $M --seed $s --work checkpoints/shrink03_s$s $REF \
    --atlas-shrinkage 0.3 $(out better_shrink03_seed$s)
done
run weaker_linear_seed7 3000 env GYM_WORKERS=1 $M --seed 7 --mode linear --work checkpoints/linear_s7 $REF $(out weaker_linear_seed7)
run weaker_radii_only_seed7 3000 env GYM_WORKERS=1 $M --seed 7 --lambda-scale 0,1,0 --work checkpoints/radii_s7 $REF \
  $(out weaker_radii_only_seed7)
run weaker_unlearned_quadratic_seed7 3000 env GYM_WORKERS=1 $M --seed 7 --mode unlearned_quadratic --work checkpoints/unlq_s7 \
  --reuse checkpoints/our_unsupervised_atlas --reuse-stages "" $REF $(out weaker_unlearned_quadratic_seed7)
run diag_more_bo_seed7 3000 env GYM_WORKERS=1 $M --seed 7 --learn-worms 6 --trials 60,60,20 --work checkpoints/more_bo_s7 \
  $(out diag_more_bo_seed7)
wait
date
# Stage B: paired better variants of the final reference.
for v in "better_shrink03_seed7 0.3" "better_shrink05_seed7 0.5"; do
  set -- $v
  run $1 3000 env GYM_WORKERS=1 $M --seed 7 --work checkpoints/${1}_final --reuse checkpoints/ref7_final \
    --reuse-stages prealign,bo,postalign,mgm $REF --atlas-shrinkage $2 $(out $1)
done
date

# Stage C: install the reference, freeze comparators, audit, final scoring.
git checkout -- eval/train/dev_labels.json 2>/dev/null || true   # in case an audit was interrupted
find outputs -mindepth 1 -maxdepth 1 ! -name our_unsupervised_atlas -exec rm -rf {} +
rm -rf outputs/our_unsupervised_atlas && mkdir -p outputs/our_unsupervised_atlas
cp hardening/runs/reference_seed7/{predictions.json,model.json,annotate.sh} outputs/our_unsupervised_atlas/
python eval/test/run_annotator.py hardening/runs/unlearned_linear_baseline hardening/runs/baseline_labelings.json
python eval/test/install_comparator.py unlearned_linear_baseline hardening/runs/baseline_labelings.json
python eval/test/install_comparator.py supervised_oracle_atlas eval/test/oracle/predictions.json
[ -f hardening/runs/reference_annotation_cache.json ] || {
  python eval/test/run_annotator.py outputs/our_unsupervised_atlas hardening/runs/reference_labelings.json &&
  python -m hardening.cached_annotate --build hardening/runs/reference_annotation_cache.json hardening/runs/reference_labelings.json; }
batch() {  # batch <case>...; cases already audited are skipped
  local args=()
  for c in "$@"; do
    name=${c%%=*}
    [ -f "hardening/cases/$name/evidence.json" ] || args+=("$c")
  done
  [ ${#args[@]} -eq 0 ] || python -m hardening.audit batch "${args[@]}"
}
R=hardening/runs
batch reference_seed7=$R/reference_seed7:reference reference_seed8=$R/reference_seed8:reference
batch reference_seed9=$R/reference_seed9:reference better_shrink03_seed7=$R/better_shrink03_seed7:better
batch better_shrink03_seed8=$R/better_shrink03_seed8:better better_shrink03_seed9=$R/better_shrink03_seed9:better
batch better_shrink05_seed7=$R/better_shrink05_seed7:better diag_more_bo_seed7=$R/diag_more_bo_seed7:diagnostic
batch weaker_unlearned_quadratic_seed7=$R/weaker_unlearned_quadratic_seed7:weaker \
  weaker_linear_seed7=$R/weaker_linear_seed7:weaker weaker_radii_only_seed7=$R/weaker_radii_only_seed7:weaker \
  unlearned_linear_baseline=$R/unlearned_linear_baseline:weaker
for s in shortcut_identity_rows shortcut_empty_object shortcut_missing_predictions shortcut_null_predictions \
         shortcut_missing_annotator shortcut_crashing_annotator shortcut_selective_rows shortcut_selective_annotation \
         shortcut_duplicate_labels shortcut_all_unassigned shortcut_claimed_metrics shortcut_forged_scores \
         shortcut_degrade_comparators shortcut_train_whitelist shortcut_edit_dev_labels shortcut_pool_singletons; do
  [ -f "hardening/cases/$s/evidence.json" ] || python -m hardening.audit shortcut $s
done
bash scripts/evaluate_train.sh > logs/final_train.log 2>&1
bash scripts/evaluate_test.sh > logs/final_test.log 2>&1
bash scripts/evaluate.sh > logs/final_scores.log 2>&1
python -m hardening.audit summarize
python validate.py --post-design || echo "VALIDATE FAILED"
mkdir -p hardening/logs
for f in logs/*.log; do grep -v -E '^([0-9]+/[0-9]+ ?)+$' "$f" | sed -E 's/([0-9]+\/[0-9]+ )+//g' > "hardening/logs/$(basename "$f")"; done
date
