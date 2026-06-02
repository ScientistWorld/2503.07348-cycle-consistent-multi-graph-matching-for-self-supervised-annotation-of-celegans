# Evaluation

How success is measured. Describe only the metrics, targets, and evaluation procedure — do NOT describe the paper's method or how they achieved these results. Think of this as a general evaluation protocal for other scientists trying to solve the same problem, where they should not see this paper's solution.

## Metrics

The primary metric is atlas accuracy: the fraction of target nuclei assigned the correct biological name after matching a target worm to an atlas. Accuracy is reported as mean and standard deviation over worms; higher mean and lower standard deviation are better.

For unsupervised atlas construction, clique labels are induced only for evaluation by greedy maximum voting against ground-truth names. Pre-atlas accuracy measures the consistency output before atlas construction. The gap to a supervised oracle atlas is a constraint metric: lower is better because the claim is near-supervised accuracy without semantic labels for atlas construction.

## Baselines and Targets

Paper targets on the full 100-train/100-test manual-segmentation setting are: prior supervised atlas 0.93 +/- 0.11, the paper's supervised atlas 0.964 +/- 0.019, and the paper's unsupervised atlas 0.961 +/- 0.020. Training-set ablations report linear dense atlas accuracy 0.955 +/- 0.031 and full-pipeline atlas accuracy 0.972 +/- 0.015.

## Evaluation Protocol

The default workspace benchmark uses the public cellmatch release's tracked preprocessed Li et al. sample: training worms in `data/cellmatch_sample/train` and test worms in `data/cellmatch_sample/test`. Run `scripts/method.sh` to produce predictions, then `scripts/evaluate.sh` to score them. Evaluation code reads prediction artifacts only and does not import from `method/`.
