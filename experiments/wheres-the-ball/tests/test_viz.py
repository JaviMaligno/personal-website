import numpy as np
from PIL import Image
import io

from wheresball.dataset import generate_items
from wheresball.schema import Condition, Knowledge, Masking, Prediction, TemporalContext
from wheresball.viz import render_item, synthetic_image_provider, to_png_bytes

SINGLE = Condition(TemporalContext.SINGLE_FRAME, Knowledge.NEUTRAL, Masking.NATURAL)
MULTI = Condition(TemporalContext.MULTI_FRAME, Knowledge.INFORMED, Masking.NATURAL)


def test_render_returns_image_of_requested_size():
    item = generate_items(4, seed=0)[0]
    img = render_item(item, size=(320, 200))
    assert img.size == (320, 200)


def test_ball_only_drawn_when_requested():
    item = generate_items(4, seed=0)[0]
    hidden = np.asarray(render_item(item, show_ball=False))
    shown = np.asarray(render_item(item, show_ball=True))
    assert not np.array_equal(hidden, shown)


def test_prediction_overlay_changes_image():
    item = generate_items(4, seed=0)[0]
    base = np.asarray(render_item(item))
    with_pred = np.asarray(
        render_item(item, prediction=Prediction(x=0.5, y=0.5, uncertainty_radius=0.1))
    )
    assert not np.array_equal(base, with_pred)


def test_provider_frame_counts_per_condition():
    provider = synthetic_image_provider(size=(160, 100))
    item = generate_items(4, seed=1)[0]
    assert len(provider(item, SINGLE)) == 1
    frames = provider(item, MULTI)
    assert len(frames) == 4
    # Frames are valid PNGs and differ over time (players move).
    decoded = [np.asarray(Image.open(io.BytesIO(f))) for f in frames]
    assert any(not np.array_equal(decoded[0], d) for d in decoded[1:])


def test_png_bytes_roundtrip():
    item = generate_items(4, seed=2)[0]
    data = to_png_bytes(render_item(item))
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
