# Evaluation

## What a submission provides

A directory `outputs/<method_name>/` (the ranked one is `outputs/our_unsupervised_atlas/`) containing

- `predictions.json`: `{"pool_cliques": {"p00": [...], ..., "p11": [...]}}` — for every pool worm, one integer per row: the identity (group id) the system gives that nucleus, or `-1`. Within a worm an id may appear at most once.
- `annotate.sh`: `bash annotate.sh <worm.txt> <labels.json>` reads ONE worm table (same format as `data/worms/*/*.txt`) and writes a JSON list with one identity id (an id used in `pool_cliques`) or `-1` per row, no id twice. It runs from `/home/user` inside the gym container, without internet, with a 900 s limit per call. Anything else the directory needs (e.g. model files) may live next to it.

## How it is scored

Held-out worms are handed to `annotate.sh` one per call: the 4 dev worms (`data/worms/dev/`) by `scripts/evaluate_train.sh`, 10 hidden worms (never visible) by `scripts/evaluate_test.sh`. Both scripts take no arguments and score every directory under `outputs/` plus two frozen comparators.

- Identity ids are turned into biological names by greedy maximum voting: hidden test — over the true names of the pool nuclei in each of the submission's pool groups; visible slice — leave-one-out over the other dev worms (only a fixed 10 % sample of identities is labeled there, and accuracy is measured on those nuclei). Unnamed ids count as wrong.
- **Primary metric** `atlas_accuracy_mean`: mean over held-out worms of the fraction of nuclei assigned their true identity (unassigned = wrong). Also ranked: `atlas_accuracy_min` (worst worm). Diagnostics (not ranked): per-worm standard deviation, accuracy of the pool groups themselves (hidden side), and the gap to the frozen supervised comparator.
- Any missing file, crash, timeout, malformed or duplicated assignment fails the run, which then receives the worst value of every metric. Nothing a submission writes besides its raw assignments is read.

## Reference points

Paper (100 training / 100 test worms): supervised reference 0.964 ± 0.019, label-free reference 0.961 ± 0.020, prior supervised method 0.93 ± 0.11. On this 12-worm benchmark the frozen supervised comparator (built with all pool names) scores 0.917 on the hidden worms and an unlearned label-free baseline 0.798.
