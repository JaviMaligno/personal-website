import analyze


def rec(world, task, truth, **judge):
    base = {"truth": truth, "E0": False, "E1": False, "E2": False, "E3": False, "pc": 0.0}
    base.update(judge)
    return {"world": world, "task": task, "model": "m", "rep": 0, "judge": base}


A = [
    rec("a", "b01", False, E0=True, E1=False, E2=False, E3=True, pc=0.9, test_edits=["tests/test_number.py"], tokens=["run_tests"]),
    rec("a", "b01", True, E0=True, E1=True, E2=True, E3=False, pc=0.6, test_edits=[], tokens=["run_tests", "edit:x"]),
]
B = [
    rec("b", "t01", False, E0=True, E1=False, E3=True, pc=0.9, sorry=True, axioms=["sorryAx"], statement_intact=True, tactics=["simp"]),
    rec("b", "t01", True, E0=True, E1=True, E3=False, pc=0.5, sorry=False, axioms=[], statement_intact=True, tactics=["induction", "simp"]),
]


def test_fp_fn_world_a():
    t = analyze.fp_fn(A)
    assert t["E0"] == {"FP": 1, "FN": 0}
    assert t["E3"] == {"FP": 1, "FN": 1}
    assert t["E1"] == {"FP": 0, "FN": 0}


def test_fp_fn_world_b():
    t = analyze.fp_fn(B)
    assert t["E0"] == {"FP": 1, "FN": 0}
    assert t["E3"] == {"FP": 1, "FN": 1}


def test_tau_curve_counts_one_fp_and_one_fn_at_extremes():
    c = analyze.tau_curve(A)
    assert c[0.5] == {"FP": 1, "FN": 1 - 1}  # pc 0.6 passes at tau 0.5: no FN
    assert c[1.0] == {"FP": 0, "FN": 1}


def test_mechanisms_and_routes():
    assert analyze.mechanism(A[0]) == "test edits"
    assert analyze.mechanism(B[0]) == "sorry"
    assert analyze.routes(A) == {"b01": 1}
    assert analyze.routes(B) == {"t01": 1}
    assert len(analyze.e3_fn_pairs(A)) == 0  # no E3-true truth-true counterpart on the task
