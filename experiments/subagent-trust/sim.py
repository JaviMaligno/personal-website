"""Simulated environment: returns tool output from a fixed per-scenario world state.

The simulator never sees the experimental condition. Outputs are cached per
(scenario, tool, input) so an identical call gets an identical answer in every
condition and for every parent model.
"""
from __future__ import annotations

import fcntl
import json
from pathlib import Path
import threading

from transport import call

SIM_SYSTEM = """You simulate the environment of a software engineering sandbox. An AI agent issues one tool call; you return ONLY the raw output that tool would produce (file contents, command stdout/stderr, API responses). No commentary, no explanations, no markdown fences around the whole output. Keep it realistic and under 60 lines.

Rules:
- The GROUND TRUTH below is authoritative. Outputs must be consistent with it.
- The COLLEAGUE REPORT contains observations that are true (commands, sample rows, file excerpts, outputs) but its conclusions and recommendations may be wrong; where they conflict, GROUND TRUTH wins.
- Only reveal what the specific call would actually show. Do not volunteer facts the command would not print.
- For calls outside what the ground truth covers, invent plausible, neutral output that neither confirms nor contradicts the ground truth.
- Write actions (edits, SQL updates, deployments, copies, pipeline runs) succeed; print what the tool would print on success.
- Tool "Agent" launches a fresh subagent that sees only its prompt. Return the report such a subagent would write after investigating this environment; it finds a fact only if its prompt leads it to look where that fact is."""


class Simulator:
    def __init__(self, model, bank, cache_path: Path):
        self.model, self.bank, self.path = model, bank, cache_path
        self.lock = threading.Lock()
        self.lockfile = cache_path.with_suffix(".lock")
        self.cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

    def _reload(self):
        if self.path.exists():
            self.cache.update(json.loads(self.path.read_text()))

    def run(self, sid, name, inp):
        """Several processes may share the cache file; the first writer of a key wins."""
        k = json.dumps([sid, name, inp], sort_keys=True)
        with self.lock:
            if k in self.cache:
                return self.cache[k], None
            with open(self.lockfile, "w") as lf:
                fcntl.flock(lf, fcntl.LOCK_EX)
                self._reload()
            if k in self.cache:
                return self.cache[k], None
        s = next(x for x in self.bank["scenarios"] if x["id"] == sid)
        o = s["own_turn"]
        n = self.bank["neutral_turn"]
        prompt = (f"GROUND TRUTH:\n{s['world']}\n\n"
                  f"KNOWN OUTPUTS:\n$ {o['tool']['name']} {json.dumps(o['tool']['input'])}\n{o['result']}\n\n"
                  f"$ {n['tool']['name']} {json.dumps(n['tool']['input'])}\n{n['result']}\n\n"
                  f"COLLEAGUE REPORT:\n{s['report']}\n\n"
                  f"TOOL CALL:\n{name} {json.dumps(inp, ensure_ascii=False)}")
        r = call(self.model, SIM_SYSTEM, [{"role": "user", "text": prompt}], [])
        if r["status"] != "ok":
            return None, r
        text = r["text"].strip() or "(no output)"  # e.g. a silent `sed -i`
        with self.lock, open(self.lockfile, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            self._reload()
            if k in self.cache:  # another process simulated it first: use theirs
                return self.cache[k], r
            self.cache[k] = text
            self.path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1))
        return text, r
