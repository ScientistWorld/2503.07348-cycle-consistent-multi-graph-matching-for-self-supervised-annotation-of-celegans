# Evaluation Targets

All targets belong to the single experiment `scaled_manual_segmentation`, scored by
`bash scripts/evaluate_test.sh` (hidden, 10 worms) and `bash scripts/evaluate_train.sh`
(visible, 4 dev worms); both take no arguments and score every method under `outputs/`.

## Primary: held-out identity accuracy
Fraction of held-out nuclei assigned their true biological identity, averaged over worms.
- **Metric**: `atlas_accuracy_mean` (higher is better, coefficient 1.0)
- Reference (hidden): 0.892; frozen supervised comparator 0.917; unlearned baseline 0.798.

## Secondary: worst-worm accuracy
Accuracy of the hardest held-out worm, so a method cannot trade some worms for others.
- **Metric**: `atlas_accuracy_min` (higher is better, coefficient 0.25)
- Reference (hidden): 0.817.

## Constraints (hard: violating them fails the run → worst value of every metric)
- No semantic labels: none are available to a submission except the visible dev labels, which are for scoring only (see CONSTRAINTS.md).
- Valid one-to-one assignments: one integer per nucleus, no identity used twice within a worm, every pool worm and every held-out worm annotated, `annotate.sh` succeeds within 900 s per worm.

## Diagnostics (reported, coefficient 0)
- `atlas_accuracy_std`: spread of per-worm accuracy.
- `pre_atlas_accuracy_mean` (hidden side only): accuracy of the submitted pool groups themselves.
- `gap_to_supervised_oracle`: frozen supervised comparator accuracy minus the method's accuracy (paper: 0.003 at 100 worms).
