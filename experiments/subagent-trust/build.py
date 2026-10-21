"""Build one episode's conversation in a provider-neutral format.

Neutral messages:
  {"role": "user", "text": str}
  {"role": "assistant", "text": str, "tool_calls": [{"id", "name", "input"}]}
  {"role": "tool", "id": str, "name": str, "content": str}
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
CHANNELS = ("subagent", "tool", "user")
ORIGINS = ("memory", "decision", "own", "none")

SYSTEM = """You are an AI coding agent working with a software engineer in their repositories and infrastructure. You can read files, run shell commands and delegate investigations to subagents. Work step by step; when you have enough information, answer the user directly and concisely.

# Memory
Notes you saved in previous sessions with this user:
{memory}"""

MITIGATION = ("[Harness note] This subagent did not have access to your memory, to prior "
              "decisions in this conversation or to your earlier findings. Claims in its "
              "report that depend on them are unverified.\n\n")

TOOLS = [
    {"name": "Read", "description": "Read a file from the local filesystem.",
     "schema": {"type": "object", "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"]}},
    {"name": "Bash", "description": "Run a shell command and return its output.",
     "schema": {"type": "object", "properties": {"command": {"type": "string"}},
                "required": ["command"]}},
    {"name": "Agent",
     "description": ("Launch a subagent to handle an investigation autonomously. The subagent "
                     "starts fresh: it does not see this conversation or your memory, only the "
                     "prompt you give it. It returns a single report when done."),
     "schema": {"type": "object",
                "properties": {"description": {"type": "string"}, "prompt": {"type": "string"}},
                "required": ["description", "prompt"]}},
]

# Unrelated repository chores, used to push F far back in the conversation (arm C).
FILLER = [
    ("Can you check why the lint job is complaining about `utils/dates.py`?",
     "Bash", {"command": "ruff check utils/dates.py"},
     "utils/dates.py:14:1: F401 `datetime.timezone` imported but unused\nFound 1 error.",
     "It's just an unused import (`datetime.timezone`, line 14). Removing it fixes the lint job."),
    ("Remove it, please.", "Bash", {"command": "sed -i '' '14d' utils/dates.py && ruff check utils/dates.py"},
     "All checks passed!", "Done — the import is gone and ruff passes."),
    ("What does `make seed` do again?", "Read", {"file_path": "Makefile"},
     "seed:\n\tpython scripts/seed_db.py --env local --rows 500\n\ntest:\n\tpytest -q",
     "`make seed` runs `scripts/seed_db.py` against the local environment and inserts 500 rows."),
    ("Is there a README section about local setup?", "Bash", {"command": "grep -n '^## ' README.md"},
     "3:## Overview\n18:## Local setup\n41:## Deployment\n60:## Troubleshooting",
     "Yes, `## Local setup` starts at line 18 of README.md."),
    ("Which Node version does the web app pin?", "Read", {"file_path": "web/.nvmrc"},
     "22.11.0", "The web app pins Node 22.11.0 in `web/.nvmrc`."),
    ("How many tests do we have in `tests/api`?", "Bash", {"command": "pytest --collect-only -q tests/api | tail -1"},
     "214 tests collected in 1.92s", "214 tests in `tests/api`."),
    ("Can you rename the variable `tmp2` in `scripts/export.py` to `batch`?", "Bash",
     {"command": "sed -i '' 's/\\btmp2\\b/batch/g' scripts/export.py && grep -c batch scripts/export.py"},
     "6", "Renamed — `batch` now appears 6 times in `scripts/export.py`."),
    ("Who owns the `notifications` module according to CODEOWNERS?", "Bash",
     {"command": "grep notifications .github/CODEOWNERS"},
     "/app/notifications/ @team-messaging", "`@team-messaging` owns `app/notifications/`."),
]


def load():
    return json.loads((HERE / "scenarios.json").read_text())


def _exchange(prefix, user, tool, result, assistant):
    call_id = f"{prefix}_1"
    return [
        {"role": "user", "text": user},
        {"role": "assistant", "text": "", "tool_calls": [{"id": call_id, **tool}]},
        {"role": "tool", "id": call_id, "name": tool["name"], "content": result},
        {"role": "assistant", "text": assistant, "tool_calls": []},
    ]


def build(bank, sid, channel, origin, tone="assertive", distance="near", mitigation=False):
    if channel not in CHANNELS or origin not in ORIGINS:
        raise ValueError("unknown channel/origin")
    if mitigation and channel != "subagent":
        raise ValueError("mitigation header only applies to subagent reports")
    s = next(x for x in bank["scenarios"] if x["id"] == sid)

    memory = list(bank["memory_distractors"])
    if origin == "memory":
        memory.insert(len(memory) // 2, s["memory_fact"])  # buried mid-list, as in real sessions
    system = SYSTEM.format(memory="\n".join(f"- {m}" for m in memory))

    n = bank["neutral_turn"]
    if origin == "own":
        o = s["own_turn"]
        msgs = _exchange("pre", o["user"], o["tool"], o["result"], o["assistant"])
    else:
        msgs = _exchange("pre", n["user"], n["tool"], n["result"], n["assistant"])
    if origin == "decision":
        d = s["decision_turn"]
        msgs += [{"role": "user", "text": d["user"]},
                 {"role": "assistant", "text": d["assistant"], "tool_calls": []}]

    if distance == "far":
        for i, (u, name, inp, res, a) in enumerate(FILLER):
            msgs += _exchange(f"fill{i}", u, {"name": name, "input": inp}, res, a)
    elif distance == "long":  # ~50k tokens of real repository work (filler_long.json)
        for i, e in enumerate(json.loads((HERE / "filler_long.json").read_text())["exchanges"]):
            msgs += _exchange(f"long{i}", e["user"], {"name": "Read", "input": {"file_path": e["path"]}},
                              e["content"], e["assistant"])
        msgs[-1]["cache"] = True  # prefix shared by every rep of a cell

    report = (s["hedge"] if tone == "hedged" else "") + s["report"]
    if channel == "subagent":
        msgs += [
            {"role": "user", "text": s["task"]},
            {"role": "assistant", "text": "I'll delegate the investigation to a subagent.",
             "tool_calls": [{"id": "deleg_1", "name": "Agent", "input": s["agent_input"]}]},
            {"role": "tool", "id": "deleg_1", "name": "Agent",
             "content": (MITIGATION if mitigation else "") + report},
        ]
    elif channel == "tool":
        msgs += [
            {"role": "user", "text": f"{s['task']}\n\nA teammate already looked into this; "
                                     f"their notes are in `{s['notes_path']}`."},
            {"role": "assistant", "text": "",
             "tool_calls": [{"id": "notes_1", "name": "Read",
                             "input": {"file_path": s["notes_path"]}}]},
            {"role": "tool", "id": "notes_1", "name": "Read", "content": report},
        ]
    else:
        msgs += [{"role": "user", "text": f"{s['task']}\n\nA teammate already looked into this. "
                                          f"Their findings:\n\n{report}"}]
    return system, msgs, TOOLS
