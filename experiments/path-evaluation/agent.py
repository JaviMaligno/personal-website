"""A minimal tool-use loop: ask the model, run its tool calls in the world, repeat."""
from __future__ import annotations

import transport


def run_episode(model, world, system, user, tools, max_calls=30, call=None):
    call = call or transport.call
    msgs = [{"role": "user", "text": user}]
    usage, calls = [], 0
    while True:
        if world.done:
            return {"stop": "done", "calls": calls, "usage": usage}
        if calls >= max_calls:
            return {"stop": "budget", "calls": calls, "usage": usage}
        r = call(model, system, msgs, tools)
        if r["status"] != "ok":
            return {"stop": "error", "error": r["error"], "calls": calls, "usage": usage}
        usage.append(r.get("usage", {}))
        if not r["tool_calls"]:
            return {"stop": "no_tool_call", "calls": calls, "usage": usage, "final_text": r["text"]}
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
