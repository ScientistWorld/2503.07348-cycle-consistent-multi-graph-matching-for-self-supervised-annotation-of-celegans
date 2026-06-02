from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np


SLICE = "test"
SPLIT_SEED = 250307348


def split_indices(count: int) -> list[int]:
    if count <= 1:
        return list(range(count))
    order = list(range(count))
    random.Random(SPLIT_SEED).shuffle(order)
    midpoint = max(1, count // 2)
    return sorted(order[midpoint:])


def worm_accuracy(atlas_labels: list[str], labels: list[str], labeling: list[Any]) -> float:
    correct = 0
    total = 0
    for atlas_idx, target_idx in enumerate(labeling):
        total += 1
        if target_idx is None:
            continue
        if not isinstance(target_idx, int):
            continue
        if target_idx < 0 or target_idx >= len(labels):
            continue
        if atlas_idx < len(atlas_labels) and atlas_labels[atlas_idx] == labels[target_idx]:
            correct += 1
    return correct / total if total else 0.0


def score_method(method: dict[str, Any], test_labels: list[list[str]], indices: list[int]) -> dict[str, float]:
    atlas_labels = method["atlas_labels"]
    labelings = method["test_labelings"]
    accuracies = [
        worm_accuracy(atlas_labels, test_labels[idx], labelings[idx])
        for idx in indices
    ]
    result = {
        "atlas_accuracy_mean": float(np.mean(accuracies)),
        "atlas_accuracy_std": float(np.std(accuracies)),
    }
    if "pre_atlas_accuracies" in method:
        vals = method["pre_atlas_accuracies"]
        result["pre_atlas_accuracy_mean"] = float(np.mean(vals))
        result["pre_atlas_accuracy_std"] = float(np.std(vals))
        result["atlas_minus_preatlas"] = result["atlas_accuracy_mean"] - result["pre_atlas_accuracy_mean"]
    return result


def validate_experiment(exp_name: str, exp: dict[str, Any]) -> None:
    test_labels = exp.get("test_labels")
    methods = exp.get("methods")
    if not isinstance(test_labels, list) or not test_labels:
        raise ValueError(f"{exp_name}: predictions must contain a non-empty test_labels list")
    if not isinstance(methods, dict) or not methods:
        raise ValueError(f"{exp_name}: predictions must contain at least one method")
    for method_name, method in methods.items():
        labelings = method.get("test_labelings")
        if not isinstance(labelings, list):
            raise ValueError(f"{exp_name}.{method_name}: missing test_labelings list")
        if len(labelings) != len(test_labels):
            raise ValueError(
                f"{exp_name}.{method_name}: {len(labelings)} test_labelings for "
                f"{len(test_labels)} label sets"
            )
        if "atlas_labels" not in method:
            raise ValueError(f"{exp_name}.{method_name}: missing atlas_labels")


def expected_methods_from_scores(path: Path) -> dict[str, list[str]]:
    scores = json.loads(path.read_text())
    experiments = scores.get("experiments", scores)
    expected: dict[str, list[str]] = {}
    for exp_name, exp in experiments.items():
        if exp_name.startswith("_"):
            continue
        if not isinstance(exp, dict):
            continue
        results = exp.get("results", exp)
        if isinstance(results, dict):
            expected[exp_name] = [
                name for name in results
                if isinstance(name, str) and not name.startswith("_")
            ]
    return expected


def restrict_to_expected(
    scored: dict[str, dict[str, float]],
    exp_name: str,
    expected: dict[str, list[str]] | None,
) -> dict[str, dict[str, float]]:
    if expected is None:
        return scored
    if exp_name not in expected:
        raise ValueError(f"{exp_name}: missing from train scores")
    missing = [name for name in expected[exp_name] if name not in scored]
    if missing:
        raise ValueError(f"{exp_name}: prediction artifact is missing train-scored methods {missing}")
    return {name: scored[name] for name in expected[exp_name]}


def add_cross_method_constraints(methods: dict[str, dict[str, float]], metadata: dict[str, Any]) -> None:
    oracle = methods.get("supervised_oracle_atlas")
    if oracle is not None:
        oracle_acc = oracle.get("atlas_accuracy_mean")
        if oracle_acc is not None:
            for method_name, method_scores in methods.items():
                if method_name == "supervised_oracle_atlas":
                    continue
                if "atlas_accuracy_mean" in method_scores:
                    method_scores["gap_to_supervised_oracle"] = float(
                        oracle_acc - method_scores["atlas_accuracy_mean"]
                    )
    if "our_unsupervised_atlas" in methods:
        methods["our_unsupervised_atlas"]["semantic_labels_used_for_training"] = float(
            metadata.get("semantic_labels_used_for_training", True)
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", nargs="?", default="outputs/method/predictions.json")
    parser.add_argument("--output", default="scoring/scores_test.json")
    parser.add_argument("--match-methods-from", default=None)
    args = parser.parse_args()

    predictions_path = Path(args.predictions)
    pred = json.loads(predictions_path.read_text())
    metadata = pred.get("metadata", {})
    expected = (
        expected_methods_from_scores(Path(args.match_methods_from))
        if args.match_methods_from
        else None
    )
    out: dict[str, Any] = {
        "_metadata": {
            "slice": SLICE,
            "split_seed": SPLIT_SEED,
            "source_predictions": str(predictions_path),
            "matched_methods_from": args.match_methods_from,
        },
        "experiments": {},
    }

    for exp_name, exp in pred["experiments"].items():
        validate_experiment(exp_name, exp)
        indices = split_indices(len(exp["test_labels"]))
        scored = {
            name: score_method(method, exp["test_labels"], indices)
            for name, method in exp["methods"].items()
        }
        methods = restrict_to_expected(scored, exp_name, expected)
        add_cross_method_constraints(methods, metadata)
        out["experiments"][exp_name] = {
            "_slice": SLICE,
            "_target_indices": indices,
            "results": methods,
        }

    if expected is not None:
        missing_exps = [exp_name for exp_name in expected if exp_name not in out["experiments"]]
        if missing_exps:
            raise ValueError(f"prediction artifact is missing train-scored experiments {missing_exps}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"eval/{SLICE}: {exc}", file=sys.stderr)
        raise
