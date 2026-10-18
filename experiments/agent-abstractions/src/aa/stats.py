"""Whether a difference stands out from noise, and how many runs it would take.

Copied from agent-code-practices (https://github.com/JaviMaligno/agent-code-practices,
`src/acp/stats.py` at commit 47853cd). The formulas and their behaviour are
unchanged; docstrings and comments were translated from Spanish to English to
match this repository's language, and the keyword arguments of
`sample_size_for` were renamed accordingly (`potencia` -> `power`,
`alfa` -> `alpha`). One function was added below the copied block
(`mann_whitney_u`, marked as such), needed for the token comparison of this
experiment.

No external dependencies on purpose: these are closed-form formulas, and the
experiment already has enough moving parts.
"""

from __future__ import annotations

from math import comb, erf, sqrt

# The usual critical values, written once. z at 95% for the interval; the
# second one is the z of 80% power, the point where an experiment is usually
# considered worth running.
Z_95 = 1.959964
Z_POWER_80 = 0.841621


def wilson(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Confidence interval for a proportion, by the Wilson method.

    Wilson rather than the normal approximation because with small cells and
    rates close to 0% or 100% the normal one leaves [0, 1] and gives
    impossible bounds.
    """
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    margin = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided p of the table [[a, b], [c, d]], by Fisher's exact test.

    Exact rather than chi-square because with cells of a few dozen runs the
    asymptotic approximation does not hold.
    """
    n = a + b + c + d
    if n == 0 or (a + b) == 0 or (c + d) == 0:
        return 1.0

    def probability(x: int) -> float:
        return comb(a + b, x) * comb(c + d, a + c - x) / comb(n, a + c)

    observed = probability(a)
    minimum = max(0, a + c - (c + d))
    maximum = min(a + b, a + c)
    # The relative margin keeps the observed table itself from falling out of
    # the sum because of a floating-point rounding error.
    return min(1.0, sum(
        probability(x) for x in range(minimum, maximum + 1)
        if probability(x) <= observed * (1 + 1e-9)
    ))


def sample_size_for(
    p1: float, p2: float, power: float = 0.80, alpha: float = 0.05
) -> int:
    """Runs per condition needed to see a difference between `p1` and `p2`.

    The question to ask **before** running: if the answer is hundreds of runs
    per condition, a design with a few dozen cannot conclude anything about
    that difference.
    """
    if p1 == p2:
        raise ValueError("no difference to detect: p1 and p2 are equal")
    z_alpha = Z_95 if abs(alpha - 0.05) < 1e-9 else _z(1 - alpha / 2)
    z_beta = Z_POWER_80 if abs(power - 0.80) < 1e-9 else _z(power)
    mean = (p1 + p2) / 2
    numerator = (
        z_alpha * sqrt(2 * mean * (1 - mean))
        + z_beta * sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2
    from math import ceil

    return ceil(numerator / (p1 - p2) ** 2)


def detectable_difference(n: int, p_base: float = 0.78) -> float:
    """The smallest drop that `n` runs per condition allow one to see.

    The useful complement of `sample_size_for`: given what one can afford to
    run, it says which effects are out of reach, which is what must be stated
    when a block comes out without differences ("not detectable", never
    "no effect").
    """
    if n <= 0:
        return 1.0
    return min(1.0, (Z_95 + Z_POWER_80) * sqrt(2 * p_base * (1 - p_base) / n))


def _z(p: float) -> float:
    """Standard normal quantile, by bisection on the error function."""
    low, high = -10.0, 10.0
    for _ in range(200):
        middle = (low + high) / 2
        if 0.5 * (1 + erf(middle / sqrt(2))) < p:
            low = middle
        else:
            high = middle
    return (low + high) / 2


# --- Added for agent-abstractions (not in the original module) --------------


def mann_whitney_u(x: list[float], y: list[float]) -> tuple[float, float]:
    """Mann-Whitney U of `x` vs `y` and its two-sided p.

    Normal approximation with tie correction and continuity correction (the
    same as scipy's `method="asymptotic", use_continuity=True`). Returns U for
    `x` (number of pairs where x wins, ties counting one half). With an empty
    sample, or when every value is tied, there is nothing to compare: p = 1.
    """
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return (0.0, 1.0)
    pooled = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks = [0.0] * len(pooled)
    tie_term = 0.0
    i = 0
    while i < len(pooled):
        j = i
        while j + 1 < len(pooled) and pooled[j + 1][0] == pooled[i][0]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = average
        t = j - i + 1
        tie_term += t ** 3 - t
        i = j + 1
    r1 = sum(r for r, (_, group) in zip(ranks, pooled) if group == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    n = n1 + n2
    mean = n1 * n2 / 2
    variance = n1 * n2 / 12 * ((n + 1) - tie_term / (n * (n - 1)))
    if variance <= 0:
        return (u1, 1.0)
    z = (abs(u1 - mean) - 0.5) / sqrt(variance)
    z = max(z, 0.0)
    p = 2 * (1 - 0.5 * (1 + erf(z / sqrt(2))))
    return (u1, min(1.0, p))
