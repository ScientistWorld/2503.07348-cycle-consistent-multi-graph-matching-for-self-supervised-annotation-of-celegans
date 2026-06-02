# Progress

## What Works

- Paper analysis is complete enough to define the core benchmark, metrics, baselines, and reported reference numbers.
- The workspace now includes the public cellmatch preprocessed Li et al. sample data: 20 train worms and 6 test worms, each with 558 nuclei.
- Implemented a scaled reproduction of the paper's computational procedure in `method/cycle_mgm.py`: Gaussian/Mahalanobis worm matching costs, staged parameter search, pairwise graph matching, synchronization into cycle-consistent cliques, atlas construction, and atlas-to-worm matching.
- Implemented method-agnostic evaluation in `eval/evaluate_outputs.py`; it reads prediction artifacts and does not import from `method/`.
- `python validate.py --reference-only` passes.

## Results

- No reproduced scores yet. CPU job `40f9b62b-e9b` was killed before any user-level method output, so it did not produce `scoring/scores.json`.
- The next submitted CPU job runs the much smaller `scripts/smoke.sh` diagnostic and writes `scoring/scores.json` if the method/evaluator pipeline completes.
- Paper reference for the main full-scale setting: unsupervised atlas 0.961 +/- 0.020, supervised atlas 0.964 +/- 0.019.

## Remaining

- Run the scaled method inside the compute container and inspect `scoring/scores.json`.
- If the smoke job succeeds, increase the scale or number of trials if runtime permits.
- If accuracy is close to the trivial baseline, diagnose parameter search, synchronization, and atlas matching before claiming `core_claim`.

## Issues

- The login Python environment lacks NumPy/SciPy, so execution is deferred to the scheduled container setup and CPU job.
- Job `40f9b62b-e9b` was killed after roughly 16 minutes with no method output. I reduced the smoke run to 4 train worms, 2 test worms, 48 nuclei, and 1 trial per learning stage, added flushed progress logging, and removed duplicate baseline all-pairs matching.
- The full paper run is CPU-heavy and reported as dozens of hours; this workspace starts with a smaller tracked public sample and reduced optimization trials.

## Deviations from Paper

- Scale: the paper uses 100 training worms, 100 test worms, 558 nuclei, and extensive Bayesian optimization. The default workspace run uses the public code release's 20/6 preprocessed sample with subset defaults of 12 train worms, 6 test worms, 160 nuclei, and 6 random-search trials per learning stage. This preserves the procedure while making the first job practical.
- Solver: the paper uses specialized Fusion Moves and MGM solvers. This implementation uses SciPy linear assignment with iterative quadratic-cost linearization and pivot-based synchronization. It keeps the same cost terms, clique construction, and atlas evaluation structure, but is a simpler solver implementation for the scaled benchmark.
