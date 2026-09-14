#!/usr/bin/env python3
"""Hero and in-article figures for "Proved, Certified, Swept, Sampled" (EN + ES).

  hero   the four epistemic labels as a ladder, each with what it actually
         guarantees and what can still knock it over.
  fig 1  why a tolerance is not a small sin: at an exactly tangent
         configuration the feasibility margin is zero, so any epsilon-thick
         acceptance band reports "fits" at the one point where the question
         is delicate. Schematic on purpose — see the caption.
  fig 2  the four rounds of the quintet certificate: what each version
         claimed, what refuted it, and what was left standing.

Usage: python docs/marketing/hero-sources/proved-certified-swept-sampled.py
"""

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

OUT = Path("public/blog")
SLUG = "proved-certified-swept-sampled"

BG = "#1a1a24"
PANEL = "#252533"
EDGE = "#3f3f52"
TEAL = "#2dd4bf"
AMBER = "#f59e0b"
RED = "#f87171"
SLATE = "#64748b"
TEXT = "#f8fafc"
MUTED = "#94a3b8"

LADDER = {
    "en": [
        ("proved", "a written proof; the machine can only recheck it", TEAL),
        ("box-certified", "exact rational arithmetic over the whole domain", "#5eead4"),
        ("grid-swept", "checked on a mesh — silent between the points", AMBER),
        ("sampled", "no contradiction found in the draws taken", RED),
    ],
    "es": [
        ("probado", "una demostración escrita; la máquina solo la recomprueba", TEAL),
        ("certificado por cajas", "aritmética racional exacta en todo el dominio", "#5eead4"),
        ("barrido en malla", "comprobado en una malla — mudo entre los puntos", AMBER),
        ("muestreado", "no se halló contradicción en las muestras tomadas", RED),
    ],
}

STR = {
    "en": {
        "hero_title": "how much is this claim actually worth?",
        "hero_foot": "four labels, one per claim — not a green tick for the whole paper",
        "f1_title": "Why a tolerance is not a small sin",
        "f1_x": "configuration parameter",
        "f1_y": "feasibility margin",
        "f1_exact": "exact answer: does not fit (margin = 0, tangent)",
        "f1_tol": "with an ε-thick acceptance band: reports FITS",
        "f1_point": "the golden point",
        "f1_cap": "Schematic: the curve is illustrative, the mechanism is not. The margin vanishes exactly at the golden point, so any tolerance turns 'touches' into 'clears' at precisely the configuration the proof turns on.",
        "f2_title": "Four certificates for one lemma",
        "f2_cap": "Three of the four were refuted. The last one assumes no floating-point fact at all.",
        "rounds": [
            ("v1", "meshes without a Lipschitz bound,\nan LP with tolerances,\nR₃ ≤ M merely sampled", RED),
            ("v2", "rational-directed — and still refuted:\nthe 1e-12 tolerance thickened the\ntangent variety at the golden point", RED),
            ("v3", "adds the trio theorem the refuter\nsupplied; still leans on mpmath", AMBER),
            ("v4", "rational series with an alternating\nLagrange remainder; asin used as an\noracle that is not believed", TEAL),
        ],
    },
    "es": {
        "hero_title": "¿cuánto vale de verdad esta afirmación?",
        "hero_foot": "cuatro etiquetas, una por afirmación — no un visto bueno para el paper entero",
        "f1_title": "Por qué una tolerancia no es un pecado pequeño",
        "f1_x": "parámetro de la configuración",
        "f1_y": "margen de factibilidad",
        "f1_exact": "respuesta exacta: no cabe (margen = 0, tangente)",
        "f1_tol": "con una banda de aceptación de grosor ε: dice QUE CABE",
        "f1_point": "el punto áureo",
        "f1_cap": "Esquema: la curva es ilustrativa, el mecanismo no. El margen se anula exactamente en el punto áureo, así que cualquier tolerancia convierte «toca» en «pasa holgado» justo en la configuración de la que depende la prueba.",
        "f2_title": "Cuatro certificados para un lema",
        "f2_cap": "Tres de los cuatro fueron refutados. El último no asume ningún hecho en coma flotante.",
        "rounds": [
            ("v1", "mallas sin cota de Lipschitz,\nun LP con tolerancias,\nR₃ ≤ M solo muestreado", RED),
            ("v2", "racional-dirigido — y aun así refutado:\nla tolerancia 1e-12 engordaba la\nvariedad tangente en el punto áureo", RED),
            ("v3", "incorpora el teorema del trío que\naportó el refutador; aún con mpmath", AMBER),
            ("v4", "serie racional con resto de Lagrange\nalternante; asin usado como oráculo\nque no se cree", TEAL),
        ],
    },
}


def save(fig, name):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=BG, edgecolor="none", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(f"wrote {path}")


