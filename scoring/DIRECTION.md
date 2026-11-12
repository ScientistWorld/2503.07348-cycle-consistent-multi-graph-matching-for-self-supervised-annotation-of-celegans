# Research Direction

## Research Problem
Label-free identity assignment for a stereotyped organism: build a reference of the 558 C. elegans nuclei from unlabeled segmented worms and use it to annotate new worms nucleus by nucleus.

## Research Scope
Improvements must keep the setting label-free and the output an identity assignment for the same nuclei: better correspondence finding across the pool, better reference statistics from few worms, better alignment of new worms, better matching of a new worm to the reference, uncertainty handling, or learning signals that need no names.

## Approach Scope
Any representation, objective, optimiser, solver or estimation procedure is allowed, as long as the reference is learned from the pool worms alone and each new worm is annotated independently by the submitted annotator.

## Out of Bounds
Using semantic names (beyond scoring with the visible dev labels), external labeled worms or atlases, the public source files of these worms, held-out worms as training data, or annotators that read evaluator files or share state across calls.
