"""Smoke tests: figures build from real harness output without errors."""

import matplotlib

matplotlib.use("Agg")

import pytest

from wheresball.analysis import (
    calibration_figure,
    error_map_figure,
    ranking_figure,
    stratum_figure,
)
from wheresball.baselines import default_baselines
from wheresball.dataset import generate_items
from wheresball.harness import BaselineSystem, MockVLMClient, evaluate, run_matrix
from wheresball.schema import Condition, Knowledge, Masking, TemporalContext

CONDITION = Condition(TemporalContext.SINGLE_FRAME, Knowledge.NEUTRAL, Masking.NATURAL)


@pytest.fixture(scope="module")
def pipeline():
    items = generate_items(30, seed=5)
    systems = [BaselineSystem(b) for b in default_baselines()[:3]] + [MockVLMClient(seed=5)]
    rows = run_matrix(items, systems, [CONDITION])
    report = evaluate(rows, items, bootstrap_replicates=100)
    return items, rows, report


def test_ranking_figure(pipeline):
    _, _, report = pipeline
    fig = ranking_figure(report, CONDITION.key)
    assert fig.axes


def test_stratum_figure(pipeline):
    _, _, report = pipeline
    fig = stratum_figure(report, ["B1_centroid", "mock-vlm"], CONDITION.key)
    assert fig.axes


def test_calibration_figure(pipeline):
    _, rows, _ = pipeline
    mock_rows = [r for r in rows if r.system == "mock-vlm"]
    fig = calibration_figure(mock_rows)
    assert fig.axes


def test_error_map_figure(pipeline):
    items, rows, _ = pipeline
    mock_rows = [r for r in rows if r.system == "mock-vlm"]
    fig = error_map_figure(items, mock_rows)
    assert fig.axes
