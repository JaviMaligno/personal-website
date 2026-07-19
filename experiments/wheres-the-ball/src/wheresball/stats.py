"""Statistical analysis utilities (design §7).

- Bootstrap confidence intervals over items (10k replicates by default).
- Paired per-item comparisons via Wilcoxon signed-rank.
- Holm correction for multiple comparisons.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Mapping, Sequence

import numpy as np
from scipy.stats import wilcoxon


@dataclass(frozen=True)
class BootstrapCI:
    estimate: float
    low: float
    high: float
    alpha: float


def bootstrap_ci(
    values: Sequence[float],
    statistic: Callable[[np.ndarray], float] = np.median,
    n_replicates: int = 10_000,
    alpha: float = 0.05,
    seed: int = 0,
) -> BootstrapCI:
    """Percentile bootstrap CI, resampling items with replacement (§7)."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        raise ValueError("bootstrap_ci requires at least one value")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(n_replicates, arr.size))
    replicates = np.apply_along_axis(statistic, 1, arr[idx])
    low, high = np.percentile(replicates, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return BootstrapCI(
        estimate=float(statistic(arr)), low=float(low), high=float(high), alpha=alpha
    )


def paired_wilcoxon(errors_a: Sequence[float], errors_b: Sequence[float]) -> float:
    """p-value of the Wilcoxon signed-rank test on paired per-item errors."""
    a = np.asarray(errors_a, dtype=float)
    b = np.asarray(errors_b, dtype=float)
    if a.shape != b.shape:
        raise ValueError("paired comparison requires equal-length error vectors")
    if np.allclose(a, b):
        return 1.0
    _, p = wilcoxon(a, b)
    return float(p)


def holm_correction(pvalues: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values (monotone, capped at 1)."""
    m = len(pvalues)
    order = np.argsort(pvalues)
    adjusted = np.empty(m)
    running_max = 0.0
    for rank, idx in enumerate(order):
        adj = min(1.0, (m - rank) * pvalues[idx])
        running_max = max(running_max, adj)
        adjusted[idx] = running_max
    return adjusted.tolist()


@dataclass(frozen=True)
class PairwiseComparison:
    system_a: str
    system_b: str
    p_raw: float
    p_holm: float


def compare_systems(errors_by_system: Mapping[str, Sequence[float]]) -> list[PairwiseComparison]:
    """All pairwise paired Wilcoxon tests with Holm correction (§7)."""
    pairs = list(combinations(sorted(errors_by_system), 2))
    raw = [paired_wilcoxon(errors_by_system[a], errors_by_system[b]) for a, b in pairs]
    adjusted = holm_correction(raw) if raw else []
    return [
        PairwiseComparison(system_a=a, system_b=b, p_raw=p, p_holm=ph)
        for (a, b), p, ph in zip(pairs, raw, adjusted)
    ]
