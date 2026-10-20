import json
from pathlib import Path

import pytest

from aa import config, runner
from aa.agents import Usage, classify_infra, parse_claude_stream, parse_codex_stream
from aa.runner import Job, Scheduler, backoff_s, build_queue, classify_status

F = Path(__file__).parent / "fixtures"


def _lines(name: str) -> list[str]:
    return (F / name).read_text().splitlines()


# --------------------------------------------------------------------------- plan tests

def test_claude_ok_has_usage():
    usage, outcome = parse_claude_stream(_lines("claude-stream-ok.jsonl"))
    assert outcome == "ok" and usage.input_tokens > 0 and usage.turns >= 1


def test_claude_ok_usage_from_real_fixture():
    # Recorded 2026-10-05 in aa-actual:A (Claude Code 2.1.289, claude-sonnet-5-5):
    # one Bash tool call, then the answer. The `result` usage is authoritative
    # (input 4 + cache creation 14200 + cache read 34751; output 144, while the
    # assistant events only carry streaming snapshots summing to 59). The stream
    # also contains a rate_limit_event with status allowed_warning: not infra.
    usage, outcome = parse_claude_stream(_lines("claude-stream-ok.jsonl"))
    assert outcome == "ok"
    assert (usage.input_tokens, usage.cached_input_tokens, usage.output_tokens) == (48955, 34751, 144)
    assert usage.turns == 2 and usage.tool_calls == 1


def test_claude_rejected_rate_limit_or_api_status_is_infra():
    base = {"type": "result", "subtype": "error_during_execution", "is_error": True,
            "num_turns": 1, "result": "API Error"}
    rl = {"type": "rate_limit_event", "rate_limit_info": {"status": "rejected"}}
    assert parse_claude_stream(_cl(rl, base))[1] == "infra"
    assert parse_claude_stream(_cl(base | {"subtype": "success", "api_error_status": 529}))[1] == "infra"
    ok = {"type": "result", "subtype": "success", "is_error": False, "num_turns": 1,
          "result": "done", "api_error_status": None}
    assert parse_claude_stream(_cl({"type": "rate_limit_event",
                                    "rate_limit_info": {"status": "allowed_warning"}}, ok))[1] == "ok"


def test_claude_usage_limit_is_infra_even_with_exit_0():
    _, outcome = parse_claude_stream(_lines("claude-stream-usage-limit.jsonl"))
    assert outcome == "infra"


def test_codex_ok_and_ratelimit():
    assert parse_codex_stream(_lines("codex-ok.jsonl"))[1] == "ok"
    assert parse_codex_stream(_lines("codex-ratelimit.jsonl"))[1] == "infra"


def test_classify_infra():
    assert classify_infra("Claude AI usage limit reached|1760000000")
    assert classify_infra("Error: 429 Too Many Requests")
    assert classify_infra("You've hit your usage limit")
    assert not classify_infra("Tests failed: 3")


# --------------------------------------------------------------------------- Codex real fixture

def test_codex_ok_usage_from_real_fixture():
    usage, _ = parse_codex_stream(_lines("codex-ok.jsonl"))
    assert usage.input_tokens > 0 and usage.output_tokens > 0
    assert 0 <= usage.cached_input_tokens <= usage.input_tokens
    # Recorded 2026-10-05: gpt-6-luna answered from a guess without running a
    # command, so the real stream has one agent_message and no tool items; the
    # three config-warning `error` items must not make it infra.
    assert (usage.input_tokens, usage.cached_input_tokens, usage.output_tokens) == (19256, 11008, 20)
    assert usage.tool_calls == 0 and usage.turns == 1


