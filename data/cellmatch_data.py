from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class Worm:
    worm_id: str
    names: list[str]
    centroids: np.ndarray
    radii: np.ndarray

    def subset(self, names: Iterable[str]) -> "Worm":
        wanted = set(names)
        keep = [i for i, name in enumerate(self.names) if name in wanted]
        return Worm(
            self.worm_id,
            [self.names[i] for i in keep],
            self.centroids[keep].copy(),
            self.radii[keep].copy(),
        )


def load_worm(path: Path) -> Worm:
    names: list[str] = []
    centroids: list[list[float]] = []
    radii: list[list[float]] = []
    with path.open() as handle:
        for line in handle:
            parts = line.strip().split()
            if not parts:
                continue
            names.append(parts[1])
            values = [float(x) for x in parts[2:]]
            centroids.append(values[:3])
            radii.append(values[3:6])
    return Worm(path.stem, names, np.asarray(centroids), np.asarray(radii))


def load_split(root: str | Path, limit: int | None = None) -> list[Worm]:
    paths = sorted(Path(root).glob("*.txt"), key=lambda p: int(p.stem) if p.stem.isdigit() else p.stem)
    if limit is not None:
        paths = paths[:limit]
    return [load_worm(path) for path in paths]


def common_labels(worms: list[Worm], max_cells: int | None = None) -> list[str]:
    common = set(worms[0].names)
    for worm in worms[1:]:
        common &= set(worm.names)
    labels = [name for name in worms[0].names if name in common]
    if max_cells is not None:
        labels = labels[:max_cells]
    return labels


def restrict_to_common(worms: list[Worm], labels: list[str]) -> list[Worm]:
    return [worm.subset(labels) for worm in worms]
