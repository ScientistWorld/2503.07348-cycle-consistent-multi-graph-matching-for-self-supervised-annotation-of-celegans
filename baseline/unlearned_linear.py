from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from data.cellmatch_data import Worm, limit_cells_by_input_order, load_split


def linear_cost(a: Worm, b: Worm) -> np.ndarray:
    cen = np.sum((a.centroids[:, None, :] - b.centroids[None, :, :]) ** 2, axis=-1)
    rad = np.sum((a.radii[:, None, :] - b.radii[None, :, :]) ** 2, axis=-1)
    return cen + rad


def solve_assignment(cost: np.ndarray) -> list[int]:
    row, col = linear_sum_assignment(cost)
    out = [-1] * cost.shape[0]
    for i, j in zip(row, col):
        out[int(i)] = int(j)
    return out


def invert(labeling: list[int], n: int) -> list[int]:
    inv = [-1] * n
    for i, j in enumerate(labeling):
        if j >= 0:
            inv[j] = i
    return inv


def get_mapping(pairs: dict[str, list[int]], i: int, j: int, n: int) -> list[int]:
    if i == j:
        return list(range(n))
    if i < j:
        return pairs[f"{i}-{j}"]
    return invert(pairs[f"{j}-{i}"], n)


def all_pairwise(worms: list[Worm]) -> dict[str, list[int]]:
    pairs = {}
    for i, j in combinations(range(len(worms)), 2):
        pairs[f"{i}-{j}"] = solve_assignment(linear_cost(worms[i], worms[j]))
    return pairs


def synchronization_agreement(cliques: list[dict[int, int]], pairs: dict[str, list[int]], n: int) -> int:
    score = 0
    for clique in cliques:
        for i, j in combinations(sorted(clique), 2):
            score += int(get_mapping(pairs, i, j, n)[clique[i]] == clique[j])
    return score


def synchronize_cliques(worms: list[Worm], pairs: dict[str, list[int]]) -> list[dict[int, int]]:
    n = len(worms[0].names)
    best_score = -1
    best_cliques = []
    for pivot in range(len(worms)):
        cliques = []
        for cell in range(n):
            clique = {pivot: cell}
            for other in range(len(worms)):
                if other == pivot:
                    continue
                mapped = get_mapping(pairs, pivot, other, n)[cell]
                if mapped >= 0:
                    clique[other] = mapped
            cliques.append(clique)
        score = synchronization_agreement(cliques, pairs, n)
        if score > best_score:
            best_score = score
            best_cliques = cliques
    return best_cliques


def induce_labels(cliques: list[dict[int, int]], worms: list[Worm]) -> list[str]:
    candidates = []
    for cidx, clique in enumerate(cliques):
        counts: dict[str, int] = {}
        for wid, nid in clique.items():
            label = worms[wid].names[nid]
            counts[label] = counts.get(label, 0) + 1
        for label, count in counts.items():
            candidates.append((count, cidx, label))
    candidates.sort(reverse=True)
    assigned_cliques: set[int] = set()
    used_labels: set[str] = set()
    labels = [f"UNASSIGNED_{i}" for i in range(len(cliques))]
    for _, cidx, label in candidates:
        if cidx in assigned_cliques or label in used_labels:
            continue
        labels[cidx] = label
        assigned_cliques.add(cidx)
        used_labels.add(label)
    return labels


def build_atlas(cliques: list[dict[int, int]], worms: list[Worm], labels: list[str]) -> Worm:
    centroids = []
    radii = []
    for clique in cliques:
        centroids.append(np.mean([worms[wid].centroids[nid] for wid, nid in clique.items()], axis=0))
        radii.append(np.mean([worms[wid].radii[nid] for wid, nid in clique.items()], axis=0))
    return Worm("unlearned_linear_atlas", labels, np.asarray(centroids), np.asarray(radii))


def match_atlas(atlas: Worm, targets: list[Worm]) -> list[list[int]]:
    return [solve_assignment(linear_cost(atlas, target)) for target in targets]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="outputs/baseline/predictions.json")
    parser.add_argument("--train-dir", default="data/cellmatch_sample/train")
    parser.add_argument("--test-dir", default="data/cellmatch_sample/test")
    parser.add_argument("--train-worms", type=int, default=12)
    parser.add_argument("--test-worms", type=int, default=6)
    parser.add_argument("--cells", type=int, default=0, help="0 means use all cells; positive values are label-free smoke subsets")
    args = parser.parse_args()
    train = load_split(args.train_dir, args.train_worms)
    test = load_split(args.test_dir, args.test_worms)
    train = limit_cells_by_input_order(train, args.cells)
    test = limit_cells_by_input_order(test, args.cells)
    pairs = all_pairwise(train)
    cliques = synchronize_cliques(train, pairs)
    atlas = build_atlas(cliques, train, induce_labels(cliques, train))
    output = {
        "metadata": {
            "train_worms": len(train),
            "test_worms": len(test),
            "cells": min(len(w.names) for w in train + test),
            "semantic_labels_used_for_training": False,
            "baseline": "unlearned_linear",
        },
        "experiments": {
            "scaled_manual_segmentation": {
                "test_labels": [w.names for w in test],
                "train_labels": [w.names for w in train],
                "methods": {
                    "unlearned_linear_baseline": {
                        "atlas_labels": atlas.names,
                        "test_labelings": match_atlas(atlas, test),
                    },
                },
            }
        },
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
