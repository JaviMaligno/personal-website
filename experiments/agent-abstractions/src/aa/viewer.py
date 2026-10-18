"""Per-run HTML viewer (spec §10, plan Task 10).

`render_run(run_dir)` turns a run directory (`transcript.jsonl`, `diff.patch`,
optional `result.json` / `agent.json`) into one self-contained HTML page: the
conversation on the left (assistant text, collapsed thinking, tool calls with
input and output clipped to 2 kB plus an expander), the agent diff next to the
task's reference diff on the right, and the evaluator's violations highlighted
on their diff lines. No JavaScript; light/dark through CSS variables.

Transcripts are either Claude Code `--output-format stream-json --verbose`
events or `codex exec --json` events; the format is detected per line, so a
transcript is parsed the same way whichever agent produced it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from string import Template
from typing import Iterable

TEMPLATES = Path(__file__).parent / "templates"
CLIP = 2048  # characters of tool input/output shown before the expander

# Shared by run.html and status.html.
BASE_CSS = """
:root {
  --bg: #fbfbfa; --surface: #ffffff; --surface-2: #f1f1ee; --text: #1d1d1b;
  --muted: #6b6b66; --border: #dcdcd6; --accent: #2d6cdf;
  --ok: #1f7a3d; --bad: #b42318; --warn: #a15c00;
  --add-bg: #e6f4ea; --del-bg: #fdecea; --bad-bg: #ffd8d3;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #161615; --surface: #1e1e1c; --surface-2: #2a2a27; --text: #e9e9e4;
    --muted: #a0a09a; --border: #3a3a36; --accent: #7aa7ff;
    --ok: #6fcf8b; --bad: #ff8a7a; --warn: #f0b45a;
    --add-bg: #1d3325; --del-bg: #3a201d; --bad-bg: #5a2620;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #161615; --surface: #1e1e1c; --surface-2: #2a2a27; --text: #e9e9e4;
  --muted: #a0a09a; --border: #3a3a36; --accent: #7aa7ff;
  --ok: #6fcf8b; --bad: #ff8a7a; --warn: #f0b45a;
  --add-bg: #1d3325; --del-bg: #3a201d; --bad-bg: #5a2620;
  color-scheme: dark;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; padding: 16px; background: var(--bg); color: var(--text);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; overflow-wrap: anywhere; }
main, header { max-width: 1400px; margin: 0 auto; }
h1 { font-size: 20px; margin: 0 0 8px; }
h2 { font-size: 16px; margin: 20px 0 8px; }
a { color: var(--accent); }
code, pre { font-family: var(--mono); font-size: 12.5px; }
pre { margin: 0; padding: 6px 8px; background: var(--surface-2); border-radius: 6px;
  overflow-x: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
details > summary { cursor: pointer; font-size: 13px; color: var(--accent); }
.facts { display: flex; flex-wrap: wrap; gap: 6px; }
.pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 13px;
  background: var(--surface-2); border: 1px solid var(--border); white-space: nowrap; }
