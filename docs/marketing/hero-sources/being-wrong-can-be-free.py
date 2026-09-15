#!/usr/bin/env python3
"""Hero image source for the article "Being Wrong Can Be Free".

Renders public/blog/being-wrong-can-be-free.png (1020x510, exact 2:1) — the
article's central contrast, drawn rather than illustrated: the same annular
no-go band with the same channel width, once where the planner drives through
it and once hidden behind the goal. Same first Betti number, opposite danger.

Both numbers come from ONE series so the comparison is like for like: the
LLM arm's exploited blind artifacts at gamma = 0.6, facing versus hidden,
16 paired MPC episodes per cell — `danger["0.6|facing"]` (0.0292) and
`danger["0.6|hidden"]` (1.1164) in
results/continuous_ring2d_open_sweep_summary.json of
JaviMaligno/code-world-models. The hidden value equals the closed ring's
(`danger["0.0|facing"]`, 1.1164) to four decimals, because it is the same
blind program facing the same reachable world.

    python docs/marketing/hero-sources/being-wrong-can-be-free.py
"""
from __future__ import annotations

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Wedge  # noqa: E402

BG = "#14141c"
PANEL = "#1a1a24"
EDGE = "#2a2a38"
DANGER = "#f43f5e"
SAFE = "#6366f1"
GOLD = "#fbbf24"
TEXT = "#f8fafc"
MUTED = "#94a3b8"

R_IN, R_OUT = 3.5, 5.0
GAP_DEG = 34.0          # 0.59 rad, i.e. the gamma = 0.6 cells drawn to scale
START = (-7.4, 0.0)

OUT = pathlib.Path(__file__).resolve().parents[3] / "public" / "blog" / "being-wrong-can-be-free.png"


def band(ax, gap_centre_deg: float, colour: str) -> None:
    """The annulus, with a channel of GAP_DEG centred on gap_centre_deg."""
    theta1 = gap_centre_deg + GAP_DEG / 2
    theta2 = gap_centre_deg - GAP_DEG / 2 + 360
    ax.add_patch(
        Wedge((0, 0), R_OUT, theta1, theta2, width=R_OUT - R_IN,
              facecolor=colour, edgecolor="none", alpha=0.85)
    )


def panel(ax, *, gap_centre_deg: float, colour: str, reaches: bool,
          tag: str, cost: str) -> None:
    ax.set_facecolor(PANEL)
    ax.set_xlim(-8.6, 8.6)
    ax.set_ylim(-6.6, 6.6)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_color(EDGE)
        side.set_linewidth(1.0)

    band(ax, gap_centre_deg, colour)

    # the phantom lode the planner wants, inside the hole
    ax.plot([0], [0], marker="*", markersize=22, color=GOLD, zorder=5)
    ax.plot([0], [0], marker="*", markersize=44, color=GOLD, alpha=0.16, zorder=4)

    # the start, outside the band
    ax.plot([START[0]], [START[1]], marker="o", markersize=8,
            color=TEXT, zorder=5)

    # the plan: straight at the lode
    if reaches:
        ax.annotate("", xy=(-1.05, 0), xytext=START,
                    arrowprops=dict(arrowstyle="-|>", color=TEXT, lw=2.1,
                                    linestyle=(0, (5, 3)), shrinkA=0, shrinkB=0))
    else:
        ax.annotate("", xy=(-R_OUT - 0.45, 0), xytext=START,
                    arrowprops=dict(arrowstyle="-|>", color=TEXT, lw=2.1,
                                    linestyle=(0, (5, 3)), shrinkA=0, shrinkB=0))
        ax.plot([-R_OUT - 0.02], [0], marker="X", markersize=15,
                color=TEXT, markeredgecolor=PANEL, markeredgewidth=1.4, zorder=6)

    ax.text(0, 5.85, tag, color=MUTED, fontsize=11, ha="center", va="center",
            family="monospace", fontweight="bold")
    ax.text(0, -5.75, cost, color=colour, fontsize=17, ha="center", va="center",
            family="monospace", fontweight="bold")


def main() -> None:
    fig = plt.figure(figsize=(10.2, 5.1), dpi=100)
    fig.patch.set_facecolor(BG)

    fig.text(0.5, 0.945, "SAME BAND · SAME γ = 0.6 · SAME β₁ = 0",
             color=MUTED, fontsize=12.5, ha="center", va="center",
             family="monospace", fontweight="bold")

    left = fig.add_axes([0.045, 0.185, 0.435, 0.715])
    right = fig.add_axes([0.520, 0.185, 0.435, 0.715])

    panel(left, gap_centre_deg=180.0, colour=SAFE, reaches=True,
          tag="CHANNEL FACING THE START", cost="play cost  0.029")
    panel(right, gap_centre_deg=0.0, colour=DANGER, reaches=False,
          tag="SAME CHANNEL, HIDDEN BEHIND THE GOAL",
          cost="play cost  1.116")

    fig.text(0.2625, 0.125, "the blind plan becomes true: danger collapses",
             color=MUTED, fontsize=10.5, ha="center", va="center",
             family="monospace")
    fig.text(0.7375, 0.125, "1.116 with the band closed, too",
             color=MUTED, fontsize=10.5, ha="center", va="center",
             family="monospace")

    fig.text(0.5, 0.045, "danger is topology relative to reach",
             color=TEXT, fontsize=14, ha="center", va="center",
             fontstyle="italic")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG, edgecolor="none", dpi=100)

    # matplotlib rounds the canvas down by a pixel; the hero contract is an
    # exact 2:1 1020x510, and OG scrapers dislike alpha, so flatten and pin it.
    from PIL import Image

    im = Image.open(OUT).convert("RGB").resize((1020, 510), Image.LANCZOS)
    im.save(OUT)
    print(f"wrote {OUT} ({im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    main()
