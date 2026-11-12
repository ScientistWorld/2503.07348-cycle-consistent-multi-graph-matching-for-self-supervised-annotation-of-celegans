"""Loaders for the anonymized C. elegans nucleus tables of this benchmark.

Each worm is a text file with one row per segmented nucleus and six columns:
``x y z r1 r2 r3`` (ellipsoid centroid after rigid body-axis alignment, and
the three principal radii). Rows are in an arbitrary per-worm order and carry
no identity information.

Groups (``data/worms/<group>/``):
  pool  12 worms to build an identity reference from (no labels anywhere visible)
  dev    4 held-out worms annotated by the visible evaluator (scripts/evaluate_train.sh)
The 10 hidden test worms are not in data/: the hidden evaluator hands them, one
at a time, to the submission's annotate.sh.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent / "worms"
GROUPS = ("pool", "dev")


@dataclass
class WormFeatures:
    worm_id: str
    centroids: np.ndarray  # (n, 3)
    radii: np.ndarray  # (n, 3)

    @property
    def n(self) -> int:
        return int(self.centroids.shape[0])

    def with_centroids(self, centroids: np.ndarray) -> "WormFeatures":
        return WormFeatures(self.worm_id, np.asarray(centroids, dtype=float), self.radii)


def load_worm(path: str | Path) -> WormFeatures:
    path = Path(path)
    values = np.loadtxt(path, dtype=float, ndmin=2)
    if values.shape[1] != 6:
        raise ValueError(f"{path}: expected 6 columns, got {values.shape[1]}")
    return WormFeatures(path.stem, values[:, :3].copy(), values[:, 3:6].copy())


def worm_ids(group: str, root: str | Path = ROOT) -> list[str]:
    return sorted(p.stem for p in (Path(root) / group).glob("*.txt"))


def load_group(group: str, root: str | Path = ROOT) -> list[WormFeatures]:
    if group not in GROUPS:
        raise ValueError(f"unknown group {group!r}; expected one of {GROUPS}")
    return [load_worm(Path(root) / group / f"{wid}.txt") for wid in worm_ids(group, root)]
