"""Hidden-test scorer for the cell-identity benchmark.

    python eval/test/evaluate_slice.py [--output scoring/scores_test.json]

Scores every method directory under outputs/ plus the fixed comparators frozen
in eval/test/fixed/. The ranked entry ``our_unsupervised_atlas`` is always
emitted. A method directory must hold
  predictions.json  {"pool_cliques": {pool_worm_id: [clique id or -1 per row]}}
  annotate.sh       annotate.sh <worm.txt> <labels.json>: writes one atlas label
                    (pool clique id) or -1 per row of ONE worm table
The 10 hidden test worms (eval/test/worms/, never visible to a submission) are
handed to annotate.sh one per call, each within TIMEOUT seconds. Any missing
file, crash, timeout or invalid output fails the run, which then scores the
worst value of every metric. Every number is recomputed here from the raw
assignments and the hidden names in keys.json.

Scoring (paper Sec. 3.3 / 4):
  * the method's pool cliques are named by greedy maximum voting over the
    hidden names of the pool nuclei (largest name count first, each clique and
    each name used once); unnamed cliques count as wrong;
  * atlas accuracy of a test worm = fraction of its nuclei whose atlas label
    carries the nucleus' true name; unassigned nuclei count as wrong;
    denominator = all nuclei of the worm;
  * pre-atlas accuracy (diagnostic) = the same fraction on the pool itself.
Validity: every pool worm present, one integer >= -1 per nucleus, no clique /
atlas label used twice within a worm.
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
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUTS = ROOT / "outputs"
FIXED = HERE / "fixed"
WORMS = HERE / "worms"
EXPERIMENT = "scaled_manual_segmentation"
CANONICAL = "our_unsupervised_atlas"
ORACLE = "supervised_oracle_atlas"
TIMEOUT = 900  # seconds per worm and call
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


def score(cliques: dict, labels: dict, pool_names: dict, test_names: dict) -> tuple[dict, dict]:
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


def read_cliques(pred, pool_names: dict) -> dict:
    if not isinstance(pred, dict) or not isinstance(pred.get("pool_cliques"), dict):
        raise ValueError("predictions.json needs a 'pool_cliques' object")
    return {w: check_assignment(pred["pool_cliques"].get(w), len(n), f"pool_cliques[{w}]")
            for w, n in pool_names.items()}


def run_annotator(method_dir: Path, worm: str, n_rows: int) -> list[int]:
    script = method_dir / "annotate.sh"
    if not script.is_file():
        raise ValueError(f"{script.relative_to(ROOT)} not found")
    with tempfile.TemporaryDirectory(prefix="cellid_") as tmp:
        inp, out = Path(tmp) / "worm.txt", Path(tmp) / "labels.json"
        shutil.copyfile(WORMS / f"{worm}.txt", inp)
        try:
            proc = subprocess.run(["bash", str(script), str(inp), str(out)], cwd=ROOT, capture_output=True,
                                  text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            raise ValueError(f"annotate.sh exceeded {TIMEOUT}s on a test worm")
        if proc.returncode != 0:
            raise ValueError(f"annotate.sh exited {proc.returncode}: {proc.stderr[-500:]}")
        if not out.is_file() or out.stat().st_size > MAX_BYTES:
            raise ValueError("annotate.sh wrote no (or an oversized) labels file")
        labels = json.loads(out.read_text())
    return check_assignment(labels, n_rows, "annotate.sh output")


def workers() -> int:
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except AttributeError:  # pragma: no cover
        return max(1, os.cpu_count() or 1)


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
                submitted[d.name] = d
    submitted.setdefault(CANONICAL, OUTPUTS / CANONICAL)
    shadowed = sorted(n for n in submitted if n in fixed)
    submitted = {n: d for n, d in submitted.items() if n not in fixed}

    results: dict = {}
    per_worm: dict = {}
    failures: dict = {}
    seconds: dict = {}

    for name, path in fixed.items():  # frozen comparators: stored assignments
        try:
            pred = load_json(path)
            cliques = read_cliques(pred, pool_names)
            labels = {w: check_assignment(pred["labelings"].get(w), len(n), f"labelings[{w}]")
                      for w, n in test_names.items()}
            results[name], per_worm[name] = score(cliques, labels, pool_names, test_names)
        except Exception as exc:
            failures[name] = f"{type(exc).__name__}: {exc}"

    cliques_of = {}
    for name, d in submitted.items():
        try:
            cliques_of[name] = read_cliques(load_json(d / "predictions.json"), pool_names)
        except Exception as exc:
            failures[name] = f"{type(exc).__name__}: {exc}"
    tasks = [(name, w) for name in cliques_of for w in sorted(test_names)]

    def task(item):
        name, worm = item
        t0 = time.time()
        try:
            return name, worm, run_annotator(submitted[name], worm, len(test_names[worm])), None, time.time() - t0
        except Exception as exc:
            return name, worm, None, f"{type(exc).__name__}: {exc}", time.time() - t0

    labels_of: dict = {name: {} for name in cliques_of}
    with ThreadPoolExecutor(max_workers=workers()) as pool:
        for name, worm, labels, error, dt in pool.map(task, tasks):
            seconds[name] = seconds.get(name, 0.0) + dt
            if error is not None:
                failures.setdefault(name, f"{worm}: {error}")
            else:
                labels_of[name][worm] = labels
    for name in submitted:
        if name in failures:
            results[name] = dict(WORST)
            continue
        results[name], per_worm[name] = score(cliques_of[name], labels_of[name], pool_names, test_names)

    if ORACLE not in results or ORACLE in failures:
        raise SystemExit("fixed supervised comparator missing or invalid: eval/test/fixed is incomplete")
    oracle_mean = results[ORACLE]["atlas_accuracy_mean"]
    for name, metrics in results.items():
        if name != ORACLE:
            metrics["gap_to_supervised_oracle"] = oracle_mean - metrics["atlas_accuracy_mean"]

    out = {
        "_metadata": {
            "slice": "test",
            "target_worms": sorted(test_names),
            "fixed_comparators": sorted(fixed),
            "submitted_methods": sorted(submitted),
            "ignored_reserved_names": shadowed,
            "failures": failures,
            "annotation_seconds": seconds,
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
