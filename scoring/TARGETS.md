# Evaluation Targets

## Primary: scaled_manual_segmentation
Tests whether an atlas built from segmented C. elegans nuclei can accurately assign biological cell identities to held-out worms.
- **Metric**: `atlas_accuracy_mean` (higher is better)
- **Run**: produce a compatible prediction artifact, then run `bash scripts/evaluate.sh <predictions.json>`

## Constraint: scaled_manual_segmentation
Tests whether high accuracy is achieved without using semantic labels during atlas construction.
- **Metric**: `semantic_labels_used_for_training` (lower is better)
- **Run**: `bash scripts/evaluate.sh <predictions.json>`

## Constraint: scaled_manual_segmentation
Tests whether the unsupervised atlas remains close to a supervised oracle atlas on the same split.
- **Metric**: `gap_to_supervised_oracle` (lower is better)
- **Run**: `bash scripts/evaluate.sh <predictions.json>`

## Diagnostic: scaled_manual_segmentation
`pre_atlas_accuracy_mean` and `atlas_minus_preatlas` may be reported as diagnostics, but they are not formal targets in this scaled benchmark because pre-atlas accuracy is measured on training worms while atlas accuracy is measured on held-out worms.
