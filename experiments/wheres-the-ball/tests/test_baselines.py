import numpy as np
import pytest

from wheresball.baselines import (
    B0CenterFrame,
    B0Random,
    B1Centroid,
    B2VelocityWeightedCentroid,
    B3FastestPlayer,
    B4VoronoiDensity,
    default_baselines,
)
from wheresball.schema import BallState, Item, Masking, Player


def make_item(players, ball=(0.5, 0.5), item_id="it-1"):
    return Item(
        item_id=item_id,
        players=tuple(players),
        ball=ball,
        state=BallState.POSSESSION,
        masking=Masking.NATURAL,
    )


SQUARE = [
    Player(x=0.2, y=0.2, player_id="a"),
    Player(x=0.8, y=0.2, player_id="b"),
    Player(x=0.2, y=0.8, player_id="c"),
    Player(x=0.8, y=0.8, vx=0.3, vy=0.0, player_id="d"),
]


def test_b0_random_in_play_area_and_deterministic():
    item = make_item(SQUARE)
    b0 = B0Random(seed=1)
    p1, p2 = b0.predict(item), b0.predict(item)
    assert (p1.x, p1.y) == (p2.x, p2.y)
    x0, y0, x1, y1 = item.play_area
    assert x0 <= p1.x <= x1 and y0 <= p1.y <= y1
    # Different items get different draws.
    other = make_item(SQUARE, item_id="it-2")
    p3 = b0.predict(other)
    assert (p1.x, p1.y) != (p3.x, p3.y)


def test_b0_center_frame():
    pred = B0CenterFrame().predict(make_item(SQUARE))
    assert (pred.x, pred.y) == (0.5, 0.5)


def test_b1_centroid_exact():
    pred = B1Centroid().predict(make_item(SQUARE))
    assert pred.x == pytest.approx(0.5)
    assert pred.y == pytest.approx(0.5)


def test_b2_velocity_weight_pulls_toward_fast_player():
    pred = B2VelocityWeightedCentroid().predict(make_item(SQUARE))
    # Only player d moves, so the weighted centroid collapses onto d.
    assert pred.x == pytest.approx(0.8, abs=1e-3)
    assert pred.y == pytest.approx(0.8, abs=1e-3)


def test_b3_fastest_player():
    pred = B3FastestPlayer().predict(make_item(SQUARE))
    assert (pred.x, pred.y) == (0.8, 0.8)


def test_b4_voronoi_in_bounds_and_near_dense_cluster():
    rng = np.random.default_rng(0)
    cluster = [
        Player(x=float(0.3 + rng.normal(0, 0.03)), y=float(0.3 + rng.normal(0, 0.03)),
               vx=0.1, vy=0.1, player_id=f"c{i}")
        for i in range(8)
    ]
    spread = [
        Player(x=float(rng.uniform(0.6, 0.95)), y=float(rng.uniform(0.6, 0.95)),
               player_id=f"s{i}")
        for i in range(6)
    ]
    item = make_item(cluster + spread, ball=(0.3, 0.3))
    pred = B4VoronoiDensity().predict(item)
    assert 0 <= pred.x <= 1 and 0 <= pred.y <= 1
    # Should land near the dense, moving cluster, not the sparse side.
    assert np.hypot(pred.x - 0.3, pred.y - 0.3) < np.hypot(pred.x - 0.8, pred.y - 0.8)


def test_b4_degenerate_few_players_falls_back():
    item = make_item(SQUARE[:3])
    pred = B4VoronoiDensity().predict(item)
    assert 0 <= pred.x <= 1 and 0 <= pred.y <= 1


def test_default_suite_names_unique():
    names = [b.name for b in default_baselines()]
    assert len(names) == len(set(names)) == 6
