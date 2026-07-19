"""VLM client interface + mock implementation.

Real API clients (Claude / GPT / Gemini / open VLM, design §4) are Phase 3
work and intentionally absent: everything in this repo must run without
touching a paid model. `MockVLMClient` stands in for them so the full
harness — prompts, cache, runner, metrics, stats — is exercised end-to-end.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

from ..schema import Condition, Item, Prediction


class VLMClient(Protocol):
    """A system that answers "where is the ball?" for one item."""

    model_id: str

    def predict(self, item: Item, condition: Condition, prompt: str) -> Prediction:
        """Return a prediction for the item under the given condition."""
        ...


class MockVLMClient:
    """Deterministic fake VLM for pipeline development.

    Behaves like a plausible mid-quality model: predicts a noisy
    speed-weighted centroid of the players, declares confidence that shrinks
    with player spread, and honors the temporal-context condition by using
    velocities only when more than one frame would be visible. Deterministic
    per (item, condition, seed) so cached and fresh runs agree.
    """

    def __init__(self, model_id: str = "mock-vlm", noise: float = 0.05, seed: int = 0):
        self.model_id = model_id
        self.noise = noise
        self.seed = seed

    def _rng(self, item: Item, condition: Condition) -> np.random.Generator:
        key = f"{self.model_id}:{self.seed}:{item.item_id}:{condition.key}"
        digest = hashlib.sha256(key.encode()).digest()
        return np.random.default_rng(int.from_bytes(digest[:8], "big"))

    def predict(self, item: Item, condition: Condition, prompt: str) -> Prediction:
        rng = self._rng(item, condition)
        pts = np.array([p.position for p in item.players])
        speeds = np.array([p.speed for p in item.players])

        # A single frame carries no velocity information; multi-frame does.
        use_velocity = condition.temporal.value != "single_frame"
        weights = speeds + 1e-6 if use_velocity else np.ones(len(pts))
        cx, cy = np.average(pts, axis=0, weights=weights)

        x = float(np.clip(cx + rng.normal(0, self.noise), 0, 1))
        y = float(np.clip(cy + rng.normal(0, self.noise), 0, 1))

        spread = float(pts.std(axis=0).mean())
        confidence = float(np.clip(90 - 200 * spread + rng.normal(0, 5), 5, 95))
        return Prediction(
            x=x,
            y=y,
            uncertainty_radius=float(np.clip(2.5 * self.noise + spread / 4, 0.02, 0.5)),
            confidence=confidence,
            rationale="mock: noisy speed-weighted centroid",
        )
