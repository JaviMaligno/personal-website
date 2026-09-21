"""Immutable snapshots, atomic per-job histories, and a single-writer run lock."""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from bank import digest


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive:
            os.link(tmp, path)  # Atomic fail-if-exists, never replace a freeze.
        else:
            os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def freeze(path, payload):
    write(path, {"sha256": digest(payload), "payload": payload}, exclusive=True)


def frozen(path):
    envelope = read(path)
    if digest(envelope["payload"]) != envelope["sha256"]:
        raise ValueError(f"Modified snapshot: {Path(path).name}")
    return envelope["payload"]


@contextlib.contextmanager
def lock(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / ".lock"
    try:
        with path.open("x") as handle:
            handle.write(f"pid={os.getpid()}\nstarted={now()}\n")
    except FileExistsError:
        raise ValueError("Run is locked. If its process died, inspect .lock before removing it.")
    try:
        yield
    finally:
        path.unlink()


def job_path(root, job):
    return Path(root) / "calls" / (digest(job) + ".json")


def latest(root, job):
    path = job_path(root, job)
    if not path.exists():
        return None
    history = read(path)
    if history["job"] != job:
        raise ValueError("Job hash mismatch")
    return history["attempts"][-1]


def call(root, job, model, complete):
    path = job_path(root, job)
    history = read(path) if path.exists() else {"job": job, "attempts": []}
    entry = {"status": "interrupted", "started": now(), "attempt": len(history["attempts"]) + 1}
    history["attempts"].append(entry)
    write(path, history)  # A crash leaves an explicit ambiguous/in-flight attempt.
    result = complete(model, job["prompt"])
    entry.update(result)
    entry["finished"] = now()
    write(path, history)
    return entry
