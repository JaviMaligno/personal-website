"""Core data types for the "Where's the ball?" benchmark.

Coordinates are normalized to the image frame: (0, 0) is the top-left corner,
(1, 1) the bottom-right, per the Level-1 experimental design (§3, "Formato de
respuesta y ground truth"). Velocities are in normalized units per second.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Iterable, Sequence


class BallState(str, Enum):
    """Stratification variable: state of the ball at the target frame (§3)."""

    POSSESSION = "possession"      # possession / dribbling
    SHORT_PASS = "short_pass"      # short pass in flight
    LONG_PASS = "long_pass"        # long pass / clearance / ball in the air
    CONTESTED = "contested"        # loose / contested ball


#: Target stratum shares for the frozen evaluation set (§3).
STRATUM_QUOTAS: dict[BallState, float] = {
    BallState.POSSESSION: 0.40,
    BallState.SHORT_PASS: 0.25,
    BallState.LONG_PASS: 0.20,
    BallState.CONTESTED: 0.15,
}


class Masking(str, Enum):
    """Masking protocol used to hide the ball (§3)."""

    NATURAL = "natural_occlusion"
    DEGRADED = "global_degradation"
    INPAINTED = "local_inpainting"


class TemporalContext(str, Enum):
    """Temporal context factor of the condition matrix (§5)."""

    SINGLE_FRAME = "single_frame"
    MULTI_FRAME = "multi_frame"    # 4 frames, t-3s .. t
    VIDEO = "video"


class Knowledge(str, Enum):
    """Game-knowledge factor of the condition matrix (§5)."""

    NEUTRAL = "neutral"
    INFORMED = "informed"


@dataclass(frozen=True)
class Player:
    """A tracked player at the target frame, with instantaneous velocity."""

    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    team: str | None = None
    player_id: str | None = None

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    @property
    def position(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True)
class Item:
    """One evaluation item: a target frame (or clip ending at it)."""

    item_id: str
    players: tuple[Player, ...]
    ball: tuple[float, float]                # ground truth (bbox center)
    state: BallState
    masking: Masking
    possessor_id: str | None = None          # ground-truth possessor, if any
    frame_refs: tuple[str, ...] = ()         # image/clip identifiers or paths
    play_area: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)


@dataclass(frozen=True)
class Prediction:
    """A system's answer for one item (§3): point + declared uncertainty."""

    x: float
    y: float
    uncertainty_radius: float = 0.0
    confidence: float = 50.0                 # declared confidence, 0-100
    rationale: str = ""

    @property
    def position(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True)
class Condition:
    """One cell of the experimental condition matrix (§5)."""

    temporal: TemporalContext
    knowledge: Knowledge
    masking: Masking

    @property
    def key(self) -> str:
        return f"{self.temporal.value}|{self.knowledge.value}|{self.masking.value}"


# ---------------------------------------------------------------------------
# Serialization: the frozen evaluation set is stored as a JSON manifest whose
# hash is recorded before any model is run (informal pre-registration, §7).
# ---------------------------------------------------------------------------

def items_to_json(items: Sequence[Item]) -> str:
    payload = [asdict(it) for it in items]
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def items_from_json(text: str) -> list[Item]:
    raw = json.loads(text)
    items = []
    for entry in raw:
        players = tuple(Player(**p) for p in entry.pop("players"))
        entry["ball"] = tuple(entry["ball"])
        entry["frame_refs"] = tuple(entry.get("frame_refs", ()))
        entry["play_area"] = tuple(entry.get("play_area", (0.0, 0.0, 1.0, 1.0)))
        entry["state"] = BallState(entry["state"])
        entry["masking"] = Masking(entry["masking"])
        items.append(Item(players=players, **entry))
    return items


def manifest_hash(items: Sequence[Item]) -> str:
    """Stable hash identifying a frozen evaluation set."""
    return hashlib.sha256(items_to_json(items).encode("utf-8")).hexdigest()


def stratum_counts(items: Iterable[Item]) -> dict[BallState, int]:
    counts = {state: 0 for state in BallState}
    for it in items:
        counts[it.state] += 1
    return counts
