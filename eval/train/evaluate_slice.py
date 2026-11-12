"""Visible (train-side) scorer for the cell-identity benchmark.

    python eval/train/evaluate_slice.py [--output scoring/scores_train.json]

Scores every method directory under outputs/ on the 4 dev worms
(data/worms/dev), plus the fixed comparators in eval/train/fixed/. The entry
``our_unsupervised_atlas`` is always emitted. A method directory must hold
  predictions.json  {"pool_cliques": {pool_worm_id: [clique id or -1 per row]}}
  annotate.sh       annotate.sh <worm.txt> <labels.json>: writes one atlas label
                    or -1 per row of ONE worm table
annotate.sh is called once per dev worm (within TIMEOUT seconds) exactly as the
hidden test calls it on the hidden worms. Any missing file, crash, timeout or
invalid output fails the run, which then scores the worst value of every metric.

Only a fixed random 10 % of the identities carry a visible dev label (the
others are null); accuracy is measured on those labeled nuclei, an unbiased
sample of the per-nucleus accuracy. Because the pool's names are not available
on this side, atlas labels are named leave-one-out: to score dev worm d, every
atlas label is named by greedy maximum voting over the true names of the
labeled nuclei it was assigned to in the other three dev worms (largest count
first, each label and each name used once). Atlas accuracy of d = fraction of
its labeled nuclei whose label carries their true name; unassigned nuclei count
as wrong. The hidden test names atlas labels from the pool cliques of all 12
pool worms instead, so it is less noisy and typically a few points higher.

The dev labels are for scoring only: building, tuning or selecting a method
with them breaks the benchmark's label-free constraint. Fixed comparators whose
raw labels would hand out supervision are stored as frozen scores
(``frozen_metrics``), computed once with ``--freeze``.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUTS = ROOT / "outputs"
FIXED = HERE / "fixed"
POOL_DIR = ROOT / "data" / "worms" / "pool"
DEV_DIR = ROOT / "data" / "worms" / "dev"
EXPERIMENT = "scaled_manual_segmentation"
CANONICAL = "our_unsupervised_atlas"
ORACLE = "supervised_oracle_atlas"
TIMEOUT = 900
WORST = {"atlas_accuracy_mean": 0.0, "atlas_accuracy_min": 0.0, "atlas_accuracy_std": 0.5}
MAX_BYTES = 50_000_000


def row_count(path: Path) -> int:
    return sum(1 for line in path.read_text().splitlines() if line.strip())


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
            if k >= 0 and dev[w][node] is not None:
                votes[(k, dev[w][node])] += 1
    names: dict = {}
    used: set = set()
    for (k, name), _ in sorted(votes.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1])):
        if k not in names and name not in used:
            names[k] = name
            used.add(name)
    return names


def dev_scores(labels: dict, dev: dict) -> tuple[dict, dict]:
    acc = {}
    for scored in sorted(labels):
        names = greedy_names({w: lab for w, lab in labels.items() if w != scored}, dev)
        lab, truth = labels[scored], dev[scored]
        labeled = [node for node, name in enumerate(truth) if name is not None]
        acc[scored] = sum(1 for node in labeled if lab[node] >= 0 and names.get(lab[node]) == truth[node]) / len(labeled)
    values = list(acc.values())
    mean = sum(values) / len(values)
    return {
        "atlas_accuracy_mean": mean,
        "atlas_accuracy_min": min(values),
        "atlas_accuracy_std": math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)),
    }, acc


def run_annotator(method_dir: Path, worm: str, n_rows: int) -> list[int]:
    script = method_dir / "annotate.sh"
    if not script.is_file():
        raise ValueError(f"{script.relative_to(ROOT)} not found")
    with tempfile.TemporaryDirectory(prefix="cellid_") as tmp:
        inp, out = Path(tmp) / "worm.txt", Path(tmp) / "labels.json"
        shutil.copyfile(DEV_DIR / f"{worm}.txt", inp)
        try:
            proc = subprocess.run(["bash", str(script), str(inp), str(out)], cwd=ROOT, capture_output=True,
                                  text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            raise ValueError(f"annotate.sh exceeded {TIMEOUT}s on a dev worm")
        if proc.returncode != 0:
            raise ValueError(f"annotate.sh exited {proc.returncode}: {proc.stderr[-500:]}")
        if not out.is_file() or out.stat().st_size > MAX_BYTES:
            raise ValueError("annotate.sh wrote no (or an oversized) labels file")
        labels = json.loads(out.read_text())
    return validate(labels, n_rows, "annotate.sh output")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "scoring" / "scores_train.json"))
    parser.add_argument("--freeze", nargs=2, metavar=("NAME", "LABELINGS"),
                        help="score a comparator's dev labelings once and store only the numbers in fixed/NAME.json")
    args = parser.parse_args()
    dev = json.loads((HERE / "dev_labels.json").read_text())["dev"]
    if args.freeze:
        name, src = args.freeze
        content = json.loads(Path(src).read_text())
        labels = {w: validate(content["labelings"].get(w), len(t), f"labelings[{w}]") for w, t in dev.items()}
        metrics, acc = dev_scores(labels, dev)
        FIXED.mkdir(parents=True, exist_ok=True)
        (FIXED / f"{name}.json").write_text(json.dumps({"frozen_metrics": metrics, "per_worm": acc}, indent=2))
        print(f"froze {name}: {metrics}")
        return
    pool_sizes = {p.stem: row_count(p) for p in sorted(POOL_DIR.glob("*.txt"))}
    fixed = {p.stem: p for p in sorted(FIXED.glob("*.json"))}
    submitted = {}
    if OUTPUTS.is_dir():
        for d in sorted(OUTPUTS.iterdir()):
            if d.is_dir() and not d.name.startswith(("_", ".")):
                submitted[d.name] = d
    submitted.setdefault(CANONICAL, OUTPUTS / CANONICAL)
    submitted = {n: d for n, d in submitted.items() if n not in fixed}

    results, per_worm, failures = {}, {}, {}
    for name, path in fixed.items():
        try:
            content = json.loads(path.read_text())
            results[name], per_worm[name] = dict(content["frozen_metrics"]), content.get("per_worm", {})
        except Exception as exc:
            failures[name] = f"{type(exc).__name__}: {exc}"

    ok = []
    for name, d in submitted.items():
        try:
            path = d / "predictions.json"
            if not path.is_file():
                raise ValueError(f"{path.relative_to(ROOT)} not found")
            if path.stat().st_size > MAX_BYTES:
                raise ValueError("predictions.json too large")
            pred = json.loads(path.read_text())
            if not isinstance(pred, dict) or not isinstance(pred.get("pool_cliques"), dict):
                raise ValueError("predictions.json needs a 'pool_cliques' object")
            for wid, n in pool_sizes.items():
                validate(pred["pool_cliques"].get(wid), n, f"pool_cliques[{wid}]")
            ok.append(name)
        except Exception as exc:
            failures[name] = f"{type(exc).__name__}: {exc}"

    def task(item):
        name, worm = item
        try:
            return name, worm, run_annotator(submitted[name], worm, len(dev[worm])), None
        except Exception as exc:
            return name, worm, None, f"{type(exc).__name__}: {exc}"

    try:
        n_workers = max(1, len(os.sched_getaffinity(0)))
    except AttributeError:  # pragma: no cover
        n_workers = max(1, os.cpu_count() or 1)
    labels_of = {name: {} for name in ok}
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        for name, worm, labels, error in executor.map(task, [(n, w) for n in ok for w in sorted(dev)]):
            if error is not None:
                failures.setdefault(name, f"{worm}: {error}")
            else:
                labels_of[name][worm] = labels
    for name in submitted:
        if name in failures:
            results[name] = dict(WORST)
        else:
            results[name], per_worm[name] = dev_scores(labels_of[name], dev)

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
            "naming": "leave-one-out greedy maximum voting over the other dev worms (labeled identities only)",
            "fixed_comparators": sorted(fixed),
            "submitted_methods": sorted(submitted),
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