def test_codex_counts_tool_items_once():
    lines = _cl(
        {"type": "turn.started"},
        {"type": "item.started", "item": {"id": "i1", "type": "command_execution", "command": "ls"}},
        {"type": "item.completed", "item": {"id": "i1", "type": "command_execution", "command": "ls"}},
        {"type": "item.completed", "item": {"id": "i2", "type": "file_change", "changes": []}},
        {"type": "item.completed", "item": {"id": "i3", "type": "agent_message", "text": "done"}},
        {"type": "turn.completed", "usage": {"input_tokens": 9, "cached_input_tokens": 4, "output_tokens": 3}},
    )
    usage, outcome = parse_codex_stream(lines)
    assert (usage.tool_calls, usage.turns, outcome) == (2, 3, "ok")


def test_codex_truncated_stream_is_infra():
    lines = _lines("codex-ok.jsonl")
    cut = [ln for ln in lines if '"turn.completed"' not in ln]
    assert parse_codex_stream(cut)[1] == "infra"


# --------------------------------------------------------------------------- Claude synthetic streams
# Shapes follow the documented `--output-format stream-json --verbose` events.

def _cl(*events: dict) -> list[str]:
    return [json.dumps(e) for e in events]


def _asst(mid: str, content: list, usage: dict | None = None, model: str = "claude-sonnet-5-5") -> dict:
    msg = {"id": mid, "type": "message", "role": "assistant", "model": model, "content": content}
    if usage is not None:
        msg["usage"] = usage
    return {"type": "assistant", "message": msg}


U1 = {"input_tokens": 10, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000,
      "output_tokens": 50}


def test_claude_dedupes_usage_per_message_id_without_result():
    lines = _cl(
        {"type": "system", "subtype": "init"},
        _asst("m1", [{"type": "text", "text": "Let me look."}], U1),
        _asst("m1", [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}], U1),
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]}},
        _asst("m2", [{"type": "text", "text": "Done."}], U1),
    )
    usage, outcome = parse_claude_stream(lines)
    assert usage.input_tokens == 2 * 1110 and usage.cached_input_tokens == 2000
    assert usage.output_tokens == 100 and usage.turns == 2 and usage.tool_calls == 1
    assert outcome == "infra"  # no result event: crashed / killed


def test_claude_result_usage_and_num_turns_win():
    lines = _cl(
        _asst("m1", [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}], U1),
        {"type": "result", "subtype": "success", "is_error": False, "num_turns": 3,
         "result": "Changed foo.ts; tests pass.",
         "usage": {"input_tokens": 5, "cache_creation_input_tokens": 0,
                   "cache_read_input_tokens": 20, "output_tokens": 7}},
    )
    usage, outcome = parse_claude_stream(lines)
    assert (usage.input_tokens, usage.cached_input_tokens, usage.output_tokens) == (25, 20, 7)
    assert usage.turns == 3 and usage.tool_calls == 1 and outcome == "ok"


def test_claude_max_turns_is_timeout():
    lines = _cl({"type": "result", "subtype": "error_max_turns", "is_error": True, "num_turns": 61})
    assert parse_claude_stream(lines)[1] == "timeout"


def test_claude_long_final_answer_mentioning_429_is_ok():
    text = "Implemented retry handling for HTTP 429 responses. " + "Details. " * 80
    lines = _cl({"type": "result", "subtype": "success", "is_error": False, "num_turns": 9,
                 "result": text})
    assert parse_claude_stream(lines)[1] == "ok"


def test_claude_usage_limit_with_is_error_false():
    lines = _cl({"type": "result", "subtype": "success", "is_error": False, "num_turns": 1,
                 "result": "You've hit your usage limit · resets 5pm"})
    assert parse_claude_stream(lines)[1] == "infra"


# --------------------------------------------------------------------------- runner pieces

def test_classify_status():
    u = Usage(turns=5)
    assert classify_status("ok", 0, u) == "ok"
    assert classify_status("infra", 0, u) == "infra"
    assert classify_status("ok", 124, u) == "timeout"
    assert classify_status("infra", 124, u) == "timeout"  # wall clock kill truncates the stream
    assert classify_status("ok", 0, Usage(turns=config.TURN_LIMIT)) == "timeout"
    assert classify_status("ok", None, u) == "infra"
    assert classify_status("ok", 1, Usage()) == "infra"
    assert classify_status("ok", 1, u) == "ok"


