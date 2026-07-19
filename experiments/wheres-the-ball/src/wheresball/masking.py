"""Masking protocol (design §3): hide the ball without leaking its position.

Two of the three conditions are implementable without any model:

1. Natural occlusion — pure selection criteria over existing annotations
   (`occlusion_stats`, `is_naturally_occluded`).
2. Global degradation — downscale + blur of the whole frame until the ball is
   illegible while players remain interpretable (`degrade_image`). No local
   artifacts that could betray the ball's position.

The third condition (local inpainting + leak check) requires a detector/VLM
and is deliberately left as an interface for the API phase.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageFilter

BBox = tuple[float, float, float, float]  # x0, y0, x1, y1 in pixels


def _intersection_area(a: BBox, b: BBox) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


def _area(box: BBox) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


@dataclass(frozen=True)
class OcclusionStats:
    ball_px: float            # ball bbox size (max side), pixels
    visible_fraction: float   # rough fraction of ball area not covered by players


def occlusion_stats(ball_bbox: BBox, player_bboxes: list[BBox]) -> OcclusionStats:
    """Approximate ball visibility from annotation geometry alone.

    Coverage is approximated as the max single-player overlap plus a saturating
    correction for multiple occluders — cheap, and errs toward *underestimating*
    occlusion, which only makes the selection stricter.
    """
    ball_area = _area(ball_bbox)
    ball_px = max(ball_bbox[2] - ball_bbox[0], ball_bbox[3] - ball_bbox[1])
    if ball_area == 0:
        return OcclusionStats(ball_px=ball_px, visible_fraction=0.0)
    overlaps = sorted(
        (_intersection_area(ball_bbox, pb) / ball_area for pb in player_bboxes),
        reverse=True,
    )
    covered = 0.0
    remaining = 1.0
    for frac in overlaps:
        covered += frac * remaining
        remaining = max(0.0, 1.0 - covered)
    return OcclusionStats(ball_px=ball_px, visible_fraction=max(0.0, 1.0 - covered))


def is_naturally_occluded(
    stats: OcclusionStats,
    max_visible_fraction: float = 0.25,
    max_ball_px: float = 8.0,
) -> bool:
    """Selection criterion for the primary masking condition: the ball is
    effectively invisible (mostly covered, or too small to read) while its
    tracking annotation still exists."""
    return stats.visible_fraction <= max_visible_fraction or stats.ball_px <= max_ball_px


def degradation_scale(ball_px: float, target_ball_px: float = 2.0) -> float:
    """Downscale factor that renders a ball of `ball_px` pixels illegible
    (~`target_ball_px` after scaling). Returns a factor in (0, 1]."""
    if ball_px <= 0:
        return 1.0
    return min(1.0, target_ball_px / ball_px)


def degrade_image(image: Image.Image, scale: float, blur_radius: float = 1.5) -> Image.Image:
    """Global degradation: downscale, upscale back, then a mild blur.

    Applied uniformly to the whole frame — simulates watching from afar and
    leaves no local artifact around the ball position.
    """
    if not 0 < scale <= 1:
        raise ValueError(f"scale must be in (0, 1], got {scale}")
    w, h = image.size
    small = image.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BILINEAR)
    restored = small.resize((w, h), Image.BILINEAR)
    return restored.filter(ImageFilter.GaussianBlur(radius=blur_radius))
