#!/usr/bin/env python3
"""In-article figures for "Count the Rings or Sear the Squid" (EN + ES).

The paper's own figures exist, but they are labelled in Spanish and the phase
diagram writes the small-ring radius as rho -- which is the symbol the article
uses for the violation of superincreasingness. Redrawn here instead: one
version per language, in the site palette, with the article's notation.

Every position is computed, never eyeballed:
  fig 1  minimal divergence instance, R = 10, w = 1, radii {9, 4.2, 4.2, 4.2}
         left  = area optimum (9 with one 4.2 nested), right = count optimum
         (three 4.2s at the true three-circle packing radius).
  fig 2  phase diagram of the divergence band, ported from the paper's
         `franja.py`: exact proved thresholds for n equal circles in a disk.
  fig 3  the n = 4 counterexample, R = 15, w = 0.3, radii {10, 5, 4.9, 4.8}.
         Left = best fit (nests the 5, strands the 4.8), right = worst fit
         (all four, with both tangencies exact).

Usage: python docs/marketing/hero-sources/count-the-rings-figures.py
"""

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Circle, Patch, Wedge

OUT = Path("public/blog")

BG = "#1a1a24"
PAN = "#252533"
PAN_EDGE = "#3f3f52"
TEAL = "#2dd4bf"
AMBER = "#f59e0b"
SLATE = "#64748b"
TEXT = "#f8fafc"
MUTED = "#94a3b8"

STRINGS = {
    "en": {
        "sear": "area optimum",
        "count": "count optimum",
        "rings2": "2 rings · area 76.7",
        "rings3": "3 rings · area 69.7",
        "cap1": "The same four rings, the same pan. Using the big ring costs you the room for the third small one.",
        "phase_x": "radius of the small rings  s",
        "phase_y": "radius of the large ring  b",
        "phase_title": "Where the two objectives disagree\npan R = 10, width w = 1",
        "leg0": "agree: better without the large ring",
        "leg1": "agree: the large ring dominates",
        "leg2": "DIVERGE: area wants it, count refuses it",
        "star": "the worked example\n(b = 9.0, s = 4.2)",
        "bestfit": "best fit — 3 rings",
        "worstfit": "worst fit — 4 rings",
        "stranded": "4.8 fits nowhere",
        "cap3": "Same four rings, two placement rules. Nesting the 5 looks tidy and strands the 4.8.",
        "thick_area": "area optimum: 1 ring",
        "thick_count": "count optimum: 2 rings",
        "thick_cap": "Thick rings, no hole big enough to nest in: the problem has quietly become circle packing.",
        "twins_hole": "hole of the 10 = 9.495",
        "twins_i1": "I₁ tail: 4.99 + 4.50 = 9.49  ≤  9.495   →  the 5 belongs in the pan",
        "twins_i2": "I₂ tail: 4.76 + 4.74 = 9.50  >  9.495   →  the 5 belongs in the hole",
        "twins_state": "identical at the decisive step: same containers, same capacities,\nsame occupants, same incoming ring, same R and w",
        "twins_cap": "The rule must decide where the 5 goes. Everything it can observe is the same; the right answer is opposite.",
        "incoming": "incoming: 5",
        "rigid": "the model: rigid rings",
        "real": "real squid: rings bend",
        "overlap_lost": "contact lost only here",
        "overlap_cap": "A ring resting on another still sears everywhere outside the overlap. The rigid model forbids the pose entirely.",
        "card_greedy": "greedy: 2 rings, best area",
        "card_more": "but three rings fit",
        "card_cap": "Superincreasing radii, and the greedy still loses on count: cardinality is not superadditive.",
    },
    "es": {
        "sear": "óptimo de área",
        "count": "óptimo de número",
        "rings2": "2 aros · área 76,7",
        "rings3": "3 aros · área 69,7",
        "cap1": "Los mismos cuatro aros, la misma sartén. Usar el aro grande te cuesta el sitio del tercer pequeño.",
        "phase_x": "radio de los aros pequeños  s",
        "phase_y": "radio del aro grande  b",
        "phase_title": "Dónde discrepan los dos objetivos\nsartén R = 10, grosor w = 1",
        "leg0": "coinciden: mejor sin el aro grande",
        "leg1": "coinciden: el aro grande domina",
        "leg2": "DIVERGEN: el área lo quiere, el número lo rechaza",
        "star": "el ejemplo del artículo\n(b = 9,0, s = 4,2)",
        "bestfit": "best fit — 3 aros",
        "worstfit": "worst fit — 4 aros",
        "stranded": "el 4,8 no cabe en ningún sitio",
        "cap3": "Los mismos cuatro aros, dos reglas de colocación. Anidar el 5 parece ordenado y deja fuera al 4,8.",
        "thick_area": "óptimo de área: 1 aro",
        "thick_count": "óptimo de número: 2 aros",
        "thick_cap": "Aros gruesos, ningún agujero en el que anidar: el problema ha degenerado en empaquetamiento de círculos.",
        "twins_hole": "agujero del 10 = 9,495",
        "twins_i1": "cola de I₁: 4,99 + 4,50 = 9,49  ≤  9,495   →  el 5 va a la sartén",
        "twins_i2": "cola de I₂: 4,76 + 4,74 = 9,50  >  9,495   →  el 5 va al agujero",
        "twins_state": "idéntico en el paso decisivo: mismos contenedores, mismas capacidades,\nmismos ocupantes, mismo aro entrante, mismos R y w",
        "twins_cap": "La regla decide dónde va el 5. Todo lo que puede observar es igual; la respuesta correcta es la contraria.",
        "incoming": "entra: 5",
        "rigid": "el modelo: aros rígidos",
        "real": "calamar real: los aros se doblan",
        "overlap_lost": "solo aquí se pierde contacto",
        "overlap_cap": "Un aro apoyado sobre otro sigue dorando fuera del solape. El modelo rígido prohíbe la postura entera.",
        "card_greedy": "el voraz: 2 aros, área óptima",
        "card_more": "pero caben tres aros",
        "card_cap": "Radios superincrecientes, y aun así el voraz pierde en número: la cardinalidad no es superaditiva.",
    },
}