def test_prompt_is_identical_template(tmp_path):
    p = runner.render_prompt("Fix the thing.\n")
    assert "Task:\nFix the thing.\n" in p
    assert "packages/loot-core must pass" in p and "<statement.md" not in p


def test_docker_argv_isolation(tmp_path):
    a = runner.docker_argv("claude", "AP", "t01", 2, tmp_path / "prompt.txt", tmp_path / "out")
    s = " ".join(a)
    assert "aa-actual:AP" in a and "--name" in a and "aa-claude-AP-t01-2" in a
    assert "-i" in a  # revert patch arrives on stdin
    assert "CLAUDE_CONFIG_DIR=/tmp/cc" in a and "CLAUDE_CODE_OAUTH_TOKEN" in a
    assert ".claude" not in s
    # Only the prompt is mounted: nothing else of the task dir is visible.
    mounts = [a[i + 1] for i, x in enumerate(a) if x == "-v"]
    assert mounts == [f"{tmp_path / 'prompt.txt'}:/task/prompt.txt:ro", f"{tmp_path / 'out'}:/out"]
    assert "revert" not in s.replace("revert patch", "")
    assert "--permission-mode bypassPermissions" in a[-1] and "--max-turns 60" in a[-1]
    c = runner.docker_argv("codex", "A", "t01", 0, tmp_path / "prompt.txt", tmp_path / "out",
                           codex_auth_dir=tmp_path / "auth")
    assert f"{tmp_path / 'auth'}:/codex-auth:ro" in c and "CODEX_HOME=/tmp/codexhome" in c
    assert "--model gpt-6-luna" in c[-1] and "timeout 1500" in c[-1]
    assert c[-1].rstrip().endswith("git diff --cached HEAD > /out/diff.patch")


def test_agent_command_disables_web():
    import shlex
    cl = shlex.split(runner.agent_command("claude").split("<")[0])
    i = cl.index("--disallowedTools")
    assert set(cl[i + 1].split(",")) == {"WebSearch", "WebFetch"}
    assert cl[i + 2].startswith("--")  # the variadic option does not swallow the next flag
    assert "--strict-mcp-config" in cl and "--mcp-config" not in cl
    cx = shlex.split(runner.agent_command("codex").split("<")[0])
    configs = {cx[j + 1] for j, x in enumerate(cx) if x == "-c"}
    assert "web_search=disabled" in configs and "--strict-config" in cx
    disabled = {cx[j + 1] for j, x in enumerate(cx) if x == "--disable"}
    # `apps` too: with only web_search=disabled codex searched via codex_apps web_run
    assert {"apps", "browser_use", "browser_use_external", "computer_use", "in_app_browser"} <= disabled
    assert "shell_tool" not in disabled  # the agent still needs its shell
    assert cx.index("-c") < cx.index("--skip-git-repo-check")  # options before the prompt


@pytest.mark.parametrize("agent", ["claude", "codex"])
def test_container_script_patch_from_stdin_and_fresh_history(agent):
    script = runner.container_script(agent)
    lines = script.splitlines()
    apply = next(i for i, ln in enumerate(lines) if ln.startswith("git apply"))
    init = next(i for i, ln in enumerate(lines) if "rm -rf .git" in ln)
    ok = lines.index("touch /out/setup_ok")
    agent_line = next(i for i, ln in enumerate(lines) if ln.startswith("timeout "))
    assert apply < init < ok < agent_line
    assert " - " in lines[apply] + " " and "/task/revert" not in script
    assert "git init -q" in lines[init] and "commit -qm start" in lines[init]
    assert f"exit {runner.SETUP_EXIT}" in lines[apply] and f"exit {runner.SETUP_EXIT}" in lines[init]
    # The agent never inherits the patch stream.
    assert lines[agent_line].endswith("< /dev/null")


