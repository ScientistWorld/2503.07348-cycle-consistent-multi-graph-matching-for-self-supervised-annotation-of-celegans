from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def worm_accuracy(atlas_labels: list[str], labels: list[str], labeling: list) -> float:
    correct = 0
    total = 0
    for atlas_idx, target_idx in enumerate(labeling):
        total += 1
        if target_idx is None or not isinstance(target_idx, int):
            continue
        if target_idx < 0 or target_idx >= len(labels):
            continue
        if atlas_idx < len(atlas_labels) and atlas_labels[atlas_idx] == labels[target_idx]:
            correct += 1
    return correct / total if total else 0.0


def invalid_assignment_rate(labels: list[str], labeling: list) -> float:
    total = len(labeling)
    if total == 0:
        return 1.0
    invalid = 0
    for target_idx in labeling:
        if target_idx is None or not isinstance(target_idx, int) or target_idx < 0 or target_idx >= len(labels):
            invalid += 1
    return invalid / total


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def std(values: list[float]) -> float:
    if not values:
        return 0.0
    avg = mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / len(values))


def score_method(method: dict, test_labels: list[list[str]]) -> dict[str, float]:
    atlas_labels = method["atlas_labels"]
    acc = [
        worm_accuracy(atlas_labels, labels, labeling)
        for labels, labeling in zip(test_labels, method["test_labelings"])
    ]
    invalid_rates = [
        invalid_assignment_rate(labels, labeling)
        for labels, labeling in zip(test_labels, method["test_labelings"])
    ]
    result = {
        "atlas_accuracy_mean": float(mean(acc)),
        "atlas_accuracy_min": float(min(acc) if acc else 0.0),
        "atlas_accuracy_std": float(std(acc)),
        "invalid_assignment_rate": float(mean(invalid_rates)),
    }
    if "pre_atlas_accuracies" in method:
        vals = method["pre_atlas_accuracies"]
        result["pre_atlas_accuracy_mean"] = float(mean(vals))
        result["pre_atlas_accuracy_std"] = float(std(vals))
        result["atlas_minus_preatlas"] = result["atlas_accuracy_mean"] - result["pre_atlas_accuracy_mean"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", nargs="?", default="outputs/method/predictions.json")
    parser.add_argument("--output", default="scoring/scores.json")
    args = parser.parse_args()

    pred = json.loads(Path(args.predictions).read_text())
    out = {"experiments": {}}
    for exp_name, exp in pred["experiments"].items():
        test_labels = exp["test_labels"]
        methods = {name: score_method(method, test_labels) for name, method in exp["methods"].items()}
        if "our_unsupervised_atlas" in methods and "supervised_oracle_atlas" in methods:
            methods["our_unsupervised_atlas"]["gap_to_supervised_oracle"] = (
                methods["supervised_oracle_atlas"]["atlas_accuracy_mean"]
                - methods["our_unsupervised_atlas"]["atlas_accuracy_mean"]
            )
            methods["our_unsupervised_atlas"]["semantic_labels_used_for_training"] = float(
                pred["metadata"].get("semantic_labels_used_for_training", True)
            )
        out["experiments"][exp_name] = {"results": methods}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