def area(r: float, w: float) -> float:
    return math.pi * (r**2 - max(0.0, r - w) ** 2)


def ring(ax, centre, r, w, colour, alpha=0.92):
    ax.add_patch(
        Wedge(centre, r, 0, 360, width=min(w, r), facecolor=colour, edgecolor="none", alpha=alpha)
    )


def pan(ax, R):
    ax.add_patch(Circle((0, 0), R, facecolor=PAN, edgecolor=PAN_EDGE, linewidth=1.4))


def frame(ax, R, bottom=1.1):
    ax.set_xlim(-R * 1.1, R * 1.1)
    ax.set_ylim(-R * bottom, R * 1.1)
    ax.set_aspect("equal")
    ax.axis("off")


def label(ax, centre, text, colour=TEXT, size=10):
    """The radius, written inside its own ring — a 5 and a 4.9 are the same
    circle to the eye, and the whole point of the figure is which is which."""
    ax.text(centre[0], centre[1], text, color=colour, fontsize=size,
            ha="center", va="center", family="monospace")


def save(fig, name):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=BG, edgecolor="none", dpi=110, bbox_inches="tight",
                pad_inches=0.25)
    plt.close(fig)
    print(f"wrote {path}")


# ---------------------------------------------------------------- figure 1

def figure_minimal(lang):
    s = STRINGS[lang]
    R, w, big, small = 10.0, 1.0, 9.0, 4.2

    fig = plt.figure(figsize=(9.6, 5.2), dpi=110)
    fig.patch.set_facecolor(BG)
    left = fig.add_axes([0.04, 0.16, 0.44, 0.70])
    right = fig.add_axes([0.52, 0.16, 0.44, 0.70])
    for ax in (left, right):
        frame(ax, R)
        pan(ax, R)

    ring(left, (0, 0), big, w, AMBER)
    ring(left, (0, 0), small, w, AMBER)
    label(left, (0, (big + small) / 2), "9.0", AMBER)
    label(left, (0, 0), "4.2", AMBER)

    d = R - small  # each small ring tangent to the pan wall
    for k in range(3):
        a = math.radians(90 + 120 * k)
        centre = (d * math.cos(a), d * math.sin(a))
        ring(right, centre, small, w, TEAL)
        label(right, centre, "4.2")

    assert abs(area(big, w) + area(small, w) - 76.7) < 0.1
    assert abs(3 * area(small, w) - 69.7) < 0.1

    fig.text(0.26, 0.93, s["sear"], color=AMBER, fontsize=14, ha="center", fontweight="bold")
    fig.text(0.74, 0.93, s["count"], color=TEAL, fontsize=14, ha="center", fontweight="bold")
    fig.text(0.26, 0.10, s["rings2"], color=TEXT, fontsize=12, ha="center", family="monospace")
    fig.text(0.74, 0.10, s["rings3"], color=TEXT, fontsize=12, ha="center", family="monospace")
    fig.text(0.5, 0.025, s["cap1"], color=MUTED, fontsize=10, ha="center", fontstyle="italic")
    save(fig, f"count-the-rings-fig-1-{lang}.png")


