"""Experiment runner: systems × conditions × items → results → report.

Baselines and VLM clients run through the same interface so every system is
scored identically. Results are plain dataclasses, exportable to JSON for the
analysis notebooks / blog figures.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from ..baselines import Baseline
from ..metrics import (
    by_stratum,
    confidence_error_correlation,
    ece_regression,
    localization_error,
    pck,
    possessor_accuracy,
    summarize_errors,
    uncertainty_coverage,
)
from ..prompts import PROMPT_VERSION, build_prompt
from ..schema import Condition, Item, Prediction
from ..stats import bootstrap_ci, compare_systems
from .cache import ResponseCache
from .client import VLMClient

#: PCK thresholds in normalized image units (§6); metric thresholds in meters
#: replace these once homography projection lands.
DEFAULT_PCK_THRESHOLDS = (0.02, 0.05, 0.10)


@dataclass(frozen=True)
class ResultRow:
    system: str
    condition: str
    item_id: str
    prediction: Prediction
    error: float


class BaselineSystem:
    """Adapter so a geometric baseline runs as a condition-blind system."""

    def __init__(self, baseline: Baseline):
        self.baseline = baseline
        self.model_id = baseline.name

    def predict(self, item: Item, condition: Condition, prompt: str) -> Prediction:
        return self.baseline.predict(item)


def run_matrix(
    items: Sequence[Item],
    systems: Sequence[VLMClient],
    conditions: Sequence[Condition],
    cache: ResponseCache | None = None,
    prompt_version: str = PROMPT_VERSION,
) -> list[ResultRow]:
    rows: list[ResultRow] = []
    for system in systems:
        for condition in conditions:
            prompt = build_prompt(condition.knowledge, version=prompt_version)
            for item in items:
                pred = None
                if cache is not None:
                    pred = cache.get(system.model_id, item.item_id, condition, prompt_version)
                if pred is None:
                    pred = system.predict(item, condition, prompt)
                    if cache is not None:
                        cache.put(system.model_id, item.item_id, condition, prompt_version, pred)
                rows.append(
                    ResultRow(
                        system=system.model_id,
                        condition=condition.key,
                        item_id=item.item_id,
                        prediction=pred,
                        error=localization_error(pred, item),
                    )
                )
    return rows


def evaluate(
    rows: Sequence[ResultRow],
    items: Sequence[Item],
    pck_thresholds: Sequence[float] = DEFAULT_PCK_THRESHOLDS,
    bootstrap_replicates: int = 10_000,
) -> dict:
    """Per (system, condition) report: robust error summary with bootstrap CI,
    PCK, possessor accuracy, calibration, and the per-stratum breakdown (H4).
    Also includes pairwise Wilcoxon+Holm comparisons across systems per
    condition (§7)."""
    items_by_id = {it.item_id: it for it in items}
    grouped: dict[tuple[str, str], list[ResultRow]] = {}
    for row in rows:
        grouped.setdefault((row.system, row.condition), []).append(row)

    report: dict = {"systems": {}, "comparisons": {}}
    errors_by_condition: dict[str, dict[str, list[float]]] = {}

    for (system, condition), group in sorted(grouped.items()):
        group = sorted(group, key=lambda r: r.item_id)
        group_items = [items_by_id[r.item_id] for r in group]
        preds = [r.prediction for r in group]
        errors = [r.error for r in group]
        ci = bootstrap_ci(errors, n_replicates=bootstrap_replicates)
        entry = {
            "error": summarize_errors(errors),
            "error_median_ci95": [ci.low, ci.high],
            "pck": pck(errors, pck_thresholds),
            "possessor_accuracy": possessor_accuracy(preds, group_items),
            "calibration": {
                "confidence_error_spearman": confidence_error_correlation(preds, errors),
                "uncertainty_coverage": uncertainty_coverage(preds, errors),
                "ece@0.05": ece_regression(preds, errors, hit_radius=0.05),
            },
            "by_stratum": {
                state.value: summary
                for state, summary in by_stratum(group_items, errors).items()
            },
        }
        report["systems"].setdefault(system, {})[condition] = entry
        errors_by_condition.setdefault(condition, {})[system] = errors

    for condition, per_system in errors_by_condition.items():
        if len(per_system) > 1:
            report["comparisons"][condition] = [
                asdict(c) for c in compare_systems(per_system)
            ]
    return report


def save_report(report: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
