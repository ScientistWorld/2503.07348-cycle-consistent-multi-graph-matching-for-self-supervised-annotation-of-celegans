"""Visible (train-side) scorer for the cell-identity benchmark.

    python eval/train/evaluate_slice.py [--output scoring/scores_train.json]

Scores the dev worms (data/worms/dev) of every method directory under
outputs/ (each holding predictions.json) plus the fixed comparators in
eval/train/fixed/. The entry ``our_unsupervised_atlas`` is always emitted; a
missing, unreadable or invalid artifact scores the worst value of every metric.

Because the pool's names are not available on this side, atlas labels are
named leave-one-out: to score dev worm d, every atlas label is named by greedy
maximum voting over the true names of the nuclei it was assigned to in the
other three dev worms (largest count first, each label and each name used
once). Atlas accuracy of d = fraction of its nuclei whose label carries their
true name; unassigned nuclei count as wrong. The hidden test instead names the
atlas labels from the pool cliques, so a method whose held-out labels are
consistent with each other but not with its own pool cliques scores higher
here than on the hidden test. The dev labels are for scoring only: using them to build,
tune or select a method breaks the benchmark's label-free constraint.

Validity (otherwise the run fails): every pool worm and dev worm present, one
integer >= -1 per nucleus, no label / clique used twice within a worm.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUTS = ROOT / "outputs"
FIXED = HERE / "fixed"
POOL_DIR = ROOT / "data" / "worms" / "pool"
EXPERIMENT = "scaled_manual_segmentation"
CANONICAL = "our_unsupervised_atlas"
ORACLE = "supervised_oracle_atlas"
WORST = {"atlas_accuracy_mean": 0.0, "atlas_accuracy_min": 0.0, "atlas_accuracy_std": 0.5}
MAX_BYTES = 50_000_000


def pool_sizes() -> dict:
    return {p.stem: sum(1 for line in p.read_text().splitlines() if line.strip())
            for p in sorted(POOL_DIR.glob("*.txt"))}


def validate(values, n: int, where: str) -> list[int]:
    if not isinstance(values, list):
        raise ValueError(f"{where}: expected a list of {n} integers")
    if len(values) != n:
        raise ValueError(f"{where}: expected {n} entries, got {len(values)}")
    seen = set()
    for v in values:
        if isinstance(v, bool) or not isinstance(v, int) or v < -1:
            raise ValueError(f"{where}: entries must be integers >= -1 (got {v!r})")
        if v >= 0:
            if v in seen:
                raise ValueError(f"{where}: label {v} used for more than one nucleus")
            seen.add(v)
    return values


def greedy_names(labels: dict, dev: dict) -> dict:
    """Name atlas labels by greedy maximum voting over the given dev worms."""
    votes: Counter = Counter()
    for w, lab in labels.items():
        for node, k in enumerate(lab):
            if k >= 0:
                votes[(k, dev[w][node])] += 1
    names: dict = {}
    used: set = set()
    for (k, name), _ in sorted(votes.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1])):
        if k not in names and name not in used:
            names[k] = name
            used.add(name)
    return names


def dev_scores(pred, dev: dict, sizes: dict | None) -> tuple[dict, dict]:
    if not isinstance(pred, dict) or not isinstance(pred.get("labelings"), dict):
        raise ValueError("predictions need a 'labelings' object")
    if sizes is not None:
        cliques = pred.get("pool_cliques")
        if not isinstance(cliques, dict):
            raise ValueError("predictions need a 'pool_cliques' object")
        for wid, n in sizes.items():
            validate(cliques.get(wid), n, f"pool_cliques[{wid}]")
    labels = {w: validate(pred["labelings"].get(w), len(t), f"labelings[{w}]") for w, t in dev.items()}
    acc = {}
    for scored in sorted(labels):
        names = greedy_names({w: lab for w, lab in labels.items() if w != scored}, dev)
        lab = labels[scored]
        acc[scored] = sum(1 for node, k in enumerate(lab) if k >= 0 and names.get(k) == dev[scored][node]) / len(lab)
    values = list(acc.values())
    mean = sum(values) / len(values)
    return {
        "atlas_accuracy_mean": mean,
        "atlas_accuracy_min": min(values),
        "atlas_accuracy_std": math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)),
    }, acc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "scoring" / "scores_train.json"))
    args = parser.parse_args()
    dev = json.loads((HERE / "dev_labels.json").read_text())["dev"]
    sizes = pool_sizes()
    fixed = {p.stem: p for p in sorted(FIXED.glob("*.json"))}
    submitted = {}
    if OUTPUTS.is_dir():
        for d in sorted(OUTPUTS.iterdir()):
            if d.is_dir() and not d.name.startswith(("_", ".")):
                submitted[d.name] = d / "predictions.json"
    submitted.setdefault(CANONICAL, OUTPUTS / CANONICAL / "predictions.json")

    results, per_worm, failures = {}, {}, {}
    entries = [(n, p, None) for n, p in fixed.items()]
    entries += [(n, p, sizes) for n, p in submitted.items() if n not in fixed]
    for name, path, check_sizes in entries:
        try:
            if not path.is_file():
                raise ValueError(f"{path.relative_to(ROOT)} not found")
            if path.stat().st_size > MAX_BYTES:
                raise ValueError("predictions file too large")
            metrics, acc = dev_scores(json.loads(path.read_text()), dev, check_sizes)
            per_worm[name] = acc
        except Exception as exc:
            metrics = dict(WORST)
            failures[name] = f"{type(exc).__name__}: {exc}"
        results[name] = metrics
    if ORACLE not in results or ORACLE in failures:
        raise SystemExit("fixed supervised comparator missing or invalid: eval/train/fixed is incomplete")
    oracle_mean = results[ORACLE]["atlas_accuracy_mean"]
    for name, metrics in results.items():
        if name != ORACLE:
            metrics["gap_to_supervised_oracle"] = oracle_mean - metrics["atlas_accuracy_mean"]
    out = {
        "_metadata": {
            "slice": "train",
            "target_worms": sorted(dev),
            "naming": "leave-one-out greedy maximum voting over the other dev worms",
            "fixed_comparators": sorted(fixed),
            "submitted_methods": sorted(n for n in submitted if n not in fixed),
            "failures": failures,
            "per_worm_accuracy": per_worm,
        },
        "experiments": {EXPERIMENT: {"results": results}},
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2))
    print(json.dumps({"failures": failures, "results": results}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"eval/train: {exc}", file=sys.stderr)
        raise
