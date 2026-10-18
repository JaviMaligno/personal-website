"""Agent transcript parsers and outcome classification.

Token accounting is normalised across agents:
  input_tokens         all prompt tokens, cached ones included
  cached_input_tokens  the cached subset (Claude: cache reads; Codex: cached_input_tokens)
  output_tokens        completion tokens (Codex: reasoning tokens are part of output)
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

from aa import config

Outcome = Literal["ok", "timeout", "infra"]


@dataclass
class Usage:
    """Token fields are None when the stream never reported them (a killed ``codex
    exec`` emits no ``turn.completed``): missing, not zero (study-3 pilot, blocking
    item 3). ``turns`` and ``tool_calls`` are counted from the stream itself."""
    input_tokens: int | None = 0
    output_tokens: int | None = 0
    cached_input_tokens: int | None = 0
    turns: int = 0
    tool_calls: int = 0

    @property
    def tokens_missing(self) -> bool:
        return self.input_tokens is None or self.output_tokens is None


_INFRA_PATTERNS = [
    r"usage limit",
    r"rate[ _-]?limit",
    r"\b429\b",
    r"too many requests",
    r"overloaded",
    r"\b529\b",
    r"insufficient_quota",
    r"exceeded your (current )?quota",
    r"credit balance is too low",
    r"authentication_error",
    r"invalid (api key|bearer token)",
    r"oauth token (has )?(expired|revoked)",
    r"\b401\b.*unauthori[sz]ed|unauthori[sz]ed.*\b401\b",
    r"please run /login",
    r"not logged in",
    r"stream disconnected",
    r"\b50[234]\b.*(bad gateway|service unavailable|gateway timeout)",
]
_INFRA_RE = re.compile("|".join(f"(?:{p})" for p in _INFRA_PATTERNS), re.IGNORECASE)
# A final agent message longer than this is a real answer that may merely mention
# "rate limit" or "429" (e.g. the task is about HTTP handling); only short final
# messages are treated as infra notices unless the CLI flags them as errors.
_SHORT_NOTICE = 400


def classify_infra(text: str) -> bool:
    """True for usage-limit / rate-limit / overloaded / auth messages."""
    return bool(text) and _INFRA_RE.search(text) is not None


def _infra_http(status: Any) -> bool:
    """HTTP statuses that mean quota/auth/overload rather than an agent failure."""
    try:
        code = int(status)
    except (TypeError, ValueError):
        return False
    return code in (401, 403, 429, 529) or 500 <= code < 600


def _events(lines: Iterable[str]) -> list[dict[str, Any]]:
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            ev = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(ev, dict):
            out.append(ev)
    return out


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


# --------------------------------------------------------------------------- Claude

def _claude_usage_fields(u: dict[str, Any]) -> tuple[int, int, int]:
    fresh = int(u.get("input_tokens") or 0)
    created = int(u.get("cache_creation_input_tokens") or 0)
    read = int(u.get("cache_read_input_tokens") or 0)
    return fresh + created + read, int(u.get("output_tokens") or 0), read


def parse_claude_stream(lines: Iterable[str]) -> tuple[Usage, Outcome]:
    """Parse `claude -p --output-format stream-json --verbose` stdout.

    Events (checked against the real stream in tests/fixtures/claude-stream-ok.jsonl,
    Claude Code 2.1.289): `system` (subtype init), `assistant` (message with
    `id`, `model`, content blocks and per-message `usage`), `user` (tool
    results), `rate_limit_event` (`rate_limit_info.status`: allowed /
    allowed_warning / rejected), and a final `result` with `subtype`,
    `is_error`, `num_turns`, `result` text, `api_error_status` and aggregate
    `usage` {input_tokens, cache_creation_input_tokens, cache_read_input_tokens,
    output_tokens}. The per-message `output_tokens` in `assistant` events are
    streaming snapshots (lower than the final count), so the `result` usage is
    authoritative; the per-message sum (de-duplicated by message id) is only a
    fallback for streams cut before `result`.

    When background tasks finish after the answer, Claude Code wakes the agent and
    writes one more `result` per wake, each with that segment's own `usage` and
    `num_turns` (study-3 pilot, blocking item 2: e.g. 23 + 3 + 2 turns). Usage and
    turns are the sum over every `result`, plus the per-message usage of assistant
    messages after the last `result` (a segment cut before its own `result`). The
    outcome is read from the last `result`.
    """
    evs = _events(lines)
    per_msg: dict[str, tuple[int, int, int]] = {}
    tool_ids: set[str] = set()
    anon_tools = 0
    last_assistant_text = ""
    last_assistant_synthetic = False
    result: dict[str, Any] | None = None
    results: list[dict[str, Any]] = []
    after_last: set[str] = set()  # assistant message ids after the last result
    rate_rejected = False
    for i, ev in enumerate(evs):
        t = ev.get("type")
        if t == "rate_limit_event":
            info = ev.get("rate_limit_info") or {}
            rate_rejected |= str(info.get("status", "")).lower() == "rejected"
            continue
        if t == "assistant":
            msg = ev.get("message") or {}
            mid = msg.get("id") or f"_anon{i}"
            if isinstance(msg.get("usage"), dict):
                per_msg[mid] = _claude_usage_fields(msg["usage"])
            else:
                per_msg.setdefault(mid, (0, 0, 0))
            if msg.get("model") != "<synthetic>":
                after_last.add(mid)
            for b in msg.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    if b.get("id"):
                        tool_ids.add(b["id"])
                    else:
                        anon_tools += 1
            txt = _text_of(msg.get("content"))
            if txt:
                last_assistant_text = txt
                last_assistant_synthetic = msg.get("model") == "<synthetic>"
        elif t == "result":
            result = ev
            results.append(ev)
            after_last = set()

    usage = Usage(tool_calls=len(tool_ids) + anon_tools)
    with_usage = [r for r in results if isinstance(r.get("usage"), dict)]
    if with_usage:
        fields = [_claude_usage_fields(r["usage"]) for r in with_usage]
        fields += [per_msg[m] for m in after_last if m in per_msg]
        usage.input_tokens = sum(f[0] for f in fields)
        usage.output_tokens = sum(f[1] for f in fields)
        usage.cached_input_tokens = sum(f[2] for f in fields)
    else:
        usage.input_tokens = sum(v[0] for v in per_msg.values())
        usage.output_tokens = sum(v[1] for v in per_msg.values())
        usage.cached_input_tokens = sum(v[2] for v in per_msg.values())
    counted = [r for r in results if r.get("num_turns") is not None]
    if counted:
        usage.turns = sum(int(r["num_turns"]) for r in counted) + len(after_last)
    else:
        usage.turns = len(per_msg)

    # Usage-limit notices can arrive as a synthetic assistant message and a
    # result with is_error=false and exit code 0 (Review Focus #4).
    if last_assistant_synthetic and classify_infra(last_assistant_text):
        return usage, "infra"
    if result is None:
        # Stream cut without a result event: the CLI crashed or was killed. A
        # wall-clock kill is recognised by the runner from exit code 124.
        return usage, "infra"
    text = str(result.get("result") or "") + " " + " ".join(
        str(e) for e in (result.get("errors") or []))
    if classify_infra(text) and (result.get("is_error") or len(text) <= _SHORT_NOTICE):
        return usage, "infra"
    api_status = result.get("api_error_status")
    if result.get("is_error") and (rate_rejected or _infra_http(api_status)):
        return usage, "infra"
    if result.get("subtype") == "error_max_turns":
        return usage, "timeout"
    if result.get("is_error") and result.get("subtype") == "error_during_execution":
        return usage, "infra"
    return usage, "ok"


# --------------------------------------------------------------------------- Codex

_CODEX_TOOL_ITEMS = {"command_execution", "mcp_tool_call", "file_change", "web_search",
                     "local_shell_call", "function_call", "custom_tool_call"}


def parse_codex_stream(lines: Iterable[str]) -> tuple[Usage, Outcome]:
    """Parse `codex exec --json` stdout (JSONL thread events).

    Events: `thread.started`, `turn.started`, `item.started` / `item.updated` /
    `item.completed` (item.type in agent_message, reasoning, command_execution,
    file_change, mcp_tool_call, web_search, todo_list, error), `turn.completed`
    with `usage` {input_tokens, cached_input_tokens, cache_write_input_tokens,
    output_tokens, reasoning_output_tokens} (input_tokens includes the cached
    ones; field names checked against tests/fixtures/codex-ok.jsonl), `turn.failed`
    with `error.message`, and top-level `error` with `message`.

    `item.completed` of type `error` also carries non-fatal config warnings
    (e.g. unrecognised settings in the repo's .codex/config.toml); they only
    matter when they match an infra pattern.

    codex exec runs a single user turn, so `turns` approximates model rounds as
    tool calls + agent messages (comparable to Claude's num_turns).
    """
    evs = _events(lines)
    usage = Usage()
    completed = failed = False
    errors: list[str] = []    # turn.failed / top-level error
    warnings: list[str] = []  # item.completed of type error (non-fatal)
    items_seen: set[str] = set()
    agent_msgs = 0
    for i, ev in enumerate(evs):
        t = ev.get("type")
        if t == "turn.completed":
            completed = True
            u = ev.get("usage") or {}
            usage.input_tokens += int(u.get("input_tokens") or 0)
            usage.cached_input_tokens += int(u.get("cached_input_tokens") or 0)
            usage.output_tokens += int(u.get("output_tokens") or 0)
        elif t == "turn.failed":
            failed = True
            err = ev.get("error") or {}
            errors.append(str(err.get("message") if isinstance(err, dict) else err))
        elif t == "error":
            errors.append(str(ev.get("message") or ev.get("error") or ""))
        elif t == "item.completed":
            item = ev.get("item") or {}
            iid = item.get("id") or f"_anon{i}"
            if iid in items_seen:
                continue
            items_seen.add(iid)
            it = item.get("type")
            if it in _CODEX_TOOL_ITEMS:
                usage.tool_calls += 1
            elif it == "agent_message":
                agent_msgs += 1
            elif it == "error":
                warnings.append(str(item.get("message") or ""))
    usage.turns = usage.tool_calls + agent_msgs
    if not completed:
        # usage arrives only with turn.completed: a killed or failed run reports none
        usage.input_tokens = usage.output_tokens = usage.cached_input_tokens = None
    fatal = " ".join(errors)
    warn = " ".join(warnings)
    if not completed and not failed:
        # Stream cut: CLI crashed or was killed (124 is recognised by the runner).
        return usage, "infra"
    if failed:
        if classify_infra(fatal) or not usage.turns:
            return usage, "infra"
        # A failed turn that is not a recognised infra error (e.g. context
        # window exceeded) still ends the agent's attempt; evaluation decides.
        return usage, "ok"
    if classify_infra(fatal + " " + warn) and not usage.output_tokens:
        return usage, "infra"
    return usage, "ok"


# --------------------------------------------------------------------------- stalls

# Transport / connection failures between the CLI and its model API (study-3 pilot,
# blocking item 1: a DNS outage left two Codex steps reconnecting until the wall limit).
_TRANSPORT_PATTERNS = [
    r"reconnecting\.\.\.",
    r"stream disconnected",
    r"waiting for network",
    r"name does not resolve|failed to lookup address|getaddrinfo|enotfound|eai_again",
    r"connection (?:failed|refused|reset|error)|econnreset|econnrefused|error sending request",
    r"fetch failed|socket hang up|request timed out|etimedout|network (?:error|is unreachable)",
]
_TRANSPORT_RE = re.compile("|".join(f"(?:{p})" for p in _TRANSPORT_PATTERNS), re.IGNORECASE)


def _stall_kind(agent: str, ev: dict[str, Any]) -> str | None:
    """``progress`` (the agent did something), ``transport`` (a connection error the
    CLI reported) or None (neutral: notifications, warnings, bookkeeping)."""
    t = ev.get("type")
    if config.engine(agent) == "codex":
        if t == "error":
            return "transport" if _TRANSPORT_RE.search(str(ev.get("message") or "")) else None
        if t in ("item.started", "item.updated", "item.completed"):
            item = ev.get("item") or {}
            if item.get("type") == "error":
                return "transport" if _TRANSPORT_RE.search(str(item.get("message") or "")) \
                    else None
            return "progress"
        if t == "turn.failed":
            err = ev.get("error") or {}
            msg = err.get("message") if isinstance(err, dict) else err
            return "transport" if _TRANSPORT_RE.search(str(msg or "")) else None
        if t == "turn.completed":
            return "progress"
        return None
    # Claude Code
    if t == "system":
        sub = str(ev.get("subtype") or "")
        if "retry" in sub or "api_error" in sub:
            return "transport"
        return None
    if t == "assistant":
        msg = ev.get("message") or {}
        if msg.get("model") == "<synthetic>":
            return "transport" if _TRANSPORT_RE.search(_text_of(msg.get("content"))) else None
        return "progress"
    if t == "user":
        return "progress"
    if t == "result":
        text = str(ev.get("result") or "") + " " + " ".join(str(e) for e in ev.get("errors") or [])
        if ev.get("is_error") and _TRANSPORT_RE.search(text):
            return "transport"
        return "progress"
    return None


def transport_stalled(agent: str, lines: Iterable[str]) -> bool:
    """True when the transcript ends in transport / connection errors with no agent
    progress after them (Codex ``Reconnecting... waiting for network``, ``stream
    disconnected``, DNS ``Name does not resolve``; Claude Code API retry notices or a
    synthetic ``API Error: Connection error.``): the CLI was waiting for the network, not
    the agent working. The runner then records ``infra`` (re-queued, never carried)
    whatever the exit code (:func:`aa.runner.classify_status`)."""
    kinds = [k for k in (_stall_kind(agent, ev) for ev in _events(lines)) if k]
    if not kinds or kinds[-1] != "transport":
        return False
    return True


def parse_stream(agent: str, lines: Iterable[str]) -> tuple[Usage, Outcome]:
    if config.engine(agent) == "claude":
        return parse_claude_stream(lines)
    if config.engine(agent) == "codex":
        return parse_codex_stream(lines)
    raise ValueError(f"unknown agent {agent!r}")


# --------------------------------------------------------------------------- contamination

# The containers have network access (the agents need their APIs). An agent that
# fetches upstream Actual (the real commit is public, and so are the published
# @actual-app packages) is flagged, not blocked. Web tools are disabled in real runs
# (``aa.runner.agent_command``); any web tool use that still shows up is flagged too.
# Hosts that answer upstream source/packages; the runner maps them to 0.0.0.0 in
# agent containers (``docker run --add-host``). The model API hosts are not here.
BLOCKED_HOSTS = ("github.com", "api.github.com", "raw.githubusercontent.com",
                 "codeload.github.com", "objects.githubusercontent.com", "gist.github.com",
                 "registry.npmjs.org", "registry.yarnpkg.com", "unpkg.com", "cdn.jsdelivr.net",
                 "esm.sh", "npmmirror.com")
# (label, pattern): the label is the marker recorded on the run; ``{0}``/``{1}`` are
# the pattern's groups.
_CONTAMINATION_PATTERNS: list[tuple[str | None, re.Pattern[str]]] = [
    (None, re.compile(r"github\.com/actualbudget|raw\.githubusercontent|api\.github\.com",
                      re.IGNORECASE)),
    ("git {0}", re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(clone|fetch|remote\s+add)\b",
                           re.IGNORECASE)),
    ("npm {0} @actual-app", re.compile(
        r"(?<!yarn )\bnpm\s+(pack|view|install|info|i)\b[^\n;&|]*@actual-app", re.IGNORECASE)),
    ("yarn npm info", re.compile(r"\byarn\s+npm\s+info\b", re.IGNORECASE)),
    ("registry.npmjs.org/@actual-app", re.compile(
        r"registry\.(?:npmjs\.org|yarnpkg\.com)/(?:@|%40)actual-app", re.IGNORECASE)),
    # curl/wget (or any download) towards a blocked host; the hosts resolve to
    # 0.0.0.0 in the agent containers (``aa.runner.docker_argv``), so the
    # attempt fails, but it is still an attempt to reach upstream.
    ("{0} {1}", re.compile(
        r"\b(curl|wget)\b[^\n;&|]*?\b(" + "|".join(re.escape(h) for h in BLOCKED_HOSTS)
        + r")(?![\w.-])", re.IGNORECASE)),
]
_CLAUDE_WEB_TOOLS = {"WebSearch", "WebFetch", "web_search", "web_fetch"}
_CLAUDE_EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_REF_RE = re.compile(r"#(\d{3,6})\b")
# A task number only counts with PR/issue context. A bare number is never enough:
# Read offsets, ``sed -n '1000,1331p'`` ranges and line numbers collide with PR
# numbers (false positives seen in real runs). In edits only the URL/``#`` forms
# count; in commands, searches and queries also ``pr 8392`` / ``issue 8392`` /
# ``gh pr view 8392``.
_REF_STRONG = r"(?:#|\bpulls?/|\bissues?/)"
_REF_CONTEXT = (r"(?:#|\bpulls?/|\bissues?/|\b(?:pr|pull|issue)s?\b[\s:#=-]*"
                r"|\bgh\s+(?:pr|issue)\s+[a-z-]+\s+(?:-\S+\s+\S+\s+)*)")


def task_refs(task: dict[str, Any]) -> list[str]:
    """Upstream PR/issue numbers of a task: ``#NNNN`` in its subject (the merged PR)
    plus optional ``pr`` / ``issue`` / ``issues`` fields in task.json, and for issue
    tasks the public PRs found for the issue (``related_prs``, ``public_fix_prs``;
    spec 6 item 5, amendment 2026-10-06)."""
    refs = set(_REF_RE.findall(str(task.get("subject") or "")))
    for k in ("pr", "issue"):
        if task.get(k):
            refs.add(str(task[k]).lstrip("#"))
    for k in ("issues", "related_prs", "public_fix_prs", "related_issues"):
        for i in task.get(k) or []:
            refs.add(str(i).lstrip("#"))
    return sorted(r for r in refs if r.isdigit())


def _agent_actions(agent: str, evs: list[dict[str, Any]]) -> Iterable[tuple[str, str, bool]]:
    """(tool name, text, is_edit) for what the agent *did* (tool inputs, commands,
    searches).

    Tool results are skipped on purpose: the repository itself mentions
    github.com/actualbudget (README, package.json), so reading a file must not
    count as contamination. ``is_edit`` marks code written by the agent (Edit/Write
    inputs, apply_patch), where a bare number is likely just a literal.
    """
    for ev in evs:
        if config.engine(agent) == "claude" and ev.get("type") == "assistant":
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") in ("tool_use", "server_tool_use"):
                    name = str(b.get("name") or "")
                    yield (name, json.dumps(b.get("input"), ensure_ascii=False),
                           name in _CLAUDE_EDIT_TOOLS)
        elif config.engine(agent) == "codex" and ev.get("type") in ("item.started", "item.completed"):
            item = ev.get("item") or {}
            it = item.get("type")
            if it in _CODEX_TOOL_ITEMS and it != "file_change":
                name = str(item.get("name") or it)
                if it == "mcp_tool_call":  # no MCP server is configured in real runs
                    name = f"mcp:{item.get('server') or '?'}.{item.get('tool') or '?'}"
                for k in ("command", "query", "arguments", "input", "action"):
                    if item.get(k) is not None:
                        v = item[k]
                        yield (name, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False),
                               name == "apply_patch")
                if it == "web_search":
                    yield (name, "", False)


def detect_contamination(agent: str, lines: Iterable[str],
                         refs: Iterable[str] = ()) -> list[str]:
    """Distinct upstream-access markers found in the agent's own actions:
    github.com/actualbudget, raw.githubusercontent, api.github.com, ``git clone`` /
    ``git fetch`` / ``git remote add``, ``npm pack|view|install|info @actual-app``,
    ``yarn npm info``, any web tool use (``web:<tool>``, MCP web tools included), any
    other MCP tool call (``mcp:<tool>``), and the task's upstream
    PR/issue numbers ``refs`` (``ref:#NNNN``; in edits only as ``#NNNN``, ``pull/NNNN``
    or ``issues/NNNN``, elsewhere also as ``pr NNNN`` / ``issue NNNN`` / ``gh pr view
    NNNN``, never as a bare number), ``curl``/``wget`` to a ``BLOCKED_HOSTS`` host and
    ``registry.npmjs.org/@actual-app`` URLs. A non-empty list sets
    `contamination_flag` on the run."""
    hits: set[str] = set()
    ref_res = [(r, re.compile(_REF_STRONG + rf"{r}(?!\d)", re.IGNORECASE),
                re.compile(_REF_CONTEXT + rf"{r}(?!\d)", re.IGNORECASE)) for r in refs]
    for name, text, is_edit in _agent_actions(agent, _events(lines)):
        if name in _CLAUDE_WEB_TOOLS or name == "web_search":
            hits.add(f"web:{name}")
        elif name.startswith(("mcp:", "mcp__")):
            # MCP tools (none configured in real runs; codex_apps exposes web search)
            hits.add(f"{'web' if 'web' in name.lower() else 'mcp'}:{name.removeprefix('mcp:')}")
        for label, rx in _CONTAMINATION_PATTERNS:
            for m in rx.finditer(text):
                if label is None:
                    hits.add(m.group(0).lower())
                else:
                    gs = [re.sub(r"\s+", " ", (g or "").lower()) for g in m.groups()]
                    hits.add(label.format(*gs))
        for r, strong, ctx in ref_res:
            if strong.search(text) or (not is_edit and ctx.search(text)):
                hits.add(f"ref:#{r}")
    return sorted(hits)
