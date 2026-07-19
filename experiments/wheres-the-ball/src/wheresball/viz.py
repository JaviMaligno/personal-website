"""Item rendering: schematic pitch images from tracking data (PIL only).

Two purposes:

1. Feed the *image* pipeline before real footage exists: the API clients take
   image bytes, so `synthetic_image_provider` renders items (ball hidden) and
   the whole VLM path — encoding, prompts, parsing — runs against them.
2. Qualitative figures for the article: the same renderer with the ball (and
   optionally a prediction) drawn on top.

These are schematic top-down views, not broadcast frames; results on them
measure pipeline health, never model ability.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw

from .schema import Condition, Item, Prediction, TemporalContext

TEAM_COLORS = {"A": (235, 235, 235), "B": (40, 90, 200), None: (200, 200, 60)}
PITCH_GREEN = (34, 120, 54)
BALL_COLOR = (255, 165, 0)
PRED_COLOR = (220, 40, 40)


def _to_px(x: float, y: float, size: tuple[int, int]) -> tuple[float, float]:
    return (x * size[0], y * size[1])


def render_item(
    item: Item,
    size: tuple[int, int] = (640, 400),
    show_ball: bool = False,
    prediction: Prediction | None = None,
    time_offset_s: float = 0.0,
    player_radius: int = 6,
) -> Image.Image:
    """Render one frame. `time_offset_s` back-projects players along their
    velocity (positions at t + offset), which is how past frames of the
    multi-frame condition are synthesized consistently with the tracking."""
    img = Image.new("RGB", size, PITCH_GREEN)
    draw = ImageDraw.Draw(img)

    # Pitch markings: border and halfway line, enough for spatial anchoring.
    x0, y0, x1, y1 = item.play_area
    left, top = _to_px(x0 + 0.01, y0 + 0.01, size)
    right, bottom = _to_px(x1 - 0.01, y1 - 0.01, size)
    draw.rectangle([left, top, right, bottom], outline=(255, 255, 255), width=2)
    mid_x = (left + right) / 2
    draw.line([mid_x, top, mid_x, bottom], fill=(255, 255, 255), width=2)

    for p in item.players:
        px, py = _to_px(p.x + p.vx * time_offset_s, p.y + p.vy * time_offset_s, size)
        r = player_radius
        draw.ellipse([px - r, py - r, px + r, py + r], fill=TEAM_COLORS.get(p.team))
        # Velocity arrow (1 s lookahead) so motion is visible in a still frame.
        if p.speed > 1e-4:
            draw.line([px, py, px + p.vx * size[0], py + p.vy * size[1]],
                      fill=(20, 20, 20), width=2)

    if show_ball:
        bx, by = _to_px(*item.ball, size)
        r = max(3, player_radius - 2)
        draw.ellipse([bx - r, by - r, bx + r, by + r], fill=BALL_COLOR)

    if prediction is not None:
        qx, qy = _to_px(prediction.x, prediction.y, size)
        s = player_radius + 2
        draw.line([qx - s, qy - s, qx + s, qy + s], fill=PRED_COLOR, width=3)
        draw.line([qx - s, qy + s, qx + s, qy - s], fill=PRED_COLOR, width=3)
        if prediction.uncertainty_radius > 0:
            ur = prediction.uncertainty_radius * size[0]
            draw.ellipse([qx - ur, qy - ur, qx + ur, qy + ur], outline=PRED_COLOR, width=2)

    return img


def to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


#: Frame offsets (seconds relative to t) for the multi-frame condition (§5).
MULTI_FRAME_OFFSETS = (-3.0, -2.0, -1.0, 0.0)


def synthetic_image_provider(size: tuple[int, int] = (640, 400)):
    """Image provider for API/mock clients: renders the item without the ball.

    Single-frame conditions get one image; multi-frame gets 4 frames covering
    t-3s..t, back-projected along player velocities.
    """

    def provide(item: Item, condition: Condition) -> list[bytes]:
        if condition.temporal == TemporalContext.SINGLE_FRAME:
            offsets: tuple[float, ...] = (0.0,)
        else:
            offsets = MULTI_FRAME_OFFSETS
        return [
            to_png_bytes(render_item(item, size=size, show_ball=False, time_offset_s=dt))
            for dt in offsets
        ]

    return provide
