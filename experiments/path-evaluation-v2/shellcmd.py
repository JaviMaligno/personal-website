"""Turn one shell command line into actions of the common vocabulary.

`;`, `&&`, `||` separate actions; in a pipeline only the first command is an action
(`pytest | tail` is a test run). Quotes are respected when splitting.
"""
from __future__ import annotations

import re
import shlex

READ = {"cat", "head", "tail", "less", "more", "nl", "type", "get-content", "gc"}
SEARCH = {"grep", "rg", "ag", "findstr", "select-string", "sls"}
LIST = {"ls", "dir", "find", "tree", "get-childitem", "gci", "get-location", "pwd"}


def unwrap_powershell(cmd: str) -> str:
    m = re.search(r"powershell(?:\.exe)?\"?\s+-Command\s+(['\"])(.*)\1\s*$", cmd, re.S | re.I)
    return m.group(2) if m else cmd


def split_segments(cmd: str) -> list[str]:
    out, cur, quote, i = [], "", None, 0
    while i < len(cmd):
        c = cmd[i]
        if quote:
            cur += c
            if c == quote:
                quote = None
        elif c in "'\"":
            quote, cur = c, cur + c
        elif cmd.startswith("&&", i) or cmd.startswith("||", i):
            out.append(cur); cur = ""; i += 1
        elif c in ";|\n":
            out.append(cur); cur = ""
        else:
            cur += c
        i += 1
    out.append(cur)
    return [s.strip() for s in out if s.strip()]


def _actions(cmd: str) -> list[tuple[str, bool]]:
    """Segments with a flag saying whether each one starts a new action (False = piped into)."""
    res, cur, quote, i, piped = [], "", None, 0, False
    while i < len(cmd):
        c = cmd[i]
        if quote:
            cur += c
            quote = None if c == quote else quote
        elif c in "'\"":
            quote, cur = c, cur + c
        elif cmd.startswith("&&", i) or cmd.startswith("||", i):
            res.append((cur.strip(), not piped)); cur, piped = "", False; i += 1
        elif c == "|":
            res.append((cur.strip(), not piped)); cur, piped = "", True
        elif c in ";\n":
            res.append((cur.strip(), not piped)); cur, piped = "", False
        else:
            cur += c
        i += 1
    res.append((cur.strip(), not piped))
    return [(s, new) for s, new in res if s]


def _rel(path: str, root: str) -> str:
    p = path.replace("\\", "/").strip("'\"")
    r = root.replace("\\", "/").rstrip("/")
    if p.lower().startswith(r.lower() + "/"):
        p = p[len(r) + 1:]
    return p[2:] if p.startswith("./") else p


def _files(words: list[str]) -> list[str]:
    return [w for w in words[1:] if not w.startswith("-") and ("/" in w or "." in w) and not re.fullmatch(r"[\d,]+p", w)]


NULL_SINKS = {"/dev/null", "nul", "$null"}


def _redirect_target(seg: str) -> str | None:
    """File written by an output redirection outside quotes; None for comparisons (`>=`),
    `2>&1`, null sinks and redirections that live inside a quoted script."""
    unquoted = re.sub(r"'[^']*'|\"[^\"]*\"", "''", seg)
    m = re.search(r"(?<![<>=!-])\d?>{1,2}(?![=>&])\s*([^\s;|&<>]+)", unquoted)
    if not m or m.group(1).lower() in NULL_SINKS or m.group(1) == "''":
        return None
    return m.group(1)


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.S)


def strip_heredocs(cmd: str) -> str:
    """A heredoc's body is the input of one command, not more commands: keep only its first line."""
    return HEREDOC.sub(lambda m: "<<HEREDOC" + m.group(3), cmd)


def classify_segment(seg: str, root: str) -> dict:
    try:
        words = shlex.split(seg, posix=True)
    except ValueError:
        words = seg.split()
    if not words:
        return {"kind": "run_other", "target": ""}
    head = words[0].lower()
    joined = " ".join(words).lower()
    files = _files(words)
    if "pytest" in joined or head in {"py.test"}:
        return {"kind": "run_tests", "target": ""}
    if head in {"lean", "lake"}:
        return {"kind": "compile", "target": ""}
    if head == "sed" and "-i" in words:
        return {"kind": "edit", "target": _rel(files[-1], root) if files else ""}
    if head in {"set-content", "out-file", "add-content"}:
        return {"kind": "edit", "target": _rel(files[-1], root) if files else ""}
    redirect = _redirect_target(seg)
    if redirect:
        return {"kind": "edit", "target": _rel(redirect, root)}
    if head == "sed" or head in READ:
        return {"kind": "read", "target": _rel(files[-1], root) if files else ""}
    if head in SEARCH or (head == "git" and len(words) > 1 and words[1] == "grep"):
        return {"kind": "list", "target": ""} if "--files" in words else {"kind": "search", "target": ""}
    if head in LIST:
        return {"kind": "list", "target": ""}
    return {"kind": "run_other", "target": ""}


SCRIPT_WRITE = re.compile(r"write_text\(|\.write\(|open\([^)]*,\s*['\"][wa]\+?['\"]")
SCRIPT_TARGET = re.compile(r"['\"]([\w./\\-]+\.(?:py|lean|toml|cfg|txt|md))['\"]")


def _script_edit(cmd: str, root: str) -> dict | None:
    """A Python script (heredoc or -c) that writes a file is an edit of that file: agents edit
    this way too (seen: Opus rewriting time.py through `python - <<EOF ... open(p).write(...)`)."""
    if not re.search(r"\bpython[\d.]*(?:\.exe)?\b", cmd) or not SCRIPT_WRITE.search(cmd):
        return None
    m = SCRIPT_TARGET.search(cmd)
    return {"kind": "edit", "target": _rel(m.group(1), root) if m else ""}


def classify(cmd: str, root: str) -> list[dict]:
    raw = unwrap_powershell(cmd)
    edit = _script_edit(raw, root)
    acts = [classify_segment(s, root) for s, new in _actions(strip_heredocs(raw)) if new]
    if edit:  # the python segment becomes the edit, in its own place; the rest keeps its actions
        i = next((k for k, a in enumerate(acts) if a["kind"] == "run_other"), None)
        acts = [a for a in acts if a["kind"] != "run_other"]
        acts.insert(len(acts) if i is None else min(i, len(acts)), edit)
    return acts