# ---------------------------------------------------------------- figure 2

def figure_phase(lang):
    """Ported from calamares/code/franja.py — same thresholds, same family."""
    s = STRINGS[lang]
    R, w = 10.0, 1.0

    def ring_ratio(k):
        return 1.0 / (1.0 + 1.0 / math.sin(math.pi / k))

    Q = {1: 1.0, 2: 0.5}
    for k in range(3, 7):
        Q[k] = ring_ratio(k)
    Q[7] = Q[6]
    Q[8] = ring_ratio(7)
    Q[9] = ring_ratio(8)
    Q[10] = 0.262258924

    def maxfit(q):
        best = 0
        for n in range(1, 11):
            if q <= Q[n] + 1e-12:
                best = n
        return best

    def a(r):
        return math.pi * w * (2 * r - w)

    smalls = np.arange(2.65, 5.201, 0.01)
    bigs = np.arange(4.80, 9.801, 0.01)
    grid = np.zeros((len(bigs), len(smalls)), dtype=int)

    for i, b in enumerate(bigs):
        hole = b - w
        for j, sm in enumerate(smalls):
            n_pan = maxfit(sm / R)
            n_hole = maxfit(sm / hole) if sm <= hole else 0
            a_cnt, a_area = 1 + n_hole, a(b) + n_hole * a(sm)
            b_cnt, b_area = n_pan, n_pan * a(sm)
            if b_cnt > a_cnt and a_area > b_area:
                grid[i, j] = 2
            elif a_cnt > b_cnt and b_area > a_area:
                grid[i, j] = 3
            elif a_area >= b_area and a_cnt >= b_cnt:
                grid[i, j] = 1
            else:
                grid[i, j] = 0

    # The inverse-divergence class must stay empty; if it ever fills, the
    # figure is claiming something the paper does not.
    assert not (grid == 3).any(), "inverse divergence appeared — check the model"

    fig, ax = plt.subplots(figsize=(8.4, 5.6), dpi=110)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    cmap = ListedColormap(["#2f3b4d", "#7c6742", "#c0392b", "#7d3c98"])
    ax.imshow(grid, origin="lower", aspect="auto", cmap=cmap, vmin=0, vmax=3,
              extent=[smalls[0], smalls[-1], bigs[0], bigs[-1]])
    ax.plot([4.2], [9.0], marker="*", ms=17, color=TEXT, mec=BG, mew=1.2)
    ax.annotate(s["star"], (4.2, 9.0), textcoords="offset points", xytext=(14, -34),
                fontsize=9.5, color=TEXT)

    ax.set_xlabel(s["phase_x"], fontsize=11.5, color=TEXT)
    ax.set_ylabel(s["phase_y"], fontsize=11.5, color=TEXT)
    ax.set_title(s["phase_title"], fontsize=12.5, color=TEXT, pad=12)
    ax.tick_params(colors=MUTED, labelsize=9.5)
    for spine in ax.spines.values():
        spine.set_color(PAN_EDGE)

    legend = ax.legend(
        handles=[
            Patch(fc="#2f3b4d", label=s["leg0"]),
            Patch(fc="#7c6742", label=s["leg1"]),
            Patch(fc="#c0392b", label=s["leg2"]),
        ],
        loc="lower left", fontsize=9, framealpha=0.95, facecolor="#11111a", edgecolor=PAN_EDGE,
    )
    for text in legend.get_texts():
        text.set_color(TEXT)

    save(fig, f"count-the-rings-fig-2-{lang}.png")


