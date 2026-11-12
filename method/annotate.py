"""Annotate one new worm with a trained unsupervised atlas.

    python -m method.annotate --model <dir>/model.json <worm.txt> <labels.json>

Same per-worm steps the paper applies to test worms (Sec. 3.4): re-align the
worm to the re-alignment target worm, first with the unlearned dense linear
model and then with the learned sparse quadratic model (7 iterations each), then
solve the worm-to-atlas graph-matching problem (Fusion Moves). Writes one atlas
label (clique id of the training pool) or -1 per input row.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from data import gmtools as gm
from data.worms import WormFeatures, load_worm


def load_atlas(model: dict) -> gm.Atlas:
    spec = model["atlas"]
    pool = [WormFeatures(f"pool{k}", np.asarray(c, dtype=float), np.asarray(r, dtype=float))
            for k, (c, r) in enumerate(zip(spec["pool_centroids"], spec["pool_radii"]))]
    membership = [np.asarray(m, dtype=int) for m in spec["membership"]]
    n_groups = int(max(m.max() for m in membership)) + 1
    x = np.zeros((len(pool), n_groups, 3))
    r = np.zeros_like(x)
    member = np.zeros((len(pool), n_groups), dtype=bool)
    for w, (worm, mem) in enumerate(zip(pool, membership)):
        nodes = np.nonzero(mem >= 0)[0]
        x[w, mem[nodes]] = worm.centroids[nodes]
        r[w, mem[nodes]] = worm.radii[nodes]
        member[w, mem[nodes]] = True
    return gm.build_atlas(x, r, member, np.arange(n_groups), weights=tuple(spec["weights"]),
                          shrinkage=float(spec.get("shrinkage", 0.0)), c0=10000.0, k_min=11,
                          tau_cen=16.0, tau_rad=25.0)


def annotate_worm(model: dict, worm: WormFeatures, atlas: gm.Atlas | None = None) -> np.ndarray:
    seed = int(model.get("seed", 7))
    target = WormFeatures("target", np.asarray(model["target_centroids"], dtype=float),
                          np.asarray(model["target_radii"], dtype=float))
    cur = worm
    for stage, spec in enumerate(model["realign"]):
        params = gm.WormParams.from_dict(spec["params"])
        cen_prec = 1.0 / np.asarray(params.cen_var, dtype=float)
        off_prec = 1.0 / np.asarray(params.off_var, dtype=float)
        for it in range(int(spec["iterations"])):
            lab = gm.match_worms(target, cur, params, bool(spec["quadratic"]),
                                 seed=seed * 7919 + stage * 1000 + it)
            idx = np.nonzero(lab >= 0)[0]
            r, o = gm.affine_fit_diag(target.centroids[idx], cur.centroids[lab[idx]], cen_prec, off_prec)
            cur = cur.with_centroids(gm.apply_affine(cur.centroids, r, o))
    if atlas is None:
        atlas = load_atlas(model)
    match = model["match"]
    lab = gm.match_atlas(atlas, cur, target_nbr_var=tuple(match["nbr_var"]), target_nbr_k=int(match["nbr_k"]),
                         quadratic=bool(match["quadratic"]), seed=seed * 104729)
    return gm.node_labels(atlas, lab, worm.n)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True)
    parser.add_argument("worm")
    parser.add_argument("output")
    args = parser.parse_args()
    model = json.loads(Path(args.model).read_text())
    labels = annotate_worm(model, load_worm(args.worm))
    Path(args.output).write_text(json.dumps([int(v) for v in labels]))


if __name__ == "__main__":
    main()
