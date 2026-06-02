# Evaluation

## Metrics

The primary metric is identity accuracy: the fraction of target nuclei assigned the correct biological name in held-out worms. Accuracy is reported as mean, minimum, and standard deviation over worms; higher mean/minimum and lower standard deviation are better.

The evaluator also reports invalid assignment rate, the fraction of predicted assignments that are missing, malformed, or point outside the target worm. The gap to a supervised oracle on the same split is a constraint metric: lower is better because the target is high identity accuracy without using semantic labels to build the unsupervised reference.

## Baselines and Targets

Paper targets on the full 100-train/100-test manual-segmentation setting are: prior supervised reference 0.93 +/- 0.11, the paper's supervised reference 0.964 +/- 0.019, and the paper's label-free reference 0.961 +/- 0.020. Training-set diagnostic results in the paper range from roughly 0.955 to 0.972 atlas accuracy, depending on the system variant.

## Evaluation Protocol

The default workspace benchmark uses the tracked preprocessed Li et al. sample: training worms in `data/cellmatch_sample/train` and test worms in `data/cellmatch_sample/test`. A submitted system should write a prediction artifact with one or more named methods under the documented JSON format, then `scripts/evaluate.sh <predictions.json>` scores that artifact. Evaluation code reads prediction artifacts only and does not import from any solution implementation.
