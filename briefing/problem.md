# Problem Definition

## Research Question

How can cell nuclei in 3D C. elegans microscopy images be assigned consistent biological identities across animals when manual semantic annotations are scarce or unavailable?

## Why It Matters

Cell-level identity maps let biologists compare gene expression and morphology across individual worms in a common reference frame. Manual annotation is slow and expert-dependent, so a good automatic solution removes a major bottleneck for high-throughput organism-scale studies.

## Success Criteria

A successful system builds a reusable identity reference from segmented nuclei, assigns identities to held-out worms with high per-cell accuracy, remains close to an otherwise comparable supervised reference in accuracy, and does not use held-out labels during training or model selection.
