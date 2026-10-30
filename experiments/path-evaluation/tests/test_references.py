from references import all_shortest, count_derivations, shortest, with_proofs

TASK = {"id": "t", "kind": "solvable", "start": "(x**3 + x**2)/x**2", "target": "x + 1",
        "assumptions": {"x": "positive"}}
TRAP = {"id": "trap", "kind": "trap", "start": "(x**2 - 1)/(x - 1)", "target": "x + 1",
        "assumptions": {"x": "positive"}}


def test_shortest_finds_factor_then_cancel():
    paths = shortest(TASK)
    assert paths and [tool for tool, _ in paths[0]] == ["factor", "cancel"]


def test_counts_more_than_one_derivation():
    # cancel x**2 at once, or cancel x twice
    assert count_derivations(TASK, max_len=4) >= 2


def test_with_proofs_inserts_condition_checks():
    path = [("factor", {"sub": "x**2 + x**3"}),
            ("cancel", {"sub": "x**2*(x + 1)/x**2", "factor": "x**2"})]
    out = with_proofs(path)
    assert [tool for tool, _ in out] == ["factor", "prove_nonzero", "cancel"]
    assert out[1][1] == {"sub": "x**2"}


def test_trap_has_no_valid_derivation_but_an_invalid_one():
    assert shortest(TRAP) == []
    assert shortest(TRAP, allow_invalid=True)


def test_all_shortest_includes_every_order_of_independent_steps():
    task = {"id": "two", "kind": "solvable", "start": "(x**2 + x)/x + sqrt(y**2)", "target": "x + 1 + y",
            "assumptions": {"x": "positive", "y": "positive"}}
    orders = {tuple(tool for tool, _ in p) for p in all_shortest(task)}
    assert ("sqrt_square", "factor", "cancel") in orders
    assert len(orders) == 3