# ---------------------------------------------------------------- figure 3

def figure_n4(lang):
    s = STRINGS[lang]
    R, w = 15.0, 0.3

    fig = plt.figure(figsize=(9.6, 5.8), dpi=110)
    fig.patch.set_facecolor(BG)
    left = fig.add_axes([0.04, 0.16, 0.44, 0.70])
    right = fig.add_axes([0.52, 0.16, 0.44, 0.70])
    for ax in (left, right):
        frame(ax, R, bottom=1.55)  # room below the pan for the rejected ring
        pan(ax, R)

    # Worst fit (right): 10 and 5 internally tangent to the pan and to each
    # other (10 + 5 = 15 = R); 4.9 and 4.8 exactly fill the hole of the 10
    # (4.9 + 4.8 = 9.7 = 10 - w).
    c_big = (-5.0, 0.0)
    c_five = (10.0, 0.0)
    assert abs(math.dist(c_big, c_five) - 15.0) < 1e-9
    hole = 10.0 - w
    assert abs(4.9 + 4.8 - hole) < 1e-9
    c_49 = (c_big[0] - (hole - 4.9), 0.0)
    c_48 = (c_big[0] + (hole - 4.8), 0.0)

    ring(right, c_big, 10.0, w, AMBER)
    ring(right, c_five, 5.0, w, TEAL)
    ring(right, c_49, 4.9, w, TEAL)
    ring(right, c_48, 4.8, w, TEAL)
    label(right, (c_big[0], c_big[1] + 10.0 - 1.1), "10", AMBER)
    label(right, c_five, "5")
    label(right, c_49, "4.9")
    label(right, c_48, "4.8")

    # Best fit (left): the 5 goes into the snug container — the hole of the 10
    # — which pushes the 4.9 out into the pan and leaves the 4.8 homeless.
    c_five_nested = (c_big[0] + (hole - 5.0), 0.0)
    ring(left, c_big, 10.0, w, AMBER)
    ring(left, c_five_nested, 5.0, w, TEAL)
    ring(left, (10.0, 0.0), 4.9, w, TEAL)
    label(left, (c_big[0], c_big[1] + 10.0 - 1.1), "10", AMBER)
    label(left, c_five_nested, "5")
    label(left, (10.0, 0.0), "4.9")

    # The 4.8 is drawn outside the pan on purpose: it is the ring this run
    # never places. Keeping it clear of the rim stops it reading as a
    # drawing error rather than as a rejection.
    rejected = (0.0, -R * 1.28)
    ring(left, rejected, 4.8, w, SLATE, alpha=0.55)
    label(left, rejected, "4.8", MUTED)
    left.plot([-6.6], [rejected[1]], marker="x", ms=13, color="#f87171", mew=2.6)

    fig.text(0.26, 0.93, s["bestfit"], color=MUTED, fontsize=13, ha="center", fontweight="bold")
    fig.text(0.74, 0.93, s["worstfit"], color=TEXT, fontsize=13, ha="center", fontweight="bold")
    fig.text(0.26, 0.095, s["stranded"], color="#f87171", fontsize=10.5, ha="center")
    fig.text(0.5, 0.025, s["cap3"], color=MUTED, fontsize=10, ha="center", fontstyle="italic")
    save(fig, f"count-the-rings-fig-3-{lang}.png")


# ---------------------------------------------------------------- figure 0

