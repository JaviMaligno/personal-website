"""Parser for MOT-format tracking as distributed by SoccerNet Tracking.

SoccerNet Tracking sequences ship as MOT challenge files:

    SNMOT-XXX/
      gameinfo.ini      # trackletID_N = class ("player team left", "ball", ...)
      gt/gt.txt         # frame,track_id,x,y,w,h,conf,...   (pixels, top-left)
      seqinfo.ini       # imWidth, imHeight, frameRate

This module turns those into evaluation `Item`s: player positions/velocities
(finite differences over a window) and ball ground truth, normalized by the
image size. Pure parsing + arithmetic — runs offline on fixture strings.

VERIFY LOCALLY (Phase 1): exact class labels in gameinfo.ini and column count
of the downloaded split before trusting a bulk conversion; the ball-state
heuristic below is provisional until validated against real clips (TODO.md).
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass

from ..schema import BallState, Item, Masking, Player


@dataclass(frozen=True)
class MotRecord:
    frame: int
    track_id: int
    x: float  # bbox top-left, pixels
    y: float
    w: float
    h: float
    conf: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.w / 2, self.y + self.h / 2)


def parse_mot(text: str) -> list[MotRecord]:
    records = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 6:
            raise ValueError(f"malformed MOT line: {line!r}")
        frame, track_id = int(parts[0]), int(parts[1])
        x, y, w, h = (float(v) for v in parts[2:6])
        conf = float(parts[6]) if len(parts) > 6 else 1.0
        records.append(MotRecord(frame, track_id, x, y, w, h, conf))
    return records


_TRACKLET = re.compile(r"trackletID_(\d+)\s*=\s*(.+)")


def parse_gameinfo(text: str) -> dict[int, str]:
    """Map track_id -> class label from a gameinfo.ini body."""
    labels = {}
    for line in text.splitlines():
        match = _TRACKLET.match(line.strip())
        if match:
            labels[int(match.group(1))] = match.group(2).strip().lower()
    return labels


def is_ball_label(label: str) -> bool:
    return "ball" in label


def is_player_label(label: str) -> bool:
    return "player" in label or "goalkeeper" in label


# ---------------------------------------------------------------------------
# Ball-state heuristic (provisional; §3 stratification).
# ---------------------------------------------------------------------------

def classify_ball_state(
    ball_speed: float,           # normalized units / s
    dist_nearest: float,         # normalized distance ball -> nearest player
    n_players_close: int,        # players within `close_radius`
    possession_dist: float = 0.03,
    fast_ball: float = 0.25,
    close_radius: float = 0.06,
) -> BallState:
    """Provisional heuristic pending validation on real clips (Phase 1):
    a slow ball at a player's feet is possession; a fast ball far from
    everyone is a long pass; several players crowding a slow ball is a
    contested ball; the rest are short passes."""
    if dist_nearest <= possession_dist and ball_speed < fast_ball:
        return BallState.CONTESTED if n_players_close >= 3 else BallState.POSSESSION
    if ball_speed >= fast_ball and dist_nearest > close_radius:
        return BallState.LONG_PASS
    return BallState.SHORT_PASS


def tracking_to_item(
    records: list[MotRecord],
    labels: dict[int, str],
    target_frame: int,
    image_size: tuple[int, int],
    sequence_id: str,
    fps: float = 25.0,
    velocity_window: int = 5,
) -> Item:
    """Build one evaluation Item at `target_frame` from a sequence's records.

    Velocities are finite differences over `velocity_window` frames. The ball
    ground truth is the annotated bbox center. Raises if the ball annotation
    is missing at the target frame (such frames are a separate condition, §3).
    """
    width, height = image_size
    by_frame: dict[int, dict[int, MotRecord]] = defaultdict(dict)
    for r in records:
        by_frame[r.frame][r.track_id] = r

    now = by_frame.get(target_frame)
    if not now:
        raise ValueError(f"no records at frame {target_frame}")
    past = by_frame.get(target_frame - velocity_window, {})
    dt = velocity_window / fps

    def norm(px: float, py: float) -> tuple[float, float]:
        return (px / width, py / height)

    players: list[Player] = []
    ball_now: tuple[float, float] | None = None
    ball_speed = 0.0
    for track_id, record in sorted(now.items()):
        label = labels.get(track_id, "")
        cx, cy = norm(*record.center)
        vx = vy = 0.0
        if track_id in past:
            ox, oy = norm(*past[track_id].center)
            vx, vy = (cx - ox) / dt, (cy - oy) / dt
        if is_ball_label(label):
            ball_now = (cx, cy)
            ball_speed = math.hypot(vx, vy)
        elif is_player_label(label):
            players.append(Player(x=cx, y=cy, vx=vx, vy=vy, player_id=f"t{track_id}"))

    if ball_now is None:
        raise ValueError(f"no ball annotation at frame {target_frame} of {sequence_id}")
    if not players:
        raise ValueError(f"no players at frame {target_frame} of {sequence_id}")

    dists = [math.hypot(p.x - ball_now[0], p.y - ball_now[1]) for p in players]
    dist_nearest = min(dists)
    n_close = sum(d <= 0.06 for d in dists)
    state = classify_ball_state(ball_speed, dist_nearest, n_close)
    possessor_id = None
    if state == BallState.POSSESSION:
        possessor_id = players[dists.index(dist_nearest)].player_id

    return Item(
        item_id=f"{sequence_id}-f{target_frame:06d}",
        players=tuple(players),
        ball=ball_now,
        state=state,
        masking=Masking.NATURAL,
        possessor_id=possessor_id,
        frame_refs=(f"{sequence_id}/img1/{target_frame:06d}.jpg",),
    )
