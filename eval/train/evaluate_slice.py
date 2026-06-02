from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

from data.cellmatch_data import common_labels, load_split, restrict_to_common


SLICE = "train"
SPLIT_SEED = 250307348
DEFAULT_TRAIN_DIR = "data/cellmatch_sample/train"
DEFAULT_TEST_DIR = "data/cellmatch_sample/test"
DEFAULT_TRAIN_WORMS = 12
DEFAULT_TEST_WORMS = 6
DEFAULT_CELLS = 160


def split_indices(count: int) -> list[int]:
    if count <= 1:
        return list(range(count))
    order = list(range(count))
    random.Random(SPLIT_SEED).shuffle(order)
    midpoint = max(1, count // 2)
    return sorted(order[:midpoint])


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


def invalid_assignment_rate(labels: list[str], labeling: list[Any]) -> float:
    total = len(labeling)
    if total == 0:
        return 1.0
    invalid = 0
    for target_idx in labeling:
        if target_idx is None or not isinstance(target_idx, int) or target_idx < 0 or target_idx >= len(labels):
            invalid += 1
    return invalid / total


def score_method(method: dict[str, Any], test_labels: list[list[str]], indices: list[int]) -> dict[str, float]:
    atlas_labels = method["atlas_labels"]
    labelings = method["test_labelings"]
    accuracies = [
        worm_accuracy(atlas_labels, test_labels[idx], labelings[idx])
        for idx in indices
    ]
    invalid_rates = [
        invalid_assignment_rate(test_labels[idx], labelings[idx])
        for idx in indices
    ]
    result = {
        "atlas_accuracy_mean": float(np.mean(accuracies)),
        "atlas_accuracy_min": float(np.min(accuracies)),
        "atlas_accuracy_std": float(np.std(accuracies)),
        "invalid_assignment_rate": float(np.mean(invalid_rates)),
    }
    if "pre_atlas_accuracies" in method:
        vals = method["pre_atlas_accuracies"]
        result["pre_atlas_accuracy_mean"] = float(np.mean(vals))
        result["pre_atlas_accuracy_std"] = float(np.std(vals))
        result["atlas_minus_preatlas"] = result["atlas_accuracy_mean"] - result["pre_atlas_accuracy_mean"]
    return result


def validate_experiment(exp_name: str, exp: dict[str, Any], expected_labelings: int) -> None:
    methods = exp.get("methods")
    if not isinstance(methods, dict) or not methods:
        raise ValueError(f"{exp_name}: predictions must contain at least one method")
    for method_name, method in methods.items():
        labelings = method.get("test_labelings")
        if not isinstance(labelings, list):
            raise ValueError(f"{exp_name}.{method_name}: missing test_labelings list")
        if len(labelings) != expected_labelings:
            raise ValueError(
                f"{exp_name}.{method_name}: {len(labelings)} test_labelings for "
                f"{expected_labelings} evaluator-loaded label sets"
            )
        if "atlas_labels" not in method:
            raise ValueError(f"{exp_name}.{method_name}: missing atlas_labels")


def load_ground_truth_labels(metadata: dict[str, Any]) -> list[list[str]]:
    expected = {
        "train_worms": DEFAULT_TRAIN_WORMS,
        "test_worms": DEFAULT_TEST_WORMS,
        "cells": DEFAULT_CELLS,
    }
    for key, value in expected.items():
        if key in metadata and int(metadata[key]) != value:
            raise ValueError(
                f"metadata {key}={metadata[key]} does not match fixed evaluation value {value}"
            )
    train = load_split(DEFAULT_TRAIN_DIR, DEFAULT_TRAIN_WORMS)
    test = load_split(DEFAULT_TEST_DIR, DEFAULT_TEST_WORMS)
    labels = common_labels(train + test, DEFAULT_CELLS)
    return [worm.names for worm in restrict_to_common(test, labels)]


def validate_ground_truth(exp_name: str, exp: dict[str, Any], truth: list[list[str]]) -> None:
    artifact_labels = exp.get("test_labels")
    if artifact_labels is not None and artifact_labels != truth:
        raise ValueError(
            f"{exp_name}: artifact test_labels do not match evaluator-loaded ground truth"
        )


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
    parser.add_argument("--output", default="scoring/scores_train.json")
    args = parser.parse_args()

    predictions_path = Path(args.predictions)
    pred = json.loads(predictions_path.read_text())
    metadata = pred.get("metadata", {})
    ground_truth_labels = load_ground_truth_labels(metadata)
    out: dict[str, Any] = {
        "_metadata": {
            "slice": SLICE,
            "split_seed": SPLIT_SEED,
            "source_predictions": str(predictions_path),
        },
        "experiments": {},
    }

    for exp_name, exp in pred["experiments"].items():
        validate_ground_truth(exp_name, exp, ground_truth_labels)
        validate_experiment(exp_name, exp, len(ground_truth_labels))
        indices = split_indices(len(ground_truth_labels))
        methods = {
            name: score_method(method, ground_truth_labels, indices)
            for name, method in exp["methods"].items()
        }
        add_cross_method_constraints(methods, metadata)
        out["experiments"][exp_name] = {
            "_slice": SLICE,
            "_target_indices": indices,
            "results": methods,
        }

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