def test_container_script_end_to_end_in_local_git(tmp_path):
    """Run the script's setup with plain bash + git: history is reset, patch applied
    from stdin, no file holds the patch, setup_ok written."""
    import subprocess
    repo, out = tmp_path / "work" / "actual", tmp_path / "out"
    repo.mkdir(parents=True)
    out.mkdir()
    g = lambda *a: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a],
                                  cwd=repo, check=True, capture_output=True, text=True).stdout
    (repo / "f.ts").write_text("// solution comment\nexport const x = 1;\n")
    g("init", "-q", "-b", "main"); g("add", "-A"); g("commit", "-qm", "base")
    (repo / "secret.patch").write_text("aplus")
    g("add", "-A"); g("commit", "-qm", "variant with A+ patch")
    (repo / "secret.patch").unlink()
    g("add", "-A"); g("commit", "-qm", "cleanup")
    patch = ("diff --git a/f.ts b/f.ts\n--- a/f.ts\n+++ b/f.ts\n@@ -1,2 +1 @@\n"
             "-// solution comment\n export const x = 1;\n")
    lines = runner.container_script("claude").splitlines()
    setup = "\n".join(lines[:lines.index("touch /out/setup_ok") + 1])
    setup = setup.replace("/work/actual", str(repo)).replace("/out/", f"{out}/")
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "HOME": str(tmp_path),
           "GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@a",
           "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@a"}
    r = subprocess.run(["bash", "-c", setup], input=patch, text=True, capture_output=True, env=env)
    assert r.returncode == 0, r.stderr
    assert (out / "setup_ok").exists()
    assert (repo / "f.ts").read_text() == "export const x = 1;\n"
    log = g("log", "--format=%s", "--all")
    assert log.strip() == "start"
    assert "solution comment" not in subprocess.run(
        ["git", "log", "-p", "--all"], cwd=repo, capture_output=True, text=True).stdout
    # A patch that does not apply -> SETUP_EXIT and no setup_ok.
    (out / "setup_ok").unlink()
    r = subprocess.run(["bash", "-c", setup], input=patch, text=True, capture_output=True, env=env)
    assert r.returncode == runner.SETUP_EXIT and not (out / "setup_ok").exists()


def test_classify_setup():
    assert runner.classify_setup(True, 0) is None
    assert runner.classify_setup(False, runner.SETUP_EXIT) == "setup_error"
    assert runner.classify_setup(False, 1) == "setup_error"
    assert runner.classify_setup(False, None) == "infra"  # host timeout
    assert runner.classify_setup(False, 125) == "infra"   # docker run failed


def test_task_inputs_reads_per_condition_patch(tmp_path, monkeypatch):
    d = tmp_path / "t01"
    d.mkdir()
    (d / "statement.md").write_text("Do it.\n")
    (d / "revert.AP.patch").write_bytes(b"diff AP\n")
    (d / "revert.A.patch").write_bytes(b"diff A\n")
    (d / "task.json").write_text(json.dumps({
        "id": "t01", "statement_path": "statement.md",
        "per_condition": {"A": {"revert_patch": "revert.A.patch"},
                          "AP": {"revert_patch": "revert.AP.patch"}}}))
    prompt, patch = runner.task_inputs("t01", "AP", tmp_path)
    assert patch == b"diff AP\n" and "Task:\nDo it." in prompt


