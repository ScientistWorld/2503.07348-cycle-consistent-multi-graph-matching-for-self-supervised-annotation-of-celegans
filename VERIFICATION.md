# Verification Report

## Initial Assessment
The workspace had a previous `core_claim_plus` history, but the current checked-out state had been changed to an all-558-cell default after the last valid score run. `action.yaml` and `MILESTONES.md` had already been downgraded to `method_runs`, and the current `outputs/method/predictions.json`, `scoring/scores.json`, `scores_train.json`, and `scores_test.json` still corresponded to the older 160-cell setting. Therefore the claimed final `core_claim_plus` state was not currently justified for the stricter default.

## Issues Found
- **Critical, fixed**: Formal code/docs required the all-558-cell default, but the score artifacts were stale from the older 160-cell run. CPU job `18a6816a-348` regenerated predictions and scores for the corrected default.
- **Critical, fixed**: Hidden train/test evaluators still assumed the old 160-cell label-selected evaluation slice, which would validate a different task than the updated formal reproduction.
- **Minor, fixed**: `briefing/evaluation.md` mentioned method-specific ablation names in a method-agnostic file.

## Fixes Applied
- Updated `eval/train/evaluate_slice.py` and `eval/test/evaluate_slice.py` to expect 558 cells and to use input-order cell limiting rather than semantic-label common-subset selection.
- Reworded `briefing/evaluation.md` to remove method-specific ablation names while preserving the headline paper target numbers.
- Confirmed `scripts/download.sh` has no `shared/` dependency and that the documented Zenodo source URL resolves with HTTP 200.
- Confirmed syntax compilation for the changed data, method, baseline, and evaluator modules.
- Reviewed successful job `18a6816a-348`: the all-cell run completed, train/test slice scores were written, and `python validate.py --compare` passed.

## Final Judgment
The workspace is ready to serve as a gym at `core_claim`. The from-scratch surface is method-agnostic (`data/`, `eval/`, `briefing/problem.md`, `briefing/evaluation.md`, and `scoring/EXPERIMENTS.md` do not expose the paper's implementation recipe), and the reusable evaluator reads method artifacts rather than rerunning the algorithm. The verified final score is intentionally lower than the prior `core_claim_plus` claim because the old expanded run used a pre-correction reduced setting.

- Milestone: core_claim
- Ready for gym use: yes
- Confidence: medium
- Key limitation: scaled public sample and simplified solver; only the core all-cell claim is verified after the label-free correction.
