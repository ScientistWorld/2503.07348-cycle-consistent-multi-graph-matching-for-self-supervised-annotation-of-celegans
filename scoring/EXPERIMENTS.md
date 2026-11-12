# Experiment Overview

## scaled_manual_segmentation
Establishes whether a reference of cell identities built from unlabeled, manually segmented C. elegans worms can annotate new worms accurately — the paper's claim that a label-free reference approaches a supervised one.

- Data: 26 real worms from the public Li et al. (2024) manual segmentations (558 nuclei each): 12 unlabeled pool worms to build the reference, 4 visible dev worms, 10 hidden test worms whose inputs and labels never leave the hidden evaluator.
- Measurement: held-out worms are annotated one at a time by the submission's own annotator; accuracy is the fraction of nuclei given their true identity (mean over worms, and worst worm). Identities are named from the pool on the hidden side and leave-one-out across the dev worms on the visible side, where only 10 % of identities are labeled; the visible score is noisier and runs a few points below the hidden one.
- Comparison points: a frozen supervised comparator (same data, uses all pool names: 0.917 hidden) and a frozen unlearned label-free baseline (0.798). The scaled reproduction of the paper's method scores 0.892 (seed spread 0.4 points); the gap to the supervised comparator is the quantity the paper reports as 0.003 at 100 training worms.
- Scale: 12 instead of 100 reference worms and 10 instead of 100 test worms; the paper reports that accuracy grows with the number of reference worms.
