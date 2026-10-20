import json
from pathlib import Path

import pytest

from aa import tables
from aa.stats import fisher_exact, mann_whitney_u, sample_size_for, wilson

# (cond, task, pass, status, correct, n_violations, input_tokens, output_tokens)
# Hand-counted per condition (status != ok counts as not correct):
#   A:   correct 3/4, bad decision 2/4, any violation 3/4
#   AL:  correct 4/4, bad decision 1/4, any violation 1/4
#   AP:  correct 2/4 (one timeout reports correct=true), bad 0/4, any 0/4
#   APL: correct 4/4, bad decision 0/4, any violation 0/4
RUNS = [
    ("A", "t1", 0, "ok", True, 1, 1000, 100),
    ("A", "t1", 1, "ok", True, 2, 2000, 200),
    ("A", "t2", 0, "ok", True, 0, 3000, 300),
    ("A", "t2", 1, "ok", False, 1, 9000, 900),
    ("AL", "t1", 0, "ok", True, 1, 1500, 150),
    ("AL", "t1", 1, "ok", True, 0, 1500, 150),
    ("AL", "t2", 0, "ok", True, 0, 2500, 250),
    ("AL", "t2", 1, "ok", True, 0, 2500, 250),
    ("AP", "t1", 0, "ok", True, 0, 500, 50),
    ("AP", "t1", 1, "ok", False, 0, 600, 60),
    ("AP", "t2", 0, "ok", True, 0, 700, 70),
    ("AP", "t2", 1, "timeout", True, 0, 8000, 800),
    ("APL", "t1", 0, "ok", True, 0, 400, 40),
    ("APL", "t1", 1, "ok", True, 0, 400, 40),
    ("APL", "t2", 0, "ok", True, 0, 400, 40),
    ("APL", "t2", 1, "ok", True, 0, 400, 40),
]


def _result(cond, task, pass_idx, status, correct, n_viol, tin, tout, agent="claude"):
    violations = [
        {"kind": "raw_write", "file": "src/server/x.ts", "line": 40 + i, "detail": "UPDATE"}
        for i in range(n_viol)
    ]
    return {
        "agent": agent, "cond": cond, "task": task, "pass": pass_idx,
        "status": status, "correct": correct,
        "violations": violations,
        "bad_decision": correct and bool(violations),
        "lint_ok": True, "typecheck_ok": True,
        "tokens": {"input": tin, "output": tout, "cached_input": 10 * tin},
        "turns": 5, "tool_calls": 10, "wall_s": 60,
        "diff": {"files": 1, "added": 3, "removed": 1},
        "reimplementation": False,
        "trace": {"files_read": [], "first_edit_turn": 2, "lint_invocations": 1},
    }


def _write(runs_dir: Path, result: dict) -> None:
    d = runs_dir / result["agent"] / result["cond"] / result["task"] / str(result["pass"])
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps(result))


@pytest.fixture
def runs_dir(tmp_path):
    root = tmp_path / "runs"
    for row in RUNS:
        _write(root, _result(*row))
    return root


def test_format_rate_matches_hand_computed_wilson():
    assert tables.format_rate(3, 4) == "75% [30–95]"
    assert tables.format_rate(4, 4) == "100% [51–100]"
    assert tables.format_rate(2, 4) == "50% [15–85]"
    assert tables.format_rate(0, 4) == "0% [0–49]"
    assert tables.format_rate(0, 0) == "–"


def test_rate_cells_per_condition(runs_dir):
    summary = tables.summarise(tables.load_results(runs_dir))
    rates = summary["claude"]["rates"]
    assert rates["correct"]["A"]["cell"] == "75% [30–95]"
    assert rates["correct"]["AL"]["cell"] == "100% [51–100]"
    assert rates["correct"]["AP"]["cell"] == "50% [15–85]"
    assert rates["correct"]["APL"]["cell"] == "100% [51–100]"
    assert (rates["bad_decision"]["A"]["k"], rates["bad_decision"]["A"]["n"]) == (2, 4)
    assert rates["bad_decision"]["A"]["cell"] == "50% [15–85]"
    assert rates["bad_decision"]["AL"]["cell"] == "25% [5–70]"
    assert rates["any_violation"]["A"]["cell"] == "75% [30–95]"
    assert rates["any_violation"]["APL"]["cell"] == "0% [0–49]"


def test_timeout_is_not_correct_even_if_tests_passed(runs_dir):
    summary = tables.summarise(tables.load_results(runs_dir))
    assert summary["claude"]["rates"]["correct"]["AP"]["k"] == 2
    assert summary["claude"]["n_by_status"]["AP"] == {"ok": 3, "timeout": 1}


def test_infra_runs_are_excluded(runs_dir):
    _write(runs_dir, _result("A", "t3", 0, "infra", False, 0, 0, 0))
    summary = tables.summarise(tables.load_results(runs_dir))
    assert summary["claude"]["rates"]["correct"]["A"]["n"] == 4
    assert summary["claude"]["excluded_infra"] == 1


