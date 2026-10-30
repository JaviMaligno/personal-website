"""CORE's Path Correctness: 1 - normalised Levenshtein, best over the references."""


def levenshtein(a, b) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def nld(a, b) -> float:
    ld = levenshtein(a, b)
    return 0.0 if ld == 0 else 2 * ld / (len(a) + len(b) + ld)


def pc(tokens, refs) -> float:
    return max(1 - nld(tokens, r) for r in refs)


NOISE = {"list", "run_other"}


def condense(tokens):
    out = []
    for t in tokens:
        if t in NOISE or (out and out[-1] == t):
            continue
        out.append(t)
    return out
