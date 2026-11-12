"""Run a method directory's annotate.sh on every dev and hidden test worm.

    python eval/test/run_annotator.py <method_dir> <out.json>

Writes {"pool_cliques": ..., "labelings": {worm_id: labels}} so a comparator
(e.g. the unlearned baseline) can be frozen with install_comparator.py.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    method_dir, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    worms = sorted((ROOT / "data" / "worms" / "dev").glob("*.txt")) + sorted((ROOT / "eval" / "test" / "worms").glob("*.txt"))

    def run(path: Path):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "labels.json"
            subprocess.run(["bash", str(method_dir / "annotate.sh"), str(path), str(dst)], cwd=ROOT, check=True)
            return path.stem, json.loads(dst.read_text())

    with ThreadPoolExecutor(max_workers=max(1, len(os.sched_getaffinity(0)))) as pool:
        labelings = dict(pool.map(run, worms))
    pred = json.loads((method_dir / "predictions.json").read_text())
    out.write_text(json.dumps({"pool_cliques": pred["pool_cliques"], "labelings": labelings,
                               "info": pred.get("info", {})}))
    print(f"wrote {out} ({len(labelings)} worms)")


if __name__ == "__main__":
    main()
