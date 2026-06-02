from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def score_method(method: dict, test_labels: list[list[str]]) -> dict[str, float]:
    atlas_labels = method["atlas_labels"]
    acc = []
    for labels, labeling in zip(test_labels, method["test_labelings"]):
        correct = 0
        total = 0
        for atlas_idx, target_idx in enumerate(labeling):
            if target_idx is None or target_idx < 0:
                total += 1
                continue
            total += 1
            correct += int(atlas_labels[atlas_idx] == labels[target_idx])
        acc.append(correct / total if total else 0.0)
    result = {
        "atlas_accuracy_mean": float(np.mean(acc)),
        "atlas_accuracy_std": float(np.std(acc)),
    }
    if "pre_atlas_accuracies" in method:
        vals = method["pre_atlas_accuracies"]
        result["pre_atlas_accuracy_mean"] = float(np.mean(vals))
        result["pre_atlas_accuracy_std"] = float(np.std(vals))
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
