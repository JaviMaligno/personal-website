"""The centred prime sum G(y), computed from the primes alone.

    G(y) = sum_{n <= y} Lambda(n) (y/n - 1)  -  y (log y - 1 - gamma)

Lambda(n) = log p when n is a power of the prime p, 0 otherwise. The explicit
formula says G(y) = log 2pi - sum_rho y^rho / (rho (rho - 1)) + O(y^-2), so the
Riemann hypothesis (every rho has real part 1/2) is the statement that
G(y) - log 2pi stays inside a band of width proportional to sqrt(y):

    |G(y) - log 2pi| <= (2 + gamma - log 4pi) sqrt(y) = 0.0462 sqrt(y)

The announced proof needs only the upper side of that band, and only on long
windows [Y, Y^(3/2)]. This script draws (G(y) - log 2pi) / sqrt(y) for
y up to 10^7 and the band, and prints the largest value found.

Usage: python scripts/figures/riemann-centred-prime-sum.py
Writes: public/blog/riemann-hypothesis-proof-prime-sum.png
"""
import math

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BG = "#1a1a24"
TEAL = "#2dd4bf"
AMBER = "#f59e0b"
MUTED = "#94a3b8"
TEXT = "#e2e8f0"

N = 10_000_000
GAMMA = 0.5772156649015329
BAND = 2 + GAMMA - math.log(4 * math.pi)


def von_mangoldt(n):
    """Lambda(1..n) by a sieve."""
    lam = np.zeros(n + 1)
    sieve = np.ones(n + 1, dtype=bool)
    sieve[:2] = False
    for p in range(2, int(n**0.5) + 1):
        if sieve[p]:
            sieve[p * p :: p] = False
    for p in np.nonzero(sieve)[0]:
        lp = math.log(p)
        q = int(p)
        while q <= n:
            lam[q] = lp
            q *= int(p)
    return lam


def main():
    lam = von_mangoldt(N)
    n = np.arange(N + 1, dtype=np.float64)
    n[0] = 1.0
    psi = np.cumsum(lam)  # sum of Lambda(n) for n <= y
    harm = np.cumsum(lam / n)  # sum of Lambda(n)/n for n <= y

    # sample y on a log grid plus every integer up to 2000 (G is continuous in y)
    ys = np.unique(
        np.concatenate([np.arange(10, 2000), np.logspace(math.log10(2000), 7, 60000)])
    )
    k = np.floor(ys).astype(int)
    G = ys * harm[k] - psi[k] - ys * (np.log(ys) - 1 - GAMMA)
    r = (G - math.log(2 * math.pi)) / np.sqrt(ys)
    print(f"band: +-{BAND:.4f}")
    print(f"max |G(y) - log 2pi| / sqrt(y) for 10 <= y <= 1e7: {np.abs(r).max():.4f}")
    print(f"max: {r.max():.4f}  min: {r.min():.4f}")

    fig, ax = plt.subplots(figsize=(12, 5.2), dpi=150)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.axhspan(-BAND, BAND, color=TEAL, alpha=0.08, lw=0)
    for s in (1, -1):
        ax.axhline(s * BAND, color=TEAL, lw=1.2, ls="--")
    ax.axhline(0, color=MUTED, lw=0.6, alpha=0.5)
    ax.plot(ys, r, color=AMBER, lw=0.7)
    ax.set_xscale("log")
    ax.set_xlim(10, N)
    ax.set_ylim(-0.085, 0.085)
    ax.set_xlabel("y  (how far along the number line the primes are counted)", color=MUTED, fontsize=11)
    ax.set_ylabel("(G(y) − log 2π) / √y", color=MUTED, fontsize=11)
    ax.tick_params(colors=MUTED, labelsize=10)
    for sp in ax.spines.values():
        sp.set_color("#334155")
    ax.text(12, BAND + 0.006, "the band the Riemann hypothesis predicts: ±0.0462", color="#5eead4", fontsize=10.5)
    ax.text(12, -0.076, "a zero off the critical line would make this curve grow like a power of y and leave the band for good",
            color=MUTED, fontsize=10)
    ax.set_title("The weighted prime count, computed from the primes up to ten million",
                 color=TEXT, fontsize=13, pad=12, loc="left")
    fig.tight_layout()
    fig.savefig("public/blog/riemann-hypothesis-proof-prime-sum.png", facecolor=BG)


if __name__ == "__main__":
    main()
