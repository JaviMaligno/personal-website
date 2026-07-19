import math

import pytest

from wheresball.metrics import (
    by_stratum,
    confidence_error_correlation,
    ece_regression,
    localization_error,
    pck,
    possessor_accuracy,
    summarize_errors,
    uncertainty_coverage,
)
from wheresball.schema import BallState, Item, Masking, Player, Prediction


def make_item(ball=(0.5, 0.5), state=BallState.POSSESSION, possessor_id=None, players=()):
    return Item(
        item_id=f"it-{ball}-{state.value}",
        players=tuple(players),
        ball=ball,
        state=state,
        masking=Masking.NATURAL,
        possessor_id=possessor_id,
    )


def test_localization_error_euclidean():
    item = make_item(ball=(0.0, 0.0))
    assert localization_error(Prediction(x=0.3, y=0.4), item) == pytest.approx(0.5)


def test_summarize_and_pck():
    errors = [0.01, 0.02, 0.03, 0.10, 1.0]
    summary = summarize_errors(errors)
    assert summary["median"] == pytest.approx(0.03)
    assert summary["n"] == 5
    acc = pck(errors, thresholds=[0.05, 0.5])
    assert acc[0.05] == pytest.approx(3 / 5)
    assert acc[0.5] == pytest.approx(4 / 5)


def test_possessor_accuracy():
    players = [Player(x=0.1, y=0.1, player_id="a"), Player(x=0.9, y=0.9, player_id="b")]
    items = [
        make_item(possessor_id="a", players=players),
        make_item(possessor_id="b", players=players),
        make_item(possessor_id=None, players=players),  # excluded
    ]
    preds = [Prediction(x=0.15, y=0.15), Prediction(x=0.2, y=0.2), Prediction(x=0.5, y=0.5)]
    assert possessor_accuracy(preds, items) == pytest.approx(0.5)
    assert possessor_accuracy([preds[2]], [items[2]]) is None


def test_calibration_correlation_sign():
    # Higher confidence ↔ lower error → strongly negative Spearman.
    preds = [Prediction(x=0, y=0, confidence=c) for c in [90, 70, 50, 30, 10]]
    errors = [0.01, 0.05, 0.1, 0.2, 0.4]
    assert confidence_error_correlation(preds, errors) == pytest.approx(-1.0)


def test_uncertainty_coverage():
    preds = [
        Prediction(x=0, y=0, uncertainty_radius=0.1),
        Prediction(x=0, y=0, uncertainty_radius=0.1),
    ]
    assert uncertainty_coverage(preds, [0.05, 0.2]) == pytest.approx(0.5)


def test_ece_perfect_and_worst():
    # All hits declared at 100% confidence → ECE 0.
    preds = [Prediction(x=0, y=0, confidence=100)] * 4
    assert ece_regression(preds, [0.01] * 4, hit_radius=0.05) == pytest.approx(0.0)
    # All misses declared at 100% confidence → ECE 1.
    assert ece_regression(preds, [0.9] * 4, hit_radius=0.05) == pytest.approx(1.0)


def test_by_stratum_groups():
    items = [
        make_item(state=BallState.POSSESSION),
        make_item(state=BallState.POSSESSION),
        make_item(state=BallState.LONG_PASS),
    ]
    result = by_stratum(items, [0.1, 0.3, 0.9])
    assert result[BallState.POSSESSION]["n"] == 2
    assert result[BallState.LONG_PASS]["median"] == pytest.approx(0.9)