def test_contrasts_use_fisher_on_the_cells(runs_dir):
    summary = tables.summarise(tables.load_results(runs_dir))
    contrasts = summary["claude"]["contrasts"]
    assert [c["pair"] for c in contrasts] == [["A", "AP"], ["A", "AL"], ["AP", "APL"], ["AL", "APL"]]
    a_vs_ap = contrasts[0]
    assert a_vs_ap["correct"]["p"] == pytest.approx(fisher_exact(3, 1, 2, 2))
    assert a_vs_ap["bad_decision"]["p"] == pytest.approx(fisher_exact(2, 2, 0, 4))
    assert a_vs_ap["any_violation"]["p"] == pytest.approx(fisher_exact(3, 1, 0, 4))
    # Detectable difference at the achieved n (4 per condition) is reported.
    assert 0 < a_vs_ap["detectable_difference"] <= 1


def test_tokens_on_correct_runs_only(runs_dir):
    summary = tables.summarise(tables.load_results(runs_dir))
    tok = summary["claude"]["tokens"]
    # A correct runs: 1100, 2200, 3300 (input + output); the failed 9900 is out.
    assert tok["A"]["n"] == 3
    assert tok["A"]["median"] == 2200
    assert tok["A"]["iqr"] == [1650, 2750]
    # AP correct runs (timeout excluded): 550, 770.
    assert tok["AP"]["median"] == 660
    assert tok["A"]["cached_median"] == 20000
    mw = summary["claude"]["tokens_mann_whitney_A_vs_AP"]
    u, p = mann_whitney_u([1100, 2200, 3300], [550, 770])
    assert mw == {"u": u, "p": pytest.approx(p)}


def test_build_writes_markdown_and_json(runs_dir, tmp_path):
    out = tmp_path / "out"
    tables.build(runs_dir, out)
    md = (out / "tables.md").read_text()
    data = json.loads((out / "summary.json").read_text())
    assert "## claude" in md
    assert "| correct | 75% [30–95] | 100% [51–100] | 50% [15–85] | 100% [51–100] |" in md
    assert "A vs AP" in md
    assert data["claude"]["rates"]["correct"]["A"]["k"] == 3


def test_interaction_degrades_without_statsmodels(runs_dir, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_statsmodels(name, *args, **kwargs):
        if name.startswith("statsmodels"):
            raise ImportError("no statsmodels")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_statsmodels)
    results = tables.load_results(runs_dir)
    inter = tables.interaction(results, "claude", "correct")
    assert inter["available"] is False


def test_interaction_with_statsmodels(runs_dir):
    pytest.importorskip("statsmodels")
    inter = tables.interaction(tables.load_results(runs_dir), "claude", "correct")
    assert inter["available"] is True
    assert "lint:plus" in inter["coef"]


# --- stats.py sanity (ported from agent-code-practices tests) ---------------


def test_wilson_reference_values():
    lo, hi = wilson(14, 18)
    assert 0.54 < lo < 0.56 and 0.90 < hi < 0.92
    assert wilson(0, 0) == (0.0, 0.0)
    assert wilson(0, 10)[1] > 0.2


def test_fisher_reference_values():
    assert fisher_exact(15, 2, 14, 4) > 0.05
    assert fisher_exact(2, 10, 8, 4) < 0.05


def test_sample_size_reference_values():
    assert sample_size_for(0.78, 0.67) > 200
    assert sample_size_for(0.67, 0.17) < 20


def test_mann_whitney_hand_computed():
    # Full separation, n=3 vs 3: U=0, mean 4.5, sd sqrt(5.25);
    # z = (4.5 - 0.5) / 2.2913 = 1.7457 -> p = 0.0809 (scipy asymptotic agrees).
    u, p = mann_whitney_u([1, 2, 3], [4, 5, 6])
    assert u == 0
    assert p == pytest.approx(0.0809, abs=1e-3)
    assert mann_whitney_u([], [1]) == (0.0, 1.0)
    assert mann_whitney_u([2, 2], [2, 2])[1] == 1.0


def test_summarise_splits_by_task_field(tmp_path):
    root = tmp_path / "runs"
    for i, row in enumerate(RUNS):
        r = _result(*row)
        r["source"] = "issue" if row[1] == "t2" else "mined"
        r["ai_label"] = None if r["source"] == "issue" else bool(i % 2)
        r["contaminated"] = row[1] == "t2"
        _write(root, r)
    results = tables.load_results(root)
    by_src = tables.summarise(results, by="source")
    assert set(by_src) == {"claude | source=issue", "claude | source=mined"}
    # t1 only: A correct 2/2, AP correct 1/2
    assert by_src["claude | source=mined"]["rates"]["correct"]["A"]["k"] == 2
    assert by_src["claude | source=mined"]["rates"]["correct"]["AP"]["k"] == 1
    assert set(tables.summarise(results, by="ai_label")) == {
        "claude | ai_label=n/a", "claude | ai_label=false", "claude | ai_label=true"}
    assert set(tables.summarise(results, by="contaminated")) == {
        "claude | contaminated=false", "claude | contaminated=true"}
    with pytest.raises(ValueError):
        tables.summarise(results, by="nope")
    out = tmp_path / "out"
    tables.build(root, out, by="source")
    assert "## claude | source=issue" in (out / "tables.md").read_text()
