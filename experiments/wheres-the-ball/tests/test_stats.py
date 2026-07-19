import numpy as np
import pytest

from wheresball.stats import bootstrap_ci, compare_systems, holm_correction, paired_wilcoxon


def test_bootstrap_ci_contains_estimate_and_is_deterministic():
    rng = np.random.default_rng(0)
    values = rng.normal(1.0, 0.2, size=200)
    ci1 = bootstrap_ci(values, n_replicates=2000, seed=42)
    ci2 = bootstrap_ci(values, n_replicates=2000, seed=42)
    assert ci1 == ci2
    assert ci1.low <= ci1.estimate <= ci1.high
    assert ci1.low == pytest.approx(1.0, abs=0.1)


def test_bootstrap_ci_empty_raises():
    with pytest.raises(ValueError):
        bootstrap_ci([])


def test_paired_wilcoxon_detects_shift():
    rng = np.random.default_rng(1)
    a = rng.normal(0.5, 0.1, size=100)
    b = a + 0.05  # consistently worse
    assert paired_wilcoxon(a, b) < 1e-6
    assert paired_wilcoxon(a, a) == 1.0


def test_paired_wilcoxon_length_mismatch():
    with pytest.raises(ValueError):
        paired_wilcoxon([1, 2], [1, 2, 3])


def test_holm_correction_monotone_and_bounded():
    raw = [0.01, 0.04, 0.03, 0.5]
    adj = holm_correction(raw)
    assert all(a >= r for a, r in zip(adj, raw))
    assert all(0 <= a <= 1 for a in adj)
    # Smallest raw p gets the largest multiplier: 0.01 * 4.
    assert adj[0] == pytest.approx(0.04)


def test_compare_systems_pairs_and_holm():
    rng = np.random.default_rng(2)
    base = rng.normal(0.5, 0.1, size=80)
    errors = {"good": base, "bad": base + 0.1, "worse": base + 0.2}
    comparisons = compare_systems(errors)
    assert len(comparisons) == 3
    for c in comparisons:
        assert c.p_holm >= c.p_raw
        assert c.p_holm < 0.01  # all clearly separated
