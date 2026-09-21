#!/usr/bin/env python3
"""Render the bilingual article figures from the public pilot export.

Run from any directory: python3 experiments/prompt-meaning/v2/article_figures.py
Requires matplotlib. No inference or network calls.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/prompt-meaning-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[3]
RESULTS = Path(__file__).parent / "results/pilot-2026-09-21-v2"
OUT = ROOT / "public/blog"
SLUG = "now-it-seems-to-mean-something"
DATA = json.loads((RESULTS / "data.json").read_text())
SUMMARY = json.loads((RESULTS / "summary.json").read_text())
DIAGNOSTICS = json.loads((RESULTS / "diagnostics.json").read_text())
BG, FG, MUTED = "#1a1a24", "#f8fafc", "#94a3b8"
TEAL, AMBER, SLATE, RED = "#2dd4bf", "#fbbf24", "#64748b", "#fb7185"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": FG,
                     "figure.facecolor": BG, "axes.facecolor": BG,
                     "savefig.facecolor": BG})


def decision(model, variant, rep):
    matches = [r for r in DATA["records"] if
               r["job"].get("stage") == "execute" and
               r["job"].get("case_id") == "synthetic-retention-suggestive" and
               r["job"].get("model_id") == model and
               r["job"].get("variant") == variant and
               r["job"].get("repetition") == rep]
    assert len(matches) == 1
    response = matches[0]["attempts"][-1]
    assert response["status"] == "ok"
    try:
        parsed = json.loads(response["text"])
    except json.JSONDecodeError:
        return "invalid"
    decisions = parsed["decisions"]
    assert len(decisions) == 12 and set(decisions.values()) <= {"allow", "deny", "review"}
    return decisions["c07"]


def canvas(height):
    fig, ax = plt.subplots(figsize=(12, height), dpi=160)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set(xlim=(0, 12), ylim=(0, height))
    ax.axis("off")
    return fig, ax


def results(lang):
    es = lang == "es"
    fig, ax = canvas(6.3)
    ax.text(.4, 5.85, "Mismo registro, cuatro instrucciones" if es else
            "Same record, four instructions", fontsize=23, weight="bold")
    ax.text(.4, 5.42, "Requiere aprobación · no aprobada · dos llamadas por celda" if es else
            "Approval required · not approved · two calls per cell", fontsize=15, color=MUTED)
    ax.text(6.75, 4.83, "GPT-5.6 Sol", ha="center", fontsize=18, weight="bold")
    ax.text(10, 4.83, "Claude Opus 5", ha="center", fontsize=18, weight="bold")
    names = (["Frase sin definir\nconditional approval closure", "Sin la frase", "Nombre sustituido\nnavic alignment", "Regla explícita\nPolítica completa"] if es else
             ["Undefined phrase\nconditional approval closure", "Phrase removed", "Name replaced\nnavic alignment", "Explicit rule\nComplete policy"])
    for i, variant in enumerate(["original", "eliminated", "substituted", "explicit"]):
        y = 4.05 - i * 1.04
        ax.text(.4, y, names[i], va="center", fontsize=17, linespacing=1.5)
        for model, x in [("gpt-sol", 6.75), ("claude-opus", 10)]:
            for rep, dx in [(0, -.77), (1, .77)]:
                label = decision(model, variant, rep)
                color = {"allow": TEAL, "review": AMBER, "invalid": MUTED}[label]
                ax.add_patch(FancyBboxPatch((x + dx - .68, y - .25), 1.36, .5,
                             boxstyle="round,pad=0.05,rounding_size=0.08", linewidth=1,
                             edgecolor=color, facecolor=color, alpha=.15))
                shown = "inválida" if es and label == "invalid" else label
                ax.text(x + dx, y, shown, va="center", ha="center", fontsize=17, color=color)
        ax.plot([.4, 11.6], [y - .49, y - .49], color=SLATE, alpha=.28, lw=.7)
    ax.text(.4, .25, "c07 · Cada resultado corresponde a una llamada nueva." if es else
            "c07 · Every result comes from a fresh call.", fontsize=14, color=MUTED)
    suffix = "" if lang == "en" else "-es"
    fig.savefig(OUT / f"{SLUG}-fig-1{suffix}.png")
    plt.close(fig)


def coverage(lang):
    es = lang == "es"
    fig, ax = canvas(8.2)
    ax.text(.4, 7.75, "Cuánto respondieron, cuánto pudimos contrastar" if es else
            "What they answered, what we could check", fontsize=22, weight="bold")
    ax.text(.4, 7.25, "Decisiones predichas · 96 inputs originales por modelo" if es else
            "Predicted decisions · 96 original inputs per model", fontsize=17)
    for model, y, name in [("gpt-sol", 6.57, "GPT"), ("claude-opus", 5.83, "Opus")]:
        counts = DIAGNOSTICS["original_prediction_coverage"][model]
        abstained = counts["undetermined"]
        concrete = sum(counts.values()) - abstained
        assert concrete + abstained == 96
        ax.text(.4, y, name, fontsize=18, va="center")
        left = 1.6
        for n, color in [(concrete, TEAL), (abstained, SLATE)]:
            width = 9.9 * n / 96
            ax.barh(y, width, left=left, height=.43, color=color)
            ax.text(left + width / 2, y, str(n), color=BG if color == TEAL else FG,
                    ha="center", va="center", fontsize=17, weight="bold")
            left += width
    ax.text(1.6, 5.2, "■ Concretas" if es else "■ Concrete", fontsize=16, color=TEAL)
    ax.text(5, 5.2, "■ Abstenciones" if es else "■ Abstentions", fontsize=16, color=MUTED)
    ax.plot([.4, 11.6], [4.75, 4.75], color=SLATE, alpha=.4)
    ax.text(.4, 4.24, "Contrastes · 768 pares previstos por explicador" if es else
            "Contrasts · 768 planned pairs per explainer", fontsize=17)
    for model, y, name in [("gpt-sol", 3.54, "GPT"), ("claude-opus", 2.8, "Opus")]:
        rows = [r for r in SUMMARY["predictions"] if r["kind"] == "synthetic" and r["explainer"] == model]
        correct = sum(r.get("exact_action_pair_matches", 0) for r in rows)
        scorable = sum(r.get("scorable_pairs", 0) for r in rows)
        abstained = sum(r.get("abstained_pairs", 0) for r in rows)
        invalid = sum(r.get("missing_or_invalid_pairs", 0) for r in rows)
        assert scorable + abstained + invalid == 768
        ax.text(.4, y, name, fontsize=18, va="center")
        left = 1.6
        for n, color in [(correct, TEAL), (scorable-correct, RED), (abstained, SLATE), (invalid, AMBER)]:
            width = 9.9 * n / 768
            ax.barh(y, width, left=left, height=.43, color=color)
            if n > 75:
                ax.text(left + width / 2, y, str(n), ha="center", va="center", fontsize=17,
                        color=BG if color in [TEAL, AMBER] else FG, weight="bold")
            left += width
        text = f"{correct}/{scorable} " + ("evaluables exactos" if es else "scorable pairs exact")
        ax.text(1.6, y - .4, text, fontsize=14, color=MUTED)
    for x, y, label, color in [(1.6, 1.8, "Exactos" if es else "Exact", TEAL),
                               (6.4, 1.8, "Discrepancias" if es else "Mismatches", RED),
                               (1.6, 1.3, "Abstenciones" if es else "Abstentions", MUTED),
                               (6.4, 1.3, "Formato inválido" if es else "Invalid format", AMBER)]:
        ax.text(x, y, "■ " + label, fontsize=16, color=color)
    ax.text(.4, .5, "Los pares reutilizan casos y repeticiones; no son problemas independientes." if es else
            "Pairs reuse cases and repetitions; they are not independent problems.", fontsize=14, color=MUTED)
    suffix = "" if lang == "en" else "-es"
    fig.savefig(OUT / f"{SLUG}-fig-2{suffix}.png")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "es"):
        results(lang)
        coverage(lang)
    print("Rendered four figures from the exported results.")
