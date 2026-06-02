# Problem Definition

What problem does this paper address? Write this so that someone with no knowledge of the paper can understand what needs to be solved and how success is measured.

Do NOT describe the paper's method or solution here — only the problem itself. Think about if a future scientist agent try to solve this problem from scratch without knowing what approach the paper took. If you leak the solution, you compromise the benchmark.

## Research Question

How can cell nuclei in 3D C. elegans microscopy images be assigned consistent biological identities across animals when manual semantic annotations are scarce or unavailable?

## Why It Matters

Cell-level identity maps let biologists compare gene expression and morphology across individual worms in a common reference frame. Manual annotation is slow and expert-dependent, so a good automatic solution removes a major bottleneck for high-throughput organism-scale studies.

## Success Criteria

A successful system builds a reusable atlas from segmented nuclei, assigns atlas identities to target worms with high per-cell accuracy, remains close to a supervised atlas in accuracy, and does not use target-test labels during training or model selection.
