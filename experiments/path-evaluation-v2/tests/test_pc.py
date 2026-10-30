from pc import condense, levenshtein, nld, pc


def test_metric():
    assert levenshtein(list("abc"), list("abd")) == 1
    assert abs(nld(list("abc"), list("abd")) - 2 / 7) < 1e-9
    assert pc(["a", "b"], [["a", "b"], ["x"]]) == 1.0


def test_condense_collapses_repeats_and_drops_noise():
    assert condense(["list", "read:a", "read:a", "run_other", "edit:a", "run_tests"]) == ["read:a", "edit:a", "run_tests"]
