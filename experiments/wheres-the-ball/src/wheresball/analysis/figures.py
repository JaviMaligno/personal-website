"""Publication figures for the blog article (design §9.3).

Each function takes the plain-data outputs of `harness.evaluate` /
`run_matrix` and returns a matplotlib Figure, so notebooks and scripts can
save or tweak them. Matplotlib is an optional dependency:

    pip install "wheres-the-ball[viz]"
"""

from __future__ import annotations

from typing import Sequence

try:
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "matplotlib is required for figures: pip install 'wheres-the-ball[viz]'"
    ) from exc

import numpy as np

from ..schema import Item
from ..harness.runner import ResultRow


def ranking_figure(report: dict, condition_key: str):
    """Horizontal ranking of systems by median error, with 95% bootstrap CIs."""
    entries = [
        (system, per_condition[condition_key])
        for system, per_condition in report["systems"].items()
        if condition_key in per_condition
    ]
    entries.sort(key=lambda kv: kv[1]["error"]["median"], reverse=True)
    names = [name for name, _ in entries]
    medians = np.array([e["error"]["median"] for _, e in entries])
    lows = np.array([e["error_median_ci95"][0] for _, e in entries])
    highs = np.array([e["error_median_ci95"][1] for _, e in entries])

    fig, ax = plt.subplots(figsize=(7, 0.5 * len(names) + 1.5))
    ax.barh(names, medians, xerr=[medians - lows, highs - medians],
            capsize=4, color="#4c72b0")
    ax.set_xlabel("Median localization error (normalized units)")
    ax.set_title(f"Where's the ball? — {condition_key}")
    fig.tight_layout()
    return fig


def stratum_figure(report: dict, systems: Sequence[str], condition_key: str):
    """Grouped bars of median error per ball-state stratum (H4 figure)."""
    strata: list[str] = []
    for system in systems:
        strata.extend(report["systems"][system][condition_key]["by_stratum"])
    strata = sorted(set(strata))

    fig, ax = plt.subplots(figsize=(8, 4))
    width = 0.8 / max(1, len(systems))
    xs = np.arange(len(strata))
    for i, system in enumerate(systems):
        by_stratum = report["systems"][system][condition_key]["by_stratum"]
        values = [by_stratum.get(s, {}).get("median", np.nan) for s in strata]
        ax.bar(xs + i * width, values, width, label=system)
    ax.set_xticks(xs + width * (len(systems) - 1) / 2)
    ax.set_xticklabels(strata, rotation=15)
    ax.set_ylabel("Median error")
    ax.set_title("Error by ball state (H4: bimodality)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def calibration_figure(rows: Sequence[ResultRow], n_bins: int = 10):
    """Declared confidence vs error: scatter + binned medians (RQ4 figure)."""
    confs = np.array([r.prediction.confidence for r in rows])
    errors = np.array([r.error for r in rows])

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.scatter(confs, errors, s=8, alpha=0.25, color="#4c72b0", label="items")
    edges = np.linspace(0, 100, n_bins + 1)
    centers, medians = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (confs >= lo) & (confs <= hi if hi == 100 else confs < hi)
        if mask.any():
            centers.append((lo + hi) / 2)
            medians.append(np.median(errors[mask]))
    ax.plot(centers, medians, "o-", color="#c44e52", label="binned median")
    ax.set_xlabel("Declared confidence")
    ax.set_ylabel("Localization error")
    ax.set_title("Does the model know when it doesn't know?")
    ax.legend()
    fig.tight_layout()
    return fig


def error_map_figure(items: Sequence[Item], rows: Sequence[ResultRow]):
    """Ground-truth ball positions colored by error ("error map over the
    pitch", §9.3). Expects rows from a single (system, condition)."""
    errors_by_item = {r.item_id: r.error for r in rows}
    xs, ys, cs = [], [], []
    for item in items:
        if item.item_id in errors_by_item:
            xs.append(item.ball[0])
            ys.append(item.ball[1])
            cs.append(errors_by_item[item.item_id])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, edgecolor="green"))
    scatter = ax.scatter(xs, ys, c=cs, cmap="RdYlGn_r", s=25)
    fig.colorbar(scatter, ax=ax, label="error")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(1.05, -0.05)  # image coordinates: y grows downward
    ax.set_aspect("equal")
    ax.set_title("Error by true ball position")
    fig.tight_layout()
    return fig
