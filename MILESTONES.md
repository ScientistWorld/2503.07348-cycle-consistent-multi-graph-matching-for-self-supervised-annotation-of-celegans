# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-02 21:37] - core_claim
- Job `2787fdde-fbc` validated the corrected default scaled reproduction.
- Result: unsupervised atlas 0.8656 +/- 0.0964, unlearned baseline 0.7990 +/- 0.1381, supervised oracle 0.8521 +/- 0.1042, and no semantic labels used for training.
- Added an expanded scaled run script to probe whether the result holds at a larger 16-train/220-cell setting.

### [2026-06-02 21:32] - core_claim
- Audited implementation, evaluation, deliverables, and scoring structure.
- Corrected synchronization to maximize agreement with pairwise matches among pivot-induced cycle-consistent solutions, and corrected target documentation for pre-atlas diagnostics.

### [2026-06-02 21:30] - core_claim
- Replaced largest-pivot synchronization with best-agreement pivot synchronization while preserving the paper's Gaussian matching and cycle-consistent atlas pipeline.
- Submitting a CPU test job to validate the updated scaled reproduction and comparison metrics inside the container.

## Stop Justification
- Completed at milestone `core_claim`.
