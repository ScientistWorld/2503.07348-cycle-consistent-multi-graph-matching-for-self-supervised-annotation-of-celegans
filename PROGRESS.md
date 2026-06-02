# Progress

## What Works

- Paper analysis is complete enough to define the core benchmark, metrics, baselines, and reported reference numbers.
- The workspace now includes the public cellmatch preprocessed Li et al. sample data: 20 train worms and 6 test worms, each with 558 nuclei.
- Implemented a scaled reproduction of the paper's computational procedure in `method/cycle_mgm.py`: Gaussian/Mahalanobis worm matching costs, staged parameter search, pairwise graph matching, synchronization into cycle-consistent cliques, atlas construction, and atlas-to-worm matching.
- Continuing audit on 2026-06-02 found that the formal default used semantic cell names to select a reduced common cell subset. The method and baseline now use all 558 cells by default, avoiding label-dependent subset construction; positive `--cells` values are retained only for label-free smoke diagnostics.
- Continuing audit on 2026-06-02 found and fixed a method-faithfulness gap: staged random search was replaced with Optuna TPE Bayesian optimization, matching the paper's three-stage parameter-learning procedure more closely. The learner now defaults to the synchronization loss used by the paper's main method.
- Updated clique synchronization to select the pivot-induced cycle-consistent multi-matching with maximum agreement to all solved pairwise matchings, a scaled approximation of the paper's synchronization objective.
- Implemented method-agnostic evaluation in `eval/evaluate_outputs.py`; it reads prediction artifacts and does not import from `method/`.
- CPU job `18a6816a-348` completed the corrected all-558-cell default reproduction, including train/test slice scoring and `python validate.py --compare`.

## Results

- Audit on 2026-06-02 confirmed that `method/` implements the paper's actual Gaussian/cycle-consistent graph matching pipeline at reduced scale, `eval/` reads artifacts without importing `method/`, and `reference.json` validates. The audit also found that synchronization should be closer to the paper's synchronization objective and that `atlas_minus_preatlas` should be treated as a diagnostic rather than a formal held-out target; both were corrected before the next submission.
- CPU job `2787fdde-fbc` completed the corrected default reproduction in 180 seconds and wrote `scoring/scores.json`. The unsupervised atlas reached 0.8656 +/- 0.0964 atlas accuracy, beating the unlearned linear baseline at 0.7990 +/- 0.1381 and staying at/above the supervised oracle on this scaled split (gap_to_supervised_oracle = -0.0135) while using no semantic labels for training.
- Added `scripts/expanded_core.sh` to probe a larger 16-train/6-test/220-cell setting without overwriting the validated default `scoring/scores.json`.
- CPU job `05ec4579-229` completed the expanded probe in 486 seconds and wrote `outputs/expanded/scores.json`. The unsupervised atlas reached 0.8598 +/- 0.0901, beating the unlearned linear baseline at 0.7720 +/- 0.1599 and staying at/above the supervised oracle at 0.8447 +/- 0.1192, again with no semantic labels used for training.
- Final validation on 2026-06-02 passed with `python validate.py --compare`. The validator confirmed that `eval/` and `data/` do not import from `method/`, evaluation reads method output artifacts, and committed code has no `shared/` path dependency.
- `scripts/method.sh` now evaluates the actual path supplied via `--output`, so custom method runs can be scored without accidentally reading the default artifact.
- CPU job `bd82a3e6-1a1` completed the audited Optuna/synchronization-loss default reproduction in 240 seconds and passed `python validate.py --compare`. The unsupervised atlas reached 0.8729 +/- 0.0913, beating the unlearned linear baseline at 0.7990 +/- 0.1381 while using no semantic labels for training; the gap to the supervised oracle was 0.0021.
- CPU job `fee0b427-5f9` completed the expanded audited Optuna/synchronization-loss probe in 481 seconds on a 16-train/6-test/220-cell setting. The unsupervised atlas reached 0.8424 +/- 0.1244, beating the unlearned linear baseline at 0.7720 +/- 0.1599 and staying at/above the supervised oracle at 0.8394 +/- 0.1504 (`gap_to_supervised_oracle = -0.0030`) while using no semantic labels for training.
- CPU job `8a05affa-d37` completed the smoke reproduction and wrote `scoring/scores.json`.
- Reproduced smoke scores on the tracked public sample: unlearned linear baseline atlas accuracy 0.9271 +/- 0.0104; unsupervised atlas accuracy 0.9583 +/- 0.0000; supervised oracle atlas accuracy 0.9583 +/- 0.0000.
- The unsupervised method also achieved pre-atlas accuracy 0.9531 +/- 0.0518, atlas-minus-pre-atlas improvement 0.0052, zero gap to the supervised oracle, and `semantic_labels_used_for_training = 0.0`.
- CPU job `f13ae259-26b` completed the medium scaled setting and updated `scoring/scores.json`: unlearned linear baseline atlas accuracy 0.9609 +/- 0.0316; unsupervised atlas accuracy 0.9609 +/- 0.0316; supervised oracle atlas accuracy 0.9661 +/- 0.0356.
- On the medium setting, the unsupervised method used no semantic labels during training, achieved pre-atlas accuracy 0.9505 +/- 0.0648, improved to atlas accuracy by 0.0104, and stayed within 0.0052 of the supervised oracle.
- CPU job `b50c2dd4-592` completed the default scaled reproduction in `scripts/reproduce.sh` and updated `scoring/scores.json`: unlearned linear baseline atlas accuracy 0.8281 +/- 0.1442; unsupervised atlas accuracy 0.8312 +/- 0.1340; supervised oracle atlas accuracy 0.8521 +/- 0.1042.
- On the default scaled setting, the unsupervised method remained near the supervised oracle with a 0.0208 gap and used no semantic labels during training, but atlas accuracy was lower than pre-atlas correspondence accuracy by 0.0844.
- Paper reference for the main full-scale setting: unsupervised atlas 0.961 +/- 0.020, supervised atlas 0.964 +/- 0.019.
- CPU job `18a6816a-348` completed the stricter all-558-cell default reproduction after removing label-dependent subset construction. `scoring/scores.json` now reports: unlearned linear baseline atlas accuracy 0.6941 +/- 0.1150; unsupervised atlas accuracy 0.7386 +/- 0.1259; supervised oracle atlas accuracy 0.7987 +/- 0.1301. The unsupervised method used no semantic labels during training, had zero invalid assignments, and stayed within 0.0600 of the supervised oracle.
- The hidden split scores also discriminate on the corrected all-cell setting: train slice unsupervised 0.7736 vs. baseline 0.7300, and test slice unsupervised 0.7037 vs. baseline 0.6583.