def test_run_one_records_harness_error(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(runner.config, "RUNS", tmp_path / "runs")
    out = runner.run_one("claude", "A", "missing-task", 0, tasks_root=tmp_path / "tasks")
    rec = json.loads((out / "agent.json").read_text())
    assert rec["status"] == "harness_error" and "FileNotFoundError" in rec["error"]


def test_scheduler_survives_run_exception(tmp_path):
    jobs = [Job("claude", "A", "t1", 0), Job("claude", "AL", "t1", 0)]

    def boom(j: Job) -> Path:
        if j.cond == "A":
            raise KeyError("AP")
        return _write_status(tmp_path / j.cond, "ok")

    res = Scheduler(jobs, workers=1, run=boom, sleep=lambda s: None,
                    status_of=lambda j: None, log=lambda s: None).execute()
    assert res == {jobs[0]: "harness_error", jobs[1]: "ok"}


def test_scheduler_skips_setup_error_as_final(tmp_path):
    j = Job("codex", "A", "t1", 0)
    calls = []
    res = Scheduler([j], workers=1, run=lambda job: calls.append(job) or tmp_path,
                    sleep=lambda s: None, status_of=lambda job: "setup_error",
                    log=lambda s: None).execute()
    assert calls == [] and res == {j: "setup_error"}


def test_run_all_uses_selected_tasks(monkeypatch):
    from aa import tasks as tasks_mod
    seen = {}
    monkeypatch.setattr(tasks_mod, "load_tasks",
                        lambda selected_only=True, root=None: seen.setdefault("sel", selected_only)
                        and [type("T", (), {"id": "t9"})()])

    class FakeSched:
        def __init__(self, q, workers):
            seen["tasks"] = sorted({j.task for j in q})

        def execute(self):
            return {}

    monkeypatch.setattr(runner, "Scheduler", FakeSched)
    runner.run_all("claude", ["A"], "all", 1)
    assert seen == {"sel": True, "tasks": ["t9"]}


def test_build_queue_interleaves_conditions_deterministically():
    q = build_queue("claude", ["A", "AL", "AP", "APL"], ["t1", "t2"], 2)
    assert len(q) == 16
    assert [j.task for j in q[:8]] == ["t1"] * 4 + ["t2"] * 4
    assert all(j.pass_idx == 0 for j in q[:8]) and all(j.pass_idx == 1 for j in q[8:])
    for k in range(0, 16, 4):
        assert sorted(j.cond for j in q[k:k + 4]) == ["A", "AL", "AP", "APL"]
    assert q == build_queue("claude", ["A", "AL", "AP", "APL"], ["t1", "t2"], 2)
    orders = {tuple(j.cond for j in q[k:k + 4]) for k in range(0, 16, 4)}
    assert len(orders) > 1  # actually shuffled


def test_backoff():
    assert [backoff_s(i) for i in range(7)] == [60, 120, 240, 480, 960, 1800, 1800]


def _write_status(path: Path, status: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "agent.json").write_text(json.dumps({"status": status}))
    return path


def test_scheduler_skips_done_and_requeues_infra(tmp_path):
    jobs = [Job("codex", c, "t1", 0) for c in ("A", "AL", "AP")]
    done = {jobs[0]: "ok"}
    calls: list[Job] = []
    sleeps: list[float] = []
    infra_left = {jobs[1]: 2}

    def fake_run(j: Job) -> Path:
        calls.append(j)
        st = "infra" if infra_left.get(j, 0) > 0 else "timeout" if j.cond == "AP" else "ok"
        if st == "infra":
            infra_left[j] -= 1
        return _write_status(tmp_path / j.cond / str(len(calls)), st)

    res = Scheduler(jobs, workers=1, run=fake_run, sleep=sleeps.append,
                    status_of=lambda j: done.get(j), log=lambda s: None).execute()
    assert jobs[0] not in calls
    assert calls.count(jobs[1]) == 3
    assert res == {jobs[0]: "ok", jobs[1]: "ok", jobs[2]: "timeout"}
    assert len(sleeps) >= 1 and max(sleeps) <= 120


def test_scheduler_gives_up_after_max_attempts(tmp_path):
    j = Job("claude", "A", "t1", 0)
    res = Scheduler([j], workers=2, run=lambda job: _write_status(tmp_path / "x", "infra"),
                    sleep=lambda s: None, status_of=lambda job: None,
                    max_infra_attempts=3, log=lambda s: None).execute()
    assert res == {j: "infra_exhausted"}
    assert json.loads((tmp_path / "x" / "agent.json").read_text())["status"] == "infra_exhausted"


def test_scheduler_default_caps_infra_attempts(tmp_path):
    j = Job("claude", "A", "t1", 0)
    n = []
    res = Scheduler([j], workers=1, run=lambda job: n.append(1) or _write_status(tmp_path / "y", "infra"),
                    sleep=lambda s: None, status_of=lambda job: None, log=lambda s: None).execute()
    assert res == {j: "infra_exhausted"} and len(n) == runner.MAX_INFRA_ATTEMPTS == 8


# --------------------------------------------------------------------------- contamination

from aa.agents import detect_contamination  # noqa: E402


def test_contamination_claude_tool_input_flagged():
    lines = _cl(
        {"type": "assistant", "message": {"id": "m1", "content": [
            {"type": "tool_use", "id": "t1", "name": "Bash",
             "input": {"command": "git clone https://github.com/actualbudget/actual /tmp/x"}}]}},
        {"type": "result", "num_turns": 1, "result": "done"})
    assert detect_contamination("claude", lines) == ["git clone", "github.com/actualbudget"]


def test_contamination_ignores_tool_results_and_reading_repo():
    lines = _cl(
        {"type": "assistant", "message": {"id": "m1", "content": [
            {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "/work/actual/README.md"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1",
                                                  "content": "see https://github.com/actualbudget/actual"}]}})
    assert detect_contamination("claude", lines) == []


def test_contamination_codex_command_and_websearch():
    lines = _cl(
        {"type": "item.completed", "item": {"id": "i1", "type": "command_execution",
                                            "command": "curl https://api.github.com/repos/x",
                                            "aggregated_output": "github.com/actualbudget"}},
        {"type": "item.completed", "item": {"id": "i2", "type": "web_search",
                                            "query": "raw.githubusercontent.com actual util.ts"}},
        {"type": "item.completed", "item": {"id": "i3", "type": "agent_message",
                                            "text": "I did not git clone anything"}})
    assert detect_contamination("codex", lines) == ["api.github.com", "curl api.github.com",
                                                    "raw.githubusercontent", "web:web_search"]


def test_contamination_registry_git_and_web_tools():
    cmds = ["npm view @actual-app/api versions", "npm pack @actual-app/crdt@2.1.0",
            "npm install --no-save @actual-app/web", "yarn npm info @actual-app/api",
            "git fetch origin", "git -C /tmp/x remote add up https://x", "git status",
            "npm view lodash"]
    lines = _cl({"type": "assistant", "message": {"id": "m1", "content": [
        {"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": c}}
        for i, c in enumerate(cmds)] + [
        {"type": "tool_use", "id": "w1", "name": "WebSearch", "input": {"query": "budget"}},
        {"type": "server_tool_use", "id": "w2", "name": "web_fetch", "input": {"url": "https://x"}}]}})
    assert detect_contamination("claude", lines) == [
        "git fetch", "git remote add", "npm install @actual-app", "npm pack @actual-app",
        "npm view @actual-app", "web:WebSearch", "web:web_fetch", "yarn npm info"]


