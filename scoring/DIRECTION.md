# Research Direction

## Research Problem
This benchmark is about unsupervised semantic identity assignment for stereotyped biological structures. The goal is to build an atlas from segmented C. elegans nuclei and use it to annotate held-out worms without relying on manual semantic labels during atlas construction.

## Research Scope
Improvements should remain within unsupervised or weakly supervised identity-reference construction for segmented worm nuclei. Work should still produce identity assignments for the same cell-identity task, rather than changing the biological input, adding extra labeled data, or redefining the target labels.

## Approach Scope
A scientist may modify the representation, correspondence model, optimization strategy, reference-estimation procedure, or uncertainty handling, provided the output remains a reusable cell-identity assignment system for the same segmented nuclei problem.

## Out of Bounds
Using semantic labels to train the unsupervised atlas is out of bounds. Replacing the problem with a supervised classifier, a memorized label lookup, or a model trained end-to-end on ground-truth identities sidesteps the paper's claim. Switching to extra biological measurements or external labeled worms for the default benchmark is also out of bounds.
