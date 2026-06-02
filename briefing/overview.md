# Overview

- **Paper ID:** 2503.07348
- **Title:** Cycle-Consistent Multi-Graph Matching for Self-Supervised Annotation of C. Elegans
- **Domain:** Biomedical computer vision / graph matching
- **TL;DR:** The paper builds a C. elegans cell atlas without semantic labels by learning Gaussian graph-matching costs from cycle consistency across segmented worms.

## Short Summary

The task is to assign consistent biological names to hundreds of nuclei in 3D worm microscopy images. The paper models worms as graphs of nuclei and learns the parameters of a Gaussian graph-matching objective without semantic labels, using cycle consistency across multiple worms as the self-supervised signal. The resulting cliques form an unsupervised statistical atlas that can be matched to new worms. On the full benchmark, the unsupervised atlas is reported within 0.003 accuracy of the paper's supervised atlas.

## Key Results

- Main manual-segmentation result: unsupervised atlas 0.961 +/- 0.020 vs supervised atlas 0.964 +/- 0.019.
- Pipeline ablation: full pipeline atlas accuracy 0.972 +/- 0.015 on training-set ablations vs 0.955 +/- 0.031 for linear dense.
- Robustness result with automatic StarDist segmentations: full unsupervised pipeline 0.809 +/- 0.147 atlas accuracy.