def hero(lang):
    rows = LADDER[lang]
    s = STR[lang]
    fig = plt.figure(figsize=(10.20, 5.10), dpi=100)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 10.2)
    ax.set_ylim(0, 5.1)
    ax.axis("off")

    ax.text(0.5, 4.62, s["hero_title"], color=TEXT, fontsize=16, fontweight="bold")

    # A ladder: each rung is inset from the one above, so the drop in strength
    # is visible before a single word is read.
    for i, (name, blurb, colour) in enumerate(rows):
        y = 3.75 - i * 0.82
        x0, width = 0.5 + i * 0.28, 8.9 - i * 0.55
        ax.add_patch(FancyBboxPatch((x0, y), width, 0.62,
                                    boxstyle="round,pad=0.02,rounding_size=0.08",
                                    facecolor=PANEL, edgecolor=colour, linewidth=1.7))
        ax.text(x0 + 0.22, y + 0.31, name, color=colour, fontsize=13,
                va="center", family="monospace", fontweight="bold")
        ax.text(x0 + 3.05, y + 0.31, blurb, color=MUTED, fontsize=10.5, va="center")

    ax.text(0.5, 0.28, s["hero_foot"], color=SLATE, fontsize=10.5, fontstyle="italic")

    path = OUT / f"{SLUG}.png"
    fig.savefig(path, facecolor=BG, edgecolor="none", dpi=100)
    plt.close(fig)

    from PIL import Image

    im = Image.open(path).convert("RGB").resize((1020, 510), Image.LANCZOS)
    im.save(path)
    print(f"wrote {path} ({im.size[0]}x{im.size[1]})")


def fig_tolerance(lang):
    s = STR[lang]
    fig, ax = plt.subplots(figsize=(8.6, 4.8), dpi=110)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    x = np.linspace(0, 10, 600)
    # A margin curve that touches zero from below at one point: the tangency.
    m = -0.35 * (x - 5.4) ** 2
    ax.plot(x, m, color=TEAL, linewidth=2.4)

    eps = 0.55  # exaggerated so it is visible at all; the real one was 1e-12
    ax.axhspan(-eps, eps, color=RED, alpha=0.16)
    ax.axhline(0, color=MUTED, linewidth=1.0, linestyle=(0, (4, 4)))
    ax.plot([5.4], [0], marker="o", ms=9, color=TEXT, mec=BG, mew=1.5, zorder=5)

    ax.annotate(s["f1_point"], (5.4, 0), textcoords="offset points", xytext=(14, 26),
                fontsize=10.5, color=TEXT,
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.2))
    # Clear of the curve: the parabola sweeps the middle of the panel.
    ax.text(0.03, 0.12, s["f1_exact"], color=MUTED, fontsize=10.5, transform=ax.transAxes)
    ax.text(0.03, 0.04, s["f1_tol"], color=RED, fontsize=10.5, transform=ax.transAxes)
    ax.text(0.985, (eps + 0.12) / 5.8 + 0.724, "ε", color=RED, fontsize=12,
            transform=ax.transAxes, ha="right", va="center")

    ax.set_xlabel(s["f1_x"], color=TEXT, fontsize=11)
    ax.set_ylabel(s["f1_y"], color=TEXT, fontsize=11)
    ax.set_title(s["f1_title"], color=TEXT, fontsize=13, pad=12)
    ax.set_xticks([])
    ax.set_yticks([0])
    ax.set_yticklabels(["0"])
    ax.tick_params(colors=MUTED)
    for sp in ax.spines.values():
        sp.set_color(EDGE)
    ax.set_ylim(-4.2, 1.6)

    fig.text(0.5, -0.02, s["f1_cap"], color=MUTED, fontsize=9.5, ha="center",
             fontstyle="italic", wrap=True)
    save(fig, f"{SLUG}-fig-1-{lang}.png")


def fig_rounds(lang):
    s = STR[lang]
    rounds = s["rounds"]
    fig = plt.figure(figsize=(9.8, 5.0), dpi=110)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 9.8)
    ax.set_ylim(0.95, 5.0)
    ax.axis("off")

    ax.text(0.35, 4.62, s["f2_title"], color=TEXT, fontsize=14, fontweight="bold")

    for i, (name, blurb, colour) in enumerate(rounds):
        x = 0.35 + i * 2.40
        ax.add_patch(FancyBboxPatch((x, 1.95), 2.05, 2.05,
                                    boxstyle="round,pad=0.03,rounding_size=0.10",
                                    facecolor=PANEL, edgecolor=colour, linewidth=1.8))
        ax.text(x + 0.22, 3.68, name, color=colour, fontsize=15,
                family="monospace", fontweight="bold")
        ax.text(x + 0.18, 3.32, textwrap.fill(blurb, 27), color=MUTED, fontsize=8.4,
                va="top", linespacing=1.6)
        if i < len(rounds) - 1:
            ax.annotate("", xy=(x + 2.36, 2.95), xytext=(x + 2.09, 2.95),
                        arrowprops=dict(arrowstyle="-|>", color=SLATE, lw=1.6))

    ax.text(0.35, 1.25, s["f2_cap"], color=MUTED, fontsize=10, fontstyle="italic")
    save(fig, f"{SLUG}-fig-2-{lang}.png")


def main():
    for lang in ("en", "es"):
        fig_tolerance(lang)
        fig_rounds(lang)
    hero("en")


if __name__ == "__main__":
    main()
