# Design Notes

## Checked
- Reviewed `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` for slice path and output-path copy-paste errors. Train writes `scoring/scores_train.json`; test writes `scoring/scores_test.json` and only reads train scores to restrict the held-out run to the same method set.
- Checked for train/test cross-imports and forbidden paper-agreement metric names in the split evaluators and `scoring/reference.json`.
- Confirmed no `scoring/scores_train.json` or `scoring/scores_test.json` stubs exist.
- Ran `bash -n` on both split scripts.

## Changed
- Fixed a label-leak shortcut: `eval/train/` and `eval/test/` no longer trust `test_labels` embedded in the method prediction artifact. Both slices load ground-truth labels from the fixed tracked benchmark data and use artifact labels only as an optional consistency check.
- Locked split evaluation to the default `scaled_manual_segmentation` scale: 12 train worms, 6 test worms, and 160 cells. Artifact metadata that tries to change those values now fails instead of silently changing the task.
- Added `atlas_accuracy_min` to reward methods that perform well across all held-out worms, not only on the average case.
- Added `invalid_assignment_rate` to penalize malformed or out-of-range assignments that could otherwise be hidden inside aggregate accuracy.
- Added required `description` fields for all metrics in `scoring/reference.json` and assigned nonzero coefficients to the two new anti-shortcut metrics.

## Runtime Concerns For Next Iteration
- The train/test slices are small because the tracked sample has 6 held-out worms, so each slice scores 3 worms. The added minimum-accuracy metric helps, but future data expansion would make the held-out gap more stable.
- The split evaluators now require prediction artifacts to contain one labeling per fixed default test worm. Artifacts generated with smoke or expanded scale settings should fail this formal split by design.
- `scoring/reference.json` now includes split metrics that are computed by `eval/train/` and `eval/test/`. If the unsplit `scripts/evaluate.sh` remains part of an automated comparison path, the runner should either refresh it to emit the same schema or keep train/test scores as the authoritative ResearchGym split outputs.
