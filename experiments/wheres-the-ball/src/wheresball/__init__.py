""""Where's the ball?" — Level-1 benchmark: can generalist VLMs locate the
unseen ball from player configuration and movement alone?

Design documents live in docs/; this package implements everything that does
not require calling a real model: schema, geometric baselines, masking,
metrics, statistics, prompts, and the evaluation harness (with a mock VLM).
"""

__version__ = "0.1.0"

from .schema import (  # noqa: F401
    BallState,
    Condition,
    Item,
    Knowledge,
    Masking,
    Player,
    Prediction,
    TemporalContext,
)