.pill.ok { color: var(--ok); border-color: var(--ok); }
.pill.bad { color: var(--bad); border-color: var(--bad); }
.pill.warn { color: var(--warn); border-color: var(--warn); }
.note, .empty { color: var(--muted); font-size: 13px; }
"""


@dataclass
class Event:
    kind: str  # text | thinking | tool | error | system | raw
    text: str = ""
    name: str = ""  # tool name (Claude) or item type (Codex)
    input: str = ""
    output: str = ""
    is_error: bool = False
    turn: int = 0


# --- transcript parsing -----------------------------------------------------

def _tool_input(name: str, inp: object) -> str:
    """Most useful human-readable form of a Claude tool input."""
    if not isinstance(inp, dict):
        return json.dumps(inp, ensure_ascii=False)
    if "command" in inp:
        return str(inp["command"])
    if name in ("Edit", "MultiEdit", "Write") or "old_string" in inp or "content" in inp:
        parts = [str(inp.get("file_path", ""))]
        for k in ("old_string", "new_string", "content"):
            if k in inp:
                parts.append(f"--- {k}\n{inp[k]}")
        if "edits" in inp:
            parts.append(json.dumps(inp["edits"], indent=1, ensure_ascii=False))
        return "\n".join(parts)
    if set(inp) <= {"file_path", "offset", "limit"}:
        extra = {k: v for k, v in inp.items() if k != "file_path"}
        return str(inp.get("file_path", "")) + (f"  {extra}" if extra else "")
    return json.dumps(inp, indent=1, ensure_ascii=False)


def _result_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for c in content:
            if isinstance(c, dict):
                out.append(c.get("text") or (f"[{c.get('type')}]" if c.get("type") else json.dumps(c)))
            else:
                out.append(str(c))
        return "\n".join(out)
    return "" if content is None else json.dumps(content, ensure_ascii=False)


class _State:
    def __init__(self) -> None:
        self.events: list[Event] = []
        self.tools: dict[str, Event] = {}  # Claude tool_use id / Codex item id -> event
        self.claude_msg_ids: list[str] = []
        self.turn = 0


def _claude(obj: dict, st: _State) -> None:
    t = obj.get("type")
    if t == "assistant":
        msg = obj.get("message") or {}
        mid = msg.get("id") or f"anon-{len(st.claude_msg_ids)}"
        # stream-json may split one API message into several events sharing an id.
        if mid not in st.claude_msg_ids:
            st.claude_msg_ids.append(mid)
            st.turn = len(st.claude_msg_ids)
        for block in msg.get("content") or []:
            bt = block.get("type")
            if bt == "text" and block.get("text", "").strip():
                st.events.append(Event("text", text=block["text"], turn=st.turn))
            elif bt in ("thinking", "redacted_thinking"):
                st.events.append(Event("thinking", text=block.get("thinking") or "[redacted]", turn=st.turn))
            elif bt in ("tool_use", "server_tool_use"):
                ev = Event("tool", name=block.get("name", "?"),
                           input=_tool_input(block.get("name", ""), block.get("input")), turn=st.turn)
                st.events.append(ev)
                if block.get("id"):
                    st.tools[block["id"]] = ev
    elif t == "user":
        content = (obj.get("message") or {}).get("content")
        if isinstance(content, str):
            st.events.append(Event("system", text=content, turn=st.turn))
            return
        for block in content or []:
            if block.get("type") != "tool_result":
                continue
            ev = st.tools.get(block.get("tool_use_id", ""))
            text = _result_text(block.get("content"))
            if ev is None:
                st.events.append(Event("tool", name="(orphan result)", output=text,
                                       is_error=bool(block.get("is_error")), turn=st.turn))
            else:
                ev.output = text
                ev.is_error = bool(block.get("is_error"))
    elif t == "system":
        if obj.get("subtype") == "init":
            st.events.append(Event("system", text=f"init: model={obj.get('model')} cwd={obj.get('cwd')}"))
        else:
            st.events.append(Event("system", text=json.dumps(obj, ensure_ascii=False)[:CLIP]))
    elif t == "result":
        label = f"result: {obj.get('subtype')}, turns={obj.get('num_turns')}"
        if obj.get("is_error"):
            st.events.append(Event("error", text=f"{label}\n{obj.get('result', '')}", turn=st.turn))
        else:
            st.events.append(Event("system", text=label, turn=st.turn))


def _codex_item(item: dict, st: _State) -> None:
    it = item.get("type", "?")
    if it == "agent_message":
        st.events.append(Event("text", text=item.get("text", ""), turn=st.turn))
    elif it == "reasoning":
        st.events.append(Event("thinking", text=item.get("text", ""), turn=st.turn))
    elif it == "error":
        st.events.append(Event("error", text=item.get("message", ""), turn=st.turn))
    else:
        if it == "command_execution":
            inp, out = str(item.get("command", "")), str(item.get("aggregated_output") or "")
            code = item.get("exit_code")
            err = (code not in (None, 0)) or item.get("status") == "failed"
            if code not in (None, 0):
                out = f"exit code {code}\n{out}"
        elif it == "file_change":
            inp = "\n".join(f"{c.get('kind', '?')} {c.get('path', '')}" for c in item.get("changes") or [])
            out, err = "", item.get("status") == "failed"
        else:  # mcp_tool_call, web_search, todo_list, ...
            rest = {k: v for k, v in item.items() if k not in ("id", "type", "result", "status")}
            inp = json.dumps(rest, indent=1, ensure_ascii=False)
            out = _result_text(item.get("result")) if "result" in item else ""
            err = item.get("status") == "failed"
        st.events.append(Event("tool", name=it, input=inp, output=out, is_error=bool(err), turn=st.turn))


def _codex(obj: dict, st: _State) -> None:
    t = obj.get("type", "")
    if t == "turn.started":
        st.turn += 1
    elif t == "item.completed":
        _codex_item(obj.get("item") or {}, st)
    elif t == "turn.failed":
        err = obj.get("error") or {}
        st.events.append(Event("error", text=f"turn failed: {err.get('message', err)}", turn=st.turn))
    elif t == "error":
        st.events.append(Event("error", text=str(obj.get("message", obj)), turn=st.turn))
    elif t == "thread.started":
        st.events.append(Event("system", text=f"thread {obj.get('thread_id', '')}"))
    elif t == "turn.completed":
        u = obj.get("usage") or {}
        st.events.append(Event("system", text="turn completed: " + ", ".join(f"{k}={v}" for k, v in u.items()),
                               turn=st.turn))
    # item.started / item.updated: superseded by item.completed


def parse_transcript(lines: Iterable[str]) -> list[Event]:
    """Parse a Claude Code stream-json or Codex --json transcript into events."""
    st = _State()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            st.events.append(Event("raw", text=line, turn=st.turn))
            continue
        if not isinstance(obj, dict):
            st.events.append(Event("raw", text=line, turn=st.turn))
        elif obj.get("type") in ("assistant", "user", "system", "result"):
            _claude(obj, st)
        else:
            _codex(obj, st)
    return st.events


# --- diffs ------------------------------------------------------------------

def _norm(path: str) -> str:
    for prefix in ("a/", "b/"):
        if path.startswith(prefix):
            path = path[2:]
    return path.split("\t")[0].strip()


def _same_file(diff_path: str, v_path: str) -> bool:
    a, b = diff_path.strip("/"), v_path.strip("/")
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)


def _violation_key(v: dict) -> tuple[str, int | None]:
    line = v.get("line")
    return str(v.get("file", "")), (int(line) if isinstance(line, int) or str(line).isdigit() else None)


def render_diff(patch: str, violations: list[dict] | None = None) -> tuple[str, set[int]]:
    """Render a unified diff as an HTML table.

    Lines whose (file, new line number) match a violation are wrapped in
    `<mark class="violation" id="v-<i>" data-line="<n>">`. Returns the HTML and
    the indices of violations that were found in the diff.
    """
    violations = violations or []
    hit: set[int] = set()
    rows: list[str] = []
    cur_file = ""
    old_ln = new_ln = 0
    in_hunk = False
    for raw in patch.splitlines():
        if raw.startswith("diff --git "):
            parts = raw.split(" ")
            cur_file = _norm(parts[-1]) if len(parts) >= 4 else raw
            rows.append(f'<tr class="file"><td colspan="3">{escape(cur_file)}</td></tr>')
            in_hunk = False
            continue
        if raw.startswith("+++ ") and not in_hunk:
            p = _norm(raw[4:])
            if p != "/dev/null":
                cur_file = p
            continue
        if raw.startswith("--- ") and not in_hunk:
            continue
        if raw.startswith("@@"):
            try:
                spec = raw.split("@@")[1].split()
                old_ln = int(spec[0][1:].split(",")[0])
                new_ln = int(spec[1][1:].split(",")[0])
            except (IndexError, ValueError):
                old_ln = new_ln = 0
            in_hunk = True
            rows.append(f'<tr class="hunk"><td class="ln"></td><td class="ln"></td><td class="code">{escape(raw)}</td></tr>')
            continue
        if not in_hunk:
            continue  # index / mode / similarity headers
        tag = raw[:1]
        if tag == "+":
            cls, o, n = "add", "", new_ln
            new_ln += 1
        elif tag == "-":
            cls, o, n = "del", old_ln, ""
            old_ln += 1
        elif tag == "\\":
            cls, o, n = "meta", "", ""
        else:
            cls, o, n = "ctx", old_ln, new_ln
            old_ln += 1
            new_ln += 1
        code = escape(raw)
        if n != "":
            for i, v in enumerate(violations):
                vf, vl = _violation_key(v)
                if vl == n and _same_file(cur_file, vf):
                    title = escape(f"{v.get('kind', '')}: {v.get('detail', '')}", quote=True)
                    anchor = f' id="v-{i}"' if i not in hit else ""
                    code = f'<mark class="violation"{anchor} data-line="{n}" title="{title}">{code}</mark>'
                    hit.add(i)
        rows.append(f'<tr class="{cls}"><td class="ln">{o}</td><td class="ln">{n}</td><td class="code">{code}</td></tr>')
    if not rows:
        return '<p class="empty">Empty diff.</p>', hit
    return f'<div class="diffwrap"><table class="diff">{"".join(rows)}</table></div>', hit


# --- page -------------------------------------------------------------------

def _clip(text: str) -> str:
    if len(text) <= CLIP:
        return f"<pre>{escape(text)}</pre>"
    return (f"<pre>{escape(text[:CLIP])}\n…</pre>"
            f"<details><summary>show all ({len(text):,} chars)</summary><pre>{escape(text)}</pre></details>")


def _render_event(e: Event) -> str:
    meta = f'<div class="meta">turn {e.turn}</div>' if e.turn else ""
    if e.kind == "text":
        return f'<div class="ev text">{meta}<div class="msg">{escape(e.text)}</div></div>'
    if e.kind == "thinking":
        return (f'<details class="thinking"><summary>thinking (turn {e.turn}, {len(e.text):,} chars)</summary>'
                f'<div class="ev"><div class="msg">{escape(e.text)}</div></div></details>')
    if e.kind == "tool":
        err = " err" if e.is_error else ""
        flag = ' <span class="pill bad">error</span>' if e.is_error else ""
        out = f'<div class="out">{_clip(e.output)}</div>' if e.output else ""
        return (f'<div class="ev tool{err}"><div class="meta">turn {e.turn} · <strong>{escape(e.name)}</strong>{flag}</div>'
                f'{_clip(e.input)}{out}</div>')
    if e.kind == "error":
        return f'<div class="ev error">{meta}<div class="msg">{escape(e.text)}</div></div>'
    return f'<div class="ev"><div class="meta">{escape(e.kind)}</div>{_clip(e.text)}</div>'


def _pill(label: str, value: object, good: bool | None = None) -> str:
    cls = "" if good is None else (" ok" if good else " bad")
    return f'<span class="pill{cls}">{escape(label)}: {escape(str(value))}</span>'


def _num(x: object) -> str:
    return f"{x:,}" if isinstance(x, int) else ("–" if x is None else str(x))


def _facts(result: dict | None, agent: dict | None) -> str:
    if result is None:
        pills = ['<span class="pill warn">not evaluated yet</span>']
        if agent:
            u = agent.get("usage") or {}
            pills += [_pill("status", agent.get("status", "?"), agent.get("status") == "ok"),
                      _pill("input tokens", _num(u.get("input_tokens"))),
                      _pill("output tokens", _num(u.get("output_tokens"))),
                      _pill("turns", _num(u.get("turns"))),
                      _pill("wall s", _num(agent.get("wall_s")))]
        return "".join(pills)
    tok = result.get("tokens") or {}
    st = result.get("status", "?")
    pills = [
        _pill("status", st, st == "ok"),
        _pill("correct", "yes" if result.get("correct") else "no", bool(result.get("correct"))),
        _pill("bad decision", "yes" if result.get("bad_decision") else "no", not result.get("bad_decision")),
        _pill("lint", "ok" if result.get("lint_ok") else "fail", bool(result.get("lint_ok"))),
        _pill("typecheck", "ok" if result.get("typecheck_ok") else "fail", bool(result.get("typecheck_ok"))),
        _pill("input tokens", _num(tok.get("input"))),
        _pill("cached input", _num(tok.get("cached_input"))),
        _pill("output tokens", _num(tok.get("output"))),
        _pill("turns", _num(result.get("turns"))),
        _pill("tool calls", _num(result.get("tool_calls"))),
        _pill("wall s", _num(result.get("wall_s"))),
    ]
    if result.get("reimplementation"):
        pills.append('<span class="pill warn">reimplementation</span>')
    if result.get("eval_error"):
        pills.append(_pill("eval error", result["eval_error"], False))
    return "".join(pills)


def _violations_list(violations: list[dict], hit: set[int]) -> str:
    if not violations:
        return '<p class="empty">No violations.</p>'
    items = []
    for i, v in enumerate(violations):
        vf, vl = _violation_key(v)
        loc = escape(f"{vf}:{vl}" if vl is not None else vf)
        loc = f'<a href="#v-{i}">{loc}</a>' if i in hit else f"{loc} <span class=\"note\">(not in diff)</span>"
        items.append(f"<li><code>{escape(str(v.get('kind', '?')))}</code> {loc} — {escape(str(v.get('detail', '')))}</li>")
    return f'<ul class="violations">{"".join(items)}</ul>'


def _read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _read_text(p: Path) -> str | None:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return None


def render_run(run_dir: Path, tasks_dir: Path | None = None) -> str:
    """HTML for one run directory `runs/<agent>/<cond>/<task>/<pass>/`."""
    run_dir = Path(run_dir)
    if tasks_dir is None:
        from aa import config
        tasks_dir = config.TASKS
    result = _read_json(run_dir / "result.json")
    agent = _read_json(run_dir / "agent.json")
    parts = run_dir.parts[-4:]
    ident = dict(zip(("agent", "cond", "task", "pass"), parts)) if len(parts) == 4 else {}
    if result:
        ident.update({k: str(result[k]) for k in ("agent", "cond", "task", "pass") if k in result})

    transcript = _read_text(run_dir / "transcript.jsonl")
    if transcript is None:
        conversation = '<p class="empty">No transcript.jsonl.</p>'
    else:
        events = parse_transcript(transcript.splitlines())
        conversation = "\n".join(_render_event(e) for e in events) or '<p class="empty">Empty transcript.</p>'

    violations = list((result or {}).get("violations") or [])
    patch = _read_text(run_dir / "diff.patch")
    if patch is None:
        agent_diff, hit = '<p class="empty">No diff.patch.</p>', set()
    else:
        agent_diff, hit = render_diff(patch, violations)

    from aa.issue_tasks import reference_patch_path  # per-family reference on issue tasks
    ref = _read_text(reference_patch_path(Path(tasks_dir) / ident.get("task", "?"), ident.get("cond")))
    reference_diff = render_diff(ref)[0] if ref is not None else '<p class="empty">No reference diff for this task.</p>'

    title = " / ".join(ident.get(k, "?") for k in ("agent", "cond", "task", "pass"))
    page = Template((TEMPLATES / "run.html").read_text())
    return page.substitute(
        title=escape(f"Run {title}"),
        base_css=BASE_CSS,
        facts=_facts(result, agent),
        violations=_violations_list(violations, hit),
        conversation=conversation,
        agent_diff=agent_diff,
        reference_diff=reference_diff,
    )


def write_run_view(run_dir: Path, tasks_dir: Path | None = None) -> Path:
    out = Path(run_dir) / "view.html"
    out.write_text(render_run(run_dir, tasks_dir=tasks_dir))
    return out
