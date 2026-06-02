# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-06-02 21:47] - core_claim_plus
- Job `05ec4579-229` validated an expanded 16-train/6-test/220-cell setting.
- Expanded result: unsupervised atlas 0.8598 +/- 0.0901, unlearned baseline 0.7720 +/- 0.1599, supervised oracle 0.8447 +/- 0.1192, and no semantic labels used for training.
- Restored `scripts/run.sh` to the default validated reproduction and comparison path.

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
- Completed at milestone `core_claim_plus`.
