"""Kokoro text-to-speech, the local fallback voice for scripts/tts.ts.

Input on stdin: {"items": [{"text", "voice", "lang", "speed", "out"}, ...]}.
Writes one WAV per item at Kokoro's native rate; tts.ts resamples it.
Model files live in $KOKORO_MODELS or ~/.cache/kokoro and are fetched on first use.
Run with: uv run --with kokoro-onnx --with soundfile python scripts/kokoro.py
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

import soundfile
from kokoro_onnx import Kokoro

MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"


def model_dir() -> Path:
    folder = Path(os.environ.get("KOKORO_MODELS", Path.home() / ".cache" / "kokoro"))
    folder.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        target = folder / name
        if not target.exists():
            print(f"fetching {name} into {folder} (one time, ~350 MB)", file=sys.stderr)
            urllib.request.urlretrieve(f"{RELEASE}/{name}", target)
    return folder


def main() -> None:
    jobs = json.load(sys.stdin)["items"]
    folder = model_dir()
    tts = Kokoro(str(folder / MODEL_FILES[0]), str(folder / MODEL_FILES[1]))
    for job in jobs:
        samples, rate = tts.create(job["text"], voice=job["voice"], speed=float(job.get("speed") or 1), lang=job["lang"])
        soundfile.write(job["out"], samples, rate)


if __name__ == "__main__":
    main()
