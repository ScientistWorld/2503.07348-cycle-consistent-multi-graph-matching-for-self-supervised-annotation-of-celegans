"""Hidden-test scorer for the cell-identity benchmark.

    python eval/test/evaluate_slice.py [--output scoring/scores_test.json]

Scores every method directory under outputs/ (each holding predictions.json),
plus the fixed comparators frozen in eval/test/fixed/. The ranked entry
``our_unsupervised_atlas`` is always emitted; a missing, unreadable or invalid
artifact scores the worst value of every metric. Only raw assignments are
read: every number is recomputed here from the hidden labels in keys.json.

Scoring (paper Sec. 3.3 / 4):
  * the method's pool cliques are named by greedy maximum voting over the
    hidden names of the pool nuclei (largest name count first, each clique and
    each name used once); unnamed cliques count as wrong;
  * atlas accuracy of a held-out worm = fraction of its nuclei whose assigned
    atlas label (clique id) carries the nucleus' true name; unassigned nuclei
    count as wrong; denominator = all nuclei of the worm;
  * pre-atlas accuracy (diagnostic) = the same fraction on the pool itself.
Validity (hard constraint, otherwise the run fails): every pool and test worm
present, one integer >= -1 per nucleus, no atlas label / clique used twice
within a worm.
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
EXPERIMENT = "scaled_manual_segmentation"
CANONICAL = "our_unsupervised_atlas"
ORACLE = "supervised_oracle_atlas"
WORST = {
    "atlas_accuracy_mean": 0.0,
    "atlas_accuracy_min": 0.0,
    "atlas_accuracy_std": 0.5,
    "pre_atlas_accuracy_mean": 0.0,
}
MAX_BYTES = 50_000_000


def load_keys() -> tuple[dict, dict]:
    keys = json.loads((HERE / "keys.json").read_text())
    return keys["pool"], keys["test"]


def check_assignment(values, n: int, where: str) -> list[int]:
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


def greedy_names(cliques: dict, names: dict) -> dict:
    counts: Counter = Counter()
    for wid, members in cliques.items():
        worm_names = names[wid]
        for node, cid in enumerate(members):
            if cid >= 0:
                counts[(cid, worm_names[node])] += 1
    assigned: dict = {}
    used: set = set()
    for (cid, name), _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1])):
        if cid in assigned or name in used:
            continue
        assigned[cid] = name
        used.add(name)
    return assigned


def accuracy(labels: list[int], truth: list[str], names: dict) -> float:
    correct = sum(1 for node, lab in enumerate(labels) if lab >= 0 and names.get(lab) == truth[node])
    return correct / len(truth)


def score(pred, pool_names: dict, test_names: dict) -> tuple[dict, dict]:
    if not isinstance(pred, dict):
        raise ValueError("predictions must be a JSON object")
    pool_cliques = pred.get("pool_cliques")
    labelings = pred.get("labelings")
    if not isinstance(pool_cliques, dict) or not isinstance(labelings, dict):
        raise ValueError("predictions need 'pool_cliques' and 'labelings' objects")
    cliques = {w: check_assignment(pool_cliques.get(w), len(n), f"pool_cliques[{w}]")
               for w, n in pool_names.items()}
    labels = {w: check_assignment(labelings.get(w), len(n), f"labelings[{w}]")
              for w, n in test_names.items()}
    names = greedy_names(cliques, pool_names)
    acc = {w: accuracy(labels[w], test_names[w], names) for w in sorted(test_names)}
    pre = [accuracy(cliques[w], pool_names[w], names) for w in sorted(pool_names)]
    values = list(acc.values())
    mean = sum(values) / len(values)
    metrics = {
        "atlas_accuracy_mean": mean,
        "atlas_accuracy_min": min(values),
        "atlas_accuracy_std": math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)),
        "pre_atlas_accuracy_mean": sum(pre) / len(pre),
    }
    return metrics, acc


def load_json(path: Path):
    if not path.is_file():
        raise ValueError(f"{path.relative_to(ROOT)} not found")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError(f"{path.relative_to(ROOT)} is larger than {MAX_BYTES} bytes")
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "scoring" / "scores_test.json"))
    args = parser.parse_args()
    pool_names, test_names = load_keys()

    fixed = {p.stem: p for p in sorted(FIXED.glob("*.json"))}
    submitted = {}
    if OUTPUTS.is_dir():
        for d in sorted(OUTPUTS.iterdir()):
            if d.is_dir() and not d.name.startswith(("_", ".")):
                submitted[d.name] = d / "predictions.json"
    submitted.setdefault(CANONICAL, OUTPUTS / CANONICAL / "predictions.json")
    shadowed = sorted(n for n in submitted if n in fixed)

    results: dict = {}
    per_worm: dict = {}
    failures: dict = {}
    for name, path in list(fixed.items()) + [(n, p) for n, p in submitted.items() if n not in fixed]:
        try:
            metrics, acc = score(load_json(path), pool_names, test_names)
            per_worm[name] = acc
        except Exception as exc:  # any failure scores worst values
            metrics = dict(WORST)
            failures[name] = f"{type(exc).__name__}: {exc}"
        results[name] = metrics

    oracle_mean = results.get(ORACLE, {}).get("atlas_accuracy_mean")
    if ORACLE in failures or oracle_mean is None:
        raise SystemExit("fixed supervised comparator missing or invalid: eval/test/fixed is incomplete")
    for name, metrics in results.items():
        if name != ORACLE:
            metrics["gap_to_supervised_oracle"] = oracle_mean - metrics["atlas_accuracy_mean"]

    out = {
        "_metadata": {
            "slice": "test",
            "target_worms": sorted(test_names),
            "fixed_comparators": sorted(fixed),
            "submitted_methods": sorted(n for n in submitted if n not in fixed),
            "ignored_reserved_names": shadowed,
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
        print(f"eval/test: {exc}", file=sys.stderr)
        raise
