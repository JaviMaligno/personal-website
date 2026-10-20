"""Result tables generated from `result.json` files, never typed by hand.

`aa tables` -> `out/tables.md` + `out/summary.json`. Per agent:

- rates per condition (correct, bad decision, any violation) with Wilson CIs;
- Fisher exact p for the contrasts A vs AP, A vs AL, AP vs APL, AL vs APL,
  plus the difference detectable at the achieved n;
- the 2x2 interaction (lint x A⁺) by mixed-effects logistic regression with a
  task random effect (statsmodels `BinomialBayesMixedGLM`, imported lazily);
- tokens on correct runs: median and IQR per condition, Mann-Whitney A vs AP.

Counting rules (spec §6):
- `infra` runs are never counted (they are retried; any leftover is excluded
  and reported as `excluded_infra`).
- `timeout` counts as a failure: correct only if `status == "ok"` and the
  hidden tests passed.
- bad decision = correct AND >= 1 violation; any violation is over all runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median, quantiles

from aa.config import AGENTS, CONDITIONS
from aa.stats import detectable_difference, fisher_exact, mann_whitney_u, wilson

METRICS = ("correct", "bad_decision", "any_violation")
METRIC_LABELS = {
    "correct": "correct",
    "bad_decision": "bad decision",
    "any_violation": "any violation",
}
CONTRASTS = (("A", "AP"), ("A", "AL"), ("AP", "APL"), ("AL", "APL"))
# Condition -> (lint, plus) factors of the 2x2 design.
FACTORS = {"A": (0, 0), "AL": (1, 0), "AP": (0, 1), "APL": (1, 1)}


def load_results(runs_dir: Path) -> list[dict]:
    """Every `result.json` under `runs_dir`, in a stable order."""
    return [json.loads(p.read_text()) for p in sorted(Path(runs_dir).rglob("result.json"))]


def is_correct(r: dict) -> bool:
    return r.get("status") == "ok" and bool(r.get("correct"))


def metric_value(r: dict, metric: str) -> bool:
    if metric == "correct":
        return is_correct(r)
    if metric == "bad_decision":
        return is_correct(r) and bool(r.get("violations"))
    if metric == "any_violation":
        return bool(r.get("violations"))
    raise ValueError(f"unknown metric {metric!r}")


def total_tokens(r: dict) -> int:
    """Input + output tokens (cached input is reported separately)."""
    t = r.get("tokens") or {}
    return int(t.get("input", 0)) + int(t.get("output", 0))


def format_rate(k: int, n: int) -> str:
    """`75% [30–95]`: rate and Wilson 95% interval, in whole percent."""
    if n == 0:
        return "–"
    lo, hi = wilson(k, n)
    return f"{round(100 * k / n)}% [{round(100 * lo)}–{round(100 * hi)}]"


def _fmt_p(p: float | None) -> str:
    if p is None:
        return "–"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def _counted(results: list[dict], agent: str) -> list[dict]:
    return [r for r in results if r.get("agent") == agent and r.get("status") != "infra"]


def _by_cond(runs: list[dict]) -> dict[str, list[dict]]:
    return {c: [r for r in runs if r.get("cond") == c] for c in CONDITIONS}


def _quartiles(values: list[int]) -> list[float]:
    if len(values) == 1:
        return [values[0], values[0]]
    q = quantiles(values, n=4, method="inclusive")
    return [q[0], q[2]]


def _num(x: float) -> float | int:
    return int(x) if float(x).is_integer() else x


def interaction(results: list[dict], agent: str, metric: str) -> dict:
    """lint x A⁺ interaction on `metric`, task as random effect.

    Returns `{"available": False, "reason": ...}` when statsmodels is not
    installed or the model cannot be fitted (e.g. a metric with no variation),
    so the tables still build.
    """
    runs = _counted(results, agent)
    try:
        import pandas as pd
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
    except ImportError:
        return {"available": False, "reason": "statsmodels not installed"}
    rows = [
        {
            "y": int(metric_value(r, metric)),
            "lint": FACTORS[r["cond"]][0],
            "plus": FACTORS[r["cond"]][1],
            "task": str(r.get("task")),
        }
        for r in runs
        if r.get("cond") in FACTORS
    ]
    ys = {row["y"] for row in rows}
    if len(ys) < 2:
        return {"available": False, "reason": "no variation in outcome"}
    df = pd.DataFrame(rows)
    try:
        model = BinomialBayesMixedGLM.from_formula(
            "y ~ lint * plus", {"task": "0 + C(task)"}, df
        )
        fit = model.fit_vb()
    except Exception as exc:  # noqa: BLE001 - report, never crash the tables
        return {"available": False, "reason": f"fit failed: {exc}"}
    names = list(model.exog_names)
    coef = {
        name: {"mean": float(fit.fe_mean[i]), "sd": float(fit.fe_sd[i])}
        for i, name in enumerate(names)
    }
    return {"available": True, "n": len(rows), "coef": coef}


# Per-task fields of result.json the tables can be split by (`aa tables --by`).
GROUP_FIELDS = ("source", "ai_label", "contaminated")


def _group_value(r: dict, field: str) -> str:
    v = r.get(field)
    return "n/a" if v is None else str(v).lower() if isinstance(v, bool) else str(v)


def summarise(results: list[dict], by: str | None = None) -> dict:
    """Summary per agent; with ``by`` (one of GROUP_FIELDS) per agent and value of that
    field, keyed ``"<agent> | <field>=<value>"`` (``n/a`` for null, e.g. ai_label on
    issue tasks)."""
    if by is not None:
        if by not in GROUP_FIELDS:
            raise ValueError(f"unknown grouping {by!r}; expected one of {GROUP_FIELDS}")
        out: dict = {}
        for val in sorted({_group_value(r, by) for r in results}):
            part = summarise([r for r in results if _group_value(r, by) == val])
            out.update({f"{agent} | {by}={val}": s for agent, s in part.items()})
        return out
    agents = [a for a in AGENTS if any(r.get("agent") == a for r in results)]
    agents += sorted({r.get("agent") for r in results} - set(agents) - {None})
    summary: dict = {}
    for agent in agents:
        runs = _counted(results, agent)
        by_cond = _by_cond(runs)
        excluded = sum(
            1 for r in results if r.get("agent") == agent and r.get("status") == "infra"
        )

        rates = {}
        for m in METRICS:
            rates[m] = {}
            for c in CONDITIONS:
                k = sum(metric_value(r, m) for r in by_cond[c])
                n = len(by_cond[c])
                lo, hi = wilson(k, n)
                rates[m][c] = {"k": k, "n": n, "rate": k / n if n else None,
                               "ci": [lo, hi], "cell": format_rate(k, n)}

        contrasts = []
        for c1, c2 in CONTRASTS:
            entry: dict = {"pair": [c1, c2]}
            n_min = min(len(by_cond[c1]), len(by_cond[c2]))
            for m in METRICS:
                a, n1 = rates[m][c1]["k"], rates[m][c1]["n"]
                c, n2 = rates[m][c2]["k"], rates[m][c2]["n"]
                entry[m] = {"p": fisher_exact(a, n1 - a, c, n2 - c)}
            # Detectable difference at the achieved n, around the pooled
            # correct rate of the two arms (clipped so 0%/100% do not give 0).
            pooled_n = rates["correct"][c1]["n"] + rates["correct"][c2]["n"]
            pooled = (
                (rates["correct"][c1]["k"] + rates["correct"][c2]["k"]) / pooled_n
                if pooled_n else 0.5
            )
            p_base = min(0.95, max(0.05, pooled))
            entry["detectable_difference"] = detectable_difference(n_min, p_base)
            entry["detectable_p_base"] = p_base
            entry["n_min"] = n_min
            contrasts.append(entry)

        tokens = {}
        for c in CONDITIONS:
            ok = [r for r in by_cond[c] if is_correct(r)]
            vals = sorted(total_tokens(r) for r in ok)
            cached = sorted(int((r.get("tokens") or {}).get("cached_input", 0)) for r in ok)
            tokens[c] = {
                "n": len(vals),
                "median": _num(median(vals)) if vals else None,
                "iqr": [_num(q) for q in _quartiles(vals)] if vals else None,
                "cached_median": _num(median(cached)) if cached else None,
            }
        x = [total_tokens(r) for r in by_cond["A"] if is_correct(r)]
        y = [total_tokens(r) for r in by_cond["AP"] if is_correct(r)]
        u, p = mann_whitney_u(x, y)

        summary[agent] = {
            "n_by_status": {
                c: {s: sum(1 for r in by_cond[c] if r.get("status") == s)
                    for s in sorted({r.get("status") for r in by_cond[c]})}
                for c in CONDITIONS
            },
            "excluded_infra": excluded,
            "rates": rates,
            "contrasts": contrasts,
            "interaction": {m: interaction(results, agent, m)
                            for m in ("correct", "bad_decision", "any_violation")},
            "tokens": tokens,
            "tokens_mann_whitney_A_vs_AP": {"u": u, "p": p},
        }
    return summary


def render_markdown(summary: dict) -> str:
    lines = ["# Results tables", "",
             "Generated by `aa tables` from `result.json` files. Rates are "
             "`rate [Wilson 95% CI]`; `infra` runs excluded, `timeout` counts "
             "as not correct.", ""]
    header = "| | " + " | ".join(CONDITIONS) + " |"
    sep = "|---" * (len(CONDITIONS) + 1) + "|"
    for agent, s in summary.items():
        lines += [f"## {agent}", ""]
        lines += [f"Runs counted per condition: " + ", ".join(
            f"{c} {s['rates']['correct'][c]['n']}" for c in CONDITIONS
        ) + f"; infra excluded: {s['excluded_infra']}.", ""]

        lines += ["### Rates", "", header, sep]
        for m in METRICS:
            cells = " | ".join(s["rates"][m][c]["cell"] for c in CONDITIONS)
            lines.append(f"| {METRIC_LABELS[m]} | {cells} |")
        lines.append("")

        lines += ["### Contrasts (Fisher exact, two-sided)", "",
                  "| contrast | correct p | bad decision p | any violation p "
                  "| detectable difference (n, p_base) |",
                  "|---|---|---|---|---|"]
        for e in s["contrasts"]:
            c1, c2 = e["pair"]
            lines.append(
                f"| {c1} vs {c2} | {_fmt_p(e['correct']['p'])} "
                f"| {_fmt_p(e['bad_decision']['p'])} | {_fmt_p(e['any_violation']['p'])} "
                f"| {round(100 * e['detectable_difference'])} pts "
                f"(n={e['n_min']}, {round(100 * e['detectable_p_base'])}%) |"
            )
        lines += ["", "Differences below the detectable one are reported as "
                  "\"not detectable\", never as \"no effect\".", ""]

        lines += ["### Interaction lint x A⁺ (mixed-effects logistic, task random effect)",
                  "", "| outcome | lint:plus mean (sd) | n |", "|---|---|---|"]
        for m, inter in s["interaction"].items():
            if inter.get("available"):
                co = inter["coef"].get("lint:plus")
                val = f"{co['mean']:.2f} ({co['sd']:.2f})" if co else "–"
                lines.append(f"| {METRIC_LABELS[m]} | {val} | {inter['n']} |")
            else:
                lines.append(f"| {METRIC_LABELS[m]} | unavailable: {inter['reason']} | – |")
        lines.append("")

        lines += ["### Tokens on correct runs (input + output)", "",
                  "| cond | n | median | IQR | cached input median |",
                  "|---|---|---|---|---|"]
        for c in CONDITIONS:
            t = s["tokens"][c]
            iqr = f"{t['iqr'][0]}–{t['iqr'][1]}" if t["iqr"] else "–"
            med = t["median"] if t["median"] is not None else "–"
            cmed = t["cached_median"] if t["cached_median"] is not None else "–"
            lines.append(f"| {c} | {t['n']} | {med} | {iqr} | {cmed} |")
        mw = s["tokens_mann_whitney_A_vs_AP"]
        lines += ["", f"Mann-Whitney A vs AP: U = {mw['u']:g}, p = {_fmt_p(mw['p'])}.", ""]
    return "\n".join(lines)


def build(runs_dir: Path, out_dir: Path, by: str | None = None) -> dict:
    """Write `tables.md` and `summary.json` into `out_dir`; return the summary."""
    summary = summarise(load_results(runs_dir), by=by)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tables.md").write_text(render_markdown(summary))
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary
