# Scientist Constraints

## Data
Use only what the benchmark ships: the 12 pool worms (`data/worms/pool`) to build the identity reference and the 4 dev worms (`data/worms/dev`) for development. Do not bring in other worms, raw images, external annotations or atlases — in particular not the public Li et al. / cellmatch files these worms come from, which carry their names.

## Labels
No semantic name of any nucleus may be used to build, train, tune, select or post-process the system. The only names a submission can read are the dev labels in `eval/train/dev_labels.json` (a fixed 10 % sample of identities); they exist so `scripts/evaluate_train.sh` can score, and may be used only to compare finished systems, never as a training or calibration signal inside the system.

## Annotation
Every held-out worm is annotated by `annotate.sh`, one worm per call, from that worm's table and the system's own trained files. An annotator must not read evaluator files (`eval/`), must not carry information between calls (e.g. caching earlier held-out worms) and must finish within 900 s per worm on one CPU.

## Evaluation
Scores come only from `scripts/evaluate_train.sh` / `scripts/evaluate_test.sh` (no arguments). Do not edit `eval/` or the frozen comparators.

## Scale
The pool size (12 worms) and the held-out sets are fixed. Training compute is free, but it must stay a property of the submitted system (the reference uses 6 learning worms and 30/30/10 optimisation trials, about 40 minutes on one CPU).

## Compliance Checklist
- [ ] Reference built only from `data/worms/pool` (dev worms used only for evaluation)
- [ ] No semantic names used inside the system; dev labels used only to compare finished systems
- [ ] `annotate.sh` annotates each worm independently, reads no `eval/` files, keeps no state across calls
- [ ] Scores produced by the two no-argument evaluation scripts
