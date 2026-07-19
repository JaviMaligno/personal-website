import pytest

from wheresball.dataset import freeze, generate_items, load_frozen, stratified_sample
from wheresball.dataset.selection import InsufficientItemsError
from wheresball.schema import (
    BallState,
    STRATUM_QUOTAS,
    manifest_hash,
    stratum_counts,
)


def test_generate_items_stratified_and_deterministic():
    items = generate_items(n_total=100, seed=7)
    assert len(items) == 100
    counts = stratum_counts(items)
    assert counts[BallState.POSSESSION] == 40
    assert counts[BallState.SHORT_PASS] == 25
    assert counts[BallState.LONG_PASS] == 20
    assert counts[BallState.CONTESTED] == 15
    assert manifest_hash(items) == manifest_hash(generate_items(n_total=100, seed=7))
    assert manifest_hash(items) != manifest_hash(generate_items(n_total=100, seed=8))


def test_generated_geometry_is_informative():
    # The synthetic generator must encode the ball in player geometry:
    # in possession items the possessor stands on the ball.
    items = [it for it in generate_items(60, seed=0) if it.state == BallState.POSSESSION]
    for item in items:
        possessor = next(p for p in item.players if p.player_id == item.possessor_id)
        dist = ((possessor.x - item.ball[0]) ** 2 + (possessor.y - item.ball[1]) ** 2) ** 0.5
        assert dist < 0.05


def test_stratified_sample_quotas_and_shortage():
    pool = generate_items(n_total=200, seed=1)
    sample = stratified_sample(pool, n_total=40, seed=2)
    counts = stratum_counts(sample)
    assert counts[BallState.POSSESSION] == 16
    assert sum(counts.values()) == 40
    with pytest.raises(InsufficientItemsError):
        stratified_sample(pool[:10], n_total=200)


def test_freeze_and_load_roundtrip(tmp_path):
    items = generate_items(n_total=20, seed=3)
    path = tmp_path / "eval.json"
    digest = freeze(items, path)
    loaded = load_frozen(path)
    assert loaded == items
    assert manifest_hash(loaded) == digest
    # Tampering is detected.
    text = path.read_text().replace("0.4", "0.41", 1)
    path.write_text(text)
    with pytest.raises(ValueError):
        load_frozen(path)


def test_quotas_sum_to_one():
    assert sum(STRATUM_QUOTAS.values()) == pytest.approx(1.0)
