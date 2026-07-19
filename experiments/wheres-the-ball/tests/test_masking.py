import numpy as np
import pytest
from PIL import Image

from wheresball.masking import (
    OcclusionStats,
    degradation_scale,
    degrade_image,
    is_naturally_occluded,
    occlusion_stats,
)


def test_occlusion_stats_uncovered():
    stats = occlusion_stats((10, 10, 20, 20), [])
    assert stats.visible_fraction == pytest.approx(1.0)
    assert stats.ball_px == pytest.approx(10)


def test_occlusion_stats_fully_covered():
    stats = occlusion_stats((10, 10, 20, 20), [(0, 0, 30, 30)])
    assert stats.visible_fraction == pytest.approx(0.0)


def test_occlusion_stats_partial_multiple():
    # Left half and right half covered by different players.
    stats = occlusion_stats((0, 0, 10, 10), [(0, 0, 5, 10), (5, 0, 10, 10)])
    assert stats.visible_fraction < 0.5


def test_is_naturally_occluded_criteria():
    assert is_naturally_occluded(OcclusionStats(ball_px=20, visible_fraction=0.1))
    assert is_naturally_occluded(OcclusionStats(ball_px=4, visible_fraction=1.0))
    assert not is_naturally_occluded(OcclusionStats(ball_px=20, visible_fraction=0.9))


def test_degradation_scale():
    assert degradation_scale(ball_px=20, target_ball_px=2) == pytest.approx(0.1)
    assert degradation_scale(ball_px=1, target_ball_px=2) == 1.0
    assert degradation_scale(ball_px=0) == 1.0


def test_degrade_image_removes_detail_keeps_size():
    rng = np.random.default_rng(0)
    array = (rng.uniform(0, 255, size=(64, 64, 3))).astype("uint8")
    img = Image.fromarray(array)
    out = degrade_image(img, scale=0.1, blur_radius=2.0)
    assert out.size == img.size
    # High-frequency detail must drop: variance of the degraded image is much lower.
    assert np.asarray(out).std() < np.asarray(img).std() * 0.5


def test_degrade_image_rejects_bad_scale():
    img = Image.new("RGB", (10, 10))
    with pytest.raises(ValueError):
        degrade_image(img, scale=0.0)
    with pytest.raises(ValueError):
        degrade_image(img, scale=1.5)
