"""Learning-free geometric baselines B0-B4 (design §4).

All baselines consume only the player tracking included in the item — never the
image — so they measure the information available in player configuration, not
detection quality. Each returns a `Prediction`; the declared uncertainty radius
is the RMS distance from the predicted point to the players, and confidence is
a fixed 50 (baselines make no calibration claim).
"""

from __future__ import annotations

import hashlib

import numpy as np
from scipy.spatial import Voronoi

from .schema import Item, Prediction


def _clip_to_area(x: float, y: float, area: tuple[float, float, float, float]) -> tuple[float, float]:
    x0, y0, x1, y1 = area
    return (min(max(x, x0), x1), min(max(y, y0), y1))


def _finish(item: Item, x: float, y: float, rationale: str) -> Prediction:
    x, y = _clip_to_area(x, y, item.play_area)
    if item.players:
        pts = np.array([p.position for p in item.players])
        radius = float(np.sqrt(np.mean(np.sum((pts - (x, y)) ** 2, axis=1))))
    else:
        radius = 0.5
    return Prediction(x=x, y=y, uncertainty_radius=radius, confidence=50.0, rationale=rationale)


def _item_seed(item: Item, salt: str) -> int:
    digest = hashlib.sha256(f"{salt}:{item.item_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


class Baseline:
    """Base class; subclasses implement `_point(item) -> (x, y, rationale)`."""

    name: str = "baseline"

    def predict(self, item: Item) -> Prediction:
        x, y, why = self._point(item)
        return _finish(item, x, y, why)

    def _point(self, item: Item) -> tuple[float, float, str]:
        raise NotImplementedError


class B0Random(Baseline):
    """B0 — uniform random over the visible play area (deterministic per item)."""

    name = "B0_random"

    def __init__(self, seed: int = 0):
        self.seed = seed

    def _point(self, item: Item) -> tuple[float, float, str]:
        rng = np.random.default_rng(_item_seed(item, f"b0:{self.seed}"))
        x0, y0, x1, y1 = item.play_area
        return (rng.uniform(x0, x1), rng.uniform(y0, y1), "uniform random over play area")


class B0CenterFrame(Baseline):
    """B0' — center of the frame. Controls for broadcast-camera bias (§8):
    TV cameras follow the ball, so the frame center is itself a cue."""

    name = "B0_center_frame"

    def _point(self, item: Item) -> tuple[float, float, str]:
        x0, y0, x1, y1 = item.play_area
        return ((x0 + x1) / 2, (y0 + y1) / 2, "center of visible play area")


class B1Centroid(Baseline):
    """B1 — centroid of the detected players."""

    name = "B1_centroid"

    def _point(self, item: Item) -> tuple[float, float, str]:
        pts = np.array([p.position for p in item.players])
        cx, cy = pts.mean(axis=0)
        return (float(cx), float(cy), "player centroid")


class B2VelocityWeightedCentroid(Baseline):
    """B2 — centroid weighted by player speed (fast runners weigh more)."""

    name = "B2_velocity_centroid"

    def __init__(self, eps: float = 1e-6):
        self.eps = eps

    def _point(self, item: Item) -> tuple[float, float, str]:
        pts = np.array([p.position for p in item.players])
        weights = np.array([p.speed for p in item.players]) + self.eps
        cx, cy = np.average(pts, axis=0, weights=weights)
        return (float(cx), float(cy), "speed-weighted player centroid")


class B3FastestPlayer(Baseline):
    """B3 — position of the player with the highest instantaneous speed."""

    name = "B3_fastest_player"

    def _point(self, item: Item) -> tuple[float, float, str]:
        fastest = max(item.players, key=lambda p: p.speed)
        return (fastest.x, fastest.y, "fastest player position")


class B4VoronoiDensity(Baseline):
    """B4 — centroid of the Voronoi cell of the player scoring highest on
    local density + speed ("smart geometric" baseline; previews Level 3).

    Cells are bounded by mirroring players across the play-area edges, the
    standard trick to make border cells finite. Falls back to the best
    player's own position when Voronoi is degenerate (< 4 players).
    """

    name = "B4_voronoi_density"

    def __init__(self, density_radius: float = 0.15, speed_weight: float = 1.0):
        self.density_radius = density_radius
        self.speed_weight = speed_weight

    def _scores(self, item: Item) -> np.ndarray:
        pts = np.array([p.position for p in item.players])
        speeds = np.array([p.speed for p in item.players])
        dists = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=2)
        density = (dists < self.density_radius).sum(axis=1) - 1  # exclude self
        max_speed = speeds.max() if speeds.max() > 0 else 1.0
        return density + self.speed_weight * (speeds / max_speed) * density.max()

    def _point(self, item: Item) -> tuple[float, float, str]:
        pts = np.array([p.position for p in item.players])
        best = int(np.argmax(self._scores(item)))
        if len(pts) < 4:
            p = item.players[best]
            return (p.x, p.y, "densest+fastest player (too few players for Voronoi)")

        x0, y0, x1, y1 = item.play_area
        mirrored = np.concatenate([
            pts,
            pts * (1, -1) + (0, 2 * y0),   # mirror across top edge
            pts * (1, -1) + (0, 2 * y1),   # bottom
            pts * (-1, 1) + (2 * x0, 0),   # left
            pts * (-1, 1) + (2 * x1, 0),   # right
        ])
        vor = Voronoi(mirrored)
        region = vor.regions[vor.point_region[best]]
        if not region or -1 in region:
            p = item.players[best]
            return (p.x, p.y, "densest+fastest player (open Voronoi cell)")
        vertices = vor.vertices[region]
        cx, cy = vertices.mean(axis=0)
        return (float(cx), float(cy), "Voronoi cell centroid of densest+fastest player")


def default_baselines(seed: int = 0) -> list[Baseline]:
    """The full B0-B4 suite in design order."""
    return [
        B0Random(seed=seed),
        B0CenterFrame(),
        B1Centroid(),
        B2VelocityWeightedCentroid(),
        B3FastestPlayer(),
        B4VoronoiDensity(),
    ]
