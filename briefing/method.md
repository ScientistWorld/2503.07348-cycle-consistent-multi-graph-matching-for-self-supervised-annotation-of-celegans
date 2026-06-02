# Paper's Method

How the paper approaches the problem, i.e. the paper's core contributions.

## Key Contribution

The paper introduces a fully unsupervised atlas-learning pipeline for C. elegans nuclei based on cycle-consistent multi-graph matching. It replaces manually annotated semantic cell labels with cycle-consistent cliques across worms, then builds a statistical atlas from those cliques.

## Approach

Each worm is represented as a graph of segmented nuclei with 3D centroid and radii features. Pairwise worm-to-worm graph matching uses Gaussian/Mahalanobis unary costs for centroid and radii similarity plus quadratic costs for pairwise centroid offsets. The method learns diagonal Gaussian covariance and sparsity parameters through three-stage Bayesian optimization using a self-supervised cycle/synchronization loss over a subset of worms. After solving pairwise matches, a synchronization step produces cycle-consistent cliques. Clique labels are used only for evaluation; the atlas itself is built from the unlabeled clique geometry and then matched to target worms.

## Main Claims

Primary: an unsupervised atlas built from instance segmentations can reach near-supervised C. elegans cell-annotation accuracy. Secondary: the learned Gaussian parameters, quadratic offset costs, synchronization loss, and explicit atlas construction improve over simpler linear or unlearned variants.
