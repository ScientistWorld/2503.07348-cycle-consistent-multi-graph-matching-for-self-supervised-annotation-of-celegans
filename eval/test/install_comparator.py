"""Freeze a comparator's predictions into the evaluators' fixed comparator files.

    python eval/test/install_comparator.py <name> <predictions.json>

Writes eval/test/fixed/<name>.json (pool cliques + hidden-test labelings) and
eval/train/fixed/<name>.json (dev labelings only; pool cliques are never written
to the visible side because a supervised comparator's cliques are the hidden
pool labels).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    name, path = sys.argv[1], Path(sys.argv[2])
    pred = json.loads(path.read_text())
    keys = json.loads((ROOT / "eval" / "test" / "keys.json").read_text())
    dev_ids = sorted(json.loads((ROOT / "eval" / "train" / "dev_labels.json").read_text())["dev"])
    test_part = {
        "pool_cliques": {w: pred["pool_cliques"][w] for w in keys["pool"]},
        "labelings": {w: pred["labelings"][w] for w in keys["test"]},
        "info": pred.get("info", {}),
    }
    dev_part = {"labelings": {w: pred["labelings"][w] for w in dev_ids}, "info": pred.get("info", {})}
    for side, part in (("test", test_part), ("train", dev_part)):
        out = ROOT / "eval" / side / "fixed" / f"{name}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(part))
        print(f"installed {out}")


if __name__ == "__main__":
    main()
