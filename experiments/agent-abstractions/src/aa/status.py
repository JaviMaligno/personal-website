"""Live status page `runs/status.html` (spec §10, plan Task 10).

Reads every run directory under the runs root and renders, per agent ×
condition: finished/total, correct rate and bad-decision rate with 95% Wilson
intervals, median tokens and `infra` retries; plus the latest 20 problem runs
linked to their `view.html`. `watch()` regenerates the page whenever a
`result.json` or `agent.json` appears or changes.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
from html import escape
from pathlib import Path
from string import Template

from aa.viewer import BASE_CSS, TEMPLATES, write_run_view

FINISHED = ("ok", "timeout")  # statuses that count as a finished run
COND_LABELS = {"A": "A", "AL": "A+L", "AP": "A⁺", "APL": "A⁺+L"}
DEFAULT_AGENTS = ("claude", "codex")
DEFAULT_CONDS = ("A", "AL", "AP", "APL")
LATEST = 20


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes out of n."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def fmt_rate(k: int, n: int) -> str:
    """`"33% [6–79]"`: rate and Wilson interval, rounded to whole percents."""
    if n == 0:
        return "–"
    lo, hi = wilson(k, n)
    return f"{round(100 * k / n)}% [{round(100 * lo)}–{round(100 * hi)}]"


def _load(p: Path) -> dict | None:
    try:
        d = json.loads(p.read_text())
        return d if isinstance(d, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def collect_results(root: Path) -> list[dict]:
    """One row per run dir under `root` that has a `result.json` or `agent.json`.

    The row is `result.json` (or, when the run is not evaluated yet, identity
    fields from the path plus `status` from `agent.json`), with private keys:
    `_evaluated`, `_view` (path of `view.html` relative to root), `_dir`,
    `_mtime` and `_infra_retries` (`infra_retries` from agent.json/result.json,
    else 1 if the run currently sits in `infra`).
    """
    root = Path(root)
    dirs = {p.parent for name in ("result.json", "agent.json") for p in root.rglob(name)}
    rows = []
    for d in sorted(dirs):
        result = _load(d / "result.json")
        agent = _load(d / "agent.json") or {}
        rel = d.relative_to(root)
        if result is not None:
            row = dict(result)
        else:
            row = {"status": agent.get("status", "unknown")}
        for key, val in zip(("agent", "cond", "task", "pass"), rel.parts[-4:]):
            row.setdefault(key, val)
        retries = row.get("infra_retries", agent.get("infra_retries"))
        if not isinstance(retries, int):
            retries = 1 if row.get("status") == "infra" else 0
        mtimes = [p.stat().st_mtime for p in (d / "result.json", d / "agent.json") if p.exists()]
        row.update({
            "_evaluated": result is not None,
            "_view": (rel / "view.html").as_posix(),
            "_dir": str(d),
            "_mtime": max(mtimes),
            "_infra_retries": retries,
        })
        rows.append(row)
    return rows


def _tokens(r: dict) -> int | None:
    t = r.get("tokens") or {}
    if not isinstance(t.get("input"), int) and not isinstance(t.get("output"), int):
        return None
    return int(t.get("input") or 0) + int(t.get("output") or 0)


def _fmt_tokens(x: float | None) -> str:
    if x is None:
        return "–"
    return f"{x / 1000:.1f}k" if x >= 1000 else f"{x:.0f}"


def _is_problem(r: dict) -> bool:
    if r.get("status") not in FINISHED:
        return r.get("status") == "infra" or r.get("_evaluated", True)
    if not r.get("_evaluated", True):
        return False
    return r.get("status") != "ok" or not r.get("correct") or bool(r.get("bad_decision"))


def _default_total() -> int | None:
    try:
        from aa import config
        n_tasks = sum(1 for p in config.TASKS.iterdir() if (p / "task.json").exists())
        return n_tasks * config.PASSES if n_tasks else None
    except (OSError, ImportError):
        return None


def render_status(rows: list[dict], total_per_cell: int | None = None) -> str:
    agents = list(DEFAULT_AGENTS) + sorted({str(r.get("agent")) for r in rows} - set(DEFAULT_AGENTS))
    conds = list(DEFAULT_CONDS) + sorted({str(r.get("cond")) for r in rows} - set(DEFAULT_CONDS))
    body = []
    tot_done = tot_retries = 0
    for agent in agents:
        body.append(f'<tr class="agent"><th colspan="7">{escape(agent)}</th></tr>')
        for cond in conds:
            cell = [r for r in rows if str(r.get("agent")) == agent and str(r.get("cond")) == cond]
            fin = [r for r in cell if r.get("status") in FINISHED and r.get("_evaluated", True)]
            n = len(fin)
            correct = sum(1 for r in fin if r.get("status") == "ok" and r.get("correct"))
            bad = sum(1 for r in fin if r.get("bad_decision"))
            toks = [t for r in fin if (t := _tokens(r)) is not None]
            retries = sum(int(r.get("_infra_retries", 0)) for r in cell)
            tot_done += n
            tot_retries += retries
            total = "–" if total_per_cell is None else str(total_per_cell)
            body.append(
                f'<tr><td class="l"><code>{escape(cond)}</code> {escape(COND_LABELS.get(cond, ""))}</td>'
                f"<td>{n}/{total}</td><td>{fmt_rate(correct, n)}</td><td>{fmt_rate(bad, n)}</td>"
                f"<td>{_fmt_tokens(statistics.median(toks) if toks else None)}</td>"
                f"<td>{sum(1 for r in cell if r.get('status') == 'timeout')}</td><td>{retries}</td></tr>")
    grid = ('<table class="grid"><thead><tr><th class="l">Condition</th><th>Done/total</th>'
            '<th>Correct</th><th>Bad decision</th><th>Median tokens</th><th>Timeouts</th>'
            '<th>Infra retries</th></tr></thead><tbody>' + "".join(body) + "</tbody></table>")

    problems = sorted((r for r in rows if _is_problem(r)), key=lambda r: r.get("_mtime", 0), reverse=True)[:LATEST]
    if problems:
        items = []
        for r in problems:
            what = []
            if r.get("status") != "ok":
                what.append(str(r.get("status")))
            elif not r.get("correct"):
                what.append("incorrect")
            if r.get("bad_decision"):
                what.append("bad decision")
            if r.get("eval_error"):
                what.append(f"eval error: {r['eval_error']}")
            ident = [str(r.get(k, "?")) for k in ("agent", "cond", "task", "pass")]
            href = r.get("_view") or "/".join(ident) + "/view.html"
            items.append(f'<li><a href="{escape(href, quote=True)}">{escape(" / ".join(ident))}</a> — '
                         f'{escape(", ".join(what))}</li>')
        latest = f'<ul class="latest">{"".join(items)}</ul>'
    else:
        latest = '<p class="empty">No problem runs yet.</p>'

    grand = "–" if total_per_cell is None else str(total_per_cell * len(agents) * len(conds))
    facts = (f'<span class="pill">finished: {tot_done}/{grand}</span>'
             f'<span class="pill{" warn" if tot_retries else ""}">infra retries: {tot_retries}</span>'
             f'<span class="pill">updated: {escape(time.strftime("%Y-%m-%d %H:%M:%S"))}</span>')
    return Template((TEMPLATES / "status.html").read_text()).substitute(
        base_css=BASE_CSS, facts=facts, grid=grid, latest=latest)


def write_status(root: Path, total_per_cell: int | None = None, tasks_dir: Path | None = None) -> Path:
    """Write `<root>/status.html`, (re)rendering `view.html` for linked problem runs."""
    root = Path(root)
    rows = collect_results(root)
    if total_per_cell is None:
        total_per_cell = _default_total()
    for r in rows:
        if not _is_problem(r):
            continue
        view = root / r["_view"]
        if not view.exists() or view.stat().st_mtime < r["_mtime"]:
            write_run_view(view.parent, tasks_dir=tasks_dir)
    out = root / "status.html"
    out.write_text(render_status(rows, total_per_cell=total_per_cell))
    return out


def _signature(root: Path) -> tuple:
    return tuple(sorted((str(p), p.stat().st_mtime) for name in ("result.json", "agent.json")
                        for p in Path(root).rglob(name)))


def watch(root: Path, interval: float = 30.0, total_per_cell: int | None = None,
          max_iterations: int | None = None) -> None:
    """Regenerate status.html whenever a result/agent file changes (poll)."""
    last: tuple | None = None
    i = 0
    while max_iterations is None or i < max_iterations:
        sig = _signature(root)
        if sig != last:
            out = write_status(root, total_per_cell=total_per_cell)
            print(f"{time.strftime('%H:%M:%S')} wrote {out} ({len(sig)} files)", file=sys.stderr)
            last = sig
        i += 1
        if max_iterations is None or i < max_iterations:
            time.sleep(interval)
