"""Evaluation-set construction: stratified sampling and freezing (design §3, §7).

The frozen set's manifest hash is recorded before any model runs — the design
doc acts as informal pre-registration, and the hash makes "the set did not
change after seeing results" verifiable.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from ..schema import BallState, Item, STRATUM_QUOTAS, items_from_json, items_to_json, manifest_hash


class InsufficientItemsError(ValueError):
    def __init__(self, state: BallState, needed: int, available: int):
        super().__init__(
            f"stratum {state.value!r} needs {needed} items but only {available} are available"
        )
        self.state, self.needed, self.available = state, needed, available


def stratified_sample(
    items: Sequence[Item],
    n_total: int,
    quotas: Mapping[BallState, float] = STRATUM_QUOTAS,
    seed: int = 0,
) -> list[Item]:
    """Sample `n_total` items following the stratum quotas, deterministically."""
    rng = np.random.default_rng(seed)
    pools: dict[BallState, list[Item]] = defaultdict(list)
    for it in items:
        pools[it.state].append(it)

    states = list(quotas)
    counts = [int(round(n_total * quotas[s])) for s in states]
    counts[0] += n_total - sum(counts)

    selected: list[Item] = []
    for state, count in zip(states, counts):
        pool = sorted(pools.get(state, []), key=lambda it: it.item_id)
        if len(pool) < count:
            raise InsufficientItemsError(state, count, len(pool))
        picks = rng.choice(len(pool), size=count, replace=False)
        selected.extend(pool[i] for i in sorted(picks))
    return selected


def freeze(items: Sequence[Item], path: str | Path) -> str:
    """Write the frozen evaluation set + sidecar hash file; returns the hash."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(items_to_json(items), encoding="utf-8")
    digest = manifest_hash(items)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar.write_text(json.dumps({"sha256": digest, "n_items": len(items)}) + "\n")
    return digest


def load_frozen(path: str | Path, expected_hash: str | None = None) -> list[Item]:
    """Load a frozen set, verifying its hash against the sidecar (or an
    explicitly expected hash)."""
    path = Path(path)
    items = items_from_json(path.read_text(encoding="utf-8"))
    digest = manifest_hash(items)
    if expected_hash is None:
        sidecar = path.with_suffix(path.suffix + ".sha256")
        if sidecar.exists():
            expected_hash = json.loads(sidecar.read_text())["sha256"]
    if expected_hash is not None and digest != expected_hash:
        raise ValueError(
            f"frozen set at {path} has hash {digest[:12]}… but expected {expected_hash[:12]}…"
        )
    return items
