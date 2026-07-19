"""Homography utilities: image coordinates → pitch coordinates in meters.

The design (§3) asks for errors in both normalized pixels and meters. SoccerNet
provides camera calibration for part of the data; when a homography H is
available for a frame, these helpers project predictions and ground truth to
the pitch plane so metric thresholds (1 m / 3 m / 5 m) apply.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

#: FIFA standard pitch, meters (length x width). SoccerNet uses 105 x 68.
PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0


def fit_homography(
    image_points: Sequence[tuple[float, float]],
    pitch_points: Sequence[tuple[float, float]],
) -> np.ndarray:
    """Fit a 3x3 homography mapping image points to pitch points (DLT).

    Needs >= 4 non-degenerate correspondences (e.g. pitch line intersections).
    """
    if len(image_points) < 4 or len(image_points) != len(pitch_points):
        raise ValueError("need >= 4 paired correspondences")
    rows = []
    for (x, y), (u, v) in zip(image_points, pitch_points):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, vt = np.linalg.svd(np.asarray(rows, dtype=float))
    h = vt[-1].reshape(3, 3)
    if abs(h[2, 2]) < 1e-12:
        raise ValueError("degenerate homography")
    return h / h[2, 2]


def project_point(h: np.ndarray, xy: tuple[float, float]) -> tuple[float, float]:
    """Apply a homography to a single 2D point."""
    vec = h @ np.array([xy[0], xy[1], 1.0])
    if abs(vec[2]) < 1e-12:
        raise ValueError(f"point {xy} projects to infinity")
    return (float(vec[0] / vec[2]), float(vec[1] / vec[2]))


def metric_error(
    h: np.ndarray, pred_xy: tuple[float, float], gt_xy: tuple[float, float]
) -> float:
    """Euclidean error in meters between two image-space points after
    projecting both onto the pitch plane."""
    px, py = project_point(h, pred_xy)
    gx, gy = project_point(h, gt_xy)
    return math.hypot(px - gx, py - gy)
