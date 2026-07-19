"""Synthetic item generator for developing and testing the pipeline.

Generates plausible player configurations whose collective geometry encodes
the ball position the way real play does (players cluster around and run
toward the ball, long balls have runners chasing a distant landing point).
This lets the whole harness — baselines, metrics, statistics, runner, cache —
be exercised end-to-end before any SoccerNet data or VLM API is touched.

Not a substitute for real data: it exists so the pipeline is frozen and tested
before Phase 1 (dataset construction) starts.
"""

from __future__ import annotations

import numpy as np

from ..schema import BallState, Item, Masking, Player, STRATUM_QUOTAS


def _clip(v: float, lo: float = 0.02, hi: float = 0.98) -> float:
    return float(min(max(v, lo), hi))


def _make_players(
    rng: np.random.Generator,
    ball: tuple[float, float],
    n_players: int,
    cluster_frac: float,
    chase_speed: float,
    cluster_spread: float = 0.08,
) -> tuple[Player, ...]:
    """Players: a fraction clustered near the ball running toward it, the rest
    spread over the pitch drifting slowly."""
    players = []
    n_cluster = max(2, int(n_players * cluster_frac))
    for i in range(n_players):
        clustered = i < n_cluster
        if clustered:
            x = _clip(rng.normal(ball[0], cluster_spread))
            y = _clip(rng.normal(ball[1], cluster_spread))
            speed = rng.uniform(0.5, 1.0) * chase_speed
        else:
            x, y = rng.uniform(0.05, 0.95, size=2)
            speed = rng.uniform(0.0, 0.3) * chase_speed
        dx, dy = ball[0] - x, ball[1] - y
        norm = max(np.hypot(dx, dy), 1e-6)
        jitter = rng.normal(0, 0.15 * chase_speed, size=2)
        players.append(
            Player(
                x=x,
                y=y,
                vx=float(speed * dx / norm + jitter[0]),
                vy=float(speed * dy / norm + jitter[1]),
                team="A" if i % 2 == 0 else "B",
                player_id=f"p{i:02d}",
            )
        )
    return tuple(players)


def _generate_one(rng: np.random.Generator, state: BallState, item_id: str) -> Item:
    n_players = int(rng.integers(14, 23))
    if state == BallState.POSSESSION:
        ball = (rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85))
        players = _make_players(rng, ball, n_players, cluster_frac=0.35, chase_speed=0.05)
        # Possessor: nudge the nearest player onto the ball.
        nearest = min(players, key=lambda p: np.hypot(p.x - ball[0], p.y - ball[1]))
        possessor = Player(
            x=_clip(ball[0] + rng.normal(0, 0.005)),
            y=_clip(ball[1] + rng.normal(0, 0.005)),
            vx=nearest.vx,
            vy=nearest.vy,
            team=nearest.team,
            player_id=nearest.player_id,
        )
        players = tuple(possessor if p.player_id == nearest.player_id else p for p in players)
        possessor_id = possessor.player_id
    elif state == BallState.SHORT_PASS:
        ball = (rng.uniform(0.2, 0.8), rng.uniform(0.2, 0.8))
        players = _make_players(rng, ball, n_players, cluster_frac=0.3, chase_speed=0.08)
        possessor_id = None
    elif state == BallState.LONG_PASS:
        # Ball in flight far from the main cluster; a few runners chase it.
        ball = (rng.uniform(0.6, 0.95), rng.uniform(0.1, 0.9))
        players = _make_players(
            rng, ball, n_players, cluster_frac=0.15, chase_speed=0.15, cluster_spread=0.18
        )
        possessor_id = None
    else:  # CONTESTED
        ball = (rng.uniform(0.2, 0.8), rng.uniform(0.2, 0.8))
        players = _make_players(
            rng, ball, n_players, cluster_frac=0.5, chase_speed=0.12, cluster_spread=0.05
        )
        possessor_id = None
    return Item(
        item_id=item_id,
        players=players,
        ball=(_clip(ball[0]), _clip(ball[1])),
        state=state,
        masking=Masking.NATURAL,
        possessor_id=possessor_id,
    )


def generate_items(n_total: int = 200, seed: int = 0) -> list[Item]:
    """Generate a stratified synthetic evaluation set following the design's
    stratum quotas (§3: 40/25/20/15)."""
    rng = np.random.default_rng(seed)
    items: list[Item] = []
    states = list(STRATUM_QUOTAS)
    counts = [int(round(n_total * STRATUM_QUOTAS[s])) for s in states]
    counts[0] += n_total - sum(counts)  # rounding remainder to the largest stratum
    for state, count in zip(states, counts):
        for i in range(count):
            items.append(_generate_one(rng, state, item_id=f"syn-{state.value}-{i:04d}"))
    return items
