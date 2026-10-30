"""A minimal tool-use loop: ask the model, run its tool calls in the world, repeat."""
from __future__ import annotations

import transport

MAX_EMPTY_RETRIES = 3


def run_episode(model, world, system, user, tools, max_calls=30, call=None):
    call = call or transport.call
    msgs = [{"role": "user", "text": user}]
    usage, calls, empty = [], 0, 0
    while True:
        if world.done:
            return {"stop": "done", "calls": calls, "usage": usage}
        if calls >= max_calls:
            return {"stop": "budget", "calls": calls, "usage": usage}
        r = call(model, system, msgs, tools)
        if r["status"] != "ok":
            return {"stop": "error", "error": r["error"], "calls": calls, "usage": usage}
        usage.append(r.get("usage", {}))
        if not r["tool_calls"] and not r["text"].strip():
            # An empty reply (all tokens spent on hidden reasoning) is not a decision to
            # stop: ask the same turn again, a bounded number of times, and count it.
            empty += 1
            if empty <= MAX_EMPTY_RETRIES:
                continue
            return {"stop": "empty_reply", "calls": calls, "usage": usage, "empty_retries": empty - 1}
        if not r["tool_calls"]:
            return {"stop": "no_tool_call", "calls": calls, "usage": usage, "final_text": r["text"],
                    "empty_retries": empty}
        msgs.append({"role": "assistant", "text": r["text"], "tool_calls": r["tool_calls"],
                     "raw_kind": r["raw_kind"], "raw": r["raw"]})
        for c in r["tool_calls"]:
            # Every tool call needs a result, even the ones past the end of the episode.
            if world.done or calls >= max_calls:
                content = "not executed: the episode is over"
            else:
                content = world.call(c["name"], c["input"] or {})
                calls += 1
            msgs.append({"role": "tool", "id": c["id"], "name": c["name"], "content": content})
