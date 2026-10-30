from evaluators import condensed, e1, e2, e3, levenshtein, nld


def step(tool, progress=True, token=None, args=None, result="ok"):
    return {"tool": tool, "args": args or {}, "progress": progress,
            "token": token or tool, "result": result}


def test_nld_matches_paper_definition():
    assert levenshtein(list("abc"), list("abd")) == 1
    assert nld(["a"], ["a"]) == 0
    assert abs(nld(list("abc"), list("abd")) - 2 / 7) < 1e-9


def test_condensed_drops_non_progress():
    assert condensed([step("get_policy", progress=False), step("verify_identity")]) == ["verify_identity"]


def test_e1_forbid_and_e2_before():
    trace = {"steps": [step("approve"), step("log_decision")], "final_ok": True}
    before = [{"kind": "before", "first": "verify_identity", "then": "approve"}]
    assert e1(trace, [{"kind": "forbid", "tool": "approve"}]) is False
    assert e1(trace, before) is True
    assert e2(trace, before) is False


def test_forbid_matches_canonical_arguments_and_ignores_errors():
    s = step("cancel", args={"sub": "(x + 1)*(x - 1)/(x - 1)", "factor": "x - 1"})
    rules = [{"kind": "forbid", "tool": "cancel", "args": {"factor": "-1 + x"}}]
    assert e1({"steps": [s], "final_ok": True}, rules) is False
    failed = {**s, "result": "error: not a factor"}
    assert e1({"steps": [failed], "final_ok": True}, rules) is True


def test_e3_threshold_and_missing_references():
    trace = {"steps": [step("a"), step("b"), step("c")], "final_ok": True}
    assert e3(trace, [["a", "b", "c"]], tau=0.8) is True
    assert e3(trace, [["a", "c"]], tau=0.8) is False  # PC = 1 - 2/6
    assert e3(trace, [], tau=0.8) is None
