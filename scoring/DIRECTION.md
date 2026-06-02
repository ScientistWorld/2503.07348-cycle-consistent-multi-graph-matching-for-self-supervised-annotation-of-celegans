# Research Direction

## Research Problem
This benchmark is about unsupervised semantic identity assignment for stereotyped biological structures. The goal is to build an atlas from segmented C. elegans nuclei and use it to annotate held-out worms without relying on manual semantic labels during atlas construction.

## Core Contribution
The paper's contribution is self-supervised, cycle-consistent multi-object matching with learned geometric matching costs. Improvements should remain in this family: correspondence learning, graph matching, multi-object synchronization, atlas construction, or self-supervised cost learning for the same cell-identity task.

## Approach Scope
A scientist may modify the cost parameterization, the self-supervised consistency objective, sparsification, synchronization, optimization strategy, or atlas-estimation procedure, provided the output remains an atlas and cell correspondence system for the same segmented nuclei problem.

## Out of Bounds
Using semantic labels to train the unsupervised atlas is out of bounds. Replacing the problem with a supervised classifier, a memorized label lookup, or a model trained end-to-end on ground-truth identities sidesteps the paper's claim. Switching to extra biological measurements or external labeled worms for the default benchmark is also out of bounds.