def figure_thick(lang):
    """Three thick rings: the degenerate divergence, where no hole can nest."""
    s = STRINGS[lang]
    R, w = 10.0, 4.5
    big, p, q = 8.0, 101 / 20, 99 / 20

    fig = plt.figure(figsize=(9.6, 5.2), dpi=110)
    fig.patch.set_facecolor(BG)
    left = fig.add_axes([0.04, 0.16, 0.44, 0.70])
    right = fig.add_axes([0.52, 0.16, 0.44, 0.70])
    for ax in (left, right):
        frame(ax, R)
        pan(ax, R)

    ring(left, (0, 0), big, w, AMBER)
    label(left, (0, big - w / 2), "8", AMBER)

    # p and q are exactly diametral: p + q = 10, so both are tangent to the
    # pan wall and to each other.
    assert abs(p + q - R) < 1e-12
    ring(right, (-(R - p), 0), p, w, TEAL)
    ring(right, ((R - q), 0), q, w, TEAL)
    label(right, (-(R - p), 0), "5.05" if lang == "en" else "5,05")
    label(right, ((R - q), 0), "4.95" if lang == "en" else "4,95")

    a_left, a_right = area(big, w), area(p, w) + area(q, w)
    assert a_left > a_right
    fmt = (lambda v: f"{v:.1f}") if lang == "en" else (lambda v: f"{v:.1f}".replace(".", ","))

    fig.text(0.26, 0.93, s["thick_area"], color=AMBER, fontsize=13.5, ha="center", fontweight="bold")
    fig.text(0.74, 0.93, s["thick_count"], color=TEAL, fontsize=13.5, ha="center", fontweight="bold")
    fig.text(0.26, 0.10, f"207π/4 = {fmt(a_left)}", color=TEXT, fontsize=12, ha="center", family="monospace")
    fig.text(0.74, 0.10, f"198π/4 = {fmt(a_right)}", color=TEXT, fontsize=12, ha="center", family="monospace")
    fig.text(0.5, 0.025, s["thick_cap"], color=MUTED, fontsize=10, ha="center", fontstyle="italic")
    save(fig, f"count-the-rings-fig-0-{lang}.png")


# ---------------------------------------------------------------- figure 4

def figure_twins(lang):
    """The twins: identical observable state, opposite correct decisions."""
    s = STRINGS[lang]
    R, w = 15.0, 0.505
    hole = 10.0 - w
    assert abs(hole - 9.495) < 1e-12
    assert 4.99 + 4.50 <= hole and 4.76 + 4.74 > hole

    fig = plt.figure(figsize=(10.0, 5.6), dpi=110)
    fig.patch.set_facecolor(BG)
    top = fig.add_axes([0.02, 0.50, 0.27, 0.34])
    bottom = fig.add_axes([0.02, 0.10, 0.27, 0.34])

    for ax in (top, bottom):
        frame(ax, R)
        pan(ax, R)
        ring(ax, (-5.0, 0.0), 10.0, w, AMBER)
        label(ax, (-5.0, 10.0 - 1.4), "10", AMBER)
        # The 5 shown at the rim, still undecided: this is the ring the rule
        # is about to place, not a placement.
        ring(ax, (10.0, 0.0), 5.0, w, TEAL, alpha=0.5)
        label(ax, (10.0, 0.0), "5")

    fig.text(0.5, 0.955, s["twins_state"], color=MUTED, fontsize=11,
             ha="center", va="top", linespacing=1.5)
    fig.text(0.155, 0.865, s["incoming"], color=TEXT, fontsize=10.5,
             ha="center", family="monospace")
    fig.text(0.155, 0.055, s["twins_hole"], color=MUTED, fontsize=10,
             ha="center", family="monospace")

    fig.text(0.33, 0.665, s["twins_i1"], color=TEAL, fontsize=11.5, family="monospace")
    fig.text(0.33, 0.265, s["twins_i2"], color=AMBER, fontsize=11.5, family="monospace")
    fig.text(0.5, 0.012, s["twins_cap"], color=MUTED, fontsize=10,
             ha="center", fontstyle="italic")
    save(fig, f"count-the-rings-fig-4-{lang}.png")


# ---------------------------------------------------------------- figure 5

