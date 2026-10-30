from analyze import fn_kind, table


def tr(world, kind, truth, final_ok, steps):
    return {"world": world, "task_id": "t", "kind": kind, "model": "m", "rep": 0,
            "stop": "done", "truth": truth, "final_ok": final_ok, "steps": steps}


def s(tok):
    return {"tool": tok, "args": {}, "progress": True, "token": tok, "result": "ok", "valid": None}


def test_table_counts_false_positives_and_negatives():
    tasks = {("rewrite", "t"): {"rules": [], "reference_tokens": [["a", "b"]]}}
    traces = [tr("rewrite", "solvable", False, True, [s("a"), s("b")]),          # E0 FP
              tr("rewrite", "solvable", True, True, [s("a"), s("x"), s("y"), s("b")])]  # E3 FN
    rows = table(traces, tasks, tau=0.8)
    assert rows[("rewrite", "E0")] == {"n": 2, "FP": 1, "FN": 0}
    assert rows[("rewrite", "E3")]["FN"] == 1


def test_fn_kind():
    assert fn_kind(["b", "a"], [["a", "b"]]) == "order"
    assert fn_kind(["a", "x", "b"], [["a", "b"]]) == "extra_steps"
    assert fn_kind(["z"], [["a", "b"]]) == "other"
