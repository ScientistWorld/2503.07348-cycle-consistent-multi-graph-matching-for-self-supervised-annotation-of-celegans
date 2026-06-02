# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-02 23:19] - core_claim
- CPU job `18a6816a-348` completed the stricter all-558-cell default reproduction and `python validate.py --compare` passed.
- The unsupervised atlas reached 0.7386 +/- 0.1259 held-out atlas accuracy, beating the unlearned linear baseline at 0.6941 +/- 0.1150 while using no semantic labels for training.
- The method stayed near the supervised oracle on the same all-cell held-out worms (`gap_to_supervised_oracle = 0.0600`) with zero invalid assignments, restoring `core_claim` for the label-free benchmark.

### [2026-06-02 22:45] - method_runs
- Removed semantic-label-dependent common-subset selection from the formal method and baseline paths.
- Updated the default reproduction to use all 558 cells in each selected worm.
- Scheduled a CPU job to regenerate predictions and scores before restoring `core_claim` or above for the stricter default.

### [2026-06-02 22:34] - core_claim_plus
- Final verification passed with `python validate.py --compare`.
- Method-agnostic documentation, formal score metrics, baseline separation, and generated-artifact cleanup were tightened without changing the reproduced milestone.

### [2026-06-02 22:08] - core_claim_plus
- CPU job `fee0b427-5f9` completed the expanded audited Optuna/synchronization-loss probe on a 16-train/6-test/220-cell setting.
- The unsupervised atlas reached 0.8424 +/- 0.1244 held-out atlas accuracy, beating the unlearned linear baseline at 0.7720 +/- 0.1599.
- The same run stayed at/above the supervised oracle on this scaled split (`gap_to_supervised_oracle = -0.0030`) while using no semantic labels for training, restoring `core_claim_plus` under the audited implementation.

### [2026-06-02 21:50] - core_claim
- Continuing audit found that the previous implementation used staged random search for parameter learning, while the paper's method uses staged Bayesian optimization.
- Replaced the learner with Optuna TPE Bayesian optimization for the paper's three stages and switched the default self-supervised objective to synchronization loss.
- Local syntax checks and `python validate.py --compare` pass; a scheduled CPU job is needed before restoring `core_claim_plus` for the updated method.

### [2026-06-02 21:58] - core_claim
- CPU job `bd82a3e6-1a1` completed the updated Optuna/synchronization-loss default reproduction and `python validate.py --compare` passed.
- Updated proposed unsupervised atlas reached 0.8729 +/- 0.0913 held-out atlas accuracy, beating the unlearned linear baseline at 0.7990 +/- 0.1381.
- The unsupervised atlas used no semantic labels for training and stayed within 0.0021 of the supervised oracle on the scaled default setting.

### [2026-06-02 21:49] - core_claim_plus
- Default scaled reproduction completed in a scheduled CPU job and validates with `python validate.py --compare`.
- Proposed unsupervised atlas reached 0.8656 +/- 0.0964 held-out atlas accuracy on the tracked public sample, beating the unlearned linear baseline at 0.7990 +/- 0.1381 while using no semantic labels for training.
- Expanded 16-train/6-test/220-cell probe also completed and supported the same claim: unsupervised atlas 0.8598 +/- 0.0901 vs. unlearned linear baseline 0.7720 +/- 0.1599.

## Stop Justification
- Completed at milestone `core_claim`.
