"""Build the anonymized benchmark split from the public cellmatch worm tables.

HIDDEN-SIDE SCRIPT. This file, together with the public source tables, can
regenerate every hidden answer, so it lives in eval/test/ only.

Source: the preprocessed Li et al. (2024) worms shipped with the authors'
code release, https://github.com/vislearn/cellmatch (commit 91cef19,
``testdata/Li_worms_train/*.txt`` and ``testdata/Li_worms_test/*.txt``).
Every table has 558 rows ``index name x y z r1 r2 r3``.

The script
  * assigns the 26 worms to three disjoint groups with a fixed permutation:
      pool (12 unlabeled worms to build a reference from),
      dev  (4 worms whose labels are visible to the train-side evaluator),
      test (10 worms whose labels exist only in eval/test/keys.json);
  * shuffles the rows of every worm with a fixed per-worm permutation and drops
    the index and name columns, writing ``x y z r1 r2 r3`` rows to
    ``data/worms/<group>/<id>.txt``;
  * writes the names of pool and test rows to ``eval/test/keys.json`` and the
    names of dev rows to ``eval/train/dev_labels.json``.

Pure Python (no numpy) so it is cheap to rerun:
    python eval/test/prepare_benchmark.py --source <cellmatch>/testdata
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPLIT_SEED = 250307348
GROUP_SIZES = {"pool": 12, "dev": 4, "test": 10}
PREFIX = {"pool": "p", "dev": "d", "test": "t"}


def read_table(path: Path) -> list[list[str]]:
    rows = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 8:
            raise ValueError(f"{path}: expected 8 columns, got {len(parts)}")
        rows.append(parts)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="cellmatch testdata directory")
    args = parser.parse_args()
    source = Path(args.source)
    tables = sorted(source.glob("Li_worms_train/*.txt"), key=lambda p: int(p.stem))
    tables += sorted(source.glob("Li_worms_test/*.txt"), key=lambda p: int(p.stem))
    if len(tables) != sum(GROUP_SIZES.values()):
        raise SystemExit(f"expected 26 source worms, found {len(tables)}")

    rng = random.Random(SPLIT_SEED)
    order = list(range(len(tables)))
    rng.shuffle(order)

    keys: dict = {"source_commit": "vislearn/cellmatch@91cef19", "provenance": {}, "pool": {}, "test": {}}
    dev_labels: dict = {}
    cursor = 0
    for group, size in GROUP_SIZES.items():
        out_dir = ROOT / "data" / "worms" / group
        out_dir.mkdir(parents=True, exist_ok=True)
        for stale in out_dir.glob("*.txt"):
            stale.unlink()
        for k in range(size):
            src = tables[order[cursor]]
            cursor += 1
            worm_id = f"{PREFIX[group]}{k:02d}"
            rows = read_table(src)
            perm = list(range(len(rows)))
            random.Random(f"{SPLIT_SEED}-{worm_id}").shuffle(perm)
            shuffled = [rows[i] for i in perm]
            (out_dir / f"{worm_id}.txt").write_text(
                "".join(" ".join(r[2:8]) + "\n" for r in shuffled)
            )
            names = [r[1].upper() for r in shuffled]
            keys["provenance"][worm_id] = f"{src.parent.name}/{src.name}"
            if group == "dev":
                dev_labels[worm_id] = names
            else:
                keys[group][worm_id] = names

    (ROOT / "eval" / "test" / "keys.json").write_text(json.dumps(keys))
    (ROOT / "eval" / "train" / "dev_labels.json").write_text(json.dumps({"dev": dev_labels}))
    print({g: sorted(p.stem for p in (ROOT / "data" / "worms" / g).glob("*.txt")) for g in GROUP_SIZES})


if __name__ == "__main__":
    main()
