"""SoccerNet adapter (design §3, "Fuente principal") — Phase 1 work.

This module defines the interface the rest of the pipeline expects; the
actual download/parsing lands in Phase 1 (dataset construction) and depends
on the `SoccerNet` pip package plus signed download credentials, so it is
deliberately not implemented in the pre-API phase.

Expected flow when implemented:

    frames = load_tracking_frames(root, split="test")
    candidates = [to_item(f) for f in frames if qualifies(f)]

where `qualifies` applies the exclusion criteria (§3: no replays, no
close-ups, ball in frame, play running) and the natural-occlusion selection
from `wheresball.masking`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..schema import Item

DOWNLOAD_HINT = (
    "Install the extra and request access first:\n"
    "  pip install 'wheres-the-ball[soccernet]'\n"
    "  # credentials: https://www.soccer-net.org/ (NDA form)\n"
)


def load_tracking_frames(root: str | Path, split: str = "test") -> Iterator[dict]:
    """Yield per-frame tracking records from a local SoccerNet download.

    Not implemented yet: Phase 1 (see docs/nivel-1-benchmark-vlm.md §10).
    """
    raise NotImplementedError(
        "SoccerNet loading is Phase 1 work and needs dataset credentials.\n" + DOWNLOAD_HINT
    )


def to_item(frame_record: dict) -> Item:
    """Convert a SoccerNet tracking record into an evaluation `Item`.

    Not implemented yet: depends on the record schema of the downloaded
    split; kept here so the target signature is fixed for Phase 1.
    """
    raise NotImplementedError("Phase 1: mapping depends on the downloaded split's schema")