## Remaining

- Higher milestones require additional post-correction settings, such as a second all-cell split, a label-free cell-count stress test that does not choose cells by semantic names, the paper's synchronization-loss ablation, specialized Fusion Moves/MGM solvers, or a larger version of the original public code path.

## Issues

- The login Python environment lacks NumPy/SciPy, so execution is deferred to the scheduled container setup and CPU job.
- A local smoke run after the synchronization update could not execute because the login Python still lacks NumPy; the next scheduled CPU test job validates it inside the container.
- Job `40f9b62b-e9b` was killed after roughly 16 minutes with no method output. I reduced the smoke run to 4 train worms, 2 test worms, 48 nuclei, and 1 trial per learning stage, added flushed progress logging, and removed duplicate baseline all-pairs matching.
- Job `8a05affa-d37` completed in roughly 44 seconds, so the next submission scales up within the same one-CPU test-job envelope.
- Job `f13ae259-26b` completed the medium scaled run successfully. The unsupervised atlas was near the supervised oracle but did not outperform the unlearned baseline on this particular subset.
- Job `b50c2dd4-592` completed the default scaled run successfully. The supervised oracle also dropped substantially on the 160-cell setting, indicating atlas-to-held-out matching is the limiting component in this simplified solver rather than only unsupervised atlas construction.
- The full paper run is CPU-heavy and reported as dozens of hours; this workspace starts with a smaller tracked public sample and reduced optimization trials.
- The earlier `core_claim_plus` expanded score was based on a pre-correction reduced setting. It remains documented for audit history, but it is not counted as the verified final milestone.

## Deviations from Paper

- Scale: the paper uses 100 training worms, 100 test worms, 558 nuclei, and extensive Bayesian optimization. The default workspace run uses the public code release's 20/6 preprocessed sample with 12 train worms, 6 test worms, all 558 nuclei, and 6 Optuna TPE trials per learning stage. This preserves the procedure while making the first job practical.
- Solver: the paper uses specialized Fusion Moves and MGM solvers. This implementation uses SciPy linear assignment with iterative quadratic-cost linearization and best-agreement pivot synchronization. It keeps the same cost terms, clique construction, and atlas evaluation structure, but is a simpler solver implementation for the scaled benchmark.
