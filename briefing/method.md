# Paper's Method

How the paper approaches the problem, i.e. the paper's core contributions.

## Key Contribution

A fully unsupervised atlas-learning pipeline for C. elegans nuclei based on cycle-consistent multi-graph matching (MGM). Cycle-consistent cliques of corresponding nuclei across worms replace manual semantic labels; a Gaussian statistical atlas is built from them and matched to new worms.

## Approach

Worms are graphs of nuclei with centroid and radii features. Worm-to-worm graph matching uses Mahalanobis unary costs (centroids, radii) and pairwise costs (centroid offsets between neighbouring nuclei) with cross-nucleus diagonal covariances, an unassignment constant and sparsification. The 12 parameters are learned with three-stage Bayesian optimisation (Optuna TPE) whose loss is the synchronisation objective: how well the independently solved pairwise matchings can be made cycle consistent (stage 1 linear covariances, stage 2 sparsity with a multi-objective trade-off against problem size, stage 3 offset covariances). Worms are re-aligned (affine, least squares from matchings) to a target worm before and after learning. The pool is matched pairwise (Fusion Moves) and synchronised densely into cliques (GREEDA); nucleus-specific Gaussian statistics of the cliques form the atlas, with cost weights derived from the learned covariances. New worms are re-aligned and matched to the atlas.

## Main Claims

Primary: an unsupervised atlas reaches near-supervised annotation accuracy (0.961 vs 0.964). Secondary: learned covariances, quadratic offset costs, the synchronisation loss and explicit atlas construction each help over simpler variants.

## In this gym

`method/cycle_mgm.py` (training) and `method/annotate.py` (per-worm annotation) implement this pipeline with the authors' solver library (pylibmgm), scaled to 12 pool worms, 6 learning worms and 30/30/10 BO trials.
