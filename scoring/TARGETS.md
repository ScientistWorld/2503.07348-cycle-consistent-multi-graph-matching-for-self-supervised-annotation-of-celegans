# Evaluation Targets

## Primary: scaled_manual_segmentation
Tests whether an atlas built from segmented C. elegans nuclei can accurately assign biological cell identities to held-out worms.
- **Metric**: `atlas_accuracy_mean` (higher is better)
- **Run**: `bash scripts/method.sh` followed by `bash scripts/evaluate.sh outputs/method/predictions.json`

## Constraint: scaled_manual_segmentation
Tests whether high accuracy is achieved without using semantic labels during atlas construction.
- **Metric**: `semantic_labels_used_for_training` (lower is better)
- **Run**: `bash scripts/evaluate.sh outputs/method/predictions.json`

## Constraint: scaled_manual_segmentation
Tests whether the unsupervised atlas remains close to a supervised oracle atlas on the same split.
- **Metric**: `gap_to_supervised_oracle` (lower is better)
- **Run**: `bash scripts/evaluate.sh outputs/method/predictions.json`

## Ablation: scaled_manual_segmentation
Tests whether constructing an atlas improves over the pre-atlas multi-worm correspondence output.
- **Metric**: `atlas_minus_preatlas` (higher is better)
- **Run**: `bash scripts/evaluate.sh outputs/method/predictions.json`
