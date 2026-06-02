# Scientist Constraints

## Data
Use only the tracked preprocessed sample in `data/cellmatch_sample` for the default benchmark: train worms from `data/cellmatch_sample/train` and test worms from `data/cellmatch_sample/test`. Do not add external labeled worms, raw image measurements, or alternative splits when reporting `scaled_manual_segmentation`, because the benchmark is intended to measure methodology rather than extra data.

## Labels
Semantic cell names in the training files may not be used to construct the unsupervised atlas, tune matching parameters, choose correspondences, or select checkpoints. They may be used only by `eval/` to score artifacts and by the supervised oracle baseline reported separately.

## Evaluation
Report scores through `scripts/evaluate.sh` using prediction artifacts written by the submitted system. Do not edit `eval/` to import solution internals or recompute correspondences during scoring.

## Scale
For comparable default scores, keep the `scripts/reproduce.sh` default subset sizes unless a separate experiment name is introduced. Increasing the number of cells, worms, or optimization trials is a scale change and must not be presented as a direct improvement on `scaled_manual_segmentation`.

## Compliance Checklist
- [ ] Used only `data/cellmatch_sample` for `scaled_manual_segmentation`
- [ ] Did not use training semantic names inside the unsupervised method
- [ ] Test labels were used only by `eval/`
- [ ] Scores were produced by `scripts/evaluate.sh`
- [ ] Default subset sizes were not changed for direct comparison
