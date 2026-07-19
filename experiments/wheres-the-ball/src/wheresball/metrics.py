"""Evaluation metrics (design §6): localization error, threshold accuracy
(PCK-style), possessor accuracy, and calibration of declared uncertainty.

Errors are in normalized image units unless a homography is available (metric
projection is a TODO tracked for Phase 1 when SoccerNet calibration data is
wired in).
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Callable, Iterable, Sequence

import numpy as np
from scipy.stats import spearmanr

from .schema import BallState, Item, Prediction


def localization_error(pred: Prediction, item: Item) -> float:
    """Euclidean distance from the prediction to the ground-truth ball."""
    return math.hypot(pred.x - item.ball[0], pred.y - item.ball[1])


def summarize_errors(errors: Sequence[float]) -> dict[str, float]:
    """Median and IQR (the design mandates robust statistics — long tails)."""
    arr = np.asarray(errors, dtype=float)
    q1, med, q3 = np.percentile(arr, [25, 50, 75])
    return {
        "n": int(arr.size),
        "median": float(med),
        "iqr": float(q3 - q1),
        "mean": float(arr.mean()),
    }


def pck(errors: Sequence[float], thresholds: Sequence[float]) -> dict[float, float]:
    """Fraction of items with error below each threshold (PCK-style, §6)."""
    arr = np.asarray(errors, dtype=float)
    return {float(r): float((arr < r).mean()) for r in thresholds}


def nearest_player_id(x: float, y: float, item: Item) -> str | None:
    """ID of the player closest to a point (None if players lack IDs)."""
    if not item.players:
        return None
    nearest = min(item.players, key=lambda p: math.hypot(p.x - x, p.y - y))
    return nearest.player_id


def possessor_accuracy(preds: Sequence[Prediction], items: Sequence[Item]) -> float | None:
    """Is the player nearest to the prediction the true possessor? (§6)

    Only defined over items with an annotated possessor; returns None when
    no item qualifies.
    """
    hits, total = 0, 0
    for pred, item in zip(preds, items):
        if item.possessor_id is None:
            continue
        total += 1
        if nearest_player_id(pred.x, pred.y, item) == item.possessor_id:
            hits += 1
    return hits / total if total else None


# ---------------------------------------------------------------------------
# Calibration (§6): does the model know when it doesn't know? (RQ4)
# ---------------------------------------------------------------------------

def confidence_error_correlation(preds: Sequence[Prediction], errors: Sequence[float]) -> float:
    """Spearman correlation between declared confidence and error.

    A well-calibrated system yields a strongly *negative* value: higher
    confidence should mean lower error. Returns NaN when degenerate
    (e.g. constant confidence).
    """
    confs = [p.confidence for p in preds]
    if len(set(confs)) < 2 or len(set(errors)) < 2:
        return float("nan")
    rho, _ = spearmanr(confs, errors)
    return float(rho)


def uncertainty_coverage(preds: Sequence[Prediction], errors: Sequence[float]) -> float:
    """Fraction of items whose true error falls within the declared
    uncertainty radius. Perfectly calibrated radii would cover ~ the
    confidence level they claim; systematic under-coverage means
    overconfidence."""
    covered = [err <= p.uncertainty_radius for p, err in zip(preds, errors)]
    return float(np.mean(covered)) if covered else float("nan")


def ece_regression(
    preds: Sequence[Prediction],
    errors: Sequence[float],
    hit_radius: float,
    n_bins: int = 10,
) -> float:
    """Expected calibration error adapted to regression (§6): treat
    "error < hit_radius" as the success event and compare each confidence
    bin's declared confidence (as probability) with its empirical hit rate.
    """
    confs = np.asarray([p.confidence for p in preds], dtype=float) / 100.0
    hits = np.asarray(errors, dtype=float) < hit_radius
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    total = len(confs)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (confs >= lo) & (confs < hi) if hi < 1.0 else (confs >= lo) & (confs <= hi)
        if not mask.any():
            continue
        ece += (mask.sum() / total) * abs(confs[mask].mean() - hits[mask].mean())
    return float(ece)


# ---------------------------------------------------------------------------
# Stratified breakdown (§6): key for H4 (bimodal error by ball state).
# ---------------------------------------------------------------------------

def by_stratum(
    items: Sequence[Item],
    values: Sequence[float],
    reducer: Callable[[Sequence[float]], dict | float] = summarize_errors,
) -> dict[BallState, dict | float]:
    groups: dict[BallState, list[float]] = defaultdict(list)
    for item, value in zip(items, values):
        groups[item.state].append(value)
    return {state: reducer(vals) for state, vals in groups.items()}
