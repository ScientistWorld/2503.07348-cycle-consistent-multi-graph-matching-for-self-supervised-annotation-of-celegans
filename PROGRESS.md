# Progress

## What Works

- Paper analysis is complete enough to define the core benchmark, metrics, baselines, and reported reference numbers.
- The workspace now includes the public cellmatch preprocessed Li et al. sample data: 20 train worms and 6 test worms, each with 558 nuclei.
- Implemented a scaled reproduction of the paper's computational procedure in `method/cycle_mgm.py`: Gaussian/Mahalanobis worm matching costs, staged parameter search, pairwise graph matching, synchronization into cycle-consistent cliques, atlas construction, and atlas-to-worm matching.
- Updated clique synchronization to select the pivot-induced cycle-consistent multi-matching with maximum agreement to all solved pairwise matchings, a scaled approximation of the paper's synchronization objective.
- Implemented method-agnostic evaluation in `eval/evaluate_outputs.py`; it reads prediction artifacts and does not import from `method/`.
- `python validate.py --reference-only` passes.

## Results

- Audit on 2026-06-02 confirmed that `method/` implements the paper's actual Gaussian/cycle-consistent graph matching pipeline at reduced scale, `eval/` reads artifacts without importing `method/`, and `reference.json` validates. The audit also found that synchronization should be closer to the paper's synchronization objective and that `atlas_minus_preatlas` should be treated as a diagnostic rather than a formal held-out target; both were corrected before the next submission.
- CPU job `8a05affa-d37` completed the smoke reproduction and wrote `scoring/scores.json`.
- Reproduced smoke scores on the tracked public sample: unlearned linear baseline atlas accuracy 0.9271 +/- 0.0104; unsupervised atlas accuracy 0.9583 +/- 0.0000; supervised oracle atlas accuracy 0.9583 +/- 0.0000.
- The unsupervised method also achieved pre-atlas accuracy 0.9531 +/- 0.0518, atlas-minus-pre-atlas improvement 0.0052, zero gap to the supervised oracle, and `semantic_labels_used_for_training = 0.0`.
- CPU job `f13ae259-26b` completed the medium scaled setting and updated `scoring/scores.json`: unlearned linear baseline atlas accuracy 0.9609 +/- 0.0316; unsupervised atlas accuracy 0.9609 +/- 0.0316; supervised oracle atlas accuracy 0.9661 +/- 0.0356.
- On the medium setting, the unsupervised method used no semantic labels during training, achieved pre-atlas accuracy 0.9505 +/- 0.0648, improved to atlas accuracy by 0.0104, and stayed within 0.0052 of the supervised oracle.
- CPU job `b50c2dd4-592` completed the default scaled reproduction in `scripts/reproduce.sh` and updated `scoring/scores.json`: unlearned linear baseline atlas accuracy 0.8281 +/- 0.1442; unsupervised atlas accuracy 0.8312 +/- 0.1340; supervised oracle atlas accuracy 0.8521 +/- 0.1042.
- On the default scaled setting, the unsupervised method remained near the supervised oracle with a 0.0208 gap and used no semantic labels during training, but atlas accuracy was lower than pre-atlas correspondence accuracy by 0.0844.
- Paper reference for the main full-scale setting: unsupervised atlas 0.961 +/- 0.020, supervised atlas 0.964 +/- 0.019.

## Remaining

- Higher milestones would require either implementing the paper's specialized Fusion Moves/MGM solvers or running a larger version of the original public code path. The current environment remains at `core_claim` until the updated synchronization is validated in a scheduled job.

## Issues

- The login Python environment lacks NumPy/SciPy, so execution is deferred to the scheduled container setup and CPU job.
- A local smoke run after the synchronization update could not execute because the login Python still lacks NumPy; the next scheduled CPU test job validates it inside the container.
- Job `40f9b62b-e9b` was killed after roughly 16 minutes with no method output. I reduced the smoke run to 4 train worms, 2 test worms, 48 nuclei, and 1 trial per learning stage, added flushed progress logging, and removed duplicate baseline all-pairs matching.
- Job `8a05affa-d37` completed in roughly 44 seconds, so the next submission scales up within the same one-CPU test-job envelope.
- Job `f13ae259-26b` completed the medium scaled run successfully. The unsupervised atlas was near the supervised oracle but did not outperform the unlearned baseline on this particular subset.
- Job `b50c2dd4-592` completed the default scaled run successfully. The supervised oracle also dropped substantially on the 160-cell setting, indicating atlas-to-held-out matching is the limiting component in this simplified solver rather than only unsupervised atlas construction.
- The full paper run is CPU-heavy and reported as dozens of hours; this workspace starts with a smaller tracked public sample and reduced optimization trials.

## Deviations from Paper

- Scale: the paper uses 100 training worms, 100 test worms, 558 nuclei, and extensive Bayesian optimization. The default workspace run uses the public code release's 20/6 preprocessed sample with subset defaults of 12 train worms, 6 test worms, 160 nuclei, and 6 random-search trials per learning stage. This preserves the procedure while making the first job practical.
- Solver: the paper uses specialized Fusion Moves and MGM solvers. This implementation uses SciPy linear assignment with iterative quadratic-cost linearization and best-agreement pivot synchronization. It keeps the same cost terms, clique construction, and atlas evaluation structure, but is a simpler solver implementation for the scaled benchmark.
