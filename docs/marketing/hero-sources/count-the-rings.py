#!/usr/bin/env python3
"""Hero image source for the article "Count the Rings or Sear the Squid".

Renders public/blog/count-the-rings.png (1020x510, exact 2:1) — the article's
central disagreement, drawn to scale rather than illustrated: the SAME four
rings (R = 10, w = 1, radii 9.0, 4.2, 4.2, 4.2) laid out the two ways that
each win a different objective.

Left  — the area optimum:        the 9.0 with one 4.2 nested in its hole.
                                 2 rings, contact area ~76.7.
Right — the cardinality optimum: three 4.2s side by side in the pan.
                                 3 rings, contact area ~69.7.

Both numbers come from the same formula the paper uses, a(r) = pi (r^2 -
max(0, r-w)^2), computed below rather than hardcoded, so the caption cannot
drift away from the geometry being drawn. Everything is at true scale: the
three small rings really are placed at the packing radius for three equal
circles in a disk, so the right panel is a legal packing and not a sketch.

Usage: python docs/marketing/hero-sources/count-the-rings.py
"""

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge

OUT = Path("public/blog/count-the-rings.png")

BG = "#1a1a24"
PAN = "#252533"
PAN_EDGE = "#3f3f52"
TEAL = "#2dd4bf"
AMBER = "#f59e0b"
TEXT = "#f8fafc"
MUTED = "#94a3b8"

R = 10.0  # pan radius
W = 1.0   # ring width
BIG = 9.0
SMALL = 4.2


def area(r: float, w: float = W) -> float:
    """Contact area of one ring: the annulus that touches the pan."""
    return math.pi * (r**2 - max(0.0, r - w) ** 2)


def draw_pan(ax) -> None:
    ax.add_patch(Circle((0, 0), R, facecolor=PAN, edgecolor=PAN_EDGE, linewidth=1.6))


def draw_ring(ax, centre, r, colour) -> None:
    """A ring drawn as what it is: an annulus of width W, not a disc."""
    ax.add_patch(
        Wedge(centre, r, 0, 360, width=min(W, r), facecolor=colour, edgecolor="none", alpha=0.92)
    )


def style(ax) -> None:
    ax.set_xlim(-R * 1.08, R * 1.08)
    ax.set_ylim(-R * 1.08, R * 1.08)
    ax.set_aspect("equal")
    ax.axis("off")


def main() -> None:
    fig = plt.figure(figsize=(10.20, 5.10), dpi=100)
    fig.patch.set_facecolor(BG)

    left = fig.add_axes([0.06, 0.20, 0.38, 0.66])
    right = fig.add_axes([0.56, 0.20, 0.38, 0.66])
    for ax in (left, right):
        style(ax)
        draw_pan(ax)

    # Left: the area optimum — the big ring, with one small ring in its hole.
    draw_ring(left, (0, 0), BIG, AMBER)
    draw_ring(left, (0, 0), SMALL, AMBER)
    area_left = area(BIG) + area(SMALL)

    # Right: the cardinality optimum — three small rings, at the true packing
    # radius for three equal circles in a disk (centres on a triangle, each
    # ring tangent to the pan wall).
    d = R - SMALL
    for k in range(3):
        angle = math.radians(90 + 120 * k)
        draw_ring(right, (d * math.cos(angle), d * math.sin(angle)), SMALL, TEAL)
    area_right = 3 * area(SMALL)

    fig.text(0.25, 0.925, "sear the squid", color=AMBER, fontsize=15,
             ha="center", va="center", fontweight="bold")
    fig.text(0.75, 0.925, "count the rings", color=TEAL, fontsize=15,
             ha="center", va="center", fontweight="bold")

    fig.text(0.25, 0.115, f"2 rings  ·  area {area_left:.1f}", color=TEXT,
             fontsize=13, ha="center", va="center", family="monospace")
    fig.text(0.75, 0.115, f"3 rings  ·  area {area_right:.1f}", color=TEXT,
             fontsize=13, ha="center", va="center", family="monospace")

    fig.text(0.5, 0.035, "same four rings, same pan, two different right answers",
             color=MUTED, fontsize=11.5, ha="center", va="center", fontstyle="italic")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG, edgecolor="none", dpi=100)

    # matplotlib rounds the canvas down by a pixel; the hero contract is an
    # exact 2:1 1020x510, and OG scrapers dislike alpha, so flatten and pin it.
    from PIL import Image

    im = Image.open(OUT).convert("RGB").resize((1020, 510), Image.LANCZOS)
    im.save(OUT)
    print(f"wrote {OUT} ({im.size[0]}x{im.size[1]}) — area {area_left:.1f} vs {area_right:.1f}")


if __name__ == "__main__":
    main()
