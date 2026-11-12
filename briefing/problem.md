# Problem Definition

## Research Question

How can the nuclei of a 3D C. elegans microscopy image be assigned their biological identities (one of 558 unique cell names) when no semantic annotation is available to build the identity reference?

## Why It Matters

Cell-level identity maps let biologists compare gene expression and morphology across individual worms in a common reference frame. Expert annotation of every nucleus is slow and error-prone; a label-free way to obtain the identity reference removes a key bottleneck for organism-scale studies.

## Setting

- Every worm is given as a table of segmented nuclei (centroid and three ellipsoid radii, already rigidly aligned along the body axes). Row order carries no identity information.
- 12 unlabeled pool worms are available to build an identity reference. No semantic name of any pool nucleus is available, and none may be obtained from outside the benchmark.
- New worms must then be annotated one at a time by the system's own procedure: every nucleus receives a reference identity (or none), with no two nuclei of a worm sharing an identity.

## Success Criteria

High per-nucleus identity accuracy on held-out worms, on every worm rather than only on average, achieved without semantic labels.
