from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path

import numpy as np

from data.cellmatch_data import Worm, common_labels, load_split, restrict_to_common


try:
    from scipy.optimize import linear_sum_assignment
except Exception:  # pragma: no cover - used only when scipy is unavailable.
    linear_sum_assignment = None


@dataclass
class Params:
    cen_cov: tuple[float, float, float] = (130.0, 43.0, 28.0)
    rad_cov: tuple[float, float, float] = (156.0, 200.0, 174.0)
    off_cov: tuple[float, float, float] = (172.0, 32.0, 44.0)
    k_min: int = 14
    tau_cen: float = 1.95
    tau_rad: float = 0.15
    w_cen: float = 1.0
    w_rad: float = 1.0
    w_off: float = 1.0
    neighbor_count: int = 5
    quadratic_iters: int = 2


def log(message: str) -> None:
    print(f"[cycle-mgm] {message}", flush=True)


def mahalanobis(a: np.ndarray, b: np.ndarray, cov_diag: tuple[float, float, float]) -> np.ndarray:
    return np.sum(((a - b) ** 2) / np.asarray(cov_diag), axis=-1)


def solve_assignment(cost: np.ndarray) -> list[int]:
    if linear_sum_assignment is None:
        remaining = set(range(cost.shape[1]))
        out = [-1] * cost.shape[0]
        for i in np.argsort(cost.min(axis=1)):
            j = min(remaining, key=lambda c: cost[i, c])
            out[i] = int(j)
            remaining.remove(j)
        return out
    row, col = linear_sum_assignment(cost)
    out = [-1] * cost.shape[0]
    for i, j in zip(row, col):
        out[int(i)] = int(j)
    return out


def unary_cost(a: Worm, b: Worm, params: Params, sparse: bool) -> np.ndarray:
    cen = mahalanobis(a.centroids[:, None, :], b.centroids[None, :, :], params.cen_cov)
    rad = mahalanobis(a.radii[:, None, :], b.radii[None, :, :], params.rad_cov)
    cost = params.w_cen * cen + params.w_rad * rad
    if sparse:
        mask = (cen <= params.tau_cen) & (rad <= params.tau_rad)
        for i in range(cost.shape[0]):
            keep = np.argsort(cost[i])[: params.k_min]
            mask[i, keep] = True
        for j in range(cost.shape[1]):
            keep = np.argsort(cost[:, j])[: params.k_min]
            mask[keep, j] = True
        cost = np.where(mask, cost, 1e9)
    return cost


def nearest_neighbors(worm: Worm, k: int, params: Params) -> list[np.ndarray]:
    dist = mahalanobis(worm.centroids[:, None, :], worm.centroids[None, :, :], params.cen_cov)
    np.fill_diagonal(dist, np.inf)
    return [np.argsort(dist[i])[:k] for i in range(len(worm.names))]


def pairwise_match(a: Worm, b: Worm, params: Params, sparse: bool = True, quadratic: bool = True) -> list[int]:
    base = unary_cost(a, b, params, sparse=sparse)
    labeling = solve_assignment(base)
    if not quadratic:
        return labeling
    neigh = nearest_neighbors(a, params.neighbor_count, params)
    for _ in range(params.quadratic_iters):
        qcost = base.copy()
        for i in range(len(a.names)):
            for t in range(len(b.names)):
                acc = 0.0
                used = 0
                for j in neigh[i]:
                    matched = labeling[int(j)]
                    if matched < 0 or matched == t:
                        continue
                    off_a = a.centroids[i] - a.centroids[int(j)]
                    off_b = b.centroids[t] - b.centroids[matched]
                    acc += float(mahalanobis(off_a, off_b, params.off_cov))
                    used += 1
                if used:
                    qcost[i, t] += params.w_off * acc / used
        labeling = solve_assignment(qcost)
    return labeling


def invert(labeling: list[int], n: int) -> list[int]:
    inv = [-1] * n
    for i, j in enumerate(labeling):
        if j >= 0:
            inv[j] = i
    return inv


