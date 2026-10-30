import sympy

from expr import canon, from_sympy, norm, parse, replace, subterms, to_str, to_sympy


def test_roundtrip_does_not_simplify():
    assert to_str(norm(parse("(x*y + x)/x"))) == "(x + x*y)/x"
    assert to_str(norm(parse("(x + 1)*(x - 1)/(x + 1)"))) == "(x + 1)*(x - 1)/(x + 1)"


def test_print_then_parse_is_identity():
    for s in ["x - 1", "-2*x + y", "sqrt((x + 1)**2) + log(x*y)", "x**2*(x + 1)/x**2", "-(x + y)"]:
        t = norm(parse(s))
        assert norm(parse(to_str(t))) == t


def test_subterms_and_replace():
    t = norm(parse("sqrt((x + 1)**2) + y"))
    sub = norm(parse("(x + 1)**2"))
    assert sub in list(subterms(t))
    new, ok = replace(t, sub, norm(parse("z")))
    assert ok and to_str(norm(new)) == "sqrt(z) + y"


def test_to_sympy_uses_assumptions():
    assert to_sympy(norm(parse("x**2 + x")), {"x": "positive"}).is_positive is True
    assert to_sympy(norm(parse("x - 1")), {"x": "positive"}).is_nonnegative is None


def test_from_sympy_factor():
    t = from_sympy(sympy.factor(to_sympy(norm(parse("x**2 - 1")))))
    assert to_str(t) == "(x + 1)*(x - 1)"


def test_canon_normalises_and_falls_back():
    assert canon("1 + x") == "x + 1"
    assert canon("not an expression!") == "not an expression!"
