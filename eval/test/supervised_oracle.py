"""Fixed supervised comparator (paper Appendix E), generated once on the hidden side.

Uses the hidden names of the pool worms, so it lives in eval/test/. Pipeline:
  1. choose the base worm whose ground-truth affine alignment of all other pool
     worms leaves the smallest mean centroid residual;
  2. align every pool worm to it with ground-truth correspondences (affine least
     squares on centroids);
  3. build the supervised Gaussian atlas (nucleus-specific centroid / radius
     covariances, pair-specific offset covariances) from the aligned pool;
  4. held-out worms: apply the average pool alignment transform, then 7 rounds of
     worm-to-atlas matching + atlas-weighted affine re-alignment;
  5. final worm-to-atlas graph matching with the paper's tuned supervised weights
     lambda = (0.48, 0.34, 0.81).
The result is installed as a fixed comparator via install_comparator.py, so
evaluation never reruns it.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from data import gmtools as gm
from data.worms import load_group

HERE = Path(__file__).resolve().parent
SUPERVISED_WEIGHTS = (0.48, 0.34, 0.81)
ITERATIONS = 7


def log(message: str) -> None:
    print(f"[supervised-oracle {time.strftime('%H:%M:%S')}] {message}", flush=True)


def annotate_task(task):
    """Iterative worm-to-atlas matching + re-alignment, then the final matching."""
    atlas, cur, seed, iterations = task
    for it in range(iterations):
        lab = gm.match_atlas(atlas, cur, quadratic=True, seed=seed + it)
        cur, _ = gm.realign_to_atlas(atlas, cur, lab)
    return gm.match_atlas(atlas, cur, quadratic=True, seed=seed + iterations)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="outputs/_comparators/supervised_oracle_atlas/predictions.json")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--iterations", type=int, default=ITERATIONS)
    args = parser.parse_args()
    t_start = time.time()
    keys = json.loads((HERE / "keys.json").read_text())
    raw = {g: load_group(g) for g in ("pool", "dev", "test")}
    pool = raw["pool"]
    names = [keys["pool"][w.worm_id] for w in pool]
    vocab = sorted(set().union(*map(set, names)))
    index = {name: k for k, name in enumerate(vocab)}
    pos = np.full((len(pool), len(vocab)), -1, dtype=int)
    for w, worm_names in enumerate(names):
        for node, name in enumerate(worm_names):
            pos[w, index[name]] = node

    def gt_fit(src: int, dst: int):
        common = np.nonzero((pos[src] >= 0) & (pos[dst] >= 0))[0]
        x = pool[dst].centroids[pos[dst, common]]
        y = pool[src].centroids[pos[src, common]]
        r, o = gm.affine_fit_diag(x, y, (1.0, 1.0, 1.0))
        resid = np.sqrt(((gm.apply_affine(y, r, o) - x) ** 2).sum(1)).mean()
        return r, o, resid

    scores = []
    for b in range(len(pool)):
        scores.append(np.mean([gt_fit(w, b)[2] for w in range(len(pool)) if w != b]))
    base = int(np.argmin(scores))
    log(f"base worm {pool[base].worm_id} (mean residual {scores[base]:.3f})")

    transforms = []
    aligned = []
    for w in range(len(pool)):
        if w == base:
            aligned.append(pool[w])
            continue
        r, o, _ = gt_fit(w, base)
        transforms.append((r, o))
        aligned.append(pool[w].with_centroids(gm.apply_affine(pool[w].centroids, r, o)))
    x = np.zeros((len(pool), len(vocab), 3))
    rad = np.zeros_like(x)
    member = pos >= 0
    for w, worm in enumerate(aligned):
        ok = pos[w] >= 0
        x[w, ok] = worm.centroids[pos[w, ok]]
        rad[w, ok] = worm.radii[pos[w, ok]]
    atlas = gm.build_atlas(x, rad, member, np.arange(len(vocab)), weights=SUPERVISED_WEIGHTS,
                           c0=10000.0, k_min=11, tau_cen=16.0, tau_rad=25.0)
    log(f"supervised atlas: {atlas.size} labels")

    r_mean = np.mean([t[0] for t in transforms], axis=0)
    o_mean = np.mean([t[1] for t in transforms], axis=0)
    held = raw["dev"] + raw["test"]
    tasks = [(atlas, w.with_centroids(gm.apply_affine(w.centroids, r_mean, o_mean)), args.seed * 31 + k * 7,
              args.iterations) for k, w in enumerate(held)]
    labs = gm.parallel_map(annotate_task, tasks)
    labelings = {w.worm_id: gm.node_labels(atlas, lab, w.n).tolist() for w, lab in zip(held, labs)}
    log(f"annotated {len(held)} held-out worms")
    output = {
        "format": "cellid-atlas-v1",
        "pool_cliques": {w.worm_id: [index[n] for n in names[i]] for i, w in enumerate(pool)},
        "labelings": labelings,
        "info": {"method": "supervised Gaussian atlas (fixed comparator)", "base": pool[base].worm_id,
                 "weights": list(SUPERVISED_WEIGHTS), "atlas_labels": atlas.size,
                 "seconds": time.time() - t_start},
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(output))
    log(f"wrote {args.output} ({time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()