def test_contamination_task_refs():
    from aa.agents import task_refs
    assert task_refs({"subject": "Fix sync (#8392)", "issues": ["#8100"]}) == ["8100", "8392"]
    assert task_refs({"subject": "no number"}) == []
    assert task_refs({"subject": "Bug", "issue": 6244, "related_prs": [7544, 8606],
                      "public_fix_prs": [7544], "related_issues": [6737]}) == [
        "6244", "6737", "7544", "8606"]
    bash = lambda c: {"type": "tool_use", "id": c, "name": "Bash", "input": {"command": c}}  # noqa: E731
    edit = {"type": "tool_use", "id": "e", "name": "Edit",
            "input": {"file_path": "a.ts", "old_string": "x", "new_string": "amount: 8392"}}
    msg = lambda *b: _cl({"type": "assistant", "message": {"id": "m", "content": list(b)}})  # noqa: E731
    assert detect_contamination("claude", msg(bash("gh pr view 8392")), ["8392"]) == ["ref:#8392"]
    assert detect_contamination("claude", msg(bash("grep -rn '#8392' .")), ["8392"]) == ["ref:#8392"]
    # a bare number in code the agent writes is just a literal; 83920 / 1.8392 never match
    assert detect_contamination("claude", msg(edit, bash("echo 83920 1.8392")), ["8392"]) == []
    cx = _cl({"type": "item.completed", "item": {"id": "i1", "type": "web_search",
                                                 "query": "actual budget pull/8392"}})
    assert detect_contamination("codex", cx, ["8392"]) == ["ref:#8392", "web:web_search"]


