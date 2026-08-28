#!/usr/bin/env python3
"""Hero image source for the article "The Bug Nobody Can Reach".

Renders public/blog/the-bug-nobody-can-reach.png (1020x510, exact 2:1): the
same doughnut-shaped wrong region, moved. In the left panel the planned route
threads its hole and the wrong model costs 0.019; in the right panel the same
object sits so the route runs into its solid part and it costs 0.898. Same
object, same contact rarity (0.0033), same trivial shape — only the position
relative to the path changes.

Numbers are the paper's TubeField3D control, from
results/tubefield_mechanism.json in JaviMaligno/code-world-models:
`aligned` (route threads the hole) = 0.0191 and `offset` (route hits the
tube) = 0.8985.

    python docs/marketing/hero-sources/the-bug-nobody-can-reach.py
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

R_IN, R_OUT = 2.2, 3.6
START = (-7.6, 0.0)
GOAL = (7.0, 0.0)

OUT = (pathlib.Path(__file__).resolve().parents[3] / "public" / "blog"
       / "the-bug-nobody-can-reach.png")


def panel(ax, *, centre_y: float, colour: str, blocked: bool,
          tag: str, cost: str) -> None:
    ax.set_facecolor(PANEL)
    ax.set_xlim(-8.8, 8.8)
    ax.set_ylim(-5.2, 7.4)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_color(EDGE)
        side.set_linewidth(1.0)

    # the wrong region: a doughnut, drawn identically in both panels
    ax.add_patch(Wedge((0, centre_y), R_OUT, 0, 360, width=R_OUT - R_IN,
                       facecolor=colour, edgecolor="none", alpha=0.85))

    ax.plot([GOAL[0]], [GOAL[1]], marker="*", markersize=20, color=GOLD, zorder=5)
    ax.plot([GOAL[0]], [GOAL[1]], marker="*", markersize=40, color=GOLD,
            alpha=0.16, zorder=4)
    ax.plot([START[0]], [START[1]], marker="o", markersize=8, color=TEXT, zorder=5)

    if blocked:
        # where the route (y = 0) first meets the outer circle
        stop = -((R_OUT ** 2 - centre_y ** 2) ** 0.5)
        ax.annotate("", xy=(stop - 0.35, 0), xytext=START,
                    arrowprops=dict(arrowstyle="-|>", color=TEXT, lw=2.1,
                                    linestyle=(0, (5, 3)), shrinkA=0, shrinkB=0))
        ax.plot([stop], [0], marker="X", markersize=15, color=TEXT,
                markeredgecolor=PANEL, markeredgewidth=1.4, zorder=6)
    else:
        ax.annotate("", xy=(GOAL[0] - 0.85, 0), xytext=START,
                    arrowprops=dict(arrowstyle="-|>", color=TEXT, lw=2.1,
                                    linestyle=(0, (5, 3)), shrinkA=0, shrinkB=0))

    ax.text(0, 6.7, tag, color=MUTED, fontsize=11, ha="center", va="center",
            family="monospace", fontweight="bold")
    ax.text(0, -4.4, cost, color=colour, fontsize=17, ha="center", va="center",
            family="monospace", fontweight="bold")


def main() -> None:
    fig = plt.figure(figsize=(10.2, 5.1), dpi=100)
    fig.patch.set_facecolor(BG)

    fig.text(0.5, 0.945, "THE SAME WRONG REGION · MOVED",
             color=MUTED, fontsize=12.5, ha="center", va="center",
             family="monospace", fontweight="bold")

    left = fig.add_axes([0.045, 0.175, 0.435, 0.72])
    right = fig.add_axes([0.520, 0.175, 0.435, 0.72])

    panel(left, centre_y=0.0, colour=SAFE, blocked=False,
          tag="THE ROUTE THREADS THE HOLE", cost="costs you  0.019")
    panel(right, centre_y=2.9, colour=DANGER, blocked=True,
          tag="THE ROUTE RUNS INTO IT", cost="costs you  0.898")

    fig.text(0.2625, 0.115, "nothing you run ever touches it",
             color=MUTED, fontsize=10.5, ha="center", va="center",
             family="monospace")
    fig.text(0.7375, 0.115, "nearly as bad as acting at random",
             color=MUTED, fontsize=10.5, ha="center", va="center",
             family="monospace")

    fig.text(0.5, 0.042, "what it costs is set by the path, not by the shape",
             color=TEXT, fontsize=14, ha="center", va="center", fontstyle="italic")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG, edgecolor="none", dpi=100)

    from PIL import Image

    im = Image.open(OUT).convert("RGB").resize((1020, 510), Image.LANCZOS)
    im.save(OUT)
    print(f"wrote {OUT} ({im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    main()
