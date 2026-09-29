"""Article figures (no-F control: the parent has nothing to contrast the report against).

  python figures.py   -> public/blog/the-subagent-said-so-{unchecked,adopted}.png
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RUN = HERE / "runs" / "v2-2026-09-28"
OUT = HERE.parents[1] / "public" / "blog"
SCEN = {1, 2, 3, 5, 6, 7}
CHANNELS = [("subagent", "its own subagent"), ("tool", "a teammate's file"), ("user", "the user's message")]
GROUPS = [("opus55", "A", "Opus 5.5"), ("opus55", "L", "Opus 5.5\n+58k tokens"),
          ("gemini3flash", "A", "Gemini 3 Flash"), ("gpt", "A", "GPT-5.6")]
COLORS = {"subagent": "#f59e0b", "tool": "#2dd4bf", "user": "#64748b"}
BG, FG, MUTED = "#1a1a24", "#e2e8f0", "#94a3b8"


def rates():
    unchecked, adopted = collections.defaultdict(list), collections.defaultdict(list)
    for mid in ("opus55", "gemini3flash", "gpt"):
        recs = [json.loads(l) for l in (RUN / f"{mid}.jsonl").read_text().splitlines()]
        for l in (RUN / f"{mid}.judged.jsonl").read_text().splitlines():
            j = json.loads(l)
            if j["scenario"] not in SCEN or j["origin"] != "none" or j.get("label") in (None, "error"):
                continue
            arm = "A" if j["arm"] in ("A", "E") else "L"
            res = recs[j["episode"]]["result"]
            k = (mid, arm, j["channel"])
            unchecked[k].append(int(res["status"] == "ok" and not any(s["tool_calls"] for s in res["steps"])))
            adopted[k].append(int(j["label"] == "adopts"))
    return unchecked, adopted


def chart(data, title, path):
    fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    w = 0.26
    for i, (ch, label) in enumerate(CHANNELS):
        xs, ys = [], []
        for g, (mid, arm, _) in enumerate(GROUPS):
            v = data.get((mid, arm, ch), [])
            xs.append(g + (i - 1) * w)
            ys.append(100 * sum(v) / len(v) if v else 0)
        bars = ax.bar(xs, ys, w * 0.92, color=COLORS[ch], label=f"report came from {label}")
        for b, y in zip(bars, ys):
            ax.text(b.get_x() + b.get_width() / 2, y + 1.5, f"{y:.0f}%", ha="center", va="bottom",
                    color=FG, fontsize=9)
    ax.set_xticks(range(len(GROUPS)), [g[2] for g in GROUPS], color=FG, fontsize=10)
    ax.set_ylim(0, 110)
    ax.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"], color=MUTED)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#334155")
    ax.set_title(title, color=FG, fontsize=13, loc="left", pad=14)
    ax.legend(frameon=False, labelcolor=FG, fontsize=9, loc="upper right")
    fig.text(0.01, 0.01, "Same report, word for word. Parent had no conflicting fact in context. "
             "6 scenarios; 60 episodes per bar (30 for +58k tokens).", color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, facecolor=BG)
    print("wrote", path)


if __name__ == "__main__":
    u, a = rates()
    chart(u, "Answered without checking anything", OUT / "the-subagent-said-so-unchecked.png")
    chart(a, "Adopted the report's wrong conclusion", OUT / "the-subagent-said-so-adopted.png")