def all_pairwise(worms: list[Worm], params: Params, sparse: bool, quadratic: bool) -> dict[str, list[int]]:
    pairs: dict[str, list[int]] = {}
    for i, j in combinations(range(len(worms)), 2):
        pairs[f"{i}-{j}"] = pairwise_match(worms[i], worms[j], params, sparse=sparse, quadratic=quadratic)
    return pairs


def get_mapping(pairs: dict[str, list[int]], i: int, j: int, n: int) -> list[int]:
    if i == j:
        return list(range(n))
    if i < j:
        return pairs[f"{i}-{j}"]
    return invert(pairs[f"{j}-{i}"], n)


def cycle_loss(worms: list[Worm], pairs: dict[str, list[int]]) -> int:
    n = len(worms[0].names)
    loss = 0
    for a, b, c in combinations(range(len(worms)), 3):
        ab = get_mapping(pairs, a, b, n)
        ac = get_mapping(pairs, a, c, n)
        bc = get_mapping(pairs, b, c, n)
        for i in range(n):
            via = bc[ab[i]] if ab[i] >= 0 else -1
            if via != ac[i]:
                loss += 1
    return loss


def avg_allowed_assignments(worms: list[Worm], params: Params) -> float:
    vals = []
    for i, j in combinations(range(len(worms)), 2):
        vals.append(float(np.sum(unary_cost(worms[i], worms[j], params, sparse=True) < 1e8)))
    return float(np.mean(vals))


def random_params(base: Params, stage: int, rng: random.Random) -> Params:
    p = Params(**asdict(base))
    if stage == 1:
        p.cen_cov = tuple(rng.uniform(10, 220) for _ in range(3))
        p.rad_cov = tuple(rng.uniform(10, 220) for _ in range(3))
    elif stage == 2:
        p.k_min = rng.randint(4, 20)
        p.tau_cen = 10 ** rng.uniform(-1.0, 1.2)
        p.tau_rad = 10 ** rng.uniform(-1.3, 1.0)
    elif stage == 3:
        p.off_cov = tuple(rng.uniform(5, 220) for _ in range(3))
        p.w_off = rng.uniform(0.25, 2.0)
    return p


def learn_params(worms: list[Worm], trials: int, seed: int) -> Params:
    rng = random.Random(seed)
    params = Params()
    for stage in (1, 2, 3):
        log(f"learning stage {stage}/3 with {len(worms)} worms and {max(1, trials)} trials")
        best = None
        for trial in range(max(1, trials)):
            cand = random_params(params, stage, rng)
            pairs = all_pairwise(worms, cand, sparse=stage >= 2, quadratic=stage == 3)
            loss = cycle_loss(worms, pairs)
            sparsity = avg_allowed_assignments(worms, cand) if stage == 2 else 0.0
            objective = loss + (1e-4 * sparsity if stage == 2 else 0.0)
            if best is None or objective < best[0]:
                best = (objective, cand)
            log(f"stage {stage} trial {trial + 1}: objective={objective:.3f}")
        params = best[1]
    return params


def synchronize_cliques(worms: list[Worm], pairs: dict[str, list[int]]) -> list[dict[int, int]]:
    n = len(worms[0].names)
    scores = []
    for pivot in range(len(worms)):
        kept = 0
        for other in range(len(worms)):
            if other != pivot:
                kept += sum(x >= 0 for x in get_mapping(pairs, pivot, other, n))
        scores.append(kept)
    pivot = int(np.argmax(scores))
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
    return cliques


def induce_clique_labels(cliques: list[dict[int, int]], worms: list[Worm]) -> list[str]:
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
    return Worm("unsupervised_atlas", labels, np.asarray(centroids), np.asarray(radii))


def supervised_atlas(worms: list[Worm]) -> Worm:
    labels = worms[0].names
    centroids = []
    radii = []
    for label in labels:
        c = []
        r = []
        for worm in worms:
            idx = worm.names.index(label)
            c.append(worm.centroids[idx])
            r.append(worm.radii[idx])
        centroids.append(np.mean(c, axis=0))
        radii.append(np.mean(r, axis=0))
    return Worm("supervised_atlas", labels, np.asarray(centroids), np.asarray(radii))


