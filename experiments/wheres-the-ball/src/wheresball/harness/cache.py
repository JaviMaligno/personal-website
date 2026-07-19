"""Disk cache for model responses (design §10, Phase 3: "caché de respuestas").

Keys include model id, item id, condition and prompt version, so changing any
of them invalidates only the affected cells of the experiment matrix. Values
are stored as one JSON file per key — trivially inspectable and diff-able.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from ..schema import Condition, Prediction


class ResponseCache:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, model_id: str, item_id: str, condition: Condition, prompt_version: str) -> Path:
        key = f"{model_id}|{item_id}|{condition.key}|{prompt_version}"
        digest = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.root / f"{digest}.json"

    def get(
        self, model_id: str, item_id: str, condition: Condition, prompt_version: str
    ) -> Prediction | None:
        path = self._path(model_id, item_id, condition, prompt_version)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Prediction(**data["prediction"])

    def put(
        self,
        model_id: str,
        item_id: str,
        condition: Condition,
        prompt_version: str,
        prediction: Prediction,
    ) -> None:
        path = self._path(model_id, item_id, condition, prompt_version)
        payload = {
            "model_id": model_id,
            "item_id": item_id,
            "condition": condition.key,
            "prompt_version": prompt_version,
            "prediction": asdict(prediction),
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def __len__(self) -> int:
        return sum(1 for _ in self.root.glob("*.json"))
