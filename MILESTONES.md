# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-02 22:04] - core_claim
- Continuing audit found that the previous implementation used staged random search for parameter learning, while the paper's method uses staged Bayesian optimization.
- Replaced the learner with Optuna TPE Bayesian optimization for the paper's three stages and switched the default self-supervised objective to synchronization loss.
- Local syntax checks and `python validate.py --compare` pass; a scheduled CPU job is needed before restoring `core_claim_plus` for the updated method.

### [2026-06-02 21:49] - core_claim_plus
- Default scaled reproduction completed in a scheduled CPU job and validates with `python validate.py --compare`.
- Proposed unsupervised atlas reached 0.8656 +/- 0.0964 held-out atlas accuracy on the tracked public sample, beating the unlearned linear baseline at 0.7990 +/- 0.1381 while using no semantic labels for training.
- Expanded 16-train/6-test/220-cell probe also completed and supported the same claim: unsupervised atlas 0.8598 +/- 0.0901 vs. unlearned linear baseline 0.7720 +/- 0.1599.

## Stop Justification
- Not stopped. The updated Bayesian-optimization learner is being submitted for scheduled validation.