def evaluate_pre_atlas(cliques: list[dict[int, int]], clique_labels: list[str], worms: list[Worm]) -> list[float]:
    acc = []
    for wid, worm in enumerate(worms):
        correct = total = 0
        for label, clique in zip(clique_labels, cliques):
            if wid not in clique:
                continue
            total += 1
            correct += int(worm.names[clique[wid]] == label)
        acc.append(correct / total if total else 0.0)
    return acc


def match_atlas(atlas: Worm, targets: list[Worm], params: Params, quadratic: bool) -> list[list[int]]:
    return [pairwise_match(atlas, target, params, sparse=False, quadratic=quadratic) for target in targets]


def run(args: argparse.Namespace) -> None:
    log("loading sample worms")
    train = load_split(args.train_dir, args.train_worms)
    test = load_split(args.test_dir, args.test_worms)
    labels = common_labels(train + test, args.cells)
    train = restrict_to_common(train, labels)
    test = restrict_to_common(test, labels)
    log(f"using {len(train)} train worms, {len(test)} test worms, {len(labels)} cells")

    learn_subset = train[: args.learn_worms]
    learned = learn_params(learn_subset, args.trials, args.seed)
    log("matching all training worms with learned cycle-consistent parameters")
    pairs = all_pairwise(train, learned, sparse=True, quadratic=True)
    log("synchronizing pairwise matches into atlas cliques")
    cliques = synchronize_cliques(train, pairs)
    clique_labels = induce_clique_labels(cliques, train)
    atlas = build_atlas(cliques, train, clique_labels)
    sup_atlas = supervised_atlas(train)

    unlearned = Params(cen_cov=(1, 1, 1), rad_cov=(1, 1, 1), off_cov=(1, 1, 1), tau_cen=1e9, tau_rad=1e9)
    log("building unlearned linear baseline atlas")
    baseline_pairs = all_pairwise(train, unlearned, sparse=False, quadratic=False)
    baseline_cliques = synchronize_cliques(train, baseline_pairs)
    baseline_atlas = build_atlas(
        baseline_cliques,
        train,
        induce_clique_labels(baseline_cliques, train),
    )

    log("matching atlases to held-out test worms")
    output = {
        "metadata": {
            "train_worms": len(train),
            "test_worms": len(test),
            "cells": len(labels),
            "semantic_labels_used_for_training": False,
            "params": asdict(learned),
        },
        "experiments": {
            "scaled_manual_segmentation": {
                "test_labels": [w.names for w in test],
                "train_labels": [w.names for w in train],
                "methods": {
                    "unlearned_linear_baseline": {
                        "atlas_labels": baseline_atlas.names,
                        "test_labelings": match_atlas(baseline_atlas, test, unlearned, quadratic=False),
                    },
                    "our_unsupervised_atlas": {
                        "atlas_labels": atlas.names,
                        "test_labelings": match_atlas(atlas, test, learned, quadratic=True),
                        "pre_atlas_accuracies": evaluate_pre_atlas(cliques, clique_labels, train),
                    },
                    "supervised_oracle_atlas": {
                        "atlas_labels": sup_atlas.names,
                        "test_labelings": match_atlas(sup_atlas, test, learned, quadratic=True),
                    },
                },
            }
        },
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(output, indent=2))
    log(f"wrote predictions to {args.output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-dir", default="data/cellmatch_sample/train")
    parser.add_argument("--test-dir", default="data/cellmatch_sample/test")
    parser.add_argument("--output", default="outputs/method/predictions.json")
    parser.add_argument("--train-worms", type=int, default=12)
    parser.add_argument("--learn-worms", type=int, default=6)
    parser.add_argument("--test-worms", type=int, default=6)
    parser.add_argument("--cells", type=int, default=160)
    parser.add_argument("--trials", type=int, default=6)
    parser.add_argument("--seed", type=int, default=7)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
