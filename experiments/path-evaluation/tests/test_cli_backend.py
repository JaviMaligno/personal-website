import json

from cli_backend import build_cmd, parse_stream


def test_build_cmd_isolates_the_session():
    cmd = build_cmd({"model": "claude-haiku-5-5"}, "SYS", "USER", "cfg.json", 40)
    joined = " ".join(cmd)
    for flag in ("--strict-mcp-config", "--no-session-persistence", "--verbose"):
        assert flag in cmd
    assert cmd[cmd.index("--setting-sources") + 1] == ""
    assert cmd[cmd.index("--tools") + 1] == ""
    assert cmd[cmd.index("--system-prompt") + 1] == "SYS"
    assert cmd[cmd.index("--allowedTools") + 1] == "mcp__world"
    assert "--bare" not in joined


def test_parse_stream_dedupes_usage_by_message_id():
    lines = [
        {"type": "system", "subtype": "init", "model": "claude-haiku-5-5"},
        {"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 2, "output_tokens": 8}}},
        {"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 2, "output_tokens": 8}}},
        {"type": "assistant", "message": {"id": "m2", "usage": {"input_tokens": 5, "output_tokens": 1}}},
        {"type": "result", "subtype": "success", "num_turns": 2, "result": "ok"},
    ]
    usage, result, model = parse_stream("\n".join(json.dumps(l) for l in lines) + "\nnot json\n")
    assert usage == [{"input_tokens": 2, "output_tokens": 8}, {"input_tokens": 5, "output_tokens": 1}]
    assert result["subtype"] == "success" and model == "claude-haiku-5-5"
