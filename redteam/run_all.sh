#!/bin/bash
set -euo pipefail
cd /home/user
# Thread limits concern method computation only; no evaluator overrides.
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
python - <<'PY'
import json
from pathlib import Path
from redteam.fast_method import validate_equivalence
Path('redteam/vectorization_checks.json').write_text(json.dumps(validate_equivalence(), indent=2))
PY
for name in reference reference_seed7 reference_seed8 reference_seed9 better_training24 better_alignment \
  better_alignment_train6 better_alignment_train24 better_statistical_atlas \
  weaker_linear weaker_noquadratic weaker_radii_only \
  shortcut_bruteforce_exemplars shortcut_label_lookup shortcut_selective_1 shortcut_selective_10 \
  shortcut_duplicate_assignments shortcut_oracle_degradation shortcut_negative_flag \
  shortcut_failed_task_negative_flag shortcut_failed_task_oracle_flag shortcut_fixed_ground_truth \
  shortcut_empty_experiments shortcut_filter_methods shortcut_omit_oracle shortcut_claimed_scores \
  shortcut_constant_outputs shortcut_empty_outputs shortcut_null_outputs shortcut_null_method \
  shortcut_test_size shortcut_artifact_truth shortcut_direct_scores shortcut_stale_scores; do
  echo "Running $name"
  bash "redteam/$name/run.sh" > "redteam/$name/run.log" 2>&1
  python - "$name" <<'PY'
import json,sys
from pathlib import Path
name=sys.argv[1]
e=json.loads(Path('redteam',name,'evidence.json').read_text())
print(name, 'train=',e.get('train_returncode'), 'test=',e.get('test_returncode'), 'seconds=',round(e['elapsed_seconds'],2),flush=True)
PY
done
python -m redteam.summarize