def test_contamination_mcp_web_tools():
    # the real codex item seen when only web_search=disabled was set (2026-10-06)
    cx = _cl({"type": "item.completed", "item": {
        "id": "item_1", "type": "mcp_tool_call", "server": "codex_apps", "tool": "search_service.web_run",
        "arguments": {"system2_search_query": [{"q": "latest release Actual Budget"}]}}},
        {"type": "item.completed", "item": {"id": "i2", "type": "mcp_tool_call", "server": "s",
                                            "tool": "lookup", "arguments": {}}})
    assert detect_contamination("codex", cx) == ["mcp:s.lookup", "web:codex_apps.search_service.web_run"]
    cl = _cl({"type": "assistant", "message": {"id": "m", "content": [
        {"type": "tool_use", "id": "t", "name": "mcp__srv__web_fetch", "input": {}}]}})
    assert detect_contamination("claude", cl) == ["web:mcp__srv__web_fetch"]


def test_contamination_bare_numbers_need_pr_context():
    """Read offsets, sed ranges and line numbers collide with PR numbers (real false
    positives): a bare task number only counts next to #, pull/, issue(s)/, pr, gh pr."""
    tool = lambda name, inp: {"type": "tool_use", "id": name + str(inp), "name": name,  # noqa: E731
                              "input": inp}
    msg = lambda *b: _cl({"type": "assistant", "message": {"id": "m", "content": list(b)}})  # noqa: E731
    reads = msg(tool("Read", {"file_path": "/work/actual/packages/loot-core/src/a.ts",
                              "offset": 1062, "limit": 80}),
                tool("Bash", {"command": "sed -n '1000,1331p' src/server/db/index.ts"}),
                tool("Bash", {"command": "grep -n foo a.ts | head -1062"}),
                tool("Grep", {"pattern": "x", "-n": True, "head_limit": 1331}))
    assert detect_contamination("claude", reads, ["1062", "1331"]) == []
    cx = _cl({"type": "item.completed", "item": {
        "id": "i1", "type": "command_execution",
        "command": "bash -lc \"sed -n '1000,1331p' packages/loot-core/src/server/db/index.ts\""}},
        {"type": "item.completed", "item": {"id": "i2", "type": "command_execution",
                                            "command": "nl -ba a.ts | sed -n 1062,1100p"}})
    assert detect_contamination("codex", cx, ["1062", "1331"]) == []
    for c in ("gh pr view 1062", "gh pr diff -R actualbudget/actual 1062", "echo PR 1062",
              "grep -rn 'issue #1062' .", "echo issues/1062", "echo pull/1062"):
        assert detect_contamination("claude", msg(tool("Bash", {"command": c})), ["1062"]) == \
            ["ref:#1062"], c
    # in code the agent writes only the URL/# forms count
    edit = tool("Edit", {"file_path": "a.ts", "old_string": "x", "new_string": "// pr 1062"})
    assert detect_contamination("claude", msg(edit), ["1062"]) == []
    edit = tool("Edit", {"file_path": "a.ts", "old_string": "x", "new_string": "// see #1062"})
    assert detect_contamination("claude", msg(edit), ["1062"]) == ["ref:#1062"]