def figure_cardinality(lang):
    """Superincreasing radii where the greedy is still suboptimal for count."""
    s = STRINGS[lang]
    R, w = 10.0, 4.8
    radii = [9.95, 5.0, 4.3, 0.6]
    for i, r in enumerate(radii):  # the instance really is superincreasing
        assert r > sum(radii[i + 1:]) - 1e-12, (r, radii[i + 1:])

    fig = plt.figure(figsize=(9.6, 5.2), dpi=110)
    fig.patch.set_facecolor(BG)
    left = fig.add_axes([0.04, 0.16, 0.44, 0.70])
    right = fig.add_axes([0.52, 0.16, 0.44, 0.70])
    for ax in (left, right):
        frame(ax, R)
        pan(ax, R)

    ring(left, (0, 0), 9.95, w, AMBER)
    label(left, (0, 9.95 - w / 2), "9.95" if lang == "en" else "9,95", AMBER)
    ring(left, (0, 0), 5.0, w, AMBER)   # nests: 5.0 <= 9.95 - 4.8 = 5.15
    label(left, (0, 0), "5")
    assert 5.0 <= 9.95 - w

    # In a row across the pan: diameters 10 + 8.6 + 1.2 = 19.8 <= 20.
    xs, prev = [], -R
    for r in (5.0, 4.3, 0.6):
        xs.append(prev + r)
        prev = xs[-1] + r
    assert prev <= R + 1e-12
    for x, r, lab in zip(xs, (5.0, 4.3, 0.6), ("5", "4.3" if lang == "en" else "4,3", "")):
        ring(right, (x, 0), r, w, TEAL)
        if lab:
            label(right, (x, 0), lab)
    right.annotate("0.6" if lang == "en" else "0,6", (xs[2], 0), textcoords="offset points",
                   xytext=(2, 26), fontsize=9.5, color=TEXT, ha="center", family="monospace")

    fig.text(0.26, 0.93, s["card_greedy"], color=AMBER, fontsize=13, ha="center", fontweight="bold")
    fig.text(0.74, 0.93, s["card_more"], color=TEAL, fontsize=13, ha="center", fontweight="bold")
    fig.text(0.5, 0.025, s["card_cap"], color=MUTED, fontsize=10, ha="center", fontstyle="italic")
    save(fig, f"count-the-rings-fig-5-{lang}.png")


# ---------------------------------------------------------------- figure 6

def figure_overlap(lang):
    """The idealization the model makes: rings never ride on top of each other."""
    s = STRINGS[lang]
    R, w = 10.0, 1.0
    r1, r2 = 5.2, 4.4

    fig = plt.figure(figsize=(9.6, 5.2), dpi=110)
    fig.patch.set_facecolor(BG)
    left = fig.add_axes([0.04, 0.16, 0.44, 0.70])
    right = fig.add_axes([0.52, 0.16, 0.44, 0.70])
    for ax in (left, right):
        frame(ax, R)
        pan(ax, R)

    # Left: the model. Siblings are packed as balls with disjoint interiors —
    # here at exact tangency, the closest the model ever allows them.
    ring(left, (-(R - r1) + 0.4, 0), r1, w, TEAL)
    ring(left, ((R - r2) - 0.4, 0), r2, w, TEAL)

    # Right: the same two rings overlapping. Centres closer than r1 + r2, so
    # the annuli cross: the pose the model has no room for.
    d = (r1 + r2) * 0.62
    cl, cr = (-d / 2, 0.0), (d / 2, 0.0)
    assert d < r1 + r2
    ring(right, cl, r1, w, TEAL)
    ring(right, cr, r2, w, AMBER)
    # Mark where the annuli actually cross. Two circles of radii r1, r2 whose
    # centres are d apart meet at x = (d^2 + r1^2 - r2^2) / 2d from the left
    # centre, at y = +/- sqrt(r1^2 - x^2) — two points, above and below the
    # axis, not on it.
    ax_ = (d**2 + r1**2 - r2**2) / (2 * d)
    ay = math.sqrt(r1**2 - ax_**2)
    for sign in (1, -1):
        right.add_patch(Circle((cl[0] + ax_, sign * ay), 1.05,
                               facecolor="#f87171", edgecolor="none", alpha=0.32))

    fig.text(0.26, 0.93, s["rigid"], color=TEAL, fontsize=13.5, ha="center", fontweight="bold")
    fig.text(0.74, 0.93, s["real"], color=AMBER, fontsize=13.5, ha="center", fontweight="bold")
    fig.text(0.74, 0.10, s["overlap_lost"], color="#f87171", fontsize=10.5, ha="center")
    fig.text(0.5, 0.025, s["overlap_cap"], color=MUTED, fontsize=10, ha="center", fontstyle="italic")
    save(fig, f"count-the-rings-fig-6-{lang}.png")


def main():
    for lang in ("en", "es"):
        figure_thick(lang)
        figure_minimal(lang)
        figure_phase(lang)
        figure_n4(lang)
        figure_twins(lang)
        figure_cardinality(lang)
        figure_overlap(lang)


if __name__ == "__main__":
    main()
