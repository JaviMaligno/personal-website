from rewrite import RewriteWorld


def test_valid_cancel_reaches_target():
    w = RewriteWorld("(x**2 + x)/x", "x + 1", {"x": "positive"})
    w.call("factor", {"sub": "x**2 + x"})
    assert w.steps[-1]["state"] == "x*(x + 1)/x"
    w.call("cancel", {"sub": "x*(x + 1)/x", "factor": "x"})
    assert w.steps[-1]["valid"] is True
    assert w.final_ok() and w.truth()


def test_invalid_step_is_applied_and_recorded():
    w = RewriteWorld("(x**2 - 1)/(x - 1)", "x + 1", {"x": "positive"})
    w.call("factor", {"sub": "x**2 - 1"})
    w.call("cancel", {"sub": "(x + 1)*(x - 1)/(x - 1)", "factor": "x - 1"})
    assert w.steps[-1]["valid"] is False
    assert w.final_ok() and not w.truth()


def test_inapplicable_rule_is_an_error_not_a_step():
    w = RewriteWorld("x + 1", "x + 1", {"x": "positive"})
    out = w.call("cancel", {"sub": "x + 1", "factor": "x"})
    s = w.steps[-1]
    assert out.startswith("error") and s["changed"] is False and s["valid"] is None
    assert s["progress"] is False


def test_prove_counts_as_progress_only_when_proved():
    w = RewriteWorld("(x - 1)/(x - 1)", "1", {"x": "positive"})
    assert w.call("prove_nonzero", {"sub": "x - 1"}) == "not proved"
    assert w.steps[-1]["progress"] is False
    assert w.call("prove_positive", {"sub": "x"}) == "proved"
    assert w.steps[-1]["progress"] is True


def test_token_normalises_arguments():
    w = RewriteWorld("(x**2 + x)/x", "x + 1", {"x": "positive"})
    w.call("factor", {"sub": "x**2 + x"})
    assert w.steps[-1]["token"] == "factor(sub=x + x**2)"


def test_sqrt_square_and_log_product_conditions():
    w = RewriteWorld("sqrt((x + 1)**2) + log(x*y)", "x + 1 + log(x) + log(y)",
                     {"x": "positive", "y": "real"})
    w.call("sqrt_square", {"sub": "sqrt((x + 1)**2)"})
    assert w.steps[-1]["valid"] is True
    w.call("log_product", {"sub": "log(x*y)"})
    assert w.steps[-1]["valid"] is False
    assert w.final_ok() and not w.truth()


def test_expand_and_factor_refuse_fractions():
    w = RewriteWorld("(x**2 + x)/x", "x + 1", {"x": "positive"})
    assert w.call("factor", {"sub": "(x**2 + x)/x"}).startswith("error")


def test_trap_truth_is_about_validity_not_reaching():
    w = RewriteWorld("(x*y + y)/y", "x + 1", {"x": "real", "y": "real"}, kind="trap")
    w.call("submit", {})
    assert w.done and not w.final_ok() and w.truth()
