"""Freeze a comparator's predictions into the evaluators' fixed comparator files.

    python eval/test/install_comparator.py <name> <predictions.json>

Writes eval/test/fixed/<name>.json (pool cliques + hidden-test labelings) and
eval/train/fixed/<name>.json. The visible side only receives the comparator's
scores, computed once by eval/train/evaluate_slice.py --freeze: a supervised
comparator's raw dev labelings would hand out supervised correspondences.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
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
    out = ROOT / "eval" / "test" / "fixed" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(test_part))
    print(f"installed {out}")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(dev_part, handle)
    try:
        subprocess.run([sys.executable, str(ROOT / "eval" / "train" / "evaluate_slice.py"), "--freeze", name,
                        handle.name], check=True)
    finally:
        Path(handle.name).unlink()


if __name__ == "__main__":
    main()
