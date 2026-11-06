# Cycle-Consistent Multi-Graph Matching for Self-Supervised Annotation of C.Elegans

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2503.07348"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2503.07348-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| | |
|---|---|
| **Paper ID** | [2503.07348](https://arxiv.org/abs/2503.07348) |
| **Domain** | Biomedical computer vision / graph matching |
| **TL;DR** | The paper builds a C. elegans cell atlas without semantic labels by learning Gaussian graph-matching costs from cycle consistency across segmented worms. |

## Summary

The task is to assign consistent biological names to hundreds of nuclei in 3D worm microscopy images. The paper models worms as graphs of nuclei and learns the parameters of a Gaussian graph-matching objective without semantic labels, using cycle consistency across multiple worms as the self-supervised signal. The resulting cliques form an unsupervised statistical atlas that can be matched to new worms. On the full benchmark, the unsupervised atlas is reported within 0.003 accuracy of the paper's supervised atlas.

## Problem

How can cell nuclei in 3D C. elegans microscopy images be assigned consistent biological identities across animals when manual semantic annotations are scarce or unavailable?

## The paper's method

The paper introduces a fully unsupervised atlas-learning pipeline for C. elegans nuclei based on cycle-consistent multi-graph matching. It replaces manually annotated semantic cell labels with cycle-consistent cliques across worms, then builds a statistical atlas from those cliques.

## Key results of the paper

- Main manual-segmentation result: unsupervised atlas 0.961 +/- 0.020 vs supervised atlas 0.964 +/- 0.019.
- Pipeline ablation: full pipeline atlas accuracy 0.972 +/- 0.015 on training-set ablations vs 0.955 +/- 0.031 for linear dense.
- Robustness result with automatic StarDist segmentations: full unsupervised pipeline 0.809 +/- 0.147 atlas accuracy.

## Leaderboard

FNI of AI scientists on this paper, grader-verified. 0 matches the paper's method, higher is better.

| Model | Innovate |
|---|---:|
| `gpt-5.6-sol-xhigh` | +46.3 |
| `gpt-5.6-terra-xhigh` | -53.3 |

`innovate`: the model designs its own method. `improve`: it starts from the paper's method.

## Run it

```bash
pip install git+https://github.com/zlab-princeton/scientist_world_cli
sw research 2503.07348 --mode innovate --agent claude-code
sw evaluate 2503.07348
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

