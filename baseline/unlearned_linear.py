"""Unlearned linear baseline (no parameter learning, no pairwise terms).

Same pipeline skeleton as the reproduction but with the unlearned model used
by the paper's ablations: identity covariances and unit weights
(Sigma^{cen,rad} = I, lambda = 1), dense linear worm-to-worm assignment, dense
synchronisation into cliques, a Gaussian atlas of the cliques and linear
worm-to-atlas assignment. It keeps the paper's label-free first re-alignment
(unlearned dense linear, 7 iterations), which needs no learning; new worms are
re-aligned the same way by its annotate.sh before linear atlas assignment.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from data import gmtools as gm
from data.worms import load_group
from method.cycle_mgm import (C0_LEARN, PAPER_ITERATIONS, build_unsupervised_atlas, load_worms, log,
                              pairwise_all, realign, save_worms, star_center, write_annotator)


def run(args: argparse.Namespace) -> None:
    t_start = time.time()
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    raw = {"pool": load_group("pool")}
    pre_path = work / "prealign.npz"
    if args.reuse and not pre_path.exists() and (Path(args.reuse) / "prealign.npz").exists():
        for name in ("prealign.npz", "prealign.json"):
            shutil.copyfile(Path(args.reuse) / name, work / name)
    params = gm.WormParams(c0=C0_LEARN)  # identity covariances, dense, unit weights
    if pre_path.exists():
        groups = load_worms(pre_path, raw)
        target_idx = json.loads(pre_path.with_suffix(".json").read_text())["target"]
    else:
        target_idx = star_center(raw["pool"], seed=args.seed)
        target = raw["pool"][target_idx]
        others = [w for w in raw["pool"] if w.worm_id != target.worm_id]
        aligned = iter(realign(others, target, params, False, args.realign_iterations, args.seed, "unlearned"))
        groups = {"pool": [w if w.worm_id == target.worm_id else next(aligned) for w in raw["pool"]]}
        save_worms(pre_path, groups, {"target": target_idx})

    pool = groups["pool"]
    sizes = [w.n for w in pool]
    pre = pairwise_all(pool, params, quadratic=False, seed=args.seed)
    sync = gm.synchronize(pre, sizes, iterations=3)
    membership = gm.cliques_to_membership(sync.cliques(), sizes)
    atlas = build_unsupervised_atlas(pool, membership, (1.0, 1.0, 1.0))
    log(f"baseline atlas: {atlas.size} labels")
    target_raw = raw["pool"][target_idx]
    model = {
        "format": "cellid-annotator-v1",
        "seed": args.seed,
        "target_centroids": target_raw.centroids.tolist(),
        "target_radii": target_raw.radii.tolist(),
        "realign": [{"params": params.to_dict(), "quadratic": False, "iterations": args.realign_iterations}],
        "atlas": {"pool_centroids": [w.centroids.tolist() for w in pool],
                  "pool_radii": [w.radii.tolist() for w in pool],
                  "membership": [m.tolist() for m in membership],
                  "weights": [1.0, 1.0, 1.0], "shrinkage": 0.0},
        "match": {"quadratic": False, "nbr_var": list(params.cen_var), "nbr_k": params.neighbor_count},
    }
    out_dir = Path(args.output).parent
    write_annotator(out_dir, model)
    output = {
        "format": "cellid-atlas-v2",
        "pool_cliques": {w.worm_id: m.tolist() for w, m in zip(pool, membership)},
        "info": {"method": "unlearned linear baseline", "seed": args.seed,
                 "atlas_labels": atlas.size, "seconds": time.time() - t_start},
    }
    Path(args.output).write_text(json.dumps(output))
    log(f"wrote {out_dir} ({time.time() - t_start:.0f}s)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default="outputs/_comparators/unlearned_linear_baseline/predictions.json")
    parser.add_argument("--work", default="checkpoints/unlearned_linear_baseline")
    parser.add_argument("--reuse", default=None, help="work dir with a first re-alignment to reuse")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--realign-iterations", type=int, default=PAPER_ITERATIONS)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