def test_contamination_blocked_hosts_curl_wget_and_registry():
    from aa.agents import BLOCKED_HOSTS
    cmds = ["curl -sS https://registry.npmjs.org/@actual-app/api",
            "wget -qO- https://unpkg.com/@actual-app/api/package.json",
            "curl -L https://codeload.github.com/x/y/tar.gz/main -o /tmp/a.tgz",
            "curl https://cdn.jsdelivr.net/npm/@actual-app/crdt",
            "curl -s https://esm.sh/lodash",
            "curl http://localhost:5006/health",   # not a blocked host
            "echo registry.npmjs.org"]               # mentioned, not fetched
    cx = _cl(*[{"type": "item.completed", "item": {"id": f"i{i}", "type": "command_execution",
                                                   "command": c}} for i, c in enumerate(cmds)])
    assert detect_contamination("codex", cx) == [
        "curl cdn.jsdelivr.net", "curl codeload.github.com", "curl esm.sh",
        "curl registry.npmjs.org", "registry.npmjs.org/@actual-app", "wget unpkg.com"]
    assert "github.com" in BLOCKED_HOSTS and "registry.npmjs.org" in BLOCKED_HOSTS


def test_docker_argv_blackholes_upstream_hosts(tmp_path):
    expected = ["github.com", "api.github.com", "raw.githubusercontent.com", "codeload.github.com",
                "objects.githubusercontent.com", "gist.github.com", "registry.npmjs.org",
                "registry.yarnpkg.com", "unpkg.com", "cdn.jsdelivr.net", "esm.sh", "npmmirror.com"]
    for agent, kw in (("claude", {}), ("codex", {"codex_auth_dir": tmp_path / "auth"})):
        a = runner.docker_argv(agent, "A", "t01", 0, tmp_path / "prompt.txt", tmp_path / "out", **kw)
        hosts = [a[i + 1] for i, x in enumerate(a) if x == "--add-host"]
        assert hosts == [f"{h}:0.0.0.0" for h in expected]
        # before the image: docker options, not container arguments
        assert a.index("--add-host") < a.index("aa-actual:A")
        # the model APIs stay reachable
        joined = " ".join(hosts)
        for api in ("anthropic.com", "openai.com", "chatgpt.com"):
            assert api not in joined
        assert "--network" not in a


def test_codex_noweb_smoke_fixture():
    """Real codex run (gpt-6-luna, 0.159.3) in aa-actual:A with the final flags
    (CODEX_NO_WEB + blocked_host_args), 2026-10-06. Prompt: (a) web-search the latest
    Actual release, (b) curl https://registry.npmjs.org/@actual-app/api, (c) ls
    packages. Both upstream routes must fail; the shell must still work."""
    lines = _lines("codex-noweb-smoke.jsonl")
    evs = [json.loads(ln) for ln in lines]
    items = [e["item"] for e in evs if e.get("type") == "item.completed"]
    types = {i["type"] for i in items}
    assert "web_search" not in types and "mcp_tool_call" not in types
    cmds = [i for i in items if i["type"] == "command_execution"]
    curl = next(i for i in cmds if "registry.npmjs.org/@actual-app/api" in i["command"])
    assert "Failed to connect to registry.npmjs.org" in curl["aggregated_output"]
    assert "curl exit: 7" in curl["aggregated_output"]
    assert "{" not in curl["aggregated_output"]  # no registry JSON came back
    ls = next(i for i in cmds if "ls packages" in i["command"])
    assert ls["exit_code"] == 0 and "loot-core" in ls["aggregated_output"]
    usage, outcome = parse_codex_stream(lines)
    assert outcome == "ok" and usage.tool_calls == 2
    # the attempt itself is still flagged
    assert detect_contamination("codex", lines) == ["curl registry.npmjs.org",
                                                    "registry.npmjs.org/@actual-app"]


def test_effort_pinned_equally_for_both_agents():
    from aa import config
    from aa.runner import agent_command
    assert f"--effort {config.EFFORT}" in agent_command("claude")
    assert f"model_reasoning_effort={config.EFFORT}" in agent_command("codex")
