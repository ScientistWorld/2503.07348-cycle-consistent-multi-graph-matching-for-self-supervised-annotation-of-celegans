"""Cycle-consistent multi-graph matching for self-supervised C. elegans atlases.

Reproduction of Karg, Stricker et al. (arXiv:2503.07348) on the benchmark's
anonymized worms. Pipeline (paper Sec. 3 and Appendix B):

1. Pre-processing / re-alignment target (Sec. 3.4): all pool worms are matched
   pairwise with dense, unlearned linear costs (identity covariances), the
   matchings are synchronised densely, and the worm whose matchings change least
   becomes the re-alignment target.
2. First re-alignment: 7 iterations of unlearned dense linear worm-to-target
   matching + affine least squares, applied to every worm (pool and held-out).
3. Bayesian optimisation of the 12 cross-nucleus Gaussian parameters on
   ``N_learn`` pool worms, with the synchronisation loss (objective of the dense
   GREEDA synchronisation of the independently solved pairwise problems):
     stage 1  diagonal centroid / radius covariances, dense linear assignment;
     stage 2  sparsity (K_min, tau_cen, tau_rad), multi-objective TPE against the
              mean number of allowed assignments, Pareto selection rule of App. B;
     stage 3  diagonal offset covariance, sparse quadratic GM (Fusion Moves).
4. Second re-alignment: 7 iterations with the fully learned sparse quadratic
   model, applied to every worm.
5. Multi-graph matching of the pool: all pairwise GM problems with the learned
   model (c0 = 40) solved with Fusion Moves, then dense synchronisation into
   cycle-consistent cliques.
6. Unsupervised atlas: nucleus-specific Gaussian statistics of the cliques, cost
   weights lambda = ||diag(Sigma)|| normalised to length sqrt(3) (Sec. 3.3).
7. Worm-to-atlas GM (Fusion Moves) for every held-out worm.

No semantic label is read anywhere. The output artifact holds the clique id of
every pool nucleus and the atlas label (clique id) of every held-out nucleus;
the evaluators attach biological names afterwards (paper Sec. 3.3).
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
import time
from itertools import combinations
from pathlib import Path

import numpy as np

from data import gmtools as gm
from data.worms import load_group

try:
    import optuna
except ImportError:  # pragma: no cover
    optuna = None

PAPER_ITERATIONS = 7
C0_LEARN = 10000.0  # App. B: c0 for cost learning and atlas matching
C0_MGM = 40.0  # App. B: c0 for the MGM after cost learning


def log(message: str) -> None:
    print(f"[cycle-mgm {time.strftime('%H:%M:%S')}] {message}", flush=True)


# --------------------------------------------------------------------------
# Multi-graph helpers
# --------------------------------------------------------------------------


def pairwise_all(worms, params: gm.WormParams, quadratic: bool, seed: int) -> dict:
    out = {}
    for k, (a, b) in enumerate(combinations(range(len(worms)), 2)):
        out[(a, b)] = gm.match_worms(worms[a], worms[b], params, quadratic, seed=seed * 1009 + k)
    return out


def sync_objective(worms, labelings: dict, iterations: int = 3) -> float:
    sizes = [w.n for w in worms]
    return float(gm.synchronize(labelings, sizes, iterations=iterations).evaluate())


def star_center(worms, seed: int) -> int:
    """Worm whose dense unlearned matchings change least under dense synchronisation."""
    params = gm.WormParams(c0=C0_LEARN)
    pre = pairwise_all(worms, params, quadratic=False, seed=seed)
    sync = gm.synchronize(pre, [w.n for w in worms], iterations=1,
                          opt_level=gm.OptimizationLevel.FAST)
    post = gm.sync_labelings(sync)
    changes = np.zeros(len(worms))
    for (a, b), lab in pre.items():
        diff = int(np.sum(np.asarray(lab) != post[(a, b)]))
        changes[a] += diff
        changes[b] += diff
    log(f"re-alignment target search: changed matchings per worm {changes.astype(int).tolist()}")
    return int(np.argmin(changes))


def realign(worms: list, target, params: gm.WormParams, quadratic: bool, iterations: int,
            seed: int, label: str) -> list:
    """Repeated worm-to-target matching + affine least squares (Sec. 3.4)."""
    cen_prec = 1.0 / np.asarray(params.cen_var, dtype=float)
    off_prec = 1.0 / np.asarray(params.off_var, dtype=float)
    worms = list(worms)
    for it in range(iterations):
        t0 = time.time()
        shift = []
        for k, w in enumerate(worms):
            lab = gm.match_worms(target, w, params, quadratic, seed=seed * 7919 + it * 131 + k)
            idx = np.nonzero(lab >= 0)[0]
            r, o = gm.affine_fit_diag(target.centroids[idx], w.centroids[lab[idx]], cen_prec, off_prec)
            new = gm.apply_affine(w.centroids, r, o)
            shift.append(float(np.sqrt(((new - w.centroids) ** 2).sum(1)).mean()))
            worms[k] = w.with_centroids(new)
        log(f"{label} re-alignment {it + 1}/{iterations}: mean shift {np.mean(shift):.3f} "
            f"({time.time() - t0:.0f}s)")
    return worms


# --------------------------------------------------------------------------
# Bayesian optimisation (Sec. 3.2)
# --------------------------------------------------------------------------


def _sampler(seed: int, trials: int, multi: bool = False):
    startup = max(2, min(10, trials // 3))
    return optuna.samplers.TPESampler(seed=seed, n_startup_trials=startup)


def learn_parameters(worms, trials: tuple[int, int, int], seed: int, max_avg_assignments: float,
                     loss_tolerance: float, stages=(1, 2, 3), start: gm.WormParams | None = None,
                     history: dict | None = None) -> tuple[gm.WormParams, dict]:
    if optuna is None:
        raise RuntimeError("optuna is required for the paper's Bayesian optimisation")
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    params = copy.deepcopy(start) if start is not None else gm.WormParams(c0=C0_LEARN)
    history = history if history is not None else {}

    if 1 in stages:
        t0 = time.time()

        def objective1(trial):
            p = copy.deepcopy(params)
            p.cen_var = tuple(float(trial.suggest_int(f"cen_{a}", 1, 200)) for a in "xyz")
            p.rad_var = tuple(float(trial.suggest_int(f"rad_{a}", 1, 200)) for a in "xyz")
            p.k_min = 0
            loss = sync_objective(worms, pairwise_all(worms, p, quadratic=False, seed=seed))
            log(f"BO stage 1 trial {trial.number + 1}/{trials[0]}: loss {loss:.0f} "
                f"cen {p.cen_var} rad {p.rad_var}")
            return loss

        study = optuna.create_study(direction="minimize", sampler=_sampler(seed + 1, trials[0]))
        study.optimize(objective1, n_trials=trials[0])
        best = study.best_params
        params.cen_var = tuple(float(best[f"cen_{a}"]) for a in "xyz")
        params.rad_var = tuple(float(best[f"rad_{a}"]) for a in "xyz")
        history["stage1"] = {"best_loss": study.best_value, "params": params.to_dict(),
                             "seconds": time.time() - t0,
                             "losses": [t.value for t in study.trials]}
        log(f"BO stage 1 done: {params.cen_var} {params.rad_var} loss {study.best_value:.0f}")

    if 2 in stages:
        t0 = time.time()
        norm_cen = float(np.linalg.norm(1.0 / np.asarray(params.cen_var)))
        norm_rad = float(np.linalg.norm(1.0 / np.asarray(params.rad_var)))

        def stage2_params(values) -> gm.WormParams:
            p = copy.deepcopy(params)
            p.k_min = int(values["k_min"])
            p.tau_cen = float(values["tau_cen"]) * norm_cen
            p.tau_rad = float(values["tau_rad"]) * norm_rad
            return p

        def objective2(trial):
            values = {
                "k_min": trial.suggest_int("k_min", 7, 20),
                "tau_cen": trial.suggest_int("tau_cen", 1, 300),
                "tau_rad": trial.suggest_int("tau_rad", 1, 100),
            }
            p = stage2_params(values)
            loss = sync_objective(worms, pairwise_all(worms, p, quadratic=False, seed=seed))
            sizes = [gm.allowed_assignments(worms[a], worms[b], p)
                     for a, b in combinations(range(len(worms)), 2)]
            mean_assign = float(np.mean(sizes))
            log(f"BO stage 2 trial {trial.number + 1}/{trials[1]}: loss {loss:.0f} "
                f"allowed {mean_assign:.0f} {values}")
            return loss, mean_assign

        study = optuna.create_study(directions=["minimize", "minimize"],
                                    sampler=_sampler(seed + 2, trials[1], multi=True))
        study.optimize(objective2, n_trials=trials[1])
        front = [t for t in study.best_trials if t.values[1] < max_avg_assignments]
        if not front:
            front = [t for t in study.trials if t.values is not None]
            front = [min(front, key=lambda t: t.values[1])]
        min_loss = min(t.values[0] for t in front)
        boundary = math.ceil(min_loss + abs(min_loss * loss_tolerance))
        chosen = min((t for t in front if t.values[0] <= boundary), key=lambda t: t.values[1])
        params = stage2_params(chosen.params)
        history["stage2"] = {"chosen": chosen.params, "values": list(chosen.values),
                             "params": params.to_dict(), "seconds": time.time() - t0,
                             "pareto": [list(t.values) for t in study.best_trials]}
        log(f"BO stage 2 done: k_min {params.k_min} tau_cen {params.tau_cen:.3f} "
            f"tau_rad {params.tau_rad:.3f} values {chosen.values}")

    if 3 in stages:
        t0 = time.time()

        def objective3(trial):
            p = copy.deepcopy(params)
            p.off_var = tuple(float(trial.suggest_int(f"off_{a}", 1, 200)) for a in "xyz")
            loss = sync_objective(worms, pairwise_all(worms, p, quadratic=True, seed=seed))
            log(f"BO stage 3 trial {trial.number + 1}/{trials[2]}: loss {loss:.0f} off {p.off_var}")
            return loss

        study = optuna.create_study(direction="minimize", sampler=_sampler(seed + 3, trials[2]))
        study.optimize(objective3, n_trials=trials[2])
        best = study.best_params
        params.off_var = tuple(float(best[f"off_{a}"]) for a in "xyz")
        history["stage3"] = {"best_loss": study.best_value, "params": params.to_dict(),
                             "seconds": time.time() - t0,
                             "losses": [t.value for t in study.trials]}
        log(f"BO stage 3 done: off {params.off_var} loss {study.best_value:.0f}")
    return params, history


# --------------------------------------------------------------------------
# Atlas construction and annotation
# --------------------------------------------------------------------------


def atlas_weights(params: gm.WormParams, ablate: tuple[float, float, float]) -> tuple:
    lam = np.array([np.linalg.norm(params.cen_var), np.linalg.norm(params.rad_var),
                    np.linalg.norm(params.off_var)], dtype=float)
    lam *= math.sqrt(3.0) / np.linalg.norm(lam)
    return tuple(float(v) for v in lam * np.asarray(ablate, dtype=float))


def membership_arrays(pool, membership: list[np.ndarray]):
    n_groups = int(max((m.max() for m in membership), default=-1)) + 1
    n = len(pool)
    x = np.zeros((n, n_groups, 3))
    r = np.zeros((n, n_groups, 3))
    member = np.zeros((n, n_groups), dtype=bool)
    for w, (worm, mem) in enumerate(zip(pool, membership)):
        nodes = np.nonzero(mem >= 0)[0]
        x[w, mem[nodes]] = worm.centroids[nodes]
        r[w, mem[nodes]] = worm.radii[nodes]
        member[w, mem[nodes]] = True
    return x, r, member, np.arange(n_groups)


def build_unsupervised_atlas(pool, membership, weights, shrinkage: float = 0.0) -> gm.Atlas:
    x, r, member, ids = membership_arrays(pool, membership)
    return gm.build_atlas(x, r, member, ids, weights=weights, shrinkage=shrinkage,
                          c0=C0_LEARN, k_min=11, tau_cen=16.0, tau_rad=25.0)


def annotate(atlas: gm.Atlas, worms, params: gm.WormParams, quadratic: bool, seed: int) -> dict:
    out = {}
    for k, w in enumerate(worms):
        lab = gm.match_atlas(atlas, w, target_nbr_var=params.cen_var,
                             target_nbr_k=params.neighbor_count, quadratic=quadratic,
                             seed=seed * 104729 + k)
        out[w.worm_id] = gm.node_labels(atlas, lab, w.n)
    return out


# --------------------------------------------------------------------------
# Checkpoint helpers
# --------------------------------------------------------------------------


def save_worms(path: Path, groups: dict, extra: dict | None = None) -> None:
    arrays = {f"{g}/{w.worm_id}": w.centroids for g, ws in groups.items() for w in ws}
    np.savez(path, **arrays)
    if extra is not None:
        path.with_suffix(".json").write_text(json.dumps(extra, indent=2))


def load_worms(path: Path, groups: dict) -> dict:
    data = np.load(path)
    return {g: [w.with_centroids(data[f"{g}/{w.worm_id}"]) for w in ws] for g, ws in groups.items()}


# --------------------------------------------------------------------------
# Main pipeline
# --------------------------------------------------------------------------


def run(args: argparse.Namespace) -> None:
    t_start = time.time()
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    reuse = Path(args.reuse) if args.reuse else None
    if reuse is not None:
        patterns = {"prealign": ["prealign.npz", "prealign.json"], "bo": ["bo.json"],
                    "postalign": ["postalign.npz"], "mgm": ["mgm_*.json"]}
        for stage in [s for s in args.reuse_stages.split(",") if s]:
            for pattern in patterns[stage]:
                for src_file in reuse.glob(pattern):
                    dst = work / src_file.name
                    if not dst.exists():
                        shutil.copyfile(src_file, dst)
                        log(f"reusing {src_file}")
    raw = {g: load_group(g) for g in ("pool", "dev", "test")}
    log(f"loaded {len(raw['pool'])} pool, {len(raw['dev'])} dev, {len(raw['test'])} test worms "
        f"({raw['pool'][0].n} nuclei each)")
    trials = tuple(int(v) for v in args.trials.split(","))
    quadratic = args.mode in ("full", "unlearned_quadratic")
    ablate = tuple(float(v) for v in args.lambda_scale.split(","))

    # 1-2. Re-alignment target and first (unlearned, dense linear) re-alignment.
    pre_path = work / "prealign.npz"
    if pre_path.exists():
        groups = load_worms(pre_path, raw)
        target_idx = json.loads(pre_path.with_suffix(".json").read_text())["target"]
        log("loaded first re-alignment")
    else:
        target_idx = star_center(raw["pool"], seed=args.seed)
        target = raw["pool"][target_idx]
        log(f"re-alignment target: pool worm {target.worm_id}")
        others = [(g, w) for g in raw for w in raw[g] if not (g == "pool" and w.worm_id == target.worm_id)]
        aligned = realign([w for _, w in others], target, gm.WormParams(c0=C0_LEARN), False,
                          args.realign_iterations, args.seed, "unlearned")
        groups = {g: [] for g in raw}
        it = iter(aligned)
        for g in raw:
            for w in raw[g]:
                groups[g].append(w if (g == "pool" and w.worm_id == target.worm_id) else next(it))
        save_worms(pre_path, groups, {"target": target_idx})
    target_id = raw["pool"][target_idx].worm_id

    # 3. Bayesian optimisation of the cross-nucleus parameters.
    bo_path = work / "bo.json"
    learn_worms = groups["pool"][: args.learn_worms]
    if args.mode == "unlearned_quadratic":
        reuse_bo = json.loads((reuse / "bo.json").read_text()) if reuse and (reuse / "bo.json").exists() else None
        params = gm.WormParams(c0=C0_LEARN)
        if reuse_bo is not None:  # Tab. 1: "as sparse as linear sparse"
            sparse = gm.WormParams.from_dict(reuse_bo["history"]["stage2"]["params"])
            params.k_min, params.tau_cen, params.tau_rad = sparse.k_min, sparse.tau_cen, sparse.tau_rad
        else:
            params.k_min = 14
        history = {"unlearned": params.to_dict()}
    elif bo_path.exists():
        saved = json.loads(bo_path.read_text())
        params, history = gm.WormParams.from_dict(saved["params"]), saved["history"]
        log("loaded learned parameters")
    else:
        stages = (1, 2, 3) if args.mode == "full" else (1, 2)
        params, history = learn_parameters(learn_worms, trials, args.seed, args.max_avg_assignments,
                                           args.loss_tolerance, stages=stages)
        history["trials"] = list(trials)
        bo_path.write_text(json.dumps({"params": params.to_dict(), "history": history}, indent=2))
    log(f"parameters: {params.to_dict()}")

    # 4. Second re-alignment with the learned model.
    post_path = work / "postalign.npz"
    if post_path.exists():
        groups = load_worms(post_path, groups)
        log("loaded second re-alignment")
    elif args.second_realign:
        target = groups["pool"][target_idx]
        others = [(g, w) for g in groups for w in groups[g] if not (g == "pool" and w.worm_id == target_id)]
        aligned = realign([w for _, w in others], target, params, quadratic, args.realign_iterations,
                          args.seed + 1, "learned")
        it = iter(aligned)
        groups = {g: [w if (g == "pool" and w.worm_id == target_id) else next(it) for w in groups[g]]
                  for g in groups}
        save_worms(post_path, groups)

    # 5. Multi-graph matching of the pool -> cycle-consistent cliques.
    mgm_params = copy.deepcopy(params)
    mgm_params.c0 = C0_MGM
    mgm_params.w_cen, mgm_params.w_rad, mgm_params.w_off = ablate
    mgm_path = work / f"mgm_{args.lambda_scale.replace(',', '_')}.json"
    pool = groups["pool"]
    sizes = [w.n for w in pool]
    if mgm_path.exists():
        membership = [np.asarray(m, dtype=int) for m in json.loads(mgm_path.read_text())["membership"]]
        log("loaded multi-graph matching")
    else:
        t0 = time.time()
        pre = pairwise_all(pool, mgm_params, quadratic, seed=args.seed + 2)
        log(f"solved {len(pre)} pairwise pool problems ({time.time() - t0:.0f}s)")
        sync = gm.synchronize(pre, sizes, iterations=3)
        membership = gm.cliques_to_membership(sync.cliques(), sizes)
        mgm_path.write_text(json.dumps({"membership": [m.tolist() for m in membership],
                                        "sync_objective": float(sync.evaluate())}))
        log(f"synchronised into {len(sync.cliques())} cliques ({time.time() - t0:.0f}s)")

    # 6. Unsupervised atlas (optionally refined by re-matching the pool to it).
    weights = atlas_weights(params, ablate)
    atlas = build_unsupervised_atlas(pool, membership, weights, shrinkage=args.atlas_shrinkage)
    log(f"atlas: {atlas.size} labels, weights {weights}")
    for refine in range(args.atlas_refine):
        labels = annotate(atlas, pool, params, quadratic, seed=args.seed + 10 + refine)
        membership = [labels[w.worm_id] for w in pool]
        atlas = build_unsupervised_atlas(pool, membership, weights, shrinkage=args.atlas_shrinkage)
        log(f"atlas refinement {refine + 1}: {atlas.size} labels")

    # 7. Annotate every held-out worm by worm-to-atlas matching.
    t0 = time.time()
    labelings = annotate(atlas, groups["dev"] + groups["test"], params, quadratic, seed=args.seed + 3)
    log(f"annotated {len(labelings)} held-out worms ({time.time() - t0:.0f}s)")

    output = {
        "format": "cellid-atlas-v1",
        "pool_cliques": {w.worm_id: m.tolist() for w, m in zip(pool, membership)},
        "labelings": {k: v.tolist() for k, v in labelings.items()},
        "info": {
            "method": "cycle-consistent MGM + BO (synchronisation loss) unsupervised atlas",
            "mode": args.mode,
            "seed": args.seed,
            "learn_worms": args.learn_worms,
            "trials": list(trials),
            "params": params.to_dict(),
            "atlas_weights": list(weights),
            "atlas_labels": atlas.size,
            "atlas_shrinkage": args.atlas_shrinkage,
            "atlas_refine": args.atlas_refine,
            "realignment_target": target_id,
            "seconds": time.time() - t_start,
        },
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(output))
    log(f"wrote {args.output} ({time.time() - t_start:.0f}s total)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default="outputs/our_unsupervised_atlas/predictions.json")
    parser.add_argument("--work", default="checkpoints/our_unsupervised_atlas")
    parser.add_argument("--reuse", default=None, help="work dir whose checkpoints may be reused")
    parser.add_argument("--reuse-stages", default="prealign,bo",
                        help="comma list of prealign,bo,postalign,mgm checkpoints to copy from --reuse")
    parser.add_argument("--mode", choices=["full", "linear", "unlearned_quadratic"], default="full")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--learn-worms", type=int, default=8)
    parser.add_argument("--trials", default="40,40,12", help="BO trials for stages 1,2,3")
    parser.add_argument("--max-avg-assignments", type=float, default=12000.0)
    parser.add_argument("--loss-tolerance", type=float, default=0.0005)
    parser.add_argument("--lambda-scale", default="1,1,1",
                        help="multiply (lambda_cen, lambda_rad, lambda_off); App. C ablations")
    parser.add_argument("--no-second-realign", dest="second_realign", action="store_false")
    parser.add_argument("--realign-iterations", type=int, default=PAPER_ITERATIONS,
                        help="re-alignment iterations per round (paper: 7; lower only for smoke tests)")
    parser.add_argument("--atlas-shrinkage", type=float, default=0.0)
    parser.add_argument("--atlas-refine", type=int, default=0)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
