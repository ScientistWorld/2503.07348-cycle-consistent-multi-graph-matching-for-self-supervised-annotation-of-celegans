# Reproduction Milestones

**Current: core_claim_plus**

<!-- Milestone levels (update "Current" above as you progress):
  none             — just started, no meaningful progress yet
  method_runs      — the paper's method executes end-to-end without errors
  core_claim       — minimum experiment supports the paper's central claim
  core_claim_plus  — core claim reproduced on additional settings
  secondary_claims — secondary results or contributions reproduced
  majority         — more than half of reported results reproduced
  near_complete    — most results reproduced, only minor gaps remain
  full             — all reported results reproduced
-->

## Progress Log

### [2026-06-02 20:51] - none
- Read the paper and identified the core claim: unsupervised cycle-consistent multi-graph matching builds a C. elegans atlas with near-supervised annotation accuracy.
- Added a scaled implementation using Gaussian unary/quadratic matching costs, parameter search, synchronization into cliques, unsupervised atlas construction, and atlas-to-worm evaluation on the public preprocessed cellmatch sample.
- Prepared a CPU smoke job to run the method end-to-end; milestone remains `none` until the job result confirms execution.

### [2026-06-02 21:27] - none
- CPU job `40f9b62b-e9b` exited `-9` before producing method output or scores.
- Added flushed progress logging, removed duplicate baseline all-pairs matching, and switched `scripts/run.sh` to a smaller diagnostic smoke run.

### [2026-06-02 21:31] - core_claim
- CPU job `8a05affa-d37` completed the cycle-consistent multi-graph matching pipeline end-to-end on the tracked public sample.
- Reproduced the central effect on a small real-data setting: unsupervised atlas accuracy 0.9583, supervised oracle atlas accuracy 0.9583, and unlearned linear baseline accuracy 0.9271.
- The reproduced method used no semantic labels during training; labels were induced only for evaluation.

### [2026-06-02 21:36] - core_claim_plus
- CPU job `f13ae259-26b` completed the medium scaled setting with 8 training worms, 4 test worms, 96 cells, and 2 trials per learning stage.
- The no-label unsupervised atlas reached 0.9609 +/- 0.0316, close to the supervised oracle at 0.9661 +/- 0.0356 and to the paper's reported unsupervised atlas accuracy of 0.961.
- The result extends the core near-supervised annotation claim beyond the initial smoke subset.

### [2026-06-02 21:45] - core_claim_plus
- CPU job `b50c2dd4-592` completed the default scaled reproduction with 12 training worms, 6 test worms, 160 cells, and 6 trials per learning stage.
- The unsupervised atlas stayed close to the supervised oracle on the same split: 0.8312 versus 0.8521, with no semantic labels used for training.
- The run does not justify a higher milestone because atlas construction reduced pre-atlas accuracy on this harder setting and the simplified solver remains below the paper's full-scale accuracy.

## Stop Justification
- Completed at milestone `core_claim_plus`.
