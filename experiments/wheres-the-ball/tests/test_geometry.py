import numpy as np
import pytest

from wheresball.geometry import fit_homography, metric_error, project_point


# Image corners of the pitch mapped to a 105x68 m pitch.
IMAGE = [(100, 50), (900, 50), (950, 550), (50, 550)]
PITCH = [(0, 0), (105, 0), (105, 68), (0, 68)]


def test_fit_and_project_roundtrip():
    h = fit_homography(IMAGE, PITCH)
    for img_pt, pitch_pt in zip(IMAGE, PITCH):
        proj = project_point(h, img_pt)
        assert proj == pytest.approx(pitch_pt, abs=1e-6)


def test_interior_point_lands_inside_pitch():
    h = fit_homography(IMAGE, PITCH)
    cx = np.mean([p[0] for p in IMAGE])
    cy = np.mean([p[1] for p in IMAGE])
    u, v = project_point(h, (cx, cy))
    assert 0 < u < 105 and 0 < v < 68


def test_metric_error_scale():
    h = fit_homography(IMAGE, PITCH)
    # Two points on the top edge separated by half the image width span
    # half the pitch length.
    err = metric_error(h, (100, 50), (500, 50))
    assert err == pytest.approx(52.5, rel=0.05)
    assert metric_error(h, (300, 300), (300, 300)) == pytest.approx(0.0)


def test_fit_requires_four_points():
    with pytest.raises(ValueError):
        fit_homography(IMAGE[:3], PITCH[:3])
